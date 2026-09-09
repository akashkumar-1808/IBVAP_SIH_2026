import logging
from typing import List, Dict, Tuple, Optional, Any
from datetime import datetime, timezone
import numpy as np

from .base import TrackerInterface
from .schemas import (
    TrackState,
    TrackStatus,
    TargetClass,
    BoundingBox,
    TrajectoryPoint,
    Detection,
)
from .kalman import KalmanBoxTracker
from .matching import compute_iou_matrix, linear_assignment
from .exceptions import InvalidDetectionError

logger = logging.getLogger(__name__)


class STrack:
    """
    Internal single-object track representation managing Kalman filter,
    state lifecycle, trajectory point buffer, and velocity.
    """

    def __init__(
        self,
        track_id: int,
        camera_id: str,
        detection: Detection,
        max_trajectory_length: int = 60,
    ):
        self.track_id = track_id
        self.camera_id = camera_id
        self.class_id = detection.class_id
        self.max_trajectory_length = max_trajectory_length

        bbox_arr = np.array([
            detection.bbox.x_min,
            detection.bbox.y_min,
            detection.bbox.x_max,
            detection.bbox.y_max,
        ], dtype=np.float32)

        self.kalman = KalmanBoxTracker(bbox_arr)
        self.bbox_arr = bbox_arr

        self.age_frames = 1
        self.missed_frames = 0
        self.hits = 1
        self.status = TrackStatus.CANDIDATE

        self.first_seen = detection.timestamp_utc
        self.last_seen = detection.timestamp_utc

        self.confidence_history: List[float] = [detection.confidence]
        cx = float((detection.bbox.x_min + detection.bbox.x_max) / 2.0)
        cy = float((detection.bbox.y_min + detection.bbox.y_max) / 2.0)
        self.center_xy = (cx, cy)
        self.velocity_xy = (0.0, 0.0)
        self.speed_pixels_per_sec = 0.0
        self.keypoints = detection.keypoints

        self.trajectory: List[TrajectoryPoint] = [
            TrajectoryPoint(
                x=cx,
                y=cy,
                timestamp_utc=detection.timestamp_utc,
                frame_id=detection.frame_id,
            )
        ]

    def predict(self) -> np.ndarray:
        """Executes Kalman predict step."""
        self.bbox_arr = self.kalman.predict()
        self.age_frames += 1
        return self.bbox_arr

    def update(self, detection: Detection, frame_id: int):
        """Updates track with a new matched detection."""
        new_bbox_arr = np.array([
            detection.bbox.x_min,
            detection.bbox.y_min,
            detection.bbox.x_max,
            detection.bbox.y_max,
        ], dtype=np.float32)

        self.bbox_arr = self.kalman.update(new_bbox_arr)
        self.hits += 1
        self.missed_frames = 0
        self.last_seen = detection.timestamp_utc
        self.class_id = detection.class_id  # update class if high-confidence refined

        if detection.keypoints is not None:
            self.keypoints = detection.keypoints

        # Bounded confidence history (max 30 entries)
        self.confidence_history.append(detection.confidence)
        if len(self.confidence_history) > 30:
            self.confidence_history.pop(0)

        # Center point & Velocity calculation
        new_cx = float((self.bbox_arr[0] + self.bbox_arr[2]) / 2.0)
        new_cy = float((self.bbox_arr[1] + self.bbox_arr[3]) / 2.0)

        if self.trajectory:
            prev_pt = self.trajectory[-1]
            dt = (detection.timestamp_utc - prev_pt.timestamp_utc).total_seconds()
            if dt > 1e-4:
                vx = (new_cx - prev_pt.x) / dt
                vy = (new_cy - prev_pt.y) / dt
                self.velocity_xy = (float(vx), float(vy))
                self.speed_pixels_per_sec = float(np.sqrt(vx**2 + vy**2))

        self.center_xy = (new_cx, new_cy)

        # Append trajectory point with bounded length
        self.trajectory.append(
            TrajectoryPoint(
                x=new_cx,
                y=new_cy,
                timestamp_utc=detection.timestamp_utc,
                frame_id=frame_id,
            )
        )
        if len(self.trajectory) > self.max_trajectory_length:
            self.trajectory.pop(0)

    def mark_missed(self):
        """Marks track as missed in the current frame."""
        self.missed_frames += 1
        if self.status == TrackStatus.TRACKED:
            self.status = TrackStatus.LOST

    def to_schema(self) -> TrackState:
        """Converts internal STrack into canonical TrackState schema."""
        return TrackState(
            track_id=self.track_id,
            camera_id=self.camera_id,
            class_id=self.class_id,
            bbox=BoundingBox(
                x_min=float(self.bbox_arr[0]),
                y_min=float(self.bbox_arr[1]),
                x_max=float(self.bbox_arr[2]),
                y_max=float(self.bbox_arr[3]),
            ),
            center_xy=self.center_xy,
            velocity_xy=self.velocity_xy,
            speed_pixels_per_sec=self.speed_pixels_per_sec,
            age_frames=self.age_frames,
            consecutive_invisible_frames=self.missed_frames,
            status=self.status,
            first_seen=self.first_seen,
            last_seen=self.last_seen,
            confidence_history=list(self.confidence_history),
            trajectory=list(self.trajectory),
            keypoints=self.keypoints,
        )


class ByteTrackTracker(TrackerInterface):
    """
    ByteTrack multi-object tracking implementation.
    Associates high and low confidence detections against predicted Kalman track states.
    Maintains per-camera track isolation and deterministic track IDs.
    """

    def __init__(
        self,
        camera_id: str = "default_camera",
        track_thresh: float = 0.50,
        match_thresh: float = 0.80,
        min_hits: int = 2,
        max_lost_frames: int = 30,
        max_trajectory_length: int = 60,
    ):
        self.camera_id = camera_id
        self.track_thresh = track_thresh
        self.match_thresh = match_thresh
        self.min_hits = min_hits
        self.max_lost_frames = max_lost_frames
        self.max_trajectory_length = max_trajectory_length

        self._next_track_id = 1
        self._tracked_stracks: List[STrack] = []
        self._lost_stracks: List[STrack] = []
        self._frame_count = 0

    def update(
        self,
        detections: List[Detection],
        frame_id: int,
        timestamp_utc: Optional[datetime] = None,
        camera_id: Optional[str] = None,
        recovered_track_map: Optional[Dict[int, int]] = None,
    ) -> List[TrackState]:
        """
        Updates tracks with detections from current frame using two-stage ByteTrack association.
        Optionally accepts recovered_track_map for preserving track identity across stream gaps.
        """
        if detections is None:
            raise InvalidDetectionError("Detections list cannot be None")

        self._frame_count += 1
        effective_camera = camera_id or self.camera_id
        ts = timestamp_utc or datetime.now(timezone.utc)

        # 1. Separate detections into high and low confidence pools
        high_dets: List[Detection] = []
        low_dets: List[Detection] = []

        for d in detections:
            if d.confidence >= self.track_thresh:
                high_dets.append(d)
            elif d.confidence >= 0.10:
                low_dets.append(d)

        # 2. Predict Kalman state for all existing active & lost tracks
        all_existing = self._tracked_stracks + self._lost_stracks
        for st in all_existing:
            st.predict()

        # -------------------------------------------------------------
        # Stage 1: Match high-confidence detections with active/lost tracks
        # -------------------------------------------------------------
        track_boxes = np.array([st.bbox_arr for st in all_existing], dtype=np.float32) if all_existing else np.empty((0, 4))
        high_det_boxes = np.array([
            [d.bbox.x_min, d.bbox.y_min, d.bbox.x_max, d.bbox.y_max] for d in high_dets
        ], dtype=np.float32) if high_dets else np.empty((0, 4))

        cost_matrix_1 = 1.0 - compute_iou_matrix(track_boxes, high_det_boxes)
        matches_1, unmatched_tracks_1, unmatched_high_dets = linear_assignment(cost_matrix_1, thresh=self.match_thresh)

        for track_idx, det_idx in matches_1:
            track = all_existing[track_idx]
            det = high_dets[det_idx]
            track.update(det, frame_id)
            if track.hits >= self.min_hits:
                track.status = TrackStatus.TRACKED

        # -------------------------------------------------------------
        # Stage 2: Match low-confidence detections with remaining unmatched active tracks
        # -------------------------------------------------------------
        remaining_tracked = [all_existing[i] for i in unmatched_tracks_1 if all_existing[i].status == TrackStatus.TRACKED]
        low_det_boxes = np.array([
            [d.bbox.x_min, d.bbox.y_min, d.bbox.x_max, d.bbox.y_max] for d in low_dets
        ], dtype=np.float32) if low_dets else np.empty((0, 4))

        cost_matrix_2 = 1.0 - compute_iou_matrix(
            np.array([st.bbox_arr for st in remaining_tracked], dtype=np.float32) if remaining_tracked else np.empty((0, 4)),
            low_det_boxes,
        )
        matches_2, unmatched_tracks_2, _ = linear_assignment(cost_matrix_2, thresh=0.50)

        for track_idx, det_idx in matches_2:
            track = remaining_tracked[track_idx]
            det = low_dets[det_idx]
            track.update(det, frame_id)

        # -------------------------------------------------------------
        # Mark unmatched tracks as missed / lost
        # -------------------------------------------------------------
        unmatched_tracks_final = [
            remaining_tracked[i] for i in unmatched_tracks_2
        ] + [
            all_existing[i] for i in unmatched_tracks_1 if all_existing[i] not in remaining_tracked and i not in [m[0] for m in matches_1]
        ]

        for track in unmatched_tracks_final:
            track.mark_missed()

        # -------------------------------------------------------------
        # Initialize new candidate tracks from unmatched high-confidence detections
        # -------------------------------------------------------------
        for det_idx in unmatched_high_dets:
            det = high_dets[det_idx]
            is_recovered = False
            if recovered_track_map and det_idx in recovered_track_map:
                assigned_id = recovered_track_map[det_idx]
                is_recovered = True
                # Deduplicate: remove older missed track with this assigned ID
                all_existing = [st for st in all_existing if st.track_id != assigned_id]
            else:
                assigned_id = self._next_track_id
                self._next_track_id += 1

            new_track = STrack(
                track_id=assigned_id,
                camera_id=effective_camera,
                detection=det,
                max_trajectory_length=self.max_trajectory_length,
            )
            if assigned_id >= self._next_track_id:
                self._next_track_id = assigned_id + 1

            if is_recovered or self.min_hits <= 1:
                new_track.status = TrackStatus.TRACKED
            all_existing.append(new_track)

        # -------------------------------------------------------------
        # Partition into active tracked, lost, and prune expired tracks
        # -------------------------------------------------------------
        self._tracked_stracks = []
        self._lost_stracks = []

        for st in all_existing:
            if st.missed_frames > self.max_lost_frames:
                st.status = TrackStatus.EXPIRED
                continue  # pruned / expired

            if st.status == TrackStatus.TRACKED and st.missed_frames == 0:
                self._tracked_stracks.append(st)
            elif st.status == TrackStatus.CANDIDATE:
                self._tracked_stracks.append(st)
            else:
                self._lost_stracks.append(st)

        return self.get_tracks()

    def get_tracks(self) -> List[TrackState]:
        """Returns all current active and lost tracks as TrackState schemas."""
        active = [st.to_schema() for st in self._tracked_stracks]
        lost = [st.to_schema() for st in self._lost_stracks]
        return active + lost

    def get_active_tracks(self) -> List[TrackState]:
        """Returns active tracked states."""
        return [st.to_schema() for st in self._tracked_stracks if st.status == TrackStatus.TRACKED]

    def reset(self) -> None:
        """Resets all internal tracks and resets track ID sequence."""
        self._tracked_stracks.clear()
        self._lost_stracks.clear()
        self._next_track_id = 1
        self._frame_count = 0
        logger.info(f"Tracker for camera '{self.camera_id}' reset cleanly.")

    def close(self) -> None:
        """Releases tracker state."""
        self.reset()
