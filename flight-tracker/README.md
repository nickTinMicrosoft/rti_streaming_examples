# PiAware Flight Tracker

Streams live ADS-B aircraft data from a local PiAware/dump1090 device to Azure Event Hub for ingestion into Microsoft Fabric Real-Time Intelligence.

## Prerequisites

### PiAware ADS-B Receiver (required hardware)

This simulator reads live aircraft data from a **PiAware / dump1090** receiver on your local network. You'll need to purchase and assemble one before using this app.

| Resource | Link |
|----------|------|
| **Build guide & parts list** | [flightaware.com/adsb/piaware/build](https://flightaware.com/adsb/piaware/build) |
| **Buy hardware (SDR, antenna, kits)** | [FlightAware ADS-B Store](https://flightaware.store/) |
| **PiAware software install** | [flightaware.com/adsb/piaware/install](https://flightaware.com/adsb/piaware/install) |

**What you need:**
- Raspberry Pi (3B+ or newer recommended)
- FlightAware Pro Stick Plus (USB SDR receiver, 1090 MHz)
- 1090 MHz ADS-B antenna
- MicroSD card (16 GB+) flashed with PiAware OS
- Power supply and case

Follow the [official build guide](https://flightaware.com/adsb/piaware/build) to assemble and register your device. Once running, your PiAware serves a local JSON feed at `http://<pi-ip>:8080/data/aircraft.json` — that's what this script reads from.

> **Bonus:** Feeding data to FlightAware gives you a free [FlightAware Enterprise account](https://flightaware.com/commercial/premium/).

### Azure Event Hub

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
