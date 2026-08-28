import os
import sys
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import cv2
import numpy as np


def organize_failure_cases():
    dump_path = "failure_cases/metadata/raw_detections_dump.json"
    if not os.path.exists(dump_path):
        print("Dump file not found.")
        return

    with open(dump_path, "r") as f:
        detections = json.load(f)

    # Categories to isolate
    categories = {
        "shadows": [],
        "poles": [],
        "vehicles_unknown": [],
        "background_false_positives": [],
        "tracking_propagation": [],
    }

    for d in detections:
        raw_name = d["raw_class_name"]
        norm_class = d["normalized_target_class"]
        conf = d["confidence"]

        # Anomaly A & D: Shadows / low flat ground objects detected as skateboard / luggage
        if raw_name in ["skateboard", "suitcase"] and norm_class == "unknown":
            categories["shadows"].append(d)

        # Anomaly B: Poles / vertical boundary structures detected as fire hydrant / parking meter
        elif raw_name in ["fire hydrant", "parking meter"] and norm_class == "unknown":
            categories["poles"].append(d)

        # Anomaly C: Non-standard vehicle / accessories detected as unknown
        elif raw_name in ["backpack", "handbag"] and norm_class == "unknown":
            categories["vehicles_unknown"].append(d)

        # Anomaly D: General background false positives
        elif norm_class == "unknown" and conf < 0.40:
            categories["background_false_positives"].append(d)

    print("\nCategorized Anomaly Summary:")
    for cat, items in categories.items():
        print(f"  {cat}: {len(items)} cases found")

    # Ensure directories exist
    for folder in ["shadows", "poles", "vehicles", "background_false_positives", "tracking_propagation"]:
        os.makedirs(f"failure_cases/{folder}", exist_ok=True)

    # Write summary metadata files for each category
    for cat, items in categories.items():
        subfolder = "vehicles" if cat == "vehicles_unknown" else cat
        out_file = f"failure_cases/{subfolder}/cases.json"
        with open(out_file, "w") as f:
            json.dump(items[:50], f, indent=2)  # store representative cases

    # Extract sample video frames and annotate for evaluation corpus
    video_cap = cv2.VideoCapture("storage/samples/test_video.mp4")
    if video_cap.isOpened():
        # Extract 2 sample frames for evaluation
        for target_cat, target_items, out_dir in [
            ("shadows", categories["shadows"], "failure_cases/shadows"),
            ("poles", categories["poles"], "failure_cases/poles"),
        ]:
            if target_items:
                sample = target_items[0]
                frame_id = sample["frame_id"]
                video_cap.set(cv2.CAP_PROP_POS_FRAMES, frame_id - 1)
                ret, frame = video_cap.read()
                if ret:
                    # Draw bbox
                    bb = sample["bbox"]
                    x1, y1, x2, y2 = int(bb[0]), int(bb[1]), int(bb[2]), int(bb[3])
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
                    label = f"{sample['raw_class_name']} ({sample['confidence']:.2f}) -> {sample['normalized_target_class']}"
                    cv2.putText(frame, label, (x1, max(20, y1 - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                    cv2.imwrite(f"{out_dir}/sample_frame_{frame_id}.jpg", frame)
        video_cap.release()

    print("\nFailure cases organized in 'failure_cases/' successfully.")


if __name__ == "__main__":
    organize_failure_cases()
