# Water Waste / Non-Revenue Water (NRW) Simulator

Streams real-time **non-revenue water** and flow balance telemetry from **12 District Metered Areas (DMAs)** to Azure Event Hub for ingestion into Microsoft Fabric Real-Time Intelligence.

---

## What is Non-Revenue Water (NRW)?

Non-Revenue Water is the difference between water **supplied** into a distribution network and water **billed** to customers. It includes:

- **Real losses** — leaks, pipe bursts, overflows from storage tanks
- **Apparent losses** — meter inaccuracies, unauthorized consumption (theft)
- **Unbilled authorized consumption** — firefighting, flushing, public fountains

Globally, utilities lose **20–40%** of treated water to NRW. Reducing NRW saves billions in water treatment costs, energy, and infrastructure damage.

---

## How District Metered Areas (DMAs) Work

A DMA is a **hydraulically isolated section** of a water distribution network where:

1. All water entering the zone is **metered at inlet points**
2. All water consumed is **metered at customer connections**
3. The **difference** (flow balance delta) reveals losses

By monitoring DMAs continuously, utilities can:
- Detect new leaks within hours (not weeks)
- Measure **Minimum Night Flow (MNF)** — the flow at 2–4 AM when legitimate consumption is minimal
- Prioritize repair crews to the worst-performing zones
- Track NRW trends over time

---

## Setup

### 1. Install Dependencies

```bash
cd water-waste
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Add the following to your `.env` file in the project root:

```env
EVENTHUB_WASTE_CONN_STR=<your-event-hub-connection-string>
EVENTHUB_WASTE_NAME=water-waste
```

### 3. Run the Simulator

```bash
python water_waste.py
```

You'll see output like:

```
Water Waste / Non-Revenue Water Simulator Starting...
Monitoring 12 District Metered Areas (DMAs)
Anomaly injection rate: 5%
Reading interval: 15-30s
================================================================================
[NRW] DMA-001 Capitol Hill Zone        NRW: 11.3%  Inlet:72PSI  Outlet:63PSI  Delta:0.312MGD
[NRW] DMA-003 Anacostia Zone           NRW:  8.7%  Inlet:68PSI  Outlet:58PSI  Delta:0.278MGD
[NRW] DMA-005 Adams Morgan Zone        NRW: 34.2%  Inlet:48PSI  Outlet:42PSI  Delta:0.893MGD  *** ALERT: pipe_burst ***
```

---

## Event Schema

Each reading produces a JSON event with the following structure:

```json
{
  "dma_id": "DMA-001",
  "dma_name": "Capitol Hill Zone",
  "connections": 2800,
  "pipe_km": 45.2,
  "latitude": 38.8899,
  "longitude": -76.9901,
  "zone_inlet_flow_mgd": 2.95,
  "zone_consumption_mgd": 2.58,
  "flow_balance_delta_mgd": 0.37,
  "nrw_percentage": 12.5,
  "inlet_pressure_psi": 72.3,
  "outlet_pressure_psi": 64.1,
  "min_night_flow_mgd": 0.08,
  "pump_efficiency_pct": 84.2,
  "storage_tank_level_ft": 28.5,
  "flow_velocity_fps": 4.2,
  "alert_flag": false,
  "alert_type": null,
  "timestamp": "2026-06-10T14:30:00Z"
}
```

### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `dma_id` | string | Unique DMA identifier |
| `dma_name` | string | Human-readable zone name |
| `connections` | int | Number of customer connections in the zone |
| `pipe_km` | float | Total pipe length in kilometers |
| `latitude` / `longitude` | float | DMA centroid coordinates |
| `zone_inlet_flow_mgd` | float | Water entering the zone (million gallons/day) |
| `zone_consumption_mgd` | float | Metered customer usage (MGD) |
| `flow_balance_delta_mgd` | float | Inlet minus consumption — the NRW indicator |
| `nrw_percentage` | float | (delta / inlet) × 100 |
| `inlet_pressure_psi` | float | Pressure at zone entry point |
| `outlet_pressure_psi` | float | Pressure at zone delivery points |
| `min_night_flow_mgd` | float | Minimum night flow baseline (most meaningful 2–4 AM) |
| `pump_efficiency_pct` | float | Pump health percentage |
| `storage_tank_level_ft` | float | Zone storage tank level in feet |
| `flow_velocity_fps` | float | Pipe flow velocity in feet per second |
| `alert_flag` | bool | Whether an anomaly is detected |
| `alert_type` | string/null | Type of anomaly if alert_flag is true |
| `timestamp` | string | ISO 8601 UTC timestamp |

---

## Anomaly Scenarios (~5% injection rate)

| Anomaly | What Happens | Real-World Cause |
|---------|-------------|------------------|
| `pipe_burst` | Sudden inlet pressure drop (−20 PSI), flow balance delta spikes (3×) | Main break, construction damage |
| `sustained_leak` | Gradually rising delta (1.5×), elevated MNF, NRW > 20% | Underground leak growing over time |
| `meter_fraud` | Delta spikes but pressure stays normal | Illegal bypass, tampered meter |
| `hydrant_theft` | Sudden 500–1500 GPM unaccounted spike | Unauthorized hydrant use (construction, pool filling) |
| `tank_overflow` | Tank level drops below 15 ft, pump efficiency drops | Control valve failure, pump malfunction |

---

## Time-of-Day Demand Simulation

The simulator applies realistic demand multipliers based on the current UTC hour:

| Period | Hours (UTC) | Multiplier | Description |
|--------|-------------|------------|-------------|
| Night | 0–5 | 0.3× | Minimal demand — MNF readings most meaningful |
| Morning Peak | 6–9 | 1.3× | Showers, dishwashers, morning routines |
| Midday | 10–16 | 1.0× | Baseline commercial/residential demand |
| Evening Peak | 17–20 | 1.2× | Cooking, laundry, irrigation |
| Declining | 21–23 | 0.6× | Demand tapering off |

---

## Complementing the Water Quality Stream

This simulator works alongside the [water-quality](../water-quality/) simulator:

| Aspect | Water Quality | Water Waste / NRW |
|--------|--------------|-------------------|
| Focus | Chemical & biological safety | Volume loss & infrastructure health |
| Sites | 18 sensor sites (plants, pumps, reservoirs) | 12 DMAs (pipe zones) |
| Key metrics | pH, turbidity, chlorine, DO | Flow balance, NRW%, pressure, MNF |
| Alerts | Contamination events | Leaks, bursts, theft |
| Interval | 10–20 seconds | 15–30 seconds |

Together they provide a complete picture of **water safety** (quality) and **water efficiency** (waste).

---

## KQL Resources

The `kql/` folder contains ready-to-use Kusto queries:

- `create_table.kql` — Table schema for KQL database
- `ingestion_mapping.kql` — JSON ingestion mapping
- `dashboard_queries.kql` — Dashboard visualization queries
- `alerts.kql` — Alert detection queries

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `EVENTHUB_WASTE_CONN_STR` | — | Event Hub connection string (required) |
| `EVENTHUB_WASTE_NAME` | `water-waste` | Event Hub name |

---

## License

MIT
