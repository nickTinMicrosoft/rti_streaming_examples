# Setting Up Azure Event Hubs

This guide walks you through creating an **Event Hubs Namespace**, individual **Event Hubs**, and the **connection strings** needed by the streaming simulators.

---

## Step 1 — Create an Event Hubs Namespace

The namespace is the container for all your Event Hubs. Think of it like a server that hosts multiple queues.

1. Go to the [Azure Portal](https://portal.azure.com).
2. Click **+ Create a resource** → search for **Event Hubs** → click **Create**.
3. Fill in the basics:

   | Field | Value |
   |-------|-------|
   | **Subscription** | Your Azure subscription |
   | **Resource Group** | Create new or use existing (e.g., `rg-fabric-rti-demo`) |
   | **Namespace Name** | Something unique (e.g., `ehns-rti-demo-<yourname>`) |
   | **Location** | Choose a region close to your Fabric workspace |
   | **Pricing Tier** | **Standard** (required for consumer groups and capture) |

4. Click **Review + Create** → **Create**.
5. Wait for deployment to complete, then click **Go to resource**.

---

## Step 2 — Create Event Hubs

You need one Event Hub per data stream. Create the following:

| Event Hub Name | Used By |
|---------------|---------|
| `hospital-vitals` | `hospital/hospital_vitals.py` |
| `hospital-movement` | `hospital/hospital_movement.py` |
| `metrotrain` | `trains/trains_eventhub.py` |
| `flight-tracker` | `flight-tracker/flight_tracker.py` |
| `water-quality` | `water-quality/water_quality.py` |
| `water-waste` | `water-waste/water_waste.py` |

For each one:

1. In your Event Hubs Namespace, click **+ Event Hub** in the left menu.
2. Enter the **Name** from the table above.
3. Set **Partition Count** to `2` (fine for demos; use `4` for `water-quality` and `water-waste`).
4. Set **Message Retention** to `1` day.
5. Click **Create**.

Repeat for all six Event Hubs.

---

## Step 3 — Create Shared Access Policies (Keys)

Each Event Hub needs a **Shared Access Policy** (SAS policy) that grants send permissions to the simulator apps.

### Option A: Namespace-Level Policy (simpler — one key for all hubs)

1. In your **Event Hubs Namespace**, click **Shared access policies** in the left menu.
2. Click **+ Add**.
3. Name: `SendPolicy`
4. Check **Send** (you can also check **Listen** if you want Fabric to use the same key).
5. Click **Create**.
6. Click on the new policy → copy the **Connection string – primary key**.

This connection string works for all Event Hubs in the namespace. Use it in your `.env` file for all `*_CONN_STR` variables.

### Option B: Hub-Level Policies (more secure — one key per hub)

1. Navigate to a specific Event Hub (e.g., `hospital-vitals`).
2. Click **Shared access policies** → **+ Add**.
3. Name: `SendPolicy`
4. Check **Send**.
5. Click **Create**.
6. Copy the **Connection string – primary key**.

Repeat for each Event Hub. Each connection string is scoped to that specific hub.

> **💡 Recommendation for demos**: Use Option A (namespace-level) for simplicity. For production, use Option B.

### Water Quality — Hub-Level Policy (recommended)

The water quality simulator uses a dedicated SAS policy with both **Send** and **Listen** claims so Fabric Eventstream can consume directly from the same policy.

1. Navigate to the `water-quality` Event Hub.
2. Click **Shared access policies** → **+ Add**.
3. Name: `water-quality-send-listen`
4. Check **Send** and **Listen**.
5. Click **Create**.
6. Copy the **Connection string – primary key** — use this as `EVENTHUB_WATER_CONN_STR` in your `.env`.

#### Consumer Groups

The `water-quality` hub uses two consumer groups:

1. `$Default` — used by the simulator for verification reads.
2. `fabric-eventstream` — used by Fabric Eventstream to consume events independently.

To create the `fabric-eventstream` consumer group:

1. In the `water-quality` Event Hub, click **Consumer groups** in the left menu.
2. Click **+ Consumer group**.
3. Name: `fabric-eventstream`
4. Click **Create**.

### Water Waste — Hub-Level Policy (recommended)

The water waste / NRW simulator uses a dedicated SAS policy with both **Send** and **Listen** claims so Fabric Eventstream can consume directly from the same policy.

1. Navigate to the `water-waste` Event Hub.
2. Click **Shared access policies** → **+ Add**.
3. Name: `wasteSendListen`
4. Check **Send** and **Listen**.
5. Click **Create**.
6. Copy the **Connection string – primary key** — use this as `EVENTHUB_WASTE_CONN_STR` in your `.env`.

#### Consumer Groups

The `water-waste` hub uses two consumer groups:

1. `$Default` — used by the simulator for verification reads.
2. `fabric-eventstream` — used by Fabric Eventstream to consume events independently.

To create the `fabric-eventstream` consumer group:

1. In the `water-waste` Event Hub, click **Consumer groups** in the left menu.
2. Click **+ Consumer group**.
3. Name: `fabric-eventstream`
4. Click **Create**.

---

## Step 4 — Create a Listen Policy for Fabric Eventstream

Fabric Eventstream needs a **Listen** policy to consume events.

1. In your **Event Hubs Namespace**, click **Shared access policies**.
2. Click **+ Add**.
3. Name: `ListenPolicy`
4. Check **Listen**.
5. Click **Create**.
6. Copy the **Connection string – primary key** — you'll use this when configuring Fabric Eventstream.

> You can also create a single policy with both **Send** and **Listen** if you prefer fewer policies.

---

## Step 5 — Configure Your `.env` File

Copy `.env.example` to `.env` in the project root and fill in the connection strings:

```bash
cp .env.example .env
```

If using a **namespace-level** Send policy, the same connection string works for all hubs:

```
EVENTHUB_VITALS_CONN_STR=Endpoint=sb://ehns-rti-demo-yourname.servicebus.windows.net/;SharedAccessKeyName=SendPolicy;SharedAccessKey=YOUR_KEY_HERE
EVENTHUB_VITALS_NAME=hospital-vitals

EVENTHUB_MOVEMENT_CONN_STR=Endpoint=sb://ehns-rti-demo-yourname.servicebus.windows.net/;SharedAccessKeyName=SendPolicy;SharedAccessKey=YOUR_KEY_HERE
EVENTHUB_MOVEMENT_NAME=hospital-movement

EVENTHUB_TRAIN_CONN_STR=Endpoint=sb://ehns-rti-demo-yourname.servicebus.windows.net/;SharedAccessKeyName=SendPolicy;SharedAccessKey=YOUR_KEY_HERE
EVENTHUB_TRAIN_NAME=metrotrain

EVENTHUB_FLIGHT_CONN_STR=Endpoint=sb://ehns-rti-demo-yourname.servicebus.windows.net/;SharedAccessKeyName=SendPolicy;SharedAccessKey=YOUR_KEY_HERE
EVENTHUB_FLIGHT_NAME=flight-tracker

EVENTHUB_WATER_CONN_STR=Endpoint=sb://ehns-rti-demo-yourname.servicebus.windows.net/;SharedAccessKeyName=water-quality-send-listen;SharedAccessKey=YOUR_KEY_HERE
EVENTHUB_WATER_NAME=water-quality

EVENTHUB_WASTE_CONN_STR=Endpoint=sb://ehns-rti-demo-yourname.servicebus.windows.net/;SharedAccessKeyName=wasteSendListen;SharedAccessKey=YOUR_KEY_HERE
EVENTHUB_WASTE_NAME=water-waste
```

If using **hub-level** policies, each connection string will be different.

---

## Connection String Format

Event Hub connection strings look like this:

```
Endpoint=sb://<namespace>.servicebus.windows.net/;SharedAccessKeyName=<policy>;SharedAccessKey=<key>
```

When using a **hub-level** policy, it also includes `EntityPath=<event-hub-name>` at the end.

---

## Verify

After creating everything, your namespace should show 6 Event Hubs:

```
ehns-rti-demo-yourname
├── hospital-vitals
├── hospital-movement
├── metrotrain
├── flight-tracker
├── water-quality
└── water-waste
```

You can verify by running one of the simulators:

```bash
cd hospital
pip install -r requirements.txt
python hospital_vitals.py
```

If you see vitals printing to the console without errors, your Event Hub is configured correctly.

---

## Clean Up

When you're done with the demo, delete the resource group to avoid ongoing charges:

```bash
az group delete --name rg-fabric-rti-demo --yes --no-wait
```

---

[← Back to main README](../README.md)
