"""
Generate a tiny SYNTHETIC dataset so train.py / inference.py / main.py can be
run and proven end-to-end without a Roboflow API key or a GPU.

This is NOT a stand-in for the real dataset (see ../DATASET.md). It draws
random colored rectangles on blank backgrounds and labels them with the same
3 classes as the real config (person / vehicle / debris) purely so YOLO has
something real to fit its loss against. Treat any metrics produced by
training on this set as a pipeline smoke test, never as a model-quality claim
— train.py and metrics.json both call this out explicitly.

Usage:
    python scripts/make_smoke_dataset.py --n-train 40 --n-val 8
"""
import argparse
import random
from pathlib import Path

import cv2
import numpy as np
import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
OUT_DIR = SCRIPT_DIR.parent / "data_smoke"

CLASS_NAMES = ["person", "vehicle", "debris"]
# Rough visual stand-ins so the three classes are at least separable by shape/size,
# the way a real detector would see distinct silhouettes.
CLASS_SHAPE = {
    0: dict(w=(10, 22), h=(24, 48), color=(60, 180, 220)),   # person: tall & narrow
    1: dict(w=(45, 90), h=(24, 44), color=(80, 200, 90)),    # vehicle: wide & squat
    2: dict(w=(20, 60), h=(15, 40), color=(120, 120, 130)),  # debris: irregular blob-ish box
}
IMG_SIZE = 416


def make_image(rng: random.Random):
    img = np.full((IMG_SIZE, IMG_SIZE, 3), fill_value=(35, 40, 45), dtype=np.uint8)
    # a few background texture blobs so it's not a flat color the model can trivially memorize
    for _ in range(6):
        cx, cy = rng.randint(0, IMG_SIZE), rng.randint(0, IMG_SIZE)
        cv2.circle(img, (cx, cy), rng.randint(5, 30), (45, 50, 55), -1)

    labels = []
    n_objects = rng.randint(1, 5)
    for _ in range(n_objects):
        cls = rng.randint(0, 2)
        shape = CLASS_SHAPE[cls]
        w = rng.randint(*shape["w"])
        h = rng.randint(*shape["h"])
        x0 = rng.randint(0, IMG_SIZE - w)
        y0 = rng.randint(0, IMG_SIZE - h)
        x1, y1 = x0 + w, y0 + h
        cv2.rectangle(img, (x0, y0), (x1, y1), shape["color"], -1)

        # YOLO format: class cx cy w h, all normalized 0-1
        cx_n = (x0 + x1) / 2 / IMG_SIZE
        cy_n = (y0 + y1) / 2 / IMG_SIZE
        w_n = w / IMG_SIZE
        h_n = h / IMG_SIZE
        labels.append(f"{cls} {cx_n:.6f} {cy_n:.6f} {w_n:.6f} {h_n:.6f}")
    return img, labels


def write_split(split: str, n: int, rng: random.Random):
    img_dir = OUT_DIR / split / "images"
    lbl_dir = OUT_DIR / split / "labels"
    img_dir.mkdir(parents=True, exist_ok=True)
    lbl_dir.mkdir(parents=True, exist_ok=True)
    for i in range(n):
        img, labels = make_image(rng)
        name = f"{split}_{i:04d}"
        cv2.imwrite(str(img_dir / f"{name}.jpg"), img)
        (lbl_dir / f"{name}.txt").write_text("\n".join(labels) + "\n")
    print(f"  {split}: {n} images -> {img_dir}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n-train", type=int, default=40)
    parser.add_argument("--n-val", type=int, default=8)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    print(f"Generating synthetic smoke-test dataset in {OUT_DIR} ...")
    write_split("train", args.n_train, rng)
    write_split("valid", args.n_val, rng)

    data_yaml = {
        # No "path" key: Ultralytics then resolves train/val relative to this
        # yaml file's own directory, regardless of the training script's cwd.
        # (Setting "path: ." resolves "." against the *caller's* cwd instead,
        # which silently breaks the moment train.py isn't run from data_smoke/'s
        # own parent -- learned this the hard way, see train.py's run log.)
        "train": "train/images",
        "val": "valid/images",
        "nc": len(CLASS_NAMES),
        "names": {i: n for i, n in enumerate(CLASS_NAMES)},
    }
    (OUT_DIR / "data.yaml").write_text(yaml.dump(data_yaml, sort_keys=False))
    print(f"Wrote {OUT_DIR / 'data.yaml'}")
    print("Done. This is synthetic data for pipeline verification only — see DATASET.md.")


if __name__ == "__main__":
    main()
