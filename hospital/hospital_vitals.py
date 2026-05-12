# Hospital Patient Vitals Simulator
# Sends de-identified vital-sign readings to Azure Event Hub
# - Simulates realistic vitals for active patients
# - Patients are assigned a condition (stable / elevated / critical)
# - Condition can shift over time (improve or deteriorate)
# - Uses same PAT-XXXXX IDs as hospital_movement.py so data can be joined

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
EVENT_HUB_CONN_STR = os.getenv("EVENTHUB_VITALS_CONN_STR")
EVENT_HUB_NAME = os.getenv("EVENTHUB_VITALS_NAME", "hospital-vitals")

NUM_PATIENTS = 15
VITALS_INTERVAL = (8, 15)  # seconds between readings per patient

# ============================
# VITAL-SIGN PROFILES (realistic ranges)
# ============================
PROFILES = {
    "stable": {
        "heart_rate": (60, 100),
        "bp_systolic": (110, 130),
        "bp_diastolic": (70, 85),
        "temperature_f": (97.5, 99.0),
        "spo2": (95, 100),
        "respiratory_rate": (12, 20),
    },
    "elevated": {
        "heart_rate": (90, 120),
        "bp_systolic": (130, 160),
        "bp_diastolic": (85, 100),
        "temperature_f": (99.0, 101.5),
        "spo2": (90, 96),
        "respiratory_rate": (18, 26),
    },
    "critical": {
        "heart_rate": (110, 150),
        "bp_systolic": (80, 110),
        "bp_diastolic": (50, 70),
        "temperature_f": (101.0, 104.0),
        "spo2": (85, 93),
        "respiratory_rate": (24, 35),
    },
}

DIAGNOSIS_CODES = [
    "J18.9", "I21.9", "K35.80", "S72.001A", "N39.0",
    "J44.1", "I50.9", "E11.65", "K92.1", "G45.9",
    "J96.01", "A41.9",
]


# ============================
# PATIENT GENERATOR
# ============================
def create_patients(count):
    patients = []
    for i in range(count):
        condition = random.choices(
            ["stable", "elevated", "critical"],
            weights=[0.60, 0.30, 0.10],
        )[0]

        patients.append({
            "patient_id": f"PAT-{10001 + i}",
            "age": random.randint(18, 95),
            "gender": random.choice(["M", "F"]),
            "diagnosis_code": random.choice(DIAGNOSIS_CODES),
            "condition": condition,
            "baseline": PROFILES[condition],
        })
    return patients


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
# VITALS READING
# ============================
def read_vitals(patient):
    b = patient["baseline"]

    def jitter(low, high):
        val = random.uniform(low, high)
        val += random.gauss(0, (high - low) * 0.05)
        return round(val, 1)

    return {
        "patient_id": patient["patient_id"],
        "age": patient["age"],
        "gender": patient["gender"],
        "diagnosis_code": patient["diagnosis_code"],
        "condition": patient["condition"],
        "heart_rate": int(jitter(*b["heart_rate"])),
        "bp_systolic": int(jitter(*b["bp_systolic"])),
        "bp_diastolic": int(jitter(*b["bp_diastolic"])),
        "temperature_f": round(jitter(*b["temperature_f"]), 1),
        "spo2": min(100, int(jitter(*b["spo2"]))),
        "respiratory_rate": int(jitter(*b["respiratory_rate"])),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ============================
# PATIENT MONITOR THREAD
# ============================
def monitor_patient(patient):
    conditions = list(PROFILES.keys())

    while True:
        vitals = read_vitals(patient)
        send_event(vitals)
        print(
            f"[VITALS] {patient['patient_id']}  HR:{vitals['heart_rate']}  "
            f"BP:{vitals['bp_systolic']}/{vitals['bp_diastolic']}  "
            f"Temp:{vitals['temperature_f']}F  SpO2:{vitals['spo2']}%  "
            f"RR:{vitals['respiratory_rate']}  ({patient['condition']})"
        )

        # ~5 % chance condition shifts each cycle (biased toward improvement)
        if random.random() < 0.05:
            current_idx = conditions.index(patient["condition"])
            new_idx = max(0, min(2, current_idx + random.choice([-1, -1, 1])))
            if new_idx != current_idx:
                patient["condition"] = conditions[new_idx]
                patient["baseline"] = PROFILES[conditions[new_idx]]
                print(f"  >> {patient['patient_id']} condition changed to {patient['condition']}")

        time.sleep(random.uniform(*VITALS_INTERVAL))


# ============================
# START SIMULATION
# ============================
if __name__ == "__main__":
    patients = create_patients(NUM_PATIENTS)

    print("Hospital Vitals Simulator Starting...")
    print(f"Monitoring {NUM_PATIENTS} patients")
    print("=" * 55)

    threads = [
        threading.Thread(target=monitor_patient, args=(p,), daemon=True)
        for p in patients
    ]

    for t in threads:
        t.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nSimulation stopped.")
