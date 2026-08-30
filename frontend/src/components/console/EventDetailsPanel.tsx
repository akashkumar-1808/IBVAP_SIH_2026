import React from 'react';
import { CheckCircle2 } from 'lucide-react';
import { EventRecord } from '../../types';

interface EventDetailsPanelProps {
  event?: EventRecord | null;
  onAcknowledge?: (eventId: string) => void;
}

export const EventDetailsPanel: React.FC<EventDetailsPanelProps> = ({ event, onAcknowledge }) => {
  if (!event) {
    return (
      <div
        className="forensic-panel"
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'var(--text-muted)',
          fontSize: '11px',
          textAlign: 'center',
          gap: '6px',
        }}
      >
        <div style={{ fontWeight: 600, color: 'var(--text-secondary)' }}>NO INCIDENT SELECTED</div>
        <div>Select an event or trigger a scenario to view reason codes</div>
      </div>
    );
  }

  const ev = event;

  // Convert raw reason codes into clean human-readable labels
  const formatReason = (code: string): string => {
    return code
      .toLowerCase()
      .replace(/_/g, ' ')
      .replace(/\b\w/g, (c) => c.toUpperCase());
  };

  return (
    <div className="forensic-panel" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
      {/* Left: Event Metadata Details */}
      <div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
          <span className="intel-card-header">EVENT DETAILS</span>
          <span className="status-pill pill-red" style={{ fontSize: '9px' }}>
            {ev.priority}
          </span>
        </div>

        <div style={{ fontSize: '15px', fontWeight: 800, color: '#f8fafc', marginBottom: '6px' }}>
          {ev.event_type.replace(/_/g, ' ')}
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '11px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ color: 'var(--text-muted)' }}>EVENT ID</span>
            <span className="font-mono" style={{ color: 'var(--text-primary)' }}>{ev.id}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ color: 'var(--text-muted)' }}>TIME</span>
            <span className="font-mono">{ev.created_at}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ color: 'var(--text-muted)' }}>BORDER TRACK</span>
            <span className="font-mono" style={{ color: '#10b981', fontWeight: 700 }}>
              {ev.border_track_id || `BT-${ev.track_id}`}
            </span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ color: 'var(--text-muted)' }}>CAMERA SEQUENCE</span>
            <span style={{ color: 'var(--accent-cyan)' }}>CAM-01 → CAM-02</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ color: 'var(--text-muted)' }}>DURATION</span>
            <span className="font-mono">{ev.duration_seconds || 19.2} sec</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ color: 'var(--text-muted)' }}>ENVIRONMENT</span>
            <span>NIGHT / DEGRADED</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ color: 'var(--text-muted)' }}>ZONE</span>
            <span style={{ color: '#ef4444', fontWeight: 700 }}>RESTRICTED</span>
          </div>
        </div>

        {onAcknowledge && (
          <button
            onClick={() => onAcknowledge(ev.id)}
            className="btn-command btn-primary"
            style={{ marginTop: '10px', width: '100%', justifyContent: 'center' }}
          >
            <CheckCircle2 size={13} />
            <span>Acknowledge Incident</span>
          </button>
        )}
      </div>

      {/* Right: "WHY THIS EVENT?" Explainability Reason Codes */}
      <div style={{ borderLeft: '1px solid var(--border-panel)', paddingLeft: '14px' }}>
        <div className="intel-card-header" style={{ marginBottom: '8px', color: 'var(--accent-cyan)' }}>
          WHY THIS EVENT?
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          {ev.reason_codes && ev.reason_codes.length > 0 ? (
            ev.reason_codes.map((code, idx) => (
              <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px' }}>
                <CheckCircle2 size={13} color="#10b981" style={{ flexShrink: 0 }} />
                <span style={{ color: '#e2e8f0' }}>{formatReason(code)}</span>
              </div>
            ))
          ) : (
            <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>No reason codes recorded.</div>
          )}
        </div>

        <div
          style={{
            marginTop: '10px',
            padding: '6px 8px',
            background: 'rgba(6, 182, 212, 0.08)',
            border: '1px solid rgba(6, 182, 212, 0.2)',
            borderRadius: '4px',
            fontSize: '10px',
            color: 'var(--accent-cyan)',
            lineHeight: 1.3,
          }}
        >
          <strong>Summary:</strong> {ev.explanation_summary}
        </div>
      </div>
    </div>
  );
};
