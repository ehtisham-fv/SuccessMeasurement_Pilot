"""
Shared utility functions for the Success Measurement project.
"""

import csv
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from dotenv import load_dotenv
from dateutil import parser as dateutil_parser


def setup_logging() -> None:
    """
    Configure minimal logging (WARNING and ERROR levels only).
    """
    logging.basicConfig(
        level=logging.WARNING,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def load_env_vars() -> Dict[str, str]:
    """
    Load and validate environment variables from .env file.
    
    Returns:
        Dictionary containing validated environment variables.
        
    Raises:
        SystemExit: If required environment variables are missing.
    """
    # Load .env file from the root of success_measurement directory
    env_path = Path(__file__).parent.parent / '.env'
    
    if not env_path.exists():
        logging.error(f".env file not found at {env_path}")
        logging.error("Please create a .env file with required credentials.")
        sys.exit(1)
    
    load_dotenv(dotenv_path=env_path)
    
    # Required environment variables
    required_vars = [
        'ATLASSIAN_EMAIL',
        'ATLASSIAN_API_TOKEN',
        'ATLASSIAN_BASE_URL',
        'GITHUB_TOKEN',
        'GITHUB_ORG'
    ]
    
    env_vars = {}
    missing_vars = []
    
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
        else:
            env_vars[var] = value
    
    if missing_vars:
        logging.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        sys.exit(1)
    
    return env_vars


def load_yaml_config(config_path: str) -> Dict[str, Any]:
    """
    Parse and validate YAML configuration file.
    
    Args:
        config_path: Path to the YAML configuration file.
        
    Returns:
        Parsed configuration dictionary.
        
    Raises:
        SystemExit: If config file is missing or invalid.
    """
    config_file = Path(config_path)
    
    if not config_file.exists():
        logging.error(f"Configuration file not found: {config_path}")
        sys.exit(1)
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        logging.error(f"Error parsing YAML configuration: {e}")
        sys.exit(1)
    
    # Validate required fields
    required_fields = ['project_key', 'repositories']
    missing_fields = [field for field in required_fields if field not in config]
    
    if missing_fields:
        logging.error(f"Missing required config fields: {', '.join(missing_fields)}")
        sys.exit(1)
    
    # Set default date_range_months if not specified
    if 'date_range_months' not in config:
        config['date_range_months'] = 12
    
    return config


def write_to_csv(data: List[Dict[str, Any]], filepath: str, fieldnames: List[str]) -> None:
    """
    Write data to CSV file with proper error handling.
    
    Args:
        data: List of dictionaries containing row data.
        filepath: Path where CSV file should be written.
        fieldnames: List of column names for the CSV.
        
    Raises:
        SystemExit: If CSV writing fails.
    """
    try:
        # Ensure directory exists
        output_path = Path(filepath)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
        
        logging.warning(f"Successfully wrote {len(data)} records to {filepath}")
        
    except (IOError, OSError) as e:
        logging.error(f"Failed to write CSV file {filepath}: {e}")
        sys.exit(1)


def parse_iso_timestamp(timestamp_str: Optional[str]) -> Optional[str]:
    """
    Convert ISO 8601 timestamp to human-readable format.
    Handles various formats including Jira timestamps with milliseconds and timezones.
    
    Args:
        timestamp_str: ISO 8601 formatted timestamp string.
        
    Returns:
        Human-readable timestamp in format 'YYYY-MM-DD HH:MM:SS' or None.
    """
    if not timestamp_str:
        return None
    
    try:
        # Use dateutil parser which handles various ISO 8601 formats
        # including: 2025-10-30T15:00:10.635+0100
        dt = dateutil_parser.isoparse(timestamp_str)
        # Format to human-readable (UTC time)
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except (ValueError, AttributeError, TypeError) as e:
        logging.warning(f"Failed to parse timestamp '{timestamp_str}': {e}")
        return timestamp_str  # Return original if parsing fails


def format_timestamp_for_csv(timestamp_str: Optional[str]) -> str:
    """
    Ensure consistent human-readable timestamp format for CSV output.
    
    Args:
        timestamp_str: Timestamp string in any format.
        
    Returns:
        Formatted timestamp string or empty string if None.
    """
    if not timestamp_str:
        return ''
    
    formatted = parse_iso_timestamp(timestamp_str)
    return formatted if formatted else ''


def calculate_date_range(months: int) -> datetime:
    """
    Calculate the start date for data collection based on months from now.
    
    Args:
        months: Number of months to look back from current date.
        
    Returns:
        datetime object representing the start date (in UTC).
    """
    # Get current UTC time
    now = datetime.now(timezone.utc)
    
    # Calculate date N months ago
    # Approximate: subtract 30 days per month for simplicity
    days_back = months * 30
    start_date = now - timedelta(days=days_back)
    
    return start_date


def format_date_for_jira(dt: datetime) -> str:
    """
    Format datetime for Jira JQL query.
    
    Args:
        dt: datetime object to format.
        
    Returns:
        Formatted date string for Jira (YYYY-MM-DD).
    """
    return dt.strftime('%Y-%m-%d')


def format_date_for_github(dt: datetime) -> str:
    """
    Format datetime for GitHub API query.
    
    Args:
        dt: datetime object to format.
        
    Returns:
        ISO 8601 formatted date string for GitHub API.
    """
    return dt.isoformat()


def ensure_data_directory(project_path: str) -> None:
    """
    Ensure the data directory exists for a project.
    
    Args:
        project_path: Path to the project directory.
    """
    data_dir = Path(project_path) / 'data'
    data_dir.mkdir(parents=True, exist_ok=True)

