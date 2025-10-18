"""
Tiny local tester for the Easy-Artistry API.

Usage:
  1) Start the server in another terminal:
        (easy_art) > python API.py
  2) Run this script:
        (easy_art) > python test_client.py
"""

import json
import time
import requests

BASE = "http://127.0.0.1:8000"

def pretty(obj): print(json.dumps(obj, ensure_ascii=False, indent=2))

def test_health():
    r = requests.get(f"{BASE}/healthz", timeout=10)
    print("healthz:", r.status_code, r.text)

def test_generate():
    payload = {
        "prompt": "silver-haired high-school girl, blue eyes, sitting by the window in a classroom, soft sunlight, blazer, red ribbon tie, anime illustration, clean lines, detailed hair, single subject, looking at viewer",
        "negative_prompt": "low quality, worst quality, blurry, watermark, text, duplicate body, extra head, extra arms, extra legs",
        "size": "768x1024",
        "n": 1,
        "model": "local",
        "preset": "high",  # fast | balanced | high | ultra
        "sd_overrides": {
            # Match your best WebUI-like settings here if needed
            "sampler_name": "DPM++ 2M SDE",
            "steps": 28,
            "cfg_scale": 6.5,
            "enable_hr": True,
            "hr_scale": 1.6,
            "hr_upscaler": "R-ESRGAN 4x+ Anime6B",
            "denoising_strength": 0.35,
            "hr_second_pass_steps": 10,
            # "seed": 123456,  # uncomment to fix seed
        },
    }
    r = requests.post(f"{BASE}/generate", json=payload, timeout=600)
    print("generate:", r.status_code)
    if r.ok:
        pretty(r.json())
    else:
        print("detail:", r.text)

def test_logs():
    r = requests.get(f"{BASE}/logs?limit=200", timeout=10)
    print("logs:", r.status_code)
    if r.ok:
        # Print last 20 lines to avoid flooding the console
        lines = r.json().get("lines", [])
        for ln in lines[-20:]:
            print(ln)

if __name__ == "__main__":
    test_health()
    test_generate()
    # Wait a moment to let the backend print stuff
    time.sleep(1.0)
    test_logs()
