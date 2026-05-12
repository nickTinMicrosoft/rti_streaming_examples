# PiAware Flight Tracker → Azure Event Hub
#
# Scrapes ADS-B aircraft data from a local PiAware/dump1090 feed
# and streams it to Azure Event Hub for ingestion into Microsoft Fabric.
#
# Usage:
#   python flight_tracker.py              # start with defaults
#   python flight_tracker.py --host 192.168.1.50 --interval 2
#
# Control:
#   Ctrl+C to gracefully stop the tracker

import os
import sys
import json
import time
import signal
import argparse
import logging
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv
from azure.eventhub import EventHubProducerClient, EventData

# ============================
# LOAD ENVIRONMENT
# ============================
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

EVENT_HUB_CONN_STR = os.getenv("EVENTHUB_FLIGHT_CONN_STR")
EVENT_HUB_NAME = os.getenv("EVENTHUB_FLIGHT_NAME", "flight-tracker")

# ============================
# LOGGING
# ============================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("flight-tracker")

# ============================
# PIAWARE DATA SOURCE
# ============================
PIAWARE_URL_TEMPLATE = "http://{host}:{port}/data/aircraft.json"


def fetch_aircraft(host: str, port: int) -> list[dict]:
    """Fetch current aircraft list from the PiAware/dump1090 JSON feed."""
    url = PIAWARE_URL_TEMPLATE.format(host=host, port=port)
    try:
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        return data.get("aircraft", [])
    except requests.RequestException as e:
        log.warning(f"Failed to reach PiAware at {url}: {e}")
        return []


def enrich_aircraft(aircraft: dict) -> dict:
    """Normalize and enrich a single aircraft record before sending."""
    return {
        "hex": aircraft.get("hex", ""),
        "flight": (aircraft.get("flight") or "").strip(),
        "alt_baro": aircraft.get("alt_baro"),
        "alt_geom": aircraft.get("alt_geom"),
        "gs": aircraft.get("gs"),              # ground speed (knots)
        "track": aircraft.get("track"),        # heading (degrees)
        "lat": aircraft.get("lat"),
        "lon": aircraft.get("lon"),
        "squawk": aircraft.get("squawk"),
        "category": aircraft.get("category"),
        "messages": aircraft.get("messages"),
        "rssi": aircraft.get("rssi"),          # signal strength
        "seen": aircraft.get("seen"),          # seconds since last message
        "seen_pos": aircraft.get("seen_pos"),  # seconds since last position
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ============================
# EVENT HUB SENDER
# ============================
class EventHubSender:
    def __init__(self):
        if not EVENT_HUB_CONN_STR:
            log.error("EVENTHUB_FLIGHT_CONN_STR is not set in .env")
            sys.exit(1)

        self.producer = EventHubProducerClient.from_connection_string(
            conn_str=EVENT_HUB_CONN_STR,
            eventhub_name=EVENT_HUB_NAME,
        )
        log.info(f"Connected to Event Hub: {EVENT_HUB_NAME}")

    def send_batch(self, aircraft_list: list[dict]):
        """Send a batch of aircraft records to Event Hub."""
        if not aircraft_list:
            return 0

        batch = self.producer.create_batch()
        count = 0

        for ac in aircraft_list:
            enriched = enrich_aircraft(ac)
            try:
                batch.add(EventData(json.dumps(enriched)))
                count += 1
            except ValueError:
                # Batch full — send what we have and start a new one
                self.producer.send_batch(batch)
                batch = self.producer.create_batch()
                batch.add(EventData(json.dumps(enriched)))
                count += 1

        if count > 0:
            self.producer.send_batch(batch)

        return count

    def close(self):
        self.producer.close()


# ============================
# TRACKER ENGINE
# ============================
class FlightTracker:
    def __init__(self, host: str, port: int, interval: int):
        self.host = host
        self.port = port
        self.interval = interval
        self.running = False
        self.sender = EventHubSender()
        self.total_sent = 0
        self.cycles = 0

    def start(self):
        """Start the tracking loop."""
        self.running = True
        log.info(f"Flight Tracker started — polling {self.host}:{self.port} every {self.interval}s")
        log.info("Press Ctrl+C to stop")
        print("=" * 55)

        while self.running:
            try:
                aircraft = fetch_aircraft(self.host, self.port)

                # Only send aircraft that have a position
                with_position = [ac for ac in aircraft if ac.get("lat") and ac.get("lon")]

                sent = self.sender.send_batch(with_position)
                self.total_sent += sent
                self.cycles += 1

                log.info(
                    f"Cycle {self.cycles}: {len(aircraft)} aircraft detected, "
                    f"{len(with_position)} with position, {sent} sent "
                    f"(total: {self.total_sent})"
                )

                time.sleep(self.interval)

            except Exception as e:
                log.error(f"Unexpected error: {e}")
                time.sleep(self.interval)

    def stop(self):
        """Gracefully stop the tracker."""
        self.running = False
        log.info("Stopping Flight Tracker...")
        self.sender.close()
        print("=" * 55)
        log.info(f"Session complete — {self.total_sent} records sent over {self.cycles} cycles")


# ============================
# MAIN
# ============================
def main():
    parser = argparse.ArgumentParser(
        description="PiAware Flight Tracker → Azure Event Hub"
    )
    parser.add_argument(
        "--host",
        default="localhost",
        help="PiAware/dump1090 host (default: localhost)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="PiAware/dump1090 HTTP port (default: 8080)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=5,
        help="Polling interval in seconds (default: 5)",
    )
    args = parser.parse_args()

    tracker = FlightTracker(args.host, args.port, args.interval)

    # Handle Ctrl+C for graceful shutdown
    def handle_signal(sig, frame):
        tracker.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    tracker.start()


if __name__ == "__main__":
    main()
