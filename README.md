# RTI Streaming Examples

Python simulators that stream real-time data to **Azure Event Hub** and **Azure IoT Hub** for ingestion into **Microsoft Fabric Real-Time Intelligence (RTI)**.

Use these apps to demo Fabric Eventstreams, KQL databases, real-time dashboards, and Data Agents — no real hardware or data sources required.

---

## Simulators

| Folder | Description | Target |
|--------|-------------|--------|
| [hospital/](hospital/) | Patient vitals + movement events for 15 simulated patients | Event Hub |
| [trains/](trains/) | NYC metro train telemetry (3 lines, GPS, speed, delays) | Event Hub or IoT Hub |
| [flight-tracker/](flight-tracker/) | Live ADS-B aircraft data from a PiAware receiver | Event Hub |

---

## Quick Start

### 1. Set Up Azure Resources

Follow the setup guides to create the necessary Azure resources:

- 📘 [**Set up Event Hubs**](docs/setup-event-hub.md) — Create an Event Hubs namespace, individual hubs, and SAS policies
- 📗 [**Set up IoT Hub**](docs/setup-iot-hub.md) — Create an IoT Hub and register devices (only needed for the IoT Hub train simulator)

### 2. Configure Environment

```bash
# Clone the repo
git clone https://github.com/nickTinMicrosoft/rti_streaming_examples.git
cd rti_streaming_examples

# Create your .env file from the template
cp .env.example .env

# Edit .env and paste in your connection strings
```

### 3. Run a Simulator

```bash
# Example: Hospital vitals
cd hospital
pip install -r requirements.txt
python hospital_vitals.py
```

Each simulator folder has its own `README.md` with full setup details.

---

## Architecture

```
┌───────────────────────┐     ┌──────────────────┐     ┌────────────────────┐
│  Python Simulators    │     │  Azure           │     │  Microsoft Fabric  │
│                       │     │                  │     │                    │
│  hospital_vitals.py  ─┼────▶│  Event Hub      ─┼────▶│  Eventstream       │
│  hospital_movement.py─┼────▶│                  │     │       │            │
│  trains_eventhub.py  ─┼────▶│                  │     │       ▼            │
│  flight_tracker.py   ─┼────▶│                  │     │  KQL Database      │
│                       │     │                  │     │       │            │
│  trains_iothub.py    ─┼────▶│  IoT Hub ────────┼────▶│       ▼            │
└───────────────────────┘     └──────────────────┘     │  Real-Time         │
                                                       │  Dashboard / Agent │
                                                       └────────────────────┘
```

---

## Environment Variables

All scripts load secrets from a `.env` file in the project root. See [`.env.example`](.env.example) for the full list.

| Variable | Used By | Required |
|----------|---------|----------|
| `EVENTHUB_VITALS_CONN_STR` | Hospital vitals | Yes (for hospital) |
| `EVENTHUB_MOVEMENT_CONN_STR` | Hospital movement | Yes (for hospital) |
| `EVENTHUB_TRAIN_CONN_STR` | Trains (Event Hub) | Yes (for EH trains) |
| `IOT_RED_LINE_CONN_STR` | Trains (IoT Hub) | Yes (for IoT trains) |
| `IOT_BLUE_LINE_CONN_STR` | Trains (IoT Hub) | Yes (for IoT trains) |
| `IOT_GREEN_LINE_CONN_STR` | Trains (IoT Hub) | Yes (for IoT trains) |
| `EVENTHUB_FLIGHT_CONN_STR` | Flight tracker | Yes (for flights) |

> ⚠️ **Never commit your `.env` file.** It is gitignored by default.

---

## Requirements

- Python 3.10+
- An Azure subscription
- A Microsoft Fabric workspace (for the Eventstream destination)

---

## License

MIT
