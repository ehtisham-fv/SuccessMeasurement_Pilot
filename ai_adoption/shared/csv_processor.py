"""
CSV Processor for monthly usage data.

Parses the team usage CSV exports and aggregates usage statistics.
"""

import csv
from pathlib import Path
from datetime import datetime, date
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from collections import defaultdict

from .utils import get_monthly_data_path, parse_month_year_from_filename, get_month_name


@dataclass
class UserMonthlyUsage:
    """Usage statistics for a user in a specific month."""
    email: str
    month: int
    year: int
    total_requests: float = 0.0
    interaction_count: int = 0  # Number of rows/interactions
    
    @property
    def month_year_str(self) -> str:
        """Get formatted month-year string."""
        return f"{get_month_name(self.month)} {self.year}"
    
    @property
    def sort_key(self) -> tuple:
        """Key for chronological sorting."""
        return (self.year, self.month)


@dataclass
class MonthlyStats:
    """Aggregate statistics for a month."""
    month: int
    year: int
    active_users: int = 0
    total_requests: float = 0.0
    total_interactions: int = 0
    user_details: Dict[str, UserMonthlyUsage] = field(default_factory=dict)
    
    @property
    def month_year_str(self) -> str:
        """Get formatted month-year string."""
        return f"{get_month_name(self.month)} {self.year}"
    
    @property
    def sort_key(self) -> tuple:
        """Key for chronological sorting."""
        return (self.year, self.month)


class CSVProcessor:
    """
    Processor for monthly team usage CSV files.
    
    Expected CSV format:
    - Columns: Date, User, Service Account Name, Service Account ID, Kind, 
               Model, Max Mode, Input (w/ Cache Write), Input (w/o Cache Write),
               Cache Read, Output Tokens, Total Tokens, Requests
    - Filename pattern: MM-YYYY-team-usage-events.csv
    """
    
    def __init__(self, data_path: Optional[Path] = None, min_requests_threshold: float = 1.0):
        """
        Initialize the CSV processor.
        
        Args:
            data_path: Path to monthly_usage_data directory
            min_requests_threshold: Minimum requests to count as active user
        """
        self.data_path = data_path or get_monthly_data_path()
        self.min_requests_threshold = min_requests_threshold
        self._monthly_stats: Dict[tuple, MonthlyStats] = {}
        self._user_totals: Dict[str, float] = defaultdict(float)
        self._user_last_activity: Dict[str, date] = {}
    
    def process_all_files(self) -> dict:
        """
        Process all CSV files in the monthly data directory.
        
        Returns:
            dict: Contains:
                - 'monthly_stats': List of MonthlyStats sorted chronologically
                - 'user_totals': Dict of email -> total requests across all months
                - 'user_last_activity': Dict of email -> last activity date
                - 'all_users': Set of all unique user emails
        """
        csv_files = sorted(self.data_path.glob("*.csv"))
        
        for csv_file in csv_files:
            self._process_file(csv_file)
        
        # Sort monthly stats chronologically
        monthly_stats = sorted(
            self._monthly_stats.values(),
            key=lambda s: s.sort_key
        )
        
        return {
            "monthly_stats": monthly_stats,
            "user_totals": dict(self._user_totals),
            "user_last_activity": dict(self._user_last_activity),
            "all_users": set(self._user_totals.keys())
        }
    
    def _process_file(self, csv_file: Path) -> None:
        """
        Process a single CSV file.
        
        Args:
            csv_file: Path to CSV file
        """
        month, year = parse_month_year_from_filename(csv_file.name)
        if month is None or year is None:
            print(f"Warning: Could not parse month/year from {csv_file.name}")
            return
        
        key = (year, month)
        if key not in self._monthly_stats:
            self._monthly_stats[key] = MonthlyStats(month=month, year=year)
        
        stats = self._monthly_stats[key]
        user_requests: Dict[str, float] = defaultdict(float)
        user_interactions: Dict[str, int] = defaultdict(int)
        
        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                email = row.get("User", "").strip().lower()
                if not email:
                    continue
                
                # Parse requests (can be decimal or empty)
                requests_str = row.get("Requests", "0").strip()
                try:
                    requests = float(requests_str) if requests_str else 0.0
                except ValueError:
                    requests = 0.0
                
                # Aggregate per user
                user_requests[email] += requests
                user_interactions[email] += 1
                
                # Track total requests
                stats.total_requests += requests
                stats.total_interactions += 1
                
                # Update user totals across all months
                self._user_totals[email] += requests
                
                # Track last activity date
                date_str = row.get("Date", "")
                if date_str:
                    try:
                        activity_date = datetime.fromisoformat(date_str.replace("Z", "+00:00")).date()
                        if email not in self._user_last_activity or activity_date > self._user_last_activity[email]:
                            self._user_last_activity[email] = activity_date
                    except (ValueError, AttributeError):
                        pass
        
        # Build user details for this month
        for email, requests in user_requests.items():
            stats.user_details[email] = UserMonthlyUsage(
                email=email,
                month=month,
                year=year,
                total_requests=requests,
                interaction_count=user_interactions[email]
            )
        
        # Count active users (meeting minimum threshold)
        stats.active_users = sum(
            1 for r in user_requests.values() 
            if r >= self.min_requests_threshold
        )
    
    def get_users_inactive_since(self, reference_date: date, days: int) -> List[str]:
        """
        Get users who have been inactive for at least N days.
        
        Args:
            reference_date: Date to calculate from
            days: Number of days threshold
            
        Returns:
            List of user emails who are inactive
        """
        cutoff_date = date(
            reference_date.year,
            reference_date.month,
            reference_date.day
        )
        
        # Calculate cutoff by subtracting days
        from datetime import timedelta
        cutoff_date = reference_date - timedelta(days=days)
        
        inactive_users = []
        for email, last_activity in self._user_last_activity.items():
            if last_activity < cutoff_date:
                inactive_users.append(email)
        
        return sorted(inactive_users)
    
    def get_top_users(self, n: int = 20) -> List[tuple]:
        """
        Get top N users by total request count.
        
        Args:
            n: Number of top users to return
            
        Returns:
            List of (email, total_requests) tuples sorted by requests descending
        """
        sorted_users = sorted(
            self._user_totals.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return sorted_users[:n]
    
    def get_user_monthly_breakdown(self, email: str) -> List[UserMonthlyUsage]:
        """
        Get monthly breakdown for a specific user.
        
        Args:
            email: User email address
            
        Returns:
            List of UserMonthlyUsage sorted chronologically
        """
        email_lower = email.lower()
        breakdown = []
        
        for stats in self._monthly_stats.values():
            if email_lower in stats.user_details:
                breakdown.append(stats.user_details[email_lower])
        
        return sorted(breakdown, key=lambda u: u.sort_key)
