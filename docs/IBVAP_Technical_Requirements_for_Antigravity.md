# IBVAP — Intelligent Border Video Analytics Platform
## Technical Requirements & Implementation Specification for Antigravity

**Document status:** Engineering specification / hackathon build specification  
**Target:** SIH-level software-only prototype, with a path toward hardened field deployment  
**Primary constraint:** Existing IP CCTV infrastructure; no dedicated smart-camera hardware required  
**Primary differentiator:** Environment-adaptive perception + temporal/spatial reasoning + evidence fusion for lower false-alarm operation across heterogeneous terrain, weather, lighting, and visibility conditions.

---

# 0. Executive Decision

## Build this — do not build a monolithic "YOLO + dashboard" application

IBVAP shall be implemented as a modular video-intelligence pipeline:

```text
Existing IP CCTV
      |
      v
RTSP / ONVIF ingestion
      |
      v
Video normalization + frame sampling
      |
      v
Scene / environment condition estimation
      |
      v
Adaptive perception
      |
      +--> person / vehicle / animal / unknown detection
      |
      v
Multi-object tracking
      |
      v
Spatial reasoning
      |
      +--> virtual fence
      +--> restricted/safe zones
      +--> movement direction
      |
      v
Temporal / behavior reasoning
      |
      +--> loitering
      +--> persistent approach
      +--> boundary crossing
      +--> suspicious movement patterns
      |
      v
Optional supporting intelligence
      +--> uniform/civilian classifier
      +--> face detection / recognition
      +--> ANPR
      |
      v
Evidence fusion + calibrated confidence
      |
      v
Risk / event engine
      |
      +--> low / medium / high priority
      |
      v
Evidence clip + event record
      |
      v
Command dashboard / API / notifications
```

The project shall **not** claim that software can guarantee visibility in conditions where the camera has no usable information. The system must instead estimate scene quality, adapt processing, preserve uncertainty, and avoid forcing uncertain observations into hard decisions.

---

# 1. Problem Statement Alignment

## 1.1 SIH requirements mapped to implementation

| SIH capability | IBVAP implementation |
|---|---|
| Existing CCTV | RTSP/ONVIF ingestion layer |
| Human detection | General object detector |
| Human tracking | Multi-object tracker |
| Vehicle detection/classification | Detector + optional vehicle attribute classifier |
| Face detection | Dedicated face detector plugin |
| Face recognition | Optional watchlist/embedding plugin; human review required |
| ANPR | Vehicle ROI -> plate detector -> OCR -> temporal aggregation |
| Virtual fence | Polygon/line zone engine |
| Suspicious activity | Temporal + spatial event rules; optional learned behavior model |
| Night movement detection | Environment estimator + low-light processing + tracking |
| Real-time alerts | Event engine + WebSocket/REST notifications |
| Event logging | SQLite for demo; PostgreSQL/Timescale-style architecture later |
| Existing command/control integration | REST/WebSocket/event-bus APIs |
| Cost-effective | Software-only, model/runtime modularity |
| Remote deployment | Offline-capable/local-first inference and store-and-forward events |
| Scalable | Multi-camera worker architecture and optional centralized inference |

---

# 2. Research-Derived Design Basis

The supplied research and papers indicate several important design lessons:

1. Traditional/manual surveillance is difficult in remote, hostile, large, and environmentally variable terrain.
2. The Digital Border Surveillance System paper uses a custom dataset for uniformed persons, non-uniformed civilians, and animals because uniformed personnel were not publicly available; it also combines detection, movement analysis, alarms, video storage and a control-room interface.
3. That study reports reduced accuracy/precision for distinguishing uniformed and non-uniformed people because both classes are visually similar.
4. Its movement logic explicitly ignores lateral movement and treats movement toward a protected direction differently.
5. The paper describes a low/intermediate/high-level pipeline: object processing -> tracking -> behavior/activity -> identification -> alarm/control.
6. The research report for IBVAP highlights environment robustness, false alarms, legacy-CCTV integration, edge/fog deployment, and evidence fusion as important gaps/requirements.

**IBVAP therefore treats the cited work as a baseline to extend, not as the final architecture.**

---

# 3. Core Design Principles

## P1 — Detect first, decide later

Object detector outputs are evidence, not security decisions.

Bad:

```python
if person_detected:
    raise_alarm()
```

Required:

```text
detection
    +
tracking persistence
    +
zone context
    +
direction
    +
behavior
    +
environment quality
    +
optional identity evidence
    ->
event confidence
    ->
risk level
```

## P2 — Environment is an input to perception

Every camera must maintain an environment state:

```json
{
  "lighting": "night",
  "brightness": 0.17,
  "blur_score": 0.31,
  "visibility": "poor",
  "weather_hint": "rain",
  "terrain_profile": "forest",
  "quality_score": 0.42
}
```

## P3 — Do not overclaim

The system must be allowed to emit:

```text
UNCERTAIN
LOW VISIBILITY
INSUFFICIENT VISUAL EVIDENCE
```

rather than inventing a high-confidence answer.

## P4 — Existing CCTV first

No sensor retrofit is required for the core system.

Thermal, PIR, radar, drone, LiDAR, etc. can be future adapters, but are out of scope for the baseline prototype.

## P5 — Human remains in the loop

IBVAP produces decision support and evidence. It must not autonomously authorize detention, use of force, or irreversible action.

---

# 4. Scope

## 4.1 In scope for prototype

- IP-camera/recorded-video ingestion
- Multi-camera management
- Person/vehicle/animal/unknown detection
- Multi-object tracking
- Scene-condition estimation
- Low-light enhancement
- Camera-specific zones
- Virtual fence crossing
- Direction-of-motion estimation
- Dwell/loitering detection
- Persistent approach detection
- Event/risk scoring
- Evidence clip generation
- Event database
- Live dashboard
- Alert feed
- Search/filter of historical events
- Optional uniform/civilian classifier
- Optional ANPR
- Optional face detection/recognition
- Offline/local inference
- Health/observability endpoints

## 4.2 Out of scope for first prototype

- Autonomous enforcement
- Weapon engagement or target assignment
- Tactical border patrol guidance
- Classified/operational military data
- Guaranteed detection through opaque/fully saturated/black frames
- Full-scale biometric watchlist deployment
- Production-grade federated learning
- Multi-sensor hardware fusion requiring non-CCTV hardware
- Automatic cross-camera identity conclusions without confidence and policy controls

---

# 5. Recommended Open-Source Technology Baseline

## 5.1 Primary recommendation

### Detector — RF-DETR

Use **RF-DETR Nano/Small** as the preferred baseline detector for a clean, permissive open-source stack.

Why:

- real-time transformer detector
- designed for fine-tuning
- detection + instance segmentation family
- Apache-2.0 for the open-source core and Apache-designated models
- current project documentation reports strong COCO accuracy/latency trade-offs

Repository:
https://github.com/roboflow/rf-detr

Use:

```text
RF-DETR-N / RF-DETR-S
```

for prototype evaluation.

Do not assume COCO performance equals border performance. Border-specific validation is mandatory.

### Alternative — Ultralytics YOLO

YOLO is technically excellent and easy to use, but the current Ultralytics licensing page states that use of its code/models/training pipelines is under AGPL-3.0 unless an Enterprise license is obtained for proprietary/private/commercial usage.

Therefore:

- acceptable for an explicitly open-source hackathon prototype if licensing obligations are acceptable;
- not the default recommendation for a future proprietary/deployable IBVAP stack.

References:
https://docs.ultralytics.com/models/
https://www.ultralytics.com/license

---

## 5.2 Tracking

### Primary — BoT-SORT

Recommended when re-identification and camera-motion robustness are useful.

Features:

- tracking-by-detection
- motion compensation options
- ReID support
- strong multi-object tracking baseline

Repository:
https://github.com/NirAharon/BoT-SORT

License: MIT.

### Simple fallback — ByteTrack

Recommended first when implementation simplicity and speed are more important.

Repository:
https://github.com/ifzhang/ByteTrack

Design principle:
- do not discard low-confidence detections too early;
- use temporal association to recover objects through imperfect frames.

### Lightweight fallback — Norfair

Useful for rapid prototypes and custom detectors.

Repository:
https://github.com/tryolabs/norfair

License: BSD-3-Clause.

### Convenience analytics — supervision

Useful for:
- zones
- line crossings
- annotations
- tracking utilities

Repository:
https://github.com/roboflow/supervision

License: MIT.

Do not let the analytics library become the source of the project's core decision logic; keep IBVAP's event engine explicit and testable.

---

# 6. Video Ingestion Requirements

## 6.1 Supported inputs

MUST support:

1. RTSP IP camera streams
2. local MP4/MKV/AVI files for reproducible testing
3. webcam input for development

SHOULD support:

- ONVIF-discovered cameras
- HLS/WebRTC input via adapter
- reconnect after stream drop

## 6.2 Recommended implementation

Use:

- GStreamer for production-style streaming pipelines
- FFmpeg for debugging/transcoding and evidence clips
- OpenCV for image processing and developer convenience

GStreamer `rtspsrc` supports RTSP transport over TCP/UDP and handles RTP session details such as jitter removal and packet reordering.

Reference:
https://gstreamer.freedesktop.org/documentation/rtsp/rtspsrc.html

ONVIF Profile S is the relevant interoperability baseline for IP video streaming/configuration.

Reference:
https://www.onvif.org/profiles/profile-s/

## 6.3 Ingestion contract

Every decoded frame MUST produce:

```python
FramePacket(
    camera_id: str,
    frame_id: int,
    timestamp_utc: datetime,
    image: ndarray,
    stream_width: int,
    stream_height: int
)
```

## 6.4 Stream reliability

MUST implement:

- connection timeout
- retry with exponential backoff
- dropped-frame accounting
- reconnect
- stale-stream detection
- FPS measurement
- last-frame timestamp
- camera health status

Example health states:

```text
ONLINE
DEGRADED
STALE
DISCONNECTED
AUTH_ERROR
DECODER_ERROR
```

---

# 7. Frame Processing Architecture

Do not process every camera at maximum resolution forever.

Required pipeline:

```text
decoder
  |
  v
bounded frame queue
  |
  +--> environment analyzer (low cost, frequent)
  |
  +--> detector (sampled / batched)
  |
  +--> tracker (every required frame/update)
  |
  +--> event engine
```

## 7.1 Queue policy

A real-time camera pipeline MUST prefer freshness over infinite buffering.

Use a bounded queue:

```text
MAX_QUEUE = configurable, e.g. 2-5 frames
```

When full:

```text
drop oldest waiting frame
```

Do not allow 10-second latency caused by backlog.

---

# 8. Environment / Scene Condition Engine

This is a core IBVAP differentiator.

## 8.1 Outputs

The engine MUST estimate:

### Illumination
- mean luminance
- percentile luminance
- histogram spread

### Sharpness / blur
- Laplacian variance or equivalent blur metric

### Contrast
- local/global contrast

### Noise / compression proxy
- optional statistical score

### Visibility
- estimated normal/degraded visibility

### Weather hints
- rain/snow/fog heuristic or learned classifier

### Terrain profile
Prototype:
- operator configured per camera

Post-prototype:
- learned scene classifier

## 8.2 Environment vector

```python
EnvironmentState(
    brightness: float,
    contrast: float,
    blur: float,
    noise: float,
    visibility: str,
    lighting: str,
    weather: str,
    terrain: str,
    quality_score: float
)
```

## 8.3 Quality score

Use a normalized 0-1 score.

Example conceptual formula:

```text
quality =
    0.30 * illumination_quality +
    0.25 * sharpness_quality +
    0.20 * contrast_quality +
    0.15 * visibility_quality +
    0.10 * stream_quality
```

These weights are prototype defaults only. They MUST be configurable and tuned using validation footage.

---

# 9. Adaptive Perception Engine

## 9.1 Baseline

Use one primary detector and adjust preprocessing around it.

DO NOT create five independently maintained deep models for day/night/rain/snow during the first build.

Pipeline:

```text
frame
 |
 v
environment state
 |
 +--> normal scene -> direct inference
 |
 +--> low light -> optional Retinex/illumination enhancement
 |
 +--> high blur -> temporal stabilization / confidence handling
 |
 +--> poor visibility -> conservative decision thresholds
 |
 v
detector
```

## 9.2 Low-light enhancement

Primary research candidate:

### Retinexformer

Repository:
https://github.com/caiyuanhao1998/Retinexformer

License: MIT.

Use it as an optional enhancement module, NOT as a mandatory per-frame stage.

Reason:
- enhancement adds latency;
- enhancement can introduce artifacts;
- excessive enhancement can create false visual structure.

Recommended policy:

```text
if quality_score < threshold and lighting == night:
    enhancement = ON
else:
    enhancement = OFF
```

## 9.3 Fast fallback enhancement

Use OpenCV-based:

- gamma correction
- CLAHE
- denoising
- contrast normalization

These are easier to run in real time.

## 9.4 Enhancement evaluation

Do not evaluate enhancement only by how pretty the frame looks.

Evaluate:

```text
before enhancement:
    person recall

after enhancement:
    person recall

false positives before/after

tracking continuity before/after
```

The enhancement module is successful only if downstream detection/tracking improves.

---

# 10. Object Detection Requirements

## 10.1 Base classes

At minimum:

```text
person
car
truck
bus
motorcycle
bicycle
animal
unknown
```

The exact animal categories can be collapsed into `animal` in the event layer.

## 10.2 Detection output

```json
{
  "camera_id": "cam_07",
  "frame_id": 18291,
  "timestamp": "2026-08-28T08:10:11.223Z",
  "class": "person",
  "confidence": 0.87,
  "bbox": [x1, y1, x2, y2]
}
```

## 10.3 Detection confidence

Detector confidence MUST NOT be interpreted directly as risk.

Example:

```text
person_confidence = 0.89
```

means:

> the detector is confident that the visual region resembles a person.

It does NOT mean:

> 89% probability of threat.

---

# 11. Small / Distant Object Strategy

This is essential for CCTV.

Required techniques:

1. Maintain camera-specific ROI configuration.
2. Prefer higher detector resolution for distant-object cameras where GPU budget allows.
3. Optional tiled inference for hard cameras.
4. Use temporal persistence to prevent single-frame misses.
5. Evaluate person recall by apparent object size.

Evaluation buckets:

```text
< 32 px height
32–64 px
64–128 px
> 128 px
```

The team MUST report performance by bucket if possible.

---

# 12. Tracking Requirements

## 12.1 Primary

Use:

```text
BoT-SORT
```

or:

```text
ByteTrack
```

## 12.2 Track record

```python
TrackState(
    track_id,
    class_id,
    bbox,
    center_xy,
    velocity_xy,
    age_frames,
    last_seen,
    confidence_history,
    trajectory,
)
```

## 12.3 Trajectory representation

Store the object center:

```text
(x_t, y_t)
```

and optionally a smoothed center:

```text
(x'_t, y'_t)
```

Use a configurable smoothing window.

## 12.4 Track persistence

A track becomes eligible for higher-level reasoning only after configurable persistence, e.g.:

```text
MIN_TRACK_AGE = 5 frames
```

This is a prototype default, not a universal value.

---

# 13. Camera-Specific Spatial Intelligence

## 13.1 Why camera-specific configuration is mandatory

Each camera has a different perspective.

Therefore "towards the border" cannot be globally hard-coded.

Every camera SHALL have a configuration:

```json
{
  "camera_id": "cam_07",
  "terrain": "forest",
  "zones": [
    {
      "id": "safe",
      "type": "safe",
      "polygon": [[...]]
    },
    {
      "id": "restricted",
      "type": "restricted",
      "polygon": [[...]]
    }
  ],
  "virtual_fences": [
    {
      "id": "vf_01",
      "type": "boundary",
      "polyline": [[...]]
    }
  ],
  "expected_direction": {
    "dx": 0.9,
    "dy": -0.2
  }
}
```

## 13.2 Zone types

At minimum:

```text
SAFE
RESTRICTED
PATROL
ROAD
CAMERA_EXCLUSION
CUSTOM
```

## 13.3 Virtual fence

Support:

- line crossing
- polygon entry
- polygon exit

A line crossing event MUST use previous and current track positions rather than checking whether a single bounding box overlaps a line.

---

# 14. Direction-of-Motion Engine

For a tracked object:

```text
v_t = position_t - position_(t-k)
```

Normalize:

```text
d_t = v_t / ||v_t||
```

Compare with camera-specific expected direction.

Compute:

```text
direction_alignment = dot(d_t, expected_direction)
```

Interpretation:

```text
~ +1  strongly aligned
~  0  perpendicular
~ -1  opposite
```

Use a deadband around zero to prevent noisy classification.

---

# 15. Temporal Behavior Engine

## 15.1 Required first-wave events

### A. Loitering

Condition:

```text
track remains inside ROI
AND
displacement remains small
AND
dwell_time > configured threshold
```

### B. Persistent approach

Condition:

```text
track survives minimum duration
AND
successive positions trend toward protected zone
AND
direction alignment exceeds threshold
```

### C. Virtual-fence crossing

Condition:

```text
trajectory segment intersects configured line
```

### D. Repeated approach

Condition:

```text
same track enters/approaches a monitored boundary
multiple times within a window
```

### E. Abnormal stationary behavior

Optional:
- person appears in restricted area
- remains unusually still
- no authorized-zone relationship

Do not label this a "threat"; label it a behavior event.

---

# 16. Suspicious Activity Strategy

## 16.1 Do NOT start with a giant end-to-end action model

For a 7-day prototype, use explainable temporal rules first.

Examples:

```text
SUSPICIOUS_APPROACH
LOITERING
RESTRICTED_ENTRY
REPEATED_APPROACH
UNUSUAL_GROUPING
ANIMAL_ASSOCIATION
```

Each event should be explainable.

## 16.2 Optional learned behavior layer

Candidate open-source framework:

### MMAction2

Repository:
https://github.com/open-mmlab/mmaction2

License: Apache-2.0.

It supports video understanding, activity recognition, and research models.

Use only after the rule engine works.

---

# 17. Uniformed / Civilian Reasoning

The supplied Digital Border paper shows why this is difficult: the classes are visually similar because both are human, and the authors report lower accuracy/precision in this distinction.

## 17.1 Required architecture

Do not force the main detector to decide all human subtypes.

Use:

```text
person detection
      |
      v
person crop
      |
      v
uniform/civilian classifier
      |
      +--> uniform
      +--> civilian
      +--> uncertain
```

## 17.2 Critical requirement: `uncertain`

Never implement:

```text
uniform confidence <= 60% => civilian
```

as a universal production rule.

Instead:

```text
uniform
civilian
uncertain
```

and combine the classifier output with:

- zone
- tracking
- temporal evidence
- camera context
- operator configuration

The 60% threshold used by the referenced paper is a study-specific engineering choice, not a scientifically universal threshold.

## 17.3 Dataset

Create a small custom dataset because the referenced research explicitly notes the sensitivity/unavailability of public uniformed-person data.

Minimum prototype labels:

```text
uniformed_person
civilian_person
uncertain
```

Conditions MUST cover:

- day
- dusk
- night
- different backgrounds
- standing
- walking
- partial occlusion
- distance
- different viewpoints
- multiple clothing variations

---

# 18. Face Detection / Recognition

## 18.1 Architecture

```text
person track
   |
   v
face detector
   |
   +--> no usable face => skip
   |
   v
face alignment
   |
   v
embedding
   |
   v
watchlist similarity search
```

## 18.2 Open-source candidate

InsightFace:
https://github.com/deepinsight/insightface

The repository states that code is MIT-licensed, but its model/training-data terms can differ and some recognition model packages require additional licensing contact.

Therefore:

- code: usable as a component subject to its license;
- model weights: MUST be audited individually before deployment;
- face recognition is OPTIONAL for the SIH prototype;
- face matching must never be treated as infallible identity proof.

## 18.3 Privacy

Default prototype behavior:

```text
face detection = optional
face recognition = OFF by default
```

Enable only with explicit operator configuration.

---

# 19. ANPR / License Plate Recognition

## 19.1 Architecture

```text
vehicle detection
      |
      v
vehicle track
      |
      v
plate detection
      |
      v
plate crop
      |
      v
OCR
      |
      v
temporal aggregation
      |
      v
plate candidate
```

## 19.2 OCR engine

### PaddleOCR

Repository:
https://github.com/PaddlePaddle/PaddleOCR

License: Apache-2.0.

It supports broad OCR functionality and many languages.

## 19.3 Important engineering rule

Never trust one frame of OCR.

Example:

```text
Frame 1: MH12AB1234
Frame 2: MH12A81234
Frame 3: MH12AB1234
Frame 4: MH12AB1234
```

Temporal aggregation should output:

```text
MH12AB1234
confidence = high
evidence_frames = 3/4
```

## 19.4 OpenALPR

OpenALPR is an established open-source ANPR codebase, but its official documentation indicates AGPL/commercial licensing options.

Reference:
https://github.com/openalpr

Do not select it as the default production baseline without licensing review.

---

# 20. Event / Evidence Fusion Engine

This is the core "intelligence" layer.

## 20.1 Event evidence

Each event can accumulate:

```text
object_confidence
track_persistence
direction_alignment
zone_violation
dwell_time
behavior_score
environment_quality
uniform_confidence
face_match_confidence
plate_confidence
```

## 20.2 Example score

For prototype:

```text
score =
    0.20 * detection_evidence +
    0.15 * persistence_evidence +
    0.20 * zone_evidence +
    0.15 * direction_evidence +
    0.15 * behavior_evidence +
    0.10 * environmental_context +
    0.05 * optional_identity_evidence
```

All weights MUST be configurable.

This is a **prototype engineering score**, not a validated military threat model.

## 20.3 Important asymmetry

False negatives and false positives are not equally costly.

Therefore threshold selection MUST consider the operational objective.

Do not optimize solely for generic accuracy.

---

# 21. Risk Levels

Recommended prototype taxonomy:

```text
INFO
LOW
MEDIUM
HIGH
CRITICAL
```

### INFO

Examples:
- animal movement
- ordinary vehicle
- non-actionable observation

### LOW

Examples:
- uncertain object
- weak/short-lived track

### MEDIUM

Examples:
- persistent movement in monitored region
- prolonged loitering

### HIGH

Examples:
- person enters restricted zone
- sustained approach plus boundary proximity

### CRITICAL

Reserve only for combinations of multiple strong signals. Do not use this merely because a detector says "person".

---

# 22. Evidence Clip System

Every alertable event MUST save:

```text
pre-event window
+
event window
+
post-event window
```

Prototype example:

```text
PRE  = 5 sec
POST = 5 sec
```

Make configurable.

Storage structure:

```text
evidence/
  2026/
    08/
      28/
        event_<uuid>/
          before.mp4
          event.mp4
          after.mp4
          snapshot.jpg
          metadata.json
```

The exact storage backend may be local filesystem for the hackathon.

---

# 23. Event Data Model

Minimum event schema:

```json
{
  "event_id": "uuid",
  "camera_id": "cam_07",
  "timestamp_utc": "2026-08-28T08:10:11Z",
  "event_type": "RESTRICTED_ENTRY",
  "severity": "HIGH",
  "track_id": 31,
  "object_class": "person",
  "detector_confidence": 0.88,
  "track_confidence": 0.93,
  "environment": {
    "lighting": "night",
    "visibility": "poor",
    "weather": "rain",
    "terrain": "forest"
  },
  "zone_id": "restricted_01",
  "direction_alignment": 0.82,
  "dwell_seconds": 8.4,
  "reason_codes": [
    "PERSISTENT_TRACK",
    "TOWARD_RESTRICTED_ZONE",
    "FENCE_CROSSED"
  ],
  "evidence_paths": [
    "snapshot.jpg",
    "event.mp4"
  ],
  "status": "UNACKNOWLEDGED"
}
```

---

# 24. Event Reason Codes

Every non-INFO alert MUST explain why it exists.

Examples:

```text
PERSON_DETECTED
VEHICLE_DETECTED
ANIMAL_DETECTED
UNKNOWN_OBJECT

PERSISTENT_TRACK
RESTRICTED_ENTRY
FENCE_CROSSED
TOWARD_RESTRICTED_ZONE
LOITERING
REPEATED_APPROACH

LOW_LIGHT
POOR_VISIBILITY
RAIN
SNOW
FOG

UNIFORM_LIKELY
CIVILIAN_LIKELY
IDENTITY_UNCERTAIN

PLATE_READ
FACE_MATCH
```

The UI must expose these reasons.

---

# 25. Database Requirements

## Prototype

Use SQLite for simplicity.

SQLite is public-domain software and is suitable for a self-contained prototype.

Reference:
https://www.sqlite.org/copyright.html

Tables:

```text
cameras
camera_zones
camera_fences
events
tracks
detections
environment_snapshots
plates
face_matches
system_alerts
audit_log
```

## Scaled deployment

Move to:

```text
PostgreSQL
+
object storage
+
optional vector database
```

### Optional vector DB

Qdrant:
https://github.com/qdrant/qdrant

License: Apache-2.0.

Potential uses:

- face embeddings where legally/operationally approved
- person/vehicle appearance embeddings
- semantic event retrieval
- similar-event search

Do not introduce a vector database just to look "AI-heavy". Use it only when it solves a demonstrated requirement.

---

# 26. Event Bus

## Prototype

Direct in-process asynchronous events are sufficient.

## Scaled architecture

Use NATS.

Repository:
https://github.com/nats-io/nats-server

License: Apache-2.0.

Example subjects:

```text
camera.frame
camera.health
detection.created
track.updated
environment.updated
event.created
alert.created
alert.acknowledged
```

NATS is suitable for local, cloud, and edge deployments.

---

# 27. Inference Runtime

Use an abstraction:

```python
class InferenceBackend:
    def load(self, model_path): ...
    def infer(self, batch): ...
    def warmup(self): ...
```

Support:

```text
PyTorch
ONNX Runtime
OpenVINO
TensorRT (optional, NVIDIA)
```

## Preferred cross-platform runtime

ONNX Runtime:
https://github.com/microsoft/onnxruntime

License: MIT.

## CPU-oriented optimization

OpenVINO:
https://github.com/openvinotoolkit/openvino

License: Apache-2.0.

Use OpenVINO when Intel CPU/GPU/NPU hardware is available.

## NVIDIA-oriented optimization

NVIDIA DeepStream:
https://developer.nvidia.com/deepstream-sdk

DeepStream is an open real-time streaming analytics toolkit built around GStreamer and supports multi-stream/multi-sensor video analytics.

Use it when the prototype has multiple NVIDIA-accelerated streams and the team can afford the integration complexity.

For a 1-4 camera SIH demo, plain Python + GStreamer/FFmpeg + ONNX Runtime is usually easier to debug.

---

# 28. Compute Profiles

## Profile A — CPU-only demo

Target:
- 1–2 streams
- lower FPS
- lower resolution

Use:
- small detector
- ONNX Runtime / OpenVINO
- simple tracker

## Profile B — Single NVIDIA GPU

Recommended hackathon profile.

Use:
- RF-DETR-N/S or another selected detector
- BoT-SORT/ByteTrack
- optional low-light enhancement
- 2–8 streams depending on resolution/model

Exact throughput MUST be benchmarked on the team's hardware.

## Profile C — Central inference server

Architecture:

```text
many CCTV streams
     |
     v
ingestion gateway
     |
     v
decode / batching
     |
     v
GPU workers
     |
     v
event bus
     |
     +--> dashboard
     +--> storage
     +--> notifications
```

## Profile D — Remote/edge deployment

Run:

```text
CCTV
 |
edge workstation
 |
local inference
 |
local event storage
 |
store-and-forward synchronization
```

No hard dependency on permanent cloud connectivity.

---

# 29. Offline-First Requirement

A remote location may have unreliable connectivity.

Therefore:

MUST:
- run inference locally
- retain recent event records locally
- cache evidence
- queue outbound events

SHOULD:
- synchronize event metadata when connectivity returns
- synchronize only high-value evidence rather than all raw video

The system should continue basic detection and event generation even if the central server is unavailable.

---

# 30. API Requirements

## 30.1 Cameras

```http
GET    /api/v1/cameras
POST   /api/v1/cameras
GET    /api/v1/cameras/{camera_id}
PATCH  /api/v1/cameras/{camera_id}
POST   /api/v1/cameras/{camera_id}/connect
POST   /api/v1/cameras/{camera_id}/disconnect
GET    /api/v1/cameras/{camera_id}/health
```

## 30.2 Events

```http
GET    /api/v1/events
GET    /api/v1/events/{event_id}
POST   /api/v1/events/{event_id}/ack
POST   /api/v1/events/{event_id}/dismiss
```

Filtering:

```text
camera_id
severity
event_type
start_time
end_time
object_class
terrain
weather
lighting
status
```

## 30.3 Zones / fences

```http
GET    /api/v1/cameras/{id}/zones
POST   /api/v1/cameras/{id}/zones
PATCH  /api/v1/zones/{zone_id}
DELETE /api/v1/zones/{zone_id}

GET    /api/v1/cameras/{id}/fences
POST   /api/v1/cameras/{id}/fences
```

## 30.4 WebSocket

```text
/ws/events
/ws/cameras/{camera_id}
```

WebSocket event:

```json
{
  "type": "alert.created",
  "event_id": "uuid",
  "severity": "HIGH",
  "camera_id": "cam_07"
}
```

---

# 31. Dashboard Requirements

## Screen 1 — Operations Overview

Show:

- live camera grid
- active alerts
- camera health
- system FPS
- latency
- current environment status

## Screen 2 — Incident Feed

Columns:

```text
time
camera
event
severity
object
environment
status
```

## Screen 3 — Incident Detail

Show:

```text
evidence clip
snapshot
track trajectory
zone/fence
environment state
detector confidence
event reasons
acknowledge
dismiss
```

## Screen 4 — Camera Configuration

Allow:

- RTSP URL
- camera name
- terrain profile
- zones
- fences
- expected direction
- thresholds

## Screen 5 — Analytics

Charts:

- events by camera
- events by hour
- events by environment
- false-alarm count
- detection FPS
- processing latency
- camera uptime
- night/day detection comparison

---

# 32. Frontend Stack

Recommended:

```text
React
TypeScript
Vite
Tailwind CSS
WebSocket
Map library only if needed
```

Backend:

```text
Python
FastAPI
Pydantic
asyncio
```

Do not build a complex microservice ecosystem for a 7-day prototype.

---

# 33. Backend Service Boundaries

Keep these logical modules even if they initially run in one process:

```text
ingestion/
environment/
detection/
tracking/
spatial/
behavior/
identity/
anpr/
fusion/
events/
storage/
api/
notifications/
```

This gives you clean upgrade paths without the operational complexity of 12 deployed microservices.

---

# 34. Suggested Repository Structure

```text
ibvap/
├── apps/
│   ├── api/
│   ├── worker/
│   └── web/
│
├── services/
│   ├── ingestion/
│   ├── environment/
│   ├── perception/
│   ├── tracking/
│   ├── spatial/
│   ├── behavior/
│   ├── identity/
│   ├── anpr/
│   ├── fusion/
│   └── events/
│
├── models/
│   ├── detector/
│   ├── uniform/
│   ├── face/
│   ├── plate/
│   └── enhancement/
│
├── datasets/
│   └── README.md
│
├── configs/
│   ├── cameras/
│   ├── zones/
│   ├── thresholds/
│   └── models/
│
├── storage/
│   ├── evidence/
│   └── database/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── replay/
│   └── evaluation/
│
├── scripts/
│   ├── download_models.py
│   ├── prepare_dataset.py
│   ├── run_replay.py
│   └── benchmark.py
│
├── docker/
├── docs/
├── .env.example
├── docker-compose.yml
└── README.md
```

---

# 35. Configuration Requirements

All important thresholds MUST live in configuration, not hard-coded source code.

Example:

```yaml
detection:
  confidence_threshold: 0.35
  nms_iou_threshold: 0.50
  inference_width: 640

tracking:
  min_track_age: 5
  max_lost_frames: 30

behavior:
  loitering_seconds: 20
  persistent_approach_seconds: 5
  repeated_approach_window_seconds: 120

environment:
  low_light_threshold: 0.20
  blur_threshold: 80
  poor_visibility_threshold: 0.40

risk:
  low_max: 30
  medium_max: 60
  high_max: 80
```

The values above are starting values only.

---

# 36. Dataset Requirements

## 36.1 Generic detector

Start from pretrained models.

Candidate datasets:

- COCO — generic objects
- CrowdHuman — difficult/occluded people
- VisDrone — small/distant objects and tracking
- MOT17/MOT20 — tracking
- VIRAT — surveillance activity/event context

Do not train the detector from scratch unless the team has a specific research reason.

## 36.2 IBVAP custom dataset

Required custom categories:

```text
uniformed_person
civilian_person
animal_context
night_person
low_visibility_person
```

Later:

```text
forest
mountain
snow
open
```

as scene labels if automated terrain recognition is pursued.

## 36.3 Dataset split

Use:

```text
70% train
15% validation
15% test
```

BUT do not randomly split adjacent frames from the same video across train/test.

The test set must be scene/video separated to avoid leakage.

## 36.4 Environment matrix

Every evaluation sample should ideally have tags:

```text
terrain
lighting
weather
visibility
distance
pose
occlusion
object_class
```

---

# 37. Evaluation Requirements

Do not use one headline "accuracy" number.

## 37.1 Detection

Report:

- precision
- recall
- mAP50
- mAP50:95
- per-class recall

## 37.2 Tracking

Report:

- IDF1
- HOTA
- MOTA where appropriate
- ID switches

## 37.3 Event detection

Report:

- event precision
- event recall
- false alarms / camera-hour
- missed events / camera-hour
- event latency

## 37.4 ANPR

Report:

- plate detection recall
- character accuracy
- exact plate-string accuracy
- temporal voting improvement

## 37.5 Face

Report:

- face detection recall at distance/quality buckets
- verification TAR/FAR if implemented
- "unknown/uncertain" rate

Do not report identity accuracy on an artificially easy demo set as if it represented operational performance.

## 37.6 System

Report:

```text
end-to-end latency
decoder FPS
inference FPS
tracking FPS
GPU utilization
CPU utilization
RAM
VRAM
stream drops
reconnect recovery time
events/hour
false alarms/hour
```

---

# 38. Environment Robustness Benchmark

This is a central IBVAP feature.

Build a benchmark matrix:

| Condition | Test |
|---|---|
| Day | detection + tracking |
| Night | detection + tracking |
| Low light | enhancement impact |
| Rain | detection + tracking |
| Fog | detection + tracking |
| Snow | detection + tracking |
| Forest | small/distant people |
| Mountain | perspective/scale changes |
| Open | baseline |
| Occluded | tracking continuity |

Report:

```text
Person recall by condition
False alarms by condition
Track IDF1 by condition
Alert latency by condition
```

---

# 39. Required Ablation Study

To prove the adaptive architecture matters, run:

### A — Baseline

```text
raw video
→ detector
→ tracker
→ rule engine
```

### B — Add environment estimation

```text
raw video
→ environment
→ detector
→ tracker
→ rules
```

### C — Add adaptive enhancement

```text
environment
→ selective enhancement
→ detector
→ tracker
→ rules
```

### D — Add evidence fusion

```text
environment
→ adaptive perception
→ tracking
→ behavior
→ evidence fusion
```

Compare false alarms and missed events.

The strongest prototype story is:

> "The additional intelligence reduced false alarms and improved difficult-condition robustness."

Not:

> "We used 12 AI models."

---

# 40. Test Video Replay Harness

The team MUST have a deterministic replay tool.

Input:

```text
video file
+
camera config
+
expected event annotations
```

Output:

```textdetection metrics
tracking metrics
event metrics
latency
resource usage
evidence clips
```

This allows rapid regression testing without a real CCTV camera.

---

# 41. Synthetic / Safe Demo Data

For the SIH demo, do NOT use operational border footage.

Create controlled demonstrations using lawful/publicly licensed or self-recorded scenes.

Demo scenarios:

```text
Scenario 1:
day + person + restricted-zone crossing

Scenario 2:
night + person + low-light enhancement

Scenario 3:
animal movement + no high-priority event

Scenario 4:
person walking parallel to fence + no intrusion alert

Scenario 5:
persistent approach + fence crossing + high alert

Scenario 6:
vehicle + readable plate + ANPR

Scenario 7:
same subject through different environmental conditions
```

---

# 42. Novelty / Differentiation Requirements

IBVAP's novelty should NOT be claimed as:

- YOLO
- OCR
- tracking
- dashboard
- virtual fence alone

Those are standard components.

The differentiation claim should center on:

## A. Environment-aware confidence

The system estimates scene quality and explicitly accounts for degraded evidence.

## B. Adaptive perception

Processing is selected based on current camera conditions.

## C. Temporal evidence aggregation

Single-frame uncertainty becomes stronger/weaker based on persistent tracks.

## D. Contextual event reasoning

The system reasons about zone, direction, dwell time, and movement patterns.

## E. Multi-evidence risk scoring

An alert requires combinations of evidence instead of one detector output.

## F. Software-defined deployment

Existing CCTV can be used without replacing each camera with a smart camera.

---

# 43. Explicit Non-Goals for Novelty

Do not claim:

```text
"first AI border surveillance system"
```

Do not claim:

```text
"90% accuracy in all weather"
```

Do not claim:

```text
"AI knows whether a person is a terrorist"
```

Do not claim:

```text
"facial recognition identifies anyone from arbitrary CCTV"
```

Do not claim:

```text
"our threat score is a military-grade risk model"
```

These would be scientifically and technically irresponsible.

---

# 44. Security Requirements

## Authentication

Dashboard MUST require authentication.

Prototype:
- JWT or secure session

## Authorization

Roles:

```text
ADMIN
OPERATOR
VIEWER
AUDITOR
```

## Secrets

RTSP credentials MUST NOT be committed to source control.

Use:

```text
.env
secret store later
```

## Network

Prefer:

```text
camera network
  |
  | isolated
  v
inference server
  |
  | controlled API
  v
operator network
```

No internet requirement for the inference path.

## Audit

Log:

- login
- camera configuration changes
- zone changes
- model changes
- alert acknowledgement
- alert dismissal
- watchlist changes
- evidence access

---

# 45. Privacy / Biometrics Requirements

Face recognition is the highest-risk module.

Therefore:

1. Make FRS a feature flag.
2. Default to face detection only.
3. Keep watchlist storage separate.
4. Encrypt or strongly restrict biometric data.
5. Log every watchlist query.
6. Define retention policy.
7. Require human review before identity-sensitive action.
8. Do not use face-match output as sole evidence of a security decision.

The system should prefer non-biometric event evidence whenever available.

---

# 46. Observability

Each camera MUST expose:

```text
stream_status
decoder_fps
inference_fps
tracking_fps
latency_ms
dropped_frames
gpu_utilization
cpu_utilization
queue_depth
last_event
```

Each model MUST expose:

```text
model_name
model_version
backend
device
load_time
average_latency
```

Every generated event MUST contain:

```text
model_versions
config_version
```

This is critical for reproducibility.

---

# 47. Model Registry

Every deployed model must be described by:

```yaml
name: ibvap-detector
version: 0.1.0
task: object_detection
framework: onnx
classes:
  - person
  - car
  - truck
  - motorcycle
  - animal
checksum: "..."
license: "..."
source_url: "..."
```

Never ship an undocumented model file.

---

# 48. Open-Source License Matrix

| Component | Recommended role | License / note |
|---|---|---|
| RF-DETR | Primary detector | Apache-2.0 for core/open designated models |
| Ultralytics YOLO | Alternative detector | AGPL-3.0; Enterprise option exists |
| BoT-SORT | Tracking | MIT |
| ByteTrack | Tracking | Verify repository license before redistribution in final packaging |
| Norfair | Lightweight tracking | BSD-3-Clause |
| supervision | Zones/analytics helpers | MIT |
| GStreamer | RTSP pipeline | LGPL components; audit final linked components |
| FFmpeg | Media processing | LGPL/GPL depending on build/configuration; audit build |
| ONNX Runtime | Inference runtime | MIT |
| OpenVINO | CPU/Intel acceleration | Apache-2.0 |
| PaddleOCR | OCR / ANPR support | Apache-2.0 |
| MMAction2 | Optional action recognition | Apache-2.0 |
| Retinexformer | Low-light enhancement | MIT |
| InsightFace | Optional face analysis | Code MIT; model/data terms require separate review |
| SQLite | Prototype DB | Public domain |
| Qdrant | Optional vector DB | Apache-2.0 |
| NATS | Optional event bus | Apache-2.0 |
| MinIO | Object storage alternative | AGPLv3; license review required |

**Critical:** licensing MUST be checked at the exact commit/release/model-weight level before any external or proprietary deployment. This document is an engineering guide, not legal advice.

---

# 49. Why RF-DETR is the Default Detector Choice Here

The current RF-DETR project is specifically designed for real-time detection and fine-tuning and publishes Apache-2.0 licensing for the core/open designated models.

This makes it attractive for a project whose long-term objective may be government/defense deployment where permissive licensing simplifies architecture and redistribution considerations.

Ultralytics remains a technically strong alternative, but its current official license guidance is materially more restrictive for private/proprietary deployment.

Decision:

```text
Default:
RF-DETR

Fallback:
YOLO only if licensing is acceptable

Evaluation:
benchmark both on IBVAP-specific data
```

---

# 50. 7-Day Hackathon Build Path

## Day 1 — Infrastructure

Deliver:

```text
repo
Docker
FastAPI
React
SQLite
RTSP/MP4 ingestion
one camera live feed
```

Acceptance:
- camera connects
- frame displayed
- reconnect works

## Day 2 — Baseline perception

Deliver:

```text
detector
person/vehicle/animal classes
basic visualization
```

Acceptance:
- detector works on replay footage

## Day 3 — Tracking + spatial

Deliver:

```text
ByteTrack or BoT-SORT
track IDs
trajectory
zones
virtual fence
```

Acceptance:
- stable track IDs
- fence crossing event

## Day 4 — Environment engine

Deliver:

```text
day/night
brightness
blur
visibility score
low-light enhancement
```

Acceptance:
- dashboard shows environment state
- nighttime pipeline differs from normal pipeline

## Day 5 — Behavior + fusion

Deliver:

```text
loitering
persistent approach
direction
risk score
reason codes
```

Acceptance:
- no alert from simple lateral movement
- high alert from multi-signal event

## Day 6 — Evidence + dashboard

Deliver:

```text
event clips
event database
incident feed
event details
filters
camera health
```

Acceptance:
- alert can be opened and explained

## Day 7 — Benchmark + polish

Deliver:

```text
3-5 curated demo scenarios
benchmark numbers
latency numbers
false alarms
before/after adaptation comparison
pitch material
```

---

# 51. Post-Hackathon 2–4 Week Hardening

## Week 1

- improve custom uniform/civilian data
- add difficult-condition examples
- improve small-object handling
- calibrate thresholds

## Week 2

- ANPR module
- optional face module
- better temporal behavior model
- replay/evaluation automation

## Week 3

- multi-camera scaling
- store-and-forward
- stronger event API
- ONNX/OpenVINO optimization

## Week 4

- security hardening
- audit logging
- model registry
- license inventory
- stress testing
- deployment documentation

---

# 52. Optional Advanced Research Extensions

Only add these after the core system is stable.

## Extension A — Learned environment classifier

```text
scene embedding
    |
    v
terrain/weather classifier
```

## Extension B — Learned anomaly detection

Candidate direction:

```text
normal-track representation
    |
    v
temporal anomaly score
```

Possible frameworks:
- Anomalib
- MMAction2
- PyTorch-based custom VAE/LSTM

Use only with a clear dataset and validation plan.

## Extension C — Multi-camera track association

```text
camera A Track 31
       |
       v
appearance embedding
       |
       v
camera B Track 12
```

Do not deploy this as an identity claim without strong validation.

## Extension D — GIS/map layer

Associate camera and zone events with a geographic map.

This should be visualization/context, not a source of fabricated positional precision.

---

# 53. Acceptance Criteria for the SIH Prototype

The prototype is considered complete only if all are true:

### AC-01
A standard IP/RTSP or replayed CCTV stream can be ingested.

### AC-02
A person, vehicle, and animal can be detected.

### AC-03
Objects receive persistent track IDs.

### AC-04
An operator can define a virtual fence.

### AC-05
A fence crossing produces an event.

### AC-06
Parallel movement does NOT automatically generate a high-priority intrusion alert.

### AC-07
Night/low-light footage changes the perception pipeline.

### AC-08
The system exposes environmental quality.

### AC-09
Loitering or persistent approach can be demonstrated.

### AC-10
Alerts include explicit reason codes.

### AC-11
Every high-priority event has evidence frames/video.

### AC-12
The event can be acknowledged/dismissed.

### AC-13
The event is stored and searchable.

### AC-14
The system survives a temporary camera disconnect and reconnects.

### AC-15
The system can run without cloud dependency during the demo.

### AC-16
The prototype reports latency and throughput.

### AC-17
The prototype demonstrates at least three environmental scenarios.

### AC-18
No claim of universal weather robustness is made without measured evidence.

---

# 54. Recommended Demo Sequence

Use this exact order.

## Demo 1 — Conventional detection baseline

Show:

```text
person detected
```

Then say:

> Detection alone is not enough.

## Demo 2 — Tracking

Show:

```text
Track #17
trajectory
```

## Demo 3 — Virtual fence

Person crosses:

```text
restricted zone
```

Alert appears.

## Demo 4 — False-alarm suppression

Animal crosses area.

System says:

```text
animal event
no high-priority intrusion
```

## Demo 5 — Direction reasoning

Person moves parallel to fence.

System:

```text
movement observed
no intrusion event
```

## Demo 6 — Night adaptation

Same type of event in low light.

Show:

```text
environment = NIGHT
quality = LOW
adaptive enhancement = ON
```

## Demo 7 — Evidence fusion

Show:

```text
persistent track
+
toward protected zone
+
fence crossing
+
poor visibility
=
HIGH
```

This is your key "intelligence" moment.

---

# 55. What the Judges Should Remember

The project is NOT:

> "We made another YOLO surveillance dashboard."

The intended message is:

> **"IBVAP adds an adaptive intelligence layer on top of existing CCTV. It estimates environmental conditions, detects and tracks objects, understands spatial and temporal context, and combines multiple uncertain signals before deciding whether an event deserves operator attention."**

This is a more defensible technical proposition than promising perfect object recognition.

---

# 56. Final Recommended Technology Stack

```text
VIDEO
  GStreamer + FFmpeg + OpenCV

DETECTION
  RF-DETR-N/S

TRACKING
  ByteTrack
  or BoT-SORT

ENVIRONMENT
  OpenCV statistics
  Retinexformer optional

UNIFORM
  custom lightweight classifier

FACE
  InsightFace optional

ANPR
  custom plate detector
  + PaddleOCR

BEHAVIOR
  deterministic temporal/spatial rules
  + MMAction2 optional

FUSION
  custom Python risk/evidence engine

BACKEND
  FastAPI
  Pydantic
  asyncio

DATABASE
  SQLite prototype

EVENT BUS
  in-process first
  NATS later

STORAGE
  local filesystem first
  object storage later

INFERENCE
  ONNX Runtime
  OpenVINO optional
  TensorRT/DeepStream optional for NVIDIA scale

FRONTEND
  React + TypeScript + Vite

DEPLOYMENT
  Docker Compose

TESTING
  pytest
  replay harness
  benchmark scripts
```

---

# 57. Antigravity Implementation Rules

Antigravity MUST follow these constraints:

1. Build the smallest working pipeline first.
2. Keep every AI module replaceable behind an interface.
3. Do not hard-code camera IDs.
4. Do not hard-code zone geometry.
5. Do not hard-code thresholds in business logic.
6. Do not make detector confidence equal threat probability.
7. Do not create alerts from single-frame detections.
8. Do not let a broken optional module stop the base surveillance pipeline.
9. Do not require internet connectivity for local inference.
10. Do not store credentials in source code.
11. Log model version/config version in every event.
12. Write unit tests for zone crossing and direction logic.
13. Write replay tests for every core alert scenario.
14. Keep the event explanation machine-readable.
15. Make face recognition and other biometric features opt-in.
16. Keep raw video retention configurable.
17. Preserve timestamps in UTC internally.
18. Use structured JSON logs.
19. Fail closed for security-sensitive control operations, but fail soft for optional analytics modules.
20. Never invent unsupported confidence or accuracy numbers.

---

# 58. First Implementation Sprint for Antigravity

Implement in exactly this order:

```text
STEP 1
FastAPI + React + SQLite

STEP 2
VideoSource abstraction

STEP 3
RTSP + MP4 source

STEP 4
Detector abstraction

STEP 5
RF-DETR baseline

STEP 6
Tracker abstraction

STEP 7
ByteTrack/BoT-SORT

STEP 8
Camera configuration

STEP 9
Zone/fence engine

STEP 10
Trajectory + direction engine

STEP 11
EnvironmentState

STEP 12
Low-light enhancement adapter

STEP 13
Behavior rules

STEP 14
Evidence fusion

STEP 15
Event persistence

STEP 16
Evidence clip writer

STEP 17
WebSocket event stream

STEP 18
Dashboard

STEP 19
Replay benchmark

STEP 20
3-5 demo scenarios
```

Do not proceed to ANPR or face recognition until Steps 1–20 are stable.

---

# 59. Minimum Viable Intelligent Border Event

The MVP "golden path" is:

```text
RTSP CCTV
   |
   v
Environment = Night / Poor
   |
   v
Adaptive preprocessing
   |
   v
Person detected
   |
   v
Track #17 created
   |
   v
Track persists
   |
   v
Direction = toward restricted zone
   |
   v
Virtual fence crossing
   |
   v
Evidence fusion
   |
   v
HIGH event
   |
   +--> snapshot
   +--> 10-second clip
   +--> trajectory
   +--> reason codes
   +--> environment state
   |
   v
Operator dashboard
```

If this single path works reliably, **you have the core IBVAP prototype**.

Everything else is an extension.

---

# 60. Source Registry

## Supplied research

1. **Digital Border Surveillance System: Towards Illegal Migration and Trafficking Free Borders**  
   ICCIT 2023. DOI: 10.1109/ICCIT60459.2023.10441013  
   Local source supplied by project team.

2. **Cross Border Intruder Detection in Hilly Terrain in Dark Environment**  
   ScienceDirect / Optik.  
   https://www.sciencedirect.com/science/article/abs/pii/S0030402615010037

3. **IBVAP Research Report**  
   Local research report supplied by project team.

## Open-source / official project references

4. RF-DETR  
   https://github.com/roboflow/rf-detr

5. Ultralytics  
   https://docs.ultralytics.com/models/  
   https://www.ultralytics.com/license

6. BoT-SORT  
   https://github.com/NirAharon/BoT-SORT

7. ByteTrack  
   https://github.com/ifzhang/ByteTrack

8. Norfair  
   https://github.com/tryolabs/norfair

9. Roboflow supervision  
   https://github.com/roboflow/supervision

10. GStreamer RTSP source  
    https://gstreamer.freedesktop.org/documentation/rtsp/rtspsrc.html

11. ONVIF Profile S  
    https://www.onvif.org/profiles/profile-s/

12. OpenVINO  
    https://github.com/openvinotoolkit/openvino

13. ONNX Runtime  
    https://github.com/microsoft/onnxruntime

14. NVIDIA DeepStream  
    https://developer.nvidia.com/deepstream-sdk

15. PaddleOCR  
    https://github.com/PaddlePaddle/PaddleOCR

16. InsightFace  
    https://github.com/deepinsight/insightface

17. MMAction2  
    https://github.com/open-mmlab/mmaction2

18. Retinexformer  
    https://github.com/caiyuanhao1998/retinexformer

19. SQLite  
    https://www.sqlite.org/copyright.html

20. Qdrant  
    https://github.com/qdrant/qdrant

21. NATS Server  
    https://github.com/nats-io/nats-server

22. MinIO  
    https://github.com/minio/minio

23. OpenALPR  
    https://github.com/openalpr

---

# 61. Final Engineering Decision

For the SIH prototype:

```text
USE:
RF-DETR
+
ByteTrack
+
OpenCV/GStreamer
+
Environment analyzer
+
Optional Retinexformer
+
Rule-based behavior
+
Evidence fusion
+
FastAPI
+
React
+
SQLite
```

Add:

```text
PaddleOCR
```

only after the main pipeline works.

Add:

```text
Face recognition
```

only as a controlled optional module.

Add:

```text
MMAction2 / learned anomaly model
```

only after the deterministic behavior engine is benchmarked.

The project should be judged primarily on:

```text
robustness
+
false-alarm reduction
+
explainability
+
environment adaptation
+
real-time operation
+
existing-CCTV compatibility
```

—not on how many AI models are visible in the architecture diagram.
