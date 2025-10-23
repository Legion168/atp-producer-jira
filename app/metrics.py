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
) -> List[CycleTime]:
    """
    Calculate cycle times using the new CycleTimeCalculator class.
    
    This is a clean wrapper around the new class-based implementation.
    """
    calculator = CycleTimeCalculator(in_progress_names, done_names, exclude_statuses)
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


