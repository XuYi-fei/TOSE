"""Shared metric helpers for RQ summaries."""

from __future__ import annotations

from typing import Any


def compute_utility_from_ar(ar_value: float) -> float:
    """Derive utility from abnormal ratio.

    Current RQ3 uses the complement of abnormal ratio as an availability-style
    utility metric so it stays aligned with the ASE AR definition already used
    by all methods.
    """

    return max(0.0, 100.0 - float(ar_value))


def enrich_summary_row(row: dict[str, Any]) -> dict[str, Any]:
    """Attach derived metrics shared by RQ1/RQ2/RQ3 outputs."""

    enriched = dict(row)
    enriched["utility"] = compute_utility_from_ar(float(enriched.get("AR", 0.0)))
    return enriched
