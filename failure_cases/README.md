# IBVAP Evaluation & Failure Case Corpus

This directory contains structured evaluation failure cases captured during Phase 5 prototype testing.

> **CRITICAL RULE:** These cases are strictly for **Evaluation and Anomaly Analysis**.  
> They are **NOT** training data and must **NOT** be used to train or fine-tune models at this stage.

---

## 1. Observed Perception Anomalies Summary Table

| ID | Anomaly Category | Raw Class Name (COCO ID) | Confidence Range | Normalized TargetClass | Tracker State Observed | Root Cause & Classification |
|---|---|---|---|---|---|---|
| **ANOM-A** | Shadow False Positive | `skateboard` (36), `suitcase` (28) | 0.20 - 0.52 | `TargetClass.UNKNOWN` | Promoted to `CANDIDATE` / `TRACKED`, persists in `LOST` | **Model Limitation**: Pretrained COCO weights misclassify dark ground shadows and elongated ground contours as skateboards/bags. |
| **ANOM-B** | Pole / Structure False Positive | `fire hydrant` (10), `parking meter` (12) | 0.22 - 0.48 | `TargetClass.UNKNOWN` | Promoted to `TRACKED` (static post), transitions to `LOST` | **Model Limitation**: Pretrained COCO weights misclassify vertical security posts/poles as urban fire hydrants or parking meters. |
| **ANOM-C** | Vehicle Mapping / UNKNOWN | `car` (2), `skateboard` (36), `backpack` (24) | 0.25 - 0.88 | `TargetClass.VEHICLE` / `TargetClass.UNKNOWN` | `TRACKED` | **Combination**: Legitimate cars map to `VEHICLE`. When vehicles are partially occluded or misclassified by raw model as generic objects, they map to `UNKNOWN`. |
| **ANOM-D** | Dark / Low-Contrast False Positives | `dog` (16), `cat` (15), `bird` (14) | 0.18 - 0.38 | `TargetClass.ANIMAL` | `CANDIDATE` (often expires quickly) | **Model Limitation**: High-noise / low-contrast border patches trigger low-confidence animal false positives. |
| **ANOM-E** | Tracking Propagation of False Detections | Any false detection | N/A | Preserved from detection | `CANDIDATE -> TRACKED -> LOST -> EXPIRED` | **Expected Tracker Behavior**: ByteTrack faithfully tracks all bounding boxes passed to it; multi-frame false detections naturally form tracks until timeout. |

---

## 2. In-Depth Root Cause Diagnosis

### Anomaly A: Shadow False Positive
- **Observation:** Dark cast shadows from moving persons or infrastructure on the ground receive bounding box detections.
- **Pipeline Trace:**
  $$\text{Raw CCTV Frame} \xrightarrow{\text{YOLOv8n}} \text{Class: `skateboard` (idx 36), Conf: 0.38} \xrightarrow{\text{COCO\_CLASS\_MAP}} \text{`TargetClass.UNKNOWN`} \xrightarrow{\text{ByteTrack}} \text{Track ID \#4}$$
- **Root Cause:** Pretrained generic COCO dataset has high sensitivity to flat ground objects. Shadows near feet match the geometric aspect ratio and dark contrast of skateboards/bags.
- **Classification:** **Pretrained Model Limitation** (Not a code bug).

### Anomaly B: Pole / Structure False Positive
- **Observation:** Slender vertical posts, boundary markers, and infrastructure poles are intermittently detected as `fire hydrant` or `parking meter`.
- **Pipeline Trace:**
  $$\text{Raw CCTV Frame} \xrightarrow{\text{YOLOv8n}} \text{Class: `fire hydrant` (idx 10)} \xrightarrow{\text{COCO\_CLASS\_MAP}} \text{`TargetClass.UNKNOWN`} \xrightarrow{\text{ByteTrack}} \text{Track ID \#7}$$
- **Root Cause:** Urban COCO training distribution contains fire hydrants and parking meters with vertical aspect ratios and metallic/painted cylindrical structures.
- **Classification:** **Pretrained Model Limitation** (Not a code bug).

### Anomaly C: Vehicle Mapping / UNKNOWN
- **Observation:** Some vehicles in the test video displayed `unknown (tracked)` on the HUD badge.
- **Pipeline Trace:**
  1. Standard cars detected as `car` (idx 2) correctly map to `TargetClass.VEHICLE`.
  2. When a vehicle is far away, heavily occluded, or unusually shaped, YOLOv8n does not predict `car` but instead predicts low-confidence object classes (e.g. `backpack`, `skateboard`, `bench`).
  3. `COCO_CLASS_MAP.get(clean_name, TargetClass.UNKNOWN)` maps these non-vehicle classes to `TargetClass.UNKNOWN`.
  4. HUD and Visualizer display `ID #X | unknown (tracked)`.
- **Classification:** **Expected Schema Normalization on Imperfect Raw Detections** (Code mapping logic verified correct).

### Anomaly D: Dark / Low-Contrast False Positives
- **Observation:** Dark patches on soil/ground intermittently trigger low-confidence detections.
- **Root Cause:** In low-light or uneven contrast regions (as detected by `EnvironmentAnalyzer.contrast < 0.15`), edge features become ambiguous.
- **Classification:** **Sensor / Lighting Contrast Challenge** (Target for future Adaptive Perception in Phase 7/8).

### Anomaly E: Tracking Propagation of False Detections
- **Observation:** When a false positive detection occurs over 2+ consecutive frames, ByteTrack creates a `TRACKED` track.
- **Root Cause:** Tracker relies on spatial IoU and Kalman motion prediction; it assumes all detections passed to it are valid physical targets.
- **Classification:** **Expected Modular Tracker Behavior** (Tracking engine is decoupled from semantic filtering).

---

## 3. Directory Layout

```text
failure_cases/
├── README.md                           # This diagnostic documentation
├── shadows/                            # Shadow false positives (cases.json + sample frames)
├── poles/                              # Pole/structure false positives (cases.json + sample frames)
├── vehicles/                           # Vehicle / UNKNOWN edge cases (cases.json)
├── background_false_positives/         # Low-contrast background false positives (cases.json)
└── metadata/
    └── raw_detections_dump.json        # Complete raw diagnostic dump (2,174 detections)
```
