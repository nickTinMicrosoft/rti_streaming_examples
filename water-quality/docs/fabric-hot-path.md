# Fabric Hot Path — Eventhouse Real-Time Monitoring

## Overview

The **hot path** delivers sub-second latency from sensor to dashboard. Water quality readings flow from the Python simulator → Azure Event Hub → Fabric Eventstream → Eventhouse (KQL Database) → Real-Time Dashboard.

This path is optimized for **live operational monitoring** — operators watch the dashboard for immediate alerts and compliance violations.

---

## Architecture

```
Python Simulator → Event Hub (water-quality) → Eventstream → Eventhouse (KQL DB)
                                                                        ↓
                                                              Real-Time Dashboard
```

---

## Step 1: Create Eventhouse & KQL Database

1. Navigate to your Fabric workspace
2. Click **+ New** → **Eventhouse**
3. Name it: `WaterQuality-Eventhouse`
4. A default KQL Database is created automatically — rename it to `WaterQualityDB`

---

## Step 2: Create the Ingestion Table

1. Open the KQL Database (`WaterQualityDB`)
2. Click **Explore your data** (opens KQL queryset)
3. Run the contents of [`../kql/create_table.kql`](../kql/create_table.kql):
   - Creates the `WaterQualityReadings` table with proper column types
   - Sets 90-day retention policy
   - Enables streaming ingestion

---

## Step 3: Apply Ingestion Mapping

1. In the same KQL queryset, run [`../kql/ingestion_mapping.kql`](../kql/ingestion_mapping.kql)
2. This creates the JSON mapping `WaterQualityReadings_JSON_Mapping` that maps Event Hub JSON fields to table columns

---

## Step 4: Create Eventstream

1. In your workspace, click **+ New** → **Eventstream**
2. Name it: `WaterQuality-Stream`
3. **Add Source:**
   - Source type: **Azure Event Hubs**
   - Connection: Create new or select existing connection to your Event Hub namespace
   - Event Hub: `water-quality`
   - Consumer group: `$Default` (or create a dedicated `fabric-hot-path` group)
   - Data format: **JSON**
4. **Add Destination:**
   - Destination type: **Eventhouse**
   - Workspace: (select your workspace)
   - Eventhouse: `WaterQuality-Eventhouse`
   - KQL Database: `WaterQualityDB`
   - Table: `WaterQualityReadings`
   - Input data format: JSON
   - Ingestion mapping: `WaterQualityReadings_JSON_Mapping`
5. Click **Publish**

---

## Step 5: Verify Data Flow

1. Start the Python simulator:
   ```bash
   cd C:\repos\rti_streaming_examples\water-quality
   python water_quality.py
   ```
2. Wait 10–15 seconds for the first batch to arrive
3. In the KQL Database, run:
   ```kql
   WaterQualityReadings
   | count
   ```
4. Verify row count is increasing
5. Run a quick sanity check:
   ```kql
   WaterQualityReadings
   | take 5
   ```

---

## Step 6: Create Real-Time Dashboard

1. In your workspace, click **+ New** → **Real-Time Dashboard**
2. Name it: `Water Quality — Live Operations`
3. Connect it to the `WaterQualityDB` KQL Database
4. Add the following tiles using queries from [`../kql/dashboard_queries.kql`](../kql/dashboard_queries.kql)

---

### Dashboard Panel Layout

#### Panel 1: Site Map (Top-Left, Large)
- **Query:** Query 1 — Latest Reading Per Site
- **Visual type:** Map
- **Configuration:**
  - Latitude: `latitude`
  - Longitude: `longitude`
  - Label: `site_name`
  - Color by: `alert_flag` (red = true, green = false)
  - Tooltip: pH, turbidity, chlorine, last timestamp
- **Auto-refresh:** 10 seconds

#### Panel 2: Time-Series Chart (Top-Right, Large)
- **Query:** Query 2 — pH, Turbidity, Chlorine over 30 min
- **Visual type:** Line chart (multi-series)
- **Configuration:**
  - X-axis: `timestamp`
  - Y-axis: `ph`, `turbidity_ntu`, `free_chlorine_ppm` (separate Y-axes)
  - Series: `site_name` (use parameter to filter)
  - Add reference lines for EPA limits (pH 6.5/8.5, turbidity 1.0)
- **Auto-refresh:** 15 seconds

#### Panel 3: Active Alerts Table (Middle, Full Width)
- **Query:** Query 3 — Active Alerts in Last Hour
- **Visual type:** Table
- **Configuration:**
  - Conditional formatting: color rows by `alert_type`
  - Sort by: `timestamp` descending
  - Show columns: timestamp, site_name, alert_type, pH, turbidity, chlorine
- **Auto-refresh:** 10 seconds

#### Panel 4: Site Health Summary (Bottom-Left)
- **Query:** Query 4 — Avg Metrics Per Site (Last 5 Min)
- **Visual type:** Multi-row card or Heatmap
- **Configuration:**
  - Group by: `site_name`
  - Values: avg_ph, avg_turbidity, avg_chlorine, status
  - Conditional formatting: highlight values outside normal ranges
- **Auto-refresh:** 30 seconds

#### Panel 5: Anomaly Trend (Bottom-Center)
- **Query:** Query 5 — Anomaly Count Per Hour, Rolling 24h
- **Visual type:** Column chart or Area chart
- **Configuration:**
  - X-axis: `timestamp` (hourly bins)
  - Y-axis: `anomaly_count`
  - Color: `distinct_sites_affected`
- **Auto-refresh:** 5 minutes

#### Panel 6: Compliance Violations (Bottom-Right)
- **Query:** Query 6 — EPA Limit Violations
- **Visual type:** Table with icons
- **Configuration:**
  - Key columns: site_name, violation_details, timestamp
  - Badge/icon for violation type
  - Link to drill-through for site detail
- **Auto-refresh:** 30 seconds

---

## Step 7: Configure Dashboard Parameters

Add a **site_id** parameter to enable drill-through:

1. Click **Parameters** → **+ Add**
2. Name: `selected_site`
3. Type: Query-based
4. Source query:
   ```kql
   WaterQualityReadings
   | distinct site_id, site_name
   | order by site_name asc
   ```
5. Apply to Query 2 as a filter:
   ```kql
   | where site_id == selected_site or isempty(selected_site)
   ```

---

## Step 8: Set Up Alerts (Data Activator / Reflex)

1. From the dashboard, select the Alerts table tile
2. Click **Set Alert** → creates a Reflex item
3. Configure trigger conditions:
   - **Condition:** `alert_count >= 3` within 10 minutes (sustained anomaly)
   - **Action:** Send Teams notification to the operations channel
4. Add a second alert for multi-site correlation:
   - **Condition:** `alerting_sites >= 3` within 5 minutes
   - **Action:** Send email to water quality manager + Teams notification

---

## Performance Notes

| Metric | Expected Value |
|--------|---------------|
| End-to-end latency | 2–5 seconds (Event Hub → Dashboard) |
| Ingestion throughput | Supports 1000s of events/sec |
| Query response time | < 1 second for dashboard queries |
| Dashboard refresh | Configurable 5–60 seconds per tile |
| Retention | 90 days (configurable) |

---

## Troubleshooting

| Issue | Resolution |
|-------|-----------|
| No data appearing | Check Eventstream is running (green status), verify Event Hub has incoming messages |
| Mapping errors | Ensure JSON field names match exactly (case-sensitive), check for null handling |
| High latency | Verify streaming ingestion is enabled, check Event Hub partition count |
| Dashboard not refreshing | Confirm auto-refresh is enabled, check KQL Database connection |
