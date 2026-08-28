# IBVAP — Intelligent Border Video Analytics Platform
## Architecture Specification for Antigravity

**Document purpose:** Authoritative architecture blueprint for implementation.  
**Audience:** Antigravity coding agent, student engineering team, reviewers/judges.  
**Prototype target:** SIH-level, software-only, existing-IP-CCTV analytics.  
**Architecture status:** Baseline architecture — implement this unless a change is explicitly approved in the project decision log.

---

# 0. HARD RULES FOR ANTIGRAVITY

These are implementation constraints, not suggestions.

1. **Do not invent services, models, APIs, datasets, sensor inputs, or dependencies that are not defined in this document.**
2. **Do not add physical sensors** to the core system. No PIR, ultrasonic, LiDAR, radar, thermal, seismic, Bluetooth or drone dependency exists in the prototype.
3. **Do not move AI inference into the browser.**
4. **Do not make FastAPI handle the continuous ML inference loop.** Continuous video processing belongs to the worker.
5. **Do not train models from scratch** for the first prototype.
6. **Do not treat detector confidence as threat probability.**
7. **Do not generate a high-priority alert from a single frame.**
8. **Do not make face recognition or ANPR mandatory for core detection.**
9. **Do not claim universal all-weather accuracy.**
10. **Do not hard-code camera geometry, zone polygons, fences, thresholds, or camera credentials.**
11. **Do not silently substitute libraries/models because a preferred dependency is unavailable.** Record the substitution in `DECISIONS.md`.
12. **Do not add Kubernetes, Kafka, cloud dependencies, microservices, or complex distributed infrastructure to the SIH prototype unless explicitly approved.**
13. **Do not create autonomous enforcement actions.** IBVAP is decision support.
14. **Every high-priority event must contain explainable reason codes and evidence metadata.**
15. **Every event must record model/configuration versions.**
16. **If visual evidence is insufficient, return `UNCERTAIN` or `INSUFFICIENT_VISUAL_EVIDENCE`; never fabricate certainty.**
17. **Keep the core pipeline functional if an optional module such as ANPR or FRS fails.**
18. **Use one machine for the initial deployment.**
19. **Optimize for a working end-to-end system before adding advanced AI.**
20. **Do not change this architecture merely because another architecture looks more sophisticated. The prototype goal is reliability and demonstrability.**

---

# 1. SYSTEM PURPOSE

IBVAP adds a software intelligence layer above existing IP CCTV.

It converts:

```text
Passive camera feed
        ↓
Detectable observations
        ↓
Persistent tracks
        ↓
Environmental context
        ↓
Spatial context
        ↓
Temporal/behavior context
        ↓
Evidence fusion
        ↓
Prioritized event
        ↓
Operator review
```

The central product idea is:

> **Detect events, not merely objects.**

---

# 2. SOURCE-OF-TRUTH RESEARCH BASIS

## 2.1 Digital Border Surveillance baseline

The supplied Digital Border Surveillance paper describes:

- object detection;
- uniformed persons;
- non-uniformed civilians;
- animals;
- movement detection;
- alarm generation;
- video storage;
- control-room interface.

It also describes a low-level image-processing layer and combines image analysis with YOLOv7 outputs for movement/behavior analysis. fileciteturn3file2L502-L520 fileciteturn3file2L553-L590

The paper's dataset contains 2,690 non-uniformed human images, 2,290 uniformed-person images, and 2,367 animal images; it reports that the human-class distinction is difficult because uniformed and non-uniformed people are both human, and it recommends preprocessing, dataset balancing, transfer learning and iterative updating. fileciteturn3file2L605-L646 fileciteturn3file2L685-L707

The research also identifies future opportunities in real-time tracking, behavior analysis and multimodal extension. fileciteturn3file2L749-L759

## 2.2 IBVAP research report

The team's research report identifies:

- object detection;
- anomaly detection;
- facial/biometric analysis;
- action/behavior recognition;
- edge/fog deployment;
- multi-signal fusion;
- existing-CCTV integration;
- false alarms;
- environmental robustness;
- privacy and accountability

as relevant areas. fileciteturn3file0L48-L71 fileciteturn3file0L81-L107

## 2.3 Indian-border context source

The supplied India-focused source describes difficult forested/mountainous areas, harsh weather, workforce/visibility constraints, and current surveillance modernization involving systems such as CIBMS and BOLD-QIT. It also identifies privacy, biometric, accountability and proportionality considerations. fileciteturn3file1L169-L221 fileciteturn3file1L223-L266

**Important:** these sources support the problem framing and architectural direction. They do **not** establish that IBVAP can guarantee a specific operational accuracy in real border deployment.

---

# 3. ARCHITECTURAL PRINCIPLE

## 3.1 Layered architecture

IBVAP is divided into these layers:

```text
LAYER 0  SOURCE
         Existing IP CCTV / replay video

LAYER 1  INGESTION
         RTSP/ONVIF + decoding + frame queue

LAYER 2  ENVIRONMENT
         lighting / visibility / blur / quality / terrain profile

LAYER 3  PERCEPTION
         person / vehicle / animal / unknown

LAYER 4  TRACKING
         track IDs / trajectory / persistence

LAYER 5  SPATIAL
         zones / virtual fences / direction

LAYER 6  TEMPORAL & BEHAVIOR
         loitering / persistent approach / repeated approach

LAYER 7  OPTIONAL SUPPORTING INTELLIGENCE
         uniform classifier / ANPR / face analysis

LAYER 8  EVIDENCE FUSION
         combine signals + uncertainty

LAYER 9  EVENT ENGINE
         event type + priority + reasons

LAYER 10 EVIDENCE & STORAGE
         clip + snapshot + metadata

LAYER 11 API
         REST + WebSocket

LAYER 12 UI
         operator dashboard
```

---

# 4. HIGH-LEVEL SYSTEM FLOW

```text
                         ┌────────────────────────┐
                         │ Existing IP CCTV      │
                         │ RTSP / ONVIF          │
                         └───────────┬────────────┘
                                     │
                                     ▼
                         ┌────────────────────────┐
                         │ Video Ingestion        │
                         │ GStreamer/FFmpeg       │
                         └───────────┬────────────┘
                                     │
                                     ▼
                         ┌────────────────────────┐
                         │ Bounded Frame Queue    │
                         └───────────┬────────────┘
                                     │
                                     ▼
                         ┌────────────────────────┐
                         │ Environment Analyzer   │
                         └───────────┬────────────┘
                                     │
                                     ▼
                         ┌────────────────────────┐
                         │ Adaptive Perception    │
                         └───────────┬────────────┘
                                     │
                  ┌──────────────────┼───────────────────┐
                  │                  │                   │
                  ▼                  ▼                   ▼
              Person             Vehicle              Animal
                  │                  │                   │
                  └──────────────────┼───────────────────┘
                                     │
                                     ▼
                         ┌────────────────────────┐
                         │ Multi-Object Tracking  │
                         └───────────┬────────────┘
                                     │
                                     ▼
                         ┌────────────────────────┐
                         │ Spatial Intelligence   │
                         │ zones/fences/direction │
                         └───────────┬────────────┘
                                     │
                                     ▼
                         ┌────────────────────────┐
                         │ Temporal / Behavior    │
                         └───────────┬────────────┘
                                     │
                                     ▼
                         ┌────────────────────────┐
                         │ Optional intelligence  │
                         │ FRS / ANPR / uniform   │
                         └───────────┬────────────┘
                                     │
                                     ▼
                         ┌────────────────────────┐
                         │ Evidence Fusion        │
                         └───────────┬────────────┘
                                     │
                                     ▼
                         ┌────────────────────────┐
                         │ Risk / Event Engine    │
                         └───────────┬────────────┘
                                     │
                         ┌───────────┴────────────┐
                         ▼                        ▼
                ┌────────────────┐      ┌────────────────┐
                │ Evidence Store │      │ Event Database │
                └───────┬────────┘      └───────┬────────┘
                        │                       │
                        └──────────┬────────────┘
                                   ▼
                         ┌────────────────────────┐
                         │ FastAPI                │
                         │ REST + WebSocket       │
                         └───────────┬────────────┘
                                     │
                                     ▼
                         ┌────────────────────────┐
                         │ React Dashboard        │
                         └────────────────────────┘
```

---

# 5. DEPLOYMENT TOPOLOGY — SIH PROTOTYPE

Do NOT build a distributed production cluster first.

Run the prototype on one workstation.

```text
                     ONE WORKSTATION
┌───────────────────────────────────────────────────────────────┐
│                                                               │
│  ┌──────────────┐          ┌─────────────────────────────┐   │
│  │ React        │◄────────►│ FastAPI                     │   │
│  │ Frontend     │ REST/WS  │ Backend                     │   │
│  └──────────────┘          └──────────────┬──────────────┘   │
│                                           │                  │
│                                  ┌────────▼────────┐         │
│                                  │ SQLite          │         │
│                                  └─────────────────┘         │
│                                           │                  │
│                         ┌─────────────────▼──────────────┐   │
│                         │ AI Worker                      │   │
│                         │                                │   │
│                         │ ingestion                      │   │
│                         │ environment                    │   │
│                         │ detector                       │   │
│                         │ tracker                        │   │
│                         │ spatial                        │   │
│                         │ behavior                       │   │
│                         │ fusion                         │   │
│                         └──────────────┬─────────────────┘   │
│                                        │                     │
│                                  ┌─────▼──────┐              │
│                                  │ GPU / CPU  │              │
│                                  └────────────┘              │
│                                                               │
│  models/     storage/evidence/     configs/                  │
└───────────────────────────────────────────────────────────────┘
                ▲
                │ RTSP
                │
        ┌───────┴────────┐
        │ Existing CCTV │
        └────────────────┘
```

For the first demo, an MP4 file may replace the CCTV source.

---

# 6. COMPONENT RESPONSIBILITIES

## 6.1 Frontend

Technology:

```text
React
TypeScript
Vite
```

Responsible for:

- camera display;
- alerts;
- event details;
- trajectory visualization;
- zone/fence configuration;
- environment status;
- historical event search;
- system status.

Frontend MUST NOT:

- run heavy ML models;
- store camera credentials;
- contain business logic for event decisions.

---

# 7. Backend

Technology:

```text
Python
FastAPI
Pydantic
asyncio
```

Responsible for:

- authentication;
- configuration;
- camera registry;
- event APIs;
- WebSocket connections;
- database access;
- serving evidence;
- permissions;
- audit logs.

Backend MUST NOT:

- process the continuous video inference loop.

---

# 8. AI WORKER

Technology:

```text
Python
OpenCV
GStreamer/FFmpeg
selected inference runtime
tracker
custom event engine
```

Responsible for:

- connecting to streams;
- decoding frames;
- environment analysis;
- AI inference;
- tracking;
- spatial/temporal logic;
- event generation;
- evidence capture.

The worker is the only component that directly executes the continuous analytics pipeline.

---

# 9. DATABASE

Prototype:

```text
SQLite
```

Stores:

```text
camera configuration
zones
fences
events
detections
tracks
environment snapshots
users
audit logs
model/config versions
```

Large media MUST NOT be stored as database blobs.

Use filesystem evidence storage for the prototype.

---

# 10. FILE/EVIDENCE STORAGE

```text
storage/
└── evidence/
    └── YYYY/
        └── MM/
            └── DD/
                └── <event_uuid>/
                    ├── snapshot.jpg
                    ├── event.mp4
                    └── metadata.json
```

---

# 11. MODEL STORAGE

```text
models/
├── detector/
│   └── selected_model.onnx
├── uniform/
│   └── uniform_classifier.onnx
├── face/
│   └── optional/
├── plate/
│   └── optional/
└── enhancement/
    └── optional/
```

Every model MUST have a registry entry containing:

```text
name
version
task
source
license
checksum
input format
output format
runtime
```

---

# 12. VIDEO INGESTION FLOW

```text
RTSP URL
   │
   ▼
Connection manager
   │
   ├── connect
   ├── authenticate
   ├── monitor
   └── reconnect
   │
   ▼
Decoder
   │
   ▼
Frame normalization
   │
   ├── timestamp
   ├── frame_id
   └── camera_id
   │
   ▼
Bounded queue
```

Frame object:

```python
FramePacket(
    camera_id,
    frame_id,
    timestamp_utc,
    image,
    width,
    height
)
```

---

# 13. STREAM FAILURE FLOW

```text
Stream active
      │
      ▼
frame received?
   /       \
 YES       NO
  │         │
  │         ▼
  │    timeout counter
  │         │
  │         ▼
  │    reconnect
  │         │
  │    ┌────┴─────┐
  │    ▼          ▼
  │  success     fail
  │    │          │
  │    ▼          ▼
  │ ONLINE    DEGRADED
  │               │
  │          repeated fail
  │               │
  │               ▼
  └──────────► DISCONNECTED
```

The dashboard MUST expose the state.

---

# 14. FRAME-SCHEDULING FLOW

Do not necessarily run the expensive detector at the native camera FPS.

```text
Camera: 25/30 FPS
        │
        ▼
Frame queue
        │
        ├── environment analyzer: frequent/lightweight
        │
        ├── detector: configurable sample rate
        │
        └── tracker/event engine: update from available detections
```

The system MUST prioritize low latency.

A growing queue MUST NOT be allowed to create seconds of stale analytics.

---

# 15. ENVIRONMENT ENGINE

## 15.1 Purpose

Determine whether the current frame is:

```text
NORMAL
LOW_LIGHT
POOR_VISIBILITY
RAIN_HINT
FOG_HINT
SNOW_HINT
UNKNOWN
```

and produce a continuous quality estimate.

## 15.2 Inputs

Only video-frame data and camera configuration.

No external physical sensors.

## 15.3 Outputs

```python
EnvironmentState(
    lighting,
    brightness,
    contrast,
    blur,
    noise,
    visibility,
    weather_hint,
    terrain,
    quality_score
)
```

---

# 16. ENVIRONMENT ENGINE FLOW

```text
Frame
  │
  ├── luminance statistics
  │
  ├── contrast statistics
  │
  ├── blur/sharpness metric
  │
  ├── optional noise estimate
  │
  └── optional weather classifier
  │
  ▼
EnvironmentState
  │
  ├── lighting
  ├── visibility
  ├── weather
  ├── quality
  └── terrain profile
```

Terrain is initially configured per camera:

```text
FOREST
MOUNTAIN
SNOW
OPEN
CUSTOM
```

Do not build automatic terrain recognition for the first working MVP unless the baseline pipeline is already stable.

---

# 17. ADAPTIVE PERCEPTION FLOW

```text
EnvironmentState
       │
       ▼
Quality decision
       │
 ┌─────┼────────────────┐
 ▼     ▼                ▼
normal low-light       poor visibility
 │      │                │
 │      ▼                ▼
 │  optional         conservative
 │  enhancement      confidence
 │      │                │
 └──────┴────────────────┘
          │
          ▼
       detector
```

Enhancement MUST be selective.

Do not run a heavyweight restoration network on every frame by default.

---

# 18. LOW-LIGHT PROCESSING

Baseline fast options:

```text
gamma correction
CLAHE
light denoising
contrast normalization
```

Optional research model:

```text
Retinexformer
```

Rule:

```text
if low_light AND quality below configured threshold:
    use optional enhancement
else:
    direct inference
```

Success criterion is **better downstream detection/tracking**, not prettier images.

---

# 19. PERCEPTION ENGINE

Primary classes:

```text
person
vehicle
animal
unknown
```

Vehicle subclasses may include:

```text
car
truck
bus
motorcycle
bicycle
```

Output:

```python
Detection(
    camera_id,
    frame_id,
    timestamp,
    class_id,
    confidence,
    bbox
)
```

Detector confidence is **not** an event-risk score.

---

# 20. DETECTOR BACKEND

Preferred architecture:

```text
DetectorInterface
      │
 ┌────┴─────────┐
 ▼              ▼
RF-DETR       Alternative
               detector
```

Do not spread model-specific code through the application.

Example interface:

```python
class Detector:
    def load(self, model_path): ...
    def warmup(self): ...
    def infer(self, image): ...
```

---

# 21. TRACKING FLOW

```text
detections
    │
    ▼
tracker
    │
    ├── match existing tracks
    ├── create new tracks
    ├── update track state
    └── expire lost tracks
    │
    ▼
TrackState
```

Recommended prototype tracker:

```text
ByteTrack
```

or:

```text
BoT-SORT
```

The tracker is a component behind an interface so it can be exchanged.

---

# 22. TRACK STATE

```python
TrackState(
    track_id,
    camera_id,
    class_id,
    bbox,
    center_xy,
    velocity_xy,
    age_frames,
    last_seen,
    confidence_history,
    trajectory
)
```

The trajectory should be stored as time-ordered points:

```text
[(x1,y1,t1), (x2,y2,t2), ...]
```

---

# 23. TRACK PERSISTENCE

Single-frame detections MUST NOT directly trigger high-priority behavior events.

Track lifecycle:

```text
candidate
   │
   ▼
MIN_AGE reached
   │
   ▼
TRACKED
   │
   ├── seen → update
   │
   └── missing → lost counter
                  │
                  ▼
               EXPIRED
```

---

# 24. SPATIAL INTELLIGENCE

Each camera has its own geometry.

```text
Camera
  │
  ├── zones
  ├── virtual fences
  └── expected movement direction
```

Never assume "toward the border" from image coordinates without camera-specific configuration.

---

# 25. ZONE CONFIGURATION

Example:

```json
{
  "camera_id": "cam_07",
  "zones": [
    {
      "id": "safe_01",
      "type": "SAFE",
      "polygon": [[100,100],[500,100],[500,500],[100,500]]
    },
    {
      "id": "restricted_01",
      "type": "RESTRICTED",
      "polygon": [[500,100],[900,100],[900,500],[500,500]]
    }
  ]
}
```

The exact coordinates are created by the operator.

---

# 26. VIRTUAL FENCE FLOW

```text
Track trajectory
       │
       ▼
Previous position
       +
Current position
       │
       ▼
Line intersection test
       │
   ┌───┴────┐
   ▼        ▼
 no         yes
   │         │
ignore    FENCE_CROSSED
```

Do not classify fence crossing from a single box overlap.

Use movement across the line.

---

# 27. DIRECTION FLOW

Given positions separated by `k` frames:

```text
v = current_position - previous_position
```

Normalize:

```text
direction = v / ||v||
```

Compare with the camera's configured expected direction:

```text
alignment = dot(direction, expected_direction)
```

Interpret approximately:

```text
+1 → strongly aligned
 0 → roughly perpendicular
-1 → opposite
```

Include a configurable deadband to prevent noisy direction changes.

---

# 28. TEMPORAL BEHAVIOR ENGINE

The first release uses explainable rules.

Supported events:

```text
LOITERING
PERSISTENT_APPROACH
RESTRICTED_ENTRY
FENCE_CROSSED
REPEATED_APPROACH
```

Optional later:

```text
learned anomaly detection
action recognition
```

---

# 29. LOITERING FLOW

```text
Track
  │
  ▼
Inside configured region?
  │
 ┌┴─────┐
NO      YES
│        │
│        ▼
│   dwell timer
│        │
│        ▼
│   displacement small?
│        │
│     ┌──┴──┐
│    NO    YES
│          │
│          ▼
│    dwell > threshold?
│          │
│       ┌──┴──┐
└──────►NO   YES
            │
            ▼
        LOITERING
```

---

# 30. PERSISTENT APPROACH FLOW

```text
Track persists
      │
      ▼
Movement direction calculated
      │
      ▼
Direction aligns with configured
protected-region direction?
      │
 ┌────┴────┐
NO        YES
 │          │
ignore      ▼
        persistent over time?
             │
          ┌──┴───┐
         NO     YES
                │
                ▼
         PERSISTENT_APPROACH
```

---

# 31. RESTRICTED ENTRY FLOW

```text
Track position
      │
      ▼
Point inside restricted polygon?
      │
 ┌────┴────┐
NO        YES
 │          │
none        ▼
          duration
              │
              ▼
       track persistence valid?
              │
          ┌───┴────┐
         NO       YES
                   │
                   ▼
          RESTRICTED_ENTRY
```

---

# 32. REPEATED APPROACH FLOW

```text
Track / appearance identity available
             │
             ▼
Approach event recorded
             │
             ▼
Store timestamp
             │
             ▼
Another approach within configured window?
          /          \
        NO            YES
        │              │
        │              ▼
        │       REPEATED_APPROACH
        ▼
     normal
```

Do not claim that repeated appearance across cameras equals identity unless a validated cross-camera ReID module is actually enabled.

---

# 33. OPTIONAL UNIFORM/CIVILIAN MODULE

The research baseline uses:

```text
uniformed person
non-uniformed person
animal
```

and demonstrates that uniform/civilian distinction is difficult. fileciteturn3file2L605-L646

IBVAP should therefore use a second-stage classifier:

```text
person detection
      │
      ▼
person crop
      │
      ▼
uniform classifier
      │
 ┌────┼──────────┐
 ▼    ▼          ▼
uniform civilian uncertain
```

`UNCERTAIN` MUST be allowed.

Do not force:

```text
not uniform = civilian
```

---

# 34. OPTIONAL ANPR FLOW

```text
Vehicle track
      │
      ▼
Plate likely visible?
      │
   ┌──┴──┐
  NO     YES
  │       │
skip      ▼
       plate detector
          │
          ▼
       plate crop
          │
          ▼
          OCR
          │
          ▼
   temporal aggregation
          │
          ▼
   plate candidate + score
```

Do not trust one OCR frame when multiple frames are available.

---

# 35. OPTIONAL FACE FLOW

```text
Person track
     │
     ▼
Face visible?
   /      \
 NO       YES
 │          │
skip        ▼
         alignment
            │
            ▼
         embedding
            │
            ▼
      controlled watchlist
            │
       ┌────┴────┐
       ▼         ▼
    no match    candidate
```

Face recognition must remain:

```text
optional
controlled
auditable
human-reviewed
```

It is not the core intrusion detector.

---

# 36. EVIDENCE FUSION ENGINE

This is the central intelligence layer.

Inputs:

```text
detector confidence
track persistence
trajectory consistency
zone relationship
fence crossing
direction
dwell time
behavior
environment quality
optional uniform result
optional plate evidence
optional face evidence
```

Output:

```text
event confidence / priority
+
reason codes
```

---

# 37. EVIDENCE FUSION FLOW

```text
                    Detector
                       │
                    Tracker
                       │
                    Spatial
                       │
                    Behavior
                       │
                  Environment
                       │
              Optional intelligence
                       │
                       ▼
             ┌──────────────────┐
             │ Evidence Fusion  │
             └────────┬─────────┘
                      │
                explainable score
                      │
              ┌───────┼────────┐
              ▼       ▼        ▼
             LOW    MEDIUM    HIGH
```

The scoring formula is configurable and must be documented as a **prototype decision-support heuristic**, not as a scientifically validated threat probability.

---

# 38. SEPARATE THESE THREE NUMBERS

The system MUST NOT confuse:

```text
Detection confidence
```

with:

```text
Track confidence
```

or:

```text
Event/risk priority
```

Example:

```text
person detection confidence = 0.91
track persistence = HIGH
risk priority = HIGH
```

These are different dimensions.

---

# 39. ENVIRONMENT-AWARE CONFIDENCE

Poor visual conditions should affect decision confidence.

Example:

```text
Night
+
low visibility
+
person detector 0.55
+
track exists 8 seconds
+
trajectory consistent
+
restricted-zone crossing
```

This may still become a meaningful event, but the UI should expose:

```text
visual_quality = poor
detection_confidence = 0.55
supporting temporal/spatial evidence = strong
```

Do not fabricate:

```text
"95% threat confidence"
```

---

# 40. EVENT CLASSIFICATION FLOW

```text
Candidate observation
       │
       ▼
Does persistent track exist?
   /               \
 NO                 YES
 │                   │
No high alert        ▼
               spatial condition?
                    /       \
                  NO         YES
                  │           │
             continue         ▼
                         temporal evidence?
                          /          \
                        NO            YES
                        │              │
                     observe      evidence fusion
                                        │
                                        ▼
                                  priority level
```

---

# 41. EVENT PRIORITY

Allowed levels:

```text
INFO
LOW
MEDIUM
HIGH
CRITICAL
```

Do NOT use `CRITICAL` merely because:

```text
person detected
```

High levels require combinations of stronger evidence.

---

# 42. EXPLAINABILITY FLOW

Every important event:

```text
Event
 │
 ├── What?
 ├── Where?
 ├── When?
 ├── Why?
 ├── Environment?
 ├── Evidence?
 └── Confidence?
```

Example:

```text
Event:
RESTRICTED_ENTRY

Why:
PERSISTENT_TRACK
TOWARD_RESTRICTED_ZONE
FENCE_CROSSED

Environment:
NIGHT
POOR_VISIBILITY

Evidence:
snapshot
event clip
trajectory
```

---

# 43. ALERT GENERATION

```text
EventEngine
     │
     ▼
priority >= configured threshold?
     │
 ┌───┴────┐
 NO      YES
 │         │
store      ▼
         create alert
             │
        ┌────┼─────┐
        ▼    ▼     ▼
      DB   clip  websocket
                  │
                  ▼
              frontend
```

---

# 44. EVIDENCE CAPTURE

For alertable event:

```text
ring buffer
   │
   ├── pre-event frames
   ├── event frames
   └── post-event frames
          │
          ▼
       encode
          │
          ▼
     event.mp4
```

Prototype example:

```text
5 seconds before
+
event
+
5 seconds after
```

Make configurable.

---

# 45. EVENT OBJECT

```json
{
  "event_id": "uuid",
  "camera_id": "cam_07",
  "timestamp_utc": "2026-08-28T00:00:00Z",
  "event_type": "RESTRICTED_ENTRY",
  "severity": "HIGH",
  "track_id": 31,
  "object_class": "person",
  "detector_confidence": 0.88,
  "environment": {
    "lighting": "NIGHT",
    "visibility": "POOR",
    "weather": "UNKNOWN",
    "terrain": "FOREST",
    "quality_score": 0.44
  },
  "reason_codes": [
    "PERSISTENT_TRACK",
    "TOWARD_RESTRICTED_ZONE",
    "FENCE_CROSSED"
  ],
  "evidence": {
    "snapshot": "storage/evidence/.../snapshot.jpg",
    "video": "storage/evidence/.../event.mp4"
  },
  "model_versions": {},
  "config_version": "..."
}
```

---

# 46. DATABASE RELATIONSHIP

```text
CAMERA
  │
  ├────< ZONE
  │
  ├────< FENCE
  │
  ├────< DETECTION
  │          │
  │          └────< TRACK
  │                    │
  │                    └────< EVENT
  │
  └────< ENVIRONMENT_SNAPSHOT

EVENT
  │
  ├──── evidence file path
  ├──── reason codes
  ├──── model versions
  └──── audit actions
```

---

# 47. API ARCHITECTURE

## REST

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

## WebSocket

```text
/ws/events
/ws/cameras/{camera_id}
```

---

# 48. EVENT WEBSOCKET FLOW

```text
AI Worker
   │
   ▼
Event created
   │
   ▼
Backend event service
   │
   ▼
WebSocket broker/manager
   │
   ▼
Connected browser
   │
   ▼
new alert appears immediately
```

No page refresh.

---

# 49. CAMERA HEALTH

Each camera should expose:

```text
stream_status
last_frame_time
decoder_fps
inference_fps
dropped_frames
latency_ms
queue_depth
```

Health states:

```text
ONLINE
DEGRADED
STALE
DISCONNECTED
ERROR
```

---

# 50. SYSTEM HEALTH

Backend should expose:

```text
API reachable
database reachable
worker alive
model loaded
storage writable
GPU/CPU health
active cameras
```

The dashboard should clearly distinguish:

```text
application healthy
```

from:

```text
camera analytics healthy
```

---

# 51. FILE STRUCTURE

The canonical repository structure is:

```text
ibvap/
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   ├── api/
│   │   ├── types/
│   │   └── utils/
│   ├── public/
│   └── package.json
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   └── websocket/
│   │   ├── auth/
│   │   ├── db/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── config/
│   │   └── main.py
│   └── tests/
│
├── worker/
│   ├── ingestion/
│   ├── environment/
│   ├── perception/
│   ├── tracking/
│   ├── spatial/
│   ├── behavior/
│   ├── fusion/
│   ├── evidence/
│   ├── runtime/
│   └── main.py
│
├── models/
│   ├── detector/
│   ├── uniform/
│   ├── face/
│   ├── plate/
│   └── enhancement/
│
├── configs/
│   ├── cameras/
│   ├── zones/
│   ├── thresholds/
│   ├── models/
│   └── system.yaml
│
├── storage/
│   ├── evidence/
│   └── database/
│
├── datasets/
│   └── README.md
│
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── replay/
│   └── evaluation/
│
├── scripts/
│   ├── run_replay.py
│   ├── benchmark.py
│   ├── validate_config.py
│   └── prepare_dataset.py
│
├── docs/
│   ├── architecture.md
│   ├── product_requirements.md
│   ├── technical_requirements.md
│   ├── deployment.md
│   └── DECISIONS.md
│
├── docker/
│   ├── backend.Dockerfile
│   ├── worker.Dockerfile
│   └── frontend.Dockerfile
│
├── docker-compose.yml
├── .env.example
├── README.md
└── DECISIONS.md
```

---

# 52. MODULE DEPENDENCY RULE

Dependency direction:

```text
frontend
    ↓
backend
    ↓
worker interfaces / event contracts

worker
    ↓
models/runtime
```

The core event logic must not depend on the React frontend.

The detector must not depend on FastAPI.

The tracker must not depend on the database.

Use interfaces.

---

# 53. CONFIGURATION STRUCTURE

Example:

```yaml
system:
  timezone_storage: UTC
  environment_update_seconds: 1
  evidence_pre_seconds: 5
  evidence_post_seconds: 5

camera:
  inference_fps: 10

detection:
  confidence_threshold: 0.35
  input_width: 640

tracking:
  min_track_age: 5
  max_lost_frames: 30

behavior:
  loitering_seconds: 20
  persistent_approach_seconds: 5
  repeated_approach_window_seconds: 120

environment:
  low_light_threshold: 0.20
  poor_quality_threshold: 0.40
  blur_threshold: 80

risk:
  low_max: 30
  medium_max: 60
  high_max: 80
```

These are initial prototype values only. They MUST be tuned against the team's evaluation videos.

---

# 54. CAMERA CONFIGURATION

Example:

```yaml
camera_id: cam_07
name: Sector 07
source_type: rtsp
source_uri_env: CAM_07_RTSP_URL

terrain: FOREST

zones:
  - id: safe_01
    type: SAFE
    polygon: []

  - id: restricted_01
    type: RESTRICTED
    polygon: []

fences:
  - id: vf_01
    type: BOUNDARY
    polyline: []

expected_direction:
  dx: 1.0
  dy: 0.0
```

Do not place credentials in YAML.

Use environment variables/secrets.

---

# 55. MESSAGE CONTRACTS

Worker-to-backend event contract:

```json
{
  "message_type": "EVENT_CREATED",
  "schema_version": "1.0",
  "event": {}
}
```

Backend-to-frontend:

```json
{
  "message_type": "ALERT_CREATED",
  "schema_version": "1.0",
  "alert": {}
}
```

All messages should be versioned.

---

# 56. OPTIONAL MODULE FAILURE POLICY

Core:

```text
ingestion
detection
tracking
spatial
behavior
fusion
events
```

Optional:

```text
uniform
ANPR
FRS
advanced enhancement
learned anomaly model
```

If optional module fails:

```text
optional module error
       │
       ▼
log error
       │
       ▼
event marks module unavailable
       │
       ▼
core pipeline continues
```

Never crash the whole surveillance worker because OCR failed.

---

# 57. DATA FLOW — SINGLE CAMERA

```text
CAM07
 │
 ▼
RTSP decoder
 │
 ▼
frame
 │
 ├── environment
 │        │
 │        ▼
 │    EnvironmentState
 │
 └───────────────┐
                 ▼
           adaptive preproc
                 │
                 ▼
              detector
                 │
                 ▼
             detections
                 │
                 ▼
              tracker
                 │
                 ▼
              tracks
                 │
                 ├── trajectory
                 ├── zone
                 ├── fence
                 ├── direction
                 └── temporal behavior
                           │
                           ▼
                    event candidate
                           │
                           ▼
                    evidence fusion
                           │
                           ▼
                     Event Engine
                           │
                    ┌──────┴──────┐
                    ▼             ▼
                  store         alert
                                  │
                                  ▼
                               frontend
```

---

# 58. DATA FLOW — MULTIPLE CAMERAS

```text
Cam 01 ──┐
Cam 02 ──┤
Cam 03 ──┼──► Worker Manager
Cam 04 ──┤
Cam N  ──┘
              │
              ├── worker/cam01
              ├── worker/cam02
              ├── worker/cam03
              └── worker/camN
                        │
                        ▼
                shared event contract
                        │
                        ▼
                    FastAPI
                        │
              ┌─────────┴──────────┐
              ▼                    ▼
          Database             WebSocket
```

For SIH, one Python process may manage multiple cameras before process-level scaling is introduced.

---

# 59. PROCESS MODEL

Recommended initial process layout:

```text
Process 1 — frontend dev/server

Process 2 — FastAPI backend

Process 3 — AI worker
            ├── camera loop(s)
            ├── environment
            ├── inference
            ├── tracking
            └── event engine

Process 4 — optional database service only if needed
```

SQLite itself does not need its own server process.

---

# 60. THREAD / ASYNC MODEL

The AI worker should logically separate:

```text
stream reader
      │
      ▼
bounded queue
      │
      ├── processing loop
      │
      └── health monitor
```

Avoid unlimited asynchronous task creation per frame.

---

# 61. COMPUTE FLOW

```text
CPU
├── video decoding
├── frame queue
├── environment statistics
├── business/event logic
├── database
└── API

GPU
└── deep-learning inference
```

CPU-only operation should remain supported for development.

GPU acceleration is recommended for real-time multi-camera demonstrations.

---

# 62. INFERENCE RUNTIME

Recommended abstraction:

```text
PyTorch model
      │
      ▼
export
      │
      ▼
ONNX
      │
      ▼
ONNX Runtime
      │
      ├── CPU
      └── CUDA
```

Optional later:

```text
ONNX
  ↓
OpenVINO on Intel
```

or:

```text
ONNX/TensorRT ecosystem
  ↓
NVIDIA accelerated deployment
```

Do not optimize before measuring.

---

# 63. DETECTOR SELECTION RULE

The architecture is detector-agnostic.

Preferred prototype candidate:

```text
RF-DETR
```

Alternative:

```text
YOLO family if licensing and project policy permit
```

The application must call:

```text
DetectorInterface
```

not:

```text
Ultralytics-specific calls everywhere
```

or:

```text
RF-DETR-specific calls everywhere
```

---

# 64. TRACKER SELECTION RULE

Preferred:

```text
ByteTrack
```

Alternative:

```text
BoT-SORT
```

Switch through:

```text
TrackerInterface
```

---

# 65. FRONTEND EVENT STATE

The frontend maintains:

```text
activeAlerts[]
cameraStates{}
selectedEvent{}
selectedCamera{}
```

When:

```text
ALERT_CREATED
```

arrives:

```text
WebSocket
   ↓
state update
   ↓
alert panel
   ↓
optional sound/browser notification
```

No page refresh.

---

# 66. OPERATOR DASHBOARD ARCHITECTURE

```text
┌───────────────────────────────────────────────────────┐
│ IBVAP                                                 │
├───────────────┬───────────────────────────────────────┤
│ Camera Grid   │ Active Alerts                         │
│               │                                       │
│ [Cam1][Cam2]  │ HIGH — Cam07 — Restricted Entry      │
│ [Cam3][Cam4]  │ MED — Cam02 — Loitering              │
│               │ LOW — Cam09 — Animal                 │
├───────────────┼───────────────────────────────────────┤
│ Selected Feed │ Event Details                         │
│               │                                       │
│ detection     │ What / Why / Environment              │
│ tracking      │ trajectory                            │
│ zones         │ evidence clip                         │
│               │ ACK / DISMISS                          │
├───────────────┴───────────────────────────────────────┤
│ Camera Health | Environment | FPS | Latency            │
└───────────────────────────────────────────────────────┘
```

---

# 67. EVENT DETAIL VIEW

Must show:

```text
Event type
Severity
Camera
Timestamp
Object class
Track ID
Environment
Reasons
Confidence/evidence fields
Snapshot
Video
Trajectory
Zone/fence
Status
```

---

# 68. CAMERA CONFIGURATION VIEW

Must allow:

```text
camera name
stream endpoint
terrain profile
zones
fences
expected direction
threshold overrides
enabled modules
```

---

# 69. EVENT HISTORY

Queries:

```text
by camera
by time
by severity
by event type
by object type
by terrain
by lighting
by environment
by status
```

---

# 70. SECURITY ARCHITECTURE

```text
User
 ↓
Authentication
 ↓
Authorization
 ↓
FastAPI
 ↓
database / event APIs
```

Roles:

```text
ADMIN
OPERATOR
VIEWER
AUDITOR
```

---

# 71. CREDENTIAL FLOW

```text
RTSP credential
      │
      ▼
environment/secret storage
      │
      ▼
camera connection manager
```

Never:

```text
source code
Git repository
frontend bundle
logs
```

---

# 72. AUDIT FLOW

Audit at minimum:

```text
login
camera added/modified
zone added/modified
fence added/modified
model changed
threshold changed
alert acknowledged
alert dismissed
sensitive evidence accessed
optional watchlist changed
```

---

# 73. OFFLINE ARCHITECTURE

Core local path:

```text
CCTV
 ↓
local worker
 ↓
local event database
 ↓
local evidence
 ↓
local dashboard
```

Cloud is not required for the core prototype.

Later:

```text
local event queue
      │
      └── when connection returns
              ↓
        central synchronization
```

---

# 74. NO-CLOUD PRINCIPLE

If the internet fails:

```text
AI inference → CONTINUE
event creation → CONTINUE
local evidence → CONTINUE
dashboard → CONTINUE on local network
central sync → PAUSED
```

---

# 75. PERFORMANCE ARCHITECTURE

Measure:

```text
decode FPS
inference FPS
tracking FPS
end-to-end latency
queue depth
GPU utilization
CPU utilization
VRAM
RAM
```

Do not optimize from assumptions.

---

# 76. LATENCY FLOW

```text
Frame captured
     ↓
decode latency
     ↓
preprocessing
     ↓
inference
     ↓
tracking
     ↓
event logic
     ↓
backend publish
     ↓
WebSocket
     ↓
UI render
```

Record:

```text
T_total
=
T_decode
+
T_preprocess
+
T_inference
+
T_tracking
+
T_reasoning
+
T_transport
+
T_UI
```

---

# 77. EVIDENCE REPLAY ARCHITECTURE

The same worker must accept:

```text
VideoSource
```

interfaces:

```text
RTSPSource
FileSource
WebcamSource
```

Then:

```text
same analytics pipeline
```

can run against:

```text
MP4
```

without modifying detector/tracker/event code.

---

# 78. REPLAY TEST FLOW

```text
Test video
   +
camera configuration
   +
expected annotations
   ↓
Replay runner
   ↓
IBVAP pipeline
   ↓
generated events
   ↓
compare with expected
   ↓
metrics report
```

This is critical for SIH testing.

---

# 79. TESTING STRATEGY

## Unit tests

Test:

```text
zone inclusion
line crossing
direction
loitering timer
risk scoring
event creation
config validation
```

## Integration tests

Test:

```text
stream → detector → tracker → event
```

## Replay tests

Test full videos.

## UI tests

Test:

```text
alert arrives
event opens
ACK works
camera disconnect shown
```

---

# 80. CORE UNIT TEST EXAMPLES

## Test 1 — lateral movement

Input:

```text
track moves parallel to configured boundary
```

Expected:

```text
no restricted-entry event
```

## Test 2 — boundary crossing

Input:

```text
track intersects virtual fence
```

Expected:

```text
FENCE_CROSSED
```

## Test 3 — animal

Input:

```text
animal track enters monitored area
```

Expected:

```text
animal event / no high human-intrusion event
```

## Test 4 — low-quality scene

Input:

```text
poor-quality detection with no persistent track
```

Expected:

```text
UNCERTAIN
```

---

# 81. DATASET ARCHITECTURE

## Generic model source

Use pretrained weights.

Candidate public datasets:

```text
COCO
CrowdHuman
VisDrone
MOT
VIRAT
```

Use them for appropriate tasks rather than claiming any is a perfect border dataset.

## Custom dataset

```text
datasets/ibvap_custom/
├── images/
├── labels/
├── metadata/
└── splits/
```

Metadata should include environment tags when available.

---

# 82. DATASET SPLIT RULE

Never put adjacent frames from the same video into both training and test sets.

Preferred:

```text
video/site-level separation
```

rather than pure random-frame splitting.

This reduces data leakage.

---

# 83. CUSTOM DATASET LABELS

Initial custom labels:

```text
uniformed_person
civilian_person
uncertain
```

Optional:

```text
forest
mountain
snow
open
night
low_visibility
```

Do not invent operational labels that the data cannot support.

---

# 84. ANOMALY DETECTION — LATER ONLY

Possible future architecture:

```text
track sequence
      ↓
feature extraction
      ↓
temporal model
      ↓
anomaly score
```

The first prototype should prefer:

```text
explicit spatial + temporal rules
```

because they are easier to validate and explain.

---

# 85. FUTURE LEARNED BEHAVIOR LAYER

Optional:

```text
MMAction2/custom temporal model
```

Position:

```text
tracks
 ↓
temporal features/video clip
 ↓
learned model
 ↓
behavior suggestion
 ↓
evidence fusion
```

It must never replace deterministic safety checks in the first release.

---

# 86. CROSS-CAMERA ARCHITECTURE — FUTURE

Do not implement as a core MVP requirement.

Future:

```text
Camera A
  ↓
Track A
  ↓
appearance embedding
  ↓
candidate matching
  ↓
Camera B Track B
```

Output must remain:

```text
possible association
```

until validated.

Never label it as certain identity.

---

# 87. MAP/GIS — FUTURE OPTIONAL

Camera:

```text
camera_id
latitude
longitude
sector
```

Dashboard may display:

```text
camera point
event point
sector
```

Do not infer precise person geographic coordinates from a normal camera unless calibration supports it.

---

# 88. CONTAINER ARCHITECTURE

Initial:

```text
docker-compose.yml

services:
  frontend
  backend
  worker
```

SQLite and evidence storage can be mounted volumes.

Example conceptual volumes:

```text
./storage:/app/storage
./models:/app/models
./configs:/app/configs
```

Do not put secrets into the image.

---

# 89. GPU CONTAINER RULE

Only the worker requires GPU access.

```text
frontend → CPU
backend  → CPU
worker   → GPU/CPU
```

Do not give GPU access to every service.

---

# 90. STARTUP SEQUENCE

```text
docker compose up
       │
       ├── frontend
       ├── backend
       └── worker
                │
                ├── load config
                ├── validate model files
                ├── load detector
                ├── warmup model
                ├── load camera config
                └── start stream loops
```

If a required model fails to load:

```text
worker health = ERROR
```

and dashboard must expose the error.

---

# 91. SHUTDOWN SEQUENCE

```text
shutdown requested
      │
      ▼
stop accepting new frames
      │
      ▼
flush pending event writes
      │
      ▼
finish evidence file
      │
      ▼
close streams
      │
      ▼
release model/runtime
      │
      ▼
exit
```

---

# 92. LOGGING

Use structured JSON logs.

Each log should include:

```text
timestamp
service
camera_id
event_id if applicable
level
message
exception
model_version if applicable
```

Log examples:

```text
CAMERA_CONNECTED
CAMERA_DISCONNECTED
MODEL_LOADED
ENVIRONMENT_CHANGED
EVENT_CREATED
EVENT_PUBLISHED
EVIDENCE_WRITTEN
```

---

# 93. OBSERVABILITY

Metrics:

```text
camera_fps
inference_fps
latency_ms
queue_depth
events_total
alerts_total
camera_reconnects
dropped_frames
model_inference_ms
```

Use simple logging/metrics in the SIH build.

Prometheus/Grafana may be added later, not required initially.

---

# 94. MODEL VERSION TRACEABILITY

Every event:

```text
detector_version
tracker_version
uniform_model_version
anpr_model_version if used
face_model_version if used
environment_version
config_version
```

This allows reproducibility.

---

# 95. MODEL UPDATE FLOW

```text
new model
   │
   ▼
validation set
   │
   ▼
benchmark
   │
   ▼
model registry
   │
   ▼
activate
   │
   ▼
new events reference new model version
```

Never replace model files silently.

---

# 96. ENVIRONMENT ADAPTATION EXPERIMENT FLOW

To prove the product differentiator:

```text
same test videos
        │
        ├──────────────► baseline pipeline
        │
        └──────────────► adaptive pipeline
                         │
                         ▼
                    compare results
```

Measure:

```text
recall
false alarms
tracking continuity
event precision
latency
```

---

# 97. PRODUCT DIFFERENTIATOR ARCHITECTURE

The distinguishing pipeline is:

```text
environment
     ↓
adaptive perception
     ↓
tracking
     ↓
spatial reasoning
     ↓
temporal reasoning
     ↓
evidence fusion
```

Not:

```text
camera → YOLO → dashboard
```

This distinction should remain visible in documentation and demos.

---

# 98. FALSE-ALARM CONTROL FLOW

```text
raw detection
     │
     ▼
is it persistent?
 /            \
NO             YES
│               │
discard         ▼
             spatial context
                  │
                  ▼
             behavioral context
                  │
                  ▼
             environment context
                  │
                  ▼
             evidence fusion
                  │
                  ▼
              priority
```

---

# 99. EXAMPLE — ANIMAL

```text
animal detected
      ↓
track persistent
      ↓
moves through normal area
      ↓
no fence crossing
      ↓
no suspicious behavior
      ↓
INFO / ignore
```

Animal is a contextual class, not automatically a threat.

---

# 100. EXAMPLE — LATERAL HUMAN MOVEMENT

```text
person detected
      ↓
track persistent
      ↓
movement parallel to boundary
      ↓
no restricted-zone entry
      ↓
no fence crossing
      ↓
no HIGH event
```

This reuses the directional concept in the supplied baseline research, while removing its dependence on physical motion sensors. The original paper's sensor module specifically distinguishes lateral from longitudinal movement. fileciteturn3file2L574-L590

---

# 101. EXAMPLE — RESTRICTED ENTRY

```text
person detected
      ↓
track #17
      ↓
toward restricted area
      ↓
restricted boundary crossed
      ↓
persistent track
      ↓
event fusion
      ↓
HIGH
      ↓
snapshot + clip + reasons
      ↓
WebSocket alert
```

---

# 102. EXAMPLE — NIGHT

```text
frame
 ↓
environment analyzer
 ↓
LOW_LIGHT + LOW_QUALITY
 ↓
selective enhancement
 ↓
detector
 ↓
tracker
 ↓
spatial/temporal reasoning
 ↓
event
```

The system must show the degraded environment state to the operator.

---

# 103. EXAMPLE — EXTREME VISIBILITY FAILURE

```text
frame
 ↓
environment = POOR
 ↓
weak detection
 ↓
no persistent track
 ↓
UNCERTAIN
 ↓
no HIGH event
```

The system does not hallucinate an object.

---

# 104. EXAMPLE — OPTIONAL ANPR

```text
vehicle
 ↓
track
 ↓
plate visible
 ↓
plate detection
 ↓
OCR
 ↓
frame 1 ─┐
frame 2 ─┼─► temporal voting
frame 3 ─┤
frame 4 ─┘
          ↓
plate candidate
          ↓
supporting evidence
```

---

# 105. EXAMPLE — OPTIONAL UNIFORM CLASSIFICATION

```text
person
 ↓
crop
 ↓
uniform classifier
 ↓
uniform / civilian / uncertain
 ↓
event fusion
```

Uniform classification alone must not decide whether an event is safe.

---

# 106. RISK ENGINE EXAMPLE

Prototype-only conceptual evidence:

```text
+ detection confidence
+ track persistence
+ restricted-zone evidence
+ direction evidence
+ behavior evidence
+ environment context
- animal context
- weak/uncertain evidence
```

No fixed weights are authoritative.

Weights belong in configuration.

---

# 107. HIGH-PRIORITY ALERT EXAMPLE

```text
HIGH

Camera: CAM07
Track: #31

Event:
RESTRICTED_ENTRY

Evidence:
• persistent person track
• movement toward restricted region
• virtual fence crossed

Environment:
• night
• poor visibility

Attachments:
• snapshot
• event clip
• trajectory

Operator action:
[ACKNOWLEDGE] [DISMISS]
```

---

# 108. ACCEPTANCE CRITERIA — ARCHITECTURE

The implementation is architecturally correct only when:

- frontend is separate from backend;
- backend is separate from continuous worker;
- worker owns video analytics;
- models are loaded once and reused;
- camera input is configurable;
- zones/fences are configurable;
- event logic is deterministic/testable;
- high-priority events have evidence;
- event reasons are available;
- database stores metadata, not large video blobs;
- optional modules cannot crash the core pipeline;
- camera failure does not silently disappear;
- model versions are traceable.

---

# 109. ACCEPTANCE CRITERIA — END-TO-END

The minimum complete flow:

```text
video
 ↓
environment
 ↓
detector
 ↓
tracker
 ↓
zone
 ↓
direction
 ↓
behavior
 ↓
fusion
 ↓
event
 ↓
evidence
 ↓
database
 ↓
WebSocket
 ↓
dashboard
```

All stages must be demonstrably connected.

---

# 110. SIH DEMO ARCHITECTURE

Use one workstation.

Scenario sequence:

```text
SCENARIO 1
Daytime person
→ detection
→ tracking

SCENARIO 2
Lateral movement
→ no HIGH intrusion event

SCENARIO 3
Animal movement
→ no HIGH human intrusion event

SCENARIO 4
Night/poor visibility
→ environment adaptation

SCENARIO 5
Persistent approach
→ spatial + temporal evidence

SCENARIO 6
Fence crossing
→ HIGH alert + evidence
```

ANPR/FRS can be shown after the core workflow if stable.

---

# 111. WHAT NOT TO DEMO

Do not spend the demo on:

```text
100 classes
```

Do not show:

```text
random bounding boxes
```

Do not claim:

```text
100% night visibility
```

Do not pretend:

```text
face recognition is always accurate
```

Do not create fake metrics.

Show one strong end-to-end event.

---

# 112. PRODUCTION-LIKE FUTURE ARCHITECTURE

Only after the prototype is stable:

```text
                CAMERA SITE
                    │
             ┌──────▼──────┐
             │ Edge Worker │
             └──────┬──────┘
                    │
            events / selected clips
                    │
                    ▼
             Central Gateway
                    │
          ┌─────────┼─────────┐
          ▼         ▼         ▼
      Event DB    Storage   Analytics
          │
          ▼
       Dashboard
```

The SIH build does not need this topology.

---

# 113. FUTURE MULTI-SITE ARCHITECTURE

```text
SITE A ─┐
SITE B ─┼─► event gateway ─► central platform
SITE C ─┤
SITE D ─┘
```

Each site retains local inference capability.

---

# 114. RESEARCH EXTENSIONS

After MVP:

```text
environment classifier
        +
learned anomaly model
        +
cross-camera association
        +
better small-object model
        +
better low-light enhancement
        +
controlled biometric modules
```

These are extensions, not prerequisites.

---

# 115. ARCHITECTURAL RISKS

## R1 — Overengineering

Mitigation:

```text
one workstation
three application components
one DB
simple storage
```

## R2 — Detector dependence

Mitigation:

```text
DetectorInterface
```

## R3 — False alerts

Mitigation:

```text
tracking
+
spatial reasoning
+
temporal reasoning
+
fusion
```

## R4 — Poor environment

Mitigation:

```text
environment state
+
selective enhancement
+
uncertainty
```

## R5 — Stream instability

Mitigation:

```text
reconnect
+
bounded queue
+
health states
```

## R6 — Optional module failure

Mitigation:

```text
fault isolation
```

---

# 116. CRITICAL ENGINEERING TRADE-OFFS

## Accuracy vs latency

Higher resolution/more complex model:

```text
accuracy potential ↑
latency ↑
compute ↑
```

Therefore benchmark.

## Enhancement vs latency

Enhancement may help low-light detection but adds compute and can create artifacts.

Use selectively.

## Rule-based vs learned behavior

Rules:
- explainable;
- fast;
- easy to test.

Learned:
- potentially more expressive;
- data hungry;
- harder to validate.

Use rules first.

## Monolithic vs modular

Monolith:
- simpler first prototype.

Modular interfaces:
- easier to replace models.

Use a **modular codebase inside a small deployment**, not many distributed services.

---

# 117. ARCHITECTURAL DECISION RECORD

Create:

```text
docs/DECISIONS.md
```

Record every nontrivial change:

```text
Decision ID
Date
Question
Chosen option
Alternatives
Reason
Impact
```

Example:

```text
ADR-001
Question: detector
Decision: RF-DETR
Reason: selected project baseline
Alternative: YOLO
Impact: licensing + integration
```

---

# 118. "DO NOT HALLUCINATE" IMPLEMENTATION PROTOCOL

Antigravity MUST use this sequence before adding any component:

```text
1. Is it required by this architecture?
        │
    NO  └────► do not add

2. Is it named in an approved requirement?
        │
    NO  └────► do not add

3. Does an existing module already solve it?
        │
    YES └────► reuse module

4. Does it change an architectural boundary?
        │
    YES └────► record decision before changing

5. Is the dependency/license verified?
        │
    NO  └────► do not add
```

---

# 119. NO INVENTED CAPABILITIES RULE

Examples:

If no thermal camera exists:

```text
DO NOT write:
"thermal confirmation received"
```

If no face is visible:

```text
DO NOT write:
"face recognized"
```

If no plate is readable:

```text
DO NOT write:
"plate = XXXXX"
```

If trajectory is too short:

```text
DO NOT write:
"persistent approach"
```

If visual evidence is insufficient:

```text
write:
"UNCERTAIN"
```

---

# 120. FINAL ARCHITECTURE

The complete intended architecture is:

```text
                         EXISTING IP CCTV
                               │
                               ▼
                       ┌──────────────┐
                       │ VideoSource  │
                       │ RTSP / File  │
                       └──────┬───────┘
                              │
                              ▼
                       ┌──────────────┐
                       │ Decoder      │
                       └──────┬───────┘
                              │
                              ▼
                       ┌──────────────┐
                       │ Frame Queue  │
                       └──────┬───────┘
                              │
                 ┌────────────┴────────────┐
                 ▼                         ▼
        ┌────────────────┐       ┌────────────────┐
        │ Environment    │       │ Frame sampler  │
        │ Analyzer       │       │ / preproc      │
        └───────┬────────┘       └───────┬────────┘
                │                        │
                └────────────┬───────────┘
                             ▼
                    ┌──────────────────┐
                    │ Detector         │
                    └────────┬─────────┘
                             ▼
                    ┌──────────────────┐
                    │ Tracker          │
                    └────────┬─────────┘
                             ▼
                    ┌──────────────────┐
                    │ Spatial Engine   │
                    │ zones/fences     │
                    │ direction        │
                    └────────┬─────────┘
                             ▼
                    ┌──────────────────┐
                    │ Behavior Engine  │
                    │ temporal rules   │
                    └────────┬─────────┘
                             │
                    ┌────────┴─────────┐
                    ▼                  ▼
             Optional modules      Environment
             uniform/ANPR/FRS       context
                    │                  │
                    └────────┬─────────┘
                             ▼
                    ┌──────────────────┐
                    │ Evidence Fusion  │
                    └────────┬─────────┘
                             ▼
                    ┌──────────────────┐
                    │ Event Engine     │
                    └───────┬───┬──────┘
                            │   │
                 ┌──────────┘   └─────────────┐
                 ▼                            ▼
        ┌──────────────────┐        ┌──────────────────┐
        │ Evidence Writer  │        │ Event Database   │
        └─────────┬────────┘        └────────┬─────────┘
                  │                          │
                  └─────────────┬────────────┘
                                ▼
                        ┌────────────────┐
                        │ FastAPI        │
                        │ REST/WebSocket │
                        └───────┬────────┘
                                ▼
                        ┌────────────────┐
                        │ React UI       │
                        └────────────────┘
```

---

# 121. FINAL TECHNOLOGY STACK

## Video

```text
GStreamer
FFmpeg
OpenCV
```

## Detector

```text
RF-DETR preferred baseline
```

## Tracking

```text
ByteTrack
or
BoT-SORT
```

## Environment

```text
OpenCV metrics
optional Retinexformer
```

## Behavior

```text
Python temporal/spatial rule engine
optional MMAction2 later
```

## Uniform

```text
custom lightweight classifier
```

## ANPR

```text
plate detector
+
PaddleOCR
```

## Face

```text
InsightFace
optional and controlled
```

## Inference

```text
ONNX Runtime
optional OpenVINO / NVIDIA optimization later
```

## Backend

```text
FastAPI
Pydantic
asyncio
```

## Frontend

```text
React
TypeScript
Vite
```

## Database

```text
SQLite prototype
PostgreSQL later
```

## Storage

```text
local filesystem prototype
object storage later
```

## Packaging

```text
Docker
Docker Compose
```

---

# 122. FINAL TECHNOLOGY FLOW

```text
GStreamer/FFmpeg
      ↓
OpenCV
      ↓
Environment Analyzer
      ↓
RF-DETR
      ↓
ByteTrack / BoT-SORT
      ↓
Custom Spatial Engine
      ↓
Custom Temporal/Behavior Engine
      ↓
Optional:
  uniform / PaddleOCR / InsightFace
      ↓
Custom Evidence Fusion
      ↓
Custom Event Engine
      ↓
FastAPI
      ↓
SQLite + Evidence Storage
      ↓
WebSocket
      ↓
React Dashboard
```

---

# 123. ARCHITECTURE COMPLETION CHECKLIST

Before declaring architecture implemented:

```text
[ ] Camera source abstraction exists
[ ] RTSP source works
[ ] MP4 replay source works
[ ] Bounded frame queue works
[ ] EnvironmentState exists
[ ] Detector interface exists
[ ] Selected detector loads once
[ ] Tracker interface exists
[ ] Persistent tracks work
[ ] Camera-specific zones exist
[ ] Virtual fence exists
[ ] Direction exists
[ ] Loitering exists
[ ] Persistent approach exists
[ ] Restricted entry exists
[ ] Evidence fusion exists
[ ] Event schema exists
[ ] Evidence clip exists
[ ] SQLite schema exists
[ ] REST API exists
[ ] WebSocket alerts exist
[ ] React dashboard exists
[ ] Camera health exists
[ ] Model/config versions are stored
[ ] Unit tests exist
[ ] Replay benchmark exists
[ ] At least 3 demo scenarios work
```

---

# 124. FINAL BUILD ORDER

Antigravity MUST build in this order:

```text
1. Repository + configuration
2. FastAPI + SQLite
3. React dashboard shell
4. VideoSource abstraction
5. MP4 replay
6. RTSP input
7. Detector interface
8. Detector implementation
9. Detection visualization
10. Tracker
11. Trajectory
12. Camera zones
13. Virtual fence
14. Direction
15. Environment analyzer
16. Low-light selective processing
17. Behavior rules
18. Evidence fusion
19. Event database
20. Evidence writer
21. WebSocket
22. Alert dashboard
23. Camera health
24. Replay tests
25. Benchmarks
26. Optional uniform classifier
27. Optional ANPR
28. Optional FRS
29. Docker packaging
30. Final SIH demo
```

Do not reorder this to work on optional features before the core event loop.

---

# 125. FINAL NON-NEGOTIABLE PRODUCT LOOP

The system is successful when this works:

```text
EXISTING CCTV
      ↓
ENVIRONMENT
      ↓
PERSON / VEHICLE / ANIMAL
      ↓
TRACK
      ↓
WHERE?
      ↓
WHICH DIRECTION?
      ↓
HOW LONG?
      ↓
WHAT BEHAVIOR?
      ↓
WHAT ENVIRONMENT?
      ↓
HOW STRONG IS THE EVIDENCE?
      ↓
IS THIS AN EVENT?
      ↓
WHAT PRIORITY?
      ↓
WHY?
      ↓
SHOW EVIDENCE
      ↓
HUMAN OPERATOR
```

That is IBVAP.

---

# 126. FINAL ARCHITECTURAL STATEMENT

**IBVAP is not a collection of AI models.**

It is a software-defined event-intelligence pipeline:

```text
Perceive
   ↓
Track
   ↓
Contextualize
   ↓
Reason
   ↓
Fuse
   ↓
Explain
   ↓
Alert
```

The product's distinguishing architectural property is:

> **environment-aware perception + persistent tracking + camera-specific spatial reasoning + temporal behavior reasoning + explainable evidence fusion, operating over existing IP CCTV without mandatory external sensors.**

No component outside this architecture is required to demonstrate the SIH prototype.
