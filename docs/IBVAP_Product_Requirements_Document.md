# IBVAP — Intelligent Border Video Analytics Platform
## Product Requirements Document (PRD)

**Document type:** Product Requirements Document  
**Product:** IBVAP — Intelligent Border Video Analytics Platform  
**Target:** Smart India Hackathon / SIH-level prototype with a credible path to field hardening  
**Primary constraint:** Software-only intelligence layer over existing IP-based CCTV infrastructure  
**Primary users:** Border surveillance operators, control-room personnel, supervisors, system administrators  
**Product principle:** Detect events, not just objects.

---

# 1. Product Vision

IBVAP is a software-defined border video intelligence platform that converts existing CCTV cameras from passive recording devices into proactive, context-aware surveillance sensors.

The product continuously analyzes live or recorded CCTV feeds and answers four operational questions:

1. **What is happening?**
2. **Where is it happening?**
3. **How is it developing over time?**
4. **Does it warrant operator attention?**

The product is specifically designed around a difficult reality: border environments are not visually uniform. Forests, mountains, snow-covered terrain, open ground, low-light scenes, fog, rain, snow, blur, occlusion, and changing illumination can reduce the reliability of conventional computer-vision pipelines.

Therefore IBVAP is not designed around the assumption that every frame is equally reliable.

Instead:

```text
CCTV
  ↓
Environment understanding
  ↓
Adaptive perception
  ↓
Object detection
  ↓
Tracking
  ↓
Spatial reasoning
  ↓
Temporal / behavior reasoning
  ↓
Evidence fusion
  ↓
Risk-aware event
  ↓
Operator alert + evidence
```

The product is intended to **assist human decision-making**, not autonomously authorize enforcement action.

---

# 2. Problem Definition

## 2.1 The operational problem

Border security teams are often required to monitor large, remote and difficult-to-access areas continuously. Traditional CCTV primarily provides live viewing and recording, leaving human operators to discover meaningful events by watching multiple feeds.

This creates several product problems:

- continuous monitoring is difficult to sustain;
- important events can be hidden inside long periods of normal footage;
- conventional motion alerts can produce excessive false alarms;
- visibility changes with lighting and weather;
- difficult terrain creates different visual conditions across cameras;
- the same object can look very different at different distances and viewpoints;
- object detection alone does not explain intent or event significance;
- existing cameras may not provide built-in advanced analytics.

The supplied Digital Border Surveillance research explicitly frames remote-area and adverse-weather monitoring as a challenge and proposes AI-assisted monitoring with object detection, movement detection, alarm generation and a control-room interface. fileciteturn2file0L22-L45

That research also demonstrates the operational value of differentiating uniformed personnel, civilians and animals to reduce false alarms and supports recording the corresponding video and notification in a control-room workflow. fileciteturn2file6L347-L361

## 2.2 The deeper product problem

The real problem is not:

> "How do we detect a person in CCTV?"

The real problem is:

> "How do we reliably identify security-relevant events from imperfect video without requiring an operator to watch every frame?"

This distinction drives the entire product design.

---

# 3. Why Current Approaches Are Not Enough

## 3.1 Passive CCTV

```text
Camera
  ↓
Live feed
  ↓
Human watches
```

Problem:
- no prioritization
- no automatic event discovery
- operator fatigue
- difficult to scale across cameras

## 3.2 Motion detection

```text
Motion
  ↓
Alert
```

Problem:
- animals trigger alerts
- vegetation can trigger alerts
- rain/snow can create motion
- shadows and illumination changes can trigger alerts
- normal movement may be irrelevant

## 3.3 Detection-only AI

```text
YOLO
 ↓
PERSON
 ↓
Alert
```

Problem:
- no temporal context
- no zone context
- no movement direction
- no behavioral context
- no uncertainty management

## 3.4 Monolithic smart-camera approach

Requires replacing or augmenting camera hardware.

Problem:
- expensive at scale
- difficult retrofit
- vendor dependency
- unsuitable for the SIH requirement that analytics be added to existing CCTV infrastructure

## 3.5 Specialized sensor architectures

Sensor-rich systems can improve detection but increase:

- cost
- installation complexity
- maintenance
- deployment dependency

The research supplied by the team also notes cost, feasibility, weather and terrain as important limitations in several existing border-surveillance approaches. fileciteturn2file2L135-L166

---

# 4. Product Opportunity

IBVAP sits between:

```text
Passive CCTV
```

and

```text
Full smart-surveillance infrastructure
```

It adds an AI/software layer without requiring every deployed camera to become a specialized smart camera.

The product opportunity is:

> **Retrofit intelligence rather than replace infrastructure.**

The platform should use existing IP cameras wherever technically possible, while allowing deployment on a local server or edge-compute workstation.

---

# 5. Product Goals

## G1 — Convert passive CCTV into intelligent event sources

A camera should produce:

```text
observations
+
tracks
+
events
+
evidence
```

rather than just a video stream.

## G2 — Reduce operator monitoring burden

Operators should focus on:

```text
important events
```

instead of:

```text
every frame from every camera
```

## G3 — Reduce false alarms

The platform should not treat every detection or motion event as a security incident.

## G4 — Improve environmental robustness

The system should adapt processing based on:

- lighting
- visibility
- blur/noise
- weather indications
- terrain/scene profile

## G5 — Preserve human oversight

IBVAP should surface evidence and reasoning to a human operator.

## G6 — Remain hardware-agnostic

Core product capabilities should operate with existing IP CCTV infrastructure.

## G7 — Provide a scalable software architecture

The same conceptual product should support:

```text
1 camera
→ 10 cameras
→ 100+ cameras
```

without redesigning the core product.

---

# 6. Non-Goals

IBVAP will NOT initially:

- autonomously use force;
- make detention decisions;
- declare a person to be a criminal or terrorist;
- infer intent solely from facial appearance;
- claim universal detection in all weather conditions;
- replace trained security personnel;
- require new field sensors for the core product;
- depend on cloud connectivity for basic local detection;
- treat AI confidence as a probability of threat.

---

# 7. Users and Stakeholders

## 7.1 Primary stakeholder — Border Surveillance Operator

### Responsibilities

- monitor assigned cameras;
- investigate alerts;
- acknowledge/dismiss events;
- review evidence;
- escalate incidents;
- monitor camera/system health.

### Problems

- too many feeds;
- long periods of inactivity;
- information overload;
- difficult visibility conditions;
- limited time to investigate every event.

### Product needs

- prioritized alerts;
- concise event explanations;
- evidence clips;
- trajectory visualization;
- camera and zone context;
- low-latency access to live feed.

---

# 8. Secondary Stakeholder — Supervisor / Command User

### Responsibilities

- monitor multiple sectors;
- review trends;
- prioritize events;
- inspect historical incidents;
- supervise operators.

### Product needs

- incident overview;
- heatmaps/trends;
- event history;
- camera health;
- performance analytics;
- environmental performance comparisons.

---

# 9. System Administrator

### Responsibilities

- add/configure cameras;
- configure zones and fences;
- manage users;
- manage models;
- maintain system health;
- review logs.

### Product needs

- camera configuration;
- stream diagnostics;
- authentication;
- model versioning;
- system metrics;
- audit logs.

---

# 10. Security / IT Infrastructure Stakeholder

Needs:

- secure network deployment;
- credential protection;
- local processing;
- auditability;
- reliable restart/recovery;
- minimal external dependencies;
- controlled access to video and events.

---

# 11. Government / Security Organization

High-level outcomes:

- better situational awareness;
- force multiplication;
- lower monitoring burden;
- greater utilization of existing CCTV investment;
- scalable software architecture;
- measurable operational performance.

---

# 12. Procurement / Technology Management Stakeholder

Needs:

- hardware compatibility;
- predictable resource requirements;
- open interfaces;
- licensing clarity;
- deployment documentation;
- maintainability;
- ability to replace individual software components.

---

# 13. Human Review / Governance Stakeholder

Important where biometric or identity-related functionality is enabled.

Needs:

- clear evidence trail;
- audit logs;
- confidence/uncertainty visibility;
- controlled use of biometric capabilities;
- retention rules;
- human review before consequential identity-related action.

The supplied research also identifies privacy, accountability, proportionality and biometric governance as important issues in AI-enabled border surveillance. fileciteturn2file3L202-L242

---

# 14. User Personas

## Persona A — Operator

> "I do not need another dashboard full of boxes. I need to know which event deserves my attention, why it matters, and where the evidence is."

## Persona B — Supervisor

> "I need to understand what is happening across cameras and whether the alerting system is actually useful."

## Persona C — Administrator

> "I need to connect cameras, configure rules, update models and diagnose failures without changing the application code."

---

# 15. User Jobs to Be Done

## Operator JTBD

"When something unusual happens, help me notice it quickly, understand the reason, inspect evidence, and decide what to do next."

## Supervisor JTBD

"When many cameras are active, help me understand where and when meaningful events are occurring."

## Administrator JTBD

"Help me onboard cameras and maintain reliable analytics without rebuilding the system."

---

# 16. Core Product Concept

IBVAP is built around five product layers:

```text
1. PERCEPTION
What objects are visible?

2. TRACKING
Where are those objects moving?

3. CONTEXT
Where are they and what is the environment?

4. REASONING
What pattern is occurring over time?

5. DECISION SUPPORT
Does this pattern deserve human attention?
```

---

# 17. Product Architecture at a Business Level

```text
             EXISTING CCTV
                   |
                   v
            IBVAP Platform
                   |
     +-------------+-------------+
     |             |             |
     v             v             v
 Perception    Context       History
     |             |             |
     +-------------+-------------+
                   |
                   v
            Event Intelligence
                   |
                   v
              Risk/priority
                   |
                   v
              Operator UI
                   |
                   v
              Human action
```

---

# 18. Core Product Capabilities

## 18.1 Live CCTV ingestion

The platform SHALL ingest supported IP-camera streams and local replay footage.

User outcome:

> "I can bring an existing camera into IBVAP without purchasing a special AI camera."

---

# 19. Multi-Camera Management

The operator SHALL be able to:

- view camera status;
- select cameras;
- inspect live feed;
- view camera environment state;
- see camera-specific events.

Camera status:

```text
ONLINE
DEGRADED
STALE
DISCONNECTED
ERROR
```

---

# 20. Object Intelligence

The system SHALL identify, at minimum:

- person;
- vehicle;
- animal;
- unknown object.

Vehicle subclasses MAY include:

- car;
- truck;
- bus;
- motorcycle;
- bicycle.

The product must clearly separate:

```text
OBJECT DETECTED
```

from:

```text
SECURITY EVENT
```

---

# 21. Person Intelligence

For a detected person, the platform MAY maintain:

- track ID;
- position;
- trajectory;
- movement direction;
- dwell time;
- zone;
- environmental context;
- optional uniform/civilian classification.

The system should support:

```text
uniform
civilian
uncertain
```

rather than forcing an uncertain visual observation into a binary decision.

The supplied Digital Border research uses uniformed, non-uniformed and animal classes specifically to reduce false alarms and distinguishes movement and alert classes. fileciteturn2file9L477-L517

---

# 22. Vehicle Intelligence

For a vehicle, the platform SHALL support:

- detection;
- classification;
- tracking;
- location/zone;
- optional plate recognition.

Vehicle events should be based on the tracked object, not an isolated frame.

---

# 23. Animal Intelligence

Animals SHALL be treated as a dedicated contextual class.

Primary product reason:

- reduce false alarms;
- distinguish movement not caused by people;
- provide contextual information.

Animal detection should not automatically generate a high-priority intrusion event.

---

# 24. Unknown Object Handling

An object that cannot be reliably classified MUST be allowed to remain:

```text
UNKNOWN / UNCERTAIN
```

This avoids harmful forced classification.

Unknown objects can still be tracked and evaluated spatially/temporally.

---

# 25. Environment Intelligence — Core Differentiator

Every camera should have a dynamic environment state.

Example:

```text
CAMERA 07

Lighting     : NIGHT
Visibility   : POOR
Blur         : MEDIUM
Weather hint : RAIN
Terrain      : FOREST
Quality      : 0.43
```

The environment state should influence downstream processing and confidence.

---

# 26. Terrain Model

IBVAP should support camera-level terrain profiles:

```text
FOREST
MOUNTAIN
SNOW
OPEN
URBAN/BUILT
CUSTOM
```

For SIH, terrain should initially be configurable by the operator.

Later it may become automatically inferred by a scene-classification model.

Why operator configuration first?

Because it is easier to validate, explain and deploy within a hackathon while still allowing the product to demonstrate terrain-adaptive behavior.

---

# 27. Weather Model

The product should support environmental states such as:

```text
CLEAR
RAIN
FOG
SNOW
HAZE
UNKNOWN
```

Weather classification may be heuristic or learned.

The product SHALL NOT imply weather classification certainty when the visual evidence does not support it.

---

# 28. Lighting Model

At minimum:

```text
DAY
DUSK
NIGHT
LOW_LIGHT
```

Lighting state SHALL be available to:

- perception;
- event explanation;
- performance evaluation.

---

# 29. Perception Adaptation

IBVAP SHALL support adaptive processing.

Example:

```text
NORMAL
→ direct inference

LOW LIGHT
→ optional enhancement

POOR VISIBILITY
→ conservative confidence handling

HIGH BLUR
→ temporal persistence emphasis
```

The system should avoid running expensive enhancement on every frame by default.

---

# 30. Tracking Experience

The user should see:

```text
Track #17
```

rather than repeated unrelated detections.

A track should expose:

- first seen;
- last seen;
- trajectory;
- current zone;
- object class;
- confidence history;
- event relationships.

---

# 31. Spatial Intelligence

Operators must be able to configure:

## Safe zones

Areas where movement is expected.

## Restricted zones

Areas where entry is noteworthy.

## Patrol zones

Areas associated with authorized activity.

## Virtual fences

Lines or boundaries whose crossing generates a condition for event evaluation.

## Camera-specific expected direction

Optional directional context.

---

# 32. Direction Intelligence

IBVAP should distinguish:

```text
toward monitored/restricted region
away
parallel/lateral
uncertain
```

A movement direction should not be treated as absolute unless the camera's scene geometry has been configured.

---

# 33. Behavioral Intelligence

The first product version should prioritize explainable behavior events.

## Required behavior events

### Loitering

Object remains within a configured region for longer than a threshold with insufficient displacement.

### Persistent approach

Object track demonstrates sustained movement toward a monitored region.

### Boundary crossing

Track crosses a configured virtual fence.

### Repeated approach

Object repeatedly approaches a protected region in a specified time window.

### Unusual stationary presence

Person remains in a sensitive region unusually long.

---

# 34. Event Intelligence

A product event is more than a detection.

Example:

```text
PERSON DETECTED
      +
TRACK PERSISTENT
      +
MOVING TOWARD RESTRICTED ZONE
      +
VIRTUAL FENCE CROSSED
      +
NIGHT / POOR VISIBILITY
      =
HIGH-PRIORITY EVENT
```

This is the core product behavior.

---

# 35. Evidence Fusion

IBVAP should combine multiple evidence streams.

Possible evidence:

```text
object confidence
track persistence
zone violation
direction
dwell time
behavior
environment quality
uniform/civilian result
plate evidence
face evidence
```

The result should be:

```text
event priority
+
reason codes
+
evidence
```

not an opaque number alone.

---

# 36. Risk / Priority Model

The product shall use priority bands such as:

```text
INFO
LOW
MEDIUM
HIGH
CRITICAL
```

The score is a decision-support mechanism.

It is NOT:

- a probability of criminal intent;
- a legal classification;
- a substitute for human judgment.

---

# 37. Alert Design

Bad alert:

```text
🚨 PERSON DETECTED
```

Required alert:

```text
HIGH PRIORITY
Camera 07
Track #31

Event:
Restricted-zone crossing

Environment:
Night / Poor visibility / Forest

Evidence:
Persistent track
Toward restricted region
Fence crossed

Confidence:
Detection: 0.88
Track consistency: High

[OPEN EVIDENCE]
[ACKNOWLEDGE]
[DISMISS]
```

---

# 38. Explainability Requirement

Every HIGH/CRITICAL alert MUST have reason codes.

Examples:

```text
PERSISTENT_TRACK
RESTRICTED_ENTRY
FENCE_CROSSED
TOWARD_RESTRICTED_ZONE
LOITERING
LOW_VISIBILITY
REPEATED_APPROACH
```

An operator should be able to answer:

> "Why did the system alert me?"

within seconds.

---

# 39. Event Evidence

An alert should contain:

- snapshot;
- short video clip;
- event timestamp;
- camera ID;
- track trajectory;
- zone/fence;
- environment state;
- detector confidence;
- event reason codes.

---

# 40. Before/During/After Evidence

The system should retain:

```text
BEFORE
EVENT
AFTER
```

A prototype can use a configurable example such as:

```text
5 sec before
+
event interval
+
5 sec after
```

This is configuration, not a fixed operational requirement.

---

# 41. Operator Workflow

```text
Alert arrives
     ↓
Operator sees priority
     ↓
Reads reason codes
     ↓
Views snapshot/clip
     ↓
Views trajectory + zone
     ↓
Checks live feed
     ↓
Acknowledges / dismisses
     ↓
Optional escalation outside IBVAP
```

IBVAP stops at decision support.

---

# 42. Dashboard Requirements

## Dashboard Home

Show:

- active alerts;
- camera health;
- environment summary;
- event count;
- system latency;
- processing status.

## Camera Grid

Show:

- live feed;
- detection boxes;
- track IDs;
- zone overlays;
- environment label.

## Alert Panel

Show:

- time;
- camera;
- severity;
- event type;
- object type;
- status.

## Incident Detail

Show:

- evidence video;
- snapshot;
- trajectory;
- zone;
- environment;
- reasons;
- confidence;
- acknowledgement state.

## Historical Search

Filter by:

- time;
- camera;
- event;
- severity;
- object;
- terrain;
- weather;
- lighting.

---

# 43. Map / Geographic View

Optional for SIH.

The map should show:

- camera locations;
- current alert locations;
- active event states;
- sector grouping.

It should NOT imply centimeter-level geolocation precision from ordinary monocular CCTV unless such calibration exists.

---

# 44. Camera Onboarding

Administrator workflow:

```text
Add Camera
   ↓
Enter name/ID
   ↓
Enter stream endpoint
   ↓
Test connection
   ↓
Set terrain profile
   ↓
Draw zones
   ↓
Draw virtual fence
   ↓
Set expected direction
   ↓
Activate analytics
```

---

# 45. Event Lifecycle

```text
CREATED
   ↓
OPEN
   ↓
ACKNOWLEDGED
   ↓
RESOLVED / DISMISSED
```

A dismissed event should remain in the audit history.

---

# 46. Camera Lifecycle

```text
DISCOVERED
   ↓
CONFIGURED
   ↓
TESTING
   ↓
ACTIVE
   ↓
DEGRADED / DISCONNECTED
   ↓
RECOVERED
```

---

# 47. Product Functional Requirements

## FR-01 — Camera ingestion

System SHALL support supported IP-camera video streams and replay videos.

## FR-02 — Multi-camera registry

System SHALL maintain camera metadata and health.

## FR-03 — Real-time object detection

System SHALL detect supported object categories in near-real-time according to available compute.

## FR-04 — Multi-object tracking

System SHALL maintain persistent IDs when possible.

## FR-05 — Environment estimation

System SHALL estimate at least lighting, quality and visibility-related state.

## FR-06 — Adaptive processing

System SHALL be able to enable/disable processing strategies based on environment state.

## FR-07 — Zone configuration

Administrator SHALL define camera-specific zones.

## FR-08 — Virtual fence configuration

Administrator SHALL draw/edit virtual boundaries.

## FR-09 — Direction analysis

System SHALL estimate movement direction from track trajectories.

## FR-10 — Event detection

System SHALL identify configured temporal/spatial behaviors.

## FR-11 — Evidence fusion

System SHALL combine multiple event signals.

## FR-12 — Prioritization

System SHALL assign event severity.

## FR-13 — Event explanation

System SHALL generate reason codes.

## FR-14 — Evidence recording

System SHALL associate evidence media with important events.

## FR-15 — Historical event search

User SHALL be able to filter and inspect past events.

## FR-16 — Alert acknowledgement

User SHALL acknowledge/dismiss events according to role permissions.

## FR-17 — Camera failure handling

System SHALL detect stream loss and display camera health.

## FR-18 — Offline operation

Core inference SHALL remain functional without cloud connectivity.

## FR-19 — Audit trail

Configuration and event actions SHALL be logged.

## FR-20 — Model version traceability

Each event SHALL retain model/configuration versions.

---

# 48. Non-Functional Requirements

## Performance

Target near-real-time behavior subject to hardware.

The system SHALL measure:

- end-to-end latency;
- inference latency;
- FPS;
- dropped frames;
- queue depth.

Do not publish performance numbers without benchmarking the final hardware/software stack.

## Reliability

The system SHALL reconnect after transient stream failures.

## Scalability

Architecture SHOULD allow multiple worker processes/instances.

## Security

Secrets must not be hard-coded.

## Maintainability

Models must be replaceable without rewriting business logic.

## Explainability

High-priority events must expose reasons.

## Testability

Event logic must be testable with deterministic replay data.

---

# 49. Product Prioritization

## P0 — Must Have for SIH

- existing CCTV ingestion;
- object detection;
- tracking;
- terrain/camera profile;
- environment state;
- virtual fence;
- direction;
- loitering/persistent approach;
- evidence fusion;
- risk/priority;
- event logging;
- evidence clips;
- dashboard;
- camera health.

## P1 — Strong Additions

- custom uniform/civilian classifier;
- improved low-light enhancement;
- ANPR;
- map;
- richer analytics;
- multi-camera association.

## P2 — Advanced Research

- learned anomaly detection;
- learned terrain classification;
- learned weather classification;
- cross-camera ReID;
- advanced video-language reasoning;
- model adaptation / continual learning.

---

# 50. Product Differentiation

IBVAP SHALL be positioned around:

## 50.1 Environment-aware perception

The product considers environmental quality before trusting vision outputs.

## 50.2 Adaptive processing

The processing pipeline can change based on current conditions.

## 50.3 Event-centric intelligence

The product converts object detections into meaningful events.

## 50.4 Temporal reasoning

Persistent motion patterns matter more than isolated frames.

## 50.5 Spatial reasoning

Zones and boundaries matter.

## 50.6 Evidence fusion

Multiple weak signals combine into stronger event evidence.

## 50.7 Existing-infrastructure retrofit

The product adds intelligence without requiring replacement of every camera.

---

# 51. Competitive Positioning

IBVAP should NOT claim:

```text
"We invented AI surveillance."
```

Instead:

```text
Traditional CCTV
→ passive observation

Basic AI CCTV
→ object detection

IBVAP
→ environment-aware event intelligence
```

The product's differentiation is the **way the signals are combined and presented**, not ownership of the underlying object-detection algorithms.

---

# 52. Terrain Strategy

## Forest

Expected product concerns:

- vegetation;
- occlusion;
- moving foliage;
- low-light scenes;
- animal activity.

IBVAP response:

```text
tracking persistence
+
animal classification
+
restricted zones
+
environment-aware confidence
```

## Mountain

Expected concerns:

- steep perspective;
- distant objects;
- unusual camera viewpoints;
- small apparent object size.

IBVAP response:

```text
camera-specific zones
+
small-object strategy
+
track persistence
+
distance-aware evaluation
```

## Snow

Expected concerns:

- high scene brightness;
- low contrast;
- white backgrounds;
- visual confusion.

IBVAP response:

```text
scene quality estimation
+
contrast-aware preprocessing
+
confidence management
```

## Open terrain

Expected concern:

- distant objects and long visible trajectories.

IBVAP response:

```text
high-resolution inference where available
+
tracking
+
trajectory analysis
```

---

# 53. Weather Strategy

## Rain

Potential issue:
- streaks/noise;
- reflections;
- visibility degradation.

Product behavior:
- environment state = rain/degraded;
- conservative single-frame decisions;
- temporal persistence.

## Fog

Potential issue:
- low contrast;
- distant objects disappear.

Product behavior:
- quality degradation shown;
- adaptive enhancement where beneficial;
- uncertainty preserved.

## Snow

Potential issue:
- brightness and texture changes.

Product behavior:
- environment-aware confidence;
- scene-adapted preprocessing.

## Night

Potential issue:
- low signal;
- high noise;
- distant objects difficult to identify.

Product behavior:
- night classification;
- selective enhancement;
- tracking persistence;
- conservative alerting.

---

# 54. Important Product Truth

The product must differentiate between:

```text
visibility problem
```

and

```text
AI problem
```

If the camera does not contain sufficient information to see an object, IBVAP must be able to report:

```text
INSUFFICIENT VISUAL EVIDENCE
```

This is a product feature, not a failure.

---

# 55. Uniform / Civilian Feature

## Product purpose

Reduce false classification of own personnel as potential intruders.

## Product behavior

```text
person
  ↓
uniform analysis
  ↓
UNIFORM LIKELY
CIVILIAN LIKELY
UNCERTAIN
```

This should be treated as supporting evidence.

The supplied research reports lower accuracy/precision when separating uniformed and non-uniformed human classes because the classes are visually similar. fileciteturn2file9L500-L514

Therefore:

> **Identity/classification uncertainty must remain visible to the operator.**

---

# 56. Face Recognition Product Policy

Face recognition should be:

```text
optional
controlled
auditable
human-reviewed
```

Default:

```text
face detection
```

Optional:

```text
face recognition
```

Never make an identity match the sole reason for a consequential security decision.

---

# 57. ANPR Product Policy

ANPR is a supporting intelligence capability.

Workflow:

```text
vehicle
 ↓
track
 ↓
plate visible?
 ↓
plate detection
 ↓
OCR
 ↓
multiple-frame consistency
 ↓
plate candidate
```

The product should display:

```text
plate text
+
confidence
+
supporting frames
```

rather than treating one OCR frame as authoritative.

---

# 58. Event Search

Operators SHOULD be able to search:

```text
"Show all HIGH events from Camera 07 between
02:00 and 04:00 during low-light conditions."
```

Results:

```text
Event ID
Time
Camera
Type
Severity
Object
Environment
Status
```

---

# 59. Analytics / Reporting

Supervisor view SHOULD include:

- events per camera;
- events per hour;
- environment distribution;
- night vs day performance;
- false-alarm statistics;
- camera uptime;
- average alert latency;
- event response/acknowledgement time.

The purpose is not to produce decorative charts.

The purpose is to answer:

> **Is the system actually making surveillance better?**

---

# 60. Product Success Metrics

## Detection metrics

- precision;
- recall;
- mAP;
- per-class recall.

## Tracking metrics

- IDF1;
- HOTA;
- ID switches.

## Event metrics

- event precision;
- event recall;
- false alarms per camera-hour;
- missed events;
- alert latency.

## Environmental robustness

Compare:

```text
day vs night
clear vs poor visibility
forest vs open
snow vs normal
```

## Operator usefulness

Prototype measures:

- time to notice event;
- time to inspect event;
- acknowledgement time;
- false-alarm dismissal rate.

---

# 61. North-Star Product Metric

Recommended north-star metric:

## **Actionable Event Precision**

Definition:

> Percentage of generated high-priority events that an operator considers genuinely worthy of attention.

Why this metric?

Because the platform exists to reduce monitoring burden and surface meaningful events.

A system that detects everything but generates hundreds of useless alerts has failed the product objective.

---

# 62. Secondary Product Metrics

### False Alert Burden

```text
high-priority false alerts / camera-hour
```

### Mean Alert Latency

```text
event occurrence → operator alert
```

### Evidence Availability

```text
% of alerts with usable evidence
```

### Camera Availability

```text
healthy stream time / total configured time
```

### Event Explanation Coverage

```text
% of high-priority alerts with reason codes
```

### Adaptive Gain

Difference in downstream event performance:

```text
baseline pipeline
vs
adaptive pipeline
```

---

# 63. User Stories

## US-01

As an operator, I want to see only meaningful alerts so that I do not need to continuously watch every camera.

## US-02

As an operator, I want to see why an alert was generated so that I can verify it quickly.

## US-03

As an operator, I want to inspect the event video and trajectory so that I have context.

## US-04

As an operator, I want animal movement to be distinguishable from human movement so that false alarms are reduced.

## US-05

As an operator, I want lateral movement to be distinguished from movement toward a restricted zone.

## US-06

As a supervisor, I want events grouped by camera and time so that I can understand patterns.

## US-07

As an administrator, I want to configure zones per camera because every camera has a different viewpoint.

## US-08

As an administrator, I want to see camera health so that silent camera failures do not go unnoticed.

## US-09

As a supervisor, I want performance broken down by terrain/weather/lighting so that I know where the system is reliable.

## US-10

As a system owner, I want the software to keep operating locally during connectivity loss.

---

# 64. Example End-to-End Scenarios

## Scenario A — Normal movement

```text
Person detected
→ Track established
→ Normal region
→ No restricted-zone interaction
→ No alert
```

## Scenario B — Animal movement

```text
Animal detected
→ Track established
→ Crosses monitored region
→ Animal context recognized
→ No high-priority human intrusion event
```

## Scenario C — Lateral movement

```text
Person detected
→ Persistent track
→ Movement parallel to boundary
→ No restricted-zone crossing
→ No high-priority intrusion event
```

The supplied border research also uses a distinction between lateral movement and movement relevant to the border direction. fileciteturn2file6L347-L359

## Scenario D — Intrusion

```text
Person detected
→ Persistent track
→ Direction toward restricted region
→ Virtual fence crossed
→ Evidence fused
→ HIGH event
→ Evidence clip generated
```

## Scenario E — Night

```text
Low-light scene
→ Environment state updated
→ Selective enhancement
→ Person detected
→ Tracking persists
→ Event reasoning continues
```

## Scenario F — Uncertain visibility

```text
Poor visibility
→ weak detection
→ no persistent track
→ uncertainty retained
→ no high-priority alert
```

---

# 65. Product States

## Camera states

```text
ONLINE
DEGRADED
DISCONNECTED
ERROR
```

## Environment states

```text
NORMAL
LOW_LIGHT
POOR_VISIBILITY
RAIN
FOG
SNOW
UNKNOWN
```

## Object states

```text
DETECTED
TRACKED
LOST
```

## Event states

```text
CREATED
OPEN
ACKNOWLEDGED
DISMISSED
RESOLVED
```

---

# 66. Accessibility and Operator UX Principles

The interface SHOULD:

- prioritize information hierarchy;
- avoid alert flooding;
- make important events visually prominent;
- avoid excessive animation;
- display uncertainty explicitly;
- allow rapid keyboard/mouse acknowledgement;
- minimize clicks from alert to evidence;
- maintain consistent terminology.

The dashboard should feel like an **operations tool**, not an AI demo.

---

# 67. Trust UX

The interface should make it easy to understand:

```text
WHAT
WHERE
WHEN
WHY
HOW CERTAIN
WHAT EVIDENCE
```

An operator should not need to inspect model internals.

---

# 68. Security Product Requirements

## Authentication

Required.

## Roles

At minimum:

```text
ADMIN
OPERATOR
VIEWER
AUDITOR
```

## Audit

Log:

- login;
- camera modifications;
- zone/fence modifications;
- model changes;
- alert acknowledgement;
- event dismissal;
- access to sensitive evidence.

## Secrets

Camera credentials SHALL NOT be embedded in source code.

---

# 69. Data Governance

The system should distinguish:

```text
raw video
event evidence
object metadata
biometric data
system logs
```

Retention should be separately configurable.

Biometric data should have stricter access controls than ordinary event metadata.

The supplied research identifies privacy, data protection and accountability as material concerns for AI surveillance, including risk of overreach and mission creep. fileciteturn2file3L239-L262

---

# 70. Product Architecture Principles

## Modular

Each major analytic capability can be replaced.

## Local-first

Inference does not require the cloud.

## Evidence-first

Events retain supporting evidence.

## Explainable

Alerts contain reason codes.

## Configurable

Camera geometry and thresholds are camera-specific.

## Measurable

Every major stage reports performance.

---

# 71. MVP Definition

The MVP is complete when the following loop works:

```text
Existing CCTV / replay video
        ↓
Environment estimate
        ↓
Person/vehicle/animal detection
        ↓
Tracking
        ↓
Virtual fence
        ↓
Direction
        ↓
Loitering / persistent approach
        ↓
Evidence fusion
        ↓
Risk level
        ↓
Alert
        ↓
Evidence clip
        ↓
Dashboard
```

The system does NOT need face recognition, ANPR and advanced anomaly learning to prove the core product.

---

# 72. SIH Demo Definition

The demo should prove five things:

### 1. Existing infrastructure

Show a normal CCTV/replay stream entering the platform.

### 2. Basic intelligence

Show person/vehicle/animal detection and tracking.

### 3. Environmental adaptation

Show the same pipeline operating under low-light/degraded conditions.

### 4. Contextual intelligence

Show lateral movement being treated differently from restricted-zone crossing.

### 5. Evidence fusion

Show multiple weak signals becoming one high-priority event.

---

# 73. Product Demo Story

Start with:

> "A conventional CCTV system records everything but asks the operator to find the important moment."

Then:

```text
Camera feed
→ person appears
→ track created
→ movement monitored
→ environment classified
→ zone relationship evaluated
→ trajectory analyzed
→ evidence fused
→ high-priority event generated
```

Then show:

```text
WHY:
Persistent person track
+
toward restricted zone
+
fence crossed
+
low-light scene
```

This demonstrates the product thesis better than a model-accuracy slideshow.

---

# 74. Rollout Strategy

## Stage 1 — Prototype

1–4 cameras.

Single local inference server.

## Stage 2 — Pilot

10–25 cameras.

Central event store.

Camera health monitoring.

Model versioning.

## Stage 3 — Multi-site deployment

Multiple local inference nodes.

Central event/management layer.

Store-and-forward synchronization.

## Stage 4 — Enterprise / government deployment

- hardened security;
- policy-based retention;
- stronger authentication;
- formal model validation;
- procurement-grade documentation;
- controlled biometric workflows;
- integration with approved command/control systems.

---

# 75. Product Dependencies

Core dependencies:

- IP cameras or replay video;
- local compute;
- GPU optional but recommended for multi-camera performance;
- network path to camera;
- configured zones/fences;
- trained/pretrained models.

Optional dependencies:

- OCR;
- face models;
- vector database;
- GIS;
- event bus.

---

# 76. Product Risks

## R1 — False alarms

### Cause

Poor visibility, animals, foliage, noise, camera artifacts.

### Mitigation

Temporal persistence + contextual fusion + environment-aware confidence.

## R2 — Missed detections

### Cause

Tiny objects, extreme occlusion, no visual signal.

### Mitigation

Small-object strategy + tracking + explicit uncertainty.

## R3 — Domain shift

### Cause

Training data does not represent deployment environment.

### Mitigation

Custom evaluation dataset + condition matrix + fine-tuning.

## R4 — Compute cost

### Cause

Many high-resolution streams.

### Mitigation

Frame sampling + lightweight models + batching + scalable workers.

## R5 — Network instability

### Cause

Remote deployment.

### Mitigation

Local inference + reconnect + store-and-forward.

## R6 — Model confidence misuse

### Cause

Treating detector confidence as threat probability.

### Mitigation

Separate detection confidence from event/risk score.

## R7 — Biometric risk

### Cause

Face recognition errors or misuse.

### Mitigation

Optional module + strict governance + human review.

## R8 — Licensing

### Cause

Model/software restrictions.

### Mitigation

Maintain license registry for every dependency/model version.

---

# 77. Product Decisions — Locked

## Decision 1

IBVAP is an intelligence layer, not a camera replacement.

## Decision 2

The core novelty is environment-adaptive event intelligence.

## Decision 3

Detector output is evidence, not a threat verdict.

## Decision 4

Tracking is mandatory for meaningful behavior analysis.

## Decision 5

Zones are camera-specific.

## Decision 6

Uncertainty is a first-class state.

## Decision 7

Face recognition and ANPR are supporting modules, not the core product.

## Decision 8

The product is local-first.

## Decision 9

Every high-priority alert must be explainable.

## Decision 10

Measured false-alarm reduction is more important than adding more AI models.

---

# 78. Product Roadmap

## Release 0 — Technical Proof

```text
camera
→ detector
→ tracker
→ live boxes
```

## Release 1 — Intelligent MVP

```text
environment
→ detection
→ tracking
→ zones
→ virtual fence
→ direction
→ behavior
→ risk
→ alerts
```

## Release 2 — Operational Prototype

Add:

- event search;
- evidence clips;
- custom uniform classifier;
- camera health;
- offline recovery;
- metrics.

## Release 3 — Extended Intelligence

Add:

- ANPR;
- face detection/controlled recognition;
- learned anomaly detection;
- improved environmental classifiers;
- cross-camera association.

## Release 4 — Pilot Hardening

Add:

- multi-node deployment;
- secure deployment;
- centralized management;
- model registry;
- policy-based retention;
- observability;
- formal validation.

---

# 79. Product Acceptance Criteria

The SIH prototype is accepted when:

1. A standard CCTV/replay stream can be added.
2. The camera can be monitored live.
3. Person/vehicle/animal detection works.
4. Objects receive tracking IDs.
5. A virtual fence can be drawn.
6. Direction can be estimated.
7. Lateral movement can be distinguished from configured protected-direction movement.
8. At least one behavioral event can be generated.
9. The environment state is visible.
10. The pipeline can change behavior under low-light conditions.
11. Event evidence is stored.
12. An alert contains reasons.
13. The operator can acknowledge/dismiss an alert.
14. Events can be searched historically.
15. Camera disconnection is surfaced.
16. The system can run locally without cloud dependency.
17. At least three environmental scenarios can be demonstrated.
18. Performance metrics are measured rather than guessed.

---

# 80. Recommended Product KPIs for the SIH Presentation

Show these numbers:

```text
Detection recall
Tracking IDF1/HOTA
High-priority event precision
False alarms / camera-hour
Median alert latency
Evidence availability %
Camera stream uptime
Night vs daytime performance
Adaptive vs baseline comparison
```

If only one comparison is possible, prioritize:

```text
BASELINE
Detector + tracker + simple rule

vs

IBVAP
Environment + detector + tracker + spatial +
temporal reasoning + evidence fusion
```

Then demonstrate whether the second pipeline reduces false alarms or improves event detection.

---

# 81. Final Product Positioning

### One-line description

> **IBVAP is a software-defined, environment-adaptive border video intelligence platform that transforms existing CCTV feeds into explainable, context-aware security events.**

### Product promise

> **Watch less. Understand more.**

### Technical promise

> **Adapt perception to the environment, track continuously, reason over space and time, and alert only when multiple pieces of evidence justify operator attention.**

### Strategic promise

> **Improve the value of existing CCTV infrastructure without requiring every camera to become a specialized smart camera.**

---

# 82. Relationship to the Research Baseline

The supplied Digital Border Surveillance research already establishes a relevant baseline around:

- object detection;
- movement detection;
- uniformed vs non-uniformed people;
- animals;
- alarms;
- video storage;
- control-room monitoring.

It also identifies difficult terrain and adverse weather as practical surveillance problems. fileciteturn2file0L22-L45

The same paper explicitly describes a low-level → tracking → behavior/activity → alarm/control architecture and indicates future scope for real-time tracking, behavior analysis and multimodal extension. fileciteturn2file6L363-L403 fileciteturn2file5L288-L300

IBVAP's product direction is therefore:

```text
Existing research baseline
        ↓
Better environmental awareness
        ↓
Better temporal/spatial reasoning
        ↓
Evidence fusion
        ↓
Better operator-focused event intelligence
```

---

# 83. What IBVAP Is Really Building

At the surface:

```text
AI video surveillance
```

Underneath:

```text
A context engine for CCTV
```

The product is ultimately trying to transform:

```text
Raw pixels
```

into:

```text
Context
```

and then:

```text
Context
+
persistent evidence
```

into:

```text
Actionable event
```

That is the product.

---

# 84. Product North Star

```text
RAW CCTV
   ↓
"What is visible?"
   ↓
"What is moving?"
   ↓
"Where is it moving?"
   ↓
"How is it behaving?"
   ↓
"What environmental conditions exist?"
   ↓
"How trustworthy is the evidence?"
   ↓
"Do multiple signals agree?"
   ↓
"Does the operator need to know?"
```

The ideal final output is not:

> **"AI detected a person."**

It is:

> **"A persistent person track has entered a configured restricted zone under low-visibility conditions; multiple independent signals support a high-priority event, with evidence attached for operator verification."**

That is the product IBVAP should become.
