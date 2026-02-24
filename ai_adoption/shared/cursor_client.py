"""
Cursor API Client for team membership data.

Uses the Cursor Admin API to fetch team member information.
API Documentation: https://cursor.com/docs/account/teams/admin-api
"""

import requests
from requests.auth import HTTPBasicAuth
from typing import Optional
from dataclasses import dataclass


@dataclass
class TeamMember:
    """Represents a team member from the Cursor API."""
    name: str
    email: str
    user_id: str
    role: str
    is_removed: bool
    
    @property
    def is_owner(self) -> bool:
        """Check if member is an owner."""
        return self.role in ["owner", "free-owner"]
    
    @property
    def is_active(self) -> bool:
        """Check if member has active access."""
        return not self.is_removed


class CursorClient:
    """
    Client for interacting with Cursor Admin API.
    
    Uses Basic Authentication with API key.
    """
    
    def __init__(self, api_key: str, base_url: str = "https://api.cursor.com", timeout: int = 30):
        """
        Initialize the Cursor API client.
        
        Args:
            api_key: Cursor API key for authentication
            base_url: Base URL for API (default: https://api.cursor.com)
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        
        if not api_key:
            raise ValueError("CURSOR_API_KEY is required")
    
    def _make_request(self, endpoint: str, params: Optional[dict] = None) -> dict:
        """
        Make an authenticated request to the Cursor API.
        
        Args:
            endpoint: API endpoint path
            params: Optional query parameters
            
        Returns:
            dict: JSON response
            
        Raises:
            requests.HTTPError: If request fails
        """
        url = f"{self.base_url}{endpoint}"
        
        response = requests.get(
            url,
            auth=HTTPBasicAuth(self.api_key, ""),
            params=params,
            timeout=self.timeout
        )
        
        response.raise_for_status()
        return response.json()
    
    def get_team_members(self) -> dict:
        """
        Fetch all team members from the Cursor API.
        
        Returns:
            dict: Contains:
                - 'all_members': List of all TeamMember objects
                - 'active_members': List of members with active access
                - 'owners': List of owner members
                - 'removed_members': List of removed members
                - 'summary': Dict with counts
        """
        response = self._make_request("/teams/members")
        
        members_data = response.get("teamMembers", [])
        
        all_members = []
        active_members = []
        owners = []
        removed_members = []
        
        for member_data in members_data:
            member = TeamMember(
                name=member_data.get("name", ""),
                email=member_data.get("email", ""),
                user_id=member_data.get("id", ""),
                role=member_data.get("role", "member"),
                is_removed=member_data.get("isRemoved", False)
            )
            
            all_members.append(member)
            
            if member.is_active:
                active_members.append(member)
                if member.is_owner:
                    owners.append(member)
            else:
                removed_members.append(member)
        
        # Sort by name for consistent display
        active_members.sort(key=lambda m: m.name.lower() if m.name else m.email.lower())
        owners.sort(key=lambda m: m.name.lower() if m.name else m.email.lower())
        removed_members.sort(key=lambda m: m.name.lower() if m.name else m.email.lower())
        
        return {
            "all_members": all_members,
            "active_members": active_members,
            "owners": owners,
            "removed_members": removed_members,
            "summary": {
                "total_members": len(all_members),
                "active_count": len(active_members),
                "owners_count": len(owners),
                "removed_count": len(removed_members)
            }
        }
    
    def get_active_member_emails(self) -> set:
        """
        Get a set of all active member emails.
        
        Useful for cross-referencing with usage data.
        
        Returns:
            set: Set of email addresses (lowercase)
        """
        result = self.get_team_members()
        return {m.email.lower() for m in result["active_members"]}
