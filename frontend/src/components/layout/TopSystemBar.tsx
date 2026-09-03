import React, { useState, useEffect } from 'react';
import { Shield, Activity, Eye, Video } from 'lucide-react';
import { CameraInfo, CameraContract, EnvironmentState } from '../../types';

interface TopSystemBarProps {
  currentSector: string;
  isLiveMode: boolean;
  camera?: CameraInfo | null;
  cameraTelemetry?: CameraContract;
  environment?: EnvironmentState;
  fps: number;
  systemHealth: string;
}

export const TopSystemBar: React.FC<TopSystemBarProps> = ({
  currentSector,
  isLiveMode,
  camera,
  cameraTelemetry,
  environment,
  fps,
  systemHealth,
}) => {
  const [timeStr, setTimeStr] = useState<string>('');

  useEffect(() => {
    const update = () => {
      const now = new Date();
      setTimeStr(
        now.toLocaleTimeString('en-GB', { hour12: false }) +
          ' ' +
          now.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
      );
    };
    update();
    const interval = setInterval(update, 1000);
    return () => clearInterval(interval);
  }, []);

  const isOnline = cameraTelemetry ? cameraTelemetry.connection_status === 'ONLINE' : (camera?.status === 'ONLINE');
  const camId = cameraTelemetry?.camera_id || camera?.camera_id || 'DEMO-CAM-01';
  const sourceType = cameraTelemetry?.source_type || 'MP4 REPLAY';
  const captureFps = cameraTelemetry?.capture_fps ? cameraTelemetry.capture_fps.toFixed(1) : (fps > 0 ? fps.toFixed(1) : '--');
  const processingFps = cameraTelemetry?.processing_fps ? cameraTelemetry.processing_fps.toFixed(1) : (fps > 0 ? fps.toFixed(1) : '--');
  const latencyMs = cameraTelemetry?.processing_latency_ms ? `${cameraTelemetry.processing_latency_ms.toFixed(0)}ms` : '--';
  const frameAgeMs = cameraTelemetry?.frame_age_ms !== undefined ? `${cameraTelemetry.frame_age_ms.toFixed(0)}ms` : '--';
  const lighting = environment?.lighting || 'DAYLIGHT';
  const visibility = environment?.visibility || 'HIGH';

  return (
    <header className="top-bar">
      {/* Brand & Active Camera */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div
            style={{
              width: '28px',
              height: '28px',
              borderRadius: '6px',
              background: 'rgba(6, 182, 212, 0.15)',
              border: '1px solid rgba(6, 182, 212, 0.4)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#06b6d4',
            }}
          >
            <Shield size={16} />
          </div>
          <div>
            <div style={{ fontWeight: 800, fontSize: '13px', letterSpacing: '0.05em' }}>IBVAP</div>
            <div style={{ fontSize: '9px', color: 'var(--text-muted)', lineHeight: 1 }}>OPERATOR CONSOLE</div>
          </div>
        </div>

        <div style={{ width: '1px', height: '24px', background: 'var(--border-panel)' }} />

        <div>
          <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span>{camId}</span>
            <span style={{ fontSize: '10px', color: 'var(--text-muted)', fontWeight: 400 }}>({currentSector})</span>
          </div>
          <div style={{ fontSize: '9px', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <Video size={10} color="var(--accent-cyan)" />
            <span>SOURCE: {sourceType}</span>
          </div>
        </div>

        <div className={`status-pill ${isOnline ? 'pill-green' : 'pill-red'}`}>
          <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: isOnline ? '#10b981' : '#ef4444', display: 'inline-block' }} />
          {isOnline ? 'ONLINE' : 'OFFLINE'}
        </div>
      </div>

      {/* Center Operational Telemetry Metrics */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px', fontFamily: 'var(--font-mono)' }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '11px', fontWeight: 700, color: '#38bdf8' }}>
            {captureFps} / {processingFps}
          </div>
          <div style={{ fontSize: '8.5px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>CAP / PROC FPS</div>
        </div>

        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '11px', fontWeight: 700, color: '#a78bfa' }}>
            {latencyMs}
          </div>
          <div style={{ fontSize: '8.5px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>LATENCY</div>
        </div>

        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '11px', fontWeight: 700, color: '#10b981' }}>
            {frameAgeMs}
          </div>
          <div style={{ fontSize: '8.5px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>FRAME AGE</div>
        </div>

        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-primary)' }}>
            {lighting} · {visibility}
          </div>
          <div style={{ fontSize: '8.5px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>ENVIRONMENT</div>
        </div>

        <div style={{ textAlign: 'center' }}>
          <div className={`status-pill ${isLiveMode ? 'pill-green' : 'pill-amber'}`} style={{ fontSize: '9px', padding: '1px 6px' }}>
            <Activity size={9} />
            {isLiveMode ? systemHealth : 'CONNECTING'}
          </div>
        </div>
      </div>

      {/* Right UTC Clock & Control Room Profile */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: '11.5px', fontWeight: 600, fontFamily: 'var(--font-mono)' }}>{timeStr}</div>
          <div style={{ fontSize: '8.5px', color: 'var(--text-muted)' }}>UTC SYNCHRONIZED</div>
        </div>

        <div style={{ width: '1px', height: '24px', background: 'var(--border-panel)' }} />

        <div style={{ display: 'flex', alignItems: 'center', gap: '7px' }}>
          <div
            style={{
              width: '26px',
              height: '26px',
              borderRadius: '50%',
              background: 'rgba(255, 255, 255, 0.08)',
              border: '1px solid rgba(255, 255, 255, 0.15)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--text-secondary)',
            }}
          >
            <Eye size={13} />
          </div>
          <div>
            <div style={{ fontSize: '10.5px', fontWeight: 600 }}>OPERATOR</div>
            <div style={{ fontSize: '8.5px', color: 'var(--accent-cyan)' }}>CONTROL ROOM</div>
          </div>
        </div>
      </div>
    </header>
  );
};
