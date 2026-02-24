#!/usr/bin/env python3
"""
AI Adoption Analytics - Main Entry Point

This script orchestrates the data collection, metric calculation,
and dashboard generation for Cursor IDE adoption analytics.

Usage:
    python run_analysis.py
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai_adoption.shared.utils import (
    load_config,
    load_env_vars,
    get_reference_date,
    get_inactive_thresholds,
    get_active_user_min_requests,
)
from ai_adoption.shared.cursor_client import CursorClient
from ai_adoption.shared.csv_processor import CSVProcessor
from ai_adoption.shared.metrics_calculator import MetricsCalculator
from ai_adoption.shared.dashboard_generator import DashboardGenerator


def main():
    """Main entry point for the analysis."""
    print("=" * 60)
    print("AI Adoption Analytics - Cursor IDE")
    print("=" * 60)
    print()
    
    # Step 1: Load configuration
    print("[1/6] Loading configuration...")
    config = load_config()
    env_vars = load_env_vars()
    
    api_key = env_vars.get("CURSOR_API_KEY")
    if not api_key:
        print("ERROR: CURSOR_API_KEY not found in .env file")
        print("Please create a .env file in the ai_adoption folder with:")
        print("  CURSOR_API_KEY=your_api_key_here")
        sys.exit(1)
    
    reference_date = get_reference_date(config)
    inactive_thresholds = get_inactive_thresholds(config)
    min_requests = get_active_user_min_requests(config)
    top_users_count = config.get("dashboard", {}).get("top_users_count", 20)
    output_filename = config.get("dashboard", {}).get("output_filename", "adoption_dashboard.html")
    
    print(f"   - Reference date: {reference_date}")
    print(f"   - Inactive thresholds: {inactive_thresholds} days")
    print(f"   - Active user min requests: {min_requests}")
    print()
    
    # Step 2: Fetch team members from API
    print("[2/6] Fetching team members from Cursor API...")
    try:
        api_config = config.get("api", {})
        cursor_client = CursorClient(
            api_key=api_key,
            base_url=api_config.get("base_url", "https://api.cursor.com"),
            timeout=api_config.get("timeout_seconds", 30)
        )
        
        # Test API connection
        team_data = cursor_client.get_team_members()
        print(f"   - Total team members: {team_data['summary']['total_members']}")
        print(f"   - Active members: {team_data['summary']['active_count']}")
        print(f"   - Owners: {team_data['summary']['owners_count']}")
        print(f"   - Removed: {team_data['summary']['removed_count']}")
        print()
        
    except Exception as e:
        print(f"ERROR: Failed to fetch team members: {e}")
        print("Please check your API key and network connection.")
        sys.exit(1)
    
    # Step 3: Process CSV data
    print("[3/6] Processing monthly usage CSV files...")
    csv_processor = CSVProcessor(min_requests_threshold=min_requests)
    csv_data = csv_processor.process_all_files()
    
    print(f"   - Months processed: {len(csv_data['monthly_stats'])}")
    print(f"   - Unique users in data: {len(csv_data['all_users'])}")
    print(f"   - Total requests: {sum(csv_data['user_totals'].values()):,.1f}")
    print()
    
    # Step 4: Calculate metrics
    print("[4/6] Calculating adoption metrics...")
    metrics_calculator = MetricsCalculator(
        cursor_client=cursor_client,
        csv_processor=csv_processor,
        reference_date=reference_date,
        inactive_thresholds=inactive_thresholds,
        top_users_count=top_users_count
    )
    
    metrics = metrics_calculator.calculate_metrics()
    
    # Calculate adoption rate
    active_in_30 = metrics.active_members_count - len(metrics.inactive_30_days)
    adoption_rate = (active_in_30 / metrics.active_members_count * 100) if metrics.active_members_count > 0 else 0
    
    print(f"   - 30-day active users: {active_in_30}")
    print(f"   - 30-day adoption rate: {adoption_rate:.1f}%")
    print(f"   - Inactive 30 days: {len(metrics.inactive_30_days)}")
    print(f"   - Inactive 60 days: {len(metrics.inactive_60_days)}")
    print(f"   - Inactive 90 days: {len(metrics.inactive_90_days)}")
    print(f"   - Never used: {len(metrics.never_used)}")
    print()
    
    # Step 5: Generate dashboard
    print("[5/6] Generating HTML dashboard...")
    dashboard_generator = DashboardGenerator(output_filename=output_filename)
    output_path = dashboard_generator.generate(metrics)
    print(f"   - Dashboard saved to: {output_path}")
    print()
    
    # Step 6: Summary
    print("[6/6] Analysis complete!")
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Team Members with Access:  {metrics.active_members_count}")
    print(f"  Active Users (30 days):    {active_in_30}")
    print(f"  Adoption Rate:             {adoption_rate:.1f}%")
    print(f"  Total Requests (all time): {metrics.total_requests_all_time:,.1f}")
    print()
    print(f"  Dashboard: {output_path}")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
