# Garud Copters — Project Context

This file is read automatically at the start of every Claude Code session in
this repo. It exists so a fresh session doesn't have to re-derive what this
project is, what's already built, and what's still open — read it before
assuming anything about project state.

## What this repo is

Two independent halves in one repo:

1. **`src/` — the original React frontend** ("Drone_DM Client"): a 3D-animated
   disaster-management dashboard. React 19 + Vite 6 + Spline (3D) + Chart.js.
   Pre-existing, not touched by the CV work below.
2. **`cv-backend/` — Garud Copters CV**: a Python ML/backend module added
   later. Disaster-response object detection (YOLOv8) + a LangGraph agent
   that turns detections into a severity assessment and plain-language
   incident report. Fully documented in [`cv-backend/README.md`](cv-backend/README.md)
   and [`cv-backend/DATASET.md`](cv-backend/DATASET.md) — read those two
   before touching `cv-backend/`, they're the source of truth on what's real
   vs. reduced-scope.

The two halves aren't wired together yet — the frontend doesn't call
`cv-backend`'s API. That's a known open item (see Known gaps below).

## cv-backend build history (commits, in order)

The module was built incrementally, one real step at a time, each verified
before moving on — not written all at once and assumed to work:

1. `Garud Copters CV: scaffold dataset structure + DATASET.md` — placeholder
   `data/` skeleton + documented the real target dataset on Roboflow Universe
2. `Garud Copters CV: YOLOv8 fine-tuning script + synthetic smoke-test dataset`
   — `train.py` (transfer learning from `yolov8n.pt`) + a synthetic dataset
   generator to prove the pipeline runs without needing real data/API keys yet
3. `Garud Copters CV: OpenCV inference pipeline with centroid tracking`
4. `Garud Copters CV: FastAPI backend (detect/image, detect/video, health)`
5. `Garud Copters CV: LangGraph incident-reporting agent (Step 5)`
6. `Garud Copters CV: Dockerize (python:3.10-slim, uvicorn on :8000)`
7. `Garud Copters CV: README`
8. `Garud Copters CV: basic API tests`
9. `Garud Copters CV: add requirements-dev.txt for pytest/httpx`
10. `Garud Copters CV: fix data.yaml path resolution, commit smoke-test run`
    — first real executed training run (synthetic data, no Roboflow key yet)
11. `Fix pip timeout in Docker build + train.py run-dir leak` — bugs found
    while actually running things, not caught by just reading the code
12. `README: note Docker build wasn't verified live (disk-constrained build env)`
13. `README: document the new Garud Copters CV backend` — top-level README updated
14. `Fix real-data bugs found while actually training on it, generalize class handling`
    — once a real Roboflow API key was provided, downloading the real dataset
    exposed two real bugs (a data.yaml path assumption, and the agent's
    severity logic assuming a merged "vehicle" class that the real dataset
    doesn't have) — fixed and reverified over HTTP
15. `Train on the real dataset, publish real results` — the real, executed
    production training run; `models/best.pt`/`metrics.json` reflect this

Merged to `main` via [PR #1](https://github.com/Malikchirag/GarudCopters/pull/1).

**Note on commit authorship**: commits do NOT carry `Co-Authored-By: Claude`
trailers — that convention was explicitly removed per repo owner preference.
Don't add it back.

## Tech stack actually used

| Area | Tech |
|---|---|
| Frontend | React 19, Vite 6, React Router DOM, Chart.js / React-Chart.js-2, Spline (`@splinetool/react-spline`, `@splinetool/runtime`), ESLint |
| CV / detection | **YOLOv8** (Ultralytics `8.4.142`), **PyTorch** (`2.14.0`, CPU build — no CUDA on the build machine) |
| Video/image processing | **OpenCV** (`cv2`) — real `cv2.rectangle`/`cv2.putText` drawing, `cv2.VideoCapture`, a hand-rolled centroid tracker (not DeepSORT/ByteTrack — see `inference.py`'s docstring for why) |
| Serving | **FastAPI** + **uvicorn**, Pydantic v2 schemas |
| Agent | **LangGraph** (`StateGraph`), **langchain-anthropic** (`ChatAnthropic`, model `claude-haiku-4-5-20251001`) — pattern deliberately reused from the sibling `cic_ids_project` repo's Aegis AI agent (`v2/api/app/context/agent.py`) |
| Dataset | **Roboflow** Python SDK — real dataset: [`aerial-person-detection/aerial-person-detection`](https://universe.roboflow.com/aerial-person-detection/aerial-person-detection) v3, CC BY 4.0 |
| Testing | pytest + httpx (FastAPI `TestClient`) |
| Containerization | Docker (`python:3.10-slim`) + docker-compose — **written but not verified live** (see Known gaps) |
| Dev env | Python 3.13 venv locally (`cv-backend/.venv`, gitignored) |

## Key facts to not re-litigate

- **The trained checkpoint (`models/best.pt`) is real but intentionally small-scale**: 6 epochs, imgsz=320, on 15% of the real training images — not the brief's 50-epoch/imgsz=640/full-dataset spec. Reduced because the build machine is CPU-only and a full-default run measured >16 min *per epoch*. Real numbers (mAP50=0.089, mAP50-95=0.041, precision=0.36, recall=0.14), documented honestly in `metrics.json`'s `note` field and in `DATASET.md`. Reproducing the full spec is a one-command `python train.py --publish` away on a GPU.
- **Debris detection is a data gap, not a code gap.** The real downloaded dataset has no debris/rubble class at all (confirmed by inspecting the actual export). `app/agent.py`'s `DEBRIS_CLASSES` and `inference.py`'s debris color are already wired and waiting.
- **Docker is unverified live.** Written correctly (confirmed through the `apt-get` layer), but the build environment this was built in had ~9GB total disk and Docker Desktop's VM disk crashed the daemon mid-build. Docker Desktop was subsequently removed from that machine entirely (not needed for CV/ML work). Needs a real `docker build && docker run` + `/health` check on a machine with normal disk headroom.
- **The real dataset's class taxonomy is 6 separate classes** (`bicycle`, `bus`, `car`, `motorcycle`, `person`, `truck`) — not the single merged `person`/`vehicle` scheme the original placeholder `data.yaml` assumed. `app/agent.py`'s `VEHICLE_CLASSES` set handles both schemes generically; don't hardcode `"vehicle"` as a literal class name anywhere new.
- **`data/` (real dataset images) and `data_smoke/` (synthetic) are both gitignored** — only `data/data.yaml` and `.gitkeep` markers are committed. Anyone cloning fresh needs `scripts/download_dataset.py` (real, needs `ROBOFLOW_API_KEY`) or `scripts/make_smoke_dataset.py` (synthetic, no key needed) before `train.py` has anything to train on.

## Known gaps / open items

- Debris class (needs a real dataset with a debris/rubble class merged in — see `DATASET.md` for the closest candidate found)
- Full-spec training run (50 epochs/imgsz=640/full dataset) on a GPU
- Docker build/run verification on a machine with more disk
- Frontend (`src/`) doesn't call `cv-backend`'s API yet — currently two independent halves

## Working conventions for this repo

- **Never fabricate metrics or dataset claims.** Every number in `metrics.json` must come from an actually-executed `model.val()` run — if reduced in scope from a spec, say so explicitly in the same file, the way `run_type`/`note` fields already do.
- **Don't add `Co-Authored-By: Claude` to commit messages** — see authorship note above.
- Before any git history rewrite (`reset --hard`, `filter-branch`, force-push), check `git status` for uncommitted changes first and stash them — a `reset --hard` mistake mid-session once destroyed uncommitted work in the sibling `cic_ids_project` repo and required digging through `git fsck --dangling` to recover it. Don't repeat that.
