# API.py
"""
Expose your existing /generate endpoint AND a simple /logs endpoint that
returns whatever appeared in the Python terminal (stdout/stderr).

How it works:
- We install a "tee" for sys.stdout and sys.stderr at import-time.
- The tee writes to the original stream (so the terminal still shows logs)
  AND also appends each written line to an in-memory ring buffer (deque).
- Front-end can poll GET /logs?limit=500 to show recent terminal output.

This is intentionally simple and dev-friendly. You can later replace it with a
proper logging pipeline or SSE streaming if needed.
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

# Your existing entry point; no change needed here.
from backend_main import generate_image_from_prompt

# -----------------------------------------------------------------------------
# Simple ring buffer for terminal output
# -----------------------------------------------------------------------------

# Keep the last N lines of "terminal" output (stdout/stderr).
_LOG_RING = deque(maxlen=2000)  # tune as you like
_LOG_LOCK = threading.Lock()    # protect multi-thread writes (extra safety)

class _RingWriter(io.TextIOBase):
    """
    A text stream that writes both to a "real" stream (stdout/stderr)
    and to an in-memory ring buffer line-by-line.
    """
    def __init__(self, real: io.TextIOBase, ring: deque, lock: threading.Lock):
        self._real = real
        self._ring = ring
        self._lock = lock
        self._buf = []  # accumulate chars until newline

    def write(self, s: str) -> int:
        # Always forward to the original stream first (so terminal stays unchanged)
        written = self._real.write(s)

        # Buffer -> split by newline -> append full lines to ring
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

# Install the tee once at import-time.
if not isinstance(sys.stdout, _RingWriter):
    sys.stdout = _RingWriter(sys.__stdout__, _LOG_RING, _LOG_LOCK)  # type: ignore[assignment]
if not isinstance(sys.stderr, _RingWriter):
    sys.stderr = _RingWriter(sys.__stderr__, _LOG_RING, _LOG_LOCK)  # type: ignore[assignment]

# -----------------------------------------------------------------------------
# API models
# -----------------------------------------------------------------------------

class GenerateRequest(BaseModel):
    prompt: str = Field(..., description="Positive prompt (plain text or SD-style).")
    negative_prompt: Optional[str] = Field("", description="Negative prompt.")
    size: str = Field("768x768", description='Canvas size "<W>x<H>", e.g. "768x1024".')
    n: int = Field(1, ge=1, le=8, description="Number of images.")
    model: str = Field("local", description='Backend route, keep "local" for A1111.')
    preset: str = Field("balanced", description='Quality preset: fast|balanced|high|ultra')
    sd_overrides: Optional[Dict[str, Any]] = Field(
        None,
        description="Per-call overrides that DO NOT modify presets."
    )

    @validator("preset")
    def _validate_preset(cls, v: str) -> str:
        allowed = {"fast", "balanced", "high", "ultra"}
        if v not in allowed:
            raise ValueError(f"preset must be one of {sorted(allowed)}")
        return v

class GenerateResponse(BaseModel):
    images: List[str] = Field(..., description="Generated image paths or URLs.")

class LogsResponse(BaseModel):
    lines: List[str] = Field(..., description="Recent terminal lines (stdout+stderr).")

# -----------------------------------------------------------------------------
# FastAPI app
# -----------------------------------------------------------------------------

app = FastAPI(title="Easy-Artistry Backend API", version="1.1.0")

# CORS for quick testing; tighten in production.
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
def healthz() -> Dict[str, str]:
    return {"status": "ok"}

@app.post("/generate", response_model=GenerateResponse)
def api_generate(req: GenerateRequest) -> GenerateResponse:
    """
    Generate images. This simply forwards 'preset' and 'sd_overrides' to your
    existing generator. Any exceptions will naturally go to stderr/stdout and
    thus appear in /logs as well.
    """
    try:
        urls = generate_image_from_prompt(
            req.prompt,
            size=req.size,
            n=req.n,
            model=req.model,
            preset=req.preset,
            sd_params=(req.sd_overrides or {}),
            negative_prompt=req.negative_prompt,
        )
        return GenerateResponse(images=urls)
    except Exception as e:
        # This message will be printed to stderr and captured in /logs.
        print(f"[API ERROR] /generate failed: {e}", file=sys.stderr)
        raise HTTPException(status_code=500, detail=str(e)) from e

@app.get("/logs", response_model=LogsResponse)
def get_logs(limit: int = Query(500, ge=1, le=2000)):
    """
    Return the most recent 'limit' lines captured from the Python terminal
    (stdout + stderr). Front-end can poll this endpoint during development
    to display backend errors/prints in a chat window or console panel.
    """
    with _LOG_LOCK:
        lines = list(_LOG_RING)[-limit:]
    return LogsResponse(lines=lines)

# -----------------------------------------------------------------------------
# Local entry point
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    # Run with: python API.py
    # Or: uvicorn API:app --host 0.0.0.0 --port 8000
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
