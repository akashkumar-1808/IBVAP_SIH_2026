import React, { useRef, useEffect, useState } from 'react';
import { CameraCalibration, EnvironmentState, SpatialState, TrackState, BehaviorPrimitive, EventRecord, CameraContract } from '../../types';
import { getStreamUrl } from '../../services/api';
import { ArrowUpRight, Video, Plus } from 'lucide-react';

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
  cameraTelemetry?: CameraContract;
  onOpenAddCamera?: () => void;
}

export const PrimaryVideoPanel: React.FC<PrimaryVideoPanelProps> = ({
  cameraId,
  cameraName,
  fps,
  environment,
  tracks,
  spatialStates,
  behaviors,
  activeEvents,
  cameraTelemetry,
  onOpenAddCamera,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [streamSrc, setStreamSrc] = useState<string>('');

  useEffect(() => {
    if (cameraId) {
      setStreamSrc(getStreamUrl(cameraId));
    } else {
      setStreamSrc('');
    }
  }, [cameraId]);

  // Primary active track (highest risk / most active)
  const primaryTrack = tracks[0] || null;
  const primarySpatial = primaryTrack ? spatialStates.find((s) => s.track_id === primaryTrack.track_id) : null;
  const primaryBehaviors = primaryTrack ? behaviors.filter((b) => b.track_id === primaryTrack.track_id) : [];
  const activeEvent = activeEvents[0] || null;

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
          <span style={{ color: 'var(--accent-cyan)' }}>| LIVE HUD</span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', fontFamily: 'var(--font-mono)', fontSize: '10.5px' }}>
          <span>STATUS: <strong style={{ color: cameraTelemetry?.connection_status === 'OFFLINE' ? '#ef4444' : '#10b981' }}>{cameraTelemetry?.connection_status || 'ONLINE'}</strong></span>
          <span>CAP: <strong style={{ color: '#38bdf8' }}>{cameraTelemetry?.capture_fps ? `${cameraTelemetry.capture_fps.toFixed(1)} FPS` : (fps > 0 ? `${fps.toFixed(1)} FPS` : '--')}</strong></span>
          <span>PROC: <strong style={{ color: '#38bdf8' }}>{fps > 0 ? `${fps.toFixed(1)} FPS` : '--'}</strong></span>
          <span>LATENCY: <strong style={{ color: '#a78bfa' }}>{cameraTelemetry?.processing_latency_ms ? `${cameraTelemetry.processing_latency_ms.toFixed(0)}ms` : '--'}</strong></span>
          <span>AGE: <strong style={{ color: '#10b981' }}>{cameraTelemetry?.frame_age_ms !== undefined ? `${cameraTelemetry.frame_age_ms.toFixed(0)}ms` : '--'}</strong></span>
          <span>
            LIGHT: <strong style={{ color: environment?.lighting === 'NIGHT' ? '#38bdf8' : '#10b981' }}>
              {environment?.lighting || '--'}
            </strong>
          </span>
          <span>
            VISIBILITY: <strong style={{ color: environment?.visibility === 'DEGRADED' ? '#f59e0b' : '#10b981' }}>
              {environment?.visibility || '--'}
            </strong>
          </span>
        </div>
      </div>

      {/* Main Video Viewport with Interactive SVG Overlay */}
      <div className="video-wrapper" ref={containerRef}>
        {streamSrc ? (
          <img
            src={streamSrc}
            alt={`Live stream for ${cameraId}`}
            className="video-element"
            onError={() => console.warn('Stream buffering or reconnecting...')}
          />
        ) : (
          <div
            style={{
              width: '100%',
              height: '100%',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              background: '#070a0f',
              gap: '12px',
            }}
          >
            <Video size={36} color="var(--accent-cyan)" />
            <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--text-primary)' }}>
              NO LIVE STREAM CONNECTED
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', maxWidth: '360px', textAlign: 'center' }}>
              Add a live RTSP stream URL to initiate real-time video ingestion, YOLO object detection, ByteTrack, and spatial border reasoning.
            </div>
            {onOpenAddCamera && (
              <button
                onClick={onOpenAddCamera}
                className="btn-command btn-primary"
                style={{ padding: '8px 16px', marginTop: '4px', gap: '6px' }}
              >
                <Plus size={14} />
                <span>Connect Live RTSP Camera</span>
              </button>
            )}
          </div>
        )}

        {/* Backend OpenCV visualizer is the single source of truth for HUD annotations. */}

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
                  {primarySpatial?.border_side || 'PERMITTED'}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>BEHAVIOUR</span>
                <span style={{ color: primaryBehaviors.length > 0 ? '#f59e0b' : 'var(--text-muted)', fontWeight: 600, textAlign: 'right' }}>
                  {primaryBehaviors.length > 0 ? primaryBehaviors.map((b) => b.behavior_type).join(', ') : 'NONE'}
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
                <div style={{ fontSize: '14px', fontWeight: 800, color: activeEvent ? '#ef4444' : '#10b981', fontFamily: 'var(--font-mono)' }}>
                  {activeEvent ? activeEvent.risk_score.toFixed(1) : '0.0'} <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>/ 100</span>
                </div>
              </div>
              <span className={`status-pill ${activeEvent ? 'pill-red' : 'pill-green'}`}>
                {activeEvent?.priority || 'NORMAL'}
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
