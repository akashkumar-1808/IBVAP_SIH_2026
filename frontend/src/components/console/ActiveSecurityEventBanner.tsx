import React from 'react';
import { AlertTriangle, Check, ArrowRight, ShieldCheck } from 'lucide-react';
import { EventRecord } from '../../types';

interface ActiveSecurityEventBannerProps {
  event?: EventRecord | null;
  onSelectEvent: (event: EventRecord) => void;
  onAcknowledge: (eventId: string) => void;
}

export const ActiveSecurityEventBanner: React.FC<ActiveSecurityEventBannerProps> = ({
  event,
  onSelectEvent,
  onAcknowledge,
}) => {
  if (!event) {
    return (
      <div
        className="active-security-banner"
        style={{
          borderColor: 'var(--color-border)',
          backgroundColor: 'var(--color-surface-dark)',
        }}
      >
        <div className="alert-left-block">
          <div
            className="alert-icon-square"
            style={{
              backgroundColor: 'var(--color-green-bg)',
              borderColor: 'rgba(16, 185, 129, 0.3)',
              color: 'var(--color-green)',
            }}
          >
            <ShieldCheck size={20} />
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
            <span style={{ fontSize: '10px', fontWeight: 700, color: 'var(--color-green)', textTransform: 'uppercase' }}>
              BORDER SECTOR SECURE
            </span>
            <span className="alert-title-main" style={{ fontSize: '13px' }}>
              No Active Security Intrusions Detected
            </span>
            <span className="alert-desc-meta">
              Autonomous spatial monitoring active · All perimeter zones clear
            </span>
          </div>
        </div>
      </div>
    );
  }

  const isMedium = event.priority === 'MEDIUM';

  const riskScore = typeof event.risk_score === 'number' ? event.risk_score.toFixed(1) : '0.0';
  const eventConfidence = event.evidence_confidence
    ? Math.round(event.evidence_confidence * 100)
    : (event.detection_confidence ? Math.round(event.detection_confidence * 100) : 0);

  const eventTitle = `${event.event_type.replace(/_/g, ' ')} — TRACK #${event.track_id}`;
  const occupancyZone = event.reason_codes && event.reason_codes.some(rc => rc.toLowerCase().includes('restricted'))
    ? 'RESTRICTED ZONE'
    : (event.reason_codes && event.reason_codes.some(rc => rc.toLowerCase().includes('buffer')) ? 'WARNING BUFFER' : 'PERIMETER');

  return (
    <div className={`active-security-banner ${isMedium ? 'medium' : ''}`}>
      {/* Left: Icon & Incident Identification */}
      <div className="alert-left-block">
        <div className={`alert-icon-square ${isMedium ? 'medium' : ''}`}>
          <AlertTriangle size={22} />
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
          <span className="alert-title-sub">
            {event.priority} PRIORITY SECURITY EVENT
          </span>
          <span className="alert-title-main">
            {eventTitle}
          </span>
          <span className="alert-desc-meta">
            CAMERA: {event.camera_id} · OCCUPANCY: {occupancyZone}
          </span>
        </div>
      </div>

      {/* Right: Risk Score, Confidence & Actions */}
      <div className="alert-right-block">
        <div className="alert-score-gauge">
          <div className="alert-score-label">RISK SCORE</div>
          <div className="alert-score-large" style={{ color: isMedium ? 'var(--color-amber)' : 'var(--color-red)' }}>
            {riskScore} <span style={{ fontSize: '12px', color: 'var(--color-text-muted)' }}>/ 100</span>
          </div>
          <div style={{ fontSize: '10px', color: 'var(--color-text-secondary)', display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '6px' }}>
            <span>CONFIDENCE <strong>{eventConfidence}%</strong></span>
            <span
              style={{
                fontSize: '8px',
                fontWeight: 800,
                color: isMedium ? 'var(--color-amber)' : 'var(--color-red)',
                backgroundColor: isMedium ? 'var(--color-amber-bg)' : 'var(--color-red-bg)',
                padding: '1px 4px',
                borderRadius: '2px',
              }}
            >
              {event.priority}
            </span>
          </div>
        </div>

        <div className="alert-actions-cluster">
          <button
            className="btn-neutral-outline"
            onClick={() => onAcknowledge(event.id)}
            title="Mark event acknowledged by operator"
          >
            <Check size={12} />
            Acknowledge Event
          </button>

          <button
            className="btn-alert-solid"
            style={{ backgroundColor: isMedium ? 'var(--color-amber)' : 'var(--color-red)', borderColor: isMedium ? 'var(--color-amber)' : 'var(--color-red)' }}
            onClick={() => onSelectEvent(event)}
            title="Inspect forensic evidence package"
          >
            Inspect Evidence
            <ArrowRight size={12} />
          </button>
        </div>
      </div>
    </div>
  );
};
