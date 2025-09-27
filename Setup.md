# Setup

> Two ways to get the backend running.  
> **Recommended** – Automated script (GPU ⬅︎→ CPU auto-detect).  
> **Alternative** – Manual install for locked-down networks or custom tuning.

---

## 1) Automated install (recommended)

### 1.1 Create & activate the conda env

```bash
conda create -n easy_art python=3.10 -y
conda activate easy_art
```

### 1.2 Run the script

| Platform | Command | What the script does |
|----------|---------|----------------------|
| **Linux / macOS / WSL** | `bash setup_unix.sh` | • Detect GPU → install cu121/cu118 wheels, else CPU wheels  \n• Clone **Automatic1111** repo  \n• Install pinned deps  \n• Download default **SD-1.5** (`v1-5-pruned.safetensors`) |
| **Windows (PowerShell)** | `Set-ExecutionPolicy -Scope Process RemoteSigned; .\setup_windows.ps1` | Performs the same steps, CUDA-aware or CPU-only |

> Scripts live in the repo root (or `scripts/` if you moved them). Both scripts print ✅ **Done** and a “Next steps” block.

### 1.3 Launch & smoke-test

```bash
# Start local A1111 (GPU or CPU-only)
python program_main/serve_local_sd.py --port 7860

# Unified backend smoke test
python program_main/backend_main.py
# Enter a description; the generated image will open automatically.
```

---

## 2) Manual install (full control)

Follow this if scripts are blocked or you need different versions.

### 2.1 Base environment

```bash
conda create -n easy_art python=3.10 -y
conda activate easy_art
```

### 2.2 PyTorch — choose **one**

| Scenario | Command |
|----------|---------|
| **CUDA 12.x GPU** | `pip install --index-url https://download.pytorch.org/whl/cu121 torch==2.2.2 torchvision==0.17.2 torchaudio==2.2.2` |
| **CUDA 11.x GPU** | `pip install --index-url https://download.pytorch.org/whl/cu118 torch==2.2.2 torchvision==0.17.2 torchaudio==2.2.2` |
| **CPU-only** | `pip install --index-url https://download.pytorch.org/whl/cpu torch torchvision torchaudio` |

### 2.3 Pinned runtime dependencies

```bash
pip install numpy==1.26.4 scipy==1.11.4 pandas==1.5.3 \
            matplotlib==3.7.2 kiwisolver==1.4.5 orjson==3.9.10 \
            fastapi gradio==3.41.2 uvicorn pillow==9.5.0 tqdm \
            transformers==4.39.3 diffusers==0.27.2 accelerate==0.27.2 \
            pyyaml addict safetensors==0.4.2 requests psutil python-dotenv
# Optional GPU speed-up:
pip install xformers   # ignore if it fails on CPU
```

### 2.4 Clone Automatic1111 & place the model

```bash
git clone --depth 1 https://github.com/AUTOMATIC1111/stable-diffusion-webui.git
mkdir -p stable-diffusion-webui/models/Stable-diffusion
curl -L -o stable-diffusion-webui/models/Stable-diffusion/v1-5-pruned.safetensors \
  https://huggingface.co/runwayml/stable-diffusion-v1-5/resolve/main/v1-5-pruned-emaonly.safetensors
```

### 2.5 Run & verify

```bash
python program_main/serve_local_sd.py --port 7860
python program_main/backend_main.py
```
If you see **“WebUI is ready at http://127.0.0.1:7860”** and an image opens, the install succeeded.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `404 /sdapi/v1/txt2img` right after start | Normal — backend auto-retries; wait ~2s. |
| `ModuleNotFoundError: numpy._core...` | `pip install --force-reinstall numpy` |
| `cannot import name '_c_internal_utils' from matplotlib` | `pip install --force-reinstall matplotlib kiwisolver` |
| Torch “not compiled with CUDA” on a GPU box | Ensure the wheel matches CUDA (cu121/cu118); uninstall & reinstall torch/vision/audio. |
| Port 7860 stuck | `lsof -i:7860` (Linux) / `netstat -ano ^| find "7860"` (Windows) → kill PID, or run `kill_7860.py`. |

---

## Environment variables (`.env`)

```ini
LOCAL_SD_HOST=http://127.0.0.1:7860
MODELSLAB_API_KEY=xxxxxxxxxxxxxxxx   # only needed for cloud SD
```

---

## Minimal usage (backend)

```python
from backend_main import start_local_server, generate_image_from_prompt, stop_local_server

start_local_server()  # idempotent, loads default SD-1.5
urls = generate_image_from_prompt("cat astronaut, anime style", model="local")
print(urls[0])
stop_local_server()
```
