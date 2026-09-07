"""
Stream Health & Continuity Subsystem for IBVAP.

Monitors temporal continuity, inter-frame intervals, arrival/processing FPS,
latency, jitter, frame gaps, stale/frozen imagery, RTSP reconnection states,
and tracking recovery after short network interruptions.

Architecture Decision: DEC-0012
"""

import time
import math
import logging
from enum import Enum
from collections import deque
from datetime import datetime, timezone
from typing import Optional, List, Dict, Tuple, Any
import numpy as np
import cv2
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class StreamHealthState(str, Enum):
    """Canonical 8-state stream health lifecycle."""
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    INTERRUPTED = "INTERRUPTED"
    RECONNECTING = "RECONNECTING"
    RECOVERED = "RECOVERED"
    STALE_FROZEN = "STALE_FROZEN"
    OFFLINE = "OFFLINE"
    COMPLETED = "COMPLETED"
    # Backward-compatible state aliases
    DISCONNECTED = "DISCONNECTED"
    ONLINE = "ONLINE"


class TrackingRecoveryState(str, Enum):
    """Status of track continuity across a stream gap."""
    STABLE = "STABLE"
    RECOVERED = "RECOVERED"
    UNCERTAIN = "UNCERTAIN"
    LOST = "LOST"


class ContinuityConfig(BaseModel):
    """Configurable operational thresholds for Stream Continuity & Health."""
    expected_fps: float = Field(default=25.0, gt=0.0, description="Nominal camera source frame rate")
    interruption_timeout_s: float = Field(default=1.5, gt=0.0, description="Seconds without frame to declare INTERRUPTED")
    stale_timeout_s: float = Field(default=2.0, gt=0.0, description="Seconds of frozen image content to declare STALE_FROZEN")
    degraded_fps_ratio: float = Field(default=0.65, gt=0.0, le=1.0, description="Ratio of expected FPS below which stream is DEGRADED")
    degraded_latency_ms: float = Field(default=250.0, gt=0.0, description="Latency threshold in ms above which stream is DEGRADED")
    recovery_confirmation_frames: int = Field(default=5, ge=1, description="Consecutive healthy frames required to transition RECOVERED -> HEALTHY")
    max_track_recovery_gap_s: float = Field(default=5.0, gt=0.0, description="Maximum stream gap duration for attempting track identity recovery")
    track_recovery_max_distance_px: float = Field(default=150.0, gt=0.0, description="Maximum spatial distance for re-associating extrapolated track")
    rolling_window_s: float = Field(default=3.0, gt=0.0, description="Time window in seconds for rolling rate measurements")
    duplicate_mse_threshold: float = Field(default=0.35, ge=0.0, description="Max perceptual MSE between downsampled frames to consider duplicate")
    max_reconnect_attempts: int = Field(default=10, ge=1, description="Maximum bounded reconnect attempts before marking OFFLINE")


class StreamGapRecord(BaseModel):
    """Immutable audit record of a detected stream interruption/gap."""
    gap_id: str
    camera_id: str
    start_utc: datetime
    end_utc: Optional[datetime] = None
    duration_seconds: float = 0.0
    estimated_missed_frames: int = 0
    start_sequence_number: Optional[int] = None
    end_sequence_number: Optional[int] = None
    tracking_state_before: Dict[str, Any] = Field(default_factory=dict)
    tracking_recovery_result: TrackingRecoveryState = TrackingRecoveryState.STABLE
    recovered_track_ids: List[int] = Field(default_factory=list)


class StreamHealthMetrics(BaseModel):
    """Snapshot of real-time stream continuity metrics and downstream AI trust score."""
    camera_id: str
    state: StreamHealthState = StreamHealthState.HEALTHY
    status_reason: str = "Stream operational and within nominal tolerances"
    trust_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Downstream AI trust multiplier [0.0 - 1.0]")
    
    # Rates and Timers
    capture_fps_rolling: float = 0.0
    processing_fps_rolling: float = 0.0
    target_fps: float = 25.0
    frame_age_ms: float = 0.0
    latency_ms: float = 0.0
    jitter_ms: float = 0.0

    # Counters
    total_frames_received: int = 0
    total_frames_dropped: int = 0
    total_frames_processed: int = 0
    reconnect_count: int = 0
    interruption_count: int = 0
    dropped_frames_total: int = 0
    gap_count: int = 0

    # Gap & Stale telemetry
    interruption_duration_s: float = 0.0
    last_interruption_duration_s: float = 0.0
    stale_duration_s: float = 0.0
    last_gap_frames_missed: int = 0
    tracking_recovery_state: TrackingRecoveryState = TrackingRecoveryState.STABLE

    # Diagnostic Flags
    is_frozen: bool = False
    is_duplicate: bool = False
    consecutive_healthy_frames: int = 0

    # Timestamps
    last_frame_received_utc: Optional[datetime] = None
    last_frame_processed_utc: Optional[datetime] = None
    updated_at: datetime = Field(default_factory=_utc_now)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes metrics to dictionary contract for telemetry and API responses."""
        return {
            "camera_id": self.camera_id,
            "state": self.state.value if hasattr(self.state, "value") else str(self.state),
            "status_reason": self.status_reason,
            "capture_fps": self.capture_fps_rolling,
            "processing_fps": self.processing_fps_rolling,
            "latency_ms": self.latency_ms,
            "jitter_ms": self.jitter_ms,
            "frame_age_ms": self.frame_age_ms,
            "dropped_frames_total": self.total_frames_dropped,
            "trust_score": self.trust_score,
            "is_frozen": self.is_frozen,
            "consecutive_healthy_frames": self.consecutive_healthy_frames,
            "last_interruption_duration": self.last_interruption_duration_s,
            "gap_count": self.gap_count,
        }


class StreamContinuityManager:
    """
    Production-grade Stream Health & Continuity Manager.
    
    Maintains per-camera temporal continuity, detects gaps, detects frozen/stale
    imagery, computes rolling rates without misleading instantaneous spikes, manages
    the health state machine with hysteresis, evaluates track recovery after interruptions,
    and calculates downstream AI trust scores.
    """

    def __init__(self, camera_id: str, config: Optional[ContinuityConfig] = None):
        self.camera_id = camera_id
        self.config = config or ContinuityConfig()

        # State Machine
        self._state: StreamHealthState = StreamHealthState.HEALTHY
        self._status_reason: str = "Stream initialized"
        self._trust_score: float = 1.0
        self._tracking_recovery_state: TrackingRecoveryState = TrackingRecoveryState.STABLE

        # Timestamps & Tracking
        self._last_arrival_mono: float = time.monotonic()
        self._last_arrival_utc: datetime = _utc_now()
        self._last_processed_mono: float = time.monotonic()
        self._last_processed_utc: datetime = _utc_now()
        self._interruption_start_mono: Optional[float] = None
        self._last_interruption_duration: float = 0.0
        self._stale_start_mono: Optional[float] = None
        self._last_stale_duration: float = 0.0

        # Sequence & Inter-frame Interval
        self._last_seq_num: Optional[int] = None
        self._last_inter_frame_interval_s: float = 1.0 / self.config.expected_fps
        self._inter_frame_intervals: deque = deque(maxlen=60)
        self._last_gap_missed_frames: int = 0

        # Rolling Windows for Rates (Mono timestamps)
        self._arrival_window: deque = deque(maxlen=150)
        self._processing_window: deque = deque(maxlen=150)
        self._latencies_ms: deque = deque(maxlen=60)

        # Frozen / Perceptual Check Cache
        self._last_downsampled_thumb: Optional[np.ndarray] = None
        self._last_source_ts: Optional[datetime] = None
        self._is_frozen: bool = False
        self._is_duplicate: bool = False

        # Confirmation / Hysteresis
        self._consecutive_healthy: int = 0
        self._consecutive_errors: int = 0

        # Counters
        self._total_received: int = 0
        self._total_dropped: int = 0
        self._total_processed: int = 0
        self._reconnect_count: int = 0
        self._interruption_count: int = 0

        # Gap History & Track Snapshots
        self._gap_history: deque = deque(maxlen=30)
        self._pre_gap_track_snapshots: Dict[int, Dict[str, Any]] = {}
        self._recovered_track_ids: List[int] = []

    # ──────────────────────────────────────────────────────────────────────────
    # Properties
    # ──────────────────────────────────────────────────────────────────────────

    @property
    def state(self) -> StreamHealthState:
        return self._state

    @property
    def is_frozen(self) -> bool:
        return self._is_frozen

    @property
    def trust_score(self) -> float:
        return self._trust_score

    @property
    def last_interruption_duration(self) -> float:
        return self._last_interruption_duration

    @property
    def tracking_recovery_state(self) -> TrackingRecoveryState:
        return self._tracking_recovery_state

    # ──────────────────────────────────────────────────────────────────────────
    # Frame Ingestion & Continuity Inspection
    # ──────────────────────────────────────────────────────────────────────────

    def on_frame_received(
        self,
        frame_image: Any,
        sequence_number: Optional[int] = None,
        timestamp_utc: Optional[datetime] = None,
        source_fps: Optional[float] = None,
    ) -> StreamHealthMetrics:
        """
        Called immediately upon receiving a frame from the capture source.
        Analyzes inter-frame interval, sequence gaps, and perceptual freshness.
        Accepts either a FramePacket or (image, sequence_number, timestamp_utc, source_fps).
        """
        if hasattr(frame_image, "image"):
            # Unpack from FramePacket
            pkt = frame_image
            frame_image = pkt.image
            sequence_number = getattr(pkt, "sequence_number", None) or getattr(pkt, "frame_id", sequence_number)
            timestamp_utc = getattr(pkt, "timestamp_utc", timestamp_utc)
            source_fps = getattr(pkt, "source_fps", source_fps)

        now_mono = time.monotonic()
        now_utc = timestamp_utc or _utc_now()
        self._total_received += 1
        self._arrival_window.append(now_mono)

        # Dynamic expected FPS update if source advertises it
        if source_fps and source_fps > 0 and abs(source_fps - self.config.expected_fps) > 2.0:
            self.config.expected_fps = float(source_fps)

        # 1. Measure Inter-Frame Interval & Gaps
        if timestamp_utc is not None and self._last_arrival_utc is not None:
            utc_diff = (now_utc - self._last_arrival_utc).total_seconds()
            if utc_diff > 0:
                inter_frame_s = utc_diff
            else:
                inter_frame_s = max(0.0001, now_mono - self._last_arrival_mono)
        else:
            inter_frame_s = max(0.0001, now_mono - self._last_arrival_mono)

        self._last_inter_frame_interval_s = inter_frame_s
        self._inter_frame_intervals.append(inter_frame_s)

        # Sequence gap detection
        missed_frames = 0
        if sequence_number is not None and self._last_seq_num is not None:
            seq_diff = sequence_number - self._last_seq_num
            if seq_diff > 1:
                missed_frames = seq_diff - 1
        elif inter_frame_s > (1.5 / self.config.expected_fps):
            # Time-based estimate of missing intervals
            estimated_slots = round(inter_frame_s * self.config.expected_fps)
            if estimated_slots > 1:
                missed_frames = estimated_slots - 1

        if missed_frames > 0:
            self._total_dropped += missed_frames
            self._last_gap_missed_frames = missed_frames
            logger.info(
                f"[STREAM_GAP] Camera '{self.camera_id}': gap of {inter_frame_s*1000.0:.1f}ms detected, "
                f"estimated missed frames: {missed_frames}"
            )
            # Record audit gap record
            gap_record = StreamGapRecord(
                gap_id=f"gap_{int(now_mono*1000)}_{self.camera_id}",
                camera_id=self.camera_id,
                start_utc=self._last_arrival_utc,
                end_utc=now_utc,
                duration_seconds=inter_frame_s,
                estimated_missed_frames=missed_frames,
                start_sequence_number=self._last_seq_num,
                end_sequence_number=sequence_number,
                tracking_state_before={
                    t_id: {"class_id": snap.get("class_id"), "center_xy": snap.get("center_xy")}
                    for t_id, snap in self._pre_gap_track_snapshots.items()
                },
            )
            self._gap_history.append(gap_record)
        else:
            self._last_gap_missed_frames = 0

        self._last_seq_num = sequence_number
        self._last_arrival_mono = now_mono
        self._last_arrival_utc = now_utc

        # 2. Perceptual Freshness Check (Frozen / Duplicate Detection)
        self._is_duplicate = False
        if frame_image is not None and frame_image.size > 0:
            self._check_perceptual_freshness(frame_image, now_utc, now_mono)

        # 3. Interruption Recovery Transition
        if self._state in (StreamHealthState.INTERRUPTED, StreamHealthState.RECONNECTING):
            gap_duration = (now_mono - self._interruption_start_mono) if self._interruption_start_mono else inter_frame_s
            self._last_interruption_duration = gap_duration
            self._interruption_start_mono = None
            self._state = StreamHealthState.RECOVERED
            self._status_reason = f"Stream re-established after {gap_duration:.2f}s interruption. Confirming continuity..."
            self._consecutive_healthy = 0
            logger.info(f"[STREAM_RECOVERED] Camera '{self.camera_id}': {self._status_reason}")

        # 4. Evaluate State Machine based on Current Observation
        self._evaluate_state(now_mono)
        return self.get_metrics()

    def _check_perceptual_freshness(self, frame_image: np.ndarray, frame_ts: datetime, now_mono: float) -> None:
        """
        Computes ultra-fast perceptual thumbnail (32x18 grayscale) to detect
        frozen imagery or duplicated frames without expensive full-frame computation (< 0.05ms).
        """
        try:
            h, w = frame_image.shape[:2]
            # Downsample to 32x18 (16:9 aspect) grayscale thumbnail
            if len(frame_image.shape) == 3 and frame_image.shape[2] == 3:
                gray = cv2.cvtColor(frame_image, cv2.COLOR_BGR2GRAY)
            else:
                gray = frame_image
            thumb = cv2.resize(gray, (32, 18), interpolation=cv2.INTER_AREA)

            if self._last_downsampled_thumb is not None:
                # Mean Squared Error between consecutive thumbnails
                diff = cv2.absdiff(self._last_downsampled_thumb, thumb)
                mse = float(np.mean(diff))

                # Check if image content has not changed at all
                if mse <= self.config.duplicate_mse_threshold:
                    self._is_duplicate = True
                    if self._stale_start_mono is None:
                        self._stale_start_mono = now_mono
                    stale_dur = now_mono - self._stale_start_mono
                    self._last_stale_duration = stale_dur

                    if stale_dur >= self.config.stale_timeout_s:
                        self._is_frozen = True
                        if self._state != StreamHealthState.STALE_FROZEN:
                            self._state = StreamHealthState.STALE_FROZEN
                            self._status_reason = f"Frozen stream: video content unchanged for {stale_dur:.1f}s"
                            logger.warning(f"[STREAM_FROZEN] Camera '{self.camera_id}': {self._status_reason}")
                else:
                    # New distinct frame content arrived
                    if self._is_frozen:
                        logger.info(f"[STREAM_UNFROZEN] Camera '{self.camera_id}': Dynamic frame motion resumed (mse={mse:.2f})")
                    self._is_frozen = False
                    self._stale_start_mono = None
                    self._last_stale_duration = 0.0

            self._last_downsampled_thumb = thumb
            self._last_source_ts = frame_ts
        except Exception as exc:
            logger.debug(f"Perceptual check notice on camera '{self.camera_id}': {exc}")

    # ──────────────────────────────────────────────────────────────────────────
    # Frame Processing Lifecycle & Latency
    # ──────────────────────────────────────────────────────────────────────────

    def on_frame_processed(
        self,
        processing_latency_ms: Any = 0.0,
        frame_timestamp_utc: Optional[datetime] = None,
    ) -> StreamHealthMetrics:
        """Called when a frame completes downstream AI inference and evidence packaging."""
        # Handle parameter order polymorphism: (latency_ms) or (timestamp, latency_ms)
        if isinstance(processing_latency_ms, datetime):
            frame_timestamp_utc, processing_latency_ms = processing_latency_ms, (frame_timestamp_utc or 0.0)
        elif processing_latency_ms is None:
            processing_latency_ms = 0.0

        now_mono = time.monotonic()
        now_utc = frame_timestamp_utc or _utc_now()
        self._total_processed += 1
        self._processing_window.append(now_mono)
        self._last_processed_mono = now_mono
        self._last_processed_utc = now_utc

        # Latency & Age
        self._latencies_ms.append(float(processing_latency_ms))
        self._evaluate_state(now_mono)
        return self.get_metrics()

    # ──────────────────────────────────────────────────────────────────────────
    # Interruption & Reconnection Lifecycle Hooks
    # ──────────────────────────────────────────────────────────────────────────

    def on_interruption_detected(self, reason: str = "Frame arrival timeout") -> None:
        """Called when no frames arrive or the socket connection drops."""
        if self._state not in (StreamHealthState.INTERRUPTED, StreamHealthState.RECONNECTING, StreamHealthState.OFFLINE):
            self._state = StreamHealthState.INTERRUPTED
            self._status_reason = reason
            self._trust_score = 0.0
            self._interruption_count += 1
            self._interruption_start_mono = time.monotonic()
            self._consecutive_healthy = 0
            logger.warning(f"[STREAM_INTERRUPTED] Camera '{self.camera_id}': {reason}")

    def on_reconnect_attempt(self, attempt_number: int, delay_seconds: float) -> None:
        """Called when the video source begins a reconnection backoff attempt."""
        self._state = StreamHealthState.RECONNECTING
        self._trust_score = 0.0
        self._reconnect_count = attempt_number
        self._status_reason = f"Reconnecting attempt {attempt_number}/{self.config.max_reconnect_attempts} (backoff {delay_seconds:.1f}s)..."
        self._consecutive_healthy = 0
        if self._interruption_start_mono is None:
            self._interruption_start_mono = time.monotonic()
        logger.info(f"[STREAM_RECONNECTING] Camera '{self.camera_id}': {self._status_reason}")

    def on_reconnecting(self, attempt: int = 1, max_attempts: int = 10, delay_s: float = 1.0) -> None:
        """Convenience hook for starting reconnect attempt."""
        self.config.max_reconnect_attempts = max(self.config.max_reconnect_attempts, max_attempts)
        self.on_reconnect_attempt(attempt, delay_s)

    def on_reconnect_failed(self, error_message: str) -> None:
        """Called when all bounded reconnection attempts are exhausted."""
        self._state = StreamHealthState.OFFLINE
        self._status_reason = f"Camera offline: {error_message}"
        self._consecutive_healthy = 0
        logger.error(f"[STREAM_OFFLINE] Camera '{self.camera_id}': {self._status_reason}")

    def on_completed(self) -> None:
        """Called when a FileVideoSource reaches EOF. Normal analysis completion."""
        self._state = StreamHealthState.COMPLETED
        self._status_reason = "Video analysis completed successfully (EOF)"
        self._trust_score = 1.0
        logger.info(f"[STREAM_COMPLETED] Camera '{self.camera_id}': {self._status_reason}")

    # ──────────────────────────────────────────────────────────────────────────
    # State Machine & Hysteresis Evaluation
    # ──────────────────────────────────────────────────────────────────────────

    def _evaluate_state(self, now_mono: float) -> None:
        """Internal deterministic state evaluation with hysteresis."""
        # Completed or Offline are terminal until reset
        if self._state in (StreamHealthState.COMPLETED, StreamHealthState.OFFLINE):
            return

        # Check for active timeout if no frames recently
        elapsed_since_arrival = now_mono - self._last_arrival_mono
        if elapsed_since_arrival > self.config.interruption_timeout_s:
            if self._state not in (StreamHealthState.INTERRUPTED, StreamHealthState.RECONNECTING):
                self.on_interruption_detected(f"No frames received for {elapsed_since_arrival:.2f}s")
            return

        # Check if currently frozen
        if self._is_frozen:
            self._state = StreamHealthState.STALE_FROZEN
            self._trust_score = 0.10
            return

        # Calculate rolling rates over window
        if len(self._inter_frame_intervals) >= 3:
            avg_interval = float(np.mean(list(self._inter_frame_intervals)[-10:]))
            capture_fps = round(1.0 / avg_interval, 1) if avg_interval > 0 else 0.0
        else:
            capture_fps = self._calc_rolling_rate(self._arrival_window, now_mono)
        avg_latency = float(np.mean(self._latencies_ms)) if self._latencies_ms else 40.0

        is_rate_degraded = (capture_fps < (self.config.expected_fps * self.config.degraded_fps_ratio))
        is_latency_degraded = (avg_latency > self.config.degraded_latency_ms)

        if self._state == StreamHealthState.RECOVERED:
            # Require confirmation frames before promoting to HEALTHY
            self._consecutive_healthy += 1
            if self._consecutive_healthy >= self.config.recovery_confirmation_frames:
                self._state = StreamHealthState.HEALTHY
                self._status_reason = "Stream continuity confirmed and stabilized"
                self._trust_score = 1.0
            else:
                self._status_reason = f"Stream recovered. Stabilizing ({self._consecutive_healthy}/{self.config.recovery_confirmation_frames})..."
                self._trust_score = 0.70
            return

        if is_rate_degraded or is_latency_degraded:
            self._state = StreamHealthState.DEGRADED
            reasons = []
            if is_rate_degraded:
                reasons.append(f"Low FPS ({capture_fps:.1f} < {self.config.expected_fps * self.config.degraded_fps_ratio:.1f})")
            if is_latency_degraded:
                reasons.append(f"High latency ({avg_latency:.1f}ms)")
            self._status_reason = f"Stream degraded: {', '.join(reasons)}"
            fps_factor = min(1.0, capture_fps / max(1.0, self.config.expected_fps))
            lat_factor = max(0.4, 1.0 - (avg_latency / 1000.0))
            self._trust_score = round(max(0.3, fps_factor * lat_factor), 2)
            self._consecutive_healthy = 0
        else:
            self._consecutive_healthy += 1
            if self._consecutive_healthy >= 3:
                self._state = StreamHealthState.HEALTHY
                self._status_reason = "Stream healthy and nominal"
                self._trust_score = 1.0

    def _calc_rolling_rate(self, window: deque, now_mono: float) -> float:
        """Calculates rolling FPS from timestamps within the rolling window."""
        cutoff = now_mono - self.config.rolling_window_s
        # Filter window
        recent = [t for t in window if t >= cutoff]
        if not recent:
            return 0.0
        window_duration = max(0.1, now_mono - recent[0])
        return round(len(recent) / window_duration, 1)

    # ──────────────────────────────────────────────────────────────────────────
    # Track Continuity & Identity Recovery After Interruption
    # ──────────────────────────────────────────────────────────────────────────

    def snapshot_tracks_before_gap(self, active_tracks: List[Any]) -> None:
        """
        Snapshots active track kinematics before a detected stream interruption
        to enable post-reconnect identity recovery.
        """
        self._pre_gap_track_snapshots.clear()
        for tr in active_tracks:
            # Extract attributes from TrackState or STrack
            t_id = getattr(tr, "track_id", None)
            if t_id is not None:
                cx, cy = getattr(tr, "center_xy", (0.0, 0.0))
                vx, vy = getattr(tr, "velocity_xy", (0.0, 0.0)) or (0.0, 0.0)
                cls_val = getattr(tr, "class_id", "person")
                cls_str = cls_val.value if hasattr(cls_val, "value") else str(cls_val).lower()
                self._pre_gap_track_snapshots[t_id] = {
                    "track_id": t_id,
                    "center_xy": (float(cx), float(cy)),
                    "velocity_xy": (float(vx), float(vy)),
                    "class_id": cls_str,
                    "timestamp_utc": _utc_now(),
                }
        if self._pre_gap_track_snapshots:
            logger.info(
                f"[TRACK_CONTINUITY] Camera '{self.camera_id}': Saved {len(self._pre_gap_track_snapshots)} "
                f"track snapshots for potential recovery."
            )

    def evaluate_track_recovery(
        self,
        candidate_detections: List[Any],
        gap_duration_seconds: float,
    ) -> Tuple[TrackingRecoveryState, Dict[int, int]]:
        """
        Evaluates candidate post-reconnection detections against pre-gap track snapshots.
        Uses motion extrapolation, spatial proximity, and class consistency.
        
        Returns:
            (TrackingRecoveryState, {candidate_detection_index: recovered_track_id})
        """
        if not self._pre_gap_track_snapshots or not candidate_detections:
            self._tracking_recovery_state = TrackingRecoveryState.STABLE
            return TrackingRecoveryState.STABLE, {}

        # 1. Check temporal bounds
        if gap_duration_seconds > self.config.max_track_recovery_gap_s:
            logger.info(
                f"[TRACK_CONTINUITY] Camera '{self.camera_id}': Gap ({gap_duration_seconds:.2f}s) "
                f"exceeds max recovery limit ({self.config.max_track_recovery_gap_s:.1f}s). Tracks expired."
            )
            self._pre_gap_track_snapshots.clear()
            self._tracking_recovery_state = TrackingRecoveryState.LOST
            return TrackingRecoveryState.LOST, {}

        recovery_matches: Dict[int, int] = {}
        matched_track_ids = set()

        # 2. Evaluate each pre-gap track against candidates
        for t_id, snap in self._pre_gap_track_snapshots.items():
            last_cx, last_cy = snap["center_xy"]
            vx, vy = snap["velocity_xy"]
            expected_cx = last_cx + (vx * gap_duration_seconds)
            expected_cy = last_cy + (vy * gap_duration_seconds)
            expected_cls = snap["class_id"]

            best_candidate_idx = None
            min_dist = float("inf")
            candidate_count_in_range = 0

            for idx, det in enumerate(candidate_detections):
                if idx in recovery_matches:
                    continue
                # Get detection center
                det_cls = getattr(det, "class_id", None) or getattr(det, "class_name", "person")
                det_cls_str = det_cls.value if hasattr(det_cls, "value") else str(det_cls).lower()
                if det_cls_str != expected_cls:
                    continue

                bbox = getattr(det, "bbox", None)
                if bbox is not None:
                    if hasattr(bbox, "x_min"):
                        cx = (bbox.x_min + bbox.x_max) / 2.0
                        cy = (bbox.y_min + bbox.y_max) / 2.0
                    elif len(bbox) == 4:
                        cx = (bbox[0] + bbox[2]) / 2.0
                        cy = (bbox[1] + bbox[3]) / 2.0
                    else:
                        continue
                else:
                    continue

                dist = math.hypot(cx - expected_cx, cy - expected_cy)
                if dist <= self.config.track_recovery_max_distance_px:
                    candidate_count_in_range += 1
                    if dist < min_dist:
                        min_dist = dist
                        best_candidate_idx = idx

            # Strict single unambiguous match criterion
            if best_candidate_idx is not None and candidate_count_in_range == 1:
                recovery_matches[best_candidate_idx] = t_id
                matched_track_ids.add(t_id)
                logger.info(
                    f"[TRACK_RECOVERED] Camera '{self.camera_id}': Track #{t_id} ({expected_cls.upper()}) "
                    f"recovered after {gap_duration_seconds:.2f}s gap (extrapolated error: {min_dist:.1f}px)"
                )
            elif candidate_count_in_range > 1:
                logger.warning(
                    f"[TRACK_UNCERTAIN] Camera '{self.camera_id}': Track #{t_id} ambiguous "
                    f"({candidate_count_in_range} candidates within range). Recovery suppressed to prevent ID swap."
                )

        # Clear consumed snapshots
        self._pre_gap_track_snapshots.clear()

        if recovery_matches:
            self._recovered_track_ids = list(recovery_matches.values())
            self._tracking_recovery_state = TrackingRecoveryState.RECOVERED
        else:
            self._tracking_recovery_state = TrackingRecoveryState.LOST

        return self._tracking_recovery_state, recovery_matches

    # ──────────────────────────────────────────────────────────────────────────
    # Metrics Export
    # ──────────────────────────────────────────────────────────────────────────

    def get_metrics(self) -> StreamHealthMetrics:
        """Returns the current canonical StreamHealthMetrics snapshot."""
        now_mono = time.monotonic()
        capture_fps = self._calc_rolling_rate(self._arrival_window, now_mono)
        proc_fps = self._calc_rolling_rate(self._processing_window, now_mono)
        avg_lat = float(np.mean(self._latencies_ms)) if self._latencies_ms else 35.0

        # Calculate jitter (standard deviation of inter-frame intervals)
        if len(self._inter_frame_intervals) >= 5:
            jitter_ms = float(np.std(self._inter_frame_intervals)) * 1000.0
        else:
            jitter_ms = 0.0

        now_utc = _utc_now()
        frame_age_ms = max(0.0, (now_utc - self._last_arrival_utc).total_seconds() * 1000.0)

        # Interruption duration if currently interrupted
        if self._state in (StreamHealthState.INTERRUPTED, StreamHealthState.RECONNECTING):
            cur_int_dur = (now_mono - self._interruption_start_mono) if self._interruption_start_mono else 0.0
        else:
            cur_int_dur = 0.0

        return StreamHealthMetrics(
            camera_id=self.camera_id,
            state=self._state,
            status_reason=self._status_reason,
            trust_score=round(self._trust_score, 2),
            capture_fps_rolling=capture_fps,
            processing_fps_rolling=proc_fps,
            target_fps=self.config.expected_fps,
            frame_age_ms=round(frame_age_ms, 1),
            latency_ms=round(avg_lat, 1),
            jitter_ms=round(jitter_ms, 1),
            total_frames_received=self._total_received,
            total_frames_dropped=self._total_dropped,
            total_frames_processed=self._total_processed,
            dropped_frames_total=self._total_dropped,
            reconnect_count=self._reconnect_count,
            interruption_count=self._interruption_count,
            gap_count=len(self._gap_history),
            interruption_duration_s=round(cur_int_dur, 2),
            last_interruption_duration_s=round(self._last_interruption_duration, 2),
            stale_duration_s=round(self._last_stale_duration, 2),
            last_gap_frames_missed=self._last_gap_missed_frames,
            tracking_recovery_state=self._tracking_recovery_state,
            is_frozen=self._is_frozen,
            is_duplicate=self._is_duplicate,
            consecutive_healthy_frames=self._consecutive_healthy,
            last_frame_received_utc=self._last_arrival_utc,
            last_frame_processed_utc=self._last_processed_utc,
            updated_at=now_utc,
        )

    def reset(self) -> None:
        """Resets manager state cleanly for a new session."""
        self._state = StreamHealthState.HEALTHY
        self._status_reason = "Stream reset"
        self._trust_score = 1.0
        self._tracking_recovery_state = TrackingRecoveryState.STABLE
        self._arrival_window.clear()
        self._processing_window.clear()
        self._latencies_ms.clear()
        self._inter_frame_intervals.clear()
        self._pre_gap_track_snapshots.clear()
        self._last_downsampled_thumb = None
        self._last_seq_num = None
        self._is_frozen = False
        self._is_duplicate = False
        self._consecutive_healthy = 0
