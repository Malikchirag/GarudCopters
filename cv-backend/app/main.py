"""
FastAPI backend for Garud Copters CV.

    uvicorn app.main:app --host 0.0.0.0 --port 8000

Endpoints:
    GET  /health         liveness/readiness check
    POST /detect/image    single image -> per-object detections
    POST /detect/video    video -> aggregate detection summary
    POST /report          raw detections -> LangGraph incident report (Step 5)
"""
import tempfile
import time
from pathlib import Path

import cv2
import numpy as np
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from app.detector import DEFAULT_CONF, get_model
from app.schemas import (
    ClassFirstSeen,
    Detection,
    ErrorResponse,
    HealthResponse,
    ImageDetectionResponse,
    VideoDetectionResponse,
)
from app.detector import DEFAULT_WEIGHTS

app = FastAPI(
    title="Garud Copters CV",
    description="Disaster-response object detection (people / vehicles / debris) for aerial imagery.",
    version="0.1.0",
)

IMAGE_CONTENT_TYPES = {"image/jpeg", "image/png", "image/bmp"}
VIDEO_CONTENT_TYPES = {"video/mp4", "video/quicktime", "video/x-msvideo", "video/avi"}

# Video processing default: same "sample, don't crunch every frame"
# reasoning as inference.py -- see that file's comment for the full rationale.
DEFAULT_EVERY_N = 5


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    model_loaded = Path(DEFAULT_WEIGHTS).exists()
    return HealthResponse(status="ok", model_loaded=model_loaded, weights_path=DEFAULT_WEIGHTS)


@app.post(
    "/detect/image",
    response_model=ImageDetectionResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
async def detect_image(file: UploadFile = File(...)) -> ImageDetectionResponse:
    if file.content_type not in IMAGE_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported image content type: {file.content_type}")

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty upload")

    arr = np.frombuffer(raw, dtype=np.uint8)
    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if frame is None:
        raise HTTPException(status_code=400, detail="Could not decode image -- file is corrupted or not a valid image")

    try:
        model = get_model()
        results = model.predict(frame, conf=DEFAULT_CONF, verbose=False)[0]
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:  # model inference failure
        raise HTTPException(status_code=500, detail=f"Inference failed: {e}")

    detections = []
    count_by_class: dict[str, int] = {}
    for box in results.boxes:
        cls_name = model.names[int(box.cls[0])]
        detections.append(
            Detection(cls=cls_name, confidence=float(box.conf[0]), box=[round(v, 2) for v in box.xyxy[0].tolist()])
        )
        count_by_class[cls_name] = count_by_class.get(cls_name, 0) + 1

    h, w = frame.shape[:2]
    return ImageDetectionResponse(
        filename=file.filename or "upload",
        width=w,
        height=h,
        detections=detections,
        count_by_class=count_by_class,
    )


@app.post(
    "/detect/video",
    response_model=VideoDetectionResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
async def detect_video(file: UploadFile = File(...), every_n: int = DEFAULT_EVERY_N) -> VideoDetectionResponse:
    if file.content_type not in VIDEO_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported video content type: {file.content_type}")
    if every_n < 1:
        raise HTTPException(status_code=400, detail="every_n must be >= 1")

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty upload")

    # cv2.VideoCapture needs a real file path, not an in-memory buffer.
    suffix = Path(file.filename or "upload.mp4").suffix or ".mp4"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(raw)
        tmp_path = tmp.name

    try:
        cap = cv2.VideoCapture(tmp_path)
        if not cap.isOpened():
            raise HTTPException(status_code=400, detail="Could not open video -- file is corrupted or an unsupported codec")

        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0

        try:
            model = get_model()
        except FileNotFoundError as e:
            raise HTTPException(status_code=500, detail=str(e))

        count_by_class: dict[str, int] = {}
        first_seen: dict[str, ClassFirstSeen] = {}
        frame_idx = 0
        frames_sampled = 0

        try:
            while True:
                ok, frame = cap.read()
                if not ok:
                    break
                if frame_idx % every_n == 0:
                    frames_sampled += 1
                    results = model.predict(frame, conf=DEFAULT_CONF, verbose=False)[0]
                    for box in results.boxes:
                        cls_name = model.names[int(box.cls[0])]
                        count_by_class[cls_name] = count_by_class.get(cls_name, 0) + 1
                        if cls_name not in first_seen:
                            first_seen[cls_name] = ClassFirstSeen(
                                cls=cls_name,
                                first_seen_seconds=round(frame_idx / fps, 2),
                                first_seen_frame=frame_idx,
                            )
                frame_idx += 1
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Inference failed at frame {frame_idx}: {e}")
        finally:
            cap.release()

        return VideoDetectionResponse(
            filename=file.filename or "upload",
            duration_seconds=round(frame_idx / fps, 2),
            frames_processed=frame_idx,
            frames_sampled=frames_sampled,
            fps=round(fps, 2),
            count_by_class=count_by_class,
            first_detection=list(first_seen.values()),
        )
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@app.post("/report")
async def generate_report(detections: ImageDetectionResponse | VideoDetectionResponse):
    """
    Feeds a /detect/image or /detect/video result into the Step 5 LangGraph
    agent and returns the structured incident report. Kept as a thin wrapper
    -- see app/agent.py for the actual graph.
    """
    from app.agent import run_agent  # imported lazily so a missing ANTHROPIC_API_KEY

    # only breaks this endpoint, not the whole app / other endpoints.
    try:
        return run_agent(detections.model_dump())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent pipeline failed: {e}")


@app.exception_handler(Exception)
async def unhandled_exception_handler(request, exc):
    # Last-resort catch-all so a truly unexpected error still returns clean
    # JSON instead of leaking a stack trace to the caller.
    return JSONResponse(status_code=500, content={"detail": f"Internal error: {exc}"})
