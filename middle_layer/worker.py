# -*- coding: utf-8 -*-
# middle_layer/worker.py
# A native Worker for the JSON-Lines (one JSON per line) protocol.
# This script is started by a C# subprocess; it receives requests from stdin and sends responses to stdout.

import sys, os, json, traceback, contextlib
from pathlib import Path

# ---------- Make Python able to import the backend directory ----------
PROJ_ROOT = Path(__file__).resolve().parents[1]           # .../Easy-Artistry-custom
BACKEND   = PROJ_ROOT / "backend"
os.chdir(PROJ_ROOT.as_posix())                            # Relative paths are based on the project root
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

# ---------- Import your facade functions ----------
from backend.backend_main import generate_image_from_prompt
from backend.local_sd import start_server as _start_server
from backend.local_sd import shutdown_server as _shutdown_server
from backend.local_sd import _switch_model as _switch_model_inner

REGISTRY = {}

def register(ns: str, table: dict):
    for name, fn in table.items():
        REGISTRY[f"{ns}.{name}"] = fn

# 1) Main image generation function
register("images", {
    "generate": generate_image_from_prompt,
})

# 2) Local SD server management - expose stable names to the outside
def start_local_sd(model_path: str | None = None):
    # Idempotent, if local_sd.start_server is already running, it will return directly
    _start_server(model_path)

def shutdown_local_sd():
    _shutdown_server()

def switch_local_model(model_name: str, timeout: int = 90):
    # Wrap it in a layer to prevent the frontend from directly depending on the internal function name `_switch_model`
    _switch_model_inner(model_name, timeout=timeout)

register("local_sd", {
    "start": start_local_sd,            # method: "local_sd.start"
    "shutdown": shutdown_local_sd,      # method: "local_sd.shutdown"
    "switch_model": switch_local_model, # method: "local_sd.switch_model"
})

def dispatch(method: str, params: dict):
    fn = REGISTRY.get(method)
    if not fn:
        raise ValueError(f"Unknown method: {method}")
    return fn(**(params or {}))

# Avoid polluting the protocol with prints from the backend: temporarily redirect stdout to stderr
@contextlib.contextmanager
def redirect_print_to_stderr():
    old = sys.stdout
    try:
        sys.stdout = sys.stderr
        yield
    finally:
        sys.stdout = old

def handle_one(line: str):
    req = json.loads(line)
    rid = req.get("id")
    try:
        with redirect_print_to_stderr():
            result = dispatch(req.get("method"), req.get("params") or {})
        out = {"id": rid, "result": result}
    except Exception:
        out = {
            "id": rid,
            "error": {
                "code": "E_RUNTIME",
                "message": "backend error",
                "trace": traceback.format_exc()
            }
        }
    sys.__stdout__.write(json.dumps(out, ensure_ascii=False) + "\n")
    sys.__stdout__.flush()

def main():
    # -u/unbuffered is handled by the C# process; here we also ensure line-by-line processing.
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        if not line.strip():
            continue
        handle_one(line)

if __name__ == "__main__":
    main()
