# Water Waste / Non-Revenue Water (NRW) Simulator
#
# Sends real-time water loss and flow balance readings to Azure Event Hub
# - Simulates 12 District Metered Areas (DMAs) across a water distribution network
# - Generates realistic NRW metrics including flow balance, pressure, and MNF
# - Injects anomalies (~5% chance) with alert labels
# - Uses threading (1 thread per DMA)

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
EVENT_HUB_CONN_STR = os.getenv("EVENTHUB_WASTE_CONN_STR")
EVENT_HUB_NAME = os.getenv("EVENTHUB_WASTE_NAME", "water-waste")

READING_INTERVAL = (15, 30)  # seconds between readings per DMA

# ============================
# DISTRICT METERED AREAS (DMAs)
# ============================
DMAS = [
    {"dma_id": "DMA-001", "dma_name": "Capitol Hill Zone", "connections": 2800, "pipe_km": 45.2, "latitude": 38.8899, "longitude": -76.9901},
    {"dma_id": "DMA-002", "dma_name": "Georgetown Zone", "connections": 1950, "pipe_km": 32.1, "latitude": 38.9065, "longitude": -77.0635},
    {"dma_id": "DMA-003", "dma_name": "Anacostia Zone", "connections": 3200, "pipe_km": 52.8, "latitude": 38.8620, "longitude": -76.9953},
    {"dma_id": "DMA-004", "dma_name": "Foggy Bottom Zone", "connections": 1500, "pipe_km": 24.3, "latitude": 38.8977, "longitude": -77.0503},
    {"dma_id": "DMA-005", "dma_name": "Adams Morgan Zone", "connections": 2100, "pipe_km": 35.6, "latitude": 38.9214, "longitude": -77.0424},
    {"dma_id": "DMA-006", "dma_name": "Tenleytown Zone", "connections": 1800, "pipe_km": 29.4, "latitude": 38.9488, "longitude": -77.0796},
    {"dma_id": "DMA-007", "dma_name": "Brookland Zone", "connections": 2400, "pipe_km": 41.0, "latitude": 38.9334, "longitude": -76.9937},
    {"dma_id": "DMA-008", "dma_name": "Navy Yard Zone", "connections": 1650, "pipe_km": 22.7, "latitude": 38.8752, "longitude": -77.0025},
    {"dma_id": "DMA-009", "dma_name": "Petworth Zone", "connections": 2600, "pipe_km": 43.5, "latitude": 38.9419, "longitude": -77.0241},
    {"dma_id": "DMA-010", "dma_name": "Dupont Circle Zone", "connections": 1400, "pipe_km": 19.8, "latitude": 38.9096, "longitude": -77.0434},
    {"dma_id": "DMA-011", "dma_name": "Brightwood Zone", "connections": 2900, "pipe_km": 48.1, "latitude": 38.9592, "longitude": -77.0275},
    {"dma_id": "DMA-012", "dma_name": "Southwest Zone", "connections": 1750, "pipe_km": 26.9, "latitude": 38.8684, "longitude": -77.0197},
]

# ============================
# TIME-OF-DAY DEMAND MULTIPLIERS
# ============================
DEMAND_MULTIPLIERS = {
    0: 0.3, 1: 0.3, 2: 0.3, 3: 0.3, 4: 0.3, 5: 0.3,
    6: 1.3, 7: 1.3, 8: 1.3, 9: 1.3,
    10: 1.0, 11: 1.0, 12: 1.0, 13: 1.0, 14: 1.0, 15: 1.0, 16: 1.0,
    17: 1.2, 18: 1.2, 19: 1.2, 20: 1.2,
    21: 0.6, 22: 0.6, 23: 0.6,
}

# ============================
# ANOMALY DEFINITIONS
# ============================
ANOMALY_TYPES = ["pipe_burst", "sustained_leak", "meter_fraud", "hydrant_theft", "tank_overflow"]
ANOMALY_CHANCE = 0.05  # ~5% chance per reading cycle


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
# READING GENERATION
# ============================
def get_demand_multiplier():
    """Get the demand multiplier based on current UTC hour."""
    current_hour = datetime.now(timezone.utc).hour
    return DEMAND_MULTIPLIERS.get(current_hour, 1.0)


def generate_reading(dma):
    """Generate a single water waste / NRW reading for a DMA."""

    def jitter(low, high):
        val = random.uniform(low, high)
        val += random.gauss(0, (high - low) * 0.05)
        return round(val, 4)

    current_hour = datetime.now(timezone.utc).hour
    demand_mult = get_demand_multiplier()

    # Base inlet flow based on connections
    base_inlet = dma["connections"] * 0.001
    zone_inlet_flow_mgd = round(base_inlet * demand_mult + random.gauss(0, base_inlet * 0.08), 4)
    zone_inlet_flow_mgd = max(zone_inlet_flow_mgd, 0.05)  # floor

    # Normal consumption is 80-95% of inlet flow
    consumption_pct = random.uniform(0.80, 0.95)
    zone_consumption_mgd = round(zone_inlet_flow_mgd * consumption_pct * demand_mult / max(demand_mult, 0.5), 4)
    zone_consumption_mgd = min(zone_consumption_mgd, zone_inlet_flow_mgd)  # can't consume more than inlet

    # Flow balance delta (the NRW indicator)
    flow_balance_delta_mgd = round(zone_inlet_flow_mgd - zone_consumption_mgd, 4)

    # NRW percentage
    nrw_percentage = round((flow_balance_delta_mgd / zone_inlet_flow_mgd) * 100, 2) if zone_inlet_flow_mgd > 0 else 0.0

    # Pressure readings
    inlet_pressure_psi = round(random.uniform(55.0, 85.0), 1)
    outlet_pressure_psi = round(random.uniform(45.0, min(75.0, inlet_pressure_psi - 3.0)), 1)

    # Min night flow — realistic only at 2-4 AM but always tracked
    base_mnf = (dma["connections"] / 3200) * 0.15  # scale by zone size
    if 2 <= current_hour <= 4:
        min_night_flow_mgd = round(random.uniform(base_mnf * 0.7, base_mnf * 1.3), 4)
    else:
        min_night_flow_mgd = round(random.uniform(base_mnf * 0.3, base_mnf * 0.8), 4)

    # Pump efficiency
    pump_efficiency_pct = round(random.uniform(72.0, 88.0), 1)

    # Storage tank level
    storage_tank_level_ft = round(random.uniform(18.0, 35.0), 1)

    # Flow velocity
    flow_velocity_fps = round(random.uniform(2.0, 8.0), 1)

    alert_flag = False
    alert_type = None

    # Anomaly injection (~5% chance)
    if random.random() < ANOMALY_CHANCE:
        anomaly = random.choice(ANOMALY_TYPES)
        alert_flag = True
        alert_type = anomaly

        if anomaly == "pipe_burst":
            # Sudden pressure drop, flow balance spikes
            inlet_pressure_psi = round(inlet_pressure_psi - random.uniform(15.0, 25.0), 1)
            inlet_pressure_psi = max(inlet_pressure_psi, 20.0)
            flow_balance_delta_mgd = round(flow_balance_delta_mgd * 3.0, 4)
            nrw_percentage = round((flow_balance_delta_mgd / zone_inlet_flow_mgd) * 100, 2) if zone_inlet_flow_mgd > 0 else 0.0

        elif anomaly == "sustained_leak":
            # Gradually increasing flow balance delta, elevated MNF
            flow_balance_delta_mgd = round(flow_balance_delta_mgd * 1.5, 4)
            nrw_percentage = round((flow_balance_delta_mgd / zone_inlet_flow_mgd) * 100, 2) if zone_inlet_flow_mgd > 0 else 0.0
            min_night_flow_mgd = round(min_night_flow_mgd * 2.0, 4)

        elif anomaly == "meter_fraud":
            # Flow balance spikes but pressure stays normal (apparent loss)
            flow_balance_delta_mgd = round(flow_balance_delta_mgd * 2.5, 4)
            nrw_percentage = round((flow_balance_delta_mgd / zone_inlet_flow_mgd) * 100, 2) if zone_inlet_flow_mgd > 0 else 0.0

        elif anomaly == "hydrant_theft":
            # Sudden unaccounted flow spike (500-1500 GPM converted to MGD)
            gpm_stolen = random.uniform(500, 1500)
            mgd_stolen = round(gpm_stolen * 0.00144, 4)
            flow_balance_delta_mgd = round(flow_balance_delta_mgd + mgd_stolen, 4)
            nrw_percentage = round((flow_balance_delta_mgd / zone_inlet_flow_mgd) * 100, 2) if zone_inlet_flow_mgd > 0 else 0.0

        elif anomaly == "tank_overflow":
            # Tank level drops, pump efficiency drops
            storage_tank_level_ft = round(random.uniform(8.0, 14.9), 1)
            pump_efficiency_pct = round(random.uniform(45.0, 65.0), 1)

    return {
        "dma_id": dma["dma_id"],
        "dma_name": dma["dma_name"],
        "connections": dma["connections"],
        "pipe_km": dma["pipe_km"],
        "latitude": dma["latitude"],
        "longitude": dma["longitude"],
        "zone_inlet_flow_mgd": round(zone_inlet_flow_mgd, 4),
        "zone_consumption_mgd": round(zone_consumption_mgd, 4),
        "flow_balance_delta_mgd": round(flow_balance_delta_mgd, 4),
        "nrw_percentage": round(nrw_percentage, 2),
        "inlet_pressure_psi": inlet_pressure_psi,
        "outlet_pressure_psi": outlet_pressure_psi,
        "min_night_flow_mgd": round(min_night_flow_mgd, 4),
        "pump_efficiency_pct": pump_efficiency_pct,
        "storage_tank_level_ft": storage_tank_level_ft,
        "flow_velocity_fps": flow_velocity_fps,
        "alert_flag": alert_flag,
        "alert_type": alert_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ============================
# DMA MONITOR THREAD
# ============================
def monitor_dma(dma):
    while True:
        reading = generate_reading(dma)
        send_event(reading)

        alert_str = f"  *** ALERT: {reading['alert_type']} ***" if reading["alert_flag"] else ""
        print(
            f"[NRW] {dma['dma_id']} {dma['dma_name']:<25}  "
            f"NRW:{reading['nrw_percentage']:5.1f}%  "
            f"Inlet:{reading['inlet_pressure_psi']:.0f}PSI  "
            f"Outlet:{reading['outlet_pressure_psi']:.0f}PSI  "
            f"Delta:{reading['flow_balance_delta_mgd']:.3f}MGD"
            f"{alert_str}"
        )

        time.sleep(random.uniform(*READING_INTERVAL))


# ============================
# START SIMULATION
# ============================
if __name__ == "__main__":
    print("Water Waste / Non-Revenue Water Simulator Starting...")
    print(f"Monitoring {len(DMAS)} District Metered Areas (DMAs)")
    print(f"Anomaly injection rate: {ANOMALY_CHANCE * 100:.0f}%")
    print(f"Reading interval: {READING_INTERVAL[0]}-{READING_INTERVAL[1]}s")
    print("=" * 80)

    threads = [
        threading.Thread(target=monitor_dma, args=(dma,), daemon=True)
        for dma in DMAS
    ]

    for t in threads:
        t.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nSimulation stopped.")
