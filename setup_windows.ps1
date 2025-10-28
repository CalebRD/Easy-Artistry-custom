# setup_windows.ps1 — conda env + GPU/CPU Torch + A1111 + SD-1.5

$ErrorActionPreference = "Stop"
$envName = "easy_art"
$pyVer   = "3.10"
$sdRepo  = "https://github.com/AUTOMATIC1111/stable-diffusion-webui.git"
$sdDir   = "stable-diffusion-webui"
$modelUrl= "https://huggingface.co/runwayml/stable-diffusion-v1-5/resolve/main/v1-5-pruned-emaonly.safetensors"
$modelOut= "$sdDir\models\Stable-diffusion\v1-5-pruned.safetensors"

if (-not (Get-Command conda.exe -ErrorAction SilentlyContinue)) {
  Write-Error "conda not found. Install Miniconda/Anaconda first."
}

# create env
conda.exe env list | Select-String -Pattern "^\s*$envName\s" | Out-Null
if ($LASTEXITCODE -ne 0) { conda.exe create -n $envName python=$pyVer -y }

# Torch channel (GPU/CPU)
$hasNvidia = (Get-Command nvidia-smi -ErrorAction SilentlyContinue) -ne $null
$cuda = ""
if ($hasNvidia) {
  $cuda = (& nvidia-smi | Select-String "CUDA Version").ToString() -replace '.*:\s*',''
}

function PipInEnv([string]$args) {
  conda.exe run -n $envName python -m pip $args
}

# PyTorch
if ($cuda.StartsWith("12")) {
  PipInEnv "install --index-url https://download.pytorch.org/whl/cu121 torch==2.2.2 torchvision==0.17.2 torchaudio==2.2.2"
} elseif ($cuda.StartsWith("11")) {
  PipInEnv "install --index-url https://download.pytorch.org/whl/cu118 torch==2.2.2 torchvision==0.17.2 torchaudio==2.2.2"
} else {
  PipInEnv "install --index-url https://download.pytorch.org/whl/cpu torch torchvision torchaudio"
}

# Deps
PipInEnv "install -U pip"
PipInEnv "install numpy==1.26.4 scipy==1.11.4 pandas==1.5.3 matplotlib==3.7.2 kiwisolver==1.4.5 orjson==3.9.10"
PipInEnv "install fastapi gradio==3.41.2 uvicorn pillow==9.5.0 tqdm"
PipInEnv "install transformers==4.39.3 diffusers==0.27.2 accelerate==0.27.2"
PipInEnv "install pyyaml addict safetensors==0.4.2 requests psutil python-dotenv"

# xformers (optional)
if ($hasNvidia) {
  try { PipInEnv "install xformers" } catch { Write-Host "skip xformers" }
}

# Clone A1111
if (-not (Test-Path "$sdDir\.git")) {
  git clone --depth 1 $sdRepo $sdDir
}

# Download model
New-Item -ItemType Directory -Force "$sdDir\models\Stable-diffusion" | Out-Null
if (-not (Test-Path $modelOut)) {
  Invoke-WebRequest -Uri $modelUrl -OutFile $modelOut
}

Write-Host "✅ Done."
Write-Host "Next:"
Write-Host "  conda activate $envName"
Write-Host "  python backend\serve_local_sd.py --port 7860"
Write-Host "  python backend\backend_main.py"
