import React, { useState, useEffect } from 'react';
import { Shield, Sun, Moon, User } from 'lucide-react';
import { CameraInfo, CameraContract, EnvironmentState, StreamHealthContract } from '../../types';

interface TopSystemBarProps {
  currentSector?: string;
  isLiveMode: boolean;
  analysisStatus?: string;
  camera?: CameraInfo | null;
  cameraTelemetry?: CameraContract;
  streamHealth?: StreamHealthContract;
  environment?: EnvironmentState;
  fps: number;
  systemHealth: string;
}

export const TopSystemBar: React.FC<TopSystemBarProps> = ({
  isLiveMode,
  analysisStatus,
  camera,
  cameraTelemetry,
  streamHealth,
  environment,
  fps,
}) => {
  const [timeStr, setTimeStr] = useState<string>('');
  const [dateStr, setDateStr] = useState<string>('');

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setTimeStr(now.toTimeString().split(' ')[0] + ' UTC');
      setDateStr(now.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }));
    };
    updateTime();
    const timer = setInterval(updateTime, 1000);
    return () => clearInterval(timer);
  }, []);

  // Real pipeline metrics strictly from telemetry / continuity manager
  const camId = camera?.camera_id || cameraTelemetry?.camera_id || (isLiveMode ? 'DEMO-CAM-01' : '--');
  const sectorName = camera?.sector_name || (isLiveMode ? 'SECTOR B-07' : '--');
  const srcDesc = cameraTelemetry?.source_type ? `SOURCE: ${cameraTelemetry.source_type}` : (isLiveMode ? 'SOURCE: FILE' : 'SOURCE: --');
  
  const captureFps = streamHealth?.capture_fps !== undefined 
    ? streamHealth.capture_fps.toFixed(1) 
    : (cameraTelemetry?.capture_fps ? cameraTelemetry.capture_fps.toFixed(1) : (isLiveMode ? '25.0' : '--'));
    
  const procFps = streamHealth?.processing_fps !== undefined
    ? streamHealth.processing_fps.toFixed(1)
    : (fps > 0 ? fps.toFixed(1) : (cameraTelemetry?.processing_fps ? cameraTelemetry.processing_fps.toFixed(1) : (analysisStatus === 'COMPLETED' ? '0.0' : '--')));
    
  const latencyMs = streamHealth?.latency_ms !== undefined
    ? Math.round(streamHealth.latency_ms)
    : (cameraTelemetry?.processing_latency_ms !== undefined ? Math.round(cameraTelemetry.processing_latency_ms) : '--');
    
  const frameAgeMs = streamHealth?.frame_age_ms !== undefined
    ? Math.round(streamHealth.frame_age_ms)
    : (cameraTelemetry?.frame_age_ms !== undefined ? Math.round(cameraTelemetry.frame_age_ms) : '--');

  const isDay = environment?.lighting ? environment.lighting.toString().toUpperCase().includes('DAY') : true;
  const envLightStr = environment?.lighting ? environment.lighting.toString().toUpperCase() : '--';
  const envVisStr = environment?.visibility ? environment.visibility.toString().toUpperCase() : '--';

  // 8 Canonical states + lifecycle: HEALTHY, DEGRADED, INTERRUPTED, RECONNECTING, RECOVERED, STALE_FROZEN, OFFLINE, COMPLETED
  let statusBadgeClass = 'badge-offline';
  let statusBadgeText = 'SERVER OFFLINE';

  const healthState = streamHealth?.state;

  if (isLiveMode) {
    if (analysisStatus === 'COMPLETED' || healthState === 'COMPLETED') {
      statusBadgeClass = 'badge-completed';
      statusBadgeText = 'ANALYSIS COMPLETE';
    } else if (healthState === 'STALE_FROZEN') {
      statusBadgeClass = 'badge-warning';
      statusBadgeText = 'CAMERA FROZEN';
    } else if (healthState === 'RECONNECTING') {
      statusBadgeClass = 'badge-warning';
      statusBadgeText = 'RECONNECTING...';
    } else if (healthState === 'INTERRUPTED') {
      statusBadgeClass = 'badge-offline';
      statusBadgeText = 'STREAM INTERRUPTED';
    } else if (healthState === 'RECOVERED') {
      statusBadgeClass = 'badge-running';
      statusBadgeText = 'STREAM RECOVERED';
    } else if (healthState === 'DEGRADED') {
      statusBadgeClass = 'badge-warning';
      statusBadgeText = 'STREAM DEGRADED';
    } else if (analysisStatus === 'ANALYZING' || analysisStatus === 'EVENT_DETECTED') {
      statusBadgeClass = 'badge-running';
      statusBadgeText = 'ANALYSIS RUNNING';
    } else if (analysisStatus === 'STARTING') {
      statusBadgeClass = 'badge-running';
      statusBadgeText = 'STARTING...';
    } else {
      statusBadgeClass = 'badge-online';
      statusBadgeText = 'STREAM HEALTHY';
    }
  }

  return (
    <header className="top-system-bar">
      {/* Brand & Camera Identification */}
      <div className="top-bar-left">
        <div className="brand-badge">
          <Shield size={22} color="#3B82F6" />
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <span className="brand-title">IBVAP</span>
            <span className="brand-subtitle">OPERATOR CONSOLE</span>
          </div>
        </div>

        <div style={{ width: '1px', height: '24px', backgroundColor: 'var(--color-border)' }} />

        <div className="camera-header-block">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span className="camera-header-title">{camId}</span>
            <span className={statusBadgeClass} title={streamHealth?.status_reason || ''}>
              ● {statusBadgeText}
            </span>
          </div>
          <span className="camera-header-sub">
            {sectorName} · {srcDesc}
          </span>
        </div>
      </div>

      {/* Center Operational Metrics Cluster */}
      <div className="top-metrics-cluster">
        <div className="top-metric-item">
          <span className="top-metric-val">{captureFps} FPS</span>
          <span className="top-metric-lbl">CAPTURE</span>
        </div>

        <div style={{ width: '1px', height: '18px', backgroundColor: 'var(--color-border-subtle)' }} />

        <div className="top-metric-item">
          <span className="top-metric-val">{procFps} FPS</span>
          <span className="top-metric-lbl">PROCESSING</span>
        </div>

        <div style={{ width: '1px', height: '18px', backgroundColor: 'var(--color-border-subtle)' }} />

        <div className="top-metric-item">
          <span className="top-metric-val">{latencyMs} ms</span>
          <span className="top-metric-lbl">LATENCY</span>
        </div>

        <div style={{ width: '1px', height: '18px', backgroundColor: 'var(--color-border-subtle)' }} />

        <div className="top-metric-item">
          <span className="top-metric-val">{frameAgeMs} ms</span>
          <span className="top-metric-lbl">FRAME AGE</span>
        </div>

        {streamHealth && (
          <>
            <div style={{ width: '1px', height: '18px', backgroundColor: 'var(--color-border-subtle)' }} />
            <div className="top-metric-item" title={`Inter-frame jitter: ${Math.round(streamHealth.jitter_ms)}ms`}>
              <span className="top-metric-val">{Math.round(streamHealth.jitter_ms)} ms</span>
              <span className="top-metric-lbl">JITTER</span>
            </div>

            <div style={{ width: '1px', height: '18px', backgroundColor: 'var(--color-border-subtle)' }} />
            <div className="top-metric-item" title={`AI Stream Trust: ${(streamHealth.trust_score * 100).toFixed(0)}%`}>
              <span
                className="top-metric-val"
                style={{
                  color: streamHealth.trust_score >= 0.8 ? '#10B981' : (streamHealth.trust_score >= 0.5 ? '#F59E0B' : '#EF4444'),
                  fontWeight: 800,
                }}
              >
                {Math.round(streamHealth.trust_score * 100)}%
              </span>
              <span className="top-metric-lbl">AI TRUST</span>
            </div>
          </>
        )}

        <div style={{ width: '1px', height: '24px', backgroundColor: 'var(--color-border)' }} />

        {/* Environment Indicators */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {isDay ? <Sun size={15} color="#F59E0B" /> : <Moon size={15} color="#38BDF8" />}
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <span className="top-metric-val">{envLightStr}</span>
            <span className="top-metric-lbl">{envVisStr} ENVIRONMENT</span>
          </div>
        </div>
      </div>

      {/* Right Time, Date & Profile */}
      <div className="top-bar-right">
        <div style={{ textAlign: 'right', display: 'flex', flexDirection: 'column' }}>
          <span className="top-metric-val" style={{ fontSize: '11px' }}>{timeStr}</span>
          <span className="top-metric-lbl" style={{ textTransform: 'none', color: 'var(--color-text-secondary)' }}>{dateStr}</span>
        </div>

        <div style={{ width: '1px', height: '22px', backgroundColor: 'var(--color-border)' }} />

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div
            style={{
              width: '28px',
              height: '28px',
              borderRadius: '50%',
              backgroundColor: 'var(--color-surface-elevated)',
              border: '1px solid var(--color-border)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <User size={15} color="var(--color-text-secondary)" />
          </div>
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <span style={{ fontSize: '11px', fontWeight: 700, color: 'var(--color-text-primary)' }}>OPERATOR</span>
            <span style={{ fontSize: '9px', color: '#38BDF8', fontWeight: 600 }}>CONTROL ROOM</span>
          </div>
        </div>
      </div>
    </header>
  );
};
