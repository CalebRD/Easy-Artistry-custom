# -*- coding: utf-8 -*-
"""
backend_main.py  –  chat-prompt, server lifecycle, image generation (cloud + local)
"""

import os, sys, re, time, webbrowser
from typing import List, Dict, Any

# ---- project modules --------------------------------------------------------
from label import extract_tags, tags_to_prompt
from model_lab import generate_image as sd_generate           # cloud Stable Diffusion
from image import generate_image as dalle_generate            # DALL·E 3
from local_sd import generate_image as local_sd_generate      # local A1111 txt2img

# local server helpers
from local_sd import start_server as _start_server
from local_sd import shutdown_server as _shutdown_server
from local_sd import _switch_model                            # checkpoint hot-swap

# ============================================================================
# 1) Chat → prompt
# ============================================================================
def chat_generate_prompt(user_input: str) -> Dict[str, Any]:
    """Extract tags then convert to prompt."""
    user_input = user_input.strip()
    if not user_input:
        raise ValueError("user_input cannot be empty")
    tags = extract_tags(user_input)
    prompt = tags_to_prompt(tags)
    return {"tags": tags, "prompt": prompt}

# ============================================================================
# 2) Local server lifecycle
# ============================================================================
_local_up = False                           # whether we started WebUI
_default_checkpoint = "v1-5-pruned.safetensors"   # SD-1.5 for CPU speed

def start_local_server(model_name: str | None = None):
    """Launch A1111 WebUI once and optionally load a checkpoint."""
    global _local_up
    if not _local_up:
        _start_server()                     # boots or skips if already running
        _local_up = True
    _switch_model(model_name or _default_checkpoint)

def switch_local_model(model_name: str):
    """Hot-swap checkpoint; raises if server not running."""
    if not _local_up:
        raise RuntimeError("Local server not running; call start_local_server() first.")
    _switch_model(model_name)

def stop_local_server():
    """Gracefully shut down WebUI (only if we started it)."""
    global _local_up
    if _local_up:
        _shutdown_server()
        _local_up = False

# ============================================================================
# 3) Unified image generation
# ============================================================================
def generate_image_from_prompt(
    prompt: str,
    *,
    size: str = "1024x1024",
    model: str = "stable-diffusion",
    n: int = 1,
    negative_prompt: str = "bad quality",
) -> List[str]:
    """Front-end single entry; routes to cloud / local generators."""
    if not re.match(r"^\d+x\d+$", size):
        raise ValueError('size must be like "1024x1024"')

    m = model.lower().strip()

    if m in ("stable-diffusion", "sd", "sdxl"):
        urls = sd_generate(prompt=prompt, n=n, size=size,
                           negative_prompt=negative_prompt)

    elif m in ("dalle", "dall-e", "dalle3"):
        urls = dalle_generate(prompt=prompt, n=n, size=size)

    elif m in ("local_stable-diffusion", "local", "local_sd", "local_sdxl"):
        start_local_server()          
        urls = local_sd_generate(
            prompt=prompt,
            n=n,
            size=size,
            negative_prompt=negative_prompt,
            quality="balanced"
        )
    else:
        raise ValueError(f"unsupported model: {model}")

    return urls

# ============================================================================
# 4) CLI demo
# ============================================================================
if __name__ == "__main__":
    try:
        print("description:")
        user_text = input("> ").strip()

        data = chat_generate_prompt(user_text)
        print("\nPrompt:", data["prompt"])

        # ---- start server & generate ----
        start_local_server()                     # default SD-1.5
        t0 = time.time()
        urls = generate_image_from_prompt(
            data["prompt"],
            size="768x768",
            model="local",                       # use local server
            n=1
        )
        dt = time.time() - t0
        img = urls[0]
        print(f"Done in {dt:.1f}s ->", img)

        # ---- open image ----
        if re.match(r"^https?://", img, re.I):
            webbrowser.open(img)
        else:  # local file
            if sys.platform.startswith("win"):
                os.startfile(img)                # type: ignore[attr-defined]
            else:
                webbrowser.open(f"file://{img}")

    finally:
        # always shut down to free port/ram
        stop_local_server()
