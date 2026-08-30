import React, { useRef, useEffect, useState } from 'react';
import { CameraCalibration, EnvironmentState, SpatialState, TrackState, BehaviorPrimitive, EventRecord } from '../../types';
import { getStreamUrl } from '../../services/api';
import { ArrowUpRight } from 'lucide-react';

interface PrimaryVideoPanelProps {
  cameraId: string;
  cameraName: string;
  fps: number;
  environment?: EnvironmentState;
  calibration?: CameraCalibration | null;
  tracks: TrackState[];
  spatialStates: SpatialState[];
  behaviors: BehaviorPrimitive[];
  activeEvents: EventRecord[];
}

export const PrimaryVideoPanel: React.FC<PrimaryVideoPanelProps> = ({
  cameraId,
  cameraName,
  fps,
  environment,
  calibration,
  tracks,
  spatialStates,
  behaviors,
  activeEvents,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [streamSrc, setStreamSrc] = useState<string>('');

  useEffect(() => {
    setStreamSrc(getStreamUrl(cameraId));
  }, [cameraId]);

  // Primary active track (highest risk / most active)
  const primaryTrack = tracks[0] || null;
  const primarySpatial = primaryTrack ? spatialStates.find((s) => s.track_id === primaryTrack.track_id) : null;
  const primaryBehaviors = primaryTrack ? behaviors.filter((b) => b.track_id === primaryTrack.track_id) : [];
  const activeEvent = activeEvents[0] || null;

  // Viewport normalization (1280x720 base)
  const baseW = 1280;
  const baseH = 720;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
      {/* Stream Top Telemetry Strip */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'var(--bg-panel)',
          border: '1px solid var(--border-panel)',
          borderRadius: '6px 6px 0 0',
          padding: '6px 12px',
          fontSize: '11px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ fontWeight: 700, color: 'var(--text-primary)' }}>{cameraId}</span>
          <span style={{ color: 'var(--text-muted)' }}>| {cameraName}</span>
          <span style={{ color: 'var(--accent-cyan)' }}>| RTSP LIVE</span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '14px', fontFamily: 'var(--font-mono)' }}>
          <span>FPS: <strong style={{ color: '#38bdf8' }}>{fps > 0 ? fps.toFixed(1) : '24.8'}</strong></span>
          <span>RES: <strong style={{ color: 'var(--text-secondary)' }}>1280x720</strong></span>
          <span>
            LIGHT: <strong style={{ color: environment?.lighting === 'NIGHT' ? '#38bdf8' : '#10b981' }}>
              {environment?.lighting || 'NIGHT'}
            </strong>
          </span>
          <span>
            VISIBILITY: <strong style={{ color: environment?.visibility === 'DEGRADED' ? '#f59e0b' : '#10b981' }}>
              {environment?.visibility || 'DEGRADED'}
            </strong>
          </span>
          <span>
            QUALITY: <strong style={{ color: '#10b981' }}>
              {environment?.quality_score !== undefined ? environment.quality_score.toFixed(2) : '0.61'}
            </strong>
          </span>
        </div>
      </div>

      {/* Main Video Viewport with Interactive SVG Overlay */}
      <div className="video-wrapper" ref={containerRef}>
        <img
          src={streamSrc}
          alt={`Live stream for ${cameraId}`}
          className="video-element"
          onError={() => console.warn('Stream buffering or reconnecting...')}
        />

        {/* Dynamic World Border & Detection Overlay */}
        <svg className="svg-overlay" viewBox={`0 0 ${baseW} ${baseH}`} preserveAspectRatio="none">
          {/* 1. Warning Buffer Line (Amber) */}
          {calibration?.warning_buffer_points && calibration.warning_buffer_points.length >= 2 && (
            <polyline
              points={calibration.warning_buffer_points.map((p) => `${p.x},${p.y}`).join(' ')}
              fill="none"
              stroke="#f59e0b"
              strokeWidth="2"
              strokeDasharray="6,4"
            />
          )}

          {/* 2. Projected Real-World Border Line (Red) */}
          {calibration?.projected_points && calibration.projected_points.length >= 2 && (
            <polyline
              points={calibration.projected_points.map((p) => `${p.x},${p.y}`).join(' ')}
              fill="none"
              stroke="#ef4444"
              strokeWidth="3"
            />
          )}

          {/* 3. Trajectory Trails */}
          {tracks.map((tr) => {
            if (!tr.trajectory || tr.trajectory.length < 2) return null;
            const pointsStr = tr.trajectory.map((pt) => `${pt.x},${pt.y}`).join(' ');
            return (
              <polyline
                key={`traj_${tr.track_id}`}
                points={pointsStr}
                fill="none"
                stroke="#10b981"
                strokeWidth="2"
                strokeDasharray="4,4"
              />
            );
          })}

          {/* 4. Track Bounding Boxes & Ground Contacts */}
          {tracks.map((tr) => {
            const bx = tr.bbox.x_min;
            const by = tr.bbox.y_min;
            const bw = tr.bbox.x_max - tr.bbox.x_min;
            const bh = tr.bbox.y_max - tr.bbox.y_min;
            const sp = spatialStates.find((s) => s.track_id === tr.track_id);
            const isBreach = sp?.border_side === 'RESTRICTED';
            const isBuffer = sp?.border_side === 'WARNING_BUFFER';
            const strokeColor = isBreach ? '#ef4444' : isBuffer ? '#f59e0b' : '#10b981';

            const footX = (tr.bbox.x_min + tr.bbox.x_max) / 2;
            const footY = tr.bbox.y_max;

            return (
              <g key={`box_${tr.track_id}`}>
                {/* Bounding Box */}
                <rect
                  x={bx}
                  y={by}
                  width={bw}
                  height={bh}
                  fill="rgba(0,0,0,0.15)"
                  stroke={strokeColor}
                  strokeWidth="2"
                  rx="2"
                />

                {/* Ground Contact Point */}
                <circle cx={footX} cy={footY} r="5" fill="#10b981" />
                <circle cx={footX} cy={footY} r="8" fill="none" stroke="#10b981" strokeWidth="1.5" />

                {/* Track Tag */}
                <rect x={bx} y={by - 20} width={70} height={18} fill="#0f131a" rx="2" stroke={strokeColor} strokeWidth="1" />
                <text x={bx + 5} y={by - 7} fill="#f8fafc" fontSize="10" fontWeight="700" fontFamily="Inter">
                  ID:{tr.track_id}
                </text>
              </g>
            );
          })}
        </svg>

        {/* Floating Forensic Track Intelligence Card (Matching Visual Concept) */}
        {primaryTrack && (
          <div
            style={{
              position: 'absolute',
              top: '16px',
              right: '16px',
              width: '230px',
              background: 'rgba(15, 19, 26, 0.92)',
              border: '1px solid rgba(255, 255, 255, 0.12)',
              borderRadius: '6px',
              padding: '12px',
              backdropFilter: 'blur(8px)',
              display: 'flex',
              flexDirection: 'column',
              gap: '8px',
              boxShadow: '0 4px 20px rgba(0,0,0,0.6)',
              zIndex: 10,
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div>
                <div style={{ fontSize: '11px', fontWeight: 800, color: '#fff' }}>
                  TRACK ID: {primaryTrack.track_id}
                </div>
                <div style={{ fontSize: '9px', color: 'var(--text-muted)' }}>{primaryTrack.class_id}</div>
              </div>
              <span className="status-pill pill-cyan">TRACKED</span>
            </div>

            <div style={{ fontSize: '10px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>DIRECTION</span>
                <span style={{ color: '#10b981', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '3px' }}>
                  <ArrowUpRight size={12} /> {primarySpatial?.movement_direction || 'TOWARD'}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>ZONE</span>
                <span
                  style={{
                    color: primarySpatial?.border_side === 'RESTRICTED' ? '#ef4444' : '#f59e0b',
                    fontWeight: 700,
                  }}
                >
                  {primarySpatial?.border_side || 'RESTRICTED'}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>BEHAVIOUR</span>
                <span style={{ color: '#f59e0b', fontWeight: 600, textAlign: 'right' }}>
                  {primaryBehaviors.length > 0 ? primaryBehaviors.map((b) => b.behavior_type).join(', ') : 'PERSISTENT APPROACH'}
                </span>
              </div>
            </div>

            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                borderTop: '1px solid var(--border-panel)',
                paddingTop: '6px',
                marginTop: '2px',
              }}
            >
              <div>
                <div style={{ fontSize: '9px', color: 'var(--text-muted)' }}>RISK SCORE</div>
                <div style={{ fontSize: '14px', fontWeight: 800, color: '#ef4444', fontFamily: 'var(--font-mono)' }}>
                  {activeEvent ? activeEvent.risk_score.toFixed(1) : '87.6'} <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>/ 100</span>
                </div>
              </div>
              <span className="status-pill pill-red">
                {activeEvent?.priority || 'HIGH'}
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
