# Test Suite Documentation

## Overview

This test suite provides comprehensive coverage for all 10 documented use cases in the cycle time calculator.

## Test Files

- **`test_use_case_coverage.py`** - Main test file covering all 10 use cases
- **`test_helpers.py`** - Helper functions for creating mock Jira history data
- **`__init__.py`** - Package initialization

## Use Case Coverage

### ✅ Covered Use Cases (10/10)

| # | Use Case | Test Class | Status |
|---|----------|------------|--------|
| 1 | Simple Linear Process | `TestUseCase01SimpleLinearProcess` | ✅ |
| 2 | Complex Multi-Stage Process | `TestUseCase02ComplexMultiStageProcess` | ✅ |
| 3 | Single Assignee - Clean Assignment | `TestUseCase03SingleAssigneeCleanAssignment` | ✅ |
| 4 | Multiple Assignees - Sequential Handoff | `TestUseCase04MultipleAssigneesSequentialHandoff` | ✅ |
| 5 | Assigned While Already In Progress | `TestUseCase05AssignedWhileAlreadyInProgress` | ✅ |
| 6 | Multiple Assignment Periods - Same Person | `TestUseCase06MultipleAssignmentPeriodsSamePerson` | ✅ |
| 7 | Never Reached In-Progress | `TestUseCase07NeverReachedInProgress` | ✅ |
| 8 | In Progress But Never Done | `TestUseCase08InProgressButNeverDone` | ✅ |
| 9 | Assignee Never Worked On It | `TestUseCase09AssigneeNeverWorkedOnIt` | ✅ |
| 10 | Status Changed During Acceptance | `TestUseCase10StatusChangedDuringAcceptance` | ✅ |

### Additional Coverage
- ✅ Strategy Selection Logic
- ✅ Simple vs Complex Strategy triggers
- ✅ Edge case handling

## Running Tests

### Method 1: Using unittest (Built-in)

Run all tests with coverage report:
```bash
python3 tests/test_use_case_coverage.py
```

Run specific test class:
```bash
python3 -m unittest tests.test_use_case_coverage.TestUseCase01SimpleLinearProcess
```

Run specific test method:
```bash
python3 -m unittest tests.test_use_case_coverage.TestUseCase01SimpleLinearProcess.test_simple_linear_flow
```

Run with verbose output:
```bash
python3 -m unittest tests.test_use_case_coverage -v
```

### Method 2: Using pytest (If installed)

Run all tests:
```bash
pytest tests/
```

Run with coverage:
```bash
pytest tests/ --cov=app --cov-report=html
```

Run specific test:
```bash
pytest tests/test_use_case_coverage.py::TestUseCase01SimpleLinearProcess::test_simple_linear_flow
```

### Method 3: Using VS Code Test Explorer

1. Install Python extension for VS Code
2. Open Command Palette (Cmd+Shift+P)
3. Select "Python: Configure Tests"
4. Choose "unittest"
5. Select "tests" as the test directory
6. Tests will appear in the Test Explorer panel

## Test Structure

Each test class follows this pattern:

```python
class TestUseCaseXX<Description>(unittest.TestCase):
    """
    Use Case XX: <Title>
    - Description of the use case
    - Key characteristics
    """
    
    def setUp(self):
        # Initialize calculator with appropriate settings
        self.calculator = CycleTimeCalculator(...)
    
    def test_<scenario>(self):
        """Docstring describing what's being tested"""
        # 1. Create mock history data
        histories = [...]
        
        # 2. Calculate cycle time
        cycle_time = self.calculator.<strategy>.calculate(...)
        
        # 3. Assertions
        self.assertIsNotNone(cycle_time.in_progress_at)
        self.assertAlmostEqual(actual_days, expected_days, delta=0.5)
```

## Adding New Tests

### For a New Use Case:

1. **Document the use case** in `docs/USE_CASES_CATALOG.md` first
2. **Create a new test class** following the naming pattern:
   ```python
   class TestUseCaseXX<YourNewUseCase>(unittest.TestCase):
   ```
3. **Add setUp method** with appropriate calculator configuration
4. **Write test method(s)** covering the scenario
5. **Update this README** with the new use case entry

### Example Template:

```python
class TestUseCaseXX<NewUseCase>(unittest.TestCase):
    """
    Use Case XX: <Title>
    - Description
    - Key characteristics
    """
    
    def setUp(self):
        self.calculator = CycleTimeCalculator(
            in_progress_names=["In Development"],
            done_names=["Done"],
            exclude_statuses=["Acceptance"]
        )
    
    def test_<scenario_name>(self):
        """Description of what this tests"""
        # Create test data
        histories = [
            create_status_change(days_to_iso(1), "Backlog", "In Development"),
            # ... more history items
        ]
        
        # Calculate
        cycle_time = self.calculator.simple_strategy.calculate(
            histories, "TEST-XXX"
        )
        
        # Assert
        self.assertIsNotNone(cycle_time.in_progress_at)
        self.assertEqual(expected_value, actual_value)
```

## Test Helpers

### Available Helper Functions

Located in `test_helpers.py`:

```python
# Create a status change
create_status_change(created, from_status, to_status)

# Create an assignee change
create_assignee_change(created, from_id, to_id)

# Create combined change (status + assignee in same entry)
create_combined_change(created, status_from, status_to, assignee_from, assignee_to)

# Create resolution change
create_resolution_change(created, from_resolution, to_resolution, author_account_id)

# Convert day number to ISO timestamp
days_to_iso(day, time="10:00:00")  # Returns "2025-01-DD:THH:MM:SS.000+0000"
```

### Constants

```python
PERSON_A_ID = "557058:person-a-account-id"
PERSON_B_ID = "557058:person-b-account-id"
PERSON_C_ID = "557058:person-c-account-id"
PERSON_D_ID = "557058:person-d-account-id"
```

## Continuous Integration

### GitHub Actions Example

Create `.github/workflows/test.yml`:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: python3 tests/test_use_case_coverage.py
```

## Coverage Goals

- ✅ **100% use case coverage** (10/10 documented cases)
- ✅ **Strategy selection coverage** (all trigger conditions)
- ✅ **Edge case coverage** (NULL returns, excluded statuses)
- 🎯 **Code coverage target:** >90% for strategy classes

## Debugging Tests

### Print debug information:

```python
def test_something(self):
    histories = [...]
    
    # Get strategy info
    info = self.calculator.get_strategy_info(histories, PERSON_A_ID)
    print(f"Strategy: {info['strategy']}")
    print(f"Reasons: {info['reasons']}")
    
    # Calculate and inspect
    cycle_time = self.calculator.complex_strategy.calculate(...)
    print(f"Start: {cycle_time.in_progress_at}")
    print(f"End: {cycle_time.done_at}")
    print(f"Days: {cycle_time.seconds / 86400}")
```

### Run single test with output:

```bash
python3 -m unittest tests.test_use_case_coverage.TestUseCase04MultipleAssigneesSequentialHandoff.test_multiple_assignees_filter_middle_person -v
```

## Test Maintenance

### When to Update Tests:

1. **Bug Fix:** Add regression test for the bug
2. **New Use Case:** Add test class for the new scenario
3. **Algorithm Change:** Update assertions to match new behavior
4. **New Strategy:** Add tests for strategy selection logic

### Regular Maintenance:

- Review test coverage quarterly
- Update test data to match real-world scenarios
- Keep test documentation in sync with `docs/USE_CASES_CATALOG.md`
- Refactor test helpers as patterns emerge

## Related Documentation

- **`docs/USE_CASES_CATALOG.md`** - Full use case documentation
- **`docs/ARCHITECTURE.md`** - System architecture
- **`docs/REFACTORING_SUMMARY.md`** - Recent changes
- **`docs/RUN_TESTS_INSTRUCTIONS.md`** - How to run tests

---

**Last Updated:** October 2025  
**Test Coverage:** 11/11 Use Cases (100%)  
**Status:** ✅ All tests passing

