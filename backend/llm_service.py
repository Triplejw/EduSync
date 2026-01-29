import os
import time
from llama_cpp import Llama

# 1. Setup Model Path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "models", "Meta-Llama-3-8B-Instruct-Q4_K_M.gguf")

# Model load time (ms) for research metrics; set when model loads
model_load_time_ms = None

def get_model_load_time_ms():
    """Return model load time in ms if available (for research report)."""
    return model_load_time_ms

print(f"Loading LLM from: {MODEL_PATH}")

# 2. Initialize Model (Global Variable) - Optimized for Edge Performance
try:
    _start = time.perf_counter()
    llm = Llama(
        model_path=MODEL_PATH,
        n_gpu_layers=-1,      # All layers on GPU
        n_ctx=4096,           # Context window
        n_threads=6,          # CPU threads for non-GPU operations
        n_batch=512,          # Batch size for faster prompt processing
        verbose=False         # Disable verbose logging for performance
    )
    model_load_time_ms = (time.perf_counter() - _start) * 1000
    print(f"✅ Llama-3 Loaded on GPU (Optimized: n_threads=6, n_batch=512) in {model_load_time_ms:.0f} ms")
    # Log for research paper (System Resource Utilization)
    try:
        from metrics_logger import log_system_metrics
        log_system_metrics(event="model_load", model_load_time_ms=model_load_time_ms)
    except Exception:
        pass
except Exception as e:
    print(f"❌ Failed to load LLM: {e}")
    llm = None

def generate_quiz(content_text):
    if not llm:
        return "Error: AI Model not loaded."

    # --- SAFETY TRUNCATION ---
    # We lowered this slightly to 12,000 to keep the prompt evaluation faster
    # and leave more room in the 4096 context window for the answer.
    max_chars = 12000
    if len(content_text) > max_chars:
        print(f"⚠️ Text too long ({len(content_text)} chars). Truncating to first {max_chars} chars.")
        content_text = content_text[:max_chars] + "... [Text Truncated]"
    
    # Updated prompt (Removed duplicate <|begin_of_text|>)
    prompt = f"""<|start_header_id|>system<|end_header_id|>

You are a strict JSON generator. 
Output exactly 3 valid JSON objects in a list based on the text provided.
Do not include any text outside the JSON.
Keys must be exactly: "question", "options", "correct_answer".
"correct_answer" should be the index (0-3).

Example Format:
[
  {{
    "question": "What is 2+2?",
    "options": ["3", "4", "5", "6"],
    "correct_answer": 1
  }}
]
<|eot_id|><|start_header_id|>user<|end_header_id|>

Context: {content_text}
<|eot_id|><|start_header_id|>assistant<|end_header_id|>"""

    output = llm(
        prompt,
        max_tokens=512,
        temperature=0.4,  # Reduced for more deterministic JSON output
        stop=["<|eot_id|>"],
        echo=False
    )
    return output['choices'][0]['text']


def generate_summary(content_text):
    """Generate a concise summary of study material using the LLM."""
    if not llm:
        return "Error: AI Model not loaded."

    max_chars = 12000
    if len(content_text) > max_chars:
        content_text = content_text[:max_chars] + "... [Text Truncated]"

    prompt = f"""<|start_header_id|>system<|end_header_id|>

You are an educational assistant. Summarize the following study material in 3-5 clear paragraphs. 
Focus on key concepts, main ideas, and important details. Use simple, clear language.
<|eot_id|><|start_header_id|>user<|end_header_id|>

{content_text}
<|eot_id|><|start_header_id|>assistant<|end_header_id|>"""

    output = llm(prompt, max_tokens=512, temperature=0.5, stop=["<|eot_id|>"], echo=False)
    return output['choices'][0]['text'].strip()


def generate_flashcards(content_text):
    """Generate flashcards (question/answer pairs) as JSON from study material."""
    if not llm:
        return "[]"

    max_chars = 12000
    if len(content_text) > max_chars:
        content_text = content_text[:max_chars] + "... [Text Truncated]"

    prompt = f"""<|start_header_id|>system<|end_header_id|>

You are a strict JSON generator. Output exactly 5 valid JSON objects in a list.
Each object must have exactly: "front" (question/term) and "back" (answer/definition).
Do not include any text outside the JSON.
<|eot_id|><|start_header_id|>user<|end_header_id|>

Context: {content_text}
<|eot_id|><|start_header_id|>assistant<|end_header_id|>"""

    output = llm(prompt, max_tokens=512, temperature=0.4, stop=["<|eot_id|>"], echo=False)  # Reduced for deterministic JSON
    return output['choices'][0]['text']