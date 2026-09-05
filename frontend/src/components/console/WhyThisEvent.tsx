import React from 'react';
import { CheckCircle2, ShieldCheck } from 'lucide-react';
import { EventRecord } from '../../types';

interface WhyThisEventProps {
  event?: EventRecord | null;
  onAcknowledge?: (eventId: string) => void;
  onInspectEvidence?: (event: EventRecord) => void;
}

export const WhyThisEvent: React.FC<WhyThisEventProps> = ({ event, onInspectEvidence }) => {
  if (!event) {
    return (
      <div className="ops-panel">
        <div style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em', borderBottom: '1px solid var(--color-border-subtle)', paddingBottom: '6px' }}>
          WHY THIS EVENT?
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', flex: 1, gap: '8px', color: 'var(--color-text-muted)' }}>
          <ShieldCheck size={24} color="var(--color-green)" />
          <span style={{ fontSize: '11px' }}>Select an event from the timeline or wait for an incident.</span>
        </div>
      </div>
    );
  }

  // Only show reason codes actually emitted by FusionEngine
  const rawCodes = event.reason_codes || [];

  return (
    <div className="ops-panel">
      {/* Title */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid var(--color-border-subtle)', paddingBottom: '6px' }}>
        <span style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
          WHY THIS EVENT?
        </span>
        {onInspectEvidence && (
          <button
            onClick={() => onInspectEvidence(event)}
            style={{
              background: 'none',
              border: 'none',
              color: '#38BDF8',
              fontSize: '10px',
              fontWeight: 700,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '3px',
            }}
            title="Inspect full forensic evidence dossier and video footages"
          >
            Inspect Evidence →
          </button>
        )}
      </div>

      {/* 2-Column Checklist of FusionEngine Reason Codes */}
      <div className="reasons-checklist">
        {rawCodes.length === 0 ? (
          <div style={{ color: 'var(--color-text-muted)', fontSize: '10.5px', gridColumn: 'span 2' }}>
            No specific reason codes attached to this event.
          </div>
        ) : (
          rawCodes.map((rc, idx) => {
            const displayLabel = rc.replace(/_/g, ' ').toUpperCase();
            return (
              <div key={idx} className="reason-item">
                <CheckCircle2 size={13} color="var(--color-green)" style={{ flexShrink: 0 }} />
                <span>{displayLabel}</span>
              </div>
            );
          })
        )}
      </div>

      {/* Explanation Summary from Backend FusionEngine */}
      <div style={{ marginTop: 'auto', paddingTop: '6px', borderTop: '1px solid var(--color-border-subtle)' }}>
        <div style={{ fontSize: '9px', fontWeight: 700, color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '3px' }}>
          EXPLANATION SUMMARY
        </div>
        <p style={{ fontSize: '10.5px', color: 'var(--color-text-secondary)', lineHeight: 1.45 }}>
          {event.explanation_summary || 'Autonomous FusionEngine evaluation in progress.'}
        </p>
      </div>
    </div>
  );
};
