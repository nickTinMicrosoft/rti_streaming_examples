# Power BI Dashboard — Water Quality Monitoring

## Overview

This Power BI report connects to the Lakehouse warm path via **DirectLake** mode for near-real-time analytical reporting. It provides executive-level compliance visibility, site-level drill-through, and anomaly pattern analysis.

---

## Connection Setup: DirectLake Mode

DirectLake reads Delta tables directly without import or DirectQuery overhead — best of both worlds.

### Prerequisites
- Lakehouse `WaterQuality-Lakehouse` with populated tables
- At least the following tables available:
  - `water_quality_readings` (raw partitioned)
  - `water_quality_daily_summary` (aggregated)
  - `water_quality_compliance_30d` (compliance scores)

### Steps

1. Open **Power BI Desktop** or create a report in the Fabric portal
2. Click **Get Data** → **Microsoft Fabric** → **Lakehouse**
3. Select `WaterQuality-Lakehouse`
4. Choose tables:
   - `water_quality_daily_summary` (primary for trends)
   - `water_quality_compliance_30d` (for compliance cards)
   - `water_quality_readings` (for drill-through detail — use with caution on large volumes)
5. Connection mode will automatically be **DirectLake** when publishing to the same workspace

> **Tip:** For the raw readings table, consider creating a Lakehouse view filtered to the last 7 days to limit data volume in the report.

---

## Semantic Model (Dataset) Configuration

### Relationships

```
water_quality_daily_summary[site_id] → water_quality_compliance_30d[site_id]  (many-to-one)
```

### Calculated Columns

```dax
// In water_quality_daily_summary
Compliance Status = 
IF(
    RELATED(water_quality_compliance_30d[compliance_pct]) >= 99, "✅ Compliant",
    IF(RELATED(water_quality_compliance_30d[compliance_pct]) >= 95, "⚠️ Watch", "🔴 Non-Compliant")
)
```

---

## DAX Measures

### Core Measures

```dax
// Overall compliance percentage (weighted by readings)
Overall Compliance % = 
DIVIDE(
    SUMX(water_quality_compliance_30d, [total_readings] - [violation_count]),
    SUM(water_quality_compliance_30d[total_readings]),
    1
) * 100

// Sites currently in alert (from daily summary, today)
Sites In Alert = 
CALCULATE(
    DISTINCTCOUNT(water_quality_daily_summary[site_id]),
    water_quality_daily_summary[total_alerts] > 0,
    water_quality_daily_summary[reading_date] = TODAY()
)

// Total alerts in period
Total Alerts = SUM(water_quality_daily_summary[total_alerts])

// Average pH across all sites
Avg pH = AVERAGE(water_quality_daily_summary[avg_ph])

// Average Turbidity
Avg Turbidity = AVERAGE(water_quality_daily_summary[avg_turbidity_ntu])

// Average Chlorine
Avg Chlorine = AVERAGE(water_quality_daily_summary[avg_free_chlorine_ppm])

// Total readings processed
Total Readings = SUM(water_quality_daily_summary[reading_count])
```

### Time Intelligence Measures

```dax
// 30-day trend - alerts
Alerts 30d Trend = 
VAR Current30 = CALCULATE([Total Alerts], DATESINPERIOD(water_quality_daily_summary[reading_date], TODAY(), -30, DAY))
VAR Previous30 = CALCULATE([Total Alerts], DATESINPERIOD(water_quality_daily_summary[reading_date], TODAY()-30, -30, DAY))
RETURN DIVIDE(Current30 - Previous30, Previous30, 0) * 100

// Week-over-week compliance change
WoW Compliance Change = 
VAR ThisWeek = CALCULATE([Overall Compliance %], DATESINPERIOD(water_quality_daily_summary[reading_date], TODAY(), -7, DAY))
VAR LastWeek = CALCULATE([Overall Compliance %], DATESINPERIOD(water_quality_daily_summary[reading_date], TODAY()-7, -7, DAY))
RETURN ThisWeek - LastWeek

// Worst compliance site
Worst Site Compliance % = 
MINX(
    VALUES(water_quality_compliance_30d[site_name]),
    CALCULATE(AVERAGE(water_quality_compliance_30d[compliance_pct]))
)
```

### Conditional Formatting Measures

```dax
// pH status color
pH Status Color = 
SWITCH(TRUE(),
    [Avg pH] < 6.5 OR [Avg pH] > 8.5, "#FF0000",  // Red - violation
    [Avg pH] < 6.8 OR [Avg pH] > 8.2, "#FFA500",  // Orange - warning
    "#00AA00"                                        // Green - normal
)

// Turbidity status  
Turbidity Status = 
SWITCH(TRUE(),
    [Avg Turbidity] > 1.0, "🔴 Violation",
    [Avg Turbidity] > 0.7, "🟡 Elevated",
    "🟢 Normal"
)
```

---

## Page 1: Executive Summary

### Layout

| Section | Visual | Data |
|---------|--------|------|
| Top banner | KPI cards (row) | Overall Compliance %, Sites In Alert, Total Alerts (30d), Avg pH |
| Left | Donut chart | Compliance status distribution (Compliant / Watch / Non-Compliant) |
| Center | Line chart | 30-day trend — compliance % over time |
| Right | Bar chart (horizontal) | Sites ranked by alert count (worst first) |
| Bottom | Multi-row card | Per-site compliance scores with conditional coloring |

### KPI Card Configuration

1. **Overall Compliance %**
   - Value: `[Overall Compliance %]`
   - Target: 99.5%
   - Format: percentage, 1 decimal
   - Conditional: Red < 95%, Yellow 95-99%, Green ≥ 99%

2. **Sites In Alert**
   - Value: `[Sites In Alert]`
   - Format: integer
   - Conditional: Red > 3, Yellow 1-3, Green 0

3. **Total Alerts (30d)**
   - Value: `[Total Alerts]` filtered to last 30 days
   - Trend: `[Alerts 30d Trend]` as sparkline
   - Show: ↑/↓ indicator

4. **Average System pH**
   - Value: `[Avg pH]`
   - Reference band: 6.5–8.5 (green zone)

---

## Page 2: Site Detail (Drill-Through)

### Drill-Through Configuration

1. Create a drill-through page
2. Add drill-through field: `site_id` or `site_name`
3. Users right-click a site on Page 1 → Drill through to Page 2

### Layout

| Section | Visual | Data |
|---------|--------|------|
| Header | Card | Site name, site type, lat/long, compliance % |
| Top-left | Line chart | pH over time (daily avg, with EPA limits as reference lines) |
| Top-right | Line chart | Turbidity over time (daily avg, with EPA limit) |
| Mid-left | Line chart | Chlorine over time (min/avg/max bands) |
| Mid-right | Line chart | Dissolved oxygen over time |
| Bottom-left | Clustered bar | Alerts by type (stacked by alert_type) |
| Bottom-right | Table | Recent violations with details |

### Reference Lines (Critical!)

For each metric line chart, add constant lines:
- **pH:** Y = 6.5 (red, dashed, "EPA Min"), Y = 8.5 (red, dashed, "EPA Max")
- **Turbidity:** Y = 1.0 (red, dashed, "EPA Max"), Y = 0.3 (orange, dotted, "Treatment Target")
- **Chlorine:** Y = 0.2 (red, dashed, "EPA Min"), Y = 4.0 (red, dashed, "EPA Max")
- **DO:** Y = 5.0 (red, dashed, "EPA Min")

---

## Page 3: Anomaly Analysis

### Layout

| Section | Visual | Data |
|---------|--------|------|
| Top | Decomposition tree | Alert count → by site_type → by site → by alert_type |
| Mid-left | Heatmap (matrix) | Sites (rows) × Hours of day (columns), values = alert count |
| Mid-right | Scatter plot | Sites: X = total readings, Y = alert rate %, size = violation count |
| Bottom-left | Waterfall chart | Week-over-week change in alerts by site |
| Bottom-right | Table | Top 10 longest alert sequences (duration, site, type) |

### Suggested Analyses

1. **Root Cause Patterns:**
   - Which alert types are most common?
   - Do certain sites always have the same issue?
   - Are alerts correlated with time of day (operational cycles)?

2. **Time-to-Resolution:**
   ```dax
   Avg Alert Duration Hours = 
   // Requires alert start/end tracking in the data model
   // Approximate: gap between first alert and next non-alert reading
   AVERAGEX(
       FILTER(water_quality_daily_summary, [total_alerts] > 0),
       [total_alerts] / [reading_count] * 24
   )
   ```

3. **Seasonal Patterns:**
   - Compare summer vs winter alert rates
   - Temperature-correlated anomalies (dissolved oxygen drops in heat)

---

## Page 4 (Optional): Geographic View

- **Visual:** ArcGIS or Fabric Map visual
- **Data:** Site locations with compliance % as bubble size / color
- **Interaction:** Click a site → filter other visuals on the page
- **Layer:** Overlay utility service zones if available

---

## Report Settings

### Auto-Refresh
- Configure automatic page refresh: **30 minutes** (DirectLake supports this)
- For more frequent refresh, consider using the Real-Time Dashboard (hot path) instead

### Row-Level Security (Optional)
If different operators manage different zones:
```dax
// RLS role: Zone Manager
[site_type] = USERPRINCIPALNAME() // Map via a security table
```

### Mobile Layout
- Create a mobile-optimized view of Page 1 (Executive Summary)
- Include: Compliance %, Sites in Alert, 7-day trend sparkline

---

## Publishing

1. Save the report
2. **Publish** to the same Fabric workspace as the Lakehouse
3. DirectLake connection activates automatically
4. Pin key visuals to a shared **Power BI Dashboard** for quick glance
5. Set up **Data-driven subscriptions** for weekly compliance emails to stakeholders
