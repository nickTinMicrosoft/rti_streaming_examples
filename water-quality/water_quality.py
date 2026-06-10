# Water Quality Monitoring Simulator
#
# Sends real-time water quality readings to Azure Event Hub
# - Simulates 18 sensor sites across example water utility infrastructure
# - Generates realistic water quality metrics per reading
# - Injects anomalies (~3-5% chance) with alert labels
# - Uses threading (1 thread per sensor site)

import os
import json
import random
import time
import threading
from datetime import datetime, timezone

from dotenv import load_dotenv
from azure.eventhub import EventHubProducerClient, EventData

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# ============================
# CONFIG
# ============================
EVENT_HUB_CONN_STR = os.getenv("EVENTHUB_WATER_CONN_STR")
EVENT_HUB_NAME = os.getenv("EVENTHUB_WATER_NAME", "water-quality")

READING_INTERVAL = (10, 20)  # seconds between readings per site

# ============================
# SENSOR SITES (example water utility infrastructure)
# ============================
SENSOR_SITES = [
    {"site_id": "WQ-001", "site_name": "Main Treatment Plant", "site_type": "treatment_plant", "latitude": 38.9072, "longitude": -77.0369},
    {"site_id": "WQ-002", "site_name": "North Pump Station", "site_type": "pump_station", "latitude": 38.9445, "longitude": -77.0280},
    {"site_id": "WQ-003", "site_name": "Central Reservoir", "site_type": "reservoir", "latitude": 38.9230, "longitude": -77.0430},
    {"site_id": "WQ-004", "site_name": "West Treatment Plant", "site_type": "treatment_plant", "latitude": 38.9320, "longitude": -77.0880},
    {"site_id": "WQ-005", "site_name": "South Treatment Plant", "site_type": "treatment_plant", "latitude": 38.8610, "longitude": -77.0200},
    {"site_id": "WQ-006", "site_name": "East Pump Station", "site_type": "pump_station", "latitude": 38.8975, "longitude": -76.9620},
    {"site_id": "WQ-007", "site_name": "River Intake Pump Station", "site_type": "pump_station", "latitude": 38.8760, "longitude": -77.0040},
    {"site_id": "WQ-008", "site_name": "West Reservoir", "site_type": "reservoir", "latitude": 38.9200, "longitude": -77.0950},
    {"site_id": "WQ-009", "site_name": "North Reservoir", "site_type": "reservoir", "latitude": 38.9580, "longitude": -77.0460},
    {"site_id": "WQ-010", "site_name": "Downtown Distribution Hub", "site_type": "distribution_point", "latitude": 38.9050, "longitude": -77.0170},
    {"site_id": "WQ-011", "site_name": "East Distribution Hub", "site_type": "distribution_point", "latitude": 38.8950, "longitude": -76.9750},
    {"site_id": "WQ-012", "site_name": "Uptown Distribution Hub", "site_type": "distribution_point", "latitude": 38.9470, "longitude": -77.0520},
    {"site_id": "WQ-013", "site_name": "South Distribution Hub", "site_type": "distribution_point", "latitude": 38.8480, "longitude": -76.9890},
    {"site_id": "WQ-014", "site_name": "Central Pump Station", "site_type": "pump_station", "latitude": 38.9160, "longitude": -77.0520},
    {"site_id": "WQ-015", "site_name": "Northwest Distribution Hub", "site_type": "distribution_point", "latitude": 38.9540, "longitude": -77.0740},
    {"site_id": "WQ-016", "site_name": "Southeast Distribution Hub", "site_type": "distribution_point", "latitude": 38.8420, "longitude": -76.9650},
    {"site_id": "WQ-017", "site_name": "Hilltop Reservoir", "site_type": "reservoir", "latitude": 38.9380, "longitude": -77.0080},
    {"site_id": "WQ-018", "site_name": "Main Street Pump Station", "site_type": "pump_station", "latitude": 38.9000, "longitude": -77.0000},
]

# ============================
# FLOW RATE RANGES BY SITE TYPE (million gallons/day)
# ============================
FLOW_RATE_RANGES = {
    "treatment_plant": (50.0, 370.0),
    "pump_station": (5.0, 50.0),
    "reservoir": (1.0, 10.0),
    "distribution_point": (0.5, 5.0),
}

# ============================
# NORMAL QUALITY METRIC RANGES
# ============================
NORMAL_RANGES = {
    "ph": (6.5, 8.5),
    "turbidity_ntu": (0.1, 4.0),
    "free_chlorine_ppm": (0.2, 4.0),
    "dissolved_oxygen_mg_l": (6.0, 14.0),
    "water_temperature_c": (5.0, 25.0),
    "conductivity_us_cm": (200.0, 800.0),
}

# ============================
# ANOMALY DEFINITIONS
# ============================
ANOMALIES = [
    {"type": "chemical_spill", "metric": "ph", "value_range": (3.5, 5.9)},
    {"type": "sediment_intrusion", "metric": "turbidity_ntu", "value_range": (10.0, 50.0)},
    {"type": "treatment_failure", "metric": "free_chlorine_ppm", "value_range": (0.0, 0.09)},
    {"type": "organic_contamination", "metric": "dissolved_oxygen_mg_l", "value_range": (1.0, 3.9)},
]

ANOMALY_CHANCE = 0.04  # ~4% chance per reading cycle


# ============================
# EVENT HUB
# ============================
producer = EventHubProducerClient.from_connection_string(
    conn_str=EVENT_HUB_CONN_STR,
    eventhub_name=EVENT_HUB_NAME,
)


def send_event(payload):
    batch = producer.create_batch()
    batch.add(EventData(json.dumps(payload)))
    producer.send_batch(batch)


# ============================
# WATER QUALITY READING
# ============================
def generate_reading(site):
    """Generate a single water quality reading for a sensor site."""

    def jitter(low, high):
        val = random.uniform(low, high)
        val += random.gauss(0, (high - low) * 0.05)
        return round(val, 2)

    # Generate normal readings
    ph = jitter(*NORMAL_RANGES["ph"])
    turbidity_ntu = jitter(*NORMAL_RANGES["turbidity_ntu"])
    free_chlorine_ppm = jitter(*NORMAL_RANGES["free_chlorine_ppm"])
    dissolved_oxygen_mg_l = jitter(*NORMAL_RANGES["dissolved_oxygen_mg_l"])
    water_temperature_c = jitter(*NORMAL_RANGES["water_temperature_c"])
    conductivity_us_cm = jitter(*NORMAL_RANGES["conductivity_us_cm"])
    flow_rate_mgd = jitter(*FLOW_RATE_RANGES[site["site_type"]])

    alert_flag = False
    alert_type = None

    # Anomaly injection (~3-5% chance)
    if random.random() < ANOMALY_CHANCE:
        anomaly = random.choice(ANOMALIES)
        alert_flag = True
        alert_type = anomaly["type"]
        anomaly_value = round(random.uniform(*anomaly["value_range"]), 2)

        # Override the affected metric
        if anomaly["metric"] == "ph":
            ph = anomaly_value
        elif anomaly["metric"] == "turbidity_ntu":
            turbidity_ntu = anomaly_value
        elif anomaly["metric"] == "free_chlorine_ppm":
            free_chlorine_ppm = anomaly_value
        elif anomaly["metric"] == "dissolved_oxygen_mg_l":
            dissolved_oxygen_mg_l = anomaly_value

    return {
        "site_id": site["site_id"],
        "site_name": site["site_name"],
        "site_type": site["site_type"],
        "latitude": site["latitude"],
        "longitude": site["longitude"],
        "ph": ph,
        "turbidity_ntu": turbidity_ntu,
        "free_chlorine_ppm": free_chlorine_ppm,
        "dissolved_oxygen_mg_l": dissolved_oxygen_mg_l,
        "water_temperature_c": water_temperature_c,
        "conductivity_us_cm": conductivity_us_cm,
        "flow_rate_mgd": flow_rate_mgd,
        "alert_flag": alert_flag,
        "alert_type": alert_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ============================
# SENSOR MONITOR THREAD
# ============================
def monitor_site(site):
    while True:
        reading = generate_reading(site)
        send_event(reading)

        alert_str = f"  *** ALERT: {reading['alert_type']} ***" if reading["alert_flag"] else ""
        print(
            f"[WATER] {site['site_id']} {site['site_name']:<35}  "
            f"pH:{reading['ph']:.1f}  Turb:{reading['turbidity_ntu']:.2f}NTU  "
            f"Cl:{reading['free_chlorine_ppm']:.2f}ppm  DO:{reading['dissolved_oxygen_mg_l']:.1f}mg/L  "
            f"Flow:{reading['flow_rate_mgd']:.1f}MGD"
            f"{alert_str}"
        )

        time.sleep(random.uniform(*READING_INTERVAL))


# ============================
# START SIMULATION
# ============================
if __name__ == "__main__":
    print("Water Quality Monitoring Simulator Starting...")
    print(f"Monitoring {len(SENSOR_SITES)} sensor sites")
    print(f"Anomaly injection rate: {ANOMALY_CHANCE * 100:.0f}%")
    print("=" * 70)

    threads = [
        threading.Thread(target=monitor_site, args=(site,), daemon=True)
        for site in SENSOR_SITES
    ]

    for t in threads:
        t.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nSimulation stopped.")
