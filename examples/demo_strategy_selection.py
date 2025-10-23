#!/usr/bin/env python3
"""
Test script to demonstrate strategy selection in the CycleTimeCalculator.

This script creates mock Jira history data and shows how the calculator
automatically selects the appropriate strategy based on issue complexity.
"""

from app.cycle_time_calculator import CycleTimeCalculator


def create_simple_history():
    """Create a mock history for a simple, clean process."""
    return [
        {
            "created": "2025-01-01T10:00:00.000+0000",
            "items": [
                {
                    "field": "status",
                    "fromString": "Backlog",
                    "toString": "In Development"
                }
            ]
        },
        {
            "created": "2025-01-05T15:00:00.000+0000",
            "items": [
                {
                    "field": "status",
                    "fromString": "In Development",
                    "toString": "Done"
                }
            ]
        }
    ]


def create_complex_history_multiple_assignees():
    """Create a mock history with multiple assignee changes."""
    return [
        {
            "created": "2025-01-01T10:00:00.000+0000",
            "items": [
                {
                    "field": "assignee",
                    "from": None,
                    "to": "person-a-id"
                }
            ]
        },
        {
            "created": "2025-01-01T10:05:00.000+0000",
            "items": [
                {
                    "field": "status",
                    "fromString": "Backlog",
                    "toString": "In Development"
                }
            ]
        },
        {
            "created": "2025-01-03T14:00:00.000+0000",
            "items": [
                {
                    "field": "assignee",
                    "from": "person-a-id",
                    "to": "person-b-id"
                }
            ]
        },
        {
            "created": "2025-01-04T11:00:00.000+0000",
            "items": [
                {
                    "field": "assignee",
                    "from": "person-b-id",
                    "to": "person-c-id"
                }
            ]
        },
        {
            "created": "2025-01-05T15:00:00.000+0000",
            "items": [
                {
                    "field": "status",
                    "fromString": "In Development",
                    "toString": "Done"
                }
            ]
        }
    ]


def create_complex_history_many_status_changes():
    """Create a mock history with many status changes."""
    return [
        {
            "created": "2025-01-01T10:00:00.000+0000",
            "items": [{"field": "status", "fromString": "Backlog", "toString": "Analysis"}]
        },
        {
            "created": "2025-01-02T10:00:00.000+0000",
            "items": [{"field": "status", "fromString": "Analysis", "toString": "In Development"}]
        },
        {
            "created": "2025-01-03T10:00:00.000+0000",
            "items": [{"field": "status", "fromString": "In Development", "toString": "On Hold"}]
        },
        {
            "created": "2025-01-04T10:00:00.000+0000",
            "items": [{"field": "status", "fromString": "On Hold", "toString": "In Development"}]
        },
        {
            "created": "2025-01-05T10:00:00.000+0000",
            "items": [{"field": "status", "fromString": "In Development", "toString": "In Review"}]
        },
        {
            "created": "2025-01-06T10:00:00.000+0000",
            "items": [{"field": "status", "fromString": "In Review", "toString": "Acceptance"}]
        },
        {
            "created": "2025-01-07T10:00:00.000+0000",
            "items": [{"field": "status", "fromString": "Acceptance", "toString": "Done"}]
        }
    ]


def print_separator(title):
    """Print a formatted separator with title."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def main():
    """Run strategy selection demonstrations."""
    
    # Initialize calculator
    calculator = CycleTimeCalculator(
        in_progress_names=["In Development", "Analysis", "In Review"],
        done_names=["Done", "Closed"],
        exclude_statuses=["Acceptance"]
    )
    
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "CYCLE TIME STRATEGY SELECTION DEMO" + " " * 24 + "║")
    print("╚" + "=" * 78 + "╝")
    
    # Test 1: Simple history, no assignee filter
    print_separator("Test 1: Simple Clean Process (No Assignee Filter)")
    histories = create_simple_history()
    info = calculator.get_strategy_info(histories, assignee_account_id=None)
    
    print(f"\n📊 History Analysis:")
    print(f"   • Assignee changes: {info['assignee_changes']}")
    print(f"   • Status changes: {info['status_changes']}")
    print(f"   • Has assignee filter: {info['has_assignee_filter']}")
    
    print(f"\n✨ Selected Strategy: {info['strategy']}")
    print(f"📝 Reasons: {', '.join(info['reasons'])}")
    print(f"\n💡 Expected behavior:")
    print(f"   → Find first 'In Progress' transition")
    print(f"   → Find first 'Done' transition")
    print(f"   → Calculate simple time difference")
    
    # Test 2: Multiple assignees
    print_separator("Test 2: Multiple Assignees (> 2 changes)")
    histories = create_complex_history_multiple_assignees()
    info = calculator.get_strategy_info(histories, assignee_account_id=None)
    
    print(f"\n📊 History Analysis:")
    print(f"   • Assignee changes: {info['assignee_changes']}")
    print(f"   • Status changes: {info['status_changes']}")
    print(f"   • Has assignee filter: {info['has_assignee_filter']}")
    
    print(f"\n✨ Selected Strategy: {info['strategy']}")
    print(f"📝 Reasons: {', '.join(info['reasons'])}")
    print(f"\n💡 Expected behavior:")
    print(f"   → Track all assignee periods")
    print(f"   → Handle complex assignee transitions")
    print(f"   → Use sophisticated period matching")
    
    # Test 3: Many status changes
    print_separator("Test 3: Many Status Changes (> 5 transitions)")
    histories = create_complex_history_many_status_changes()
    info = calculator.get_strategy_info(histories, assignee_account_id=None)
    
    print(f"\n📊 History Analysis:")
    print(f"   • Assignee changes: {info['assignee_changes']}")
    print(f"   • Status changes: {info['status_changes']}")
    print(f"   • Has assignee filter: {info['has_assignee_filter']}")
    
    print(f"\n✨ Selected Strategy: {info['strategy']}")
    print(f"📝 Reasons: {', '.join(info['reasons'])}")
    print(f"\n💡 Expected behavior:")
    print(f"   → Handle complex status flow")
    print(f"   → Filter out non-work transitions")
    print(f"   → Exclude specified statuses (e.g., Acceptance)")
    
    # Test 4: Assignee filter forces complex strategy
    print_separator("Test 4: Simple History WITH Assignee Filter")
    histories = create_simple_history()
    info = calculator.get_strategy_info(histories, assignee_account_id="person-a-id")
    
    print(f"\n📊 History Analysis:")
    print(f"   • Assignee changes: {info['assignee_changes']}")
    print(f"   • Status changes: {info['status_changes']}")
    print(f"   • Has assignee filter: {info['has_assignee_filter']}")
    
    print(f"\n✨ Selected Strategy: {info['strategy']}")
    print(f"📝 Reasons: {', '.join(info['reasons'])}")
    print(f"\n💡 Expected behavior:")
    print(f"   → Track assignee periods for 'person-a-id'")
    print(f"   → Only count time while assigned")
    print(f"   → Handle edge cases (assigned while in progress, etc.)")
    
    # Summary
    print_separator("Summary")
    print("""
The CycleTimeCalculator automatically selects the appropriate strategy:

┌─────────────────────────────────────────────────────────────────────┐
│  SimpleCycleTimeStrategy                                            │
├─────────────────────────────────────────────────────────────────────┤
│  ✓ Fast and efficient                                               │
│  ✓ For clean, linear processes                                      │
│  ✓ Single assignee or no filter                                     │
│  ✓ ≤ 2 assignee changes, ≤ 5 status changes                         │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│  ComplexCycleTimeStrategy                                           │
├─────────────────────────────────────────────────────────────────────┤
│  ✓ Handles multiple assignees                                       │
│  ✓ Tracks assignee-specific periods                                 │
│  ✓ For complicated workflows                                        │
│  ✓ Required when assignee filter is specified                       │
│  ✓ > 2 assignee changes OR > 5 status changes                       │
└─────────────────────────────────────────────────────────────────────┘

All selection is AUTOMATIC - no configuration needed!
    """)
    
    print("\n✅ All tests completed successfully!")
    print("\n")


if __name__ == "__main__":
    main()

