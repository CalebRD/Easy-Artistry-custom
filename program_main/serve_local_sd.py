#!/usr/bin/env python
"""
Automatically detect GPU and launch Automatic1111 WebUI (with --api).

• GPU detected  → add --xformers + half precision for extra speed  
• No GPU       → start in CPU‑only mode (--precision full --no‑half --skip‑torch‑cuda‑test)

Usage:
    python serve_local_sd.py [--port 7860] [--model-path /path/to/model.safetensors]
"""

import argparse, shutil, subprocess, sys, os, pathlib, time
import torch, requests

ROOT = pathlib.Path(__file__).resolve().parent / "stable-diffusion-webui"

def detect_cuda() -> bool:
    return torch.cuda.is_available() and shutil.which("nvidia-smi") is not None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", default="7860")
    ap.add_argument("--model-path", default="")
    args = ap.parse_args()

    if not ROOT.exists():
        print("Cannot find 'stable-diffusion-webui' directory; please git clone it first.")
        sys.exit(1)

    cmd = [sys.executable, "launch.py", "--api", "--listen", "--port", args.port]

    if detect_cuda():
        print("✅ GPU detected (CUDA available). Launching with xformers + half precision …")
        cmd += ["--xformers", "--medvram"]
    else:
        print("⚠️ No GPU detected, running in CPU‑only mode (this will be slower) …")
        cmd += ["--precision", "full", "--no-half", "--skip-torch-cuda-test"]

    # add checkpoint path if provided
    if args.model_path:
        cmd += ["--ckpt", args.model_path]

    # start WebUI
    print("▶ Launch command:", " ".join(cmd))
    subprocess.Popen(cmd, cwd=ROOT)

    # simple heartbeat check
    host = f"http://127.0.0.1:{args.port}"
    for _ in range(30):
        try:
            requests.get(f"{host}/sdapi/v1/sd-models", timeout=3)
            print(f"🚀 WebUI is ready at {host}")
            break
        except requests.exceptions.RequestException:
            time.sleep(2)
    else:
        print("⏰ WebUI startup timed out; please check the log window.")

if __name__ == "__main__":
    main()
