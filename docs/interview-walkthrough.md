# Five-minute interview walkthrough

## 0:00–0:45 — Frame the decision

Inventory teams often have demand, safety stock, transfers, and on-hand balances in separate reports. The hard question is not “what is the forecast?” It is “what action should a planner take now, where, and why?”

This project converts synthetic planning inputs into an auditable decision queue for each SKU and warehouse.

## 0:45–1:45 — Explain the data flow

1. Generate 12 weeks of reproducible SKU demand and a current inventory snapshot.
2. Validate keys, nulls, quantities, and pack sizes before calculating decisions.
3. Blend a recency-weighted four-week signal with the 12-week mean.
4. Credit an inbound transfer only when it arrives inside the effective lead-time window.
5. Project the inventory position at replenishment and classify stockout, below-safety, healthy, or excess risk.
6. Round suggested orders to complete supplier packs.

## 1:45–2:45 — Demonstrate the dashboard

Start with the base plan. Show that urgent stockouts rise to the top, then select a row to expose its forecast, on-hand balance, safety stock, lead time, transfer treatment, projected position, and modeled order value.

Switch to the promotion scenario to increase demand 25%, then to supplier delay to increase lead time 50%. The decision queue and modeled exposure update immediately.

## 2:45–3:35 — Defend forecast quality

The dashboard reports a walk-forward backtest, not in-sample fit. Each of the final four weeks is predicted using only earlier observations, producing 48 holdouts across 12 SKU-location series. WAPE, bias, MAE, and a clearly defined accuracy score make the result interpretable.

The test suite includes an anti-leakage guard: changing a holdout actual cannot change the prediction made for that holdout.

## 3:35–4:20 — Discuss business value honestly

The engine attaches synthetic unit costs and a 22% annual holding-rate assumption to expose purchase commitment, stockout units, excess working capital, and potential holding cost for review.

These are modeled decision exposures—not realized savings. The dashboard labels that distinction directly so an executive can use the estimate without mistaking it for booked impact.

## 4:20–5:00 — Production trade-offs

A production version would add service-level targets, minimum order quantities, supplier calendars and capacity, promotions, seasonality, substitutions, carrying and stockout costs, role-based access, and planner feedback. Recommendations would remain human-reviewed until monitoring demonstrated reliable performance.

## Questions I can answer

- Why use WAPE instead of MAPE?
- How does the code prevent forecast leakage?
- When should an inbound transfer count toward available stock?
- Why round after calculating the target position?
- How would I calibrate safety stock and service levels?
- Which parts should remain rules and which should become learned models?
