from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import pandas as pd

from inventory_decision_engine.engine import (
    build_recommendations,
    compare_scenarios,
    validate_inputs,
)
from inventory_decision_engine.generate_data import generate_inputs
from inventory_decision_engine.evaluation import summarize_backtest, walk_forward_backtest
from inventory_decision_engine.impact import summarize_modeled_impact
from inventory_decision_engine.report import build_dashboard


class InventoryDecisionEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = TemporaryDirectory()
        self.demand, self.inventory = generate_inputs(Path(self.temp_dir.name))

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_generator_creates_twelve_weeks_per_sku_warehouse(self) -> None:
        counts = self.demand.groupby(["sku_id", "warehouse"]).size()
        self.assertTrue((counts == 12).all())

    def test_late_transfer_is_not_credited(self) -> None:
        result = build_recommendations(self.demand, self.inventory)
        row = result.query("sku_id == 'HOME-CLEAN-01' and warehouse == 'east'").iloc[0]
        self.assertGreater(row["open_transfer_units"], 0)
        self.assertEqual(row["usable_transfer_units"], 0)

    def test_orders_are_rounded_to_pack_size(self) -> None:
        result = build_recommendations(self.demand, self.inventory)
        ordered = result[result["recommended_order_units"] > 0]
        remainder = ordered["recommended_order_units"] % ordered["pack_size"]
        self.assertTrue((remainder == 0).all())

    def test_promotion_increases_recommended_units(self) -> None:
        scenarios = compare_scenarios(self.demand, self.inventory).set_index("scenario")
        self.assertGreater(
            scenarios.loc["promotion", "recommended_order_units"],
            scenarios.loc["base", "recommended_order_units"],
        )

    def test_stockout_queue_contains_expedite_action(self) -> None:
        result = build_recommendations(self.demand, self.inventory)
        stockouts = result[result["risk"] == "stockout"]
        self.assertFalse(stockouts.empty)
        self.assertTrue(stockouts["recommended_action"].str.startswith("Expedite").all())

    def test_duplicate_demand_key_fails_validation(self) -> None:
        duplicate = pd.concat([self.demand, self.demand.iloc[[0]]], ignore_index=True)
        with self.assertRaisesRegex(ValueError, "Demand keys must be unique"):
            validate_inputs(duplicate, self.inventory)

    def test_dashboard_embeds_scenarios_and_decision_controls(self) -> None:
        dashboard = Path(self.temp_dir.name) / "dashboard" / "index.html"
        build_dashboard(self.demand, self.inventory, dashboard)
        html = dashboard.read_text()
        self.assertIn('data-scenario="promotion"', html)
        self.assertIn('data-scenario="supplier_delay"', html)
        self.assertIn("Planner decision queue", html)
        self.assertIn("HOME-CLEAN-01", html)
        self.assertIn("Forecast trust check", html)
        self.assertIn("Modeled decision exposure", html)

    def test_walk_forward_backtest_uses_four_holdouts_per_series(self) -> None:
        backtest = walk_forward_backtest(self.demand)
        counts = backtest.groupby(["sku_id", "warehouse"]).size()
        self.assertTrue((counts == 4).all())
        summary = summarize_backtest(backtest)
        self.assertEqual(summary["holdout_observations"], 48)
        self.assertGreater(summary["forecast_accuracy_pct"], 0)
        self.assertLessEqual(summary["forecast_accuracy_pct"], 100)

    def test_backtest_prediction_does_not_use_holdout_actual(self) -> None:
        baseline = walk_forward_backtest(self.demand)
        changed = self.demand.copy()
        target_index = changed.sort_values("week_start").index[-1]
        changed.loc[target_index, "units_sold"] *= 20
        revised = walk_forward_backtest(changed)
        key = ["sku_id", "warehouse", "week_start", "predicted_units"]
        baseline_predictions = baseline[key].sort_values(key[:3]).reset_index(drop=True)
        revised_predictions = revised[key].sort_values(key[:3]).reset_index(drop=True)
        pd.testing.assert_frame_equal(baseline_predictions, revised_predictions)

    def test_modeled_impact_is_labeled_and_nonnegative(self) -> None:
        recommendations = build_recommendations(self.demand, self.inventory)
        impact = summarize_modeled_impact(recommendations)
        self.assertGreater(impact["purchase_commitment_usd"], 0)
        self.assertGreaterEqual(impact["excess_working_capital_usd"], 0)
        self.assertIn("not realized", impact["interpretation"])


if __name__ == "__main__":
    unittest.main()
