"""Lazy local Llama inference for EduSync.

Importing this module never loads the model. The first generation request (or the
preflight command with ``--load-llm``) initializes llama.cpp exactly once.
"""

import threading
import time

from settings import llm_config


_llm = None
_load_error: str | None = None
_load_lock = threading.Lock()
model_load_time_ms: float | None = None


def get_model_load_time_ms():
    return model_load_time_ms


def get_model_status() -> dict:
    """Return readiness without triggering a multi-gigabyte model load."""
    return {
        "configured": bool(str(llm_config.model_path)),
        "model_exists": llm_config.model_path.is_file(),
        "loaded": _llm is not None,
        "load_error": _load_error,
        "backend": "llama.cpp",
    }


def get_llm():
    """Load and return the shared llama.cpp model, or raise a useful error."""
    global _llm, _load_error, model_load_time_ms
    if _llm is not None:
        return _llm

    with _load_lock:
        if _llm is not None:
            return _llm
        if not llm_config.model_path.is_file():
            _load_error = (
                "Model file not found. Set EDUSYNC_MODEL_PATH to a downloaded GGUF file: "
                f"{llm_config.model_path}"
            )
            raise RuntimeError(_load_error)

        try:
            from llama_cpp import Llama

            started = time.perf_counter()
            _llm = Llama(
                model_path=str(llm_config.model_path),
                n_gpu_layers=llm_config.gpu_layers,
                n_ctx=llm_config.n_ctx,
                n_threads=llm_config.n_threads,
                n_batch=llm_config.n_batch,
                use_mlock=llm_config.use_mlock,
                verbose=False,
            )
            model_load_time_ms = (time.perf_counter() - started) * 1000
            _load_error = None
            try:
                from metrics_logger import log_system_metrics

                log_system_metrics(event="model_load", model_load_time_ms=model_load_time_ms)
            except Exception:
                pass
            return _llm
        except Exception as exc:
            _load_error = str(exc)
            _llm = None
            raise RuntimeError(f"Local LLM failed to load: {exc}") from exc


def _run(prompt: str, *, max_tokens: int, temperature: float) -> str:
    output = get_llm()(
        prompt,
        max_tokens=max_tokens,
        temperature=temperature,
        stop=["<|eot_id|>"],
        echo=False,
    )
    return output["choices"][0]["text"].strip()


def generate_quiz(content_text):
    """Generate five multiple-choice questions as JSON."""
    if len(content_text) > 6000:
        content_text = content_text[:6000] + "... [Text Truncated]"
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
    return _run(prompt, max_tokens=512, temperature=0.4)


def generate_summary(content_text):
    """Generate a concise bullet-point summary."""
    if len(content_text) > 8000:
        content_text = content_text[:8000] + "... [Text Truncated]"
    prompt = f"""<|start_header_id|>system<|end_header_id|>

You are an educational assistant. Summarize the following study material as key bullet points that are easy to learn.
Use concise bullet points only, not paragraphs. Cover main concepts and important details.
<|eot_id|><|start_header_id|>user<|end_header_id|>

{content_text}
<|eot_id|><|start_header_id|>assistant<|end_header_id|>"""
    return _run(prompt, max_tokens=512, temperature=0.5)


def generate_flashcards(content_text):
    """Generate five question/answer flashcards as JSON."""
    if len(content_text) > 8000:
        content_text = content_text[:8000] + "... [Text Truncated]"
    prompt = f"""<|start_header_id|>system<|end_header_id|>

You are a strict JSON generator. Output exactly 5 valid JSON objects in a list.
Each object must have exactly: "front" (question/term) and "back" (answer/definition).
Do not include any text outside the JSON.
<|eot_id|><|start_header_id|>user<|end_header_id|>

Context: {content_text}
<|eot_id|><|start_header_id|>assistant<|end_header_id|>"""
    return _run(prompt, max_tokens=512, temperature=0.4)
