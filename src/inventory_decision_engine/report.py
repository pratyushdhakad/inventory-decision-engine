"""Generate a self-contained interactive inventory planning dashboard."""

from __future__ import annotations

import json
from html import escape
from pathlib import Path

import pandas as pd

from .engine import SCENARIOS, build_recommendations
from .evaluation import summarize_backtest, walk_forward_backtest
from .impact import summarize_modeled_impact


def _records(frame: pd.DataFrame) -> list[dict[str, object]]:
    return json.loads(frame.to_json(orient="records"))


def build_dashboard(demand: pd.DataFrame, inventory: pd.DataFrame, output_path: Path) -> Path:
    """Write a portable dashboard with all scenario data embedded."""
    scenario_data: dict[str, dict[str, object]] = {}
    for scenario in SCENARIOS:
        recommendations = build_recommendations(demand, inventory, scenario=scenario)
        scenario_data[scenario] = {
            "rows": _records(recommendations),
            "summary": {
                "stockout": int((recommendations["risk"] == "stockout").sum()),
                "below_safety": int((recommendations["risk"] == "below_safety").sum()),
                "healthy": int((recommendations["risk"] == "healthy").sum()),
                "excess": int((recommendations["risk"] == "excess").sum()),
                "order_units": int(recommendations["recommended_order_units"].sum()),
                "at_risk_units": int(
                    recommendations.loc[
                        recommendations["risk"].isin(["stockout", "below_safety"]),
                        "recommended_order_units",
                    ].sum()
                ),
                **summarize_modeled_impact(recommendations),
            },
        }

    evaluation = summarize_backtest(walk_forward_backtest(demand))
    latest_week = escape(str(pd.to_datetime(demand["week_start"]).max().date()))
    payload = json.dumps(scenario_data, separators=(",", ":"))
    evaluation_payload = json.dumps(evaluation, separators=(",", ":"))
    html = (
        DASHBOARD_TEMPLATE.replace("__SCENARIO_DATA__", payload)
        .replace("__EVALUATION_DATA__", evaluation_payload)
        .replace("__LATEST_WEEK__", latest_week)
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html)
    return output_path


DASHBOARD_TEMPLATE = r'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="An interactive inventory planning cockpit for explainable replenishment decisions and supply scenarios.">
  <meta property="og:title" content="Inventory Decision Engine">
  <meta property="og:description" content="Forecast risk. Stress-test supply. Act earlier.">
  <meta property="og:image" content="https://pratyushdhakad.github.io/inventory-decision-engine/og.png">
  <meta property="og:type" content="website">
  <meta name="twitter:card" content="summary_large_image">
  <title>Inventory Decision Engine</title>
  <style>
    :root {
      --ink: #102129; --muted: #607078; --paper: #f4f0e8; --panel: #fffdf8;
      --line: #d8d2c5; --cyan: #177f91; --cyan-soft: #d9eef0; --amber: #c27b17;
      --amber-soft: #f7e8c9; --coral: #c94d3d; --coral-soft: #f8dfda;
      --green: #4e785f; --green-soft: #e1ece4; --navy: #0d2631;
      --shadow: 0 16px 40px rgba(16,33,41,.08); --radius: 18px;
    }
    * { box-sizing: border-box; }
    body { margin: 0; background: var(--paper); color: var(--ink); font: 15px/1.5 Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
    button, input { font: inherit; }
    button { cursor: pointer; }
    .shell { max-width: 1440px; margin: 0 auto; padding: 28px; }
    .topbar { display: flex; align-items: flex-start; justify-content: space-between; gap: 24px; margin-bottom: 26px; }
    .eyebrow { color: var(--cyan); font-size: 12px; font-weight: 800; letter-spacing: .14em; text-transform: uppercase; }
    h1 { margin: 6px 0 7px; font: 800 clamp(30px, 4vw, 54px)/1.02 Georgia, serif; letter-spacing: -.035em; }
    .dek { max-width: 700px; margin: 0; color: var(--muted); font-size: 17px; }
    .freshness { text-align: right; color: var(--muted); font-size: 13px; }
    .freshness strong { display: block; color: var(--ink); font-size: 14px; }
    .scenario-strip { background: var(--navy); border-radius: var(--radius); padding: 18px; color: white; box-shadow: var(--shadow); display: flex; align-items: center; gap: 18px; margin-bottom: 18px; }
    .scenario-copy { min-width: 250px; }
    .scenario-copy strong { display: block; font-size: 16px; }
    .scenario-copy span { color: #b6c8cf; font-size: 13px; }
    .scenario-buttons { display: grid; grid-template-columns: repeat(3, 1fr); gap: 9px; flex: 1; }
    .scenario-button { border: 1px solid #39515b; border-radius: 12px; background: transparent; color: #cfdbdf; padding: 11px 14px; text-align: left; transition: .15s ease; }
    .scenario-button strong { display: block; color: white; font-size: 14px; }
    .scenario-button.active { background: #f8f4eb; border-color: #f8f4eb; color: var(--muted); transform: translateY(-1px); }
    .scenario-button.active strong { color: var(--ink); }
    .metrics { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; margin-bottom: 18px; }
    .metric { background: var(--panel); border: 1px solid var(--line); border-radius: 15px; padding: 19px; box-shadow: 0 8px 22px rgba(16,33,41,.04); }
    .metric .label { color: var(--muted); font-size: 12px; font-weight: 800; letter-spacing: .08em; text-transform: uppercase; }
    .metric .value { display: block; margin-top: 5px; font: 800 30px/1.15 Georgia, serif; }
    .metric .delta { color: var(--muted); font-size: 12px; }
    .metric.urgent { border-top: 4px solid var(--coral); }
    .metric.order { border-top: 4px solid var(--amber); }
    .evidence-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 18px; }
    .evidence-card { background: var(--navy); color: white; border-radius: var(--radius); padding: 20px 22px; box-shadow: var(--shadow); }
    .evidence-card.impact { background: #fffdf8; color: var(--ink); border: 1px solid var(--line); }
    .evidence-card h2 { margin: 0 0 4px; font: 700 20px/1.1 Georgia, serif; }
    .evidence-card > p { margin: 0 0 16px; color: #b6c8cf; font-size: 12px; }
    .evidence-card.impact > p { color: var(--muted); }
    .evidence-values { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
    .evidence-value { border-left: 1px solid #39515b; padding-left: 11px; }
    .impact .evidence-value { border-left-color: var(--line); }
    .evidence-value span { display: block; color: #b6c8cf; font-size: 10px; font-weight: 800; letter-spacing: .05em; text-transform: uppercase; }
    .impact .evidence-value span { color: var(--muted); }
    .evidence-value strong { display: block; margin-top: 4px; font-size: 18px; }
    .grid { display: grid; grid-template-columns: minmax(0, 1.65fr) minmax(300px, .75fr); gap: 18px; align-items: start; }
    .panel { background: var(--panel); border: 1px solid var(--line); border-radius: var(--radius); box-shadow: var(--shadow); overflow: hidden; }
    .panel-header { padding: 20px 22px 14px; display: flex; align-items: center; justify-content: space-between; gap: 16px; }
    .panel-header h2 { margin: 0; font: 700 22px/1.1 Georgia, serif; }
    .panel-header p { margin: 4px 0 0; color: var(--muted); font-size: 13px; }
    .toolbar { display: flex; gap: 8px; padding: 0 22px 16px; flex-wrap: wrap; }
    .filter { border: 1px solid var(--line); border-radius: 999px; padding: 7px 12px; background: white; color: var(--muted); }
    .filter.active { background: var(--ink); color: white; border-color: var(--ink); }
    .search { margin-left: auto; min-width: 190px; border: 1px solid var(--line); border-radius: 999px; padding: 7px 12px; background: #fff; color: var(--ink); }
    .table-wrap { overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; min-width: 780px; }
    th { padding: 11px 18px; background: #eee9df; color: var(--muted); font-size: 11px; letter-spacing: .07em; text-align: left; text-transform: uppercase; }
    td { padding: 14px 18px; border-top: 1px solid #e6e0d5; vertical-align: middle; }
    tbody tr { transition: background .15s ease; cursor: pointer; }
    tbody tr:hover, tbody tr:focus { background: #f7f3eb; outline: none; }
    .sku { font-weight: 800; }
    .warehouse { color: var(--muted); font-size: 12px; text-transform: capitalize; }
    .risk { display: inline-block; border-radius: 999px; padding: 5px 9px; font-size: 11px; font-weight: 800; letter-spacing: .04em; text-transform: uppercase; }
    .risk-stockout { color: #8e2e24; background: var(--coral-soft); }
    .risk-below_safety { color: #79500e; background: var(--amber-soft); }
    .risk-excess { color: #236171; background: var(--cyan-soft); }
    .risk-healthy { color: #315b41; background: var(--green-soft); }
    .order-qty { font-weight: 800; }
    .muted { color: var(--muted); }
    .side-stack { display: grid; gap: 18px; }
    .canvas-wrap { padding: 4px 20px 20px; }
    canvas { width: 100%; height: 210px; display: block; }
    .legend { display: grid; gap: 9px; padding: 0 22px 20px; }
    .legend-row { display: grid; grid-template-columns: 88px 1fr 28px; gap: 8px; align-items: center; font-size: 12px; }
    .bar { height: 8px; border-radius: 999px; background: #e8e2d7; overflow: hidden; }
    .bar span { display: block; height: 100%; border-radius: inherit; }
    .decision-detail { padding: 0 22px 22px; }
    .empty-detail { color: var(--muted); padding: 22px 0 8px; }
    .detail-card { border-top: 1px solid var(--line); padding-top: 17px; }
    .detail-card h3 { margin: 0 0 4px; font-size: 18px; }
    .action-callout { margin: 14px 0; padding: 13px; border-radius: 12px; background: var(--navy); color: white; font-weight: 700; }
    .facts { display: grid; grid-template-columns: 1fr 1fr; gap: 9px; }
    .fact { padding: 10px; border: 1px solid var(--line); border-radius: 10px; }
    .fact span { display: block; color: var(--muted); font-size: 11px; }
    .fact strong { font-size: 15px; }
    .logic { margin: 13px 0 0; color: var(--muted); font-size: 12px; }
    footer { display: flex; justify-content: space-between; gap: 20px; padding: 22px 2px 0; color: var(--muted); font-size: 12px; }
    footer a { color: var(--cyan); font-weight: 700; }
    @media (max-width: 920px) {
      .topbar, .scenario-strip { align-items: stretch; flex-direction: column; }
      .freshness { text-align: left; }
      .scenario-buttons { width: 100%; }
      .metrics { grid-template-columns: repeat(2, 1fr); }
      .evidence-grid { grid-template-columns: 1fr; }
      .grid { grid-template-columns: 1fr; }
    }
    @media (max-width: 580px) {
      .shell { padding: 16px; }
      .scenario-buttons { grid-template-columns: 1fr; }
      .metrics { grid-template-columns: 1fr; }
      .evidence-values { grid-template-columns: repeat(2, 1fr); }
      .toolbar { align-items: stretch; }
      .search { margin-left: 0; width: 100%; }
      footer { flex-direction: column; }
    }
  </style>
</head>
<body>
  <main class="shell">
    <header class="topbar">
      <div>
        <div class="eyebrow">Decision intelligence · portfolio build</div>
        <h1>Inventory Decision Engine</h1>
        <p class="dek">Forecast risk. Stress-test supply. Act earlier. A planner-first cockpit that explains what to order, where, and why.</p>
      </div>
      <div class="freshness"><strong>Data through __LATEST_WEEK__</strong>Synthetic demonstration · 12-week demand window</div>
    </header>

    <section class="scenario-strip" aria-labelledby="scenario-title">
      <div class="scenario-copy"><strong id="scenario-title">Stress-test the plan</strong><span>Change one assumption and watch the decision queue move.</span></div>
      <div class="scenario-buttons" role="group" aria-label="Supply planning scenario">
        <button class="scenario-button active" data-scenario="base"><strong>Base plan</strong>Current demand + lead time</button>
        <button class="scenario-button" data-scenario="promotion"><strong>Promotion</strong>Demand +25%</button>
        <button class="scenario-button" data-scenario="supplier_delay"><strong>Supplier delay</strong>Lead time +50%</button>
      </div>
    </section>

    <section class="metrics" aria-label="Scenario summary">
      <article class="metric urgent"><span class="label">Stockout risks</span><strong class="value" id="stockoutMetric">—</strong><span class="delta">Requires an expedited decision</span></article>
      <article class="metric"><span class="label">Below safety</span><strong class="value" id="safetyMetric">—</strong><span class="delta">Positive stock, inadequate buffer</span></article>
      <article class="metric order"><span class="label">Order recommendation</span><strong class="value" id="orderMetric">—</strong><span class="delta">Pack-rounded units across the network</span></article>
      <article class="metric"><span class="label">Excess positions</span><strong class="value" id="excessMetric">—</strong><span class="delta">More than eight forecast weeks</span></article>
    </section>

    <section class="evidence-grid" aria-label="Evaluation and modeled business exposure">
      <article class="evidence-card">
        <h2>Forecast trust check</h2>
        <p>Walk-forward holdout: every prediction uses only the weeks available beforehand.</p>
        <div class="evidence-values">
          <div class="evidence-value"><span>Accuracy</span><strong id="accuracyEvidence">—</strong></div>
          <div class="evidence-value"><span>WAPE</span><strong id="wapeEvidence">—</strong></div>
          <div class="evidence-value"><span>Bias</span><strong id="biasEvidence">—</strong></div>
          <div class="evidence-value"><span>Holdouts</span><strong id="holdoutEvidence">—</strong></div>
        </div>
      </article>
      <article class="evidence-card impact">
        <h2>Modeled decision exposure</h2>
        <p>Synthetic unit costs + 22% annual holding rate. Exposure for review—not realized savings.</p>
        <div class="evidence-values">
          <div class="evidence-value"><span>Order value</span><strong id="purchaseEvidence">—</strong></div>
          <div class="evidence-value"><span>Stockout units</span><strong id="stockoutUnitsEvidence">—</strong></div>
          <div class="evidence-value"><span>Excess capital</span><strong id="excessCapitalEvidence">—</strong></div>
          <div class="evidence-value"><span>Holding cost</span><strong id="holdingCostEvidence">—</strong></div>
        </div>
      </article>
    </section>

    <section class="grid">
      <article class="panel">
        <div class="panel-header"><div><h2>Planner decision queue</h2><p>Urgent exceptions rise to the top. Select a row to audit the recommendation.</p></div><span id="resultCount" class="muted"></span></div>
        <div class="toolbar">
          <button class="filter active" data-risk="all">All</button>
          <button class="filter" data-risk="stockout">Stockout</button>
          <button class="filter" data-risk="below_safety">Below safety</button>
          <button class="filter" data-risk="excess">Excess</button>
          <button class="filter" data-risk="healthy">Healthy</button>
          <input class="search" id="searchBox" type="search" placeholder="Find SKU or warehouse" aria-label="Find SKU or warehouse">
        </div>
        <div class="table-wrap">
          <table>
            <thead><tr><th>SKU / location</th><th>Risk</th><th>Weeks cover</th><th>Projected position</th><th>Suggested order</th><th>Action</th></tr></thead>
            <tbody id="decisionRows"></tbody>
          </table>
        </div>
      </article>

      <aside class="side-stack">
        <article class="panel">
          <div class="panel-header"><div><h2>Network risk mix</h2><p>Count of SKU-location decisions by status</p></div></div>
          <div class="canvas-wrap"><canvas id="riskChart" width="560" height="300" aria-label="Inventory risk distribution chart"></canvas></div>
          <div class="legend" id="riskLegend"></div>
        </article>
        <article class="panel">
          <div class="panel-header"><div><h2>Why this action?</h2><p>Trace a recommendation back to its inputs.</p></div></div>
          <div class="decision-detail" id="decisionDetail"><div class="empty-detail">Select a row from the decision queue.</div></div>
        </article>
      </aside>
    </section>

    <footer><span>All data is synthetic. Recommendations support human review and never place orders.</span><a href="https://github.com/pratyushdhakad/inventory-decision-engine">View methodology and tested code on GitHub →</a></footer>
  </main>

  <script>
    const scenarioData = __SCENARIO_DATA__;
    const evaluationData = __EVALUATION_DATA__;
    const riskMeta = {
      stockout: {label: "Stockout", color: "#c94d3d"},
      below_safety: {label: "Below safety", color: "#c27b17"},
      excess: {label: "Excess", color: "#177f91"},
      healthy: {label: "Healthy", color: "#4e785f"}
    };
    let activeScenario = "base";
    let activeRisk = "all";
    let searchTerm = "";

    const number = value => new Intl.NumberFormat("en-US", {maximumFractionDigits: 1}).format(value);
    const currency = value => new Intl.NumberFormat("en-US", {style:"currency", currency:"USD", maximumFractionDigits:0}).format(value);
    const signed = value => `${value > 0 ? "+" : ""}${number(value)}`;
    const labelScenario = key => ({base:"Base plan", promotion:"Promotion", supplier_delay:"Supplier delay"})[key];

    function filteredRows() {
      return scenarioData[activeScenario].rows.filter(row => {
        const riskMatch = activeRisk === "all" || row.risk === activeRisk;
        const text = `${row.sku_id} ${row.warehouse}`.toLowerCase();
        return riskMatch && text.includes(searchTerm);
      });
    }

    function renderMetrics() {
      const summary = scenarioData[activeScenario].summary;
      document.querySelector("#stockoutMetric").textContent = summary.stockout;
      document.querySelector("#safetyMetric").textContent = summary.below_safety;
      document.querySelector("#orderMetric").textContent = number(summary.order_units);
      document.querySelector("#excessMetric").textContent = summary.excess;
      document.querySelector("#purchaseEvidence").textContent = currency(summary.purchase_commitment_usd);
      document.querySelector("#stockoutUnitsEvidence").textContent = number(summary.stockout_exposure_units);
      document.querySelector("#excessCapitalEvidence").textContent = currency(summary.excess_working_capital_usd);
      document.querySelector("#holdingCostEvidence").textContent = currency(summary.estimated_annual_holding_cost_usd);
    }

    function renderTable() {
      const rows = filteredRows();
      document.querySelector("#resultCount").textContent = `${rows.length} decisions`;
      document.querySelector("#decisionRows").innerHTML = rows.map((row, index) => `
        <tr tabindex="0" data-row="${index}">
          <td><div class="sku">${row.sku_id}</div><div class="warehouse">${row.warehouse} warehouse</div></td>
          <td><span class="risk risk-${row.risk}">${riskMeta[row.risk].label}</span></td>
          <td>${number(row.weeks_of_cover)}</td>
          <td>${signed(row.projected_at_replenishment_units)}</td>
          <td class="order-qty">${number(row.recommended_order_units)}</td>
          <td>${row.recommended_action}</td>
        </tr>`).join("") || `<tr><td colspan="6" class="muted">No decisions match this filter.</td></tr>`;
      document.querySelectorAll("#decisionRows tr[data-row]").forEach(element => {
        const open = () => renderDetail(rows[Number(element.dataset.row)]);
        element.addEventListener("click", open);
        element.addEventListener("keydown", event => { if (event.key === "Enter" || event.key === " ") open(); });
      });
    }

    function renderDetail(row) {
      const transferNote = row.usable_transfer_units > 0
        ? `${number(row.usable_transfer_units)} transfer units arrive inside the ${number(row.effective_lead_time_days)}-day window.`
        : row.open_transfer_units > 0
          ? `${number(row.open_transfer_units)} open transfer units arrive too late to reduce near-term risk.`
          : "No open transfer is available for this decision window.";
      document.querySelector("#decisionDetail").innerHTML = `
        <div class="detail-card">
          <h3>${row.sku_id} · ${row.warehouse}</h3>
          <span class="risk risk-${row.risk}">${riskMeta[row.risk].label} · ${labelScenario(activeScenario)}</span>
          <div class="action-callout">${row.recommended_action}</div>
          <div class="facts">
            <div class="fact"><span>Weekly forecast</span><strong>${number(row.weekly_forecast_units)}</strong></div>
            <div class="fact"><span>On hand</span><strong>${number(row.on_hand_units)}</strong></div>
            <div class="fact"><span>Safety stock</span><strong>${number(row.safety_stock_units)}</strong></div>
            <div class="fact"><span>Lead time</span><strong>${number(row.effective_lead_time_days)} days</strong></div>
            <div class="fact"><span>Modeled order value</span><strong>${currency(row.recommended_order_value_usd)}</strong></div>
            <div class="fact"><span>Stockout exposure</span><strong>${number(row.stockout_exposure_units)} units</strong></div>
          </div>
          <p class="logic">${transferNote} The projected position is ${signed(row.projected_at_replenishment_units)} units when replenishment would arrive. The order suggestion covers lead-time demand, two operating weeks, and safety stock, rounded to packs of ${row.pack_size}.</p>
        </div>`;
    }

    function renderRiskChart() {
      const summary = scenarioData[activeScenario].summary;
      const canvas = document.querySelector("#riskChart");
      const ctx = canvas.getContext("2d");
      const ratio = window.devicePixelRatio || 1;
      const width = canvas.clientWidth;
      const height = 210;
      canvas.width = width * ratio; canvas.height = height * ratio;
      ctx.scale(ratio, ratio); ctx.clearRect(0, 0, width, height);
      const values = [summary.stockout, summary.below_safety, summary.excess, summary.healthy];
      const keys = ["stockout", "below_safety", "excess", "healthy"];
      const max = Math.max(...values, 1);
      keys.forEach((key, index) => {
        const x = 18 + index * ((width - 36) / 4);
        const barWidth = Math.max(28, ((width - 72) / 4) - 20);
        const barHeight = (values[index] / max) * 135;
        ctx.fillStyle = "#e8e2d7"; ctx.fillRect(x, 24, barWidth, 150);
        ctx.fillStyle = riskMeta[key].color; ctx.fillRect(x, 174 - barHeight, barWidth, barHeight);
        ctx.fillStyle = "#102129"; ctx.font = "700 14px system-ui"; ctx.fillText(values[index], x, 198);
      });
      document.querySelector("#riskLegend").innerHTML = keys.map(key => {
        const value = summary[key];
        return `<div class="legend-row"><span>${riskMeta[key].label}</span><div class="bar"><span style="width:${(value/max)*100}%;background:${riskMeta[key].color}"></span></div><strong>${value}</strong></div>`;
      }).join("");
    }

    function renderEvaluation() {
      document.querySelector("#accuracyEvidence").textContent = `${evaluationData.forecast_accuracy_pct}%`;
      document.querySelector("#wapeEvidence").textContent = `${evaluationData.wape_pct}%`;
      document.querySelector("#biasEvidence").textContent = `${evaluationData.bias_pct > 0 ? "+" : ""}${evaluationData.bias_pct}%`;
      document.querySelector("#holdoutEvidence").textContent = evaluationData.holdout_observations;
    }
    function renderAll() { renderMetrics(); renderTable(); renderRiskChart(); renderEvaluation(); document.querySelector("#decisionDetail").innerHTML = '<div class="empty-detail">Select a row from the decision queue.</div>'; }
    document.querySelectorAll(".scenario-button").forEach(button => button.addEventListener("click", () => {
      activeScenario = button.dataset.scenario;
      document.querySelectorAll(".scenario-button").forEach(item => item.classList.toggle("active", item === button));
      renderAll();
    }));
    document.querySelectorAll(".filter").forEach(button => button.addEventListener("click", () => {
      activeRisk = button.dataset.risk;
      document.querySelectorAll(".filter").forEach(item => item.classList.toggle("active", item === button));
      renderTable();
    }));
    document.querySelector("#searchBox").addEventListener("input", event => { searchTerm = event.target.value.trim().toLowerCase(); renderTable(); });
    window.addEventListener("resize", renderRiskChart);
    renderAll();
  </script>
</body>
</html>'''
