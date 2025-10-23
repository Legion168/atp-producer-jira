"""
Helper functions for creating mock Jira history data for testing.
"""

from typing import List, Dict, Optional


def create_status_change(created: str, from_status: str, to_status: str) -> Dict:
    """Create a status change history entry."""
    return {
        "created": created,
        "items": [
            {
                "field": "status",
                "fromString": from_status,
                "toString": to_status
            }
        ]
    }


def create_assignee_change(created: str, from_id: Optional[str], to_id: Optional[str]) -> Dict:
    """Create an assignee change history entry."""
    return {
        "created": created,
        "items": [
            {
                "field": "assignee",
                "from": from_id or "",
                "to": to_id or ""
            }
        ]
    }


def create_combined_change(created: str, status_from: Optional[str] = None, 
                          status_to: Optional[str] = None,
                          assignee_from: Optional[str] = None, 
                          assignee_to: Optional[str] = None) -> Dict:
    """Create a history entry with multiple changes."""
    items = []
    
    if status_from is not None and status_to is not None:
        items.append({
            "field": "status",
            "fromString": status_from,
            "toString": status_to
        })
    
    if assignee_from is not None or assignee_to is not None:
        items.append({
            "field": "assignee",
            "from": assignee_from or "",
            "to": assignee_to or ""
        })
    
    return {
        "created": created,
        "items": items
    }


def create_resolution_change(created: str, from_resolution: Optional[str], 
                            to_resolution: Optional[str],
                            author_account_id: Optional[str] = None) -> Dict:
    """Create a resolution change history entry."""
    entry = {
        "created": created,
        "items": [
            {
                "field": "resolution",
                "from": from_resolution or "",
                "to": to_resolution or ""
            }
        ]
    }
    
    if author_account_id:
        entry["author"] = {"accountId": author_account_id}
    
    return entry


# Common test data constants
PERSON_A_ID = "557058:person-a-account-id"
PERSON_B_ID = "557058:person-b-account-id"
PERSON_C_ID = "557058:person-c-account-id"
PERSON_D_ID = "557058:person-d-account-id"


def days_to_iso(day: int, time: str = "10:00:00") -> str:
    """Convert day offset to ISO timestamp starting from 2025-01-01.
    
    Args:
        day: Day offset (0 = 2025-01-01, 1 = 2025-01-02, etc.)
        time: Time of day in HH:MM:SS format
        
    Returns:
        ISO timestamp string
    """
    import datetime as dt
    base = dt.datetime(2025, 1, 1, 0, 0, 0)
    target = base + dt.timedelta(days=day)
    parts = time.split(":")
    target = target.replace(hour=int(parts[0]), minute=int(parts[1]), second=int(parts[2]))
    return target.strftime("%Y-%m-%dT%H:%M:%S.000+0000")

