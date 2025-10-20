from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence, Tuple

import numpy as np
import pytz


@dataclass(frozen=True)
class TimeWindow:
    start: dt.datetime  # inclusive
    end: dt.datetime    # inclusive


def compute_quarter_range(year: int, quarter: int, tz: str = "UTC") -> TimeWindow:
    if quarter not in (1, 2, 3, 4):
        raise ValueError("Quarter must be 1..4")
    timezone = pytz.timezone(tz)
    month_start = {1: 1, 2: 4, 3: 7, 4: 10}[quarter]
    start = timezone.localize(dt.datetime(year, month_start, 1, 0, 0, 0))
    # Compute end as the last microsecond of the quarter
    month_end = month_start + 2
    last_day = _last_day_of_month(year, month_end)
    end = timezone.localize(dt.datetime(year, month_end, last_day, 23, 59, 59, 999999))
    return TimeWindow(start=start, end=end)


def _last_day_of_month(year: int, month: int) -> int:
    if month == 12:
        return 31
    first_next = dt.date(year if month < 12 else year + 1, (month % 12) + 1, 1)
    last = first_next - dt.timedelta(days=1)
    return last.day


def jql_time_range_clause(field: str, window: TimeWindow) -> str:
    # Jira expects yyyy/MM/dd HH:mm
    fmt = "%Y/%m/%d %H:%M"
    start_str = window.start.strftime(fmt)
    end_str = window.end.strftime(fmt)
    return f"{field} during (\"{start_str}\", \"{end_str}\")"


def jql_and(*parts: Sequence[str]) -> str:
    non_empty = [p for p in parts if p and p.strip()]
    return " AND ".join(f"({p})" for p in non_empty)


def _strip_order_by(jql: str) -> str:
    """Remove trailing ORDER BY clause from a JQL string (case-insensitive)."""
    if not jql:
        return jql
    # Split on ORDER BY and keep the part before it.
    parts = re.split(r"\border\s+by\b", jql, flags=re.IGNORECASE)
    return parts[0].strip()


def jql_wrap_filter(base_filter_jql: str, extra: str) -> str:
    if not base_filter_jql:
        return extra
    sanitized = _strip_order_by(base_filter_jql)
    return jql_and(sanitized, extra)


def percentile(values: Sequence[float], p: float) -> Optional[float]:
    if not values:
        return None
    return float(np.percentile(np.array(values, dtype=float), p))


@dataclass(frozen=True)
class CycleTime:
    issue_key: str
    in_progress_at: Optional[dt.datetime]
    done_at: Optional[dt.datetime]
    seconds: Optional[float]


def extract_cycle_times(
    client,
    issue_keys: Iterable[str],
    in_progress_names: Sequence[str] = ("In Progress",),
    done_names: Sequence[str] = ("Done",),
    assignee_account_id: Optional[str] = None,
) -> List[CycleTime]:
    in_lower = {n.lower() for n in in_progress_names}
    done_lower = {n.lower() for n in done_names}
    results: List[CycleTime] = []

    for key in issue_keys:
        histories = client.get_issue_changelog(key)
        first_in_progress: Optional[dt.datetime] = None
        first_done: Optional[dt.datetime] = None
        
        # First pass: Find the most recent "In Progress" transition that led to completion
        if assignee_account_id:
            # Find when resolution was set to a valid completion to establish the completion context
            final_done_time = None
            for h in reversed(histories):
                created_str = h.get("created")
                try:
                    created_at = _parse_jira_datetime(created_str)
                except Exception:
                    continue
                
                # Check if this history entry has a resolution change
                has_resolution_change = False
                for item in h.get("items", []):
                    if item.get("field") == "resolution":
                        has_resolution_change = True
                        to_string = (item.get("toString") or "").strip()
                        # Check if resolution is "Won't Do" and if so, who set it
                        if to_string.lower() == "won't do" or to_string.lower() == "wont do":
                            # If someone else set it to "Won't Do", skip this history entry entirely
                            author = h.get("author", {})
                            author_account_id = author.get("accountId")
                            if author_account_id != assignee_account_id:
                                break  # Skip this history entry, continue to next one
                            # If the target assignee set it to "Won't Do", count it as completion
                            else:
                                final_done_time = created_at
                                break
                        else:
                            # Only count non-empty resolutions as completion (exclude "None")
                            if to_string and to_string.lower() != "none":
                                # Any valid resolution by anyone counts as completion
                                final_done_time = created_at
                                break
                
                # If we found a valid completion, stop searching
                if final_done_time:
                    break
            
            # Now find the MOST RECENT "In Progress" transition by target person that led to completion
            if final_done_time:
                # Process in reverse chronological order to find the most recent valid transition
                for h in reversed(histories):
                    created_str = h.get("created")
                    try:
                        created_at = _parse_jira_datetime(created_str)
                    except Exception:
                        continue
                    
                    # Only consider transitions before the final completion
                    if created_at >= final_done_time:
                        continue
                    
                    author = h.get("author", {})
                    author_account_id = author.get("accountId")
                    
                    # Check for assignee changes when issue is already in "In Progress" status
                    for item in h.get("items", []):
                        if item.get("field") == "assignee":
                            # Check if target assignee was assigned to this issue
                            to_string = (item.get("toString") or "").strip()
                            if to_string and assignee_account_id:
                                # Check if the issue was already in "In Progress" status when assigned
                                # Look for the current status at the time of assignment
                                current_status = None
                                for h_status in histories:
                                    h_status_created_str = h_status.get("created")
                                    try:
                                        h_status_created_at = _parse_jira_datetime(h_status_created_str)
                                    except Exception:
                                        continue
                                    
                                    # Only consider status changes before or at the assignment time
                                    if h_status_created_at > created_at:
                                        continue
                                    
                                    for h_status_item in h_status.get("items", []):
                                        if h_status_item.get("field") == "status":
                                            current_status = (h_status_item.get("toString") or "").strip().lower()
                                            break
                                    if current_status:
                                        break
                                
                                # If the issue was already in "In Progress" status when assigned, use assignment time
                                if current_status and current_status in in_lower:
                                    first_in_progress = created_at
                                    break
                    
                    for item in h.get("items", []):
                        if item.get("field") != "status":
                            continue
                        to_string = (item.get("toString") or "").strip()
                        if to_string.lower() in in_lower:
                            # If target assignee made this transition, check if they actually completed work
                            if author_account_id == assignee_account_id:
                                # Check if this person moved it back to backlog without completing it
                                was_moved_back = False
                                for h3 in histories:
                                    h3_created_str = h3.get("created")
                                    try:
                                        h3_created_at = _parse_jira_datetime(h3_created_str)
                                    except Exception:
                                        continue
                                    
                                    # Only consider actions after this "In Progress" transition
                                    if h3_created_at <= created_at:
                                        continue
                                    
                                    # Check if target assignee moved it back to backlog within reasonable time
                                    time_diff = (h3_created_at - created_at).total_seconds()
                                    if time_diff > 3600:  # More than 1 hour, stop looking
                                        break
                                    
                                    h3_author = h3.get("author", {})
                                    h3_author_account_id = h3_author.get("accountId")
                                    if h3_author_account_id == assignee_account_id:
                                        for h3_item in h3.get("items", []):
                                            if h3_item.get("field") == "status":
                                                h3_to_string = (h3_item.get("toString") or "").strip().lower()
                                                # Check if moved back to backlog or similar non-work states
                                                if h3_to_string in ["backlog", "to do", "open"]:
                                                    was_moved_back = True
                                                    break
                                    if was_moved_back:
                                        break
                                
                                # Only use this transition if it wasn't immediately moved back
                                if not was_moved_back:
                                    # Check if this transition came from "Backlog" to allow overwrite
                                    should_overwrite = False
                                    
                                    # Check the current transition's "from" status
                                    for item in h.get("items", []):
                                        if item.get("field") == "status":
                                            from_string = (item.get("fromString") or "").strip().lower()
                                            to_string = (item.get("toString") or "").strip().lower()
                                            
                                            # Only allow overwrite if it came from "Backlog"
                                            if to_string.lower() in in_lower and from_string == "backlog":
                                                should_overwrite = True
                                            break
                                    
                                    # Set first_in_progress if this is a significant change
                                    if should_overwrite:
                                        first_in_progress = created_at
                                        break
                            # If automation/other made this transition, check if target assignee followed up soon after
                            else:
                                # Look for target assignee's next action within reasonable time (e.g., 1 hour)
                                next_action_time = None
                                for h2 in histories:
                                    h2_created_str = h2.get("created")
                                    try:
                                        h2_created_at = _parse_jira_datetime(h2_created_str)
                                    except Exception:
                                        continue
                                    
                                    # Only consider actions after the automation transition
                                    if h2_created_at <= created_at:
                                        continue
                                    
                                    # Check if target assignee took action within 1 hour
                                    time_diff = (h2_created_at - created_at).total_seconds()
                                    if time_diff > 3600:  # More than 1 hour, stop looking
                                        break
                                    
                                    h2_author = h2.get("author", {})
                                    h2_author_account_id = h2_author.get("accountId")
                                    if h2_author_account_id == assignee_account_id:
                                        next_action_time = h2_created_at
                                        break
                                
                                # If target assignee followed up, use the automation transition time
                                if next_action_time:
                                    first_in_progress = created_at
                                    break
                    if first_in_progress:
                        break
        
        # Second pass: Find when resolution was last set to a valid completion (most recent completion)
        for h in reversed(histories):  # Process in reverse chronological order
            created_str = h.get("created")
            try:
                created_at = _parse_jira_datetime(created_str)
            except Exception:
                continue
            
            # Check if this history entry has a resolution change
            for item in h.get("items", []):
                if item.get("field") == "resolution":
                    to_string = (item.get("toString") or "").strip()
                    # Check if resolution is "Won't Do" and if so, who set it
                    if to_string.lower() == "won't do" or to_string.lower() == "wont do":
                        # If someone else set it to "Won't Do", skip this history entry entirely
                        author = h.get("author", {})
                        author_account_id = author.get("accountId")
                        if author_account_id != assignee_account_id:
                            break  # Skip this history entry, continue to next one
                        # If the target assignee set it to "Won't Do", count it as completion
                        else:
                            first_done = created_at  # This will be the most recent resolution by target assignee
                            break
                    else:
                        # Only count non-empty resolutions as completion (exclude "None")
                        if to_string and to_string.lower() != "none":
                            # Any valid resolution by anyone counts as completion
                            first_done = created_at  # This will be the most recent valid resolution
                            break
            
            # If we found a valid completion, stop searching
            if first_done:
                break
        seconds: Optional[float] = None
        if first_in_progress and first_done and first_done >= first_in_progress:
            seconds = (first_done - first_in_progress).total_seconds()
        results.append(CycleTime(issue_key=key, in_progress_at=first_in_progress, done_at=first_done, seconds=seconds))
    return results


def summarize_cycle_times(seconds_list: Sequence[float]) -> dict:
    if not seconds_list:
        return {"count": 0}
    days = [s / 86400.0 for s in seconds_list]
    return {
        "count": len(seconds_list),
        "avg_days": float(np.mean(days)),
        "median_days": percentile(days, 50),
        "p75_days": percentile(days, 75),
        "p90_days": percentile(days, 90),
        "max_days": max(days),
    }


def _parse_jira_datetime(value: Optional[str]) -> Optional[dt.datetime]:
    if not value:
        return None
    # Jira returns ISO-8601 with timezone, e.g. 2024-01-15T12:34:56.789+0000
    # We normalize to aware UTC datetime
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
        return dt_obj.astimezone(pytz.UTC)
    except Exception:
        # Fallback: try dateutil if available
        try:
            from dateutil import parser  # type: ignore

            dt_obj = parser.parse(value)
            if dt_obj.tzinfo is None:
                dt_obj = dt_obj.replace(tzinfo=pytz.UTC)
            return dt_obj.astimezone(pytz.UTC)
        except Exception:
            return None
