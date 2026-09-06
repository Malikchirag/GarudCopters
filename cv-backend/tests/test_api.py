"""
Basic API tests -- run with:  pytest tests/

These exercise the error-handling paths (Step 4's requirement) without
needing a trained model loaded: /health always works, and the invalid-input
cases (wrong content type, corrupted upload) are rejected before inference
is ever attempted, so they don't depend on models/best.pt existing.
"""
import io

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "model_loaded" in body
    assert "weights_path" in body


def test_detect_image_rejects_wrong_content_type():
    resp = client.post(
        "/detect/image",
        files={"file": ("notes.txt", io.BytesIO(b"hello"), "text/plain")},
    )
    assert resp.status_code == 400
    assert "content type" in resp.json()["detail"].lower()


def test_detect_image_rejects_corrupted_upload():
    resp = client.post(
        "/detect/image",
        files={"file": ("broken.jpg", io.BytesIO(b"not actually a jpeg"), "image/jpeg")},
    )
    assert resp.status_code == 400
    assert "decode" in resp.json()["detail"].lower()


def test_detect_video_rejects_wrong_content_type():
    resp = client.post(
        "/detect/video",
        files={"file": ("notes.txt", io.BytesIO(b"hello"), "text/plain")},
    )
    assert resp.status_code == 400


def test_detect_video_rejects_empty_upload():
    resp = client.post(
        "/detect/video",
        files={"file": ("empty.mp4", io.BytesIO(b""), "video/mp4")},
    )
    assert resp.status_code == 400
