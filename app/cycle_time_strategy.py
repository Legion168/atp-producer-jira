from __future__ import annotations

import datetime as dt
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Dict, Tuple
import pytz


@dataclass(frozen=True)
class CycleTime:
    issue_key: str
    in_progress_at: Optional[dt.datetime]
    done_at: Optional[dt.datetime]
    seconds: Optional[float]
    excluded_seconds: Optional[float] = None  # Time excluded from cycle time calculation
    impediment_seconds: Optional[float] = None  # Time spent flagged as Impediment


class CycleTimeStrategy(ABC):
    """Abstract base class for cycle time calculation strategies."""
    
    def __init__(self, in_progress_names: List[str], done_names: List[str], exclude_statuses: List[str], is_qa: bool = False):
        """
        Initialize the strategy with status names.
        
        Args:
            in_progress_names: List of status names that indicate work has started
            done_names: List of status names that indicate work is completed
            exclude_statuses: List of status names to exclude from cycle time
            is_qa: If True, use QA-specific logic: ATP starts when QA assigns themselves
                   on 'Acceptance' or assigns on 'in review' and moves to 'Acceptance'
        """
        self.in_progress_lower = {name.lower() for name in in_progress_names}
        self.done_lower = {name.lower() for name in done_names}
        self.exclude_lower = {name.lower() for name in exclude_statuses}
        self.is_qa = is_qa
    
    @abstractmethod
    def calculate(self, histories: List[Dict], issue_key: str, assignee_account_id: Optional[str] = None) -> CycleTime:
        """
        Calculate cycle time for a single issue.
        
        Args:
            histories: List of history entries from Jira
            issue_key: The issue key
            assignee_account_id: Optional assignee filter
            
        Returns:
            CycleTime object
        """
        pass
    
    @staticmethod
    def should_use_complex_strategy(histories: List[Dict], assignee_account_id: Optional[str] = None) -> bool:
        """
        Determine if the complex strategy should be used based on issue history.
        
        Args:
            histories: List of history entries from Jira
            assignee_account_id: Optional assignee filter
            
        Returns:
            True if complex strategy should be used, False for simple strategy
        """
        assignee_changes = 0
        status_changes = 0
        
        for history in histories:
            for item in history.get("items", []):
                field = item.get("field")
                if field == "assignee":
                    assignee_changes += 1
                elif field == "status":
                    status_changes += 1
        
        # Use complex strategy if:
        # 1. Multiple assignee changes (> 2 means at least 3 different assignees)
        # 2. Many status changes (> 5 indicates complex flow)
        # 3. Assignee filter is provided (need to track assignee periods)
        return assignee_changes > 2 or status_changes > 5 or assignee_account_id is not None
    
    def _parse_jira_datetime(self, value: Optional[str]) -> Optional[dt.datetime]:
        """
        Parse a Jira datetime string to a timezone-aware datetime object.
        Applies +1 hour adjustment to correct for Jira timestamp offset.
        
        Args:
            value: Jira datetime string
            
        Returns:
            Parsed datetime object with +1 hour adjustment or None if parsing fails
        """
        if not value:
            return None
        
        try:
            # Support +0000 or +00:00
            if value.endswith("Z"):
                dt_obj = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
            elif "+" in value[-6:] or "-" in value[-6:]:
                # Attempt to insert colon in timezone if missing
                if value[-5] in ["+", "-"] and ":" not in value[-5:]:
                    value = value[:-2] + ":" + value[-2:]
                dt_obj = dt.datetime.fromisoformat(value)
            else:
                dt_obj = dt.datetime.fromisoformat(value)
            
            if dt_obj.tzinfo is None:
                dt_obj = dt_obj.replace(tzinfo=pytz.UTC)
            
            # Apply +1 hour adjustment to correct for Jira timestamp offset
            dt_obj = dt_obj + dt.timedelta(hours=1)
            
            return dt_obj.astimezone(pytz.UTC)
        except Exception:
            # Fallback: try dateutil if available
            try:
                from dateutil import parser
                dt_obj = parser.parse(value)
                if dt_obj.tzinfo is None:
                    dt_obj = dt_obj.replace(tzinfo=pytz.UTC)
                
                # Apply +1 hour adjustment to correct for Jira timestamp offset
                dt_obj = dt_obj + dt.timedelta(hours=1)
                
                return dt_obj.astimezone(pytz.UTC)
            except Exception:
                return None
    
    def _calculate_excluded_time(self, histories: List[Dict], in_progress_at: dt.datetime, done_at: dt.datetime) -> float:
        """
        Calculate the total time spent in excluded statuses (e.g., "Acceptance").
        
        Args:
            histories: List of history entries
            in_progress_at: When work started
            done_at: When work was completed
            
        Returns:
            Total seconds to exclude from cycle time
        """
        excluded_seconds = 0.0
        current_status = None
        status_start_time = None
        
        # Process histories in chronological order to track status changes
        for history in histories:
            created_at = self._parse_jira_datetime(history.get("created"))
            if not created_at:
                continue
            
            # Only consider changes within our cycle time window
            if created_at < in_progress_at or created_at > done_at:
                continue
            
            for item in history.get("items", []):
                if item.get("field") == "status":
                    from_string = (item.get("fromString") or "").strip().lower()
                    to_string = (item.get("toString") or "").strip().lower()
                    
                    # If we were in an excluded status and are leaving it, add the time
                    if current_status and current_status in self.exclude_lower and status_start_time:
                        if to_string not in self.exclude_lower:
                            excluded_seconds += (created_at - status_start_time).total_seconds()
                    
                    # Update current status tracking
                    if to_string in self.exclude_lower:
                        # Entering an excluded status
                        current_status = to_string
                        status_start_time = created_at
                    else:
                        # Leaving an excluded status or in a normal status
                        current_status = to_string
                        status_start_time = created_at
        
        # If we're still in an excluded status at the end, add that time too
        if current_status and current_status in self.exclude_lower and status_start_time:
            excluded_seconds += (done_at - status_start_time).total_seconds()
        
        return excluded_seconds
    
    def _calculate_impediment_time(self, histories: List[Dict], in_progress_at: dt.datetime, done_at: dt.datetime) -> float:
        """
        Calculate the total time when issue was flagged as "Impediment".
        
        Args:
            histories: List of history entries
            in_progress_at: When work started
            done_at: When work was completed
            
        Returns:
            Total seconds spent as Impediment
        """
        impediment_seconds = 0.0
        is_impediment = False
        impediment_start_time = None
        
        # Process histories in chronological order to track Flagged field changes
        for history in histories:
            created_at = self._parse_jira_datetime(history.get("created"))
            if not created_at:
                continue
            
            # Only consider changes within our cycle time window
            if created_at < in_progress_at or created_at > done_at:
                continue
            
            for item in history.get("items", []):
                if item.get("field") == "Flagged":
                    to_string = (item.get("toString") or "").strip()
                    
                    # If we were flagged and are being unflagged, add the time
                    if is_impediment and impediment_start_time:
                        if to_string.lower() in ["none", ""]:
                            # Impediment cleared
                            impediment_seconds += (created_at - impediment_start_time).total_seconds()
                            is_impediment = False
                            impediment_start_time = None
                    
                    # Check if being flagged as impediment
                    if to_string.lower() == "impediment":
                        is_impediment = True
                        impediment_start_time = created_at
        
        # If still flagged at the end, add that time too
        if is_impediment and impediment_start_time:
            impediment_seconds += (done_at - impediment_start_time).total_seconds()
        
        return impediment_seconds
    
    def _calculate_excluded_impediment_overlap(self, histories: List[Dict], in_progress_at: dt.datetime, done_at: dt.datetime) -> float:
        """
        Calculate the overlap between excluded status time and impediment time.
        This prevents double-counting when an issue is both in an excluded status AND flagged as impediment.
        
        Args:
            histories: List of history entries
            in_progress_at: When work started
            done_at: When work was completed
            
        Returns:
            Total seconds of overlap between excluded and impediment periods
        """
        overlap_seconds = 0.0
        
        # Track impediment periods
        impediment_periods = []
        is_impediment = False
        impediment_start_time = None
        
        # Track excluded status periods
        excluded_periods = []
        current_status = None
        status_start_time = None
        
        # Process histories to identify both impediment and excluded periods
        for history in histories:
            created_at = self._parse_jira_datetime(history.get("created"))
            if not created_at:
                continue
            
            # Only consider changes within our cycle time window
            if created_at < in_progress_at or created_at > done_at:
                continue
            
            for item in history.get("items", []):
                if item.get("field") == "Flagged":
                    to_string = (item.get("toString") or "").strip()
                    
                    # If we were flagged and are being unflagged, add the period
                    if is_impediment and impediment_start_time:
                        if to_string.lower() in ["none", ""]:
                            impediment_periods.append((impediment_start_time, created_at))
                            is_impediment = False
                            impediment_start_time = None
                    
                    # Check if being flagged as impediment
                    if to_string.lower() == "impediment":
                        is_impediment = True
                        impediment_start_time = created_at
                
                elif item.get("field") == "status":
                    from_string = (item.get("fromString") or "").strip().lower()
                    to_string = (item.get("toString") or "").strip().lower()
                    
                    # If we were in an excluded status and are leaving it, add the period
                    if current_status and current_status in self.exclude_lower and status_start_time:
                        if to_string not in self.exclude_lower:
                            excluded_periods.append((status_start_time, created_at))
                    
                    # Update current status tracking
                    if to_string in self.exclude_lower:
                        current_status = to_string
                        status_start_time = created_at
                    else:
                        current_status = to_string
                        status_start_time = created_at
        
        # Handle periods that extend to the end
        if is_impediment and impediment_start_time:
            impediment_periods.append((impediment_start_time, done_at))
        
        if current_status and current_status in self.exclude_lower and status_start_time:
            excluded_periods.append((status_start_time, done_at))
        
        # Calculate overlap between impediment and excluded periods
        for impediment_start, impediment_end in impediment_periods:
            for excluded_start, excluded_end in excluded_periods:
                # Calculate overlap between these two periods
                overlap_start = max(impediment_start, excluded_start)
                overlap_end = min(impediment_end, excluded_end)
                
                if overlap_start < overlap_end:
                    overlap_seconds += (overlap_end - overlap_start).total_seconds()
        
        return overlap_seconds

