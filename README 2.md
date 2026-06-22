# IoT Guardian — Secure Smart Agriculture Sensor System

> **Cyber Defence Innovation Hackathon · York St John University London**  
> Theme 3: Secure IoT · 22 June 2026

---

## Overview

IoT Guardian is a security-first smart agriculture sensor system built on the principle of **zero trust data** — the system never acts on a reading it cannot cryptographically prove is genuine and fresh.

Most smart-farm tutorials send sensor data to the cloud in plaintext with no authentication. Anyone who can write to the database can control what the system does. IoT Guardian fixes this. Every reading is **sealed with AES-256-GCM** on the ESP32 before it leaves the device. The Guardian dashboard only accepts a reading if it proves two things:

- **Authentic** — produced by a device holding the shared AES-256 key (not forged)
- **Fresh** — carries a sequence number strictly newer than the last accepted one (not replayed)

Forged and replayed readings are detected and rejected in real time, even if an attacker has full write access to the Firebase database. The system proves this live with a working attacker demo.

---

## Problem & Challenge

Agricultural IoT systems take **automatic physical actions** based on sensor data received over a network — but most have no way to verify whether a reading is genuine. An attacker does not need to break in or steal anything; they only need to lie to the system convincingly.

The danger is **physical and irreversible on a crop's timescale**:

- A forged *"soil is wet"* reading stops irrigation → the crop dies of drought
- A forged *"soil is dry"* reading triggers irrigation → the field floods

By the time anyone notices, the damage is done. This makes **integrity** — not just confidentiality — the real security stake. A stolen soil reading is harmless; a forged one can destroy a harvest.

### Threat Model

The attacker can watch network traffic and write directly to the Firebase database — the database rules are left open on purpose to prove this. But the attacker does **not** have the device's secret AES key.

| # | Vulnerability                 | Attack                                 | Defence                                      |
|---|-------------------------------|----------------------------------------|----------------------------------------------|
| 1 | Data is not authenticated     | Inject a fake reading                  | AES-256-GCM authentication tag               |
| 2 | Data is not fresh             | Replay a captured genuine reading      | Monotonic sequence number                    |
| 3 | Transport / store not trusted | Sniff traffic or write to the database | Payload-level encryption (defence in depth)  |
---

## Tech Stack

| Layer                  | Technology                                                                                                                                                        |
|------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Sensor node**        | ESP32 (simulated in [Wokwi](https://wokwi.com/projects/467531344015877121))                                                                                       |
| **Sensors**            | DHT22 (temperature & humidity), FC-28 (soil moisture), LDR (light), RTC DS1307                                                                                   |
| **Actuators**          | Relay (irrigation), LED                                                                                                                                           |
| **Display**            | 20×4 I²C LCD, OLED                                                                                                                                                |
| **Encryption**         | AES-256-GCM via mbedTLS (built into ESP32 core)                                                                                                                   |
| **Anti-replay**        | Monotonic sequence number persisted to ESP32 flash (NVS)                                                                                                          |
| **Cloud store**        | [Firebase Realtime Database](https://console.firebase.google.com/u/0/project/tester1-1f5af/database/tester1-1f5af-default-rtdb/data/~2Freadings) over HTTPS       |
| **Guardian dashboard** | Vanilla HTML/JS — polls Firebase, decrypts with Web Crypto API, verifies, decides                                                                                 |
| **Attacker demo**      | Python 3 + `requests`                                                                                                                                             |

### Architecture

```
ESP32 sensor node            Cloud store           Guardian (dashboard)
(Wokwi simulation)

┌──────────────────┐  HTTPS  ┌──────────┐  poll  ┌─────────────────────┐
│  read sensors    │────────►│ Firebase │───────►│  decrypt + verify   │
│  AES-256-GCM     │encrypted│ Realtime │encrypted│  tag  → authentic? │
│  seal + nonce    │envelope │ Database │envelope │  seq  → fresh?     │
│  + sequence      │         │          │         │  → irrigate?        │
└──────────────────┘         └──────────┘         └─────────────────────┘
  senses, seals, sends           stores              decides what to trust
```

The sensor node makes **no security-critical decisions** — it senses, seals, and sends. The Guardian is the sole gatekeeper. The LED on the ESP32 reacts to an `/alert` flag the Guardian writes to Firebase when an attack is detected.

---

AES-256-GCM (the core)

Each reading is sealed with AES-256-GCM. We use GCM specifically — not
plain AES — because GCM does two jobs at once:


AES-256 encrypts the reading with a 256-bit key → confidentiality
(anyone without the key sees only ciphertext).
GCM produces a 16-byte authentication tag, a key-dependent fingerprint
of the message → integrity and authenticity. If even one bit is altered, or
the message was made by someone without the key, the tag fails verification
and the reading is rejected.


Plain AES (or modes such as CBC) would encrypt but could not detect tampering;
the GCM tag is exactly what makes forgery detection — and the whole project —
possible. The encryption produces three values, all visible in Firebase: the
nonce, the ciphertext, and the tag.


## Project Files

| File                      | Role                                                                                                                                                                         |
|---------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `main.ino`                | ESP32 sensor node: reads sensors, AES-256-GCM encrypts each reading, POSTs the encrypted envelope to Firebase. Sequence number persisted to flash. Polls `/alert` node to trigger LED alarm. |
| `FC28.h` / `FC28.cpp`     | FC-28 soil moisture sensor library                                                                                                                                           |
| `diagram.json`            | Wokwi circuit diagram                                                                                                                                                        |
| `guardian-dashboard.html` | Guardian: polls Firebase, decrypts and verifies each reading (tag + sequence), shows live irrigation decision, logs every acceptance and rejection with timestamps. Attack rate detection with live alert banner. |
| `attacker.py`             | Attack demo: injects forged records (tamper) and replays captured genuine records (replay) directly into Firebase to prove both defences work.                                |
---

## Setup & Run Instructions

### Prerequisites

- A [Wokwi](https://wokwi.com) account (browser-based, no hardware required). The simulator can be found at https://wokwi.com/projects/467531344015877121
- A Firebase project with a **Realtime Database** (not Firestore). The databse can be found at https://console.firebase.google.com/u/0/project/tester1-1f5af/database/tester1-1f5af-default-rtdb/data/~2Freadings
- Python 3 with the `requests` library

```bash
pip install requests
```

---

### Step 1 — Firebase

1. In the [Firebase console](https://console.firebase.google.com/u/0/project/tester1-1f5af/database/tester1-1f5af-default-rtdb/data/~2Freadings), create a **Realtime Database** and start it in **test mode**
2. Copy the database URL (no trailing slash), e.g. `https://YOUR-PROJECT-default-rtdb.firebaseio.com`
3. Set the database rules — intentionally open for the demo to prove the system stays secure regardless:

```json
{ "rules": { ".read": true, ".write": true } }
```

---

### Step 2 — Configure

Set the **same** database URL and **same** 32-character AES key in both files:

| File                      | Variables to set                     |
|---------------------------|--------------------------------------|
| `main.ino`                | `FB_URL` and `AES_KEY`               |
| `guardian-dashboard.html` | `FB_URL` and `KEY_STR`               |
| `attacker.py`             | `FB_URL` only (attacker has no key)  |

> `AES_KEY` (sketch) and `KEY_STR` (dashboard) must be **byte-for-byte identical** or every reading will fail authentication.

---

### Step 3 — Clear Firebase (before each demo)

Delete any old readings so the log starts clean:

1. Firebase console → Realtime Database → Data
2. Click **`readings`** → three dots ⋮ → **Delete**

---

### Step 4 — Run the Sensor Node

Load `main.ino` into [Wokwi](https://wokwi.com/projects/467531344015877121) (with `FC28.cpp`, `FC28.h`, and `diagram.json`) and run it.

The Wokwi simulation implements three security steps:

- **Step 1 — Encryption:** every sensor reading is sealed with **AES-256-GCM**, producing a ciphertext and a 16-byte authentication tag
- **Step 2 — Cloud:** the encrypted envelope is POSTed to Firebase over HTTPS
- **Step 3 — Trust validation:** the Guardian dashboard decrypts and verifies each reading before it is allowed to drive any irrigation decision

> **About AES-256-GCM:** this is an authenticated encryption mode that does two things at once — AES-256 scrambles the payload so no one without the key can read it, and GCM produces a cryptographic tag that proves the message was not tampered with. If even one byte is changed, the tag fails and the reading is rejected.

The serial monitor should print:
```
Sequence loaded from flash: N
Secure node initialised
Seq 1  ->  Firebase POST 200
```

Encrypted records will appear in the Firebase console immediately.

---

### Step 5 — Open the Guardian Dashboard

Open `guardian-dashboard.html` directly in a browser.

Within a couple of seconds you will see:
- 🟢 Green dot — live and connected to Firebase
- Soil %, temperature, humidity updating in real time
- **IRRIGATE** or **HOLD** irrigation decision
- The encrypted envelope exactly as stored in Firebase
- ACCEPTED entries appearing in the verification log

---

### Step 6 — Run the Attack Demo

This step demonstrates that the Guardian rejects both types of attack even when the attacker has full write access to Firebase.

**How the attacker works:**

- **Tamper attack** — injects a completely forged record with a fake ciphertext and zeroed-out tag. Because the attacker has no AES key, the GCM tag cannot be valid and the Guardian rejects it immediately.
- **Replay attack** — captures the most recent genuine record from Firebase and re-sends it verbatim. The tag is valid (it was genuine once), but the sequence number is stale so the Guardian rejects it as a replay.

**How to run the attacker:**

1. Install the required library:
```bash
pip install requests
```

2. Navigate to the project folder:
```bash
cd E:\Hackthon Event Files
```

3. Run the tamper attack:
```bash
python "attacker (1).py" tamper
```

4. Run the replay attack:
```bash
python "attacker (1).py" replay
```

Both appear as **REJECTED** in the dashboard immediately. If 5+ rejections hit within 10 seconds, the 🚨 **ACTIVE ATTACK DETECTED** banner appears automatically.

| Attack | Command                           | Dashboard result                     | Reason                                   |
|--------|-----------------------------------|--------------------------------------|------------------------------------------|
| Tamper | `python "attacker (1).py" tamper` | REJECTED — authentication tag failed | Attacker has no key, tag cannot be valid |
| Replay | `python "attacker (1).py" replay` | REJECTED — stale sequence            | Sequence number already seen and passed  |

---

## Dashboard Features

| Feature                | Description                                                  |
|------------------------|--------------------------------------------------------------|
| Live verified reading  | Decrypted soil %, temp, humidity, sequence number            |
| Irrigation decision    | IRRIGATE / HOLD based on verified soil reading only          |
| Encrypted record view  | Shows exactly what an attacker sees in Firebase              |
| 4 stat counters        | Accepted / Tampered / Replayed / Total seen                  |
| Attack alert banner    | Pulses amber when rejection rate spikes (≥5 in 10s)          |
| Sensor offline banner  | Warns if no verified reading arrives for 15 seconds          |
| Timestamp log          | Every acceptance and rejection logged with HH:MM:SS          |
| Pause scroll           | Freeze the log while reading during a live demo              |
---

## Team

| Name                        | Role                                                                   |
|-----------------------------|------------------------------------------------------------------------|
| **Dasuni Abeywickrama**     | Security design, ESP32 sensor node, Guardian dashboard, attacker demo  |
| **Sarujan Rajaratnam**      | AES-256-GCM layer, Firebase pipeline, Wokwi simulation                 |

York St John University London — Computer and Data Science Department

---

## Known Limitations & Next Steps

| Limitation                                                        | Production Answer                                                                   |
|-------------------------------------------------------------------|-------------------------------------------------------------------------------------|
| Single shared AES key across all nodes                            | Unique key per device stored in ESP32 hardware secure element                       |
| `sensor_id` stored in plaintext in Firebase                       | Bind as GCM Associated Data (AAD) so the tag also authenticates the field identity  |
| Verification happens in the browser after data is already stored  | Move to a Firebase Cloud Function — bad data never reaches the database             |
| Open database rules                                               | Restrict writes to authenticated devices only                                       |
| Certificate validation relaxed in Wokwi simulation               | Production deployment pins certificates and uses MQTT-over-TLS                      |
| Single sequence counter in RAM                                    | Already persisted to flash (NVS) — next step is per-field counters                  |
**Possible extensions:** timestamp-based freshness windows, anomaly detection (flagging impossible value jumps), rate limiting, key rotation protocol.

---

