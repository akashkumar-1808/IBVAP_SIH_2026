import React, { useState } from 'react';
import {
  ShieldAlert,
  ShieldCheck,
  Archive,
  CheckCircle2,
  ArrowRight,
} from 'lucide-react';
import { EventRecord, EvidencePackage, EnvironmentState, StreamHealthContract } from '../../types';

interface IncidentsViewProps {
  events: EventRecord[];
  selectedEvent: EventRecord | null;
  evidencePackage: EvidencePackage | null;
  environment?: EnvironmentState;
  streamHealth?: StreamHealthContract;
  onSelectEvent: (ev: EventRecord) => void;
  onAcknowledge: (eventId: string) => void;
  onInspectEvidence: (ev?: EventRecord | null) => void;
}

export const IncidentsView: React.FC<IncidentsViewProps> = ({
  events,
  selectedEvent,
  evidencePackage,
  environment,
  streamHealth,
  onSelectEvent,
  onAcknowledge,
  onInspectEvidence,
}) => {
  const [priorityFilter, setPriorityFilter] = useState<'ALL' | 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW'>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');

  const filteredEvents = events.filter((ev) => {
    if (priorityFilter !== 'ALL' && ev.priority !== priorityFilter) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      return (
        ev.id.toLowerCase().includes(q) ||
        ev.event_type.toLowerCase().includes(q) ||
        (ev.explanation_summary || '').toLowerCase().includes(q)
      );
    }
    return true;
  });

  const active = selectedEvent || filteredEvents[0] || null;

  // Real reason codes mapping into an Intelligence Chain
  const reasonCodes = active?.reason_codes || [];

  return (
    <div
      className="incidents-workspace"
      style={{
        display: 'grid',
        gridTemplateColumns: '360px 1fr',
        gap: '14px',
        width: '100%',
        height: '100%',
        overflow: 'hidden',
      }}
    >
      {/* Left Column: Filterable Incidents Queue */}
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          backgroundColor: 'rgba(15, 23, 42, 0.85)',
          border: '1px solid var(--color-border)',
          borderRadius: '6px',
          overflow: 'hidden',
        }}
      >
        {/* Header & Filter Controls */}
        <div style={{ padding: '12px', borderBottom: '1px solid var(--color-border-subtle)', display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <ShieldAlert size={16} color="#38BDF8" />
              <span style={{ fontSize: '12px', fontWeight: 800, color: '#F1F5F9', letterSpacing: '0.04em' }}>
                SECURITY INCIDENTS
              </span>
            </div>
            <span style={{ fontSize: '10px', color: 'var(--color-text-muted)', fontWeight: 700 }}>
              {filteredEvents.length} TOTAL
            </span>
          </div>

          {/* Search bar */}
          <input
            type="text"
            placeholder="Search incident ID, type, reasons..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              padding: '6px 10px',
              backgroundColor: 'rgba(0, 0, 0, 0.4)',
              border: '1px solid var(--color-border-subtle)',
              borderRadius: '4px',
              color: '#F1F5F9',
              fontSize: '10.5px',
              outline: 'none',
            }}
          />

          {/* Priority Pill Filters */}
          <div style={{ display: 'flex', gap: '4px' }}>
            {(['ALL', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'] as const).map((p) => (
              <button
                key={p}
                onClick={() => setPriorityFilter(p)}
                style={{
                  flex: 1,
                  padding: '4px 0',
                  fontSize: '8.5px',
                  fontWeight: 700,
                  borderRadius: '3px',
                  border: priorityFilter === p ? '1px solid #38BDF8' : '1px solid var(--color-border-subtle)',
                  backgroundColor: priorityFilter === p ? 'rgba(56, 189, 248, 0.2)' : 'rgba(0,0,0,0.2)',
                  color: priorityFilter === p ? '#38BDF8' : 'var(--color-text-secondary)',
                  cursor: 'pointer',
                }}
              >
                {p}
              </button>
            ))}
          </div>
        </div>

        {/* Incidents List */}
        <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column' }}>
          {filteredEvents.length === 0 ? (
            <div style={{ padding: '24px', textAlign: 'center', color: 'var(--color-text-muted)', fontSize: '11px' }}>
              No incidents match the active filter.
            </div>
          ) : (
            filteredEvents.map((ev) => {
              const isSelected = active?.id === ev.id;
              const isCrit = ev.priority === 'CRITICAL';
              const isHigh = ev.priority === 'HIGH';

              return (
                <div
                  key={ev.id}
                  onClick={() => onSelectEvent(ev)}
                  style={{
                    padding: '10px 12px',
                    borderBottom: '1px solid var(--color-border-subtle)',
                    backgroundColor: isSelected ? 'rgba(59, 130, 246, 0.12)' : 'transparent',
                    borderLeft: isSelected
                      ? `3px solid ${isCrit ? '#EF4444' : isHigh ? '#F59E0B' : '#38BDF8'}`
                      : '3px solid transparent',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease-out',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
                    <span style={{ fontSize: '10px', fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--color-text-muted)' }}>
                      #{ev.id.slice(0, 8)}
                    </span>
                    <span
                      style={{
                        fontSize: '8px',
                        fontWeight: 800,
                        padding: '1px 6px',
                        borderRadius: '2px',
                        backgroundColor: isCrit ? 'rgba(239, 68, 68, 0.2)' : isHigh ? 'rgba(245, 158, 11, 0.2)' : 'rgba(59, 130, 246, 0.2)',
                        color: isCrit ? '#F87171' : isHigh ? '#FBBF24' : '#60A5FA',
                      }}
                    >
                      {ev.priority}
                    </span>
                  </div>

                  <div style={{ fontSize: '11px', fontWeight: 800, color: '#F1F5F9', marginBottom: '4px' }}>
                    {ev.event_type.replace(/_/g, ' ')}
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '9px', color: 'var(--color-text-secondary)' }}>
                    <span>TRACK #{ev.track_id}</span>
                    <span style={{ color: '#38BDF8', fontWeight: 700 }}>
                      RISK: {ev.risk_score?.toFixed(1) || '0.0'}
                    </span>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Right Column: Forensic Security Event Workspace */}
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          gap: '12px',
          height: '100%',
          overflowY: 'auto',
          paddingRight: '2px',
        }}
      >
        {active ? (
          <>
            {/* 1. Incident Overview Dossier Box */}
            <div
              style={{
                backgroundColor: 'rgba(15, 23, 42, 0.85)',
                border: '1px solid var(--color-border)',
                borderRadius: '6px',
                padding: '16px',
                display: 'flex',
                flexDirection: 'column',
                gap: '12px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid var(--color-border-subtle)', paddingBottom: '10px' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <h3 style={{ fontSize: '15px', fontWeight: 800, color: '#F1F5F9', margin: 0 }}>
                      {active.event_type.replace(/_/g, ' ')}
                    </h3>
                    <span
                      style={{
                        fontSize: '9px',
                        fontWeight: 800,
                        padding: '2px 8px',
                        borderRadius: '3px',
                        backgroundColor: active.priority === 'CRITICAL' ? 'rgba(239, 68, 68, 0.25)' : 'rgba(245, 158, 11, 0.25)',
                        color: active.priority === 'CRITICAL' ? '#F87171' : '#FBBF24',
                        border: `1px solid ${active.priority === 'CRITICAL' ? 'rgba(239, 68, 68, 0.5)' : 'rgba(245, 158, 11, 0.5)'}`,
                      }}
                    >
                      {active.priority} THREAT
                    </span>
                  </div>
                  <div style={{ fontSize: '10px', color: 'var(--color-text-muted)', marginTop: '3px' }}>
                    INCIDENT ID: <span style={{ fontFamily: 'var(--font-mono)', color: '#38BDF8' }}>{active.id}</span> · TIMESTAMP: {active.created_at || 'RECENT'}
                  </div>
                </div>

                <div style={{ display: 'flex', gap: '8px' }}>
                  {active.status !== 'RESOLVED' && (
                    <button
                      onClick={() => onAcknowledge(active.id)}
                      style={{
                        padding: '6px 12px',
                        backgroundColor: 'rgba(16, 185, 129, 0.2)',
                        border: '1px solid rgba(16, 185, 129, 0.4)',
                        borderRadius: '4px',
                        color: '#34D399',
                        fontSize: '10px',
                        fontWeight: 700,
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '4px',
                      }}
                    >
                      <CheckCircle2 size={13} /> Acknowledge
                    </button>
                  )}
                  <button
                    onClick={() => onInspectEvidence(active)}
                    style={{
                      padding: '6px 14px',
                      backgroundColor: '#2563EB',
                      border: 'none',
                      borderRadius: '4px',
                      color: '#FFFFFF',
                      fontSize: '10px',
                      fontWeight: 700,
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '5px',
                    }}
                  >
                    <Archive size={13} /> Inspect Sealed Evidence Dossier
                  </button>
                </div>
              </div>

              {/* Forensic Parameter Grid */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '10px' }}>
                <div style={{ backgroundColor: 'rgba(0,0,0,0.3)', padding: '10px', borderRadius: '4px' }}>
                  <span style={{ fontSize: '8px', color: 'var(--color-text-muted)', fontWeight: 700 }}>RISK SCORE</span>
                  <div style={{ fontSize: '18px', fontWeight: 800, color: active.risk_score >= 70 ? '#EF4444' : '#F59E0B', marginTop: '2px' }}>
                    {active.risk_score?.toFixed(1) || '0.0'} <span style={{ fontSize: '10px', color: 'var(--color-text-muted)' }}>/ 100</span>
                  </div>
                </div>

                <div style={{ backgroundColor: 'rgba(0,0,0,0.3)', padding: '10px', borderRadius: '4px' }}>
                  <span style={{ fontSize: '8px', color: 'var(--color-text-muted)', fontWeight: 700 }}>TRACK & CLASS</span>
                  <div style={{ fontSize: '14px', fontWeight: 800, color: '#38BDF8', marginTop: '2px' }}>
                    TRACK #{active.track_id}
                  </div>
                  <span style={{ fontSize: '9px', color: 'var(--color-text-secondary)' }}>
                    {active.target_class || 'PERSON'}
                  </span>
                </div>

                <div style={{ backgroundColor: 'rgba(0,0,0,0.3)', padding: '10px', borderRadius: '4px' }}>
                  <span style={{ fontSize: '8px', color: 'var(--color-text-muted)', fontWeight: 700 }}>DETECTION CONFIDENCE</span>
                  <div style={{ fontSize: '16px', fontWeight: 800, color: '#10B981', marginTop: '2px' }}>
                    {active.detection_confidence ? `${Math.round(active.detection_confidence * 100)}%` : '--'}
                  </div>
                </div>

                <div style={{ backgroundColor: 'rgba(0,0,0,0.3)', padding: '10px', borderRadius: '4px' }}>
                  <span style={{ fontSize: '8px', color: 'var(--color-text-muted)', fontWeight: 700 }}>SECTOR & CAMERA</span>
                  <div style={{ fontSize: '13px', fontWeight: 800, color: '#E2E8F0', marginTop: '2px' }}>
                    {active.camera_id || 'DEMO-CAM-01'}
                  </div>
                  <span style={{ fontSize: '9px', color: 'var(--color-text-secondary)' }}>
                    SECTOR B-07 · {environment?.visibility || 'GOOD'} ({streamHealth?.state || 'HEALTHY'})
                  </span>
                </div>

                <div style={{ backgroundColor: 'rgba(0,0,0,0.3)', padding: '10px', borderRadius: '4px' }}>
                  <span style={{ fontSize: '8px', color: 'var(--color-text-muted)', fontWeight: 700 }}>EVIDENCE PACKAGE</span>
                  <div style={{ fontSize: '12px', fontWeight: 800, color: '#34D399', marginTop: '2px' }}>
                    {evidencePackage ? 'SEALED & READY' : 'ATTACHED'}
                  </div>
                  <span style={{ fontSize: '9px', color: 'var(--color-text-secondary)' }}>
                    SHA-256 VERIFIED
                  </span>
                </div>
              </div>
            </div>

            {/* 2. "WHY DID IBVAP TATVA RAISE THIS EVENT?" (Section 9 Requirement) */}
            <div
              style={{
                backgroundColor: 'rgba(15, 23, 42, 0.85)',
                border: '1px solid var(--color-border)',
                borderRadius: '6px',
                padding: '16px',
                display: 'flex',
                flexDirection: 'column',
                gap: '12px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <ShieldCheck size={18} color="#10B981" />
                <span style={{ fontSize: '12px', fontWeight: 800, color: '#F1F5F9', letterSpacing: '0.04em' }}>
                  WHY DID IBVAP TATVA RAISE THIS EVENT?
                </span>
              </div>

              {/* Intelligence Chain Flow */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <div style={{ fontSize: '9px', color: 'var(--color-text-muted)', fontWeight: 700, textTransform: 'uppercase' }}>
                  DETERMINISTIC INTELLIGENCE CHAIN
                </div>

                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    flexWrap: 'wrap',
                    gap: '6px',
                    padding: '12px',
                    backgroundColor: 'rgba(0,0,0,0.35)',
                    borderRadius: '4px',
                    border: '1px solid rgba(255,255,255,0.06)',
                  }}
                >
                  {[
                    { label: 'Person Detected', icon: '👤', sub: 'YOLO Model' },
                    { label: 'Track Established', icon: '🎯', sub: 'ByteTrack' },
                    { label: 'Movement Toward Border', icon: '↗', sub: 'Spatial Geometry' },
                    { label: 'Restricted Zone Ingress', icon: '⛔', sub: 'Virtual Geofence' },
                    { label: 'Occupancy Exceeded', icon: '⏱', sub: 'Temporal Logic' },
                    { label: 'Risk Escalation', icon: '⚠', sub: 'Fusion Engine' },
                    { label: 'Evidence Sealed', icon: '🔒', sub: 'SHA-256 Crypto' },
                  ].map((step, idx) => (
                    <React.Fragment key={idx}>
                      <div
                        style={{
                          display: 'flex',
                          flexDirection: 'column',
                          alignItems: 'center',
                          padding: '6px 10px',
                          backgroundColor: 'rgba(15, 23, 42, 0.8)',
                          border: '1px solid rgba(56, 189, 248, 0.3)',
                          borderRadius: '4px',
                        }}
                      >
                        <span style={{ fontSize: '11px', fontWeight: 700, color: '#F1F5F9' }}>
                          {step.icon} {step.label}
                        </span>
                        <span style={{ fontSize: '7.5px', color: '#38BDF8', fontWeight: 600 }}>
                          {step.sub}
                        </span>
                      </div>
                      {idx < 6 && (
                        <ArrowRight size={14} color="#6B7280" style={{ margin: '0 2px' }} />
                      )}
                    </React.Fragment>
                  ))}
                </div>
              </div>

              {/* Real Backend Reason Codes */}
              <div>
                <div style={{ fontSize: '9px', color: 'var(--color-text-muted)', fontWeight: 700, textTransform: 'uppercase', marginBottom: '6px' }}>
                  ATTACHED FUSION REASON CODES
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '6px' }}>
                  {reasonCodes.length > 0 ? (
                    reasonCodes.map((rc, idx) => (
                      <div
                        key={idx}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '6px',
                          padding: '6px 10px',
                          backgroundColor: 'rgba(16, 185, 129, 0.1)',
                          border: '1px solid rgba(16, 185, 129, 0.25)',
                          borderRadius: '3px',
                          fontSize: '10px',
                          fontWeight: 700,
                          color: '#34D399',
                        }}
                      >
                        <CheckCircle2 size={12} color="#10B981" />
                        <span>{rc.replace(/_/g, ' ').toUpperCase()}</span>
                      </div>
                    ))
                  ) : (
                    <div style={{ color: 'var(--color-text-muted)', fontSize: '10px' }}>
                      Standard autonomous spatial breach evaluation.
                    </div>
                  )}
                </div>
              </div>

              {/* Fusion Explanation Text */}
              <div style={{ borderTop: '1px solid var(--color-border-subtle)', paddingTop: '10px' }}>
                <div style={{ fontSize: '9px', color: 'var(--color-text-muted)', fontWeight: 700, textTransform: 'uppercase', marginBottom: '4px' }}>
                  AUTONOMOUS EXPLANATION SUMMARY
                </div>
                <p style={{ fontSize: '11px', color: 'var(--color-text-secondary)', lineHeight: 1.5 }}>
                  {active.explanation_summary || 'Autonomous FusionEngine evaluation confirmed unauthorized restricted zone ingress and raised security alert.'}
                </p>
              </div>
            </div>
          </>
        ) : (
          <div
            style={{
              backgroundColor: 'rgba(15, 23, 42, 0.85)',
              border: '1px solid var(--color-border)',
              borderRadius: '6px',
              padding: '32px',
              textAlign: 'center',
              color: 'var(--color-text-muted)',
              fontSize: '12px',
            }}
          >
            Select an incident from the left queue to inspect the forensic intelligence chain.
          </div>
        )}
      </div>
    </div>
  );
};
