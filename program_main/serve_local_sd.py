#!/usr/bin/env python
"""
自动检测 GPU 并启动 Automatic1111 WebUI（带 --api）。
- GPU 可用 ➜ xformers / half precision / 高速
- GPU 不可用 ➜ CPU-only 模式 (--precision full --no-half --skip-torch-cuda-test)

用法:
    python serve_local_sd.py [--port 7860] [--model-path /your/model.safetensors]
"""
import argparse, shutil, subprocess, sys, os, pathlib, time
import torch  

ROOT = pathlib.Path(__file__).resolve().parent / "stable-diffusion-webui"

def detect_cuda() -> bool:
    return torch.cuda.is_available() and shutil.which("nvidia-smi") is not None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", default="7860")
    ap.add_argument("--model-path", default="")
    args = ap.parse_args()

    if not ROOT.exists():
        print("找不到 stable-diffusion-webui 目录，请先 git clone。")
        sys.exit(1)

    cmd = [sys.executable, "launch.py", "--api", "--listen", "--port", args.port]

    if detect_cuda():
        print("✅ 检测到 GPU，可用 CUDA。以 xformers 半精度启动...")
        cmd += ["--xformers", "--medvram"]
    else:
        print("⚠️ 未检测到 GPU，将以 CPU only 模式启动（速度较慢）...")
        cmd += ["--precision", "full", "--no-half", "--skip-torch-cuda-test"]

    # 附加模型路径
    if args.model_path:
        cmd += ["--ckpt", args.model_path]

    # 启动
    print("▶ 启动命令：", " ".join(cmd))
    subprocess.Popen(cmd, cwd=ROOT)

    # 简单心跳检测
    host = f"http://127.0.0.1:{args.port}"
    import requests, time
    for _ in range(30):
        try:
            requests.get(f"{host}/sdapi/v1/sd-models", timeout=3)
            print(f"🚀 WebUI 已就绪 {host}")
            break
        except Exception:
            time.sleep(2)
    else:
        print("⏰ WebUI 启动超时，请检查日志窗口。")

if __name__ == "__main__":
    main()
