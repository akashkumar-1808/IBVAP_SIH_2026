"""
Live Pipeline Orchestrator for IBVAP.

Coordinates real-time ingestion, perception, tracking, spatial border analysis,
behavioral recognition, multi-modal evidence fusion, and forensic evidence packaging
from real RTSP streams or video sources.

Architecture Decision: DEC-0010
"""

import os
import cv2
import numpy as np
import time
import json
import uuid
import signal
import logging
import statistics
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone, timedelta

from .schemas import PipelineConfig, PipelineMetrics, StageMetrics, RunMode
from .visualizer import LiveStreamVisualizer

from worker.ingestion import (
    VideoSource,
    RTSPVideoSource,
    FileVideoSource,
    BoundedFrameQueue,
    FramePacket,
    StreamHealthState,
    mask_rtsp_url,
)
from worker.environment import EnvironmentAnalyzer, EnvironmentConfig, EnvironmentState
from worker.perception import ObjectDetector, Detection
from worker.tracking import ByteTrackTracker, TrackState
from worker.spatial import (
    SpatialEngine,
    SpatialState,
    BorderSection,
    CameraCalibration,
    CameraRegistration,
    ProjectedBorder,
    WorldPoint,
    CalibrationCorrespondence,
    CalibrationModel,
    CoordinateReference,
    TerrainMode,
)
from worker.behavior import BehaviorEngine, BehaviorPrimitive
from worker.fusion import FusionEngine, EventRecord, EventPriority, EventStatus
from worker.evidence import EvidencePackager, EvidencePackageConfig, EvidencePackage

logger = logging.getLogger("ibvap.pipeline")


class LivePipelineOrchestrator:
    """
    Production Live Pipeline Orchestrator.
    Connects existing modular intelligence engines to live video streams.
    """

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.run_id = config.run_id or f"run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        self.config.run_id = self.run_id

        # Lifecycle Flags
        self._is_running = False
        self._shutdown_requested = False
        self._start_time: Optional[datetime] = None

        # Pipelines and Engines
        self.source: Optional[VideoSource] = None
        self.queue = BoundedFrameQueue(max_size=config.queue_max_size)
        self.environment_analyzer = EnvironmentAnalyzer()
        self.detector = ObjectDetector(model_path=config.model_path, device=config.device, confidence_threshold=config.detection_confidence)
        self.tracker = ByteTrackTracker()
        self.spatial_engine = SpatialEngine()
        self.behavior_engine = BehaviorEngine()
        self.fusion_engine = FusionEngine()
        self.evidence_packager = EvidencePackager(EvidencePackageConfig(storage_root=config.evidence_storage_dir))
        self.visualizer = LiveStreamVisualizer(camera_id=config.camera_id)

        # Video Recorder for --record-debug
        self._video_writer: Optional[cv2.VideoWriter] = None
        self._record_output_path: Optional[str] = None

        # Metrics and State History
        self.metrics = PipelineMetrics(
            run_id=self.run_id,
            camera_id=config.camera_id,
            started_at_utc=datetime.now(timezone.utc),
        )
        self._stage_latencies_history: Dict[str, List[float]] = {
            "environment": [], "detection": [], "tracking": [], "spatial": [],
            "behavior": [], "fusion": [], "evidence": [], "visualization": [], "total": [],
        }
        self._recorded_events: List[EventRecord] = []
        self._recorded_tracks: Dict[int, Dict[str, Any]] = {}
        self._latest_environment: Optional[EnvironmentState] = None
        self._latest_projected_border: Optional[ProjectedBorder] = None
        self._is_calibrated = False

        # Output Directory
        self.run_output_dir = Path(config.record_output_dir) / self.run_id
        self.run_output_dir.mkdir(parents=True, exist_ok=True)

        self._last_status_print = time.time()
        self._fps_window: List[float] = []

        # Real-Time Telemetry and Streaming Callback Hook
        self.on_frame_processed: Optional[Any] = None

    def setup_prototype_border(
        self,
        border_section_id: str = "SEC-ALPHA",
        points_world: Optional[List[Tuple[float, float]]] = None,
        correspondences: Optional[List[Tuple[float, float, float, float]]] = None,
    ) -> None:
        """Configures a real calibrated world-border for live camera testing."""
        pts = points_world or [(-20.0, 15.0), (0.0, 15.0), (20.0, 15.0)]
        section = BorderSection(
            id=border_section_id,
            name="Live Prototype Sector Alpha Border",
            points=[WorldPoint(x=x, y=y) for x, y in pts],
            permitted_side_normal=(0.0, -1.0),
            warning_buffer_distance=5.0,
            coordinate_reference=CoordinateReference.LOCAL_CARTESIAN,
            terrain_mode=TerrainMode.PLANAR_GROUND,
        )

        corr_tuples = correspondences or [
            (-15.0, 10.0, 80.0, 360.0),
            (15.0, 10.0, 560.0, 360.0),
            (15.0, 30.0, 480.0, 200.0),
            (-15.0, 30.0, 160.0, 200.0),
        ]
        cal = CameraCalibration(
            camera_id=self.config.camera_id,
            image_width=640,
            image_height=480,
            calibration_version="live_v1.0",
            calibration_model=CalibrationModel.PLANAR_HOMOGRAPHY,
            correspondences=[
                CalibrationCorrespondence(world_point=WorldPoint(x=wx, y=wy), image_point=(ix, iy))
                for wx, wy, ix, iy in corr_tuples
            ],
        )

        from worker.spatial.world_schemas import CalibrationStatus
        reg = CameraRegistration(
            camera_id=self.config.camera_id,
            visible_border_sections=[border_section_id],
            calibration_status=CalibrationStatus.CALIBRATED,
        )

        self.spatial_engine.register_border_section(section)
        self.spatial_engine.register_camera(reg)
        self.spatial_engine.register_calibration(cal)
        self._latest_projected_border = self.spatial_engine.project_border(self.config.camera_id, border_section_id)
        self._is_calibrated = (self._latest_projected_border is not None)

    def initialize_source(self) -> None:
        """Establishes video ingestion source with health verification."""
        if self.config.rtsp_url:
            masked = mask_rtsp_url(self.config.rtsp_url)
            print(f"Connecting to RTSP Stream: {masked} ...")
            self.source = RTSPVideoSource(
                camera_id=self.config.camera_id,
                rtsp_url=self.config.rtsp_url,
                max_reconnect_attempts=5,
            )
        elif self.config.file_path:
            print(f"Opening Video File: {self.config.file_path} ...")
            self.source = FileVideoSource(
                camera_id=self.config.camera_id,
                file_path=self.config.file_path,
                realtime_pacing=True,
            )
        else:
            raise ValueError("Either rtsp_url, file_path, or synthetic_stream must be configured.")

        # Test Connection and Health
        connected = self.source.connect()
        if not connected:
            raise RuntimeError(f"Failed to connect to video source for camera '{self.config.camera_id}'")
        health = self.source.get_health()
        print(f"Stream Health: {health.state.value.upper()} | FPS: {health.fps_measured:.1f}")

    def run(self) -> PipelineMetrics:
        """Main execution entrypoint for live processing."""
        self._is_running = True
        self._start_time = datetime.now(timezone.utc)
        self.metrics.started_at_utc = self._start_time

        # Print Startup Banner
        self._print_startup_banner()

        # Initialize detector warmup
        self.detector.load()
        self.detector.warmup()

        try:
            while self._is_running and not self._shutdown_requested:
                # 1. Check Max Runtime Limit
                if self.config.max_runtime_seconds:
                    elapsed = (datetime.now(timezone.utc) - self._start_time).total_seconds()
                    if elapsed >= self.config.max_runtime_seconds:
                        print(f"\nMax runtime of {self.config.max_runtime_seconds:.1f}s reached. Initiating shutdown...")
                        break

                # 2. Ingest Frame Packet
                packet = self.source.read()
                if packet is None:
                    if isinstance(self.source, FileVideoSource):
                        print("\nEnd of video stream reached.")
                        break
                    # RTSP stream reconnecting/transient drop
                    time.sleep(0.01)
                    continue

                self.metrics.frames_received += 1
                self.queue.put(packet)

                # 3. Process from Queue
                frame_packet = self.queue.get()
                if frame_packet is None:
                    continue

                t_frame_start = time.perf_counter()
                self._process_single_frame(frame_packet)
                t_frame_end = time.perf_counter()

                total_ms = (t_frame_end - t_frame_start) * 1000.0
                self._stage_latencies_history["total"].append(total_ms)
                self.metrics.frames_processed += 1

                # 4. Measure FPS
                now_s = time.time()
                self._fps_window.append(now_s)
                self._fps_window = [t for t in self._fps_window if now_s - t <= 2.0]
                current_fps = len(self._fps_window) / 2.0

                # 5. Periodic Terminal Monitor
                if now_s - self._last_status_print >= self.config.status_interval_seconds:
                    self._print_status_monitor(current_fps)
                    self._last_status_print = now_s

        except KeyboardInterrupt:
            print("\nReceived SIGINT (Ctrl+C). Stopping live pipeline gracefully...")
        finally:
            self.stop()

        return self.metrics

    def _process_single_frame(self, packet: FramePacket) -> None:
        """Executes the complete 9-stage intelligence chain for one frame."""
        img = packet.image
        cam_id = packet.camera_id
        frame_id = packet.frame_id
        ts = packet.timestamp_utc

        # Buffer raw frame for evidence rolling buffer
        self.evidence_packager.add_frame(packet)

        # Stage 1: Environment Analysis
        t0 = time.perf_counter()
        env_state = self.environment_analyzer.analyze(packet)
        self._latest_environment = env_state
        self._stage_latencies_history["environment"].append((time.perf_counter() - t0) * 1000.0)

        # Stage 2: Object Detection (YOLOv8n)
        t0 = time.perf_counter()
        detections = self.detector.infer(packet)
        self._stage_latencies_history["detection"].append((time.perf_counter() - t0) * 1000.0)

        # Stage 3: Multi-Object Tracking (ByteTrack)
        t0 = time.perf_counter()
        tracks = self.tracker.update(detections, camera_id=cam_id, timestamp_utc=ts, frame_id=frame_id)
        self._stage_latencies_history["tracking"].append((time.perf_counter() - t0) * 1000.0)

        for tr in tracks:
            self._recorded_tracks[tr.track_id] = {
                "track_id": tr.track_id, "class_id": tr.class_id.value,
                "first_seen": tr.first_seen.isoformat(), "last_seen": tr.last_seen.isoformat(),
                "age_frames": tr.age_frames,
            }

        # Stage 4: World-Border Spatial Intelligence
        t0 = time.perf_counter()
        spatial_states = self.spatial_engine.process_tracks(tracks, cam_id, ts)
        self._stage_latencies_history["spatial"].append((time.perf_counter() - t0) * 1000.0)

        # Stage 5: Temporal Behavioral Analytics
        t0 = time.perf_counter()
        behaviors = self.behavior_engine.process(tracks, spatial_states, ts, env_state)
        self._stage_latencies_history["behavior"].append((time.perf_counter() - t0) * 1000.0)

        # Stage 6: Multi-Modal Evidence Fusion & Events
        t0 = time.perf_counter()
        events = self.fusion_engine.process(
            tracks=tracks,
            spatial_states=spatial_states,
            environment_state=env_state,
            behavior_primitives=behaviors,
            camera_id=cam_id,
            timestamp_utc=ts,
        )
        self._stage_latencies_history["fusion"].append((time.perf_counter() - t0) * 1000.0)

        # Stage 7: Evidence Packaging where triggered
        t0 = time.perf_counter()
        for ev in events:
            if ev.priority in (EventPriority.HIGH, EventPriority.CRITICAL):
                # Log event created banner once per active transition
                if ev.duration_seconds <= 0.1:
                    self._print_event_banner(ev, tracks, spatial_states, behaviors)
                    matching_tr = next((t for t in tracks if t.track_id == ev.track_id), None)
                    matching_sp = next((s for s in spatial_states if s.track_id == ev.track_id), None)
                    if matching_tr and matching_sp:
                        pkg = self.evidence_packager.create_package(ev, matching_tr, matching_sp)
                        self.metrics.total_evidence_packages += 1
                        print(f"Evidence Package Sealed: {pkg.package_id} [SHA-256: {pkg.sha256_seal[:16]}...]")

                if not any(e.id == ev.id for e in self._recorded_events):
                    self._recorded_events.append(ev)
                    self.metrics.total_events_generated += 1
        self._stage_latencies_history["evidence"].append((time.perf_counter() - t0) * 1000.0)

        # Stage 8: Visualization Rendering & OpenCV Display
        t0 = time.perf_counter()
        if self.config.run_mode in (RunMode.VISUAL, RunMode.RECORD_DEBUG):
            fps_val = len(self._fps_window) / 2.0 if self._fps_window else 0.0
            vis_img = self.visualizer.render_frame(
                frame=img,
                tracks=tracks,
                spatial_states=spatial_states,
                behavior_primitives=behaviors,
                events=events,
                environment=env_state,
                projected_border=self._latest_projected_border,
                is_calibrated=self._is_calibrated,
                fps=fps_val,
            )

            # Show window in VISUAL mode
            if self.config.run_mode == RunMode.VISUAL:
                cv2.imshow("IBVAP Live Operational View", vis_img)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    self._shutdown_requested = True

            # Record in RECORD_DEBUG mode
            if self.config.run_mode == RunMode.RECORD_DEBUG:
                if self._video_writer is None:
                    h, w = vis_img.shape[:2]
                    self._record_output_path = str(self.run_output_dir / "debug_annotated.mp4")
                    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                    self._video_writer = cv2.VideoWriter(self._record_output_path, fourcc, 20.0, (w, h))
                self._video_writer.write(vis_img)

        self._stage_latencies_history["visualization"].append((time.perf_counter() - t0) * 1000.0)

        # Stage 9: External Telemetry / Streaming Hook
        if self.on_frame_processed and callable(self.on_frame_processed):
            fps_val = len(self._fps_window) / 2.0 if self._fps_window else 0.0
            try:
                self.on_frame_processed(
                    packet=packet,
                    env_state=env_state,
                    detections=detections,
                    tracks=tracks,
                    spatial_states=spatial_states,
                    behaviors=behaviors,
                    events=events,
                    fps=fps_val,
                )
            except Exception as e:
                logger.warning(f"Error in on_frame_processed hook: {e}")

    def _print_startup_banner(self) -> None:
        """Prints formatted startup credentials banner."""
        stream_str = mask_rtsp_url(self.config.rtsp_url) if self.config.rtsp_url else (self.config.file_path or "Synthetic")
        print("\n" + "=" * 60)
        print("   IBVAP LIVE MVP ORCHESTRATION PIPELINE")
        print("=" * 60)
        print(f"Camera:   {self.config.camera_id}")
        print(f"Stream:   {stream_str}")
        print(f"Model:    {self.config.model_path}")
        print(f"Device:   {self.config.device.upper()}")
        print(f"Run ID:   {self.run_id}")
        print(f"Mode:     {self.config.run_mode.value.upper()}")
        print(f"Spatial:  {'CALIBRATED' if self._is_calibrated else 'UNCALIBRATED'}")
        print("=" * 60)
        print("PIPELINE STATE: RUNNING\n")

    def _print_status_monitor(self, fps: float) -> None:
        """Prints compact periodic terminal status."""
        health = self.source.get_health() if self.source else None
        h_str = health.state.value.upper() if health else "ONLINE"
        env = self._latest_environment
        light_str = env.lighting.value.upper() if env else "--"
        vis_str = env.visibility.value.upper() if env else "--"

        active_tracks = self.tracker.get_tracks()
        self.metrics.active_tracks_count = len(active_tracks)

        print("-" * 50)
        print(f"IBVAP LIVE STATUS | Cam: {self.config.camera_id} | Health: {h_str}")
        print(f"FPS: {fps:.1f} | Frame: {self.metrics.frames_processed} | Dropped: {self.metrics.frames_dropped}")
        print(f"Environment: Light: {light_str} | Vis: {vis_str}")
        print(f"Active Tracks ({len(active_tracks)}):")
        for tr in active_tracks[:3]:
            print(f"  #{tr.track_id} {tr.class_id.value.upper()} (age: {tr.age_frames})")
        print(f"Events Emitted: {self.metrics.total_events_generated} | Evidence Packages: {self.metrics.total_evidence_packages}")
        print("-" * 50)

    def _print_event_banner(
        self,
        event: EventRecord,
        tracks: List[TrackState],
        spatial_states: List[SpatialState],
        behaviors: List[BehaviorPrimitive],
    ) -> None:
        """Prints high-visibility event activation banner."""
        print("\n" + "=" * 60)
        print(f"!! ACTIVE SECURITY EVENT: {event.event_type.value.upper()} !!")
        print("=" * 60)
        print(f"Event ID:  {event.id}")
        print(f"Priority:  {event.priority.value.upper()} (Risk Score: {event.risk_score:.1f})")
        print(f"Camera:    {event.camera_id} | Track: #{event.track_id} ({event.target_class.value.upper()})")
        print("Reasons:")
        for r in event.reason_codes:
            print(f"  - {r.value}")
        print(f"Summary:   {event.explanation_summary}")
        print("=" * 60 + "\n")

    def stop(self) -> None:
        """Safely shuts down sources, resources, and generates the run report."""
        was_running = self._is_running
        self._is_running = False
        self.metrics.stopped_at_utc = datetime.now(timezone.utc)

        # 1. Close Video Source
        if self.source:
            self.source.stop()
            self.source = None

        if not was_running:
            return

        # 2. Release Video Writer & OpenCV Windows
        if self._video_writer is not None:
            self._video_writer.release()
            self._video_writer = None

        try:
            cv2.destroyAllWindows()
        except Exception:
            pass

        # 3. Compute Metrics
        duration = (self.metrics.stopped_at_utc - self.metrics.started_at_utc).total_seconds()
        self.metrics.effective_fps = self.metrics.frames_processed / max(0.001, duration)

        for st_name, times in self._stage_latencies_history.items():
            if times:
                self.metrics.avg_stage_latencies_ms[st_name] = round(statistics.mean(times), 4)
                self.metrics.p95_stage_latencies_ms[st_name] = round(statistics.quantiles(times, n=20)[18] if len(times) >= 20 else statistics.mean(times), 4)

        # 4. Save Run Artifacts
        self._export_run_report()

    def _export_run_report(self) -> None:
        """Saves summary.json, metrics.json, events.json, tracks.json to results/live_runs/<run_id>/."""
        summary = {
            "run_id": self.run_id,
            "camera_id": self.config.camera_id,
            "mode": self.config.run_mode.value,
            "started_at": self.metrics.started_at_utc.isoformat(),
            "stopped_at": self.metrics.stopped_at_utc.isoformat() if self.metrics.stopped_at_utc else None,
            "frames_processed": self.metrics.frames_processed,
            "effective_fps": round(self.metrics.effective_fps, 2),
            "events_generated": self.metrics.total_events_generated,
            "evidence_packages": self.metrics.total_evidence_packages,
        }
        with open(self.run_output_dir / "summary.json", "w") as f:
            json.dump(summary, f, indent=2)

        with open(self.run_output_dir / "metrics.json", "w") as f:
            json.dump(self.metrics.model_dump(mode="json"), f, indent=2)

        with open(self.run_output_dir / "events.json", "w") as f:
            json.dump([e.model_dump(mode="json") for e in self._recorded_events], f, indent=2)

        with open(self.run_output_dir / "tracks.json", "w") as f:
            json.dump(list(self._recorded_tracks.values()), f, indent=2)

        if self._latest_environment:
            with open(self.run_output_dir / "environment.json", "w") as f:
                json.dump(self._latest_environment.model_dump(mode="json"), f, indent=2)

        print(f"\nLive Run Report Exported: {self.run_output_dir}")
