"""Create deterministic synthetic demand and inventory inputs."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


PRODUCTS = {
    "HOME-CLEAN-01": {"category": "home", "weekly_demand": 720, "lead_time_days": 21, "pack_size": 24},
    "HOME-CLEAN-02": {"category": "home", "weekly_demand": 460, "lead_time_days": 28, "pack_size": 20},
    "LAUNDRY-01": {"category": "laundry", "weekly_demand": 920, "lead_time_days": 35, "pack_size": 36},
    "LAUNDRY-02": {"category": "laundry", "weekly_demand": 540, "lead_time_days": 21, "pack_size": 24},
    "KITCHEN-01": {"category": "kitchen", "weekly_demand": 330, "lead_time_days": 42, "pack_size": 12},
    "BUNDLE-01": {"category": "bundle", "weekly_demand": 210, "lead_time_days": 14, "pack_size": 10},
}

WAREHOUSE_SHARE = {"east": 0.64, "west": 0.36}

# Coverage choices intentionally produce a mix of decision outcomes.
INVENTORY_COVER_WEEKS = {
    ("HOME-CLEAN-01", "east"): 1.2,
    ("HOME-CLEAN-01", "west"): 5.0,
    ("HOME-CLEAN-02", "east"): 4.0,
    ("HOME-CLEAN-02", "west"): 10.0,
    ("LAUNDRY-01", "east"): 2.0,
    ("LAUNDRY-01", "west"): 3.0,
    ("LAUNDRY-02", "east"): 6.0,
    ("LAUNDRY-02", "west"): 1.5,
    ("KITCHEN-01", "east"): 8.0,
    ("KITCHEN-01", "west"): 12.0,
    ("BUNDLE-01", "east"): 3.5,
    ("BUNDLE-01", "west"): 4.5,
}


def generate_inputs(output_dir: Path, seed: int = 41) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Generate 12 weeks of demand plus one current inventory snapshot."""
    rng = np.random.default_rng(seed)
    weeks = pd.date_range("2026-05-11", periods=12, freq="W-MON")
    demand_rows: list[dict[str, object]] = []
    inventory_rows: list[dict[str, object]] = []

    for sku_index, (sku_id, product) in enumerate(PRODUCTS.items()):
        for warehouse, share in WAREHOUSE_SHARE.items():
            baseline = float(product["weekly_demand"]) * share
            for week_index, week_start in enumerate(weeks):
                trend = 1 + (week_index * 0.008)
                promotion = 1.18 if sku_index in {0, 2} and week_index == 10 else 1.0
                noise = rng.normal(1.0, 0.055)
                units = max(0, round(baseline * trend * promotion * noise))
                demand_rows.append(
                    {
                        "sku_id": sku_id,
                        "category": product["category"],
                        "warehouse": warehouse,
                        "week_start": week_start.date().isoformat(),
                        "units_sold": units,
                    }
                )

            cover = INVENTORY_COVER_WEEKS[(sku_id, warehouse)]
            on_hand = round(baseline * cover)
            safety_stock = round(baseline * 1.25)
            transfer_units = round(baseline * 0.7) if cover < 2.5 else 0
            transfer_eta = 14 if sku_id != "HOME-CLEAN-01" else 35
            inventory_rows.append(
                {
                    "sku_id": sku_id,
                    "warehouse": warehouse,
                    "on_hand_units": on_hand,
                    "open_transfer_units": transfer_units,
                    "transfer_eta_days": transfer_eta if transfer_units else 0,
                    "supplier_lead_time_days": product["lead_time_days"],
                    "safety_stock_units": safety_stock,
                    "pack_size": product["pack_size"],
                }
            )

    demand = pd.DataFrame(demand_rows)
    inventory = pd.DataFrame(inventory_rows)
    output_dir.mkdir(parents=True, exist_ok=True)
    demand.to_csv(output_dir / "weekly_demand.csv", index=False)
    inventory.to_csv(output_dir / "inventory_snapshot.csv", index=False)
    return demand, inventory


if __name__ == "__main__":
    generate_inputs(Path("data"))
