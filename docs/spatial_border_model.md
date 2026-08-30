# IBVAP — Spatial Border Model Architecture

## 1. Overview

This document describes the world-owned border model that governs IBVAP's spatial intelligence layer.

The core principle is:

```text
THE BORDER IS A REAL-WORLD SPATIAL OBJECT.
A CAMERA IS ONLY A VIEW OF THAT OBJECT.
```

---

## 2. Why the Pixel-Fence Model Is Insufficient

### Old Model (Phase 6 — Superseded)

```text
Camera
  → manually defined image-pixel zones / fences
  → image-space geometry
  → SpatialState
```

Each camera independently defines its own pixel-space virtual fences and zones. There is no shared world model. This creates several problems:

1. **No shared truth**: Two cameras observing the same fence define two independent pixel lines with no semantic relationship.
2. **Scaling cost**: Every new camera requires manual pixel-coordinate fence placement by an operator, even if it views an already-defined boundary.
3. **Inconsistent semantics**: A crossing in Camera A and a crossing in Camera B cannot be correlated to the same world boundary.
4. **Fragile to camera changes**: If a camera is adjusted (pan/tilt/zoom), the pixel fence becomes invalid with no detection mechanism.

### New Model (This Correction)

```text
GLOBAL BORDER (world coordinates)
  → BORDER SECTIONS
  → CAMERA REGISTRATION
  → CAMERA CALIBRATION (planar homography)
  → PROJECTED BORDER (derived image-space geometry)
  → GROUND-CONTACT POINT (bottom-center approx)
  → SIDE / BUFFER / CROSSING RELATIONSHIP
  → SpatialState (backward-compatible output)
```

---

## 3. Conceptual Hierarchy

```text
                    ┌─────────────────────┐
                    │   GLOBAL BORDER     │
                    │  (world coordinates)│
                    └────────┬────────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
     ┌────────────┐  ┌────────────┐  ┌────────────┐
     │  Section A │  │  Section B │  │  Section C │
     └─────┬──────┘  └─────┬──────┘  └─────┬──────┘
           │               │               │
     ┌─────┴─────┐   ┌─────┴─────┐   ┌─────┴─────┐
     │ Camera 01 │   │ Camera 07 │   │ Camera 09 │
     │ Camera 02 │   │ Camera 08 │   │           │
     └───────────┘   └───────────┘   └───────────┘

Each camera produces its own PROJECTED BORDER
derived from the same world-level border definition.
```

The logical relationship is:

```text
ONE REAL-WORLD BORDER
        |
        +---- Camera A → projected image border A (diagonal)
        |
        +---- Camera B → projected image border B (horizontal)
        |
        +---- Camera C → projected image border C (near-vertical)
```

All projections originate from the same world-level border definition. Different cameras may show the same world border as horizontal, vertical, or diagonal. This is correct and expected behavior.

---

## 4. World-Space Border Representation

For prototype purposes, a LOCAL CARTESIAN coordinate system (X, Y) is used. GPS/WGS84 coordinates are NOT required and are NOT fabricated.

### Border Section

```text
BorderSection:
    id: str                       # Unique identifier
    name: str                     # Human-readable name
    coordinate_reference: enum    # LOCAL_CARTESIAN or GPS_WGS84
    points: List[WorldPoint]      # Ordered world-coordinate vertices
    permitted_side_normal: (x, y) # Normal vector pointing toward permitted side
    warning_buffer_distance: float # Buffer width in world units
    terrain_mode: enum            # PLANAR_GROUND or TERRAIN_3D
    version: str                  # Semantic version
```

### Border Sectoring

An entire national border is NOT modeled as one computational object. Instead:

```text
BORDER
  ↓
SECTOR / SECTION (manageable local representation)
  ↓
CAMERA COVERAGE
```

Each section is a manageable local representation of the border. Each camera explicitly declares which border section(s) it can observe.

---

## 5. Camera Registration

Every camera must be registered with metadata describing its relationship to the border:

```text
CameraRegistration:
    camera_id: str
    location: WorldPoint (optional)
    height_meters: float (optional)
    orientation_deg: float (optional)
    visible_border_sections: List[str]
    calibration_profile_id: str
    calibration_version: str
    calibration_status: enum
```

### Calibration Status States

```text
CALIBRATED              — valid, verified calibration active
UNCALIBRATED            — no calibration data available
STALE                   — calibration data exists but may be outdated
RECALIBRATION_REQUIRED  — camera pose/zoom/lens changed
INVALID                 — calibration data is provably wrong
```

A camera is NOT marked `CALIBRATED` merely because configuration exists. Calibration state must represent actual validity.

---

## 6. Camera Calibration

For the prototype, calibration uses explicit correspondences between world points and image pixels:

```text
world_point_1  ↔  image_point_1
world_point_2  ↔  image_point_2
world_point_3  ↔  image_point_3
world_point_4  ↔  image_point_4
(additional points if available)
```

At least 4 non-collinear correspondences are required for the planar model. Additional correspondences improve accuracy and are always accepted.

### Calibration Metadata

```text
CameraCalibration:
    camera_id: str
    image_width: int
    image_height: int
    correspondences: List[CalibrationCorrespondence]
    calibration_model: enum        # PLANAR_HOMOGRAPHY or TERRAIN_3D
    calibration_version: str
    reprojection_error: float (if computed)
    distortion_coefficients: optional
    created_at: datetime
    status: CalibrationStatus
```

---

## 7. Calibration Model Selection

Two explicit conceptual modes exist:

| Mode | Status | Description |
|------|--------|-------------|
| `PLANAR_GROUND` | **IMPLEMENTED** | Assumes ground surface is approximately flat |
| `TERRAIN_3D` | **NOT IMPLEMENTED** | Requires 3D terrain data and camera pose |

If `terrain_mode = TERRAIN_3D` is requested, the system returns an explicit `NotImplementedError`. It does not fake 3D terrain mapping.

---

## 8. Planar Ground Transform (Homography)

For approximately planar regions, the mapping is:

```text
WORLD POINT  →  HOMOGRAPHY MATRIX H  →  IMAGE PIXEL
IMAGE PIXEL  →  INVERSE H            →  WORLD POINT
```

The transform is computed using OpenCV `findHomography` with RANSAC. It accounts for perspective distortion. It must be versioned per camera calibration.

### Homography Limitations

A single planar homography assumes the relevant mapped surface can be treated as one plane.

**Suitable / reasonable for:**
- Roads
- Open relatively flat ground
- Local approximately planar areas

**Potentially inaccurate for:**
- Steep hills
- Valleys
- Large elevation changes
- Mountains
- Terrain with significant depth variation

The planar model does NOT solve arbitrary mountain terrain. Future mode `TERRAIN_3D` (camera pose + elevation data + 3D projection) is a separate future capability.

---

## 9. Border Projection

```text
project_border_to_camera(border_section, camera_calibration)
  → ProjectedBorder
```

The `ProjectedBorder` is a DERIVED VIEW containing:

```text
ProjectedBorder:
    camera_id: str
    border_section_id: str
    projected_points: List[Tuple[float, float]]
    warning_buffer_points: optional
    validity: SpatialConfidence
    calibration_version: str
```

**Source of truth**: The WORLD BORDER is the source of truth. The projected border is always re-derived from the world definition + calibration. If the border changes, it must be re-projected. Manually editing the projected image fence as a separate configuration is NOT permitted.

---

## 10. Warning Buffer

The world model supports a layered spatial structure:

```text
PERMITTED SIDE
    ↓
WARNING BUFFER (configurable world-distance)
    ↓
BORDER LINE
    ↓
RESTRICTED SIDE
```

If world-scale metric coordinates are available, the buffer uses real distance. If using pixel-distance in an image-only fallback mode, it is labeled `IMAGE_SPACE_BUFFER`, NOT "5 metres", unless real-world calibration supports that measurement.

---

## 11. Ground-Contact Point

For person/standing-object detections, the ground-contact point is approximated as the bottom-center of the bounding box:

```text
    +-----------+
    |   PERSON  |
    |           |
    |           |
    +-----●-----+
          ↑
    ground-contact
      estimate
```

### Representation

```text
GroundContactPoint:
    pixel_xy: (x, y)
    source_track_id: int
    method: GroundReferenceMethod  # BOTTOM_CENTER, CENTER, CUSTOM
    confidence: SpatialConfidence
```

### Important Constraints

- The ground-contact point is an APPROXIMATION. It does NOT claim exact foot position.
- For heavily occluded objects, confidence is marked `UNCERTAIN`.
- The same bottom-center approximation does NOT have identical reliability for person, vehicle, and animal. The `method` field allows per-class configuration.

---

## 12. Side Determination

Deterministic method to determine whether the tracked ground reference point lies on:

```text
PERMITTED_SIDE     — friendly / home territory
WARNING_BUFFER     — approaching boundary
BORDER_LINE        — on/near the boundary itself
RESTRICTED_SIDE    — crossed into restricted territory
UNKNOWN            — insufficient data or calibration
```

The result is camera-independent at the semantic level. The underlying projection may be camera-specific.

---

## 13. Crossing Detection

### Trajectory-Based Logic

A crossing is determined from movement over time, NOT from single-frame overlap:

```text
Previous world-side  →  Current world-side  →  Different sides  →  Possible crossing
```

Specifically:

```text
PREVIOUS = PERMITTED
CURRENT  = RESTRICTED
→ CROSSING_CANDIDATE
```

### What Does NOT Trigger a Crossing

- Bounding box touches projected line
- Bounding box overlaps line
- Detection is near line
- One noisy frame appears across line

Crossings require `TrackState` continuity.

### Crossing Confirmation

```text
CROSSING_CANDIDATE  →  (sustained N frames)  →  CONFIRMED_CROSSING
```

A one-frame crossing observation is NOT immediately escalated. The confirmation threshold is configurable. This prevents detection jitter from generating false crossing events.

---

## 14. Camera Movement & Calibration Versioning

If a fixed camera is physically moved, rotated, tilted, or zoomed beyond calibration assumptions:

```text
OLD CALIBRATION  →  INVALID / STALE  →  RECALIBRATION_REQUIRED
```

Calibration is versioned:

```text
CAM-07 calibration v1
CAM-07 calibration v2
```

The projected border must identify the calibration version from which it was generated. The old border projection must not continue to be used as valid.

---

## 15. Lens Distortion

If camera calibration contains distortion parameters:

```text
RAW FRAME  →  DISTORTION HANDLING  →  CALIBRATED IMAGE SPACE  →  BORDER PROJECTION
```

If no calibration exists, status = `UNCALIBRATED`. Zero distortion is NOT silently assumed for wide-angle cameras unless documented as an explicit approximation.

---

## 16. Uncertainty Sources

Explicit uncertainty is tracked where appropriate:

| Source | Possible State |
|--------|---------------|
| Calibration quality | `VALID`, `LOW_CONFIDENCE`, `UNCERTAIN`, `INVALID` |
| Poor ground-contact estimate | `UNCERTAIN` |
| Occlusion | `UNCERTAIN` |
| Border projection outside visible image | `INVALID` |
| Insufficient world reference | `UNCERTAIN` |
| Non-planar terrain | `LOW_CONFIDENCE` |

Numerical uncertainty percentages are NOT invented unless actually calculated.

---

## 17. Multi-Camera Consistency

```text
Camera A:  projected border = diagonal
Camera B:  projected border = horizontal
Camera C:  projected border = near-vertical

All three reference:  THE SAME WORLD BORDER
```

The same simulated world movement must produce semantically consistent `PERMITTED` / `BUFFER` / `CROSSING` / `RESTRICTED` states in all cameras even though their image projections differ. This is the key architectural benefit.

---

## 18. Backward Compatibility

- `SpatialState` is EXTENDED with optional fields, not broken.
- Phase 7 `BehaviorEngine` continues to consume `SpatialState` without modification.
- Uncalibrated cameras fall back to legacy image-space zone/fence logic.
- Existing `CameraSpatialConfig` with manual pixel zones remains functional.

---

## 19. Future Extensions

- **TERRAIN_3D**: 3D terrain data + camera pose + elevation-aware projection (NOT this prototype).
- **GPS/WGS84**: National-scale GIS coordinates (NOT this prototype).
- **Cross-camera ReID**: Correlating tracks across cameras via the shared world model.
- **Automated calibration**: Using known-size reference objects for self-calibration.
