#!/usr/bin/env python3
"""
Piper TTS Demo - Fast Local Neural Text-to-Speech
https://github.com/rhasspy/piper

Run: python piper_tts_app.py
"""

import gradio as gr
import subprocess
import tempfile
import os
import wave

# Check if piper is installed
try:
    import piper
    PIPER_AVAILABLE = True
except ImportError:
    PIPER_AVAILABLE = False

# Available Piper voices (will download on first use ~20-50MB each)
VOICES = {
    "Amy (US Female, Medium)": "en_US-amy-medium",
    "Lessac (US Male, Medium)": "en_US-lessac-medium", 
    "Libritts (US, High Quality)": "en_US-libritts-high",
    "Jenny (UK Female)": "en_GB-jenny_dioco-medium",
    "Alba (UK Female)": "en_GB-alba-medium",
    "Danny (US Male, Low)": "en_US-danny-low",
}

def generate_speech(text: str, voice_name: str) -> str:
    """Generate speech using Piper TTS."""
    if not text.strip():
        return None
    
    if not PIPER_AVAILABLE:
        # Fallback to command line piper
        voice_model = VOICES.get(voice_name, "en_US-amy-medium")
        
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            output_path = f.name
        
        try:
            # Use piper CLI
            process = subprocess.run(
                ["piper", "--model", voice_model, "--output_file", output_path],
                input=text,
                text=True,
                capture_output=True,
                timeout=60
            )
            if process.returncode == 0 and os.path.exists(output_path):
                return output_path
            else:
                print(f"Piper error: {process.stderr}")
                return None
        except FileNotFoundError:
            print("Piper CLI not found. Install with: pip install piper-tts")
            return None
        except Exception as e:
            print(f"Error: {e}")
            return None
    else:
        # Use piper Python API
        from piper import PiperVoice
        voice_model = VOICES.get(voice_name, "en_US-amy-medium")
        
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            output_path = f.name
        
        voice = PiperVoice.load(voice_model)
        with wave.open(output_path, "wb") as wav_file:
            voice.synthesize(text, wav_file)
        
        return output_path

def create_ui():
    with gr.Blocks(title="Piper TTS Demo") as demo:
        gr.Markdown("""
        # 🎤 Piper TTS Demo
        **Fast, Local Neural Text-to-Speech**
        
        - No GPU required
        - Runs entirely offline
        - Voice models ~20-50MB (download on first use)
        - [GitHub](https://github.com/rhasspy/piper)
        """)
        
        status_msg = "✅ Piper installed" if PIPER_AVAILABLE else "⚠️ Using Piper CLI mode"
        gr.Markdown(f"**Status:** {status_msg}")
        
        with gr.Row():
            with gr.Column(scale=2):
                text_input = gr.Textbox(
                    label="Text to Speak",
                    placeholder="Enter text to convert to speech...",
                    lines=4,
                    value="Hello! This is Piper, a fast local neural text to speech system. It runs entirely on your device with no internet required."
                )
                
                voice_dropdown = gr.Dropdown(
                    choices=list(VOICES.keys()),
                    value=list(VOICES.keys())[0],
                    label="Voice (downloads ~30MB on first use)"
                )
                
                generate_btn = gr.Button("🔊 Generate Speech", variant="primary")
            
            with gr.Column(scale=1):
                audio_output = gr.Audio(label="Generated Audio", type="filepath")
        
        generate_btn.click(
            fn=generate_speech,
            inputs=[text_input, voice_dropdown],
            outputs=audio_output
        )
        
        gr.Markdown("""
        ---
        ### About Piper
        - **Speed**: ~10x realtime on CPU
        - **Quality**: Neural network based, natural sounding
        - **Size**: Voice models are 20-50MB each
        - **Privacy**: 100% local, no data leaves your machine
        """)
    
    return demo

if __name__ == "__main__":
    print("Starting Piper TTS Demo...")
    print("Voice models will download on first use (~30MB each)")
    demo = create_ui()
    demo.launch(server_name="127.0.0.1", server_port=7861, inbrowser=True)
