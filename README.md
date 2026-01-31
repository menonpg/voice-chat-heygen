# 🎭 Voice Chat with HeyGen Avatar

A real-time conversational AI with a lip-synced video avatar. Speak naturally and watch the avatar respond!

![Demo](https://img.shields.io/badge/Demo-Live-green) ![Python](https://img.shields.io/badge/Python-3.9+-blue) ![License](https://img.shields.io/badge/License-MIT-yellow)

## ✨ Features

- **🎤 Voice Input** — Speak naturally using your microphone (Web Speech API)
- **🧠 AI Responses** — Powered by Azure OpenAI GPT
- **🎭 Talking Avatar** — Real-time lip-synced video via HeyGen Streaming
- **🔍 Web Search** — Optional Brave Search for real-time information
- **💬 Conversation Memory** — Maintains context across the chat

## 🔄 How It Works

```
You speak → Browser STT → Azure OpenAI → HeyGen Avatar speaks back
```

1. Your voice is captured and converted to text (browser-native)
2. Text is sent to Azure OpenAI for an AI response
3. Response is sent to HeyGen's Streaming Avatar API
4. Avatar speaks with realistic lip-sync via WebRTC

## 🚀 Quick Deploy (Railway)

1. Fork this repository
2. Create a project on [railway.app](https://railway.app)
3. Connect your GitHub repo
4. Add environment variables:

| Variable | Description |
|----------|-------------|
| `AZURE_OPENAI_ENDPOINT` | Your Azure OpenAI endpoint URL |
| `AZURE_OPENAI_KEY` | Your Azure OpenAI API key |
| `AZURE_OPENAI_DEPLOYMENT` | Deployment name (e.g., `gpt-4`, `gpt-5-chat`) |
| `HEYGEN_API_KEY` | Your HeyGen API key |
| `BRAVE_API_KEY` | *(Optional)* Brave Search API key |

5. Deploy! Railway will give you a public URL.

## 💻 Local Development

```bash
# Clone the repo
git clone https://github.com/menonpg/voice-chat-heygen.git
cd voice-chat-heygen

# Install dependencies
pip install -r requirements.txt

# Create .env file with your API keys
cat > .env << EOF
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_KEY=your-key
AZURE_OPENAI_DEPLOYMENT=gpt-5-chat
HEYGEN_API_KEY=your-heygen-key
BRAVE_API_KEY=your-brave-key
EOF

# Run the server
python voice_chat_heygen_server.py

# Open http://localhost:8001
```

## 🎭 Available Avatars

The app includes a curated selection of HeyGen's streaming avatars:

**Women:** Marianne, Katya, Alessandra, Anastasia, Amina, Rika  
**Men:** Thaddeus, Pedro, Graham, Anthony

Each available in Professional, Casual, and Sitting poses.

## 🛠 Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | FastAPI + Uvicorn |
| Frontend | Vanilla JS |
| Speech-to-Text | Web Speech API (browser) |
| AI | Azure OpenAI |
| Avatar | HeyGen Streaming (WebRTC) |
| Search | Brave Search API |

## 📋 Requirements

- Python 3.9+
- Modern browser (Chrome/Edge recommended for Web Speech API)
- HeyGen account with Streaming Avatar access
- Azure OpenAI account

## 📄 License

MIT License - feel free to use and modify!

---

Built with ❤️ using [HeyGen](https://heygen.com) and [Azure OpenAI](https://azure.microsoft.com/en-us/products/ai-services/openai-service)
