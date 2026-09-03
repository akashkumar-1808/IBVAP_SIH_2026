import React from 'react';
import { AlertOctagon, ArrowRight, CheckCircle2 } from 'lucide-react';
import { EventRecord } from '../../types';

interface ActiveSecurityEventBannerProps {
  event?: EventRecord | null;
  onSelectEvent?: (event: EventRecord) => void;
  onAcknowledge?: (eventId: string) => void;
}

export const ActiveSecurityEventBanner: React.FC<ActiveSecurityEventBannerProps> = ({
  event,
  onSelectEvent,
  onAcknowledge,
}) => {
  if (!event) return null;

  const isHighOrCritical = event.priority === 'HIGH' || event.priority === 'CRITICAL';
  const score = event.risk_score;
  const confidencePct = event.confidence ? `${(event.confidence * 100).toFixed(0)}%` : '80%';

  return (
    <div
      style={{
        background: isHighOrCritical ? 'rgba(239, 68, 68, 0.12)' : 'rgba(245, 158, 11, 0.10)',
        border: `2px solid ${isHighOrCritical ? '#ef4444' : '#f59e0b'}`,
        borderRadius: '6px',
        padding: '12px 16px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '16px',
        boxShadow: isHighOrCritical ? '0 0 25px rgba(239, 68, 68, 0.25)' : 'none',
        animation: isHighOrCritical ? 'pulse 2s infinite' : 'none',
      }}
    >
      {/* Alert Icon & Identification */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <div
          style={{
            width: '38px',
            height: '38px',
            borderRadius: '6px',
            background: isHighOrCritical ? '#ef4444' : '#f59e0b',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#fff',
            flexShrink: 0,
          }}
        >
          <AlertOctagon size={22} />
        </div>

        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span
              style={{
                fontSize: '11px',
                fontWeight: 900,
                color: isHighOrCritical ? '#ef4444' : '#f59e0b',
                letterSpacing: '0.08em',
              }}
            >
              🚨 {event.priority} PRIORITY SECURITY EVENT
            </span>
            <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>•</span>
            <span className="font-mono" style={{ fontSize: '11px', color: '#f8fafc' }}>
              ID: {event.id}
            </span>
          </div>

          <div style={{ fontSize: '15px', fontWeight: 800, color: '#ffffff', marginTop: '2px' }}>
            {event.event_type.replace(/_/g, ' ')} — TRACK #{event.track_id}
          </div>

          <div style={{ fontSize: '10.5px', color: 'var(--text-secondary)', marginTop: '2px' }}>
            CAMERA: <strong style={{ color: '#fff' }}>{event.camera_id}</strong> | OCCUPANCY: <strong style={{ color: '#ef4444' }}>RESTRICTED ZONE</strong>
          </div>
        </div>
      </div>

      {/* Center Intelligence Metrics */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '20px', fontFamily: 'var(--font-mono)' }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '9px', color: 'var(--text-muted)' }}>RISK SCORE</div>
          <div style={{ fontSize: '18px', fontWeight: 900, color: isHighOrCritical ? '#ef4444' : '#f59e0b' }}>
            {score.toFixed(1)} <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>/ 100</span>
          </div>
        </div>

        <div style={{ width: '1px', height: '28px', background: 'var(--border-panel)' }} />

        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '9px', color: 'var(--text-muted)' }}>CONFIDENCE</div>
          <div style={{ fontSize: '18px', fontWeight: 800, color: '#10b981' }}>
            {confidencePct}
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        {onAcknowledge && (
          <button
            onClick={() => onAcknowledge(event.id)}
            className="btn-command"
            style={{
              padding: '6px 12px',
              fontSize: '11px',
              background: 'rgba(255,255,255,0.06)',
              border: '1px solid rgba(255,255,255,0.2)',
            }}
          >
            <CheckCircle2 size={13} />
            <span>Acknowledge</span>
          </button>
        )}

        {onSelectEvent && (
          <button
            onClick={() => onSelectEvent(event)}
            className="btn-command btn-primary"
            style={{
              padding: '6px 14px',
              fontSize: '11px',
              fontWeight: 700,
              background: '#ef4444',
              borderColor: '#ef4444',
            }}
          >
            <span>Inspect Evidence</span>
            <ArrowRight size={13} />
          </button>
        )}
      </div>
    </div>
  );
};
