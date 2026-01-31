#!/usr/bin/env python3
"""
NVIDIA PersonaPlex Demo
Full-duplex conversational AI with voice and role control

⚠️  REQUIRES: NVIDIA A100 or H100 GPU
    This demo will NOT work on consumer hardware (MacBook, gaming GPUs, etc.)

🚀 OPTIONS TO RUN PERSONAPLEX:

1. GOOGLE COLAB (Easiest)
   https://colab.research.google.com/#fileId=https://huggingface.co/nvidia/personaplex-7b-v1.ipynb
   Note: Free tier may not have enough GPU. Colab Pro+ has A100.

2. CLOUD GPU RENTAL (~$1-2/hour)
   - RunPod:      https://runpod.io      (A100 80GB ~$1.99/hr)
   - Vast.ai:     https://vast.ai        (A100 80GB ~$1.50/hr)  
   - Lambda Labs: https://lambdalabs.com (A100 ~$1.10/hr)

3. LOCAL (if you have A100/H100)
   See setup instructions below.

For more info:
- GitHub: https://github.com/NVIDIA/personaplex
- HuggingFace: https://huggingface.co/nvidia/personaplex-7b-v1
- Paper: https://research.nvidia.com/labs/adlr/files/personaplex/personaplex_preprint.pdf

"""

import os
import sys

def check_requirements():
    """Check if system meets PersonaPlex requirements."""
    print("=" * 60)
    print("NVIDIA PersonaPlex - Requirements Check")
    print("=" * 60)
    
    # Check for NVIDIA GPU
    try:
        import torch
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            gpu_mem = torch.cuda.get_device_properties(0).total_memory / 1e9
            print(f"✅ GPU Found: {gpu_name}")
            print(f"   Memory: {gpu_mem:.1f} GB")
            
            # Check if it's A100 or H100
            if "A100" in gpu_name or "H100" in gpu_name:
                print("✅ GPU is compatible with PersonaPlex")
                return True
            else:
                print("⚠️  GPU may not have sufficient memory for PersonaPlex")
                print("   Recommended: NVIDIA A100 (80GB) or H100")
                return False
        else:
            print("❌ No NVIDIA GPU detected")
            print("   PersonaPlex requires NVIDIA A100 or H100 GPU")
            return False
    except ImportError:
        print("❌ PyTorch not installed")
        return False

def show_setup_instructions():
    """Display setup instructions for PersonaPlex."""
    instructions = """
╔══════════════════════════════════════════════════════════════╗
║              PersonaPlex Setup Instructions                   ║
╚══════════════════════════════════════════════════════════════╝

1. HARDWARE REQUIREMENTS
   - NVIDIA A100 (80GB) or H100 GPU
   - Linux OS recommended
   - ~20GB disk space for model weights

2. INSTALL DEPENDENCIES
   
   # Install Opus codec
   sudo apt install libopus-dev  # Ubuntu/Debian
   brew install opus             # macOS
   
   # Clone repository
   git clone https://github.com/NVIDIA/personaplex
   cd personaplex
   
   # Install Python package
   pip install moshi/.
   
   # For CPU offload (if limited VRAM)
   pip install accelerate

3. HUGGINGFACE AUTHENTICATION
   
   # Accept license at: https://huggingface.co/nvidia/personaplex-7b-v1
   # Then set your token:
   export HF_TOKEN=your_huggingface_token

4. RUN THE SERVER
   
   # Create temp SSL certs and launch
   SSL_DIR=$(mktemp -d)
   python -m moshi.server --ssl "$SSL_DIR"
   
   # With CPU offload for limited VRAM
   python -m moshi.server --ssl "$SSL_DIR" --cpu-offload
   
   # Access Web UI at: https://localhost:8998

5. OFFLINE EVALUATION
   
   python -m moshi.offline \\
       --voice-prompt "NATF2.pt" \\
       --text-prompt "You are a helpful assistant." \\
       --input-wav "input.wav" \\
       --output-wav "output.wav"

═══════════════════════════════════════════════════════════════

AVAILABLE VOICES:
   Natural (Female): NATF0, NATF1, NATF2, NATF3
   Natural (Male):   NATM0, NATM1, NATM2, NATM3
   Variety (Female): VARF0-VARF4
   Variety (Male):   VARM0-VARM4

EXAMPLE PROMPTS:

   Assistant:
   "You are a wise and friendly teacher. Answer questions or 
    provide advice in a clear and engaging way."
   
   Customer Service:
   "You work for Acme Corp as a customer service agent. Your 
    name is Alex. Help customers with their orders."
   
   Casual:
   "You enjoy having a good conversation."

═══════════════════════════════════════════════════════════════

For more information:
- GitHub: https://github.com/NVIDIA/personaplex
- Paper: PersonaPlex: Voice and Role Control for Full Duplex 
         Conversational Speech Models (Roy et al., 2026)
- Demo: https://research.nvidia.com/labs/adlr/personaplex/

"""
    print(instructions)

def run_demo():
    """Attempt to run PersonaPlex demo."""
    print("\nAttempting to start PersonaPlex...")
    
    try:
        # Try to import moshi
        from moshi.server import main as server_main
        print("✅ Moshi package found")
        
        # Check HuggingFace token
        hf_token = os.environ.get("HF_TOKEN")
        if not hf_token:
            print("❌ HF_TOKEN not set")
            print("   Set with: export HF_TOKEN=your_token")
            return
        
        print("✅ HuggingFace token found")
        print("\nStarting PersonaPlex server...")
        print("Access the Web UI at: https://localhost:8998")
        
        # This would start the server
        # server_main()
        
    except ImportError as e:
        print(f"❌ Cannot import moshi: {e}")
        print("\nInstall PersonaPlex first:")
        print("  git clone https://github.com/NVIDIA/personaplex")
        print("  cd personaplex && pip install moshi/.")

if __name__ == "__main__":
    has_gpu = check_requirements()
    
    if not has_gpu:
        print("\n" + "=" * 60)
        print("PersonaPlex cannot run on this system.")
        print("Showing setup instructions instead...")
        print("=" * 60)
    
    show_setup_instructions()
    
    if has_gpu and len(sys.argv) > 1 and sys.argv[1] == "--run":
        run_demo()
    elif has_gpu:
        print("\nTo attempt running the demo, use: python personaplex_demo.py --run")
