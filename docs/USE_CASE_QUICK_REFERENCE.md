# Cycle Time Use Cases - Quick Reference Card

## 🎯 Quick Identification Guide

| Symptoms | Likely Use Case | Strategy | Action |
|----------|----------------|----------|--------|
| Simple flow, no filter | **#1: Simple Linear** | Simple | ✅ Working correctly |
| Many status changes, no filter | **#2: Complex Multi-Stage** | Complex | ✅ Working correctly |
| Single assignee with filter | **#3: Clean Assignment** | Complex | ✅ Fixed in v2.0 |
| Multiple people worked on it | **#4: Sequential Handoff** | Complex | ✅ Fixed in v2.0 |
| Assigned while in progress | **#5: Late Assignment** | Complex | ✅ Fixed in v2.0 |
| Assigned multiple times | **#6: Re-assignment** | Complex | ⚠️ Uses first period |
| Never reached in-progress | **#7: No Work Started** | Both | ⚠️ Returns NULL |
| Still in progress | **#8: Not Completed** | Both | ⚠️ Returns NULL |
| Wrong assignee filter | **#9: Never Assigned** | Complex | ⚠️ Returns NULL |
| Time in Acceptance counted | **#10: Excluded Status** | Both | ✅ Time excluded |

## 🔍 Quick Diagnosis

### Issue: Cycle time too long?
```
☑ Check: Multiple assignees? → Filter by specific person (Use Case #4)
☑ Check: Acceptance time counted? → Add to exclude_statuses (Use Case #10)
☑ Check: Many status changes? → Review for On Hold periods (Use Case #2)
```

### Issue: Wrong start date?
```
☑ Check: No assignee filter? → Add filter (Use Case #3)
☑ Check: Multiple people before target? → Expected behavior (Use Case #4)
☑ Check: Assigned while in progress? → Should use assignment date (Use Case #5)
```

### Issue: No cycle time (NULL)?
```
☑ Check: Ever in progress? → Use Case #7
☑ Check: Ever completed? → Use Case #8
☑ Check: Correct assignee? → Use Case #9
```

## 🏗️ Strategy Selection Logic

```
Has assignee filter? → Complex
> 2 assignee changes? → Complex
> 5 status changes?  → Complex
Otherwise            → Simple
```

## 📊 Common Patterns

### Pattern A: Standard Development
```
Backlog → In Dev → Done
Strategy: Simple
```

### Pattern B: With Review Stage
```
Backlog → In Dev → Review → Done
Strategy: Simple (if ≤5 changes)
```

### Pattern C: With Acceptance
```
Backlog → In Dev → Review → Acceptance → Done
Strategy: Complex (exclude Acceptance time)
```

### Pattern D: Team Handoff
```
Person A: Backlog → In Dev
Person B: In Dev → Review → Done
Strategy: Complex (filter by person)
```

### Pattern E: Back and Forth
```
In Dev → Review → In Dev → Review → Done
Strategy: Complex (>5 changes)
```

## 🚨 Common Mistakes

| Mistake | Result | Fix |
|---------|--------|-----|
| No assignee filter with team work | Counts all team time | Add assignee filter |
| Acceptance not excluded | Too long cycle time | Add to exclude_statuses |
| Wrong assignee selected | NULL or wrong dates | Check assignee history |
| Filtering on reporter not assignee | Wrong person's time | Use assignee field |

## 📝 Quick Test Commands

```python
# Get strategy info for debugging
info = calculator.get_strategy_info(histories, assignee_id)
print(f"Strategy: {info['strategy']}")
print(f"Reasons: {info['reasons']}")

# Check if issue matches expected pattern
print(f"Assignee changes: {info['assignee_changes']}")
print(f"Status changes: {info['status_changes']}")
```

## 🔗 Full Documentation

For detailed examples and complete use case descriptions, see:
→ **USE_CASES_CATALOG.md**

For architecture and technical details, see:
→ **ARCHITECTURE.md**

For recent changes and migration notes, see:
→ **REFACTORING_SUMMARY.md**

---

**Print this page** for quick reference while analyzing issues!

