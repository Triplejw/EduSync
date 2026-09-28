"""Pre-call checks for the EduSync local demo."""

import argparse
import importlib.util
import json
import os
import platform
import sys
import urllib.request

from settings import llm_config


def package_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def main() -> int:
    parser = argparse.ArgumentParser(description="Check EduSync demo readiness")
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    parser.add_argument("--load-llm", action="store_true", help="Load the GGUF and run one short inference")
    args = parser.parse_args()

    checks = {
        "architecture": platform.machine(),
        "native_arm64": platform.machine() == "arm64",
        "python": platform.python_version(),
        "model_path": str(llm_config.model_path),
        "model_exists": llm_config.model_path.is_file(),
        "packages": {
            name: package_available(name)
            for name in ("fastapi", "sqlalchemy", "llama_cpp", "easyocr", "mediapipe", "cv2")
        },
        "expo_api_url": os.environ.get("EXPO_PUBLIC_API_URL"),
    }
    if checks["packages"]["llama_cpp"]:
        from llama_cpp import llama_supports_gpu_offload

        checks["llama_gpu_offload"] = llama_supports_gpu_offload()
    else:
        checks["llama_gpu_offload"] = False

    try:
        with urllib.request.urlopen(f"{args.api_url.rstrip('/')}/health", timeout=3) as response:
            checks["api_health"] = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        checks["api_health"] = {"reachable": False, "detail": str(exc)}

    if args.load_llm:
        try:
            from llm_service import get_llm, get_model_load_time_ms

            llm = get_llm()
            result = llm.create_chat_completion(
                messages=[
                    {"role": "system", "content": "Follow the user's instruction exactly."},
                    {"role": "user", "content": "Reply with exactly: EduSync ready"},
                ],
                max_tokens=16,
                temperature=0,
            )
            output = result["choices"][0]["message"]["content"].strip()
            checks["llm_smoke"] = {
                "ok": "edusync ready" in output.lower(),
                "load_time_ms": get_model_load_time_ms(),
                "output": output,
            }
        except Exception as exc:
            checks["llm_smoke"] = {"ok": False, "detail": str(exc)}

    print(json.dumps(checks, indent=2))
    required_packages = checks["packages"]
    base_ok = (
        checks["native_arm64"]
        and checks["model_exists"]
        and all(required_packages.values())
        and checks["llama_gpu_offload"]
    )
    llm_ok = not args.load_llm or checks.get("llm_smoke", {}).get("ok", False)
    return 0 if base_ok and llm_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
