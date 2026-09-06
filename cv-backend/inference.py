"""
OpenCV-based inference pipeline: run models/best.pt on a single image, a
video file, or a live webcam stream, drawing boxes with cv2 primitives
directly (not results.plot()) and tracking objects across frames.

Why not just call results.plot(): the brief wants this to demonstrate real
OpenCV usage — reading frames with cv2.VideoCapture, drawing with
cv2.rectangle/cv2.putText, and doing our own simple tracking — the kind of
code you'd actually be extending if you had to add, say, a custom overlay or
a non-YOLO tracker later. results.plot() is a fine one-liner for a demo, but
it hides all of that.

Usage:
    python inference.py --source path/to/image.jpg
    python inference.py --source path/to/video.mp4 --every-n 3
    python inference.py --source 0                      # webcam
"""
import argparse
import time
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO

ROOT = Path(__file__).resolve().parent
DEFAULT_WEIGHTS = ROOT / "models" / "best.pt"

# Confidence threshold: 0.35 rather than Ultralytics' default 0.25.
# Disaster imagery from a drone is exactly the kind of input (motion blur,
# small/occluded people, cluttered backgrounds) that produces more low-
# confidence false positives than a clean benchmark dataset. Raising the bar
# a bit trades a little recall for a lot fewer spurious boxes cluttering the
# operator's view — for a "how many people are down there" tool, a human
# skimming the feed benefits more from fewer wrong boxes than from catching
# every last 0.26-confidence maybe-a-person. It's re-tunable per deployment
# via --conf.
DEFAULT_CONF = 0.35

BOX_COLOR = {
    "person": (60, 180, 220),   # BGR
    # Real dataset ships these as separate classes rather than one merged
    # "vehicle" (see DATASET.md) -- one shared green family, distinguishable
    # from person/debris, individually still readable via the text label.
    "vehicle": (80, 200, 90),
    "car": (80, 200, 90),
    "truck": (60, 170, 80),
    "bus": (50, 150, 70),
    "motorcycle": (100, 210, 110),
    "bicycle": (120, 220, 130),
    "debris": (120, 120, 130),
}
DEFAULT_COLOR = (255, 255, 255)


def draw_detection(frame, xyxy, cls_name, conf, color=None, extra_label=""):
    """Real cv2 drawing — no results.plot(). Box + filled label strip + text."""
    x0, y0, x1, y1 = map(int, xyxy)
    color = color or DEFAULT_COLOR
    cv2.rectangle(frame, (x0, y0), (x1, y1), color, thickness=2)

    label = f"{cls_name} {conf:.2f}{extra_label}"
    (tw, th), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
    label_y0 = max(y0 - th - baseline - 4, 0)
    cv2.rectangle(frame, (x0, label_y0), (x0 + tw + 4, label_y0 + th + baseline + 4), color, thickness=-1)
    cv2.putText(
        frame, label, (x0 + 2, label_y0 + th + 2),
        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), thickness=1, lineType=cv2.LINE_AA,
    )


class CentroidTracker:
    """
    Minimal centroid tracker: matches this frame's detection centroids to the
    nearest still-alive track from recent frames (greedy nearest-neighbor,
    within max_distance px), and gives each a stable integer ID across frames.

    This is deliberately the simple/classic approach (not DeepSORT/ByteTrack)
    -- it needs no extra model or embedding, runs in microseconds, and is
    enough to demonstrate "track objects across frames" for a fixed, mostly-
    non-crossing set of detections like people/vehicles in a drone shot. The
    tradeoff: it can swap IDs when two objects' paths cross close together,
    since it has no appearance model to disambiguate them — acceptable here,
    would need ByteTrack/DeepSORT if identity had to survive occlusion/crossing.
    """

    def __init__(self, max_distance: float = 60.0, max_missed: int = 10):
        self.max_distance = max_distance
        self.max_missed = max_missed
        self.next_id = 0
        self.tracks: dict[int, dict] = {}  # id -> {centroid, missed}

    def update(self, centroids: list[tuple[float, float]]) -> list[int]:
        assigned_ids = [None] * len(centroids)
        unmatched_track_ids = set(self.tracks.keys())

        # greedy nearest-neighbor matching
        pairs = []
        for i, c in enumerate(centroids):
            for tid, t in self.tracks.items():
                d = np.hypot(c[0] - t["centroid"][0], c[1] - t["centroid"][1])
                if d <= self.max_distance:
                    pairs.append((d, i, tid))
        pairs.sort(key=lambda p: p[0])

        used_dets, used_tracks = set(), set()
        for d, i, tid in pairs:
            if i in used_dets or tid in used_tracks:
                continue
            assigned_ids[i] = tid
            self.tracks[tid]["centroid"] = centroids[i]
            self.tracks[tid]["missed"] = 0
            used_dets.add(i)
            used_tracks.add(tid)
            unmatched_track_ids.discard(tid)

        # new tracks for unmatched detections
        for i, c in enumerate(centroids):
            if assigned_ids[i] is None:
                self.tracks[self.next_id] = {"centroid": c, "missed": 0}
                assigned_ids[i] = self.next_id
                self.next_id += 1

        # age out unmatched tracks, drop stale ones
        for tid in unmatched_track_ids:
            self.tracks[tid]["missed"] += 1
            if self.tracks[tid]["missed"] > self.max_missed:
                del self.tracks[tid]

        return assigned_ids


def run_on_image(model: YOLO, image_path: str, conf: float, out_path: str | None):
    frame = cv2.imread(image_path)
    if frame is None:
        raise FileNotFoundError(f"Could not read image: {image_path}")

    results = model.predict(frame, conf=conf, verbose=False)[0]
    for box in results.boxes:
        xyxy = box.xyxy[0].tolist()
        cls_id = int(box.cls[0])
        cls_name = model.names[cls_id]
        conf_val = float(box.conf[0])
        draw_detection(frame, xyxy, cls_name, conf_val, BOX_COLOR.get(cls_name))

    out_path = out_path or str(Path(image_path).with_stem(Path(image_path).stem + "_detected"))
    cv2.imwrite(out_path, frame)
    print(f"{len(results.boxes)} detections -> {out_path}")


def run_on_video(model: YOLO, source: str, conf: float, every_n: int, out_path: str | None, show: bool):
    # source "0" (a string, from argparse) means webcam index 0
    cap_source = int(source) if source.isdigit() else source
    cap = cv2.VideoCapture(cap_source)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video source: {source}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    writer = None
    if out_path:
        writer = cv2.VideoWriter(out_path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))

    tracker = CentroidTracker()
    frame_idx = 0
    last_annotated = None
    t0 = time.time()

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        # Frame-sampling: only run the (relatively expensive) YOLO forward
        # pass every Nth frame, and reuse the last annotated frame for the
        # ones in between. This is the standard trick for real-time video on
        # modest hardware -- detections don't meaningfully change frame-to-
        # frame at 25-30fps, so paying the inference cost every frame is
        # mostly wasted compute. --every-n 1 disables this (process every
        # frame) when accuracy matters more than throughput.
        if frame_idx % every_n == 0:
            results = model.predict(frame, conf=conf, verbose=False)[0]
            centroids = []
            boxes_info = []
            for box in results.boxes:
                xyxy = box.xyxy[0].tolist()
                x0, y0, x1, y1 = xyxy
                centroids.append(((x0 + x1) / 2, (y0 + y1) / 2))
                boxes_info.append((xyxy, model.names[int(box.cls[0])], float(box.conf[0])))

            track_ids = tracker.update(centroids)
            annotated = frame.copy()
            for (xyxy, cls_name, conf_val), tid in zip(boxes_info, track_ids):
                draw_detection(annotated, xyxy, cls_name, conf_val, BOX_COLOR.get(cls_name), extra_label=f" id{tid}")
            last_annotated = annotated
        else:
            annotated = last_annotated if last_annotated is not None else frame

        if writer:
            writer.write(annotated)
        if show:
            cv2.imshow("Garud Copters CV", annotated)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

        frame_idx += 1

    elapsed = time.time() - t0
    print(f"Processed {frame_idx} frames in {elapsed:.1f}s ({frame_idx / max(elapsed, 1e-6):.1f} fps effective, every_n={every_n})")

    cap.release()
    if writer:
        writer.release()
    if show:
        cv2.destroyAllWindows()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--weights", default=str(DEFAULT_WEIGHTS))
    parser.add_argument("--source", required=True, help="image/video path, or webcam index e.g. 0")
    parser.add_argument("--conf", type=float, default=DEFAULT_CONF)
    parser.add_argument("--every-n", type=int, default=3, help="process every Nth frame (video only)")
    parser.add_argument("--out", default=None, help="output path for annotated image/video")
    parser.add_argument("--show", action="store_true", help="display frames in a window while processing")
    args = parser.parse_args()

    model = YOLO(args.weights)

    ext = Path(args.source).suffix.lower()
    image_exts = {".jpg", ".jpeg", ".png", ".bmp"}
    if ext in image_exts:
        run_on_image(model, args.source, args.conf, args.out)
    else:
        run_on_video(model, args.source, args.conf, args.every_n, args.out, args.show)


if __name__ == "__main__":
    main()
