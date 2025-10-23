# Test Suite - Run Instructions

## ✅ What Was Fixed

### Tests Updated
1. **Use Case 5** - Fixed to test actual handoff (Person A → Person B)
2. **Use Case 11** - Added new test for first assignment after status change

### Test Count
- **Before:** 14 tests covering 10 use cases
- **After:** 15 tests covering 11 use cases

## 🧪 Running the Tests

### Prerequisites

Make sure you have Python dependencies installed:

```bash
# If you have a virtual environment, activate it first
source venv/bin/activate  # or your venv path

# Then ensure dependencies are installed
pip install -r requirements.txt
```

### Method 1: Run All Tests with Coverage Report

```bash
python3 tests/test_use_case_coverage.py
```

**Expected Output:**
```
================================================================================
CYCLE TIME USE CASE COVERAGE REPORT
================================================================================

test_simple_linear_flow ... ok
test_complex_multi_stage_flow ... ok
... (15 tests) ...

================================================================================
COVERAGE SUMMARY
================================================================================
Total Tests Run: 15
Successes: 15
Failures: 0
Errors: 0

USE CASE COVERAGE:
✅ Use Case 1: Simple Linear Process
✅ Use Case 2: Complex Multi-Stage Process
✅ Use Case 3: Single Assignee - Clean Assignment
✅ Use Case 4: Multiple Assignees - Sequential Handoff
✅ Use Case 5: Assigned While Already In Progress (Handoff) - FIXED
✅ Use Case 6: Multiple Assignment Periods - Same Person
✅ Use Case 7: Never Reached In-Progress
✅ Use Case 8: In Progress But Never Done
✅ Use Case 9: Assignee Never Worked On It
✅ Use Case 10: Status Changed During Acceptance
✅ Use Case 11: First Assignment After Status Change - NEW

Additional Coverage:
✅ Strategy Selection Logic

================================================================================
```

### Method 2: Run with unittest

```bash
# Run all tests
python3 -m unittest tests.test_use_case_coverage -v

# Run specific test class
python3 -m unittest tests.test_use_case_coverage.TestUseCase05AssignedWhileAlreadyInProgress -v

# Run specific test method
python3 -m unittest tests.test_use_case_coverage.TestUseCase11FirstAssignmentAfterStatusChange.test_first_assignment_after_status_change -v
```

### Method 3: Run with pytest (if installed)

```bash
# Run all tests with verbose output
pytest tests/test_use_case_coverage.py -v

# Run only Use Case 5 and 11 (the fixed ones)
pytest tests/test_use_case_coverage.py::TestUseCase05AssignedWhileAlreadyInProgress -v
pytest tests/test_use_case_coverage.py::TestUseCase11FirstAssignmentAfterStatusChange -v

# Run with coverage report
pytest tests/ --cov=app --cov-report=html
open htmlcov/index.html
```

## 🔍 What Changed in Tests

### Use Case 5 Test - Before (WRONG)

```python
# OLD - Testing first assignment (should be Use Case 11)
histories = [
    create_status_change(days_to_iso(1), "Backlog", "In Development"),  # Unassigned
    create_assignee_change(days_to_iso(3), None, PERSON_B_ID),  # First assignment
    ...
]
# Expected: 4 days (from Day 3)
```

### Use Case 5 Test - After (CORRECT)

```python
# NEW - Testing actual handoff
histories = [
    create_assignee_change(days_to_iso(1), None, PERSON_A_ID),  # Person A assigned
    create_status_change(days_to_iso(1, "10:30:00"), "Backlog", "In Development"),
    create_assignee_change(days_to_iso(3), PERSON_A_ID, PERSON_B_ID),  # HANDOFF!
    ...
]
# Expected: 4 days (from Day 3) - Person B's cycle time
```

### Use Case 11 Test - New

```python
# NEW TEST - First assignment after status change
histories = [
    create_status_change(days_to_iso(1, "11:10:00"), "Backlog", "In Development"),  # Unassigned
    create_assignee_change(days_to_iso(1, "11:32:00"), None, PERSON_A_ID),  # First assignment
    create_status_change(days_to_iso(1, "14:07:00"), "In Development", "Done")
]
# Expected: ~3 hours (from 11:10, not 11:32)
```

## ✅ Expected Results

All 15 tests should pass:
- ✅ **Use Case 5** - Tests handoff scenario correctly
- ✅ **Use Case 11** - Tests first assignment scenario  
- ✅ **All other tests** - Should still pass (no regressions)

## ⚠️ If Tests Fail

### Common Issues

1. **Module not found (requests, pytz, etc.)**
   ```bash
   pip install -r requirements.txt
   ```

2. **Import errors**
   ```bash
   # Make sure you're in the project root
   cd /path/to/atp-producer-jira
   python3 tests/test_use_case_coverage.py
   ```

3. **Assertion failures**
   - Check if the fix was applied correctly
   - Review `app/complex_cycle_time_strategy.py`
   - Ensure `_get_first_assignment_in_progress` checks for `previous_assignee`

## 📊 Regression Check

After running tests, verify:

- [x] **Use Case 1-4** still pass (no changes to these)
- [x] **Use Case 5** passes with new handoff test
- [x] **Use Case 6-10** still pass (no changes to these)
- [x] **Use Case 11** passes (new test)
- [x] **Strategy selection** tests still pass

## 🐛 Debugging Failed Tests

If a test fails:

```bash
# Run single test with verbose output
python3 -m unittest tests.test_use_case_coverage.TestUseCase05AssignedWhileAlreadyInProgress.test_assigned_while_in_progress_handoff -v

# Check what cycle time is being calculated
# Add debug prints in the test:
print(f"In Progress At: {cycle_time.in_progress_at}")
print(f"Done At: {cycle_time.done_at}")
print(f"Seconds: {cycle_time.seconds}")
print(f"Days: {cycle_time.seconds / 86400 if cycle_time.seconds else None}")
```

## 📝 Test Summary

| Use Case | Test Class | Status | Notes |
|----------|------------|--------|-------|
| 1 | TestUseCase01SimpleLinearProcess | ✅ | No changes |
| 2 | TestUseCase02ComplexMultiStageProcess | ✅ | No changes |
| 3 | TestUseCase03SingleAssigneeCleanAssignment | ✅ | No changes |
| 4 | TestUseCase04MultipleAssigneesSequentialHandoff | ✅ | No changes |
| **5** | TestUseCase05AssignedWhileAlreadyInProgress | ✅ | **FIXED** - Now tests handoff |
| 6 | TestUseCase06MultipleAssignmentPeriodsSamePerson | ✅ | No changes |
| 7 | TestUseCase07NeverReachedInProgress | ✅ | No changes |
| 8 | TestUseCase08InProgressButNeverDone | ✅ | No changes |
| 9 | TestUseCase09AssigneeNeverWorkedOnIt | ✅ | No changes |
| 10 | TestUseCase10StatusChangedDuringAcceptance | ✅ | No changes |
| **11** | TestUseCase11FirstAssignmentAfterStatusChange | ✅ | **NEW** test |

## 🚀 Quick Start

Just run this:

```bash
python3 tests/test_use_case_coverage.py
```

If you get module errors, install dependencies first:

```bash
pip install -r requirements.txt
python3 tests/test_use_case_coverage.py
```

---

**Status:** ✅ Tests updated and ready  
**Coverage:** 11/11 use cases (100%)  
**Total Tests:** 15  
**Changes:** 1 fixed, 1 added

