# Voice Chat with HeyGen Avatar

A real-time voice chat application featuring a lip-synced AI avatar.

## Features

- 🎤 **Voice Input** - Web Speech API (browser-native STT)
- 🧠 **AI Responses** - Azure OpenAI GPT
- 🎭 **Talking Avatar** - HeyGen Streaming Avatar with lip-sync
- 🔍 **Web Search** - Brave Search API for real-time info

## How It Works

1. You speak into your microphone
2. Browser converts speech to text
3. Azure OpenAI generates a response
4. HeyGen avatar speaks the response with realistic lip-sync

## Deployment

### Railway (Recommended)

1. Fork this repo
2. Create a new project on [railway.app](https://railway.app)
3. Connect your GitHub repo
4. Add environment variables (see below)
5. Deploy!

### Environment Variables

```
AZURE_OPENAI_ENDPOINT=your-azure-endpoint
AZURE_OPENAI_KEY=your-azure-key
AZURE_OPENAI_DEPLOYMENT=gpt-4
AZURE_OPENAI_API_VERSION=2024-02-15-preview
HEYGEN_API_KEY=your-heygen-key
BRAVE_API_KEY=your-brave-key (optional)
```

### Local Development

```bash
pip install -r requirements.txt
cp .env.example .env  # Edit with your keys
python voice_chat_heygen_server.py
# Open http://localhost:8001
```

## Tech Stack

- **Backend**: FastAPI + Uvicorn
- **Frontend**: Vanilla JS + Web Speech API
- **AI**: Azure OpenAI
- **Avatar**: HeyGen Streaming Avatar (WebRTC)
- **Search**: Brave Search API
