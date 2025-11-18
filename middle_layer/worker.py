# -*- coding: utf-8 -*-
# middle_layer/worker.py
# A native Worker for the JSON-Lines (one JSON per line) protocol.
# This script is started by a C# subprocess; it receives requests from stdin and sends responses to stdout.

import sys, os, json, traceback, contextlib
from pathlib import Path

# ---------- Make Python able to import the backend directory ----------
PROJ_ROOT = Path(__file__).resolve().parents[1]           # .../Easy-Artistry-custom
BACKEND   = PROJ_ROOT / "backend"
LOG_PATH  = PROJ_ROOT / "backend.log"
os.chdir(PROJ_ROOT.as_posix())                            # Relative paths are based on the project root
root_str = str(PROJ_ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)
backend_str = str(BACKEND)
if backend_str not in sys.path:
    sys.path.insert(0, backend_str)

# Always start with a fresh log for each worker process
try:
    LOG_PATH.write_text("", encoding="utf-8")
except OSError:
    # If another process still holds the file, append mode below will continue working
    pass

def _append_log(message: str) -> None:
    """Append a single line to backend.log."""
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as log_file:
        log_file.write(message)
        if not message.endswith("\n"):
            log_file.write("\n")


_append_log("[startup] worker initializing")

def _append_log(message: str) -> None:
    """Append a single line to backend.log."""
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as log_file:
        log_file.write(message)
        if not message.endswith("\n"):
            log_file.write("\n")


_append_log("[startup] worker initializing")

# ---------- Import your facade functions ----------
try:
    from backend.backend_main import generate_image_from_prompt
    from backend.local_sd import start_server as _start_server
    from backend.local_sd import shutdown_server as _shutdown_server
    from backend.local_sd import _switch_model as _switch_model_inner
except Exception:  # pragma: no cover - defensive logging
    _append_log("[startup] failed to import backend modules")
    _append_log(traceback.format_exc())
    # Surface the failure via stderr so the host process can show it
    sys.__stderr__.write("backend worker import failed\n")
    sys.__stderr__.write(traceback.format_exc())
    sys.__stderr__.flush()
    raise
else:
    _append_log("[startup] backend modules loaded")

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

# Avoid polluting the protocol with prints from the backend: temporarily redirect stdout to backend.log
@contextlib.contextmanager
def redirect_print_to_log():
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    old_stdout = sys.stdout
    log_file = open(LOG_PATH, "a", encoding="utf-8")

    class _LogWriter:
        def __init__(self, file):
            self._file = file

        def write(self, data):
            if data:
                self._file.write(data)
                self._file.flush()

        def flush(self):
            self._file.flush()

    sys.stdout = _LogWriter(log_file)
    try:
        yield
    finally:
        sys.stdout = old_stdout
        log_file.close()

def handle_one(line: str):
    req = json.loads(line)
    rid = req.get("id")
    method = req.get("method")
    _append_log(f"[request] id={rid} method={method}")
    try:
        with redirect_print_to_log():
            result = dispatch(req.get("method"), req.get("params") or {})
        out = {"id": rid, "result": result}
        _append_log(f"[response] id={rid} method={method} status=ok")
    except Exception:
        _append_log(f"[error] id={rid} method={method} dispatch failed")
        _append_log(traceback.format_exc())
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
    _append_log("[startup] worker entering request loop")
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        if not line.strip():
            continue
        handle_one(line)

if __name__ == "__main__":
    main()
