# -*- coding: utf-8 -*-
"""
backend_main.py  – chat → prompt, local-server lifecycle, unified image generation
"""

import os, sys, re, time, webbrowser
from typing import List, Dict, Any, Optional

# ---------- project modules ----------
from label import extract_tags, tags_to_prompt
from model_lab import generate_image as sd_generate           # cloud Stable Diffusion
from image import generate_image as dalle_generate            # DALL·E 3
from local_sd import generate_image as local_sd_generate      # local A1111 txt2img

# local server helpers
from local_sd import start_server as _start_server
from local_sd import shutdown_server as _shutdown_server
from local_sd import _switch_model                            # checkpoint hot-swap

# ======================================================================
# 1) chat → prompt
# ======================================================================
def chat_generate_prompt(user_input: str) -> Dict[str, Any]:
    user_input = user_input.strip()
    if not user_input:
        raise ValueError("user_input cannot be empty")
    tags = extract_tags(user_input)
    return {"tags": tags, "prompt": tags_to_prompt(tags)}

# ======================================================================
# 2) local server lifecycle
# ======================================================================
_local_up = False
_default_checkpoint = "v1-5-pruned.safetensors"

def start_local_server(model_name: Optional[str] = None):
    global _local_up
    if not _local_up:
        _start_server()
        _local_up = True
    _switch_model(model_name or _default_checkpoint)

def switch_local_model(model_name: str):
    if not _local_up:
        raise RuntimeError("Local server not running; call start_local_server() first.")
    _switch_model(model_name)

def stop_local_server():
    global _local_up
    if _local_up:
        _shutdown_server()
        _local_up = False

# ======================================================================
# 3) unified image generation
# ======================================================================
def generate_image_from_prompt(
    prompt: str,
    *,
    size: str = "1024x1024",
    model: str = "stable-diffusion",
    n: int = 1,
    negative_prompt: str = "bad quality",
    preset: str = "balanced",
    sd_params: Optional[Dict[str, Any]] = None,
) -> List[str]:
    """
    ------------------------------------------------------------------------
    Universal image-generation entry for the front-end
    ------------------------------------------------------------------------
    Parameters
    ----------
    prompt : str
        The positive prompt (what you want to see in the picture).

    size : str, default "1024x1024"
        Image resolution in the form "WIDTHxHEIGHT".
        WIDTH and HEIGHT must be multiples of 64 (e.g. "768x1024").

    model : str, default "stable-diffusion"
        Which back-end to use:
            • "local" / "local_sd" / "local_stable-diffusion"
                  → call the **local A1111 WebUI** running on port 7860  
            • "stable-diffusion" / "sd" / "sdxl"
                  → call the **cloud SD API** (model_lab.py)  
            • "dalle" / "dall-e" / "dalle3"
                  → call **OpenAI DALL·E 3**

    n : int, default 1  
        Number of images to generate (batch size).

    negative_prompt : str, default "bad quality"
        Negative prompt forwarded to the selected back-end.

    preset : str, default "balanced"
        Quick quality profile **(only for local SD)**:
            • "fast"       lowest latency  
            • "balanced"   speed / quality trade-off  
            • "high"       best detail, slowest  

    sd_params : dict | None
        **Extra overrides for local SD** (ignored by cloud & DALL·E).  
        Any key that the A1111 `/sdapi/v1/txt2img` endpoint accepts is valid.
        Common examples:

        ┌───────────────────────┬──────────────────────────┐
        │ key                   │ example/value            │
        ├───────────────────────┼──────────────────────────┤
        │ steps                 │ 28                       │
        │ sampler_name          │ "Euler a"                │
        │ cfg_scale             │ 6.5                      │
        │ seed                  │ 123456789                │
        │ enable_hr             │ True / False             │
        │ hr_scale              │ 1.5                      │
        │ hr_upscaler           │ "R-ESRGAN 4x+"           │
        │ denoising_strength    │ 0.35                     │
        └───────────────────────┴──────────────────────────┘

        The function first loads the chosen *preset*, then updates / adds every
        key in `sd_params` — so your dict **overrides** the preset.

    Returns
    -------
    List[str]
        • For **local SD**   absolute file paths (PNG) on the server machine  
          (add ``file:///`` prefix or serve via static route to display).  
        • For **cloud SD / DALL·E**  direct HTTPS image URLs.
    """

    if not re.match(r"^\d+x\d+$", size):
        raise ValueError('size must be like "1024x1024"')
    if sd_params and not isinstance(sd_params, dict):
        raise ValueError("sd_params must be a dict")

    m = model.lower().strip()

    if m in ("stable-diffusion", "sd", "sdxl"):
        return sd_generate(prompt=prompt, n=n, size=size,
                           negative_prompt=negative_prompt)

    if m in ("dalle", "dall-e", "dalle3"):
        return dalle_generate(prompt=prompt, n=n, size=size)

    if m in ("local_stable-diffusion", "local", "local_sd", "local_sdxl"):
        start_local_server()          # idempotent
        kwargs = dict(
            prompt=prompt,
            n=n,
            size=size,
            negative_prompt=negative_prompt,
            quality=preset.lower()
        )
        if sd_params:
            kwargs.update(sd_params)  # custom overrides
        return local_sd_generate(**kwargs)

    raise ValueError(f"unsupported model: {model}")

# ======================================================================
# 4) CLI demo
# ======================================================================
if __name__ == "__main__":
    try:
        print("description:")
        user_text = input("> ").strip()
        data = chat_generate_prompt(user_text)
        print("\nPrompt:", data["prompt"])

        start_local_server("toonyou_beta6XL.safetensors")  # demo: anime XL
        urls = generate_image_from_prompt(
            data["prompt"],
            size="768x768",
            model="local",
            n=1,
            preset="fast",                     # choose preset
            sd_params={"steps": 18}            # override example
        )
        img = urls[0]
        print("Saved:", img)

        # open
        if img.startswith("http"):
            webbrowser.open(img)
        elif sys.platform.startswith("win"):
            os.startfile(img)                 # type: ignore[attr-defined]
        else:
            webbrowser.open(f"file://{img}")

    finally:
        stop_local_server()
