#!/usr/bin/env python3
"""
Main analysis script for Omnichannel Customer Account project.
Fetches GitHub and Jira data and stores in CSV files.
"""

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
    ensure_data_directory
)
from shared.github_client import GitHubClient
from shared.jira_client import JiraClient


def temp_main():
    # Setup logging (minimal - WARNING/ERROR only)
    setup_logging()

    logging.warning("=" * 60)
    logging.warning("SUCCESS MEASUREMENT - DATA COLLECTION")
    logging.warning("Project: Omnichannel Customer Account")
    logging.warning("=" * 60)

    # Get the project directory
    project_dir = Path(__file__).parent

    # Load environment variables
    logging.warning("Loading environment variables...")
    try:
        env_vars = load_env_vars()
    except SystemExit:
        logging.error("Failed to load environment variables. Aborting.")
        sys.exit(1)

    # Load project configuration
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

    # Initialize GitHub client
    logging.warning("\n" + "=" * 60)
    logging.warning("PHASE 1: FETCHING GITHUB DATA")
    logging.warning("=" * 60)


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

    # Print summary
    logging.warning("\n" + "=" * 60)
    logging.warning("SUMMARY")
    logging.warning("=" * 60)
    logging.warning(f"Total Jira Issues: {len(jira_data)}")
    logging.warning(f"\nData saved to:")
    logging.warning(f"  - Jira:   {project_dir / 'data' / 'jira_data.csv'}")
    logging.warning("\n" + "=" * 60)
    logging.warning("DATA COLLECTION COMPLETED SUCCESSFULLY")
    logging.warning("=" * 60)

    sys.exit(0)


def main():
    """Main execution function."""
    
    # Setup logging (minimal - WARNING/ERROR only)
    setup_logging()
    
    logging.warning("=" * 60)
    logging.warning("SUCCESS MEASUREMENT - DATA COLLECTION")
    logging.warning("Project: Omnichannel Customer Account")
    logging.warning("=" * 60)
    
    # Get the project directory
    project_dir = Path(__file__).parent
    
    # Load environment variables
    logging.warning("Loading environment variables...")
    try:
        env_vars = load_env_vars()
    except SystemExit:
        logging.error("Failed to load environment variables. Aborting.")
        sys.exit(1)
    
    # Load project configuration
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
    
    # Print summary
    logging.warning("\n" + "=" * 60)
    logging.warning("SUMMARY")
    logging.warning("=" * 60)
    logging.warning(f"Total Pull Requests: {len(all_github_data)}")
    logging.warning(f"Total Jira Issues: {len(jira_data)}")
    logging.warning(f"\nData saved to:")
    logging.warning(f"  - GitHub: {project_dir / 'data' / 'github_data.csv'}")
    logging.warning(f"  - Jira:   {project_dir / 'data' / 'jira_data.csv'}")
    logging.warning("\n" + "=" * 60)
    logging.warning("DATA COLLECTION COMPLETED SUCCESSFULLY")
    logging.warning("=" * 60)
    
    sys.exit(0)


if __name__ == '__main__':
    #main()
    temp_main()

