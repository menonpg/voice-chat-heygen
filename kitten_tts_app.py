#!/usr/bin/env python3
"""
KittenTTS Demo App
Ultra-lightweight TTS (~25MB, 15M params) - No GPU required!

Install first:
    pip install https://github.com/KittenML/KittenTTS/releases/download/0.1/kittentts-0.1.0-py3-none-any.whl
    pip install gradio soundfile

Run:
    python kitten_tts_app.py
"""

import gradio as gr
import tempfile
import os

# Try to import KittenTTS
try:
    from kittentts import KittenTTS
    import soundfile as sf
    KITTEN_AVAILABLE = True
except ImportError:
    KITTEN_AVAILABLE = False
    print("⚠️  KittenTTS not installed. Run:")
    print("pip install https://github.com/KittenML/KittenTTS/releases/download/0.1/kittentts-0.1.0-py3-none-any.whl")

# Available voices
VOICES = {
    "Female Voice 2": "expr-voice-2-f",
    "Male Voice 2": "expr-voice-2-m",
    "Female Voice 3": "expr-voice-3-f",
    "Male Voice 3": "expr-voice-3-m",
    "Female Voice 4": "expr-voice-4-f",
    "Male Voice 4": "expr-voice-4-m",
    "Female Voice 5": "expr-voice-5-f",
    "Male Voice 5": "expr-voice-5-m",
}

# Global model instance (lazy loaded)
_model = None

def get_model():
    """Lazy load the KittenTTS model."""
    global _model
    if _model is None and KITTEN_AVAILABLE:
        print("Loading KittenTTS model (first run downloads ~25MB)...")
        _model = KittenTTS("KittenML/kitten-tts-nano-0.2")
        print("Model loaded!")
    return _model

def generate_speech(text: str, voice_name: str):
    """Generate speech from text using KittenTTS."""
    if not KITTEN_AVAILABLE:
        return None, "❌ KittenTTS not installed. Run: pip install https://github.com/KittenML/KittenTTS/releases/download/0.1/kittentts-0.1.0-py3-none-any.whl"
    
    if not text.strip():
        return None, "Please enter some text"
    
    try:
        model = get_model()
        voice_id = VOICES.get(voice_name, "expr-voice-2-f")
        
        # Generate audio
        audio = model.generate(text, voice=voice_id)
        
        # Save to temp file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            sf.write(f.name, audio, 24000)
            return f.name, f"✅ Generated with voice: {voice_id}"
    except Exception as e:
        return None, f"❌ Error: {str(e)}"

def create_ui():
    """Create the Gradio UI."""
    with gr.Blocks(title="KittenTTS Demo") as demo:
        gr.Markdown("""
        # 🐱 KittenTTS Demo
        **Ultra-lightweight TTS (~25MB) - No GPU required!**
        
        - 15 million parameters
        - 8 expressive voices
        - 24kHz output
        - [GitHub](https://github.com/KittenML/KittenTTS)
        """)
        
        if not KITTEN_AVAILABLE:
            gr.Markdown("""
            ### ⚠️ KittenTTS not installed!
            
            Run in terminal:
            ```
            pip install https://github.com/KittenML/KittenTTS/releases/download/0.1/kittentts-0.1.0-py3-none-any.whl
            ```
            Then restart this app.
            """)
        
        with gr.Row():
            with gr.Column(scale=2):
                text_input = gr.Textbox(
                    label="Text to Speak",
                    placeholder="Enter text to convert to speech...",
                    lines=4,
                    value="Hello! This is KittenTTS, an ultra-lightweight text to speech model that works without a GPU."
                )
                
                voice_dropdown = gr.Dropdown(
                    choices=list(VOICES.keys()),
                    value="Female Voice 2",
                    label="Select Voice"
                )
                
                generate_btn = gr.Button("🎙️ Generate Speech", variant="primary")
                
                status_text = gr.Textbox(label="Status", interactive=False)
            
            with gr.Column(scale=1):
                audio_output = gr.Audio(label="Generated Audio", type="filepath")
        
        generate_btn.click(
            fn=generate_speech,
            inputs=[text_input, voice_dropdown],
            outputs=[audio_output, status_text]
        )
        
        gr.Markdown("""
        ---
        ### Available Voices
        | Female | Male |
        |--------|------|
        | expr-voice-2-f | expr-voice-2-m |
        | expr-voice-3-f | expr-voice-3-m |
        | expr-voice-4-f | expr-voice-4-m |
        | expr-voice-5-f | expr-voice-5-m |
        
        ### Model Info
        - **Size**: ~25MB (15M parameters)
        - **Sample Rate**: 24kHz
        - **Model**: KittenML/kitten-tts-nano-0.2
        """)
    
    return demo

if __name__ == "__main__":
    print("=" * 50)
    print("KittenTTS Demo")
    print("=" * 50)
    if KITTEN_AVAILABLE:
        print("✅ KittenTTS is installed")
    else:
        print("❌ KittenTTS not found")
        print("Install: pip install https://github.com/KittenML/KittenTTS/releases/download/0.1/kittentts-0.1.0-py3-none-any.whl")
    print()
    
    demo = create_ui()
    demo.launch(server_name="127.0.0.1", server_port=7862, inbrowser=True)
