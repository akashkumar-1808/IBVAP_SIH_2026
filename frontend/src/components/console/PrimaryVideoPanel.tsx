import React, { useRef, useState, useEffect, useCallback } from 'react';
import { Maximize2, Camera as CameraIcon, Film, AlertCircle, Upload, Play, Square } from 'lucide-react';
import {
  getStreamUrl,
  uploadAnalysisVideo,
  runAnalysis,
  stopAnalysis,
  fetchAnalysisStatus,
} from '../../services/api';
import {
  EnvironmentState,
  TrackState,
  SpatialState,
  BehaviorPrimitive,
  EventRecord,
  CameraContract,
  StreamHealthContract,
} from '../../types';

interface PrimaryVideoPanelProps {
  cameraId: string;
  cameraName?: string;
  fps: number;
  environment?: EnvironmentState;
  tracks: TrackState[];
  spatialStates: SpatialState[];
  behaviors: BehaviorPrimitive[];
  activeEvents: EventRecord[];
  cameraTelemetry?: CameraContract;
  streamHealth?: StreamHealthContract;
  analysisStatus?: string;
  onOpenAddCamera: () => void;
}

type SourceStatus = 'IDLE' | 'READY' | 'UPLOADING' | 'READY TO ANALYZE' | 'STARTING' | 'ANALYZING' | 'EVENT_DETECTED' | 'COMPLETED' | 'ERROR';

export const PrimaryVideoPanel: React.FC<PrimaryVideoPanelProps> = ({
  cameraId,
  cameraTelemetry,
  streamHealth,
  analysisStatus: incomingStatus,
  onOpenAddCamera,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [streamSrc, setStreamSrc] = useState<string>('');
  const [streamError, setStreamError] = useState<boolean>(false);
  const [timeStr, setTimeStr] = useState<string>('');

  // Video Source & Analysis Workflow State
  const [analysisStatus, setAnalysisStatus] = useState<SourceStatus>('READY');
  const [selectedFileName, setSelectedFileName] = useState<string>('');
  const [selectedFilePath, setSelectedFilePath] = useState<string>('');
  const [uploadProgress, setUploadProgress] = useState<number>(0);
  const [statusMessage, setStatusMessage] = useState<string>('');
  const [isActionBusy, setIsActionBusy] = useState<boolean>(false);

  // Sync real-time status from WebSocket telemetry if provided
  useEffect(() => {
    if (incomingStatus) {
      setAnalysisStatus(incomingStatus as SourceStatus);
    }
  }, [incomingStatus]);

  const camId = cameraId || 'DEMO-CAM-01';

  // Periodic poll for backend analysis status
  const checkStatus = useCallback(async () => {
    if (analysisStatus === 'UPLOADING') return;
    try {
      const res = await fetchAnalysisStatus(camId);
      if (res.status) {
        setAnalysisStatus(res.status as SourceStatus);
        if (res.file_name && !selectedFileName) {
          setSelectedFileName(res.file_name);
        }
        if (res.video_path && !selectedFilePath) {
          setSelectedFilePath(res.video_path);
        }
      }
    } catch {
      // Backend status poll failure ignored
    }
  }, [camId, analysisStatus, selectedFileName, selectedFilePath]);

  useEffect(() => {
    checkStatus();
    const interval = setInterval(checkStatus, 3000);
    return () => clearInterval(interval);
  }, [checkStatus]);

  useEffect(() => {
    const targetCam = cameraId || 'DEMO-CAM-01';
    setStreamSrc(getStreamUrl(targetCam));
    setStreamError(false);
  }, [cameraId]);

  useEffect(() => {
    const updateTimer = () => {
      const now = new Date();
      setTimeStr(now.toISOString().replace('T', ' ').substring(0, 19) + ' UTC');
    };
    updateTimer();
    const interval = setInterval(updateTimer, 1000);
    return () => clearInterval(interval);
  }, []);

  const handleFullscreen = () => {
    if (containerRef.current) {
      if (document.fullscreenElement) {
        document.exitFullscreen();
      } else {
        containerRef.current.requestFullscreen();
      }
    }
  };

  // Upload handler for MP4 file
  const handleFileSelected = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.name.toLowerCase().endsWith('.mp4') && file.type !== 'video/mp4') {
      setAnalysisStatus('ERROR');
      setStatusMessage('Only .mp4 video files are supported.');
      return;
    }

    setAnalysisStatus('UPLOADING');
    setSelectedFileName(file.name);
    setUploadProgress(0);
    setStatusMessage(`Uploading ${file.name}...`);

    try {
      const res = await uploadAnalysisVideo(file, camId, (pct) => setUploadProgress(pct));
      setAnalysisStatus('READY TO ANALYZE');
      setSelectedFilePath(res.video_path);
      setStatusMessage(res.message);
    } catch (err: any) {
      setAnalysisStatus('ERROR');
      setStatusMessage(err?.message || 'Video upload failed.');
    } finally {
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  // Trigger analysis on target video file
  const handleRunAnalysis = async (targetVideoPath?: string) => {
    const pathToRun = targetVideoPath || selectedFilePath || 'storage/samples/test_video.mp4';
    setIsActionBusy(true);
    setAnalysisStatus('STARTING');
    setStatusMessage('Starting 9-stage AI analysis pipeline...');
    try {
      const res = await runAnalysis({
        camera_id: camId,
        video_file_path: pathToRun,
        device: 'cpu',
      });
      const nextStatus = (res.status as SourceStatus) || 'ANALYZING';
      setAnalysisStatus(nextStatus);
      setStatusMessage(`Real AI pipeline active on ${selectedFileName || res.file_name || 'test_video.mp4'}`);
      // Re-trigger live stream with timestamp cache buster
      setStreamSrc(`${getStreamUrl(camId)}?t=${Date.now()}`);
      setStreamError(false);
    } catch (err: any) {
      setAnalysisStatus('ERROR');
      setStatusMessage(err?.message || 'Failed to start analysis.');
    } finally {
      setIsActionBusy(false);
    }
  };

  // Stop analysis session
  const handleStopAnalysis = async () => {
    setIsActionBusy(true);
    try {
      await stopAnalysis(camId);
      setAnalysisStatus('COMPLETED');
      setStatusMessage('Analysis stopped by operator.');
    } catch (err: any) {
      setStatusMessage(err?.message || 'Failed to stop analysis.');
    } finally {
      setIsActionBusy(false);
    }
  };

  // Quick SIH Demo button
  const handleQuickDemo = () => {
    setSelectedFileName('test_video.mp4');
    setSelectedFilePath('storage/samples/test_video.mp4');
    handleRunAnalysis('storage/samples/test_video.mp4');
  };

  return (
    <div className="live-video-box" ref={containerRef}>
      {/* Panel Top Header Strip */}
      <div className="panel-header-strip">
        <span style={{ textTransform: 'uppercase' }}>LIVE VIDEO FEED</span>
        <span style={{ fontSize: '10px', color: 'var(--color-text-secondary)', fontFamily: 'var(--font-mono)' }}>
          {cameraTelemetry?.resolution || '1280x720'} · 25.0 FPS
        </span>
      </div>

      {/* Main Video Viewport */}
      <div className="video-screen-container">
        {streamSrc && !streamError ? (
          <img
            src={streamSrc}
            alt="Live Stream"
            className="video-stream-img"
            onError={() => setStreamError(true)}
          />
        ) : (
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '12px',
              padding: '24px',
              textAlign: 'center',
            }}
          >
            <AlertCircle size={32} color="var(--color-amber)" />
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <span style={{ fontWeight: 700, fontSize: '13px' }}>NO ACTIVE VIDEO STREAM</span>
              <span style={{ fontSize: '11px', color: 'var(--color-text-secondary)' }}>
                Camera {camId} is offline or stream is initializing.
              </span>
            </div>
            <button className="btn-neutral-outline" onClick={onOpenAddCamera}>
              Connect Video Stream
            </button>
          </div>
        )}

        {/* Video HUD Overlays: Timestamp + Camera ID (Top-Left) */}
        <div
          style={{
            position: 'absolute',
            top: '10px',
            left: '12px',
            pointerEvents: 'none',
            display: 'flex',
            flexDirection: 'column',
            gap: '2px',
            fontFamily: 'var(--font-mono)',
            fontSize: '10.5px',
            fontWeight: 700,
            color: '#FFFFFF',
            textShadow: '0 1px 3px rgba(0,0,0,0.85)',
          }}
        >
          <span>{timeStr}</span>
          <span>{camId}</span>
        </div>

        {/* Video HUD Overlays: Status Badge & Continuity (Top-Right) */}
        {(() => {
          let badgeBg = 'rgba(0, 0, 0, 0.65)';
          let badgeBorder = 'rgba(239, 68, 68, 0.4)';
          let dotColor = 'var(--color-red)';
          let badgeLabel = 'LIVE';

          if (analysisStatus === 'COMPLETED' || streamHealth?.state === 'COMPLETED') {
            badgeBg = 'rgba(6, 78, 59, 0.85)';
            badgeBorder = '#10B981';
            dotColor = '#10B981';
            badgeLabel = 'ANALYSIS COMPLETE';
          } else if (streamHealth?.state === 'STALE_FROZEN') {
            badgeBg = 'rgba(180, 83, 9, 0.85)';
            badgeBorder = '#F59E0B';
            dotColor = '#F59E0B';
            badgeLabel = 'FROZEN SENSOR';
          } else if (streamHealth?.state === 'RECONNECTING') {
            badgeBg = 'rgba(180, 83, 9, 0.85)';
            badgeBorder = '#F59E0B';
            dotColor = '#F59E0B';
            badgeLabel = 'RECONNECTING';
          } else if (streamHealth?.state === 'INTERRUPTED') {
            badgeBg = 'rgba(153, 27, 27, 0.85)';
            badgeBorder = '#EF4444';
            dotColor = '#EF4444';
            badgeLabel = 'INTERRUPTED';
          } else if (streamHealth?.state === 'RECOVERED') {
            badgeBg = 'rgba(30, 58, 138, 0.85)';
            badgeBorder = '#38BDF8';
            dotColor = '#38BDF8';
            badgeLabel = 'RECOVERED';
          } else if (streamHealth?.state === 'DEGRADED') {
            badgeBg = 'rgba(180, 83, 9, 0.85)';
            badgeBorder = '#F59E0B';
            dotColor = '#F59E0B';
            badgeLabel = 'DEGRADED';
          } else if (streamHealth?.state === 'HEALTHY') {
            badgeBg = 'rgba(6, 78, 59, 0.75)';
            badgeBorder = 'rgba(16, 185, 129, 0.4)';
            dotColor = '#10B981';
            badgeLabel = 'LIVE · HEALTHY';
          }

          return (
            <div style={{ position: 'absolute', top: '10px', right: '12px', pointerEvents: 'none', display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '4px' }}>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  background: badgeBg,
                  border: `1px solid ${badgeBorder}`,
                  padding: '3px 8px',
                  borderRadius: '4px',
                  fontFamily: 'var(--font-mono)',
                  fontSize: '10px',
                  fontWeight: 800,
                  color: '#FFFFFF',
                }}
              >
                <span
                  style={{
                    width: '6px',
                    height: '6px',
                    borderRadius: '50%',
                    backgroundColor: dotColor,
                  }}
                />
                <span>{badgeLabel}</span>
              </div>
              {streamHealth && streamHealth.gap_count > 0 && analysisStatus !== 'COMPLETED' && (
                <div
                  style={{
                    background: 'rgba(0, 0, 0, 0.75)',
                    border: '1px solid rgba(245, 158, 11, 0.3)',
                    padding: '2px 6px',
                    borderRadius: '3px',
                    fontFamily: 'var(--font-mono)',
                    fontSize: '9px',
                    color: '#F59E0B',
                    fontWeight: 600,
                  }}
                >
                  AUDIT: {streamHealth.gap_count} GAPS ({streamHealth.dropped_frames_total} DROPPED)
                </div>
              )}
            </div>
          );
        })()}

        {/* Video HUD Overlays: Post-completion indicator banner */}
        {analysisStatus === 'COMPLETED' && (
          <div
            style={{
              position: 'absolute',
              bottom: '10px',
              left: '50%',
              transform: 'translateX(-50%)',
              pointerEvents: 'none',
              background: 'rgba(15, 23, 42, 0.9)',
              border: '1px solid rgba(16, 185, 129, 0.5)',
              borderRadius: '4px',
              padding: '4px 12px',
              fontSize: '10px',
              fontWeight: 700,
              color: '#10B981',
              letterSpacing: '0.04em',
              fontFamily: 'var(--font-mono)',
              boxShadow: '0 2px 10px rgba(0,0,0,0.6)',
              whiteSpace: 'nowrap',
            }}
          >
            ● VIDEO REACHED EOF · LAST PROCESSED KEYFRAME PRESERVED
          </div>
        )}

        {/* Video HUD Overlays: Camera Frozen Warning */}
        {streamHealth?.is_frozen && analysisStatus !== 'COMPLETED' && (
          <div
            style={{
              position: 'absolute',
              bottom: '10px',
              left: '50%',
              transform: 'translateX(-50%)',
              pointerEvents: 'none',
              background: 'rgba(180, 83, 9, 0.9)',
              border: '1px solid #F59E0B',
              borderRadius: '4px',
              padding: '4px 12px',
              fontSize: '10px',
              fontWeight: 700,
              color: '#FFFFFF',
              letterSpacing: '0.04em',
              fontFamily: 'var(--font-mono)',
              boxShadow: '0 2px 10px rgba(0,0,0,0.6)',
              whiteSpace: 'nowrap',
            }}
          >
            ● STATIC IMAGERY DETECTED · SUSPECTED SENSOR OR ENCODER FREEZE
          </div>
        )}

        {/* Video HUD Overlays: Reconnecting Banner */}
        {streamHealth?.state === 'RECONNECTING' && (
          <div
            style={{
              position: 'absolute',
              bottom: '10px',
              left: '50%',
              transform: 'translateX(-50%)',
              pointerEvents: 'none',
              background: 'rgba(15, 23, 42, 0.9)',
              border: '1px solid #F59E0B',
              borderRadius: '4px',
              padding: '4px 12px',
              fontSize: '10px',
              fontWeight: 700,
              color: '#F59E0B',
              letterSpacing: '0.04em',
              fontFamily: 'var(--font-mono)',
              boxShadow: '0 2px 10px rgba(0,0,0,0.6)',
              whiteSpace: 'nowrap',
            }}
          >
            ● STREAM INTERRUPTED · AUTOMATIC BOUNDED BACKOFF ACTIVE
          </div>
        )}
      </div>

      {/* Video Source & Intelligence Analysis Bar */}
      <div className="video-source-bar">
        {/* Left: Source Status Badge & File info */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: 0, flex: 1 }}>
          <span className={`video-source-status-badge status-badge-${analysisStatus.toLowerCase().replace(/\s+/g, '-')}`}>
            <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: 'currentColor' }} />
            {analysisStatus === 'UPLOADING' ? `UPLOADING (${uploadProgress}%)` : analysisStatus}
          </span>
          <span
            style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '10px',
              color: 'var(--color-text-secondary)',
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              maxWidth: '220px',
            }}
            title={selectedFileName || statusMessage}
          >
            {selectedFileName ? selectedFileName : (statusMessage || 'Select or upload MP4')}
          </span>
        </div>

        {/* Right: Operator Video Actions */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <input
            type="file"
            ref={fileInputRef}
            accept=".mp4,video/mp4"
            style={{ display: 'none' }}
            onChange={handleFileSelected}
          />
          <button
            className="btn-neutral-outline"
            style={{ padding: '3px 8px', fontSize: '10px' }}
            onClick={() => fileInputRef.current?.click()}
            disabled={analysisStatus === 'UPLOADING' || isActionBusy}
            title="Upload custom MP4 video file"
          >
            <Upload size={11} />
            <span>Upload MP4</span>
          </button>

          {analysisStatus === 'ANALYZING' || analysisStatus === 'EVENT_DETECTED' || analysisStatus === 'STARTING' ? (
            <button
              className="btn-neutral-outline"
              style={{ padding: '3px 8px', fontSize: '10px', borderColor: 'var(--color-red)', color: 'var(--color-red)' }}
              onClick={handleStopAnalysis}
              disabled={isActionBusy}
              title="Stop active analysis pipeline"
            >
              <Square size={11} />
              <span>Stop</span>
            </button>
          ) : (
            <button
              className="btn-primary"
              style={{ padding: '3px 10px', fontSize: '10px', background: '#38BDF8', color: '#04070D', fontWeight: 700 }}
              onClick={() => handleRunAnalysis(selectedFilePath || 'storage/samples/test_video.mp4')}
              disabled={analysisStatus === 'UPLOADING' || isActionBusy}
              title="Run real 9-stage intelligence analysis"
            >
              <Play size={11} style={{ fill: 'currentColor' }} />
              <span>Run Analysis</span>
            </button>
          )}

          <button
            className="btn-neutral-outline"
            style={{ padding: '3px 8px', fontSize: '10px', color: 'var(--color-text-secondary)' }}
            onClick={handleQuickDemo}
            disabled={analysisStatus === 'ANALYZING' || analysisStatus === 'UPLOADING' || isActionBusy}
            title="Replay standard SIH test breach video"
          >
            <Film size={11} />
            <span>SIH Demo Video</span>
          </button>
        </div>
      </div>

      {/* Upload Progress Bar (when active) */}
      {analysisStatus === 'UPLOADING' && (
        <div style={{ height: '3px', width: '100%', backgroundColor: 'rgba(56, 189, 248, 0.2)' }}>
          <div style={{ height: '100%', width: `${uploadProgress}%`, backgroundColor: '#38BDF8', transition: 'width 0.2s ease' }} />
        </div>
      )}

      {/* Bottom Video Controls Strip */}
      <div className="video-control-bar">
        <button
          style={{ background: 'none', border: 'none', color: 'inherit', cursor: 'pointer', display: 'flex', alignItems: 'center' }}
          title="Capture Snapshot"
          onClick={() => window.open(`/api/v1/streams/${camId}/snapshot`, '_blank')}
        >
          <CameraIcon size={14} />
        </button>
        <button
          style={{ background: 'none', border: 'none', color: 'inherit', cursor: 'pointer', display: 'flex', alignItems: 'center' }}
          title="Stream Info"
        >
          <Film size={14} />
        </button>
        <button
          style={{ background: 'none', border: 'none', color: 'inherit', cursor: 'pointer', display: 'flex', alignItems: 'center' }}
          title="Fullscreen Mode"
          onClick={handleFullscreen}
        >
          <Maximize2 size={14} />
        </button>
      </div>
    </div>
  );
};
