from __future__ import annotations

import datetime as dt
from typing import List, Optional, Dict, Tuple
import pytz

from app.cycle_time_strategy import CycleTimeStrategy, CycleTime


class SimpleCycleTimeStrategy(CycleTimeStrategy):
    """
    Simple cycle time calculation for clean, straightforward processes.
    
    This strategy assumes:
    - Single assignee (or no assignee filter)
    - Linear progression through statuses
    - First in-progress to first done transition
    
    Use case: Clean process where a person takes work from backlog and completes it.
    """
    
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
            status_before = current_status
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
    
    def _has_reopening(self, histories: List[Dict]) -> bool:
        """
        Detect if an issue was closed and then reopened.
        
        Returns True if there's any transition from a Done state to an In Progress state.
        
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
        - First-to-last: For normal issues (simpler, faster)
        
        Args:
            histories: List of history entries from Jira
            issue_key: The issue key
            assignee_account_id: Optional assignee filter (not used in simple strategy)
            
        Returns:
            CycleTime object
        """
        # For QA, check for QA-specific start time
        if self.is_qa and assignee_account_id:
            qa_start_result = self._find_qa_start_time(histories, assignee_account_id)
            if qa_start_result:
                qa_start, start_status = qa_start_result
                # Use QA start time instead of normal in-progress logic
                return self._calculate_with_qa_start(histories, issue_key, qa_start, start_status, assignee_account_id)
        
        # Detect if issue was reopened and choose appropriate algorithm
        if self._has_reopening(histories):
            # Use cycle-based approach for reopened issues
            return self._calculate_with_cycles(histories, issue_key)
        else:
            # Use traditional first→last approach for normal issues
            return self._calculate_first_to_last(histories, issue_key)
    
    def _calculate_with_cycles(self, histories: List[Dict], issue_key: str) -> CycleTime:
        """
        Calculate cycle time using cycle-based logic with support for reopened issues.
        
        This method tracks ALL open→close cycles and sums them. This handles issues that are
        closed and then reopened for more work.
        
        Args:
            histories: List of history entries from Jira
            issue_key: The issue key
            assignee_account_id: Optional assignee filter (not used in simple strategy)
            
        Returns:
            CycleTime object with first in_progress_at, last done_at, and summed seconds
        """
        # Find all open→close cycles
        cycles = self._find_all_cycles(histories)
        
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
    
    def _calculate_first_to_last(self, histories: List[Dict], issue_key: str) -> CycleTime:
        """
        Calculate cycle time using traditional first→last logic for non-reopened issues.
        
        This is the original simple algorithm: first in-progress to first done.
        
        Args:
            histories: List of history entries from Jira
            issue_key: The issue key
            
        Returns:
            CycleTime object
        """
        # Find the first in-progress transition
        in_progress_at = self._find_first_in_progress(histories)
        
        if not in_progress_at:
            return CycleTime(
                issue_key=issue_key,
                in_progress_at=None,
                done_at=None,
                seconds=None
            )
        
        # Find the first done transition after in-progress
        done_at = self._find_first_done(histories, in_progress_at)
        
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
    
    def _find_all_cycles(self, histories: List[Dict]) -> List[tuple]:
        """
        Find all open→close cycles in the issue history.
        
        This handles issues that are closed and then reopened. Each cycle is tracked separately.
        
        Args:
            histories: List of history entries
            
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
                    to_string = (item.get("toString") or "").strip().lower()
                    
                    # Check if this is a transition to an in-progress state
                    if to_string in self.in_progress_lower and current_cycle_start is None:
                        current_cycle_start = created_at
                    
                    # Check if this is a transition to a done state
                    elif to_string in self.done_lower and current_cycle_start is not None:
                        # Complete the cycle
                        cycles.append((current_cycle_start, created_at))
                        current_cycle_start = None
        
        # If there's an open cycle, add it with None as end date
        if current_cycle_start is not None:
            cycles.append((current_cycle_start, None))
        
        return cycles
    
    def _find_first_in_progress(self, histories: List[Dict]) -> Optional[dt.datetime]:
        """
        Find the first in-progress transition.
        
        Args:
            histories: List of history entries
            
        Returns:
            Datetime when work started, or None if not found
        """
        earliest = None
        
        for history in histories:
            created_at = self._parse_jira_datetime(history.get("created"))
            if not created_at:
                continue
            
            for item in history.get("items", []):
                if item.get("field") == "status":
                    to_string = (item.get("toString") or "").strip().lower()
                    
                    if to_string in self.in_progress_lower:
                        if earliest is None or created_at < earliest:
                            earliest = created_at
        
        return earliest
    
    def _find_first_done(self, histories: List[Dict], in_progress_at: dt.datetime) -> Optional[dt.datetime]:
        """
        Find the first done transition after the in-progress time.
        
        Args:
            histories: List of history entries
            in_progress_at: When work started
            
        Returns:
            Datetime when work was completed, or None if not found
        """
        earliest_done = None
        
        for history in histories:
            created_at = self._parse_jira_datetime(history.get("created"))
            if not created_at or created_at <= in_progress_at:
                continue
            
            for item in history.get("items", []):
                if item.get("field") == "status":
                    to_string = (item.get("toString") or "").strip().lower()
                    
                    if to_string in self.done_lower:
                        if earliest_done is None or created_at < earliest_done:
                            earliest_done = created_at
        
        return earliest_done
    
    def _calculate_with_qa_start(self, histories: List[Dict], issue_key: str, qa_start: dt.datetime, start_status: str, assignee_account_id: str) -> CycleTime:
        """
        Calculate cycle time using QA-specific start time.
        Stops when ticket moves to a different status.
        
        Args:
            histories: List of history entries from Jira
            issue_key: The issue key
            qa_start: When QA work started (QA assigned themselves on Acceptance or moved from in review to Acceptance)
            start_status: The status at which QA started (e.g., "acceptance")
            assignee_account_id: The QA assignee account ID
            
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

