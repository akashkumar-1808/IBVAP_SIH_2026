import React from 'react';
import {
  LayoutDashboard,
  Bell,
  Archive,
  BarChart3,
  Settings,
  Plus,
  ShieldAlert,
  AlertTriangle,
  CheckCircle2,
  Video,
} from 'lucide-react';
import { CameraInfo, EventRecord } from '../../types';

interface SidebarNavProps {
  cameras: CameraInfo[];
  selectedCameraId: string;
  onSelectCamera: (id: string) => void;
  onOpenAddCamera: () => void;
  onDisconnectCamera: (id: string) => void;
  events: EventRecord[];
}

export const SidebarNav: React.FC<SidebarNavProps> = ({
  cameras,
  selectedCameraId,
  onSelectCamera,
  onOpenAddCamera,
  events,
}) => {
  // Compute real threat summary from actual events in memory/repository
  const criticalOrHigh = events.filter((e) => e.priority === 'CRITICAL' || e.priority === 'HIGH').length;
  const medium = events.filter((e) => e.priority === 'MEDIUM').length;
  const lowOrInfo = events.filter((e) => (e.priority as string) === 'LOW' || (e.priority as string) === 'NORMAL' || (e.priority as string) === 'INFO').length;

  const activeCam = cameras.find((c) => c.camera_id === selectedCameraId) || cameras[0] || {
    camera_id: 'DEMO-CAM-01',
    name: 'SIH Recorded Breach Demo',
    sector_id: 'B-07',
    sector_name: 'Northern Border Sector',
    status: 'ONLINE',
  };

  return (
    <aside className="operator-sidebar">
      {/* 1. Main Functional Navigation */}
      <div className="sidebar-nav-list">
        <div className="sidebar-nav-item active">
          <LayoutDashboard size={15} color="#3B82F6" />
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <span style={{ fontSize: '11px', fontWeight: 700 }}>OVERVIEW</span>
            <span style={{ fontSize: '9px', color: 'var(--color-text-muted)' }}>Live Operations</span>
          </div>
        </div>

        <div className="sidebar-nav-item">
          <Bell size={15} color="var(--color-text-secondary)" />
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <span style={{ fontSize: '11px', fontWeight: 600 }}>EVENTS</span>
            <span style={{ fontSize: '9px', color: 'var(--color-text-muted)' }}>Timeline & Alerts</span>
          </div>
        </div>

        <div className="sidebar-nav-item">
          <Archive size={15} color="var(--color-text-secondary)" />
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <span style={{ fontSize: '11px', fontWeight: 600 }}>EVIDENCE</span>
            <span style={{ fontSize: '9px', color: 'var(--color-text-muted)' }}>Evidence Packages</span>
          </div>
        </div>

        <div className="sidebar-nav-item">
          <BarChart3 size={15} color="var(--color-text-secondary)" />
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <span style={{ fontSize: '11px', fontWeight: 600 }}>ANALYTICS</span>
            <span style={{ fontSize: '9px', color: 'var(--color-text-muted)' }}>Reports & Insights</span>
          </div>
        </div>

        <div className="sidebar-nav-item">
          <Settings size={15} color="var(--color-text-secondary)" />
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <span style={{ fontSize: '11px', fontWeight: 600 }}>CONFIGURATION</span>
            <span style={{ fontSize: '9px', color: 'var(--color-text-muted)' }}>System Settings</span>
          </div>
        </div>
      </div>

      <div style={{ width: '100%', height: '1px', backgroundColor: 'var(--color-border-subtle)' }} />

      {/* 2. Camera Network */}
      <div>
        <div className="sidebar-section-title">
          <span>CAMERA NETWORK</span>
          <button
            onClick={onOpenAddCamera}
            title="Connect RTSP Stream"
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--color-text-secondary)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
            }}
          >
            <Plus size={14} />
          </button>
        </div>

        {cameras.length === 0 ? (
          <div
            className="sidebar-card"
            onClick={onOpenAddCamera}
            style={{ cursor: 'pointer', textAlign: 'center', padding: '12px 8px' }}
          >
            <span style={{ fontSize: '11px', fontWeight: 600, color: 'var(--color-text-secondary)' }}>
              No Cameras Connected
            </span>
            <span style={{ fontSize: '9.5px', color: '#38BDF8', marginTop: '2px' }}>
              + Click to connect source
            </span>
          </div>
        ) : (
          cameras.map((cam) => (
            <div
              key={cam.camera_id}
              className="sidebar-card"
              onClick={() => onSelectCamera(cam.camera_id)}
              style={{
                cursor: 'pointer',
                borderColor: cam.camera_id === selectedCameraId ? 'rgba(59, 130, 246, 0.4)' : 'var(--color-border-subtle)',
                backgroundColor: cam.camera_id === selectedCameraId ? 'rgba(59, 130, 246, 0.06)' : 'var(--color-surface-elevated)',
                marginBottom: '4px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Video size={13} color="var(--color-text-primary)" />
                  <span style={{ fontWeight: 700, fontSize: '11px' }}>{cam.camera_id}</span>
                </div>
                <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: cam.status === 'ONLINE' ? 'var(--color-green)' : 'var(--color-red)' }} />
              </div>
              <span style={{ fontSize: '10px', color: 'var(--color-text-secondary)' }}>{cam.name}</span>
              <span style={{ fontSize: '9px', color: 'var(--color-text-muted)', fontFamily: 'var(--font-mono)' }}>
                SECTOR {cam.sector_id || 'B-07'}
              </span>
            </div>
          ))
        )}
      </div>

      {/* 3. Border Sector */}
      <div>
        <div className="sidebar-section-title">BORDER SECTOR</div>
        <div className="sidebar-card">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontWeight: 700, fontSize: '11px' }}>
              {activeCam ? `SECTOR ${activeCam.sector_id || 'B-07'}` : 'SECTOR --'}
            </span>
            <span
              style={{
                fontSize: '9px',
                fontWeight: 700,
                color: activeCam ? 'var(--color-green)' : 'var(--color-text-muted)',
                background: activeCam ? 'var(--color-green-bg)' : 'transparent',
                padding: '1px 5px',
                borderRadius: '3px',
              }}
            >
              {activeCam ? 'ACTIVE' : 'OFFLINE'}
            </span>
          </div>
          <span style={{ fontSize: '10px', color: 'var(--color-text-secondary)' }}>
            {activeCam?.sector_name || 'No Active Sector'}
          </span>
        </div>
      </div>

      {/* 4. Threat Summary */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
        <div className="sidebar-section-title">THREAT SUMMARY</div>

        <div className="threat-count-row">
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <ShieldAlert size={13} color="var(--color-red)" />
            <span style={{ fontSize: '10px', fontWeight: 600, color: 'var(--color-red)' }}>CRITICAL / HIGH</span>
          </div>
          <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--color-red)' }}>
            {criticalOrHigh}
          </span>
        </div>

        <div className="threat-count-row">
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <AlertTriangle size={13} color="var(--color-amber)" />
            <span style={{ fontSize: '10px', fontWeight: 600, color: 'var(--color-amber)' }}>MEDIUM</span>
          </div>
          <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--color-amber)' }}>
            {medium}
          </span>
        </div>

        <div className="threat-count-row">
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <CheckCircle2 size={13} color="var(--color-blue)" />
            <span style={{ fontSize: '10px', fontWeight: 600, color: 'var(--color-blue)' }}>LOW / INFO</span>
          </div>
          <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--color-blue)' }}>
            {lowOrInfo}
          </span>
        </div>
      </div>

      {/* 5. System Health */}
      <div style={{ marginTop: 'auto', paddingTop: '8px' }}>
        <div className="sidebar-section-title">SYSTEM HEALTH</div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '10px', marginTop: '3px' }}>
          <span style={{ color: 'var(--color-green)', fontWeight: 700 }}>ALL SYSTEMS OPERATIONAL</span>
          <span style={{ color: 'var(--color-green)', fontFamily: 'var(--font-mono)', fontWeight: 700 }}>100%</span>
        </div>
        <div
          style={{
            width: '100%',
            height: '4px',
            backgroundColor: 'var(--color-surface-elevated)',
            borderRadius: '2px',
            marginTop: '5px',
            overflow: 'hidden',
          }}
        >
          <div style={{ width: '100%', height: '100%', backgroundColor: 'var(--color-green)' }} />
        </div>
      </div>
    </aside>
  );
};
