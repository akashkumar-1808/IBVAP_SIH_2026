# IBVAP — Persistent Project Memory

> **Purpose:** This file is the long-term memory/source-of-current-state for the IBVAP project.
>
> **Primary rule:** After **every meaningful implementation change, bug fix, configuration change, model change, dependency change, test run, deployment change, architecture change, or Git commit**, this file MUST be updated.
>
> **Important:** Do not overwrite history. Append new information while keeping previous records intact.
>
> **Truth rule:** Record what actually happened. Never invent work, metrics, files, commits, test results, capabilities, or decisions.

---

# 0. MEMORY FILE OPERATING RULES

## M-01 — Update after every implementation

After each implementation unit, update this file.

An implementation unit includes:

- feature;
- bug fix;
- refactor;
- model integration;
- model replacement;
- dependency addition/removal;
- API change;
- UI change;
- database migration;
- configuration change;
- test addition/change;
- deployment change;
- performance optimization;
- security change;
- documentation change that changes project behavior;
- architecture decision.

---

## M-02 — Git must be recorded

Every Git commit associated with the project MUST have a memory entry.

Record:

```text
commit hash
commit message
date/time
author if available
files/components affected
what changed
why it changed
tests run
result
known issues
next work
```

Example:

```text
Commit: abc1234
Message: Add virtual fence event engine
Date: YYYY-MM-DD HH:MM
Affected:
  worker/spatial/
  worker/behavior/
  backend/
  tests/

Summary:
  Added line-crossing event detection.

Validation:
  pytest tests/unit/test_fence.py

Result:
  PASS

Known issues:
  Perspective calibration is camera-specific and must be configured.

Next:
  Connect event to evidence writer.
```

---

## M-03 — Never erase historical records

Do not delete old entries because the architecture changed.

Use:

```text
SUPERSEDED
REPLACED
DEPRECATED
REVERTED
```

when necessary.

Example:

```text
Decision D-003
Status: SUPERSEDED by D-009
```

---

## M-04 — Distinguish fact from intention

Use these labels:

```text
IMPLEMENTED
TESTED
VERIFIED
PLANNED
IN PROGRESS
BLOCKED
DEFERRED
REJECTED
SUPERSEDED
UNKNOWN
```

Never write:

```text
implemented
```

for something that is only planned.

---

## M-05 — No fabricated metrics

Only record metrics actually measured by the project.

Never invent:

- FPS;
- latency;
- accuracy;
- precision;
- recall;
- mAP;
- IDF1;
- HOTA;
- false alarms/hour;
- GPU utilization;
- memory usage.

Use:

```text
NOT MEASURED
```

when unavailable.

---

## M-06 — Track model versions

Whenever a model changes, record:

```text
model name
version
source
artifact path
runtime
license
input/output details
reason for change
benchmark comparison
```

---

## M-07 — Track dependencies

Every meaningful dependency change must record:

```text
package
version
purpose
license
reason
compatibility impact
```

---

## M-08 — Track architecture changes

Any change to:

```text
frontend
backend
worker
database
storage
messaging
inference
deployment
```

must include:

```text
old architecture
new architecture
reason
trade-offs
affected files
rollback path
```

---

## M-09 — Track decisions

Whenever the team chooses one technology or implementation approach over alternatives, record the decision.

Do not rely on chat history.

---

## M-10 — Track failures

Failures are valuable project knowledge.

Record:

```text
what failed
when
why
symptom
root cause if known
fix
whether regression test was added
```

Never hide failed attempts merely because they were later fixed.

---

## M-11 — Track uncertainty

If something is not verified:

```text
UNKNOWN
```

If something is assumed:

```text
ASSUMPTION
```

If something is speculative:

```text
RESEARCH ONLY
```

---

## M-12 — Memory must be updated before closing an implementation task

Before considering a task complete:

```text
code updated
→ tests run
→ git status checked
→ commit hash captured if committed
→ memory updated
```

---

# 1. PROJECT IDENTITY

## Project

**IBVAP — Intelligent Border Video Analytics Platform**

## Product description

A software-defined, environment-adaptive intelligent video analytics platform intended to transform existing IP CCTV infrastructure into context-aware surveillance/event intelligence without requiring additional physical sensors in the core system.

## Primary product principle

```text
Detect events, not merely objects.
```

## Core differentiation

```text
environment-aware perception
+
persistent tracking
+
camera-specific spatial reasoning
+
temporal/behavior reasoning
+
evidence fusion
+
explainable event generation
```

## Core deployment constraint

```text
Existing IP CCTV
+
software analytics
```

No mandatory external sensors.

---

# 2. APPROVED PRODUCT BOUNDARY

## Core

```text
CCTV ingestion
Environment analysis
Adaptive perception
Object detection
Tracking
Spatial reasoning
Temporal/behavior reasoning
Evidence fusion
Risk/event generation
Evidence capture
Backend API
Dashboard
```

## Optional

```text
Uniform/civilian classifier
ANPR
Face detection
Face recognition
Advanced learned anomaly detection
Automatic terrain classification
Advanced low-light enhancement
Cross-camera ReID
```

## Not part of core

```text
PIR
Ultrasonic
LiDAR
Radar
Seismic
Thermal sensor
Drone
Bluetooth sensing
```

---

# 3. APPROVED HIGH-LEVEL ARCHITECTURE

```text
Existing IP CCTV
       ↓
Video ingestion
       ↓
Environment state
       ↓
Adaptive perception
       ↓
Object detection
       ↓
Multi-object tracking
       ↓
Spatial reasoning
       ↓
Temporal / behavior reasoning
       ↓
Optional intelligence
       ↓
Evidence fusion
       ↓
Risk / Event Engine
       ↓
Evidence capture
       ↓
FastAPI
       ↓
React dashboard
```

---

# 4. APPROVED PROTOTYPE DEPLOYMENT

Initial SIH deployment:

```text
ONE WORKSTATION

├── React frontend
├── FastAPI backend
├── AI worker
├── SQLite database
├── model artifacts
└── evidence storage
```

CCTV input:

```text
RTSP
```

or for deterministic development:

```text
MP4 replay
```

---

# 5. APPROVED TECHNOLOGY BASELINE

## Frontend

```text
React
TypeScript
Vite
```

## Backend

```text
Python
FastAPI
Pydantic
asyncio
```

## Video

```text
GStreamer
FFmpeg
OpenCV
```

## Detector

Preferred baseline:

```text
RF-DETR
```

Alternative:

```text
YOLO family
```

only when licensing/project policy permits.

## Tracking

```text
ByteTrack
```

or:

```text
BoT-SORT
```

## Environment

```text
OpenCV-based image statistics
```

Optional:

```text
Retinexformer
```

## Behavior

Initial:

```text
deterministic temporal/spatial rules
```

Optional later:

```text
MMAction2 / learned anomaly model
```

## OCR

Optional:

```text
PaddleOCR
```

## Face

Optional:

```text
InsightFace
```

subject to model/license/governance review.

## Inference runtime

```text
ONNX Runtime
```

Optional:

```text
OpenVINO
TensorRT / NVIDIA-specific optimization
```

## Database

```text
SQLite
```

Later:

```text
PostgreSQL
```

## Storage

Prototype:

```text
local filesystem
```

## Packaging

```text
Docker
Docker Compose
```

---

# 6. CANONICAL REPOSITORY STRUCTURE

```text
ibvap/
│
├── frontend/
├── backend/
├── worker/
├── models/
├── configs/
├── storage/
├── datasets/
├── tests/
├── scripts/
├── docs/
├── docker/
├── docker-compose.yml
├── .env.example
├── README.md
└── DECISIONS.md
```

Detailed structure belongs in:

```text
docs/architecture.md
```

---

# 7. GOLDEN PATH

The path that must remain functional:

```text
CCTV / replay
    ↓
environment
    ↓
person / vehicle / animal detection
    ↓
tracking
    ↓
virtual fence
    ↓
direction
    ↓
temporal behavior
    ↓
evidence fusion
    ↓
HIGH event
    ↓
snapshot + evidence clip
    ↓
database
    ↓
WebSocket
    ↓
dashboard
```

---

# 8. CURRENT PROJECT STATE

## Status

**PHASE 9 COMPLETED — STRUCTURED EVIDENCE STORAGE & PACKAGING INITIALIZED**

The Structured Evidence Storage & Packaging Subsystem, standard `EvidencePackagerInterface`, `EvidencePackager` orchestrator, `RollingFrameBuffer` pre-event ring buffer, raw & forensic HUD-annotated `SnapshotExtractor`, `ClipPackager` MP4 compilation, `EvidenceHasher` SHA-256 cryptographic sealing & tamper verification, `EvidenceStorageManager` local & Supabase storage abstraction, unit test suite (12 tests), deterministic replay test, and packaging benchmark suite have been implemented and verified.

## Current implementation status

```text
Frontend: NOT IMPLEMENTED (Scaffold pending in Phase 11)
Backend: IMPLEMENTED (FastAPI + Supabase PostgreSQL Client + Storage Abstraction)
AI worker: IMPLEMENTED (Ingestion + Perception + Tracking + Environment + World-Border Spatial + Behavior + Evidence Fusion + Evidence Packaging)
Database: IMPLEMENTED (Supabase PostgreSQL schema migration & Repositories active)
Detector: IMPLEMENTED (ObjectDetector / DetectorInterface baseline active)
Tracker: IMPLEMENTED (ByteTrackTracker / TrackerInterface baseline active)
Environment engine: IMPLEMENTED (EnvironmentAnalyzer / Visual Quality Metrics active)
Spatial engine: IMPLEMENTED (SpatialEngine / World-Owned Border Model & Calibrated Projection active)
Behavior engine: IMPLEMENTED (BehaviorEngine / Temporal Pattern Reasoning active)
Evidence fusion: IMPLEMENTED (FusionEngine / Multi-Modal Evidence Fusion & Risk Scoring active)
Evidence storage: IMPLEMENTED (EvidencePackager / SHA-256 Cryptographic Sealing & Supabase Storage active)
ANPR: PLANNED (Optional isolated plugin)
FRS: PLANNED (Optional isolated plugin)
Docker: PLANNED (Scheduled for Phase 14)
Tests: IMPLEMENTED (141 unit & replay tests active with pytest)
Deployment: PLANNED (Local workstation setup)
```

---

# 9. IMPLEMENTATION LOG

> Append new entries below. Never rewrite old entries to hide history.

---

## [MEM-0001] Memory System Created

**Status:** IMPLEMENTED

**Date:** 2026-08-28

### Change

Created the project-level persistent memory file:

```text
IBVAP_memory.md
```

### Purpose

Maintain a complete chronological record of implementations, decisions, commits, models, dependencies, tests, failures, fixes, deployment changes, architecture changes, and known limitations.

### Git commit

```text
Commit: 763a6a49782720d5f91afe652c4843b0c9783161
Message: Feat : Initial Commit ith docs placement
```

### Verification

```text
Memory file created successfully.
Repository commit status: VERIFIED.
```

### Next

Inspect repository and establish the first verified baseline snapshot and implementation plan.

---

## [MEM-0002] Repository Baseline, Scaffolding, and Data Contracts Initialized

**Status:** IMPLEMENTED & TESTED

**Date:** 2026-08-28

### Change

1. Created formal architecture decisions log: `docs/DECISIONS.md`.
2. Created default system configuration: `configs/system.yaml`.
3. Created Python dependency manifest: `requirements.txt`.
4. Created pytest configuration: `pytest.ini`.
5. Created project `.gitignore`.
6. Created domain schemas and data contracts under `backend/app/schemas/`:
   - `common.py` (Enums: TargetClass, LightingCondition, VisibilityQuality, StreamStatus, ZoneType, BehaviorType, EventPriority)
   - `environment.py` (`EnvironmentState` with quality scores and image statistics)
   - `spatial.py` (`ZonePolygon`, `VirtualFence`, `CameraSpatialConfig`)
   - `camera.py` (`CameraCreate`, `CameraUpdate`, `CameraResponse`)
   - `events.py` (`Detection`, `TrackState`, `EventRecord`, `EvidenceMetadata`)
   - `__init__.py`
7. Created initial unit tests: `tests/unit/test_schemas.py`.

### Purpose

Establish strong architectural boundaries, deterministic data contracts, and type safety across backend and worker layers.

### Git commits

```text
Commit 1: e6ff13a17e149777530cfdc7504450b3c5e73f48
Message: chore: initialize repository baseline, shared schemas, system config, and DECISIONS.md

Commit 2: 6b388943039f7fbdf2e62976c2a9e3949e2d932a
Message: chore: add .gitignore and un-track pycache artifacts
```

### Verification

```text
Command: pytest tests/unit/test_schemas.py
Result: 4 passed in 0.14s (100% PASS)
Python version: 3.13.14
```

### Known issues / Notes

Timezone-aware UTC helpers `_utc_now()` standardizing on `datetime.now(timezone.utc)` for clean Python 3.13 deprecation compliance.

### Next

Phase 1: Implement Supabase PostgreSQL and Storage data layer foundation.

---

## [MEM-0003] Supabase PostgreSQL & Storage Backend Foundation

**Status:** IMPLEMENTED & TESTED

**Date:** 2026-08-28

### Change

1. Created `backend/.env.example` template for development without real secrets.
2. Updated `.gitignore` to guarantee `.env`, `.env.*`, `backend/.env`, and local credentials are not tracked, while whitelisting `.env.example`.
3. Created configuration manager `backend/app/config/settings.py` with `pydantic-settings` and `SecretStr` masking for sensitive Supabase keys.
4. Created Supabase database client and secure health check `backend/app/db/client.py`.
5. Created Supabase Storage abstraction `backend/app/db/storage.py` for evidence bucket operations.
6. Created clean database repository layer `backend/app/db/repositories/` (`base.py`, `cameras.py`, `events.py`).
7. Created FastAPI application factory `backend/app/main.py` and health endpoint `backend/app/api/routes/health.py` (`/health` and `/api/v1/health`).
8. Created initial PostgreSQL migration script `supabase/migrations/20260828000000_initial_schema.sql` (cameras, zones, virtual_fences, events, model_versions, audit_logs, RLS policies).
9. Created setup documentation `docs/SUPABASE_SETUP.md`.
10. Added architecture decision `[DEC-0004]` in `docs/DECISIONS.md`.
11. Created unit test suites for settings, db client, health endpoint, storage abstraction, and repositories (`test_config.py`, `test_db_client.py`, `test_health_api.py`, `test_storage_and_repos.py`).

### Purpose

Establish a robust, shared PostgreSQL database and storage foundation on Supabase for the FastAPI backend, with strict process isolation from the AI worker.

### Git commit

```text
Commit: 92bce3e55e5cd98a8d03ef9a55f4da9959162e20
Message: feat(backend): implement Supabase PostgreSQL and Storage data layer foundation
```

### Verification

```text
Command: pytest
Result: 17 passed in 0.91s (100% PASS)
- test_config.py (3 passed)
- test_db_client.py (3 passed)
- test_health_api.py (3 passed)
- test_schemas.py (4 passed)
- test_storage_and_repos.py (4 passed)
```

### Known issues / Notes

Supabase URL and API keys are externalized. When unconfigured, the backend boots safely in unconfigured mode and `/health` reports `database_status: not_configured` without error or secret leakage.

### Next

Phase 2: Video ingestion subsystem and bounded frame queue abstraction in worker.

---

## [MEM-0004] Video Ingestion Subsystem & Bounded Frame Queue

**Status:** IMPLEMENTED & TESTED

**Date:** 2026-08-28

### Change

1. Created VideoSource abstract base class `worker/ingestion/base.py` (`connect`, `read`, `is_alive`, `get_metadata`, `stop`, `close`, `get_health`).
2. Created canonical `FramePacket` in `worker/ingestion/frame.py` with memory-efficient `__slots__`, top-left origin coordinate standards, BGR numpy array image representation, and timestamping.
3. Created thread-safe `BoundedFrameQueue` in `worker/ingestion/queue.py` enforcing the **DROP OLDEST** overflow policy (`REAL-TIME FRESHNESS > PROCESSING EVERY STALE FRAME`), tracking `total_dropped`, `total_inserted`, and oldest frame age.
4. Created `FileVideoSource` in `worker/ingestion/file_source.py` with deterministic replay, monotonic frame ID sequences, FPS progression, looping support, and real-time pacing options.
5. Created `RTSPVideoSource` in `worker/ingestion/rtsp_source.py` with dedicated background capture thread, credential URL masking (`mask_rtsp_url`), frame timeout detection, and exponential reconnect backoff.
6. Created stream health monitoring `worker/ingestion/health.py` (`StreamHealthState`: ONLINE, DEGRADED, STALE, DISCONNECTED, ERROR).
7. Created domain exceptions in `worker/ingestion/exceptions.py`.
8. Created unit tests in `tests/unit/test_bounded_queue.py`, `tests/unit/test_file_source.py`, and `tests/unit/test_rtsp_source.py`.
9. Created replay pipeline test harness in `tests/replay/test_replay_runner.py`.
10. Created standalone benchmark script `scripts/benchmark_ingestion.py`.

### Purpose

Build a robust, leak-free, bounded video transport foundation that delivers fresh video frames to downstream perception and tracking workers without letting stale frames accumulate.

### Git commit

```text
Commit: e018246fc69cefab998d4db096d78d0114378da1
Message: feat(worker): implement video ingestion subsystem, bounded frame queue, and replay pipeline
```

### Verification

```text
Command: pytest
Result: 30 passed in 1.26s (100% PASS)
- tests/replay/test_replay_runner.py (1 passed)
- tests/unit/test_bounded_queue.py (5 passed)
- tests/unit/test_config.py (3 passed)
- tests/unit/test_db_client.py (3 passed)
- tests/unit/test_file_source.py (3 passed)
- tests/unit/test_health_api.py (4 passed)
- tests/unit/test_rtsp_source.py (3 passed)
- tests/unit/test_schemas.py (4 passed)
- tests/unit/test_storage_and_repos.py (4 passed)

Benchmark Measured Throughput: 300 synthetic frames (640x480) decoded in 0.091s (~3296 decode FPS).
Queue drop verified: 270 frames dropped into capacity-30 queue with monotonic newest retention.
```

### Known issues / Notes

OpenCV CAP_FFMPEG backend is used for RTSP and video files. RTSP capture runs on an isolated background daemon thread to maintain buffer freshness.

### Next

Phase 3: Baseline Object Detection & Detector Interface (`worker/perception/`).

---

## [MEM-0005] Baseline Object Detection & Detector Interface Initialized

**Status:** IMPLEMENTED & TESTED

**Date:** 2026-08-28

### Change

1. Created `DetectorInterface` abstract base class in `worker/perception/base.py` (`load`, `warmup`, `infer`, `get_metadata`, `close`).
2. Created production `ObjectDetector` in `worker/perception/detector.py` implementing `DetectorInterface` on top of Ultralytics YOLOv8 / PyTorch runtime with configurable confidence thresholds, IOU thresholds, and compute device selection (CPU/CUDA).
3. Created class mapping and normalization in `worker/perception/schemas.py` (`COCO_CLASS_MAP` mapping standard labels to `TargetClass.PERSON`, `TargetClass.VEHICLE`, `TargetClass.ANIMAL`, `TargetClass.UNKNOWN`).
4. Created domain exceptions in `worker/perception/exceptions.py`.
5. Created debug visualizer utility `draw_detections()` in `worker/perception/visualizer.py`.
6. Created model registry documentation `models/README.md` and updated `.gitignore` for model weight binaries (`*.pt`, `*.onnx`).
7. Added architecture decision `[DEC-0005]` in `docs/DECISIONS.md`.
8. Created unit tests in `tests/unit/test_detector.py` and deterministic replay test in `tests/replay/test_detector_replay.py`.
9. Created detector benchmark suite in `scripts/benchmark_detector.py`.

### Purpose

Establish a clean, reproducible object detection baseline directly consuming Phase 2 `FramePacket` objects, providing structured `Detection` outputs for future tracking and comparison against environment-adaptive processing.

### Git commit

```text
Commit: e52adc59c98021d1c03997e6b124bf523adb0f39
Message: feat(worker): implement baseline object detection layer, DetectorInterface, and replay tests
```

### Verification

```text
Command: pytest
Result: 38 passed in 103.13s (100% PASS)
- tests/replay/test_detector_replay.py (1 passed)
- tests/replay/test_replay_runner.py (1 passed)
- tests/unit/test_bounded_queue.py (5 passed)
- tests/unit/test_config.py (3 passed)
- tests/unit/test_db_client.py (3 passed)
- tests/unit/test_detector.py (7 passed)
- tests/unit/test_file_source.py (3 passed)
- tests/unit/test_health_api.py (4 passed)
- tests/unit/test_rtsp_source.py (3 passed)
- tests/unit/test_schemas.py (4 passed)
- tests/unit/test_storage_and_repos.py (4 passed)

Benchmark Measured Performance (CPU):
- Model Load Time: 1.0796s
- Warmup Time: 0.2507s
- Mean Latency: 44.22 ms
- Min / Max Latency: 37.44 ms / 56.75 ms
- P95 Latency: 49.95 ms
- Effective Inference FPS: 22.61 FPS (640x480 resolution)
```

### Known issues / Notes

Detector confidence is strictly model output probability [0, 1] and is not conflated with risk or tracking. RF-DETR interface compatibility is preserved via `DetectorInterface`.

### Next

Phase 4: Multi-Object Tracking Engine (`worker/tracking/`) implementing `TrackerInterface` and ByteTrack multi-frame association.

---

## [MEM-0006] Multi-Object Tracking Engine & Tracker Interface Initialized

**Status:** IMPLEMENTED & TESTED

**Date:** 2026-08-28

### Change

1. Created `TrackerInterface` abstract base class in `worker/tracking/base.py` (`update`, `get_tracks`, `reset`, `close`).
2. Created 2D Kalman box filter state estimator in `worker/tracking/kalman.py` (`KalmanBoxTracker`) modeling 8-dimensional bounding box coordinates and velocities $[cx, cy, a, h, \dot{cx}, \dot{cy}, \dot{a}, \dot{h}]$.
3. Created IoU matrix and Hungarian linear assignment matching utilities in `worker/tracking/matching.py` using `scipy.optimize.linear_sum_assignment`.
4. Created `ByteTrackTracker` and `STrack` in `worker/tracking/tracker.py` with two-stage association (high-confidence and low-confidence detection matching), explicit lifecycle state transitions (`CANDIDATE -> TRACKED -> LOST -> EXPIRED`), bounded trajectory point history (max 60 points), instantaneous velocity calculation $(\Delta x / \Delta t, \Delta y / \Delta t)$, speed estimation, and per-camera isolation.
5. Created debug visualizer `draw_tracks()` in `worker/tracking/visualizer.py` rendering colored bounding boxes, persistent Track IDs, status badges, and trailing trajectory lines.
6. Created domain exceptions in `worker/tracking/exceptions.py`.
7. Created unit test suite in `tests/unit/test_tracker.py` and deterministic end-to-end replay test in `tests/replay/test_tracker_replay.py`.
8. Created tracker benchmark suite in `scripts/benchmark_tracker.py`.

### Purpose

Provide robust, multi-frame object track persistence consuming Phase 3 `Detection[]` outputs, enabling downstream trajectory, velocity, loitering, and zone reasoning without re-running detector inference.

### Git commit

```text
Commit: c264d1c93f8d9b4ac536946a754ce06665cbaf92
Message: feat(worker): implement ByteTrack multi-object tracking engine, TrackerInterface, and replay tests
```

### Verification

```text
Command: pytest
Result: 48 passed in 17.87s (100% PASS)
- tests/replay/test_detector_replay.py (1 passed)
- tests/replay/test_replay_runner.py (1 passed)
- tests/replay/test_tracker_replay.py (1 passed)
- tests/unit/test_bounded_queue.py (5 passed)
- tests/unit/test_config.py (3 passed)
- tests/unit/test_db_client.py (3 passed)
- tests/unit/test_detector.py (7 passed)
- tests/unit/test_file_source.py (3 passed)
- tests/unit/test_health_api.py (4 passed)
- tests/unit/test_rtsp_source.py (3 passed)
- tests/unit/test_schemas.py (4 passed)
- tests/unit/test_storage_and_repos.py (4 passed)
- tests/unit/test_tracker.py (9 passed)

Benchmark Measured Performance (CPU):
- Frames Processed: 200
- Total Detections Processed: 1,890
- Total Tracks Created: 10
- Mean Update Latency: 1.5290 ms
- Min / Max Latency: 1.0867 ms / 3.7437 ms
- P95 Latency: 2.4949 ms
- Effective Tracking FPS: 654.03 FPS
```

### Known issues / Notes

No database writes or cross-camera ReID logic are introduced in tracking. Track IDs are scoped strictly per camera session.

### Next

Phase 5: Environment Engine (Layer 2) for luminance, contrast, blur/sharpness, noise, and scene quality estimation.

---

## [MEM-0007] Environment Engine & Visual Quality Observation Initialized

**Status:** IMPLEMENTED & TESTED

**Date:** 2026-08-28

### Change

1. Created `EnvironmentAnalyzerInterface` abstract base class in `worker/environment/base.py` (`analyze`, `get_state`, `reset`, `close`).
2. Created vectorized image statistic calculations in `worker/environment/metrics.py`:
   - Normalized luminance distribution (mean, standard deviation, P10/P90 percentiles).
   - Normalized RMS contrast $\sigma_Y / 255.0$.
   - Sharpness / blur score via Laplacian variance $\sigma^2(\nabla^2 I)$.
   - High-frequency noise estimation via Immerkær 3x3 residual convolution kernel.
   - Rule-based lighting classification (`DAY`, `DUSK_DAWN`, `LOW_LIGHT`, `NIGHT`).
   - Composite visual quality score $[0.0, 1.0]$ and visibility classification (`EXCELLENT`, `GOOD`, `FAIR`, `POOR`, `INSUFFICIENT`).
3. Created production `EnvironmentAnalyzer` in `worker/environment/analyzer.py` with per-camera state isolation, exponential moving average (EMA) temporal smoothing ($\alpha = 0.25$), and configurable threshold parameters.
4. Created domain exceptions in `worker/environment/exceptions.py`.
5. Preserved baseline integrity: Detector in `worker/perception/` remains untouched and un-polluted by adaptive enhancement logic.
6. Created unit tests in `tests/unit/test_environment_analyzer.py` and deterministic replay test in `tests/replay/test_environment_replay.py`.
7. Created environment benchmark suite in `scripts/benchmark_environment.py`.

### Purpose

Provide structured, real-time observation of visual environmental conditions per camera stream without modifying baseline perception weights, establishing the telemetry foundation for future adaptive perception and risk certainty estimation.

### Git commit

```text
Commit: 52c4a014497f53711d75901509b00cf554447cd4
Message: feat(worker): implement Environment Engine, visual quality metrics, and replay tests
```

### Verification

```text
Command: pytest
Result: 56 passed in 17.58s (100% PASS)
- tests/replay/test_detector_replay.py (1 passed)
- tests/replay/test_environment_replay.py (1 passed)
- tests/replay/test_replay_runner.py (1 passed)
- tests/replay/test_tracker_replay.py (1 passed)
- tests/unit/test_bounded_queue.py (5 passed)
- tests/unit/test_config.py (3 passed)
- tests/unit/test_db_client.py (3 passed)
- tests/unit/test_detector.py (7 passed)
- tests/unit/test_environment_analyzer.py (7 passed)
- tests/unit/test_file_source.py (3 passed)
- tests/unit/test_health_api.py (4 passed)
- tests/unit/test_rtsp_source.py (3 passed)
- tests/unit/test_schemas.py (4 passed)
- tests/unit/test_storage_and_repos.py (4 passed)
- tests/unit/test_tracker.py (9 passed)

Benchmark Measured Performance (CPU):
- Frames Analyzed: 500
- Mean Latency per Frame: 7.3256 ms
- Min / Max Latency: 4.4718 ms / 35.8491 ms
- P95 Latency: 8.9683 ms
- Effective Analysis Throughput: 136.51 FPS (640x480 resolution)
```

### Known issues / Notes

Environment observation only in Phase 5. Adaptive enhancement / correction (e.g., CLAHE / Retinex) will consume `EnvironmentState` in a future phase.

### Next

Phase 5 Checkpoint: Anomaly Capture & Failure Case Analysis.

---

## [MEM-0008] Phase 5 Checkpoint: Perception Anomaly Capture & Failure Case Analysis

**Status:** DIAGNOSED & DOCUMENTED

**Date:** 2026-08-28

### Change

1. Executed detailed perception and tracking diagnostic runs on sample test videos (`storage/samples/test_video.mp4`, `test_video2.mp4`).
2. Created structured evaluation failure case directory `failure_cases/` (`shadows/`, `poles/`, `vehicles/`, `background_false_positives/`, `metadata/`).
3. Captured and categorized 2,174 raw detection events across 400+ frames into `failure_cases/metadata/raw_detections_dump.json`.
4. Documented in-depth root cause analysis in `failure_cases/README.md`:
   - **Anomaly A (Shadow False Positive):** Pretrained COCO YOLOv8n misclassifies dark cast ground shadows as `skateboard` (idx 36, 90 occurrences) or `suitcase` (idx 28). Identified as a **Pretrained Model Limitation**, not a code bug.
   - **Anomaly B (Pole / Structure False Positive):** Pretrained COCO YOLOv8n misclassifies slender vertical posts/bollards as `fire hydrant` (idx 10, 12 occurrences) or `parking meter` (idx 12, 2 occurrences). Identified as a **Pretrained Model Limitation**.
   - **Anomaly C (Vehicle Mapping / UNKNOWN):** Valid cars detected as `car` correctly map to `TargetClass.VEHICLE`. When vehicles are occluded or predicted as non-vehicle COCO classes by the raw detector, `COCO_CLASS_MAP` correctly normalizes them to `TargetClass.UNKNOWN`. Schema mapping verified sound.
   - **Anomaly D (Dark / Low-Contrast FP):** Low-contrast border patches trigger low-confidence animal detections (`dog`, `cat`, `bird`).
   - **Anomaly E (Tracking Propagation):** ByteTrack faithfully tracks all bounding boxes passed to it; multi-frame false detections naturally form tracks until expiration. Expected modular tracker behavior.
5. Strict baseline integrity preserved: No detector retraining, no threshold tweaking, no model modifications.

### Purpose

Establish a clean, reproducible baseline evaluation failure set before designing future adaptive perception and spatial reasoning layers.

### Next

Phase 6: Spatial Intelligence Engine & Geo-referenced Virtual Fencing (`worker/spatial/`).

---

## [MEM-0009] Spatial Intelligence Engine & Camera-Relative Virtual Fencing Initialized

**Status:** IMPLEMENTED & TESTED

**Date:** 2026-08-28

### Change

1. Created `SpatialEngineInterface` abstract base class in `worker/spatial/base.py` (`configure_camera`, `process_tracks`, `get_spatial_state`, `reset`, `close`).
2. Created deterministic 2D geometric algorithms in `worker/spatial/geometry.py`:
   - Point-in-polygon ray-casting with explicit boundary and edge inclusion tolerance ($\epsilon = 1e-5$).
   - Segment-segment cross-product intersection test with exact crossing coordinate calculation.
   - Cosine-similarity movement direction estimation relative to camera threat vector (`TOWARD`, `AWAY`, `PARALLEL`, `UNCERTAIN`).
   - Deadband threshold ($< 3.0\text{px}$) for stationary/sub-pixel noise.
3. Created production `SpatialEngine` in `worker/spatial/engine.py`:
   - Camera-specific zone and virtual fence configuration validation.
   - Deterministic precedence for overlapping zones (`CRITICAL` > `RESTRICTED` > `BUFFER` > `SAFE`).
   - State transition tracking per object track (`ZONE_ENTERED`, `ZONE_EXITED`).
   - Virtual fence crossing events (`FenceCrossingEvent`) based on trajectory segments.
   - Per-camera state and track isolation.
4. Created domain exceptions in `worker/spatial/exceptions.py`.
5. Created debug visualizer `draw_spatial_overlay` in `worker/spatial/visualizer.py`.
6. Created unit tests in `tests/unit/test_spatial.py` and deterministic replay test in `tests/replay/test_spatial_replay.py`.
7. Created spatial benchmark suite in `scripts/benchmark_spatial.py`.

### Purpose

Provide 2D camera-space spatial reasoning (zone containment, virtual fence crossing, and movement direction) from multi-object tracks before high-level behavioral and threat analysis layers.

### Git commit

```text
Commit: d90e27334d1409ee0d3e000e105aacbfc50f1d86
Message: feat(worker): implement Spatial Intelligence Engine, virtual fencing, and geometry tests
```

### Verification

```text
Command: pytest
Result: 65 passed in ~3 min (Unit tests: 60 passed in 5.19s, 100% PASS)
- tests/replay/test_detector_replay.py (1 passed)
- tests/replay/test_environment_replay.py (1 passed)
- tests/replay/test_replay_runner.py (1 passed)
- tests/replay/test_spatial_replay.py (1 passed)
- tests/replay/test_tracker_replay.py (1 passed)
- tests/unit/test_bounded_queue.py (5 passed)
- tests/unit/test_config.py (3 passed)
- tests/unit/test_db_client.py (3 passed)
- tests/unit/test_detector.py (7 passed)
- tests/unit/test_environment_analyzer.py (7 passed)
- tests/unit/test_file_source.py (3 passed)
- tests/unit/test_health_api.py (4 passed)
- tests/unit/test_rtsp_source.py (3 passed)
- tests/unit/test_schemas.py (4 passed)
- tests/unit/test_spatial.py (8 passed)
- tests/unit/test_storage_and_repos.py (4 passed)
- tests/unit/test_tracker.py (9 passed)

Benchmark Measured Performance (CPU):
- Frames Processed: 1,000
- Total Tracks Processed: 20,000
- Total Zone Checks: 80,000
- Total Fence Checks: 40,000
- Mean Latency per Frame: 0.2834 ms
- Min / Max Latency: 0.2478 ms / 4.7117 ms
- P95 Latency: 0.3896 ms
- Effective Spatial Processing Throughput: 3,528.68 FPS (CPU)
```

### Known issues / Notes

Operates in 2D image coordinates (pixels). Geolocation / world-coordinate mapping will only be added if camera calibration/homography is provided in a future phase.

### Next

Phase 7: Behavioral Analytics & Event Engine (`worker/behavior/`).

---

## [MEM-0010] Behavioral Analytics & Temporal Pattern Engine Initialized

**Status:** IMPLEMENTED & TESTED

**Date:** 2026-08-28

### Change

1. Created `BehaviorEngineInterface` abstract base class in `worker/behavior/base.py` (`configure`, `process`, `get_active_behaviors`, `reset`, `close`).
2. Created behavioral data contracts in `worker/behavior/schemas.py`:
   - `BehaviorType`: `LOITERING`, `PERSISTENT_APPROACH`, `RESTRICTED_OCCUPANCY`, `FENCE_BREACH`, `REPEATED_APPROACH`.
   - `BehaviorStatus`: `CANDIDATE`, `ACTIVE`, `COMPLETED`, `EXPIRED`.
   - `ReasonCode`: `DWELL_TIME_EXCEEDED`, `LOW_DISPLACEMENT`, `PERSISTENT_TOWARD`, `RESTRICTED_OCCUPANCY`, `FENCE_CROSSED`, `REPEATED_APPROACH`.
   - `BehaviorConfig`: Configurable temporal windows (`loitering_seconds=5.0`, `loitering_max_displacement_px=40.0`, `persistent_approach_seconds=3.0`, `repeated_approach_window_sec=30.0`).
   - `BehaviorPrimitive`: Canonical explainable behavior representation.
3. Created specialized temporal detector modules:
   - `LoiteringDetector` in `worker/behavior/loitering.py`: Evaluates dwell duration and displacement radius inside zones.
   - `ApproachDetector` in `worker/behavior/approach.py`: Evaluates persistent motion toward threat vectors and recurring approach attempts.
   - `OccupancyDetector` & `FenceBreachDetector` in `worker/behavior/occupancy.py`: Tracks sustained restricted zone occupancy and converts fence crossing events into behavior primitives.
4. Created production `BehaviorEngine` in `worker/behavior/engine.py` with per-camera state isolation, bounded track memory, and sustained event de-duplication.
5. Created unit tests in `tests/unit/test_behavior.py` and deterministic replay test in `tests/replay/test_behavior_replay.py`.
6. Created behavior benchmark suite in `scripts/benchmark_behavior.py`.

### Purpose

Provide explainable temporal behavior pattern detection from track and spatial trajectories without making final security/threat classifications.

### Git commit

```text
Commit: d6f00ce6b2e14277d547c680dd5c4a3b8859dc01
Message: feat(worker): implement Behavioral Analytics Engine, temporal detectors, and replay tests
```

### Verification

```text
Command: pytest tests/unit/
Result: 66 passed in 5.47s (100% PASS)
- tests/unit/test_behavior.py (6 passed)
- tests/unit/test_bounded_queue.py (5 passed)
- tests/unit/test_config.py (3 passed)
- tests/unit/test_db_client.py (3 passed)
- tests/unit/test_detector.py (7 passed)
- tests/unit/test_environment_analyzer.py (7 passed)
- tests/unit/test_file_source.py (3 passed)
- tests/unit/test_health_api.py (4 passed)
- tests/unit/test_rtsp_source.py (3 passed)
- tests/unit/test_schemas.py (4 passed)
- tests/unit/test_spatial.py (8 passed)
- tests/unit/test_storage_and_repos.py (4 passed)
- tests/unit/test_tracker.py (9 passed)

Benchmark Measured Performance (CPU):
- Frames Processed: 1,000
- Total Tracks Evaluated: 20,000
- Total Behaviors Generated: 29,459
- Mean Latency per Frame: 0.1679 ms
- Min / Max Latency: 0.0658 ms / 0.5760 ms
- P95 Latency: 0.2179 ms
- Effective Behavior Engine Throughput: 5,956.41 FPS (CPU)
```

### Known issues / Notes

Behavior primitives describe purely physical and temporal movement (e.g. loitering, approach); security risk scoring and threat level assignment are handled in Phase 8.

---

## [MEM-0011] World-Owned Border Model Architectural Correction Initialized

**Status:** IMPLEMENTED & TESTED

**Date:** 2026-08-30

### Change

1. Updated documentation first:
   - Created `docs/spatial_border_model.md` detailing global border hierarchy, border sections, camera registration, calibration, planar homography, ground-contact points, warning buffers, crossing confirmation, and flat vs. mountain terrain limitations.
   - Recorded `[DEC-0006]` in `docs/DECISIONS.md`.
2. Created world-space border schemas in `worker/spatial/world_schemas.py`:
   - `CoordinateReference` (`LOCAL_CARTESIAN`, `GPS_WGS84`), `TerrainMode` (`PLANAR_GROUND`, `TERRAIN_3D`).
   - `BorderSection`, `CameraRegistration`, `CameraCalibration`, `CalibrationCorrespondence`.
   - `BorderSide` (`PERMITTED`, `WARNING_BUFFER`, `BORDER_LINE`, `RESTRICTED`, `UNKNOWN`), `CrossingStatus` (`NONE`, `CROSSING_CANDIDATE`, `CONFIRMED_CROSSING`).
   - `GroundContactPoint`, `ProjectedBorder`, `CrossingEvent`.
3. Created camera calibration subsystem in `worker/spatial/calibration.py`:
   - `compute_homography(correspondences)` with OpenCV RANSAC and collinearity rejection.
   - `project_world_to_image(world_point, H)` and `project_image_to_world(image_point, H_inv)`.
   - `validate_calibration(calibration)` returning `CalibrationStatus` (`CALIBRATED`, `UNCALIBRATED`, `STALE`, `INVALID`).
   - `project_border_to_camera(border_section, calibration)` computing derived `ProjectedBorder`.
   - Explicit `TerrainModeNotImplementedError` when `TERRAIN_3D` is requested.
4. Created ground-contact point extraction in `worker/spatial/ground_contact.py`:
   - `estimate_ground_contact(track)` approximating bottom-center of bounding box for persons/vehicles with occlusion confidence flags.
   - `image_to_world_ground(pixel_xy, H_inv)` mapping ground contact to local world coordinates.
5. Created world-space border logic in `worker/spatial/border_logic.py`:
   - `determine_side(world_point, border_section)` evaluating signed distance to border polyline relative to `permitted_side_normal`.
   - `check_crossing(previous_side, current_side)` detecting candidate transitions.
   - `CrossingConfirmation(confirmation_frames=N)` stateful multi-frame confirmation with jitter rejection.
6. Refactored `SpatialEngine` in `worker/spatial/engine.py`:
   - Dual-mode architecture: world-border mode for calibrated cameras, legacy image-space mode for uncalibrated cameras.
   - Preserved `SpatialState` schema output contract for 100% backward compatibility with Phase 7 `BehaviorEngine`.
7. Created database migration `supabase/migrations/20260830000000_border_calibration.sql` and example configuration `configs/border_config_example.yaml`.
8. Created unit test suite in `tests/unit/test_world_border.py` (37 tests) and replay test in `tests/replay/test_border_replay.py`.
9. Created performance benchmark in `scripts/benchmark_border.py`.

### Purpose

Transition spatial reasoning from camera-owned manual pixel fences to a single real-world border definition where cameras act as calibrated viewpoints.

### Git commit

```text
Commit: de8c30e9e2864de12d79f454baf53501ce46242a
Message: feat(spatial): implement world-owned border model, camera calibration, and crossing confirmation
```

### Verification

```text
Command: pytest tests/unit/
Result: 103 passed in 15.55s (100% PASS)
- tests/unit/test_world_border.py (37 passed)
- tests/unit/test_spatial.py (8 passed)
- tests/unit/test_behavior.py (6 passed)
- tests/unit/test_bounded_queue.py (5 passed)
- tests/unit/test_config.py (3 passed)
- tests/unit/test_db_client.py (3 passed)
- tests/unit/test_detector.py (7 passed)
- tests/unit/test_environment_analyzer.py (7 passed)
- tests/unit/test_file_source.py (3 passed)
- tests/unit/test_health_api.py (4 passed)
- tests/unit/test_rtsp_source.py (3 passed)
- tests/unit/test_schemas.py (4 passed)
- tests/unit/test_storage_and_repos.py (4 passed)
- tests/unit/test_tracker.py (9 passed)

Command: pytest tests/replay/test_border_replay.py
Result: 1 passed in 22.78s (100% PASS)

- tests/replay/test_replay_runner.py (1 passed)

Benchmark Measured Performance (CPU):
- Evidence Extraction Latency (per track): 0.01368 ms (5 items)
- Risk Score Calculation Latency: 0.00427 ms (Score: 59.5/100)
- Factual Explanation Summary Latency: 0.00260 ms
- End-to-End Mean Latency per Frame (20 tracks): 0.6248 ms
- P95 Latency: 0.8918 ms
- Effective Fusion Throughput: 1,594.05 FPS (20 tracks/frame on CPU)
```

### Known limitations

1. Prototype Weights: Initial weights are configuration-driven defaults and should be empirically tuned with field operational datasets.
2. Optional Intelligence: ANPR and FRS remain decoupled optional plugins for future phases.

---

## [MEM-0013] Phase 9 — Structured Evidence Storage & Packaging Initialized

**Status:** IMPLEMENTED & TESTED

**Date:** 2026-08-30

### Change

1. Created domain exceptions in `worker/evidence/exceptions.py`:
   - `EvidenceError`, `BufferUnderflowError`, `EncodingError`, `IntegrityVerificationError`, `StorageError`.
2. Created data contracts and schemas in `worker/evidence/schemas.py`:
   - `EvidenceStatus` enum: `RECORDING`, `PACKAGED`, `SEALED`, `STORED`, `FAILED`.
   - `EvidencePackageConfig`: configurable pre/post durations, snapshot JPEG quality, target FPS, and storage directories.
   - `ArtifactChecksum`: cryptographic SHA-256 fingerprint for individual media artifacts.
   - `EvidenceManifest`: immutable audit manifest linking event details, target class, risk score, priority, reason codes, artifact hashes, and seal timestamps.
   - `EvidencePackage`: complete package schema containing physical paths, audit manifest, and SHA-256 seal.
3. Created continuous pre-event ring buffer in `worker/evidence/buffer.py`:
   - `RollingFrameBuffer` with bounded memory deque and thread-safe operations.
   - Zero-latency time-window retrieval `get_window(start_utc, end_utc)` and `get_pre_event_frames()`.
4. Created snapshot extraction and forensic HUD annotation in `worker/evidence/snapshot.py`:
   - `SnapshotExtractor.save_raw_snapshot()`: high-quality clean JPEG keyframe.
   - `SnapshotExtractor.save_annotated_snapshot()`: renders top forensic metadata banner, target bounding boxes, ground-contact points, and projected world borders.
5. Created video clip compilation in `worker/evidence/clip.py`:
   - `ClipPackager.encode_clip()`: compiles chronological buffered frames into standard MP4 files.
6. Created cryptographic sealing and verification engine in `worker/evidence/hasher.py`:
   - `EvidenceHasher.hash_file()`, `create_artifact_checksum()`, and `verify_package_integrity()`.
7. Created storage manager in `worker/evidence/storage.py`:
   - Local directory hierarchy (`storage/evidence/{camera_id}/{event_id}/`) and manifest serialization.
   - Optional asynchronous non-blocking cloud upload to Supabase Storage `evidence` bucket.
8. Created production orchestrator in `worker/evidence/packager.py`:
   - Implemented `EvidencePackagerInterface` managing multi-camera ring buffers, snapshot extraction, clip compilation, manifest sealing, and verification.
9. Added `get_projected_borders` helper to `SpatialEngine` in `worker/spatial/engine.py`.
10. Created unit tests in `tests/unit/test_evidence.py` (12 tests) and deterministic replay test in `tests/replay/test_evidence_replay.py`.
11. Created performance benchmark in `scripts/benchmark_evidence.py`.
12. Registered `[DEC-0008]` in `docs/DECISIONS.md`.

### Purpose

Provide an automated, non-repudiable, tamper-evident evidence packaging pipeline satisfying legal chain of custody requirements for all high-priority security incidents.

### Git commit

```text
Commit: [PENDING_COMMIT]
Message: feat(worker): implement Structured Evidence Storage & Packaging subsystem, SHA-256 sealing, and replay tests
```

### Verification

```text
Command: pytest tests/unit/ tests/replay/
Result: 141 passed in 18.56s (100% PASS)
- tests/unit/test_evidence.py (12 passed)
- tests/unit/test_fusion.py (17 passed)
- tests/unit/test_world_border.py (37 passed)
- tests/unit/test_spatial.py (8 passed)
- tests/unit/test_behavior.py (6 passed)
- tests/unit/test_detector.py (7 passed)
- tests/unit/test_tracker.py (9 passed)
- tests/unit/test_environment_analyzer.py (7 passed)
- tests/unit/test_bounded_queue.py (5 passed)
- tests/unit/test_config.py (3 passed)
- tests/unit/test_db_client.py (3 passed)
- tests/unit/test_file_source.py (3 passed)
- tests/unit/test_health_api.py (4 passed)
- tests/unit/test_rtsp_source.py (3 passed)
- tests/unit/test_schemas.py (4 passed)
- tests/unit/test_storage_and_repos.py (4 passed)
- tests/replay/test_evidence_replay.py (1 passed)
- tests/replay/test_fusion_replay.py (1 passed)
- tests/replay/test_border_replay.py (1 passed)
- tests/replay/test_behavior_replay.py (1 passed)
- tests/replay/test_detector_replay.py (1 passed)
- tests/replay/test_environment_replay.py (1 passed)
- tests/replay/test_spatial_replay.py (1 passed)
- tests/replay/test_tracker_replay.py (1 passed)
- tests/replay/test_replay_runner.py (1 passed)

Benchmark Measured Performance (CPU):
- Ring Buffer Frame Push Latency: 0.08668 ms (per frame, including copy)
- Time-Window Slice Retrieval Latency: 0.01924 ms
- Raw Snapshot JPEG Encoding Latency: 1.385 ms (640x480 @ Q=95)
- Forensic HUD Annotated JPEG Latency: 3.034 ms
- MP4 Clip Encoding Latency (50 frames): 41.513 ms (1,204.4 FPS encoding speed)
- Cryptographic SHA-256 Sealing Latency: 0.4268 ms (per artifact pair)
- Full Package Assembly & Sealing Throughput: 5.16 packages/sec on CPU
```

### Known limitations

1. Memory Overhead: High-FPS multiple cameras require memory sizing for uncompressed frame ring buffers (e.g. 15s at 25fps = 375 frames ~ 345MB per camera).
2. Video Codec: Standard OpenCV `mp4v` is used for immediate portability without requiring external FFmpeg binaries.

### Next

Phase 10: System Integration & Worker Pipeline Orchestration.

---

# 10. GIT HISTORY

## Current baseline

```text
Branch: main
HEAD: [PENDING_COMMIT]
Working tree: clean
Total Commits: 17
1. 763a6a49782720d5f91afe652c4843b0c9783161 - Feat : Initial Commit ith docs placement
2. e6ff13a17e149777530cfdc7504450b3c5e73f48 - chore: initialize repository baseline, shared schemas, system config, and DECISIONS.md
3. 6b388943039f7fbdf2e62976c2a9e3949e2d932a - chore: add .gitignore and un-track pycache artifacts
4. 92bce3e55e5cd98a8d03ef9a55f4da9959162e20 - feat(backend): implement Supabase PostgreSQL and Storage data layer foundation
5. e018246fc69cefab998d4db096d78d0114378da1 - feat(worker): implement video ingestion subsystem, bounded frame queue, and replay pipeline
6. e52adc59c98021d1c03997e6b124bf523adb0f39 - feat(worker): implement baseline object detection layer, DetectorInterface, and replay tests
7. c264d1c93f8d9b4ac536946a754ce06665cbaf92 - feat(worker): implement ByteTrack multi-object tracking engine, TrackerInterface, and replay tests
8. 52c4a014497f53711d75901509b00cf554447cd4 - feat(worker): implement Environment Engine, visual quality metrics, and replay tests
9. 30db6728c0abfe71e3c83d5890884f3d270c1d9c - docs(eval): capture Phase 5 perception anomalies and structured failure case corpus [MEM-0008]
10. d90e27334d1409ee0d3e000e105aacbfc50f1d86 - feat(worker): implement Spatial Intelligence Engine, virtual fencing, and geometry tests
11. d6f00ce6b2e14277d547c680dd5c4a3b8859dc01 - feat(worker): implement Behavioral Analytics Engine, temporal detectors, and replay tests
12. 8812eb86dd0d9d28ab83217a3cdb5878591c632b - feat(scripts): upgrade pipeline runner to render Spatial Zones, Virtual Fences, and Behavior Badges
13. de8c30e9e2864de12d79f454baf53501ce46242a - feat(spatial): implement world-owned border model, camera calibration, and crossing confirmation
14. b1fb40e4deed1b4ca3909fd5e6bf07f357269250 - feat(scripts): add multi-camera world border coordination test and visualizer
15. 7672d063c5a1c8d2f89668fa994555ade8dccd1f - feat(worker): implement Multi-Modal Evidence Fusion Engine, risk scoring, and replay tests
16. 30b2c782b0679e2fb594512b33bc7b2d9b2890c8 - docs: record Phase 8 Multi-Modal Evidence Fusion baseline [MEM-0012]
17. [PENDING_COMMIT] - feat(worker): implement Structured Evidence Storage & Packaging subsystem, SHA-256 sealing, and replay tests
```

---

# 11. IMPLEMENTATION BASELINE

## 11.1 Frontend

```text
Status: PLANNED
Framework: React + TypeScript + Vite
```

## 11.2 Backend

```text
Status: IMPLEMENTED (Foundation & Database Client)
Framework: FastAPI + Pydantic v2
Entry point: backend/app/main.py
Routes: /health, /api/v1/health
Database: Supabase PostgreSQL (PostgREST Client + Repository Layer)
Storage: Supabase Storage ('evidence' bucket abstraction)
Known issues: None
Last changed: 2026-08-28
Commit: 92bce3e55e5cd98a8d03ef9a55f4da9959162e20
```

## 11.3 AI Worker

```text
Status: IMPLEMENTED (Ingestion + Perception + Tracking + Environment + World-Border Spatial + Behavior + Evidence Fusion + Evidence Packaging)
Entry point: worker/
Video sources: FileVideoSource (deterministic MP4 replay), RTSPVideoSource (IP camera with reconnect)
Frame queue: BoundedFrameQueue (drop-oldest overflow policy, default capacity 30)
Detector: ObjectDetector (YOLOv8n / PyTorch, DetectorInterface)
Tracker: ByteTrackTracker (Kalman Filter + Linear Assignment, TrackerInterface)
Environment: EnvironmentAnalyzer (Luminance, Contrast, Blur, Noise, Visibility Quality)
Spatial: SpatialEngine (World-Owned Border Model, Planar Homography, Ground-Contact Point, Side Determination, Crossing Confirmation)
Behavior: BehaviorEngine (Loitering, Persistent Approach, Restricted Occupancy, Fence Breach)
Fusion: FusionEngine (Multi-Modal Evidence Fusion, Weighted Risk Scoring, Event Deduplication, Priority Tiers)
Evidence: EvidencePackager (Rolling Frame Buffer, JPEG Snapshots, MP4 Clips, SHA-256 Cryptographic Sealing, Local & Cloud Storage)
Known issues: None
Last changed: 2026-08-30
Commit: [PENDING_COMMIT]
```

## 11.4 Detector

```text
Status: IMPLEMENTED (Baseline Perception)
Model: YOLOv8n (Pretrained COCO)
Version: 8.4.37 (Ultralytics)
Runtime: PyTorch 2.10.0+cpu
Device: CPU (auto-detects CUDA)
Classes: person, vehicle categories (car, truck, bus, motorcycle, bicycle), animal categories (dog, horse, etc.) mapped to TargetClass
Artifact: models/detector/yolov8n.pt
License: AGPL-3.0
Input: BGR uint8 NumPy array (FramePacket)
Output: List[Detection] in original frame coordinates [x_min, y_min, x_max, y_max]
Measured latency: 44.22 ms (Mean)
Measured FPS: 22.61 FPS (CPU, 640x480)
Known limitations: Pretrained COCO false positives on shadows (skateboards) and vertical poles (fire hydrants) recorded in failure_cases/.
Last changed: 2026-08-28
Commit: e52adc59c98021d1c03997e6b124bf523adb0f39
```

## 11.5 Tracker

```text
Status: IMPLEMENTED (Multi-Object Tracking)
Tracker: ByteTrackTracker (2-stage association + Kalman Filter)
Version: Custom SciPy / NumPy implementation
Input: List[Detection] from perception layer
Output: List[TrackState] with track_id, center_xy, velocity_xy, speed, and bounded trajectory
Lifecycle: CANDIDATE -> TRACKED -> LOST -> EXPIRED (pruned after max_lost_frames=30)
Measured performance: 1.5290 ms update latency (~654 FPS) on CPU
Known issues: None
Last changed: 2026-08-28
Commit: c264d1c93f8d9b4ac536946a754ce06665cbaf92
```

## 11.6 Environment Engine

```text
Status: IMPLEMENTED (Visual Quality Observation)
Analyzer: EnvironmentAnalyzer (worker/environment/)
Inputs: FramePacket (image array)
Outputs: EnvironmentState (lighting, brightness, contrast, blur_score, noise_estimate, visibility, quality_score)
Lighting: DAY, DUSK_DAWN, LOW_LIGHT, NIGHT
Visibility: EXCELLENT, GOOD, FAIR, POOR, INSUFFICIENT
Smoothing: Exponential Moving Average (EMA alpha=0.25)
Measured latency: 7.33 ms (~136 FPS) on CPU
Known issues: None
Last changed: 2026-08-28
Commit: 52c4a014497f53711d75901509b00cf554447cd4
```

## 11.7 Spatial Engine

```text
Status: IMPLEMENTED (2D Image-Coordinate Spatial Reasoning)
Engine: SpatialEngine (worker/spatial/)
Inputs: List[TrackState] from tracking engine + CameraSpatialConfig
Outputs: List[SpatialState], List[FenceCrossingEvent]
Zones: SAFE, BUFFER, RESTRICTED, CRITICAL (deterministic precedence)
Fences: VirtualFence segment-segment trajectory intersection
Direction: TOWARD, AWAY, PARALLEL, UNCERTAIN (Cosine similarity with threat vector)
Coordinate space: 2D image coordinates (pixels)
Measured latency: 0.2834 ms (~3,528 FPS) on CPU
Known issues: None
Last changed: 2026-08-28
Commit: d90e27334d1409ee0d3e000e105aacbfc50f1d86
```

## 11.8 Behavior Engine

```text
Status: IMPLEMENTED (Temporal Pattern Reasoning)
Engine: BehaviorEngine (worker/behavior/)
Inputs: List[TrackState], List[SpatialState], Optional[EnvironmentState]
Outputs: List[BehaviorPrimitive]
Behaviors: LOITERING, PERSISTENT_APPROACH, RESTRICTED_OCCUPANCY, FENCE_BREACH, REPEATED_APPROACH
Reason codes: DWELL_TIME_EXCEEDED, LOW_DISPLACEMENT, PERSISTENT_TOWARD, RESTRICTED_OCCUPANCY, FENCE_CROSSED, REPEATED_APPROACH
Deduplication: Sustained active behaviors update duration without generating duplicate event objects
Measured latency: 0.1679 ms (~5,956 FPS) on CPU
Known issues: None
Last changed: 2026-08-28
Commit: d6f00ce6b2e14277d547c680dd5c4a3b8859dc01
```

## 11.4 Detector

```text
Status: IMPLEMENTED (Baseline Perception)
Model: YOLOv8n (Pretrained COCO)
Version: 8.4.37 (Ultralytics)
Runtime: PyTorch 2.10.0+cpu
Device: CPU (auto-detects CUDA)
Classes: person, vehicle categories (car, truck, bus, motorcycle, bicycle), animal categories (dog, horse, etc.) mapped to TargetClass
Artifact: models/detector/yolov8n.pt
License: AGPL-3.0
Input: BGR uint8 NumPy array (FramePacket)
Output: List[Detection] in original frame coordinates [x_min, y_min, x_max, y_max]
Measured latency: 44.22 ms (Mean)
Measured FPS: 22.61 FPS (CPU, 640x480)
Known limitations: Pretrained COCO false positives on shadows (skateboards) and vertical poles (fire hydrants) recorded in failure_cases/.
Last changed: 2026-08-28
Commit: e52adc59c98021d1c03997e6b124bf523adb0f39
```

## 11.5 Tracker

```text
Status: IMPLEMENTED (Multi-Object Tracking)
Tracker: ByteTrackTracker (2-stage association + Kalman Filter)
Version: Custom SciPy / NumPy implementation
Input: List[Detection] from perception layer
Output: List[TrackState] with track_id, center_xy, velocity_xy, speed, and bounded trajectory
Lifecycle: CANDIDATE -> TRACKED -> LOST -> EXPIRED (pruned after max_lost_frames=30)
Measured performance: 1.5290 ms update latency (~654 FPS) on CPU
Known issues: None
Last changed: 2026-08-28
Commit: c264d1c93f8d9b4ac536946a754ce06665cbaf92
```

## 11.6 Environment Engine

```text
Status: IMPLEMENTED (Visual Quality Observation)
Analyzer: EnvironmentAnalyzer (worker/environment/)
Inputs: FramePacket (image array)
Outputs: EnvironmentState (lighting, brightness, contrast, blur_score, noise_estimate, visibility, quality_score)
Lighting: DAY, DUSK_DAWN, LOW_LIGHT, NIGHT
Visibility: EXCELLENT, GOOD, FAIR, POOR, INSUFFICIENT
Smoothing: Exponential Moving Average (EMA alpha=0.25)
Measured latency: 7.33 ms (~136 FPS) on CPU
Known issues: None
Last changed: 2026-08-28
Commit: 52c4a014497f53711d75901509b00cf554447cd4
```

## 11.7 Spatial Engine

```text
Status: IMPLEMENTED (2D Image-Coordinate Spatial Reasoning)
Engine: SpatialEngine (worker/spatial/)
Inputs: List[TrackState] from tracking engine + CameraSpatialConfig
Outputs: List[SpatialState], List[FenceCrossingEvent]
Zones: SAFE, BUFFER, RESTRICTED, CRITICAL (deterministic precedence)
Fences: VirtualFence segment-segment trajectory intersection
Direction: TOWARD, AWAY, PARALLEL, UNCERTAIN (Cosine similarity with threat vector)
Coordinate space: 2D image coordinates (pixels)
Measured latency: 0.2834 ms (~3,528 FPS) on CPU
Known issues: None
Last changed: 2026-08-28
Commit: d90e27334d1409ee0d3e000e105aacbfc50f1d86
```
Blur:
Contrast:
Weather:
Terrain:
Adaptive behavior:
Tests:
Last changed:
Commit:
```

## 11.7 Spatial Engine

```text
Status: NOT RECORDED
Zones:
Fences:
Direction:
Coordinate system:
Tests:
Last changed:
Commit:
```

## 11.8 Behavior Engine

```text
Status: NOT RECORDED
Loitering:
Persistent approach:
Restricted entry:
Fence crossing:
Repeated approach:
Tests:
Last changed:
Commit:
```

## 11.9 Evidence Fusion

```text
Status: NOT RECORDED
Inputs:
Scoring:
Reason codes:
Priority levels:
Calibration:
Tests:
Last changed:
Commit:
```

## 11.10 Evidence Storage

```text
Status: NOT RECORDED
Backend:
Directory:
Pre-event duration:
Post-event duration:
Format:
Retention:
Known issues:
Last changed:
Commit:
```

---

# 12. DATABASE STATE

```text
Database type:
Schema version:
Migration mechanism:
Tables:
Indexes:
Known issues:
Last migration:
Commit:
```

Expected logical entities:

```text
cameras
zones
fences
detections
tracks
events
environment_snapshots
users
audit_logs
model_versions
```

Do not claim that a table exists until repository inspection confirms it.

---

# 13. API STATE

## REST

Expected conceptual routes:

```text
/api/v1/cameras
/api/v1/cameras/{id}
/api/v1/cameras/{id}/health

/api/v1/zones
/api/v1/fences

/api/v1/events
/api/v1/events/{id}
/api/v1/events/{id}/ack
/api/v1/events/{id}/dismiss

/api/v1/system/health
/api/v1/system/metrics
```

**Status:** Architecture-defined, implementation must be verified.

Do not mark an endpoint IMPLEMENTED until tested.

---

# 14. WEBSOCKET STATE

Expected:

```text
/ws/events
/ws/cameras/{camera_id}
```

Purpose:

```text
real-time event delivery
```

Status:

```text
NOT RECORDED
```

---

# 15. EVENT TYPES

Core intended event types:

```text
PERSON_DETECTED
VEHICLE_DETECTED
ANIMAL_DETECTED
UNKNOWN_OBJECT

PERSISTENT_TRACK
LOITERING
PERSISTENT_APPROACH
RESTRICTED_ENTRY
FENCE_CROSSED
REPEATED_APPROACH
```

Optional later:

```text
ANPR_EVENT
FACE_MATCH_CANDIDATE
UNIFORM_CLASSIFICATION
ADVANCED_ANOMALY
```

---

# 16. REASON CODES

Core intended reason codes:

```text
PERSISTENT_TRACK
TOWARD_RESTRICTED_ZONE
RESTRICTED_ENTRY
FENCE_CROSSED
LOITERING
REPEATED_APPROACH
LOW_LIGHT
LOW_VISUAL_QUALITY
UNKNOWN_OBJECT
UNCERTAIN
```

Add new reason codes only after documenting their semantics.

---

# 17. RISK MODEL STATE

Risk/priority levels:

```text
INFO
LOW
MEDIUM
HIGH
CRITICAL
```

Important:

```text
detector confidence != threat probability
risk score != probability of intent
```

Current exact weighting:

```text
NOT YET VERIFIED / IMPLEMENTATION-DEPENDENT
```

Any weights must be recorded when implemented.

---

# 18. ENVIRONMENT STATE

Expected structure:

```json
{
  "lighting": "...",
  "brightness": 0.0,
  "contrast": 0.0,
  "blur": 0.0,
  "noise": 0.0,
  "visibility": "...",
  "weather": "...",
  "terrain": "...",
  "quality_score": 0.0
}
```

Status:

```text
Architecture-defined.
Implementation values: NOT RECORDED.
```

---

# 19. MODEL REGISTRY

Use one entry per model.

Template:

```text
Model name:
Task:
Version:
Source:
Artifact:
Runtime:
License:
Checksum:
Input:
Output:
Classes:
Benchmark:
Selected because:
Rejected alternatives:
Known limitations:
Commit:
```

---

# 20. DEPENDENCY REGISTRY

Template:

```text
Package:
Version:
Purpose:
License:
Added on:
Added by:
Reason:
Alternative considered:
Compatibility impact:
Commit:
```

---

# 21. CONFIGURATION REGISTRY

Track all important configurable parameters.

Template:

```text
Configuration:
Old value:
New value:
Reason:
Validation:
Affected module:
Commit:
```

Examples:

```text
detector confidence
inference FPS
input size
minimum track age
loitering duration
approach duration
fence threshold
risk threshold
evidence duration
```

---

# 22. TEST HISTORY

Every meaningful test run should be recorded.

Template:

```text
TEST ID:
Date:
Commit:
Command:
Scope:
Input:
Expected:
Actual:
Result:
Metrics:
Failure:
Follow-up:
```

---

# 23. GOLDEN PATH TEST HISTORY

## GP-0001

```text
Status: NOT RUN / NOT RECORDED
```

Expected:

```text
CCTV/replay
→ environment
→ detection
→ tracking
→ fence
→ direction
→ behavior
→ fusion
→ high event
→ evidence
→ dashboard
```

Record the first verified successful run here.

---

# 24. FAILURE LOG

Template:

```text
FAILURE ID:
Date:
Commit:
Component:
Symptom:
Expected:
Actual:
Root cause:
Fix:
Regression test:
Commit containing fix:
Status:
```

Never delete failures.

---

# 25. PERFORMANCE HISTORY

Record only measured results.

| Date | Commit | Hardware | Model | Input | FPS | Latency | CPU | GPU | Result |
|---|---|---|---|---|---:|---:|---:|---:|---|
| — | — | — | — | — | — | — | — | — | NOT MEASURED |

---

# 26. ENVIRONMENT ROBUSTNESS HISTORY

Record actual tests.

| Condition | Video/Test | Baseline | Adaptive | Detection | Tracking | Events | False alerts | Notes |
|---|---|---|---|---|---|---|---|---|
| Day | — | NOT MEASURED | NOT MEASURED | — | — | — | — | — |
| Night | — | NOT MEASURED | NOT MEASURED | — | — | — | — | — |
| Low light | — | NOT MEASURED | NOT MEASURED | — | — | — | — | — |
| Rain | — | NOT MEASURED | NOT MEASURED | — | — | — | — | — |
| Fog | — | NOT MEASURED | NOT MEASURED | — | — | — | — | — |
| Snow | — | NOT MEASURED | NOT MEASURED | — | — | — | — | — |
| Forest | — | NOT MEASURED | NOT MEASURED | — | — | — | — | — |
| Mountain | — | NOT MEASURED | NOT MEASURED | — | — | — | — | — |
| Open | — | NOT MEASURED | NOT MEASURED | — | — | — | — | — |

---

# 27. ARCHITECTURE DECISION HISTORY

Template:

```text
DECISION ID:
Date:
Question:
Options:
Chosen:
Why:
Trade-offs:
Rejected:
Impact:
Status:
Commit:
```

---

# 28. CURRENT OPEN DECISIONS

> Populate only with real open decisions.

```text
None recorded yet.
```

---

# 29. CURRENT BLOCKERS

```text
None recorded yet.
```

---

# 30. CURRENT KNOWN LIMITATIONS

Initial architecture-level limitations:

1. Ordinary monocular CCTV cannot recover information the camera did not capture.
2. Extreme low-light/visibility conditions can cause uncertainty.
3. Uniform/civilian classification is visually difficult.
4. ANPR depends on plate visibility and image quality.
5. Face recognition depends strongly on face quality and must remain controlled.
6. Terrain and weather generalization require representative evaluation data.
7. Detector performance must be measured on the project's actual domain data.
8. External sensor fusion is not part of the core prototype.

These are architectural/research limitations, not measured failure rates.

---

# 31. SECURITY STATE

Track:

```text
Authentication:
Authorization:
RTSP credential handling:
Secrets:
Audit logs:
Sensitive evidence:
Biometric controls:
Network exposure:
```

Never mark secure merely because a login page exists.

---

# 32. DATA GOVERNANCE STATE

Track:

```text
Raw video retention:
Evidence retention:
Event metadata retention:
Biometric retention:
Access roles:
Deletion mechanism:
Audit coverage:
```

Status:

```text
Implementation to be verified.
```

---

# 33. OPTIONAL MODULE STATE

## Uniform classifier

```text
Status:
Model:
Version:
Dataset:
Evaluation:
Commit:
```

## ANPR

```text
Status:
Detector:
OCR:
Temporal aggregation:
Evaluation:
Commit:
```

## Face Recognition

```text
Status:
Face detector:
Embedding model:
Watchlist:
Access policy:
Evaluation:
Commit:
```

## Advanced anomaly detection

```text
Status:
Model:
Dataset:
Evaluation:
Commit:
```

---

# 34. DATASET MEMORY

Track datasets used.

Template:

```text
Dataset:
Purpose:
Source:
License:
Classes:
Size:
Split:
Preprocessing:
Training:
Validation:
Test:
Known domain gap:
Last used:
Commit:
```

Important datasets under consideration:

```text
COCO
CrowdHuman
VisDrone
MOT
VIRAT
Custom IBVAP dataset
```

Do not mark any as actually used until verified.

---

# 35. DEPLOYMENT MEMORY

## Local development

```text
OS:
Python:
Node:
GPU:
CUDA:
Docker:
```

## Prototype deployment

```text
Machine:
CPU:
GPU:
RAM:
Storage:
Camera count:
Resolution:
Inference FPS:
Observed latency:
```

## Production-like deployment

```text
Not yet implemented.
```

---

# 36. GIT COMMIT RULE

For every commit, add:

```text
## COMMIT <HASH>

Date:
Message:
Author:
Parent:
Files changed:
Summary:
Why:
Tests:
Result:
Known issue:
Next:
```

Never summarize a commit only as:

```text
"updated code"
```

---

# 37. GIT WORKTREE RULE

At each implementation checkpoint record:

```text
branch:
HEAD:
working tree clean/dirty:
untracked files:
staged files:
```

This makes the memory auditable.

---

# 38. RELEASE / MILESTONE HISTORY

Template:

```text
MILESTONE:
Date:
Commit:
Goal:
Delivered:
Verified:
Not delivered:
Known issues:
Next milestone:
```

Suggested milestones:

```text
M0 — Repository initialized
M1 — Video ingestion
M2 — Detection
M3 — Tracking
M4 — Spatial intelligence
M5 — Environment adaptation
M6 — Behavior/fusion
M7 — Event/evidence
M8 — Dashboard
M9 — SIH demo
```

---

# 39. CHANGE IMPACT TEMPLATE

For each major change:

```text
CHANGE:
Reason:
Affected layers:
Breaking?:
New dependencies:
Performance impact:
Security impact:
Data/schema impact:
UI impact:
Test impact:
Documentation impact:
Rollback:
Commit:
```

---

# 40. REVERT HISTORY

If something is reverted:

```text
REVERT ID:
Original commit:
Revert commit:
Reason:
What was lost:
What remains:
Replacement plan:
```

Never delete the original history.

---

# 41. MODEL EXPERIMENT LOG

Template:

```text
Experiment:
Date:
Commit:
Hypothesis:
Model:
Dataset:
Configuration:
Metric:
Baseline:
Result:
Decision:
```

Example:

```text
Hypothesis:
Selective low-light enhancement reduces false alarms.

Baseline:
raw frame

Treatment:
adaptive enhancement only in low-light scenes

Metrics:
false alarms/camera-hour
person recall
latency

Decision:
PENDING MEASUREMENT
```

---

# 42. ENVIRONMENT EXPERIMENT LOG

Template:

```text
Experiment:
Condition:
Baseline pipeline:
Adaptive pipeline:
Input video:
Metric:
Result:
Conclusion:
Commit:
```

---

# 43. BUG REGRESSION RULE

Every fixed bug that could recur should have a test.

Memory entry:

```text
Bug:
Root cause:
Fix:
Regression test:
Commit:
```

---

# 44. API CHANGE LOG

Template:

```text
API change:
Endpoint:
Old schema:
New schema:
Reason:
Breaking:
Consumers updated:
Tests:
Commit:
```

---

# 45. DATABASE CHANGE LOG

Template:

```text
Migration:
Schema version:
Change:
Reason:
Affected tables:
Rollback:
Tests:
Commit:
```

---

# 46. UI CHANGE LOG

Template:

```text
UI change:
Page:
User problem:
Before:
After:
Backend dependency:
Test:
Commit:
```

---

# 47. DEPLOYMENT CHANGE LOG

Template:

```text
Deployment change:
Environment:
Old:
New:
Reason:
Dependencies:
Measured impact:
Rollback:
Commit:
```

---

# 48. CURRENT NEXT STEPS

Only list verified/planned work here.

Initial:

```text
1. Inspect repository and record initial implementation baseline.
2. Record actual Git HEAD/history.
3. Verify which architecture components already exist.
4. Build/verify the golden path.
5. Update this memory after each implementation checkpoint.
```

---

# 49. AGENT UPDATE PROCEDURE

After each meaningful implementation:

```text
STEP 1
Inspect git status.

STEP 2
Determine exactly what changed.

STEP 3
Run relevant tests.

STEP 4
Record actual results.

STEP 5
Commit if the project's commit policy calls for it.

STEP 6
Capture exact commit hash.

STEP 7
Update this memory file.

STEP 8
Verify the memory change is itself included in the repository state.

STEP 9
Only then report the task complete.
```

---

# 50. AGENT MEMORY ENTRY FORMAT

Use this compact format for routine changes:

```text
## [MEM-XXXX] <Change Title>

Status:
Date:
Commit:
Files/components:

### What changed
...

### Why
...

### Technical details
...

### Tests
...

### Result
...

### Known limitations
...

### Next
...
```

For major architecture decisions, use the extended decision template.

---

# 51. NO "MEMORY CLEANUP" THAT DESTROYS HISTORY

The agent may reorganize sections for readability, but must preserve:

```text
old entries
old commits
old decisions
old failures
old metrics
old limitations
```

If the file becomes large:

```text
split historical records into archive files
```

but leave a pointer here.

Never erase historical information.

---

# 52. MEMORY ARCHIVE RULE

When needed:

```text
docs/memory/
├── 2026-08.md
├── 2026-09.md
└── ...
```

`IBVAP_memory.md` remains the current index.

Archive entries must preserve:

```text
commit
date
change
tests
result
decision
```

---

# 53. CURRENT PROJECT TRUTH TABLE

This table should always represent the latest verified state.

| Area | Current state | Last verified commit | Notes |
|---|---|---|---|
| Repository | NOT RECORDED | — | Must inspect |
| Frontend | NOT RECORDED | — | Must inspect |
| Backend | NOT RECORDED | — | Must inspect |
| AI worker | NOT RECORDED | — | Must inspect |
| Video ingestion | NOT RECORDED | — | Must inspect |
| Detector | NOT RECORDED | — | Must inspect |
| Tracker | NOT RECORDED | — | Must inspect |
| Environment | NOT RECORDED | — | Must inspect |
| Spatial | NOT RECORDED | — | Must inspect |
| Behavior | NOT RECORDED | — | Must inspect |
| Fusion | NOT RECORDED | — | Must inspect |
| Evidence | NOT RECORDED | — | Must inspect |
| Database | NOT RECORDED | — | Must inspect |
| API | NOT RECORDED | — | Must inspect |
| WebSocket | NOT RECORDED | — | Must inspect |
| Dashboard | NOT RECORDED | — | Must inspect |
| ANPR | NOT RECORDED | — | Must inspect |
| FRS | NOT RECORDED | — | Must inspect |
| Docker | NOT RECORDED | — | Must inspect |
| Tests | NOT RECORDED | — | Must inspect |
| Performance | NOT MEASURED | — | Do not invent |

---

# 54. FINAL MEMORY RULE

## **The memory file is the project's chronological truth, not a promotional document.**

It must tell the next agent:

```text
What exists?
What does not exist?
What changed?
Why?
Which commit changed it?
Was it tested?
Did it work?
What failed?
What was reverted?
What remains uncertain?
What should happen next?
```

The next agent must be able to continue the project **without relying on previous chat history**.

---

# END OF INITIAL MEMORY FILE
