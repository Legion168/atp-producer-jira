# ATP Producer - Jira Throughput & Cycle Time Analysis Tool

## 📋 Overview

ATP Producer is a Python-based web application that analyzes team performance by calculating **ATP (Average Throughput Performance)** metrics from Jira data. The tool provides comprehensive insights into team productivity, cycle times, and work completion patterns across different time periods.

## 🎯 Purpose

As a Team Leader, you can use this tool to:
- **Track Team Performance**: Monitor throughput and cycle time improvements
- **Set Goals**: Establish targets like "Improve throughput by 20%"
- **Measure Impact**: Quantify the effect of process improvements (e.g., adopting Cursor for pair-programming/AI boost)
- **Quarterly Analysis**: Compare performance across different quarters
- **Identify Trends**: Spot patterns in team productivity over time

## 🏗️ Architecture

### Technology Stack
- **Frontend**: Streamlit (Python web framework)
- **Backend**: Python with Jira REST API integration
- **Data Visualization**: Plotly for interactive charts
- **Data Processing**: Pandas, NumPy for calculations
- **Authentication**: Jira API tokens

### Key Components
- `app/main.py`: Main Streamlit application and UI
- `app/jira_client.py`: Jira API client and data fetching
- `app/metrics.py`: ATP calculation logic and metrics
- `app/config.py`: Configuration management

## 📊 ATP Calculation Rules

### Definition
**ATP (Average Throughput Performance)** is calculated using two primary metrics:

1. **Throughput**: Total number of tasks, stories, or bugs transitioned to "Done" status within a specific time interval
2. **Cycle Time**: Total time elapsed from when work starts on an issue (first transition to "In Progress") until it is marked as "Done"

### Throughput Calculation

#### What Counts as "Completed"
- Issues with **resolution** set to any valid value (not "Won't Do" or "None")
- Issues that were **closed** within the specified time window
- Only issues assigned to the selected person (if specified)

#### What's Excluded
- Issues with resolution "Won't Do" (unless set by the same person being analyzed)
- Issues with incomplete status transition data
- Issues without valid "In Progress" start dates
- Subtasks (when "Include subtasks in ATP calculation" checkbox is unchecked)

### Cycle Time Calculation

The application provides **two complementary cycle time metrics**:

#### 1. Active Cycle Time (Team Performance)
- **Definition**: Active work time excluding waiting states and impediment periods
- **Excludes**: Time in Acceptance, Feedback, and impediment periods
- **Use for**: Team velocity measurement, process improvement
- **Formula**: `(total_seconds - excluded_seconds - impediment_seconds) / 86400` days

#### 2. Impediment Time (Blocking Analysis)
- **Definition**: Time spent flagged as "Impediment"
- **Tracks**: "Flagged" field changes in Jira changelog
- **Use for**: Identifying systemic bottlenecks, process optimization
- **Formula**: `impediment_seconds / 86400` days

#### Start of Work ("In Progress")
The cycle time starts when an issue transitions to any of the configured "In Progress" statuses:
- **Default**: "In Development", "Failed/Blocked", "Analysis"
- **Configurable**: Can be customized in the UI

#### End of Work ("Done")
The cycle time ends when an issue is marked as completed:
- **Resolution-based**: When resolution is set to a valid value
- **Status-based**: When status changes to "Closed" (configurable)

#### Special Rules & Edge Cases

##### 1. Assignee-Specific Filtering
- **"In Progress" Start**: Only transitions by the target assignee count as work start
- **"Done" End**: Any valid completion by anyone counts (handles work handoffs)

##### 2. Automation Handling
- If automation moves an issue to "In Progress" and the target person takes action within 1 hour, the automation time is used as the start
- This accounts for automated workflows followed by human intervention

##### 3. "Pick Up and Put Back" Detection
- If a person moves an issue to "In Progress" and immediately moves it back to "Backlog" within 1 hour, this doesn't count as work start
- Prevents false cycle time calculations from brief status changes

##### 4. Multiple Work Periods
- For issues that are reopened and retaken, cycle time is calculated from the **most recent** "In Progress" transition that led to the **final** completion
- This ensures cycle time reflects the actual work period, not the total time including gaps

##### 5. "Won't Do" Resolution Handling
- If someone **other than** the target assignee sets resolution to "Won't Do", this completion is ignored
- If the **target assignee** sets resolution to "Won't Do", it still counts as their completion
- This handles external cancellations vs. self-cancellations appropriately

##### 6. Subtask Filtering
- **Default Behavior**: All issue types (including subtasks) are included in ATP calculations
- **Filtering Option**: Use the "Include subtasks in ATP calculation" checkbox to exclude subtasks
- **When Unchecked**: JQL queries automatically exclude issues with `issuetype = Sub-task`
- **Use Cases**: 
  - Exclude subtasks when you want to focus on main work items (stories, tasks, bugs)
  - Include subtasks when you want comprehensive throughput metrics including granular work breakdown
- **Impact**: Affects both throughput counts and cycle time calculations

##### 7. Resolution Clearing
- When resolution is cleared (set to "None"), this doesn't count as completion
- Only non-empty, non-"None" resolutions are considered valid completions

##### 8. Assignee Changes to "In Progress" Issues
- When a person gets assigned to an issue that is already in "In Progress" status, the assignment time counts as the start of work
- This handles scenarios where work is handed off or reassigned mid-process
- Example: Issue is in "In Development" status, then person A gets assigned → assignment time becomes the "In Progress" start for person A

##### 9. "In Progress" Date Overwrite Rules
- **Backlog Overwrite**: When a person moves an issue from "Backlog" to any "In Progress" status, this overwrites any previous "In Progress" date
- **No Other Overwrites**: Transitions from other statuses (like "Feedback", "To Do", "Analysis") to "In Progress" do NOT overwrite the original date
- **Purpose**: Ensures that only significant work starts (from Backlog) reset the cycle time, while minor status changes preserve the original work start
- **Examples**:
  - ✅ "Backlog" → "In Development": **OVERWRITES** previous "In Progress" date
  - ❌ "Feedback" → "In Development": **PRESERVES** original "In Progress" date
  - ❌ "Analysis" → "In Development": **PRESERVES** original "In Progress" date

## 🎛️ User Interface

### Input Parameters
- **Jira Credentials**: Base URL, email, API token
- **Board Selection**: Dropdown of available Jira boards
- **Assignee Selection**: Dropdown of users associated with the selected board
- **Year**: Analysis year (processes all 4 quarters automatically)
- **Status Configuration**: Customizable "In Progress" and "Done" status names

### Output Features

#### 1. Quarterly Comparison Charts
- **Throughput Chart**: Issues completed and story points by quarter
- **Cycle Time Chart**: Average, median, P75, and P90 cycle times by quarter
- **Interactive**: Hover tooltips, zoom, and pan capabilities

#### 2. Quarterly Summary Table
- Comprehensive metrics for each quarter
- Easy comparison of performance across quarters

#### 3. Detailed Quarter Tabs
- **Q1, Q2, Q3, Q4**: Individual tabs with detailed analysis
- **Metrics**: Count, Total Story Points, Average, Median, P75, P90
- **Issue Table**: All completed issues with clickable Jira links
- **Debug Table**: Issues filtered out due to incomplete data

#### 4. Story Points Integration
- Displays story points for each completed issue
- Calculates total story points completed per quarter
- Shows story points in the comparison charts

## 🔧 Technical Features

### Performance Optimizations
- **Session State Management**: Prevents unnecessary API calls
- **Smart Caching**: Boards and users loaded only when needed
- **Efficient Processing**: Parallel quarter processing

### Error Handling
- **Jira API Errors**: Graceful handling of 410/400 errors
- **Fallback Mechanisms**: Project-only filters when board filters fail
- **Data Validation**: Filters out incomplete or invalid data

### Data Quality
- **Incomplete Data Filtering**: Excludes issues with missing transition data
- **Debug Information**: Shows why certain issues were filtered out
- **Transparency**: JQL queries visible for verification

## 📈 Metrics Explained

### Count
- Total number of issues completed in the time period
- Primary throughput metric

### Total Story Points
- Sum of all story points from completed issues
- Alternative throughput metric (if story points are used)

### Average Cycle Time
- Mean time from "In Progress" to "Done"
- Overall performance indicator

### Median Cycle Time
- 50th percentile of cycle times
- Less affected by outliers than average

### P75 Cycle Time
- 75th percentile of cycle times
- Shows performance for most issues

### P90 Cycle Time
- 90th percentile of cycle times
- Identifies worst-case scenarios

## 🚀 Getting Started

### Prerequisites
- Python 3.12+
- Jira account with API access
- Jira API token

### Installation
1. Clone the repository
2. Create virtual environment: `python3 -m venv .venv`
3. Activate environment: `source .venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`

### Configuration
1. Copy `.env.example` to `.env`
2. Add your Jira credentials:
   ```
   JIRA_BASE_URL=https://your-domain.atlassian.net
   JIRA_EMAIL=your-email@domain.com
   JIRA_API_TOKEN=your-api-token
   ```

### Running the Application
```bash
streamlit run app/main.py
```

Access the application at `http://localhost:8501`

## 📝 Usage Workflow

1. **Enter Credentials**: Provide Jira base URL, email, and API token
2. **Select Board**: Choose the Jira board to analyze
3. **Select Assignee**: Choose specific person or "All assignees"
4. **Configure Statuses**: Adjust "In Progress" and "Done" status names if needed
5. **Set Year**: Enter the year to analyze (all quarters will be processed)
6. **Compute Metrics**: Click "Compute Metrics" to run the analysis
7. **Review Results**: 
   - View quarterly comparison charts
   - Examine detailed quarter tabs
   - Check debug information for data quality

## 🔍 Troubleshooting

### Common Issues

#### No Data Available
- Check if the selected person has completed issues in the time period
- Verify that "In Progress" and "Done" status names match your Jira configuration
- Ensure the board filter includes the relevant projects

#### Missing Story Points
- Verify that story points are configured in your Jira instance
- Check if the custom field ID is correct (default: `customfield_10120`)

#### API Errors
- Verify Jira credentials are correct
- Check if your API token has sufficient permissions
- Ensure the Jira instance is accessible

### Debug Information
- Use the "JQL used" expanders to verify search queries
- Check the debug tables for issues with incomplete data
- Review the console logs for detailed error messages

## 📊 Example Use Cases

### Team Performance Tracking
- **Monthly Reviews**: Compare quarterly performance
- **Goal Setting**: Establish throughput improvement targets
- **Process Optimization**: Measure impact of workflow changes

### Individual Performance Analysis
- **Developer Assessment**: Track individual contributor metrics
- **Workload Analysis**: Understand capacity and velocity
- **Skill Development**: Identify areas for improvement

### Project Management
- **Sprint Planning**: Use historical data for capacity planning
- **Risk Assessment**: Identify potential bottlenecks
- **Quality Metrics**: Track cycle time trends

## 🤝 Contributing

### Development Setup
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

### Code Style
- Follow PEP 8 guidelines
- Add type hints where appropriate
- Include docstrings for functions
- Write tests for new features

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For issues, questions, or contributions:
1. Check the troubleshooting section
2. Review existing issues
3. Create a new issue with detailed information
4. Include relevant logs and configuration details

---

**ATP Producer** - Empowering teams to measure and improve their performance through data-driven insights.
