"""
Utility functions for AI Adoption Analytics module.
"""

import os
import yaml
from datetime import datetime, date
from pathlib import Path
from dotenv import load_dotenv


def get_module_root() -> Path:
    """Get the root path of the ai_adoption module."""
    return Path(__file__).parent.parent


def load_env_vars() -> dict:
    """
    Load environment variables from .env file.
    
    Returns:
        dict: Dictionary containing environment variables
    """
    module_root = get_module_root()
    env_path = module_root / ".env"
    
    if env_path.exists():
        load_dotenv(env_path)
    else:
        # Try parent directory
        parent_env = module_root.parent / ".env"
        if parent_env.exists():
            load_dotenv(parent_env)
    
    return {
        "CURSOR_API_KEY": os.getenv("CURSOR_API_KEY"),
    }


def load_config(config_path: str = None) -> dict:
    """
    Load configuration from YAML file.
    
    Args:
        config_path: Optional path to config file. Defaults to config.yaml in module root.
        
    Returns:
        dict: Configuration dictionary
    """
    if config_path is None:
        config_path = get_module_root() / "config.yaml"
    
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    
    return config


def get_reference_date(config: dict) -> date:
    """
    Get the reference date for inactive user calculation.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        date: Reference date (from config or today)
    """
    ref_date_str = config.get("analysis", {}).get("reference_date")
    
    if ref_date_str is None:
        return date.today()
    
    return datetime.strptime(ref_date_str, "%Y-%m-%d").date()


def get_inactive_thresholds(config: dict) -> list:
    """
    Get the inactive user thresholds from config.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        list: List of threshold days [30, 60, 90]
    """
    return config.get("analysis", {}).get("inactive_thresholds_days", [30, 60, 90])


def get_active_user_min_requests(config: dict) -> float:
    """
    Get the minimum requests threshold to be considered active.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        float: Minimum request count (default: 1)
    """
    return config.get("analysis", {}).get("active_user_min_requests", 1)


def get_data_path() -> Path:
    """Get the path to the data directory."""
    return get_module_root() / "data"


def get_monthly_data_path() -> Path:
    """Get the path to monthly usage data directory."""
    return get_data_path() / "monthly_usage_data"


def format_number(value: float, decimals: int = 1) -> str:
    """
    Format a number for display with thousands separator.
    
    Args:
        value: Number to format
        decimals: Number of decimal places
        
    Returns:
        str: Formatted number string
    """
    if decimals == 0:
        return f"{int(value):,}"
    return f"{value:,.{decimals}f}"


def parse_month_year_from_filename(filename: str) -> tuple:
    """
    Parse month and year from CSV filename.
    
    Expected format: MM-YYYY-team-usage-events.csv
    Example: 12-2025-team-usage-events.csv -> (12, 2025)
    
    Args:
        filename: CSV filename
        
    Returns:
        tuple: (month, year) as integers
    """
    parts = filename.split("-")
    if len(parts) >= 2:
        try:
            month = int(parts[0])
            year = int(parts[1])
            return (month, year)
        except ValueError:
            pass
    return (None, None)


def get_month_name(month: int) -> str:
    """
    Get month name from month number.
    
    Args:
        month: Month number (1-12)
        
    Returns:
        str: Month name
    """
    months = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]
    if 1 <= month <= 12:
        return months[month - 1]
    return f"Month {month}"
