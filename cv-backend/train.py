"""
Fine-tune YOLOv8 on the Garud Copters disaster-response dataset.

This is TRANSFER LEARNING, not training from scratch: we start from
`yolov8n.pt`, a checkpoint Ultralytics already pretrained on COCO (80 classes,
~118k images). Its early/mid conv layers already know general-purpose visual
features — edges, textures, shapes — so fine-tuning on our much smaller
disaster dataset only has to adapt the later layers and detection head to our
3 classes (person / vehicle / debris), instead of learning vision from zero.
That's what makes a few thousand aerial images enough to get a usable model.

Why yolov8n (nano) and not a bigger variant (s/m/l/x):
  - Garud Copters' payload is a drone: inference needs to run on-board or on
    a lightweight ground-station GPU, in near real-time on video, not a
    server-room GPU. Nano is ~3.2M params vs ~11M+ for `s` and up — the
    accuracy gap on a 3-class problem this constrained is small, and the
    speed/memory win is large.
  - We're fine-tuning on a dataset in the thousands-of-images range, not
    hundreds of thousands. Larger backbones need more data to actually use
    their extra capacity, or they just overfit faster on a small set.
  - It's also just the right default to prototype fast; swapping to yolov8s
    later is a one-line change (`--weights yolov8s.pt`) if accuracy turns out
    to be the bottleneck rather than latency.

Why these hyperparameters:
  - epochs=50, patience=10: early stopping on 10 epochs of no val-mAP
    improvement. 50 is enough headroom for a nano model to converge on a
    few-thousand-image set without babysitting it; patience=10 stops us
    wasting compute once it plateaus, and guards against overfitting a small
    dataset by training indefinitely.
  - imgsz=640: Ultralytics' standard YOLOv8 training resolution — matches
    what yolov8n.pt was pretrained at, and is the resolution its anchor-free
    head and default augmentation pipeline were tuned around. Going lower
    would speed up training but cost small-object recall (a person from
    30m altitude is already a small object).
  - batch=16: a safe default that fits on a single consumer GPU (or CPU, just
    slower) at imgsz=640 without tuning gradient accumulation.
  - Augmentation is left at Ultralytics' defaults (Mosaic, horizontal flip,
    HSV jitter, etc.) deliberately: aerial disaster imagery has no fixed
    "up" that mosaic/flip would violate (unlike, say, text), and the default
    recipe is already tuned for exactly this kind of general object dataset.
    Aerial-specific augmentation (rotation-heavy, since drones aren't level)
    would be the first thing to revisit if this were going to production.

Usage:
    # real dataset (after scripts/download_dataset.py has populated data/)
    python train.py

    # tiny synthetic smoke test (no GPU/API key needed) — see DATASET.md
    python scripts/make_smoke_dataset.py
    python train.py --data data_smoke/data.yaml --epochs 3 --imgsz 320 \\
        --batch 8 --patience 3 --name smoke_test --run-type smoke_test_synthetic_data
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

from ultralytics import YOLO

ROOT = Path(__file__).resolve().parent


def dataset_is_empty(data_yaml: Path) -> bool:
    """train/images having zero files means only the placeholder skeleton is
    present (see DATASET.md) — fail fast with a clear message instead of
    letting Ultralytics error out deep in its dataloader."""
    import yaml as _yaml

    cfg = _yaml.safe_load(data_yaml.read_text())
    train_dir = data_yaml.parent / cfg["train"]
    if not train_dir.exists():
        return True
    return not any(train_dir.iterdir())


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--weights", default="yolov8n.pt", help="pretrained checkpoint to fine-tune from")
    parser.add_argument("--data", default=str(ROOT / "data" / "data.yaml"), help="path to data.yaml")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--patience", type=int, default=10, help="early-stopping patience, epochs")
    parser.add_argument("--project", default=str(ROOT / "runs" / "detect"), help="Ultralytics run output root")
    parser.add_argument("--name", default="train", help="run name, becomes <project>/<name>/")
    parser.add_argument("--run-type", default="production",
                         choices=["production", "smoke_test_synthetic_data"],
                         help="tagged into metrics.json so results are never mistaken for real accuracy numbers")
    parser.add_argument("--publish", action="store_true",
                         help="also copy best.pt -> models/best.pt and metrics.json -> repo root "
                              "(the 'official' checkpoint main.py/inference.py load by default)")
    args = parser.parse_args()

    data_yaml = Path(args.data).resolve()
    if not data_yaml.exists():
        sys.exit(f"No data.yaml at {data_yaml}. See DATASET.md.")
    if dataset_is_empty(data_yaml):
        sys.exit(
            f"{data_yaml.parent} has no training images yet — this is the placeholder "
            "skeleton described in DATASET.md, not a real dataset.\n\n"
            "Either:\n"
            "  export ROBOFLOW_API_KEY=... && python scripts/download_dataset.py   # real data\n"
            "  python scripts/make_smoke_dataset.py                                # tiny synthetic smoke test\n"
        )

    print(f"Loading pretrained (COCO) checkpoint: {args.weights}")
    model = YOLO(args.weights)  # starts from COCO weights -> this whole call is the transfer-learning step

    print(
        f"Fine-tuning on {data_yaml} for {args.epochs} epochs "
        f"(imgsz={args.imgsz}, batch={args.batch}, patience={args.patience}) ..."
    )
    model.train(
        data=str(data_yaml),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        patience=args.patience,
        project=args.project,
        name=args.name,
        exist_ok=True,
        # augmentation params intentionally omitted -> Ultralytics defaults
        # (Mosaic, flipud/fliplr, HSV jitter, etc.) apply, see module docstring.
    )

    run_dir = Path(model.trainer.save_dir)
    best_pt = run_dir / "weights" / "best.pt"

    # Re-load the best checkpoint (not the last epoch) for validation, same as
    # `yolo val` would — this is what actually gets reported/shipped.
    print(f"Validating best checkpoint: {best_pt}")
    val_model = YOLO(str(best_pt))
    metrics = val_model.val(data=str(data_yaml))

    metrics_out = {
        "run_type": args.run_type,
        "weights": str(best_pt),
        "data_yaml": str(data_yaml),
        "epochs_requested": args.epochs,
        "imgsz": args.imgsz,
        "batch": args.batch,
        "patience": args.patience,
        # These four are the real numbers the brief asks for, pulled straight
        # out of Ultralytics' own DetMetrics object — nothing hand-typed.
        "mAP50": float(metrics.box.map50),
        "mAP50-95": float(metrics.box.map),
        "precision": float(metrics.box.mp),
        "recall": float(metrics.box.mr),
        "per_class_mAP50-95": {
            val_model.names[i]: float(v) for i, v in enumerate(metrics.box.maps)
        },
    }
    if args.run_type == "smoke_test_synthetic_data":
        metrics_out["note"] = (
            "Trained on scripts/make_smoke_dataset.py synthetic shapes, not the real "
            "aerial-person-detection dataset in DATASET.md. These numbers prove the "
            "train/val pipeline runs end-to-end; they are not a model-quality claim."
        )

    metrics_path = run_dir / "metrics.json"
    metrics_path.write_text(json.dumps(metrics_out, indent=2))
    print(f"Wrote {metrics_path}")
    print(json.dumps(metrics_out, indent=2))

    if args.publish:
        models_dir = ROOT / "models"
        models_dir.mkdir(exist_ok=True)
        shutil.copy2(best_pt, models_dir / "best.pt")
        shutil.copy2(metrics_path, ROOT / "metrics.json")
        print(f"Published: {models_dir / 'best.pt'}, {ROOT / 'metrics.json'}")


if __name__ == "__main__":
    main()
