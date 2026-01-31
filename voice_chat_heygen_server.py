#!/usr/bin/env python3
"""
Voice Chat Server with HeyGen Avatar Integration
- Web Speech API for STT (browser)
- Azure OpenAI GPT for conversation  
- HeyGen Streaming Avatar for video response
- Optional: KittenTTS fallback

Setup:
    1. Create .env file with your Azure and HeyGen credentials (see below)
    2. pip install fastapi uvicorn httpx python-dotenv
    3. python voice_chat_heygen_server.py
    4. Open http://localhost:8001
"""

import os
import base64
import time
import glob
from pathlib import Path
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import httpx
import uvicorn

# Load .env file
from dotenv import load_dotenv
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
    print(f"✅ Loaded .env from {env_path}")
else:
    print(f"⚠️  No .env file found at {env_path}")
    print("   Create one with your Azure OpenAI and HeyGen credentials")

# Create cache directory for audio files
CACHE_DIR = Path(__file__).parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)

def cleanup_cache(max_age_seconds=3600):
    """Remove cached audio files older than max_age_seconds."""
    now = time.time()
    for f in glob.glob(str(CACHE_DIR / "*.wav")):
        if now - os.path.getmtime(f) > max_age_seconds:
            try:
                os.unlink(f)
            except:
                pass

# Azure OpenAI config
AZURE_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT", "")
AZURE_KEY = os.environ.get("AZURE_OPENAI_KEY", "")
AZURE_DEPLOYMENT = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4")
AZURE_API_VERSION = os.environ.get("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")

# HeyGen config
HEYGEN_API_KEY = os.environ.get("HEYGEN_API_KEY", "sk_V2_hgu_kf1EmwApleX_wEqDWoNGw9N8RmrSAbEXorNRvCdKIgvx")

# Brave Search API (for web lookups)
BRAVE_API_KEY = os.environ.get("BRAVE_API_KEY", "")

print(f"Azure Endpoint: {AZURE_ENDPOINT[:50]}..." if AZURE_ENDPOINT else "❌ AZURE_OPENAI_ENDPOINT not set")
print(f"Azure Deployment: {AZURE_DEPLOYMENT}")
print(f"HeyGen API: {'✅ Configured' if HEYGEN_API_KEY else '❌ Not configured'}")
print(f"Brave Search: {'✅ Configured' if BRAVE_API_KEY else '❌ Not configured'}")

# Keywords that suggest user wants web search
SEARCH_TRIGGERS = [
    "look up", "search", "google", "find out", "what is", "who is", "when did",
    "current", "latest", "recent", "news", "price", "weather",
    "look online", "check online", "can you find", "do you know about",
    "internet", "online", "browse", "website", "tell me about", "explain what",
    "how does", "where can", "define"
]

async def brave_search(query: str, num_results: int = 5):
    """Search the web using Brave Search API.
    Returns: (text_for_llm, list_of_results_for_ui)
    """
    if not BRAVE_API_KEY:
        return "", []
    
    url = "https://api.search.brave.com/res/v1/web/search"
    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": BRAVE_API_KEY
    }
    params = {
        "q": query,
        "count": num_results
    }
    
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            response = await client.get(url, headers=headers, params=params)
            if response.status_code == 200:
                data = response.json()
                text_results = []
                ui_results = []
                for item in data.get("web", {}).get("results", [])[:num_results]:
                    title = item.get("title", "")
                    description = item.get("description", "")
                    url = item.get("url", "")
                    text_results.append(f"- {title}: {description}")
                    ui_results.append({
                        "title": title,
                        "description": description,
                        "url": url
                    })
                return "\n".join(text_results), ui_results
        except Exception as e:
            print(f"Brave Search error: {e}")
    return "", []

def needs_search(message: str) -> bool:
    """Check if message seems to need web search."""
    message_lower = message.lower()
    return any(trigger in message_lower for trigger in SEARCH_TRIGGERS)

# Try to load KittenTTS (fallback option)
try:
    from kittentts import KittenTTS
    import soundfile as sf
    import numpy as np
    print("Loading KittenTTS model...")
    KITTEN_MODEL = KittenTTS("KittenML/kitten-tts-nano-0.2")
    KITTEN_AVAILABLE = True
    print("✅ KittenTTS loaded (available as fallback)")
except Exception as e:
    KITTEN_AVAILABLE = False
    KITTEN_MODEL = None
    print(f"⚠️ KittenTTS not available: {e}")

app = FastAPI(title="Voice Chat with HeyGen")

# Conversation history
conversation_history = []

class ChatRequest(BaseModel):
    message: str

class TTSRequest(BaseModel):
    text: str
    voice: str = "expr-voice-2-f"
    speed: float = 1.0

class HeyGenSessionRequest(BaseModel):
    avatar_id: str
    voice_id: str

@app.post("/api/chat")
async def chat(request: ChatRequest):
    """Send message to Azure OpenAI and get response."""
    global conversation_history
    
    # Validate config
    if not AZURE_ENDPOINT or not AZURE_KEY:
        return {"error": "Azure OpenAI not configured. Create .env file with AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_KEY"}
    
    user_message = request.message
    search_context = ""
    search_results_for_ui = []  # For showing in UI
    
    # Check if we need to search the web
    if needs_search(user_message) and BRAVE_API_KEY:
        print(f"🔍 Searching web for: {user_message}")
        search_results, search_results_for_ui = await brave_search(user_message)
        if search_results:
            search_context = f"\n\n[Web Search Results]\n{search_results}\n\nUse these results to answer the user's question."
            print(f"Found {len(search_results_for_ui)} search results")
    
    # Add user message to history
    conversation_history.append({"role": "user", "content": user_message})
    
    # Keep last 20 messages
    if len(conversation_history) > 20:
        conversation_history = conversation_history[-20:]
    
    # Get current date/time
    now = datetime.now()
    current_datetime = now.strftime("%A, %B %d, %Y at %I:%M %p")
    
    # Prepare system prompt
    system_prompt = f"""You are a helpful voice assistant with web search capabilities. 

Current date and time: {current_datetime}

Keep responses concise and conversational - typically 1-3 sentences since they will be spoken aloud by an avatar. Be friendly, warm, and natural. Don't use markdown or special formatting.

If web search results are provided, use them to give accurate, up-to-date information. Summarize the key points naturally. You CAN access the internet through web search - if someone asks you to look something up, you can do it."""
    
    if search_context:
        system_prompt += search_context
    
    # Prepare messages
    messages = [
        {"role": "system", "content": system_prompt}
    ] + conversation_history
    
    # Call Azure OpenAI
    url = f"{AZURE_ENDPOINT}/openai/deployments/{AZURE_DEPLOYMENT}/chat/completions?api-version={AZURE_API_VERSION}"
    
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            response = await client.post(
                url,
                headers={
                    "api-key": AZURE_KEY,
                    "Content-Type": "application/json"
                },
                json={
                    "messages": messages,
                    "max_tokens": 200,
                    "temperature": 0.7
                }
            )
            
            if response.status_code != 200:
                error_detail = response.text
                print(f"Azure API Error: {response.status_code} - {error_detail}")
                return {"error": f"Azure API error ({response.status_code}): {error_detail[:200]}"}
            
            data = response.json()
            assistant_message = data["choices"][0]["message"]["content"]
            conversation_history.append({"role": "assistant", "content": assistant_message})
            
            return {
                "response": assistant_message,
                "sources": search_results_for_ui if search_results_for_ui else None
            }
            
        except httpx.TimeoutException:
            return {"error": "Request timed out. Please try again."}
        except Exception as e:
            print(f"Error: {e}")
            return {"error": str(e)}

@app.post("/api/tts")
async def text_to_speech(request: TTSRequest):
    """Convert text to speech using KittenTTS (fallback)."""
    print(f"🎙️ TTS Request: voice={request.voice}, speed={request.speed}, text={request.text[:50]}...")
    
    if not KITTEN_AVAILABLE:
        print("❌ KittenTTS not available")
        return {"error": "KittenTTS not available"}
    
    try:
        cleanup_cache()
        print("Generating audio with KittenTTS...")
        audio = KITTEN_MODEL.generate(request.text, voice=request.voice)
        
        output_path = CACHE_DIR / f"tts_{int(time.time() * 1000)}.wav"
        sf.write(str(output_path), audio, 24000)
        print(f"✅ Audio saved to {output_path}")
        
        with open(output_path, "rb") as audio_file:
            audio_base64 = base64.b64encode(audio_file.read()).decode()
        
        print(f"✅ Returning {len(audio_base64)} bytes of audio")
        return {"audio": audio_base64}
    except Exception as e:
        print(f"❌ TTS Error: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}

@app.post("/api/clear")
async def clear_history():
    global conversation_history
    conversation_history = []
    return {"status": "cleared"}

@app.get("/api/status")
async def status():
    return {
        "kitten_tts": KITTEN_AVAILABLE,
        "azure_configured": bool(AZURE_ENDPOINT and AZURE_KEY),
        "azure_endpoint": AZURE_ENDPOINT[:30] + "..." if AZURE_ENDPOINT else None,
        "azure_deployment": AZURE_DEPLOYMENT,
        "heygen_configured": bool(HEYGEN_API_KEY),
        "brave_search": bool(BRAVE_API_KEY),
        "history_length": len(conversation_history)
    }

@app.get("/api/heygen/key")
async def get_heygen_key():
    """Get HeyGen API key for client-side use."""
    return {"api_key": HEYGEN_API_KEY}

@app.post("/api/heygen/cleanup")
async def cleanup_heygen_sessions():
    """Stop all active HeyGen streaming sessions."""
    if not HEYGEN_API_KEY:
        return {"error": "HeyGen API key not configured", "stopped": 0}
    
    stopped = 0
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            # List active sessions
            list_resp = await client.get(
                "https://api.heygen.com/v1/streaming.list",
                headers={"X-Api-Key": HEYGEN_API_KEY}
            )
            data = list_resp.json()
            sessions = data.get("data", {}).get("sessions", [])
            
            # Stop each session
            for session in sessions:
                sid = session.get("session_id")
                if sid:
                    await client.post(
                        "https://api.heygen.com/v1/streaming.stop",
                        headers={"X-Api-Key": HEYGEN_API_KEY, "Content-Type": "application/json"},
                        json={"session_id": sid}
                    )
                    stopped += 1
                    print(f"Stopped session: {sid}")
            
            return {"status": "ok", "stopped": stopped, "message": f"Stopped {stopped} session(s)"}
    except Exception as e:
        return {"error": str(e), "stopped": stopped}

@app.get("/", response_class=HTMLResponse)
async def index():
    return HTML_CONTENT

HTML_CONTENT = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Voice Chat with HeyGen Avatar</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            color: white;
            padding: 20px;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        h1 { text-align: center; margin-bottom: 10px; font-size: 32px; }
        .subtitle { text-align: center; color: #888; margin-bottom: 20px; font-size: 14px; }
        
        /* Two column layout */
        .main-content {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 20px;
        }
        
        @media (max-width: 900px) {
            .main-content {
                grid-template-columns: 1fr;
            }
        }
        
        /* Avatar section */
        .avatar-section {
            background: rgba(255,255,255,0.03);
            border-radius: 16px;
            padding: 20px;
            border: 1px solid rgba(255,255,255,0.1);
        }
        
        #avatar-container {
            width: 100%;
            height: 400px;
            background: #000;
            border-radius: 12px;
            margin-bottom: 15px;
            position: relative;
            overflow: hidden;
        }
        
        #avatar-video {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }
        
        .avatar-placeholder {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            text-align: center;
            color: #666;
        }
        
        .avatar-placeholder-icon {
            font-size: 64px;
            margin-bottom: 10px;
        }
        
        /* Config section */
        .config-section {
            background: rgba(255,255,255,0.05);
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 15px;
            font-size: 13px;
        }
        
        .config-section input, .config-section select {
            width: 100%;
            padding: 10px;
            margin: 5px 0;
            border: 1px solid rgba(255,255,255,0.2);
            border-radius: 6px;
            background: rgba(255,255,255,0.1);
            color: white;
            font-size: 13px;
            cursor: pointer;
        }
        
        .config-section select {
            appearance: none;
            background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' fill='white' viewBox='0 0 16 16'%3E%3Cpath d='M8 11L3 6h10l-5 5z'/%3E%3C/svg%3E");
            background-repeat: no-repeat;
            background-position: right 10px center;
            padding-right: 30px;
        }
        
        .config-section select option {
            background: #1a1a2e;
            color: white;
            padding: 8px;
        }
        
        .config-section select optgroup {
            background: #16213e;
            color: #90cdf4;
            font-weight: bold;
        }
        
        .config-section label {
            font-weight: 600;
            color: #aaa;
            display: block;
            margin-top: 8px;
        }
        
        /* Chat section */
        .chat-section {
            background: rgba(255,255,255,0.03);
            border-radius: 16px;
            padding: 20px;
            border: 1px solid rgba(255,255,255,0.1);
            display: flex;
            flex-direction: column;
        }
        
        .chat-box {
            background: rgba(0,0,0,0.2);
            border-radius: 12px;
            padding: 15px;
            height: 400px;
            overflow-y: auto;
            margin-bottom: 15px;
            border: 1px solid rgba(255,255,255,0.1);
        }
        
        .message {
            padding: 10px 14px;
            border-radius: 12px;
            margin-bottom: 10px;
            max-width: 85%;
            animation: slideIn 0.3s ease;
        }
        
        @keyframes slideIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .user { 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            margin-left: auto; 
            border-bottom-right-radius: 4px;
        }
        
        .assistant { 
            background: rgba(255,255,255,0.1);
            border-bottom-left-radius: 4px;
        }
        
        .message-label { 
            font-size: 10px; 
            opacity: 0.7; 
            margin-bottom: 4px; 
        }
        
        .error-msg {
            background: rgba(245, 101, 101, 0.2);
            border: 1px solid rgba(245, 101, 101, 0.5);
            color: #feb2b2;
            padding: 8px 12px;
            border-radius: 8px;
            margin-bottom: 10px;
            font-size: 13px;
        }
        
        /* Status indicator */
        .status-bar {
            padding: 12px 20px;
            margin: 15px 0;
            border-radius: 10px;
            background: rgba(66, 153, 225, 0.2);
            color: #90cdf4;
            text-align: center;
            font-weight: 500;
            font-size: 14px;
            border: 1px solid rgba(66, 153, 225, 0.3);
        }
        
        .status-bar.error {
            background: rgba(245, 101, 101, 0.2);
            color: #feb2b2;
            border-color: rgba(245, 101, 101, 0.3);
        }
        
        .status-bar.success {
            background: rgba(72, 187, 120, 0.2);
            color: #9ae6b4;
            border-color: rgba(72, 187, 120, 0.3);
        }
        
        .status-bar.warning {
            background: rgba(237, 137, 54, 0.2);
            color: #fbd38d;
            border-color: rgba(237, 137, 54, 0.3);
        }
        
        /* Controls */
        .controls {
            display: flex;
            gap: 10px;
            justify-content: center;
            flex-wrap: wrap;
            margin-bottom: 15px;
        }
        
        .btn {
            padding: 12px 24px;
            border: none;
            border-radius: 10px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        
        .btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        
        .btn-primary:hover:not(:disabled) { 
            transform: scale(1.05); 
            box-shadow: 0 5px 25px rgba(102, 126, 234, 0.4); 
        }
        
        .btn-voice {
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            color: white;
            font-size: 18px;
            padding: 16px 32px;
        }
        
        .btn-voice.recording {
            background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
            animation: pulse 1.5s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.05); }
        }
        
        .btn-danger { 
            background: linear-gradient(135deg, #f56565 0%, #ed64a6 100%);
            color: white;
        }
        
        .btn-secondary { 
            background: rgba(255,255,255,0.1); 
            color: white;
        }
        
        .btn-secondary:hover:not(:disabled) { background: rgba(255,255,255,0.2); }
        .btn:disabled { opacity: 0.5; cursor: not-allowed; transform: none !important; }
        
        /* Sources */
        .sources {
            margin-top: 8px;
            font-size: 11px;
        }
        
        .sources-toggle {
            color: #4299e1;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 4px;
        }
        
        .sources-toggle:hover { text-decoration: underline; }
        
        .sources-list {
            display: none;
            margin-top: 8px;
            padding: 8px;
            background: rgba(0,0,0,0.3);
            border-radius: 6px;
        }
        
        .sources-list.open { display: block; }
        
        .source-item {
            margin-bottom: 6px;
            padding-bottom: 6px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        
        .source-item:last-child { border-bottom: none; margin-bottom: 0; padding-bottom: 0; }
        
        .source-title {
            color: #4299e1;
            text-decoration: none;
            font-weight: 500;
            font-size: 11px;
        }
        
        .source-title:hover { text-decoration: underline; }
        
        .source-desc {
            color: #a0aec0;
            font-size: 10px;
            margin-top: 2px;
        }
        
        .transcript {
            background: rgba(255,255,255,0.05);
            border-radius: 8px;
            padding: 12px;
            margin-top: 10px;
            min-height: 50px;
        }
        
        .transcript-label {
            font-weight: 600;
            color: #aaa;
            margin-bottom: 6px;
            font-size: 12px;
        }
        
        .transcript-text {
            color: #ccc;
            font-size: 14px;
            line-height: 1.4;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎭 Voice Chat with HeyGen Avatar</h1>
        <p class="subtitle">Speak naturally • GPT-4 • Custom Avatar with your voice</p>
        
        <div id="globalStatus" class="status-bar">Configure your avatar settings and click Start Session</div>
        
        <div class="main-content">
            <!-- Left: Avatar -->
            <div class="avatar-section">
                <h3 style="margin-bottom: 12px;">🎥 Your Avatar</h3>
                
                <div class="config-section">
                    <label>Avatar:</label>
                    <select id="avatarId">
                        <optgroup label="👩 Women - Professional">
                            <option value="Marianne_ProfessionalLook_public">Marianne (Professional)</option>
                            <option value="Marianne_ProfessionalLook2_public">Marianne (Professional 2)</option>
                            <option value="Katya_ProfessionalLook_public">Katya (Professional)</option>
                            <option value="Katya_ProfessionalLook2_public">Katya (Professional 2)</option>
                            <option value="Alessandra_ProfessionalLook_public">Alessandra (Professional)</option>
                            <option value="Anastasia_ProfessionalLook_public">Anastasia (Professional)</option>
                            <option value="Amina_ProfessionalLook_public">Amina (Professional)</option>
                            <option value="Rika_ProfessionalLook_public">Rika (Professional)</option>
                        </optgroup>
                        <optgroup label="👩 Women - Casual/Sitting">
                            <option value="Marianne_CasualLook_public">Marianne (Casual)</option>
                            <option value="Marianne_Chair_Sitting_public">Marianne (Sitting)</option>
                            <option value="Katya_CasualLook_public">Katya (Casual)</option>
                            <option value="Katya_Chair_Sitting_public">Katya (Sitting)</option>
                            <option value="Alessandra_CasualLook_public">Alessandra (Casual)</option>
                            <option value="Alessandra_Chair_Sitting_public">Alessandra (Sitting)</option>
                        </optgroup>
                        <optgroup label="👨 Men - Professional">
                            <option value="Thaddeus_ProfessionalLook_public">Thaddeus (Professional)</option>
                            <option value="Thaddeus_ProfessionalLook2_public">Thaddeus (Professional 2)</option>
                            <option value="Pedro_ProfessionalLook_public">Pedro (Professional)</option>
                            <option value="Pedro_ProfessionalLook2_public">Pedro (Professional 2)</option>
                            <option value="Graham_ProfessionalLook_public">Graham (Professional)</option>
                            <option value="Anthony_ProfessionalLook_public">Anthony (Professional)</option>
                        </optgroup>
                        <optgroup label="👨 Men - Casual/Sitting">
                            <option value="Thaddeus_CasualLook_public">Thaddeus (Casual)</option>
                            <option value="Thaddeus_Chair_Sitting_public">Thaddeus (Sitting)</option>
                            <option value="Pedro_CasualLook_public">Pedro (Casual)</option>
                            <option value="Pedro_Chair_Sitting_public">Pedro (Sitting)</option>
                            <option value="Graham_CasualLook_public">Graham (Casual)</option>
                            <option value="Anthony_CasualLook_public">Anthony (Casual)</option>
                        </optgroup>
                    </select>
                    
                    <label>Voice:</label>
                    <select id="voiceId">
                        <optgroup label="👩 Female Voices">
                            <option value="2f72ee82b83d4b00af16c4771d611752">Jenny - Professional</option>
                            <option value="628161fd1c79432d853b610e84dbc7a4">Bella - Friendly</option>
                            <option value="1bd001e7e50f421d891986aad5158bc8">Sara - Cheerful</option>
                            <option value="6e7404e25c4b4385b04b0e2704c861c8">Michelle - Natural</option>
                            <option value="c2958d67f1e74403a0038e3445d93d50">Sherry - Friendly</option>
                            <option value="932643d355ed4a3d837370a3068bbd1b">Josie - Cheerful</option>
                            <option value="1fe966a9dfa14b16ab4d146fabe868b5">Ana - Cheerful</option>
                            <option value="456e13f3ff1345d3b7ab0435ce024dc7">Isabella - Cheerful</option>
                            <option value="2d5b0e6cf36f460aa7fc47e3eee4ba54">Sonia - Warm</option>
                            <option value="727e9d6d492e456b9f27708fa8018744">Clara - Professional</option>
                        </optgroup>
                        <optgroup label="👨 Male Voices">
                            <option value="1ae3be1e24894ccabdb4d8139399f721">Tony - Professional</option>
                            <option value="f5a3cb4edbfc4d37b5614ce118be7bc8">Ryan - Professional</option>
                            <option value="d7bbcdd6964c47bdaae26decade4a933">Christopher - Calm</option>
                            <option value="ec4aa6ac882147ffb679176d49f3e41f">Eric - Newscaster</option>
                            <option value="e17b99e1b86e47e8b7f4cae0f806aa78">Liam - Professional</option>
                            <option value="beaa640abaa24c32bea33b280d2f5ea3">Johan - Friendly</option>
                            <option value="ff465a8dab0d42c78f874a135b11d47d">Davis - Professional</option>
                            <option value="5dddee02307b4f49a17c123c120a60ca">Luke - Professional</option>
                        </optgroup>
                        <optgroup label="✨ Multilingual (Emotion Support)">
                            <option value="7682f3cff71a47abb2d6ae7ab3b339fd">Christine - Friendly ✨</option>
                            <option value="788cd5ac4afe4f88a88c86feafebf88e">Melissa - Soothing ✨</option>
                            <option value="5c1ade5e514c4c6c900b0ded224970fd">Theo - Friendly ✨</option>
                            <option value="5cb81a519c4845f2b3c3d12b9630e258">Paul - Friendly ✨</option>
                            <option value="2d432723a02444acb48e28ada714cc43">Rex - Friendly ✨</option>
                        </optgroup>
                    </select>
                </div>
                
                <div id="avatar-container">
                    <video id="avatar-video" autoplay playsinline></video>
                    <div class="avatar-placeholder" id="avatarPlaceholder">
                        <div class="avatar-placeholder-icon">🎭</div>
                        <div>Avatar will appear here</div>
                    </div>
                </div>
                
                <div class="controls">
                    <button id="startBtn" class="btn btn-primary" onclick="startSession()">🚀 Start Session</button>
                    <button id="stopBtn" class="btn btn-danger" disabled onclick="stopSession()">⏹️ Stop Session</button>
                    <button class="btn btn-secondary" onclick="cleanupSessions()" title="Clear all stuck HeyGen sessions">🧹 Cleanup</button>
                </div>
            </div>
            
            <!-- Right: Chat -->
            <div class="chat-section">
                <h3 style="margin-bottom: 12px;">💬 Conversation</h3>
                
                <div id="chatBox" class="chat-box"></div>
                
                <div class="controls">
                    <button id="voiceBtn" class="btn btn-voice" disabled onclick="toggleVoiceRecording()">🎤 Click & Speak</button>
                    <button class="btn btn-secondary" onclick="clearChat()">🗑️ Clear</button>
                </div>
                
                <div class="transcript">
                    <div class="transcript-label">You said:</div>
                    <div id="transcriptText" class="transcript-text">Your speech will appear here...</div>
                </div>
            </div>
        </div>
    </div>

    <script>
        // State
        let sessionId = null;
        let peerConnection = null;
        let recognition = null;
        let isRecording = false;
        let heygenApiKey = null;
        
        // DOM Elements
        const avatarIdInput = document.getElementById('avatarId');
        const voiceIdInput = document.getElementById('voiceId');
        const startBtn = document.getElementById('startBtn');
        const stopBtn = document.getElementById('stopBtn');
        const voiceBtn = document.getElementById('voiceBtn');
        const globalStatus = document.getElementById('globalStatus');
        const avatarVideo = document.getElementById('avatar-video');
        const avatarPlaceholder = document.getElementById('avatarPlaceholder');
        const transcriptText = document.getElementById('transcriptText');
        const chatBox = document.getElementById('chatBox');
        
        // Initialize Speech Recognition
        function initSpeechRecognition() {
            if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
                updateStatus('Speech recognition not supported in this browser. Use Chrome or Edge.', 'error');
                return false;
            }
            
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            recognition = new SpeechRecognition();
            recognition.continuous = false;
            recognition.interimResults = false;
            recognition.lang = 'en-US';
            
            recognition.onresult = async (event) => {
                const transcript = event.results[0][0].transcript;
                transcriptText.textContent = transcript;
                addMessage('user', transcript);
                updateStatus('🤔 Thinking...', 'warning');
                await handleUserMessage(transcript);
            };
            
            recognition.onerror = (event) => {
                console.error('Speech recognition error:', event.error);
                if (event.error !== 'no-speech' && event.error !== 'aborted') {
                    updateStatus('Speech recognition error: ' + event.error, 'error');
                }
                voiceBtn.classList.remove('recording');
                voiceBtn.innerHTML = '🎤 Click & Speak';
                isRecording = false;
            };
            
            recognition.onend = () => {
                voiceBtn.classList.remove('recording');
                voiceBtn.innerHTML = '🎤 Click & Speak';
                isRecording = false;
            };
            
            return true;
        }
        
        // Update status
        function updateStatus(message, type = 'info') {
            globalStatus.textContent = message;
            globalStatus.className = 'status-bar ' + type;
        }
        
        // Add message to chat
        function addMessage(role, text, sources = null) {
            const div = document.createElement('div');
            div.className = 'message ' + role;
            const label = role === 'user' ? '👤 You' : '🤖 Assistant';
            
            let html = `<div class="message-label">${label}</div>${text}`;
            
            if (sources && sources.length > 0) {
                const sourcesId = 'sources-' + Date.now();
                html += `
                    <div class="sources">
                        <div class="sources-toggle" onclick="toggleSources('${sourcesId}')">
                            📎 ${sources.length} sources <span id="${sourcesId}-arrow">▼</span>
                        </div>
                        <div id="${sourcesId}" class="sources-list">
                            ${sources.map(s => `
                                <div class="source-item">
                                    <a href="${s.url}" target="_blank" class="source-title">${s.title}</a>
                                    <div class="source-desc">${s.description}</div>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                `;
            }
            
            div.innerHTML = html;
            chatBox.appendChild(div);
            chatBox.scrollTop = chatBox.scrollHeight;
        }
        
        function toggleSources(id) {
            const list = document.getElementById(id);
            const arrow = document.getElementById(id + '-arrow');
            if (list.classList.contains('open')) {
                list.classList.remove('open');
                arrow.textContent = '▼';
            } else {
                list.classList.add('open');
                arrow.textContent = '▲';
            }
        }
        
        function showError(text) {
            const div = document.createElement('div');
            div.className = 'error-msg';
            div.textContent = '⚠️ ' + text;
            chatBox.appendChild(div);
            chatBox.scrollTop = chatBox.scrollHeight;
            updateStatus('Error occurred', 'error');
        }
        
        // Start HeyGen session
        async function startSession() {
            const avatarId = avatarIdInput.value.trim();
            const voiceId = voiceIdInput.value.trim();
            
            if (!avatarId || !voiceId) {
                updateStatus('Please fill in Avatar ID and Voice ID', 'error');
                return;
            }
            
            try {
                updateStatus('Loading HeyGen API key...');
                
                // Get API key from server
                const keyResponse = await fetch('/api/heygen/key');
                const keyData = await keyResponse.json();
                heygenApiKey = keyData.api_key;
                
                if (!heygenApiKey) {
                    throw new Error('HeyGen API key not configured on server');
                }
                
                updateStatus('Starting session with your custom avatar...');
                
                const response = await fetch('https://api.heygen.com/v1/streaming.new', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Api-Key': heygenApiKey
                    },
                    body: JSON.stringify({
                        avatar_id: avatarId,
                        voice: {
                            voice_id: voiceId
                        },
                        quality: 'high',
                        version: 'v2'
                    })
                });
                
                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.message || 'Failed to start session');
                }
                
                const data = await response.json();
                console.log('HeyGen response:', data);
                
                // Check for error codes
                if (data.code && data.code !== 100) {
                    throw new Error(data.message || `HeyGen error code: ${data.code}`);
                }
                
                if (data.data && data.data.session_id) {
                    sessionId = data.data.session_id;
                    console.log('Session ID:', sessionId);
                    await setupWebRTC(data.data);
                    
                    if (initSpeechRecognition()) {
                        updateStatus('✅ Ready! Click the microphone to speak', 'success');
                        startBtn.disabled = true;
                        stopBtn.disabled = false;
                        voiceBtn.disabled = false;
                        avatarPlaceholder.style.display = 'none';
                    }
                } else {
                    throw new Error('Invalid response from HeyGen API');
                }
            } catch (error) {
                updateStatus('Error: ' + error.message, 'error');
                console.error('Session error:', error);
            }
        }
        
        // Setup WebRTC
        async function setupWebRTC(sessionData) {
            console.log('sessionData:', sessionData);
            console.log('sessionData.sdp:', sessionData.sdp);
            
            // HeyGen returns sdp as {type, sdp} object, extract the actual SDP string
            const sdpData = sessionData.sdp;
            let serverSdp;
            
            if (typeof sdpData === 'string') {
                serverSdp = sdpData;
            } else if (sdpData && typeof sdpData === 'object' && sdpData.sdp) {
                serverSdp = sdpData.sdp;
            }
            
            console.log('Extracted serverSdp:', serverSdp ? serverSdp.substring(0, 100) : 'null');
            
            const iceServers = sessionData.ice_servers2;
            
            if (!serverSdp) {
                console.error('SDP extraction failed. sdpData was:', sdpData);
                throw new Error('No SDP received from HeyGen - check console for details');
            }
            
            peerConnection = new RTCPeerConnection({
                iceServers: iceServers || [
                    { urls: 'stun:stun.l.google.com:19302' }
                ]
            });
            
            peerConnection.ontrack = (event) => {
                if (event.streams && event.streams[0]) {
                    avatarVideo.srcObject = event.streams[0];
                    avatarPlaceholder.style.display = 'none';
                }
            };
            
            peerConnection.oniceconnectionstatechange = () => {
                console.log('ICE connection state:', peerConnection.iceConnectionState);
            };
            
            // Set remote description
            await peerConnection.setRemoteDescription(
                new RTCSessionDescription({ type: 'offer', sdp: serverSdp })
            );
            
            // Create answer
            const answer = await peerConnection.createAnswer();
            await peerConnection.setLocalDescription(answer);
            
            // Send answer to HeyGen
            await fetch('https://api.heygen.com/v1/streaming.start', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Api-Key': heygenApiKey
                },
                body: JSON.stringify({
                    session_id: sessionId,
                    sdp: answer.sdp
                })
            });
        }
        
        // Handle user message
        async function handleUserMessage(text) {
            try {
                // Get response from Azure OpenAI
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: text })
                });
                
                const data = await response.json();
                
                if (data.error) {
                    showError(data.error);
                    updateStatus('Ready for next message', 'success');
                    return;
                }
                
                addMessage('assistant', data.response, data.sources);
                
                // Send to HeyGen avatar
                await sendTextToAvatar(data.response);
                
            } catch (error) {
                console.error('Error:', error);
                showError('Connection error: ' + error.message);
                updateStatus('Ready for next message', 'success');
            }
        }
        
        // Send text to HeyGen avatar
        async function sendTextToAvatar(text) {
            if (!sessionId || !text) return;
            
            try {
                updateStatus('🗣️ Avatar is speaking...', 'success');
                
                const response = await fetch('https://api.heygen.com/v1/streaming.task', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Api-Key': heygenApiKey
                    },
                    body: JSON.stringify({
                        session_id: sessionId,
                        text: text,
                        task_type: 'talk'
                    })
                });
                
                if (!response.ok) {
                    throw new Error('Failed to send message to avatar');
                }
                
                // Wait a bit for avatar to finish
                setTimeout(() => {
                    updateStatus('✅ Ready! Click the microphone to speak', 'success');
                    transcriptText.textContent = 'Click the microphone to speak...';
                }, 3000);
            } catch (error) {
                updateStatus('Error: ' + error.message, 'error');
                console.error(error);
            }
        }
        
        // Toggle voice recording
        function toggleVoiceRecording() {
            if (!recognition) return;
            
            if (isRecording) {
                recognition.stop();
            } else {
                isRecording = true;
                voiceBtn.classList.add('recording');
                voiceBtn.innerHTML = '🔴 Listening...';
                updateStatus('🎤 Listening... Speak now!', 'success');
                recognition.start();
            }
        }
        
        // Stop session
        async function stopSession() {
            try {
                if (sessionId) {
                    await fetch('https://api.heygen.com/v1/streaming.stop', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-Api-Key': heygenApiKey
                        },
                        body: JSON.stringify({ session_id: sessionId })
                    });
                }
                
                if (peerConnection) {
                    peerConnection.close();
                    peerConnection = null;
                }
                
                if (recognition && isRecording) {
                    recognition.stop();
                }
                
                sessionId = null;
                avatarVideo.srcObject = null;
                avatarPlaceholder.style.display = 'block';
                transcriptText.textContent = 'Your speech will appear here...';
                
                startBtn.disabled = false;
                stopBtn.disabled = true;
                voiceBtn.disabled = true;
                
                updateStatus('Session ended. Configure and start again.');
            } catch (error) {
                updateStatus('Error stopping session: ' + error.message, 'error');
                console.error(error);
            }
        }
        
        // Clear chat
        async function clearChat() {
            chatBox.innerHTML = '';
            await fetch('/api/clear', { method: 'POST' });
            updateStatus('Chat cleared', 'success');
        }
        
        // Cleanup stuck HeyGen sessions
        async function cleanupSessions() {
            updateStatus('🧹 Cleaning up stuck sessions...', 'warning');
            try {
                const response = await fetch('/api/heygen/cleanup', { method: 'POST' });
                const data = await response.json();
                if (data.error) {
                    updateStatus('Cleanup error: ' + data.error, 'error');
                } else {
                    updateStatus(`✅ Cleaned up ${data.stopped} session(s). Try Start Session again!`, 'success');
                }
            } catch (error) {
                updateStatus('Cleanup failed: ' + error.message, 'error');
            }
        }
        
        // Save/load config from localStorage
        avatarIdInput.addEventListener('change', () => {
            localStorage.setItem('heygen_avatar_id', avatarIdInput.value);
        });
        
        voiceIdInput.addEventListener('change', () => {
            localStorage.setItem('heygen_voice_id', voiceIdInput.value);
        });
        
        window.addEventListener('load', () => {
            // Load from localStorage only if previously saved and exists in dropdown
            const savedAvatar = localStorage.getItem('heygen_avatar_id');
            const savedVoice = localStorage.getItem('heygen_voice_id');
            if (savedAvatar && avatarIdInput.querySelector(`option[value="${savedAvatar}"]`)) {
                avatarIdInput.value = savedAvatar;
            }
            if (savedVoice && voiceIdInput.querySelector(`option[value="${savedVoice}"]`)) {
                voiceIdInput.value = savedVoice;
            }
            
            // Check server status
            fetch('/api/status').then(r => r.json()).then(data => {
                console.log('Server status:', data);
                if (!data.azure_configured) {
                    updateStatus('⚠️ Azure OpenAI not configured. Check server logs.', 'error');
                } else if (!data.heygen_configured) {
                    updateStatus('⚠️ HeyGen API key not configured. Check server logs.', 'error');
                }
            });
        });
        
        // CRITICAL: Clean up session on page close/refresh
        async function cleanupSession() {
            if (sessionId && heygenApiKey) {
                try {
                    // Use fetch with keepalive for reliable delivery during page unload
                    await fetch('https://api.heygen.com/v1/streaming.stop', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-Api-Key': heygenApiKey
                        },
                        body: JSON.stringify({ session_id: sessionId }),
                        keepalive: true  // Ensures request completes even if page closes
                    });
                    console.log('Session cleaned up:', sessionId);
                } catch (e) {
                    console.error('Cleanup failed:', e);
                }
            }
        }
        
        window.addEventListener('beforeunload', (event) => {
            cleanupSession();
        });
        
        // Also clean up if tab becomes hidden for a while (mobile)
        let hiddenTimeout = null;
        document.addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'hidden') {
                // Give 30 seconds before cleaning up (user might just be switching tabs)
                hiddenTimeout = setTimeout(cleanupSession, 30000);
            } else {
                // Tab is visible again, cancel cleanup
                if (hiddenTimeout) {
                    clearTimeout(hiddenTimeout);
                    hiddenTimeout = null;
                }
            }
        });
    </script>
</body>
</html>
'''

if __name__ == "__main__":
    import sys
    
    # Get port from environment (Railway sets this) or default to 8001
    port = int(os.environ.get("PORT", 8001))
    
    print("=" * 60)
    print("Voice Chat Server with HeyGen Avatar")
    print("=" * 60)
    print(f"KittenTTS: {'✅ Available (fallback)' if KITTEN_AVAILABLE else '❌ Not available'}")
    print(f"Azure: {'✅ Configured' if AZURE_ENDPOINT and AZURE_KEY else '❌ Not configured'}")
    print(f"HeyGen: {'✅ Configured' if HEYGEN_API_KEY else '❌ Not configured'}")
    print(f"Brave Search: {'✅ Configured' if BRAVE_API_KEY else '❌ Not configured'}")
    if not AZURE_ENDPOINT or not AZURE_KEY:
        print("\n⚠️  Set environment variables:")
        print("   AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com")
        print("   AZURE_OPENAI_KEY=your-api-key")
        print("   AZURE_OPENAI_DEPLOYMENT=gpt-4")
    if not HEYGEN_API_KEY:
        print("   HEYGEN_API_KEY=your-heygen-api-key")
    print()
    print(f"Starting server on port {port}")
    print("=" * 60)
    
    # Use 0.0.0.0 for production (Railway), 127.0.0.1 for local
    host = "0.0.0.0" if os.environ.get("RAILWAY_ENVIRONMENT") else "127.0.0.1"
    uvicorn.run(app, host=host, port=port)
