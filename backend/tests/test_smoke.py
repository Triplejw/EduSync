import os
from uuid import uuid4

os.environ.setdefault("EDUSYNC_JWT_SECRET", "test-only-secret")
os.environ.setdefault("EDUSYNC_DATABASE_URL", "sqlite:///backend/tests/test-smoke.db")

from fastapi.testclient import TestClient

import llm_service
import main
import parser_service
from vision_service import estimate_pose


client = TestClient(main.app)


def test_health_starts_without_loading_heavy_services():
    assert client.get("/health").json() == {"status": "ok"}
    services = client.get("/health/services")
    assert services.status_code == 200
    assert services.json()["llm"]["loaded"] is False
    assert services.json()["ocr"]["loaded"] is False
    assert llm_service.get_model_status()["loaded"] is False
    assert parser_service.get_ocr_status()["loaded"] is False


def test_extract_text_uses_document_dispatch(monkeypatch):
    monkeypatch.setattr(main, "extract_text_from_document", lambda contents, ext: f"{ext}:{len(contents)}")
    response = client.post(
        "/extract-text",
        files={"file": ("slide.png", b"image-bytes", "image/png")},
    )
    assert response.status_code == 200
    assert response.json() == {"extracted_text": ".png:11"}


def test_extract_text_rejects_unsupported_extension():
    response = client.post(
        "/extract-text",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 400


def test_auth_and_dsp_flow(monkeypatch):
    monkeypatch.setattr(main, "log_engagement_metrics", lambda **kwargs: None)
    email = f"smoke-{uuid4().hex}@example.com"
    register = client.post(
        "/register",
        json={
            "email": email,
            "password": "DemoPass123!",
            "full_name": "Smoke Test",
            "role": "student",
        },
    )
    assert register.status_code == 200
    token = register.json()["access_token"]

    login = client.post("/login", json={"email": email, "password": "DemoPass123!"})
    assert login.status_code == 200

    analytics = client.post(
        "/submit-analytics",
        headers={"Authorization": f"Bearer {token}"},
        json={"material_id": 999, "scroll_signal": [0, 5, 12, 20, 18, 4, 0]},
    )
    assert analytics.status_code == 200
    assert 0 <= analytics.json()["engagement_score"] <= 100
    assert "zcr" in analytics.json()["dsp_metrics"]


def test_vision_handles_invalid_image_without_crashing():
    result = estimate_pose(b"not-an-image", student_id="smoke")
    assert result["attention_score"] == 0
