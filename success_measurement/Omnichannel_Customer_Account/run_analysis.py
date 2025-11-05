#!/usr/bin/env python3
"""
Main analysis script for Omnichannel Customer Account project.
Fetches GitHub and Jira data, calculates metrics, and generates dashboard.

Usage:
    python3 run_analysis.py all          # Fetch data + calculate metrics + generate dashboard
    python3 run_analysis.py fetch_data   # Only fetch GitHub and Jira data
    python3 run_analysis.py metrics      # Only calculate metrics and generate dashboard
"""

import argparse
import logging
import sys
from pathlib import Path

# Add parent directory to path to import shared modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.utils import (
    setup_logging,
    load_env_vars,
    load_yaml_config,
    write_to_csv,
    ensure_data_directory,
    load_csv_to_dict,
    csv_exists
)
from shared.github_client import GitHubClient
from shared.jira_client import JiraClient
from shared.metrics_calculator import calculate_all_metrics
from shared.dashboard_generator import generate_html_dashboard


def main():
    """Main execution function."""
    
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description='Success Measurement Analysis Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 run_analysis.py all          # Full execution (default)
  python3 run_analysis.py fetch_data   # Only fetch data from APIs
  python3 run_analysis.py metrics      # Only calculate metrics from existing CSVs
        """
    )
    parser.add_argument(
        'mode',
        nargs='?',
        default='all',
        choices=['all', 'fetch_data', 'metrics'],
        help='Execution mode (default: all)'
    )
    
    args = parser.parse_args()
    mode = args.mode
    
    # Setup logging (minimal - WARNING/ERROR only)
    setup_logging()
    
    logging.warning("=" * 60)
    logging.warning("SUCCESS MEASUREMENT - DATA COLLECTION & METRICS")
    logging.warning("Project: Omnichannel Customer Account")
    logging.warning(f"Execution Mode: {mode.upper()}")
    logging.warning("=" * 60)
    
    # Get the project directory
    project_dir = Path(__file__).parent
    
    # Load project configuration (always needed)
    config_path = project_dir / 'config.yaml'
    logging.warning(f"Loading configuration from {config_path}...")
    try:
        config = load_yaml_config(str(config_path))
    except SystemExit:
        logging.error("Failed to load configuration. Aborting.")
        sys.exit(1)
    
    # Ensure data directory exists
    ensure_data_directory(str(project_dir))
    
    # Extract configuration
    project_name = config.get('project_name', 'Unknown')
    project_key = config.get('project_key')
    repositories = config.get('repositories', [])
    date_range_months = config.get('date_range_months', 12)
    
    logging.warning(f"Project: {project_name}")
    logging.warning(f"Date Range: Last {date_range_months} months")
    logging.warning(f"Repositories: {len(repositories)}")
    logging.warning(f"Jira Project Key: {project_key}")
    
    # ==========================================================================
    # DATA FETCHING PHASE (modes: 'all' or 'fetch_data')
    # ==========================================================================
    
    if mode in ['all', 'fetch_data']:
        # Load environment variables (only needed for data fetching)
        logging.warning("\nLoading environment variables...")
        try:
            env_vars = load_env_vars()
        except SystemExit:
            logging.error("Failed to load environment variables. Aborting.")
            sys.exit(1)
        
        # Initialize GitHub client
        logging.warning("\n" + "=" * 60)
        logging.warning("PHASE 1: FETCHING GITHUB DATA")
        logging.warning("=" * 60)
        
        try:
            github_client = GitHubClient(
                token=env_vars['GITHUB_TOKEN'],
                organization=env_vars['GITHUB_ORG'],
                date_range_months=date_range_months
            )
        except Exception as e:
            logging.error(f"Failed to initialize GitHub client: {e}")
            sys.exit(1)
        
        # Fetch GitHub data for all repositories
        all_github_data = []
        
        for repo_config in repositories:
            try:
                repo_data = github_client.fetch_all_pr_data(repo_config)
                all_github_data.extend(repo_data)
            except Exception as e:
                logging.error(f"Failed to fetch GitHub data for {repo_config['repository']}: {e}")
                sys.exit(1)
        
        # Write GitHub data to CSV
        if all_github_data:
            github_csv_path = project_dir / 'data' / 'github_data.csv'
            github_fieldnames = [
                'repository',
                'pr_name',
                'pr_number',
                'created_at',
                'merged_at',
                'is_merged',
                'num_comments',
                'num_commits',
                'num_files_changed'
            ]
            
            try:
                write_to_csv(all_github_data, str(github_csv_path), github_fieldnames)
            except SystemExit:
                logging.error("Failed to write GitHub CSV. Aborting.")
                sys.exit(1)
        else:
            logging.warning("No GitHub data found in the specified date range.")
        
        # Initialize Jira client
        logging.warning("\n" + "=" * 60)
        logging.warning("PHASE 2: FETCHING JIRA DATA")
        logging.warning("=" * 60)
        
        try:
            jira_client = JiraClient(
                email=env_vars['ATLASSIAN_EMAIL'],
                api_token=env_vars['ATLASSIAN_API_TOKEN'],
                base_url=env_vars['ATLASSIAN_BASE_URL'],
                date_range_months=date_range_months
            )
        except Exception as e:
            logging.error(f"Failed to initialize Jira client: {e}")
            sys.exit(1)
        
        # Fetch Jira data
        try:
            jira_data = jira_client.fetch_all_jira_data(project_key, config)
        except Exception as e:
            logging.error(f"Failed to fetch Jira data: {e}")
            sys.exit(1)
        
        # Write Jira data to CSV
        if jira_data:
            jira_csv_path = project_dir / 'data' / 'jira_data.csv'
            jira_fieldnames = [
                'ticket_key',
                'summary',
                'type',
                'created',
                'in_progress_timestamp',
                'done_timestamp'
            ]
            
            try:
                write_to_csv(jira_data, str(jira_csv_path), jira_fieldnames)
            except SystemExit:
                logging.error("Failed to write Jira CSV. Aborting.")
                sys.exit(1)
        else:
            logging.warning("No Jira data found in the specified date range.")
        
        logging.warning("\n" + "=" * 60)
        logging.warning("DATA COLLECTION COMPLETED SUCCESSFULLY")
        logging.warning("=" * 60)
    
    # ==========================================================================
    # METRICS CALCULATION PHASE (modes: 'all' or 'metrics')
    # ==========================================================================
    
    if mode in ['all', 'metrics']:
        logging.warning("\n" + "=" * 60)
        logging.warning("PHASE 3: CALCULATING METRICS")
        logging.warning("=" * 60)
        
        # Define CSV paths
        github_csv_path = project_dir / 'data' / 'github_data.csv'
        jira_csv_path = project_dir / 'data' / 'jira_data.csv'
        
        # Check if CSV files exist
        if not csv_exists(str(github_csv_path)):
            logging.error(f"GitHub CSV not found: {github_csv_path}")
            logging.error("Please run data collection first: python3 run_analysis.py fetch_data")
            sys.exit(1)
        
        if not csv_exists(str(jira_csv_path)):
            logging.error(f"Jira CSV not found: {jira_csv_path}")
            logging.error("Please run data collection first: python3 run_analysis.py fetch_data")
            sys.exit(1)
        
        # Load CSV data
        logging.warning("Loading existing CSV data...")
        github_data = load_csv_to_dict(str(github_csv_path))
        jira_data = load_csv_to_dict(str(jira_csv_path))
        
        # Calculate metrics
        logging.warning("Calculating metrics...")
        try:
            metrics_results = calculate_all_metrics(jira_data, github_data, config)
        except Exception as e:
            logging.error(f"Failed to calculate metrics: {e}")
            sys.exit(1)
        
        # Generate HTML dashboard
        logging.warning("\n" + "=" * 60)
        logging.warning("PHASE 4: GENERATING HTML DASHBOARD")
        logging.warning("=" * 60)
        
        dashboard_path = project_dir / 'data' / 'metrics_dashboard.html'
        
        try:
            generate_html_dashboard(metrics_results, str(dashboard_path))
            logging.warning(f"Dashboard saved to: {dashboard_path}")
        except Exception as e:
            logging.error(f"Failed to generate dashboard: {e}")
            sys.exit(1)
        
        # Print metrics summary
        logging.warning("\n" + "=" * 60)
        logging.warning("METRICS SUMMARY")
        logging.warning("=" * 60)
        
        if 'change_lead_time' in metrics_results:
            clt = metrics_results['change_lead_time']
            logging.warning(f"Change Lead Time (Median): {clt.get('median_days', 0):.1f} days")
            logging.warning(f"  Based on {clt.get('matched_pr_count', 0)} matched PRs")
        
        if 'cycle_time' in metrics_results:
            ct = metrics_results['cycle_time']
            logging.warning(f"Cycle Time (Median): {ct.get('median_days', 0):.1f} days")
            logging.warning(f"  Based on {ct.get('completed_count', 0)} completed issues")
        
        if 'bug_resolution_time' in metrics_results:
            brt = metrics_results['bug_resolution_time']
            logging.warning(f"Bug Resolution Time (Median): {brt.get('median_days', 0):.1f} days")
            logging.warning(f"  Based on {brt.get('completed_count', 0)} completed bugs")
        
        logging.warning(f"\nDashboard: {dashboard_path}")
        logging.warning("\n" + "=" * 60)
        logging.warning("METRICS GENERATION COMPLETED SUCCESSFULLY")
        logging.warning("=" * 60)
    
    sys.exit(0)


if __name__ == '__main__':
    main()

