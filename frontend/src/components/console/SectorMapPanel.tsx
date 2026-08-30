import React from 'react';
import { Map } from 'lucide-react';
import { CameraInfo, BorderTrack } from '../../types';

interface SectorMapPanelProps {
  cameras: CameraInfo[];
  borderTrack?: BorderTrack;
}

export const SectorMapPanel: React.FC<SectorMapPanelProps> = ({ cameras: _, borderTrack }) => {
  return (
    <div className="mini-map-panel" style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span className="intel-card-header">SECTOR MAP (SECTOR B-07)</span>
        <Map size={13} color="var(--text-muted)" />
      </div>

      <div
        style={{
          flex: 1,
          background: '#070a0f',
          border: '1px solid var(--border-panel)',
          borderRadius: '4px',
          position: 'relative',
          overflow: 'hidden',
        }}
      >
        <svg viewBox="0 0 300 160" style={{ width: '100%', height: '100%' }}>
          {/* Background Grid */}
          <defs>
            <pattern id="sectorGrid" width="20" height="20" patternUnits="userSpaceOnUse">
              <path d="M 20 0 L 0 0 0 20" fill="none" stroke="rgba(255,255,255,0.04)" strokeWidth="0.5" />
            </pattern>
          </defs>
          <rect width="300" height="160" fill="url(#sectorGrid)" />

          {/* Restricted Zone Region */}
          <path d="M 0 100 L 300 100 L 300 160 L 0 160 Z" fill="rgba(239, 68, 68, 0.08)" />
          <text x="10" y="145" fill="#ef4444" fontSize="8" fontWeight="700" opacity="0.6">
            RESTRICTED ZONE
          </text>

          {/* Warning Buffer Region */}
          <path d="M 0 70 L 300 70 L 300 100 L 0 100 Z" fill="rgba(245, 158, 11, 0.06)" />
          <text x="10" y="88" fill="#f59e0b" fontSize="8" fontWeight="600" opacity="0.6">
            BUFFER (15m)
          </text>

          {/* Border Line */}
          <line x1="0" y1="100" x2="300" y2="100" stroke="#ef4444" strokeWidth="2" strokeDasharray="4,2" />
          <text x="230" y="96" fill="#ef4444" fontSize="8" fontWeight="700">
            BORDER LINE
          </text>

          {/* Camera 1 Icon & FOV Cone */}
          <path d="M 120 30 L 70 120 L 170 120 Z" fill="rgba(6, 182, 212, 0.05)" />
          <circle cx="120" cy="30" r="4" fill="#06b6d4" />
          <text x="128" y="32" fill="#06b6d4" fontSize="8" fontWeight="700">
            CAM-01
          </text>

          {/* Camera 2 Icon & FOV Cone */}
          <path d="M 220 30 L 170 120 L 270 120 Z" fill="rgba(6, 182, 212, 0.05)" />
          <circle cx="220" cy="30" r="4" fill="#06b6d4" />
          <text x="228" y="32" fill="#06b6d4" fontSize="8" fontWeight="700">
            CAM-02
          </text>

          {/* Multi-Camera Trajectory Path (Rendered only when active) */}
          {borderTrack && (
            <g>
              <path d="M 110 50 Q 130 90 150 115 T 190 135" fill="none" stroke="#10b981" strokeWidth="2" strokeDasharray="3,3" />
              <circle cx="150" cy="115" r="4" fill="#10b981" />
              <circle cx="150" cy="115" r="7" fill="none" stroke="#10b981" strokeWidth="1" />
              <text x="160" y="118" fill="#10b981" fontSize="8" fontWeight="800">
                {borderTrack.border_track_id}
              </text>
            </g>
          )}
        </svg>
      </div>
    </div>
  );
};
