"""Translate recommendations into transparent modeled business exposure."""

from __future__ import annotations

import pandas as pd


def summarize_modeled_impact(recommendations: pd.DataFrame) -> dict[str, object]:
    """Aggregate synthetic planning exposure without claiming realized savings."""
    urgent = recommendations["risk"].isin(["stockout", "below_safety"])
    return {
        "actions_needing_review": int(urgent.sum()),
        "stockout_exposure_units": int(recommendations["stockout_exposure_units"].sum()),
        "purchase_commitment_usd": round(float(recommendations["recommended_order_value_usd"].sum()), 2),
        "excess_working_capital_usd": round(float(recommendations["excess_working_capital_usd"].sum()), 2),
        "estimated_annual_holding_cost_usd": round(float(recommendations["estimated_annual_holding_cost_usd"].sum()), 2),
        "assumption": "Synthetic unit costs and a 22% annual holding-rate assumption",
        "interpretation": "Decision exposure for review; not realized or guaranteed savings",
    }
