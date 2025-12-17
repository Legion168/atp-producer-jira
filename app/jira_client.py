from __future__ import annotations

import logging
import json
import math
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

import requests


_DEFAULT_MAX_RESULTS = 100


@dataclass(frozen=True)
class JiraAuth:
    base_url: str
    email: str
    api_token: str


class JiraClient:
    def __init__(self, base_url: str, email: str, api_token: str, request_delay: float = 0.1) -> None:
        if not base_url or not email or not api_token:
            raise ValueError("Missing Jira credentials or base URL")
        self.auth = JiraAuth(base_url=base_url.rstrip("/"), email=email, api_token=api_token)
        self._session = self._create_session()
        self.request_delay = request_delay  # Delay between requests in seconds

    def _create_session(self) -> requests.Session:
        session = requests.Session()
        session.auth = (self.auth.email, self.auth.api_token)
        session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json",
        })
        return session

    # ---- Users ----
    def search_user(self, query: str, max_results: int = 20) -> List[Dict[str, Any]]:
        url = f"{self.auth.base_url}/rest/api/3/user/search"
        params = {"query": query, "maxResults": max_results}
        resp = self._session.get(url, params=params)
        self._raise_for_status(resp)
        return resp.json()

    def get_all_users(self, max_results: int = 1000) -> List[Dict[str, Any]]:
        """List all users visible to the authenticated account (may require admin scopes)."""
        url = f"{self.auth.base_url}/rest/api/3/users/search"
        start_at = 0
        users: List[Dict[str, Any]] = []
        while True:
            params = {"startAt": start_at, "maxResults": max_results}
            resp = self._session.get(url, params=params)
            self._raise_for_status(resp)
            batch = resp.json()
            if not isinstance(batch, list):
                break
            users.extend(batch)
            if len(batch) < max_results:
                break
            start_at += max_results
        return users

    def get_assignable_users(self, project_key: str, query: str = "", max_results: int = 1000) -> List[Dict[str, Any]]:
        url = f"{self.auth.base_url}/rest/api/3/user/assignable/search"
        params: Dict[str, Any] = {"project": project_key, "maxResults": max_results}
        if query:
            params["query"] = query
        resp = self._session.get(url, params=params)
        self._raise_for_status(resp)
        return resp.json()

    def get_board_users(self, board_id: int, max_results: int = 1000) -> List[Dict[str, Any]]:
        """Get users associated with a specific board by searching for issues in the board and extracting unique assignees."""
        # Get the board's JQL filter to find issues in this board
        try:
            board_jql = self.get_board_filter_jql(board_id)
        except Exception as e:
            logging.warning(f"Could not get board filter JQL for board {board_id}: {e}")
            return []
        
        # Search for issues in the board to get assignees
        try:
            # Search for issues with assignee field to get all users who have been assigned to issues in this board
            search_result = self.search_issues(
                board_jql,
                fields=["assignee"],
                max_results=max_results
            )
            
            # Extract unique assignees
            users = {}
            for issue in search_result.get("issues", []):
                assignee = issue.get("fields", {}).get("assignee")
                if assignee and assignee.get("accountId"):
                    users[assignee["accountId"]] = assignee
            
            return list(users.values())
            
        except Exception as e:
            logging.warning(f"Could not get board users for board {board_id}: {e}")
            return []

    # ---- Boards ----
    def list_boards(self, name: str = "", board_type: Optional[str] = None, max_results: int = 50) -> List[Dict[str, Any]]:
        url = f"{self.auth.base_url}/rest/agile/1.0/board"
        start_at = 0
        results: List[Dict[str, Any]] = []
        while True:
            params: Dict[str, Any] = {"startAt": start_at, "maxResults": max_results}
            if name:
                params["name"] = name
            if board_type:
                params["type"] = board_type
            resp = self._session.get(url, params=params)
            self._raise_for_status(resp)
            data = resp.json()
            values = data.get("values", [])
            results.extend(values)
            is_last = data.get("isLast", False)
            if is_last or not values:
                break
            start_at += max_results
        return results

    def get_board_config(self, board_id: int) -> Dict[str, Any]:
        url = f"{self.auth.base_url}/rest/agile/1.0/board/{board_id}/configuration"
        resp = self._session.get(url)
        self._raise_for_status(resp)
        return resp.json()

    def get_board_projects(self, board_id: int) -> List[Dict[str, Any]]:
        """Return projects associated with a board (Agile API)."""
        url = f"{self.auth.base_url}/rest/agile/1.0/board/{board_id}/project"
        start_at = 0
        projects: List[Dict[str, Any]] = []
        while True:
            params = {"startAt": start_at, "maxResults": 50}
            resp = self._session.get(url, params=params)
            self._raise_for_status(resp)
            data = resp.json()
            values = data.get("values", [])
            projects.extend(values)
            is_last = data.get("isLast", False)
            if is_last or not values:
                break
            start_at += 50
        return projects

    def get_board_filter_jql(self, board_id: int) -> str:
        cfg_url = f"{self.auth.base_url}/rest/agile/1.0/board/{board_id}/configuration"
        cfg_resp = self._session.get(cfg_url)
        self._raise_for_status(cfg_resp)
        cfg = cfg_resp.json()
        filter_id = cfg.get("filter", {}).get("id")
        if not filter_id:
            raise RuntimeError("Unable to resolve board filter id")
        flt_url = f"{self.auth.base_url}/rest/api/3/filter/{filter_id}"
        flt_resp = self._session.get(flt_url)
        self._raise_for_status(flt_resp)
        jql = flt_resp.json().get("jql", "")
        if not jql:
            raise RuntimeError("Board filter JQL is empty")
        return jql

    # ---- Fields ----
    def list_fields(self) -> List[Dict[str, Any]]:
        url = f"{self.auth.base_url}/rest/api/3/field"
        resp = self._session.get(url)
        self._raise_for_status(resp)
        return resp.json()

    # ---- Search (POST /search/jql with queries[]) ----
    def search_issues(self,
                      jql: str,
                      fields: Optional[Iterable[str]] = None,
                      expand: Optional[Iterable[str]] = None,
                      max_results: int = _DEFAULT_MAX_RESULTS,
                      validate_query: str = "WARN") -> Dict[str, Any]:
        url_jql = f"{self.auth.base_url}/rest/api/3/search/jql"
        start_at = 0
        all_issues: List[Dict[str, Any]] = []
        total: Optional[int] = None
        field_list = list(fields) if fields else []
        expand_list = list(expand) if expand else []

        while True:
            payload: Dict[str, Any] = {
                "jql": jql,
                "maxResults": max_results,
            }
            if field_list:
                payload["fields"] = field_list
            if expand_list:
                payload["expand"] = expand_list
            # Add startAt for pagination (not in curl example but needed for our pagination)
            if start_at > 0:
                payload["startAt"] = start_at

            try:
                logging.info("Jira search request payload: %s", json.dumps(payload, ensure_ascii=False))
            except Exception:
                logging.info("Jira search request payload (repr): %r", payload)

            resp = self._make_request_with_retry(lambda: self._session.post(url_jql, json=payload))
            try:
                self._raise_for_status(resp)
            except requests.HTTPError:
                logging.error("Jira search failed (%s): %s", resp.status_code, resp.text)
                raise

            data = resp.json()
            issues_block = data

            if total is None:
                total = issues_block.get("total", 0)
            issues = issues_block.get("issues", [])
            all_issues.extend(issues)

            if len(all_issues) >= (total or 0):
                break
            start_at += max_results

        return {"total": total or 0, "issues": all_issues, "startAt": 0, "maxResults": max_results}

    # ---- Changelog ----
    def get_issue_changelog(self, issue_key: str, max_results: int = 100) -> List[Dict[str, Any]]:
        url = f"{self.auth.base_url}/rest/api/3/issue/{issue_key}/changelog"
        start_at = 0
        histories: List[Dict[str, Any]] = []
        while True:
            params = {"startAt": start_at, "maxResults": max_results}
            resp = self._make_request_with_retry(lambda: self._session.get(url, params=params))
            self._raise_for_status(resp)
            data = resp.json()
            histories.extend(data.get("values", []))
            total = data.get("total", 0)
            if len(histories) >= total:
                break
            start_at += max_results
            # Add delay between pagination requests
            if self.request_delay > 0:
                time.sleep(self.request_delay)
        return histories

    def has_subtasks(self, issue_key: str) -> bool:
        """
        Check if an issue has subtasks.
        
        Args:
            issue_key: The Jira issue key (e.g., "PROJ-123")
            
        Returns:
            True if the issue has subtasks, False otherwise
        """
        # Search for subtasks of this issue
        jql = f'parent = "{issue_key}"'
        try:
            result = self.search_issues(jql, fields=["key"], max_results=1)
            return result.get("total", 0) > 0
        except Exception as e:
            logging.warning(f"Could not check subtasks for {issue_key}: {e}")
            return False

    def _make_request_with_retry(self, request_func, max_retries: int = 5, initial_delay: float = 1.0) -> requests.Response:
        """
        Make a request with exponential backoff retry for rate limiting (429 errors).
        
        Args:
            request_func: A callable that returns a requests.Response
            max_retries: Maximum number of retry attempts
            initial_delay: Initial delay in seconds before first retry
            
        Returns:
            requests.Response object
            
        Raises:
            requests.HTTPError: If request fails after all retries
        """
        delay = initial_delay
        
        for attempt in range(max_retries + 1):
            try:
                resp = request_func()
                
                # If we get a 429, retry with exponential backoff
                if resp.status_code == 429:
                    if attempt < max_retries:
                        retry_after = resp.headers.get("Retry-After")
                        if retry_after:
                            try:
                                delay = float(retry_after)
                            except ValueError:
                                pass
                        
                        logging.warning(
                            f"Rate limited (429). Retrying in {delay:.1f}s (attempt {attempt + 1}/{max_retries + 1})"
                        )
                        time.sleep(delay)
                        delay *= 2  # Exponential backoff
                        continue
                    else:
                        # Last attempt failed
                        resp.raise_for_status()
                
                # Add small delay between requests to avoid hitting rate limits
                if self.request_delay > 0:
                    time.sleep(self.request_delay)
                
                return resp
                
            except requests.HTTPError as e:
                if e.response and e.response.status_code == 429:
                    if attempt < max_retries:
                        retry_after = e.response.headers.get("Retry-After")
                        if retry_after:
                            try:
                                delay = float(retry_after)
                            except ValueError:
                                pass
                        
                        logging.warning(
                            f"Rate limited (429). Retrying in {delay:.1f}s (attempt {attempt + 1}/{max_retries + 1})"
                        )
                        time.sleep(delay)
                        delay *= 2  # Exponential backoff
                        continue
                
                # For other errors or last attempt, raise immediately
                raise
        
        # Should never reach here, but just in case
        raise requests.HTTPError("Request failed after all retries")
    
    @staticmethod
    def _raise_for_status(resp: requests.Response) -> None:
        try:
            resp.raise_for_status()
        except requests.HTTPError as e:
            logging.error("Jira API error: %s", e)
            raise
