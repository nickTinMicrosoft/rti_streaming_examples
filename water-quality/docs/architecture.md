# Water Quality Monitoring — Architecture Overview

## End-to-End Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           DATA SOURCES                                           │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│   │  WQ-001      │  │  WQ-002      │  │  WQ-003      │  │  WQ-0XX      │      │
│   │  Main Treat. │  │  North Pump  │  │  Central Res │  │  ...15-20    │      │
│   │  Plant       │  │  Station     │  │             │  │  sites       │      │
│   └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│          │                  │                  │                  │              │
│          └──────────────────┴──────────────────┴──────────────────┘              │
│                                      │                                           │
│                       Python Simulator (water_quality.py)                        │
│                          Sends JSON events every 10-20 seconds                   │
│                                      │                                           │
└──────────────────────────────────────┼───────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        AZURE EVENT HUB                                           │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│   Namespace: [your-namespace].servicebus.windows.net                            │
│   Event Hub: water-quality                                                      │
│   Partitions: 4 (keyed by site_id for ordering)                                 │
│   Retention: 24 hours                                                           │
│   Consumer Groups:                                                              │
│     - fabric-hot-path   → Eventhouse Eventstream                                │
│     - fabric-warm-path  → Lakehouse Eventstream                                 │
│                                                                                 │
└─────────────────────────┬───────────────────────────────┬───────────────────────┘
                          │                               │
              ┌───────────┘                               └───────────┐
              │                                                       │
              ▼                                                       ▼
┌─────────────────────────────────────┐   ┌─────────────────────────────────────┐
│        HOT PATH (Real-Time)         │   │       WARM PATH (Historical)        │
├─────────────────────────────────────┤   ├─────────────────────────────────────┤
│                                     │   │                                     │
│  ┌─────────────────────────────┐    │   │  ┌─────────────────────────────┐    │
│  │  Eventstream                │    │   │  │  Eventstream                │    │
│  │  WaterQuality-Stream      │    │   │  │  WaterQuality-Stream-Lakehouse │    │
│  └──────────────┬──────────────┘    │   │  └──────────────┬──────────────┘    │
│                 │                    │   │                 │                    │
│                 ▼                    │   │                 ▼                    │
│  ┌─────────────────────────────┐    │   │  ┌─────────────────────────────┐    │
│  │  Eventhouse                 │    │   │  │  Lakehouse                  │    │
│  │  KQL Database:              │    │   │  │  Delta Tables:              │    │
│  │    WaterQualityReadings     │    │   │  │    water_quality_readings   │    │
│  │  Retention: 90 days         │    │   │  │    (partitioned by date,    │    │
│  │  Streaming ingestion: ON    │    │   │  │     site_id)                │    │
│  └──────────────┬──────────────┘    │   │  └──────────────┬──────────────┘    │
│                 │                    │   │                 │                    │
│                 ▼                    │   │                 ▼                    │
│  ┌─────────────────────────────┐    │   │  ┌─────────────────────────────┐    │
│  │  Real-Time Dashboard        │    │   │  │  Spark Notebooks            │    │
│  │  - Site Map                 │    │   │  │  - Daily Aggregations       │    │
│  │  - Time-Series Charts       │    │   │  │  - Compliance Reports       │    │
│  │  - Alert Table              │    │   │  │  - Trend Analysis           │    │
│  │  - Compliance Violations    │    │   │  │                             │    │
│  │  Auto-refresh: 10-30 sec    │    │   │  │  Scheduled: nightly/weekly  │    │
│  └──────────────┬──────────────┘    │   │  └──────────────┬──────────────┘    │
│                 │                    │   │                 │                    │
│                 ▼                    │   │                 ▼                    │
│  ┌─────────────────────────────┐    │   │  ┌─────────────────────────────┐    │
│  │  Data Activator (Reflex)    │    │   │  │  Power BI (DirectLake)      │    │
│  │  - Sustained anomaly alert  │    │   │  │  - Executive Summary        │    │
│  │  - Multi-site correlation   │    │   │  │  - Site Drill-Through       │    │
│  │  - Teams / Email notify     │    │   │  │  - Anomaly Analysis         │    │
│  └─────────────────────────────┘    │   │  └─────────────────────────────┘    │
│                                     │   │                                     │
│  Latency: 2-5 seconds              │   │  Latency: 1-5 minutes               │
│  Retention: 90 days                 │   │  Retention: 1-5 years               │
│  Query: KQL (time-series optimized) │   │  Query: Spark SQL / T-SQL / DAX     │
│                                     │   │                                     │
└─────────────────────────────────────┘   └─────────────────────────────────────┘
```

---

## Hot Path — Sub-Second Live Monitoring

### Purpose
Operators need to see water quality readings **as they happen** to react immediately to anomalies, contamination events, or equipment failures.

### Characteristics
| Property | Value |
|----------|-------|
| End-to-end latency | 2–5 seconds |
| Query engine | KQL (Kusto) |
| Optimized for | Time-series, aggregations, pattern detection |
| Retention | 90 days |
| Dashboard refresh | 10–30 seconds |
| Alerting | Data Activator (Reflex) — Teams/Email in < 60 sec |
| Cost model | Always-on compute (Eventhouse capacity) |

### Key Capabilities
- **Live map** of all sensor sites with real-time status
- **Streaming time-series** charts updating every 10 seconds
- **Instant alert detection** via KQL anomaly queries
- **Cascading failure detection** — upstream → downstream propagation
- **EPA compliance checks** running continuously against incoming data

### When to Use Hot Path
- ✅ "Is anything wrong RIGHT NOW?"
- ✅ "Show me the last 30 minutes of pH at Main Treatment Plant"
- ✅ "Which sites are currently in violation?"
- ✅ "Alert me if 3+ sites go into alarm simultaneously"
- ❌ "What was our compliance rate last quarter?" (use warm path)
- ❌ "Show me year-over-year turbidity trends" (use warm path)

---

## Warm Path — Historical Analysis & Reporting

### Purpose
Analysts and regulators need to examine **trends, patterns, and compliance** over weeks, months, and years. This path prioritizes query flexibility and long-term storage over latency.

### Characteristics
| Property | Value |
|----------|-------|
| End-to-end latency | 1–5 minutes (micro-batch) |
| Query engine | Spark SQL, T-SQL (SQL endpoint), DAX (Power BI) |
| Optimized for | Complex joins, aggregations, ML, reporting |
| Retention | 1–5 years |
| Report refresh | 30 minutes (DirectLake) |
| Cost model | On-demand compute (Spark notebooks) + storage |

### Key Capabilities
- **Daily/weekly aggregations** for executive reporting
- **Compliance scoring** against EPA thresholds with full audit trail
- **Trend analysis** — rolling averages, seasonal patterns, degradation detection
- **Cross-site correlation** — compare sites over long periods
- **ML-ready data** — feature engineering for predictive maintenance

### When to Use Warm Path
- ✅ "What was our 30-day compliance percentage?"
- ✅ "Which sites have degrading water quality over the past month?"
- ✅ "Generate the quarterly EPA compliance report"
- ✅ "Compare summer vs winter dissolved oxygen levels"
- ✅ "Train an ML model to predict equipment failures"
- ❌ "What's the current pH at site WQ-003?" (use hot path)
- ❌ "Alert me when turbidity spikes" (use hot path)

---

## When to Use Which Path

```
                    ┌────────────────────────────────┐
                    │     What's the question?        │
                    └───────────────┬────────────────┘
                                    │
                    ┌───────────────┴────────────────┐
                    │  Is it about RIGHT NOW          │
                    │  or the LAST FEW HOURS?         │
                    └───────┬───────────────┬────────┘
                            │               │
                       YES  │               │  NO
                            │               │
                            ▼               ▼
                  ┌─────────────┐   ┌─────────────────┐
                  │  HOT PATH   │   │  Is it about     │
                  │  Eventhouse  │   │  trends over     │
                  │  + KQL       │   │  days/weeks/     │
                  │  + RT Dash   │   │  months?         │
                  └─────────────┘   └────┬────────┬───┘
                                         │        │
                                    YES  │        │  MAYBE BOTH
                                         │        │
                                         ▼        ▼
                               ┌──────────────┐ ┌──────────────┐
                               │  WARM PATH   │ │  Power BI +  │
                               │  Lakehouse   │ │  RT Dash     │
                               │  + Spark     │ │  (Hybrid)    │
                               │  + Power BI  │ │              │
                               └──────────────┘ └──────────────┘
```

---

## Data Retention Strategy

| Layer | Store | Retention | Purpose |
|-------|-------|-----------|---------|
| **Ingestion** | Event Hub | 24 hours | Buffer, replay capability |
| **Hot** | Eventhouse (KQL DB) | 90 days | Live monitoring, recent history |
| **Warm (raw)** | Lakehouse Delta | 1 year | Detailed investigation, audit |
| **Warm (aggregated)** | Lakehouse Delta | 5 years | Compliance reporting, trends |
| **Cold (archive)** | OneLake (Parquet/archive tier) | 7+ years | Regulatory archive |

### Retention Automation

```
Daily at 2 AM:
  1. Aggregate previous day → daily_summary table
  2. Run compliance checks → compliance table

Weekly on Sunday at 3 AM:
  1. OPTIMIZE all Delta tables (compact small files)
  2. VACUUM old file versions (7-day retention)

Monthly on 1st at 4 AM:
  1. Archive raw data older than 1 year → cold storage
  2. Delete archived data from warm Lakehouse
  3. Generate monthly compliance report
```

---

## Security & Access

| Role | Hot Path Access | Warm Path Access |
|------|----------------|-----------------|
| Operators (24/7) | Real-Time Dashboard (view) | — |
| Water Quality Engineers | RT Dashboard + KQL queries | Lakehouse notebooks (read/write) |
| Compliance Officers | — | Power BI reports (view) |
| Data Engineers | Full Eventhouse admin | Full Lakehouse admin |
| External Regulators | — | Exported PDF reports only |

---

## Monitoring the Monitoring System

### Health Checks
- **Eventstream lag:** Alert if > 30 seconds behind Event Hub
- **Missing data:** Alert if no readings from a site for > 5 minutes
- **Notebook failures:** Alert if scheduled notebook fails
- **Table growth:** Monitor Delta table file count (too many small files = need OPTIMIZE)

### Fabric Capacity Monitoring
- Track CU consumption across Eventhouse + Spark + Power BI
- Set capacity alerts at 80% utilization
- Consider autoscale or capacity pause during off-hours (if applicable)

---

## Future Enhancements

1. **ML Predictions:** Train anomaly detection model on historical data, deploy as real-time scoring in Eventstream (custom operator)
2. **Digital Twin:** Integrate with Azure Digital Twins for full distribution network modeling
3. **External Data Enrichment:** Weather data, water demand forecasts, maintenance schedules
4. **Citizen Portal:** Public-facing compliance dashboard (anonymized, delayed 1 hour)
5. **Mobile Alerts:** Push notifications to field technicians via Power Automate
