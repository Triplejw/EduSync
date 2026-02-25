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

# 2. Initialize Model (Global Variable) - Optimized for RTX 3060 6GB + Ryzen 7 5800H
try:
    _start = time.perf_counter()
    llm = Llama(
        model_path=MODEL_PATH,
        n_gpu_layers=-1,      # All layers on GPU (RTX 3060 6GB can handle 8B Q4 model)
        n_ctx=4096,           # Context window (can increase to 8192 if needed)
        n_threads=8,          # Match Ryzen 7 5800H core count for parallel CPU ops
        n_batch=512,          # Optimal batch size for prompt processing
        use_mlock=True,       # Lock model in RAM to prevent swapping
        verbose=False         # Disable verbose logging for performance
    )
    model_load_time_ms = (time.perf_counter() - _start) * 1000
    print(f"✅ Llama-3 8B Loaded on GPU (n_threads=8, n_batch=512, mlock=True) in {model_load_time_ms:.0f} ms")
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
    """Generate 5 multiple-choice questions from the first 6000 chars (single call, fast on edge)."""
    if not llm:
        return "Error: AI Model not loaded."

    # Truncate to 6000 chars so enough context remains for output
    max_chars = 6000
    if len(content_text) > max_chars:
        content_text = content_text[:max_chars] + "... [Text Truncated]"

    prompt = f"""<|start_header_id|>system<|end_header_id|>

You are a strict JSON generator. Output exactly 5 multiple-choice questions in a list based on the text provided.
Do not include any text outside the JSON. Keys must be exactly: "question", "options", "correct_answer".
"options" must be a list of 4 strings. "correct_answer" is the index (0-3).

Example format:
[
  {{ "question": "What is 2+2?", "options": ["3", "4", "5", "6"], "correct_answer": 1 }},
  {{ "question": "Next question?", "options": ["A", "B", "C", "D"], "correct_answer": 0 }}
]
<|eot_id|><|start_header_id|>user<|end_header_id|>

Context: {content_text}
<|eot_id|><|start_header_id|>assistant<|end_header_id|>"""

    output = llm(
        prompt,
        max_tokens=512,  # Enough for 5 questions; keeps generation fast on edge
        temperature=0.4,
        stop=["<|eot_id|>"],
        echo=False,
    )
    return output["choices"][0]["text"]


def generate_summary(content_text):
    """Generate a concise summary of study material using the LLM."""
    if not llm:
        return "Error: AI Model not loaded."

    max_chars = 8000  # Optimized for faster generation on edge hardware
    if len(content_text) > max_chars:
        content_text = content_text[:max_chars] + "... [Text Truncated]"

    prompt = f"""<|start_header_id|>system<|end_header_id|>

You are an educational assistant. Summarize the following study material as key bullet points that are easy to learn.
Use concise bullet points only, not paragraphs. Cover main concepts and important details.
<|eot_id|><|start_header_id|>user<|end_header_id|>

{content_text}
<|eot_id|><|start_header_id|>assistant<|end_header_id|>"""

    output = llm(prompt, max_tokens=512, temperature=0.5, stop=["<|eot_id|>"], echo=False)
    return output['choices'][0]['text'].strip()


def generate_flashcards(content_text):
    """Generate flashcards (question/answer pairs) as JSON from study material."""
    if not llm:
        return "[]"

    max_chars = 8000  # Optimized for faster generation on edge hardware
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