# Fabric Warm Path — Lakehouse Historical Analysis

## Overview

The **warm path** stores water quality data in a Fabric Lakehouse as Delta tables for long-term historical analysis, compliance reporting, and trend analysis. Data flows from Event Hub → Eventstream → Lakehouse (Delta). Unlike the hot path (sub-second, 90-day retention), the warm path optimizes for **deep analysis over months/years** of data.

---

## Architecture

```
Python Simulator → Event Hub (water-quality) → Eventstream → Lakehouse (Delta Tables)
                                                                        ↓
                                                              Spark Notebooks (Aggregation)
                                                                        ↓
                                                              Power BI (DirectLake)
```

---

## Hot Path vs. Warm Path Tradeoffs

| Aspect | Hot Path (Eventhouse) | Warm Path (Lakehouse) |
|--------|----------------------|----------------------|
| **Latency** | Sub-second to seconds | Minutes (micro-batch) |
| **Retention** | 90 days (configurable) | Unlimited (years) |
| **Query Engine** | KQL (optimized for time-series) | Spark SQL / T-SQL |
| **Cost** | Higher (streaming compute) | Lower (batch compute) |
| **Best For** | Live monitoring, alerts | Historical reporting, ML |
| **Schema** | Flat denormalized | Can be star-schema / partitioned |
| **Concurrency** | High (dashboard queries) | Moderate (notebook/report queries) |

**Use the hot path** when operators need to see data NOW and react in real-time.
**Use the warm path** when analysts need to answer questions about trends, compliance, and patterns over weeks/months.

---

## Step 1: Create the Lakehouse

1. In your workspace, click **+ New** → **Lakehouse**
2. Name it: `WaterQuality-Lakehouse`
3. This creates both the Lakehouse (Files + Tables) and a SQL analytics endpoint

---

## Step 2: Add Lakehouse Destination to Eventstream

You can reuse the same Eventstream from the hot path, or create a separate one.

### Option A: Add a second destination to existing Eventstream

1. Open `WaterQuality-Stream` (the Eventstream from hot path setup)
2. Click **+ Add destination**
3. Select **Lakehouse**
4. Configure:
   - Workspace: (your workspace)
   - Lakehouse: `WaterQuality-Lakehouse`
   - Delta table: `water_quality_readings_raw`
   - Input data format: JSON
   - **Column mapping:** Map all fields from the Event Hub payload
5. Click **Publish**

### Option B: Create a separate Eventstream (recommended for isolation)

1. Click **+ New** → **Eventstream**
2. Name it: `WaterQuality-Stream-Lakehouse`
3. Add Source: Azure Event Hubs → `water-quality` (use a different consumer group: `fabric-warm-path`)
4. Add Destination: Lakehouse (same config as above)
5. Click **Publish**

---

## Step 3: Configure Delta Table Partitioning

After the first events land, optimize the table layout:

1. Open a Fabric Notebook attached to the Lakehouse
2. Run the following PySpark to restructure with partitioning:

```python
from pyspark.sql import functions as F

# Read the raw ingested table
df = spark.read.format("delta").load("Tables/water_quality_readings_raw")

# Add partition columns
df_partitioned = df \
    .withColumn("reading_date", F.to_date(F.col("timestamp"))) \
    .withColumn("reading_hour", F.hour(F.col("timestamp")))

# Write as a partitioned Delta table
df_partitioned.write \
    .format("delta") \
    .mode("overwrite") \
    .partitionBy("reading_date", "site_id") \
    .option("overwriteSchema", "true") \
    .save("Tables/water_quality_readings")

# Optimize the table
spark.sql("OPTIMIZE water_quality_readings ZORDER BY (timestamp)")
```

> **Note:** After initial setup, the Eventstream writes directly to the partitioned table. The above is a one-time restructuring step.

---

## Step 4: Create Spark Notebooks for Historical Analysis

### Notebook 1: Daily Aggregations

Create a notebook named `WQ-Daily-Aggregations` and schedule it to run nightly:

```python
from pyspark.sql import functions as F
from datetime import date, timedelta

# Process yesterday's data
target_date = date.today() - timedelta(days=1)

df = spark.read.format("delta").table("water_quality_readings") \
    .filter(F.col("reading_date") == target_date)

# Daily aggregations per site
daily_agg = df.groupBy("site_id", "site_name", "site_type", "reading_date").agg(
    F.count("*").alias("reading_count"),
    F.round(F.avg("ph"), 2).alias("avg_ph"),
    F.round(F.min("ph"), 2).alias("min_ph"),
    F.round(F.max("ph"), 2).alias("max_ph"),
    F.round(F.avg("turbidity_ntu"), 3).alias("avg_turbidity_ntu"),
    F.round(F.max("turbidity_ntu"), 3).alias("max_turbidity_ntu"),
    F.round(F.avg("free_chlorine_ppm"), 2).alias("avg_free_chlorine_ppm"),
    F.round(F.min("free_chlorine_ppm"), 2).alias("min_free_chlorine_ppm"),
    F.round(F.avg("dissolved_oxygen_mg_l"), 2).alias("avg_dissolved_oxygen_mg_l"),
    F.round(F.avg("water_temperature_c"), 1).alias("avg_water_temperature_c"),
    F.round(F.avg("conductivity_us_cm"), 0).alias("avg_conductivity_us_cm"),
    F.round(F.avg("flow_rate_mgd"), 1).alias("avg_flow_rate_mgd"),
    F.sum(F.col("alert_flag").cast("int")).alias("total_alerts"),
    F.collect_set("alert_type").alias("alert_types_seen")
)

# Write to aggregation table (append mode — idempotent with merge preferred)
daily_agg.write \
    .format("delta") \
    .mode("append") \
    .saveAsTable("water_quality_daily_summary")
```

### Notebook 2: EPA Compliance Reporting

Create a notebook named `WQ-Compliance-Report`:

```python
from pyspark.sql import functions as F

# EPA Safe Drinking Water Act thresholds
EPA_LIMITS = {
    "ph_min": 6.5,
    "ph_max": 8.5,
    "turbidity_max": 1.0,          # General
    "turbidity_treatment_max": 0.3, # Treatment plants
    "chlorine_min": 0.2,
    "chlorine_max": 4.0,
    "dissolved_oxygen_min": 5.0,
}

# Read last 30 days
df = spark.read.format("delta").table("water_quality_readings") \
    .filter(F.col("reading_date") >= F.date_sub(F.current_date(), 30))

# Flag violations
compliance_df = df.withColumn("ph_violation",
    (F.col("ph") < EPA_LIMITS["ph_min"]) | (F.col("ph") > EPA_LIMITS["ph_max"])
).withColumn("turbidity_violation",
    F.col("turbidity_ntu") > EPA_LIMITS["turbidity_max"]
).withColumn("chlorine_violation",
    (F.col("free_chlorine_ppm") < EPA_LIMITS["chlorine_min"]) |
    (F.col("free_chlorine_ppm") > EPA_LIMITS["chlorine_max"])
).withColumn("do_violation",
    F.col("dissolved_oxygen_mg_l") < EPA_LIMITS["dissolved_oxygen_min"]
).withColumn("has_any_violation",
    F.col("ph_violation") | F.col("turbidity_violation") |
    F.col("chlorine_violation") | F.col("do_violation")
)

# Compliance summary per site
compliance_summary = compliance_df.groupBy("site_id", "site_name", "site_type").agg(
    F.count("*").alias("total_readings"),
    F.sum(F.col("has_any_violation").cast("int")).alias("violation_count"),
    F.sum(F.col("ph_violation").cast("int")).alias("ph_violations"),
    F.sum(F.col("turbidity_violation").cast("int")).alias("turbidity_violations"),
    F.sum(F.col("chlorine_violation").cast("int")).alias("chlorine_violations"),
    F.sum(F.col("do_violation").cast("int")).alias("do_violations"),
).withColumn("compliance_pct",
    F.round(100.0 * (1 - F.col("violation_count") / F.col("total_readings")), 2)
)

compliance_summary.write \
    .format("delta") \
    .mode("overwrite") \
    .saveAsTable("water_quality_compliance_30d")

# Display summary
compliance_summary.orderBy("compliance_pct").show()
```

### Notebook 3: Trend Analysis Across Sites

Create a notebook named `WQ-Trend-Analysis`:

```python
from pyspark.sql import functions as F
from pyspark.sql.window import Window

# Weekly rolling averages for trend detection
df = spark.read.format("delta").table("water_quality_daily_summary")

# 7-day rolling average per site
window_7d = Window.partitionBy("site_id").orderBy("reading_date").rowsBetween(-6, 0)

trends = df.withColumn("rolling_7d_ph", F.round(F.avg("avg_ph").over(window_7d), 2)) \
    .withColumn("rolling_7d_turbidity", F.round(F.avg("avg_turbidity_ntu").over(window_7d), 3)) \
    .withColumn("rolling_7d_chlorine", F.round(F.avg("avg_free_chlorine_ppm").over(window_7d), 2)) \
    .withColumn("rolling_7d_alerts", F.sum("total_alerts").over(window_7d))

# Detect degradation: 7-day average trending toward limits
degradation = trends.filter(
    (F.col("rolling_7d_ph") < 6.8) | (F.col("rolling_7d_ph") > 8.2) |
    (F.col("rolling_7d_turbidity") > 0.7) |
    (F.col("rolling_7d_chlorine") < 0.5)
).select(
    "site_id", "site_name", "reading_date",
    "rolling_7d_ph", "rolling_7d_turbidity", "rolling_7d_chlorine"
)

degradation.write \
    .format("delta") \
    .mode("overwrite") \
    .saveAsTable("water_quality_degradation_alerts")
```

---

## Step 5: Schedule Notebooks

1. Open each notebook in Fabric
2. Click **Schedule** (in the ribbon)
3. Configure:
   - `WQ-Daily-Aggregations`: Daily at 2:00 AM ET
   - `WQ-Compliance-Report`: Weekly on Monday at 6:00 AM ET
   - `WQ-Trend-Analysis`: Daily at 3:00 AM ET (after aggregations complete)

---

## Step 6: Verify Warm Path Data Flow

1. Check the Lakehouse Tables view — you should see:
   - `water_quality_readings_raw` (Eventstream target)
   - `water_quality_readings` (partitioned)
   - `water_quality_daily_summary` (after first notebook run)
   - `water_quality_compliance_30d` (after compliance notebook)
   - `water_quality_degradation_alerts` (after trend notebook)

2. Use the SQL analytics endpoint to query:
   ```sql
   SELECT COUNT(*) as total_records,
          MIN(timestamp) as earliest,
          MAX(timestamp) as latest,
          COUNT(DISTINCT site_id) as sites
   FROM water_quality_readings
   ```

---

## Step 7: Optimize for Performance

### Table Maintenance (weekly scheduled notebook)

```python
# Run OPTIMIZE to compact small files from streaming ingestion
spark.sql("OPTIMIZE water_quality_readings")
spark.sql("OPTIMIZE water_quality_daily_summary")

# VACUUM to remove old files (retain 7 days for time travel)
spark.sql("VACUUM water_quality_readings RETAIN 168 HOURS")
spark.sql("VACUUM water_quality_daily_summary RETAIN 168 HOURS")
```

### Lakehouse Best Practices

- **Partition pruning:** Queries filtering by `reading_date` and `site_id` will be fast due to partitioning
- **Z-ordering:** The `ZORDER BY (timestamp)` ensures time-range queries are efficient
- **Small file compaction:** Streaming ingestion creates many small files — schedule OPTIMIZE regularly
- **Statistics collection:** Delta automatically collects min/max stats for partition pruning

---

## Data Retention Strategy

| Table | Retention | Rationale |
|-------|-----------|-----------|
| `water_quality_readings` | 1 year (raw) | Full granularity for detailed investigation |
| `water_quality_daily_summary` | 5 years | Regulatory compliance requires multi-year records |
| `water_quality_compliance_30d` | Overwritten monthly | Always shows current 30-day window |
| `water_quality_degradation_alerts` | 2 years | Historical degradation patterns |

Implement retention via a scheduled notebook:

```python
from datetime import date, timedelta

# Delete raw readings older than 1 year
cutoff = date.today() - timedelta(days=365)
spark.sql(f"DELETE FROM water_quality_readings WHERE reading_date < '{cutoff}'")
spark.sql("VACUUM water_quality_readings RETAIN 168 HOURS")
```
