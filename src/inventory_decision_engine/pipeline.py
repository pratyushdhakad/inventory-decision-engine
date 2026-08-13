"""Run the synthetic inventory decision pipeline end to end."""

from __future__ import annotations

import json
from pathlib import Path

from .engine import build_recommendations, compare_scenarios
from .generate_data import generate_inputs
from .report import build_dashboard


def run(root: Path = Path(".")) -> dict[str, object]:
    data_dir = root / "data"
    artifact_dir = root / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)

    demand, inventory = generate_inputs(data_dir)
    recommendations = build_recommendations(demand, inventory)
    scenarios = compare_scenarios(demand, inventory)
    recommendations.to_csv(artifact_dir / "recommendations.csv", index=False)
    scenarios.to_csv(artifact_dir / "scenario_summary.csv", index=False)
    build_dashboard(demand, inventory, root / "dashboard" / "index.html")

    summary = {
        "sku_warehouse_decisions": int(len(recommendations)),
        "stockout_count": int((recommendations["risk"] == "stockout").sum()),
        "below_safety_count": int((recommendations["risk"] == "below_safety").sum()),
        "excess_count": int((recommendations["risk"] == "excess").sum()),
        "recommended_order_units": int(recommendations["recommended_order_units"].sum()),
        "highest_priority_sku": str(recommendations.iloc[0]["sku_id"]),
        "highest_priority_warehouse": str(recommendations.iloc[0]["warehouse"]),
    }
    (artifact_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
