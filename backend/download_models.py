"""Download the approved quantized Llama 3 model into the Git-ignored model folder."""

from pathlib import Path
import os
import shutil


REPO_ID = "bartowski/Meta-Llama-3-8B-Instruct-GGUF"
FILENAME = "Meta-Llama-3-8B-Instruct-Q4_K_M.gguf"
DEFAULT_TARGET = Path(__file__).resolve().parent / "models" / FILENAME


def main() -> None:
    target = Path(os.environ.get("EDUSYNC_MODEL_PATH", DEFAULT_TARGET)).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    local_cache = Path(__file__).resolve().parent.parent / ".cache" / "huggingface"
    local_cache.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("HF_HOME", str(local_cache))
    os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
    from huggingface_hub import hf_hub_download

    print(f"Downloading {FILENAME} (~5 GB) to {target.parent}")
    downloaded = Path(
        hf_hub_download(
            repo_id=REPO_ID,
            filename=FILENAME,
            local_dir=target.parent,
            cache_dir=local_cache,
        )
    ).resolve()
    if downloaded != target:
        shutil.move(str(downloaded), str(target))
    print(f"Model ready: {target}")


if __name__ == "__main__":
    main()
