# Dataset

This document records exactly which dataset(s) this module targets, and exactly
what data the checkpoint currently committed to this repo (`models/best.pt`,
`metrics.json`) was actually trained on. These are two different things —
see [Honesty note](#honesty-note-what-was-actually-run) at the bottom before
citing any number from this repo.

## Primary target dataset (real, verified on Roboflow Universe)

| Field | Value |
|---|---|
| Name | **Aerial Person Detection Dataset** |
| Roboflow project | [`aerial-person-detection/aerial-person-detection`](https://universe.roboflow.com/aerial-person-detection/aerial-person-detection) |
| Owner/workspace | Aerial Person Detection |
| Task | Object Detection |
| Images | **7,015** (verified on the project page, 3 published dataset versions) |
| License | **CC BY 4.0** (attribution required) |
| Classes (12) | `car`, `truck`, `bus`, `bicycle`, `people`, `pedestrian`, `van`, `motor`, `tricycle`, `awning-tricycle`, `ignored regions`, `others` |
| Perspective | Overhead / drone (aerial) — matches Garud Copters' drone-mounted camera use case |
| Why this one | Meets the ">500 images, clean annotations" bar with a wide margin (7,015 images), overhead perspective matches an actual disaster-drone camera angle, and the label set covers both target categories the brief asks for (`people` → **person** class, `car`/`truck`/`bus`/`van`/`motor`/`bicycle`/`tricycle` → **vehicle** classes). Its own "Ways to use" section on Roboflow explicitly lists Search and Rescue Operations as an intended use case. |
| Checked | 2026-09-06, via Roboflow Universe (page contents fetched live, not from memory) |

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

**Decision:** ship `person` + `vehicle` as the two production classes fine-tuned in this
repo, and track `debris` as a documented roadmap item — either (a) once the
Disaster Scene Box dataset (or an equivalent) clears the 500-image/clean-annotation bar,
merge its `rubble debris` class in as a third head, or (b) combine multiple debris-focused
sources via Roboflow's dataset-merge feature. `data.yaml` already reserves class index `2`
for `debris` so this is a config change + retrain, not a code change — see
[`data/data.yaml`](data/data.yaml).

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
folder skeleton so `train.py` runs unmodified the moment a real dataset (from the
command above, or manually) is dropped in:

```
data/
  data.yaml
  train/images/  train/labels/
  valid/images/  valid/labels/
  test/images/   test/labels/
```

## Honesty note: what was actually run

**No `ROBOFLOW_API_KEY` was available in the environment this repo was built in**, so
the 7,015-image real dataset above was identified and documented, but never
downloaded or trained on here. To avoid the cardinal sin this brief explicitly warns
against — reporting invented metrics as if they were real — `models/best.pt` and
`metrics.json` in this repo were instead produced by an **actual, executed** training
run of `train.py` against a tiny synthetic smoke-test set
(`scripts/make_smoke_dataset.py` → `data_smoke/`, ~48 generated images with
programmatically-drawn "person"/"vehicle" boxes). That run is real — the numbers in
`metrics.json` are that run's genuine `model.val()` output — but it proves the
*pipeline* works end-to-end, not that the model detects real people or vehicles well.
`metrics.json` says `"run_type": "smoke_test_synthetic_data"` for exactly this reason.

To get real, reportable accuracy numbers: set `ROBOFLOW_API_KEY`, run
`scripts/download_dataset.py`, then `python train.py` with the default (real) config
described in [README.md](README.md#training).
