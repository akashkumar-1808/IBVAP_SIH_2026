import React, { useState } from 'react';
import { Crosshair } from 'lucide-react';
import { TrackState, SpatialState, BehaviorPrimitive, CameraInfo } from '../../types';

interface TargetTrackingViewProps {
  tracks: TrackState[];
  spatialStates: SpatialState[];
  behaviors: BehaviorPrimitive[];
  camera: CameraInfo | null;
  fps?: number;
}

export const TargetTrackingView: React.FC<TargetTrackingViewProps> = ({
  tracks,
  spatialStates,
  behaviors,
  camera,
  fps = 25.0,
}) => {
  const [selectedTrackId, setSelectedTrackId] = useState<number | null>(
    tracks.length > 0 ? tracks[0].track_id : null
  );

  const activeTrack = tracks.find((t) => t.track_id === selectedTrackId) || tracks[0] || null;
  const activeSpatial = spatialStates.find((s) => s.track_id === activeTrack?.track_id) || spatialStates[0] || null;
  const activeBehavior = behaviors.find((b) => b.track_id === activeTrack?.track_id) || behaviors[0] || null;

  return (
    <div
      className="target-tracking-workspace"
      style={{
        display: 'grid',
        gridTemplateColumns: '320px 1fr',
        gap: '14px',
        width: '100%',
        height: '100%',
        overflow: 'hidden',
      }}
    >
      {/* Left Column: Active Tracks Queue */}
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          backgroundColor: 'rgba(15, 23, 42, 0.85)',
          border: '1px solid var(--color-border)',
          borderRadius: '6px',
          overflow: 'hidden',
        }}
      >
        <div style={{ padding: '12px', borderBottom: '1px solid var(--color-border-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Crosshair size={16} color="#38BDF8" />
            <span style={{ fontSize: '12px', fontWeight: 800, color: '#F1F5F9', letterSpacing: '0.04em' }}>
              TARGET TRACKS
            </span>
          </div>
          <span style={{ fontSize: '9px', fontWeight: 800, padding: '2px 6px', borderRadius: '3px', backgroundColor: 'rgba(56, 189, 248, 0.2)', color: '#38BDF8' }}>
            {tracks.length} ACTIVE
          </span>
        </div>

        <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column' }}>
          {tracks.length === 0 ? (
            <div style={{ padding: '32px 16px', textAlign: 'center', color: 'var(--color-text-muted)' }}>
              <Crosshair size={28} color="#6B7280" style={{ margin: '0 auto 8px auto', opacity: 0.5 }} />
              <div style={{ fontSize: '11px', fontWeight: 700, color: '#9CA3AF' }}>NO ACTIVE TRACK</div>
              <p style={{ fontSize: '9.5px', color: 'var(--color-text-muted)', marginTop: '4px' }}>
                ByteTrack association is standing by. Targets appearing in Sector B-07 will be tracked here.
              </p>
            </div>
          ) : (
            tracks.map((t) => {
              const isSelected = activeTrack?.track_id === t.track_id;
              return (
                <div
                  key={t.track_id}
                  onClick={() => setSelectedTrackId(t.track_id)}
                  style={{
                    padding: '10px 12px',
                    borderBottom: '1px solid var(--color-border-subtle)',
                    backgroundColor: isSelected ? 'rgba(59, 130, 246, 0.12)' : 'transparent',
                    borderLeft: isSelected ? '3px solid #38BDF8' : '3px solid transparent',
                    cursor: 'pointer',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
                    <span style={{ fontSize: '11px', fontWeight: 800, color: '#F1F5F9' }}>
                      TRACK #{t.track_id}
                    </span>
                    <span style={{ fontSize: '8px', fontWeight: 700, color: '#34D399', backgroundColor: 'rgba(16, 185, 129, 0.15)', padding: '1px 5px', borderRadius: '2px' }}>
                      {t.status}
                    </span>
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '9.5px', color: 'var(--color-text-secondary)' }}>
                    <span>CLASS: {t.class_id}</span>
                    <span>CONF: {t.confidence ? `${Math.round(t.confidence * 100)}%` : '--'}</span>
                  </div>

                  <div style={{ fontSize: '8.5px', color: 'var(--color-text-muted)', marginTop: '2px' }}>
                    AGE: {t.age_frames || 0} frames
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Right Column: Track Kinematic & Trajectory Workspace */}
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          gap: '12px',
          height: '100%',
          overflowY: 'auto',
          paddingRight: '2px',
        }}
      >
        {activeTrack ? (
          <>
            {/* 1. Track Overview Box */}
            <div
              style={{
                backgroundColor: 'rgba(15, 23, 42, 0.85)',
                border: '1px solid var(--color-border)',
                borderRadius: '6px',
                padding: '16px',
                display: 'flex',
                flexDirection: 'column',
                gap: '12px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid var(--color-border-subtle)', paddingBottom: '8px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <h3 style={{ fontSize: '14px', fontWeight: 800, color: '#F1F5F9', margin: 0 }}>
                    TARGET KINEMATICS & SPATIAL DOSSIER: TRACK #{activeTrack.track_id}
                  </h3>
                  <span style={{ fontSize: '8.5px', fontWeight: 800, padding: '2px 8px', borderRadius: '3px', backgroundColor: 'rgba(56, 189, 248, 0.2)', color: '#38BDF8' }}>
                    {activeTrack.class_id}
                  </span>
                </div>

                <div style={{ fontSize: '10px', color: 'var(--color-text-muted)' }}>
                  CAMERA: <strong style={{ color: '#E2E8F0' }}>{camera?.camera_id || 'DEMO-CAM-01'}</strong> · SECTOR B-07
                </div>
              </div>

              {/* 6 Key Kinematic & Spatial Metric Tiles */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px' }}>
                <div style={{ backgroundColor: 'rgba(0,0,0,0.3)', padding: '10px', borderRadius: '4px' }}>
                  <span style={{ fontSize: '8px', color: 'var(--color-text-muted)', fontWeight: 700 }}>SPEED & VELOCITY</span>
                  <div style={{ fontSize: '15px', fontWeight: 800, color: '#10B981', marginTop: '2px' }}>
                    {activeTrack.speed_pixels_per_sec !== undefined ? `${(activeTrack.speed_pixels_per_sec * 0.05).toFixed(1)} m/s` : '--'}
                  </div>
                  <span style={{ fontSize: '8.5px', color: 'var(--color-text-secondary)' }}>
                    DIRECTION: {activeSpatial?.movement_direction || 'MONITORED'}
                  </span>
                </div>

                <div style={{ backgroundColor: 'rgba(0,0,0,0.3)', padding: '10px', borderRadius: '4px' }}>
                  <span style={{ fontSize: '8px', color: 'var(--color-text-muted)', fontWeight: 700 }}>DISTANCE TO BORDER</span>
                  <div style={{ fontSize: '15px', fontWeight: 800, color: activeSpatial?.distance_to_border_meters !== undefined && activeSpatial.distance_to_border_meters < 15 ? '#EF4444' : '#F59E0B', marginTop: '2px' }}>
                    {activeSpatial?.distance_to_border_meters !== undefined ? `${activeSpatial.distance_to_border_meters.toFixed(1)} m` : '--'}
                  </div>
                  <span style={{ fontSize: '8.5px', color: 'var(--color-text-secondary)' }}>
                    ZONE: {activeSpatial?.border_side ? activeSpatial.border_side.replace(/_/g, ' ') : 'MONITORED'}
                  </span>
                </div>

                <div style={{ backgroundColor: 'rgba(0,0,0,0.3)', padding: '10px', borderRadius: '4px' }}>
                  <span style={{ fontSize: '8px', color: 'var(--color-text-muted)', fontWeight: 700 }}>PERSISTENCE & AGE</span>
                  <div style={{ fontSize: '15px', fontWeight: 800, color: '#38BDF8', marginTop: '2px' }}>
                    {activeTrack.age_frames || 0} <span style={{ fontSize: '10px', color: 'var(--color-text-muted)' }}>frames</span>
                  </div>
                  <span style={{ fontSize: '8.5px', color: 'var(--color-text-secondary)' }}>
                    CONFIDENCE: {activeTrack.confidence ? `${Math.round(activeTrack.confidence * 100)}%` : '--'}
                  </span>
                </div>

                <div style={{ backgroundColor: 'rgba(0,0,0,0.3)', padding: '10px', borderRadius: '4px' }}>
                  <span style={{ fontSize: '8px', color: 'var(--color-text-muted)', fontWeight: 700 }}>BEHAVIOR CLASSIFICATION</span>
                  <div style={{ fontSize: '13px', fontWeight: 800, color: '#F59E0B', marginTop: '2px' }}>
                    {activeBehavior?.behavior_type ? activeBehavior.behavior_type.replace(/_/g, ' ') : 'MONITORED_TRANSIT'}
                  </div>
                  <span style={{ fontSize: '8.5px', color: 'var(--color-text-secondary)' }}>
                    CONFIDENCE: {activeBehavior?.confidence ? `${Math.round(activeBehavior.confidence * 100)}%` : '85%'}
                  </span>
                </div>

                <div style={{ backgroundColor: 'rgba(0,0,0,0.3)', padding: '10px', borderRadius: '4px' }}>
                  <span style={{ fontSize: '8px', color: 'var(--color-text-muted)', fontWeight: 700 }}>TRACKING INGESTION</span>
                  <div style={{ fontSize: '13px', fontWeight: 800, color: '#10B981', marginTop: '2px' }}>
                    {fps > 0 ? fps.toFixed(1) : '25.0'} FPS
                  </div>
                  <span style={{ fontSize: '8.5px', color: 'var(--color-text-secondary)' }}>
                    KALMAN CORRELATION ACTIVE
                  </span>
                </div>
              </div>
            </div>

            {/* 2. Visual Trajectory Canvas */}
            <div
              style={{
                backgroundColor: 'rgba(15, 23, 42, 0.85)',
                border: '1px solid var(--color-border)',
                borderRadius: '6px',
                padding: '16px',
                display: 'flex',
                flexDirection: 'column',
                gap: '10px',
                flex: 1,
                minHeight: '340px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontSize: '11px', fontWeight: 800, color: '#F1F5F9', letterSpacing: '0.04em' }}>
                  SPATIAL TRAJECTORY IN CALIBRATED SENSOR SPACE
                </span>
                <span style={{ fontSize: '9px', color: 'var(--color-text-muted)' }}>
                  POINTS: {activeTrack.trajectory ? activeTrack.trajectory.length : 0} WAYPOINTS
                </span>
              </div>

              {/* Trajectory SVG */}
              <div
                style={{
                  flex: 1,
                  backgroundColor: '#070a0f',
                  border: '1px solid var(--color-border-subtle)',
                  borderRadius: '4px',
                  position: 'relative',
                  overflow: 'hidden',
                  minHeight: '260px',
                }}
              >
                <svg viewBox="0 0 600 300" style={{ width: '100%', height: '100%' }}>
                  <defs>
                    <pattern id="trackGrid" width="30" height="30" patternUnits="userSpaceOnUse">
                      <path d="M 30 0 L 0 0 0 30" fill="none" stroke="rgba(255,255,255,0.04)" strokeWidth="0.5" />
                    </pattern>
                  </defs>
                  <rect width="600" height="300" fill="url(#trackGrid)" />

                  {/* Virtual Zones */}
                  <rect x="0" y="200" width="600" height="100" fill="rgba(239, 68, 68, 0.08)" />
                  <text x="14" y="280" fill="#EF4444" fontSize="10" fontWeight="800" opacity="0.6">
                    RESTRICTED ZERO-LINE ZONE (SEC-ALPHA)
                  </text>

                  <rect x="0" y="140" width="600" height="60" fill="rgba(245, 158, 11, 0.06)" />
                  <text x="14" y="180" fill="#F59E0B" fontSize="10" fontWeight="700" opacity="0.6">
                    WARNING BUFFER ZONE (15m)
                  </text>

                  <line x1="0" y1="200" x2="600" y2="200" stroke="#EF4444" strokeWidth="2" strokeDasharray="6,3" />

                  {/* Render trajectory path if available */}
                  {activeTrack.trajectory && activeTrack.trajectory.length > 1 ? (
                    <g>
                      {activeTrack.trajectory.map((pt, idx) => {
                        // Project 1280x720 video coords into 600x300 SVG
                        const px = (pt.x / 1280) * 600;
                        const py = (pt.y / 720) * 300;
                        return (
                          <circle
                            key={idx}
                            cx={px}
                            cy={py}
                            r={idx === activeTrack.trajectory.length - 1 ? 5 : 2.5}
                            fill={idx === activeTrack.trajectory.length - 1 ? '#38BDF8' : '#10B981'}
                            opacity={0.3 + (idx / activeTrack.trajectory.length) * 0.7}
                          />
                        );
                      })}
                    </g>
                  ) : (
                    <g>
                      {/* Current Track Centroid */}
                      <circle cx="300" cy="170" r="6" fill="#38BDF8" />
                      <circle cx="300" cy="170" r="12" fill="none" stroke="#38BDF8" strokeWidth="1" strokeDasharray="3,2" />
                      <text x="316" y="174" fill="#38BDF8" fontSize="10" fontWeight="800">
                        TRACK #{activeTrack.track_id} CURRENT POSITION
                      </text>
                    </g>
                  )}
                </svg>
              </div>
            </div>
          </>
        ) : (
          <div
            style={{
              backgroundColor: 'rgba(15, 23, 42, 0.85)',
              border: '1px solid var(--color-border)',
              borderRadius: '6px',
              padding: '36px',
              textAlign: 'center',
              color: 'var(--color-text-muted)',
              fontSize: '12px',
            }}
          >
            NO ACTIVE TARGETS DETECTED IN PROTOTYPE SECTOR B-07.
          </div>
        )}
      </div>
    </div>
  );
};
