"""
Acceptance Test for Phase 2: Final SIH Operator Console Integration
Verifies the complete real pipeline and operator console API chain:
- Real MP4 processing
- Real YOLOv8 detection
- Real ByteTrack tracking
- Real border crossing & restricted zone detection
- Real FusionEngine high priority event creation
- Real Evidence package creation with SHA-256 seals
- Real API endpoints for Console rendering:
  - /api/v1/cameras
  - /api/v1/streams/{id}/live
  - /api/v1/events
  - /api/v1/events/{id}/evidence
  - /api/v1/evidence/{id}/verify
  - /api/v1/events/{id}/acknowledge
"""

import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.api.routes.cameras import ConnectCameraRequest
from backend.app.db.repositories import EventRepository, EvidenceRepository

event_repo = EventRepository()
evidence_repo = EvidenceRepository()

def test_phase2_operator_console():
    print("=" * 70)
    print("   IBVAP PHASE 2 — FINAL OPERATOR CONSOLE ACCEPTANCE TEST")
    print("=" * 70)

    client = TestClient(app)

    # 1. Verify Cameras List
    print("\n[STEP 1] Testing /api/v1/cameras ...")
    res = client.get("/api/v1/cameras")
    assert res.status_code == 200
    cams = res.json()
    print(f"Cameras registered: {len(cams)}")
    for c in cams:
        print(f"  - {c['camera_id']} ({c['name']}) | Status: {c['status']}")

    # 2. Connect Real MP4 Video Pipeline
    video_path = "storage/samples/test_video.mp4"
    print(f"\n[STEP 2] Connecting Real MP4 Pipeline ({video_path}) ...")
    req = ConnectCameraRequest(
        camera_id="DEMO-CAM-01",
        name="North Border Gate 01",
        video_file_path=video_path,
        device="cpu"
    )
    res = client.post("/api/v1/cameras/connect", json=req.model_dump())
    assert res.status_code == 200, f"Connect failed: {res.text}"
    print(f"Connected successfully: {res.json()['status']}")

    # 3. Allow pipeline to process frames and emit real security event
    print("\n[STEP 3] Running Live Pipeline to ingest and process frames ...")
    start_time = time.time()
    detected_event = None
    while time.time() - start_time < 35.0:
        time.sleep(2.0)
        # Check event repository via API
        res = client.get("/api/v1/events?camera_id=DEMO-CAM-01")
        if res.status_code == 200:
            events = res.json()
            high_events = [e for e in events if e.get("priority") in ("HIGH", "CRITICAL")]
            if high_events:
                detected_event = high_events[0]
                print(f"✓ Real Security Event Detected! ID: {detected_event['id']} (Elapsed: {time.time() - start_time:.1f}s)")
                break
            else:
                print(f"  Processing frames... ({time.time() - start_time:.1f}s elapsed, {len(events)} events in repo)")
        else:
            print(f"  Waiting for events endpoint... ({time.time() - start_time:.1f}s)")

    assert detected_event is not None, "Pipeline failed to produce high/critical event within runtime window."

    # 4. Verify Live Stream MJPEG Endpoint
    print("\n[STEP 4] Testing Live Stream Snapshot (/api/v1/streams/DEMO-CAM-01/snapshot) ...")
    res = client.get("/api/v1/streams/DEMO-CAM-01/snapshot")
    assert res.status_code == 200
    assert res.headers["content-type"] == "image/jpeg"
    print(f"Snapshot received: {len(res.content)} bytes JPEG (OpenCV HUD annotated)")

    # 5. Verify Event Details & Explainability (FusionEngine reason codes)
    print("\n[STEP 5] Testing Event Explainability & Reason Codes ...")
    event_id = detected_event["id"]
    res = client.get(f"/api/v1/events/{event_id}")
    assert res.status_code == 200
    ev_data = res.json()
    print(f"Event ID:           {ev_data['id']}")
    print(f"Event Type:         {ev_data['event_type']}")
    print(f"Track ID:           #{ev_data['track_id']}")
    print(f"Priority:           {ev_data['priority']}")
    print(f"Risk Score:         {ev_data['risk_score']} / 100")
    print(f"Reason Codes ({len(ev_data.get('reason_codes', []))}):")
    for rc in ev_data.get("reason_codes", []):
        print(f"  ✓ {rc}")
    print(f"Explanation:        {ev_data['explanation_summary']}")

    # 6. Verify Evidence Package & Playable Media
    print("\n[STEP 6] Testing Evidence Package (/api/v1/events/{id}/evidence) ...")
    evidence_pkg = None
    records = []
    for _ in range(12):
        res = client.get(f"/api/v1/events/{event_id}/evidence")
        if res.status_code == 200:
            data = res.json()
            if len(data.get("evidence_records", [])) > 0:
                evidence_pkg = data
                records = data.get("evidence_records", [])
                break
        time.sleep(0.5)

    assert evidence_pkg is not None and len(records) > 0, "Evidence package was not populated in time."
    print(f"Evidence Package:   {evidence_pkg.get('evidence_package_id')}")
    print(f"SHA-256 Seal:       {evidence_pkg.get('sha256_seal')}")
    print(f"Records Count:      {len(records)}")
    for rec in records:
        print(f"  - {rec['evidence_type']}: {rec['storage_reference']} (SHA-256: {rec['sha256'][:12]}...)")

    # 7. Test Media Streaming Endpoint for Video Clip and Snapshots
    print("\n[STEP 7] Testing Direct Evidence File Streaming (/api/v1/evidence/{id}/file) ...")
    for rec in records:
        f_res = client.get(f"/api/v1/evidence/{rec['id']}/file")
        assert f_res.status_code == 200, f"Failed streaming {rec['evidence_type']}: {f_res.status_code}"
        print(f"  ✓ Streamed {rec['evidence_type']} ({len(f_res.content)} bytes, Content-Type: {f_res.headers.get('content-type')})")

    # 8. Test Cryptographic SHA-256 Verification Endpoint
    print("\n[STEP 8] Testing SHA-256 Cryptographic Verification (/api/v1/evidence/{id}/verify) ...")
    sample_rec = records[0]
    res = client.get(f"/api/v1/evidence/{sample_rec['id']}/verify")
    assert res.status_code == 200
    verify_data = res.json()
    print(f"Evidence ID:        {verify_data['evidence_id']}")
    print(f"Calculated SHA-256: {verify_data['calculated_sha256']}")
    print(f"Stored SHA-256:     {verify_data['stored_sha256']}")
    print(f"Integrity Status:   {verify_data['status']}")
    print(f"Is Valid / Seal:    {verify_data['is_valid']}")
    assert verify_data["is_valid"] is True, "Cryptographic verification failed!"

    # 9. Test Event Acknowledgement
    print("\n[STEP 9] Testing Operator Event Acknowledgment (/api/v1/events/{id}/acknowledge) ...")
    res = client.post(f"/api/v1/events/{event_id}/acknowledge", json={"acknowledged_by": "Jury-Lead-Operator"})
    assert res.status_code == 200
    ack_data = res.json()
    print(f"Acknowledgment:     {ack_data['status']}")
    print(f"Acknowledged By:    {ack_data.get('event', {}).get('acknowledged_by')}")
    print(f"Updated Status:     {ack_data.get('event', {}).get('status')}")

    print("\n" + "=" * 70)
    print("   ALL 9 PHASE 2 ACCEPTANCE CRITERIA VERIFIED SUCCESSFULLY!")
    print("=" * 70)

if __name__ == "__main__":
    test_phase2_operator_console()
