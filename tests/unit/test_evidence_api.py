"""
Unit tests for FastAPI Event & Evidence REST API endpoints.

Architecture Decision: DEC-0008
"""

import os
import hashlib
import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timezone

from backend.app.main import app
from backend.app.db.repositories.events import EventRepository
from backend.app.db.repositories.evidence import EvidenceRepository


@pytest.fixture
def client():
    return TestClient(app)


def test_api_list_events(client, monkeypatch):
    sample_events = [
        {
            "id": "evt_test_101",
            "camera_id": "cam_01",
            "event_type": "border_crossing",
            "priority": "HIGH",
            "risk_score": 85.0,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    ]
    monkeypatch.setattr(EventRepository, "query_events", lambda self, **kwargs: sample_events)

    res = client.get("/api/v1/events")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["id"] == "evt_test_101"


def test_api_get_event_not_found(client, monkeypatch):
    monkeypatch.setattr(EventRepository, "get_by_id", lambda self, id_: None)
    res = client.get("/api/v1/events/non_existent")
    assert res.status_code == 404


def test_api_get_event_with_evidence(client, monkeypatch):
    sample_event = {
        "id": "evt_ev_202",
        "camera_id": "cam_02",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    sample_records = [
        {
            "id": "evr_1",
            "event_id": "evt_ev_202",
            "camera_id": "cam_02",
            "evidence_type": "snapshot_raw",
            "storage_reference": "storage/evidence/cam_02/evt_ev_202/snapshot_raw.jpg",
            "mime_type": "image/jpeg",
            "sha256": "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
            "file_size_bytes": 45000,
            "status": "sealed",
            "model_versions": {"detector": "YOLOv8n-v1"},
            "metadata": {},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    ]
    monkeypatch.setattr(EventRepository, "get_by_id", lambda self, id_: sample_event)
    monkeypatch.setattr(EvidenceRepository, "get_by_event_id", lambda self, id_: sample_records)

    res = client.get("/api/v1/events/evt_ev_202/evidence")
    assert res.status_code == 200
    data = res.json()
    assert data["event_id"] == "evt_ev_202"
    assert data["is_sealed"] is True
    assert len(data["evidence_records"]) == 1
    assert data["evidence_records"][0]["id"] == "evr_1"


def test_api_verify_evidence_integrity(client, tmp_path, monkeypatch):
    test_file = str(tmp_path / "evidence_verify.jpg")
    file_bytes = b"VERIFIABLE_FORENSIC_DATA_2026"
    with open(test_file, "wb") as f:
        f.write(file_bytes)

    valid_sha256 = hashlib.sha256(file_bytes).hexdigest()

    record = {
        "id": "evr_verify_303",
        "storage_reference": test_file,
        "sha256": valid_sha256,
    }
    monkeypatch.setattr(EvidenceRepository, "get_by_id", lambda self, id_: record)

    # 1. Unaltered file -> PASS (is_valid=True)
    res = client.get("/api/v1/evidence/evr_verify_303/verify")
    assert res.status_code == 200
    data = res.json()
    assert data["is_valid"] is True
    assert data["status"] == "verified"

    # 2. Tampered file -> FAIL (is_valid=False)
    with open(test_file, "ab") as f:
        f.write(b"TAMPERED_EXTRA_BYTES")

    res_tampered = client.get("/api/v1/evidence/evr_verify_303/verify")
    assert res_tampered.status_code == 200
    data_tampered = res_tampered.json()
    assert data_tampered["is_valid"] is False
    assert data_tampered["status"] == "tamper_detected"
