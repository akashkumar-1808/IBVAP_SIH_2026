import os
import sys
import json
from pathlib import Path
from datetime import datetime, timezone

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import cv2
import numpy as np

from worker.ingestion import FileVideoSource
from worker.perception import ObjectDetector
from worker.tracking import ByteTrackTracker
from worker.environment import EnvironmentAnalyzer


def diagnose_video(video_path: str, max_frames: int = 150):
    print(f"\n==================================================")
    print(f"DIAGNOSING VIDEO: {video_path}")
    print(f"==================================================")

    if not os.path.exists(video_path):
        print(f"Video not found: {video_path}")
        return []

    source = FileVideoSource(camera_id="diag_cam", file_path=video_path, loop=False)
    if not source.connect():
        print(f"Failed to connect to video: {video_path}")
        return []

    meta = source.get_metadata()
    print(f"Resolution: {meta['width']}x{meta['height']}, FPS: {meta['fps']}, Total Frames: {meta['total_frames']}")

    detector = ObjectDetector(confidence_threshold=0.15)
    detector.load()
    tracker = ByteTrackTracker(camera_id="diag_cam", track_thresh=0.40, min_hits=1, max_lost_frames=30)
    env_analyzer = EnvironmentAnalyzer()

    diagnostics = []
    frame_idx = 0

    while True:
        pkt = source.read()
        if pkt is None:
            break

        frame_idx += 1
        if max_frames > 0 and frame_idx > max_frames:
            break

        env_state = env_analyzer.analyze(pkt)
        detections = detector.infer(pkt)
        tracks = tracker.update(
            detections=detections,
            frame_id=pkt.frame_id,
            timestamp_utc=pkt.timestamp_utc,
            camera_id=pkt.camera_id,
        )

        for det in detections:
            diag_entry = {
                "frame_id": frame_idx,
                "video": os.path.basename(video_path),
                "raw_class_name": det.metadata.get("raw_class_name"),
                "class_index": det.metadata.get("class_index"),
                "confidence": round(det.confidence, 4),
                "normalized_target_class": det.class_id.value,
                "bbox": [round(det.bbox.x_min, 1), round(det.bbox.y_min, 1), round(det.bbox.x_max, 1), round(det.bbox.y_max, 1)],
                "env_lighting": env_state.lighting.value,
                "env_quality": env_state.visibility.value,
                "env_quality_score": round(env_state.quality_score, 4),
                "env_brightness": round(env_state.brightness, 4),
                "env_contrast": round(env_state.contrast, 4),
                "env_blur": round(env_state.blur_score, 2),
                "env_noise": round(env_state.noise_estimate, 4),
                "active_tracks_count": len(tracks),
            }
            diagnostics.append(diag_entry)

        if frame_idx % 25 == 0:
            print(f"Processed frame {frame_idx}... found {len(detections)} detections, {len(tracks)} tracks.")

    source.close()
    detector.close()
    tracker.close()
    env_analyzer.close()

    print(f"Total detections collected from {video_path}: {len(diagnostics)}")
    return diagnostics


if __name__ == "__main__":
    all_diags = []
    for vid in ["storage/samples/test_video.mp4", "storage/samples/test_video2.mp4"]:
        if os.path.exists(vid):
            diags = diagnose_video(vid, max_frames=200)
            all_diags.extend(diags)

    os.makedirs("failure_cases/metadata", exist_ok=True)
    with open("failure_cases/metadata/raw_detections_dump.json", "w") as f:
        json.dump(all_diags, f, indent=2)

    print("\nSummary of Raw Classes Detected across all videos:")
    raw_class_counts = {}
    for d in all_diags:
        key = f"{d['raw_class_name']} (idx {d['class_index']}) -> {d['normalized_target_class']}"
        raw_class_counts[key] = raw_class_counts.get(key, 0) + 1

    for k, v in sorted(raw_class_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {k}: {v} detections")
