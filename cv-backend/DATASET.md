# Dataset

This document records exactly which dataset(s) this module targets, and exactly
what data the checkpoint currently committed to this repo (`models/best.pt`,
`metrics.json`) was actually trained on. As of the run described in
[What was actually run](#what-was-actually-run) below, **these are now the same
dataset** — real photos downloaded via the Roboflow SDK, not synthetic data —
though see that section for exactly how much of it and for how long.

## Primary dataset (real, downloaded, and trained on)

| Field | Value |
|---|---|
| Name | **Aerial Person Detection Dataset** |
| Roboflow project | [`aerial-person-detection/aerial-person-detection`](https://universe.roboflow.com/aerial-person-detection/aerial-person-detection), version 3 |
| Owner/workspace | Aerial Person Detection |
| Task | Object Detection |
| Images | **7,015** total on the Universe project page; **6,445 train / 545 valid / 0 test** in the actual version-3 YOLOv8 export downloaded here (`du -sh data/` = 1.6GB) |
| License | **CC BY 4.0** (attribution required) |
| Classes actually in the export (6) | `bicycle`, `bus`, `car`, `motorcycle`, `person`, `truck` — see [`data/data.yaml`](data/data.yaml). The Universe project *page* lists 12 classes (`pedestrian`, `van`, `tricycle`, `awning-tricycle`, `ignored regions`, `others` among them); the actual version-3 export only contains these 6. Recorded here because it's a real discrepancy between the listing page and the downloadable artifact, not something to paper over. |
| Perspective | Overhead / drone (aerial) — matches Garud Copters' drone-mounted camera use case |
| Why this one | Meets the ">500 images, clean annotations" bar with a wide margin, overhead perspective matches an actual disaster-drone camera angle, and covers both target categories the brief asks for (`person`, and 5 separate vehicle-type classes rather than one merged "vehicle" — `app/agent.py`'s `VEHICLE_CLASSES` set treats any of them as vehicle for severity purposes). Its own "Ways to use" section on Roboflow explicitly lists Search and Rescue Operations as an intended use case. |
| Checked | 2026-09-06, via Roboflow Universe (page contents fetched live, not from memory); downloaded 2026-09-07 |

Cite as (from the project's own citation block):

```bibtex
@misc{ aerial-person-detection_dataset,
  title = { Aerial Person Detection Dataset },
  type = { Open Source Dataset },
  author = { Aerial Person Detection },
  howpublished = { \url{ https://universe.roboflow.com/aerial-person-detection/aerial-person-detection } },
  url = { https://universe.roboflow.com/aerial-person-detection/aerial-person-detection },
  journal = { Roboflow Universe },
  publisher = { Roboflow },
  year = { 2026 },
}
```

### Debris — known gap, not invented

The brief asks for a third class, **debris**. No single public Roboflow dataset was
found that combines aerial people+vehicle detection *and* a clean, 500+ image debris/rubble
class. The closest real candidate found and verified live:

| Field | Value |
|---|---|
| Name | Disaster Scene Box Ground Truth |
| Roboflow project | [`leeely-campus-technion-ac-il/disaster-scene-box-ground-truth`](https://universe.roboflow.com/leeely-campus-technion-ac-il/disaster-scene-box-ground-truth) |
| Images | 443 (verified) — under the 500-image bar this brief sets |
| License | CC BY 4.0 |
| Classes | `damaged or collapsed building`, `machinery`, `personnel`, `rubble debris`, `standing building` |
| Status | 0 published dataset *versions* on Roboflow at time of check, i.e. no generated export exists yet to pull via the SDK — would need to be versioned/exported from the Roboflow UI first, or trained via the raw images+annotations. |

**Decision:** ship `person` + 5 vehicle-type classes as the production classes fine-tuned
in this repo (confirmed: the real, downloaded version-3 export has no debris/rubble class
of any kind, so this isn't a config gap — the data itself doesn't have it), and track
`debris` as a documented roadmap item — either (a) once the Disaster Scene Box dataset (or
an equivalent) clears the 500-image/clean-annotation bar, merge its `rubble debris` class
in as a third head, or (b) combine multiple debris-focused sources via Roboflow's
dataset-merge feature. `app/agent.py`'s `DEBRIS_CLASSES` set and `inference.py`'s debris
color are already wired up and waiting for that class to exist — it's a retrain, not a
code change.

## How to pull the real dataset

```bash
export ROBOFLOW_API_KEY=your_key_here   # https://app.roboflow.com/settings/api
python scripts/download_dataset.py
```

`scripts/download_dataset.py` uses the official `roboflow` Python SDK to pull
`aerial-person-detection/aerial-person-detection` version 3 in YOLOv8 format into
`data/`, overwriting the placeholder folders below with real images/labels and a
generated `data.yaml`. See the script for the exact workspace/project/version slug.

## Fallback: placeholder structure (what ships when no API key is present)

Per the brief's own fallback instruction, `data/` ships as an empty, YOLOv8-ready
folder skeleton whenever `ROBOFLOW_API_KEY` isn't set, so `train.py` runs unmodified
the moment a real dataset (from the command above, or manually) is dropped in:

```
data/
  data.yaml
  train/images/  train/labels/
  valid/images/  valid/labels/
  test/images/   test/labels/
```

`data/` itself is gitignored (only `data.yaml` and `.gitkeep` markers are committed) —
1.6GB of images has no reason to live in the repo. Anyone cloning this repo starts from
that placeholder skeleton until they run `scripts/download_dataset.py` themselves.

## What was actually run

Two real, executed training runs happened over the course of building this repo, in order:

1. **First, no `ROBOFLOW_API_KEY` was available.** `models/best.pt`/`metrics.json` were
   produced by an actual `train.py` run against a tiny **synthetic** smoke-test set
   (`scripts/make_smoke_dataset.py` → `data_smoke/`, ~48 generated images with
   programmatically-drawn shapes standing in for person/vehicle/debris). Real numbers from
   a real run, tagged `"run_type": "smoke_test_synthetic_data"` — but it only proved the
   pipeline runs end-to-end, not that the model detects anything real.
2. **Once an API key was provided**, `scripts/download_dataset.py` pulled the real
   7,015-image dataset above (6,445 train / 545 valid), verified by inspecting the actual
   downloaded files (`ls data/train/images | wc -l`, not just trusting the script's exit
   code) — see `runs/detect/production_v2/train_batch0.jpg` for a real annotated-batch
   sample if that run directory is still present locally (`runs/` is gitignored, not
   committed). `train.py` was then run against this **real** data:

   ```
   epochs=6, imgsz=320, batch=16, patience=3, fraction=0.15 (real images, ~15% of train set)
   ```

   Reduced from the brief's 50-epoch/imgsz=640/full-dataset defaults because this machine
   is CPU-only (Apple M2, no CUDA) — the first attempt at full defaults took >16 minutes
   for a single epoch and was killed as impractical for this build session. `models/best.pt`
   and `metrics.json` now reflect **this** run — real photos, real annotations, genuinely
   executed `model.val()` — tagged `"run_type": "production"` with a `note` field spelling
   out exactly what was scaled down and why, so a reader never mistakes a 6-epoch/15%-data
   number for the full spec's result. Actual numbers: **mAP50 = 0.089, mAP50-95 = 0.041,
   precision = 0.36, recall = 0.14** (per-class breakdown in `metrics.json` — `car` is the
   strongest class at this epoch count, `bicycle` is essentially unlearned with only 6
   epochs on 15% of the data). Modest, exactly as expected for 6 epochs on a sixth of the
   data — but real, and visibly working: `inference.py` correctly draws boxes around real
   cars, people, and a motorcycle in held-out validation images at this checkpoint.

To reproduce the full spec's real run: `export ROBOFLOW_API_KEY=...`,
`python scripts/download_dataset.py`, then `python train.py --publish` (defaults are
`--epochs 50 --imgsz 640 --fraction 1.0`) on a GPU — the CPU-only reduction above was a
time constraint of this specific build environment, not a limitation of the code.
