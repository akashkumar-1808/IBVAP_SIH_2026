# IBVAP Model Registry & Storage Directory

This directory contains model artifacts, configuration, and runtime weights for IBVAP perception and intelligence modules.

---

## 1. Registered Detection Models

### Baseline Object Detector
- **Model Name:** `yolov8n`
- **Version:** 8.4.37 (Ultralytics)
- **Task:** General Object Detection (`person`, `vehicle`, `animal`)
- **Artifact Path:** `models/detector/yolov8n.pt`
- **Framework / Runtime:** PyTorch / Ultralytics
- **Compute Device Support:** CPU, CUDA, MPS
- **Input Resolution:** 640x640 RGB (or configurable)
- **Output:** Bounding boxes `[x1, y1, x2, y2]`, class index, confidence score `[0.0, 1.0]`
- **License:** AGPL-3.0 (Ultralytics open-source)
- **Source:** Ultralytics Official Release (https://github.com/ultralytics/ultralytics)

### Planned Alternative / Transformer Detector
- **Model Name:** `RF-DETR Nano/Small`
- **Task:** Real-Time Transformer Object Detection
- **License:** Apache-2.0
- **Source:** Roboflow RF-DETR (https://github.com/roboflow/rf-detr)
- **Status:** Interface compatible via `DetectorInterface` in `worker/perception/base.py`

---

## 2. Directory Structure

```text
models/
├── detector/       # Object detection weights (.pt, .onnx)
├── uniform/        # Optional uniform / civilian classification models
├── face/           # Optional face detection / embedding models
├── plate/          # Optional license plate OCR models
└── enhancement/    # Optional low-light enhancement models
```

> **Note:** Model weights (`*.pt`, `*.onnx`) are git-ignored to prevent bloating repository history. Weights are loaded/cached automatically by `ObjectDetector.load()`.
