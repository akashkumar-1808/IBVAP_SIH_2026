import React from 'react';
import { Camera, Layers, AlertTriangle, CheckCircle2, ShieldAlert } from 'lucide-react';
import { CameraInfo, EventRecord } from '../../types';

interface SidebarNavProps {
  cameras: CameraInfo[];
  selectedCameraId: string;
  onSelectCamera: (cameraId: string) => void;
  events: EventRecord[];
}

export const SidebarNav: React.FC<SidebarNavProps> = ({
  cameras,
  selectedCameraId,
  onSelectCamera,
  events,
}) => {
  const highCount = events.filter((e) => e.priority === 'CRITICAL' || e.priority === 'HIGH').length;
  const medCount = events.filter((e) => e.priority === 'MEDIUM').length;
  const infoCount = events.filter((e) => e.priority === 'LOW' || e.priority === 'INFO').length;

  return (
    <aside className="left-panel">
      {/* Overview Navigation */}
      <div>
        <div className="intel-card-header" style={{ marginBottom: '8px' }}>OVERVIEW</div>
        <button
          className="btn-command btn-primary"
          style={{ width: '100%', justifyContent: 'flex-start', padding: '8px 10px' }}
        >
          <Camera size={15} />
          <span>Live Console</span>
        </button>
      </div>

      {/* Camera Network */}
      <div>
        <div className="intel-card-header" style={{ marginBottom: '8px' }}>CAMERA NETWORK</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          {cameras.map((cam) => {
            const isSelected = cam.camera_id === selectedCameraId;
            const isOnline = cam.status === 'ONLINE';
            const isDegraded = cam.status === 'DEGRADED';

            return (
              <div
                key={cam.camera_id}
                onClick={() => onSelectCamera(cam.camera_id)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '8px 10px',
                  borderRadius: '5px',
                  cursor: 'pointer',
                  background: isSelected ? 'rgba(6, 182, 212, 0.12)' : 'var(--bg-card)',
                  border: isSelected ? '1px solid rgba(6, 182, 212, 0.5)' : '1px solid var(--border-panel)',
                  transition: 'all 0.15s ease',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Camera size={14} color={isSelected ? 'var(--accent-cyan)' : 'var(--text-secondary)'} />
                  <div>
                    <div style={{ fontSize: '11px', fontWeight: 700, color: isSelected ? '#fff' : 'var(--text-primary)' }}>
                      {cam.camera_id}
                    </div>
                    <div style={{ fontSize: '9px', color: 'var(--text-muted)' }}>{cam.name}</div>
                  </div>
                </div>

                <div
                  style={{
                    width: '8px',
                    height: '8px',
                    borderRadius: '50%',
                    background: isOnline ? '#10b981' : isDegraded ? '#f59e0b' : '#ef4444',
                    boxShadow: isOnline ? '0 0 6px rgba(16,185,129,0.6)' : isDegraded ? '0 0 6px rgba(245,158,11,0.6)' : 'none',
                  }}
                />
              </div>
            );
          })}
        </div>
      </div>

      {/* Border Sectors */}
      <div>
        <div className="intel-card-header" style={{ marginBottom: '8px' }}>BORDER SECTOR</div>
        <div
          style={{
            padding: '8px 10px',
            background: 'var(--bg-card)',
            border: '1px solid var(--border-panel)',
            borderRadius: '5px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div>
            <div style={{ fontSize: '11px', fontWeight: 700, color: '#38bdf8' }}>SECTOR B-07</div>
            <div style={{ fontSize: '9px', color: 'var(--text-muted)' }}>Northern Border Sector</div>
          </div>
          <Layers size={14} color="#38bdf8" />
        </div>
      </div>

      {/* Threat Tiers Summary */}
      <div>
        <div className="intel-card-header" style={{ marginBottom: '8px' }}>EVENT SUMMARY</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '11px' }}>
            <span style={{ color: '#ef4444', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <ShieldAlert size={12} /> High Priority
            </span>
            <span className="font-mono" style={{ fontWeight: 700, color: '#ef4444' }}>
              {String(highCount).padStart(2, '0')}
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '11px' }}>
            <span style={{ color: '#f59e0b', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <AlertTriangle size={12} /> Medium Priority
            </span>
            <span className="font-mono" style={{ fontWeight: 700, color: '#f59e0b' }}>
              {String(medCount).padStart(2, '0')}
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '11px' }}>
            <span style={{ color: '#94a3b8', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <CheckCircle2 size={12} /> Info / Normal
            </span>
            <span className="font-mono" style={{ fontWeight: 700, color: '#94a3b8' }}>
              {String(infoCount).padStart(2, '0')}
            </span>
          </div>
        </div>
      </div>

      {/* Backend Intelligence Subsystems */}
      <div style={{ marginTop: 'auto' }}>
        <div className="intel-card-header" style={{ marginBottom: '8px' }}>SUBSYSTEM STATUS</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '5px', fontSize: '10px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ color: 'var(--text-secondary)' }}>Ingestion Worker</span>
            <span style={{ color: '#10b981', fontWeight: 600 }}>ONLINE</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ color: 'var(--text-secondary)' }}>AI Perception</span>
            <span style={{ color: '#10b981', fontWeight: 600 }}>ONLINE</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ color: 'var(--text-secondary)' }}>Spatial & Behavior</span>
            <span style={{ color: '#10b981', fontWeight: 600 }}>ONLINE</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ color: 'var(--text-secondary)' }}>Evidence Seal</span>
            <span style={{ color: '#10b981', fontWeight: 600 }}>ONLINE</span>
          </div>
        </div>
      </div>
    </aside>
  );
};
