import React, { useRef, useState, useEffect } from 'react';
import { Maximize2, Camera as CameraIcon, Film, AlertCircle } from 'lucide-react';
import { getStreamUrl } from '../../services/api';
import {
  EnvironmentState,
  TrackState,
  SpatialState,
  BehaviorPrimitive,
  EventRecord,
  CameraContract,
} from '../../types';

interface PrimaryVideoPanelProps {
  cameraId: string;
  cameraName?: string;
  fps: number;
  environment?: EnvironmentState;
  tracks: TrackState[];
  spatialStates: SpatialState[];
  behaviors: BehaviorPrimitive[];
  activeEvents: EventRecord[];
  cameraTelemetry?: CameraContract;
  onOpenAddCamera: () => void;
}

export const PrimaryVideoPanel: React.FC<PrimaryVideoPanelProps> = ({
  cameraId,
  cameraTelemetry,
  onOpenAddCamera,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [streamSrc, setStreamSrc] = useState<string>('');
  const [streamError, setStreamError] = useState<boolean>(false);
  const [timeStr, setTimeStr] = useState<string>('');

  useEffect(() => {
    if (cameraId) {
      setStreamSrc(getStreamUrl(cameraId));
      setStreamError(false);
    } else {
      setStreamSrc('');
    }
  }, [cameraId]);

  useEffect(() => {
    const updateTimer = () => {
      const now = new Date();
      setTimeStr(now.toISOString().replace('T', ' ').substring(0, 19) + ' UTC');
    };
    updateTimer();
    const interval = setInterval(updateTimer, 1000);
    return () => clearInterval(interval);
  }, []);

  const handleFullscreen = () => {
    if (containerRef.current) {
      if (document.fullscreenElement) {
        document.exitFullscreen();
      } else {
        containerRef.current.requestFullscreen();
      }
    }
  };

  const camId = cameraId || 'DEMO-CAM-01';

  return (
    <div className="live-video-box" ref={containerRef}>
      {/* Panel Top Header Strip */}
      <div className="panel-header-strip">
        <span style={{ textTransform: 'uppercase' }}>LIVE VIDEO FEED</span>
        <span style={{ fontSize: '10px', color: 'var(--color-text-secondary)', fontFamily: 'var(--font-mono)' }}>
          {cameraTelemetry?.resolution || '1280x720'} · 25.0 FPS
        </span>
      </div>

      {/* Main Video Viewport */}
      <div className="video-screen-container">
        {streamSrc && !streamError ? (
          <img
            src={streamSrc}
            alt="Live Stream"
            className="video-stream-img"
            onError={() => setStreamError(true)}
          />
        ) : (
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '12px',
              padding: '24px',
              textAlign: 'center',
            }}
          >
            <AlertCircle size={32} color="var(--color-amber)" />
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <span style={{ fontWeight: 700, fontSize: '13px' }}>NO ACTIVE VIDEO STREAM</span>
              <span style={{ fontSize: '11px', color: 'var(--color-text-secondary)' }}>
                Camera {camId} is offline or stream is initializing.
              </span>
            </div>
            <button className="btn-neutral-outline" onClick={onOpenAddCamera}>
              Connect Video Stream
            </button>
          </div>
        )}

        {/* Video HUD Overlays: Timestamp + Camera ID (Top-Left) */}
        <div
          style={{
            position: 'absolute',
            top: '10px',
            left: '12px',
            pointerEvents: 'none',
            display: 'flex',
            flexDirection: 'column',
            gap: '2px',
            fontFamily: 'var(--font-mono)',
            fontSize: '10.5px',
            fontWeight: 700,
            color: '#FFFFFF',
            textShadow: '0 1px 3px rgba(0,0,0,0.85)',
          }}
        >
          <span>{timeStr}</span>
          <span>{camId}</span>
        </div>

        {/* Video HUD Overlays: LIVE Badge (Top-Right) */}
        <div
          style={{
            position: 'absolute',
            top: '10px',
            right: '12px',
            pointerEvents: 'none',
            display: 'flex',
            alignItems: 'center',
            gap: '5px',
            background: 'rgba(0, 0, 0, 0.65)',
            border: '1px solid rgba(239, 68, 68, 0.4)',
            padding: '3px 8px',
            borderRadius: '4px',
            fontFamily: 'var(--font-mono)',
            fontSize: '10px',
            fontWeight: 800,
            color: '#FFFFFF',
          }}
        >
          <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: 'var(--color-red)' }} />
          <span>LIVE</span>
        </div>
      </div>

      {/* Bottom Video Controls Strip */}
      <div className="video-control-bar">
        <button
          style={{ background: 'none', border: 'none', color: 'inherit', cursor: 'pointer', display: 'flex', alignItems: 'center' }}
          title="Capture Snapshot"
          onClick={() => window.open(`/api/v1/streams/${camId}/snapshot`, '_blank')}
        >
          <CameraIcon size={14} />
        </button>
        <button
          style={{ background: 'none', border: 'none', color: 'inherit', cursor: 'pointer', display: 'flex', alignItems: 'center' }}
          title="Stream Info"
        >
          <Film size={14} />
        </button>
        <button
          style={{ background: 'none', border: 'none', color: 'inherit', cursor: 'pointer', display: 'flex', alignItems: 'center' }}
          title="Fullscreen Mode"
          onClick={handleFullscreen}
        >
          <Maximize2 size={14} />
        </button>
      </div>
    </div>
  );
};
