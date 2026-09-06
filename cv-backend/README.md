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

See [DATASET.md](DATASET.md) for the full, source-checked writeup. Short version:

- **Target dataset**: [Aerial Person Detection Dataset](https://universe.roboflow.com/aerial-person-detection/aerial-person-detection)
  on Roboflow Universe — 7,015 images, CC BY 4.0, overhead/drone perspective,
  person + vehicle classes. `scripts/download_dataset.py` pulls it via the
  Roboflow SDK once `ROBOFLOW_API_KEY` is set.
- **No Roboflow/GPU access was available in the environment this repo was
  built in.** So the numbers actually committed in [`metrics.json`](metrics.json)
  and the checkpoint in `models/best.pt` come from a real, executed
  `train.py` run — but against a small **synthetic smoke-test set**
  (`scripts/make_smoke_dataset.py`), not the real dataset above. This proves
  the training/inference/serving pipeline genuinely works end-to-end; it is
  **not** a claim about real-world detection accuracy. `metrics.json` tags
  itself `"run_type": "smoke_test_synthetic_data"` for exactly this reason —
  see [DATASET.md's honesty note](DATASET.md#honesty-note-what-was-actually-run).
- To get real, reportable numbers: `export ROBOFLOW_API_KEY=...`, run
  `python scripts/download_dataset.py`, then `python train.py --publish`.
  That overwrites `models/best.pt` and `metrics.json` with a genuine
  production run against the real 7,015-image dataset.

### Known gaps

- **Debris** is reserved as class index 2 in `data/data.yaml` but the primary
  dataset doesn't include it (see DATASET.md for the closest real dataset
  found and why it didn't clear the bar). Fine-tuning currently only produces
  a 2-class (person/vehicle) production model; debris support is a
  documented roadmap item, not a silently-missing feature.

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

### 2. Get a real dataset (optional — a smoke-test checkpoint already ships)

```bash
export ROBOFLOW_API_KEY=your_key_here   # https://app.roboflow.com/settings/api
python scripts/download_dataset.py
```

### 3. Train

```bash
# Real run (needs the real dataset from step 2, and ideally a GPU):
python train.py --publish

# Or the fast synthetic smoke test used to produce the checkpoint in this repo:
python scripts/make_smoke_dataset.py
python train.py --data data_smoke/data.yaml --epochs 3 --imgsz 320 --batch 8 \
    --patience 3 --name smoke_test --run-type smoke_test_synthetic_data --publish
```

Either way this writes `runs/detect/<name>/metrics.json` and, with
`--publish`, also copies `best.pt` -> `models/best.pt` and the metrics to the
repo root `metrics.json` — see `train.py`'s docstring for why yolov8n /
these hyperparameters / default augmentation were chosen.

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
