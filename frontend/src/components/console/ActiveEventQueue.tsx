import React from 'react';
import { ShieldAlert, AlertTriangle, Info, ChevronRight } from 'lucide-react';
import { EventRecord } from '../../types';

interface ActiveEventQueueProps {
  events: EventRecord[];
  selectedEventId?: string;
  onSelectEvent: (event: EventRecord) => void;
}

export const ActiveEventQueue: React.FC<ActiveEventQueueProps> = ({
  events,
  selectedEventId,
  onSelectEvent,
}) => {
  const displayEvents: EventRecord[] = events;

  return (
    <div className="events-panel">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
        <span className="intel-card-header">ACTIVE EVENTS</span>
        <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>{displayEvents.length} INCIDENTS</span>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {displayEvents.length === 0 ? (
          <div
            style={{
              padding: '24px 12px',
              textAlign: 'center',
              background: 'rgba(255, 255, 255, 0.02)',
              border: '1px dashed var(--border-panel)',
              borderRadius: '6px',
              color: 'var(--text-muted)',
              fontSize: '11px',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            <div style={{ color: '#10b981', fontWeight: 600 }}>● NO ACTIVE INCIDENTS</div>
            <div>Sector B-07 boundary secure</div>
          </div>
        ) : (
          displayEvents.map((ev) => {
          const isSelected = ev.id === selectedEventId;
          const isHigh = ev.priority === 'CRITICAL' || ev.priority === 'HIGH';
          const isMed = ev.priority === 'MEDIUM';

          const cardBorder = isSelected
            ? 'rgba(6, 182, 212, 0.6)'
            : isHigh
            ? 'rgba(239, 68, 68, 0.4)'
            : isMed
            ? 'rgba(245, 158, 11, 0.4)'
            : 'var(--border-panel)';

          const cardBg = isSelected
            ? 'rgba(6, 182, 212, 0.12)'
            : isHigh
            ? 'rgba(239, 68, 68, 0.06)'
            : isMed
            ? 'rgba(245, 158, 11, 0.06)'
            : 'var(--bg-card)';

          return (
            <div
              key={ev.id}
              onClick={() => onSelectEvent(ev)}
              style={{
                background: cardBg,
                border: `1px solid ${cardBorder}`,
                borderRadius: '6px',
                padding: '10px 12px',
                cursor: 'pointer',
                transition: 'all 0.15s ease',
                display: 'flex',
                flexDirection: 'column',
                gap: '6px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  {isHigh ? (
                    <ShieldAlert size={14} color="#ef4444" />
                  ) : isMed ? (
                    <AlertTriangle size={14} color="#f59e0b" />
                  ) : (
                    <Info size={14} color="#38bdf8" />
                  )}
                  <span
                    style={{
                      fontSize: '10px',
                      fontWeight: 700,
                      color: isHigh ? '#ef4444' : isMed ? '#f59e0b' : '#38bdf8',
                    }}
                  >
                    {ev.priority}
                  </span>
                </div>
                <span className="font-mono" style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
                  {ev.created_at}
                </span>
              </div>

              <div>
                <div style={{ fontSize: '12px', fontWeight: 700, color: '#fff' }}>
                  {ev.event_type}
                </div>
                <div style={{ fontSize: '10px', color: 'var(--text-secondary)' }}>
                  {ev.border_track_id || `ID #${ev.track_id}`} | {ev.camera_id}
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '2px' }}>
                <span className={`status-pill ${isHigh ? 'pill-red' : isMed ? 'pill-amber' : 'pill-cyan'}`} style={{ fontSize: '9px' }}>
                  {isHigh ? 'NEW' : 'REVIEW'}
                </span>
                <span style={{ fontSize: '10px', color: 'var(--accent-cyan)', display: 'flex', alignItems: 'center' }}>
                  View Evidence <ChevronRight size={12} />
                </span>
              </div>
            </div>
          );
        }))}
      </div>
    </div>
  );
};
