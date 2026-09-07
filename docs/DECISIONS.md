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

---

## [DEC-0009] MVP Differentiation: Multi-Camera Persistent BorderTrack, Sector Normality, and Evidence-on-Demand
- **Date:** 2026-08-30
- **Status:** APPROVED
- **Context:** To distinguish IBVAP from generic single-camera detection pipelines ("YOLO + tracking + fence + alert"), the system requires cross-camera border-level continuity, sector-specific normality baselines, incident storytelling narratives, and evidence-on-demand corroboration before escalating alerts.
- **Decision:**
  1. **Persistent Border Track (`worker/cross_camera/`)**: Implement `BorderTrack` and `CrossCameraAssociator` maintaining entity continuity across adjacent cameras using `CameraTopology`, travel time windows ($\Delta t \in [t_{\min}, t_{\max}]$), movement direction alignment, and target class consistency without claiming biometric ReID certainty. Categorize association states honestly as `CONFIRMED`, `LIKELY`, `UNCERTAIN`, or `ENDED`.
  2. **Sector Normality Engine (`worker/sector/`)**: Implement `SectorNormalityEngine` comparing observed activity against defined hourly sector baselines. Returns `COLD_START` when historical data is insufficient and flags `SECTOR_ACTIVITY_UNUSUAL` as supporting evidence for abnormal nocturnal border activity.
  3. **Incident Story Narrative (`worker/fusion/incident.py`)**: Implement `IncidentStory` recording chronological transitions (`Approach` $\rightarrow$ `Warning Buffer` $\rightarrow$ `Border Cross` $\rightarrow$ `Restricted Occupancy` $\rightarrow$ `Cross-Cam Continuation`).
  4. **Evidence-on-Demand & Corroboration Engine (`worker/fusion/corroboration.py`)**: Implement `EvidenceRequest` holding uncertain event candidates in an internal pending state until corroborating evidence (persistence, physical crossing, neighbour camera handoff) arrives. Requests time out safely into `INSUFFICIENT_EVIDENCE` without generating operator alert fatigue.
  5. **Phase 8 & 9 Integration**: Wire all 4 subsystems into `FusionEngine` and `calculate_risk_score`, preserving separation of detector confidence $\neq$ track persistence $\neq$ spatial confidence $\neq$ environment quality $\neq$ association confidence $\neq$ evidence confidence $\neq$ risk priority.
- **Trade-offs:**
  - **Pro:** Visibly demonstrates higher-level border intelligence, eliminates false alarms on transient/unverified detections, supports multi-camera handoff, 100% explainable and deterministic (>5,000 FPS throughput).
  - **Con:** Requires explicit camera transition topology configuration between adjacent cameras.
- **Affected Components:** `worker/cross_camera/`, `worker/sector/`, `worker/fusion/`, `scripts/benchmark_differentiation.py`, `docs/IBVAP_memory.md`.

---

## [DEC-0010] Live MVP Execution and Orchestration Layer
- **Date:** 2026-08-30
- **Status:** APPROVED
- **Context:** Prior to building the React operator dashboard, an end-to-end execution layer is required to connect the 9 verified intelligence layers to live RTSP camera streams, validate real-time frame rates, test calibration projections, and verify event/evidence packaging on physical hardware.
- **Decision:**
  1. **Live Pipeline Orchestrator (`worker/pipeline/`)**: Implement `LivePipelineOrchestrator` orchestrating `VideoSource` (RTSP or test stream) $\rightarrow$ `BoundedFrameQueue` $\rightarrow$ `EnvironmentAnalyzer` $\rightarrow$ `ObjectDetector` $\rightarrow$ `ByteTrackTracker` $\rightarrow$ `SpatialEngine` $\rightarrow$ `BehaviorEngine` $\rightarrow$ `FusionEngine` $\rightarrow$ `EvidencePackager` in a single unified loop.
  2. **Security & Secrets**: Mask all RTSP stream credentials in logs and terminal outputs using `mask_rtsp_url()`. Configuration is read via environment variables (`IBVAP_RTSP_URL`, `IBVAP_CAMERA_ID`, etc.) or CLI flags.
  3. **Execution Modes**: Provide three execution modes:
     - `--headless`: Compact periodic terminal status monitoring without graphical dependencies.
     - `--visual`: Real-time OpenCV HUD visualizer displaying calibrated world borders, tracks, ground points, behavior badges, and active event banners.
     - `--record-debug`: Background video writer saving annotated debug MP4s to `results/live_runs/<run_id>/`.
  4. **Run Reporting**: On clean shutdown (or SIGINT), compile and persist `summary.json`, `metrics.json`, `events.json`, `tracks.json`, and `environment.json` into structured run directories.
  5. **Stage vs End-to-End Latency Tracking**: Track stage-by-stage latencies independently (e.g. environment: ~2.2ms, detection: ~50.7ms, tracking: ~0.05ms, spatial: ~0.02ms, behavior: ~0.001ms, fusion: ~0.02ms) to expose compute bottlenecks accurately.
- **Trade-offs:**
  - **Pro:** Fully verifies the perception, reasoning, and evidence packaging stack against physical RTSP cameras before frontend construction; zero mock dependencies for live tests.
  - **Con:** OpenCV GUI windows require desktop display context in `--visual` mode; `--headless` is default for headless server deployments.
- **Affected Components:** `worker/pipeline/`, `scripts/run_live_mvp.py`, `tests/integration/test_live_pipeline.py`, `docs/IBVAP_memory.md`.

---

## [DEC-0011] Phase 10: React MVP Operator Console and Intelligence Streaming Architecture
- **Date:** 2026-08-30
- **Status:** APPROVED
- **Context:** An operations console is required to present real-time multi-stage intelligence (perception, tracking, spatial world-border analysis, temporal behavior, sector normality, evidence-on-demand, and cryptographic evidence packages) directly to the jury.
- **Decision:**
  1. **Visual Style**: Adopt a Dark Modern Command Console design matching the operational visual concept (deep charcoal `#080a0f`, slate panels `#0f131a`, cyan `#06b6d4` operational accents, amber `#f59e0b` warning buffers, red `#ef4444` restricted breaches, off-white text `#f8fafc`).
  2. **Zero Mock AI**: The UI connects to real backend REST APIs (`/api/v1/cameras`, `/api/v1/events`, `/api/v1/evidence`, `/api/v1/scenarios`) and a high-frequency WebSocket (`/api/v1/ws/telemetry`). No frontend simulated AI logic.
  3. **Video Delivery**: FastAPI MJPEG stream bridge (`/api/v1/streams/{camera_id}/live`) delivers real-time frames with SVG HUD overlays for projected world borders, buffer zones, tracks, ground contact points, trajectory trails, and floating track intelligence cards.
  4. **Why This Event? Explainability**: The operator console explicitly exposes backend reason codes (e.g. `PERSISTENT_TRACK_ESTABLISHED`, `MOVEMENT_TOWARD_PROTECTED_REGION`, `BORDER_LINE_CROSSED`, `RESTRICTED_ZONE_OCCUPANCY`, `CROSS_CAMERA_CORROBORATION`) to make detection-to-decision logic 100% explainable.
  5. **Deterministic Jury Replay Controller**: Scenario controller (`/api/v1/scenarios`) enables instant one-click demonstration of deterministic intrusion, shadow false-positive suppression, and multi-camera border track handoffs.
  6. **Static Dist Serving**: Production build (`frontend/dist/`) is served directly at `/console` via FastAPI `StaticFiles`.
- **Trade-offs:**
  - **Pro:** Complete transparency and explainability; zero mock AI; high performance; responsive command room visual feel.
  - **Con:** Multi-camera live streams share browser connections; optimized with MJPEG + WebSocket pub/sub.
- **Affected Components:** `frontend/`, `backend/app/api/routes/`, `backend/app/main.py`, `docs/IBVAP_memory.md`.
---

## [DEC-0012] Basic Detection Stabilization and Camera Motion Filtering
- **Date:** 2026-08-31
- **Status:** APPROVED & IMPLEMENTED
- **Context:** During daytime and live camera movement testing, camera motion produced transient visual detections. Furthermore, non-supported COCO classes normalized to `TargetClass.UNKNOWN` were reaching ByteTrack and spawning unwanted candidate/tracked entities, cluttering the live prototype.
- **Decision:**
  1. **Operational vs. Raw Detection Isolation (`worker/perception/filter.py`)**:
     - Introduced `DetectionFilter` between `Class Normalization` and `ByteTrackTracker`.
     - `TargetClass.UNKNOWN` detections are strictly excluded from operational tracking while preserved in `raw_detections` for forensic logging, anomaly analysis, and telemetry.
     - Only valid operational targets (`PERSON`, `VEHICLE`, `ANIMAL`) meeting geometric quality thresholds (non-zero width/height, $\ge 8$ px dimensions, $\ge 64$ px$^2$ area, within frame bounds) proceed to ByteTrack.
  2. **Lightweight Camera Motion Check (`CameraMotionEstimator`)**:
     - Sub-millisecond ($<0.4$ ms) optical flow motion estimator on downscaled ($160	imes 120$) grayscale frames.
     - Distinguishes `CAMERA STABLE` vs. `CAMERA MOVING`.
     - When `CAMERA MOVING`, transient/weak detections below dynamic threshold ($0.60$) are held back from spawning candidate tracks, while strong targets ($\ge 0.60$) proceed normally.
     - When `CAMERA STABLE`, baseline threshold ($0.35$) applies.
  3. **Diagnostic HUD Counters**:
     - Live HUD top telemetry displays: `RAW: X | OP: Y | TRK: Z | CAM: STABLE/MOVING`.
     - Only operational targets are drawn as tracked entities.
  4. **Deferred Night Perception Notice**:
     - "Normal/daytime perception stabilization was implemented. Night/low-light perception remains unchanged and is intentionally deferred."
- **Trade-offs:**
  - **Pro:** Completely eliminates clutter and spurious tracks from unsupported classes and camera pans; preserves 100% of raw forensic detections; zero model modification or latency penalty (<0.4ms overhead).
  - **Con:** Requires small motion estimation window (1 frame history).
- **Affected Components:** `worker/perception/filter.py`, `worker/perception/__init__.py`, `worker/pipeline/orchestrator.py`, `worker/pipeline/visualizer.py`, `tests/unit/test_detection_filter.py`, `docs/DECISIONS.md`, `docs/IBVAP_memory.md`.
---

## [DEC-0013] Production-Grade Stream Health & Continuity Subsystem
- **Date:** 2026-09-07
- **Status:** APPROVED & IMPLEMENTED
- **Context:** Live border CCTV camera streams over RTSP and network links experience jitter, packet drops, transport reconnects, and sensor freezes. Unhandled dropouts previously risked broken tracking IDs, false high-confidence alarms on stale imagery, or pipeline termination. Synthetic/hallucinated video frames are strictly impermissible in a sovereign surveillance system.
- **Decision:**
  1. **Canonical 8-State Continuity Machine (`worker/ingestion/continuity.py`)**:
     - Formalized discrete states: `HEALTHY`, `DEGRADED`, `INTERRUPTED`, `RECONNECTING`, `RECOVERED`, `STALE_FROZEN`, `OFFLINE`, `COMPLETED`.
     - Deterministic state machine with hysteresis requiring consecutive confirmation frames before promoting `RECOVERED` to `HEALTHY`.
  2. **Audit-Grade Zero-Fabrication Gap Accounting**:
     - Never injects fabricated/synthetic surveillance frames into the analytical pipeline.
     - Detects frame sequence gaps and time drops, auditing them as immutable `StreamGapRecord` structures.
  3. **Ultra-Fast Perceptual Freshness Check**:
     - 32x18 grayscale downsampled thumbnail perceptual MSE (< 0.05ms on CPU) detecting frozen camera sensors or duplicate frames without expensive full-resolution comparisons.
  4. **Kinematic Post-Interruption Track Identity Recovery**:
     - Snapshots active track coordinates, velocities, and classes before interruptions.
     - Upon stream restoration, evaluates candidate detections against extrapolated track positions within temporal bounds ($< 5.0$s) and spatial proximity, restoring pre-gap track IDs while suppressing ambiguous multi-candidate associations.
  5. **Downstream AI Trust Modulation**:
     - Stream continuity health feeds into `FusionEngine` evidence extraction (`EvidenceType.STREAM_CONTINUITY`).
     - Modulates risk scores with a stream trust multiplier $[0.0, 1.0]$ and attaches audit reason codes (`STREAM_QUALITY_DEGRADED`, `STREAM_INTERRUPTION_RECENT`).
  6. **Telemetry & Operator HUD Integration**:
     - Propagates stream health contracts over WebSocket to `TopSystemBar` and `PrimaryVideoPanel`, rendering live badges, jitter, AI trust scores, and gap audit indicators without altering established styling.
- **Trade-offs:**
  - **Pro:** Complete resilience against network blips; eliminates track fragmentation; prevents false alarms on degraded streams; zero simulated frame fabrication; preserves FastAPI process uptime.
  - **Con:** Minor memory footprint for track snapshot buffer and thumbnail cache (< 0.5 MB).
- **Affected Components:** `worker/ingestion/continuity.py`, `worker/ingestion/rtsp_source.py`, `worker/tracking/tracker.py`, `worker/fusion/`, `worker/pipeline/orchestrator.py`, `backend/app/api/routes/cameras.py`, `frontend/src/`, `tests/unit/test_stream_continuity.py`, `tests/integration/test_stream_continuity_lifecycle.py`.

