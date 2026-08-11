"""Forecast demand and translate inventory positions into planner actions."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd


DEMAND_COLUMNS = {"sku_id", "warehouse", "week_start", "units_sold"}
INVENTORY_COLUMNS = {
    "sku_id",
    "warehouse",
    "on_hand_units",
    "open_transfer_units",
    "transfer_eta_days",
    "supplier_lead_time_days",
    "safety_stock_units",
    "pack_size",
}
SCENARIOS = {
    "base": {"demand_multiplier": 1.0, "lead_time_multiplier": 1.0},
    "promotion": {"demand_multiplier": 1.25, "lead_time_multiplier": 1.0},
    "supplier_delay": {"demand_multiplier": 1.0, "lead_time_multiplier": 1.5},
}


def validate_inputs(demand: pd.DataFrame, inventory: pd.DataFrame) -> None:
    """Fail fast on structural errors that could create unsafe decisions."""
    missing_demand = DEMAND_COLUMNS - set(demand.columns)
    missing_inventory = INVENTORY_COLUMNS - set(inventory.columns)
    if missing_demand or missing_inventory:
        raise ValueError(
            f"Missing columns — demand: {sorted(missing_demand)}, "
            f"inventory: {sorted(missing_inventory)}"
        )
    if demand[list(DEMAND_COLUMNS)].isna().any().any() or inventory[list(INVENTORY_COLUMNS)].isna().any().any():
        raise ValueError("Decision inputs cannot contain null values")
    if (demand["units_sold"] < 0).any():
        raise ValueError("Demand cannot be negative")
    numeric_inventory = [
        "on_hand_units",
        "open_transfer_units",
        "transfer_eta_days",
        "supplier_lead_time_days",
        "safety_stock_units",
        "pack_size",
    ]
    if (inventory[numeric_inventory] < 0).any().any() or (inventory["pack_size"] == 0).any():
        raise ValueError("Inventory quantities must be nonnegative and pack size must be positive")
    if demand.duplicated(["sku_id", "warehouse", "week_start"]).any():
        raise ValueError("Demand keys must be unique")
    if inventory.duplicated(["sku_id", "warehouse"]).any():
        raise ValueError("Inventory snapshot keys must be unique")


def forecast_weekly_demand(demand: pd.DataFrame) -> pd.DataFrame:
    """Blend the 12-week mean with a recency-weighted four-week signal."""
    forecasts: list[dict[str, object]] = []
    ordered = demand.assign(week_start=pd.to_datetime(demand["week_start"]))
    for (sku_id, warehouse), group in ordered.groupby(["sku_id", "warehouse"]):
        history = group.sort_values("week_start").tail(12)
        recent = history.tail(4)["units_sold"].astype(float)
        weights = np.arange(1, len(recent) + 1, dtype=float)
        recent_weighted = float(np.average(recent, weights=weights))
        long_run = float(history["units_sold"].mean())
        forecast = (0.7 * recent_weighted) + (0.3 * long_run)
        forecasts.append(
            {
                "sku_id": sku_id,
                "warehouse": warehouse,
                "weekly_forecast_units": round(forecast, 1),
                "history_weeks": len(history),
            }
        )
    return pd.DataFrame(forecasts)


def _risk_label(projected: float, safety: float, weeks_of_cover: float) -> str:
    if projected < 0:
        return "stockout"
    if projected < safety:
        return "below_safety"
    if weeks_of_cover > 8:
        return "excess"
    return "healthy"


def _action_text(risk: str, order_units: int) -> str:
    if risk == "stockout":
        return f"Expedite supply and order {order_units:,} units"
    if risk == "below_safety":
        return f"Review replenishment of {order_units:,} units"
    if risk == "excess":
        return "Pause replenishment and review demand plan"
    return "Monitor; no immediate action"


def build_recommendations(
    demand: pd.DataFrame,
    inventory: pd.DataFrame,
    scenario: str = "base",
    target_cover_weeks: float = 2.0,
) -> pd.DataFrame:
    """Create an explainable recommendation for every SKU/warehouse pair."""
    validate_inputs(demand, inventory)
    if scenario not in SCENARIOS:
        raise ValueError(f"Unknown scenario: {scenario}")

    config = SCENARIOS[scenario]
    recommendations = inventory.merge(
        forecast_weekly_demand(demand), on=["sku_id", "warehouse"], how="left", validate="one_to_one"
    )
    recommendations["scenario"] = scenario
    recommendations["weekly_forecast_units"] *= config["demand_multiplier"]
    recommendations["effective_lead_time_days"] = (
        recommendations["supplier_lead_time_days"] * config["lead_time_multiplier"]
    )
    recommendations["usable_transfer_units"] = np.where(
        recommendations["transfer_eta_days"] <= recommendations["effective_lead_time_days"],
        recommendations["open_transfer_units"],
        0,
    )
    lead_weeks = recommendations["effective_lead_time_days"] / 7
    recommendations["projected_at_replenishment_units"] = (
        recommendations["on_hand_units"]
        + recommendations["usable_transfer_units"]
        - recommendations["weekly_forecast_units"] * lead_weeks
    )
    recommendations["weeks_of_cover"] = (
        recommendations["on_hand_units"] + recommendations["usable_transfer_units"]
    ) / recommendations["weekly_forecast_units"]
    target_position = (
        recommendations["weekly_forecast_units"] * (lead_weeks + target_cover_weeks)
        + recommendations["safety_stock_units"]
    )
    shortage = (
        target_position
        - recommendations["on_hand_units"]
        - recommendations["usable_transfer_units"]
    ).clip(lower=0)
    recommendations["recommended_order_units"] = [
        int(math.ceil(units / pack) * pack) if units > 0 else 0
        for units, pack in zip(shortage, recommendations["pack_size"])
    ]
    recommendations["risk"] = [
        _risk_label(projected, safety, cover)
        for projected, safety, cover in zip(
            recommendations["projected_at_replenishment_units"],
            recommendations["safety_stock_units"],
            recommendations["weeks_of_cover"],
        )
    ]
    priority = {"stockout": 0, "below_safety": 1, "excess": 2, "healthy": 3}
    recommendations["priority"] = recommendations["risk"].map(priority)
    recommendations["recommended_action"] = [
        _action_text(risk, order_units)
        for risk, order_units in zip(
            recommendations["risk"], recommendations["recommended_order_units"]
        )
    ]
    rounded = ["weekly_forecast_units", "projected_at_replenishment_units", "weeks_of_cover"]
    recommendations[rounded] = recommendations[rounded].round(1)
    return recommendations.sort_values(
        ["priority", "recommended_order_units"], ascending=[True, False]
    ).reset_index(drop=True)


def compare_scenarios(demand: pd.DataFrame, inventory: pd.DataFrame) -> pd.DataFrame:
    """Summarize how the decision queue changes under operating stress."""
    rows: list[dict[str, object]] = []
    for scenario in SCENARIOS:
        result = build_recommendations(demand, inventory, scenario=scenario)
        rows.append(
            {
                "scenario": scenario,
                "stockout_count": int((result["risk"] == "stockout").sum()),
                "below_safety_count": int((result["risk"] == "below_safety").sum()),
                "excess_count": int((result["risk"] == "excess").sum()),
                "recommended_order_units": int(result["recommended_order_units"].sum()),
            }
        )
    return pd.DataFrame(rows)
