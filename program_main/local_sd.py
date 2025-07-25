# -------------------------------------------------
# local_sd.py — unified local Stable‑Diffusion caller
# -------------------------------------------------
"""
Features
1. start_server()       start Automatic1111 WebUI (skips if already running)
2. shutdown_server()    stop WebUI via REST / port‑kill
3. generate_image()     call /sdapi/v1/txt2img
   · signature matches image.py / model_lab.py so the front‑end can switch
     between cloud and local with one flag.
"""

import os, re, subprocess, time, requests, psutil, shutil, sys
from pathlib import Path

# adjust to your WebUI folder (same path as serve_local_sd.py)
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

_proc: subprocess.Popen | None = None      # global handle

def start_server(model_path: str | None = None):
    """Launch WebUI if not already running."""
    global _proc
    if _server_running():
        return
    if not ROOT.exists():
        raise RuntimeError(f"WebUI dir not found: {ROOT}")

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
    """Block until WebUI is responsive or timeout."""
    for _ in range(timeout):
        if _server_running():
            print(f"🚀 Local SD ready on {HOST}")
            return
        time.sleep(1)
    raise TimeoutError("WebUI failed to start within timeout")

def _detect_cuda() -> bool:
    """Simple check for NVIDIA GPU via nvidia‑smi."""
    return shutil.which("nvidia-smi") is not None

# ---------- 2. txt2img --------------------------

def generate_image(
    prompt: str,
    n: int = 1,
    size: str = "768x768",
    *,
    negative_prompt: str = "",
    quality: str = "balanced",           # <── 新增：画质预设
    steps: int | None = None,            # <── 允许手动覆盖（可选）
    sampler_name: str | None = None,
    cfg_scale: float | None = None,
    seed: int | None = None,
    model_name: str | None = None,       # <── 允许指定模型名称（可选）
) -> list[str]:
    """
    Same signature idea as model_lab.generate_image but with extra quality preset.
    Returns local PNG paths.
    """
    start_server()  # ensure server is running
    if model_name:
        _switch_model(model_name)    
    w, h = _parse_size(size)

    # ---------- choose defaults by quality ----------
    presets = {
        "fast": {
            "steps": 20,
            "sampler_name": "Euler a",
            "cfg_scale": 6.5,
            "enable_hr": False,
        },
        "balanced": {
            "steps": 28,
            "sampler_name": "DPM++ 2M Karras",
            "cfg_scale": 7.0,
            "enable_hr": True,
            "hr_scale": 1.5,
            "hr_second_pass_steps": 12,
            "denoising_strength": 0.35,
            "hr_upscaler": "R-ESRGAN 4x+",
        },
        "high": {
            "steps": 36,
            "sampler_name": "DPM++ SDE Karras",
            "cfg_scale": 7.5,
            "enable_hr": True,
            "hr_scale": 2.0,
            "hr_second_pass_steps": 16,
            "denoising_strength": 0.4,
            "hr_upscaler": "R-ESRGAN 4x+",
        },
    }
    q = presets.get(quality.lower(), presets["balanced"])

    steps = steps or q["steps"]
    sampler_name = sampler_name or q["sampler_name"]
    cfg_scale = cfg_scale or q["cfg_scale"]

    payload = {
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "width": w,
        "height": h,
        "steps": steps,
        "sampler_name": sampler_name,
        "cfg_scale": cfg_scale,
        "batch_size": n,
        "n_iter": 1,
        "seed": seed,
        "save_images": False,
    }

    # Hires.fix
    if q.get("enable_hr"):
        payload.update({
            "enable_hr": True,
            "hr_scale": q["hr_scale"],
            "hr_upscaler": q["hr_upscaler"],
            "denoising_strength": q["denoising_strength"],
            "hr_second_pass_steps": q["hr_second_pass_steps"],
        })

    r = requests.post(f"{HOST}/sdapi/v1/txt2img", json=payload, timeout=600)
    r.raise_for_status()
    images_b64: list[str] = r.json()["images"]
    return _save_images(images_b64)

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
# ---------- helper: hot‑swap checkpoint ----------
def _switch_model(model_name: str, timeout: int = 90):
    """
    Ask WebUI to load another checkpoint via /sdapi/v1/options.
    Will poll /sdapi/v1/progress until loading finishes or timeout.
    """
    # 1) tell WebUI to switch
    requests.post(f"{HOST}/sdapi/v1/options",
                  json={"sd_model_checkpoint": model_name},
                  timeout=10)
    # 2) wait until the model is really loaded
    for _ in range(timeout):
        p = requests.get(f"{HOST}/sdapi/v1/progress?skip_current_image=true", timeout=10).json()
        if not p.get("state", {}).get("job_count", 0):         # no pending jobs → done
            return
        time.sleep(1)
    raise TimeoutError(f"Loading model '{model_name}' timed out")

# -------------------------------------------------
if __name__ == "__main__":
    demo = "(masterpiece), pink hair girl in flower meadow, anime style"
    imgs = generate_image(demo, n=1, size="512x768",
                          negative_prompt="lowres, blurry")
    print("Saved:", imgs[0])
