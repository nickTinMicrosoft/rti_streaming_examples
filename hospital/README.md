# Hospital Simulators

Streams simulated hospital patient data to Azure Event Hub for ingestion into Microsoft Fabric Real-Time Intelligence.

## Apps

| Script | Description |
|--------|-------------|
| `hospital_vitals.py` | Simulates vital-sign readings (heart rate, BP, SpO2, temperature, respiratory rate) for 15 patients with conditions that shift over time |
| `hospital_movement.py` | Simulates patient movement events — admissions, room transfers, X-Ray visits, and discharges |

Both simulators use the same `PAT-XXXXX` patient IDs so the data can be joined in Fabric.

## Setup

```bash
cd hospital
pip install -r requirements.txt
```

Add these to your `.env` file in the project root:

```
EVENTHUB_VITALS_CONN_STR=<your-connection-string>
EVENTHUB_VITALS_NAME=hospital-vitals
EVENTHUB_MOVEMENT_CONN_STR=<your-connection-string>
EVENTHUB_MOVEMENT_NAME=hospital-movement
```

## Run

```bash
python hospital_vitals.py
python hospital_movement.py
```

Press `Ctrl+C` to stop.

## Data Fields

### Vitals

| Field | Type | Description |
|-------|------|-------------|
| `patient_id` | string | De-identified ID (PAT-XXXXX) |
| `age` | int | Patient age |
| `gender` | string | M or F |
| `diagnosis_code` | string | ICD-10 code |
| `condition` | string | stable, elevated, or critical |
| `heart_rate` | int | Beats per minute |
| `bp_systolic` / `bp_diastolic` | int | Blood pressure (mmHg) |
| `temperature_f` | float | Body temperature (°F) |
| `spo2` | int | Oxygen saturation (%) |
| `respiratory_rate` | int | Breaths per minute |
| `timestamp` | string | UTC ISO 8601 |

### Movement

| Field | Type | Description |
|-------|------|-------------|
| `patient_id` | string | De-identified ID (PAT-XXXXX) |
| `event_type` | string | Admitted, Transferred, Sent to X-Ray, Returned from X-Ray, Discharged |
| `from_location` / `to_location` | string | Room or area name |
| `diagnosis_code` / `diagnosis_desc` | string | ICD-10 code and description |
| `floor` | string | Floor/unit identifier |
| `timestamp` | string | UTC ISO 8601 |
