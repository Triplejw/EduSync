import os
from llama_cpp import Llama

# 1. Setup Model Path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "models", "Meta-Llama-3-8B-Instruct-Q4_K_M.gguf")

print(f"Loading LLM from: {MODEL_PATH}")

# 2. Initialize Model (Global Variable)
try:
    llm = Llama(
        model_path=MODEL_PATH,
        n_gpu_layers=-1, 
        n_ctx=4096,
        verbose=True 
    )
    print("✅ Llama-3 Loaded on GPU")
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
        temperature=0.7,
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

    output = llm(prompt, max_tokens=512, temperature=0.6, stop=["<|eot_id|>"], echo=False)
    return output['choices'][0]['text']