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

---

## [DEC-0005] Baseline Object Detector Architecture & Runtime
- **Date:** 2026-08-28
- **Status:** APPROVED
- **Context:** The baseline perception layer requires real-time generic object detection (person, vehicle, animal) wrapped in a decoupled interface to establish an un-adapted baseline for later comparison with environment-adaptive perception.
- **Decision:**
  1. Define a strict `DetectorInterface` in `worker/perception/base.py` (`load`, `warmup`, `infer`, `get_metadata`, `close`) consuming canonical `FramePacket` objects.
  2. Integrate Ultralytics YOLOv8 / PyTorch real-time detector (AGPL-3.0 / enterprise runtime) as the immediately runnable baseline in the local Python environment where `rfdetr` native package is not pre-installed.
  3. Strict class mapping: Raw model classes (e.g. `person`, `car`, `truck`, `dog`, `horse`) are mapped to IBVAP `TargetClass` enums (`PERSON`, `VEHICLE`, `ANIMAL`, `UNKNOWN`) while preserving original class index and raw labels in `Detection.metadata`.
  4. Non-leakage guarantee: Detector confidence is strictly documented and handled as model prediction confidence, completely decoupled from risk scoring and tracking persistence.
- **Trade-offs:** Provides 22+ FPS CPU inference immediately without custom C++/CUDA compilation, while maintaining a pure interface enabling drop-in replacement of RF-DETR or ONNX models.
- **Affected Components:** `worker/perception/`, `tests/unit/test_detector.py`, `tests/replay/test_detector_replay.py`, `scripts/benchmark_detector.py`.

---

## [DEC-0006] Replace Camera-Owned Pixel Fence with World-Owned Border Model
- **Date:** 2026-08-30
- **Status:** APPROVED IMPLEMENTATION DIRECTION
- **Context:** The Phase 6 spatial engine defines virtual fences as manually placed pixel-coordinate line segments per camera. Each camera independently owns its fence definition with no shared world reference. When multiple cameras observe the same physical boundary, there is no semantic link between their pixel fences.
- **Decision:**
  1. Introduce a global world-space border model where ONE logical border definition exists as the source of truth.
  2. Cameras do NOT define the logical border itself. Cameras define how they observe the border through calibrated projections.
  3. Camera calibration uses explicit world-to-image point correspondences and planar homography for the prototype.
  4. The projected border in each camera's image space is a DERIVED VIEW, not an independent configuration.
  5. Ground-contact point (bottom-center of bounding box) is used to locate tracked objects in world space.
  6. Side determination (permitted / buffer / restricted) and crossing detection are computed in world coordinates.
  7. Crossing confirmation requires sustained multi-frame evidence, preventing jitter-induced false crossings.
  8. The old pixel-fence model is preserved as `LEGACY_IMAGE_SPACE` fallback for uncalibrated cameras.
  9. `TERRAIN_3D` mode is explicitly declared as NOT IMPLEMENTED; only `PLANAR_GROUND` is supported in the prototype.
- **Trade-offs:**
  - **Pro:** Scalability (new camera inherits existing border), semantic correctness (two cameras reference same boundary), consistent real-world representation.
  - **Con:** Calibration complexity (requires world-image correspondences), camera registration overhead, uncertainty from non-planar terrain, homography limitations on hilly ground.
- **Affected Components:** `worker/spatial/`, `backend/app/schemas/spatial.py`, `supabase/migrations/`, `configs/`, `docs/spatial_border_model.md`.

---

## [DEC-0007] Multi-Modal Evidence Fusion & Event Intelligence Architecture
- **Date:** 2026-08-30
- **Status:** APPROVED
- **Context:** Upstream perception (YOLOv8), tracking (ByteTrack), environmental analysis, world-border spatial intelligence, and temporal behaviors produce independent observations. A principled fusion layer is required to synthesize these signals into explainable, prioritized security events without opaque neural classifiers or LLM hallucination.
- **Decision:**
  1. Implement `FusionEngine` behind `FusionEngineInterface` in `worker/fusion/`.
  2. Maintain strict semantic separation: Detector Confidence $\neq$ Track Persistence $\neq$ Risk Priority Score $\neq$ Threat Intent.
  3. Adopt a transparent, rule-based weighted mathematical scoring model bounding priority scores strictly in $[0, 100]$.
  4. Implement discrete operational priority tiers: `INFO` ($\le 30$), `LOW` ($31-50$), `MEDIUM` ($51-70$), `HIGH` ($71-85$), `CRITICAL` ($> 85$).
  5. Enforce stateful event lifecycle (`CANDIDATE` $\rightarrow$ `ACTIVE` $\rightarrow$ `RESOLVED`) with automatic deduplication across sustained frames (updating single `EventRecord` duration) and configurable cooldown to prevent alert spam.
  6. Calibration and environmental safeguards: When camera spatial calibration is `INVALID` or `UNCERTAIN`, border crossing confidence is penalized and flagged with uncertainty rather than generating false critical alerts.
  7. Deterministic factual summaries: Human-readable explanations are synthesized purely from structured facts and machine-readable `FusionReasonCode`s without LLM dependencies.
- **Trade-offs:**
  - **Pro:** 100% deterministic, explainable, audit-traceable, high throughput (>1,500 FPS on CPU), zero hallucination risk.
  - **Con:** Requires explicit threshold and weight configuration; learned multi-modal weights can be researched in future phases.
- **Affected Components:** `worker/fusion/`, `backend/app/schemas/events.py`, `docs/IBVAP_Architecture.md`, `docs/IBVAP_memory.md`.

---

## [DEC-0008] Structured Evidence Storage & Cryptographic Packaging Architecture
- **Date:** 2026-08-30
- **Status:** APPROVED
- **Context:** Actionable `EventRecord`s produced by the Phase 8 Fusion Engine must be sealed with immutable forensic evidence (raw and annotated keyframe snapshots, pre-event and incident video clips, and audit manifests) to satisfy court-admissible legal chain of custody and non-repudiation requirements.
- **Decision:**
  1. Implement `EvidencePackager` behind `EvidencePackagerInterface` in `worker/evidence/`.
  2. Rolling Frame Ring Buffer (`RollingFrameBuffer`): Maintain a lightweight in-memory ring buffer of recent frames per camera (bounded by `(pre_event_seconds + post_event_seconds + 10) * fps`) allowing instant zero-latency extraction of pre-event context without re-querying disk or video streams.
  3. Forensic Snapshots: Save raw uncompressed/high-quality JPEG keyframes along with forensic HUD-annotated keyframes (containing top metadata banner, bounding boxes, ground-contact points, and projected world borders).
  4. Video Clips: Compile chronological MP4 video clips for pre-event (e.g. 5s buffer preceding intrusion) and incident duration.
  5. Cryptographic Sealing: Compute hex-encoded SHA-256 hashes of all media artifacts and embed them in an immutable `manifest.json`. The package itself is sealed with the manifest's SHA-256 hash.
  6. Tamper Verification: Provide `verify_package()` which checks all artifact checksums against the manifest to detect any byte alterations.
  7. Dual Storage Mode: Write packages to structured local directories (`storage/evidence/{camera_id}/{event_id}/`) with optional, non-blocking asynchronous cloud upload to Supabase Storage.
- **Trade-offs:**
  - **Pro:** Complete forensic chain of custody, tamper-evident, non-blocking to perception pipelines, deterministic verification.
  - **Con:** Memory overhead for ring buffers (bounded to ~10–15s per camera) and disk storage for high-quality MP4 clips.
- **Affected Components:** `worker/evidence/`, `worker/spatial/engine.py`, `backend/app/db/storage.py`, `docs/IBVAP_memory.md`.



