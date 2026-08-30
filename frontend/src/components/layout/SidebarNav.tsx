import React from 'react';
import { Camera, AlertTriangle, CheckCircle2, ShieldAlert, Plus, X, Radio } from 'lucide-react';
import { CameraInfo, EventRecord } from '../../types';

interface SidebarNavProps {
  cameras: CameraInfo[];
  selectedCameraId: string;
  onSelectCamera: (cameraId: string) => void;
  onOpenAddCamera: () => void;
  onDisconnectCamera?: (cameraId: string) => void;
  events: EventRecord[];
}

export const SidebarNav: React.FC<SidebarNavProps> = ({
  cameras,
  selectedCameraId,
  onSelectCamera,
  onOpenAddCamera,
  onDisconnectCamera,
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

      {/* Camera Network & Add RTSP Stream */}
      <div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
          <span className="intel-card-header">CAMERA NETWORK</span>
          <button
            onClick={onOpenAddCamera}
            className="btn-command"
            style={{
              padding: '2px 6px',
              fontSize: '10px',
              color: 'var(--accent-cyan)',
              border: '1px solid rgba(6, 182, 212, 0.4)',
              background: 'rgba(6, 182, 212, 0.08)',
              gap: '4px',
            }}
          >
            <Plus size={11} />
            <span>Add RTSP</span>
          </button>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
          {cameras.length === 0 ? (
            <div
              onClick={onOpenAddCamera}
              style={{
                padding: '16px 10px',
                textAlign: 'center',
                background: 'rgba(255, 255, 255, 0.02)',
                border: '1px dashed var(--border-panel)',
                borderRadius: '6px',
                color: 'var(--text-muted)',
                fontSize: '11px',
                cursor: 'pointer',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: '6px',
              }}
            >
              <Radio size={16} color="var(--accent-cyan)" />
              <div style={{ color: 'var(--text-primary)', fontWeight: 600 }}>No Cameras Connected</div>
              <div style={{ fontSize: '10px', color: 'var(--accent-cyan)' }}>+ Connect Live RTSP URL</div>
            </div>
          ) : (
            cameras.map((cam) => {
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

                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <div
                      style={{
                        width: '8px',
                        height: '8px',
                        borderRadius: '50%',
                        background: isOnline ? '#10b981' : isDegraded ? '#f59e0b' : '#ef4444',
                        boxShadow: isOnline ? '0 0 6px rgba(16,185,129,0.6)' : isDegraded ? '0 0 6px rgba(245,158,11,0.6)' : 'none',
                      }}
                    />
                    {onDisconnectCamera && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onDisconnectCamera(cam.camera_id);
                        }}
                        title="Disconnect camera"
                        style={{
                          background: 'transparent',
                          border: 'none',
                          color: 'var(--text-muted)',
                          padding: '2px',
                          cursor: 'pointer',
                        }}
                      >
                        <X size={12} />
                      </button>
                    )}
                  </div>
                </div>
              );
            })
          )}
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
            <div style={{ fontSize: '11px', fontWeight: 700, color: '#fff' }}>SECTOR B-07</div>
            <div style={{ fontSize: '9px', color: 'var(--text-muted)' }}>Northern Border Sector</div>
          </div>
          <span className="status-pill pill-cyan" style={{ fontSize: '9px' }}>
            ACTIVE
          </span>
        </div>
      </div>

      {/* Threat Summary Counters */}
      <div>
        <div className="intel-card-header" style={{ marginBottom: '8px' }}>THREAT SUMMARY</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '6px 10px',
              background: 'rgba(239, 68, 68, 0.08)',
              border: '1px solid rgba(239, 68, 68, 0.25)',
              borderRadius: '4px',
              fontSize: '11px',
            }}
          >
            <span style={{ color: '#ef4444', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '6px' }}>
              <ShieldAlert size={13} />
              CRITICAL / HIGH
            </span>
            <span className="font-mono" style={{ fontWeight: 800, color: '#ef4444' }}>
              {highCount}
            </span>
          </div>

          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '6px 10px',
              background: 'rgba(245, 158, 11, 0.08)',
              border: '1px solid rgba(245, 158, 11, 0.25)',
              borderRadius: '4px',
              fontSize: '11px',
            }}
          >
            <span style={{ color: '#f59e0b', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '6px' }}>
              <AlertTriangle size={13} />
              MEDIUM
            </span>
            <span className="font-mono" style={{ fontWeight: 800, color: '#f59e0b' }}>
              {medCount}
            </span>
          </div>

          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '6px 10px',
              background: 'rgba(6, 182, 212, 0.08)',
              border: '1px solid rgba(6, 182, 212, 0.25)',
              borderRadius: '4px',
              fontSize: '11px',
            }}
          >
            <span style={{ color: 'var(--accent-cyan)', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '6px' }}>
              <CheckCircle2 size={13} />
              LOW / INFO
            </span>
            <span className="font-mono" style={{ fontWeight: 800, color: 'var(--accent-cyan)' }}>
              {infoCount}
            </span>
          </div>
        </div>
      </div>

      {/* Subsystem Health Monitoring */}
      <div style={{ marginTop: 'auto' }}>
        <div className="intel-card-header" style={{ marginBottom: '8px' }}>ARCHITECTURE ENGINES</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '10px' }}>
          {[
            { name: 'Video Ingestion', status: cameras.some((c) => c.status === 'ONLINE') ? 'ONLINE' : 'STANDBY' },
            { name: 'YOLO Perception', status: 'ACTIVE' },
            { name: 'ByteTrack', status: 'ACTIVE' },
            { name: 'Spatial World Border', status: 'CALIBRATED' },
            { name: 'Evidence Packager', status: 'STANDBY' },
          ].map((item) => (
            <div key={item.name} style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-secondary)' }}>
              <span>{item.name}</span>
              <span style={{ color: item.status === 'ONLINE' || item.status === 'ACTIVE' || item.status === 'CALIBRATED' ? '#10b981' : 'var(--text-muted)' }}>
                {item.status}
              </span>
            </div>
          ))}
        </div>
      </div>
    </aside>
  );
};
