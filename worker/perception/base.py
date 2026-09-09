"""
Model-Agnostic Detector Interface & Base Adapter for IBVAP Perception.

Architectural Contract:
1. Enforces strict decoupling between any underlying computer vision framework
   (Ultralytics YOLOv8, YOLO11, YOLO26, RT-DETR, ONNX, TensorRT, TorchScript)
   and downstream tracking, GIS, behavioral analytics, evidence fusion, and UI logic.
2. Under no circumstance do framework-specific result objects, tensors, or model handles
   leak past this adapter boundary.
3. Every detector adapter must output solely canonical Detection instances with
   unified bounding box coordinates and normalized TargetClass mappings.
"""

from abc import ABC, abstractmethod
import time
import logging
from typing import List, Optional, Dict, Any, Tuple
import numpy as np
import torch

from ..ingestion.frame import FramePacket
from .schemas import Detection, BoundingBox, TargetClass, map_raw_class_to_target
from .exceptions import (
    ModelLoadError,
    ModelInferenceError,
    InvalidInputError,
    UnsupportedDeviceError,
)

logger = logging.getLogger(__name__)


class DetectorInterface(ABC):
    """
    Abstract Base Class for all object detection backends in IBVAP.
    Guarantees seamless pluggability across model architectures (YOLOv8, YOLO11, YOLO26, RT-DETR, ONNX).
    """

    @abstractmethod
    def load(self, model_path: Optional[str] = None) -> bool:
        """
        Loads model weights into memory and initializes computation graph.
        Returns True if loaded successfully, False otherwise.
        """
        pass

    @abstractmethod
    def warmup(self, input_size: Tuple[int, int] = (640, 640)) -> bool:
        """
        Executes dummy forward passes to warm up computation engine / GPU kernels.
        Returns True if warmup completes without error.
        """
        pass

    @abstractmethod
    def infer(self, frame_packet: FramePacket) -> List[Detection]:
        """
        Performs object detection on the provided canonical FramePacket.
        Returns a list of structured, unified Detection objects.
        """
        pass

    @abstractmethod
    def get_metadata(self) -> Dict[str, Any]:
        """
        Returns model metadata (name, model_type, version, device, confidence threshold, runtime).
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """
        Releases model weights and frees memory buffers cleanly.
        """
        pass


class BaseDetectorAdapter(DetectorInterface):
    """
    Base Adapter class implementing common boilerplate, device management,
    thread concurrency limits, latency profiling, and canonical Detection normalization.
    """

    def __init__(
        self,
        model_name: str = "generic_detector",
        model_type: str = "detector",
        model_path: Optional[str] = None,
        confidence_threshold: float = 0.35,
        iou_threshold: float = 0.45,
        input_size: Tuple[int, int] = (640, 640),
        device: Optional[str] = None,
        max_detections: int = 100,
    ):
        self.model_name = model_name
        self.model_type = model_type
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.iou_threshold = iou_threshold
        self.input_size = input_size
        self.max_detections = max_detections

        # Device selection: auto-detect CUDA if available and not explicitly requested
        if device is None:
            self.device = "cuda:0" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device
            if "cuda" in device and not torch.cuda.is_available():
                raise UnsupportedDeviceError(f"Requested CUDA device '{device}' but CUDA is not available.")

        # Constrain CPU thread contention on containerized environments
        if "cpu" in self.device:
            try:
                if torch.get_num_threads() > 2:
                    torch.set_num_threads(2)
            except Exception:
                pass

        self._model: Optional[Any] = None
        self._is_loaded: bool = False
        self._warmup_done: bool = False
        self._total_inferences: int = 0
        self._total_inference_time_sec: float = 0.0

    @staticmethod
    def _get_rss_mb() -> float:
        try:
            import psutil
            return psutil.Process().memory_info().rss / (1024 * 1024)
        except Exception:
            return 0.0

    def create_unified_detection(
        self,
        frame_packet: FramePacket,
        bbox_xyxy: Tuple[float, float, float, float],
        confidence: float,
        raw_class_name: str,
        class_index: int = -1,
        target_class: Optional[TargetClass] = None,
        tracking_id: Optional[int] = None,
        mask: Optional[Any] = None,
        obb: Optional[List[float]] = None,
        keypoints: Optional[List[Any]] = None,
        depth: Optional[float] = None,
        inference_time_ms: float = 0.0,
        extra_metadata: Optional[Dict[str, Any]] = None,
    ) -> Detection:
        """
        Guarantees that raw framework outputs are converted strictly into
        the canonical unified Detection schema. Prevents framework object leaks.
        """
        assigned_target_class = target_class or map_raw_class_to_target(raw_class_name)

        bbox = BoundingBox(
            x_min=float(bbox_xyxy[0]),
            y_min=float(bbox_xyxy[1]),
            x_max=float(bbox_xyxy[2]),
            y_max=float(bbox_xyxy[3]),
        )

        meta: Dict[str, Any] = {
            "raw_class_name": raw_class_name,
            "class_index": class_index,
            "model_name": self.model_name,
            "model_type": self.model_type,
            "inference_time_ms": round(inference_time_ms, 2),
        }
        if extra_metadata:
            meta.update(extra_metadata)

        return Detection(
            camera_id=frame_packet.camera_id,
            frame_id=frame_packet.frame_id,
            timestamp_utc=frame_packet.timestamp_utc,
            class_id=assigned_target_class,
            class_name=raw_class_name.lower().strip(),
            confidence=float(confidence),
            bbox=bbox,
            tracking_id=tracking_id,
            mask=mask,
            obb=obb,
            keypoints=keypoints,
            depth=depth,
            metadata=meta,
        )

    def get_metadata(self) -> Dict[str, Any]:
        """Returns standardized operational telemetry for this detector adapter."""
        avg_latency_ms = (
            (self._total_inference_time_sec / self._total_inferences * 1000.0)
            if self._total_inferences > 0
            else 0.0
        )
        return {
            "model_name": self.model_name,
            "model_type": self.model_type,
            "model_path": self.model_path,
            "device": self.device,
            "confidence_threshold": self.confidence_threshold,
            "iou_threshold": self.iou_threshold,
            "input_size": self.input_size,
            "is_loaded": self._is_loaded,
            "warmup_done": self._warmup_done,
            "total_inferences": self._total_inferences,
            "average_latency_ms": round(avg_latency_ms, 2),
            "effective_inference_fps": round(1000.0 / avg_latency_ms, 2) if avg_latency_ms > 0 else 0.0,
        }

    def close(self) -> None:
        """Releases model weights and frees memory buffers cleanly."""
        self._model = None
        self._is_loaded = False
        self._warmup_done = False
        logger.info(f"Detector adapter '{self.model_name}' closed cleanly.")
