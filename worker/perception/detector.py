import os
import time
import logging
from typing import List, Optional, Dict, Any, Tuple
import numpy as np
import torch

from .base import DetectorInterface
from .schemas import Detection, BoundingBox, TargetClass, map_raw_class_to_target
from .exceptions import (
    ModelNotFoundError,
    ModelLoadError,
    ModelInferenceError,
    InvalidInputError,
    UnsupportedDeviceError,
)
from ..ingestion.frame import FramePacket

logger = logging.getLogger(__name__)


class ObjectDetector(DetectorInterface):
    """
    Standard Object Detector implementation for IBVAP baseline perception.
    Integrates pretrained real-time object detection models behind the canonical DetectorInterface.
    """

    def __init__(
        self,
        model_name: str = "yolov8n",
        model_path: Optional[str] = None,
        confidence_threshold: float = 0.35,
        iou_threshold: float = 0.45,
        input_size: Tuple[int, int] = (640, 640),
        device: Optional[str] = None,
        max_detections: int = 100,
    ):
        self.model_name = model_name
        self.model_path = model_path or f"models/detector/{model_name}.pt"
        self.confidence_threshold = confidence_threshold
        self.iou_threshold = iou_threshold
        self.input_size = input_size
        self.max_detections = max_detections

        # Device selection: auto-detect CUDA if available and not explicitly specified
        if device is None:
            self.device = "cuda:0" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device
            if "cuda" in device and not torch.cuda.is_available():
                raise UnsupportedDeviceError(f"Requested CUDA device '{device}' but CUDA is not available.")

        self._model = None
        self._is_loaded = False
        self._warmup_done = False
        self._total_inferences = 0
        self._total_inference_time_sec = 0.0

    def load(self, model_path: Optional[str] = None) -> bool:
        """Loads model into memory and moves to configured compute device."""
        target_path = model_path or self.model_path

        try:
            from ultralytics import YOLO

            logger.info(f"Loading detection model '{self.model_name}' from '{target_path}' on device '{self.device}'...")
            self._model = YOLO(target_path)
            self._is_loaded = True
            logger.info(f"Detection model '{self.model_name}' loaded successfully.")
            return True
        except Exception as exc:
            self._is_loaded = False
            logger.error(f"Failed to load detection model from '{target_path}': {exc}")
            raise ModelLoadError(f"Cannot load model '{target_path}': {exc}") from exc

    def warmup(self, input_size: Optional[Tuple[int, int]] = None) -> bool:
        """Executes a dummy inference pass to initialize model weights and GPU kernels."""
        if not self._is_loaded or self._model is None:
            self.load()

        warmup_size = input_size or self.input_size
        logger.info(f"Warming up detector with dummy {warmup_size[0]}x{warmup_size[1]} frame...")

        try:
            dummy_image = np.zeros((warmup_size[1], warmup_size[0], 3), dtype=np.uint8)
            self._model.predict(
                source=dummy_image,
                conf=self.confidence_threshold,
                iou=self.iou_threshold,
                device=self.device,
                verbose=False,
            )
            self._warmup_done = True
            logger.info("Detector warmup completed successfully.")
            return True
        except Exception as exc:
            logger.error(f"Warmup forward pass failed: {exc}")
            raise ModelInferenceError(f"Detector warmup failed: {exc}") from exc

    def infer(self, frame_packet: FramePacket) -> List[Detection]:
        """
        Executes object detection on a canonical FramePacket.
        Returns a list of Detection objects in original frame coordinates.
        """
        if frame_packet is None or frame_packet.image is None:
            raise InvalidInputError("Cannot run inference on None or empty FramePacket")

        if frame_packet.image.size == 0 or len(frame_packet.image.shape) != 3:
            raise InvalidInputError(f"Invalid frame image shape: {getattr(frame_packet.image, 'shape', None)}")

        if not self._is_loaded or self._model is None:
            self.load()
            if not self._warmup_done:
                self.warmup()

        start_time = time.perf_counter()

        try:
            results = self._model.predict(
                source=frame_packet.image,
                conf=self.confidence_threshold,
                iou=self.iou_threshold,
                device=self.device,
                max_det=self.max_detections,
                verbose=False,
            )
        except Exception as exc:
            logger.error(f"Inference error on camera '{frame_packet.camera_id}', frame {frame_packet.frame_id}: {exc}")
            raise ModelInferenceError(f"Model forward pass failed: {exc}") from exc

        elapsed = time.perf_counter() - start_time
        self._total_inferences += 1
        self._total_inference_time_sec += elapsed

        detections: List[Detection] = []
        if not results:
            return detections

        res = results[0]
        boxes = res.boxes
        if boxes is None or len(boxes) == 0:
            return detections

        names_dict = res.names or {}

        for box in boxes:
            xyxy = box.xyxy[0].tolist()  # [x_min, y_min, x_max, y_max]
            conf = float(box.conf[0])
            cls_idx = int(box.cls[0])
            raw_class_name = names_dict.get(cls_idx, f"class_{cls_idx}")

            target_class = map_raw_class_to_target(raw_class_name)

            bbox = BoundingBox(
                x_min=float(xyxy[0]),
                y_min=float(xyxy[1]),
                x_max=float(xyxy[2]),
                y_max=float(xyxy[3]),
            )

            detection = Detection(
                camera_id=frame_packet.camera_id,
                frame_id=frame_packet.frame_id,
                timestamp_utc=frame_packet.timestamp_utc,
                class_id=target_class,
                confidence=conf,
                bbox=bbox,
                metadata={
                    "raw_class_name": raw_class_name,
                    "class_index": cls_idx,
                    "model_name": self.model_name,
                    "inference_time_ms": elapsed * 1000.0,
                },
            )
            detections.append(detection)

        return detections

    def get_metadata(self) -> Dict[str, Any]:
        avg_latency_ms = (
            (self._total_inference_time_sec / self._total_inferences * 1000.0)
            if self._total_inferences > 0
            else 0.0
        )
        return {
            "model_name": self.model_name,
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
        """Releases model weights and frees memory."""
        self._model = None
        self._is_loaded = False
        self._warmup_done = False
        logger.info(f"Detector '{self.model_name}' closed cleanly.")
