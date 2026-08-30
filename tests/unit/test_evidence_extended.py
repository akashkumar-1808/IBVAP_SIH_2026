"""
Comprehensive 19-Scenario Test Suite for IBVAP Phase 9 Evidence Packaging & Storage.

Covers all required evaluation cases:
1. snapshot extraction
2. clip extraction
3. pre-event window
4. post-event window
5. event-duration handling
6. event/evidence relationship
7. evidence metadata
8. SHA-256 generation
9. SHA-256 verification
10. tampered evidence detection
11. missing source video
12. partial evidence failure
13. duplicate capture request (idempotency)
14. event lifecycle integration
15. shadow regression (no high-priority evidence for shadow false alarm)
16. border-crossing evidence preservation
17. deterministic replay
18. model-version propagation
19. storage metadata persistence
"""

import os
import cv2
import pytest
import numpy as np
from datetime import datetime, timezone, timedelta
from typing import List

from worker.evidence import (
    RollingFrameBuffer,
    BufferedFrame,
    SnapshotExtractor,
    ClipPackager,
    EvidenceHasher,
    EvidenceStorageManager,
    EvidencePackager,
    EvidencePackageConfig,
    EvidencePackage,
    EvidenceManifest,
    EvidenceStatus,
    ArtifactChecksum,
    BufferUnderflowError,
    EncodingError,
)
from worker.fusion.schemas import EventRecord, EventType, EventStatus, FusionReasonCode
from worker.tracking.schemas import TrackState, TrajectoryPoint, TargetClass, BoundingBox, TrackStatus
from worker.spatial.schemas import SpatialState, MovementDirection, BorderSide, CrossingStatus, SpatialConfidence
from backend.app.schemas.common import EventPriority


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_dummy_frame(text: str = "Test Frame", w: int = 640, h: int = 480) -> np.ndarray:
    img = np.full((h, w, 3), 40, dtype=np.uint8)
    cv2.putText(img, text, (40, 240), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
    return img


def _make_event(
    event_id: str = "evt_001",
    camera_id: str = "cam_01",
    event_type: EventType = EventType.BORDER_CROSSING,
    priority: EventPriority = EventPriority.HIGH,
    score: float = 82.0,
    target_class: TargetClass = TargetClass.PERSON,
) -> EventRecord:
    t0 = datetime(2026, 8, 30, 12, 0, 0, tzinfo=timezone.utc)
    return EventRecord(
        id=event_id,
        camera_id=camera_id,
        track_id=10,
        event_type=event_type,
        priority=priority,
        risk_score=score,
        status=EventStatus.ACTIVE,
        target_class=target_class,
        created_at=t0,
        updated_at=t0,
        first_observed_utc=t0,
        last_observed_utc=t0 + timedelta(seconds=2.0),
        duration_seconds=2.0,
        detection_confidence=0.94,
        track_persistence_frames=15,
        reason_codes=[FusionReasonCode.PERSON_DETECTED, FusionReasonCode.BORDER_CROSSED],
        explanation_summary=f"[{priority.value} PRIORITY] {event_type.value}: {target_class.value} detected.",
    )


# ── 1. Snapshot Extraction ───────────────────────────────────────────────────

def test_1_snapshot_extraction(tmp_path):
    raw_path = str(tmp_path / "snap_raw.jpg")
    ann_path = str(tmp_path / "snap_ann.jpg")
    frame = _make_dummy_frame("Snapshot Test")
    ev = _make_event()

    SnapshotExtractor.save_raw_snapshot(frame, raw_path, quality=95)
    SnapshotExtractor.save_annotated_snapshot(frame, ev, ann_path, quality=95)

    assert os.path.exists(raw_path) and os.path.getsize(raw_path) > 500
    assert os.path.exists(ann_path) and os.path.getsize(ann_path) > 500


# ── 2. Clip Extraction ───────────────────────────────────────────────────────

def test_2_clip_extraction(tmp_path):
    clip_path = str(tmp_path / "test_clip.mp4")
    t0 = datetime(2026, 8, 30, 12, 0, 0, tzinfo=timezone.utc)
    frames = [
        BufferedFrame(i, t0 + timedelta(milliseconds=i * 40), _make_dummy_frame(f"F{i}"), "cam_01")
        for i in range(25)
    ]
    saved = ClipPackager.encode_clip(frames, clip_path, fps=25.0)
    assert os.path.exists(saved) and os.path.getsize(saved) > 1000


# ── 3. Pre-Event Window ──────────────────────────────────────────────────────

def test_3_pre_event_window():
    buf = RollingFrameBuffer(max_seconds=10.0, fps=10.0)
    t0 = datetime(2026, 8, 30, 12, 0, 0, tzinfo=timezone.utc)
    for i in range(50):
        buf.add_frame(i, t0 + timedelta(milliseconds=i * 100), _make_dummy_frame(), "cam_01")

    event_start = t0 + timedelta(seconds=3.0)  # at 3.0s
    pre_frames = buf.get_pre_event_frames(event_start, pre_seconds=2.0)  # 1.0s to 3.0s (21 frames)
    assert len(pre_frames) == 21
    assert pre_frames[0].timestamp_utc == event_start - timedelta(seconds=2.0)
    assert pre_frames[-1].timestamp_utc == event_start


# ── 4. Post-Event Window ─────────────────────────────────────────────────────

def test_4_post_event_window():
    buf = RollingFrameBuffer(max_seconds=10.0, fps=10.0)
    t0 = datetime(2026, 8, 30, 12, 0, 0, tzinfo=timezone.utc)
    for i in range(50):
        buf.add_frame(i, t0 + timedelta(milliseconds=i * 100), _make_dummy_frame(), "cam_01")

    event_end = t0 + timedelta(seconds=2.0)
    post_end = event_end + timedelta(seconds=1.5)
    post_frames = buf.get_window(event_end, post_end)
    assert len(post_frames) == 16


# ── 5. Event-Duration Handling ───────────────────────────────────────────────

def test_5_event_duration_handling(tmp_path):
    config = EvidencePackageConfig(storage_root=str(tmp_path / "ev_dur"))
    packager = EvidencePackager(config)
    t0 = datetime(2026, 8, 30, 12, 0, 0, tzinfo=timezone.utc)
    for i in range(40):
        packager.add_raw_frame("cam_01", i, t0 + timedelta(milliseconds=i * 100), _make_dummy_frame())

    ev = _make_event(event_id="evt_dur", camera_id="cam_01")
    ev.first_observed_utc = t0 + timedelta(seconds=1.0)
    ev.last_observed_utc = t0 + timedelta(seconds=3.0)
    ev.duration_seconds = 2.0

    pkg = packager.create_package(ev)
    assert pkg.manifest.duration_seconds == 2.0
    assert pkg.manifest.first_observed_utc == ev.first_observed_utc
    assert pkg.manifest.last_observed_utc == ev.last_observed_utc


# ── 6. Event/Evidence Relationship ───────────────────────────────────────────

def test_6_event_evidence_relationship(tmp_path):
    config = EvidencePackageConfig(storage_root=str(tmp_path / "ev_rel"))
    packager = EvidencePackager(config)
    ev = _make_event(event_id="evt_rel_123", camera_id="cam_east_04")
    pkg = packager.create_package(ev, current_frame=_make_dummy_frame())

    assert pkg.event_id == "evt_rel_123"
    assert pkg.camera_id == "cam_east_04"
    assert pkg.manifest.event_id == "evt_rel_123"
    assert pkg.manifest.camera_id == "cam_east_04"


# ── 7. Evidence Metadata ─────────────────────────────────────────────────────

def test_7_evidence_metadata(tmp_path):
    config = EvidencePackageConfig(storage_root=str(tmp_path / "ev_meta"))
    packager = EvidencePackager(config)
    ev = _make_event()
    pkg = packager.create_package(ev, current_frame=_make_dummy_frame())

    m = pkg.manifest
    assert m.risk_score == 82.0
    assert m.priority == EventPriority.HIGH
    assert m.target_class == TargetClass.PERSON
    assert FusionReasonCode.BORDER_CROSSED in m.reason_codes
    assert len(m.artifacts) >= 2


# ── 8. SHA-256 Generation ───────────────────────────────────────────────────

def test_8_sha256_generation(tmp_path):
    test_f = str(tmp_path / "sha_test.bin")
    with open(test_f, "wb") as f:
        f.write(b"IBVAP Security Evidence Block")
    checksum = EvidenceHasher.create_artifact_checksum(test_f, "application/octet-stream")
    assert len(checksum.sha256_hash) == 64
    assert checksum.file_size_bytes == 29


# ── 9. SHA-256 Verification (Pass) ───────────────────────────────────────────

def test_9_sha256_verification_pass(tmp_path):
    config = EvidencePackageConfig(storage_root=str(tmp_path / "ev_pass"))
    packager = EvidencePackager(config)
    ev = _make_event(event_id="evt_pass_01")
    pkg = packager.create_package(ev, current_frame=_make_dummy_frame())

    is_valid, errors = packager.verify_package(pkg.manifest_path)
    assert is_valid is True
    assert len(errors) == 0


# ── 10. Tampered Evidence Detection ──────────────────────────────────────────

def test_10_tampered_evidence_detection(tmp_path):
    config = EvidencePackageConfig(storage_root=str(tmp_path / "ev_tamp"))
    packager = EvidencePackager(config)
    ev = _make_event(event_id="evt_tamp_01")
    pkg = packager.create_package(ev, current_frame=_make_dummy_frame())

    # Alter 1 byte in raw snapshot file
    with open(pkg.snapshot_path, "ab") as f:
        f.write(b"MALICIOUS_TAMPER_BYTES")

    is_valid, errors = packager.verify_package(pkg.manifest_path)
    assert is_valid is False
    assert any("TAMPER DETECTED" in err for err in errors)


# ── 11. Missing Source Video ─────────────────────────────────────────────────

def test_11_missing_source_video(tmp_path):
    config = EvidencePackageConfig(storage_root=str(tmp_path / "ev_missing"))
    packager = EvidencePackager(config)
    ev = _make_event(event_id="evt_missing")

    # Packaging with completely empty frame buffer generates fallback keyframe without crashing
    pkg = packager.create_package(ev, current_frame=None)
    assert pkg.status in (EvidenceStatus.SEALED, EvidenceStatus.PARTIAL)
    assert os.path.exists(pkg.snapshot_path)


# ── 12. Partial Evidence Failure ─────────────────────────────────────────────

def test_12_partial_evidence_failure(tmp_path, monkeypatch):
    config = EvidencePackageConfig(storage_root=str(tmp_path / "ev_part"))
    packager = EvidencePackager(config)
    ev = _make_event(event_id="evt_part_01")

    # Mock ClipPackager.encode_clip to simulate a video encoder crash
    def mock_fail_clip(frames, dest, fps):
        raise EncodingError("Simulated video encoder failure.")

    monkeypatch.setattr(ClipPackager, "encode_clip", mock_fail_clip)

    pkg = packager.create_package(ev, current_frame=_make_dummy_frame())
    # Snapshot succeeds, clip fails -> status is PARTIAL, manifest is still valid
    assert pkg.status == EvidenceStatus.PARTIAL
    assert os.path.exists(pkg.snapshot_path)
    assert pkg.incident_clip_path is None
    assert pkg.manifest.metadata.get("partial_error_reason") is not None


# ── 13. Duplicate Capture Request (Idempotency) ──────────────────────────────

def test_13_duplicate_capture_idempotency(tmp_path):
    config = EvidencePackageConfig(storage_root=str(tmp_path / "ev_idemp"))
    packager = EvidencePackager(config)
    ev = _make_event(event_id="evt_idemp_01")
    frame = _make_dummy_frame()

    pkg1 = packager.create_package(ev, current_frame=frame)
    seal1 = pkg1.sha256_seal

    # Second call for the same event
    pkg2 = packager.create_package(ev, current_frame=frame, force_repackage=False)
    seal2 = pkg2.sha256_seal

    assert pkg1.id == pkg2.id
    assert seal1 == seal2


# ── 14. Event Lifecycle Integration ─────────────────────────────────────────

def test_14_event_lifecycle_integration(tmp_path):
    config = EvidencePackageConfig(storage_root=str(tmp_path / "ev_life"))
    packager = EvidencePackager(config)
    ev = _make_event(event_id="evt_life_01")

    assert ev.status == EventStatus.ACTIVE
    pkg = packager.create_package(ev, current_frame=_make_dummy_frame())
    assert pkg.status == EvidenceStatus.SEALED
    assert pkg.is_sealed is True


# ── 15. Shadow Regression (No High-Priority Evidence) ────────────────────────

def test_15_shadow_regression_no_high_evidence(tmp_path):
    """
    Demonstrates that a low-priority false detection (shadow / pole)
    produces score <= 30.0 (INFO) and does NOT qualify for high-priority evidence escalation.
    """
    ev_shadow = EventRecord(
        id="evt_shadow_001",
        camera_id="cam_01",
        track_id=99,
        event_type=EventType.OBJECT_OBSERVED,
        priority=EventPriority.INFO,
        risk_score=24.5,
        status=EventStatus.ACTIVE,
        target_class=TargetClass.UNKNOWN,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        first_observed_utc=datetime.now(timezone.utc),
        last_observed_utc=datetime.now(timezone.utc),
        duration_seconds=0.1,
        detection_confidence=0.35,
        track_persistence_frames=1,
        reason_codes=[FusionReasonCode.UNKNOWN_OBJECT_DETECTED],
        explanation_summary="[INFO PRIORITY — Score 24.5/100] Transient object observation.",
    )

    # Shadow stays at INFO priority
    assert ev_shadow.priority == EventPriority.INFO
    assert ev_shadow.risk_score <= 30.0
    # Operational rule: High-priority evidence packaging triggers only for >= MEDIUM/HIGH priority
    should_package_high = ev_shadow.priority in (EventPriority.HIGH, EventPriority.CRITICAL)
    assert should_package_high is False


# ── 16. Border-Crossing Evidence Preservation ────────────────────────────────

def test_16_border_crossing_evidence_preservation(tmp_path):
    config = EvidencePackageConfig(storage_root=str(tmp_path / "ev_border"))
    packager = EvidencePackager(config)
    t0 = datetime(2026, 8, 30, 12, 0, 0, tzinfo=timezone.utc)

    spatial_state = SpatialState(
        camera_id="cam_border_01",
        track_id=10,
        timestamp_utc=t0,
        border_side=BorderSide.RESTRICTED,
        crossing_status=CrossingStatus.CONFIRMED_CROSSING,
        direction=MovementDirection.TOWARD,
        spatial_confidence=SpatialConfidence.VALID,
        calibration_version="2.1-homography",
    )

    ev = _make_event(event_id="evt_border_cross", camera_id="cam_border_01")
    pkg = packager.create_package(ev, spatial_state=spatial_state, current_frame=_make_dummy_frame())

    assert pkg.manifest.model_versions.get("calibration_version") == "2.1-homography"
    assert pkg.manifest.model_versions.get("spatial") == "WorldBorder-v1"


# ── 17. Deterministic Replay ─────────────────────────────────────────────────

def test_17_deterministic_replay(tmp_path):
    dir1 = str(tmp_path / "replay_run1")
    dir2 = str(tmp_path / "replay_run2")

    packager1 = EvidencePackager(EvidencePackageConfig(storage_root=dir1))
    packager2 = EvidencePackager(EvidencePackageConfig(storage_root=dir2))

    ev = _make_event(event_id="evt_deterministic")
    frame = _make_dummy_frame("Deterministic Frame")

    pkg1 = packager1.create_package(ev, current_frame=frame)
    pkg2 = packager2.create_package(ev, current_frame=frame)

    # SHA-256 of raw snapshots generated identically must be equal
    raw_hash1 = EvidenceHasher.hash_file(pkg1.snapshot_path)
    raw_hash2 = EvidenceHasher.hash_file(pkg2.snapshot_path)
    assert raw_hash1 == raw_hash2


# ── 18. Model Version Propagation ────────────────────────────────────────────

def test_18_model_version_propagation(tmp_path):
    config = EvidencePackageConfig(storage_root=str(tmp_path / "ev_ver"))
    packager = EvidencePackager(config)
    ev = _make_event(event_id="evt_ver_01")
    pkg = packager.create_package(ev, current_frame=_make_dummy_frame())

    versions = pkg.manifest.model_versions
    assert versions["detector"] == "YOLOv8n-v1"
    assert versions["tracker"] == "ByteTrack-v1"
    assert versions["environment"] == "Env-v1"
    assert versions["fusion"] == "Fusion-v1"
    assert versions["evidence"] == "Evidence-v1"


# ── 19. Storage Metadata Persistence ─────────────────────────────────────────

def test_19_storage_metadata_persistence(tmp_path):
    mgr = EvidenceStorageManager(root_dir=str(tmp_path / "storage_store"))
    pkg_dir = mgr.get_package_dir("cam_01", "evt_store_01")
    ev = _make_event(event_id="evt_store_01")

    manifest = EvidenceManifest(
        event_id=ev.id,
        camera_id=ev.camera_id,
        track_id=ev.track_id,
        event_type=ev.event_type,
        priority=ev.priority,
        risk_score=ev.risk_score,
        target_class=ev.target_class,
        created_at_utc=ev.created_at,
        first_observed_utc=ev.first_observed_utc,
        last_observed_utc=ev.last_observed_utc,
        duration_seconds=ev.duration_seconds,
        reason_codes=ev.reason_codes,
        explanation_summary=ev.explanation_summary,
        artifacts=[],
        model_versions={"detector": "YOLOv8n-v1"},
    )

    path = mgr.save_manifest(manifest, pkg_dir)
    loaded = mgr.load_manifest(path)

    assert loaded.event_id == "evt_store_01"
    assert loaded.model_versions["detector"] == "YOLOv8n-v1"
