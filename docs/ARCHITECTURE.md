# Cycle Time Calculator Architecture

## Overview

The cycle time calculator uses a **Strategy Pattern** to handle different types of issue workflows. This allows for specialized logic depending on the complexity of the issue history.

## Architecture Components

### 1. Base Strategy (`cycle_time_strategy.py`)

**`CycleTimeStrategy`** - Abstract base class that defines:
- Common interface for all strategies
- Shared utility methods (datetime parsing, excluded time calculation)
- Strategy selection logic (`should_use_complex_strategy`)

### 2. Simple Strategy (`simple_cycle_time_strategy.py`)

**`SimpleCycleTimeStrategy`** - For clean, straightforward processes

**Use Case:**
- Single assignee (or no assignee filter)
- Linear progression through statuses
- Person takes work from backlog and completes it

**Hybrid Approach:**
The strategy automatically detects if an issue was reopened and selects the appropriate algorithm:

1. **For Reopened Issues** (cycle-based):
   - Detects Done → InProgress transitions (reopening)
   - Tracks ALL open→close cycles
   - Sums total time across all cycles
   - Excludes time spent in specified statuses per cycle

2. **For Normal Issues** (first-to-last):
   - Finds the **first** "In Progress" status transition
   - Finds the **first** "Done" status transition after that
   - Calculates the time difference
   - Excludes time spent in specified statuses

**When Used:**
- No assignee filter specified
- ≤ 2 assignee changes
- ≤ 5 status changes

**Example (Normal Issue):**
```
Timeline:
├─ [Backlog] → [In Development] ← START HERE
├─ [In Development] → [In Review]
└─ [In Review] → [Done] ← END HERE

Cycle Time = END - START (minus excluded statuses)
```

**Example (Reopened Issue):**
```
Timeline:
├─ [Backlog] → [In Development] ← Cycle 1 Start
├─ [In Development] → [Done] ← Cycle 1 End (2 days)
├─ [Done] → [In Development] ← REOPENED! Cycle 2 Start
└─ [In Development] → [Done] ← Cycle 2 End (3 days)

Total Cycle Time = Cycle 1 + Cycle 2 = 5 days
```

### 3. Complex Strategy (`complex_cycle_time_strategy.py`)

**`ComplexCycleTimeStrategy`** - For complicated processes with multiple people

**Use Case:**
- Multiple assignees involved
- Complex status transition flows
- Assignee-specific filtering required
- Issues passed between team members

**Hybrid Approach:**
The strategy automatically detects if an issue was reopened and selects the appropriate algorithm:

1. **For Reopened Issues** (cycle-based):
   - Detects Done → InProgress transitions (reopening)
   - Tracks ALL open→close cycles within assignee periods
   - Sums total time across all cycles
   - Handles complex scenarios: multiple closures, multiple assignments

2. **For Normal Issues** (first-to-last with assignee tracking):
   - **Check for formal assignment** - Track assignee periods from changelog
   - **Fallback to author detection** - If no assignment events, check if person authored workflow transitions (Use Case 13)
   - **Find work start** - GLOBAL first "In Progress", then adjust for assignee period
     - If in-progress before assignment: Check if handoff or first assignment
     - Handoff (had previous assignee): Use assignment time
     - First assignment (no previous assignee): Use status change time
   - **Find completion** - First "Done" during assignee's period (with 4-hour grace period)
   - **Calculate time** - Only count time while assignee was working on it
   - **Exclude periods** - Remove time spent in excluded statuses

**When Used:**
- Assignee filter is specified (most important)
- > 2 assignee changes
- > 5 status changes

**Example:**
```
Timeline:
├─ [Backlog] (Person A assigned)
├─ [In Development] (Person A working)
├─ [On Hold] (Person A still assigned)
├─ (Person B assigned) ← START TRACKING FOR PERSON B
├─ [In Development] ← START HERE for Person B
├─ [In Review]
├─ [Done] ← END HERE for Person B
└─ (Person B unassigned) ← STOP TRACKING

Cycle Time for Person B = END - START (only their work period)
```

### 4. Calculator Factory (`cycle_time_calculator.py`)

**`CycleTimeCalculator`** - Main entry point that:
- Initializes both strategies
- Automatically selects the appropriate strategy per issue
- Provides a consistent interface to the rest of the application

**Key Methods:**

```python
# Main calculation method
calculate_cycle_times(client, issue_keys, assignee_account_id)

# Strategy selection (internal)
_select_strategy(histories, assignee_account_id)

# Debug/info method
get_strategy_info(histories, assignee_account_id)
```

## Decision Flow

```
┌─────────────────────────────────┐
│  CycleTimeCalculator.calculate  │
│         (for each issue)         │
└────────────────┬────────────────┘
                 │
                 ▼
         ┌───────────────┐
         │ Get changelog │
         │   from Jira   │
         └───────┬───────┘
                 │
                 ▼
    ┌────────────────────────┐
    │  Analyze complexity:   │
    │ • Assignee filter?     │
    │ • Assignee changes?    │
    │ • Status changes?      │
    └────────┬───────────────┘
             │
      ┌──────┴──────┐
      │             │
      ▼             ▼
┌──────────┐  ┌──────────┐
│  Simple  │  │ Complex  │
│ Strategy │  │ Strategy │
└────┬─────┘  └────┬─────┘
     │             │
     └──────┬──────┘
            │
            ▼
     ┌──────────────┐
     │  CycleTime   │
     │    Result    │
     └──────────────┘
```

## Strategy Selection Criteria

| Condition | Simple | Complex |
|-----------|--------|---------|
| No assignee filter | ✓ | |
| Assignee filter specified | | ✓ |
| ≤ 2 assignee changes | ✓ | |
| > 2 assignee changes | | ✓ |
| ≤ 5 status changes | ✓ | |
| > 5 status changes | | ✓ |

## Usage Examples

### Basic Usage (No Assignee Filter)

```python
from app.cycle_time_calculator import CycleTimeCalculator
from app.jira_client import JiraClient

# Initialize
calculator = CycleTimeCalculator(
    in_progress_names=["In Development", "In Review"],
    done_names=["Closed", "Done"],
    exclude_statuses=["Acceptance"]
)

# Calculate (will use SimpleCycleTimeStrategy)
cycle_times = calculator.calculate_cycle_times(
    client=jira_client,
    issue_keys=["PROJ-123", "PROJ-124"]
)
```

### With Assignee Filter

```python
# Calculate for specific assignee (will use ComplexCycleTimeStrategy)
cycle_times = calculator.calculate_cycle_times(
    client=jira_client,
    issue_keys=["PROJ-123"],
    assignee_account_id="557058:abc123..."
)
```

### Debug Strategy Selection

```python
# Get info about which strategy would be used
info = calculator.get_strategy_info(histories, assignee_account_id)
print(f"Strategy: {info['strategy']}")
print(f"Reasons: {info['reasons']}")
print(f"Assignee changes: {info['assignee_changes']}")
print(f"Status changes: {info['status_changes']}")
```

## Cycle Time Metrics

### CycleTime Data Structure

The `CycleTime` dataclass returned by all strategies contains:

```python
@dataclass(frozen=True)
class CycleTime:
    issue_key: str                           # Jira issue key
    in_progress_at: Optional[datetime]       # When work started
    done_at: Optional[datetime]              # When work completed
    seconds: Optional[float]                 # Active cycle time (excludes waiting states)
    excluded_seconds: Optional[float]        # Time in Acceptance/Feedback (not counted)
    impediment_seconds: Optional[float]      # Time flagged as Impediment (tracked separately)
```

### Three Types of Metrics

#### 1. **Active Cycle Time** (Team Performance)
- **Formula**: `(total_seconds - excluded_seconds - impediment_seconds) / 86400` days
- **Purpose**: Measure actual productive work time
- **Excludes**: Time in Acceptance, Feedback, and impediment periods
- **Use for**: Team velocity, performance tracking, process improvement

#### 2. **Impediment Time** (Blocking Issues)
- **Formula**: `impediment_seconds / 86400` days
- **Purpose**: Track time spent blocked
- **Tracked via**: "Flagged" field changes in Jira changelog
- **Use for**: Identifying systemic blockers, process bottlenecks

### Example

```
Issue Timeline:
- Day 0:  In Development (work starts)
- Day 5:  Acceptance (waiting for QA)
- Day 8:  In Development (QA feedback)
- Day 10: Flagged as Impediment (blocked)
- Day 45: Impediment cleared (unblocked)
- Day 47: Closed (completed)

Results:
- Active Cycle Time: 9 days (excludes 3 days in Acceptance + 35 days impediment)
- Impediment Time: 35 days (blocked period)
```

### Excluded Statuses

Configurable list of statuses to exclude from active cycle time:
- Default: `["Acceptance", "Feedback"]`
- These represent waiting states where the team isn't actively working
- Time is excluded from Active Cycle Time but included in Total Cycle Time

### Impediment Tracking

Automatically tracks when issues are flagged as "Impediment":
- Monitors "Flagged" field in Jira changelog
- Detects transitions: `None → Impediment` and `Impediment → None`
- Sums total time spent flagged within the cycle time window
- Reported separately to identify blocking patterns

### Overlap Handling (Use Case 14)

Prevents double-counting when periods overlap:
- **Problem**: Issue is both impediment AND in excluded status (e.g., Feedback)
- **Solution**: `_calculate_excluded_impediment_overlap()` method
- **Formula**: `active_time = total - excluded - impediment + overlap`
- **Result**: Prevents negative cycle times from double-counting

Example:
```
Issue flagged as impediment: 5 days
Issue in Feedback status: 4 days  
Overlap period: 3 days (both impediment AND Feedback)
Active time = 10 - 4 - 5 + 3 = 4 days ✅
```

## Key Benefits

### 1. **Separation of Concerns**
- Each strategy handles its specific use case
- Shared logic in base class
- Easy to maintain and test

### 2. **Automatic Optimization**
- Simple strategy is faster for straightforward issues
- Complex strategy only used when necessary
- No manual configuration needed

### 3. **Extensibility**
- Easy to add new strategies (e.g., `TeamCycleTimeStrategy`)
- Can override strategy selection logic
- Can customize per-strategy behavior

### 4. **Debuggability**
- `get_strategy_info()` helps understand decisions
- Clear separation makes troubleshooting easier
- Each strategy is independently testable

## File Structure

```
app/
├── cycle_time_strategy.py           # Base abstract class
├── simple_cycle_time_strategy.py    # Clean process strategy
├── complex_cycle_time_strategy.py   # Multi-assignee strategy
├── cycle_time_calculator.py         # Factory/orchestrator
├── metrics.py                       # Integration layer
└── main.py                          # UI/application
```

## Future Enhancements

### Potential New Strategies:

1. **`TeamCycleTimeStrategy`**
   - Track multiple team members simultaneously
   - Calculate team-level metrics
   - Handle handoffs between team members

2. **`SprintCycleTimeStrategy`**
   - Focus on work within sprint boundaries
   - Handle sprint rollovers
   - Sprint-specific exclusions

3. **`PriorityWeightedStrategy`**
   - Weight cycle times by priority
   - Different algorithms for different priorities
   - Priority-aware exclusions

### Extension Points:

```python
# Custom strategy
class CustomStrategy(CycleTimeStrategy):
    def calculate(self, histories, issue_key, assignee_account_id):
        # Your custom logic here
        pass

# Register in calculator
calculator.custom_strategy = CustomStrategy(...)
```

## Testing Recommendations

### Unit Tests:
- Test each strategy independently
- Mock Jira history data
- Verify strategy selection logic

### Integration Tests:
- Test with real Jira data
- Verify correct strategy is selected
- Compare simple vs complex results

### Performance Tests:
- Benchmark simple strategy speed
- Ensure complex strategy overhead is acceptable
- Test with large issue batches

## Migration Notes

**No changes required to existing code!**

The public API of `CycleTimeCalculator` remains the same:
- `calculate_cycle_times()` method signature unchanged
- Backward compatible with existing calls
- Automatic strategy selection is transparent

Your existing code will continue to work, but now benefits from:
- Better performance (simple strategy when possible)
- More accurate assignee filtering (complex strategy)
- Clearer, more maintainable codebase

