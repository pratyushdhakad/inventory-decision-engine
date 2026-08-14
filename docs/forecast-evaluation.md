# Forecast evaluation

## Evaluation question

Would the forecast have been useful before the actual demand was known?

The evaluation uses a walk-forward holdout. For every SKU and warehouse, weeks 9–12 are predicted one at a time using only the weeks available beforehand. This creates 48 holdout observations across 12 SKU-location series without leaking future demand into the training window.

## Metrics

- **WAPE:** total absolute error divided by total actual units. This weights error by business volume and is stable across differently sized SKUs.
- **Forecast accuracy:** `max(0, 1 − WAPE)`. This is a communication metric, not a universal statistical definition.
- **Bias:** signed error divided by actual units. Positive bias means over-forecasting; negative bias means under-forecasting.
- **MAE:** average absolute unit error across holdouts.

## What the test does not prove

The synthetic history is short and intentionally regular. A strong result here validates implementation and evaluation discipline; it does not prove production accuracy. A production review would compare seasonal-naive, moving-average, and causal models across longer history, promotions, stockouts, launches, and channel shifts.

## Guardrail

`test_backtest_prediction_does_not_use_holdout_actual` changes a holdout actual after generating the baseline. The corresponding prediction must remain unchanged, demonstrating that the forecast did not see the value it was asked to predict.
