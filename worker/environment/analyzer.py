import logging
from typing import Dict, Optional, Any, Tuple
from dataclasses import dataclass
import cv2
import numpy as np

from .base import EnvironmentAnalyzerInterface
from .schemas import (
    EnvironmentState,
    LightingCondition,
    VisibilityQuality,
    WeatherHint,
    TerrainProfile,
)
from .metrics import (
    compute_luminance_stats,
    compute_rms_contrast,
    compute_sharpness_laplacian,
    estimate_image_noise,
    classify_lighting_condition,
    compute_aggregate_quality,
    classify_visibility_quality,
)
from .exceptions import InvalidFrameError
from ..ingestion.frame import FramePacket

logger = logging.getLogger(__name__)


@dataclass
class EnvironmentConfig:
    """Configurable threshold parameters for the Environment Engine."""
    day_threshold: float = 0.40
    dusk_threshold: float = 0.20
    low_light_threshold: float = 0.08
    blur_midpoint: float = 100.0
    ema_alpha: float = 0.25  # Exponential Moving Average factor (0 = full history, 1 = no smoothing)
    resize_analysis_width: int = 320  # Fast downsampling for statistical speedup


class CameraEnvironmentTracker:
    """Maintains smoothed temporal statistics for a single camera stream."""

    def __init__(self, camera_id: str, config: EnvironmentConfig):
        self.camera_id = camera_id
        self.config = config
        self.smoothed_brightness: Optional[float] = None
        self.smoothed_contrast: Optional[float] = None
        self.smoothed_blur: Optional[float] = None
        self.smoothed_noise: Optional[float] = None
        self.last_state: Optional[EnvironmentState] = None

    def update(
        self,
        raw_brightness: float,
        raw_contrast: float,
        raw_blur: float,
        raw_noise: float,
        timestamp_utc,
    ) -> EnvironmentState:
        alpha = self.config.ema_alpha

        if self.smoothed_brightness is None:
            self.smoothed_brightness = raw_brightness
            self.smoothed_contrast = raw_contrast
            self.smoothed_blur = raw_blur
            self.smoothed_noise = raw_noise
        else:
            self.smoothed_brightness = alpha * raw_brightness + (1.0 - alpha) * self.smoothed_brightness
            self.smoothed_contrast = alpha * raw_contrast + (1.0 - alpha) * self.smoothed_contrast
            self.smoothed_blur = alpha * raw_blur + (1.0 - alpha) * self.smoothed_blur
            self.smoothed_noise = alpha * raw_noise + (1.0 - alpha) * self.smoothed_noise

        lighting = classify_lighting_condition(
            self.smoothed_brightness,
            day_threshold=self.config.day_threshold,
            dusk_threshold=self.config.dusk_threshold,
            low_light_threshold=self.config.low_light_threshold,
        )

        quality_score = compute_aggregate_quality(
            brightness=self.smoothed_brightness,
            contrast=self.smoothed_contrast,
            blur_score=self.smoothed_blur,
            noise_estimate=self.smoothed_noise,
            blur_midpoint=self.config.blur_midpoint,
        )

        visibility = classify_visibility_quality(quality_score)

        state = EnvironmentState(
            camera_id=self.camera_id,
            timestamp_utc=timestamp_utc,
            lighting=lighting,
            brightness=round(float(self.smoothed_brightness), 4),
            contrast=round(float(self.smoothed_contrast), 4),
            blur_score=round(float(self.smoothed_blur), 2),
            noise_estimate=round(float(self.smoothed_noise), 4),
            visibility=visibility,
            weather_hint=WeatherHint.CLEAR,
            terrain_profile=TerrainProfile.OPEN_GROUND,
            quality_score=round(float(quality_score), 4),
            is_enhancement_applied=False,
            metadata={
                "raw_brightness": round(raw_brightness, 4),
                "raw_contrast": round(raw_contrast, 4),
                "raw_blur": round(raw_blur, 2),
                "raw_noise": round(raw_noise, 4),
            },
        )
        self.last_state = state
        return state

    def reset(self):
        self.smoothed_brightness = None
        self.smoothed_contrast = None
        self.smoothed_blur = None
        self.smoothed_noise = None
        self.last_state = None


class EnvironmentAnalyzer(EnvironmentAnalyzerInterface):
    """
    Production Environment Analyzer for real-time CCTV visual quality evaluation.
    Computes luminance, contrast, blur/sharpness, noise, and visibility quality per camera.
    """

    def __init__(self, config: Optional[EnvironmentConfig] = None):
        self.config = config or EnvironmentConfig()
        self._camera_trackers: Dict[str, CameraEnvironmentTracker] = {}

    def analyze(self, frame_packet: FramePacket) -> EnvironmentState:
        """
        Extracts visual quality statistics and produces a canonical EnvironmentState.
        """
        if frame_packet is None or frame_packet.image is None:
            raise InvalidFrameError("FramePacket or image cannot be None")

        image = frame_packet.image
        if image.size == 0 or len(image.shape) != 3:
            raise InvalidFrameError(f"Invalid frame image shape: {getattr(image, 'shape', None)}")

        # Convert to Grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Fast downsampling for statistical efficiency if image is large
        if self.config.resize_analysis_width and gray.shape[1] > self.config.resize_analysis_width:
            h, w = gray.shape[:2]
            scale = self.config.resize_analysis_width / float(w)
            new_h = int(round(h * scale))
            analysis_gray = cv2.resize(gray, (self.config.resize_analysis_width, new_h), interpolation=cv2.INTER_LINEAR)
        else:
            analysis_gray = gray

        # Compute raw metrics
        brightness, _, _, _ = compute_luminance_stats(analysis_gray)
        contrast = compute_rms_contrast(analysis_gray)
        blur_score = compute_sharpness_laplacian(analysis_gray)
        noise = estimate_image_noise(analysis_gray)

        # Get or create camera tracker
        camera_id = frame_packet.camera_id
        if camera_id not in self._camera_trackers:
            self._camera_trackers[camera_id] = CameraEnvironmentTracker(camera_id, self.config)

        tracker = self._camera_trackers[camera_id]
        return tracker.update(
            raw_brightness=brightness,
            raw_contrast=contrast,
            raw_blur=blur_score,
            raw_noise=noise,
            timestamp_utc=frame_packet.timestamp_utc,
        )

    def get_state(self, camera_id: str) -> Optional[EnvironmentState]:
        tracker = self._camera_trackers.get(camera_id)
        return tracker.last_state if tracker else None

    def reset(self, camera_id: Optional[str] = None) -> None:
        if camera_id:
            if camera_id in self._camera_trackers:
                self._camera_trackers[camera_id].reset()
        else:
            for tracker in self._camera_trackers.values():
                tracker.reset()
            self._camera_trackers.clear()
        logger.info(f"EnvironmentAnalyzer reset for camera(s): {camera_id or 'ALL'}")

    def close(self) -> None:
        self.reset()
