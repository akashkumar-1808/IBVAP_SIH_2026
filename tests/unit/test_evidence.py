"""
Unit tests for IBVAP Phase 9 Structured Evidence Storage & Packaging Subsystem.

Covers:
1. RollingFrameBuffer insertion, capacity limits, and time-window retrieval
2. Pre-event frame window extraction
3. SnapshotExtractor raw and forensic HUD-annotated JPEG generation
4. ClipPackager MP4 video clip encoding
5. EvidenceHasher cryptographic SHA-256 calculation
6. Tamper detection (detects byte alterations in artifacts)
7. EvidenceStorageManager manifest saving and loading
8. EvidencePackager complete package generation and sealing
9. EvidencePackager package verification against manifest
10. Buffer underflow and empty buffer graceful fallbacks
"""

import os
import cv2
import pytest
import numpy as np
from datetime import datetime, timezone, timedelta

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
from worker.spatial.schemas import SpatialState, MovementDirection, BorderSide
from backend.app.schemas.common import EventPriority


# ── Test Helpers ──────────────────────────────────────────────────────────────

def _make_dummy_frame(text: str = "Test Frame", w: int = 640, h: int = 480) -> np.ndarray:
    img = np.full((h, w, 3), 40, dtype=np.uint8)
    cv2.putText(img, text, (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
    return img


def _make_dummy_event(event_id: str = "evt_test_001", camera_id: str = "cam_01") -> EventRecord:
    t0 = datetime(2026, 8, 30, 12, 0, 0, tzinfo=timezone.utc)
    return EventRecord(
        id=event_id,
        camera_id=camera_id,
        track_id=1,
        event_type=EventType.BORDER_CROSSING,
        priority=EventPriority.HIGH,
        risk_score=78.5,
        status=EventStatus.ACTIVE,
        target_class=TargetClass.PERSON,
        created_at=t0,
        updated_at=t0,
        first_observed_utc=t0,
        last_observed_utc=t0 + timedelta(seconds=3.0),
        duration_seconds=3.0,
        detection_confidence=0.92,
        track_persistence_frames=10,
        reason_codes=[FusionReasonCode.PERSON_DETECTED, FusionReasonCode.BORDER_CROSSED],
        explanation_summary="[HIGH PRIORITY — Score 78.5/100] BORDER CROSSING: PERSON detected.",
    )


# ── 1. RollingFrameBuffer Tests ──────────────────────────────────────────────

def test_rolling_frame_buffer_capacity():
    buf = RollingFrameBuffer(max_seconds=2.0, fps=10.0)  # capacity = 20 frames
    t0 = datetime(2026, 8, 30, 12, 0, 0, tzinfo=timezone.utc)

    for i in range(30):
        ts = t0 + timedelta(milliseconds=i * 100)
        buf.add_frame(i, ts, _make_dummy_frame(f"F{i}"), "cam_01")

    # Bounded by capacity
    assert len(buf) == 20
    assert buf.get_latest_frame().frame_id == 29


def test_rolling_frame_buffer_window_retrieval():
    buf = RollingFrameBuffer(max_seconds=5.0, fps=10.0)
    t0 = datetime(2026, 8, 30, 12, 0, 0, tzinfo=timezone.utc)

    for i in range(20):
        ts = t0 + timedelta(milliseconds=i * 100)
        buf.add_frame(i, ts, _make_dummy_frame(f"F{i}"), "cam_01")

    # Query window from 0.5s to 1.2s (inclusive)
    t_start = t0 + timedelta(milliseconds=500)
    t_end = t0 + timedelta(milliseconds=1200)
    window = buf.get_window(t_start, t_end)

    assert len(window) == 8  # indices 5, 6, 7, 8, 9, 10, 11, 12
    assert window[0].frame_id == 5
    assert window[-1].frame_id == 12


def test_pre_event_window_retrieval():
    buf = RollingFrameBuffer(max_seconds=10.0, fps=10.0)
    t0 = datetime(2026, 8, 30, 12, 0, 0, tzinfo=timezone.utc)

    for i in range(40):
        ts = t0 + timedelta(milliseconds=i * 100)
        buf.add_frame(i, ts, _make_dummy_frame(f"F{i}"), "cam_01")

    event_start = t0 + timedelta(seconds=3.0)  # frame index 30
    pre_frames = buf.get_pre_event_frames(event_start, pre_seconds=1.0)

    # 1.0s of pre-event at 10 fps = 11 frames (t=2.0s to t=3.0s)
    assert len(pre_frames) == 11
    assert pre_frames[-1].frame_id == 30


# ── 2. SnapshotExtractor Tests ───────────────────────────────────────────────

def test_snapshot_extractor_raw(tmp_path):
    out_path = str(tmp_path / "raw.jpg")
    img = _make_dummy_frame()
    saved = SnapshotExtractor.save_raw_snapshot(img, out_path, quality=90)

    assert os.path.exists(saved)
    assert os.path.getsize(saved) > 1000  # Valid JPEG
    loaded = cv2.imread(saved)
    assert loaded.shape == img.shape


def test_snapshot_extractor_annotated(tmp_path):
    out_path = str(tmp_path / "annotated.jpg")
    img = _make_dummy_frame()
    event = _make_dummy_event()

    saved = SnapshotExtractor.save_annotated_snapshot(img, event, out_path, quality=95)
    assert os.path.exists(saved)
    loaded = cv2.imread(saved)
    # Annotated snapshot includes top banner (+50px height)
    assert loaded.shape[0] == img.shape[0] + 50


def test_snapshot_extractor_empty_fails(tmp_path):
    out_path = str(tmp_path / "empty.jpg")
    with pytest.raises(EncodingError):
        SnapshotExtractor.save_raw_snapshot(None, out_path)


# ── 3. ClipPackager Tests ───────────────────────────────────────────────────

def test_clip_packager_encoding(tmp_path):
    out_path = str(tmp_path / "clip.mp4")
    t0 = datetime(2026, 8, 30, 12, 0, 0, tzinfo=timezone.utc)
    frames = [
        BufferedFrame(i, t0 + timedelta(milliseconds=i * 40), _make_dummy_frame(f"Frame {i}"), "cam_01")
        for i in range(25)  # 1 second of 25fps video
    ]

    saved = ClipPackager.encode_clip(frames, out_path, fps=25.0)
    assert os.path.exists(saved)
    assert os.path.getsize(saved) > 2000  # Valid MP4

    # Verify readable with OpenCV VideoCapture
    cap = cv2.VideoCapture(saved)
    assert cap.isOpened()
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    assert frame_count == 25
    cap.release()


def test_clip_packager_empty_raises(tmp_path):
    out_path = str(tmp_path / "empty_clip.mp4")
    with pytest.raises(BufferUnderflowError):
        ClipPackager.encode_clip([], out_path)


# ── 4. EvidenceHasher & Tamper Detection Tests ───────────────────────────────

def test_hasher_sha256_calculation(tmp_path):
    test_file = str(tmp_path / "sample.txt")
    with open(test_file, "wb") as f:
        f.write(b"IBVAP Forensic Evidence Data 2026")

    h = EvidenceHasher.hash_file(test_file)
    assert len(h) == 64  # Hex SHA-256 length

    checksum = EvidenceHasher.create_artifact_checksum(test_file, "text/plain")
    assert checksum.file_name == "sample.txt"
    assert checksum.file_size_bytes == 33
    assert checksum.sha256_hash == h


def test_tamper_verification_clean_vs_modified(tmp_path):
    pkg_dir = str(tmp_path / "pkg_01")
    os.makedirs(pkg_dir, exist_ok=True)

    # Create dummy artifact files
    snap_file = os.path.join(pkg_dir, "snapshot.jpg")
    with open(snap_file, "wb") as f:
        f.write(b"\xFF\xD8\xFF\xE0MockJpegBytes")

    clip_file = os.path.join(pkg_dir, "clip.mp4")
    with open(clip_file, "wb") as f:
        f.write(b"MockMp4VideoBytes")

    # Build manifest
    artifacts = [
        EvidenceHasher.create_artifact_checksum(snap_file, "image/jpeg"),
        EvidenceHasher.create_artifact_checksum(clip_file, "video/mp4"),
    ]

    manifest = EvidenceManifest(
        event_id="evt_01",
        camera_id="cam_01",
        track_id=1,
        event_type=EventType.BORDER_CROSSING,
        priority=EventPriority.HIGH,
        risk_score=80.0,
        target_class=TargetClass.PERSON,
        created_at_utc=datetime.now(timezone.utc),
        first_observed_utc=datetime.now(timezone.utc),
        last_observed_utc=datetime.now(timezone.utc),
        duration_seconds=2.0,
        explanation_summary="Test event",
        artifacts=artifacts,
    )

    manifest_path = os.path.join(pkg_dir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        f.write(manifest.model_dump_json(indent=2))

    # Verification 1: Clean untouched package -> VALID
    is_valid, errors = EvidenceHasher.verify_package_integrity(manifest_path)
    assert is_valid is True
    assert len(errors) == 0

    # Verification 2: Alter 1 byte in clip.mp4 -> TAMPER DETECTED
    with open(clip_file, "wb") as f:
        f.write(b"TamperedBytesAltered")

    is_valid_tampered, errors_tampered = EvidenceHasher.verify_package_integrity(manifest_path)
    assert is_valid_tampered is False
    assert len(errors_tampered) == 1
    assert "TAMPER DETECTED" in errors_tampered[0]


# ── 5. EvidenceStorageManager Tests ──────────────────────────────────────────

def test_storage_manager_manifest_lifecycle(tmp_path):
    mgr = EvidenceStorageManager(root_dir=str(tmp_path / "evidence_store"))
    pkg_dir = mgr.get_package_dir("cam_test", "evt_99")

    manifest = EvidenceManifest(
        event_id="evt_99",
        camera_id="cam_test",
        track_id=5,
        event_type=EventType.RESTRICTED_ZONE_INTRUSION,
        priority=EventPriority.HIGH,
        risk_score=75.0,
        target_class=TargetClass.PERSON,
        created_at_utc=datetime.now(timezone.utc),
        first_observed_utc=datetime.now(timezone.utc),
        last_observed_utc=datetime.now(timezone.utc),
        duration_seconds=4.0,
        explanation_summary="Intrusion manifest test",
        artifacts=[],
    )

    manifest_path = mgr.save_manifest(manifest, pkg_dir)
    assert os.path.exists(manifest_path)

    loaded = mgr.load_manifest(manifest_path)
    assert loaded.event_id == "evt_99"
    assert loaded.risk_score == 75.0


# ── 6. EvidencePackager Complete End-to-End Test ─────────────────────────────

def test_evidence_packager_complete_package_creation(tmp_path):
    config = EvidencePackageConfig(
        pre_event_seconds=2.0,
        post_event_seconds=1.0,
        fps=10.0,
        storage_root=str(tmp_path / "packaged_evidence"),
    )
    packager = EvidencePackager(config=config)

    t0 = datetime(2026, 8, 30, 12, 0, 0, tzinfo=timezone.utc)
    camera_id = "cam_pack_01"

    # Pre-fill rolling buffer with 30 frames (3 seconds at 10 fps)
    for i in range(30):
        ts = t0 + timedelta(milliseconds=i * 100)
        packager.add_raw_frame(camera_id, i, ts, _make_dummy_frame(f"Frame #{i}"))

    event = _make_dummy_event(event_id="evt_full_pack_01", camera_id=camera_id)
    event.first_observed_utc = t0 + timedelta(seconds=1.0)
    event.last_observed_utc = t0 + timedelta(seconds=2.0)

    package = packager.create_package(event=event)

    assert package.status == EvidenceStatus.SEALED
    assert package.is_sealed is True
    assert package.sha256_seal is not None
    assert len(package.sha256_seal) == 64

    # Verify physical artifacts exist
    assert os.path.exists(package.snapshot_path)
    assert os.path.exists(package.annotated_snapshot_path)
    assert os.path.exists(package.incident_clip_path)
    assert os.path.exists(package.manifest_path)

    # Verify manifest contains all artifact checksums
    assert len(package.manifest.artifacts) >= 3

    # Verify package passes cryptographic verification
    is_valid, errors = packager.verify_package(package.manifest_path)
    assert is_valid is True
    assert len(errors) == 0
