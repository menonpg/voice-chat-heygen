# KittenTTS Research

## Overview
**KittenTTS** is an open-source, state-of-the-art text-to-speech model with **only 15 million parameters** (~25MB), designed for lightweight deployment and high-quality voice synthesis.

## Key Features
- **Ultra-lightweight**: Under 25MB model size
- **No GPU Required**: Works on CPU
- **High Quality**: State-of-the-art synthesis for its size class
- **Multiple Voices**: 8 built-in voice options
- **24kHz Output**: High-quality audio sampling rate

## Installation
```bash
pip install https://github.com/KittenML/KittenTTS/releases/download/0.1/kittentts-0.1.0-py3-none-any.whl
```

## Quick Start
```python
from kittentts import KittenTTS
import soundfile as sf

# Initialize model
m = KittenTTS("KittenML/kitten-tts-nano-0.2")

# Generate speech
audio = m.generate(
    "This high quality TTS model works without a GPU",
    voice='expr-voice-2-f'
)

# Save the audio
sf.write('output.wav', audio, 24000)
```

## Available Voices
| Voice ID | Description |
|----------|-------------|
| `expr-voice-2-m` | Expressive Male Voice 2 |
| `expr-voice-2-f` | Expressive Female Voice 2 |
| `expr-voice-3-m` | Expressive Male Voice 3 |
| `expr-voice-3-f` | Expressive Female Voice 3 |
| `expr-voice-4-m` | Expressive Male Voice 4 |
| `expr-voice-4-f` | Expressive Female Voice 4 |
| `expr-voice-5-m` | Expressive Male Voice 5 |
| `expr-voice-5-f` | Expressive Female Voice 5 |

## Use Cases
- **Edge Devices**: IoT, embedded systems, mobile apps
- **Offline Applications**: No internet required
- **Low-latency TTS**: Quick synthesis on limited hardware
- **Privacy-focused Apps**: All processing stays local

## Dependencies
- `soundfile` - For audio file I/O
- `numpy` - Numerical operations

## Source
- GitHub: https://github.com/0xSojalSec/KittenTTS-25MB
- Original: https://github.com/KittenML/KittenTTS

---
*Research compiled: January 29, 2026*
