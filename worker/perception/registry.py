"""
Detector Registry & Factory for IBVAP Perception.

Provides centralized registration and dynamic instantiation of model-agnostic
detector backends (YOLOv8, YOLO11, YOLO26, RT-DETR, ONNX, Mock).
"""

import logging
from typing import Dict, Type, List, Optional, Any
from .base import DetectorInterface
from .config import ModelConfig, resolve_model_config

logger = logging.getLogger(__name__)

_DETECTOR_REGISTRY: Dict[str, Type[DetectorInterface]] = {}


def register_detector(detector_type: str, detector_cls: Type[DetectorInterface]) -> None:
    """Registers a detector adapter class under a unique type identifier."""
    key = detector_type.lower().strip()
    _DETECTOR_REGISTRY[key] = detector_cls
    logger.debug(f"Registered detector adapter '{key}' -> {detector_cls.__name__}")


def get_detector(detector_type: str = "yolov8", **kwargs) -> DetectorInterface:
    """
    Factory function instantiating the requested detector adapter.

    Args:
        detector_type: Identifier such as 'yolov8', 'yolo11', 'yolo26', 'rtdetr', 'onnx', 'mock'.
        **kwargs: Arguments passed to the detector adapter constructor (model_path, device, etc.).

    Returns:
        Instance conforming to DetectorInterface.
    """
    key = detector_type.lower().strip()

    _ensure_defaults_registered()

    # Normalization of aliases
    if key in ("rt-detr", "rtdetr"):
        key = "rtdetr"
    elif key in ("yolo26-pose", "yolo26_pose"):
        key = "yolo26-pose"
    elif key in ("yolov8-pose", "yolov8_pose"):
        key = "yolov8-pose"
    elif key.startswith("yolo"):
        # If specific exact model name like yolo26 or yolo11 or yolov8
        if key not in _DETECTOR_REGISTRY:
            if "pose" in key:
                if "26" in key:
                    key = "yolo26-pose"
                else:
                    key = "yolov8-pose"
            elif "yolo26" in key:
                key = "yolo26"
            elif "yolo11" in key:
                key = "yolo11"
            else:
                key = "yolov8"

    if key not in _DETECTOR_REGISTRY:
        available = list_available_detectors()
        raise ValueError(
            f"Unknown detector type '{detector_type}'. Available detectors: {available}"
        )

    detector_cls = _DETECTOR_REGISTRY[key]
    return detector_cls(**kwargs)


def create_detector_from_config(config: Optional[ModelConfig] = None) -> DetectorInterface:
    """
    Instantiates the appropriate detector adapter directly from a centralized ModelConfig.
    """
    cfg = config or resolve_model_config()
    return get_detector(
        detector_type=cfg.model_type,
        model_path=cfg.model_weights,
        confidence_threshold=cfg.confidence_threshold,
        iou_threshold=cfg.iou_threshold,
        input_size=cfg.input_size,
        device=cfg.device,
        max_detections=cfg.max_detections,
    )


def list_available_detectors() -> List[str]:
    """Returns a list of all registered detector backend keys."""
    _ensure_defaults_registered()
    return sorted(list(_DETECTOR_REGISTRY.keys()))


def _ensure_defaults_registered() -> None:
    if not _DETECTOR_REGISTRY:
        try:
            from .detector import (
                YOLOv8Detector,
                YOLO11Detector,
                YOLO26Detector,
                YOLO26PoseDetector,
                YOLOv8PoseDetector,
                RTDETRDetector,
                MockDetector,
                ObjectDetector,
            )
            register_detector("yolov8", YOLOv8Detector)
            register_detector("yolo11", YOLO11Detector)
            register_detector("yolo26", YOLO26Detector)
            register_detector("yolo26-pose", YOLO26PoseDetector)
            register_detector("yolo26_pose", YOLO26PoseDetector)
            register_detector("yolov8-pose", YOLOv8PoseDetector)
            register_detector("yolov8_pose", YOLOv8PoseDetector)
            register_detector("rtdetr", RTDETRDetector)
            register_detector("rt-detr", RTDETRDetector)
            register_detector("mock", MockDetector)
            register_detector("default", ObjectDetector)
        except ImportError as err:
            logger.debug(f"Notice during default detector registration: {err}")
