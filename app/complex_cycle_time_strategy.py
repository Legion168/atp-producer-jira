from __future__ import annotations

import datetime as dt
from typing import List, Optional, Dict, Tuple
import pytz

from app.cycle_time_strategy import CycleTimeStrategy, CycleTime


class ComplexCycleTimeStrategy(CycleTimeStrategy):
    """
    Complex cycle time calculation for complicated processes.
    
    This strategy handles:
    - Multiple assignees with period tracking
    - Complex status transition flows
    - Assignee-specific work periods
    - Edge cases (assigned while already in progress, etc.)
    
    Use case: Complicated process with multiple people involved or many status changes.
    """
    
    def _has_reopening(self, histories: List[Dict]) -> bool:
        """
        Detect if an issue was closed and then reopened.
        
        Returns True if there's any transition from a Done state to an In Progress state,
        which indicates the issue was closed and then reopened for more work.
        
        Args:
            histories: List of history entries
            
        Returns:
            True if issue has been reopened, False otherwise
        """
        # Sort histories chronologically
        sorted_histories = sorted(
            histories,
            key=lambda h: self._parse_jira_datetime(h.get("created")) or dt.datetime.min.replace(tzinfo=pytz.UTC)
        )
        
        previous_status = None
        for history in sorted_histories:
            created_at = self._parse_jira_datetime(history.get("created"))
            if not created_at:
                continue
            
            for item in history.get("items", []):
                if item.get("field") == "status":
                    to_status = (item.get("toString") or "").strip().lower()
                    
                    # Check if transitioning FROM done TO in-progress (reopening!)
                    if previous_status and previous_status in self.done_lower and to_status in self.in_progress_lower:
                        return True
                    
                    previous_status = to_status
        
        return False
    
    def calculate(self, histories: List[Dict], issue_key: str, assignee_account_id: Optional[str] = None) -> CycleTime:
        """
        Calculate cycle time using hybrid approach.
        
        This method intelligently chooses between two algorithms:
        - Cycle-based: For issues that have been closed and reopened (sums all cycles)
        - First-to-last: For normal issues (better handles assignee handoffs)
        
        Args:
            histories: List of history entries from Jira
            issue_key: The issue key
            assignee_account_id: Optional assignee filter
            
        Returns:
            CycleTime object
        """
        # For QA, check for QA-specific start time
        if self.is_qa and assignee_account_id:
            qa_start_result = self._find_qa_start_time(histories, assignee_account_id)
            if qa_start_result:
                qa_start, start_status = qa_start_result
                # Use QA start time instead of normal in-progress logic
                assignee_periods = self._get_assignee_periods(histories, assignee_account_id)
                return self._calculate_with_qa_start(histories, issue_key, qa_start, start_status, assignee_account_id, assignee_periods)
        
        # Get assignee periods if filtering by assignee
        if assignee_account_id:
            assignee_periods = self._get_assignee_periods(histories, assignee_account_id)
            if not assignee_periods:
                # No formal assignment, but check if this person was the author of status changes
                if self._is_author_of_transitions(histories, assignee_account_id):
                    # Person moved the card to in-progress and/or done, treat as their work
                    assignee_periods = None  # Will calculate without period restrictions
                else:
                    # Assignee was never involved with this issue
                    return CycleTime(
                        issue_key=issue_key,
                        in_progress_at=None,
                        done_at=None,
                        seconds=None
                    )
        else:
            assignee_periods = None
        
        # Detect if issue was reopened and choose appropriate algorithm
        if self._has_reopening(histories):
            # Use cycle-based approach for reopened issues
            return self._calculate_with_cycles(histories, issue_key, assignee_account_id, assignee_periods)
        else:
            # Use traditional first→last approach for normal issues
            return self._calculate_first_to_last(histories, issue_key, assignee_account_id, assignee_periods)
    
    def _calculate_with_cycles(self, histories: List[Dict], issue_key: str, assignee_account_id: Optional[str], assignee_periods: Optional[List[Tuple[dt.datetime, Optional[dt.datetime]]]]) -> CycleTime:
        """
        Calculate cycle time using cycle-based logic for reopened issues.
        
        This method tracks ALL open→close cycles and sums them. This handles issues that are
        closed and then reopened for more work.
        
        Args:
            histories: List of history entries from Jira
            issue_key: The issue key
            assignee_account_id: Optional assignee filter
            assignee_periods: Pre-calculated assignee periods (or None)
            
        Returns:
            CycleTime object with first in_progress_at, last done_at, and summed seconds
        """
        # Find all open→close cycles
        cycles = self._find_all_cycles(histories, assignee_periods, assignee_account_id)
        
        if not cycles:
            return CycleTime(
                issue_key=issue_key,
                in_progress_at=None,
                done_at=None,
                seconds=None
            )
        
        # Calculate total cycle time across all cycles
        total_seconds = 0.0
        total_excluded_seconds = 0.0
        total_impediment_seconds = 0.0
        first_in_progress = None
        last_done = None
        
        for cycle_start, cycle_end in cycles:
            if first_in_progress is None or cycle_start < first_in_progress:
                first_in_progress = cycle_start
            
            if cycle_end:  # Cycle is complete
                if last_done is None or cycle_end > last_done:
                    last_done = cycle_end
                
                # Calculate time for this cycle, excluding excluded statuses
                cycle_seconds = (cycle_end - cycle_start).total_seconds()
                excluded_seconds = self._calculate_excluded_time(histories, cycle_start, cycle_end)
                impediment_seconds = self._calculate_impediment_time(histories, cycle_start, cycle_end)
                # Calculate overlap for this cycle
                cycle_overlap = self._calculate_excluded_impediment_overlap(histories, cycle_start, cycle_end)
                
                # Active time = cycle - excluded - impediment + overlap (to avoid double-counting)
                total_seconds += (cycle_seconds - excluded_seconds - impediment_seconds + cycle_overlap)
                total_excluded_seconds += excluded_seconds
                total_impediment_seconds += impediment_seconds
        
        # If no cycles were completed, return with None for done_at and seconds
        if last_done is None:
            return CycleTime(
                issue_key=issue_key,
                in_progress_at=first_in_progress,
                done_at=None,
                seconds=None,
                excluded_seconds=None,
                impediment_seconds=None
            )
        
        return CycleTime(
            issue_key=issue_key,
            in_progress_at=first_in_progress,
            done_at=last_done,
            seconds=total_seconds,
            excluded_seconds=total_excluded_seconds,
            impediment_seconds=total_impediment_seconds
        )
    
    def _calculate_first_to_last(self, histories: List[Dict], issue_key: str, assignee_account_id: Optional[str], assignee_periods: Optional[List[Tuple[dt.datetime, Optional[dt.datetime]]]]) -> CycleTime:
        """
        Calculate cycle time using traditional first→last logic for non-reopened issues.
        
        This is the original algorithm that works better for assignee handoffs and 
        mid-cycle assignments. It finds the first in-progress transition and first
        completion, then filters by assignee period.
        
        Args:
            histories: List of history entries from Jira
            issue_key: The issue key
            assignee_account_id: Optional assignee filter
            assignee_periods: Pre-calculated assignee periods (or None)
            
        Returns:
            CycleTime object
        """
        # Find the start of work (first in-progress transition)
        in_progress_at = self._find_first_in_progress(histories, assignee_periods)
        
        if not in_progress_at:
            return CycleTime(
                issue_key=issue_key,
                in_progress_at=None,
                done_at=None,
                seconds=None
            )
        
        # Find the completion (first done transition after in-progress)
        done_at = self._find_first_completion(histories, in_progress_at, assignee_account_id, assignee_periods)
        
        if not done_at:
            return CycleTime(
                issue_key=issue_key,
                in_progress_at=in_progress_at,
                done_at=None,
                seconds=None
            )
        
        # Calculate cycle time in seconds, excluding time spent in excluded statuses
        total_seconds = (done_at - in_progress_at).total_seconds()
        excluded_seconds = self._calculate_excluded_time(histories, in_progress_at, done_at)
        impediment_seconds = self._calculate_impediment_time(histories, in_progress_at, done_at)
        
        # Calculate overlap between excluded and impediment time to avoid double-counting
        overlap_seconds = self._calculate_excluded_impediment_overlap(histories, in_progress_at, done_at)
        
        # Active time = total - excluded - impediment + overlap (to avoid double-counting)
        seconds = total_seconds - excluded_seconds - impediment_seconds + overlap_seconds
        
        return CycleTime(
            issue_key=issue_key,
            in_progress_at=in_progress_at,
            done_at=done_at,
            seconds=seconds,
            excluded_seconds=excluded_seconds,
            impediment_seconds=impediment_seconds
        )
    
    def _find_all_cycles(self, histories: List[Dict], assignee_periods: Optional[List[Tuple[dt.datetime, Optional[dt.datetime]]]], assignee_account_id: Optional[str]) -> List[Tuple[dt.datetime, Optional[dt.datetime]]]:
        """
        Find all open→close cycles in the issue history.
        
        This handles issues that are closed and then reopened. Each cycle is tracked separately.
        
        Args:
            histories: List of history entries
            assignee_periods: Optional list of assignee periods to filter by
            assignee_account_id: Optional assignee filter
            
        Returns:
            List of (cycle_start, cycle_end) tuples. cycle_end is None for incomplete cycles.
        """
        cycles = []
        current_cycle_start = None
        
        # Sort histories chronologically
        sorted_histories = sorted(
            histories,
            key=lambda h: self._parse_jira_datetime(h.get("created")) or dt.datetime.min.replace(tzinfo=pytz.UTC)
        )
        
        for history in sorted_histories:
            created_at = self._parse_jira_datetime(history.get("created"))
            if not created_at:
                continue
            
            for item in history.get("items", []):
                if item.get("field") == "status":
                    from_string = (item.get("fromString") or "").strip().lower()
                    to_string = (item.get("toString") or "").strip().lower()
                    
                    # Check if this is a transition to an in-progress state
                    if to_string in self.in_progress_lower and current_cycle_start is None:
                        # Only count if within assignee period
                        if self._is_in_assignee_period(created_at, assignee_periods):
                            current_cycle_start = created_at
                    
                    # Check if this is a transition to a done state
                    elif to_string in self.done_lower and current_cycle_start is not None:
                        # Only count if within assignee period
                        if self._is_in_assignee_period(created_at, assignee_periods):
                            # Complete the cycle
                            cycles.append((current_cycle_start, created_at))
                            current_cycle_start = None
        
        # If there's an open cycle, add it with None as end date
        if current_cycle_start is not None:
            cycles.append((current_cycle_start, None))
        
        return cycles
    
    def _get_assignee_periods(self, histories: List[Dict], assignee_account_id: str) -> List[Tuple[dt.datetime, Optional[dt.datetime]]]:
        """
        Get time periods when the specified assignee was assigned to the issue.
        
        Args:
            histories: List of history entries
            assignee_account_id: The assignee account ID to track
            
        Returns:
            List of (start, end) datetime tuples for when the assignee was assigned.
            End is None if the period extends to the present.
        """
        periods = []
        current_assignee = None
        assignment_start = None
        
        # Process histories in chronological order
        sorted_histories = sorted(histories, key=lambda h: self._parse_jira_datetime(h.get("created")) or dt.datetime.min.replace(tzinfo=pytz.UTC))
        
        for history in sorted_histories:
            created_at = self._parse_jira_datetime(history.get("created"))
            if not created_at:
                continue
            
            for item in history.get("items", []):
                if item.get("field") == "assignee":
                    from_id = (item.get("from") or "").strip()
                    to_id = (item.get("to") or "").strip()
                    
                    # If currently tracking our assignee and they're being unassigned
                    if current_assignee == assignee_account_id and to_id != assignee_account_id:
                        if assignment_start:
                            periods.append((assignment_start, created_at))
                        current_assignee = to_id if to_id else None
                        assignment_start = None
                    
                    # If our assignee is being assigned
                    elif to_id == assignee_account_id:
                        # Close previous period if tracking a different assignee
                        if current_assignee and current_assignee != assignee_account_id and assignment_start:
                            assignment_start = None
                        
                        current_assignee = assignee_account_id
                        assignment_start = created_at
        
        # If the assignee period extends to the present, add it with None as end
        if current_assignee == assignee_account_id and assignment_start:
            periods.append((assignment_start, None))
        
        return periods
    
    def _is_in_assignee_period(self, timestamp: dt.datetime, assignee_periods: Optional[List[Tuple[dt.datetime, Optional[dt.datetime]]]]) -> bool:
        """
        Check if a timestamp falls within any of the assignee periods.
        
        Note: For period endings, we allow a small grace period (same calendar day)
        to handle cases where status changes happen shortly after handoffs.
        
        Args:
            timestamp: The timestamp to check
            assignee_periods: List of (start, end) periods, or None if no filter
            
        Returns:
            True if timestamp is in any period (or no filter), False otherwise
        """
        if assignee_periods is None:
            return True
        
        for start, end in assignee_periods:
            if end is None:
                # Period extends to present
                if timestamp >= start:
                    return True
            else:
                # Closed period - allow completion on same day as period end
                # This handles handoffs where status change happens shortly after assignment change
                if start <= timestamp <= end:
                    return True
                # Grace period: if timestamp is on same day as period end
                elif timestamp.date() == end.date() and timestamp > end:
                    # Check if it's within a few hours (same work day)
                    time_diff = (timestamp - end).total_seconds() / 3600
                    if time_diff <= 4:  # Within 4 hours of handoff
                        return True
        
        return False
    
    def _find_first_in_progress(self, histories: List[Dict], assignee_periods: Optional[List[Tuple[dt.datetime, Optional[dt.datetime]]]] = None) -> Optional[dt.datetime]:
        """
        Find the most appropriate work start time using a comprehensive algorithm.
        
        Algorithm:
        1. Find GLOBAL first in-progress transition (no assignee filtering yet)
        2. Filter out transitions that lead to non-work states
        3. If assignee_periods is provided, adjust if the first transition is outside period
        4. Special case: if assignee was assigned when issue was already in progress, use assignment time
        5. Return the first valid work start
        
        Args:
            histories: List of history entries
            assignee_periods: Optional list of (start, end) periods when the assignee was assigned
            
        Returns:
            Datetime when work started, or None if not found
        """
        # Non-work states that shouldn't be considered as work start
        non_work_states = {
            "on hold", "waiting", "paused", "stopped", "cancelled"
        }
        
        # Find all in-progress transitions with their context (NO assignee filtering here)
        work_transitions = []
        
        for i, history in enumerate(histories):
            created_at = self._parse_jira_datetime(history.get("created"))
            if not created_at:
                continue
            
            for item in history.get("items", []):
                if item.get("field") == "status":
                    to_string = (item.get("toString") or "").strip().lower()
                    from_string = (item.get("fromString") or "").strip().lower()
                    
                    if to_string in self.in_progress_lower:
                        # Double-check: exclude known non-work states
                        if to_string in non_work_states:
                            continue
                            
                        # Check if this leads to a non-work state
                        leads_to_non_work = self._check_leads_to_non_work(histories, i, non_work_states)
                        
                        work_transitions.append({
                            'timestamp': created_at,
                            'status': to_string,
                            'from_status': from_string,
                            'leads_to_non_work': leads_to_non_work
                        })
        
        # Filter out transitions that lead to non-work states
        valid_transitions = [t for t in work_transitions if not t['leads_to_non_work']]
        
        if not valid_transitions:
            # Fallback: use any in-progress transition if no valid ones found
            valid_transitions = work_transitions
        
        if not valid_transitions:
            # Special case: if assignee was assigned when issue was already in progress
            # Use the assignment time as the work start
            if assignee_periods:
                first_assignment = self._get_first_assignment_in_progress(histories, assignee_periods)
                if first_assignment:
                    return first_assignment
            return None
        
        # Get the global first work start
        first_in_progress = min(valid_transitions, key=lambda x: x['timestamp'])['timestamp']
        
        # If no assignee filter, return the global first
        if not assignee_periods:
            return first_in_progress
        
        # Check if the first in-progress is within assignee period
        if self._is_in_assignee_period(first_in_progress, assignee_periods):
            # It's within period, use it
            return first_in_progress
        
        # The work started BEFORE the assignee was assigned
        # Check if this was a handoff (previous assignee) or first assignment
        first_assignment = self._get_first_assignment_in_progress(histories, assignee_periods)
        if first_assignment:
            # This was a HANDOFF - use the assignment time (assignee inherited in-progress work)
            return first_assignment
        
        # Not a handoff - check if issue was in progress when first assigned
        # If so, use the status change time (the assignee took over unassigned work)
        if assignee_periods:
            first_period_start = min(assignee_periods, key=lambda p: p[0])[0]
            # Check if issue was in progress at time of first assignment
            current_status = self._get_status_at_time(histories, first_period_start)
            if current_status and current_status in self.in_progress_lower:
                # Issue was in progress when assigned - use the original status change time
                return first_in_progress
        
        # Otherwise, find the first in-progress transition WITHIN the assignee period
        for transition in sorted(valid_transitions, key=lambda x: x['timestamp']):
            if self._is_in_assignee_period(transition['timestamp'], assignee_periods):
                return transition['timestamp']
        
        return None
    
    def _get_first_assignment_in_progress(self, histories: List[Dict], assignee_periods: List[Tuple[dt.datetime, Optional[dt.datetime]]]) -> Optional[dt.datetime]:
        """
        Check if the assignee was assigned to the issue when it was already in an in-progress status
        AND there was a previous assignee (i.e., it's a handoff, not first assignment).
        
        Use Case 5 should ONLY apply when:
        - Issue was assigned to Person A
        - Issue already in progress
        - Then reassigned to Person B (the filtered assignee)
        
        It should NOT apply when:
        - Issue was UNASSIGNED
        - Issue moves to in progress
        - Then gets assigned for the first time
        
        Args:
            histories: List of history entries
            assignee_periods: List of (start, end) periods when the assignee was assigned
            
        Returns:
            The first assignment time if the issue was in progress AND had a previous assignee, 
            None otherwise
        """
        if not assignee_periods:
            return None
        
        # Get the first assignment time
        first_assignment_time = min(start for start, _ in assignee_periods)
        
        # Check what the status was and who the previous assignee was
        current_status = None
        previous_assignee = None
        
        for history in sorted(histories, key=lambda h: self._parse_jira_datetime(h.get("created")) or dt.datetime.min.replace(tzinfo=pytz.UTC)):
            created_at = self._parse_jira_datetime(history.get("created"))
            if not created_at:
                continue
            
            # Process changes up to the assignment time
            if created_at <= first_assignment_time:
                for item in history.get("items", []):
                    if item.get("field") == "status":
                        to_string = (item.get("toString") or "").strip().lower()
                        current_status = to_string
                    elif item.get("field") == "assignee":
                        # Track the assignee just before our target assignee
                        to_id = (item.get("to") or "").strip()
                        if created_at < first_assignment_time:
                            # This is before our assignee was assigned
                            previous_assignee = to_id if to_id else None
            else:
                break
        
        # Only use assignment time if:
        # 1. Issue was in progress, AND
        # 2. There was a previous assignee (not just unassigned)
        if current_status and current_status in self.in_progress_lower:
            if previous_assignee:  # There was someone assigned before (handoff)
                return first_assignment_time
        
        return None
    
    def _get_status_at_time(self, histories: List[Dict], timestamp: dt.datetime) -> Optional[str]:
        """
        Get the status of an issue at a specific point in time.
        
        Args:
            histories: List of history entries
            timestamp: The time to check
            
        Returns:
            The status at that time (lowercase), or None if not found
        """
        current_status = None
        
        for history in sorted(histories, key=lambda h: self._parse_jira_datetime(h.get("created")) or dt.datetime.min.replace(tzinfo=pytz.UTC)):
            created_at = self._parse_jira_datetime(history.get("created"))
            if not created_at:
                continue
            
            # Process status changes up to the timestamp
            if created_at <= timestamp:
                for item in history.get("items", []):
                    if item.get("field") == "status":
                        to_string = (item.get("toString") or "").strip().lower()
                        current_status = to_string
            else:
                break
        
        return current_status
    
    def _check_leads_to_non_work(self, histories: List[Dict], start_index: int, non_work_states: set) -> bool:
        """
        Check if a work transition leads to a non-work state.
        
        Args:
            histories: List of history entries
            start_index: Index of the work transition
            non_work_states: Set of non-work state names
            
        Returns:
            True if the work transition leads to a non-work state
        """
        # Look ahead in the history to see what happens after this work start
        for i in range(start_index + 1, len(histories)):
            history = histories[i]
            created_at = self._parse_jira_datetime(history.get("created"))
            if not created_at:
                continue
            
            for item in history.get("items", []):
                if item.get("field") == "status":
                    to_string = (item.get("toString") or "").strip().lower()
                    if to_string in non_work_states:
                        return True
                    # If we find another in-progress state, this work period ended
                    if to_string in self.in_progress_lower:
                        return False
        
        return False
    
    def _find_first_completion(self, histories: List[Dict], in_progress_at: dt.datetime, assignee_account_id: Optional[str] = None, assignee_periods: Optional[List[Tuple[dt.datetime, Optional[dt.datetime]]]] = None) -> Optional[dt.datetime]:
        """
        Find the first completion after the in-progress start time.
        
        Algorithm:
        1. Look for both status changes to done states and resolution changes
        2. Prioritize status changes over resolution changes (status is more reliable)
        3. Handle assignee filtering for resolution changes
        4. If assignee_periods is provided, only consider completions during those periods
        5. Return the earliest valid completion
        
        Args:
            histories: List of history entries
            in_progress_at: When work started
            assignee_account_id: Optional assignee filter
            assignee_periods: Optional list of (start, end) periods when the assignee was assigned
            
        Returns:
            Datetime when work was completed, or None if not found
        """
        status_completions = []
        resolution_completions = []
        
        # Process in chronological order to find all completion events
        for history in histories:
            created_at = self._parse_jira_datetime(history.get("created"))
            if not created_at or created_at <= in_progress_at:
                continue
            
            # Filter by assignee period if provided
            if not self._is_in_assignee_period(created_at, assignee_periods):
                continue
            
            # Check for status completion
            status_completion = self._check_status_completion(history, created_at)
            if status_completion:
                status_completions.append(status_completion)
            
            # Check for resolution completion
            resolution_completion = self._check_resolution_completion(history, created_at, assignee_account_id)
            if resolution_completion:
                resolution_completions.append(resolution_completion)
        
        # Prioritize status completions over resolution completions
        if status_completions:
            return min(status_completions)
        elif resolution_completions:
            return min(resolution_completions)
        else:
            return None
    
    def _check_status_completion(self, history: Dict, created_at: dt.datetime) -> Optional[dt.datetime]:
        """
        Check if a history entry represents a status-based completion.
        
        Args:
            history: History entry
            created_at: When this history entry occurred
            
        Returns:
            Completion datetime if found, None otherwise
        """
        for item in history.get("items", []):
            if item.get("field") == "status":
                to_string = (item.get("toString") or "").strip()
                if to_string.lower() in self.done_lower:
                    return created_at
        
        return None
    
    def _check_resolution_completion(self, history: Dict, created_at: dt.datetime, assignee_account_id: Optional[str] = None) -> Optional[dt.datetime]:
        """
        Check if a history entry represents a resolution-based completion.
        
        Args:
            history: History entry
            created_at: When this history entry occurred
            assignee_account_id: Optional assignee filter
            
        Returns:
            Completion datetime if found, None otherwise
        """
        for item in history.get("items", []):
            if item.get("field") == "resolution":
                to_string = (item.get("toString") or "").strip()
                
                # Handle "Won't Do" resolutions
                if to_string.lower() in ["won't do", "wont do"]:
                    if assignee_account_id:
                        author = history.get("author", {})
                        author_account_id = author.get("accountId")
                        # Only count if the target assignee set it to "Won't Do"
                        if author_account_id == assignee_account_id:
                            return created_at
                    else:
                        # If no assignee filter, count any "Won't Do"
                        return created_at
                else:
                    # Count any non-empty resolution (exclude "None")
                    if to_string and to_string.lower() != "none":
                        return created_at
        
        return None
    
    def _is_author_of_transitions(self, histories: List[Dict], assignee_account_id: str) -> bool:
        """
        Check if the given account ID is the author of in-progress or done status transitions.
        
        This handles the case where someone creates and works on an issue without being formally
        assigned. If they're the one moving it through the workflow, we should count it as their work.
        
        Args:
            histories: List of history entries
            assignee_account_id: Account ID to check
            
        Returns:
            True if this person authored any in-progress or done transitions
        """
        for history in histories:
            author = history.get("author", {})
            author_account_id = author.get("accountId")
            
            if author_account_id == assignee_account_id:
                for item in history.get("items", []):
                    if item.get("field") == "status":
                        to_string = (item.get("toString") or "").strip().lower()
                        
                        # Check if they moved it to in-progress or done
                        if to_string in self.in_progress_lower or to_string in self.done_lower:
                            return True
        
        return False
    
    def _find_qa_start_time(self, histories: List[Dict], assignee_account_id: Optional[str]) -> Optional[Tuple[dt.datetime, str]]:
        """
        Find when QA work started: when QA assigns themselves on 'Acceptance', 
        assigns on 'in review' and moves to 'Acceptance', or moves ticket from 'Backlog' to any state.
        
        Args:
            histories: List of history entries
            assignee_account_id: The QA assignee account ID
            
        Returns:
            Tuple of (datetime when QA work started, status at start) or None if not found
        """
        if not self.is_qa or not assignee_account_id:
            return None
        
        acceptance_lower = "acceptance"
        in_review_lower = "in review"
        backlog_lower = "backlog"
        
        # Sort histories chronologically
        sorted_histories = sorted(
            histories,
            key=lambda h: self._parse_jira_datetime(h.get("created")) or dt.datetime.min.replace(tzinfo=pytz.UTC)
        )
        
        # Track the status and assignee at each point
        current_status = None
        current_assignee = None
        qa_assigned_on_in_review = None  # Track when QA was assigned on 'in review'
        
        for history in sorted_histories:
            created_at = self._parse_jira_datetime(history.get("created"))
            if not created_at:
                continue
            
            author = history.get("author", {})
            author_account_id = author.get("accountId")
            
            # First, update status from status changes in this history entry
            for item in history.get("items", []):
                if item.get("field") == "status":
                    from_string = (item.get("fromString") or "").strip().lower()
                    to_string = (item.get("toString") or "").strip().lower()
                    
                    # Check if QA moves ticket from 'Backlog' to any state
                    if from_string == backlog_lower and author_account_id == assignee_account_id:
                        # QA moved ticket from Backlog to any state - ATP starts
                        return (created_at, to_string)
                    
                    # Check if QA assigned themselves on 'in review' and then moved to 'Acceptance'
                    if from_string == in_review_lower and to_string == acceptance_lower:
                        if current_assignee == assignee_account_id and author_account_id == assignee_account_id:
                            # QA was assigned on 'in review' and moved it to 'Acceptance'
                            return (created_at, acceptance_lower)
                        elif qa_assigned_on_in_review and author_account_id == assignee_account_id:
                            # QA was assigned on 'in review' (tracked earlier) and now moves to 'Acceptance'
                            return (created_at, acceptance_lower)
                    
                    # Check if QA was already assigned and status moved to Acceptance
                    if to_string == acceptance_lower and current_assignee == assignee_account_id:
                        if author_account_id == assignee_account_id:
                            return (created_at, acceptance_lower)
                    
                    current_status = to_string
            
            # Then, process assignee changes (using the status we just updated)
            for item in history.get("items", []):
                if item.get("field") == "assignee":
                    from_id = (item.get("from") or "").strip()
                    to_id = (item.get("to") or "").strip()
                    
                    # Check if QA assigns themselves
                    if to_id == assignee_account_id:
                        current_assignee = assignee_account_id
                        
                        # If assigning on 'Acceptance', this is the start
                        if current_status == acceptance_lower:
                            return (created_at, acceptance_lower)
                        
                        # If assigning on 'in review', track it
                        if current_status == in_review_lower:
                            qa_assigned_on_in_review = created_at
                    
                    elif from_id == assignee_account_id:
                        current_assignee = to_id if to_id else None
                        qa_assigned_on_in_review = None  # Reset if unassigned
        
        return None
    
    def _find_qa_end_time(self, histories: List[Dict], qa_start: dt.datetime, start_status: str) -> Optional[dt.datetime]:
        """
        Find when QA work ended: when the ticket moves to a different status.
        
        Args:
            histories: List of history entries
            qa_start: When QA work started
            start_status: The status at which QA started (e.g., "acceptance")
            
        Returns:
            Datetime when ticket moved to a different status, or None if not found
        """
        start_status_lower = start_status.lower()
        
        # Sort histories chronologically
        sorted_histories = sorted(
            histories,
            key=lambda h: self._parse_jira_datetime(h.get("created")) or dt.datetime.min.replace(tzinfo=pytz.UTC)
        )
        
        for history in sorted_histories:
            created_at = self._parse_jira_datetime(history.get("created"))
            if not created_at or created_at <= qa_start:
                continue
            
            for item in history.get("items", []):
                if item.get("field") == "status":
                    from_string = (item.get("fromString") or "").strip().lower()
                    to_string = (item.get("toString") or "").strip().lower()
                    
                    # If moving away from the start status, this is the end
                    if from_string == start_status_lower and to_string != start_status_lower:
                        return created_at
        
        return None
    
    def _calculate_with_qa_start(self, histories: List[Dict], issue_key: str, qa_start: dt.datetime, start_status: str, assignee_account_id: str, assignee_periods: Optional[List[Tuple[dt.datetime, Optional[dt.datetime]]]]) -> CycleTime:
        """
        Calculate cycle time using QA-specific start time.
        Stops when ticket moves to a different status.
        
        Args:
            histories: List of history entries from Jira
            issue_key: The issue key
            qa_start: When QA work started (QA assigned themselves on Acceptance or moved from in review to Acceptance)
            start_status: The status at which QA started (e.g., "acceptance")
            assignee_account_id: The QA assignee account ID
            assignee_periods: Optional list of assignee periods to filter by
            
        Returns:
            CycleTime object
        """
        # Find when ticket moves to a different status
        done_at = self._find_qa_end_time(histories, qa_start, start_status)
        
        if not done_at:
            return CycleTime(
                issue_key=issue_key,
                in_progress_at=qa_start,
                done_at=None,
                seconds=None
            )
        
        # Calculate cycle time in seconds, excluding time spent in excluded statuses
        total_seconds = (done_at - qa_start).total_seconds()
        excluded_seconds = self._calculate_excluded_time(histories, qa_start, done_at)
        impediment_seconds = self._calculate_impediment_time(histories, qa_start, done_at)
        
        # Calculate overlap between excluded and impediment time to avoid double-counting
        overlap_seconds = self._calculate_excluded_impediment_overlap(histories, qa_start, done_at)
        
        # Active time = total - excluded - impediment + overlap (to avoid double-counting)
        seconds = total_seconds - excluded_seconds - impediment_seconds + overlap_seconds
        
        return CycleTime(
            issue_key=issue_key,
            in_progress_at=qa_start,
            done_at=done_at,
            seconds=seconds,
            excluded_seconds=excluded_seconds,
            impediment_seconds=impediment_seconds
        )

