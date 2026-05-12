# PiAware Flight Tracker

Streams live ADS-B aircraft data from a local PiAware/dump1090 device to Azure Event Hub for ingestion into Microsoft Fabric Real-Time Intelligence.

## Prerequisites

- A PiAware or dump1090 receiver on your local network
- An Azure Event Hub (see [docs/setup-event-hub.md](../docs/setup-event-hub.md))

## Setup

```bash
cd flight-tracker
pip install -r requirements.txt
```

Add to your `.env` in the project root:

```
EVENTHUB_FLIGHT_CONN_STR=<your-connection-string>
EVENTHUB_FLIGHT_NAME=flight-tracker
```

## Run

```bash
# Default (localhost:8080, 5s interval)
python flight_tracker.py

# Custom host and polling interval
python flight_tracker.py --host 192.168.1.50 --port 8080 --interval 2
```

Press `Ctrl+C` to stop (graceful shutdown).

## Data Fields

| Field | Type | Description |
|-------|------|-------------|
| `hex` | string | ICAO 24-bit aircraft address |
| `flight` | string | Callsign / flight number |
| `lat` / `lon` | float | Position coordinates |
| `alt_baro` | int | Barometric altitude (ft) |
| `alt_geom` | int | Geometric altitude (ft) |
| `gs` | float | Ground speed (knots) |
| `track` | float | Heading (degrees) |
| `squawk` | string | Transponder code |
| `category` | string | Aircraft category |
| `rssi` | float | Signal strength (dBFS) |
| `timestamp` | string | UTC ISO 8601 |

## Architecture

```
PiAware (dump1090) → flight_tracker.py → Azure Event Hub → Fabric Eventstream
```
