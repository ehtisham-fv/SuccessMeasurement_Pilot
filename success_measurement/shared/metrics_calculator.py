#!/usr/bin/env python3
"""
Metrics calculation module for success measurement.
Provides reusable functions for calculating team performance metrics.
"""

import re
import statistics
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple


def parse_ticket_key_from_pr(pr_name: str) -> Optional[str]:
    """
    Extract Jira ticket key from PR name.
    
    Pattern: "OA-123: Title" or "oa-123: Title" (case-insensitive prefix, exact numbers)
    
    Args:
        pr_name: Pull request name.
        
    Returns:
        Normalized ticket key (e.g., "OA-123") or None if no match.
    """
    if not pr_name:
        return None
    
    # Match pattern: PREFIX-NUMBER: (case-insensitive for prefix, exact for numbers)
    match = re.match(r'^([A-Za-z]+)-(\d+):', pr_name.strip())
    if match:
        prefix = match.group(1).upper()
        number = match.group(2)
        return f"{prefix}-{number}"
    
    return None


def match_prs_to_jira(jira_data: List[Dict[str, Any]], 
                      github_data: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Match GitHub PRs to Jira issues based on ticket key in PR name.
    
    Args:
        jira_data: List of Jira issue dictionaries.
        github_data: List of GitHub PR dictionaries.
        
    Returns:
        Tuple of (matched_prs, unmatched_pr_names):
        - matched_prs: List of PR dicts with added 'ticket_key' field
        - unmatched_pr_names: List of PR names that couldn't be matched
    """
    # Build set of valid Jira ticket keys for O(1) lookup
    valid_ticket_keys = {issue['ticket_key'] for issue in jira_data if issue.get('ticket_key')}
    
    matched_prs = []
    unmatched_pr_names = []
    
    for pr in github_data:
        pr_name = pr.get('pr_name', '')
        ticket_key = parse_ticket_key_from_pr(pr_name)
        
        if ticket_key and ticket_key in valid_ticket_keys:
            # Add ticket_key to PR data for reference
            pr_with_key = pr.copy()
            pr_with_key['ticket_key'] = ticket_key
            matched_prs.append(pr_with_key)
        else:
            unmatched_pr_names.append(pr_name)
    
    logging.warning(f"Matched {len(matched_prs)} PRs to Jira issues")
    logging.warning(f"Unmatched PRs: {len(unmatched_pr_names)} (ignored for metrics)")
    
    return matched_prs, unmatched_pr_names


def calculate_change_lead_time(jira_data: List[Dict[str, Any]], 
                                 github_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate Change Lead Time: duration from PR creation to merge.
    Only includes merged PRs that match Jira tickets.
    
    Args:
        jira_data: List of Jira issue dictionaries.
        github_data: List of GitHub PR dictionaries.
        
    Returns:
        Dictionary with median time, averages, and counts.
    """
    logging.warning("Calculating Change Lead Time...")
    
    # Filter for merged PRs only
    merged_prs = [pr for pr in github_data if pr.get('is_merged') == 'True']
    non_merged_count = len([pr for pr in github_data if pr.get('is_merged') != 'True'])
    
    logging.warning(f"  Merged PRs: {len(merged_prs)}")
    logging.warning(f"  Non-merged PRs: {non_merged_count}")
    
    # Match PRs to Jira issues
    matched_prs, _ = match_prs_to_jira(jira_data, merged_prs)
    
    if not matched_prs:
        logging.warning("  No matched PRs found for Change Lead Time calculation")
        return {
            'median_days': 0,
            'median_hours': 0,
            'avg_comments': 0,
            'avg_commits': 0,
            'avg_files_changed': 0,
            'matched_pr_count': 0,
            'non_merged_pr_count': non_merged_count
        }
    
    # Calculate lead times and collect stats
    lead_times_hours = []
    comments_list = []
    commits_list = []
    files_changed_list = []
    
    for pr in matched_prs:
        try:
            # Parse timestamps
            created = datetime.strptime(pr['created_at'], '%Y-%m-%d %H:%M:%S')
            merged = datetime.strptime(pr['merged_at'], '%Y-%m-%d %H:%M:%S')
            
            # Calculate lead time in hours
            lead_time_hours = (merged - created).total_seconds() / 3600
            lead_times_hours.append(lead_time_hours)
            
            # Collect PR stats
            comments_list.append(int(pr.get('num_comments', 0)))
            commits_list.append(int(pr.get('num_commits', 0)))
            files_changed_list.append(int(pr.get('num_files_changed', 0)))
            
        except (ValueError, KeyError) as e:
            logging.warning(f"  Skipping PR {pr.get('pr_name')} due to parsing error: {e}")
            continue
    
    if not lead_times_hours:
        logging.warning("  No valid lead times calculated")
        return {
            'median_days': 0,
            'median_hours': 0,
            'avg_comments': 0,
            'avg_commits': 0,
            'avg_files_changed': 0,
            'matched_pr_count': 0,
            'non_merged_pr_count': non_merged_count
        }
    
    # Calculate statistics
    median_hours = statistics.median(lead_times_hours)
    median_days = median_hours / 24
    
    avg_comments = statistics.mean(comments_list) if comments_list else 0
    avg_commits = statistics.mean(commits_list) if commits_list else 0
    avg_files_changed = statistics.mean(files_changed_list) if files_changed_list else 0
    
    logging.warning(f"  Median Lead Time: {median_days:.1f} days ({median_hours:.1f} hours)")
    logging.warning(f"  Based on {len(matched_prs)} matched PRs")
    
    return {
        'median_days': round(median_days, 1),
        'median_hours': round(median_hours, 1),
        'avg_comments': round(avg_comments, 1),
        'avg_commits': round(avg_commits, 1),
        'avg_files_changed': round(avg_files_changed, 1),
        'matched_pr_count': len(matched_prs),
        'non_merged_pr_count': non_merged_count
    }


def calculate_cycle_time(jira_data: List[Dict[str, Any]], 
                         issue_types: List[str]) -> Dict[str, Any]:
    """
    Calculate Cycle Time: duration from In Progress to Done for Jira issues.
    Only includes issues with both timestamps.
    
    Args:
        jira_data: List of Jira issue dictionaries.
        issue_types: List of issue types to include (e.g., ["Story", "Sub-task"]).
        
    Returns:
        Dictionary with median time, averages, and counts.
    """
    logging.warning("Calculating Cycle Time...")
    logging.warning(f"  Including issue types: {', '.join(issue_types)}")
    
    # Filter for specified issue types
    filtered_issues = [
        issue for issue in jira_data 
        if issue.get('type') in issue_types
    ]
    
    logging.warning(f"  Total issues of specified types: {len(filtered_issues)}")
    
    # Filter for issues with both timestamps
    issues_with_timestamps = [
        issue for issue in filtered_issues
        if issue.get('in_progress_timestamp') and 
           issue.get('done_timestamp') and
           issue.get('in_progress_timestamp').strip() and
           issue.get('done_timestamp').strip()
    ]
    
    # Count issues still in progress (have in_progress but no done)
    in_progress_only = [
        issue for issue in filtered_issues
        if issue.get('in_progress_timestamp') and 
           issue.get('in_progress_timestamp').strip() and
           (not issue.get('done_timestamp') or not issue.get('done_timestamp').strip())
    ]
    
    logging.warning(f"  Issues with complete timestamps: {len(issues_with_timestamps)}")
    logging.warning(f"  Issues still in progress: {len(in_progress_only)}")
    
    if not issues_with_timestamps:
        logging.warning("  No issues with complete timestamps for Cycle Time calculation")
        return {
            'median_days': 0,
            'median_hours': 0,
            'avg_days': 0,
            'avg_hours': 0,
            'completed_count': 0,
            'in_progress_count': len(in_progress_only),
            'issue_types_tracked': issue_types
        }
    
    # Calculate cycle times
    cycle_times_hours = []
    
    for issue in issues_with_timestamps:
        try:
            # Parse timestamps
            in_progress = datetime.strptime(issue['in_progress_timestamp'], '%Y-%m-%d %H:%M:%S')
            done = datetime.strptime(issue['done_timestamp'], '%Y-%m-%d %H:%M:%S')
            
            # Calculate cycle time in hours
            cycle_time_hours = (done - in_progress).total_seconds() / 3600
            
            # Skip negative times (data quality issue)
            if cycle_time_hours >= 0:
                cycle_times_hours.append(cycle_time_hours)
            else:
                logging.warning(f"  Skipping {issue.get('ticket_key')} - negative cycle time")
            
        except (ValueError, KeyError) as e:
            logging.warning(f"  Skipping {issue.get('ticket_key')} due to parsing error: {e}")
            continue
    
    if not cycle_times_hours:
        logging.warning("  No valid cycle times calculated")
        return {
            'median_days': 0,
            'median_hours': 0,
            'avg_days': 0,
            'avg_hours': 0,
            'completed_count': 0,
            'in_progress_count': len(in_progress_only),
            'issue_types_tracked': issue_types
        }
    
    # Calculate statistics
    median_hours = statistics.median(cycle_times_hours)
    median_days = median_hours / 24
    avg_hours = statistics.mean(cycle_times_hours)
    avg_days = avg_hours / 24
    
    logging.warning(f"  Median Cycle Time: {median_days:.1f} days ({median_hours:.1f} hours)")
    logging.warning(f"  Average Cycle Time: {avg_days:.1f} days ({avg_hours:.1f} hours)")
    logging.warning(f"  Based on {len(cycle_times_hours)} completed issues")
    
    return {
        'median_days': round(median_days, 1),
        'median_hours': round(median_hours, 1),
        'avg_days': round(avg_days, 1),
        'avg_hours': round(avg_hours, 1),
        'completed_count': len(cycle_times_hours),
        'in_progress_count': len(in_progress_only),
        'issue_types_tracked': issue_types
    }


def calculate_bug_resolution_time(jira_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate Bug Resolution Time: duration from In Progress to Done for Bug issues.
    Only includes bugs with both timestamps.
    
    Args:
        jira_data: List of Jira issue dictionaries.
        
    Returns:
        Dictionary with median time, averages, and counts.
    """
    logging.warning("Calculating Bug Resolution Time...")
    
    # Filter for Bug issue type
    bug_issues = [
        issue for issue in jira_data 
        if issue.get('type') == 'Bug'
    ]
    
    logging.warning(f"  Total Bug issues: {len(bug_issues)}")
    
    # Filter for bugs with both timestamps
    bugs_with_timestamps = [
        issue for issue in bug_issues
        if issue.get('in_progress_timestamp') and 
           issue.get('done_timestamp') and
           issue.get('in_progress_timestamp').strip() and
           issue.get('done_timestamp').strip()
    ]
    
    # Count bugs still in progress (have in_progress but no done)
    in_progress_bugs = [
        issue for issue in bug_issues
        if issue.get('in_progress_timestamp') and 
           issue.get('in_progress_timestamp').strip() and
           (not issue.get('done_timestamp') or not issue.get('done_timestamp').strip())
    ]
    
    logging.warning(f"  Bugs with complete timestamps: {len(bugs_with_timestamps)}")
    logging.warning(f"  Bugs still in progress: {len(in_progress_bugs)}")
    
    if not bugs_with_timestamps:
        logging.warning("  No bugs with complete timestamps for Bug Resolution Time calculation")
        return {
            'median_days': 0,
            'median_hours': 0,
            'avg_days': 0,
            'avg_hours': 0,
            'completed_count': 0,
            'in_progress_count': len(in_progress_bugs)
        }
    
    # Calculate resolution times
    resolution_times_hours = []
    
    for issue in bugs_with_timestamps:
        try:
            # Parse timestamps
            in_progress = datetime.strptime(issue['in_progress_timestamp'], '%Y-%m-%d %H:%M:%S')
            done = datetime.strptime(issue['done_timestamp'], '%Y-%m-%d %H:%M:%S')
            
            # Calculate resolution time in hours
            resolution_time_hours = (done - in_progress).total_seconds() / 3600
            
            # Skip negative times (data quality issue)
            if resolution_time_hours >= 0:
                resolution_times_hours.append(resolution_time_hours)
            else:
                logging.warning(f"  Skipping {issue.get('ticket_key')} - negative resolution time")
            
        except (ValueError, KeyError) as e:
            logging.warning(f"  Skipping {issue.get('ticket_key')} due to parsing error: {e}")
            continue
    
    if not resolution_times_hours:
        logging.warning("  No valid resolution times calculated")
        return {
            'median_days': 0,
            'median_hours': 0,
            'avg_days': 0,
            'avg_hours': 0,
            'completed_count': 0,
            'in_progress_count': len(in_progress_bugs)
        }
    
    # Calculate statistics
    median_hours = statistics.median(resolution_times_hours)
    median_days = median_hours / 24
    avg_hours = statistics.mean(resolution_times_hours)
    avg_days = avg_hours / 24
    
    logging.warning(f"  Median Bug Resolution Time: {median_days:.1f} days ({median_hours:.1f} hours)")
    logging.warning(f"  Average Bug Resolution Time: {avg_days:.1f} days ({avg_hours:.1f} hours)")
    logging.warning(f"  Based on {len(resolution_times_hours)} completed bugs")
    
    return {
        'median_days': round(median_days, 1),
        'median_hours': round(median_hours, 1),
        'avg_days': round(avg_days, 1),
        'avg_hours': round(avg_hours, 1),
        'completed_count': len(resolution_times_hours),
        'in_progress_count': len(in_progress_bugs)
    }


def calculate_all_metrics(jira_data: List[Dict[str, Any]], 
                          github_data: List[Dict[str, Any]],
                          config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate all enabled metrics based on configuration.
    
    Args:
        jira_data: List of Jira issue dictionaries.
        github_data: List of GitHub PR dictionaries.
        config: Configuration dictionary with metrics settings.
        
    Returns:
        Dictionary with all calculated metrics and summary data.
    """
    metrics_config = config.get('metrics', {})
    
    results = {
        'project_name': config.get('project_name', 'Unknown Project'),
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'summary': {
            'total_jira_issues': len(jira_data),
            'total_prs': len(github_data),
            'matched_prs': 0,
            'non_merged_prs': 0
        }
    }
    
    # Calculate Change Lead Time if enabled
    if metrics_config.get('change_lead_time', {}).get('enabled', False):
        change_lead_time = calculate_change_lead_time(jira_data, github_data)
        results['change_lead_time'] = change_lead_time
        results['summary']['matched_prs'] = change_lead_time['matched_pr_count']
        results['summary']['non_merged_prs'] = change_lead_time['non_merged_pr_count']
    
    # Calculate Cycle Time if enabled
    if metrics_config.get('cycle_time', {}).get('enabled', False):
        issue_types = metrics_config.get('cycle_time', {}).get('include_issue_types', ['Story', 'Sub-task'])
        cycle_time = calculate_cycle_time(jira_data, issue_types)
        results['cycle_time'] = cycle_time
    
    # Calculate Bug Resolution Time if enabled
    if metrics_config.get('bug_resolution_time', {}).get('enabled', False):
        bug_resolution_time = calculate_bug_resolution_time(jira_data)
        results['bug_resolution_time'] = bug_resolution_time
    
    return results


