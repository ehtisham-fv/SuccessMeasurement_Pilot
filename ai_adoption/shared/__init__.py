"""
Shared modules for AI Adoption Analytics.

Import modules individually to avoid circular imports:
    from ai_adoption.shared.utils import load_config
    from ai_adoption.shared.cursor_client import CursorClient
    from ai_adoption.shared.csv_processor import CSVProcessor
    from ai_adoption.shared.metrics_calculator import MetricsCalculator
    from ai_adoption.shared.dashboard_generator import DashboardGenerator
"""

__all__ = [
    "utils",
    "cursor_client", 
    "csv_processor",
    "metrics_calculator",
    "dashboard_generator",
]
