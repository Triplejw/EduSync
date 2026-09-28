"""Environment-backed runtime settings for EduSync."""

from dataclasses import dataclass
from pathlib import Path
import os


BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BACKEND_DIR.parent


def _int_env(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer, got {value!r}") from exc


def _bool_env(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _path_env(name: str, default: Path) -> Path:
    """Resolve configured paths consistently, independent of the launch directory."""
    configured = Path(os.environ.get(name, default)).expanduser()
    if configured.is_absolute():
        return configured
    return (PROJECT_DIR / configured).resolve()


@dataclass(frozen=True)
class LLMConfig:
    model_path: Path = _path_env(
        "EDUSYNC_MODEL_PATH",
        BACKEND_DIR / "models" / "Meta-Llama-3-8B-Instruct-Q4_K_M.gguf",
    )
    gpu_layers: int = _int_env("EDUSYNC_GPU_LAYERS", -1)
    n_threads: int = _int_env("EDUSYNC_N_THREADS", max(1, min(os.cpu_count() or 4, 8)))
    n_batch: int = _int_env("EDUSYNC_N_BATCH", 256)
    n_ctx: int = _int_env("EDUSYNC_N_CTX", 2048)
    use_mlock: bool = _bool_env("EDUSYNC_USE_MLOCK", False)


@dataclass(frozen=True)
class DSPConfig:
    reading_lower_px_s: float = 2.0
    idle_max_px_s: float = 2.0
    skimming_lower_px_s: float = 100.0
    weight_reading: float = 60.0
    weight_energy: float = 25.0
    weight_zcr: float = 15.0
    energy_norm_factor: float = 1000.0
    optimal_zcr: float = 0.3


@dataclass(frozen=True)
class VisionConfig:
    yaw_threshold: float = 20.0
    pitch_threshold: float = 15.0
    ma_buffer_size: int = 10
    ma_buffer_ttl_sec: float = 300.0


llm_config = LLMConfig()
dsp_config = DSPConfig()
vision_config = VisionConfig()
