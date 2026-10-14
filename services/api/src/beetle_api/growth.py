"""Deterministic growth metrics. Must match the Dart implementation; both are
tested against packages/api-contracts/fixtures/growth/cases.json."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class WeightPoint:
    id: str
    measured_at: datetime
    grams: float


def compute_growth(points: list[WeightPoint]) -> dict:
    pts = sorted(points, key=lambda p: (p.measured_at, p.id))
    empty = {
        "count": 0,
        "latest_grams": None,
        "first_grams": None,
        "previous_grams": None,
        "change_since_previous_grams": None,
        "percent_change_since_previous": None,
        "total_change_grams": None,
        "span_days": None,
        "avg_daily_change_grams": None,
        "avg_weekly_change_grams": None,
        "max_grams": None,
        "max_at": None,
        "is_losing_weight": False,
    }
    if not pts:
        return empty
    first, latest = pts[0], pts[-1]
    previous = pts[-2] if len(pts) >= 2 else None
    peak = pts[0]
    for p in pts[1:]:
        if p.grams > peak.grams:  # earliest record wins ties
            peak = p
    span_days = (latest.measured_at - first.measured_at).total_seconds() / 86400
    change = latest.grams - previous.grams if previous else None
    pct = change / previous.grams * 100 if previous and previous.grams else None
    total = latest.grams - first.grams if len(pts) >= 2 else None
    daily = total / span_days if total is not None and span_days >= 1 else None
    return {
        "count": len(pts),
        "latest_grams": latest.grams,
        "first_grams": first.grams,
        "previous_grams": previous.grams if previous else None,
        "change_since_previous_grams": change,
        "percent_change_since_previous": pct,
        "total_change_grams": total,
        "span_days": span_days,
        "avg_daily_change_grams": daily,
        "avg_weekly_change_grams": daily * 7 if daily is not None else None,
        "max_grams": peak.grams,
        "max_at": peak.measured_at.isoformat(),
        "is_losing_weight": (change or 0) < 0,
    }
