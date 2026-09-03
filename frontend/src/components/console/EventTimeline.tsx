import React from 'react';
import { Clock, ShieldAlert, AlertTriangle, Info } from 'lucide-react';
import { EventRecord } from '../../types';

interface EventTimelineProps {
  events?: EventRecord[];
  selectedEvent?: EventRecord | null;
  onSelectEvent?: (event: EventRecord) => void;
}

export const EventTimeline: React.FC<EventTimelineProps> = ({
  events = [],
  selectedEvent,
  onSelectEvent,
}) => {
  // Sort events chronologically (newest first or chronological)
  const displayEvents = events.length > 0 ? events : (selectedEvent ? [selectedEvent] : []);

  if (displayEvents.length === 0) {
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
          minHeight: '140px',
        }}
      >
        <Clock size={16} color="var(--text-muted)" />
        <div style={{ fontWeight: 600, color: 'var(--text-secondary)' }}>NO TIMELINE INCIDENTS</div>
        <div>Awaiting pipeline intrusion events</div>
      </div>
    );
  }

  return (
    <div className="forensic-panel" style={{ display: 'flex', flexDirection: 'column', gap: '8px', minHeight: '140px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span className="intel-card-header">EVENT TIMELINE ({displayEvents.length})</span>
        <Clock size={13} color="var(--text-muted)" />
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', overflowY: 'auto', maxHeight: '180px' }}>
        {displayEvents.map((ev) => {
          const isSelected = ev.id === selectedEvent?.id;
          const isHigh = ev.priority === 'HIGH' || ev.priority === 'CRITICAL';
          const isMed = ev.priority === 'MEDIUM';

          const timeDisplay = ev.created_at
            ? (ev.created_at.includes('T') ? ev.created_at.split('T')[1].slice(0, 8) : ev.created_at.slice(0, 8))
            : 'LIVE';

          return (
            <div
              key={ev.id}
              onClick={() => onSelectEvent && onSelectEvent(ev)}
              style={{
                background: isSelected ? 'rgba(6, 182, 212, 0.12)' : 'rgba(255, 255, 255, 0.02)',
                border: `1px solid ${isSelected ? 'rgba(6, 182, 212, 0.5)' : (isHigh ? 'rgba(239, 68, 68, 0.3)' : 'var(--border-panel)')}`,
                borderRadius: '4px',
                padding: '8px 10px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: '8px',
                transition: 'all 0.15s ease',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                {isHigh ? (
                  <ShieldAlert size={14} color="#ef4444" />
                ) : isMed ? (
                  <AlertTriangle size={14} color="#f59e0b" />
                ) : (
                  <Info size={14} color="#38bdf8" />
                )}
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span className="font-mono" style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
                      {timeDisplay}
                    </span>
                    <span style={{ fontSize: '11px', fontWeight: 700, color: '#f8fafc' }}>
                      {ev.event_type.replace(/_/g, ' ')}
                    </span>
                  </div>
                  <div style={{ fontSize: '9.5px', color: 'var(--text-secondary)' }}>
                    TRACK #{ev.track_id} • {ev.camera_id}
                  </div>
                </div>
              </div>

              <div style={{ textAlign: 'right', display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '2px' }}>
                <span
                  className={`status-pill ${isHigh ? 'pill-red' : isMed ? 'pill-amber' : 'pill-green'}`}
                  style={{ fontSize: '9px', padding: '1px 5px' }}
                >
                  {ev.priority}
                </span>
                <span className="font-mono" style={{ fontSize: '10px', fontWeight: 700, color: isHigh ? '#ef4444' : '#10b981' }}>
                  {ev.risk_score.toFixed(1)}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
