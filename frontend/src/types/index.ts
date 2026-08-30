/**
 * IBVAP Operator Console - Canonical TypeScript Types
 * Mirrors the Python intelligence backend models 1:1.
 */

export type TargetClass = 'PERSON' | 'VEHICLE' | 'ANIMAL' | 'UNKNOWN';

export type TrackStatus = 'CANDIDATE' | 'TRACKED' | 'LOST' | 'REMOVED';

export type BorderSide = 'PERMITTED' | 'WARNING_BUFFER' | 'RESTRICTED' | 'UNKNOWN';

export type CrossingStatus = 'NO_CROSSING' | 'CROSSING_WARNING_BUFFER' | 'BORDER_BREACH_DETECTED' | 'CONFIRMED_CROSSING';

export type MovementDirection = 'TOWARD' | 'AWAY' | 'PARALLEL' | 'STATIONARY' | 'UNKNOWN';

export type LightingCondition = 'DAY' | 'DUSK' | 'LOW_LIGHT' | 'NIGHT' | 'OVEREXPOSED';

export type VisibilityQuality = 'EXCELLENT' | 'GOOD' | 'FAIR' | 'POOR' | 'DEGRADED';

export type EventPriority = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFO';

export type EventStatus = 'ACTIVE' | 'RESOLVED' | 'DISMISSED' | 'AUTO_SUPPRESSED';

export type AssociationState = 'NEW' | 'ACTIVE' | 'CONFIRMED' | 'LIKELY' | 'UNCERTAIN' | 'ENDED';

export interface BoundingBox {
  x_min: number;
  y_min: number;
  x_max: number;
  y_max: number;
}

export interface TrajectoryPoint {
  x: number;
  y: number;
  timestamp_utc?: string;
  frame_id?: number;
}

export interface TrackState {
  track_id: number;
  camera_id: string;
  class_id: TargetClass;
  bbox: BoundingBox;
  center_xy: [number, number];
  velocity_xy?: [number, number];
  speed_pixels_per_sec?: number;
  age_frames: number;
  status: TrackStatus;
  first_seen?: string;
  last_seen?: string;
  confidence_history?: number[];
  trajectory: TrajectoryPoint[];
}

export interface SpatialState {
  camera_id: string;
  track_id: number;
  timestamp_utc?: string;
  border_side: BorderSide;
  crossing_status: CrossingStatus;
  distance_to_border_meters?: number;
  movement_direction: MovementDirection;
  confidence: string;
  ground_contact_point?: { x: number; y: number };
}

export interface BehaviorPrimitive {
  behavior_id: string;
  track_id: number;
  camera_id: string;
  behavior_type: string;
  first_observed_utc?: string;
  last_observed_utc?: string;
  duration_seconds: number;
  confidence?: number;
}

export interface EnvironmentState {
  camera_id: string;
  lighting: LightingCondition;
  visibility: VisibilityQuality;
  quality_score: number;
  brightness?: number;
  contrast?: number;
  noise_estimate?: number;
  blur_score?: number;
}

export interface BorderTrack {
  border_track_id: string;
  target_class: TargetClass;
  camera_sequence: string[];
  active_camera_id: string;
  current_local_track_id: number;
  association_state: AssociationState;
  association_confidence: number;
  direction: MovementDirection;
  duration_seconds: number;
}

export interface SectorContext {
  sector_id: string;
  normality_state: 'NORMAL' | 'UNUSUAL_ACTIVITY' | 'COLD_START';
  expected_density: number;
  observed_count: number;
  anomaly_score: number;
  reasons: string[];
}

export interface EventRecord {
  id: string;
  camera_id: string;
  track_id: number;
  border_track_id?: string;
  event_type: string;
  priority: EventPriority;
  risk_score: number;
  status: EventStatus;
  target_class: TargetClass;
  created_at: string;
  updated_at: string;
  first_observed_utc?: string;
  last_observed_utc?: string;
  duration_seconds?: number;
  detection_confidence?: number;
  track_confidence?: number;
  spatial_confidence?: number;
  environment_quality?: number;
  evidence_confidence?: number;
  reason_codes: string[];
  explanation_summary: string;
  acknowledged_by?: string;
  acknowledged_at?: string;
}

export interface EvidenceRecord {
  id: string;
  event_id: string;
  camera_id: string;
  evidence_type: 'SNAPSHOT_RAW' | 'SNAPSHOT_ANNOTATED' | 'VIDEO_PRE_EVENT' | 'VIDEO_INCIDENT' | 'AUDIT_MANIFEST';
  storage_reference: string;
  sha256: string;
  is_verified: boolean;
  created_at: string;
  metadata?: Record<string, any>;
}

export interface EvidencePackage {
  event_id: string;
  camera_id: string;
  status: string;
  is_sealed: boolean;
  sha256_seal?: string;
  created_at_utc?: string;
  evidence_records: EvidenceRecord[];
  manifest?: any;
}

export interface CameraInfo {
  camera_id: string;
  name: string;
  sector_id: string;
  sector_name: string;
  status: 'ONLINE' | 'DEGRADED' | 'DISCONNECTED' | 'ERROR';
  resolution: string;
  fps_target: number;
  is_calibrated: boolean;
  location?: { lat: number; lng: number; elevation_m: number };
  visible_border_sections: string[];
}

export interface CameraCalibration {
  camera_id: string;
  calibration_status: string;
  border_section_id: string;
  projected_points: { x: number; y: number }[];
  warning_buffer_points?: { x: number; y: number }[];
  reprojection_error_px?: number;
}

export interface TelemetryPacket {
  camera_id: string;
  timestamp_utc: string;
  fps: number;
  is_calibrated: boolean;
  scenario_id?: string;
  environment?: EnvironmentState;
  tracks: TrackState[];
  spatial_states: SpatialState[];
  behavior_primitives: BehaviorPrimitive[];
  border_track?: BorderTrack;
  sector_context?: SectorContext;
  active_events: EventRecord[];
}

export interface DemonstrationScenario {
  id: string;
  title: string;
  category: string;
  camera_id: string;
  description: string;
  duration_seconds: number;
  expected_event: string;
}
