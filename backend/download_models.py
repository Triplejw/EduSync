from huggingface_hub import hf_hub_download
import os

# Create models directory if not exists
os.makedirs("models", exist_ok=True)

print("Downloading Llama-3-8B (Quantized) - This is ~5GB...")
# We use a GGUF format which is optimized for your 6GB VRAM
hf_hub_download(
    repo_id="bartowski/Meta-Llama-3-8B-Instruct-GGUF",
    filename="Meta-Llama-3-8B-Instruct-Q4_K_M.gguf",
    local_dir="models",
    local_dir_use_symlinks=False
)
print("Llama-3 Downloaded!")

print("Downloading Florence-2 (Vision) - This is ~1GB...")
# This will be cached by transformers automatically, 
# but we can pre-fetch it to ensure it works.
from transformers import AutoModelForCausalLM, AutoProcessor
AutoModelForCausalLM.from_pretrained("microsoft/Florence-2-large", trust_remote_code=True)
AutoProcessor.from_pretrained("microsoft/Florence-2-large", trust_remote_code=True)
print("Florence-2 Downloaded!")
