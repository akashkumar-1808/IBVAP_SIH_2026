"""
End-to-End Acceptance Test for IBVAP Final Demo Changes:
1. Dashboard Video Upload -> Run Analysis Workflow
2. Evidence Stream Capture & Cryptographic Correlation (event_id authoritative key)
"""

import sys
import time
import json
from pathlib import Path
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.main import app
from backend.app.config import settings
from backend.app.db.repositories import EventRepository, EvidenceRepository

def test_full_upload_and_evidence_lifecycle():
    client = TestClient(app)
    sample_mp4 = settings.samples_path / "test_video.mp4"
    assert sample_mp4.exists(), f"Sample MP4 not found at {sample_mp4}"

    cam_id = "TEST-E2E-CAM"

    print("\n" + "=" * 70)
    print("STEP 1: Testing MP4 Upload via POST /api/v1/cameras/upload")
    print("=" * 70)
    with open(sample_mp4, "rb") as f:
        response = client.post(
            "/api/v1/cameras/upload",
            files={"file": ("test_upload.mp4", f, "video/mp4")},
            data={"camera_id": cam_id},
        )

    assert response.status_code == 200, f"Upload failed: {response.text}"
    upload_data = response.json()
    print(f"Upload Response: {upload_data}")
    assert upload_data["status"] == "READY TO ANALYZE"
    assert "video_path" in upload_data
    uploaded_path = upload_data["video_path"]
    assert Path(uploaded_path).exists(), f"Uploaded file not found on disk: {uploaded_path}"

    print("\n" + "=" * 70)
    print(f"STEP 2: Checking Status via GET /api/v1/cameras/{cam_id}/analysis-status")
    print("=" * 70)
    status_resp = client.get(f"/api/v1/cameras/{cam_id}/analysis-status")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    print(f"Status: {status_data}")
    assert status_data["status"] == "READY TO ANALYZE"

    print("\n" + "=" * 70)
    print("STEP 3: Initiating Real Analysis via POST /api/v1/cameras/run-analysis")
    print("=" * 70)
    run_resp = client.post(
        "/api/v1/cameras/run-analysis",
        json={
            "camera_id": cam_id,
            "video_file_path": uploaded_path,
            "device": "cpu",
        },
    )
    assert run_resp.status_code == 200, f"Run analysis failed: {run_resp.text}"
    run_data = run_resp.json()
    print(f"Run Response: {run_data['message']}")
    assert run_data["status"] == "ANALYZING"

    # Verify status is ANALYZING
    status_resp = client.get(f"/api/v1/cameras/{cam_id}/analysis-status")
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "ANALYZING"

    print("\n" + "=" * 70)
    print("STEP 4: Allowing Real AI Pipeline to Process Video & Detect Intrusion...")
    print("=" * 70)
    # Wait for the background worker to process frames and trigger intrusion event
    event_repo = EventRepository()
    evidence_repo = EvidenceRepository()

    detected_event = None
    t0 = time.time()
    while time.time() - t0 < 35.0:
        events_resp = client.get(f"/api/v1/events?camera_id={cam_id}")
        if events_resp.status_code == 200:
            ev_list = events_resp.json()
            # Pick the qualifying HIGH or CRITICAL security event
            high_events = [e for e in ev_list if str(e.get("priority")).upper() in ("HIGH", "CRITICAL")]
            if high_events:
                detected_event = high_events[0]
                print(f"Real High-Priority Intrusion Event Detected: {detected_event['id']} | Priority: {detected_event.get('priority')} | Risk: {detected_event.get('risk_score')}")
                break
        time.sleep(1.0)

    assert detected_event is not None, "Pipeline did not detect real HIGH/CRITICAL intrusion event within 35s!"
    event_id = detected_event["id"]

    print("\n" + "=" * 70)
    print(f"STEP 5: Verifying Authoritative Event-Evidence Correlation for ID: {event_id}")
    print("=" * 70)
    # Check evidence package endpoint (wait up to 25s for async video encoding and sealing to complete)
    ev_pkg = None
    t1 = time.time()
    while time.time() - t1 < 25.0:
        ev_resp = client.get(f"/api/v1/events/{event_id}/evidence")
        if ev_resp.status_code == 200:
            candidate = ev_resp.json()
            if candidate.get("is_sealed") or candidate.get("evidence_records"):
                ev_pkg = candidate
                break
        time.sleep(1.0)

    assert ev_pkg is not None, f"Evidence package not available for {event_id} after waiting!"
    print(f"Evidence Package Event ID: {ev_pkg['event_id']}")
    assert ev_pkg["event_id"] == event_id, f"Event ID mismatch! Expected {event_id}, got {ev_pkg['event_id']}"
    assert ev_pkg["sha256_seal"], "Missing cryptographic SHA-256 seal!"
    print(f"Cryptographic SHA-256 Seal: {ev_pkg['sha256_seal']}")

    # Verify individual evidence records
    rec_types = [r["evidence_type"] for r in ev_pkg["evidence_records"]]
    print(f"Captured Evidence Artifacts: {rec_types}")
    assert any("RAW" in t for t in rec_types), "Missing raw snapshot!"
    assert any("ANNOTATED" in t for t in rec_types), "Missing annotated snapshot!"

    # Verify integrity endpoint
    for rec in ev_pkg["evidence_records"]:
        v_resp = client.get(f"/api/v1/evidence/{rec['id']}/verify")
        assert v_resp.status_code == 200, f"Integrity check endpoint failed for {rec['id']}"
        v_data = v_resp.json()
        print(f"Verification [{rec['evidence_type']}]: Valid={v_data['is_valid']} | SHA={v_data['calculated_sha256'][:16]}...")
        assert v_data["is_valid"] is True, f"Integrity mismatch on {rec['id']}!"

    print("\n" + "=" * 70)
    print("STEP 6: Testing Event Acknowledgment via POST /api/v1/events/{id}/acknowledge")
    print("=" * 70)
    ack_resp = client.post(
        f"/api/v1/events/{event_id}/acknowledge",
        json={"acknowledged_by": "Operator Akash"},
    )
    assert ack_resp.status_code == 200
    ack_data = ack_resp.json()
    print(f"Acknowledge Response: {ack_data['status']} by {ack_data.get('acknowledged_by')}")
    assert ack_data["status"] in ("RESOLVED", "ACKNOWLEDGED")

    print("\n" + "=" * 70)
    print("STEP 7: Testing Stop Analysis via POST /api/v1/cameras/stop-analysis")
    print("=" * 70)
    stop_resp = client.post(
        "/api/v1/cameras/stop-analysis",
        json={"camera_id": cam_id},
    )
    assert stop_resp.status_code == 200
    assert stop_resp.json()["status"] == "COMPLETED"

    status_resp = client.get(f"/api/v1/cameras/{cam_id}/analysis-status")
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "COMPLETED"
    print(f"Final Analysis Status: {status_resp.json()['status']}")

    print("\n" + "=" * 70)
    print("ALL 7 END-TO-END ACCEPTANCE STEPS PASSED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    test_full_upload_and_evidence_lifecycle()
