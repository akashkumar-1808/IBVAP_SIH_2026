import React from 'react';
import { Clock } from 'lucide-react';
import { EventRecord } from '../../types';

interface EventTimelineProps {
  selectedEvent?: EventRecord | null;
}

export const EventTimeline: React.FC<EventTimelineProps> = ({ selectedEvent }) => {
  if (!selectedEvent) {
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
        <div style={{ fontWeight: 600, color: 'var(--text-secondary)' }}>NO TIMELINE ACTIVE</div>
        <div>Awaiting incident events</div>
      </div>
    );
  }

  // Derive timeline milestones from actual event reason codes & duration
  const baseTime = selectedEvent.created_at || '00:00:00';
  const milestones = [
    { time: baseTime, label: `Target Detected (ID:#${selectedEvent.track_id})`, status: 'done' },
    ...selectedEvent.reason_codes.map((rc, idx) => ({
      time: baseTime,
      label: rc.toLowerCase().replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()),
      status: idx === selectedEvent.reason_codes.length - 1 ? ('active' as const) : ('done' as const),
    })),
  ];

  return (
    <div className="forensic-panel">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
        <span className="intel-card-header">EVENT TIMELINE</span>
        <Clock size={13} color="var(--text-muted)" />
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', position: 'relative' }}>
        {/* Timeline connector line */}
        <div
          style={{
            position: 'absolute',
            left: '6px',
            top: '6px',
            bottom: '10px',
            width: '2px',
            background: 'rgba(255,255,255,0.1)',
            zIndex: 1,
          }}
        />

        {milestones.map((item, idx) => {
          const isActive = item.status === 'active';
          return (
            <div key={idx} style={{ display: 'flex', alignItems: 'flex-start', gap: '10px', zIndex: 2 }}>
              <div
                style={{
                  width: '14px',
                  height: '14px',
                  borderRadius: '50%',
                  background: isActive ? '#ef4444' : '#10b981',
                  border: '2px solid var(--bg-panel)',
                  flexShrink: 0,
                  marginTop: '2px',
                }}
              />
              <div>
                <div style={{ fontSize: '10px', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                  {item.time}
                </div>
                <div style={{ fontSize: '11px', fontWeight: isActive ? 700 : 500, color: isActive ? '#ef4444' : 'var(--text-primary)' }}>
                  {item.label}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
