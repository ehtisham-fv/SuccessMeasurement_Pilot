"""
Metrics Calculator for AI Adoption Analytics.

Combines team membership data (API) with usage data (CSV) to calculate
adoption metrics and identify inactive users.
"""

from datetime import date, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional

from .cursor_client import CursorClient, TeamMember
from .csv_processor import CSVProcessor, MonthlyStats


@dataclass
class InactiveUserInfo:
    """Information about an inactive user."""
    email: str
    name: str
    role: str
    last_activity: Optional[date]
    days_inactive: int


@dataclass
class AdoptionMetrics:
    """Complete adoption metrics for dashboard generation."""
    # Team membership (from API)
    total_team_members: int = 0
    active_members_count: int = 0
    owners_count: int = 0
    removed_members_count: int = 0
    
    # Active members list
    active_members: List[TeamMember] = field(default_factory=list)
    owners: List[TeamMember] = field(default_factory=list)
    removed_members: List[TeamMember] = field(default_factory=list)
    
    # Monthly usage stats (from CSV)
    monthly_stats: List[MonthlyStats] = field(default_factory=list)
    
    # User rankings
    top_users: List[tuple] = field(default_factory=list)  # (email, requests)
    
    # Inactive users (have access but no recent activity)
    inactive_30_days: List[InactiveUserInfo] = field(default_factory=list)
    inactive_60_days: List[InactiveUserInfo] = field(default_factory=list)
    inactive_90_days: List[InactiveUserInfo] = field(default_factory=list)
    
    # Users with access who never used the tool
    never_used: List[InactiveUserInfo] = field(default_factory=list)
    
    # Summary stats
    total_requests_all_time: float = 0.0
    current_month_active_users: int = 0
    
    # Reference date used for calculations
    reference_date: date = field(default_factory=date.today)


class MetricsCalculator:
    """
    Calculator that combines API and CSV data to produce adoption metrics.
    """
    
    def __init__(
        self,
        cursor_client: CursorClient,
        csv_processor: CSVProcessor,
        reference_date: date,
        inactive_thresholds: List[int] = None,
        top_users_count: int = 20
    ):
        """
        Initialize the metrics calculator.
        
        Args:
            cursor_client: Initialized CursorClient for API calls
            csv_processor: Initialized CSVProcessor with processed data
            reference_date: Date to use for inactive user calculations
            inactive_thresholds: Days thresholds for inactive detection [30, 60, 90]
            top_users_count: Number of top users to include in leaderboard
        """
        self.cursor_client = cursor_client
        self.csv_processor = csv_processor
        self.reference_date = reference_date
        self.inactive_thresholds = inactive_thresholds or [30, 60, 90]
        self.top_users_count = top_users_count
    
    def calculate_metrics(self) -> AdoptionMetrics:
        """
        Calculate all adoption metrics.
        
        Returns:
            AdoptionMetrics: Complete metrics object for dashboard
        """
        metrics = AdoptionMetrics(reference_date=self.reference_date)
        
        # Get team membership from API
        team_data = self.cursor_client.get_team_members()
        
        metrics.total_team_members = team_data["summary"]["total_members"]
        metrics.active_members_count = team_data["summary"]["active_count"]
        metrics.owners_count = team_data["summary"]["owners_count"]
        metrics.removed_members_count = team_data["summary"]["removed_count"]
        
        metrics.active_members = team_data["active_members"]
        metrics.owners = team_data["owners"]
        metrics.removed_members = team_data["removed_members"]
        
        # Get usage data from CSV
        csv_data = self.csv_processor.process_all_files()
        
        metrics.monthly_stats = csv_data["monthly_stats"]
        metrics.top_users = self.csv_processor.get_top_users(self.top_users_count)
        
        # Calculate total requests
        metrics.total_requests_all_time = sum(csv_data["user_totals"].values())
        
        # Get current month active users (most recent month in data)
        if metrics.monthly_stats:
            latest_month = metrics.monthly_stats[-1]
            metrics.current_month_active_users = latest_month.active_users
        
        # Build set of active member emails for cross-reference
        active_member_emails = {m.email.lower() for m in metrics.active_members}
        
        # Build lookup for member info
        member_lookup = {m.email.lower(): m for m in metrics.active_members}
        
        # Users who have access but appear in CSV data
        users_with_activity = set(csv_data["user_last_activity"].keys())
        
        # Calculate inactive users for each threshold
        for threshold in self.inactive_thresholds:
            inactive_list = self._find_inactive_users(
                active_member_emails=active_member_emails,
                member_lookup=member_lookup,
                user_last_activity=csv_data["user_last_activity"],
                threshold_days=threshold
            )
            
            if threshold == 30:
                metrics.inactive_30_days = inactive_list
            elif threshold == 60:
                metrics.inactive_60_days = inactive_list
            elif threshold == 90:
                metrics.inactive_90_days = inactive_list
        
        # Find users who have access but NEVER used the tool
        metrics.never_used = self._find_never_used_users(
            active_member_emails=active_member_emails,
            member_lookup=member_lookup,
            users_with_activity=users_with_activity
        )
        
        return metrics
    
    def _find_inactive_users(
        self,
        active_member_emails: Set[str],
        member_lookup: Dict[str, TeamMember],
        user_last_activity: Dict[str, date],
        threshold_days: int
    ) -> List[InactiveUserInfo]:
        """
        Find users who have access but haven't been active within threshold.
        
        Args:
            active_member_emails: Set of emails with active access
            member_lookup: Dict to look up member info by email
            user_last_activity: Dict of email -> last activity date
            threshold_days: Number of days to consider inactive
            
        Returns:
            List of InactiveUserInfo for inactive users
        """
        cutoff_date = self.reference_date - timedelta(days=threshold_days)
        inactive_users = []
        
        for email in active_member_emails:
            last_activity = user_last_activity.get(email)
            
            # User has never been active OR last activity is before cutoff
            if last_activity is None or last_activity < cutoff_date:
                member = member_lookup.get(email)
                
                if last_activity:
                    days_inactive = (self.reference_date - last_activity).days
                else:
                    days_inactive = -1  # Never used
                
                inactive_users.append(InactiveUserInfo(
                    email=email,
                    name=member.name if member else "",
                    role=member.role if member else "unknown",
                    last_activity=last_activity,
                    days_inactive=days_inactive
                ))
        
        # Sort by days inactive (most inactive first), then by name
        inactive_users.sort(key=lambda u: (-u.days_inactive if u.days_inactive > 0 else float('inf'), u.name.lower()))
        
        return inactive_users
    
    def _find_never_used_users(
        self,
        active_member_emails: Set[str],
        member_lookup: Dict[str, TeamMember],
        users_with_activity: Set[str]
    ) -> List[InactiveUserInfo]:
        """
        Find users who have access but have never used the tool.
        
        Args:
            active_member_emails: Set of emails with active access
            member_lookup: Dict to look up member info by email
            users_with_activity: Set of emails that appear in usage data
            
        Returns:
            List of InactiveUserInfo for users who never used the tool
        """
        never_used = []
        
        for email in active_member_emails:
            if email not in users_with_activity:
                member = member_lookup.get(email)
                
                never_used.append(InactiveUserInfo(
                    email=email,
                    name=member.name if member else "",
                    role=member.role if member else "unknown",
                    last_activity=None,
                    days_inactive=-1
                ))
        
        # Sort by name
        never_used.sort(key=lambda u: u.name.lower() if u.name else u.email.lower())
        
        return never_used
    
    def get_adoption_rate(self, metrics: AdoptionMetrics, days: int = 30) -> float:
        """
        Calculate adoption rate as percentage of team members who are active.
        
        Args:
            metrics: Calculated AdoptionMetrics
            days: Time period to consider for activity
            
        Returns:
            float: Adoption rate percentage (0-100)
        """
        if metrics.active_members_count == 0:
            return 0.0
        
        # Count users with activity in the period
        if days == 30:
            inactive_count = len(metrics.inactive_30_days)
        elif days == 60:
            inactive_count = len(metrics.inactive_60_days)
        elif days == 90:
            inactive_count = len(metrics.inactive_90_days)
        else:
            inactive_count = 0
        
        active_usage_count = metrics.active_members_count - inactive_count
        
        return (active_usage_count / metrics.active_members_count) * 100
