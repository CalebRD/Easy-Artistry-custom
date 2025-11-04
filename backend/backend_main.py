# -*- coding: utf-8 -*-
"""
backend_main.py   chat → prompt, local-server lifecycle, unified image generation
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
#DELL3 api DO NOT NEED TO CALL THIS FUNCTION,just call generate_image_from_prompt
def chat_generate_prompt(user_input: str, provider: str) -> Dict[str, Any]:
    user_input = user_input.strip()
    if not user_input:
        raise ValueError("user_input cannot be empty")
    tags = extract_tags(user_input, provider)
    return {"tags": tags, "prompt": tags_to_prompt(tags)}

# ======================================================================
# 2) local server lifecycle
# ======================================================================
_local_up = False
_default_checkpoint = "sd_xl_base_1.0.safetensors"

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
        # Get user description and convert into SD-style prompt
        print("description:")
        
        user_text = input("> ").strip()
        data = chat_generate_prompt(user_text, provider="openai")
        print("\nPrompt:", data["prompt"])
        
        # Launch local WebUI with a given checkpoint (example: anime XL)
        start_local_server("sd_xl_base_1.0.safetensors")
        
        # Choose preset: fast / balanced / high
        chosen_preset = "high"

        # Optional per-call overrides (sd_overrides)
        # These keys can override preset values for this single call.
        # If a key is not provided, the value from the chosen preset is used.

        
        sd_overrides = {
            # ----- Core generation parameters -----
            # "steps": 28,                # Number of denoising steps.
                                        # Higher → more detail, slower. Typical 18–40.
            # "sampler_name": "Euler a",  # Sampler algorithm.
                                        # Examples: "Euler a", "DPM++ 2M", "DPM++ SDE Karras".
            # "cfg_scale": 7.5,           # Classifier-Free Guidance scale.
                                        # Higher → stronger prompt adherence, but risk of oversaturation.
                                        # Common range: 6.5–8.
            # "seed": 123456,             # Random seed. Fix for reproducibility.
                                        # Use None or -1 for random.

            # ----- High-resolution (second-pass) options -----
            # "enable_hr": True,          # Enable high-res fix (runs a second pass).
                                        # Improves detail, increases runtime.
            # "hr_scale": 1.6,            # Upscaling factor for the second pass (1.3–2.0 typical).
            # "hr_upscaler": "R-ESRGAN 4x+",  # Upscaler algorithm used in second pass.
            # "denoising_strength": 0.35, # Strength of re-denoising in the second pass (0–1).
                                        # Lower preserves more original structure, higher redraws more.
            # "hr_second_pass_steps": 12  # Number of steps used in the second pass.
        }
        sd_overrides = {
                        "steps": 26,
                        "sampler_name": "DPM++ 3M SDE",       # 3M series produces finer details
                        "cfg_scale": 6.8,
                        "enable_hr": True,
                        "hr_scale": 1.6,
                        "hr_upscaler": "R-ESRGAN 4x+ Anime6B",
                        "denoising_strength": 0.30,
                        "hr_second_pass_steps": 14
                    }
        positive_prompt="""1girl, solo, silver hair, blue eyes, school uniform, beige blazer, white shirt, red ribbon bow,
                        black pleated skirt, thighhighs, sitting on classroom chair, hand touching ear, gentle blush,
                        classroom interior, window side lighting, soft sunlight, depth of field, clean lineart,
                        detailed hair, sharp focus, anime style, masterpiece, best quality, high detail, absurdres
                        """
        negative_prompt="""(worst quality, low quality, normal quality, lowres, low details, oversaturated, undersaturated, overexposed, underexposed, grainy, blurry, bad anatomy, bad hands, missing fingers, extra digit, fewer digits, cropped:1.4), jpeg artifacts, signature, watermark, username, artist name, text, error, extra limbs, missing arms, missing legs, extra arms, extra legs, malformed limbs, fused fingers, too many fingers, long neck, bad body, bad proportions, gross proportions, text, error, missing fingers, missing limbs, extra limbs, extra fingers
                        """                    
        # Generate image
        urls = generate_image_from_prompt(
            #data["prompt"],
            positive_prompt,
            size="640x896",
            model="local",
            n=1,
            preset=chosen_preset,
            sd_params=sd_overrides,
            negative_prompt=negative_prompt
        )

        img = urls[0]
        print("Saved:", img)

        # Open result
        if img.startswith("http"):
            webbrowser.open(img)
        elif sys.platform.startswith("win"):
            os.startfile(img)  # type: ignore[attr-defined]
        else:
            webbrowser.open(f"file://{img}")

    finally:
        # Graceful shutdown
        stop_local_server()

