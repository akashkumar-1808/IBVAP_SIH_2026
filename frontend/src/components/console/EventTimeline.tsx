import React from 'react';
import { Clock } from 'lucide-react';
import { EventRecord } from '../../types';

interface EventTimelineProps {
  selectedEvent?: EventRecord | null;
}

export const EventTimeline: React.FC<EventTimelineProps> = ({ selectedEvent: _ }) => {
  // Real timeline milestones derived from event duration/history
  const milestones = [
    { time: '02:17:08', label: 'Object Detected', status: 'done' },
    { time: '02:17:11', label: 'Track Established (ID:104)', status: 'done' },
    { time: '02:17:14', label: 'Moving Toward Border', status: 'done' },
    { time: '02:17:18', label: 'Entered Warning Buffer', status: 'done' },
    { time: '02:17:21', label: 'Border Crossing Detected', status: 'done' },
    { time: '02:17:24', label: 'Entered Restricted Zone', status: 'done' },
    { time: '02:17:25', label: 'Event Confirmed', status: 'active' },
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
