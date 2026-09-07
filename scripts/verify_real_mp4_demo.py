"""
Automated Verification Script for Real MP4 SIH Demo Pipeline.

Processes frames from test_video.mp4 through LivePipelineOrchestrator with:
- Real YOLOv8n object detection
- Real ByteTrack tracking
- Real border crossing detection
- Real FusionEngine scoring & reason codes
- Real EvidencePackager cryptographic sealing
"""
import os
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from worker.pipeline import LivePipelineOrchestrator, PipelineConfig, RunMode
from backend.app.api.routes.streams import update_latest_frame
from backend.app.db.repositories import EventRepository, EvidenceRepository
from configs.demo_border_config import build_world_border_components, build_camera_spatial_config

event_repo = EventRepository()
evidence_repo = EvidenceRepository()


def run_verification(video_path: str, max_seconds: float = 20.0):
    print("=" * 70)
    print("      IBVAP REAL MP4 VERIFICATION RUNNER")
    print("=" * 70)
    print(f"Video Path: {video_path}")

    config = PipelineConfig(
        camera_id="VERIFY-CAM-01",
        file_path=video_path,
        run_mode=RunMode.HEADLESS,
        device="cpu",
        max_runtime_seconds=max_seconds,
        status_interval_seconds=3.0,
    )

    orchestrator = LivePipelineOrchestrator(config)
    orchestrator.setup_prototype_border()
    orchestrator.initialize_source()

    captured_data = {
        "frames": 0,
        "persons_detected": 0,
        "tracks": set(),
        "crossings": 0,
        "events": [],
        "evidence_packages": 0,
    }

    def telemetry_hook(packet, env_state, detections, tracks, spatial_states, behaviors, events, fps):
        captured_data["frames"] += 1
        for d in detections:
            if d.class_id.value == "person":
                captured_data["persons_detected"] += 1
        for tr in tracks:
            captured_data["tracks"].add(tr.track_id)
        for sp in spatial_states:
            if sp.crossing_status.value in ("confirmed", "confirmed_crossing") or len(sp.fences_crossed) > 0:
                captured_data["crossings"] += 1
        for ev in events:
            if ev.priority.value.upper() in ("HIGH", "CRITICAL"):
                if not any(e["id"] == ev.id for e in captured_data["events"]):
                    captured_data["events"].append({
                        "id": ev.id,
                        "track_id": ev.track_id,
                        "priority": ev.priority.value.upper(),
                        "risk_score": ev.risk_score,
                        "confidence": ev.detection_confidence,
                        "reasons": [rc.value for rc in ev.reason_codes],
                        "summary": ev.explanation_summary,
                        "frame": captured_data["frames"],
                    })

    orchestrator.on_frame_processed = telemetry_hook

    t_start = time.perf_counter()
    metrics = orchestrator.run()
    elapsed = time.perf_counter() - t_start

    print("\n" + "=" * 70)
    print("              VERIFICATION RESULTS")
    print("=" * 70)
    print(f"Frames Processed:        {captured_data['frames']}")
    print(f"Elapsed Time:            {elapsed:.2f}s")
    print(f"Effective FPS:           {captured_data['frames'] / elapsed if elapsed > 0 else 0.0:.2f} FPS")
    print(f"Person Detections Count: {captured_data['persons_detected']}")
    print(f"Unique Track IDs:        {sorted(list(captured_data['tracks']))}")
    print(f"Crossing Detections:     {captured_data['crossings']}")
    print(f"High/Critical Events:    {len(captured_data['events'])}")
    print(f"Evidence Packages Built: {metrics.total_evidence_packages}")

    for idx, ev in enumerate(captured_data["events"]):
        print(f"\n[EVENT {idx+1}] ID: {ev['id']} (Track #{ev['track_id']})")
        print(f"  Priority:    {ev['priority'].upper()}")
        print(f"  Risk Score:  {ev['risk_score']:.1f} / 100")
        print(f"  Confidence:  {ev['confidence']:.2f}")
        print(f"  Frame:       {ev['frame']}")
        print(f"  Reasons:     {', '.join(ev['reasons'])}")
        print(f"  Summary:     {ev['summary']}")

    # Check evidence directory on disk
    evidence_dir = Path("storage/evidence") / "VERIFY-CAM-01"
    if evidence_dir.exists():
        print(f"\nEvidence files in {evidence_dir}:")
        for p in evidence_dir.rglob("*"):
            if p.is_file():
                print(f"  - {p.relative_to(evidence_dir)} ({p.stat().st_size} bytes)")

    print("=" * 70)
    return captured_data


if __name__ == "__main__":
    video = sys.argv[1] if len(sys.argv) > 1 else "storage/samples/test_video.mp4"
    run_verification(video, max_seconds=18.0)
