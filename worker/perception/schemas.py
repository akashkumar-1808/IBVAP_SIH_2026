from typing import Dict, Any, Optional
from backend.app.schemas.common import TargetClass
from backend.app.schemas.events import BoundingBox, Detection

# Mapping from standard COCO class names to normalized IBVAP TargetClass
COCO_CLASS_MAP: Dict[str, TargetClass] = {
    "person": TargetClass.PERSON,
    "bicycle": TargetClass.VEHICLE,
    "car": TargetClass.VEHICLE,
    "motorcycle": TargetClass.VEHICLE,
    "airplane": TargetClass.VEHICLE,
    "bus": TargetClass.VEHICLE,
    "train": TargetClass.VEHICLE,
    "truck": TargetClass.VEHICLE,
    "boat": TargetClass.VEHICLE,
    "bird": TargetClass.ANIMAL,
    "cat": TargetClass.ANIMAL,
    "dog": TargetClass.ANIMAL,
    "horse": TargetClass.ANIMAL,
    "sheep": TargetClass.ANIMAL,
    "cow": TargetClass.ANIMAL,
    "elephant": TargetClass.ANIMAL,
    "bear": TargetClass.ANIMAL,
    "zebra": TargetClass.ANIMAL,
    "giraffe": TargetClass.ANIMAL,
}


def map_raw_class_to_target(raw_class_name: str) -> TargetClass:
    """Maps raw detector class names to high-level IBVAP TargetClass without losing raw name."""
    clean_name = raw_class_name.lower().strip()
    return COCO_CLASS_MAP.get(clean_name, TargetClass.UNKNOWN)


__all__ = ["BoundingBox", "Detection", "TargetClass", "COCO_CLASS_MAP", "map_raw_class_to_target"]
