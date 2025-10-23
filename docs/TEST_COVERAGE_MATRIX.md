# Test Coverage Matrix

## Overview

This document maps each use case to its test coverage, making it easy to track what's tested and identify gaps.

## Coverage Matrix

| Use Case # | Use Case Name | Test Class | Test Methods | Status | Notes |
|------------|---------------|------------|--------------|--------|-------|
| **1** | Simple Linear Process | `TestUseCase01SimpleLinearProcess` | `test_simple_linear_flow` | ✅ 100% | Tests basic Backlog→Dev→Review→Done flow |
| **2** | Complex Multi-Stage Process | `TestUseCase02ComplexMultiStageProcess` | `test_complex_multi_stage_flow` | ✅ 100% | Tests >5 status changes with reversals |
| **3** | Single Assignee - Clean Assignment | `TestUseCase03SingleAssigneeCleanAssignment` | `test_single_assignee_clean_flow` | ✅ 100% | Tests assignee filter with clean handoff |
| **4** | Multiple Assignees - Sequential Handoff | `TestUseCase04MultipleAssigneesSequentialHandoff` | `test_multiple_assignees_filter_middle_person` | ✅ 100% | Tests A→B→C handoff, filtering for B |
| **5** | Assigned While Already In Progress | `TestUseCase05AssignedWhileAlreadyInProgress` | `test_assigned_while_in_progress_handoff` | ✅ 100% | Tests handoff from Person A to B while in progress |
| **6** | Multiple Assignment Periods - Same Person | `TestUseCase06MultipleAssignmentPeriodsSamePerson` | `test_multiple_assignment_periods` | ✅ 100% | Tests person assigned→unassigned→reassigned |
| **7** | Never Reached In-Progress | `TestUseCase07NeverReachedInProgress` | `test_never_in_progress` | ✅ 100% | Tests direct Backlog→Done transition |
| **8** | In Progress But Never Done | `TestUseCase08InProgressButNeverDone` | `test_in_progress_not_done` | ✅ 100% | Tests work in progress (WIP) |
| **9** | Assignee Never Worked On It | `TestUseCase09AssigneeNeverWorkedOnIt` | `test_wrong_assignee_filter` | ✅ 100% | Tests filtering by unrelated assignee |
| **10** | Status Changed During Acceptance/Feedback | `TestUseCase10StatusChangedDuringAcceptance` | `test_excluded_status_time_not_counted`, `test_feedback_status_excluded_with_reassignment` | ✅ 100% | Tests excluded status time (Acceptance & Feedback) |
| **11** | First Assignment After Status Change | `TestUseCase11FirstAssignmentAfterStatusChange` | `test_first_assignment_after_status_change` | ✅ 100% | Tests unassigned→in-progress→assigned (uses status time) |
| **12** | Issue Closed and Reopened | `TestUseCase12IssueClosedAndReopened` | `test_issue_closed_and_reopened` | ✅ 100% | Tests reopened issues with cycle tracking |
| **13** | Author of Transitions Without Formal Assignment | `TestUseCase13AuthorOfTransitionsWithoutAssignment` | `test_author_of_transitions_without_assignment`, `test_different_author_excluded` | ✅ 100% | Tests author-based attribution without assignment events |
| **14** | Overlapping Impediment and Excluded Time | `TestUseCase14OverlappingImpedimentAndExcludedTime` | `test_overlapping_impediment_and_excluded_time` | ✅ 100% | Tests overlap handling to prevent negative cycle time |

## Strategy Selection Coverage

| Trigger Condition | Test Class | Test Method | Status |
|-------------------|------------|-------------|--------|
| Simple flow (default) | `TestStrategySelection` | `test_simple_strategy_selected_for_simple_flow` | ✅ |
| Assignee filter provided | `TestStrategySelection` | `test_complex_strategy_selected_for_assignee_filter` | ✅ |
| > 2 assignee changes | `TestStrategySelection` | `test_complex_strategy_selected_for_many_assignee_changes` | ✅ |
| > 5 status changes | `TestStrategySelection` | `test_complex_strategy_selected_for_many_status_changes` | ✅ |

## Code Coverage by Component

### CycleTimeCalculator
- ✅ `__init__` - Initialization
- ✅ `calculate_cycle_times` - Main calculation loop (via all tests)
- ✅ `_select_strategy` - Strategy selection (via TestStrategySelection)
- ✅ `get_strategy_info` - Debug information (via multiple tests)

### SimpleCycleTimeStrategy
- ✅ `calculate` - Main calculation
- ✅ `_find_first_in_progress` - Find work start
- ✅ `_find_first_done` - Find completion
- ✅ `_calculate_excluded_time` - Exclude status periods

### ComplexCycleTimeStrategy
- ✅ `calculate` - Main calculation
- ✅ `_get_assignee_periods` - Track assignment periods
- ✅ `_is_in_assignee_period` - Period checking
- ✅ `_is_author_of_transitions` - Check authorship of workflow transitions (Use Case 13)
- ✅ `_find_first_in_progress` - Find work start with period filter
- ✅ `_get_first_assignment_in_progress` - Handle late assignments
- ✅ `_check_leads_to_non_work` - Validate work transitions
- ✅ `_find_first_completion` - Find completion with period filter
- ✅ `_check_status_completion` - Status-based completion
- ✅ `_check_resolution_completion` - Resolution-based completion
- ✅ `_calculate_excluded_time` - Exclude status periods

### CycleTimeStrategy (Base Class)
- ✅ `__init__` - Initialization
- ✅ `should_use_complex_strategy` - Decision logic
- ✅ `_parse_jira_datetime` - Date parsing (via all tests)
- ✅ `_calculate_excluded_time` - Exclude status periods (via both strategies)

## Test Scenarios by Category

### ✅ Basic Flows (2 scenarios)
1. Simple linear workflow
2. Complex multi-stage workflow

### ✅ Assignee Filtering (5 scenarios)
3. Single assignee clean flow
4. Multiple assignees with handoff
5. Late assignment to in-progress issue (handoff)
6. Re-assignment of same person
11. First assignment after status change

### ✅ Edge Cases (3 scenarios)
7. Never reached in-progress
8. In progress but not done
9. Wrong assignee filter

### ✅ Time Exclusions (1 scenario)
10. Excluded status time calculation (Acceptance & Feedback)

### ✅ Reopened Issues (1 scenario)
12. Issue closed and reopened (cycle tracking)

### ✅ Strategy Selection (4 scenarios)
- Simple strategy triggers
- Complex strategy triggers (3 conditions)

## Coverage Statistics

```
Total Use Cases Documented:     14
Total Use Cases Tested:         14
Coverage Percentage:            100%

Total Test Classes:             15 (14 use cases + 1 strategy selection)
Total Test Methods:             20
Estimated Lines of Test Code:  ~700
```

## Test Execution Matrix

### Quick Test Commands

Run all tests:
```bash
python3 tests/test_use_case_coverage.py
```

Run specific use case:
```bash
# Use Case 1
python3 -m unittest tests.test_use_case_coverage.TestUseCase01SimpleLinearProcess

# Use Case 4
python3 -m unittest tests.test_use_case_coverage.TestUseCase04MultipleAssigneesSequentialHandoff
```

Run by category (if using pytest with markers):
```bash
pytest -m use_case
pytest -m simple_strategy
pytest -m complex_strategy
pytest -m edge_case
```

## Gaps and Future Coverage

### Current Gaps
- ⚠️ **Integration tests** with real Jira client (currently all unit tests)
- ⚠️ **Performance tests** for large histories
- ⚠️ **Stress tests** with extreme edge cases

### Planned Additions
- [ ] Integration tests with mock Jira API
- [ ] Performance benchmarks
- [ ] Property-based testing (hypothesis)
- [ ] Mutation testing
- [ ] Test data generators for fuzzing

## Coverage Improvement Plan

### Phase 1: Complete Basic Coverage ✅
- ✅ All 10 use cases covered
- ✅ Strategy selection covered
- ✅ Edge cases covered

### Phase 2: Integration Testing (Future)
- [ ] Mock Jira API responses
- [ ] Test with real-world history data
- [ ] End-to-end workflow tests

### Phase 3: Advanced Testing (Future)
- [ ] Property-based testing
- [ ] Performance profiling
- [ ] Load testing with large datasets
- [ ] Concurrency testing

## Regression Test Tracking

When bugs are found, add them here:

| Date | Bug Description | Related Use Case | Test Added | Status |
|------|----------------|------------------|------------|--------|
| [Date] | Assignee filtering used wrong dates | Use Case 3, 4, 5 | ✅ All | ✅ Fixed |
| | | | | |

## Test Maintenance Log

| Date | Change | Affected Tests | Status |
|------|--------|----------------|--------|
| [Date] | Initial test suite creation | All | ✅ Complete |
| | | | |

## Quality Metrics

### Test Quality Indicators
- ✅ **Clear test names** - All tests have descriptive names
- ✅ **Good documentation** - All tests have docstrings
- ✅ **Isolated tests** - Each test is independent
- ✅ **Fast execution** - All tests run in <1 second
- ✅ **Deterministic** - Tests always produce same results

### Coverage Goals
- ✅ **Use Case Coverage:** 100% (10/10)
- ✅ **Strategy Coverage:** 100% (both strategies tested)
- 🎯 **Code Coverage:** Target >90% (run `pytest --cov` to measure)
- 🎯 **Branch Coverage:** Target >85%

## Continuous Monitoring

### Regular Reviews
- **Weekly:** Check for new use cases to add
- **Monthly:** Review test execution times
- **Quarterly:** Update coverage matrix
- **Annually:** Refactor and optimize test suite

### Metrics to Track
1. Number of use cases vs tests
2. Test execution time
3. Code coverage percentage
4. Number of flaky tests
5. Time to add new test

## How to Use This Matrix

### When Adding a New Use Case:
1. Document in `USE_CASES_CATALOG.md`
2. Add row to this matrix with ⚠️ status
3. Create test class and methods
4. Update status to ✅ when complete
5. Update coverage statistics

### When Fixing a Bug:
1. Add to Regression Test Tracking table
2. Create test that reproduces bug
3. Fix bug
4. Verify test passes
5. Update affected use case coverage

### When Reviewing Coverage:
1. Check this matrix for gaps
2. Identify uncovered scenarios
3. Prioritize based on risk/frequency
4. Add tests for high-priority gaps
5. Update matrix

---

**Last Updated:** March 2025  
**Coverage Status:** ✅ 100% (13/13 use cases, 19 tests)  
**Next Review:** As new use cases are discovered  
**Maintainer:** Development Team

