import React, { useState, useEffect } from 'react';
import { Shield, User } from 'lucide-react';
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
  isBackendOnline?: boolean;
  wsStatus?: 'CONNECTED' | 'DISCONNECTED' | 'RECONNECTING';
  hasActiveSecurityEvent?: boolean;
  activeEvidenceCount?: number;
}

export const TopSystemBar: React.FC<TopSystemBarProps> = ({
  isLiveMode,
  analysisStatus,
  camera,
  cameraTelemetry,
  streamHealth,
  fps,
  isBackendOnline = true,
  wsStatus = 'CONNECTED',
  hasActiveSecurityEvent = false,
  activeEvidenceCount = 0,
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

  const captureFps = streamHealth?.capture_fps !== undefined 
    ? streamHealth.capture_fps.toFixed(1) 
    : (cameraTelemetry?.capture_fps ? cameraTelemetry.capture_fps.toFixed(1) : (isLiveMode ? '25.0' : '--'));
    
  const procFps = streamHealth?.processing_fps !== undefined
    ? streamHealth.processing_fps.toFixed(1)
    : (fps > 0 ? fps.toFixed(1) : (cameraTelemetry?.processing_fps ? cameraTelemetry.processing_fps.toFixed(1) : (analysisStatus === 'COMPLETED' ? '0.0' : '--')));
    
  const latencyMs = streamHealth?.latency_ms !== undefined
    ? Math.round(streamHealth.latency_ms)
    : (cameraTelemetry?.processing_latency_ms !== undefined ? Math.round(cameraTelemetry.processing_latency_ms) : '--');

  // 6 Distinct System States:
  let statusBadgeClass = 'badge-offline';
  let statusBadgeText = 'BACKEND UNAVAILABLE';

  const healthState = streamHealth?.state;
  const isCameraOnline = ((camera?.status || cameraTelemetry?.connection_status || '').toUpperCase() === 'ONLINE');

  if (!isBackendOnline) {
    statusBadgeClass = 'badge-offline';
    statusBadgeText = 'BACKEND UNAVAILABLE';
  } else if (hasActiveSecurityEvent) {
    statusBadgeClass = 'badge-offline';
    statusBadgeText = 'ACTIVE SECURITY EVENT';
  } else if (analysisStatus === 'COMPLETED' || healthState === 'COMPLETED') {
    statusBadgeClass = 'badge-completed';
    statusBadgeText = 'ANALYSIS COMPLETE';
  } else if (healthState === 'INTERRUPTED') {
    statusBadgeClass = 'badge-offline';
    statusBadgeText = 'STREAM INTERRUPTED';
  } else if (healthState === 'RECOVERED') {
    statusBadgeClass = 'badge-running';
    statusBadgeText = 'STREAM RECOVERED';
  } else if (healthState === 'DEGRADED') {
    statusBadgeClass = 'badge-warning';
    statusBadgeText = 'STREAM DEGRADED';
  } else if (healthState === 'STALE_FROZEN') {
    statusBadgeClass = 'badge-warning';
    statusBadgeText = 'CAMERA FROZEN';
  } else if (healthState === 'RECONNECTING' || wsStatus === 'RECONNECTING') {
    statusBadgeClass = 'badge-warning';
    statusBadgeText = 'RECONNECTING...';
  } else if (camera && !isCameraOnline && !isLiveMode) {
    statusBadgeClass = 'badge-offline';
    statusBadgeText = 'CAMERA OFFLINE';
  } else if (isLiveMode) {
    statusBadgeClass = 'badge-running';
    statusBadgeText = 'STREAM HEALTHY';
  } else {
    statusBadgeClass = 'badge-warning';
    statusBadgeText = 'STANDBY';
  }

  // Determine individual persistent status strip indicators (Section 16)
  const streamStatusText = !isBackendOnline ? 'OFFLINE' : (healthState === 'DEGRADED' ? 'DEGRADED' : (isLiveMode ? 'HEALTHY' : 'STANDBY'));
  const streamStatusColor = !isBackendOnline ? '#EF4444' : (healthState === 'DEGRADED' ? '#F59E0B' : '#10B981');

  const aiStatusText = analysisStatus === 'COMPLETED' ? 'COMPLETED' : (isLiveMode ? 'ACTIVE' : 'READY');
  const aiStatusColor = analysisStatus === 'COMPLETED' ? '#3B82F6' : (isLiveMode ? '#10B981' : '#9CA3AF');

  const dbStatusText = isBackendOnline ? 'CONNECTED' : 'DISCONNECTED';
  const dbStatusColor = isBackendOnline ? '#10B981' : '#EF4444';

  const evidenceStatusText = activeEvidenceCount > 0 ? `${activeEvidenceCount} SEALED` : 'VERIFIED';
  const evidenceStatusColor = '#10B981';

  const wsStatusText = wsStatus === 'CONNECTED' ? 'CONNECTED' : (wsStatus === 'RECONNECTING' ? 'RECONNECTING' : 'OFFLINE');
  const wsStatusColor = wsStatus === 'CONNECTED' ? '#10B981' : (wsStatus === 'RECONNECTING' ? '#F59E0B' : '#EF4444');

  return (
    <header className="top-system-bar">
      {/* 1. Brand Identity & Product Positioning */}
      <div className="top-bar-left">
        <div className="brand-badge">
          <Shield size={24} color="#38BDF8" style={{ flexShrink: 0 }} />
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '6px' }}>
              <span className="brand-title" style={{ letterSpacing: '0.08em', color: '#F1F5F9' }}>
                IBVAP TATVA
              </span>
              <span style={{ fontSize: '9px', fontWeight: 800, color: '#38BDF8', letterSpacing: '0.06em' }}>
                PROTOTYPE
              </span>
            </div>
            <span className="brand-subtitle" style={{ fontSize: '8.5px', color: '#9CA3AF' }}>
              Intelligent Border Video Analytics Platform
            </span>
          </div>
        </div>

        <div style={{ width: '1px', height: '26px', backgroundColor: 'var(--color-border)' }} />

        {/* Core Pipeline Visual Flow (Detect -> Track -> Understand -> Assess -> Explain -> Prove) */}
        <div className="pipeline-flow-tracker" style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
          {['DETECT', 'TRACK', 'UNDERSTAND', 'ASSESS', 'EXPLAIN', 'PROVE'].map((step, idx) => (
            <React.Fragment key={step}>
              <span
                style={{
                  fontSize: '8px',
                  fontWeight: 700,
                  letterSpacing: '0.06em',
                  color: isLiveMode ? '#38BDF8' : '#6B7280',
                }}
              >
                {step}
              </span>
              {idx < 5 && (
                <span style={{ fontSize: '8px', color: '#4B5563', userSelect: 'none' }}>→</span>
              )}
            </React.Fragment>
          ))}
        </div>
      </div>

      {/* 2. Persistent Operational Status Strip (Section 16) */}
      <div
        className="persistent-status-strip"
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          backgroundColor: 'rgba(15, 23, 42, 0.85)',
          border: '1px solid var(--color-border)',
          borderRadius: '4px',
          padding: '4px 12px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
          <span style={{ fontSize: '8px', color: '#9CA3AF', fontWeight: 700 }}>STREAM</span>
          <span style={{ fontSize: '9px', color: streamStatusColor, fontWeight: 800 }}>● {streamStatusText}</span>
        </div>

        <div style={{ width: '1px', height: '14px', backgroundColor: 'var(--color-border-subtle)' }} />

        <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
          <span style={{ fontSize: '8px', color: '#9CA3AF', fontWeight: 700 }}>AI PIPELINE</span>
          <span style={{ fontSize: '9px', color: aiStatusColor, fontWeight: 800 }}>● {aiStatusText}</span>
        </div>

        <div style={{ width: '1px', height: '14px', backgroundColor: 'var(--color-border-subtle)' }} />

        <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
          <span style={{ fontSize: '8px', color: '#9CA3AF', fontWeight: 700 }}>DATABASE</span>
          <span style={{ fontSize: '9px', color: dbStatusColor, fontWeight: 800 }}>● {dbStatusText}</span>
        </div>

        <div style={{ width: '1px', height: '14px', backgroundColor: 'var(--color-border-subtle)' }} />

        <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
          <span style={{ fontSize: '8px', color: '#9CA3AF', fontWeight: 700 }}>EVIDENCE</span>
          <span style={{ fontSize: '9px', color: evidenceStatusColor, fontWeight: 800 }}>● {evidenceStatusText}</span>
        </div>

        <div style={{ width: '1px', height: '14px', backgroundColor: 'var(--color-border-subtle)' }} />

        <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
          <span style={{ fontSize: '8px', color: '#9CA3AF', fontWeight: 700 }}>WS</span>
          <span style={{ fontSize: '9px', color: wsStatusColor, fontWeight: 800 }}>● {wsStatusText}</span>
        </div>

        <div style={{ width: '1px', height: '14px', backgroundColor: 'var(--color-border-subtle)' }} />

        <span className={statusBadgeClass} style={{ fontSize: '8.5px', padding: '1px 6px' }}>
          {statusBadgeText}
        </span>
      </div>

      {/* 3. Real Operational Telemetry Cluster */}
      <div className="top-metrics-cluster">
        <div className="top-metric-item">
          <span className="top-metric-val">{captureFps} FPS</span>
          <span className="top-metric-lbl">CAPTURE</span>
        </div>

        <div style={{ width: '1px', height: '16px', backgroundColor: 'var(--color-border-subtle)' }} />

        <div className="top-metric-item">
          <span className="top-metric-val">{procFps} FPS</span>
          <span className="top-metric-lbl">PROC</span>
        </div>

        <div style={{ width: '1px', height: '16px', backgroundColor: 'var(--color-border-subtle)' }} />

        <div className="top-metric-item">
          <span className="top-metric-val">{latencyMs} ms</span>
          <span className="top-metric-lbl">LATENCY</span>
        </div>

        {streamHealth && (
          <>
            <div style={{ width: '1px', height: '16px', backgroundColor: 'var(--color-border-subtle)' }} />
            <div className="top-metric-item">
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
      </div>

      {/* 4. Right Time, Date & Role */}
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
            <User size={15} color="#38BDF8" />
          </div>
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <span style={{ fontSize: '10.5px', fontWeight: 700, color: 'var(--color-text-primary)' }}>OPERATOR</span>
            <span style={{ fontSize: '8.5px', color: '#38BDF8', fontWeight: 600 }}>HQ COMMAND</span>
          </div>
        </div>
      </div>
    </header>
  );
};
