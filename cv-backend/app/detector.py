"""
Shared YOLO model wrapper. inference.py and app/main.py both go through this
so there's exactly one place that knows how to load weights and apply the
confidence threshold -- avoids the two entry points quietly drifting apart.
"""
import os
from pathlib import Path

from ultralytics import YOLO

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_WEIGHTS = os.environ.get("GARUD_CV_WEIGHTS", str(ROOT / "models" / "best.pt"))

# See inference.py's DEFAULT_CONF docstring for why 0.35 rather than
# Ultralytics' 0.25 default: aerial/disaster imagery produces more marginal
# low-confidence boxes than a clean benchmark, and for an operator-facing
# tool, fewer wrong boxes beats catching every last borderline one.
DEFAULT_CONF = float(os.environ.get("GARUD_CV_CONF", "0.35"))

_model_cache: dict[str, YOLO] = {}


def get_model(weights_path: str = DEFAULT_WEIGHTS) -> YOLO:
    """Load once per process, not once per request -- YOLO(weights) does real
    disk + CUDA/CPU init work that a request handler shouldn't repeat."""
    if weights_path not in _model_cache:
        if not Path(weights_path).exists():
            raise FileNotFoundError(
                f"No weights at {weights_path}. Run train.py (see README.md) "
                "or point GARUD_CV_WEIGHTS at an existing .pt file."
            )
        _model_cache[weights_path] = YOLO(weights_path)
    return _model_cache[weights_path]
