"""
Model-Agnostic Detector Adapters for IBVAP Perception.

Implements concrete adapters behind DetectorInterface / BaseDetectorAdapter:
- YOLOv8Detector: Ultralytics YOLOv8 runtime adapter.
- YOLO11Detector: Ultralytics YOLO11 runtime adapter.
- YOLO26Detector: Ultralytics YOLO26 runtime adapter (strictly 2D object detection).
- RTDETRDetector: Real-Time DEtection TRansformer adapter.
- MockDetector: Deterministic test detector for unit tests without weights.
- ObjectDetector: Backward-compatible alias for YOLOv8Detector.

Architectural Guarantees:
1. Translates raw model outputs directly into unified canonical Detection instances.
2. Strictly prevents framework-specific objects, tensors, or models from leaking downstream.
3. If installed Ultralytics version does not support the requested model family,
   raises ModelCompatibilityError clearly without silent model substitution.
4. Downstream tracking, GIS, and behavioral reasoning remain completely independent.
"""

import os
import time
import logging
from typing import List, Optional, Dict, Any, Tuple
import numpy as np
import torch

from .base import BaseDetectorAdapter, DetectorInterface
from .schemas import (
    Detection,
    BoundingBox,
    TargetClass,
    map_raw_class_to_target,
    PoseKeypoint,
    HumanPose,
    COCO_POSE_KEYPOINTS,
    SKELETON_CONNECTIONS,
)
from .exceptions import (
    ModelNotFoundError,
    ModelLoadError,
    ModelInferenceError,
    InvalidInputError,
    UnsupportedDeviceError,
    ModelCompatibilityError,
)
from .config import resolve_model_weights
from ..ingestion.frame import FramePacket

logger = logging.getLogger(__name__)


def parse_human_pose(raw_kp: Any) -> Optional[HumanPose]:
    """
    Normalizes raw model keypoint predictions (shape (17, 3) or (17, 2))
    into a structured, model-agnostic HumanPose schema containing all 17 COCO joints:
    nose, eyes, ears, shoulders, elbows, wrists, hips, knees, ankles.
    """
    if raw_kp is None:
        return None

    if isinstance(raw_kp, HumanPose):
        return raw_kp

    if isinstance(raw_kp, dict) and "keypoints" in raw_kp:
        try:
            return HumanPose(**raw_kp)
        except Exception:
            pass

    # If it's a tensor or numpy array or list
    if hasattr(raw_kp, "cpu") and hasattr(raw_kp, "numpy"):
        raw_kp = raw_kp.cpu().numpy()
    elif isinstance(raw_kp, (list, tuple)):
        raw_kp = np.array(raw_kp)

    if not isinstance(raw_kp, np.ndarray) or raw_kp.ndim < 2:
        return None

    kps_dict: Dict[str, PoseKeypoint] = {}
    conf_list: List[float] = []

    for idx, name in enumerate(COCO_POSE_KEYPOINTS):
        if idx < len(raw_kp):
            pt = raw_kp[idx]
            x = float(pt[0])
            y = float(pt[1])
            conf = float(pt[2]) if len(pt) >= 3 else 1.0
            visible = bool(conf > 0.25)
            kps_dict[name] = PoseKeypoint(
                name=name,
                x=round(x, 2),
                y=round(y, 2),
                confidence=round(conf, 4),
                visible=visible,
            )
            conf_list.append(conf)

    mean_conf = float(np.mean(conf_list)) if conf_list else 0.0
    return HumanPose(
        keypoints=kps_dict,
        confidence=round(mean_conf, 4),
        num_keypoints=len(kps_dict),
    )


class YOLOBaseAdapter(BaseDetectorAdapter):
    """
    Shared base adapter for all Ultralytics YOLO model families (YOLOv8, YOLO11, YOLO26).
    Encapsulates PyTorch and Ultralytics specifics, converting all predictions
    into unified canonical Detection objects.
    """

    def __init__(
        self,
        model_name: str,
        model_type: str,
        model_path: Optional[str] = None,
        confidence_threshold: float = 0.35,
        iou_threshold: float = 0.45,
        input_size: Tuple[int, int] = (640, 640),
        device: Optional[str] = None,
        max_detections: int = 100,
    ):
        resolved_path = resolve_model_weights(model_type, model_path)
        super().__init__(
            model_name=model_name,
            model_type=model_type,
            model_path=resolved_path,
            confidence_threshold=confidence_threshold,
            iou_threshold=iou_threshold,
            input_size=input_size,
            device=device,
            max_detections=max_detections,
        )

    def load(self, model_path: Optional[str] = None) -> bool:
        """
        Loads model into memory and verifies runtime compatibility.
        Raises ModelCompatibilityError if the installed Ultralytics version cannot load the architecture.
        """
        target_path = model_path or self.model_path
        t0 = time.perf_counter()
        rss_before = self._get_rss_mb()

        # Check explicit path existence if specified as a custom filesystem path
        if target_path and ("/" in target_path or "\\" in target_path or target_path.endswith(".pt") or target_path.startswith(".")):
            if not os.path.exists(target_path):
                raise ModelNotFoundError(
                    f"Model weights file '{target_path}' not found. Please ensure weights exist in models/detector/ or supply valid path."
                )

        try:
            import ultralytics
            from ultralytics import YOLO
        except ImportError as imp_err:
            raise ModelCompatibilityError(
                f"Ultralytics runtime is not installed in the environment: {imp_err}"
            ) from imp_err

        try:
            logger.info(
                f"Loading {self.model_type.upper()} model '{self.model_name}' "
                f"from '{target_path}' on device '{self.device}' (Ultralytics v{ultralytics.__version__})..."
            )
            self._model = YOLO(target_path)
            self._is_loaded = True
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            rss_after = self._get_rss_mb()
            logger.info(
                f"[RESOURCE] detector.load ({self.model_type}): rss_before={rss_before:.1f}MB, "
                f"rss_after={rss_after:.1f}MB, delta={rss_after - rss_before:+.1f}MB, elapsed={elapsed_ms:.1f}ms"
            )
            logger.info(f"{self.model_type.upper()} model '{self.model_name}' loaded successfully.")
            return True
        except ModelNotFoundError:
            raise
        except FileNotFoundError as fnf:
            self._is_loaded = False
            raise ModelNotFoundError(f"Model weights file '{target_path}' not found: {fnf}") from fnf
        except Exception as exc:
            self._is_loaded = False
            exc_str = str(exc).lower()
            # Explicit compatibility validation — do not silently substitute another model!
            if any(term in exc_str for term in ("unsupported", "not implemented", "invalid model", "not a valid", "corrupted", "cannot be recognized")):
                msg = (
                    f"Installed Ultralytics version ({getattr(ultralytics, '__version__', 'unknown')}) "
                    f"does not support requested model family '{self.model_type}' (path: '{target_path}'): {exc}"
                )
                logger.error(msg)
                raise ModelCompatibilityError(msg) from exc

            logger.error(f"Failed to load detection model from '{target_path}': {exc}")
            raise ModelLoadError(f"Cannot load model '{target_path}': {exc}") from exc

    def warmup(self, input_size: Optional[Tuple[int, int]] = None) -> bool:
        """Executes a dummy inference pass to initialize model weights and GPU kernels once."""
        if not self._is_loaded or self._model is None:
            self.load()

        warmup_size = input_size or self.input_size
        logger.info(f"Warming up {self.model_type.upper()} detector with dummy {warmup_size[0]}x{warmup_size[1]} frame...")
        t0 = time.perf_counter()
        rss_before = self._get_rss_mb()

        try:
            dummy_image = np.zeros((warmup_size[1], warmup_size[0], 3), dtype=np.uint8)
            with torch.inference_mode():
                self._model.predict(
                    source=dummy_image,
                    conf=self.confidence_threshold,
                    iou=self.iou_threshold,
                    device=self.device,
                    verbose=False,
                )
            self._warmup_done = True
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            rss_after = self._get_rss_mb()
            logger.info(
                f"[RESOURCE] detector.warmup ({self.model_type}): rss_before={rss_before:.1f}MB, "
                f"rss_after={rss_after:.1f}MB, delta={rss_after - rss_before:+.1f}MB, elapsed={elapsed_ms:.1f}ms"
            )
            logger.info(f"{self.model_type.upper()} detector warmup completed successfully.")
            return True
        except Exception as exc:
            logger.error(f"Warmup forward pass failed: {exc}")
            raise ModelInferenceError(f"Detector warmup failed: {exc}") from exc

    def infer(self, frame_packet: FramePacket) -> List[Detection]:
        """
        Executes object detection on an incremental FramePacket.
        Converts all raw results strictly into normalized Detection objects.
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
            with torch.inference_mode():
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

        # Optional features extraction if model outputs masks/keypoints/obb/tracking
        has_masks = getattr(res, "masks", None) is not None
        has_keypoints = getattr(res, "keypoints", None) is not None
        has_obb = getattr(res, "obb", None) is not None

        for idx, box in enumerate(boxes):
            xyxy = box.xyxy[0].tolist()  # [x_min, y_min, x_max, y_max]
            conf = float(box.conf[0])
            cls_idx = int(box.cls[0])
            raw_class_name = names_dict.get(cls_idx, f"class_{cls_idx}")

            # Optional tracker ID if model performed tracking internally
            track_id = int(box.id[0]) if (getattr(box, "id", None) is not None and box.id is not None) else None

            # Optional segmentation mask
            mask_data = None
            if has_masks and idx < len(res.masks):
                try:
                    mask_data = res.masks.xy[idx].tolist() if hasattr(res.masks, "xy") else None
                except Exception:
                    mask_data = None

            # Optional keypoints
            kp_data = None
            if has_keypoints and idx < len(res.keypoints):
                try:
                    raw_kp = res.keypoints.data[idx] if hasattr(res.keypoints, "data") else None
                    if raw_kp is not None:
                        kp_data = parse_human_pose(raw_kp)
                except Exception:
                    kp_data = None

            # Optional oriented bounding box
            obb_data = None
            if has_obb and idx < len(res.obb):
                try:
                    obb_data = res.obb.xywhr[idx].tolist() if hasattr(res.obb, "xywhr") else None
                except Exception:
                    obb_data = None

            det = self.create_unified_detection(
                frame_packet=frame_packet,
                bbox_xyxy=(float(xyxy[0]), float(xyxy[1]), float(xyxy[2]), float(xyxy[3])),
                confidence=conf,
                raw_class_name=raw_class_name,
                class_index=cls_idx,
                tracking_id=track_id,
                mask=mask_data,
                obb=obb_data,
                keypoints=kp_data,
                inference_time_ms=elapsed * 1000.0,
            )
            detections.append(det)

        return detections


class YOLOv8Detector(YOLOBaseAdapter):
    """
    Adapter for Ultralytics YOLOv8 real-time detection family.
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
        super().__init__(
            model_name=model_name,
            model_type="yolov8",
            model_path=model_path,
            confidence_threshold=confidence_threshold,
            iou_threshold=iou_threshold,
            input_size=input_size,
            device=device,
            max_detections=max_detections,
        )


class YOLO11Detector(YOLOBaseAdapter):
    """
    Adapter for Ultralytics YOLO11 real-time detection family.
    """

    def __init__(
        self,
        model_name: str = "yolo11n",
        model_path: Optional[str] = None,
        confidence_threshold: float = 0.35,
        iou_threshold: float = 0.45,
        input_size: Tuple[int, int] = (640, 640),
        device: Optional[str] = None,
        max_detections: int = 100,
    ):
        super().__init__(
            model_name=model_name,
            model_type="yolo11",
            model_path=model_path,
            confidence_threshold=confidence_threshold,
            iou_threshold=iou_threshold,
            input_size=input_size,
            device=device,
            max_detections=max_detections,
        )


class YOLO26Detector(YOLOBaseAdapter):
    """
    Adapter for Ultralytics YOLO26 real-time detection family.

    ARCHITECTURAL MANDATE:
    Integrated STRICTLY for 2D bounding-box object detection.
    YOLO26 does not directly perform loitering, approach, border crossing,
    or suspicious behavior detection. All behavior intelligence is derived
    strictly downstream in SpatialEngine, BehaviorEngine, and FusionEngine.
    """

    def __init__(
        self,
        model_name: str = "yolo26n",
        model_path: Optional[str] = None,
        confidence_threshold: float = 0.35,
        iou_threshold: float = 0.45,
        input_size: Tuple[int, int] = (640, 640),
        device: Optional[str] = None,
        max_detections: int = 100,
    ):
        super().__init__(
            model_name=model_name,
            model_type="yolo26",
            model_path=model_path,
            confidence_threshold=confidence_threshold,
            iou_threshold=iou_threshold,
            input_size=input_size,
            device=device,
            max_detections=max_detections,
        )


class RTDETRDetector(BaseDetectorAdapter):
    """
    Adapter for Real-Time DEtection TRansformer (RT-DETR) architectures.
    Provides transformer-based end-to-end detection for high-fidelity border surveillance.
    """

    def __init__(
        self,
        model_name: str = "rtdetr-l",
        model_path: Optional[str] = None,
        confidence_threshold: float = 0.35,
        iou_threshold: float = 0.45,
        input_size: Tuple[int, int] = (640, 640),
        device: Optional[str] = None,
        max_detections: int = 100,
    ):
        resolved_path = resolve_model_weights("rtdetr", model_path)
        super().__init__(
            model_name=model_name,
            model_type="rtdetr",
            model_path=resolved_path,
            confidence_threshold=confidence_threshold,
            iou_threshold=iou_threshold,
            input_size=input_size,
            device=device,
            max_detections=max_detections,
        )

    def load(self, model_path: Optional[str] = None) -> bool:
        target_path = model_path or self.model_path
        t0 = time.perf_counter()
        rss_before = self._get_rss_mb()

        # Check explicit path existence if specified as a custom filesystem path
        if target_path and ("/" in target_path or "\\" in target_path or target_path.startswith(".")):
            if not os.path.exists(target_path):
                raise ModelNotFoundError(
                    f"RT-DETR weights file '{target_path}' not found. Please ensure weights exist in models/detector/ or supply MODEL_WEIGHTS."
                )

        try:
            import ultralytics
            try:
                from ultralytics import RTDETR
                self._model = RTDETR(target_path)
            except ImportError:
                from ultralytics import YOLO
                self._model = YOLO(target_path)

            self._is_loaded = True
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            rss_after = self._get_rss_mb()
            logger.info(
                f"[RESOURCE] rtdetr.load: rss_before={rss_before:.1f}MB, rss_after={rss_after:.1f}MB, "
                f"delta={rss_after - rss_before:+.1f}MB, elapsed={elapsed_ms:.1f}ms"
            )
            logger.info(f"RT-DETR model '{self.model_name}' loaded successfully.")
            return True
        except ModelNotFoundError:
            raise
        except Exception as exc:
            self._is_loaded = False
            exc_str = str(exc).lower()
            if any(term in exc_str for term in ("unsupported", "not implemented", "invalid model", "not a valid", "corrupted")):
                msg = (
                    f"Installed Ultralytics version ({getattr(ultralytics, '__version__', 'unknown')}) "
                    f"does not support requested model family 'rtdetr' (path: '{target_path}'): {exc}"
                )
                logger.error(msg)
                raise ModelCompatibilityError(msg) from exc

            logger.error(f"Failed to load RT-DETR model from '{target_path}': {exc}")
            raise ModelLoadError(f"Cannot load RT-DETR model '{target_path}': {exc}") from exc

    def warmup(self, input_size: Optional[Tuple[int, int]] = None) -> bool:
        if not self._is_loaded or self._model is None:
            self.load()

        warmup_size = input_size or self.input_size
        logger.info(f"Warming up RT-DETR detector with dummy {warmup_size[0]}x{warmup_size[1]} frame...")
        try:
            dummy_image = np.zeros((warmup_size[1], warmup_size[0], 3), dtype=np.uint8)
            with torch.inference_mode():
                self._model.predict(
                    source=dummy_image,
                    conf=self.confidence_threshold,
                    device=self.device,
                    verbose=False,
                )
            self._warmup_done = True
            logger.info("RT-DETR warmup completed successfully.")
            return True
        except Exception as exc:
            logger.error(f"RT-DETR warmup forward pass failed: {exc}")
            raise ModelInferenceError(f"RT-DETR warmup failed: {exc}") from exc

    def infer(self, frame_packet: FramePacket) -> List[Detection]:
        if frame_packet is None or frame_packet.image is None:
            raise InvalidInputError("Cannot run inference on None or empty FramePacket")

        if not self._is_loaded or self._model is None:
            self.load()
            if not self._warmup_done:
                self.warmup()

        start_time = time.perf_counter()
        try:
            with torch.inference_mode():
                results = self._model.predict(
                    source=frame_packet.image,
                    conf=self.confidence_threshold,
                    device=self.device,
                    max_det=self.max_detections,
                    verbose=False,
                )
        except Exception as exc:
            raise ModelInferenceError(f"RT-DETR inference failed: {exc}") from exc

        elapsed = time.perf_counter() - start_time
        self._total_inferences += 1
        self._total_inference_time_sec += elapsed

        detections: List[Detection] = []
        if not results or results[0].boxes is None:
            return detections

        res = results[0]
        names_dict = res.names or {}

        for box in res.boxes:
            xyxy = box.xyxy[0].tolist()
            conf = float(box.conf[0])
            cls_idx = int(box.cls[0])
            raw_class_name = names_dict.get(cls_idx, f"class_{cls_idx}")

            det = self.create_unified_detection(
                frame_packet=frame_packet,
                bbox_xyxy=(float(xyxy[0]), float(xyxy[1]), float(xyxy[2]), float(xyxy[3])),
                confidence=conf,
                raw_class_name=raw_class_name,
                class_index=cls_idx,
                inference_time_ms=elapsed * 1000.0,
            )
            detections.append(det)

        return detections


class MockDetector(BaseDetectorAdapter):
    """
    Deterministic mock detector adapter for fast CI/CD and unit testing
    without PyTorch weights or GPU dependencies.
    """

    def __init__(
        self,
        model_name: str = "mock_detector",
        model_type: str = "mock",
        mock_detections: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ):
        super().__init__(model_name=model_name, model_type=model_type, **kwargs)
        self.mock_detections = mock_detections or []

    def load(self, model_path: Optional[str] = None) -> bool:
        self._is_loaded = True
        return True

    def warmup(self, input_size: Optional[Tuple[int, int]] = None) -> bool:
        self._warmup_done = True
        return True

    def infer(self, frame_packet: FramePacket) -> List[Detection]:
        if frame_packet is None or frame_packet.image is None:
            raise InvalidInputError("Cannot run inference on empty frame")

        self._total_inferences += 1
        self._total_inference_time_sec += 0.001

        dets: List[Detection] = []
        for item in self.mock_detections:
            conf = float(item.get("confidence", 0.90))
            if conf < self.confidence_threshold:
                continue

            raw_kp_item = item.get("keypoints")
            parsed_kp = parse_human_pose(raw_kp_item) if raw_kp_item is not None else None

            det = self.create_unified_detection(
                frame_packet=frame_packet,
                bbox_xyxy=item.get("bbox_xyxy", (50.0, 50.0, 150.0, 200.0)),
                confidence=conf,
                raw_class_name=item.get("class_name", "person"),
                tracking_id=item.get("tracking_id"),
                mask=item.get("mask"),
                obb=item.get("obb"),
                keypoints=parsed_kp,
                depth=item.get("depth"),
            )
            dets.append(det)
        return dets


class YOLO26PoseDetector(YOLOBaseAdapter):
    """
    Optional Perception Adapter for Ultralytics YOLO26 Pose family.
    Extracts 2D human bounding boxes AND 17 human pose keypoints (nose, eyes, ears,
    shoulders, elbows, wrists, hips, knees, ankles).

    Architectural Guardrails:
    1. YOLO26 Pose provides human pose keypoints. It does NOT directly classify border behaviour.
    2. Optional pose keypoints are attached to the normalized Detection record for downstream tracking.
    3. Behaviour intelligence (approach, loitering, crossing) remains strictly grounded in
       spatial zones, trajectories, and border geometry.
    4. If weights are missing, raises ModelNotFoundError with actionable remediation.
    5. If architecture cannot be instantiated by the runtime, raises ModelCompatibilityError.
    """

    def __init__(
        self,
        model_name: str = "yolo26n-pose",
        model_path: Optional[str] = None,
        confidence_threshold: float = 0.35,
        iou_threshold: float = 0.45,
        input_size: Tuple[int, int] = (640, 640),
        device: Optional[str] = None,
        max_detections: int = 100,
    ):
        resolved_path = resolve_model_weights("yolo26-pose", model_path)
        super().__init__(
            model_name=model_name,
            model_type="yolo26-pose",
            model_path=resolved_path,
            confidence_threshold=confidence_threshold,
            iou_threshold=iou_threshold,
            input_size=input_size,
            device=device,
            max_detections=max_detections,
        )


class YOLOv8PoseDetector(YOLOBaseAdapter):
    """
    Baseline Adapter for Ultralytics YOLOv8 Pose family (e.g. yolov8n-pose.pt).
    """

    def __init__(
        self,
        model_name: str = "yolov8n-pose",
        model_path: Optional[str] = None,
        confidence_threshold: float = 0.35,
        iou_threshold: float = 0.45,
        input_size: Tuple[int, int] = (640, 640),
        device: Optional[str] = None,
        max_detections: int = 100,
    ):
        resolved_path = resolve_model_weights("yolov8-pose", model_path)
        super().__init__(
            model_name=model_name,
            model_type="yolov8-pose",
            model_path=resolved_path,
            confidence_threshold=confidence_threshold,
            iou_threshold=iou_threshold,
            input_size=input_size,
            device=device,
            max_detections=max_detections,
        )


class ObjectDetector(YOLOv8Detector):
    """
    Standard Object Detector implementation for IBVAP baseline perception.
    Maintains 100% backward compatibility for existing callers.
    """
    pass


# Register default detector adapters
try:
    from .registry import register_detector
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
except Exception:
    pass


__all__ = [
    "DetectorInterface",
    "BaseDetectorAdapter",
    "YOLOBaseAdapter",
    "YOLOv8Detector",
    "YOLO11Detector",
    "YOLO26Detector",
    "YOLO26PoseDetector",
    "YOLOv8PoseDetector",
    "RTDETRDetector",
    "MockDetector",
    "ObjectDetector",
    "parse_human_pose",
]
