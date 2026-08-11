# Decision rules and assumptions

## Why the output is a decision queue

A forecast alone does not tell an inventory planner what to do. The engine combines expected demand with the stock that will actually be usable before replenishment arrives, then returns a risk label, suggested quantity, and plain-language action.

## Forecast

The weekly forecast blends two interpretable signals:

- 70%: recency-weighted average of the latest four weeks;
- 30%: average of up to 12 weeks.

This responds to recent movement without abandoning the longer baseline. It is intentionally simpler than a production seasonal model so every recommendation remains explainable in an interview or planning review.

## Transfer timing

Open transfers count only when their ETA is within the effective supplier lead-time window. A late transfer may eventually help inventory, but crediting it before it arrives would hide near-term stockout risk.

## Projected position

```text
projected at replenishment
  = on hand
  + usable transfers
  - forecast demand during lead time
```

## Risk labels

- `stockout`: projected position is below zero before replenishment.
- `below_safety`: projected position is nonnegative but below safety stock.
- `excess`: current usable stock is greater than eight forecast weeks.
- `healthy`: no immediate exception under the current rules.

## Replenishment quantity

The target covers supplier lead time, two additional operating weeks, and safety stock. Suggested orders are rounded up to full pack sizes. The engine never automatically submits an order.

## Scenarios

- `base`: current forecast and lead time.
- `promotion`: demand increases 25%.
- `supplier_delay`: lead time increases 50%.

These are sensitivity tests, not probabilistic predictions.

## Production extensions

A production version should incorporate service-level targets, minimum order quantities, carrying and stockout costs, supplier capacity, order calendars, seasonality, promotion features, substitutions, and planner feedback.
