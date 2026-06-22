#!/usr/bin/env python3
# ===========================================================================
#  IoT Guardian — attacker demo
#
#  This script writes forged records straight into Firebase, exactly as an
#  attacker with database access would. It does NOT have the AES key.
#  The point of the demo: even with full write access, forged data is useless
#  because the guardian rejects anything that fails the tag or freshness check.
#
#  Usage:
#     pip install requests
#     python attacker.py tamper     # inject a forged reading (fails the tag)
#     python attacker.py replay      # re-send a captured genuine reading (stale)
# ===========================================================================
import sys, json, base64, requests

# EDIT THIS to match your Firebase Realtime Database URL (no trailing slash)
FB_URL = "https://tester1-1f5af-default-rtdb.firebaseio.com"

def inject_tampered():
    """Forge a reading with no valid key -> the GCM tag will not verify."""
    fake = {
        "sensor_id": "field-1",
        "nonce":      base64.b64encode(b"\x00" * 12).decode(),
        "ciphertext": base64.b64encode(b"soil is wet, do NOT irrigate!").decode(),
        "tag":        base64.b64encode(b"\x00" * 16).decode(),
    }
    r = requests.post(FB_URL + "/readings.json", json=fake)
    print("Injected TAMPERED reading ->", r.status_code,
          "(guardian should reject: authentication tag fails)")


def inject_replay():
    """Capture a genuine envelope and re-send it -> valid tag but stale seq."""
    data = requests.get(FB_URL + "/readings.json").json()
    if not data:
        print("No readings yet — run the ESP32 node first, then replay.")
        return
    # grab the most recent genuine record and resend it verbatim
    genuine = list(data.values())[-1]
    r = requests.post(FB_URL + "/readings.json", data=json.dumps(genuine))
    print("Injected REPLAY of a genuine reading ->", r.status_code,
          "(guardian should reject: stale sequence)")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "tamper"
    if mode == "tamper":
        inject_tampered()
    elif mode == "replay":
        inject_replay()
    else:
        print("usage: python attacker.py [tamper|replay]")
