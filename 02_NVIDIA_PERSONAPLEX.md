# NVIDIA PersonaPlex Research

## Overview
**PersonaPlex** is NVIDIA's real-time, full-duplex speech-to-speech conversational model that enables persona control through text prompts and voice conditioning. Released January 15, 2026.

## Key Features
- **Full Duplex**: Listens and speaks simultaneously
- **7 Billion Parameters**: Based on Moshi architecture
- **Voice Cloning**: Condition on voice samples for target vocal characteristics
- **Role Prompting**: Text prompts define persona, role, and context
- **Natural Dynamics**: Supports interruptions, backchannels, overlaps, rapid turn-taking
- **Commercial Ready**: NVIDIA Open Model License

## Architecture
- Based on **Moshi** architecture from Kyutai
- **Mimi Speech Encoder**: ConvNet + Transformer (audio → tokens)
- **Temporal + Depth Transformers**: Process conversation
- **Mimi Speech Decoder**: Transformer + ConvNet (tokens → speech)
- **24kHz audio** sample rate
- Backbone: **Helium** LLM for semantic understanding

## Hardware Requirements
- **NVIDIA Ampere (A100)** or **Hopper (H100)** GPUs
- Significant VRAM (7B parameters)
- Linux OS recommended
- CPU offload available for lower VRAM setups

## Installation
```bash
# Install Opus codec
# Ubuntu/Debian
sudo apt install libopus-dev

# macOS
brew install opus

# Clone and install
git clone https://github.com/NVIDIA/personaplex
cd personaplex
pip install moshi/.

# Set HuggingFace token
export HF_TOKEN=<YOUR_TOKEN>
```

## Usage

### Web Server (Live Interaction)
```bash
SSL_DIR=$(mktemp -d)
python -m moshi.server --ssl "$SSL_DIR"
# Access at https://localhost:8998
```

### Offline Processing
```bash
python -m moshi.offline \
  --voice-prompt "NATF2.pt" \
  --input-wav "input.wav" \
  --seed 42424242 \
  --output-wav "output.wav" \
  --output-text "output.json"
```

## Pre-packaged Voices
### Natural (Conversational)
| Female | Male |
|--------|------|
| NATF0, NATF1, NATF2, NATF3 | NATM0, NATM1, NATM2, NATM3 |

### Variety (Diverse)
| Female | Male |
|--------|------|
| VARF0-VARF4 | VARM0-VARM4 |

## Prompting Examples

### Assistant Role
```
You are a wise and friendly teacher. Answer questions or provide advice in a clear and engaging way.
```

### Customer Service
```
You work for Jerusalem Shakshuka which is a restaurant and your name is Owen Foster. Information: There are two shakshuka options: Classic (poached eggs, $9.50) and Spicy (scrambled eggs with jalapenos, $10.25).
```

### Casual Conversation
```
You enjoy having a good conversation. Have a reflective conversation about career changes and feeling of home.
```

## Benchmarks (FullDuplexBench)
| Metric | PersonaPlex | vs Others |
|--------|-------------|-----------|
| Smooth Turn Taking | 90.8% | Best |
| User Interruption | 95.0% | Best |
| Response Latency | 170ms | Fastest |
| Interruption Latency | 240ms | Fastest |
| Task Adherence (GPT-4o) | 4.29/5 | Best |

## 🚀 How to Run PersonaPlex

### Option 1: Google Colab (Easiest to Try)
Official notebook available:
```
https://colab.research.google.com/#fileId=https://huggingface.co/nvidia/personaplex-7b-v1.ipynb
```
⚠️ Free Colab has T4 GPUs (16GB) - may be insufficient. **Colab Pro+** ($50/month) has A100 access.

### Option 2: Cloud GPU Rental (Best for Development)
Rent an A100 80GB for ~$1-2/hour:

| Provider | GPU | Price/hr | Link |
|----------|-----|----------|------|
| RunPod | A100 80GB | ~$1.99 | [runpod.io](https://runpod.io) |
| Vast.ai | A100 80GB | ~$1.50 | [vast.ai](https://vast.ai) |
| Lambda Labs | A100 | ~$1.10 | [lambdalabs.com](https://lambdalabs.com) |

### Option 3: HuggingFace Inference Endpoints
Deploy your own A100 endpoint via HuggingFace - good for production, but expensive for always-on.

### Option 4: Local (If You Have Hardware)
Requires NVIDIA A100 or H100 GPU. See [Installation](#installation) section above.

## Links
- HuggingFace: https://huggingface.co/nvidia/personaplex-7b-v1
- GitHub: https://github.com/NVIDIA/personaplex
- Project Page: https://research.nvidia.com/labs/adlr/personaplex/
- Paper: https://research.nvidia.com/labs/adlr/files/personaplex/personaplex_preprint.pdf
- **Colab Notebook**: https://colab.research.google.com/#fileId=https://huggingface.co/nvidia/personaplex-7b-v1.ipynb

## License
- Code: MIT License
- Weights: NVIDIA Open Model License
- Base (Moshi): CC-BY-4.0

---
*Research compiled: January 29, 2026*
