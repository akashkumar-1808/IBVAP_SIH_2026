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
  // Default mock active events if queue is empty
  const displayEvents: EventRecord[] = events.length > 0 ? events : [
    {
      id: 'EVT-2025-0518-000104',
      camera_id: 'CAM-01',
      track_id: 104,
      border_track_id: 'BT-104',
      event_type: 'Border Crossing',
      priority: 'HIGH',
      risk_score: 87.6,
      status: 'ACTIVE',
      target_class: 'PERSON',
      created_at: '02:24:21 AM',
      updated_at: '02:24:21 AM',
      reason_codes: ['PERSISTENT_TRACK', 'BORDER_CROSSED', 'RESTRICTED_OCCUPANCY'],
      explanation_summary: 'Confirmed human crossing into restricted sector',
    },
    {
      id: 'EVT-2025-0518-000109',
      camera_id: 'CAM-03',
      track_id: 109,
      border_track_id: 'BT-109',
      event_type: 'Persistent Approach',
      priority: 'MEDIUM',
      risk_score: 64.0,
      status: 'ACTIVE',
      target_class: 'PERSON',
      created_at: '02:19:07 AM',
      updated_at: '02:19:07 AM',
      reason_codes: ['MOVEMENT_TOWARD_BUFFER'],
      explanation_summary: 'Target moving consistently toward buffer zone',
    },
    {
      id: 'EVT-2025-0518-000098',
      camera_id: 'CAM-03',
      track_id: 98,
      event_type: 'Animal Detected',
      priority: 'INFO',
      risk_score: 25.0,
      status: 'ACTIVE',
      target_class: 'ANIMAL',
      created_at: '02:18:45 AM',
      updated_at: '02:18:45 AM',
      reason_codes: ['WILDLIFE_CLASSIFIED'],
      explanation_summary: 'Wildlife activity near outer buffer boundary',
    },
  ];

  return (
    <div className="events-panel">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
        <span className="intel-card-header">ACTIVE EVENTS</span>
        <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>{displayEvents.length} INCIDENTS</span>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {displayEvents.map((ev) => {
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
        })}
      </div>
    </div>
  );
};
