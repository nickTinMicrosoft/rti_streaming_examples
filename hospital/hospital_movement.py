# Hospital Patient Movement Simulator
# Sends de-identified patient movement events to Azure Event Hub
# - Patients move between ward rooms and X-Ray
# - Each patient visits X-Ray at most once
# - Patients can transfer rooms multiple times
# - Discharged patients are replaced by new admissions

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
EVENT_HUB_CONN_STR = os.getenv("EVENTHUB_MOVEMENT_CONN_STR")
EVENT_HUB_NAME = os.getenv("EVENTHUB_MOVEMENT_NAME", "hospital-movement")

MAX_ACTIVE_PATIENTS = 15
ADMIT_INTERVAL = (10, 20)       # seconds between new admissions
MOVEMENT_INTERVAL = (5, 12)     # seconds between movements
DISCHARGE_CHANCE = 0.10         # probability a move becomes a discharge
XRAY_CHANCE = 0.25              # probability a move sends patient to X-Ray

# ============================
# HOSPITAL LAYOUT
# ============================
GENERAL_ROOMS = [f"Room {i}" for i in range(101, 116)]
ICU_ROOMS = [f"ICU-{i}" for i in range(1, 6)]
XRAY_SUITES = ["X-Ray Suite A", "X-Ray Suite B"]
ALL_WARD_ROOMS = GENERAL_ROOMS + ICU_ROOMS

# ============================
# DIAGNOSIS CODES (ICD-10 style)
# ============================
DIAGNOSIS_CODES = [
    {"code": "J18.9",    "desc": "Pneumonia"},
    {"code": "I21.9",    "desc": "Acute MI"},
    {"code": "K35.80",   "desc": "Appendicitis"},
    {"code": "S72.001A", "desc": "Hip Fracture"},
    {"code": "N39.0",    "desc": "UTI"},
    {"code": "J44.1",    "desc": "COPD Exacerbation"},
    {"code": "I50.9",    "desc": "Heart Failure"},
    {"code": "E11.65",   "desc": "Diabetes Type 2"},
    {"code": "K92.1",    "desc": "GI Bleed"},
    {"code": "G45.9",    "desc": "TIA"},
    {"code": "J96.01",   "desc": "Respiratory Failure"},
    {"code": "A41.9",    "desc": "Sepsis"},
]

# ============================
# PATIENT GENERATOR
# ============================
_next_patient_id = 10001
_id_lock = threading.Lock()


def generate_patient():
    global _next_patient_id
    with _id_lock:
        pid = f"PAT-{_next_patient_id}"
        _next_patient_id += 1

    diagnosis = random.choice(DIAGNOSIS_CODES)
    room = random.choice(ALL_WARD_ROOMS)

    return {
        "patient_id": pid,
        "age": random.randint(18, 95),
        "gender": random.choice(["M", "F"]),
        "diagnosis_code": diagnosis["code"],
        "diagnosis_desc": diagnosis["desc"],
        "current_location": room,
        "admitted_at": datetime.now(timezone.utc).isoformat(),
        "has_visited_xray": False,
        "move_count": 0,
    }


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
# SIMULATION STATE
# ============================
active_patients = []
patients_lock = threading.Lock()


def build_event(patient, event_type, from_loc, to_loc):
    return {
        "patient_id": patient["patient_id"],
        "age": patient["age"],
        "gender": patient["gender"],
        "diagnosis_code": patient["diagnosis_code"],
        "diagnosis_desc": patient["diagnosis_desc"],
        "event_type": event_type,
        "from_location": from_loc,
        "to_location": to_loc,
        "floor": to_loc.split("-")[0] if "-" in to_loc else to_loc[:3],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ============================
# ADMISSION LOOP
# ============================
def admission_loop():
    while True:
        time.sleep(random.uniform(*ADMIT_INTERVAL))
        with patients_lock:
            if len(active_patients) < MAX_ACTIVE_PATIENTS:
                patient = generate_patient()
                active_patients.append(patient)

                event = build_event(patient, "Admitted", "Entrance", patient["current_location"])
                send_event(event)
                print(f"[ADMIT]      {patient['patient_id']} -> {patient['current_location']}  "
                      f"({patient['diagnosis_desc']}, age {patient['age']}, {patient['gender']})")


# ============================
# MOVEMENT LOOP
# ============================
def movement_loop():
    while True:
        time.sleep(random.uniform(*MOVEMENT_INTERVAL))
        with patients_lock:
            if not active_patients:
                continue

            patient = random.choice(active_patients)
            old_location = patient["current_location"]

            # --- Patient is currently in X-Ray → return to a ward room ---
            if old_location in XRAY_SUITES:
                new_room = random.choice(ALL_WARD_ROOMS)
                patient["current_location"] = new_room
                patient["move_count"] += 1

                event = build_event(patient, "Returned from X-Ray", old_location, new_room)
                send_event(event)
                print(f"[XRAY-RTN]   {patient['patient_id']}  {old_location} -> {new_room}")

            # --- Discharge (only after ≥2 moves so the patient has some history) ---
            elif patient["move_count"] >= 2 and random.random() < DISCHARGE_CHANCE:
                active_patients.remove(patient)

                event = build_event(patient, "Discharged", old_location, "Discharge")
                send_event(event)
                print(f"[DISCHARGE]  {patient['patient_id']}  from {old_location}")

            # --- Send to X-Ray (once per patient) ---
            elif not patient["has_visited_xray"] and random.random() < XRAY_CHANCE:
                xray = random.choice(XRAY_SUITES)
                patient["current_location"] = xray
                patient["has_visited_xray"] = True
                patient["move_count"] += 1

                event = build_event(patient, "Sent to X-Ray", old_location, xray)
                send_event(event)
                print(f"[XRAY]       {patient['patient_id']}  {old_location} -> {xray}")

            # --- Transfer to a different ward room ---
            else:
                available = [r for r in ALL_WARD_ROOMS if r != old_location]
                new_room = random.choice(available)
                patient["current_location"] = new_room
                patient["move_count"] += 1

                event = build_event(patient, "Transferred", old_location, new_room)
                send_event(event)
                print(f"[TRANSFER]   {patient['patient_id']}  {old_location} -> {new_room}")


# ============================
# START SIMULATION
# ============================
if __name__ == "__main__":
    print("Hospital Movement Simulator Starting...")
    print(f"Max active patients: {MAX_ACTIVE_PATIENTS}")
    print("=" * 55)

    # Seed with an initial batch of admitted patients
    for _ in range(5):
        patient = generate_patient()
        active_patients.append(patient)
        event = build_event(patient, "Admitted", "Entrance", patient["current_location"])
        send_event(event)
        print(f"[ADMIT]      {patient['patient_id']} -> {patient['current_location']}  "
              f"({patient['diagnosis_desc']}, age {patient['age']}, {patient['gender']})")

    threads = [
        threading.Thread(target=admission_loop, daemon=True),
        threading.Thread(target=movement_loop, daemon=True),
    ]

    for t in threads:
        t.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nSimulation stopped.")
