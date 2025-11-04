"""
Jira API client for fetching issue data and changelog information.
"""

import base64
import logging
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .utils import format_timestamp_for_csv, format_date_for_jira, calculate_date_range
from dateutil.relativedelta import relativedelta


class JiraClient:
    """Client for interacting with Jira/Atlassian REST API."""
    
    def __init__(self, email: str, api_token: str, base_url: str, date_range_months: int = 12):
        """
        Initialize Jira client.
        
        Args:
            email: Atlassian account email.
            api_token: Atlassian API token.
            base_url: Base URL for Jira instance.
            date_range_months: Number of months to look back for data.
        """
        self.email = email
        self.api_token = api_token
        self.base_url = base_url.rstrip('/')
        self.date_range_months = date_range_months  # Store for monthly chunking
        
        # Create Basic Auth header
        auth_string = f"{email}:{api_token}"
        auth_bytes = auth_string.encode('utf-8')
        auth_b64 = base64.b64encode(auth_bytes).decode('utf-8')
        
        self.headers = {
            "Authorization": f"Basic {auth_b64}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # Calculate date range (kept for backward compatibility)
        self.since_date = calculate_date_range(date_range_months)
        self.since_date_str = format_date_for_jira(self.since_date)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((requests.exceptions.RequestException, requests.exceptions.Timeout))
    )
    def _make_request(self, url: str, params: Optional[Dict] = None, method: str = 'GET', json_data: Optional[Dict] = None) -> requests.Response:
        """
        Make HTTP request with retry logic.
        
        Args:
            url: API endpoint URL.
            params: Query parameters (for GET requests).
            method: HTTP method ('GET' or 'POST').
            json_data: JSON body (for POST requests).
            
        Returns:
            Response object.
            
        Raises:
            SystemExit: If request fails after retries.
        """
        try:
            if method == 'POST':
                response = requests.post(url, headers=self.headers, json=json_data, timeout=30)
            else:
                response = requests.get(url, headers=self.headers, params=params, timeout=30)
            
            # Check for errors
            if response.status_code >= 400:
                logging.error(f"Jira API error: {response.status_code} - {response.text}")
                sys.exit(1)
            
            response.raise_for_status()
            return response
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Jira API request failed: {e}")
            raise
    
    def get_all_issues(self, project_key: str) -> List[Dict[str, Any]]:
        """
        Fetch all issues for a project by breaking down into monthly chunks.
        This approach avoids pagination issues by querying month-by-month.
        
        Args:
            project_key: Jira project key (e.g., "OA").
            
        Returns:
            List of issue dictionaries with changelog.
        """
        # Use API v3 search/jql endpoint with GET
        base_url = f"{self.base_url}/rest/api/3/search/jql"
        
        all_issues = []
        seen_keys = set()  # Track issue keys to avoid duplicates
        
        # Calculate monthly date ranges
        end_date = datetime.now()
        
        logging.warning(f"Fetching issues month-by-month for last {self.date_range_months} months...")
        
        for month_offset in range(self.date_range_months):
            # Calculate start and end of this month chunk
            month_end = end_date - relativedelta(months=month_offset)
            month_start = month_end - relativedelta(months=1)
            
            # Format dates for JQL
            start_str = format_date_for_jira(month_start)
            end_str = format_date_for_jira(month_end)
            
            # JQL query for this month
            jql = f'project={project_key} AND created >= "{start_str}" AND created < "{end_str}" ORDER BY created DESC'
            
            logging.warning(f"Month {month_offset + 1}/{self.date_range_months}: {start_str} to {end_str}")
            
            # Try to get up to 1000 results per month (max allowed by Jira)
            params = {
                'jql': jql,
                'startAt': 0,
                'maxResults': 1000,  # Try maximum allowed
                'expand': 'changelog',
                'fields': 'key,summary,issuetype,created,status'
            }
            
            try:
                response = self._make_request(base_url, params=params)
                data = response.json()
                
                issues = data.get('issues', [])
                total = data.get('total', 0)
                
                logging.warning(f"  Fetched {len(issues)} issues (total in period: {total})")
                
                # Add only new issues (avoid duplicates at month boundaries)
                new_issues = 0
                for issue in issues:
                    issue_key = issue.get('key')
                    if issue_key not in seen_keys:
                        all_issues.append(issue)
                        seen_keys.add(issue_key)
                        new_issues += 1
                
                if new_issues < len(issues):
                    logging.warning(f"  Skipped {len(issues) - new_issues} duplicate issues")
                
                # If we got 1000 issues, there might be more - warn user
                if len(issues) >= 1000:
                    logging.warning(f"  WARNING: Hit 1000 issue limit for this month. Some issues may be missing!")
                    
            except Exception as e:
                logging.error(f"Failed to fetch issues for month {start_str} to {end_str}: {e}")
                # Continue with next month instead of failing completely
                continue
        
        logging.warning(f"Total unique issues fetched: {len(all_issues)}")
        return all_issues
    
    def get_issue_changelog(self, issue_key: str) -> List[Dict[str, Any]]:
        """
        Get changelog for a specific issue (if not already expanded).
        
        Args:
            issue_key: Jira issue key (e.g., "OA-123").
            
        Returns:
            List of changelog entries.
        """
        url = f"{self.base_url}/rest/api/3/issue/{issue_key}"
        params = {'expand': 'changelog'}
        
        response = self._make_request(url, params)
        data = response.json()
        
        changelog = data.get('changelog', {}).get('histories', [])
        return changelog
    
    def extract_status_timestamps(
        self, 
        issue: Dict[str, Any], 
        config_statuses: Dict[str, List[str]]
    ) -> Dict[str, Optional[str]]:
        """
        Extract LATEST status transition timestamps from issue changelog.
        
        Args:
            issue: Issue dictionary with changelog.
            config_statuses: Status configuration from config.yaml.
            
        Returns:
            Dictionary with 'in_progress_timestamp' and 'done_timestamp'.
        """
        # Get target status names from config
        in_progress_statuses = config_statuses.get('in_progress', ['In Progress'])
        done_statuses = config_statuses.get('done', ['Done'])
        
        # Initialize timestamps
        in_progress_timestamp = None
        done_timestamp = None
        
        # Get changelog
        changelog = issue.get('changelog', {}).get('histories', [])
        
        if not changelog:
            # Try to fetch changelog separately if not expanded
            try:
                changelog = self.get_issue_changelog(issue['key'])
            except Exception as e:
                logging.warning(f"Could not fetch changelog for {issue['key']}: {e}")
                return {
                    'in_progress_timestamp': None,
                    'done_timestamp': None
                }
        
        # Parse changelog for status transitions
        # We want the LATEST occurrence of each status
        for history in changelog:
            created = history.get('created')
            
            for item in history.get('items', []):
                # Only process status field changes
                if item.get('field') != 'status':
                    continue
                
                to_status = item.get('toString', '')
                
                # Check if this is a transition to "In Progress"
                if to_status in in_progress_statuses:
                    in_progress_timestamp = created
                
                # Check if this is a transition to "Done"
                if to_status in done_statuses:
                    done_timestamp = created
        
        return {
            'in_progress_timestamp': format_timestamp_for_csv(in_progress_timestamp),
            'done_timestamp': format_timestamp_for_csv(done_timestamp)
        }
    
    def fetch_all_jira_data(self, project_key: str, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Fetch complete issue data for a Jira project.
        
        Args:
            project_key: Jira project key.
            config: Full configuration dictionary.
            
        Returns:
            List of dictionaries with flattened issue data ready for CSV.
        """
        logging.warning(f"Fetching Jira issues for project {project_key}...")
        
        # Get all issues with changelog
        issues = self.get_all_issues(project_key)
        logging.warning(f"Found {len(issues)} issues in date range for {project_key}")
        
        csv_data = []
        config_statuses = config.get('statuses', {})
        
        for idx, issue in enumerate(issues, 1):
            try:
                issue_key = issue['key']
                fields = issue.get('fields', {})
                
                # Extract status timestamps
                timestamps = self.extract_status_timestamps(issue, config_statuses)
                
                # Build CSV row
                row = {
                    'ticket_key': issue_key,
                    'summary': fields.get('summary', ''),
                    'type': fields.get('issuetype', {}).get('name', ''),
                    'created': format_timestamp_for_csv(fields.get('created')),
                    'in_progress_timestamp': timestamps['in_progress_timestamp'],
                    'done_timestamp': timestamps['done_timestamp']
                }
                
                csv_data.append(row)
                
                # Log progress every 50 issues
                if idx % 50 == 0:
                    logging.warning(f"Processed {idx}/{len(issues)} issues for {project_key}")
                
            except Exception as e:
                logging.error(f"Failed to process issue {issue.get('key', 'UNKNOWN')}: {e}")
                sys.exit(1)
        
        logging.warning(f"Completed fetching {len(csv_data)} issues for {project_key}")
        return csv_data

