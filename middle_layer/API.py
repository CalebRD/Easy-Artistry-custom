"""
Minimal REST API for Easy-Artistry.

- POST /generate : create images by forwarding to your existing
  `generate_image_from_prompt(...)`
- GET  /logs     : return recent stdout/stderr lines (dev-friendly)

The API accepts:
  - prompt (str)
  - negative_prompt (str)
  - size (e.g. "768x1024")
  - n (1..8)
  - model ("local" for A1111 path)
  - preset ("fast" | "balanced" | "high" | "ultra")
  - sd_overrides (dict)  # per-call overrides; DO NOT mutate presets

Notes:
- We tee stdout/stderr into a ring buffer so the front-end can poll /logs.
- Keep this simple now; you can later switch to structured logging or SSE.
"""

from __future__ import annotations

import io
import sys
import threading
from collections import deque
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator

# Import your existing entry point. This must exist.
# Signature we call: generate_image_from_prompt(prompt, size, n, model, preset, sd_params, negative_prompt)
import sys
import os
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backend'))
from backend_main import generate_image_from_prompt

# -----------------------------------------------------------------------------
# Log tee (stdout/stderr -> terminal AND in-memory ring)
# -----------------------------------------------------------------------------

_LOG_RING = deque(maxlen=3000)
_LOG_LOCK = threading.Lock()

class _RingWriter(io.TextIOBase):
    def __init__(self, real: io.TextIOBase, ring: deque, lock: threading.Lock):
        self._real = real
        self._ring = ring
        self._lock = lock
        self._buf: list[str] = []

    def write(self, s: str) -> int:
        written = self._real.write(s)
        for ch in s:
            self._buf.append(ch)
            if ch == "\n":
                line = "".join(self._buf)
                with self._lock:
                    self._ring.append(line.rstrip("\n"))
                self._buf.clear()
        return written

    def flush(self) -> None:
        self._real.flush()

# Install tees once.
if not isinstance(sys.stdout, _RingWriter):
    sys.stdout = _RingWriter(sys.__stdout__, _LOG_RING, _LOG_LOCK)  # type: ignore
if not isinstance(sys.stderr, _RingWriter):
    sys.stderr = _RingWriter(sys.__stderr__, _LOG_RING, _LOG_LOCK)  # type: ignore

# -----------------------------------------------------------------------------
# Models
# -----------------------------------------------------------------------------

class GenerateRequest(BaseModel):
    prompt: str = Field(..., description="Positive prompt (plain or SD-style).")
    negative_prompt: Optional[str] = Field("", description="Negative prompt.")
    size: str = Field("768x768", description='Canvas "<W>x<H>", e.g. "768x1024".')
    n: int = Field(1, ge=1, le=8, description="Number of images to create.")
    model: str = Field("local", description='Backend route; keep "local" for A1111.')
    preset: str = Field("balanced", description='Quality preset: fast|balanced|high|ultra')
    sd_overrides: Optional[Dict[str, Any]] = Field(
        None, description="Per-call overrides (will NOT mutate presets)."
    )

    @validator("preset")
    def _check_preset(cls, v: str) -> str:
        allowed = {"fast", "balanced", "high", "ultra"}
        if v not in allowed:
            raise ValueError(f'preset must be one of {sorted(allowed)}')
        return v

class GenerateResponse(BaseModel):
    images: List[str] = Field(..., description="File paths or URLs to generated images.")

class LogsResponse(BaseModel):
    lines: List[str] = Field(..., description="Recent stdout/stderr lines.")

# -----------------------------------------------------------------------------
# FastAPI app
# -----------------------------------------------------------------------------

app = FastAPI(title="Easy-Artistry API", version="1.2.0")

# CORS for quick local testing; tighten for production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------------

@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}

@app.post("/generate", response_model=GenerateResponse)
def api_generate(req: GenerateRequest) -> GenerateResponse:
    """
    Forward request to your generator. Any Python exception will also be
    captured by /logs because stdout/stderr are tee'd to a ring buffer.
    """
    try:
        urls = generate_image_from_prompt(
            req.prompt,
            size=req.size,
            n=req.n,
            model=req.model,
            preset=req.preset,
            sd_params=(req.sd_overrides or {}),  # IMPORTANT: backend expects sd_params
            negative_prompt=req.negative_prompt or "",
        )
        return GenerateResponse(images=urls)
    except Exception as e:
        # Make sure the message shows in /logs.
        print(f"[API ERROR] /generate failed: {e}", file=sys.stderr)
        raise HTTPException(status_code=500, detail=str(e)) from e

@app.get("/logs", response_model=LogsResponse)
def api_logs(limit: int = Query(500, ge=1, le=3000)) -> LogsResponse:
    with _LOG_LOCK:
        lines = list(_LOG_RING)[-limit:]
    return LogsResponse(lines=lines)

# -----------------------------------------------------------------------------
# Dev entry
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    # Run API locally:
    #   python API.py
    # Then test with the provided test_client.py or curl.
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
