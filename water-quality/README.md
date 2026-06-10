# Water Quality Monitoring Simulator

A real-time water quality monitoring simulator for a generic water utility. Streams synthetic sensor readings to Azure Event Hub for use with Microsoft Fabric Real-Time Intelligence (RTI) demos.

## Overview

This simulator models 18 sensor sites across a water utility network — including treatment plants, pump stations, reservoirs, and distribution points. Each site generates water quality metrics at 10–20 second intervals with realistic values and occasional anomaly injection (~4% chance per reading).

## Sensor Sites

| Site ID | Name | Type |
|---------|------|------|
| WQ-001 | Main Treatment Plant | treatment_plant |
| WQ-002 | North Pump Station | pump_station |
| WQ-003 | Central Reservoir | reservoir |
| WQ-004 | West Treatment Plant | treatment_plant |
| WQ-005 | South Treatment Plant | treatment_plant |
| WQ-006 | East Pump Station | pump_station |
| WQ-007 | River Intake Pump Station | pump_station |
| WQ-008 | West Reservoir | reservoir |
| WQ-009 | North Reservoir | reservoir |
| WQ-010 | Downtown Distribution Hub | distribution_point |
| WQ-011 | East Distribution Hub | distribution_point |
| WQ-012 | Uptown Distribution Hub | distribution_point |
| WQ-013 | South Distribution Hub | distribution_point |
| WQ-014 | Central Pump Station | pump_station |
| WQ-015 | Northwest Distribution Hub | distribution_point |
| WQ-016 | Southeast Distribution Hub | distribution_point |
| WQ-017 | Hilltop Reservoir | reservoir |
| WQ-018 | Main Street Pump Station | pump_station |

## Setup

### 1. Create Azure Event Hub

1. Create an Event Hub namespace in Azure (Standard tier recommended)
2. Create an Event Hub named `water-quality` (or your preferred name)
3. Create a Shared Access Policy with **Send** permission
4. Copy the connection string

### 2. Configure Environment Variables

Add the following to `../.env` (in the repo root):

```env
# ----- Water Quality Monitoring Simulator -----
EVENTHUB_WATER_CONN_STR=<your-event-hub-connection-string>
EVENTHUB_WATER_NAME=water-quality
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

## Running the Simulator

```bash
python water_quality.py
```

The simulator will start 18 threads (one per sensor site) and continuously stream water quality readings to your Event Hub.

Press `Ctrl+C` to stop.

## Event Schema

Each event is a JSON object with the following fields:

```json
{
  "site_id": "WQ-001",
  "site_name": "Main Treatment Plant",
  "site_type": "treatment_plant",
  "latitude": 38.9072,
  "longitude": -77.0369,
  "ph": 7.2,
  "turbidity_ntu": 0.8,
  "free_chlorine_ppm": 2.1,
  "dissolved_oxygen_mg_l": 9.4,
  "water_temperature_c": 18.3,
  "conductivity_us_cm": 450,
  "flow_rate_mgd": 300.5,
  "alert_flag": false,
  "alert_type": null,
  "timestamp": "2026-06-10T14:30:00Z"
}
```

### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `site_id` | string | Unique sensor site identifier (WQ-001 to WQ-018) |
| `site_name` | string | Human-readable site name |
| `site_type` | string | One of: treatment_plant, pump_station, reservoir, distribution_point |
| `latitude` | float | Site latitude (example utility coordinates) |
| `longitude` | float | Site longitude (example utility coordinates) |
| `ph` | float | pH level (normal: 6.5–8.5) |
| `turbidity_ntu` | float | Turbidity in NTU (normal: 0.1–4.0) |
| `free_chlorine_ppm` | float | Free chlorine in ppm (normal: 0.2–4.0) |
| `dissolved_oxygen_mg_l` | float | Dissolved oxygen in mg/L (normal: 6.0–14.0) |
| `water_temperature_c` | float | Water temperature in Celsius (normal: 5.0–25.0) |
| `conductivity_us_cm` | float | Conductivity in μS/cm (normal: 200–800) |
| `flow_rate_mgd` | float | Flow rate in million gallons/day (varies by site type) |
| `alert_flag` | boolean | Whether an anomaly was detected |
| `alert_type` | string/null | Type of anomaly if alert_flag is true |
| `timestamp` | string | ISO 8601 UTC timestamp |

### Flow Rate Ranges by Site Type

| Site Type | Flow Rate (MGD) |
|-----------|----------------|
| treatment_plant | 50–370 |
| pump_station | 5–50 |
| reservoir | 1–10 |
| distribution_point | 0.5–5 |

## Anomaly Scenarios

The simulator injects anomalies with ~4% probability per reading cycle. When an anomaly fires, `alert_flag` is set to `true` and `alert_type` identifies the scenario:

| Alert Type | Affected Metric | Anomaly Value | Real-World Cause |
|------------|----------------|---------------|------------------|
| `chemical_spill` | pH | < 6.0 (range: 3.5–5.9) | Chemical contamination causing pH crash |
| `sediment_intrusion` | turbidity_ntu | > 10 NTU (range: 10–50) | Sediment or particulate matter entering supply |
| `treatment_failure` | free_chlorine_ppm | < 0.1 ppm (range: 0–0.09) | Chlorination system malfunction |
| `organic_contamination` | dissolved_oxygen_mg_l | < 4.0 mg/L (range: 1.0–3.9) | Organic matter consuming dissolved oxygen |

## Integration with Microsoft Fabric RTI

1. Create an **Eventstream** in Fabric connected to your Event Hub
2. Route data to a **KQL Database** (Eventhouse)
3. Build **Real-Time Dashboards** to visualize water quality across sites
4. Set up **Data Activator** alerts for anomaly conditions
