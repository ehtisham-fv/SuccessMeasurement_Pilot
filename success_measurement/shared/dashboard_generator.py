#!/usr/bin/env python3
"""
HTML Dashboard Generator for success measurement metrics.
Creates a visual dashboard based on calculated metrics.
"""

from typing import Dict, Any
from datetime import datetime


def format_time_duration(hours: float) -> str:
    """
    Format time duration for display.
    
    Args:
        hours: Duration in hours.
        
    Returns:
        Formatted string (e.g., "5.2 days" or "125.3 hours").
    """
    if hours == 0:
        return "0 hours"
    
    days = hours / 24
    if days >= 1:
        return f"{days:.1f} days"
    else:
        return f"{hours:.1f} hours"


def create_summary_cards_html(metrics: Dict[str, Any]) -> str:
    """Generate HTML for summary cards section."""
    summary = metrics.get('summary', {})
    
    return f"""
        <div class="summary-cards">
            <div class="summary-card">
                <h3>Total JIRA Issues</h3>
                <div class="number">{summary.get('total_jira_issues', 0)}</div>
                <p>All issues in date range</p>
            </div>
            <div class="summary-card">
                <h3>Matched PRs</h3>
                <div class="number">{summary.get('matched_prs', 0)}</div>
                <p>PRs with Jira issues</p>
            </div>
            <div class="summary-card">
                <h3>Total Pull Requests</h3>
                <div class="number">{summary.get('total_prs', 0)}</div>
                <p>Across all repositories</p>
            </div>
            <div class="summary-card">
                <h3>Non-Merged PRs</h3>
                <div class="number">{summary.get('non_merged_prs', 0)}</div>
                <p>Still open or closed</p>
            </div>
        </div>
    """


def create_change_lead_time_section(metrics: Dict[str, Any]) -> str:
    """Generate HTML for Change Lead Time metrics section."""
    clt = metrics.get('change_lead_time', {})
    
    if not clt or clt.get('matched_pr_count', 0) == 0:
        return """
        <div class="phase-section">
            <div class="phase-header" style="background: linear-gradient(135deg, #ff6b6b, #ee5a24);">
                Change Lead Time Analysis
            </div>
            <div class="phase-content">
                <p style="color: #666; text-align: center; padding: 2rem;">
                    No matched PRs available for Change Lead Time calculation.
                </p>
            </div>
        </div>
        """
    
    median_display = format_time_duration(clt.get('median_hours', 0))
    
    return f"""
        <div class="phase-section">
            <div class="phase-header" style="background: linear-gradient(135deg, #ff6b6b, #ee5a24);">
                Change Lead Time Analysis
            </div>
            <div class="phase-content">
                <div class="metrics-grid">
                    <div class="metric-card">
                        <h4>Median Time to Merge</h4>
                        <div class="metric-value">{clt.get('median_days', 0):.1f} days</div>
                        <div class="metric-subtitle">{clt.get('median_hours', 0):.1f} hours</div>
                    </div>
                    <div class="metric-card">
                        <h4>Average Commits per PR</h4>
                        <div class="metric-value">{clt.get('avg_commits', 0):.1f}</div>
                        <div class="metric-subtitle">Per matched PR</div>
                    </div>
                    <div class="metric-card">
                        <h4>Average Files Changed</h4>
                        <div class="metric-value">{clt.get('avg_files_changed', 0):.1f}</div>
                        <div class="metric-subtitle">Per matched PR</div>
                    </div>
                    <div class="metric-card">
                        <h4>Average Comments</h4>
                        <div class="metric-value">{clt.get('avg_comments', 0):.1f}</div>
                        <div class="metric-subtitle">Per matched PR</div>
                    </div>
                </div>
                <div class="info-box">
                    <p>Based on {clt.get('matched_pr_count', 0)} merged PRs matched to Jira issues</p>
                    <p>Non-merged PRs excluded: {clt.get('non_merged_pr_count', 0)}</p>
                </div>
            </div>
        </div>
    """


def create_cycle_time_section(metrics: Dict[str, Any]) -> str:
    """Generate HTML for Cycle Time metrics section."""
    ct = metrics.get('cycle_time', {})
    
    if not ct or ct.get('completed_count', 0) == 0:
        return """
        <div class="phase-section">
            <div class="phase-header" style="background: linear-gradient(135deg, #4ecdc4, #44a08d);">
                Cycle Time Analysis
            </div>
            <div class="phase-content">
                <p style="color: #666; text-align: center; padding: 2rem;">
                    No completed issues available for Cycle Time calculation.
                </p>
            </div>
        </div>
        """
    
    issue_types_str = ', '.join(ct.get('issue_types_tracked', []))
    
    return f"""
        <div class="phase-section">
            <div class="phase-header" style="background: linear-gradient(135deg, #4ecdc4, #44a08d);">
                Cycle Time Analysis
            </div>
            <div class="phase-content">
                <div class="metrics-grid">
                    <div class="metric-card">
                        <h4>Median Cycle Time</h4>
                        <div class="metric-value">{ct.get('median_days', 0):.1f} days</div>
                        <div class="metric-subtitle">{ct.get('median_hours', 0):.1f} hours (In Progress → Done)</div>
                    </div>
                    <div class="metric-card">
                        <h4>Average Cycle Time</h4>
                        <div class="metric-value">{ct.get('avg_days', 0):.1f} days</div>
                        <div class="metric-subtitle">{ct.get('avg_hours', 0):.1f} hours (In Progress → Done)</div>
                    </div>
                    <div class="metric-card">
                        <h4>Completed Issues</h4>
                        <div class="metric-value">{ct.get('completed_count', 0)}</div>
                        <div class="metric-subtitle">With complete timestamps</div>
                    </div>
                    <div class="metric-card">
                        <h4>In-Progress Issues</h4>
                        <div class="metric-value">{ct.get('in_progress_count', 0)}</div>
                        <div class="metric-subtitle">Not yet completed</div>
                    </div>
                </div>
                <div class="info-box">
                    <p>Tracking issue types: {issue_types_str}</p>
                    <p>Issues with missing timestamps excluded from calculations</p>
                </div>
            </div>
        </div>
    """


def create_bug_resolution_time_section(metrics: Dict[str, Any]) -> str:
    """Generate HTML for Bug Resolution Time metrics section."""
    brt = metrics.get('bug_resolution_time', {})
    
    if not brt or brt.get('completed_count', 0) == 0:
        return """
        <div class="phase-section">
            <div class="phase-header" style="background: linear-gradient(135deg, #ff9a56, #ff6b35);">
                Bug Resolution Time Analysis
            </div>
            <div class="phase-content">
                <p style="color: #666; text-align: center; padding: 2rem;">
                    No completed bugs available for Bug Resolution Time calculation.
                </p>
            </div>
        </div>
        """
    
    return f"""
        <div class="phase-section">
            <div class="phase-header" style="background: linear-gradient(135deg, #ff9a56, #ff6b35);">
                Bug Resolution Time Analysis
            </div>
            <div class="phase-content">
                <div class="metrics-grid">
                    <div class="metric-card">
                        <h4>Median Bug Resolution Time</h4>
                        <div class="metric-value">{brt.get('median_days', 0):.1f} days</div>
                        <div class="metric-subtitle">{brt.get('median_hours', 0):.1f} hours (In Progress → Done)</div>
                    </div>
                    <div class="metric-card">
                        <h4>Average Bug Resolution Time</h4>
                        <div class="metric-value">{brt.get('avg_days', 0):.1f} days</div>
                        <div class="metric-subtitle">{brt.get('avg_hours', 0):.1f} hours (In Progress → Done)</div>
                    </div>
                    <div class="metric-card">
                        <h4>Completed Bugs</h4>
                        <div class="metric-value">{brt.get('completed_count', 0)}</div>
                        <div class="metric-subtitle">With complete timestamps</div>
                    </div>
                    <div class="metric-card">
                        <h4>In-Progress Bugs</h4>
                        <div class="metric-value">{brt.get('in_progress_count', 0)}</div>
                        <div class="metric-subtitle">Not yet resolved</div>
                    </div>
                </div>
                <div class="info-box">
                    <p>Tracking issue type: Bug</p>
                    <p>Bugs with missing timestamps excluded from calculations</p>
                </div>
            </div>
        </div>
    """


def generate_html_dashboard(metrics_data: Dict[str, Any], output_path: str) -> None:
    """
    Generate complete HTML dashboard from metrics data.
    
    Args:
        metrics_data: Dictionary containing all calculated metrics.
        output_path: Path where HTML file should be saved.
    """
    project_name = metrics_data.get('project_name', 'Unknown Project')
    generated_at = metrics_data.get('generated_at', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    
    # Generate sections
    summary_cards = create_summary_cards_html(metrics_data)
    change_lead_time_section = create_change_lead_time_section(metrics_data)
    cycle_time_section = create_cycle_time_section(metrics_data)
    bug_resolution_time_section = create_bug_resolution_time_section(metrics_data)
    
    # Complete HTML document
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{project_name} - Success Metrics Dashboard</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #f5f7fa;
            color: #333;
            line-height: 1.6;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            text-align: center;
            padding: 2rem 0;
            margin-bottom: 2rem;
        }}
        
        .header h1 {{
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
        }}
        
        .header p {{
            font-size: 1.1rem;
            opacity: 0.9;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 1rem;
        }}
        
        .summary-cards {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1.5rem;
            margin-bottom: 3rem;
        }}
        
        .summary-card {{
            background: white;
            border-radius: 10px;
            padding: 1.5rem;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            text-align: center;
            transition: transform 0.3s ease;
        }}
        
        .summary-card:hover {{
            transform: translateY(-5px);
        }}
        
        .summary-card h3 {{
            color: #667eea;
            margin-bottom: 0.5rem;
            font-size: 1rem;
        }}
        
        .summary-card .number {{
            font-size: 2.5rem;
            font-weight: bold;
            color: #333;
            margin-bottom: 0.5rem;
        }}
        
        .summary-card p {{
            color: #666;
            font-size: 0.9rem;
        }}
        
        .phase-section {{
            background: white;
            border-radius: 10px;
            margin-bottom: 2rem;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            overflow: hidden;
        }}
        
        .phase-header {{
            padding: 1.5rem;
            font-size: 1.5rem;
            font-weight: bold;
            color: white;
        }}
        
        .phase-content {{
            padding: 2rem;
        }}
        
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 1.5rem;
            margin-bottom: 1.5rem;
        }}
        
        .metric-card {{
            background: #f8f9fa;
            border-radius: 8px;
            padding: 1.5rem;
            border-left: 4px solid #667eea;
        }}
        
        .metric-card h4 {{
            color: #667eea;
            margin-bottom: 1rem;
            font-size: 0.95rem;
        }}
        
        .metric-value {{
            font-size: 2rem;
            font-weight: bold;
            margin-bottom: 0.5rem;
            color: #333;
        }}
        
        .metric-subtitle {{
            color: #666;
            font-size: 0.85rem;
        }}
        
        .info-box {{
            background: #e3f2fd;
            border: 1px solid #90caf9;
            border-radius: 8px;
            padding: 1rem;
            margin-top: 1.5rem;
        }}
        
        .info-box p {{
            color: #1565c0;
            margin-bottom: 0.3rem;
            font-size: 0.9rem;
        }}
        
        .info-box p:last-child {{
            margin-bottom: 0;
        }}
        
        .footer {{
            text-align: center;
            padding: 2rem;
            color: #666;
            border-top: 1px solid #e0e0e0;
            margin-top: 3rem;
        }}
        
        .footer p {{
            margin-bottom: 0.5rem;
        }}
        
        @media (max-width: 768px) {{
            .header h1 {{
                font-size: 2rem;
            }}
            
            .summary-cards {{
                grid-template-columns: 1fr;
            }}
            
            .metrics-grid {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <div class="container">
            <h1>{project_name} - Metrics</h1>
            <p>Team Dashboard</p>
            <p>Generated on {generated_at}</p>
        </div>
    </div>

    <div class="container">
        <!-- Summary Cards -->
        {summary_cards}

        <!-- Change Lead Time Section -->
        {change_lead_time_section}

        <!-- Cycle Time Section -->
        {cycle_time_section}

        <!-- Bug Resolution Time Section -->
        {bug_resolution_time_section}
    </div>

    <div class="footer">
        <p>Generated by Success Measurement System | {project_name} Team</p>
        <p>Data sources: Jira Issues ({metrics_data.get('summary', {}).get('total_jira_issues', 0)} issues) 
           & GitHub PRs ({metrics_data.get('summary', {}).get('total_prs', 0)} PRs)</p>
    </div>
</body>
</html>"""
    
    # Write to file
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"HTML dashboard generated successfully: {output_path}")
        return output_path
    except Exception as e:
        raise Exception(f"Failed to write HTML dashboard to {output_path}: {e}")


