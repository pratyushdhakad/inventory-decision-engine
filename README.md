# Inventory Decision Engine

An interactive decision-support system that turns SKU demand, inventory, safety stock, transfers, and supplier lead times into explainable replenishment recommendations.

**[Open the live planner dashboard](https://pratyushdhakad.github.io/inventory-decision-engine/)**

> Portfolio demonstration using synthetic data only. The operating logic is inspired by real planning problems, not copied from any employer system.

## Day 3 build status

The tested decision engine now powers a responsive planner cockpit. It currently:

- generates reproducible 12-week SKU demand and inventory snapshots;
- produces a blended four-week demand forecast;
- credits inbound transfers only when they arrive inside the replenishment window;
- classifies stockout, below-safety, healthy, and excess-inventory risk;
- rounds suggested orders to supplier pack sizes; and
- compares base, promotion, and supplier-delay scenarios;
- filters the decision queue by risk, SKU, or warehouse;
- explains the inputs behind each recommended action; and
- deploys the static dashboard automatically through GitHub Pages.

## The business question

For each SKU and warehouse, what action should a planner take now—and why?

The output is designed for a supply-chain or inventory owner who needs a short, auditable queue of decisions instead of another raw forecast export. The live dashboard makes scenario changes visible without hiding the assumptions behind them.

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
make test
make run
```

Generated outputs are written to `artifacts/`, and the self-contained dashboard is written to `dashboard/index.html`.

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
dashboard/                       interactive planner cockpit and social preview
docs/                            assumptions and decision rules
.github/workflows/               continuous integration and Pages deployment
```

## Current limitations

- The forecast is deliberately interpretable; it does not model seasonality or causal promotion effects.
- Order suggestions assume one supplier lead time and pack size per SKU/warehouse.
- Recommendations support human review; they do not place purchase orders.
- Service levels, carrying cost, minimum order quantities, and supplier capacity are future extensions.

## License

MIT
