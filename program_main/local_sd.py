# -------------------------------------------------
# local_sd.py —— 本地 Stable-Diffusion 统一调用
# -------------------------------------------------
"""
功能：
1. start_server()  ─ 启动 Automatic1111 WebUI（若已在运行会自动跳过）
2. shutdown_server() ─ 通过 REST 或 kill 端口方式优雅关停
3. generate_image(prompt, n=1, size="768x768", …) ─ 调 /sdapi/v1/txt2img
   · 签名与 image.py / model_lab.py 保持一致，方便前端统一调用
"""

import os, re, json, subprocess, time, requests, psutil, shutil, sys
from pathlib import Path

# —— 修改为你的 WebUI 目录（与 serve_local_sd.py 相同）———————
ROOT = Path(__file__).resolve().parent / "stable-diffusion-webui"
HOST = os.getenv("LOCAL_SD_HOST", "http://127.0.0.1:7860")
PORT = int(HOST.split(":")[-1])

# ------------- 1. 启动 / 检测 ---------------------
def _server_running() -> bool:
    try:
        requests.get(f"{HOST}/sdapi/v1/sd-models", timeout=2)
        return True
    except requests.exceptions.RequestException:
        return False

_proc: subprocess.Popen | None = None    # 全局进程句柄

def start_server(model_path: str | None = None):
    global _proc
    if _server_running():
        return  # 已运行
    if not ROOT.exists():
        raise RuntimeError(f"WebUI dir not found: {ROOT}")
    cmd = [sys.executable, "launch.py",
           "--api", "--listen", "--port", str(PORT),
           "--precision", "full", "--no-half", "--skip-torch-cuda-test"]
    if model_path:
        cmd += ["--ckpt", model_path]
    # 如有 GPU，可自动检测并追加 --xformers
    if _detect_cuda():
        cmd += ["--xformers", "--medvram"]
    _proc = subprocess.Popen(cmd, cwd=ROOT)
    _wait_ready()

def _wait_ready(timeout: int = 90):
    for _ in range(timeout):
        if _server_running():
            print(f"🚀 Local SD ready on {HOST}")
            return
        time.sleep(1)
    raise TimeoutError("WebUI failed to start within timeout")

def _detect_cuda() -> bool:
    return shutil.which("nvidia-smi") is not None

# ------------- 2. 生成图片 ------------------------
def generate_image(
    prompt: str,
    n: int = 1,
    size: str = "768x768",
    *,
    negative_prompt: str = "",
    steps: int = 28,
    sampler_name: str = "DPM++ 2M Karras",
    seed: int | None = None,
) -> list[str]:
    """
    与 model_lab.generate_image 同签名：
    prompt, n, size, negative_prompt, seed
    返回:list[str] 本地保存 PNG 路径
    """
    start_server()   # 确保服务器已启动
    w, h = _parse_size(size)
    payload = {
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "width": w, "height": h,
        "steps": steps,
        "sampler_name": sampler_name,
        "batch_size": n,
        "n_iter": 1,
        "seed": seed,
        "save_images": False,
    }
    r = requests.post(f"{HOST}/sdapi/v1/txt2img", json=payload, timeout=300)
    r.raise_for_status()
    images_b64: list[str] = r.json()["images"]
    paths = _save_images(images_b64)
    return paths

def _parse_size(sz: str) -> tuple[int, int]:
    m = re.match(r"\s*(\d+)[xX](\d+)\s*$", sz)
    if not m:
        raise ValueError('size 应写成 "宽x高"，如 "768x1024"')
    return int(m.group(1)), int(m.group(2))

def _save_images(b64_list: list[str]) -> list[str]:
    import base64, datetime
    out_dir = Path("outputs")
    out_dir.mkdir(exist_ok=True)
    paths = []
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    for i, b in enumerate(b64_list):
        p = out_dir / f"local_{ts}_{i}.png"
        p.write_bytes(base64.b64decode(b))
        paths.append(str(p.resolve()))
    return paths

# ------------- 3. 关停服务器 ----------------------
def shutdown_server():
    # 先尝试官方 API（v1.6+）
    try:
        requests.post(f"{HOST}/shutdown", timeout=2)
    except requests.exceptions.RequestException:
        pass
    time.sleep(3)
    # 若端口仍被占用 -> 强杀
    for p in psutil.process_iter(["pid", "connections"]):
        for c in p.info["connections"]:
            if c.laddr and c.laddr.port == PORT:
                p.kill()

# -------------------------------------------------
if __name__ == "__main__":
    demo = "(masterpiece), pink hair girl in flower meadow, anime style"
    imgs = generate_image(demo, n=1, size="512x768",
                          negative_prompt="lowres, blurry")
    print("Saved:", imgs[0])
