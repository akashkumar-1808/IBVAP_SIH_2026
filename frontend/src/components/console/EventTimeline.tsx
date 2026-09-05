import React, { useState } from 'react';
import { ChevronDown, ListFilter, LayoutGrid, Search } from 'lucide-react';
import { EventRecord } from '../../types';

interface EventTimelineProps {
  events: EventRecord[];
  selectedEvent?: EventRecord | null;
  onSelectEvent: (event: EventRecord) => void;
  onInspectEvidence?: (event: EventRecord) => void;
}

export const EventTimeline: React.FC<EventTimelineProps> = ({
  events,
  selectedEvent,
  onSelectEvent,
  onInspectEvidence,
}) => {
  const [priorityFilter, setPriorityFilter] = useState<string>('ALL');

  const filteredEvents = events.filter((ev) => {
    if (priorityFilter === 'ALL') return true;
    return ev.priority === priorityFilter;
  });

  const getPriorityBadgeClass = (priority: string) => {
    switch (priority) {
      case 'CRITICAL':
      case 'HIGH':
        return { color: 'var(--color-red)', bg: 'var(--color-red-bg)' };
      case 'MEDIUM':
        return { color: 'var(--color-amber)', bg: 'var(--color-amber-bg)' };
      default:
        return { color: 'var(--color-blue)', bg: 'var(--color-blue-bg)' };
    }
  };

  return (
    <div className="ops-panel">
      {/* Header with Title and Filter controls */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid var(--color-border-subtle)', paddingBottom: '6px' }}>
        <span style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
          EVENT TIMELINE
        </span>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              fontSize: '10px',
              color: 'var(--color-text-secondary)',
              cursor: 'pointer',
              padding: '2px 6px',
              borderRadius: '3px',
              border: '1px solid var(--color-border-subtle)',
            }}
            onClick={() => setPriorityFilter((prev) => (prev === 'ALL' ? 'HIGH' : prev === 'HIGH' ? 'MEDIUM' : 'ALL'))}
          >
            <span>{priorityFilter === 'ALL' ? 'All Priorities' : `${priorityFilter} Only`}</span>
            <ChevronDown size={11} />
          </div>

          <ListFilter size={13} color="var(--color-text-secondary)" style={{ cursor: 'pointer' }} />
          <LayoutGrid size={13} color="var(--color-text-secondary)" style={{ cursor: 'pointer' }} />
        </div>
      </div>

      {/* Table of Chronological Real Events */}
      <div style={{ overflowY: 'auto', flex: 1 }}>
        {filteredEvents.length === 0 ? (
          <div style={{ padding: '20px 0', textAlign: 'center', color: 'var(--color-text-muted)', fontSize: '11px' }}>
            No events recorded yet. Pipeline monitoring active.
          </div>
        ) : (
          <table className="timeline-table">
            <thead>
              <tr>
                <th>TIME (UTC)</th>
                <th>EVENT TYPE</th>
                <th>CAMERA</th>
                <th>TRACK ID</th>
                <th>PRIORITY</th>
                <th>RISK SCORE</th>
                <th>STATUS</th>
                <th style={{ textAlign: 'center' }}>ACTION</th>
              </tr>
            </thead>
            <tbody>
              {filteredEvents.map((ev) => {
                const isSelected = selectedEvent?.id === ev.id;
                const timeOnly = ev.created_at
                  ? (ev.created_at.includes('T') ? ev.created_at.split('T')[1].substring(0, 8) : ev.created_at.substring(0, 8))
                  : '--';
                const pStyle = getPriorityBadgeClass(ev.priority);

                return (
                  <tr
                    key={ev.id}
                    className={isSelected ? 'selected' : ''}
                    onClick={() => onSelectEvent(ev)}
                    onDoubleClick={() => onInspectEvidence?.(ev)}
                    style={{ cursor: 'pointer' }}
                  >
                    <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{timeOnly}</td>
                    <td style={{ fontWeight: 600, color: 'var(--color-text-primary)' }}>
                      {ev.event_type.replace(/_/g, ' ')}
                    </td>
                    <td style={{ fontFamily: 'var(--font-mono)' }}>{ev.camera_id}</td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{ev.track_id}</td>
                    <td>
                      <span
                        style={{
                          fontSize: '8.5px',
                          fontWeight: 800,
                          color: pStyle.color,
                          backgroundColor: pStyle.bg,
                          padding: '1px 5px',
                          borderRadius: '2px',
                        }}
                      >
                        {ev.priority}
                      </span>
                    </td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: pStyle.color }}>
                      {typeof ev.risk_score === 'number' ? ev.risk_score.toFixed(1) : '0.0'}
                    </td>
                    <td>
                      <span
                        style={{
                          fontSize: '9px',
                          fontWeight: 700,
                          color: ev.status === 'RESOLVED' ? 'var(--color-text-muted)' : 'var(--color-red)',
                        }}
                      >
                        {ev.status || 'ACTIVE'}
                      </span>
                    </td>
                    <td style={{ textAlign: 'center' }}>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectEvent(ev);
                          onInspectEvidence?.(ev);
                        }}
                        style={{
                          backgroundColor: 'rgba(56, 189, 248, 0.12)',
                          border: '1px solid rgba(56, 189, 248, 0.4)',
                          color: '#38BDF8',
                          padding: '3px 8px',
                          borderRadius: '3px',
                          fontSize: '9.5px',
                          fontWeight: 700,
                          cursor: 'pointer',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '4px',
                          transition: 'all 0.15s ease',
                        }}
                        title="Inspect forensic evidence and timeline"
                      >
                        <Search size={10} />
                        Inspect
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};
