# ATP Producer (Jira Throughput & Cycle Time)

Visualize per-person ATP metrics from Jira:
- Total issues transitioned to "Done" within a time window (throughput)
- Average/median cycle time from first "In Progress" to "Done"

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

## Notes
- The app uses Jira Cloud REST API and Agile API to query issues on a board and inspect changelogs for status transitions.
- Permissions: The API token must have access to the board's project(s).
- Timeframe filter uses year+quarter to compute start/end dates.
