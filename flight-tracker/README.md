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

### 1. SSH into Your PiAware Device

The flight tracker script runs **on the Raspberry Pi** itself (or on any machine that can reach the PiAware JSON feed). To deploy it to your Pi:

```bash
# SSH into the PiAware device (default user: pi)
ssh pi@<your-pi-ip>

# Create a working directory
mkdir -p ~/flight-tracker && cd ~/flight-tracker
```

### 2. Upload the Script and Dependencies

From your local machine, copy the files to the Pi using `scp`:

```bash
scp flight_tracker.py requirements.txt .env pi@<your-pi-ip>:~/flight-tracker/
```

> **Tip:** Make sure your `.env` file is populated with your Event Hub connection string before uploading.

### 3. Install Python Dependencies on the Pi

```bash
# Back on the Pi (via SSH)
cd ~/flight-tracker
pip install -r requirements.txt
```

If `pip` is not available, install it first:

```bash
sudo apt update && sudo apt install -y python3-pip
```

### 4. Configure Your `.env` File

Ensure your `.env` file contains:

```
EVENTHUB_FLIGHT_CONN_STR=<your-connection-string>
EVENTHUB_FLIGHT_NAME=flight-tracker
```

### 5. Verify PiAware Is Serving Data

Before running the tracker, confirm the local JSON feed is accessible:

```bash
curl http://localhost:8080/data/aircraft.json | head -c 200
```

You should see JSON with an `aircraft` array. If this doesn't work, check that dump1090 / PiAware is running (`sudo systemctl status piaware`).

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
