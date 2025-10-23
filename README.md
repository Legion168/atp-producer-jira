# ATP Producer (Jira Throughput & Cycle Time)

Visualize per-person ATP metrics from Jira:
- Total issues transitioned to "Done" within a time window (throughput)
- Average/median cycle time from first "In Progress" to "Done"
- Assignee-specific cycle time tracking with intelligent strategy selection
- Optional subtask filtering to focus on main work items

## Setup

1. Ensure Python 3.10+.
2. Create and populate `.env` using `.env.example`:
   - `JIRA_BASE_URL` like `https://your-domain.atlassian.net`
   - `JIRA_EMAIL` Atlassian account email
   - `JIRA_API_TOKEN` from Atlassian API tokens
3. Install deps:
```bash
pip install -r requirements.txt
```

## Run
```bash
streamlit run app/main.py
```

## Features

### Cycle Time Metrics
The application provides **two complementary metrics** for comprehensive analysis:

1. **Active Cycle Time** (Team Performance)
   - Active work time excluding waiting states (Acceptance, Feedback) and impediment periods
   - Measures actual productive work time
   - Use for process improvement and capacity planning

2. **Impediment Time** (Blocking Analysis)
   - Tracks time spent flagged as "Impediment"
   - Identifies systemic bottlenecks
   - Use for process optimization

### Intelligent Cycle Time Calculation
The application uses a **strategy pattern** to automatically select the best algorithm based on issue complexity:

- **Simple Strategy**: Fast calculation for clean, linear workflows
- **Complex Strategy**: Accurate tracking for multi-assignee or complex workflows with proper period tracking
- **Hybrid Approach**: Automatically detects reopened issues and adjusts calculation method

### Assignee Filtering
When filtering by assignee, the calculator:
- ✅ Tracks only the time when that person was assigned
- ✅ Handles handoffs between team members
- ✅ Manages edge cases (assigned while in progress, re-assignments)
- ✅ Detects work via authorship when no formal assignment exists
- ✅ Excludes time in specified statuses (e.g., "Acceptance", "Feedback")

## Documentation

### User Documentation
- **[USE_CASES_CATALOG.md](docs/USE_CASES_CATALOG.md)** - Complete catalog of all supported cycle time scenarios with examples
- **[USE_CASE_QUICK_REFERENCE.md](docs/USE_CASE_QUICK_REFERENCE.md)** - Quick reference card for identifying and troubleshooting issues

### Technical Documentation
- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** - Detailed architecture documentation and design decisions
- **[REFACTORING_SUMMARY.md](docs/REFACTORING_SUMMARY.md)** - Recent changes, bug fixes, and migration guide
- **[COMPLETE_PROJECT_SUMMARY.md](docs/COMPLETE_PROJECT_SUMMARY.md)** - Complete overview of all changes
- **[CHANGES_SUMMARY.md](docs/CHANGES_SUMMARY.md)** - Detailed changes with git commit templates

### Test Documentation
- **[TEST_SUITE_SUMMARY.md](docs/TEST_SUITE_SUMMARY.md)** - Test coverage summary and how to run tests
- **[TEST_COVERAGE_MATRIX.md](docs/TEST_COVERAGE_MATRIX.md)** - Detailed test coverage tracking matrix
- **[RUN_TESTS_INSTRUCTIONS.md](docs/RUN_TESTS_INSTRUCTIONS.md)** - How to run the test suite
- **[tests/README_TESTS.md](tests/README_TESTS.md)** - Complete test suite documentation

### Bug Fixes & History
- **[BUGFIX_USE_CASE_5.md](docs/BUGFIX_USE_CASE_5.md)** - Use Case 5 bug fix documentation
- **[ATP_PRODUCER_DOCUMENTATION.md](docs/ATP_PRODUCER_DOCUMENTATION.md)** - Original application documentation

### Examples & Demos
- **[examples/demo_strategy_selection.py](examples/demo_strategy_selection.py)** - Interactive demo of strategy selection
- **[examples/README.md](examples/README.md)** - Examples documentation

## Notes
- The app uses Jira Cloud REST API and Agile API to query issues on a board and inspect changelogs for status transitions.
- Permissions: The API token must have access to the board's project(s).
- Timeframe filter uses year+quarter to compute start/end dates.
- Cycle time calculation automatically adapts to issue complexity - no configuration needed.
