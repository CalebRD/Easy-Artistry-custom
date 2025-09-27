# -------------------------------------------------
# local_sd.py — unified local Stable-Diffusion caller
# -------------------------------------------------
"""
Features
1. start_server()       start Automatic1111 WebUI (skips if already running)
2. shutdown_server()    stop WebUI via REST / port-kill
3. generate_image()     call /sdapi/v1/txt2img  (no longer changes model)

Checkpoint selection is now handled **outside** this module via:
    start_local_server(model_name)  or  switch_local_model(model_name)

Default presets are tuned for SD-1.5 on CPU; SD-XL works but will be slower.
"""

import os, re, subprocess, time, requests, psutil, shutil, sys, webbrowser
from pathlib import Path
_PRESETS: dict[str, dict] = {
    "fast": {
        "steps": 20,
        "sampler_name": "Euler a",
        "cfg_scale": 6.5,
        "enable_hr": False,
    },
    "balanced": {
        "steps": 24,
        "sampler_name": "DPM++ 2M",
        "cfg_scale": 7.0,
        "enable_hr": False,
    },
    "high": {
        "steps": 36,
        "sampler_name": "DPM++ SDE Karras",
        "cfg_scale": 7.5,
        "enable_hr": True,
<<<<<<< HEAD
        "hr_scale": 1.6,
        "hr_second_pass_steps": 14,
        "denoising_strength": 0.35,
=======
        "hr_scale": 1.8,
        "hr_second_pass_steps": 14,
        "denoising_strength": 0.4,
>>>>>>> origin/ai
        "hr_upscaler": "R-ESRGAN 4x+",
    },
}
# ───────────── paths & server conf ──────────────
ROOT = Path(__file__).resolve().parent / "stable-diffusion-webui"
HOST = os.getenv("LOCAL_SD_HOST", "http://127.0.0.1:7860")
PORT = int(HOST.split(":")[-1])

# ---------- 1. start / detect -------------------
def _server_running() -> bool:
    """Return True if /sdapi endpoint responds."""
    try:
        requests.get(f"{HOST}/sdapi/v1/sd-models", timeout=2)
        return True
    except requests.exceptions.RequestException:
        return False

_proc: subprocess.Popen | None = None       # global handle

<<<<<<< HEAD
def start_server(model_path: str | None = None, *, no_half_vae: bool = True):
    """Launch WebUI aiming for max GPU utilization on 10GB+ cards (e.g., RTX 4070 12GB)."""
    import torch
    global _proc

=======
def start_server(model_path: str | None = None):
    """Launch WebUI if not already running."""
    global _proc
>>>>>>> origin/ai
    if _server_running():
        return
    if not ROOT.exists():
        raise RuntimeError(f"WebUI dir not found: {ROOT}")

<<<<<<< HEAD
    cmd = [sys.executable, "launch.py", "--api", "--listen", "--port", str(PORT)]
    if model_path:
        cmd += ["--ckpt", model_path]

    # Detect CUDA & VRAM
    use_cuda, vram_bytes, device_name = False, 0, "CPU"
    try:
        if torch.cuda.is_available():
            use_cuda = True
            props = torch.cuda.get_device_properties(0)
            vram_bytes = int(getattr(props, "total_memory", 0))
            device_name = props.name
    except Exception:
        use_cuda = False

    gb = vram_bytes / (1024 ** 3) if vram_bytes else 0
    print(f"[WebUI] Detected device: {device_name} | VRAM: {gb:.2f} GB | CUDA: {use_cuda}")

    if use_cuda:
        # 激进：吃满 12GB，不用 medvram；开 xformers+SDP；channels_last 提升带宽利用率
        cmd += ["--xformers", "--opt-sdp-attention", "--opt-channelslast"]
        if no_half_vae:
            cmd += ["--no-half-vae"]   # 画质更稳（VAE 用 fp32），显存+~1GB。若OOM可关掉
        # （不加 --precision full/--no-half，让主干网络跑 fp16，更快更省显存）
        if vram_bytes < 10 * 1024**3:
            # 小显卡兜底
            cmd += ["--medvram"]
    else:
        # CPU 路线：维持你原本的安全参数
        cmd += ["--precision", "full", "--no-half", "--skip-torch-cuda-test"]

    _proc = subprocess.Popen(cmd, cwd=ROOT)
    print("Launching WebUI with:", " ".join(cmd))
    _wait_ready()



def _wait_ready(timeout: int = 120):
=======
    cmd = [sys.executable, "launch.py",
           "--api", "--listen", "--port", str(PORT),
           "--precision", "full", "--no-half", "--skip-torch-cuda-test"]
    if model_path:
        cmd += ["--ckpt", model_path]
    if _detect_cuda():
        cmd += ["--xformers", "--medvram"]

    _proc = subprocess.Popen(cmd, cwd=ROOT)
    _wait_ready()

def _wait_ready(timeout: int = 90):
>>>>>>> origin/ai
    """Block until WebUI is responsive or timeout."""
    for _ in range(timeout):
        if _server_running():
            print(f"🚀 Local SD ready on {HOST}")
            return
        time.sleep(1)
    raise TimeoutError("WebUI failed to start within timeout")

def _detect_cuda() -> bool:
<<<<<<< HEAD
    try:
        import torch
        return torch.cuda.is_available()
    except Exception:
        import shutil
        return shutil.which("nvidia-smi") is not None

=======
    """Simple check for NVIDIA GPU via nvidia-smi."""
    return shutil.which("nvidia-smi") is not None
>>>>>>> origin/ai

# ---------- 2. txt2img -------------------------- 
def generate_image(
    prompt: str,
    n: int = 1,
<<<<<<< HEAD
    size: str = "512x512",
=======
    size: str = "768x768",
>>>>>>> origin/ai
    *,
    negative_prompt: str = "",
    quality: str = "balanced",                 # preset key: fast / balanced / high
    steps: int | None = None,                  # override: sampling steps
    sampler_name: str | None = None,           # override: sampler
    cfg_scale: float | None = None,            # override: CFG scale
    seed: int | None = None,                   # override: random seed
    # —— fine-tuning options (per-call overrides, do NOT change presets) ——
    enable_hr: bool | None = None,
    hr_scale: float | None = None,
    hr_upscaler: str | None = None,
    denoising_strength: float | None = None,
    hr_second_pass_steps: int | None = None,
) -> list[str]:
    """
    Generate images via local Stable Diffusion WebUI API.

    Behavior:
    - Selects a baseline configuration from one of the fixed presets
      ("fast", "balanced", "high").
    - Call-time arguments (steps, sampler_name, cfg_scale, seed, etc.)
      can override preset values, but do not modify the presets themselves.
    - High-resolution options (enable_hr, hr_scale, etc.) follow the same rule:
      per-call overrides > preset values > default values.
    - Returns a list of file paths pointing to locally saved PNG images.
    """
    start_server()                          # ensure the WebUI server is running
    w, h = _parse_size(size)

    # ---------- get baseline from immutable presets ----------
    base = _PRESETS.get(quality.lower(), _PRESETS["balanced"])

    # basic parameters: caller overrides > preset
    eff_steps = steps if steps is not None else base.get("steps")
    eff_sampler = sampler_name if sampler_name is not None else base.get("sampler_name")
    eff_cfg = cfg_scale if cfg_scale is not None else base.get("cfg_scale")

    # high-resolution parameters: caller overrides > preset > defaults
    eff_enable_hr = enable_hr if enable_hr is not None else base.get("enable_hr", False)
    eff_hr_scale = hr_scale if hr_scale is not None else base.get("hr_scale", 1.5)
    eff_hr_upscaler = hr_upscaler if hr_upscaler is not None else base.get("hr_upscaler", "R-ESRGAN 4x+")
    eff_denoise = denoising_strength if denoising_strength is not None else base.get("denoising_strength", 0.4)
    eff_hr_steps = hr_second_pass_steps if hr_second_pass_steps is not None else base.get("hr_second_pass_steps", 12)

    payload = {
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "width": w,
        "height": h,
        "steps": eff_steps,
        "sampler_name": eff_sampler,
        "cfg_scale": eff_cfg,
        "batch_size": n,
        "n_iter": 1,
        "seed": seed,
        "save_images": False,
    }

    if eff_enable_hr:
        payload.update({
            "enable_hr": True,
            "hr_scale": eff_hr_scale,
            "hr_upscaler": eff_hr_upscaler,
            "denoising_strength": eff_denoise,
            "hr_second_pass_steps": eff_hr_steps,
        })

    # ---- retry loop: handle 404 if API not yet ready ----
    for _ in range(5):
        r = requests.post(f"{HOST}/sdapi/v1/txt2img", json=payload, timeout=600)
        if r.status_code == 404:            # API not ready yet
            time.sleep(1)
            continue
        r.raise_for_status()
        images_b64 = r.json()["images"]
        return _save_images(images_b64)

    raise RuntimeError("txt2img API unavailable after retries")


# ---------- helpers -----------------------------
def _parse_size(sz: str) -> tuple[int, int]:
    m = re.match(r"\s*(\d+)[xX](\d+)\s*$", sz)
    if not m:
        raise ValueError('size must be "WxH", e.g. "768x1024"')
    return int(m.group(1)), int(m.group(2))

def _save_images(b64_list: list[str]) -> list[str]:
    """Decode base64 strings → PNG files under ./outputs/"""
    import base64, datetime
    out_dir = Path("outputs")
    out_dir.mkdir(exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    paths = []
    for i, b in enumerate(b64_list):
        p = out_dir / f"local_{ts}_{i}.png"
        p.write_bytes(base64.b64decode(b))
        paths.append(str(p.resolve()))
    return paths

# ---------- 3. shutdown -------------------------
def shutdown_server():
    """Try REST /shutdown first; if still alive, kill by port."""
    try:
        requests.post(f"{HOST}/shutdown", timeout=2)
    except requests.exceptions.RequestException:
        pass
    time.sleep(3)
    for p in psutil.process_iter(["pid", "connections"]):
        for c in p.info["connections"]:
            if c.laddr and c.laddr.port == PORT:
                p.kill()

# ---------- helper: hot-swap checkpoint ----------
def _switch_model(model_name: str, timeout: int = 90):
    """Internal helper to change checkpoint (used by backend_main)."""
    requests.post(f"{HOST}/sdapi/v1/options",
                  json={"sd_model_checkpoint": model_name},
                  timeout=10)
    for _ in range(timeout):
        p = requests.get(f"{HOST}/sdapi/v1/progress?skip_current_image=true", timeout=10).json()
        if not p.get("state", {}).get("job_count", 0):
            return
        time.sleep(1)
    raise TimeoutError(f"Loading model '{model_name}' timed out")

# -------------------------------------------------
if __name__ == "__main__":
    demo = "(masterpiece), pink hair girl in flower meadow, anime style"
    imgs = generate_image(
        demo, n=1, size="512x768", negative_prompt="lowres, blurry")
    if imgs:
        path = imgs[0]
        print("Saved:", path)
        if sys.platform.startswith("win"):
            os.startfile(path)               # type: ignore[attr-defined]
        else:
            webbrowser.open(f"file://{path}")
