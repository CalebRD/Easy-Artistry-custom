#!/usr/bin/env bash
# install_sd_cpu.sh ───────────────
# install Automatic1111 (CPU-only)

set -euo pipefail
ENV=easy_art_cpu
PY=3.10
SD_REPO="https://github.com/AUTOMATIC1111/stable-diffusion-webui.git"
SD_DIR="stable-diffusion-webui"
MODEL_URL="https://huggingface.co/runwayml/stable-diffusion-v1-5/resolve/main/v1-5-pruned-emaonly.safetensors"
MODEL_NAME="v1-5-pruned.safetensors"

echo "── 1. remove old conda environment $ENV (if exists)"
conda remove -n "$ENV" --all -y || true

echo "── 2. build conda environment $ENV with Python $PY"
conda create -y -n "$ENV" python=$PY
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate "$ENV"

echo "── 3. clone WebUI"
git clone --depth 1 "$SD_REPO" "$SD_DIR"

echo "── 4. install dependencies (CPU-only)"
pip install -U pip
pip install torch==2.2.0+cpu torchvision==0.17.0+cpu torchaudio==2.2.0+cpu \
  -f https://download.pytorch.org/whl/torch_stable.html

# dependency versions are fixed to avoid compatibility issues
pip install numpy==1.26.4 scipy==1.11.4 pandas==1.5.3 \
  matplotlib==3.7.2 kiwisolver==1.4.5 orjson==3.9.10 \
  fastapi gradio==3.41.2 uvicorn pillow==9.5.0 tqdm \
  transformers==4.39.3 diffusers==0.27.2 accelerate==0.27.2 \
  pyyaml addict safetensors==0.4.2

echo "── 5. download Stable Diffusion model"
mkdir -p "$SD_DIR/models/Stable-diffusion"
curl -L "$MODEL_URL" -o "$SD_DIR/models/Stable-diffusion/$MODEL_NAME"

echo "── 6. copy config files"
if [[ ! -f $SD_DIR/../serve_local_sd.py ]]; then
  cat > "$SD_DIR/../serve_local_sd.py" <<'PY'

PY
fi

echo "✅ installation complete!"
echo "   1) conda activate $ENV"
echo "   2) python serve_local_sd.py --port 7860"
echo "   open http://localhost:7860 in your browser"
