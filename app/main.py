from __future__ import annotations

import os
import re
from typing import List, Optional, Dict, Any

import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from app.config import get_jira_config
from app.jira_client import JiraClient
from app.metrics import (
    TimeWindow,
    compute_quarter_range,
    extract_cycle_times,
    jql_and,
    jql_wrap_filter,
    summarize_cycle_times,
)


st.set_page_config(page_title="ATP Producer", layout="wide")
st.title("ATP Producer: Jira Throughput & Cycle Time")

# Initialize session state
if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = False

# ------------------- Sidebar: Credentials -------------------
with st.sidebar:
    st.header("Jira Credentials")
    cfg = get_jira_config()
    base_url = st.text_input("Base URL", value=cfg.base_url or "https://your-domain.atlassian.net")
    email = st.text_input("Email", value=cfg.email)
    api_token = st.text_input("API Token", type="password", value=cfg.api_token)

    st.divider()
    st.caption("Your credentials are used only from your browser session to call Jira APIs.")

# ------------------- Inputs -------------------
st.subheader("Inputs")
cols = st.columns(2)
with cols[0]:
    year = st.number_input("Year", min_value=2000, max_value=2100, value=pd.Timestamp.now().year)
with cols[1]:
    st.write("")

# Always use Europe/Rome timezone
timezone = "Europe/Rome"

# Status mappings
status_cols = st.columns(2)
with status_cols[0]:
    in_progress_names_str = st.text_input("In Progress statuses (comma-separated)", value="In Development, Failed/Blocked, Analysis")
with status_cols[1]:
    done_names_str = st.text_input("Done statuses (comma-separated)", value="Closed")

in_progress_names = [s.strip() for s in in_progress_names_str.split(",") if s.strip()]
done_names = [s.strip() for s in done_names_str.split(",") if s.strip()]

client: Optional[JiraClient] = None
if base_url and email and api_token:
    try:
        client = JiraClient(base_url=base_url, email=email, api_token=api_token)
    except Exception as e:
        st.error(f"Failed to initialize Jira client: {e}")
        client = None

# Check if credentials changed to reload data
credentials_key = f"{base_url}_{email}_{api_token}"
if 'last_credentials' not in st.session_state or st.session_state.last_credentials != credentials_key:
    st.session_state.last_credentials = credentials_key
    st.session_state.data_loaded = False
    # Clear cached data when credentials change
    for key in ['boards', 'selected_board_id', 'project_keys_for_board', 'selected_account_id']:
        if key in st.session_state:
            del st.session_state[key]

selected_board_id: Optional[int] = st.session_state.get("selected_board_id")
selected_account_id: Optional[str] = st.session_state.get("selected_account_id")
project_keys_for_board: List[str] = st.session_state.get("project_keys_for_board") or []

if client and not st.session_state.data_loaded:
    with st.spinner("Loading boards..."):
        try:
            boards = client.list_boards()
            st.session_state.boards = boards
        except Exception as e:
            st.error(f"Failed to list boards: {e}")
            st.session_state.boards = []
    st.session_state.data_loaded = True

if client and st.session_state.get("boards"):
    boards = st.session_state.boards
    if boards:
        boards_sorted = sorted(boards, key=lambda b: int(b.get("id", 0)))
        label_to_board = {f"{b.get('name')} (#{b.get('id')})": b for b in boards_sorted}
        board_label = st.selectbox("Board", options=list(label_to_board.keys()), key="board_select")
        selected_board = label_to_board[board_label]
        selected_board_id = int(selected_board.get("id"))
        
        # Only reload projects if board changed
        if st.session_state.get("selected_board_id") != selected_board_id:
            st.session_state["selected_board_id"] = selected_board_id
            try:
                projects = client.get_board_projects(selected_board_id)
                project_keys_for_board = [p.get("key") for p in projects if p.get("key")]
                if not project_keys_for_board:
                    # fallback derive one key from board filter JQL
                    base_filter = client.get_board_filter_jql(selected_board_id)
                    m = re.search(r"project\s*=\s*([A-Z][A-Z0-9]+)", base_filter)
                    if m:
                        project_keys_for_board = [m.group(1)]
                st.session_state["project_keys_for_board"] = project_keys_for_board
            except Exception as e:
                st.warning(f"Could not get board projects: {e}")
                project_keys_for_board = []
                st.session_state["project_keys_for_board"] = []
        else:
            project_keys_for_board = st.session_state.get("project_keys_for_board") or []

        # Assignees: get users associated with the specific board
        selected_account_id = None
        try:
            board_users = client.get_board_users(selected_board_id)
            if board_users:
                # Create a mapping from display name to account ID
                label_to_id = {f"{u.get('displayName')} ({u.get('emailAddress', 'n/a')})": u.get("accountId") for u in board_users if u.get("accountId")}
                labels = ["-- All assignees --"] + sorted(label_to_id.keys())
                choice = st.selectbox("Assignee", options=labels, index=0, key="assignee_select")
                if choice != "-- All assignees --":
                    selected_account_id = label_to_id.get(choice)
        except Exception as e:
            st.warning(f"Could not get board users: {e}")
            # Fallback to project assignable users if board users fail
            union_users: Dict[str, Dict[str, Any]] = {}
            for pk in project_keys_for_board:
                try:
                    users = client.get_assignable_users(pk)
                    for u in users:
                        union_users[u.get("accountId")] = u
                except Exception:
                    continue
            if union_users:
                label_to_id = {f"{u.get('displayName')} ({u.get('emailAddress', 'n/a')})": uid for uid, u in union_users.items()}
                labels = ["-- All assignees --"] + sorted(label_to_id.keys())
                choice = st.selectbox("Assignee", options=labels, index=0, key="assignee_select")
                if choice != "-- All assignees --":
                    selected_account_id = label_to_id.get(choice)
        st.session_state["selected_account_id"] = selected_account_id

compute = st.button("Compute Metrics", type="primary")

if compute:
    if not client:
        st.error("Please provide Jira credentials in the sidebar.")
        st.stop()
    if not selected_board_id:
        st.error("Please select a board from the dropdown.")
        st.stop()

    # Base filter from board
    try:
        base_filter = client.get_board_filter_jql(int(selected_board_id))
    except Exception as e:
        st.error(f"Failed to read board filter: {e}")
        st.stop()

    # Process all quarters for the selected year
    quarters_data = {}
    fmt = "%Y/%m/%d %H:%M"
    
    for quarter in range(1, 5):
        # Time window for this quarter
        window: TimeWindow = compute_quarter_range(int(year), quarter, tz=timezone)
        start_str = window.start.strftime(fmt)
        end_str = window.end.strftime(fmt)

        parts: List[str] = []
        # Use status changed to Closed during for more reliable results
        parts.append(f"status changed to Closed during (\"{start_str}\", \"{end_str}\")")
        if selected_account_id:
            parts.append(f"assignee = \"{selected_account_id}\"")

        extra_jql = jql_and(*parts)
        full_jql = jql_wrap_filter(base_filter, extra_jql)

        with st.expander(f"Q{quarter} JQL used", expanded=False):
            st.code(full_jql)

        # Search issues for this quarter
        with st.spinner(f"Searching issues for Q{quarter}..."):
            try:
                search = client.search_issues(full_jql, fields=["key", "summary", "issuetype", "status", "updated", "customfield_10120"])  # noqa: E501
            except Exception as e:
                if "410" in str(e) and project_keys_for_board:
                    st.warning(f"Q{quarter}: Board filter caused a 410; retrying with project-only filter.")
                    # Use an OR of projects if multiple
                    proj_clause = " OR ".join([f"project = {k}" for k in project_keys_for_board])
                    fallback_jql = jql_and(f"({proj_clause})", extra_jql)
                    try:
                        search = client.search_issues(fallback_jql, fields=["key", "summary", "issuetype", "status", "updated", "customfield_10120"])  # noqa: E501
                    except Exception as e2:
                        st.error(f"Q{quarter}: Issue search failed after fallback: {e2}")
                        continue
                else:
                    st.error(f"Q{quarter}: Issue search failed: {e}")
                    continue

        issues = search.get("issues", [])
        issue_keys = [it.get("key") for it in issues]
        
        # Create mapping from issue key to story points
        issue_to_story_points = {}
        for issue in issues:
            issue_key = issue.get("key")
            fields = issue.get("fields", {})
            
            # Use the correct story points field ID for this Jira instance
            story_points_raw = fields.get("customfield_10120")
            
            # Convert to integer if it's a number, otherwise keep as is
            if story_points_raw is not None and isinstance(story_points_raw, (int, float)):
                story_points = int(story_points_raw)
            else:
                story_points = story_points_raw
            
            issue_to_story_points[issue_key] = story_points

        # Compute cycle times for this quarter
        with st.spinner(f"Computing cycle times for Q{quarter}..."):
            cycles = extract_cycle_times(client, issue_keys, in_progress_names=in_progress_names, done_names=done_names, assignee_account_id=selected_account_id)
        
        # Store quarter data
        quarters_data[quarter] = {
            'issues': issues,
            'issue_keys': issue_keys,
            'issue_to_story_points': issue_to_story_points,
            'cycles': cycles,
            'window': window
        }

    # Display quarterly statistics
    st.subheader(f"Year {year} - Quarterly Cycle Time Statistics")
    
    # Add general explanation
    with st.expander("📚 Understanding These Metrics", expanded=False):
        st.markdown("""
        **What is Cycle Time?**
        Cycle time measures how long it takes for work to move from 'In Progress' to 'Done' status. It's a key metric for understanding team efficiency and delivery speed.
        
        **Key Metrics Explained:**
        - **Count**: Total issues completed in the time period
        - **Story Points**: Relative effort/complexity of completed work
        - **Average**: Mean cycle time across all issues
        - **Median**: Middle value (50th percentile) - less affected by outliers
        - **P75**: 75th percentile - 75% of issues complete within this time
        - **P90**: 90th percentile - 90% of issues complete within this time
        
        **How to Use These Metrics:**
        - **Throughput** (Count/Story Points): Shows how much work is being delivered
        - **Cycle Time**: Shows how fast work is being delivered
        - **Percentiles**: Use P75/P90 for realistic planning and commitments
        - **Trends**: Compare quarters to identify improvements or issues
        
        **Data Source**: Issues that changed status to 'Closed' during each quarter, with cycle time calculated from first 'In Progress' to first 'Done' transition.
        """)
    
    # Create comparison graph
    if quarters_data:
        # Prepare data for comparison graph
        comparison_data = []
        for quarter in range(1, 5):
            if quarter in quarters_data:
                data = quarters_data[quarter]
                cycles = data['cycles']
                issue_to_story_points = data['issue_to_story_points']
                
                # Filter valid cycles
                valid_cycles = [c for c in cycles if c.in_progress_at is not None and c.done_at is not None]
                seconds_list = [c.seconds for c in valid_cycles if c.seconds is not None]
                story_points_list = []
                for c in valid_cycles:
                    story_points = issue_to_story_points.get(c.issue_key, "N/A")
                    if isinstance(story_points, int):
                        story_points_list.append(story_points)
                
                if seconds_list:
                    summary = summarize_cycle_times(seconds_list)
                    total_story_points = sum(story_points_list) if story_points_list else 0
                    
                    comparison_data.append({
                        'Quarter': f'Q{quarter}',
                        'Count': summary.get("count", 0),
                        'Total Story Points': total_story_points,
                        'Avg Cycle Time (days)': round(summary.get('avg_days', 0), 2),
                        'Median Cycle Time (days)': round(summary.get('median_days', 0), 2),
                        'P75 Cycle Time (days)': round(summary.get('p75_days', 0), 2),
                        'P90 Cycle Time (days)': round(summary.get('p90_days', 0), 2)
                    })
        
        if comparison_data:
            # Create comparison charts with explanations
            st.subheader("📊 Quarterly Performance Comparison")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Count and Story Points comparison
                df_comparison = pd.DataFrame(comparison_data)
                
                fig_count = go.Figure()
                fig_count.add_trace(go.Bar(
                    x=df_comparison['Quarter'],
                    y=df_comparison['Count'],
                    name='Count',
                    marker_color='lightblue'
                ))
                fig_count.add_trace(go.Bar(
                    x=df_comparison['Quarter'],
                    y=df_comparison['Total Story Points'],
                    name='Total Story Points',
                    marker_color='lightgreen'
                ))
                
                fig_count.update_layout(
                    title='Issues Completed & Story Points by Quarter',
                    xaxis_title='Quarter',
                    yaxis_title='Count / Story Points',
                    barmode='group',
                    height=400
                )
                st.plotly_chart(fig_count, use_container_width=True)
                
                with st.expander("📈 Throughput Explanation", expanded=False):
                    st.markdown("""
                    **Throughput Metrics:**
                    - **Count**: Number of issues completed each quarter
                    - **Story Points**: Total effort delivered each quarter
                    
                    *Higher values indicate better throughput. Compare quarters to identify trends in team productivity.*
                    """)
            
            with col2:
                # Cycle Time metrics comparison
                fig_cycle = go.Figure()
                fig_cycle.add_trace(go.Bar(
                    x=df_comparison['Quarter'],
                    y=df_comparison['Avg Cycle Time (days)'],
                    name='Avg',
                    marker_color='orange'
                ))
                fig_cycle.add_trace(go.Bar(
                    x=df_comparison['Quarter'],
                    y=df_comparison['Median Cycle Time (days)'],
                    name='Median',
                    marker_color='red'
                ))
                fig_cycle.add_trace(go.Bar(
                    x=df_comparison['Quarter'],
                    y=df_comparison['P75 Cycle Time (days)'],
                    name='P75',
                    marker_color='purple'
                ))
                fig_cycle.add_trace(go.Bar(
                    x=df_comparison['Quarter'],
                    y=df_comparison['P90 Cycle Time (days)'],
                    name='P90',
                    marker_color='brown'
                ))
                
                fig_cycle.update_layout(
                    title='Cycle Time Metrics by Quarter',
                    xaxis_title='Quarter',
                    yaxis_title='Days',
                    barmode='group',
                    height=400
                )
                st.plotly_chart(fig_cycle, use_container_width=True)
                
                with st.expander("⏱️ Cycle Time Explanation", expanded=False):
                    st.markdown("""
                    **Cycle Time Metrics:**
                    - **Avg**: Average time from 'In Progress' to 'Done'
                    - **Median**: 50th percentile (middle value)
                    - **P75**: 75% of issues complete within this time
                    - **P90**: 90% of issues complete within this time
                    
                    *Lower values indicate faster delivery. Use P75/P90 for realistic planning and commitments.*
                    """)
            
            # Summary table
            st.subheader("📊 Quarterly Summary")
            st.dataframe(df_comparison, use_container_width=True)
            
            with st.expander("📋 Summary Table Explanation", expanded=False):
                st.markdown("""
                **Summary Table Columns:**
                - **Quarter**: Q1, Q2, Q3, Q4 of the selected year
                - **Count**: Number of completed issues per quarter
                - **Total Story Points**: Sum of story points delivered per quarter
                - **Avg Cycle Time**: Average days from 'In Progress' to 'Done'
                - **Median Cycle Time**: 50th percentile cycle time
                - **P75 Cycle Time**: 75th percentile cycle time
                - **P90 Cycle Time**: 90th percentile cycle time
                
                **How to Read This Table:**
                - Compare **Count** and **Story Points** across quarters to see throughput trends
                - Compare **cycle time metrics** to see delivery speed trends
                - Use **P75/P90** values for realistic sprint planning and commitments
                - Look for patterns: Are we getting faster? More productive? More consistent?
                """)
    
    # Create tabs for each quarter
    if quarters_data:
        tab1, tab2, tab3, tab4 = st.tabs(["Q1", "Q2", "Q3", "Q4"])
        
        for quarter, tab in enumerate([tab1, tab2, tab3, tab4], 1):
            with tab:
                if quarter in quarters_data:
                    data = quarters_data[quarter]
                    cycles = data['cycles']
                    issue_to_story_points = data['issue_to_story_points']
                    
                    # Filter out cycles without in_progress_at (incomplete data)
                    valid_cycles = [c for c in cycles if c.in_progress_at is not None and c.done_at is not None]
                    filtered_cycles = [c for c in cycles if c.in_progress_at is None or c.done_at is None]
                    
                    # Sort by cycle time (ascending - fastest first)
                    valid_cycles.sort(key=lambda c: c.seconds or 0)
                    
                    # Calculate metrics
                    seconds_list = [c.seconds for c in valid_cycles if c.seconds is not None]
                    story_points_list = []
                    for c in valid_cycles:
                        story_points = issue_to_story_points.get(c.issue_key, "N/A")
                        if isinstance(story_points, int):
                            story_points_list.append(story_points)
                    
                    if not seconds_list:
                        st.info(f"Q{quarter}: No cycle time data available (missing status transitions).")
                    else:
                        summary = summarize_cycle_times(seconds_list)
                        total_story_points = sum(story_points_list) if story_points_list else 0
                        
                        # Display metrics with explanations
                        st.subheader("📈 Cycle Time Metrics")
                        
                        # Create expandable sections for each metric
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            with st.expander("📊 Count", expanded=True):
                                st.metric("Count", summary.get("count", 0))
                                st.caption("Total number of issues that completed their cycle (moved from 'In Progress' to 'Done' status) during this quarter.")
                        
                        with col2:
                            with st.expander("🎯 Story Points", expanded=True):
                                st.metric("Total Story Points", total_story_points)
                                st.caption("Sum of story points for all completed issues. Story points represent the relative effort/complexity of work items.")
                        
                        with col3:
                            with st.expander("⏱️ Cycle Time", expanded=True):
                                st.metric("Avg (days)", f"{summary.get('avg_days', 0):.2f}")
                                st.caption("Average time from 'In Progress' to 'Done' status across all completed issues.")
                        
                        col4, col5, col6 = st.columns(3)
                        
                        with col4:
                            with st.expander("📈 Median", expanded=True):
                                st.metric("Median (days)", f"{(summary.get('median_days') or 0):.2f}")
                                st.caption("50th percentile - half of issues complete faster, half take longer. Less affected by outliers than average.")
                        
                        with col5:
                            with st.expander("🎯 P75", expanded=True):
                                st.metric("P75 (days)", f"{(summary.get('p75_days') or 0):.2f}")
                                st.caption("75th percentile - 75% of issues complete within this time. Good for setting realistic expectations.")
                        
                        with col6:
                            with st.expander("🚀 P90", expanded=True):
                                st.metric("P90 (days)", f"{(summary.get('p90_days') or 0):.2f}")
                                st.caption("90th percentile - 90% of issues complete within this time. Useful for worst-case planning.")
                        
                        # Display table with explanation
                        if valid_cycles:
                            with st.expander("📋 Detailed Issue Table", expanded=False):
                                st.markdown("""
                                **Table Columns Explained:**
                                - **#**: Sequential number for easy reference
                                - **Issue**: Clickable Jira issue key (opens in new tab)
                                - **In Progress At**: When the issue first moved to 'In Progress' status
                                - **Done At**: When the issue first moved to 'Done' status
                                - **Story Points**: Effort/complexity estimate for the issue
                                - **Cycle Time (days)**: Total time from 'In Progress' to 'Done'
                                
                                **How to Use This Data:**
                                - Click issue links to view details in Jira
                                - Sort by cycle time to identify fastest/slowest issues
                                - Look for patterns in story points vs cycle time
                                - Use for retrospective analysis and process improvement
                                """)
                            
                            rows = []
                            for i, c in enumerate(valid_cycles, 1):
                                # Create clickable link to the issue
                                issue_url = f"{client.auth.base_url}/browse/{c.issue_key}"
                                
                                # Format dates to YYYY-MM-DD H:M:S
                                in_progress_str = c.in_progress_at.strftime("%Y-%m-%d %H:%M:%S")
                                done_str = c.done_at.strftime("%Y-%m-%d %H:%M:%S")
                                
                                # Get story points for this issue
                                story_points = issue_to_story_points.get(c.issue_key, "N/A")
                                
                                rows.append({
                                    "#": i,
                                    "Issue": c.issue_key,
                                    "Issue Link": issue_url,
                                    "In Progress At": in_progress_str,
                                    "Done At": done_str,
                                    "Story Points": story_points,
                                    "Cycle Time (days)": round((c.seconds or 0.0) / 86400.0, 2),
                                })
                            
                            # Create HTML table
                            html_table = "<table><tr>"
                            # Headers
                            for col in ["#", "Issue", "In Progress At", "Done At", "Story Points", "Cycle Time (days)"]:
                                html_table += f"<th>{col}</th>"
                            html_table += "</tr>"
                            
                            # Data rows
                            for row in rows:
                                html_table += "<tr>"
                                html_table += f"<td>{row['#']}</td>"
                                # Make issue key clickable
                                html_table += f"<td><a href='{row['Issue Link']}' target='_blank'>{row['Issue']}</a></td>"
                                html_table += f"<td>{row['In Progress At'] or 'N/A'}</td>"
                                html_table += f"<td>{row['Done At'] or 'N/A'}</td>"
                                html_table += f"<td>{row['Story Points']}</td>"
                                html_table += f"<td>{row['Cycle Time (days)']}</td>"
                                html_table += "</tr>"
                            
                            html_table += "</table>"
                            st.markdown(html_table, unsafe_allow_html=True)
                        
                        # Debug table for filtered issues
                        if filtered_cycles:
                            st.subheader(f"🔍 Q{quarter} Debug: Filtered Issues (N/A values)")
                            debug_rows = []
                            for i, c in enumerate(filtered_cycles, 1):
                                issue_url = f"{client.auth.base_url}/browse/{c.issue_key}"
                                in_progress_str = c.in_progress_at.strftime("%Y-%m-%d %H:%M:%S") if c.in_progress_at else "N/A"
                                done_str = c.done_at.strftime("%Y-%m-%d %H:%M:%S") if c.done_at else "N/A"
                                
                                # Get story points for this issue
                                story_points = issue_to_story_points.get(c.issue_key, "N/A")
                                
                                debug_rows.append({
                                    "#": i,
                                    "Issue": c.issue_key,
                                    "Issue Link": issue_url,
                                    "In Progress At": in_progress_str,
                                    "Done At": done_str,
                                    "Story Points": story_points,
                                    "Reason": "Missing In Progress" if c.in_progress_at is None else "Missing Done" if c.done_at is None else "Both Missing"
                                })
                            
                            # Create debug HTML table
                            debug_html = "<table><tr>"
                            for col in ["#", "Issue", "In Progress At", "Done At", "Story Points", "Reason"]:
                                debug_html += f"<th>{col}</th>"
                            debug_html += "</tr>"
                            
                            for row in debug_rows:
                                debug_html += "<tr>"
                                debug_html += f"<td>{row['#']}</td>"
                                debug_html += f"<td><a href='{row['Issue Link']}' target='_blank'>{row['Issue']}</a></td>"
                                debug_html += f"<td>{row['In Progress At']}</td>"
                                debug_html += f"<td>{row['Done At']}</td>"
                                debug_html += f"<td>{row['Story Points']}</td>"
                                debug_html += f"<td>{row['Reason']}</td>"
                                debug_html += "</tr>"
                            
                            debug_html += "</table>"
                            st.markdown(debug_html, unsafe_allow_html=True)
                            st.caption(f"Q{quarter}: These issues were excluded from cycle time calculations due to missing status transition data.")
                else:
                    st.info(f"Q{quarter}: No data available for this quarter.")
    else:
        st.info("No data available for any quarter.")

    st.caption("Throughput uses resolutiondate within the selected window; cycle time uses first transition to selected 'In Progress' → first transition to selected 'Done'.")
