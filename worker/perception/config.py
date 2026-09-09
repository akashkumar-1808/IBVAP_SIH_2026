"""
Central Model Configuration & Path Resolution for IBVAP Perception.

Provides environment-aware configuration for object detection backends
(YOLOv8, YOLO11, YOLO26, RT-DETR, ONNX) without hardcoded paths.
"""

import os
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List
from pydantic import BaseModel, Field


class ModelConfig(BaseModel):
    """Configuration for a pluggable object detection backend."""
    model_type: str = Field(default="yolov8", description="Detector family: yolov8, yolo11, yolo26, rtdetr, yolo26-pose, mock")
    model_weights: Optional[str] = Field(default=None, description="Path or identifier for model weights artifact")
    confidence_threshold: float = Field(default=0.35, ge=0.0, le=1.0, description="Detection confidence cutoff")
    iou_threshold: float = Field(default=0.45, ge=0.0, le=1.0, description="NMS IOU cutoff")
    input_size: Tuple[int, int] = Field(default=(640, 640), description="Inference input resolution (width, height)")
    device: Optional[str] = Field(default=None, description="Compute device: 'cpu', 'cuda:0', etc.")
    max_detections: int = Field(default=100, ge=1, le=1000, description="Maximum detections per frame")
    enable_pose: bool = Field(default=False, description="Enable optional human pose keypoint perception")
    pose_model_type: Optional[str] = Field(default=None, description="Optional pose model type (e.g. yolo26-pose, yolov8-pose)")


def resolve_model_weights(model_type: str, explicit_weights: Optional[str] = None) -> str:
    """
    Resolves the weights path for the requested model type across standard repository paths.
    Avoids hardcoding paths throughout application logic.
    """
    if explicit_weights and explicit_weights.strip():
        # Check if provided path exists
        candidate = Path(explicit_weights)
        if candidate.exists() and candidate.is_file():
            return str(candidate.resolve())
        # Check relative to repository root
        repo_root = Path(__file__).resolve().parent.parent.parent
        cand_repo = repo_root / explicit_weights.replace("\\", "/")
        if cand_repo.exists() and cand_repo.is_file():
            return str(cand_repo.resolve())
        return explicit_weights

    # Fallback default weight names per family
    clean_type = model_type.lower().strip()
    if clean_type in ("rtdetr", "rt-detr", "rtdetr-l"):
        default_filename = "rtdetr-l.pt"
    elif clean_type in ("yolo26-pose", "yolo26_pose", "yolo26n-pose"):
        default_filename = "yolo26n-pose.pt"
    elif clean_type in ("yolov8-pose", "yolov8_pose", "yolov8n-pose"):
        default_filename = "yolov8n-pose.pt"
    elif clean_type in ("yolo11-pose", "yolo11_pose", "yolo11n-pose"):
        default_filename = "yolo11n-pose.pt"
    elif "-pose" in clean_type or "_pose" in clean_type:
        base = clean_type.replace("_pose", "-pose")
        default_filename = f"{base}.pt" if base.endswith(".pt") else f"{base}.pt"
    else:
        default_filename = f"{clean_type}n.pt" if not clean_type.endswith(".pt") else clean_type

    repo_root = Path(__file__).resolve().parent.parent.parent
    search_paths: List[Path] = [
        repo_root / "models" / "detector" / default_filename,
        repo_root / default_filename,
        Path("models") / "detector" / default_filename,
        Path(default_filename),
    ]

    for p in search_paths:
        if p.exists() and p.is_file():
            return str(p.resolve())

    # Return default filename so runtime/downloader can locate or pull it if supported
    return default_filename


def resolve_model_config(
    model_type: Optional[str] = None,
    model_weights: Optional[str] = None,
    confidence_threshold: Optional[float] = None,
    iou_threshold: Optional[float] = None,
    device: Optional[str] = None,
    input_size: Optional[Tuple[int, int]] = None,
    max_detections: Optional[int] = None,
    enable_pose: Optional[bool] = None,
    pose_model_type: Optional[str] = None,
) -> ModelConfig:
    """
    Builds a unified ModelConfig by merging explicit parameters with environment variables
    (MODEL_TYPE, DETECTOR_TYPE, MODEL_WEIGHTS, YOLO_MODEL_PATH, CONFIDENCE_THRESHOLD, IOU_THRESHOLD, DEFAULT_DEVICE, ENABLE_POSE, POSE_MODEL_TYPE).
    """
    # 1. Resolve model family
    m_type = (
        model_type
        or os.environ.get("MODEL_TYPE")
        or os.environ.get("DETECTOR_TYPE")
        or "yolov8"
    ).lower().strip()

    # 2. Resolve weights
    w_path = (
        model_weights
        or os.environ.get("MODEL_WEIGHTS")
        or os.environ.get("YOLO_MODEL_PATH")
    )
    resolved_w = resolve_model_weights(m_type, w_path)

    # 3. Resolve confidence
    conf = confidence_threshold
    if conf is None:
        env_conf = os.environ.get("CONFIDENCE_THRESHOLD") or os.environ.get("DETECTION_CONFIDENCE")
        conf = float(env_conf) if env_conf else 0.35

    # 4. Resolve IOU
    iou = iou_threshold
    if iou is None:
        env_iou = os.environ.get("IOU_THRESHOLD")
        iou = float(env_iou) if env_iou else 0.45

    # 5. Resolve compute device
    dev = device or os.environ.get("DEVICE") or os.environ.get("DEFAULT_DEVICE")

    # 6. Resolve pose enablement
    pose_on = enable_pose
    if pose_on is None:
        env_pose = os.environ.get("ENABLE_POSE", "").lower().strip()
        pose_on = env_pose in ("1", "true", "yes") or "-pose" in m_type or "_pose" in m_type

    p_type = pose_model_type or os.environ.get("POSE_MODEL_TYPE")

    return ModelConfig(
        model_type=m_type,
        model_weights=resolved_w,
        confidence_threshold=conf,
        iou_threshold=iou,
        input_size=input_size or (640, 640),
        device=dev,
        max_detections=max_detections or 100,
        enable_pose=pose_on,
        pose_model_type=p_type,
    )
