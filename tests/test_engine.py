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


if __name__ == "__main__":
    unittest.main()
