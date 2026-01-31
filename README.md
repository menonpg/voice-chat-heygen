# VOICE - Speech Technology Research & Demos

This folder contains research and **working demos** for various speech technologies.

## 📚 Research Documents

| File | Description |
|------|-------------|
| `01_KITTEN_TTS_RESEARCH.md` | KittenTTS - Ultra-lightweight TTS (<25MB) - *research only* |
| `02_NVIDIA_PERSONAPLEX_RESEARCH.md` | NVIDIA PersonaPlex - Full-duplex conversational AI |
| `03_WEB_SPEECH_API_RESEARCH.md` | Browser-native Speech Recognition & Synthesis |

## 🚀 Working Demos

### ✅ Option 1: Web Speech API (Zero Setup) - TESTED
Works entirely in-browser, no installation needed.

```bash
open web_speech_demo.html
```
Features: Speech-to-text + Text-to-speech in browser

### ✅ Option 2: Piper TTS (Fast Local Neural TTS) - RECOMMENDED
Fast, offline neural TTS that works on Mac/Linux/Windows.

```bash
source ~/miniconda3/bin/activate voice
pip install piper-tts pytz
python piper_tts_app.py
```
Then open http://localhost:7861

### ✅ Option 3: macOS TTS (Built-in Voices)
Uses macOS `say` command - zero downloads.

```bash
source ~/miniconda3/bin/activate voice
python tts_app.py
```
Then open http://localhost:7860

### ⚠️ PersonaPlex (Requires NVIDIA A100/H100)
Full-duplex conversational AI - **cannot run on MacBook**.
See `personaplex_notes.md` for details if you have the hardware.

### ⚠️ KittenTTS
The package referenced in research may not be publicly available yet.
Use **Piper TTS** as a working alternative.

## 📁 Files

```
VOICE/
├── README.md                         # This file
├── requirements.txt                  # Python dependencies
│
├── 📄 Research
├── 01_KITTEN_TTS_RESEARCH.md        # KittenTTS research
├── 02_NVIDIA_PERSONAPLEX_RESEARCH.md # PersonaPlex research
├── 03_WEB_SPEECH_API_RESEARCH.md    # Web Speech API research
├── personaplex_notes.md             # PersonaPlex setup notes
│
├── 🎯 Working Demos
├── web_speech_demo.html             # ✅ Browser STT/TTS (zero setup)
├── piper_tts_app.py                 # ✅ Piper neural TTS (fast, local)
└── tts_app.py                       # ✅ macOS built-in TTS
```

## 🎯 Comparison

| Feature | Piper TTS | Web Speech API | PersonaPlex |
|---------|-----------|----------------|-------------|
| **Type** | TTS only | STT + TTS | Full conversation |
| **Size** | ~30MB/voice | Built-in | ~14GB |
| **GPU** | No | No | Yes (A100/H100) |
| **Offline** | Yes | Partial | Yes |
| **Setup** | pip install | Zero | Complex |
| **Quality** | Excellent | Good | Excellent |
| **Mac Support** | ✅ | ✅ | ❌ |

## 🔗 Links

- Piper TTS: https://github.com/rhasspy/piper
- PersonaPlex: https://github.com/NVIDIA/personaplex
- Web Speech API: https://developer.mozilla.org/en-US/docs/Web/API/Web_Speech_API

---
*Created: January 29, 2026*
