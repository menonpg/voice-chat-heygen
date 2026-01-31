# PersonaPlex Setup Notes

## ⚠️ Important: Hardware Requirements

PersonaPlex is a **7 billion parameter** model that requires:
- **NVIDIA A100 (80GB)** or **H100 GPU**
- Alternatively: `--cpu-offload` flag (much slower, needs `accelerate` package)
- **Linux** recommended (macOS/Windows may have issues)

**This is NOT a lightweight model like KittenTTS!**

## If You Have the Hardware

### 1. Install Dependencies
```bash
# Install Opus codec (macOS)
brew install opus

# Clone repo
git clone https://github.com/NVIDIA/personaplex
cd personaplex

# Install Python package
pip install moshi/.

# For CPU offload (if limited VRAM)
pip install accelerate
```

### 2. Set Up HuggingFace Access
1. Go to https://huggingface.co/nvidia/personaplex-7b-v1
2. Accept the license
3. Get your token from https://huggingface.co/settings/tokens
4. Export it:
```bash
export HF_TOKEN=your_token_here
```

### 3. Run the Server
```bash
# Create temp SSL certs and launch
SSL_DIR=$(mktemp -d)
python -m moshi.server --ssl "$SSL_DIR"

# With CPU offload for limited VRAM
python -m moshi.server --ssl "$SSL_DIR" --cpu-offload
```

### 4. Access Web UI
Open browser to: `https://localhost:8998`

## Alternative: Use NVIDIA's Demo
If you don't have the hardware, NVIDIA may have a hosted demo at:
https://research.nvidia.com/labs/adlr/personaplex/

## Offline Batch Processing
```bash
python -m moshi.offline \
    --voice-prompt "NATF2.pt" \
    --text-prompt "You are a helpful assistant." \
    --input-wav "input.wav" \
    --output-wav "output.wav"
```

---

**For lightweight TTS, use KittenTTS instead!** (See kitten_tts_app.py)
