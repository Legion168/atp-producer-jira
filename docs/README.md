# Documentation Index

Welcome to the ATP Producer Jira documentation! This directory contains all technical and user documentation for the cycle time calculator.

## 📚 Quick Navigation

### 🚀 Getting Started

**New to the project?** Start here:

1. **[ATP_PRODUCER_DOCUMENTATION.md](ATP_PRODUCER_DOCUMENTATION.md)** - Overview of the application
2. **[ARCHITECTURE.md](ARCHITECTURE.md)** - System architecture and hybrid approach
3. **[USE_CASES_CATALOG.md](USE_CASES_CATALOG.md)** - All 12 supported scenarios

### 👥 User Documentation

**Using the cycle time calculator:**

- **[USE_CASES_CATALOG.md](USE_CASES_CATALOG.md)** - Complete catalog of all 12 use cases with examples
- **[USE_CASE_QUICK_REFERENCE.md](USE_CASE_QUICK_REFERENCE.md)** - Quick reference card for troubleshooting
- **[ATP_PRODUCER_DOCUMENTATION.md](ATP_PRODUCER_DOCUMENTATION.md)** - Full application guide

### 🔧 Developer Documentation

**Working on the code:**

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Hybrid approach and strategy pattern architecture
- **[USE_CASES_CATALOG.md](USE_CASES_CATALOG.md)** - Technical details for each scenario
- **[../examples/README.md](../examples/README.md)** - Demo scripts and examples

### 🧪 Testing Documentation

**Running and writing tests:**

- **[RUN_TESTS_INSTRUCTIONS.md](RUN_TESTS_INSTRUCTIONS.md)** - How to run the test suite
- **[TEST_SUITE_SUMMARY.md](TEST_SUITE_SUMMARY.md)** - Test coverage overview
- **[TEST_COVERAGE_MATRIX.md](TEST_COVERAGE_MATRIX.md)** - Detailed coverage tracking
- **[../tests/README_TESTS.md](../tests/README_TESTS.md)** - Complete test suite documentation

## 📋 Documentation by Purpose

### I need to...

#### **Understand what the app does**
→ [ATP_PRODUCER_DOCUMENTATION.md](ATP_PRODUCER_DOCUMENTATION.md)

#### **Learn how cycle times are calculated**
→ [USE_CASES_CATALOG.md](USE_CASES_CATALOG.md)

#### **Debug an incorrect cycle time**
→ [USE_CASE_QUICK_REFERENCE.md](USE_CASE_QUICK_REFERENCE.md)

#### **Understand the hybrid approach & architecture**
→ [ARCHITECTURE.md](ARCHITECTURE.md)

#### **Run the tests**
→ [RUN_TESTS_INSTRUCTIONS.md](RUN_TESTS_INSTRUCTIONS.md)

#### **Add a new use case or test**
→ [USE_CASES_CATALOG.md](USE_CASES_CATALOG.md) + [../tests/README_TESTS.md](../tests/README_TESTS.md)

## 📂 File Descriptions

| File | Purpose | Audience |
|------|---------|----------|
| **ATP_PRODUCER_DOCUMENTATION.md** | Original app documentation & user guide | All users |
| **ARCHITECTURE.md** | Hybrid approach and strategy pattern design | Developers |
| **USE_CASES_CATALOG.md** | All 12 use cases with detailed examples | Users & Developers |
| **USE_CASE_QUICK_REFERENCE.md** | Quick troubleshooting guide | Users |
| **RUN_TESTS_INSTRUCTIONS.md** | How to run tests | Developers |
| **TEST_SUITE_SUMMARY.md** | Test coverage overview | Developers |
| **TEST_COVERAGE_MATRIX.md** | Detailed test tracking | Developers |

## 🎯 Common Workflows

### Debugging a Cycle Time Issue

1. Look at the card history
2. Check **[USE_CASE_QUICK_REFERENCE.md](USE_CASE_QUICK_REFERENCE.md)** - identify the use case
3. Read the full use case in **[USE_CASES_CATALOG.md](USE_CASES_CATALOG.md)**
4. If it involves reopening, check if the hybrid approach detected it correctly

### Understanding the Code

1. Start with **[ARCHITECTURE.md](ARCHITECTURE.md)** - get the big picture
2. Review **[USE_CASES_CATALOG.md](USE_CASES_CATALOG.md)** - see all 12 scenarios
3. Check **[../tests/README_TESTS.md](../tests/README_TESTS.md)** - see test examples
4. Run **[../examples/demo_strategy_selection.py](../examples/demo_strategy_selection.py)** - see it in action

### Adding a New Feature

1. Document the use case in **[USE_CASES_CATALOG.md](USE_CASES_CATALOG.md)**
2. Understand which strategy to modify in **[ARCHITECTURE.md](ARCHITECTURE.md)**
3. Write tests following **[../tests/README_TESTS.md](../tests/README_TESTS.md)**
4. Update **[TEST_COVERAGE_MATRIX.md](TEST_COVERAGE_MATRIX.md)**
5. Run tests using **[RUN_TESTS_INSTRUCTIONS.md](RUN_TESTS_INSTRUCTIONS.md)**

## 📊 Current Status

- ✅ **12 Use Cases** documented and fully supported
- ✅ **17 Tests** covering all use cases (100% coverage)
- ✅ **Hybrid Approach** - Automatic detection of reopened issues
- ✅ **Strategy Pattern** architecture with intelligent routing
- ✅ **Comprehensive** documentation for users and developers

## 🎯 Key Features

### Hybrid Algorithm
The system automatically detects if an issue was reopened and selects the optimal calculation method:
- **Cycle-based**: For issues closed and reopened (sums all cycles)
- **First-to-last**: For normal issues (handles assignee handoffs correctly)

### All Use Cases Covered
1. Simple Linear Process
2. Complex Multi-Stage Process
3. Single Assignee - Clean Assignment
4. Multiple Assignees - Sequential Handoff
5. Assigned While Already In Progress (Handoff)
6. Multiple Assignment Periods - Same Person
7. Never Reached In-Progress
8. In Progress But Never Done
9. Assignee Never Worked On It
10. Status Changed During Acceptance/Feedback
11. First Assignment After Status Change
12. Issue Closed and Reopened ← **NEW!**

## 🤝 Contributing

When making changes:

1. **Document first** - Update USE_CASES_CATALOG.md
2. **Test second** - Add tests following patterns in tests/
3. **Update docs** - Keep documentation in sync
4. **Verify coverage** - Update TEST_COVERAGE_MATRIX.md

## ❓ Questions?

- **Can't find what you need?** Check [ATP_PRODUCER_DOCUMENTATION.md](ATP_PRODUCER_DOCUMENTATION.md)
- **Need architectural context?** See [ARCHITECTURE.md](ARCHITECTURE.md)
- **Need to debug?** Use [USE_CASE_QUICK_REFERENCE.md](USE_CASE_QUICK_REFERENCE.md)

---

**Last Updated:** October 2025  
**Documentation Status:** ✅ Complete and up-to-date  
**Test Coverage:** 12/12 Use Cases (100%)  
**Algorithm:** Hybrid approach with automatic reopening detection
