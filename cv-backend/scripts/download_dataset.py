"""
Download the real Garud Copters CV training set from Roboflow Universe.

Dataset: Aerial Person Detection Dataset
Project: aerial-person-detection/aerial-person-detection
License: CC BY 4.0
Images:  7,015 (verified live on 2026-09-06, see ../DATASET.md)

Why this dataset and not something invented: see ../DATASET.md, which records
the exact project checked, its license, image count, and the (documented) gap
around a debris class.

Usage:
    export ROBOFLOW_API_KEY=your_key_here   # https://app.roboflow.com/settings/api
    python scripts/download_dataset.py [--version 3] [--out ../data]

If ROBOFLOW_API_KEY is not set, this script exits cleanly with instructions
instead of crashing — per the brief's fallback instruction, the placeholder
folder structure in data/ is what ships in that case, and train.py is written
to work against it once real files land there.
"""
import argparse
import os
import shutil
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_OUT = SCRIPT_DIR.parent / "data"

# Exact Roboflow Universe coordinates for the dataset documented in DATASET.md.
WORKSPACE = "aerial-person-detection"
PROJECT = "aerial-person-detection"
DEFAULT_VERSION = 3  # latest of the 3 published dataset versions at time of writing


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", type=int, default=DEFAULT_VERSION,
                         help="Roboflow dataset version number to pull")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT,
                         help="Directory to download the YOLOv8-format export into")
    args = parser.parse_args()

    api_key = os.environ.get("ROBOFLOW_API_KEY")
    if not api_key:
        print(
            "ROBOFLOW_API_KEY is not set — nothing to download.\n"
            "Get a free key at https://app.roboflow.com/settings/api, then:\n\n"
            "    export ROBOFLOW_API_KEY=your_key_here\n"
            "    python scripts/download_dataset.py\n\n"
            f"Until then, {args.out} keeps its placeholder train/valid/test\n"
            "skeleton (see DATASET.md) so train.py has somewhere valid to point at.",
            file=sys.stderr,
        )
        return 1

    try:
        from roboflow import Roboflow
    except ImportError:
        print("The `roboflow` package is required: pip install roboflow", file=sys.stderr)
        return 1

    rf = Roboflow(api_key=api_key)
    project = rf.workspace(WORKSPACE).project(PROJECT)
    version = project.version(args.version)

    print(f"Downloading {WORKSPACE}/{PROJECT} v{args.version} (YOLOv8 format) -> {args.out} ...")
    # Roboflow's SDK downloads into a new directory it names itself
    # (e.g. "aerial-person-detection-3"); we then fold that into data/
    # so data/data.yaml + data/train|valid|test match what train.py expects.
    dataset = version.download("yolov8", location=str(args.out.parent / "_rf_download_tmp"))

    tmp_dir = Path(dataset.location)
    for split_src, split_dst in (("train", "train"), ("valid", "valid"), ("test", "test")):
        src = tmp_dir / split_src
        if not src.exists():
            continue
        dst = args.out / split_dst
        for sub in ("images", "labels"):
            (dst / sub).mkdir(parents=True, exist_ok=True)
            src_sub = src / sub
            if src_sub.exists():
                for f in src_sub.iterdir():
                    shutil.copy2(f, dst / sub / f.name)

    # Roboflow's export writes its own data.yaml with correct class names/order —
    # trust that over our placeholder once real data lands.
    rf_yaml = tmp_dir / "data.yaml"
    if rf_yaml.exists():
        shutil.copy2(rf_yaml, args.out / "data.yaml")

    shutil.rmtree(tmp_dir, ignore_errors=True)
    print(f"Done. Real dataset now in {args.out} — train.py can be run as-is.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
