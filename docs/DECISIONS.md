# IBVAP — Architecture & Engineering Decisions Log (DECISIONS.md)

This document tracks all formal architectural and engineering decisions made during the lifecycle of the IBVAP project, adhering to `IBVAP_Rules.md`.

---

## [DEC-0001] Baseline Architecture & Modularity Enforcement
- **Date:** 2026-08-28
- **Status:** APPROVED
- **Context:** IBVAP requires a software-only, environment-adaptive intelligence layer operating on existing IP CCTV / MP4 feeds without dedicated smart camera hardware or physical sensor retrofits.
- **Decision:**
  1. Decouple continuous ML/video analytics from the API layer: the continuous inference loop runs strictly within the AI Worker process.
  2. The FastAPI backend handles camera registries, configuration persistence, SQLite database CRUD, REST APIs, and WebSocket alert streams.
  3. The core perception, tracking, spatial, behavior, and fusion engines are structured behind explicit interfaces (`DetectorInterface`, `TrackerInterface`, `SpatialEngine`, `BehaviorEngine`, `FusionEngine`).
  4. Decision confidence is decomposed into three distinct dimensions: Detector Confidence, Track Persistence, and Event Risk Priority.
- **Trade-offs:** Introduces inter-process / IPC communication patterns between the worker and backend, but protects API responsiveness, prevents pipeline deadlocks, and guarantees modularity.
- **Affected Components:** `worker/`, `backend/`, `configs/`.

---

## [DEC-0002] Multi-Object Tracking Baseline
- **Date:** 2026-08-28
- **Status:** APPROVED
- **Context:** Single-frame detections suffer from false positives and cannot evaluate trajectory or dwell behavior.
- **Decision:** Adopt ByteTrack association algorithm (Kalman Filter + Hungarian IoU matching on high/low confidence boxes) as the default tracking engine. Tracks maintain lifecycle states (`candidate`, `tracked`, `lost`, `expired`).
- **Trade-offs:** Fast CPU-efficient multi-object tracking without requiring continuous deep ReID inference on every frame.
- **Affected Components:** `worker/tracking/`.

---

## [DEC-0003] Environment-Aware Dynamic Thresholding
- **Date:** 2026-08-28
- **Status:** APPROVED
- **Context:** Border conditions fluctuate across night/day, fog, and rain, causing detection dropouts and noisy false positives.
- **Decision:** Implement a lightweight `EnvironmentEngine` evaluating Laplacian variance (blur/sharpness), luminance histograms, and contrast on incoming frames. Trigger selective low-light enhancements (CLAHE / Gamma) only when quality drops below configurable thresholds, and scale event certainty accordingly.
- **Trade-offs:** Adds minimal CPU overhead per frame (~2-4ms) while significantly improving false alarm suppression and explainability.
- **Affected Components:** `worker/environment/`, `worker/perception/`, `worker/fusion/`.

---

## [DEC-0004] Supabase PostgreSQL & Supabase Storage Backend Foundation
- **Date:** 2026-08-28
- **Status:** APPROVED
- **Context:** Multi-developer collaboration and shared persistent storage require a robust cloud/remote PostgreSQL database and object storage for security incidents without machine-specific SQLite file locks or local-only storage.
- **Decision:**
  1. Adopt Supabase PostgreSQL as the primary shared application database, accessed via FastAPI backend repositories and PostgREST client.
  2. Adopt Supabase Storage (`evidence` bucket) for security event frame snapshots (`.jpg`) and short video clip buffers (`.mp4`).
  3. Strict architectural boundary: The AI/video worker runs independently and communicates structured data through the FastAPI backend. Continuous video feeds and heavy ML inference do **not** run inside Supabase.
  4. Environment configurations are externalized (`.env.example`) with strict SecretStr masking to prevent credential leakage.
- **Trade-offs:** Requires network connectivity to the Supabase endpoint for persistent event storage, while local offline cache fallback remains supported.
- **Affected Components:** `backend/app/config/`, `backend/app/db/`, `supabase/migrations/`, `docs/SUPABASE_SETUP.md`.
