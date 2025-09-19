# -*- coding: utf-8 -*-
"""
api.py — Unified backend API wrapper for front-end integration.

This module consolidates functions from `backend_main.py` into a stable, 
front-end-facing API layer. It provides:
  1) Pure Python API (functions/classes) for direct invocation from C# via interop.
  2) Optional FastAPI HTTP endpoints for C# applications to call over HTTP.

Dependencies:
  - Requires `backend_main.py` in the same directory.
  - For HTTP service, install: `pip install fastapi uvicorn`.

Usage in C# (via HTTP)
----------------------
// Example with HttpClient
HttpClient client = new HttpClient();
var response = await client.PostAsJsonAsync("http://localhost:8000/generate", new {
    prompt = "Cyberpunk city skyline",
    model = "dalle",
    size = "1024x1024"
});
var result = await response.Content.ReadFromJsonAsync<MyResponse>();

Usage in Python
---------------
from api import ImageAPI
api = ImageAPI()
prompt_obj = api.chat_to_prompt("Cyberpunk city skyline")
imgs = api.generate_image({"prompt": prompt_obj["prompt"], "model": "dalle"})
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
import json
import re
import socket

# Import functions from backend_main.py
from backend_main import (
    chat_generate_prompt,
    generate_image_from_prompt,
    start_local_server,
    stop_local_server,
    switch_local_model,
)

# ---------------------------------------------------------------------
# Types & Validation
# ---------------------------------------------------------------------
class ModelKind(str, Enum):
    """Enum alias for supported models (aligned with backend_main)."""
    LOCAL = "local"
    SD = "stable-diffusion"
    DALLE = "dalle"
    DALLE3 = "dalle3"
    SDXL = "sdxl"


def _validate_size(size: str) -> None:
    if not isinstance(size, str) or not re.match(r"^\d+x\d+$", size):
        raise ValueError('size must follow format "1024x1024" with multiples of 64')
    w, h = (int(x) for x in size.split("x"))
    if w % 64 or h % 64:
        raise ValueError("Width and height must be multiples of 64")


@dataclass
class GenerateParams:
    prompt: str
    size: str = "1024x1024"
    model: str = "stable-diffusion"
    n: int = 1
    negative_prompt: str = "bad quality"
    preset: str = "balanced"
    sd_params: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.prompt or not isinstance(self.prompt, str):
            raise ValueError("prompt cannot be empty")
        _validate_size(self.size)
        if not isinstance(self.n, int) or self.n <= 0:
            raise ValueError("n must be a positive integer")
        if not isinstance(self.sd_params, dict):
            raise ValueError("sd_params must be a dictionary")


# ---------------------------------------------------------------------
# Facade Class: Unified API for front-end
# ---------------------------------------------------------------------
class ImageAPI:
    """Unified API for image generation and local server lifecycle management."""

    def chat_to_prompt(self, text: str) -> Dict[str, Any]:
        """Convert natural language text into structured tags and prompt."""
        return chat_generate_prompt(text)

    def generate_image(self, params: GenerateParams | Dict[str, Any]) -> List[str]:
        """Generate images using backend implementation."""
        if isinstance(params, dict):
            params = GenerateParams(**params)
        params.validate()
        return generate_image_from_prompt(
            prompt=params.prompt,
            size=params.size,
            model=params.model,
            n=params.n,
            negative_prompt=params.negative_prompt,
            preset=params.preset,
            sd_params=params.sd_params or None,
        )

    def start_local_sd(self, model_name: Optional[str] = None) -> None:
        """Start local Stable Diffusion server (idempotent)."""
        start_local_server(model_name)

    def switch_local_sd(self, model_name: str) -> None:
        """Switch the active model in local Stable Diffusion server."""
        switch_local_model(model_name)

    def stop_local_sd(self) -> None:
        """Stop the local Stable Diffusion server."""
        stop_local_server()

    @staticmethod
    def health() -> Dict[str, Any]:
        """Health check: verify if port 7860 is open (A1111 WebUI default)."""
        return {
            "local_sd_port_7860_open": _port_open("127.0.0.1", 7860),
            "status": "ok",
        }


# ---------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------

def _port_open(host: str, port: int, timeout: float = 0.2) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


# ---------------------------------------------------------------------
# Optional: FastAPI HTTP Endpoints (for C# front-end calls)
# ---------------------------------------------------------------------
try:
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel

    class _GenBody(BaseModel):
        prompt: str
        size: str = "1024x1024"
        model: str = "stable-diffusion"
        n: int = 1
        negative_prompt: str = "bad quality"
        preset: str = "balanced"
        sd_params: Dict[str, Any] = {}

    class _ChatBody(BaseModel):
        text: str

    class _SwitchBody(BaseModel):
        model_name: str

    class _StartBody(BaseModel):
        model_name: Optional[str] = None

    _api_impl = ImageAPI()
    http_app = FastAPI(title="Image API", version="1.0.0")

    @http_app.get("/health")
    def _health():
        return _api_impl.health()

    @http_app.post("/chat-to-prompt")
    def _chat_to_prompt(body: _ChatBody):
        try:
            return _api_impl.chat_to_prompt(body.text)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @http_app.post("/generate")
    def _generate(body: _GenBody):
        try:
            params = GenerateParams(**body.model_dump())
            return {"images": _api_impl.generate_image(params)}
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @http_app.post("/server/start")
    def _server_start(body: _StartBody):
        try:
            _api_impl.start_local_sd(body.model_name)
            return {"ok": True}
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @http_app.post("/server/switch")
    def _server_switch(body: _SwitchBody):
        try:
            _api_impl.switch_local_sd(body.model_name)
            return {"ok": True}
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @http_app.post("/server/stop")
    def _server_stop():
        try:
            _api_impl.stop_local_sd()
            return {"ok": True}
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

except Exception:
    http_app = None  # FastAPI not installed


# ---------------------------------------------------------------------
# CLI Example
# ---------------------------------------------------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Image API CLI")
    parser.add_argument("prompt", type=str, help="positive prompt")
    parser.add_argument("--model", default="stable-diffusion")
    parser.add_argument("--size", default="1024x1024")
    parser.add_argument("--n", type=int, default=1)
    parser.add_argument("--negative", default="bad quality")
    parser.add_argument("--preset", default="balanced")
    parser.add_argument("--sd-params", default="{}", help="JSON dict for A1111 overrides")
    parser.add_argument("--start-local", action="store_true")
    parser.add_argument("--switch", default=None)

    args = parser.parse_args()

    api = ImageAPI()

    if args.start_local:
        api.start_local_sd(args.switch)
    elif args.switch:
        api.switch_local_sd(args.switch)

    params = GenerateParams(
        prompt=args.prompt,
        model=args.model,
        size=args.size,
        n=args.n,
        negative_prompt=args.negative,
        preset=args.preset,
        sd_params=json.loads(args.sd_params),
    )
    images = api.generate_image(params)
    print("\nGenerated:")
    for i, url in enumerate(images, 1):
        print(f"  [{i}] {url}")
