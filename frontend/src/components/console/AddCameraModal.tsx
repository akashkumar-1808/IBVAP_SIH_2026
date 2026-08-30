import React, { useState } from 'react';
import { Video, Plus, X, AlertCircle, Loader2 } from 'lucide-react';
import { CameraInfo } from '../../types';
import { connectCamera } from '../../services/api';

interface AddCameraModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCameraConnected: (camera: CameraInfo) => void;
}

export const AddCameraModal: React.FC<AddCameraModalProps> = ({
  isOpen,
  onClose,
  onCameraConnected,
}) => {
  const [cameraId, setCameraId] = useState<string>('LIVE-01');
  const [cameraName, setCameraName] = useState<string>('Perimeter North RTSP');
  const [rtspUrl, setRtspUrl] = useState<string>('rtsp://192.168.1.4:1945/');
  const [sectorName, setSectorName] = useState<string>('Northern Border Sector B-07');
  const [device, setDevice] = useState<string>('cpu');
  const [isConnecting, setIsConnecting] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!rtspUrl.trim()) {
      setErrorMsg('RTSP Stream URL is required.');
      return;
    }

    setIsConnecting(true);
    setErrorMsg(null);

    try {
      const response = await connectCamera({
        camera_id: cameraId.trim() || 'LIVE-01',
        name: cameraName.trim() || 'Live RTSP Camera',
        rtsp_url: rtspUrl.trim(),
        sector_name: sectorName.trim(),
        device,
      });

      onCameraConnected(response.camera);
      onClose();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to connect to RTSP stream. Check IP/port connectivity.');
    } finally {
      setIsConnecting(false);
    }
  };

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(4, 6, 10, 0.85)',
        backdropFilter: 'blur(6px)',
        zIndex: 150,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '20px',
      }}
      onClick={onClose}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          width: '540px',
          maxWidth: '95vw',
          background: 'var(--bg-panel)',
          border: '1px solid var(--border-panel)',
          borderRadius: '8px',
          padding: '22px',
          display: 'flex',
          flexDirection: 'column',
          gap: '16px',
          boxShadow: '0 12px 40px rgba(0, 0, 0, 0.85)',
        }}
      >
        {/* Modal Header */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid var(--border-panel)', paddingBottom: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Video size={18} color="var(--accent-cyan)" />
            <span style={{ fontSize: '15px', fontWeight: 800, color: '#fff' }}>CONNECT LIVE RTSP CAMERA</span>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-muted)',
              cursor: 'pointer',
            }}
          >
            <X size={18} />
          </button>
        </div>

        {errorMsg && (
          <div
            style={{
              background: 'rgba(239, 68, 68, 0.12)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              borderRadius: '6px',
              padding: '10px 12px',
              display: 'flex',
              alignItems: 'flex-start',
              gap: '8px',
              fontSize: '11px',
              color: '#f87171',
            }}
          >
            <AlertCircle size={15} style={{ flexShrink: 0, marginTop: '1px' }} />
            <div>{errorMsg}</div>
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '10px', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '4px' }}>
                CAMERA ID
              </label>
              <input
                type="text"
                value={cameraId}
                onChange={(e) => setCameraId(e.target.value)}
                placeholder="e.g. LIVE-01"
                required
                style={{
                  width: '100%',
                  background: 'var(--bg-card)',
                  border: '1px solid var(--border-panel)',
                  borderRadius: '4px',
                  padding: '8px 10px',
                  color: '#fff',
                  fontSize: '12px',
                  fontFamily: 'var(--font-mono)',
                  outline: 'none',
                }}
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '10px', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '4px' }}>
                CAMERA LABEL / NAME
              </label>
              <input
                type="text"
                value={cameraName}
                onChange={(e) => setCameraName(e.target.value)}
                placeholder="e.g. Perimeter North"
                required
                style={{
                  width: '100%',
                  background: 'var(--bg-card)',
                  border: '1px solid var(--border-panel)',
                  borderRadius: '4px',
                  padding: '8px 10px',
                  color: '#fff',
                  fontSize: '12px',
                  outline: 'none',
                }}
              />
            </div>
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '10px', fontWeight: 700, color: 'var(--accent-cyan)', marginBottom: '4px' }}>
              RTSP STREAM URL (LIVE IP CAMERA)
            </label>
            <input
              type="text"
              value={rtspUrl}
              onChange={(e) => setRtspUrl(e.target.value)}
              placeholder="rtsp://192.168.1.4:1945/"
              required
              style={{
                width: '100%',
                background: 'var(--bg-card)',
                border: '1px solid rgba(6, 182, 212, 0.4)',
                borderRadius: '4px',
                padding: '10px 12px',
                color: '#fff',
                fontSize: '12px',
                fontFamily: 'var(--font-mono)',
                outline: 'none',
              }}
            />
            <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: '3px' }}>
              Example: <code>rtsp://192.168.1.4:1945/</code> or <code>rtsp://user:pass@192.168.1.50:554/live</code>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1.5fr 1fr', gap: '12px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '10px', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '4px' }}>
                SECTOR LOCATION
              </label>
              <input
                type="text"
                value={sectorName}
                onChange={(e) => setSectorName(e.target.value)}
                placeholder="Sector Name"
                style={{
                  width: '100%',
                  background: 'var(--bg-card)',
                  border: '1px solid var(--border-panel)',
                  borderRadius: '4px',
                  padding: '8px 10px',
                  color: '#fff',
                  fontSize: '12px',
                  outline: 'none',
                }}
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '10px', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '4px' }}>
                INFERENCE DEVICE
              </label>
              <select
                value={device}
                onChange={(e) => setDevice(e.target.value)}
                style={{
                  width: '100%',
                  background: 'var(--bg-card)',
                  border: '1px solid var(--border-panel)',
                  borderRadius: '4px',
                  padding: '8px 10px',
                  color: '#fff',
                  fontSize: '12px',
                  outline: 'none',
                }}
              >
                <option value="cpu">CPU (Standard)</option>
                <option value="cuda">CUDA (GPU)</option>
              </select>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '10px', marginTop: '10px' }}>
            <button
              type="button"
              onClick={onClose}
              className="btn-command"
              disabled={isConnecting}
              style={{ padding: '8px 14px' }}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn-command btn-primary"
              disabled={isConnecting}
              style={{ padding: '8px 16px', gap: '6px' }}
            >
              {isConnecting ? (
                <>
                  <Loader2 size={14} className="animate-spin" />
                  <span>Connecting & Warming Up Pipeline...</span>
                </>
              ) : (
                <>
                  <Plus size={14} />
                  <span>Connect & Launch Analysis</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
