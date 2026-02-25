"""
Billing API Client for on-demand usage data.

Fetches usage events from the Cursor Admin API (/teams/filtered-usage-events),
handles pagination and rate limiting, and caches results as monthly JSON files.

API Documentation: https://cursor.com/docs/account/teams/admin-api
"""

import json
import time
import calendar
from datetime import datetime, date, timezone
from pathlib import Path
from typing import Optional

import requests
from requests.auth import HTTPBasicAuth

from .utils import get_data_path


class BillingClient:
    """
    Client for fetching on-demand usage events from the Cursor Admin API.

    Handles:
    - Paginated fetching of /teams/filtered-usage-events
    - Rate-limit throttling (configurable delay between requests)
    - Exponential backoff on HTTP 429
    - Local JSON caching in data/monthly_usage_data/
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.cursor.com",
        timeout: int = 30,
        page_size: int = 100,
        request_delay: float = 3.0,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.page_size = page_size
        self.request_delay = request_delay

        if not api_key:
            raise ValueError("CURSOR_API_KEY is required")

    def _make_post_request(self, endpoint: str, payload: dict, max_retries: int = 5) -> dict:
        """
        Make an authenticated POST request with exponential backoff on 429.
        """
        url = f"{self.base_url}{endpoint}"

        for attempt in range(max_retries):
            response = requests.post(
                url,
                json=payload,
                auth=HTTPBasicAuth(self.api_key, ""),
                timeout=self.timeout,
            )

            if response.status_code == 429:
                wait_time = 2 ** attempt
                print(f"   Rate limited (429). Waiting {wait_time}s before retry {attempt + 1}/{max_retries}...")
                time.sleep(wait_time)
                continue

            response.raise_for_status()
            return response.json()

        raise Exception(f"Max retries ({max_retries}) exceeded for {endpoint}")

    def _get_month_epoch_range(self, year: int, month: int) -> tuple:
        """
        Get epoch millisecond timestamps for the start and end of a calendar month.

        Returns (start_ms, end_ms) where:
        - start_ms = first day of month at 00:00:00 UTC
        - end_ms = first day of next month at 00:00:00 UTC
        """
        start_dt = datetime(year, month, 1, tzinfo=timezone.utc)

        if month == 12:
            end_dt = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            end_dt = datetime(year, month + 1, 1, tzinfo=timezone.utc)

        start_ms = int(start_dt.timestamp() * 1000)
        end_ms = int(end_dt.timestamp() * 1000)
        return start_ms, end_ms

    def fetch_monthly_usage_events(self, year: int, month: int) -> list:
        """
        Fetch all usage-based chargeable events for a given month.

        Paginates through all pages, filters for on-demand events, and
        respects rate limits with delays between requests.

        Returns:
            list: Filtered usage events (kind=Usage-based, isChargeable=true)
        """
        start_ms, end_ms = self._get_month_epoch_range(year, month)
        month_name = calendar.month_name[month]

        all_events = []
        page = 1
        total_pages = "?"

        while True:
            if page > 1:
                time.sleep(self.request_delay)

            print(f"   Fetching page {page}/{total_pages} for {month_name} {year}...")

            payload = {
                "startDate": start_ms,
                "endDate": end_ms,
                "page": page,
                "pageSize": self.page_size,
            }

            data = self._make_post_request("/teams/filtered-usage-events", payload)

            pagination = data.get("pagination", {})
            total_pages = pagination.get("numPages", "?")

            events = data.get("usageEvents", [])
            for event in events:
                if (
                    event.get("kind") == "Usage-based"
                    and event.get("isChargeable") is True
                ):
                    all_events.append(event)

            if not pagination.get("hasNextPage", False):
                break

            page += 1

        print(f"   -> {len(all_events)} usage-based chargeable events for {month_name} {year}")
        return all_events

    @staticmethod
    def get_cache_filepath(year: int, month: int) -> Path:
        """Get the expected cache file path for a given month."""
        data_dir = get_data_path() / "billing_data"
        filename = f"{month:02d}-{year}-usage-based-data.json"
        return data_dir / filename

    @staticmethod
    def cache_exists(year: int, month: int) -> bool:
        """Check if a cached JSON file exists for the given month."""
        return BillingClient.get_cache_filepath(year, month).exists()

    @staticmethod
    def save_month_cache(year: int, month: int, events: list) -> Path:
        """
        Save fetched events to a JSON cache file.

        File format: MM-YYYY-usage-based-data.json
        """
        filepath = BillingClient.get_cache_filepath(year, month)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        cache_data = {
            "month": f"{month:02d}-{year}",
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "total_events": len(events),
            "events": events,
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, indent=2, ensure_ascii=False)

        return filepath

    @staticmethod
    def load_month_cache(year: int, month: int) -> Optional[dict]:
        """
        Load events from a cached JSON file.

        Returns:
            dict with keys: month, fetched_at, total_events, events
            None if cache file doesn't exist
        """
        filepath = BillingClient.get_cache_filepath(year, month)
        if not filepath.exists():
            return None

        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def get_months_to_fetch(months_back: int) -> list:
        """
        Compute the list of (year, month) tuples to fetch,
        going back `months_back` months from the current month (inclusive).

        Example: if today is Feb 2026 and months_back=2,
        returns [(2026, 1), (2026, 2)]
        """
        today = date.today()
        months = []

        for i in range(months_back, 0, -1):
            # Go back (i - 1) months from current month
            # (months_back=2 means current month and previous month)
            year = today.year
            month = today.month - (i - 1)

            while month <= 0:
                month += 12
                year -= 1

            months.append((year, month))

        return months
