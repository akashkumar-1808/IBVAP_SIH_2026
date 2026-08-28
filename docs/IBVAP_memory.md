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

**PHASE 0 COMPLETED — REPOSITORY BASELINE & DATA CONTRACTS INITIALIZED**

The project structure, shared schemas, default configuration, DECISIONS.md, and unit test suite have been established and verified.

## Current implementation status

```text
Frontend: NOT IMPLEMENTED (Scaffold pending in Phase 11)
Backend: PARTIALLY IMPLEMENTED (Schemas and configuration created)
AI worker: PARTIALLY IMPLEMENTED (Data contracts defined)
Database: PLANNED (Schema & ORM scheduled for Phase 1)
Detector: PLANNED (Interface defined in schema; scheduled for Phase 4)
Tracker: PLANNED (TrackState schema defined; scheduled for Phase 5)
Environment engine: PLANNED (EnvironmentState schema defined; scheduled for Phase 3)
Spatial engine: PLANNED (Polygon/Fence schemas defined; scheduled for Phase 6)
Behavior engine: PLANNED (Event & behavior schemas defined; scheduled for Phase 7)
Evidence fusion: PLANNED (Risk priority schemas defined; scheduled for Phase 8)
Evidence storage: PLANNED (Storage layout specified; scheduled for Phase 9)
ANPR: PLANNED (Optional isolated plugin)
FRS: PLANNED (Optional isolated plugin)
Docker: PLANNED (Scheduled for Phase 14)
Tests: IMPLEMENTED (Unit test suite active with pytest)
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

# 10. GIT HISTORY

## Current baseline

```text
Branch: main
HEAD: 92bce3e55e5cd98a8d03ef9a55f4da9959162e20
Working tree: clean
Total Commits: 4
1. 763a6a49782720d5f91afe652c4843b0c9783161 - Feat : Initial Commit ith docs placement
2. e6ff13a17e149777530cfdc7504450b3c5e73f48 - chore: initialize repository baseline, shared schemas, system config, and DECISIONS.md
3. 6b388943039f7fbdf2e62976c2a9e3949e2d932a - chore: add .gitignore and un-track pycache artifacts
4. 92bce3e55e5cd98a8d03ef9a55f4da9959162e20 - feat(backend): implement Supabase PostgreSQL and Storage data layer foundation
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
Commit:
```

## 11.3 AI Worker

```text
Status: NOT RECORDED
Entry point:
Video sources:
Frame queue:
Environment:
Detector:
Tracker:
Spatial:
Behavior:
Fusion:
Evidence:
Known issues:
Last changed:
Commit:
```

## 11.4 Detector

```text
Status: NOT RECORDED
Model:
Version:
Runtime:
Classes:
Artifact:
License:
Input:
Output:
Measured latency:
Measured FPS:
Known limitations:
Last changed:
Commit:
```

## 11.5 Tracker

```text
Status: NOT RECORDED
Tracker:
Version:
Input:
Output:
Measured performance:
Known issues:
Last changed:
Commit:
```

## 11.6 Environment Engine

```text
Status: NOT RECORDED
Inputs:
Outputs:
Lighting:
Visibility:
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
