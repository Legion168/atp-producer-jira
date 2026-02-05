from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence, Tuple

import numpy as np
import pytz

from app.cycle_time_calculator import CycleTimeCalculator, CycleTime


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


def compute_relative_period(months: int, tz: str = "UTC") -> TimeWindow:
    """
    Calculate time window for last N months from current date.
    
    Args:
        months: Number of months to look back
        tz: Timezone string (default: "UTC")
        
    Returns:
        TimeWindow with start date N months ago and end date as current date/time
    """
    if months <= 0:
        raise ValueError("Months must be positive")
    timezone = pytz.timezone(tz)
    now = timezone.localize(dt.datetime.now())
    
    # Calculate start date: N months ago
    # Handle month boundaries properly by working with date objects
    current_date = now.date()
    
    # Calculate target month and year
    target_month = current_date.month - months
    target_year = current_date.year
    
    # Adjust year if month goes negative
    while target_month <= 0:
        target_month += 12
        target_year -= 1
    
    # Set start to beginning of that month
    start = timezone.localize(dt.datetime(target_year, target_month, 1, 0, 0, 0))
    
    # End is current date/time
    end = now
    
    return TimeWindow(start=start, end=end)


def compute_custom_period(start_date: dt.date, end_date: dt.date, tz: str = "UTC") -> TimeWindow:
    """
    Create TimeWindow from custom start and end dates.
    
    Args:
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        tz: Timezone string (default: "UTC")
        
    Returns:
        TimeWindow with start at beginning of start_date and end at end of end_date
    """
    if end_date < start_date:
        raise ValueError("End date must be after or equal to start date")
    timezone = pytz.timezone(tz)
    
    # Start at beginning of start_date
    start = timezone.localize(dt.datetime(start_date.year, start_date.month, start_date.day, 0, 0, 0))
    
    # End at end of end_date (23:59:59.999999)
    end = timezone.localize(dt.datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59, 999999))
    
    return TimeWindow(start=start, end=end)


def split_period_into_months(window: TimeWindow) -> List[Tuple[str, TimeWindow]]:
    """
    Split a TimeWindow into monthly chunks.
    
    Args:
        window: TimeWindow to split
        
    Returns:
        List of tuples (month_label, TimeWindow) for each month in the period
    """
    months = []
    current = window.start
    
    while current <= window.end:
        # Calculate end of current month
        if current.month == 12:
            next_month = current.replace(year=current.year + 1, month=1, day=1)
        else:
            next_month = current.replace(month=current.month + 1, day=1)
        
        # End of month is the last moment before next month starts
        month_end = next_month - dt.timedelta(microseconds=1)
        
        # Don't go beyond the original window end
        if month_end > window.end:
            month_end = window.end
        
        # Create month label
        month_label = current.strftime("%b %Y")
        
        # Create TimeWindow for this month
        month_window = TimeWindow(start=current, end=month_end)
        months.append((month_label, month_window))
        
        # Move to start of next month
        current = next_month
    
    return months


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


def extract_cycle_times(
    client,
    issue_keys: Iterable[str],
    in_progress_names: Sequence[str] = ("In Progress",),
    done_names: Sequence[str] = ("Done",),
    assignee_account_id: Optional[str] = None,
    exclude_statuses: Sequence[str] = ("Acceptance", "Feedback"),
    is_qa: bool = False,
) -> List[CycleTime]:
    """
    Calculate cycle times using the new CycleTimeCalculator class.
    
    This is a clean wrapper around the new class-based implementation.
    
    Args:
        is_qa: If True, use QA-specific logic: ATP starts when QA assigns themselves
               on 'Acceptance' or assigns on 'in review' and moves to 'Acceptance'
    """
    calculator = CycleTimeCalculator(in_progress_names, done_names, exclude_statuses, is_qa=is_qa)
    return calculator.calculate_cycle_times(client, list(issue_keys), assignee_account_id)


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


