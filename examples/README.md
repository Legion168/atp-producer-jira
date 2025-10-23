# Examples

This folder contains demonstration scripts and examples for the ATP Producer cycle time calculator.

## 📁 Contents

### `demo_strategy_selection.py`

**Purpose:** Interactive demonstration of how the `CycleTimeCalculator` automatically selects the appropriate strategy based on issue complexity.

**What it does:**
- Creates mock Jira history data for different scenarios
- Shows which strategy is selected (Simple vs Complex)
- Explains the reasons for each selection
- Demonstrates with 4 different test cases

**How to run:**
```bash
# Activate your virtual environment first
source venv/bin/activate  # or your venv path

# Run the demo
python3 examples/demo_strategy_selection.py
```

**Expected output:**
```
╔══════════════════════════════════════════════════════════════════════════════╗
║                    CYCLE TIME STRATEGY SELECTION DEMO                        ║
╚══════════════════════════════════════════════════════════════════════════════╝

================================================================================
  Test 1: Simple Clean Process (No Assignee Filter)
================================================================================

📊 History Analysis:
   • Assignee changes: 0
   • Status changes: 2
   • Has assignee filter: False

✨ Selected Strategy: SimpleCycleTimeStrategy
📝 Reasons: Clean linear process (≤ 2 assignee changes, ≤ 5 status changes)
...
```

**Use cases:**
- ✅ Understanding strategy selection logic
- ✅ Debugging why a certain strategy was chosen
- ✅ Learning how the calculator works
- ✅ Demo for team members

**Note:** This is a **demonstration script**, not an automated test. For actual tests, see the `tests/` folder.

---

## 🔗 Related Documentation

- **[../tests/README_TESTS.md](../tests/README_TESTS.md)** - Automated test suite
- **[../docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md)** - System architecture
- **[../docs/USE_CASES_CATALOG.md](../docs/USE_CASES_CATALOG.md)** - All use cases

---

## 📝 Adding New Examples

When adding new example scripts:

1. **Name:** Use `demo_*.py` or `example_*.py` prefix
2. **Purpose:** Add clear docstring explaining what it demonstrates
3. **Documentation:** Update this README
4. **Dependencies:** Document required packages
5. **Output:** Show expected output in the README

### Example Template

```python
#!/usr/bin/env python3
"""
Demo: [Brief description]

This script demonstrates [what it demonstrates].
"""

def main():
    """Run the demonstration."""
    print("Starting demo...")
    # Your demo code here
    print("Demo complete!")

if __name__ == "__main__":
    main()
```

---

**Last Updated:** October 2025  
**Examples:** 1 (demo_strategy_selection.py)

