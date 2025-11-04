"""
GitHub API client for fetching pull request data.
"""

import logging
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .utils import format_timestamp_for_csv, format_date_for_github, calculate_date_range


class GitHubClient:
    """Client for interacting with GitHub REST API."""
    
    def __init__(self, token: str, organization: str, date_range_months: int = 12):
        """
        Initialize GitHub client.
        
        Args:
            token: GitHub personal access token.
            organization: GitHub organization name.
            date_range_months: Number of months to look back for data.
        """
        self.token = token
        self.organization = organization
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        # Calculate date range
        self.since_date = calculate_date_range(date_range_months)
        self.since_date_str = format_date_for_github(self.since_date)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((requests.exceptions.RequestException, requests.exceptions.Timeout))
    )
    def _make_request(self, url: str, params: Optional[Dict] = None) -> requests.Response:
        """
        Make HTTP request with retry logic and rate limit handling.
        
        Args:
            url: API endpoint URL.
            params: Query parameters.
            
        Returns:
            Response object.
            
        Raises:
            SystemExit: If request fails after retries or rate limit exceeded.
        """
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            
            # Check rate limit
            remaining = int(response.headers.get('X-RateLimit-Remaining', 0))
            if remaining < 10:
                reset_time = int(response.headers.get('X-RateLimit-Reset', 0))
                wait_time = max(reset_time - time.time(), 0) + 5
                logging.warning(f"GitHub rate limit low ({remaining} remaining). Waiting {wait_time}s...")
                time.sleep(wait_time)
            
            # Handle rate limit exceeded (429)
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 60))
                logging.warning(f"Rate limited. Retrying after {retry_after}s...")
                time.sleep(retry_after)
                return self._make_request(url, params)
            
            # Check for errors
            if response.status_code >= 400:
                logging.error(f"GitHub API error: {response.status_code} - {response.text}")
                sys.exit(1)
            
            response.raise_for_status()
            return response
            
        except requests.exceptions.RequestException as e:
            logging.error(f"GitHub API request failed: {e}")
            raise
    
    def get_pull_requests(self, repo: str, state: str = 'all', per_page: int = 100) -> List[Dict[str, Any]]:
        """
        Fetch all pull requests for a repository with pagination.
        
        Args:
            repo: Repository name.
            state: PR state filter ('all', 'open', 'closed').
            per_page: Number of results per page.
            
        Returns:
            List of pull request dictionaries.
        """
        url = f"{self.base_url}/repos/{self.organization}/{repo}/pulls"
        params = {
            'state': state,
            'per_page': per_page,
            'page': 1,
            'sort': 'created',
            'direction': 'desc'
        }
        
        all_prs = []
        
        while True:
            response = self._make_request(url, params)
            prs = response.json()
            
            if not prs:
                break
            
            # Filter by date range
            filtered_prs = []
            for pr in prs:
                created_at = datetime.fromisoformat(pr['created_at'].replace('Z', '+00:00'))
                if created_at >= self.since_date:
                    filtered_prs.append(pr)
                else:
                    # Since PRs are sorted by created date desc, we can stop here
                    return all_prs + filtered_prs
            
            all_prs.extend(filtered_prs)
            
            # Check for next page
            if 'Link' in response.headers:
                links = response.headers['Link']
                if 'rel="next"' not in links:
                    break
            else:
                break
            
            params['page'] += 1
        
        return all_prs
    
    def get_pr_comments(self, repo: str, pr_number: int) -> int:
        """
        Get total comment count for a PR (review comments + issue comments).
        
        Args:
            repo: Repository name.
            pr_number: Pull request number.
            
        Returns:
            Total number of comments.
        """
        # Get review comments (code-level comments)
        review_comments_url = f"{self.base_url}/repos/{self.organization}/{repo}/pulls/{pr_number}/comments"
        review_response = self._make_request(review_comments_url, {'per_page': 100})
        review_comments = review_response.json()
        
        # Paginate if necessary
        review_count = len(review_comments)
        page = 2
        while len(review_comments) == 100:
            response = self._make_request(review_comments_url, {'per_page': 100, 'page': page})
            more_comments = response.json()
            if not more_comments:
                break
            review_count += len(more_comments)
            page += 1
        
        # Get issue comments (general discussion)
        issue_comments_url = f"{self.base_url}/repos/{self.organization}/{repo}/issues/{pr_number}/comments"
        issue_response = self._make_request(issue_comments_url, {'per_page': 100})
        issue_comments = issue_response.json()
        
        # Paginate if necessary
        issue_count = len(issue_comments)
        page = 2
        while len(issue_comments) == 100:
            response = self._make_request(issue_comments_url, {'per_page': 100, 'page': page})
            more_comments = response.json()
            if not more_comments:
                break
            issue_count += len(more_comments)
            page += 1
        
        return review_count + issue_count
    
    def get_pr_commits(self, repo: str, pr_number: int) -> int:
        """
        Get commit count for a PR.
        
        Args:
            repo: Repository name.
            pr_number: Pull request number.
            
        Returns:
            Number of commits.
        """
        url = f"{self.base_url}/repos/{self.organization}/{repo}/pulls/{pr_number}/commits"
        response = self._make_request(url, {'per_page': 100})
        commits = response.json()
        
        # Count all commits with pagination
        commit_count = len(commits)
        page = 2
        while len(commits) == 100:
            response = self._make_request(url, {'per_page': 100, 'page': page})
            more_commits = response.json()
            if not more_commits:
                break
            commit_count += len(more_commits)
            page += 1
        
        return commit_count
    
    def get_pr_file_changes(self, repo: str, pr_number: int) -> int:
        """
        Get number of files changed in a PR.
        
        Args:
            repo: Repository name.
            pr_number: Pull request number.
            
        Returns:
            Number of files changed.
        """
        url = f"{self.base_url}/repos/{self.organization}/{repo}/pulls/{pr_number}/files"
        response = self._make_request(url, {'per_page': 100})
        files = response.json()
        
        # Count all files with pagination
        file_count = len(files)
        page = 2
        while len(files) == 100:
            response = self._make_request(url, {'per_page': 100, 'page': page})
            more_files = response.json()
            if not more_files:
                break
            file_count += len(more_files)
            page += 1
        
        return file_count
    
    def fetch_all_pr_data(self, repo_config: Dict[str, str]) -> List[Dict[str, Any]]:
        """
        Fetch complete PR data for a repository.
        
        Args:
            repo_config: Repository configuration dictionary.
            
        Returns:
            List of dictionaries with flattened PR data ready for CSV.
        """
        repo_name = repo_config['repository']
        logging.warning(f"Fetching PRs for {self.organization}/{repo_name}...")
        
        # Get all PRs
        prs = self.get_pull_requests(repo_name)
        logging.warning(f"Found {len(prs)} PRs in date range for {repo_name}")
        
        csv_data = []
        
        for idx, pr in enumerate(prs, 1):
            try:
                pr_number = pr['number']
                
                # Fetch additional details
                num_comments = self.get_pr_comments(repo_name, pr_number)
                num_commits = self.get_pr_commits(repo_name, pr_number)
                num_files_changed = self.get_pr_file_changes(repo_name, pr_number)
                
                # Extract and format data
                row = {
                    'repository': repo_name,
                    'pr_name': pr.get('title', ''),
                    'pr_number': pr_number,
                    'created_at': format_timestamp_for_csv(pr.get('created_at')),
                    'merged_at': format_timestamp_for_csv(pr.get('merged_at')),
                    'is_merged': pr.get('merged_at') is not None,
                    'num_comments': num_comments,
                    'num_commits': num_commits,
                    'num_files_changed': num_files_changed
                }
                
                csv_data.append(row)
                
                # Log progress every 10 PRs
                if idx % 10 == 0:
                    logging.warning(f"Processed {idx}/{len(prs)} PRs for {repo_name}")
                
            except Exception as e:
                logging.error(f"Failed to fetch details for PR #{pr_number} in {repo_name}: {e}")
                sys.exit(1)
        
        logging.warning(f"Completed fetching {len(csv_data)} PRs for {repo_name}")
        return csv_data

