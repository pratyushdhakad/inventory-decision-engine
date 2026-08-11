# Inventory Decision Engine

An in-progress decision-support system that turns SKU demand, inventory, safety stock, transfers, and supplier lead times into explainable replenishment recommendations.

> Portfolio demonstration using synthetic data only. The operating logic is inspired by real planning problems, not copied from any employer system.

## Day 2 build status

The decision engine is live locally and covered by automated tests. It currently:

- generates reproducible 12-week SKU demand and inventory snapshots;
- produces a blended four-week demand forecast;
- credits inbound transfers only when they arrive inside the replenishment window;
- classifies stockout, below-safety, healthy, and excess-inventory risk;
- rounds suggested orders to supplier pack sizes; and
- compares base, promotion, and supplier-delay scenarios.

Next: add the decision-oriented dashboard, visual scenario controls, and a live demo.

## The business question

For each SKU and warehouse, what action should a planner take now—and why?

The output is designed for a supply-chain or inventory owner who needs a short, auditable queue of decisions instead of another raw forecast export.

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
make test
make run
```

Generated outputs are written to `artifacts/`.

## Decision flow

```mermaid
flowchart LR
    A[12-week demand] --> C[Demand forecast]
    B[Inventory + transfers] --> D[Projected position]
    C --> D
    D --> E[Risk classification]
    E --> F[Pack-rounded recommendation]
    F --> G[Planner decision queue]
```

## AI-augmented build method

I use AI as an engineering multiplier for implementation, edge-case generation, and documentation. I own the business framing, assumptions, architecture, validation rules, evaluation, and every published decision. Generated work is not accepted until it runs, passes tests, and can be explained.

## Repository map

```text
src/inventory_decision_engine/   generation, validation, forecasting, decisions
sql/                             portable inventory-position model
tests/                           business-rule and pipeline tests
data/                            deterministic synthetic inputs
artifacts/                       generated recommendations and scenario summary
docs/                            assumptions and decision rules
.github/workflows/               continuous integration
```

## Current limitations

- The forecast is deliberately interpretable; it does not model seasonality or causal promotion effects.
- Order suggestions assume one supplier lead time and pack size per SKU/warehouse.
- Recommendations support human review; they do not place purchase orders.
- Service levels, carrying cost, minimum order quantities, and supplier capacity are future extensions.

## License

MIT
