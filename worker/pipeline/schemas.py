"""
Live Pipeline Orchestration Schemas for IBVAP.

Defines configuration, runtime state, and stage-by-stage latency metrics.

Architecture Decision: DEC-0010
"""

from enum import Enum
from typing import Optional, Dict, List, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class RunMode(str, Enum):
    """Execution mode for live MVP pipeline."""
    HEADLESS = "headless"
    VISUAL = "visual"
    RECORD_DEBUG = "record_debug"


class StageMetrics(BaseModel):
    """Per-stage execution latency in milliseconds."""
    environment_ms: float = 0.0
    detection_ms: float = 0.0
    tracking_ms: float = 0.0
    spatial_ms: float = 0.0
    behavior_ms: float = 0.0
    fusion_ms: float = 0.0
    evidence_ms: float = 0.0
    visualization_ms: float = 0.0
    total_frame_ms: float = 0.0


class PipelineMetrics(BaseModel):
    """Comprehensive performance and lifecycle metrics for a live run."""
    run_id: str
    camera_id: str
    started_at_utc: datetime
    stopped_at_utc: Optional[datetime] = None
    frames_received: int = 0
    frames_processed: int = 0
    frames_dropped: int = 0
    effective_fps: float = 0.0
    avg_stage_latencies_ms: Dict[str, float] = Field(default_factory=dict)
    p95_stage_latencies_ms: Dict[str, float] = Field(default_factory=dict)
    active_tracks_count: int = 0
    total_events_generated: int = 0
    total_evidence_packages: int = 0


class PipelineConfig(BaseModel):
    """Runtime configuration for live pipeline orchestration."""
    camera_id: str = "LIVE-01"
    run_id: Optional[str] = None
    rtsp_url: Optional[str] = None
    file_path: Optional[str] = None
    synthetic_stream: bool = False
    run_mode: RunMode = RunMode.HEADLESS
    max_runtime_seconds: Optional[float] = None
    status_interval_seconds: float = 1.0
    queue_max_size: int = 30
    model_path: str = "yolov8n.pt"
    device: str = "cpu"
    detection_confidence: float = 0.40
    record_output_dir: str = "results/live_runs"
    evidence_storage_dir: str = "storage/evidence"
