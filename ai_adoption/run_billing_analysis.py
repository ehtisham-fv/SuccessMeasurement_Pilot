#!/usr/bin/env python3
"""
On-Demand Billing Analysis - Main Entry Point

Two-part script:
  Part 1: Fetch usage events from Cursor Admin API and cache as monthly JSON files
  Part 2: Load cached JSON, calculate analytics, and generate HTML billing dashboard

Usage:
    python -m ai_adoption.run_billing_analysis
    python ai_adoption/run_billing_analysis.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from ai_adoption.shared.utils import load_config, load_env_vars, get_month_name
from ai_adoption.shared.billing_client import BillingClient
from ai_adoption.shared.billing_calculator import BillingCalculator
from ai_adoption.shared.billing_dashboard_generator import BillingDashboardGenerator


def main():
    print("=" * 60)
    print("On-Demand Billing Analysis - Cursor IDE")
    print("=" * 60)
    print()

    # ── Load configuration ──────────────────────────────────────
    print("[1/4] Loading configuration...")
    config = load_config()
    env_vars = load_env_vars()

    api_key = env_vars.get("CURSOR_API_KEY")
    if not api_key:
        print("ERROR: CURSOR_API_KEY not found in .env file")
        sys.exit(1)

    billing_config = config.get("billing", {})
    api_config = config.get("api", {})

    months_back = billing_config.get("months_back", 2)
    page_size = billing_config.get("page_size", 100)
    output_filename = billing_config.get("output_filename", "billing_dashboard.html")
    top_spenders_count = billing_config.get("top_spenders_count", 20)
    request_delay = billing_config.get("request_delay_seconds", 3)

    months = BillingClient.get_months_to_fetch(months_back)
    month_labels = [f"{get_month_name(m)} {y}" for y, m in months]

    print(f"   - Months to analyze: {', '.join(month_labels)}")
    print(f"   - Page size: {page_size}")
    print(f"   - Request delay: {request_delay}s")
    print()

    # ── Part 1: Fetch & Cache ───────────────────────────────────
    print("[2/4] Part 1: Fetching usage data from API...")

    client = BillingClient(
        api_key=api_key,
        base_url=api_config.get("base_url", "https://api.cursor.com"),
        timeout=api_config.get("timeout_seconds", 30),
        page_size=page_size,
        request_delay=request_delay,
    )

    fetched_count = 0
    skipped_count = 0

    for year, month in months:
        label = f"{get_month_name(month)} {year}"

        if BillingClient.cache_exists(year, month):
            cache_data = BillingClient.load_month_cache(year, month)
            event_count = cache_data.get("total_events", 0) if cache_data else 0
            print(f"   [{label}] Cache exists ({event_count} events) - skipping API call")
            skipped_count += 1
            continue

        print(f"   [{label}] Fetching from API...")
        try:
            events = client.fetch_monthly_usage_events(year, month)
            filepath = BillingClient.save_month_cache(year, month, events)
            print(f"   [{label}] Saved {len(events)} events to {filepath}")
            fetched_count += 1
        except Exception as e:
            print(f"   [{label}] ERROR: {e}")
            print(f"   Continuing with remaining months...")

    print(f"   -> Fetched: {fetched_count} month(s), Skipped (cached): {skipped_count} month(s)")
    print()

    # ── Part 2: Calculate Analytics ─────────────────────────────
    print("[3/4] Part 2: Calculating billing analytics...")

    calculator = BillingCalculator(
        months=months,
        top_spenders_count=top_spenders_count,
    )

    metrics = calculator.calculate()

    print(f"   - Total on-demand cost: ${metrics.total_cost_dollars:,.2f}")
    print(f"   - Total requests: {metrics.total_requests:,}")
    print(f"   - Unique models: {len(metrics.model_stats)}")
    print(f"   - Unique users: {len(metrics.user_stats)}")

    if metrics.model_stats:
        print(f"   - Costliest model: {metrics.top_cost_model}")
    if metrics.user_stats:
        print(f"   - Top spender: {metrics.top_spender_email}")
    print()

    # ── Generate Dashboard ──────────────────────────────────────
    print("[4/4] Generating HTML billing dashboard...")

    dashboard = BillingDashboardGenerator(output_filename=output_filename)
    output_path = dashboard.generate(metrics, top_count=top_spenders_count)

    print(f"   - Dashboard saved to: {output_path}")
    print()

    # ── Summary ─────────────────────────────────────────────────
    print("=" * 60)
    print("BILLING ANALYSIS COMPLETE")
    print("=" * 60)
    print(f"  Months Analyzed:     {metrics.months_analyzed}")
    print(f"  Total On-Demand:     ${metrics.total_cost_dollars:,.2f}")
    print(f"  Total Requests:      {metrics.total_requests:,}")
    print(f"  Unique Users:        {len(metrics.user_stats)}")
    print(f"  Unique Models:       {len(metrics.model_stats)}")
    print()

    if metrics.monthly_breakdowns:
        print("  Monthly Costs:")
        for bd in metrics.monthly_breakdowns:
            print(f"    {bd.month_label:20s}  ${bd.total_cost_dollars:>10,.2f}  ({bd.total_requests:,} requests)")
        print()

    print(f"  Dashboard: {output_path}")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
