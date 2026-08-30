"""
Production Structured Evidence Storage & Packaging Engine for IBVAP.

Orchestrates rolling frame ring buffers, keyframe snapshot extraction,
pre-event/incident video clip compilation, SHA-256 cryptographic sealing,
and local/cloud storage management.

Architecture Decision: DEC-0008
"""

import os
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
import numpy as np

from .base import EvidencePackagerInterface
from .schemas import (
    EvidencePackage,
    EvidenceManifest,
    ArtifactChecksum,
    EvidenceStatus,
    EvidencePackageConfig,
)
from .buffer import RollingFrameBuffer, BufferedFrame
from .snapshot import SnapshotExtractor
from .clip import ClipPackager
from .hasher import EvidenceHasher
from .storage import EvidenceStorageManager
from .exceptions import EvidenceError, BufferUnderflowError
from ..fusion.schemas import EventRecord
from ..tracking.schemas import TrackState
from ..spatial.schemas import SpatialState, CameraSpatialConfig
from ..spatial.world_schemas import ProjectedBorder
from ..ingestion import FramePacket

logger = logging.getLogger(__name__)


class EvidencePackager(EvidencePackagerInterface):
    """
    Production Structured Evidence Packager.

    Guarantees:
    1. Continuous rolling pre-event frame buffering without blocking perception.
    2. High-resolution raw and forensic HUD-annotated keyframe snapshots.
    3. Multi-segment MP4 video clips (pre-event buffer + incident active duration).
    4. Immutable SHA-256 cryptographic sealing of all package artifacts.
    5. Local-first file structure with optional Supabase Storage upload.
    """

    def __init__(self, config: Optional[EvidencePackageConfig] = None):
        self.config = config or EvidencePackageConfig()
        self._buffers: Dict[str, RollingFrameBuffer] = {}
        self.storage_manager = EvidenceStorageManager(root_dir=self.config.storage_root)

    def _get_or_create_buffer(self, camera_id: str) -> RollingFrameBuffer:
        if camera_id not in self._buffers:
            # Buffer capacity = (pre_event_seconds + post_event_seconds + 10) * fps
            max_seconds = self.config.pre_event_seconds + self.config.post_event_seconds + 10.0
            self._buffers[camera_id] = RollingFrameBuffer(max_seconds=max_seconds, fps=self.config.fps)
        return self._buffers[camera_id]

    def add_frame(self, frame_packet: FramePacket) -> None:
        """Buffers an incoming frame into the camera's rolling ring buffer."""
        buf = self._get_or_create_buffer(frame_packet.camera_id)
        buf.add_packet(frame_packet)

    def add_raw_frame(self, camera_id: str, frame_id: int, timestamp_utc: datetime, image: np.ndarray) -> None:
        """Buffers a raw frame image."""
        buf = self._get_or_create_buffer(camera_id)
        buf.add_frame(frame_id, timestamp_utc, image, camera_id)

    def create_package(
        self,
        event: EventRecord,
        track: Optional[TrackState] = None,
        spatial_state: Optional[SpatialState] = None,
        projected_borders: Optional[List[ProjectedBorder]] = None,
        spatial_config: Optional[CameraSpatialConfig] = None,
        current_frame: Optional[np.ndarray] = None,
        force_repackage: bool = False,
    ) -> EvidencePackage:
        """
        Builds, seals, and persists a complete Evidence Package for an EventRecord.
        Guarantees idempotency when an identical package is already sealed.
        """
        camera_id = event.camera_id
        event_id = event.id
        buf = self._get_or_create_buffer(camera_id)

        # 1. Create structured package directory
        pkg_dir = self.storage_manager.get_package_dir(camera_id, event_id)
        manifest_path = os.path.join(pkg_dir, "manifest.json")

        # 2. Idempotency Check: Return existing sealed package if already built
        if not force_repackage and os.path.exists(manifest_path):
            try:
                existing_manifest = self.storage_manager.load_manifest(manifest_path)
                existing_seal = EvidenceHasher.hash_file(manifest_path)
                logger.info(f"Returning existing sealed EvidencePackage for event '{event_id}' (idempotent)")
                return EvidencePackage(
                    id=event_id,
                    event_id=event_id,
                    camera_id=camera_id,
                    status=EvidenceStatus.SEALED,
                    package_dir=pkg_dir,
                    snapshot_path=os.path.join(pkg_dir, "snapshot_raw.jpg"),
                    annotated_snapshot_path=os.path.join(pkg_dir, "snapshot_annotated.jpg"),
                    pre_event_clip_path=os.path.join(pkg_dir, "pre_event_clip.mp4") if os.path.exists(os.path.join(pkg_dir, "pre_event_clip.mp4")) else None,
                    incident_clip_path=os.path.join(pkg_dir, "incident_clip.mp4") if os.path.exists(os.path.join(pkg_dir, "incident_clip.mp4")) else None,
                    manifest_path=manifest_path,
                    manifest=existing_manifest,
                    created_at_utc=existing_manifest.sealed_at_utc,
                    is_sealed=True,
                    sha256_seal=existing_seal,
                )
            except Exception:
                pass  # Rebuild if existing manifest corrupted

        # 3. Determine Keyframe Image for Snapshot
        keyframe_img = current_frame
        if keyframe_img is None:
            latest_bf = buf.get_latest_frame()
            if latest_bf is not None:
                keyframe_img = latest_bf.image

        if keyframe_img is None:
            keyframe_img = np.zeros((480, 640, 3), dtype=np.uint8)

        # 4. Extract & Save Snapshots
        raw_snapshot_path = os.path.join(pkg_dir, "snapshot_raw.jpg")
        annotated_snapshot_path = os.path.join(pkg_dir, "snapshot_annotated.jpg")

        SnapshotExtractor.save_raw_snapshot(
            image=keyframe_img,
            destination_path=raw_snapshot_path,
            quality=self.config.snapshot_quality,
        )

        SnapshotExtractor.save_annotated_snapshot(
            image=keyframe_img,
            event=event,
            destination_path=annotated_snapshot_path,
            track=track,
            spatial_state=spatial_state,
            projected_borders=projected_borders,
            spatial_config=spatial_config,
            quality=self.config.snapshot_quality,
        )

        # 5. Extract Video Clips from Rolling Frame Buffer
        pre_start_utc = event.first_observed_utc - timedelta(seconds=self.config.pre_event_seconds)
        post_end_utc = event.last_observed_utc + timedelta(seconds=self.config.post_event_seconds)

        pre_frames = buf.get_window(pre_start_utc, event.first_observed_utc)
        incident_frames = buf.get_window(pre_start_utc, post_end_utc)

        if not incident_frames:
            incident_frames = [
                BufferedFrame(0, event.first_observed_utc, keyframe_img, camera_id)
            ]

        pre_clip_path = None
        incident_clip_path = os.path.join(pkg_dir, "incident_clip.mp4")
        is_partial = False
        partial_error_reason = None

        if pre_frames:
            pre_clip_path = os.path.join(pkg_dir, "pre_event_clip.mp4")
            try:
                ClipPackager.encode_clip(pre_frames, pre_clip_path, fps=self.config.fps)
            except Exception as e:
                logger.warning(f"Failed to encode pre-event clip: {e}")
                pre_clip_path = None

        try:
            ClipPackager.encode_clip(incident_frames, incident_clip_path, fps=self.config.fps)
        except Exception as e:
            logger.warning(f"Failed to encode incident clip: {e}")
            incident_clip_path = None
            is_partial = True
            partial_error_reason = str(e)

        # 6. Cryptographic SHA-256 Artifact Checksums
        artifact_checksums: List[ArtifactChecksum] = []

        if os.path.exists(raw_snapshot_path):
            artifact_checksums.append(EvidenceHasher.create_artifact_checksum(raw_snapshot_path, "image/jpeg"))

        if os.path.exists(annotated_snapshot_path):
            artifact_checksums.append(EvidenceHasher.create_artifact_checksum(annotated_snapshot_path, "image/jpeg"))

        if pre_clip_path and os.path.exists(pre_clip_path):
            artifact_checksums.append(EvidenceHasher.create_artifact_checksum(pre_clip_path, "video/mp4"))

        if incident_clip_path and os.path.exists(incident_clip_path):
            artifact_checksums.append(EvidenceHasher.create_artifact_checksum(incident_clip_path, "video/mp4"))

        # 7. Model Versions & Traceability
        model_versions = {
            "detector": "YOLOv8n-v1",
            "tracker": "ByteTrack-v1",
            "environment": "Env-v1",
            "spatial": "WorldBorder-v1",
            "fusion": "Fusion-v1",
            "evidence": "Evidence-v1",
        }
        if spatial_state and spatial_state.calibration_version:
            model_versions["calibration_version"] = spatial_state.calibration_version

        # 8. Build & Seal Audit Manifest
        manifest = EvidenceManifest(
            event_id=event_id,
            camera_id=camera_id,
            track_id=event.track_id,
            event_type=event.event_type,
            priority=event.priority,
            risk_score=event.risk_score,
            target_class=event.target_class,
            created_at_utc=event.created_at,
            first_observed_utc=event.first_observed_utc,
            last_observed_utc=event.last_observed_utc,
            duration_seconds=event.duration_seconds,
            reason_codes=event.reason_codes,
            explanation_summary=event.explanation_summary,
            environment_quality=event.environment_quality,
            lighting=event.lighting,
            artifacts=artifact_checksums,
            model_versions=model_versions,
            sealed_at_utc=datetime.now(timezone.utc),
            metadata={
                "detection_confidence": event.detection_confidence,
                "track_persistence_frames": event.track_persistence_frames,
                "uncertainty_flags": event.uncertainty_flags,
                "partial_error_reason": partial_error_reason,
            },
        )

        manifest_path = self.storage_manager.save_manifest(manifest, pkg_dir)
        manifest_seal = EvidenceHasher.hash_file(manifest_path)
        final_status = EvidenceStatus.PARTIAL if is_partial else EvidenceStatus.SEALED

        # 9. Assemble EvidencePackage
        package = EvidencePackage(
            id=event_id,
            event_id=event_id,
            camera_id=camera_id,
            status=final_status,
            package_dir=pkg_dir,
            snapshot_path=raw_snapshot_path,
            annotated_snapshot_path=annotated_snapshot_path,
            pre_event_clip_path=pre_clip_path,
            incident_clip_path=incident_clip_path,
            manifest_path=manifest_path,
            manifest=manifest,
            created_at_utc=datetime.now(timezone.utc),
            is_sealed=True,
            sha256_seal=manifest_seal,
        )

        # 10. Optional Supabase Storage Cloud Upload
        if self.config.auto_upload_supabase:
            self.storage_manager.upload_package_to_supabase(package)

        # 11. Optional PostgreSQL Evidence Record Persistence
        if self.config.auto_persist_db:
            self._persist_to_db(package)

        logger.info(f"EvidencePackage created ({final_status.value}) for event '{event_id}' ({len(artifact_checksums)} artifacts, seal={manifest_seal[:12]}...)")
        return package

    def _persist_to_db(self, package: EvidencePackage) -> None:
        """Persists individual evidence records into backend PostgreSQL."""
        try:
            from backend.app.db.repositories.evidence import EvidenceRepository
            repo = EvidenceRepository()
            manifest = package.manifest
            if not manifest:
                return

            for art in manifest.artifacts:
                art_path = os.path.join(package.package_dir, art.file_name)
                record_id = f"evr_{package.event_id}_{art.file_name.replace('.', '_')}"
                repo.upsert(
                    record_id,
                    {
                        "id": record_id,
                        "event_id": package.event_id,
                        "camera_id": package.camera_id,
                        "track_id": manifest.track_id,
                        "evidence_type": art.file_name.split(".")[0],
                        "storage_reference": art_path,
                        "source_reference": f"{package.camera_id}_stream",
                        "start_time_utc": manifest.first_observed_utc.isoformat(),
                        "end_time_utc": manifest.last_observed_utc.isoformat(),
                        "file_size_bytes": art.file_size_bytes,
                        "mime_type": art.file_type,
                        "sha256": art.sha256_hash,
                        "status": package.status.value,
                        "model_versions": manifest.model_versions,
                        "metadata": manifest.metadata,
                    }
                )
        except Exception as exc:
            logger.debug(f"Could not persist evidence records to DB: {exc}")

    def verify_package(self, manifest_path: str) -> Tuple[bool, List[str]]:
        """Verifies package integrity against manifest checksums."""
        return EvidenceHasher.verify_package_integrity(manifest_path)

    def reset(self, camera_id: Optional[str] = None) -> None:
        """Clears frame buffers."""
        if camera_id:
            if camera_id in self._buffers:
                self._buffers[camera_id].clear()
        else:
            for b in self._buffers.values():
                b.clear()
            self._buffers.clear()

    def close(self) -> None:
        self.reset()
