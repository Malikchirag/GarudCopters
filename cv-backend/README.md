# Garud Copters CV

Disaster-response object detection + agentic incident reporting, built on top of
the Garud Copters drone platform. Detects **people**, **vehicles**, and (partially —
see [Known gaps](#known-gaps)) **debris** in aerial/disaster imagery with a
fine-tuned YOLOv8 model, serves it through FastAPI, and runs a LangGraph agent
on top that turns raw detections into a severity assessment and a plain-
language incident report a human operator can act on.

This is the ML/backend half of the project — `../src` is the existing React
frontend this repo started as.

## What it does

1. A drone (or any camera) captures aerial footage of a disaster scene.
2. YOLOv8, fine-tuned from COCO weights, detects people/vehicles/debris per frame.
3. FastAPI exposes that over HTTP for a single image or a video.
4. A LangGraph agent takes those detections, applies rule-based severity logic
   (not LLM judgment — see [Step 5](#step-5-why-severity-is-rule-based-not-llm-decided)),
   and asks Claude to write a short plain-language summary, then recommends a
   concrete next action ("dispatch rescue team" vs "continue monitoring").

## Architecture

```
Roboflow Universe dataset
        |  (scripts/download_dataset.py, YOLOv8 format)
        v
   data/ (train/valid/test, images+labels)
        |  (train.py: transfer learning from yolov8n.pt)
        v
   models/best.pt  +  metrics.json
        |
        |            +-------------------------+
        +----------->| FastAPI (app/main.py)    |
        |            |  GET  /health            |
        |            |  POST /detect/image      |
        |            |  POST /detect/video      |
        |            |  POST /report ---------- +--+
        |            +-------------------------+   |
        |                                            v
        |                              LangGraph agent (app/agent.py)
        |                              analyze_detections -> assess_severity
        |                                -> [any objects?] -> generate_report (Claude)
        |                                                   -> recommend_action -> report
        v
   inference.py (standalone OpenCV pipeline: image/video/webcam,
                  cv2.rectangle/putText drawing, centroid tracking)
```

## Real dataset & results

See [DATASET.md](DATASET.md) for the full, source-checked writeup, including exactly
what was downloaded and run and why. Short version:

- **Dataset**: [Aerial Person Detection Dataset](https://universe.roboflow.com/aerial-person-detection/aerial-person-detection)
  on Roboflow Universe, version 3 — CC BY 4.0, overhead/drone perspective. The actual
  downloaded export is **6,445 train / 545 valid real images** across 6 classes
  (`bicycle`, `bus`, `car`, `motorcycle`, `person`, `truck`). `scripts/download_dataset.py`
  pulls it via the Roboflow SDK once `ROBOFLOW_API_KEY` is set.
- **`models/best.pt` / [`metrics.json`](metrics.json) are trained on this real data**
  (not synthetic — an earlier build of this repo shipped a synthetic-data smoke-test
  checkpoint before a Roboflow key was available; DATASET.md documents both runs).
  Reduced from the brief's 50-epoch/imgsz=640/full-dataset spec to
  `epochs=6, imgsz=320, fraction=0.15` because this build machine is CPU-only (no CUDA)
  — a full-default run was timed at >16 min for a *single* epoch and wasn't practical
  for this session. `metrics.json` tags this `"run_type": "production"` with a `note`
  field spelling out the reduction so it's never mistaken for the full-spec result.
  **Actual numbers**: mAP50 = **0.089**, mAP50-95 = **0.041**, precision = **0.36**,
  recall = **0.14** — modest, as expected for 6 epochs on 15% of the data, but real:
  `car` is already the strongest class (mAP50-95 = 0.167), and `inference.py` visibly
  draws correct boxes around real cars, people, and a motorcycle in held-out validation
  images at this checkpoint.
- To reproduce the full spec's real run: `export ROBOFLOW_API_KEY=...`, run
  `python scripts/download_dataset.py`, then `python train.py --publish` (defaults are
  `--epochs 50 --imgsz 640 --fraction 1.0`) on a GPU.

### Known gaps

- **Debris** has no code gap — `app/agent.py`'s `DEBRIS_CLASSES` and `inference.py`'s
  debris color are already wired up — but the real dataset's actual downloaded export has
  no debris/rubble class at all (confirmed by inspecting `data/data.yaml` after download,
  not assumed from the Universe listing page — see DATASET.md for the closest real
  candidate dataset found and why it didn't clear the bar). Production classes are
  currently `person` + 5 vehicle types; debris support is a documented roadmap item.
- **6 epochs / 15% of the training data**, not the brief's 50-epoch/full-dataset spec —
  a CPU-only build-machine constraint, not a code limitation (see above).

## Tech stack

- **YOLOv8** / **Ultralytics** — detection model + training/val loop
- **PyTorch** — underlying deep learning framework Ultralytics runs on
- **OpenCV** — video I/O, frame drawing, centroid tracking (`inference.py`)
- **FastAPI** — HTTP serving layer
- **Docker** — containerized deployment
- **LangGraph** — agentic pipeline (severity assessment -> LLM report -> recommendation)
- **Roboflow** — dataset hosting/versioning + Python SDK for download

## Repo layout

```
cv-backend/
  DATASET.md              dataset provenance, license, honesty note
  data/                   REAL dataset target (placeholder skeleton until populated)
  data_smoke/              synthetic smoke-test set (generated, gitignored)
  scripts/
    download_dataset.py    pull the real Roboflow dataset
    make_smoke_dataset.py  generate the synthetic smoke-test set
  train.py                 fine-tune YOLOv8n, writes metrics.json
  inference.py              OpenCV image/video/webcam pipeline + tracking
  app/
    main.py                 FastAPI app
    schemas.py               Pydantic models
    detector.py               shared YOLO model loader
    agent.py                   LangGraph incident-report agent
  models/best.pt            trained checkpoint (committed: the smoke-test one)
  metrics.json               val() output from the run that produced best.pt
  Dockerfile / docker-compose.yml
  requirements.txt
```

## How to run it locally

### 1. Install

```bash
cd cv-backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Get the real dataset (optional — a trained checkpoint already ships)

```bash
export ROBOFLOW_API_KEY=your_key_here   # https://app.roboflow.com/settings/api
python scripts/download_dataset.py
```

### 3. Train

```bash
# Full spec (needs the real dataset from step 2, and ideally a GPU -- see
# DATASET.md for why the checkpoint in this repo used a reduced config instead):
python train.py --publish

# The reduced config actually used to produce this repo's checkpoint
# (CPU-only build machine -- see DATASET.md):
python train.py --epochs 6 --imgsz 320 --fraction 0.15 --patience 3 \
    --name production_v2 --run-type production --publish

# Or a fast synthetic smoke test with no real data at all, just to prove the
# pipeline runs (see DATASET.md -- this is what shipped before a Roboflow key
# was available):
python scripts/make_smoke_dataset.py
python train.py --data data_smoke/data.yaml --epochs 3 --imgsz 320 --batch 8 \
    --patience 3 --name smoke_test --run-type smoke_test_synthetic_data --publish
```

Any of these writes `runs/detect/<name>/metrics.json` and, with `--publish`,
also copies `best.pt` -> `models/best.pt` and the metrics to the repo root
`metrics.json` — see `train.py`'s docstring for why yolov8n / these
hyperparameters / default augmentation were chosen, and its `--fraction` flag
for training on a real (but smaller) slice of the dataset instead of the full set.

### 4. Run inference standalone (OpenCV)

```bash
python inference.py --source path/to/image.jpg
python inference.py --source path/to/video.mp4 --every-n 3 --out annotated.mp4
python inference.py --source 0 --show          # webcam
```

### 5. Run the API

```bash
uvicorn app.main:app --reload --port 8000
```

```bash
curl http://localhost:8000/health

curl -X POST http://localhost:8000/detect/image \
  -F "file=@path/to/image.jpg"

curl -X POST "http://localhost:8000/detect/video?every_n=5" \
  -F "file=@path/to/video.mp4"

# Feed a /detect/image result into the LangGraph agent:
curl -X POST http://localhost:8000/detect/image -F "file=@path/to/image.jpg" \
  | curl -X POST http://localhost:8000/report -H "Content-Type: application/json" -d @-
```

### 6. Docker

> **Not verified live in this build environment** — the build environment's
> disk quota (~9GB total) was too small for Docker Desktop's VM disk plus a
> `python:3.10-slim` + torch/opencv image; the first build attempt filled the
> disk and crashed the Docker daemon entirely. Docker was removed from that
> machine rather than fight its disk budget, since Docker itself isn't
> central to this module (the CV/agent pipeline is, and that's verified —
> see the rest of this README). The Dockerfile/docker-compose.yml below are
> written correctly and got through the `apt-get` layer successfully before
> running out of space on `pip install`; they just haven't had a real
> `docker build && docker run` + `/health` check on a machine with normal
> disk headroom. That's the one remaining thing to confirm before calling
> Step 6 done.

```bash
docker compose up --build
curl http://localhost:8000/health
```

or without compose:

```bash
docker build -t garud-copters-cv .
docker run -p 8000:8000 -v $(pwd)/models:/app/models:ro garud-copters-cv
```

## Step 5: why severity is rule-based, not LLM-decided

`app/agent.py` follows the same pattern as this codebase's other LangGraph
agent (`../v2/api/app/context/agent.py`, Aegis AI's threat-analysis agent):
the LLM only writes prose (the plain-language summary). Severity and the
recommended action are deterministic Python rules, because for a tool whose
output can trigger "dispatch a rescue team," the decision that matters has to
be auditable and reproducible — not something that can vary because an LLM
was prompted slightly differently. See `app/agent.py`'s module docstring and
`ACTION_RULES` table for the exact logic, and its conditional edge
(`has_objects`) for the branching: zero detections skips the LLM call
entirely rather than paying latency/cost to narrate an empty frame.
