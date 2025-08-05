#!/usr/bin/env bash
# install_sd_auto.sh — Install Automatic1111 (GPU if available, otherwise CPU)
# Target: Python 3.10 + A1111 repo + Torch + pinned deps + SD-1.5 model

set -euo pipefail

ENV="easy_art"
PY="3.10"
SD_REPO="https://github.com/AUTOMATIC1111/stable-diffusion-webui.git"
SD_DIR="stable-diffusion-webui"
MODEL_URL="https://huggingface.co/runwayml/stable-diffusion-v1-5/resolve/main/v1-5-pruned-emaonly.safetensors"
MODEL_NAME="v1-5-pruned.safetensors"

echo "==> 1) Create/activate conda env: $ENV (Python $PY)"
if ! command -v conda >/dev/null 2>&1; then
  echo "ERROR: conda not found. Please install Miniconda/Anaconda first." >&2
  exit 1
fi
source "$(conda info --base)/etc/profile.d/conda.sh"
conda env list | grep -q "^$ENV " || conda create -y -n "$ENV" python=$PY
conda activate "$ENV"

echo "==> 2) Clone A1111 repo (if missing)"
if [[ ! -d "$SD_DIR/.git" ]]; then
  git clone --depth 1 "$SD_REPO" "$SD_DIR"
else
  echo "   - Repo exists; skip clone."
fi

echo "==> 3) Decide Torch build (GPU / CPU)"
GPU_WHL_INDEX=""
if command -v nvidia-smi >/dev/null 2>&1; then
  CUDA_VER=$(nvidia-smi | grep -o "CUDA Version: [0-9.]*" | awk '{print $3}' || echo "")
  if [[ "$CUDA_VER" =~ ^12\. ]]; then
    GPU_WHL_INDEX="https://download.pytorch.org/whl/cu121"
    echo "   - Detected CUDA $CUDA_VER → using cu121 wheels."
  elif [[ "$CUDA_VER" =~ ^11\. ]]; then
    GPU_WHL_INDEX="https://download.pytorch.org/whl/cu118"
    echo "   - Detected CUDA $CUDA_VER → using cu118 wheels."
  else
    echo "   - Unknown CUDA version ($CUDA_VER). Falling back to CPU."
  fi
else
  echo "   - nvidia-smi not found → CPU install."
fi

echo "==> 4) Install PyTorch"
python - <<'PY'
import sys, platform
print("Python:", sys.version)
print("Platform:", platform.platform())
PY

pip install -U pip

if [[ -n "$GPU_WHL_INDEX" ]]; then
  # Pinned minor versions known to work broadly; adjust if needed
  pip install --index-url "$GPU_WHL_INDEX" torch==2.2.2 torchvision==0.17.2 torchaudio==2.2.2 || {
    echo "   - GPU wheel failed; falling back to CPU wheels."
    pip install --index-url https://download.pytorch.org/whl/cpu torch torchvision torchaudio
  }
else
  pip install --index-url https://download.pytorch.org/whl/cpu torch torchvision torchaudio
fi

echo "==> 5) Install pinned deps (reduce Windows/macOS build issues)"
pip install numpy==1.26.4 scipy==1.11.4 pandas==1.5.3 \
            matplotlib==3.7.2 kiwisolver==1.4.5 orjson==3.9.10 \
            fastapi gradio==3.41.2 uvicorn pillow==9.5.0 tqdm \
            transformers==4.39.3 diffusers==0.27.2 accelerate==0.27.2 \
            pyyaml addict safetensors==0.4.2 requests psutil python-dotenv

# Optional: xformers
if [[ -n "$GPU_WHL_INDEX" ]]; then
  echo "==> 6) (Optional) Install xformers for speed"
  pip install xformers || echo "   - xformers install skipped."
fi

echo "==> 7) Download default SD-1.5 checkpoint"
mkdir -p "$SD_DIR/models/Stable-diffusion"
if [[ ! -f "$SD_DIR/models/Stable-diffusion/$MODEL_NAME" ]]; then
  curl -L "$MODEL_URL" -o "$SD_DIR/models/Stable-diffusion/$MODEL_NAME"
else
  echo "   - Model exists; skip download."
fi

cat <<'TXT'
✅ Installation complete!

Next steps:
  1) conda activate easy_art
  2) python program_main/serve_local_sd.py --port 7860
  3) python program_main/backend_main.py   # smoke test; follow CLI prompt

Notes:
- GPU detected → WebUI auto-starts with xformers/half (if available).
- No GPU → CPU-only (slower, but works).
TXT
