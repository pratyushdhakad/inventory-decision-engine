"""Leakage-safe walk-forward evaluation for the demand forecast."""

from __future__ import annotations

import pandas as pd

from .engine import forecast_weekly_demand


def walk_forward_backtest(demand: pd.DataFrame, minimum_training_weeks: int = 8) -> pd.DataFrame:
    """Predict each holdout week using only observations available beforehand."""
    results: list[dict[str, object]] = []
    ordered = demand.assign(week_start=pd.to_datetime(demand["week_start"]))
    for (sku_id, warehouse), group in ordered.groupby(["sku_id", "warehouse"]):
        history = group.sort_values("week_start").reset_index(drop=True)
        if len(history) <= minimum_training_weeks:
            continue
        for holdout_index in range(minimum_training_weeks, len(history)):
            training = history.iloc[:holdout_index].copy()
            holdout = history.iloc[holdout_index]
            prediction = float(
                forecast_weekly_demand(training).iloc[0]["weekly_forecast_units"]
            )
            actual = float(holdout["units_sold"])
            error = prediction - actual
            results.append(
                {
                    "sku_id": sku_id,
                    "warehouse": warehouse,
                    "week_start": holdout["week_start"].date().isoformat(),
                    "training_weeks": holdout_index,
                    "predicted_units": round(prediction, 1),
                    "actual_units": round(actual, 1),
                    "error_units": round(error, 1),
                    "absolute_error_units": round(abs(error), 1),
                }
            )
    return pd.DataFrame(results)


def summarize_backtest(backtest: pd.DataFrame) -> dict[str, object]:
    """Return interpretable portfolio-level forecast quality measures."""
    if backtest.empty:
        raise ValueError("Backtest requires at least one holdout observation")
    total_actual = float(backtest["actual_units"].sum())
    absolute_error = float(backtest["absolute_error_units"].sum())
    signed_error = float(backtest["error_units"].sum())
    wape = absolute_error / total_actual if total_actual else 0.0
    return {
        "holdout_observations": int(len(backtest)),
        "sku_warehouse_series": int(backtest[["sku_id", "warehouse"]].drop_duplicates().shape[0]),
        "mean_absolute_error_units": round(float(backtest["absolute_error_units"].mean()), 1),
        "wape_pct": round(wape * 100, 1),
        "forecast_accuracy_pct": round(max(0.0, 1 - wape) * 100, 1),
        "bias_pct": round((signed_error / total_actual * 100) if total_actual else 0.0, 1),
        "method": "Walk-forward holdout; each prediction uses prior weeks only",
    }
