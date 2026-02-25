"""
Billing Calculator for on-demand usage analytics.

Loads cached monthly JSON files and aggregates usage events into
structured metrics: cost by user, cost by model, monthly trends,
and user-model cross-references.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional

from .billing_client import BillingClient
from .utils import get_month_name


@dataclass
class ModelStats:
    """Aggregated stats for a single model."""
    model: str
    total_cost_cents: float = 0.0
    total_requests: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cache_write_tokens: int = 0
    total_cache_read_tokens: int = 0
    unique_users: set = field(default_factory=set)

    @property
    def total_cost_dollars(self) -> float:
        return self.total_cost_cents / 100.0

    @property
    def total_tokens(self) -> int:
        return (
            self.total_input_tokens
            + self.total_output_tokens
            + self.total_cache_write_tokens
            + self.total_cache_read_tokens
        )

    @property
    def avg_cost_per_request_cents(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.total_cost_cents / self.total_requests


@dataclass
class UserStats:
    """Aggregated stats for a single user."""
    email: str
    total_cost_cents: float = 0.0
    total_requests: int = 0
    model_costs: Dict[str, float] = field(default_factory=lambda: defaultdict(float))
    model_requests: Dict[str, int] = field(default_factory=lambda: defaultdict(int))

    @property
    def total_cost_dollars(self) -> float:
        return self.total_cost_cents / 100.0

    @property
    def top_model(self) -> str:
        if not self.model_costs:
            return "N/A"
        return max(self.model_costs, key=self.model_costs.get)

    @property
    def avg_cost_per_request_cents(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.total_cost_cents / self.total_requests


@dataclass
class MonthlyBreakdown:
    """Cost breakdown for a single month."""
    year: int
    month: int
    total_cost_cents: float = 0.0
    total_requests: int = 0
    model_costs: Dict[str, float] = field(default_factory=lambda: defaultdict(float))
    model_requests: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    model_tokens: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    user_costs: Dict[str, float] = field(default_factory=lambda: defaultdict(float))
    user_requests: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    user_top_model: Dict[str, Dict[str, float]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(float))
    )

    @property
    def total_cost_dollars(self) -> float:
        return self.total_cost_cents / 100.0

    @property
    def month_label(self) -> str:
        return f"{get_month_name(self.month)} {self.year}"

    @property
    def month_key(self) -> str:
        return f"{self.month:02d}-{self.year}"


@dataclass
class BillingMetrics:
    """Complete billing analytics output."""
    monthly_breakdowns: List[MonthlyBreakdown]
    user_stats: Dict[str, UserStats]
    model_stats: Dict[str, ModelStats]
    total_cost_cents: float
    total_requests: int
    months_analyzed: int

    @property
    def total_cost_dollars(self) -> float:
        return self.total_cost_cents / 100.0

    @property
    def top_spender_email(self) -> str:
        if not self.user_stats:
            return "N/A"
        return max(self.user_stats.values(), key=lambda u: u.total_cost_cents).email

    @property
    def top_cost_model(self) -> str:
        if not self.model_stats:
            return "N/A"
        return max(self.model_stats.values(), key=lambda m: m.total_cost_cents).model

    def get_top_users(self, count: int = 20) -> List[UserStats]:
        return sorted(
            self.user_stats.values(),
            key=lambda u: u.total_cost_cents,
            reverse=True,
        )[:count]

    def get_top_models(self, count: int = 20) -> List[ModelStats]:
        return sorted(
            self.model_stats.values(),
            key=lambda m: m.total_cost_cents,
            reverse=True,
        )[:count]

    def get_users_for_model(self, model_name: str, count: int = 20) -> List[Tuple[str, float, int]]:
        """
        For a given model, return top users ranked by spend on that model.
        Returns list of (email, cost_cents, request_count).
        """
        user_model_data = []
        for email, user in self.user_stats.items():
            cost = user.model_costs.get(model_name, 0.0)
            reqs = user.model_requests.get(model_name, 0)
            if cost > 0:
                user_model_data.append((email, cost, reqs))

        user_model_data.sort(key=lambda x: x[1], reverse=True)
        return user_model_data[:count]


def _compute_event_cost_cents(event: dict) -> float:
    """
    Compute total cost for a single usage event in cents.

    tokenUsage.totalCents is the PRE-discount model cost.
    If discountPercentOff is present, apply it to get the actual charged amount.
    Then add cursorTokenFee (if present) to match Cursor Dashboard totals.
    """
    token_usage = event.get("tokenUsage")
    if token_usage is None:
        return 0.0

    model_cost = token_usage.get("totalCents", 0.0)

    discount = token_usage.get("discountPercentOff")
    if discount:
        model_cost = model_cost * (1 - discount / 100)

    cursor_fee = event.get("cursorTokenFee", 0.0) or 0.0
    return model_cost + cursor_fee


def _extract_tokens(event: dict) -> dict:
    """Extract token counts from an event."""
    token_usage = event.get("tokenUsage") or {}
    return {
        "input": token_usage.get("inputTokens", 0),
        "output": token_usage.get("outputTokens", 0),
        "cache_write": token_usage.get("cacheWriteTokens", 0),
        "cache_read": token_usage.get("cacheReadTokens", 0),
    }


class BillingCalculator:
    """
    Calculates billing analytics from cached monthly JSON data.
    """

    def __init__(self, months: List[Tuple[int, int]], top_spenders_count: int = 20):
        """
        Args:
            months: List of (year, month) tuples to analyze
            top_spenders_count: Number of top spenders to include in results
        """
        self.months = months
        self.top_spenders_count = top_spenders_count

    def calculate(self) -> BillingMetrics:
        """
        Load cached JSON for each month and compute all analytics.
        """
        monthly_breakdowns = []
        global_user_stats: Dict[str, UserStats] = {}
        global_model_stats: Dict[str, ModelStats] = {}
        total_cost_cents = 0.0
        total_requests = 0

        for year, month in self.months:
            cache_data = BillingClient.load_month_cache(year, month)
            if cache_data is None:
                print(f"   WARNING: No cached data for {get_month_name(month)} {year}, skipping")
                continue

            events = cache_data.get("events", [])
            breakdown = self._process_month(year, month, events, global_user_stats, global_model_stats)
            monthly_breakdowns.append(breakdown)
            total_cost_cents += breakdown.total_cost_cents
            total_requests += breakdown.total_requests

        return BillingMetrics(
            monthly_breakdowns=monthly_breakdowns,
            user_stats=global_user_stats,
            model_stats=global_model_stats,
            total_cost_cents=total_cost_cents,
            total_requests=total_requests,
            months_analyzed=len(monthly_breakdowns),
        )

    def _process_month(
        self,
        year: int,
        month: int,
        events: list,
        global_user_stats: Dict[str, UserStats],
        global_model_stats: Dict[str, ModelStats],
    ) -> MonthlyBreakdown:
        """Process all events for a single month, updating global and monthly stats."""
        breakdown = MonthlyBreakdown(year=year, month=month)

        for event in events:
            cost_cents = _compute_event_cost_cents(event)
            if cost_cents <= 0:
                continue

            email = event.get("userEmail", "unknown")
            model = event.get("model", "unknown")
            tokens = _extract_tokens(event)

            # Monthly breakdown
            breakdown.total_cost_cents += cost_cents
            breakdown.total_requests += 1
            breakdown.model_costs[model] += cost_cents
            breakdown.model_requests[model] += 1
            total_tokens = tokens["input"] + tokens["output"] + tokens["cache_write"] + tokens["cache_read"]
            breakdown.model_tokens[model] += total_tokens
            breakdown.user_costs[email] += cost_cents
            breakdown.user_requests[email] += 1
            breakdown.user_top_model[email][model] += cost_cents

            # Global user stats
            if email not in global_user_stats:
                global_user_stats[email] = UserStats(email=email)
            user = global_user_stats[email]
            user.total_cost_cents += cost_cents
            user.total_requests += 1
            user.model_costs[model] += cost_cents
            user.model_requests[model] += 1

            # Global model stats
            if model not in global_model_stats:
                global_model_stats[model] = ModelStats(model=model)
            m_stats = global_model_stats[model]
            m_stats.total_cost_cents += cost_cents
            m_stats.total_requests += 1
            m_stats.total_input_tokens += tokens["input"]
            m_stats.total_output_tokens += tokens["output"]
            m_stats.total_cache_write_tokens += tokens["cache_write"]
            m_stats.total_cache_read_tokens += tokens["cache_read"]
            m_stats.unique_users.add(email)

        return breakdown
