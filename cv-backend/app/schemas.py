"""Pydantic request/response models for the FastAPI backend."""
from typing import Literal

from pydantic import BaseModel, Field


class Detection(BaseModel):
    cls: str = Field(..., description="Class name, e.g. 'person', 'vehicle', 'debris'")
    confidence: float = Field(..., ge=0.0, le=1.0)
    box: list[float] = Field(..., description="[x0, y0, x1, y1] pixel coordinates", min_length=4, max_length=4)


class ImageDetectionResponse(BaseModel):
    filename: str
    width: int
    height: int
    detections: list[Detection]
    count_by_class: dict[str, int]


class ClassFirstSeen(BaseModel):
    cls: str
    first_seen_seconds: float
    first_seen_frame: int


class VideoDetectionResponse(BaseModel):
    filename: str
    duration_seconds: float
    frames_processed: int
    frames_sampled: int
    fps: float
    count_by_class: dict[str, int]
    first_detection: list[ClassFirstSeen]


class HealthResponse(BaseModel):
    status: Literal["ok"]
    model_loaded: bool
    weights_path: str


class ErrorResponse(BaseModel):
    detail: str
