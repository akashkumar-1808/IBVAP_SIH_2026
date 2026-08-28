# IBVAP — Rules.md
## Agent Safety, Quality, Scope & Anti-Degradation Rules

**Document status:** NON-NEGOTIABLE project guardrails  
**Applies to:** Antigravity and any coding/engineering agent modifying the IBVAP repository  
**Priority:** These rules take precedence over convenience, speed, novelty, or speculative improvements.

---

# 0. PRIMARY DIRECTIVE

IBVAP is a **software-only intelligent video analytics platform operating on existing IP CCTV infrastructure**.

The agent's job is to make the project:

- more correct;
- more reliable;
- more explainable;
- more maintainable;
- more demonstrable;
- more faithful to the approved architecture.

The agent must **never degrade a working system merely to make it appear more advanced**.

---

# 1. SOURCE-OF-TRUTH ORDER

When making an implementation decision, use this priority order:

```text
1. Explicit user-approved requirement
2. Approved IBVAP Product Requirements Document
3. Approved IBVAP Architecture document
4. Approved Technical Requirements document
5. Existing working code and tests
6. Verified dependency/model documentation
7. General engineering judgment
8. Speculation
```

**Never use speculation when a requirement, architecture decision, test, or verified source already exists.**

If two project documents appear to conflict:

```text
STOP
↓
identify the conflict
↓
do not silently choose
↓
record it in docs/DECISIONS.md
↓
use the least-destructive interpretation
```

---

# 2. ABSOLUTE ANTI-HALLUCINATION RULE

The agent MUST NOT invent:

- AI models;
- datasets;
- camera capabilities;
- sensor inputs;
- API endpoints;
- environmental classes;
- event types;
- hardware;
- benchmark numbers;
- accuracy figures;
- licenses;
- deployment capabilities;
- security capabilities;
- integrations;
- government/defense integrations;
- operational facts.

If something is unknown:

```text
UNKNOWN
```

or:

```text
NOT IMPLEMENTED
```

or:

```text
REQUIRES VERIFICATION
```

Do not fill the gap with a plausible-looking answer.

---

# 3. NO NEW PHYSICAL SENSORS

The core IBVAP project is:

```text
EXISTING IP CCTV
        ↓
SOFTWARE ANALYTICS
```

The core system MUST NOT require:

- PIR;
- ultrasonic;
- LiDAR;
- radar;
- seismic sensors;
- thermal cameras;
- external IR sensors;
- Bluetooth sensing;
- drones;
- external sensor fields.

These may exist in research literature or future extension concepts, but they are **not dependencies of the approved prototype**.

If an agent believes an external sensor is necessary:

```text
DO NOT ADD IT
↓
record the limitation
↓
propose the option in DECISIONS.md
```

---

# 4. DO NOT TURN IBVAP INTO A GENERIC CCTV PROJECT

The project is not merely:

```text
camera
→ YOLO
→ bounding boxes
→ dashboard
```

The approved identity is:

```text
environment
→ adaptive perception
→ detection
→ tracking
→ spatial reasoning
→ temporal/behavior reasoning
→ evidence fusion
→ explainable event
→ operator alert
```

Any change that makes the system effectively equivalent to a generic object-detection dashboard is a **project degradation**.

---

# 5. DO NOT ADD FEATURES JUST TO INCREASE FEATURE COUNT

Never add a feature because:

- another team has it;
- it sounds impressive;
- it uses a new AI model;
- it looks good in a screenshot;
- an LLM suggested it;
- it increases the number of bullets in the pitch.

Every new feature MUST answer:

```text
What requirement does it satisfy?
What user problem does it solve?
What architecture layer does it belong to?
How will it be tested?
What does it cost in latency/complexity?
```

If these cannot be answered:

```text
DO NOT ADD IT
```

---

# 6. CORE PIPELINE MUST NEVER BE BROKEN FOR OPTIONAL FEATURES

Core modules:

```text
video ingestion
environment
detection
tracking
spatial
behavior
fusion
events
evidence
API
dashboard
```

Optional modules:

```text
uniform classification
ANPR
face recognition
advanced anomaly model
learned terrain classifier
advanced enhancement
```

If an optional module fails:

```text
optional module fails
        ↓
log failure
        ↓
mark module unavailable
        ↓
continue core pipeline
```

Never let:

```text
ANPR failure
```

crash:

```text
person detection
tracking
intrusion detection
```

---

# 7. NO MONOLITHIC MODEL DEPENDENCY

Do not make one model responsible for everything.

Avoid:

```text
one giant model
→ person
→ vehicle
→ uniform
→ behavior
→ threat
→ identity
```

Use modular reasoning:

```text
detector
   ↓
tracker
   ↓
spatial
   ↓
behavior
   ↓
optional intelligence
   ↓
fusion
```

This keeps the system replaceable and testable.

---

# 8. DO NOT TRAIN FROM SCRATCH WITHOUT EXPLICIT APPROVAL

The default strategy is:

```text
pretrained model
+
transfer learning where necessary
+
custom domain data
```

Do NOT:

```text
random weights
→ large training project
```

unless a specific research requirement justifies it and the decision is documented.

The SIH prototype is constrained by time and compute.

---

# 9. DO NOT OVERFIT TO THE DEMO

The agent MUST NOT optimize only for one curated video.

Forbidden behavior:

```text
hard-code camera position
hard-code object path
hard-code event timestamp
hard-code detection result
```

The system must work from configuration and actual input.

Demo scenarios may be curated, but the logic itself cannot be fake.

---

# 10. NO FAKE AI OUTPUTS

Do not hard-code:

```text
person confidence = 0.98
risk = HIGH
```

unless those values are genuinely produced by the corresponding module.

Do not fabricate:

- confidence;
- detections;
- identity matches;
- plate text;
- weather state;
- terrain state;
- anomaly score.

If a demo needs a mock:

```text
MOCK
```

must be explicit in code/config/UI and isolated from the real pipeline.

---

# 11. NO FAKE PERFORMANCE METRICS

Never invent:

- FPS;
- mAP;
- precision;
- recall;
- IDF1;
- HOTA;
- latency;
- false alarms/hour;
- accuracy;
- GPU utilization.

Every displayed benchmark must come from:

```text
actual test run
+
recorded hardware
+
recorded software/model versions
```

If no measurement exists:

```text
NOT MEASURED
```

---

# 12. DO NOT CONFUSE DETECTION CONFIDENCE WITH THREAT CONFIDENCE

This is one of the most important rules.

A detector output:

```text
person = 0.91
```

means:

> the detector is confident the region resembles a person.

It does NOT mean:

```text
91% threat probability
```

The system must maintain separate concepts:

```text
detection confidence
track consistency
environment quality
behavior evidence
event score/priority
```

---

# 13. HIGH-PRIORITY ALERTS MUST NOT COME FROM ONE RAW FRAME

Forbidden:

```python
if person_detected:
    high_alert()
```

Required direction:

```text
detection
+
persistent track
+
spatial/temporal evidence
+
context
+
fusion
→
event priority
```

Single-frame observations may create:

```text
INFO
LOW
UNCERTAIN
```

depending on configured logic.

---

# 14. UNCERTAINTY IS A VALID RESULT

The system MUST be allowed to say:

```text
UNCERTAIN
LOW_VISUAL_QUALITY
INSUFFICIENT_VISUAL_EVIDENCE
UNKNOWN_OBJECT
MODULE_UNAVAILABLE
```

Never force:

```text
not uniform → civilian
```

or:

```text
poor frame → person
```

or:

```text
failed OCR → invented plate
```

---

# 15. NEVER CLAIM SOFTWARE CREATES INFORMATION THAT IS NOT PRESENT

Software can improve processing.

It cannot guarantee recovery of information that the camera did not capture.

Do not claim:

```text
100% night visibility
```

or:

```text
reliable identification from a fully invisible object
```

or:

```text
guaranteed detection through dense fog
```

The system must reflect degraded visual quality.

---

# 16. ENVIRONMENT ADAPTATION MUST BE REAL

If the architecture claims:

```text
day/night/weather-aware processing
```

then the implementation must contain an actual environment state.

At minimum:

```text
lighting
quality
visibility
```

Optional:

```text
weather hint
terrain profile
blur
contrast
noise
```

Do not merely put "AI adaptive" in the UI without an actual state or processing consequence.

---

# 17. DO NOT RUN EXPENSIVE PROCESSING UNCONDITIONALLY

Heavy enhancement models must not automatically run on every frame.

Use:

```text
environment state
↓
decision
↓
optional expensive processing
```

Reason:

```text
latency
compute
throughput
stability
```

A feature that theoretically improves image quality but destroys real-time performance is not automatically an improvement.

---

# 18. CAMERA-SPECIFIC GEOMETRY IS MANDATORY

Never hard-code a global assumption that:

```text
right side of image = border
```

or:

```text
upward movement = intrusion
```

Every camera may have different perspective.

Use configurable:

```text
zones
fences
expected direction
terrain profile
```

---

# 19. VIRTUAL FENCE MUST USE TRAJECTORY LOGIC

Avoid:

```text
bbox overlaps line
→ intrusion
```

Instead use:

```text
previous track position
+
current track position
→
line crossing test
```

This prevents persistent overlap from being interpreted as repeated crossings.

---

# 20. DO NOT CALL LATERAL MOVEMENT AN INTRUSION BY DEFAULT

The approved architecture distinguishes movement direction.

Example:

```text
person
→ moves parallel to configured boundary
→ no fence crossing
→ no restricted entry
→ no automatic HIGH intrusion
```

Direction is context, not a standalone threat verdict.

---

# 21. TRACKING MUST BE ACTUAL TRACKING

Do not create a fake:

```text
Track #17
```

that simply increments every frame.

A tracking module must maintain state over time.

Track should contain at least:

```text
track_id
camera_id
class
bbox
position
timestamp
trajectory
last_seen
confidence history
```

---

# 22. DO NOT USE TRACK IDS AS IDENTITY

Important distinction:

```text
Track ID #31
```

means:

> this is the same tracked object according to the tracker.

It does NOT mean:

```text
this is the same real-world person
```

unless a validated identity/ReID system exists.

---

# 23. DO NOT OVERCLAIM CROSS-CAMERA REIDENTIFICATION

If cross-camera ReID is not implemented and validated:

Do not write:

```text
Person #31 moved from Camera A to Camera B
```

Write:

```text
possible visual association
```

only when an actual association module exists.

---

# 24. UNIFORM CLASSIFICATION MUST NOT BECOME A SAFETY BYPASS

The approved conceptual states are:

```text
UNIFORM
CIVILIAN
UNCERTAIN
```

Do not make:

```text
UNIFORM → SAFE
```

or:

```text
CIVILIAN → THREAT
```

as unconditional rules.

Uniform analysis is supporting evidence.

---

# 25. ANIMAL DETECTION IS CONTEXT, NOT AUTOMATIC THREAT

The project includes animals partly to reduce false alarms.

Expected behavior:

```text
animal detected
→ track
→ contextual event if useful
→ no automatic HIGH human intrusion merely because animal moved
```

---

# 26. FACE RECOGNITION MUST REMAIN OPTIONAL

Face Recognition:

```text
OPTIONAL
CONTROLLED
AUDITABLE
```

Default prototype behavior should favor:

```text
face detection
```

over forcing identity recognition.

Never fabricate a face match.

Never display:

```text
IDENTIFIED: Person X
```

without an actual enabled recognition pipeline and valid evidence.

---

# 27. ANPR MUST BE TEMPORALLY CONSISTENT

Do not trust a single OCR frame if multiple frames exist.

Preferred:

```text
frame 1
frame 2
frame 3
frame 4
   ↓
temporal aggregation
   ↓
plate candidate
```

If the result is inconsistent:

```text
PLATE UNCERTAIN
```

not a fabricated clean plate.

---

# 28. EVENT REASONS ARE MANDATORY

Every HIGH/CRITICAL event must explain itself.

Example:

```text
PERSISTENT_TRACK
TOWARD_RESTRICTED_ZONE
FENCE_CROSSED
```

Do not produce:

```text
HIGH ALERT
```

with no explanation.

---

# 29. NEVER HIDE MODEL FAILURE

Bad:

```text
model failed
→ continue showing last prediction as if current
```

Required:

```text
model unavailable
```

or:

```text
stale inference
```

with appropriate UI/system status.

---

# 30. STALE DATA MUST NEVER LOOK LIVE

A disconnected or frozen camera must not continue showing apparently live intelligence.

The UI must distinguish:

```text
LIVE
STALE
DISCONNECTED
ERROR
```

A last-known frame may be displayed, but it must be clearly marked.

---

# 31. NO UNBOUNDED VIDEO QUEUES

A queue that grows indefinitely creates stale alerts.

Required:

```text
bounded queue
```

Prefer freshness.

If overloaded:

```text
drop stale waiting frames
```

rather than allowing multi-second or multi-minute latency.

---

# 32. DO NOT LOAD MODELS PER FRAME

Models should be:

```text
load
→ warm up
→ reuse
```

not:

```text
frame
→ load model
→ infer
→ unload
```

That is unacceptable for a real-time video pipeline.

---

# 33. DO NOT LET FRONTEND CONTROL AI LOGIC

Frontend:

```text
display
configuration UI
user interaction
```

Backend:

```text
API
authentication
configuration
persistence
```

Worker:

```text
continuous video analytics
```

Do not implement core event decisions in React components.

---

# 34. DO NOT PUT CONTINUOUS VIDEO IN NORMAL REST REQUESTS

Avoid:

```text
POST /infer
```

for every CCTV frame.

Continuous processing belongs in the worker.

Use:

```text
worker → backend event/message
```

for event publication.

---

# 35. DATABASE IS NOT VIDEO STORAGE

Do not store MP4 evidence as giant database blobs in the prototype.

Use:

```text
database → metadata
filesystem/object storage → media
```

Database records should reference evidence paths/IDs.

---

# 36. DO NOT EXPOSE RTSP CREDENTIALS TO FRONTEND

Never place:

```text
rtsp://username:password@...
```

in:

- React code;
- browser state;
- committed config;
- Git repository;
- screenshots;
- logs.

Use protected backend/worker configuration.

---

# 37. DO NOT COMMIT SECRETS

Never commit:

```text
API keys
passwords
RTSP credentials
JWT secrets
private keys
cloud secrets
watchlist secrets
```

Use environment variables or secret storage.

---

# 38. DO NOT LOG SENSITIVE DATA CARELESSLY

Do not print:

```text
camera password
face embeddings
raw watchlists
full private URLs
```

into normal logs.

---

# 39. DO NOT CHANGE THE API CONTRACT CASUALLY

Before changing an API field:

```text
search all consumers
→ frontend
→ worker
→ tests
→ docs
```

If breaking:

```text
version schema
or
update all consumers atomically
```

Do not silently change:

```json
"confidence"
```

from:

```text
0.0–1.0
```

to:

```text
0–100
```

without updating contracts.

---

# 40. SCHEMA VERSIONING

Version message contracts:

```text
schema_version: "1.0"
```

If fields change materially:

```text
increment schema version
```

---

# 41. MODEL VERSIONING IS REQUIRED

Every important event must be traceable to:

```text
detector version
tracker version
environment version
optional model versions
configuration version
```

Never silently replace model files.

---

# 42. DO NOT CHANGE MODEL WITHOUT VALIDATION

Any model replacement MUST be evaluated against:

```text
baseline test set
```

at minimum.

Compare:

```text
precision
recall
latency
memory
false alarms
event performance
```

If the new model is faster but significantly worse in relevant conditions, do not blindly adopt it.

---

# 43. LICENSES MUST BE CHECKED

Do not add an open-source dependency without checking:

```text
license
version
model-weight terms
redistribution terms
commercial restrictions
```

Code license and model-weight license are not automatically identical.

Record significant licensing decisions in:

```text
docs/DECISIONS.md
```

or:

```text
docs/LICENSES.md
```

---

# 44. DO NOT ADD DEPENDENCIES WITHOUT NEED

Every dependency increases:

```text
failure surface
security surface
build time
license complexity
maintenance
```

Before adding one:

```text
Can existing code solve this?
Can standard library solve this?
Is the dependency actually required?
```

If not:

```text
do not add it
```

---

# 45. DO NOT REPLACE A WORKING LIBRARY BECAUSE A NEW ONE IS TRENDING

Do not migrate:

```text
working tracker
→ newest tracker
```

or:

```text
working detector
→ new model
```

just because it is newer.

Replacement requires:

```text
measured benefit
+
compatibility
+
license review
+
test coverage
```

---

# 46. DON'T USE LLM/VISION-LANGUAGE MODELS AS A SUBSTITUTE FOR BASIC ENGINEERING

Do not add a large multimodal model to interpret:

```text
person crossed a line
```

when simple geometry is sufficient.

Use the simplest correct method.

Example:

```text
virtual fence → geometry
direction → vector math
loitering → trajectory + dwell time
```

Advanced AI is for problems that actually need it.

---

# 47. DO NOT BUILD MICRO-SERVICES FOR THE SAKE OF LOOKING ENTERPRISE-GRADE

The SIH prototype is intended to run initially on one machine.

Do not introduce:

```text
Kubernetes
Kafka
service mesh
10 independent services
cloud-only orchestration
```

without an actual requirement.

Preferred:

```text
frontend
backend
AI worker
database
```

with modular code.

---

# 48. DON'T BUILD CLOUD DEPENDENCY INTO THE CORE

The core inference path must work locally.

Bad:

```text
camera
→ internet
→ cloud AI
→ dashboard
```

Preferred:

```text
camera
→ local worker
→ local events
→ local dashboard
```

Cloud/central synchronization is a future extension.

---

# 49. INTERNET LOSS MUST NOT DESTROY CORE ANALYTICS

When internet connectivity is lost:

```text
local inference → continue
local events → continue
local evidence → continue
local dashboard → continue on local network
central sync → pause
```

---

# 50. CONFIGURATION OVER HARDCODING

Do not hard-code:

```text
camera ID
zone polygon
fence line
threshold
RTSP URL
event threshold
model path
evidence duration
```

Use configuration.

---

# 51. DO NOT MODIFY PRODUCTION-LIKE CONFIG FOR ONE DEMO

If a demo needs special conditions:

```text
configs/demo/
```

or an explicit demo profile.

Do not permanently contaminate default configuration.

---

# 52. ENVIRONMENT STATE MUST BE TESTABLE

Environment functions should accept deterministic input.

Example:

```text
image
→ environment analyzer
→ EnvironmentState
```

Unit tests should validate:

```text
obviously dark image → low-light classification
```

within the limits of the chosen method.

Do not write tests that only assert:

```text
function does not crash
```

when an actual output can be checked.

---

# 53. BEHAVIOR RULES MUST BE DETERMINISTIC WHERE POSSIBLE

Rules such as:

```text
line crossing
dwell time
direction
zone membership
```

should be deterministic.

Avoid unnecessary model dependence for simple geometry/temporal logic.

This improves:

```text
explainability
testing
latency
reliability
```

---

# 54. DO NOT CALL RULES "AI" IF THEY ARE RULES

Correct:

```text
trajectory-based rule
```

Incorrect:

```text
deep AI behavioral intelligence
```

unless a learned model actually performs the behavior inference.

---

# 55. DO NOT CALL HEURISTICS "PROBABILITY"

If the risk engine produces:

```text
score = 72
```

do not display:

```text
72% probability of threat
```

Display:

```text
Risk priority: HIGH
```

or:

```text
Evidence score: 72/100
```

---

# 56. RISK SCORE MUST REMAIN CONFIGURABLE

Do not scatter weights throughout source code.

Use:

```text
configuration
```

and document:

```text
these weights are prototype heuristics
```

---

# 57. DO NOT LET A RISK SCORE OVERRIDE RAW EVIDENCE

The UI should show:

```text
Risk: HIGH

Reasons:
fence crossed
persistent track
toward restricted zone

Environment:
night / poor visibility
```

A score without evidence is not sufficient.

---

# 58. EVERY IMPORTANT EVENT MUST HAVE EVIDENCE

For HIGH/CRITICAL:

```text
snapshot
+
event clip where possible
+
trajectory
+
reason codes
```

If media capture fails:

```text
EVIDENCE_CAPTURE_ERROR
```

must be recorded.

Do not claim evidence exists when it doesn't.

---

# 59. EVIDENCE MUST BE TIME-CONSISTENT

Event clip timestamps must align with the event.

Do not save arbitrary unrelated video and attach it to an event.

---

# 60. NO EVENT DUPLICATION FLOOD

A single prolonged event should not generate:

```text
500 alerts
```

simply because it remains in the restricted region.

Use event lifecycle/state:

```text
candidate
→ created
→ active
→ acknowledged/resolved
```

and configurable cooldown/deduplication.

---

# 61. NO ALERT STORM

If an environmental issue causes massive detections:

```text
do not fire thousands of alerts
```

Use:

```text
aggregation
cooldown
event deduplication
environment degradation state
```

and show system health.

---

# 62. FALSE-ALARM REDUCTION IS A FIRST-CLASS OBJECTIVE

Do not optimize solely for:

```text
recall
```

The product exists partly to reduce operator burden.

Measure:

```text
false alarms / camera-hour
```

and:

```text
actionable event precision
```

where possible.

---

# 63. TEST NEGATIVE CASES, NOT JUST POSITIVE CASES

At minimum test:

```text
animal movement
lateral human movement
short-lived detection
poor visibility
camera disconnect
no zone crossing
no persistent track
failed optional module
```

A system that only works when the expected event happens is not robust.

---

# 64. TEST THE ABSENCE OF ALERTS

Some of the most important tests are:

```text
NO HIGH ALERT expected
```

Examples:

```text
animal crosses normal area
person moves parallel to fence
uncertain detection disappears
camera is disconnected
```

---

# 65. REPLAY TESTS ARE REQUIRED FOR CORE CHANGES

Before changing:

```text
detector
tracker
environment
behavior
fusion
```

run the relevant replay tests.

Do not rely only on visual inspection.

---

# 66. DO NOT LEAK TRAINING/TEST DATA

Do not randomly split adjacent video frames into train and test if they come from the same sequence.

Prefer:

```text
scene/video-level separation
```

for meaningful evaluation.

---

# 67. DATASET QUALITY OVER DATASET SIZE

Do not collect thousands of almost identical images merely to inflate dataset size.

Prioritize:

```text
terrain diversity
weather diversity
lighting diversity
distance
occlusion
pose
camera angle
background
```

---

# 68. DO NOT ASSUME PUBLIC DATASETS ARE BORDER DATASETS

COCO, CrowdHuman, VisDrone, VIRAT, MOT, etc. may support components of the system.

They do not automatically represent:

```text
Indian border CCTV
```

Do not claim they do.

---

# 69. CUSTOM UNIFORM DATA MUST BE HANDLED CAREFULLY

Uniform/civilian classification is known to be visually difficult.

Do not interpret:

```text
uniform confidence = high
```

as:

```text
authorized person = guaranteed
```

Use:

```text
uniform likely
```

as supporting evidence.

---

# 70. ENVIRONMENT ADAPTATION MUST NOT BE ONLY COSMETIC

Bad:

```text
UI says "NIGHT MODE"
```

while the processing is unchanged.

A meaningful adaptation must modify something measurable:

```text
preprocessing
frame strategy
confidence handling
model selection
resolution
```

---

# 71. DO NOT CLAIM WEATHER DETECTION WITHOUT A METHOD

If rain/fog/snow is not actually detected:

Do not show:

```text
RAIN DETECTED
```

Instead:

```text
WEATHER HINT: UNKNOWN
```

or only show supported environment properties.

---

# 72. TERRAIN SHOULD BE CONFIGURABLE BEFORE IT IS AUTOMATIC

For the SIH prototype:

```text
camera → configured terrain profile
```

is acceptable.

Do not pretend automatic terrain classification exists unless implemented.

---

# 73. NO HIDDEN FALLBACKS

If:

```text
RF-DETR fails
```

do not silently switch to:

```text
random YOLO model
```

without reporting it.

Fallbacks must be explicit and documented.

---

# 74. ERROR MESSAGES MUST BE ACTIONABLE

Bad:

```text
Something went wrong.
```

Better:

```text
Camera CAM07:
RTSP connection timed out after 10s.
Retrying in 5s.
```

Bad:

```text
Model error.
```

Better:

```text
Detector failed to load:
models/detector/model.onnx
Reason: file not found.
```

---

# 75. DO NOT SWALLOW EXCEPTIONS

Avoid:

```python
try:
    ...
except:
    pass
```

for core components.

Failures must be logged and surfaced.

---

# 76. FAIL SOFT FOR ANALYTICS, FAIL SAFE FOR CONTROL

Analytics failure:

```text
degrade gracefully
```

Security/control configuration error:

```text
do not invent permissions/actions
```

IBVAP does not directly control physical enforcement systems.

---

# 77. HUMAN-IN-THE-LOOP IS REQUIRED FOR CONSEQUENTIAL INTERPRETATION

The system provides:

```text
observation
+
evidence
+
priority
```

The human operator remains responsible for interpreting the event and taking any external action.

Do not build automatic enforcement decisions.

---

# 78. DO NOT CREATE "THREAT INTENT" FROM APPEARANCE

The system must not infer:

```text
face/body appearance → criminal intent
```

Behavioral/spatial evidence may create an event according to configured rules, but the product must not claim to know a person's intent.

---

# 79. BIOMETRIC DATA MUST BE ISOLATED

If FRS is enabled:

```text
face data
```

must be treated as more sensitive than ordinary event metadata.

Keep separate access controls and audit trails.

---

# 80. DO NOT RETAIN RAW VIDEO FOREVER

Use configurable retention.

Prototype:

```text
evidence clips
```

rather than indiscriminately duplicating all video.

---

# 81. KEEP MODEL AND EVENT TRACEABILITY

Every event should be reproducible to:

```text
what camera
what time
what model version
what configuration
```

If relevant:

```text
tracker version
environment version
optional model versions
```

---

# 82. DOCUMENT EVERY ARCHITECTURAL CHANGE

For a change that affects:

```text
components
data flow
models
interfaces
deployment
security
storage
```

update:

```text
docs/DECISIONS.md
```

before or together with the implementation.

---

# 83. NO SILENT REARCHITECTURE

Do not silently change:

```text
FastAPI → another backend
React → another frontend
SQLite → another DB
worker architecture → microservices
```

just because a different stack is preferred.

Record the decision.

---

# 84. PRESERVE EXISTING WORKING FEATURES

Before modifying a module:

```text
identify current behavior
run relevant tests
make smallest change
rerun tests
```

Do not rewrite a working module from scratch unless there is a demonstrated reason.

---

# 85. PREFER SMALL DIFFS

When solving a problem:

```text
smallest correct change
```

is preferred over:

```text
rewrite everything
```

Small changes are easier to:

```text
review
test
debug
revert
```

---

# 86. DO NOT CHANGE MULTIPLE ARCHITECTURAL LAYERS UNNECESSARILY

For example:

If fixing:

```text
zone-crossing bug
```

do not simultaneously rewrite:

```text
frontend
database
detector
tracker
```

unless required.

---

# 87. BEFORE DELETING CODE, PROVE IT IS UNUSED

Do not delete:

```text
service
function
API
configuration
model adapter
```

without checking references.

If uncertain:

```text
leave it
```

and document.

---

# 88. DO NOT LEAVE DEAD DEMO CODE IN THE CORE PATH

Mock/demo code must be clearly isolated:

```text
demo/
mock/
fixtures/
```

Never silently substitute mock data during normal execution.

---

# 89. DO NOT HARD-CODE DEMO RESULTS

Never:

```python
event = "HIGH"
```

just to make the dashboard look good.

The dashboard must receive actual events.

---

# 90. DEMO DATA MUST BE CLEARLY IDENTIFIED

If using synthetic/public/self-recorded footage:

```text
DEMO DATA
```

should be visible somewhere in the system or documentation where appropriate.

Do not represent demo data as operational border footage.

---

# 91. DO NOT USE SENSITIVE/CLASSIFIED DATA

Do not request or embed:

```text
classified border layouts
sensitive operational procedures
security vulnerabilities
restricted watchlists
```

The prototype should use lawful, non-sensitive test data.

---

# 92. DON'T CREATE OPERATIONAL TACTICAL GUIDANCE

IBVAP is a software analytics project.

Do not turn the software into:

```text
patrol route optimization
force deployment instructions
engagement decisions
evasion analysis
security bypass methods
```

unless an approved, non-sensitive requirement explicitly defines a safe research context.

---

# 93. UI MUST REFLECT REAL SYSTEM STATE

Do not show:

```text
GPU 92%
```

unless that metric is actually measured.

Do not show:

```text
AI ACTIVE
```

if the worker is disconnected.

---

# 94. SYSTEM STATUS IS NOT MODEL STATUS

These are separate:

```text
API healthy
```

does not imply:

```text
AI worker healthy
```

Likewise:

```text
camera online
```

does not imply:

```text
detector active
```

The dashboard should distinguish these states.

---

# 95. DO NOT HIDE LATENCY

If a result is stale:

```text
show processing latency
```

or an appropriate freshness indicator.

Never present a 5-second-old event as instant real-time intelligence.

---

# 96. BUILD OBSERVABILITY BEFORE OPTIMIZATION

Before trying to make the system faster, measure:

```text
decode
preprocess
inference
tracking
reasoning
API
UI
```

Optimization without profiling is guesswork.

---

# 97. DO NOT SACRIFICE CORRECTNESS FOR FPS WITHOUT MEASUREMENT

Example:

```text
30 FPS
```

is not automatically better than:

```text
10 FPS
```

if the 30 FPS pipeline produces:

```text
false alerts
latency
dropped frames
```

Compare end-to-end system usefulness.

---

# 98. DO NOT SACRIFICE SAFETY/EXPLAINABILITY FOR A SMALL ACCURACY GAIN

A model that improves mAP slightly but:

```text
doubles latency
triples memory
makes results less explainable
```

may be a worse product choice.

---

# 99. DO NOT USE SCREENSHOTS AS PROOF OF MODEL QUALITY

A visually good detection screenshot is not a benchmark.

Use measured metrics and replay evaluation.

---

# 100. DO NOT CALL A SINGLE TEST CASE "VALIDATION"

At minimum, evaluate:

```text
positive
negative
night
poor visibility
animal
lateral movement
fence crossing
camera failure
```

---

# 101. REQUIRED CORE TEST SCENARIOS

The system must maintain replayable scenarios for:

```text
T01 — normal person
T02 — lateral movement
T03 — animal movement
T04 — persistent approach
T05 — restricted entry
T06 — fence crossing
T07 — night/low-light
T08 — uncertain/low-quality
T09 — vehicle
T10 — camera disconnect
```

Optional:

```text
T11 — ANPR
T12 — uniform
T13 — face
T14 — learned anomaly
```

---

# 102. NO FEATURE IS "DONE" WITHOUT A FAILURE CASE

For each major feature, test:

```text
works when expected
fails safely when input is bad
```

Example:

```text
ANPR
→ good plate
→ unreadable plate
→ partial plate
→ inconsistent OCR
```

---

# 103. DO NOT USE MODEL OUTPUTS OUTSIDE THEIR VALID DOMAIN

A generic detector may recognize:

```text
person
car
dog
```

but that does not make it a validated:

```text
border-intruder detector
```

Domain-specific claims require domain-specific evaluation.

---

# 104. NO RANDOM THRESHOLD CHANGES

Changing:

```text
confidence = 0.35
→ 0.20
```

must have a reason.

Record:

```text
why
what changed
what metric changed
```

Do not tune until the demo happens to look good.

---

# 105. THRESHOLD TUNING MUST USE VALIDATION DATA

Never tune solely on the final test videos.

Use:

```text
training
validation
test
```

with proper separation.

---

# 106. DON'T CONFUSE CLASSIFICATION WITH AUTHORIZATION

Example:

```text
uniform detected
```

is not equivalent to:

```text
authorized personnel
```

The product must not overstate what visual classification proves.

---

# 107. DON'T CONFUSE FACE MATCH WITH CERTAIN IDENTITY

A similarity result is evidence.

It is not proof.

The UI should preserve uncertainty.

---

# 108. DON'T CONFUSE PLATE OCR WITH VEHICLE OWNERSHIP

ANPR can produce:

```text
plate candidate
```

It does not automatically establish:

```text
vehicle owner identity
```

unless another validated data source exists.

---

# 109. NO UNDOCUMENTED EXTERNAL API DEPENDENCIES

Do not add:

```text
weather API
map API
LLM API
cloud vision API
geocoding API
```

to the core path without explicit approval.

A remote API can break offline deployment and introduce cost/privacy/licensing issues.

---

# 110. CORE SYSTEM MUST WORK WITHOUT AN LLM

IBVAP's fundamental event detection must NOT depend on:

```text
GPT
LLM
cloud AI
vision-language API
```

The core stack is deterministic/CV/ML video analytics.

LLMs may assist engineering or future research, but cannot be a hidden runtime dependency.

---

# 111. NO "AI WASHING"

Do not rename:

```text
if statement
```

as:

```text
AI behavioral reasoning
```

Do not rename:

```text
threshold rule
```

as:

```text
deep learning confidence
```

Use accurate technical language.

---

# 112. PRODUCT LANGUAGE MUST MATCH IMPLEMENTATION

If implemented:

```text
rule-based loitering detection
```

say:

```text
trajectory-based loitering detection
```

not:

```text
AI understands human intent
```

---

# 113. SOURCE/CITATION DISCIPLINE

When documentation states a factual claim derived from research:

```text
cite the source
```

Do not turn a research paper's reported result into a universal claim.

Use:

```text
"the cited study reported..."
```

rather than:

```text
"the system achieves..."
```

unless IBVAP itself has measured it.

---

# 114. RESEARCH RESULTS MUST NOT BE COPIED AS IBVAP RESULTS

If a paper reports:

```text
92% accuracy
```

that means:

```text
paper result
```

not:

```text
IBVAP result
```

unless IBVAP actually reproduces and validates that experiment.

---

# 115. DO NOT REPRODUCE SENSITIVE OPERATIONAL DETAILS

Research may mention:

```text
specific security deployments
```

Do not infer or invent:

```text
tactical procedures
blind spots
patrol patterns
security vulnerabilities
```

The project remains a technology prototype.

---

# 116. KEEP OPTIONAL FEATURES FEATURE-FLAGGED

Recommended conceptual flags:

```yaml
features:
  uniform_classifier: false
  anpr: false
  face_recognition: false
  advanced_anomaly: false
```

The core pipeline must remain functional with all optional features disabled.

---

# 117. DO NOT REQUIRE EVERY MODEL TO BE PRESENT FOR STARTUP

Startup dependencies:

```text
core detector
core tracker
core environment logic
```

Optional model missing:

```text
warning
module disabled
```

Core startup should continue.

---

# 118. MODEL LOAD FAILURE MUST BE VISIBLE

If detector fails:

```text
WORKER HEALTH = ERROR
```

Do not silently show an empty camera as healthy.

---

# 119. CONFIG VALIDATION IS REQUIRED

At startup validate:

```text
camera IDs
zone polygons
fence points
direction vector
model paths
threshold ranges
```

Invalid config should produce explicit errors.

---

# 120. MODEL INPUT CONTRACTS MUST BE VALIDATED

Before inference:

```text
image shape
dtype
color format
resolution
```

must be as expected.

Do not silently feed incompatible data into a model.

---

# 121. DATA NORMALIZATION MUST BE EXPLICIT

Document:

```text
RGB/BGR
normalization
resize
letterbox
padding
channel order
```

Do not rely on accidental preprocessing.

---

# 122. TRACKING COORDINATES MUST USE A KNOWN REFERENCE

Document whether coordinates refer to:

```text
original frame
resized frame
letterboxed frame
ROI coordinates
```

Do not mix coordinate systems.

---

# 123. ZONE COORDINATES MUST MATCH DISPLAY COORDINATES

If the frontend draws:

```text
100,100
```

the worker must understand the same coordinate space.

Otherwise:

```text
visual fence ≠ actual fence
```

which is a critical bug.

---

# 124. UI CONFIGURATION MUST PERSIST

If an operator draws a fence:

```text
save it
```

Do not keep it only in browser memory unless explicitly intended for temporary demo state.

---

# 125. DATABASE MIGRATIONS MUST BE EXPLICIT

If schema changes:

```text
migration
or
clean documented initialization
```

Do not manually edit production tables in hidden code.

---

# 126. TIME HANDLING MUST BE CONSISTENT

Internal timestamps:

```text
UTC
```

Display:

```text
configured local timezone
```

Avoid mixing local/UTC timestamps inside event logic.

---

# 127. EVENT ORDERING MUST BE DETERMINISTIC

Use timestamps:

```text
frame timestamp
event timestamp
creation timestamp
```

Do not rely only on database insertion order.

---

# 128. EVIDENCE PATHS MUST BE RELATIVE/CONFIGURED

Do not hard-code:

```text
C:\Users\Akash\Desktop\...
```

Use:

```text
storage/evidence/...
```

or configured paths.

---

# 129. DO NOT MAKE WINDOWS/MAC/LINUX ASSUMPTIONS WITHOUT CHECKING

The prototype should document its target development/runtime OS.

Use portable path handling.

---

# 130. DO NOT ASSUME GPU AVAILABILITY

The worker must report:

```text
GPU
or
CPU
```

and fail clearly when an unavailable acceleration backend is selected.

---

# 131. CPU FALLBACK MUST BE EXPLICIT

If GPU is unavailable:

```text
CPU mode
```

may be used where supported.

Do not silently claim:

```text
GPU inference
```

when it is running on CPU.

---

# 132. HARDWARE-SPECIFIC OPTIMIZATION MUST BE ISOLATED

For example:

```text
TensorRT
```

should not become a hard dependency of core application logic.

Use runtime adapters.

---

# 133. DO NOT OPTIMIZE BEFORE THE BASELINE WORKS

Order:

```text
correctness
→ tests
→ benchmark
→ optimize
```

Not:

```text
optimize
→ discover architecture is wrong
```

---

# 134. DOCUMENT EVERY MODEL

For each model store:

```text
name
version
task
source
license
checksum
runtime
input format
output format
```

---

# 135. DO NOT DOWNLOAD RANDOM MODEL WEIGHTS DURING RUNTIME

Production/prototype runtime should load known model artifacts.

Do not make startup depend on an arbitrary external download.

---

# 136. PIN DEPENDENCIES WHERE PRACTICAL

Use lockfiles/requirements pins to avoid:

```text
today works
tomorrow breaks
```

---

# 137. DO NOT MAKE THE PROJECT INTERNET-DEPENDENT FOR INSTALLATION IF A LOCAL BUNDLE IS POSSIBLE

For hackathon demo:

```text
known dependencies
known model artifacts
```

should be prepared beforehand.

---

# 138. DON'T DELETE DOCUMENTATION TO "KEEP THE REPO CLEAN"

Architecture/product/technical documentation is part of the project.

If code and docs conflict:

```text
fix both
```

Do not simply delete the docs.

---

# 139. README MUST DESCRIBE ACTUAL SETUP

No imaginary:

```text
one-click deployment
```

unless it actually works.

---

# 140. INSTALLATION MUST BE REPRODUCIBLE

Document:

```text
Python version
Node version
GPU requirements
environment setup
model files
startup commands
RTSP configuration
```

---

# 141. DOCKER IS PACKAGING, NOT MAGIC

Docker must package a working application.

Do not use Docker to hide:

```text
missing dependency
incorrect path
broken environment
GPU misconfiguration
```

---

# 142. DO NOT DOCKERIZE BEFORE LOCAL DEBUGGING

Preferred:

```text
local working application
→ tests
→ dockerization
→ docker test
```

---

# 143. HEALTH CHECKS MUST MEAN SOMETHING

Do not return:

```json
{"status": "ok"}
```

if:

```text
worker dead
database unavailable
model unloaded
```

Health should reflect real dependencies.

---

# 144. NO FALSE "REAL-TIME" CLAIM

Use:

```text
near-real-time
```

unless measured latency supports a stronger statement.

Report actual:

```text
median latency
P95 latency
FPS
```

when available.

---

# 145. NO FALSE "ACCURACY" CLAIM

If the test set has not been formally evaluated:

```text
not measured
```

Do not quote an accuracy estimate from intuition.

---

# 146. ENVIRONMENT ROBUSTNESS MUST BE MEASURED

If claiming:

```text
works in night/forest/snow/fog
```

create condition-specific evaluation:

```text
day
night
forest
mountain
snow
poor visibility
```

At minimum, the demo may show scenarios, but production-like claims require metrics.

---

# 147. THE PRODUCT MUST NOT HIDE DEGRADED CONDITIONS

If environment quality is poor:

```text
show it
```

Do not pretend the result has normal confidence.

---

# 148. DO NOT RANDOMLY STACK MULTIPLE ENHANCEMENT MODELS

Avoid:

```text
CLAHE
→ Retinex
→ denoise
→ super-resolution
→ sharpening
→ another enhancement
```

without measuring downstream benefit.

Every preprocessing step can create artifacts.

---

# 149. USE THE SIMPLEST EFFECTIVE ENHANCEMENT

If:

```text
gamma + CLAHE
```

provides adequate improvement,

do not add a large enhancement model just because it is more sophisticated.

---

# 150. DO NOT CHANGE MODEL CLASS AFTER TRAINING WITHOUT RE-EVALUATION

If changing:

```text
person → human
```

or:

```text
animal → dog/cow/etc.
```

update:

```text
schema
UI
rules
dataset
evaluation
```

---

# 151. EVENT TYPES MUST BE CLOSED AND DOCUMENTED

Core events:

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

Do not invent arbitrary event names dynamically.

---

# 152. USE REASON CODES, NOT FREE-FORM AI EXPLANATIONS

Prefer:

```text
FENCE_CROSSED
PERSISTENT_TRACK
LOW_LIGHT
```

over generated paragraphs that may hallucinate.

The explanatory text may be assembled from verified structured facts.

---

# 153. DO NOT LET GENERATIVE TEXT INVENT INCIDENT FACTS

If an LLM is ever used to summarize an event, it may only summarize supplied structured fields.

It must not invent:

```text
weapon
identity
intent
location
number of people
```

that are not present in event data.

---

# 154. ALERT TEXT MUST BE DERIVED FROM EVENT DATA

Example:

```text
event_type
camera_id
timestamp
reasons
environment
```

should generate the alert.

Not:

```text
free-form model imagination
```

---

# 155. NO HIDDEN STATE IN GLOBAL VARIABLES

Core modules should have explicit state.

Avoid hidden:

```python
global_last_detection
```

that different cameras accidentally share.

---

# 156. CAMERA STATE MUST BE ISOLATED

Each camera should maintain separate:

```text
queue
environment state
tracker state
zone configuration
event state
health state
```

unless cross-camera functionality is explicitly implemented.

---

# 157. DO NOT MIX TRACK IDS BETWEEN CAMERAS

Track:

```text
camera_id + track_id
```

is safer than assuming:

```text
track_id alone is globally unique
```

---

# 158. RESOURCE ISOLATION

One overloaded camera must not freeze all cameras.

Use:

```text
per-camera state
bounded work
timeouts
```

and report degraded cameras.

---

# 159. NO MEMORY LEAKS FROM UNBOUNDED TRAJECTORIES

Trajectories must have:

```text
maximum age
or
maximum points
```

unless full history is explicitly required.

---

# 160. NO UNBOUNDED EVENT HISTORY IN PROCESS MEMORY

Persist events in the database.

Do not retain all historical events forever in Python lists.

---

# 161. EVIDENCE BUFFER MUST BE BOUNDED

Ring buffers should have fixed memory/resource limits.

---

# 162. NO BLOCKING I/O IN THE HOT PATH WHEN AVOIDABLE

Avoid long database/file/network operations blocking the detector loop.

Use appropriate asynchronous/background handling.

---

# 163. DO NOT BLOCK FRAME PROCESSING ON UI

The AI worker must not wait for a browser to consume each frame.

---

# 164. FRONTEND SHOULD NOT REQUEST RAW HIGH-FPS VIDEO FROM THE WORKER BY DEFAULT

Use a suitable streaming/replay architecture.

Do not accidentally create:

```text
one HTTP response per frame
```

with no backpressure.

---

# 165. BACKEND MUST NOT BECOME A VIDEO BOTTLENECK

The backend handles:

```text
events
configuration
auth
metadata
```

The worker handles:

```text
continuous video inference
```

---

# 166. KEEP THE CORE EVENT ENGINE PURE WHERE POSSIBLE

A useful separation:

```text
raw detection/tracking
        ↓
structured observation
        ↓
pure event rules
```

This makes event logic easy to unit test.

---

# 167. TEST EVENT LOGIC WITHOUT AI

You should be able to feed:

```text
synthetic TrackState sequences
```

to test:

```text
fence crossing
loitering
direction
```

without running a deep model.

---

# 168. TEST AI ADAPTERS WITHOUT THE FULL UI

Detector/tracker tests should be independently runnable.

---

# 169. TEST FRONTEND WITH MOCK EVENT FIXTURES, NOT MOCKED CORE LOGIC

Frontend can use fixtures for UI tests.

Do not replace the production worker logic with mocks in normal runtime.

---

# 170. DO NOT CHANGE THE PRODUCT GOAL MID-BUILD

The goal is:

```text
software-defined intelligent border video analytics
```

not:

```text
drone system
```

not:

```text
sensor network
```

not:

```text
general-purpose smart city surveillance
```

Stay focused.

---

# 171. DO NOT GENERALIZE THE PRODUCT TO EVERYTHING

Avoid turning the architecture into:

```text
generic AI platform for hospitals/cities/factories/borders
```

The domain context is important.

---

# 172. BORDER-SPECIFIC VALUE MUST REMAIN VISIBLE

Examples:

```text
restricted zones
boundary/fence logic
lateral vs protected-direction movement
uniform/civilian support
terrain/environment context
operator event prioritization
```

---

# 173. DO NOT OVERDEPEND ON FACIAL RECOGNITION

A person may be:

```text
too far
side-facing
occluded
blurred
dark
```

The system must still function without a usable face.

---

# 174. DO NOT OVERDEPEND ON ANPR

A vehicle may have:

```text
unreadable plate
occlusion
distance
motion blur
```

The vehicle should still be tracked.

---

# 175. CORE INTRUSION DETECTION MUST WORK WITHOUT ANPR OR FRS

Required:

```text
person
+
track
+
spatial/temporal context
```

is sufficient for core event reasoning.

---

# 176. DO NOT USE ANIMAL DETECTION ONLY AS A SHOWCASE

It exists for a concrete reason:

```text
false-alarm reduction
```

Tie animal events into the reasoning system.

---

# 177. DO NOT USE TERRAIN LABELS ONLY AS UI DECORATION

Terrain should influence:

```text
configuration
evaluation
environment interpretation
```

or remain clearly a metadata field.

---

# 178. DEMO TERRAIN MODES MUST BE REALISTIC

If demonstrating:

```text
forest
mountain
snow
```

use actual visual characteristics in the videos or explicitly label them as simulated/demo scenarios.

---

# 179. DO NOT PROMISE "ALL WEATHER"

Use:

```text
environment-adaptive
```

or:

```text
evaluated under selected degraded conditions
```

unless comprehensive testing exists.

---

# 180. DO NOT PROMISE "MILITARY GRADE"

That phrase has no meaning unless backed by specific formal requirements and testing.

Do not use it.

---

# 181. DO NOT PROMISE "100% AUTONOMOUS"

IBVAP is decision support.

Operator remains in the loop.

---

# 182. DO NOT PROMISE "ZERO FALSE ALARMS"

The research itself indicates environmental conditions can generate false alarms.

The product goal is:

```text
reduce
```

not:

```text
eliminate
```

---

# 183. DO NOT USE PAPER RESULTS AS MARKETING WITHOUT CONTEXT

When citing prior work:

```text
"Prior study reported..."
```

Then explain:

```text
dataset
environment
method
```

where relevant.

---

# 184. EVERY CLAIM OF IMPROVEMENT NEEDS A BASELINE

If claiming:

```text
adaptive pipeline is better
```

compare:

```text
baseline
vs
adaptive
```

on the same appropriate evaluation data.

---

# 185. REQUIRED ABLATION DIRECTION

Where practical:

```text
A — detector + tracker
B — + environment
C — + adaptive processing
D — + spatial/temporal reasoning
E — + evidence fusion
```

The purpose is to prove each added layer contributes.

---

# 186. DON'T ADD RESEARCH COMPLEXITY TO A BROKEN BASELINE

If:

```text
RTSP → detector → tracker
```

does not work reliably:

Do not jump to:

```text
VLM + anomaly model + ReID
```

Fix the baseline first.

---

# 187. BUILD IN VERTICAL SLICES

Best progression:

```text
camera
→ detection
→ tracking
→ fence
→ event
→ evidence
→ dashboard
```

Then extend.

Do not build disconnected components that never connect.

---

# 188. "DONE" MEANS END-TO-END

A module is not done merely because:

```text
Python function exists
```

It is done when:

```text
actual input
→ module
→ actual downstream consumer
```

works.

---

# 189. KEEP THE GOLDEN PATH WORKING

The golden path is:

```text
CCTV/replay
→ environment
→ person detection
→ tracking
→ virtual fence
→ direction
→ evidence fusion
→ HIGH event
→ evidence clip
→ dashboard
```

Every major change must preserve it.

---

# 190. GOLDEN PATH REGRESSION CHECK

Before final demo/build:

```text
run golden-path replay
→ confirm detection
→ confirm tracking
→ confirm fence crossing
→ confirm event
→ confirm clip
→ confirm dashboard alert
```

---

# 191. DO NOT LET OPTIONAL FEATURE FAILURE DESTROY THE GOLDEN PATH

If:

```text
ANPR broken
```

golden path should still work.

If:

```text
FRS broken
```

golden path should still work.

---

# 192. REQUIRED STARTUP ORDER

```text
configuration
→ database
→ model load
→ worker
→ backend
→ frontend
```

The exact process order may vary, but dependencies must be healthy before use.

---

# 193. REQUIRED SHUTDOWN BEHAVIOR

On shutdown:

```text
stop new frames
→ flush important event/evidence writes
→ close streams
→ close resources
```

Avoid corrupting evidence clips.

---

# 194. DO NOT LOSE EVENTS ON NORMAL SHUTDOWN

Important pending events should be persisted where feasible.

---

# 195. NO "SILENT SUCCESS"

If:

```text
evidence save failed
```

the event must not silently appear complete.

Use:

```text
evidence_status = ERROR
```

---

# 196. USER ACTIONS MUST BE AUDITABLE

At minimum:

```text
login
camera changes
zone changes
fence changes
model/config changes
alert acknowledge
alert dismiss
sensitive evidence access
```

---

# 197. DO NOT ALLOW FRONTEND-ONLY AUTHORIZATION

Backend MUST enforce permissions.

The browser is untrusted.

---

# 198. DO NOT TRUST CLIENT-SUPPLIED CAMERA/USER AUTHORITY

Server must validate:

```text
user
role
resource
action
```

---

# 199. SECURITY MUST NOT BE "COSMETIC"

A login screen without backend authorization is not security.

A hidden button is not authorization.

---

# 200. FINAL AGENT CHECK BEFORE ANY SIGNIFICANT CHANGE

Before modifying IBVAP, the agent must ask:

```text
1. Does this change solve an approved problem?
2. Is it consistent with the PRD?
3. Is it consistent with the Architecture?
4. Does it preserve the software-only constraint?
5. Does it preserve the golden path?
6. Does it add a new dependency?
7. Has its license been checked?
8. Does it affect latency?
9. Does it affect false alarms?
10. Does it require new configuration?
11. Does it require new tests?
12. Could it make the system appear more capable than it really is?
13. Could it introduce hallucinated/fake data?
14. Can the change be made smaller?
```

If the answer to #12 or #13 is YES:

```text
STOP AND FIX THE DESIGN.
```

---

# 201. FINAL RULE

## **Never optimize IBVAP for "looking advanced." Optimize it for being correct.**

The preferred system is:

```text
smaller
+
measurable
+
modular
+
explainable
+
testable
+
environment-aware
+
reliable
```

rather than:

```text
larger
+
more AI models
+
more buzzwords
+
less validation
+
more hidden assumptions
```

The agent must protect this principle throughout development.

---

# 202. THE IBVAP GOLDEN ARCHITECTURE

The final intended direction remains:

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
Temporal/behavior reasoning
       ↓
Optional supporting intelligence
       ↓
Evidence fusion
       ↓
Risk/event engine
       ↓
Evidence capture
       ↓
FastAPI
       ↓
React dashboard
```

No additional physical sensor is required by this architecture.

---

# 203. THE IBVAP GOLDEN PRODUCT PRINCIPLE

Do not build:

```text
"AI says person."
```

Build:

```text
"Here is what the camera observed,
here is the environmental quality,
here is how the object moved,
here is its spatial/temporal context,
here is why the system raised an event,
and here is the evidence for a human operator to verify."
```

---

# 204. END CONDITION

An implementation should be considered successful only when:

```text
It works on real input.
It survives expected failures.
It does not invent unavailable information.
It explains important decisions.
It preserves the approved architecture.
It is measurable.
It is reproducible.
It remains useful when optional AI features are disabled.
```

**When in doubt: preserve correctness, transparency, and the golden path.**
