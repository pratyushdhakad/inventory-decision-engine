-- Portable starting point for the inventory-position layer.
-- Replace DATE_DIFF syntax as needed for the target warehouse.

WITH demand_12_week AS (
    SELECT
        sku_id,
        warehouse,
        AVG(units_sold) AS average_weekly_demand,
        COUNT(DISTINCT week_start) AS observed_weeks
    FROM weekly_demand
    WHERE week_start >= CURRENT_DATE - INTERVAL '84' DAY
    GROUP BY 1, 2
),

inventory_position AS (
    SELECT
        inventory.sku_id,
        inventory.warehouse,
        demand.average_weekly_demand,
        inventory.on_hand_units,
        inventory.safety_stock_units,
        inventory.supplier_lead_time_days,
        CASE
            WHEN inventory.transfer_eta_days <= inventory.supplier_lead_time_days
                THEN inventory.open_transfer_units
            ELSE 0
        END AS usable_transfer_units
    FROM inventory_snapshot AS inventory
    INNER JOIN demand_12_week AS demand
        ON inventory.sku_id = demand.sku_id
       AND inventory.warehouse = demand.warehouse
)

SELECT
    *,
    on_hand_units
        + usable_transfer_units
        - average_weekly_demand * supplier_lead_time_days / 7.0
        AS projected_at_replenishment_units,
    (on_hand_units + usable_transfer_units)
        / NULLIF(average_weekly_demand, 0)
        AS weeks_of_cover
FROM inventory_position;
