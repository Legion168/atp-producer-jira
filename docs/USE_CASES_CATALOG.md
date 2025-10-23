# Cycle Time Use Cases Catalog

## Purpose
This document catalogs all known use cases for cycle time calculation in Jira. Use this to:
- **Identify** which scenario you're dealing with
- **Track** new edge cases as they're discovered
- **Verify** the correct strategy is being used
- **Document** expected behavior for each scenario

## How to Use This Document

1. **When analyzing an issue:** Find the matching use case below
2. **When finding a bug:** Check if the use case is documented
3. **When discovering a new scenario:** Add it using the template at the end
4. **When troubleshooting:** Use the decision tree to identify the case

---

## Decision Tree

```
START: Analyzing issue cycle time
│
├─ Is an assignee filter specified?
│  ├─ NO → Check status/assignee complexity
│  │      ├─ Simple flow (≤5 status changes, ≤2 assignee changes)
│  │      │  └─→ Use Case 1: Simple Linear Process
│  │      │
│  │      └─ Complex flow (>5 status changes OR >2 assignee changes)
│  │         └─→ Use Case 2: Complex Multi-Stage Process
│  │
│  └─ YES → Multiple assignees involved?
│         ├─ NO (Single assignee) → Issue already assigned when work started?
│         │                         ├─ YES → Use Case 5
│         │                         └─ NO → Use Case 3
│         │
│         └─ YES (Multiple assignees) → Assignee worked multiple times?
│                                      ├─ YES → Use Case 6
│                                      └─ NO → Use Case 4
```

---

## Documented Use Cases

### ✅ Use Case 1: Simple Linear Process
**Status:** ✅ Fully Supported  
**Strategy:** SimpleCycleTimeStrategy  
**Frequency:** Very Common (~70% of issues)

#### Description
A single person takes an issue from backlog, works on it linearly through statuses, and completes it. Clean, straightforward workflow.

#### Characteristics
- Single assignee (or no assignee tracking needed)
- Linear status progression
- ≤ 5 status changes
- ≤ 2 assignee changes
- No assignee filter specified

#### Example Timeline
```
Day 1:  [Backlog] → [In Development]  (Person A)
Day 5:  [In Development] → [In Review]
Day 7:  [In Review] → [Done]

Expected:
- Start: Day 1
- End: Day 7
- Cycle Time: 6 days
```

#### Jira History Example
```
1. Status: Backlog → In Development
2. Status: In Development → In Review
3. Status: In Review → Done
```

#### Expected Behavior
- ✅ Uses first "In Progress" transition as start
- ✅ Uses first "Done" transition as end
- ✅ Excludes time in specified statuses (e.g., Acceptance)
- ✅ Fast calculation (simple algorithm)

---

### ✅ Use Case 2: Complex Multi-Stage Process
**Status:** ✅ Fully Supported  
**Strategy:** ComplexCycleTimeStrategy  
**Frequency:** Common (~20% of issues)

#### Description
Issue goes through many status changes, back-and-forth movements, or has complex workflow. Still single assignee but complicated flow.

#### Characteristics
- Single or no assignee filter
- > 5 status changes
- Multiple status reversals (e.g., Dev → Review → Dev → Review)
- May include non-work statuses (On Hold, Blocked)

#### Example Timeline
```
Day 1:  [Backlog] → [Analysis]
Day 2:  [Analysis] → [In Development]
Day 3:  [In Development] → [On Hold]        ← Blocked
Day 5:  [On Hold] → [In Development]        ← Resumed
Day 7:  [In Development] → [In Review]
Day 8:  [In Review] → [In Development]      ← Rework
Day 10: [In Development] → [In Review]
Day 11: [In Review] → [Acceptance]          ← Excluded status
Day 12: [Acceptance] → [Done]

Expected:
- Start: Day 2 (first valid in-progress)
- End: Day 12
- Cycle Time: 10 days (excluding Acceptance period)
```

#### Jira History Example
```
1. Status: Backlog → Analysis
2. Status: Analysis → In Development
3. Status: In Development → On Hold
4. Status: On Hold → In Development
5. Status: In Development → In Review
6. Status: In Review → In Development
7. Status: In Development → In Review
8. Status: In Review → Acceptance
9. Status: Acceptance → Done
```

#### Expected Behavior
- ✅ Filters out non-work status transitions
- ✅ Handles status reversals correctly
- ✅ Excludes specified statuses from cycle time
- ✅ Uses sophisticated flow analysis

---

### ✅ Use Case 3: Single Assignee - Clean Assignment
**Status:** ✅ Fully Supported (Fixed in latest version)  
**Strategy:** ComplexCycleTimeStrategy  
**Frequency:** Common (~15% when filtering)

#### Description
Filtering by a specific assignee who was assigned at the start and completed the work. Clean handoff with clear start/end.

#### Characteristics
- Assignee filter specified
- Person assigned before or at work start
- Person completed the work
- No re-assignments during work

#### Example Timeline
```
Day 1:  Person A assigned
Day 1:  [Backlog] → [In Development]  (Person A)
Day 5:  [In Development] → [Done]     (Person A)
Day 5:  Person A unassigned

Expected for Person A:
- Start: Day 1 (assignment or first in-progress, whichever is later)
- End: Day 5
- Cycle Time: 4 days
```

#### Jira History Example
```
1. Assignee: None → Person A
2. Status: Backlog → In Development
3. Status: In Development → Done
4. Assignee: Person A → None
```

#### Expected Behavior
- ✅ Tracks Person A's assignment period
- ✅ Only counts work during their assignment
- ✅ Starts when they were assigned (if already in progress) or when moved to in-progress
- ✅ Ends when they completed or were unassigned

---

### ✅ Use Case 4: Multiple Assignees - Sequential Handoff
**Status:** ✅ Fully Supported (Fixed in latest version)  
**Strategy:** ComplexCycleTimeStrategy  
**Frequency:** Common (~10% when filtering)

#### Description
Work is handed off between multiple people. When filtering by a specific assignee, only their work period should be counted.

#### Characteristics
- Assignee filter specified
- Multiple people worked on the issue
- Clear handoff points
- Target assignee worked once

#### Example Timeline
```
Day 1:  Person A assigned
Day 1:  [Backlog] → [In Development]  (Person A)
Day 3:  Person A → Person B            ← Handoff
Day 3:  [In Development] → [In Review] (Person B)
Day 5:  Person B → Person C            ← Handoff
Day 5:  [In Review] → [Done]           (Person C)

Expected for Person B:
- Start: Day 3 (when assigned)
- End: Day 5 (when unassigned)
- Cycle Time: 2 days
```

#### Jira History Example
```
1. Assignee: None → Person A
2. Status: Backlog → In Development
3. Assignee: Person A → Person B          ← Track this for Person B
4. Status: In Development → In Review
5. Assignee: Person B → Person C          ← End tracking for Person B
6. Status: In Review → Done
```

#### Expected Behavior
- ✅ Tracks only Person B's assignment period (Day 3-5)
- ✅ Ignores work by Person A and Person C
- ✅ Starts at assignment or next in-progress transition
- ✅ Ends at unassignment or completion during their period

---

### ✅ Use Case 5: Assigned While Already In Progress (Handoff)
**Status:** ✅ Fully Supported (Fixed in latest version)  
**Strategy:** ComplexCycleTimeStrategy  
**Frequency:** Occasional (~5% when filtering)

#### Description
Issue is already in an "In Progress" status when the target assignee is assigned **from another person** (handoff scenario). Should use assignment time as the start for the new assignee.

**Important:** This ONLY applies when there's a handoff from Person A to Person B, NOT when issue is unassigned and then assigned for the first time.

#### Characteristics
- Assignee filter specified
- Issue already in progress before assignment
- **Previous assignee exists** (Person A → Person B handoff)
- Assignment happens during work, not at start

#### Example Timeline
```
Day 1:  Person A assigned
Day 1:  [Backlog] → [In Development]  (Person A)
Day 3:  Person A → Person B            ← Handoff! Issue already in development
Day 5:  [In Development] → [In Review] (Person B)
Day 7:  [In Review] → [Done]           (Person B)

Expected for Person B:
- Start: Day 3 (assignment time, since it's a handoff while in progress)
- End: Day 7
- Cycle Time: 4 days
```

#### Jira History Example
```
1. Assignee: None → Person A
2. Status: Backlog → In Development    (Person A working)
3. Assignee: Person A → Person B       ← Handoff while in progress
4. Status: In Development → In Review  (Person B continues)
5. Status: In Review → Done
```

#### Counter-Example (NOT Use Case 5)
```
1. Status: Backlog → In Development    (Unassigned)
2. Assignee: None → Person B           ← First assignment, not a handoff
   
Expected for Person B:
- Start: Step 1 time (status change), NOT Step 2 time
- This is just normal assignment, not Use Case 5
```

#### Expected Behavior
- ✅ Detects issue was in progress at assignment time
- ✅ Uses assignment time as start (not earlier transition)
- ✅ Only counts time from when Person B took over
- ✅ Handles edge case correctly

---

### ✅ Use Case 6: Multiple Assignment Periods - Same Person
**Status:** ✅ Fully Supported (Fixed in latest version)  
**Strategy:** ComplexCycleTimeStrategy  
**Frequency:** Rare (~2% when filtering)

#### Description
The same person is assigned, unassigned, and then assigned again. Should track all their work periods or just the first valid one.

#### Characteristics
- Assignee filter specified
- Person assigned multiple times
- May have worked in multiple periods
- Complex re-assignment pattern

#### Example Timeline
```
Day 1:  Person A assigned
Day 1:  [Backlog] → [In Development]  (Person A)
Day 3:  Person A → Person B            ← Person A unassigned
Day 5:  Person B → Person A            ← Person A re-assigned!
Day 5:  [In Development] → [In Review] (Person A again)
Day 7:  [In Review] → [Done]           (Person A)

Expected for Person A:
- Start: Day 1 (first assignment and in-progress)
- End: Day 7 (final completion)
- Cycle Time: 6 days (but only periods when assigned)
  - Period 1: Day 1-3 (2 days)
  - Period 2: Day 5-7 (2 days)
  - Total: 4 days (excluding unassigned period)
```

#### Jira History Example
```
1. Assignee: None → Person A
2. Status: Backlog → In Development
3. Assignee: Person A → Person B       ← Unassigned
4. Assignee: Person B → Person A       ← Re-assigned
5. Status: In Development → In Review
6. Status: In Review → Done
```

#### Expected Behavior
- ✅ Tracks multiple assignment periods
- ✅ Sums time across all periods
- ✅ Excludes time when unassigned
- ✅ Handles re-assignments correctly

**Note:** Current implementation uses first assignment period to completion. May need enhancement to sum multiple periods.

---

## Edge Cases & Corner Cases

### 🟡 Use Case 7: Never Reached In-Progress
**Status:** ⚠️ Handled (Returns NULL)  
**Strategy:** Both  
**Frequency:** Occasional

#### Description
Issue was resolved/closed without ever reaching an "In Progress" status.

#### Example
```
1. Status: Backlog → Done  (directly)
```

#### Expected Behavior
- ✅ Returns CycleTime with NULL values
- ✅ Issue excluded from metrics
- ✅ Shows in "filtered issues" debug table

---

### 🟡 Use Case 8: In Progress But Never Done
**Status:** ⚠️ Handled (Returns NULL done_at)  
**Strategy:** Both  
**Frequency:** Common (work in progress)

#### Description
Issue is currently in progress but not yet completed.

#### Example
```
1. Status: Backlog → In Development
2. (No done transition yet)
```

#### Expected Behavior
- ✅ Returns in_progress_at with value
- ✅ Returns done_at as NULL
- ✅ Excluded from completed metrics
- ✅ Shows in "filtered issues" debug table

---

### 🟡 Use Case 9: Assignee Never Worked On It
**Status:** ⚠️ Handled (Returns NULL)  
**Strategy:** ComplexCycleTimeStrategy  
**Frequency:** Occasional

#### Description
Filtering by an assignee who was never actually assigned to the issue (or was assigned but issue never reached in-progress during their period).

#### Example
```
Filter: Person B
History:
1. Assignee: None → Person A
2. Status: Backlog → In Development (Person A)
3. Status: In Development → Done (Person A)
```

#### Expected Behavior
- ✅ Detects Person B never assigned
- ✅ Returns CycleTime with NULL values
- ✅ Issue excluded from Person B's metrics

---

### 🔴 Use Case 10: Status Changed During Excluded Status (Acceptance/Feedback)
**Status:** ✅ Handled (Time excluded)  
**Strategy:** Both  
**Frequency:** Common with Acceptance/Feedback stages

#### Description
Issue moves through excluded status (like Acceptance or Feedback) which should not count toward cycle time. These are statuses where the team is waiting for external input/approval.

#### Example 1: Acceptance Status
```
Day 1:  [Backlog] → [In Development]
Day 5:  [In Development] → [Acceptance]  ← Start exclusion
Day 7:  [Acceptance] → [Done]            ← End exclusion

Expected:
- Start: Day 1
- End: Day 7
- Cycle Time: 4 days (7 - 1 - 2 days in Acceptance)
```

#### Example 2: Feedback Status
```
Sept 11, 14:41: [Backlog] → [In Development]    ← Start work
Sept 11, 17:10: [In Development] → [Feedback]   ← Start exclusion (waiting for feedback)
Sept 12, 09:48: Reassigned to different person  (still in Feedback)
Feb 20, 11:17:  Reassigned back to Person A     (still in Feedback)
Feb 20, 11:18:  [Feedback] → [Closed]           ← End exclusion

Expected for Person A:
- Active work time: Sept 11, 14:41 → Sept 11, 17:10 = ~2.5 hours
- Excluded time: Sept 11, 17:10 → Feb 20, 11:18 = NOT counted
- Cycle Time: ~2.5 hours (NOT 161 days)
```

#### Expected Behavior
- ✅ Tracks entry to excluded status
- ✅ Tracks exit from excluded status
- ✅ Subtracts excluded time from total
- ✅ Handles multiple excluded periods

---

### ✅ Use Case 11: First Assignment After Status Change
**Status:** ✅ Resolved (Bug Fixed)  
**Strategy:** ComplexCycleTimeStrategy  
**Frequency:** Common  
**Discovered:** [Current Date]  
**Related Issue(s):** Example Issue  
**Fixed:** [Current Date]

#### Description
Issue moves to "In Progress" status while **unassigned**, then gets assigned to someone for the first time. This is NOT a handoff (Use Case 5), so should use the status change time as start, not assignment time.

**Root Cause:** Use Case 5 logic was incorrectly triggering for first assignments, not just handoffs.

#### Characteristics
- Issue **unassigned**
- Issue moves to in-progress status
- Then gets assigned to someone for the first time
- NOT a handoff from another person

#### Example Timeline
```
Mar 12, 11:10  - Status: Backlog → In Development (Unassigned)
Mar 12, 11:32  - Assignee: Unassigned → Developer (first assignment)
Mar 12, 14:07  - Status: In Development → Done

Expected for Developer:
- Start: Mar 12, 11:10 (status change) ✅
- End: Mar 12, 14:07 (done)
- Cycle Time: ~3 hours
```

#### Jira History Example
```
1. Status: Backlog → In Development  (11:10, Unassigned)
2. Assignee: None → Developer   (11:32, First assignment)
3. Status: In Development → Done     (14:07)
```

#### Bug Behavior (Before Fix)
- ❌ Used 11:32 (assignment time) as start
- ❌ Incorrectly treated as Use Case 5 (handoff)
- ❌ Started counting 22 minutes late

#### Fixed Behavior (After Fix)
- ✅ Uses 11:10 (status change time) as start
- ✅ Correctly recognizes this is NOT a handoff
- ✅ Use Case 5 now only applies when there's a previous assignee

#### Code Fix
Modified `_get_first_assignment_in_progress()` in `complex_cycle_time_strategy.py` to:
```python
# Only use assignment time if:
# 1. Issue was in progress, AND
# 2. There was a previous assignee (handoff from Person A to Person B)
if current_status and current_status in self.in_progress_lower:
    if previous_assignee:  # There was someone assigned before (handoff)
        return first_assignment_time
```

#### Status
- [x] Reproduced with test data
- [x] Root cause identified
- [x] Fix implemented
- [x] Use Case 5 corrected to only apply to handoffs
- [ ] Regression test added (pending)

#### Related Use Cases
- **Use Case 5** - Now correctly applies ONLY to handoffs (Person A → Person B)
- **Use Case 3** - First assignment when issue is already in a different status

#### Lessons Learned
- Use Case 5 should ONLY apply to handoffs between assignees
- First assignments should use status change time, not assignment time
- Need to check for previous assignee, not just check if issue was in progress

---

### ✅ Use Case 12: Issue Closed and Reopened
**Status:** ✅ Resolved (Implemented)  
**Strategy:** Both (SimpleCycleTimeStrategy and ComplexCycleTimeStrategy)  
**Frequency:** Common (especially with test/staging deployments)  
**Discovered:** [Current Date]  
**Related Issue(s):** Example Issue  
**Fixed:** [Current Date]

#### Description
Issue is closed (marked as Done/Closed), but then reopened and worked on again. This happens when:
- Issue is closed prematurely (wrong fix, incomplete)
- Issue is reopened after testing reveals problems
- Issue is closed by automation, then reopened manually

The system should use the **LAST closure** as the completion date, not the first closure.

#### Characteristics
- Issue moves to a "done" status (Closed, Done, etc.)
- Later, issue is moved back to an "in progress" status (reopened)
- Issue may be closed and reopened multiple times
- Final closure is when work actually completes

#### Example Timeline
```
Nov 28, 12:15  - Status: Backlog → In Development (start work)
...
Jan 14, 14:24  - Status: In Development → Closed (first closure, by Lorenzo)
Jan 14, 14:39  - Status: Closed → In Development (reopened by Developer)
Jan 14, 14:55  - Status: In Development → In Peer Review
Jan 14, 15:24  - Status: In Peer Review → Closed (second closure, by Automation)
Jan 14, 15:28  - Status: Closed → In Development (reopened again by Developer)
...
Jan 20, 17:18  - Status: In Development → Closed (FINAL closure by Developer)

Expected:
- Start: Nov 28, 12:15 (first in progress)
- End: Jan 20, 17:18 (LAST closure) ✅
- Cycle Time: ~53 days (NOT 47 days from first closure)
```

#### Jira History Example
```
1. Status: Backlog → In Development  (Nov 28, 12:15)
2. Assignee: None → Person A         (Nov 28, 12:15)
... (work continues) ...
3. Status: In Development → Closed   (Jan 14, 14:24) ← First closure
4. Status: Closed → In Development   (Jan 14, 14:39) ← Reopened!
5. Status: In Development → In Peer Review (Jan 14, 14:55)
6. Status: In Peer Review → Closed   (Jan 14, 15:24) ← Second closure
7. Status: Closed → In Development   (Jan 14, 15:28) ← Reopened again!
... (more work) ...
8. Status: In Development → Closed   (Jan 20, 17:18) ← FINAL closure
```

#### Before Fix Behavior
- ❌ Used FIRST closure (Jan 14, 14:24) as end date
- ❌ Cycle time = ~47 days (premature closure)
- ❌ Ignored all work done after first closure

#### After Fix Behavior
- ✅ Uses LAST closure (Jan 20, 17:18) as end date
- ✅ Cycle time = ~53 days (actual completion)
- ✅ Correctly accounts for all work until final closure

#### Algorithm Change
Changed `_find_first_completion()` and `_find_first_done()` to find LAST completion instead of FIRST:

**Before (Simple Strategy):**
```python
if earliest_done is None or created_at < earliest_done:
    earliest_done = created_at
return earliest_done  # Returns FIRST closure
```

**After (Simple Strategy):**
```python
if latest_done is None or created_at > latest_done:
    latest_done = created_at
return latest_done  # Returns LAST closure
```

**Before (Complex Strategy):**
```python
if status_completions:
    return min(status_completions)  # Returns FIRST
```

**After (Complex Strategy):**
```python
if status_completions:
    return max(status_completions)  # Returns LAST
```

#### Why This Approach
**Option 1: Use LAST closure** (chosen)
- ✅ Reflects reality - work continued until final closure
- ✅ Simpler to understand
- ✅ Matches "time in the system" metric
- ✅ Penalizes premature closures (encourages quality)

**Option 2: Track separate cycles** (not chosen)
- Would track each open→close→reopen→close as separate cycles
- More complex to implement and understand
- Doesn't match typical cycle time definitions

#### Related Use Cases
- **Use Case 1-2:** Standard completion detection
- **Use Case 10:** Excluded statuses (if "Closed" was excluded, would still apply)

#### Status
- [x] Reproduced with test data
- [x] Root cause identified (using min instead of max)
- [x] Fix implemented in both strategies
- [x] Testing completed (test_issue_closed_and_reopened)
- [x] Documented

#### Test Coverage
Test: `TestUseCase12IssueClosedAndReopened.test_issue_closed_and_reopened()`
- ✅ Simulates multiple close/reopen cycles
- ✅ Verifies LAST closure is used
- ✅ Confirms ~53 days, not ~47 days

#### Notes
- This is a common pattern when using automated testing/deployment
- May also occur with "false positive" closures by support/QA
- The fix applies to both Simple and Complex strategies

#### Lessons Learned
- Always consider that issues can be reopened
- "First" doesn't always mean "correct" - last closure is more reliable
- Need to track ALL completions, not just stop at the first one

---

### ✅ Use Case 13: Author of Transitions Without Formal Assignment
**Status:** ✅ Resolved (Implemented)  
**Strategy:** ComplexCycleTimeStrategy  
**Frequency:** Common (especially with solo work or quick fixes)  
**Discovered:** March 2025  
**Related Issue(s):** Example Issue  
**Fixed:** March 2025

#### Description
An issue is created and worked on by someone, but they are never formally assigned through a changelog event. The person moves the card through the workflow (e.g., Backlog → In Development → Closed) but no "assignee" field change appears in the history. This commonly happens when:
- Assignee is set during issue creation (doesn't create changelog entry)
- Developer creates and immediately works on a quick fix
- Issues are moved through workflow without formal assignment

When filtering by assignee, the algorithm should recognize their **authorship of status transitions** as evidence of their work, even without a formal assignment event.

#### Characteristics
- **No assignee change events** in the changelog
- Current assignee field may show the person (set at creation)
- The person is the **author** of in-progress and/or done status transitions
- Filtering by their account ID would normally exclude the issue

#### Example Timeline
```
Mar 28, 09:58  - Created by Developer (assignee set to Developer, no changelog)
Mar 28, 09:58  - Status: Backlog → In Development (author: Developer)
Mar 28, 10:57  - Status: In Development → Closed (author: Developer)

Changelog shows:
- ✅ Status changes authored by Developer
- ❌ No assignee change events

Expected when filtering by Developer:
- Start: Mar 28, 09:58 (In Development transition)
- End: Mar 28, 10:57 (Closed transition)
- Cycle Time: ~0.04 days (59 minutes) ✅
```

#### Jira History Example
```json
{
  "created": "2025-03-28T09:58:23.766+0100",
  "author": {
    "accountId": "6304d4a59a460a36a1edacad",
    "displayName": "Developer"
  },
  "items": [
    {
      "field": "status",
      "fromString": "Backlog",
      "toString": "In Development"
    }
  ]
}
```

**Key observation:** The `author` field shows who made each change, providing evidence of work even without formal assignment.

#### Before Fix Behavior
When filtering by Developer (account ID: 6304d4a59a460a36a1edacad):
- ❌ `_get_assignee_periods()` returns empty list (no assignment events)
- ❌ Algorithm returns "Missing In Progress" (None/None/None)
- ❌ Issue excluded from Developer's cycle time metrics

#### After Fix Behavior
When filtering by Developer:
- ✅ `_get_assignee_periods()` returns empty list (no assignment events)
- ✅ `_is_author_of_transitions()` detects Developer authored the workflow transitions
- ✅ Algorithm proceeds without period restrictions
- ✅ Cycle time calculated: 0.04 days (59 minutes)
- ✅ Issue correctly attributed to Developer

#### Algorithm Enhancement
Added new method `_is_author_of_transitions()` in `ComplexCycleTimeStrategy`:

```python
def _is_author_of_transitions(self, histories: List[Dict], assignee_account_id: str) -> bool:
    """
    Check if the given account ID is the author of in-progress or done status transitions.
    
    This handles the case where someone creates and works on an issue without being formally
    assigned. If they're the one moving it through the workflow, we should count it as their work.
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
```

**Modified `calculate()` method:**
```python
if assignee_account_id:
    assignee_periods = self._get_assignee_periods(histories, assignee_account_id)
    if not assignee_periods:
        # No formal assignment, but check if this person was the author of status changes
        if self._is_author_of_transitions(histories, assignee_account_id):
            # Person moved the card to in-progress and/or done, treat as their work
            assignee_periods = None  # Will calculate without period restrictions
        else:
            # Assignee was never involved with this issue
            return CycleTime(...)  # Return empty result
```

#### Why This Approach
**Benefits:**
- ✅ Captures work done without formal assignment ceremony
- ✅ Uses existing Jira data (author field in changelog)
- ✅ Only applies to ComplexCycleTimeStrategy (when filtering by assignee)
- ✅ Still excludes issues where person wasn't involved at all
- ✅ Respects the intent: if someone moved the card, they worked on it

**Safeguards:**
- Only triggers when filtering by specific assignee
- Only counts if they authored in-progress OR done transitions
- If someone else authored the transitions, issue is still excluded
- Doesn't affect non-filtered queries (all assignees)

#### Related Use Cases
- **Use Case 3:** Single Assignee - Clean Assignment (formal assignment version)
- **Use Case 9:** Assignee Never Worked On It (negative case - correctly excludes)

#### Status
- [x] Reproduced with real data
- [x] Root cause identified (missing assignee changelog events)
- [x] Enhancement implemented in ComplexCycleTimeStrategy
- [x] Testing completed (test_author_of_transitions_without_assignment)
- [x] Negative case tested (test_different_author_excluded)
- [x] Documented

#### Test Coverage
**Test 1:** `TestUseCase13AuthorOfTransitionsWithoutAssignment.test_author_of_transitions_without_assignment()`
- ✅ Simulates issue with no assignment events
- ✅ Person authors both in-progress and done transitions
- ✅ Verifies cycle time is calculated when filtering by that person
- ✅ Confirms ~1.19 days cycle time

**Test 2:** `TestUseCase13AuthorOfTransitionsWithoutAssignment.test_different_author_excluded()`
- ✅ Simulates issue authored by someone else
- ✅ Filtering by different person
- ✅ Verifies issue is correctly excluded (returns None/None/None)

#### Real-World Impact
This enhancement is particularly important for:
- **Quick fixes:** Developer creates, fixes, and closes issue rapidly
- **Solo work:** Single developer working alone doesn't need formal assignment
- **Small teams:** Less ceremony around assignment tracking
- **Issue triage:** Person who triages and immediately fixes doesn't formally assign

#### Notes
- Only implemented in `ComplexCycleTimeStrategy` (assignee filtering logic)
- `SimpleCycleTimeStrategy` doesn't need this (no assignee filtering)
- Author detection checks **any** in-progress or done transition, not just the first
- If issue has both assignment events AND author evidence, assignment takes precedence

#### Lessons Learned
- Jira's `author` field in changelog is valuable evidence of work
- Formal assignment isn't always required for accurate attribution
- Edge cases often reveal workflow ceremony mismatches
- Good to have both positive and negative test cases

---

### ✅ Use Case 14: Overlapping Impediment and Excluded Time
**Status:** ✅ Resolved (Implemented)  
**Strategy:** Both SimpleCycleTimeStrategy and ComplexCycleTimeStrategy  
**Frequency:** Common (when issues are blocked AND waiting for feedback)  
**Discovered:** October 2025  
**Related Issue(s):** Example Issue  
**Fixed:** October 2025

#### Description
An issue is both flagged as impediment AND in an excluded status (like Feedback) simultaneously. This creates overlapping periods that could cause negative cycle time due to double-counting the same time period.

#### Characteristics
- Issue is **flagged as impediment** (blocked by external factors)
- Issue is **in an excluded status** (like Feedback, Acceptance)
- These periods **overlap in time**
- Without proper handling, this causes **negative active cycle time**

#### Example Timeline
```
Aug 18, 11:08  - In Development (work starts)
Aug 19, 18:08  - Flagged as Impediment (blocked)
Sep 01, 14:15  - Impediment cleared
Sep 02, 10:01  - In Development → Feedback (waiting for feedback)
Sep 02, 14:52  - Feedback → In Development
Sep 04, 09:31  - Flagged as Impediment again
Sep 05, 09:41  - In Development → Feedback (while still impediment)
Sep 09, 09:05  - Impediment cleared
Sep 09, 09:08  - Feedback → Closed (done)

Overlapping period: Sep 05-09 (both impediment AND Feedback)
```

#### The Problem
**Before Fix:**
- Total time: 21.92 days
- Impediment time: 17.82 days
- Excluded time: 4.18 days
- Active time: 21.92 - 17.82 - 4.18 = **-0.08 days** ❌

**After Fix:**
- Total time: 21.92 days
- Impediment time: 17.82 days
- Excluded time: 4.18 days
- Overlap: ~4 days (time that was both impediment AND Feedback)
- Active time: 21.92 - 17.82 - 4.18 + 4.00 = **3.89 days** ✅

#### Solution
Added **overlap detection** to prevent double-counting:
- New method: `_calculate_excluded_impediment_overlap()`
- Identifies periods that are both impediment AND excluded
- Calculates overlap time and adds it back to active time
- Formula: `active_time = total - excluded - impediment + overlap`

#### Test Coverage
**Test:** `TestUseCase14OverlappingImpedimentAndExcludedTime.test_overlapping_impediment_and_excluded_time()`
- ✅ Simulates issue with overlapping impediment and excluded periods
- ✅ Verifies positive active cycle time (no negative values)
- ✅ Confirms both impediment and excluded time are tracked
- ✅ Validates overlap calculation prevents double-counting

#### Real-World Impact
This fix is important for:
- **Blocked issues:** When external dependencies cause delays
- **Feedback loops:** When issues are waiting for stakeholder input
- **Complex workflows:** Multiple status types and blocking conditions
- **Accurate metrics:** Prevents negative cycle times that break analytics

#### Lessons Learned
- Overlapping periods need special handling in time calculations
- Double-counting can cause negative values in arithmetic
- Real-world scenarios are often more complex than simple cases
- Good to test edge cases that could break the calculation logic

---

## Template for New Use Cases

### 🆕 Use Case [NUMBER]: [SHORT TITLE]
**Status:** 🆕 Newly Discovered / 🔄 Under Investigation / ✅ Resolved  
**Strategy:** [SimpleCycleTimeStrategy / ComplexCycleTimeStrategy / Unknown]  
**Frequency:** [Very Common / Common / Occasional / Rare]  
**Discovered:** [Date]  
**Discovered By:** [Your Name]  
**Related Issue(s):** [JIRA-KEY]

#### Description
[Describe what makes this case unique or different from existing cases]

#### Characteristics
- [Key characteristic 1]
- [Key characteristic 2]
- [Key characteristic 3]

#### Example Timeline
```
[Provide day-by-day or step-by-step example]
```

#### Jira History Example
```
[Paste actual or sanitized Jira history]
```

#### Current Behavior
- [What currently happens]

#### Expected Behavior
- [What should happen]

#### Status
- [ ] Reproduced
- [ ] Root cause identified
- [ ] Fix implemented
- [ ] Testing completed
- [ ] Documented

#### Notes
[Any additional context, screenshots, or references]

---

## Statistics & Metrics

### Use Case Distribution (Estimated)
Based on typical Jira usage:

```
Use Case 1 (Simple Linear):              ████████████████████ 70%
Use Case 2 (Complex Multi-Stage):        ████████ 20%
Use Case 3 (Single Assignee Clean):      ████ 5%
Use Case 4 (Multiple Assignees):         ██ 3%
Use Case 5 (Assigned While In Progress): █ 1%
Use Case 6 (Multiple Assignment Periods): █ 1%
```

### Strategy Usage
- **SimpleCycleTimeStrategy:** ~70% of issues (no filter, simple flow)
- **ComplexCycleTimeStrategy:** ~30% of issues (has filter or complex flow)

---

## Troubleshooting Guide

### Problem: Cycle time seems too long
**Check for:**
- Use Case 4: Is the issue assigned to multiple people? Filter by specific assignee.
- Use Case 10: Is time in "Acceptance" or other statuses being counted? Check exclude_statuses.
- Use Case 2: Are there many status changes? Check for On Hold or Blocked periods.

### Problem: Cycle time starts too early
**Check for:**
- Use Case 4: Work started before your assignee was assigned
- Use Case 1: No assignee filter specified, using first in-progress transition

### Problem: No cycle time calculated (NULL)
**Check for:**
- Use Case 7: Issue never reached in-progress status
- Use Case 8: Issue never reached done status
- Use Case 9: Filtered assignee never worked on the issue

### Problem: Cycle time starts at wrong date with assignee filter
**Check for:**
- Bug was fixed in latest version - ensure you're using ComplexCycleTimeStrategy
- Use Case 5: Assignee joined while already in progress - should use assignment date

---

## Version History

### v2.0 (Current) - Strategy Pattern Refactoring
- ✅ Fixed Use Case 3, 4, 5, 6 (assignee filtering)
- ✅ Implemented automatic strategy selection
- ✅ Added ComplexCycleTimeStrategy for assignee tracking
- ✅ Improved handling of edge cases

### v1.0 (Previous) - Monolithic Implementation
- ✅ Supported Use Case 1 (simple linear)
- ✅ Supported Use Case 2 (complex multi-stage)
- ❌ Bug in Use Cases 3-6 (assignee filtering incorrect)

---

## How to Add a New Use Case

1. **Identify the Issue:**
   - Note the Jira issue key
   - Document unexpected behavior
   - Gather the issue's full history

2. **Check Existing Use Cases:**
   - Review this document
   - Confirm it's not already covered

3. **Document the Use Case:**
   - Copy the template above
   - Fill in all sections
   - Provide real examples

4. **Create a Test Case:**
   - Add to `test_strategy_selection.py`
   - Or create a specific test file

5. **Investigate:**
   - Determine which strategy should handle it
   - Identify if it's a bug or missing feature
   - Document root cause

6. **Implement Fix (if needed):**
   - Modify appropriate strategy
   - Add tests
   - Update documentation

7. **Update This Document:**
   - Change status to ✅ Fully Supported
   - Document expected behavior
   - Update statistics if significant

---

## Related Documents

- `ARCHITECTURE.md` - System architecture and design
- `REFACTORING_SUMMARY.md` - Recent changes and migration guide
- `test_strategy_selection.py` - Automated strategy selection tests
- `ATP_PRODUCER_DOCUMENTATION.md` - Overall application documentation

---

**Last Updated:** [Current Date]  
**Maintainer:** [Your Team/Name]  
**Next Review:** [Schedule regular reviews as you discover new cases]

