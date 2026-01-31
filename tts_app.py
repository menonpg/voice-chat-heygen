#!/usr/bin/env python3
"""
Simple TTS Demo using macOS 'say' command + Gradio UI
No external TTS models required!
"""

import gradio as gr
import subprocess
import tempfile
import os

# Get available macOS voices
def get_voices():
    result = subprocess.run(['say', '-v', '?'], capture_output=True, text=True)
    voices = {}
    for line in result.stdout.strip().split('\n'):
        if line:
            parts = line.split()
            name = parts[0]
            lang = parts[1] if len(parts) > 1 else 'en_US'
            voices[f"{name} ({lang})"] = name
    # Return subset of common voices
    common = ['Alex', 'Samantha', 'Victoria', 'Daniel', 'Karen', 'Moira', 'Tessa', 'Fiona']
    filtered = {k: v for k, v in voices.items() if any(c in k for c in common)}
    return filtered if filtered else dict(list(voices.items())[:10])

VOICES = get_voices()

def generate_speech(text: str, voice_name: str, speed: int) -> str:
    """Generate speech using macOS say command."""
    if not text.strip():
        return None
    
    voice = VOICES.get(voice_name, 'Alex')
    
    # Create temp file for audio
    with tempfile.NamedTemporaryFile(suffix=".aiff", delete=False) as f:
        output_path = f.name
    
    # Generate audio with say command
    subprocess.run([
        'say', '-v', voice, '-r', str(speed), '-o', output_path, text
    ], check=True)
    
    # Convert to wav for better compatibility
    wav_path = output_path.replace('.aiff', '.wav')
    subprocess.run([
        'afconvert', '-f', 'WAVE', '-d', 'LEI16', output_path, wav_path
    ], check=True)
    
    os.unlink(output_path)  # Clean up aiff
    return wav_path

def create_ui():
    with gr.Blocks(title="macOS TTS Demo", theme=gr.themes.Soft()) as demo:
        gr.Markdown("""
        # 🎙️ Text-to-Speech Demo
        **Using macOS built-in voices - No GPU or downloads needed!**
        """)
        
        with gr.Row():
            with gr.Column(scale=2):
                text_input = gr.Textbox(
                    label="Text to Speak",
                    placeholder="Enter text to convert to speech...",
                    lines=4,
                    value="Hello! This is a text to speech demo using macOS built-in voices."
                )
                
                with gr.Row():
                    voice_dropdown = gr.Dropdown(
                        choices=list(VOICES.keys()),
                        value=list(VOICES.keys())[0] if VOICES else "Alex",
                        label="Voice"
                    )
                    speed_slider = gr.Slider(
                        minimum=100, maximum=300, value=175,
                        step=25, label="Speed (words/min)"
                    )
                
                generate_btn = gr.Button("🔊 Generate Speech", variant="primary")
            
            with gr.Column(scale=1):
                audio_output = gr.Audio(label="Generated Audio", type="filepath")
        
        generate_btn.click(
            fn=generate_speech,
            inputs=[text_input, voice_dropdown, speed_slider],
            outputs=audio_output
        )
        
        gr.Markdown(f"""
        ---
        ### Available Voices: {len(VOICES)}
        These are macOS system voices. More can be downloaded in System Preferences > Accessibility > Spoken Content.
        """)
    
    return demo

if __name__ == "__main__":
    demo = create_ui()
    demo.launch(server_name="127.0.0.1", server_port=7860, inbrowser=True)
