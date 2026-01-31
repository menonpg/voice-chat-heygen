#!/usr/bin/env python3
"""
Voice Chat Server - Natural Conversational AI
- Web Speech API for STT (browser)
- Azure OpenAI GPT for conversation
- KittenTTS for TTS output

Setup:
    1. Create .env file with your Azure credentials (see below)
    2. pip install fastapi uvicorn httpx python-dotenv
    3. python voice_chat_server.py
    4. Open http://localhost:8000
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
    print("   Create one with your Azure OpenAI credentials")

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

# Brave Search API (for web lookups)
BRAVE_API_KEY = os.environ.get("BRAVE_API_KEY", "")

print(f"Azure Endpoint: {AZURE_ENDPOINT[:50]}..." if AZURE_ENDPOINT else "❌ AZURE_OPENAI_ENDPOINT not set")
print(f"Azure Deployment: {AZURE_DEPLOYMENT}")
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

# Try to load KittenTTS
try:
    from kittentts import KittenTTS
    import soundfile as sf
    import numpy as np
    print("Loading KittenTTS model...")
    KITTEN_MODEL = KittenTTS("KittenML/kitten-tts-nano-0.2")
    KITTEN_AVAILABLE = True
    print("✅ KittenTTS loaded")
except Exception as e:
    KITTEN_AVAILABLE = False
    KITTEN_MODEL = None
    print(f"⚠️ KittenTTS not available: {e}")

app = FastAPI(title="Voice Chat")

# Conversation history
conversation_history = []

class ChatRequest(BaseModel):
    message: str

class TTSRequest(BaseModel):
    text: str
    voice: str = "expr-voice-2-f"
    speed: float = 1.0

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

Keep responses concise and conversational - typically 1-3 sentences since they will be spoken aloud. Be friendly, warm, and natural. Don't use markdown or special formatting.

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
    """Convert text to speech using KittenTTS."""
    print(f"🎙️ TTS Request: voice={request.voice}, speed={request.speed}, text={request.text[:50]}...")
    
    if not KITTEN_AVAILABLE:
        print("❌ KittenTTS not available")
        return {"error": "KittenTTS not available"}
    
    try:
        cleanup_cache()
        print("Generating audio with KittenTTS...")
        audio = KITTEN_MODEL.generate(request.text, voice=request.voice)
        
        # Note: Speed is applied client-side via Audio.playbackRate
        # This preserves pitch better than server-side resampling
        
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
        "brave_search": bool(BRAVE_API_KEY),
        "history_length": len(conversation_history)
    }

@app.get("/", response_class=HTMLResponse)
async def index():
    return HTML_CONTENT

HTML_CONTENT = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Voice Chat</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            color: white;
            padding: 20px;
        }
        .container { max-width: 700px; margin: 0 auto; }
        h1 { text-align: center; margin-bottom: 5px; }
        .subtitle { text-align: center; color: #888; margin-bottom: 20px; font-size: 14px; }
        
        /* Status indicator */
        .status-container {
            display: flex;
            justify-content: center;
            margin-bottom: 20px;
        }
        .status {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 15px 25px;
            background: rgba(255,255,255,0.05);
            border-radius: 50px;
            font-size: 16px;
            transition: all 0.3s;
        }
        .status-dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: #4a5568;
            transition: all 0.3s;
        }
        .status.ready .status-dot { background: #48bb78; }
        .status.listening .status-dot { 
            background: #f56565; 
            animation: pulse 1s infinite;
        }
        .status.thinking .status-dot { 
            background: #ecc94b; 
            animation: pulse 0.5s infinite;
        }
        .status.speaking .status-dot { 
            background: #4299e1; 
            animation: pulse 0.8s infinite;
        }
        .status.error .status-dot { background: #f56565; }
        
        @keyframes pulse {
            0%, 100% { transform: scale(1); opacity: 1; }
            50% { transform: scale(1.3); opacity: 0.7; }
        }
        
        /* Waveform animation for listening */
        .waveform {
            display: none;
            align-items: center;
            gap: 3px;
            height: 20px;
        }
        .status.listening .waveform { display: flex; }
        .status.listening .status-text-default { display: none; }
        .wave-bar {
            width: 4px;
            background: #f56565;
            border-radius: 2px;
            animation: wave 0.5s ease-in-out infinite;
        }
        .wave-bar:nth-child(1) { animation-delay: 0s; height: 8px; }
        .wave-bar:nth-child(2) { animation-delay: 0.1s; height: 16px; }
        .wave-bar:nth-child(3) { animation-delay: 0.2s; height: 12px; }
        .wave-bar:nth-child(4) { animation-delay: 0.3s; height: 18px; }
        .wave-bar:nth-child(5) { animation-delay: 0.4s; height: 10px; }
        @keyframes wave {
            0%, 100% { transform: scaleY(1); }
            50% { transform: scaleY(0.5); }
        }
        
        /* Chat area */
        .chat-box {
            background: rgba(255,255,255,0.03);
            border-radius: 16px;
            padding: 20px;
            height: 350px;
            overflow-y: auto;
            margin-bottom: 20px;
            border: 1px solid rgba(255,255,255,0.1);
        }
        .message {
            padding: 12px 16px;
            border-radius: 16px;
            margin-bottom: 12px;
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
            font-size: 11px; 
            opacity: 0.7; 
            margin-bottom: 4px; 
        }
        .error-msg {
            background: rgba(245, 101, 101, 0.2);
            border: 1px solid rgba(245, 101, 101, 0.5);
            color: #feb2b2;
            padding: 10px 15px;
            border-radius: 8px;
            margin-bottom: 12px;
            font-size: 14px;
        }
        
        /* Controls */
        .controls {
            display: flex;
            gap: 10px;
            justify-content: center;
            flex-wrap: wrap;
        }
        .btn {
            padding: 16px 32px;
            border: none;
            border-radius: 50px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            min-width: 180px;
            justify-content: center;
        }
        .btn-primary:hover:not(:disabled) { 
            transform: scale(1.05); 
            box-shadow: 0 5px 25px rgba(102, 126, 234, 0.4); 
        }
        .btn-primary.active {
            background: linear-gradient(135deg, #f56565 0%, #ed64a6 100%);
        }
        .btn-secondary { 
            background: rgba(255,255,255,0.1); 
            color: white;
            padding: 16px 20px;
        }
        .btn-secondary:hover:not(:disabled) { background: rgba(255,255,255,0.2); }
        .btn:disabled { opacity: 0.5; cursor: not-allowed; transform: none !important; }
        
        /* Settings */
        .settings {
            display: flex;
            gap: 15px;
            justify-content: center;
            margin-top: 20px;
            flex-wrap: wrap;
        }
        .settings label { 
            display: flex; 
            align-items: center; 
            gap: 8px; 
            font-size: 13px;
            color: #a0aec0;
        }
        .settings select, .settings input[type="range"] { 
            padding: 6px 10px; 
            border-radius: 6px; 
            border: 1px solid rgba(255,255,255,0.2);
            background: rgba(255,255,255,0.1);
            color: white;
        }
        .settings input[type="range"] {
            width: 80px;
            padding: 0;
        }
        .settings input[type="checkbox"] {
            width: 18px;
            height: 18px;
        }
        .speed-value {
            font-size: 11px;
            min-width: 30px;
        }
        
        /* Sources/Citations */
        .sources {
            margin-top: 8px;
            font-size: 12px;
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
            padding: 10px;
            background: rgba(0,0,0,0.2);
            border-radius: 8px;
        }
        .sources-list.open { display: block; }
        .source-item {
            margin-bottom: 8px;
            padding-bottom: 8px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        .source-item:last-child { border-bottom: none; margin-bottom: 0; padding-bottom: 0; }
        .source-title {
            color: #4299e1;
            text-decoration: none;
            font-weight: 500;
        }
        .source-title:hover { text-decoration: underline; }
        .source-desc {
            color: #a0aec0;
            font-size: 11px;
            margin-top: 2px;
        }
        
        /* Thinking dots */
        .thinking-dots {
            display: none;
        }
        .status.thinking .thinking-dots {
            display: flex;
            gap: 4px;
        }
        .status.thinking .status-text-default { display: none; }
        .thinking-dot {
            width: 8px;
            height: 8px;
            background: #ecc94b;
            border-radius: 50%;
            animation: thinking 1.4s ease-in-out infinite;
        }
        .thinking-dot:nth-child(1) { animation-delay: 0s; }
        .thinking-dot:nth-child(2) { animation-delay: 0.2s; }
        .thinking-dot:nth-child(3) { animation-delay: 0.4s; }
        @keyframes thinking {
            0%, 80%, 100% { transform: scale(0.6); opacity: 0.5; }
            40% { transform: scale(1); opacity: 1; }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎙️ Voice Chat</h1>
        <p class="subtitle">Speak naturally • GPT + KittenTTS + Web Search</p>
        
        <div class="status-container">
            <div id="status" class="status ready">
                <span class="status-dot"></span>
                <span class="status-text-default">Ready to chat</span>
                <div class="waveform">
                    <div class="wave-bar"></div>
                    <div class="wave-bar"></div>
                    <div class="wave-bar"></div>
                    <div class="wave-bar"></div>
                    <div class="wave-bar"></div>
                    <span style="margin-left: 8px;">Listening...</span>
                </div>
                <div class="thinking-dots">
                    <div class="thinking-dot"></div>
                    <div class="thinking-dot"></div>
                    <div class="thinking-dot"></div>
                    <span style="margin-left: 8px;">Thinking...</span>
                </div>
            </div>
        </div>
        
        <div id="chatBox" class="chat-box"></div>
        
        <div class="controls">
            <button id="mainBtn" class="btn btn-primary" onclick="toggleConversation()">
                🎤 Start Conversation
            </button>
            <button class="btn btn-secondary" onclick="stopAll()">⏹️ Stop</button>
            <button class="btn btn-secondary" onclick="clearChat()">🗑️ Clear</button>
        </div>
        
        <div class="settings">
            <label>
                TTS:
                <select id="ttsEngine">
                    <option value="kitten">🐱 KittenTTS</option>
                    <option value="browser">🌐 Browser</option>
                </select>
            </label>
            <label>
                Voice:
                <select id="kittenVoice">
                    <option value="expr-voice-2-f">Female 2</option>
                    <option value="expr-voice-3-f">Female 3</option>
                    <option value="expr-voice-2-m">Male 2</option>
                    <option value="expr-voice-3-m">Male 3</option>
                </select>
            </label>
            <label>
                Speed:
                <input type="range" id="ttsSpeed" min="0.5" max="2" step="0.1" value="1" oninput="updateSpeedLabel()">
                <span id="speedValue" class="speed-value">1.0x</span>
            </label>
            <label>
                <input type="checkbox" id="autoContinue" checked>
                Auto-continue
            </label>
        </div>
    </div>

    <script>
        // State
        let isConversationActive = false;
        let isListening = false;
        let isSpeaking = false;
        let isProcessing = false;
        
        // Speech Recognition setup
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        let recognition = null;
        
        if (SpeechRecognition) {
            recognition = new SpeechRecognition();
            recognition.continuous = false;
            recognition.interimResults = true;
            recognition.lang = 'en-US';
            
            recognition.onstart = () => {
                isListening = true;
                setStatus('listening');
                updateMainButton();
            };
            
            recognition.onend = () => {
                isListening = false;
                if (!isProcessing && !isSpeaking) {
                    setStatus('ready');
                }
                updateMainButton();
                
                // Auto-restart if conversation is active and we're not processing
                if (isConversationActive && !isProcessing && !isSpeaking && document.getElementById('autoContinue').checked) {
                    setTimeout(() => {
                        if (isConversationActive && !isProcessing && !isSpeaking) {
                            startListening();
                        }
                    }, 300);
                }
            };
            
            recognition.onresult = (event) => {
                let finalTranscript = '';
                let interimTranscript = '';
                
                for (let i = event.resultIndex; i < event.results.length; i++) {
                    if (event.results[i].isFinal) {
                        finalTranscript = event.results[i][0].transcript;
                    } else {
                        interimTranscript = event.results[i][0].transcript;
                    }
                }
                
                if (finalTranscript.trim()) {
                    handleUserMessage(finalTranscript.trim());
                }
            };
            
            recognition.onerror = (event) => {
                console.error('Speech error:', event.error);
                if (event.error !== 'no-speech' && event.error !== 'aborted') {
                    showError('Speech recognition error: ' + event.error);
                }
            };
        }
        
        function setStatus(state, customText) {
            const el = document.getElementById('status');
            el.className = 'status ' + state;
            if (customText) {
                el.querySelector('.status-text-default').textContent = customText;
            } else {
                const texts = {
                    ready: 'Ready to chat',
                    listening: 'Listening...',
                    thinking: 'Thinking...',
                    speaking: '🔊 Speaking...',
                    error: 'Error occurred'
                };
                el.querySelector('.status-text-default').textContent = texts[state] || state;
            }
        }
        
        function updateMainButton() {
            const btn = document.getElementById('mainBtn');
            if (isConversationActive) {
                btn.classList.add('active');
                btn.innerHTML = '🔴 End Conversation';
            } else {
                btn.classList.remove('active');
                btn.innerHTML = '🎤 Start Conversation';
            }
        }
        
        function toggleConversation() {
            if (isConversationActive) {
                stopAll();
            } else {
                isConversationActive = true;
                updateMainButton();
                startListening();
            }
        }
        
        function startListening() {
            if (recognition && !isListening && !isSpeaking) {
                try {
                    recognition.start();
                } catch (e) {
                    console.log('Recognition already started');
                }
            }
        }
        
        function stopAll() {
            isConversationActive = false;
            isProcessing = false;
            isSpeaking = false;
            
            if (recognition) recognition.stop();
            speechSynthesis.cancel();
            
            // Stop any playing audio
            document.querySelectorAll('audio').forEach(a => {
                a.pause();
                a.remove();
            });
            
            setStatus('ready');
            updateMainButton();
        }
        
        function updateSpeedLabel() {
            const speed = parseFloat(document.getElementById('ttsSpeed').value).toFixed(1);
            document.getElementById('speedValue').textContent = speed + 'x';
        }
        
        function addMessage(role, text, sources = null) {
            const chatBox = document.getElementById('chatBox');
            const div = document.createElement('div');
            div.className = 'message ' + role;
            const label = role === 'user' ? '👤 You' : '🤖 Assistant';
            
            let html = `<div class="message-label">${label}</div>${text}`;
            
            // Add sources if available
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
            const chatBox = document.getElementById('chatBox');
            const div = document.createElement('div');
            div.className = 'error-msg';
            div.textContent = '⚠️ ' + text;
            chatBox.appendChild(div);
            chatBox.scrollTop = chatBox.scrollHeight;
            setStatus('error');
        }
        
        async function handleUserMessage(text) {
            // Stop listening while processing
            if (recognition) recognition.stop();
            isProcessing = true;
            
            addMessage('user', text);
            setStatus('thinking');
            
            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: text })
                });
                
                const data = await response.json();
                
                if (data.error) {
                    showError(data.error);
                    isProcessing = false;
                    if (isConversationActive) startListening();
                    return;
                }
                
                addMessage('assistant', data.response, data.sources);
                await speak(data.response);
                
            } catch (error) {
                console.error('Error:', error);
                showError('Connection error: ' + error.message);
                isProcessing = false;
                if (isConversationActive) startListening();
            }
        }
        
        async function speak(text) {
            isSpeaking = true;
            setStatus('speaking');
            
            const engine = document.getElementById('ttsEngine').value;
            
            try {
                if (engine === 'kitten') {
                    await speakWithKitten(text);
                } else {
                    await speakWithBrowser(text);
                }
            } catch (e) {
                console.error('TTS error:', e);
            }
            
            isSpeaking = false;
            isProcessing = false;
            
            // Continue conversation if active
            if (isConversationActive && document.getElementById('autoContinue').checked) {
                setStatus('ready', 'Your turn...');
                setTimeout(() => startListening(), 500);
            } else {
                setStatus('ready');
            }
        }
        
        async function speakWithKitten(text) {
            const voice = document.getElementById('kittenVoice').value;
            const speed = parseFloat(document.getElementById('ttsSpeed').value);
            console.log('🐱 Using KittenTTS with voice:', voice, 'speed:', speed);
            
            try {
                const response = await fetch('/api/tts', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ text, voice, speed })
                });
                
                const data = await response.json();
                console.log('TTS response:', data.error ? data.error : 'Got audio data');
                
                if (data.error) {
                    console.warn('KittenTTS error, falling back to browser:', data.error);
                    setStatus('speaking', '🔊 Speaking (browser)...');
                    await speakWithBrowser(text);
                    return;
                }
                
                setStatus('speaking', '🔊 Speaking (KittenTTS)...');
                
                return new Promise((resolve) => {
                    const audio = new Audio('data:audio/wav;base64,' + data.audio);
                    // Apply speed via playbackRate (preserves pitch!)
                    audio.playbackRate = speed;
                    audio.onended = () => {
                        console.log('✅ KittenTTS playback complete');
                        resolve();
                    };
                    audio.onerror = (e) => {
                        console.error('Audio playback error:', e);
                        resolve();
                    };
                    audio.play().catch(e => {
                        console.error('Play error:', e);
                        speakWithBrowser(text).then(resolve);
                    });
                });
            } catch (error) {
                console.error('KittenTTS fetch error:', error);
                setStatus('speaking', '🔊 Speaking (browser)...');
                await speakWithBrowser(text);
            }
        }
        
        function speakWithBrowser(text) {
            return new Promise((resolve) => {
                const utterance = new SpeechSynthesisUtterance(text);
                utterance.rate = parseFloat(document.getElementById('ttsSpeed').value);
                utterance.onend = resolve;
                utterance.onerror = () => resolve();
                speechSynthesis.speak(utterance);
            });
        }
        
        async function clearChat() {
            document.getElementById('chatBox').innerHTML = '';
            await fetch('/api/clear', { method: 'POST' });
        }
        
        // Check status on load
        fetch('/api/status').then(r => r.json()).then(data => {
            console.log('Server status:', data);
            if (!data.kitten_tts) {
                document.getElementById('ttsEngine').value = 'browser';
            }
            if (!data.azure_configured) {
                showError('Azure OpenAI not configured. Create .env file with AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_KEY');
            }
        });
    </script>
</body>
</html>
'''

if __name__ == "__main__":
    print("=" * 60)
    print("Voice Chat Server")
    print("=" * 60)
    print(f"KittenTTS: {'✅ Available' if KITTEN_AVAILABLE else '❌ Not available'}")
    print(f"Azure: {'✅ Configured' if AZURE_ENDPOINT and AZURE_KEY else '❌ Not configured'}")
    if not AZURE_ENDPOINT or not AZURE_KEY:
        print("\n⚠️  Create .env file with:")
        print("   AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com")
        print("   AZURE_OPENAI_KEY=your-api-key")
        print("   AZURE_OPENAI_DEPLOYMENT=gpt-4")
    print()
    print("Starting server at http://localhost:8000")
    print("=" * 60)
    
    uvicorn.run(app, host="127.0.0.1", port=8000)
