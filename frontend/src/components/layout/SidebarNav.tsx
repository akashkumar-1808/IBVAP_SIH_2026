import React from 'react';
import {
  Globe,
  Video,
  Map,
  ShieldAlert,
  Crosshair,
  Archive,
  BarChart3,
  FileText,
  Plus,
  Radio,
} from 'lucide-react';
import { CameraInfo, EventRecord } from '../../types';

export type NavTab =
  | 'OVERVIEW'
  | 'LIVE_SURVEILLANCE'
  | 'BORDER_INTELLIGENCE'
  | 'INCIDENTS'
  | 'TARGET_TRACKING'
  | 'EVIDENCE_AUDIT'
  | 'AI_ANALYTICS'
  | 'REPORTS';

interface SidebarNavProps {
  activeNav: NavTab;
  onSelectNav: (tab: NavTab) => void;
  cameras: CameraInfo[];
  selectedCameraId: string;
  onSelectCamera: (id: string) => void;
  onOpenAddCamera: () => void;
  onDisconnectCamera?: (id: string) => void;
  events: EventRecord[];
  activeTracksCount?: number;
  evidenceCount?: number;
  isBackendOnline?: boolean;
}

export const SidebarNav: React.FC<SidebarNavProps> = ({
  activeNav,
  onSelectNav,
  cameras,
  selectedCameraId,
  onSelectCamera,
  onOpenAddCamera,
  onDisconnectCamera: _onDisconnectCamera,
  events,
  activeTracksCount = 0,
  evidenceCount = 0,
  isBackendOnline = true,
}) => {
  // Compute real threat metrics from backend events
  const criticalCount = events.filter((e) => e.priority === 'CRITICAL').length;
  const highCount = events.filter((e) => e.priority === 'HIGH').length;
  const totalThreats = criticalCount + highCount;

  const activeCam = cameras.find((c) => c.camera_id === selectedCameraId) || cameras[0] || {
    camera_id: 'DEMO-CAM-01',
    name: 'Sector B-07 Border Camera',
    sector_id: 'SECTOR-B07',
    sector_name: 'Northern Border Sector',
    status: 'ONLINE',
  };

  const navItems: Array<{
    id: NavTab;
    label: string;
    sub: string;
    icon: React.ReactNode;
    badge?: string | number;
    badgeColor?: string;
  }> = [
    {
      id: 'OVERVIEW',
      label: 'OVERVIEW',
      sub: 'National Border GIS',
      icon: <Globe size={16} />,
    },
    {
      id: 'LIVE_SURVEILLANCE',
      label: 'LIVE SURVEILLANCE',
      sub: 'Sector B-07 Stream',
      icon: <Video size={16} />,
      badge: 'LIVE',
      badgeColor: isBackendOnline ? '#10B981' : '#EF4444',
    },
    {
      id: 'BORDER INTELLIGENCE' as any,
      label: 'BORDER INTELLIGENCE',
      sub: 'Tactical GIS Workspace',
      icon: <Map size={16} />,
    },
    {
      id: 'INCIDENTS',
      label: 'INCIDENTS',
      sub: 'Forensic Event Log',
      icon: <ShieldAlert size={16} />,
      badge: events.length > 0 ? events.length : undefined,
      badgeColor: totalThreats > 0 ? '#EF4444' : '#3B82F6',
    },
    {
      id: 'TARGET_TRACKING',
      label: 'TARGET TRACKING',
      sub: 'Kinematics & Spatial',
      icon: <Crosshair size={16} />,
      badge: activeTracksCount > 0 ? activeTracksCount : undefined,
      badgeColor: '#38BDF8',
    },
    {
      id: 'EVIDENCE_AUDIT',
      label: 'EVIDENCE AUDIT',
      sub: 'Cryptographic Chain',
      icon: <Archive size={16} />,
      badge: evidenceCount > 0 ? evidenceCount : undefined,
      badgeColor: '#10B981',
    },
    {
      id: 'AI_ANALYTICS',
      label: 'AI ANALYTICS',
      sub: 'Funnel & Intelligence',
      icon: <BarChart3 size={16} />,
    },
    {
      id: 'REPORTS',
      label: 'REPORTS',
      sub: 'Operational Dossier',
      icon: <FileText size={16} />,
    },
  ];

  return (
    <aside className="operator-sidebar">
      {/* 1. Primary Operational Navigation (8 Views) */}
      <div className="sidebar-nav-list">
        {navItems.map((item) => {
          // Normalizing id
          const targetId = item.id === ('BORDER INTELLIGENCE' as any) ? 'BORDER_INTELLIGENCE' : item.id;
          const isActive = activeNav === targetId;

          return (
            <div
              key={targetId}
              className={`sidebar-nav-item ${isActive ? 'active' : ''}`}
              onClick={() => onSelectNav(targetId)}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '9px 12px',
                borderRadius: '4px',
                cursor: 'pointer',
                backgroundColor: isActive ? 'rgba(59, 130, 246, 0.14)' : 'transparent',
                borderLeft: isActive ? '3px solid #38BDF8' : '3px solid transparent',
                marginBottom: '3px',
                transition: 'all 0.15s ease-out',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <div style={{ color: isActive ? '#38BDF8' : 'var(--color-text-secondary)' }}>
                  {item.icon}
                </div>
                <div style={{ display: 'flex', flexDirection: 'column' }}>
                  <span
                    style={{
                      fontSize: '10.5px',
                      fontWeight: isActive ? 800 : 600,
                      color: isActive ? '#F1F5F9' : 'var(--color-text-primary)',
                      letterSpacing: '0.04em',
                    }}
                  >
                    {item.label}
                  </span>
                  <span style={{ fontSize: '8.5px', color: 'var(--color-text-muted)' }}>
                    {item.sub}
                  </span>
                </div>
              </div>

              {item.badge !== undefined && (
                <span
                  style={{
                    fontSize: '8.5px',
                    fontWeight: 800,
                    padding: '2px 6px',
                    borderRadius: '3px',
                    backgroundColor: item.badgeColor ? `${item.badgeColor}25` : 'rgba(255,255,255,0.1)',
                    color: item.badgeColor || '#E2E8F0',
                    border: `1px solid ${item.badgeColor || 'rgba(255,255,255,0.2)'}`,
                  }}
                >
                  {item.badge}
                </span>
              )}
            </div>
          );
        })}
      </div>

      <div style={{ width: '100%', height: '1px', backgroundColor: 'var(--color-border-subtle)', margin: '10px 0' }} />

      {/* 2. Active Sector & Camera Network Status */}
      <div style={{ padding: '0 4px' }}>
        <div className="sidebar-section-title" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
          <span style={{ fontSize: '9px', fontWeight: 800, color: 'var(--color-text-muted)', letterSpacing: '0.08em' }}>
            ACTIVE PROTOTYPE SECTOR
          </span>
          <button
            onClick={onOpenAddCamera}
            title="Connect Video Feed"
            style={{
              background: 'none',
              border: 'none',
              color: '#38BDF8',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              padding: 0,
            }}
          >
            <Plus size={14} />
          </button>
        </div>

        <div
          className="sidebar-card"
          onClick={() => onSelectCamera(activeCam.camera_id)}
          style={{
            padding: '10px',
            backgroundColor: 'rgba(15, 23, 42, 0.65)',
            border: '1px solid var(--color-border-subtle)',
            borderRadius: '4px',
            display: 'flex',
            flexDirection: 'column',
            gap: '6px',
            cursor: 'pointer',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '10px', fontWeight: 800, color: '#F1F5F9' }}>
              SECTOR B-07
            </span>
            <span
              style={{
                fontSize: '8px',
                fontWeight: 800,
                color: isBackendOnline ? '#34D399' : '#F87171',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
              }}
            >
              <span
                style={{
                  width: 5,
                  height: 5,
                  borderRadius: '50%',
                  backgroundColor: isBackendOnline ? '#10B981' : '#EF4444',
                }}
              />
              {isBackendOnline ? 'ONLINE' : 'OFFLINE'}
            </span>
          </div>

          <div style={{ fontSize: '8.5px', color: 'var(--color-text-secondary)' }}>
            CAM: <strong style={{ color: '#E2E8F0' }}>{activeCam.camera_id}</strong>
          </div>

          <div style={{ fontSize: '8px', color: 'var(--color-text-muted)' }}>
            YOLO / ByteTrack / Spatial / Fusion
          </div>

          <button
            onClick={() => onSelectNav('LIVE_SURVEILLANCE')}
            style={{
              marginTop: '4px',
              padding: '4px 8px',
              backgroundColor: 'rgba(59, 130, 246, 0.15)',
              border: '1px solid rgba(59, 130, 246, 0.35)',
              borderRadius: '3px',
              color: '#60A5FA',
              fontSize: '8.5px',
              fontWeight: 700,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '4px',
            }}
          >
            <Radio size={11} /> Open Live Feed
          </button>
        </div>
      </div>
    </aside>
  );
};
