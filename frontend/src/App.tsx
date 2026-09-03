import React, { useState, useEffect, useCallback, useRef } from 'react';
import { TopSystemBar } from './components/layout/TopSystemBar';
import { SidebarNav } from './components/layout/SidebarNav';
import { BottomStatusBar } from './components/layout/BottomStatusBar';
import { PrimaryVideoPanel } from './components/console/PrimaryVideoPanel';
import { IntelligenceCards } from './components/console/IntelligenceCards';
import { EventTimeline } from './components/console/EventTimeline';
import { EventDetailsPanel } from './components/console/EventDetailsPanel';
import { EvidencePackagePreview } from './components/console/EvidencePackagePreview';
import { ActiveEventQueue } from './components/console/ActiveEventQueue';
import { ActiveSecurityEventBanner } from './components/console/ActiveSecurityEventBanner';
import { AddCameraModal } from './components/console/AddCameraModal';

import {
  CameraInfo,
  CameraCalibration,
  EventRecord,
  EvidencePackage,
  TelemetryPacket,
} from './types';

import {
  fetchCameras,
  fetchCameraCalibration,
  fetchEvents,
  fetchEventEvidence,
  acknowledgeEvent,
  disconnectCamera,
} from './services/api';

import { TelemetryWebSocket } from './services/websocket';

export const App: React.FC = () => {
  const [cameras, setCameras] = useState<CameraInfo[]>([]);
  const [selectedCameraId, setSelectedCameraId] = useState<string>('');
  const [calibration, setCalibration] = useState<CameraCalibration | null>(null);
  const [events, setEvents] = useState<EventRecord[]>([]);
  const [selectedEvent, setSelectedEvent] = useState<EventRecord | null>(null);
  const [evidencePackage, setEvidencePackage] = useState<EvidencePackage | null>(null);
  const [isAddCameraModalOpen, setIsAddCameraModalOpen] = useState<boolean>(false);

  // Deduplication ref for high priority alert selection
  const lastAlertedEventIdRef = useRef<string | null>(null);

  // Real-time live telemetry state from WebSocket
  const [telemetry, setTelemetry] = useState<TelemetryPacket>({
    camera_id: '',
    timestamp_utc: new Date().toISOString(),
    fps: 0.0,
    is_calibrated: true,
    tracks: [],
    spatial_states: [],
    behavior_primitives: [],
    active_events: [],
  });

  const [wsStatus, setWsStatus] = useState<'CONNECTED' | 'DISCONNECTED' | 'RECONNECTING'>('RECONNECTING');

  // 1. Initial Load: Cameras, Events
  useEffect(() => {
    fetchCameras()
      .then((cams) => {
        setCameras(cams);
        if (cams.length > 0) setSelectedCameraId(cams[0].camera_id);
      })
      .catch((err) => console.warn('Failed to load cameras:', err));

    fetchEvents()
      .then((evList) => {
        setEvents(evList);
        if (evList.length > 0) {
          setSelectedEvent(evList[0]);
          fetchEventEvidence(evList[0].id)
            .then(setEvidencePackage)
            .catch(() => {});
        }
      })
      .catch(() => {});
  }, []);

  // 2. Load Calibration for selected camera
  useEffect(() => {
    if (!selectedCameraId) {
      setCalibration(null);
      return;
    }
    fetchCameraCalibration(selectedCameraId)
      .then(setCalibration)
      .catch(() => setCalibration(null));
  }, [selectedCameraId]);

  // 3. Connect to Real-Time Telemetry WebSocket
  const handleTelemetryPacket = useCallback((packet: TelemetryPacket) => {
    setTelemetry(packet);
    if (packet.active_events && packet.active_events.length > 0) {
      setEvents((prev) => {
        const updated = [...prev];
        packet.active_events.forEach((newEv) => {
          const idx = updated.findIndex((e) => e.id === newEv.id);
          if (idx >= 0) updated[idx] = newEv;
          else updated.unshift(newEv);
        });
        return updated;
      });

      // Deduplicated auto-selection of newest high/critical event
      const highEv = packet.active_events.find(
        (e) => e.priority === 'CRITICAL' || e.priority === 'HIGH'
      );
      if (highEv && highEv.id !== lastAlertedEventIdRef.current) {
        lastAlertedEventIdRef.current = highEv.id;
        setSelectedEvent(highEv);
      }
    }
  }, []);

  useEffect(() => {
    const ws = new TelemetryWebSocket(
      '/api/v1/ws/telemetry',
      handleTelemetryPacket,
      setWsStatus
    );
    ws.connect();
    return () => ws.disconnect();
  }, [handleTelemetryPacket]);

  // 4. Automatically fetch evidence package whenever selectedEvent changes
  useEffect(() => {
    if (selectedEvent?.id) {
      fetchEventEvidence(selectedEvent.id)
        .then(setEvidencePackage)
        .catch(() => setEvidencePackage(null));
    } else {
      setEvidencePackage(null);
    }
  }, [selectedEvent?.id]);

  const handleSelectEvent = (ev: EventRecord) => {
    setSelectedEvent(ev);
  };

  // 5. Handle Camera Connection Callback
  const handleCameraConnected = (newCamera: CameraInfo) => {
    setCameras((prev) => {
      const idx = prev.findIndex((c) => c.camera_id === newCamera.camera_id);
      if (idx >= 0) {
        const updated = [...prev];
        updated[idx] = newCamera;
        return updated;
      }
      return [...prev, newCamera];
    });
    setSelectedCameraId(newCamera.camera_id);
  };

  // 6. Handle Camera Disconnect
  const handleDisconnectCamera = async (camId: string) => {
    try {
      await disconnectCamera(camId);
      setCameras((prev) => prev.filter((c) => c.camera_id !== camId));
      if (selectedCameraId === camId) {
        const remaining = cameras.filter((c) => c.camera_id !== camId);
        setSelectedCameraId(remaining.length > 0 ? remaining[0].camera_id : '');
      }
    } catch (err) {
      console.warn('Failed to disconnect camera:', err);
    }
  };

  // 7. Handle Event Acknowledge
  const handleAcknowledge = async (eventId: string) => {
    try {
      await acknowledgeEvent(eventId, 'Operator');
      setEvents((prev) =>
        prev.map((e) => (e.id === eventId ? { ...e, status: 'RESOLVED' as const } : e))
      );
    } catch (err) {
      console.warn('Failed to acknowledge event:', err);
    }
  };

  const selectedCam = cameras.find((c) => c.camera_id === selectedCameraId);
  const activeAlertEvent = telemetry.active_events.find(
    (e) => e.priority === 'CRITICAL' || e.priority === 'HIGH'
  ) || (selectedEvent && (selectedEvent.priority === 'CRITICAL' || selectedEvent.priority === 'HIGH') ? selectedEvent : null);

  return (
    <div className="app-container">
      {/* Top System Bar */}
      <TopSystemBar
        currentSector="SECTOR B-07"
        isLiveMode={wsStatus === 'CONNECTED'}
        camera={selectedCam}
        cameraTelemetry={telemetry.camera}
        environment={telemetry.environment}
        fps={telemetry.fps}
        systemHealth={wsStatus === 'CONNECTED' ? 'HEALTHY' : 'RECONNECTING'}
      />

      {/* Main Command Console 3-Column Grid */}
      <main className="console-grid">
        {/* Column 1: Left Navigation & Camera Network */}
        <SidebarNav
          cameras={cameras}
          selectedCameraId={selectedCameraId}
          onSelectCamera={setSelectedCameraId}
          onOpenAddCamera={() => setIsAddCameraModalOpen(true)}
          onDisconnectCamera={handleDisconnectCamera}
          events={events}
        />

        {/* Column 2: Center Primary Video & Forensic Deck */}
        <section className="center-deck">
          {/* Prominent Real Active Security Event Alert (Driven by real EventRecord) */}
          {activeAlertEvent && (
            <ActiveSecurityEventBanner
              event={activeAlertEvent}
              onSelectEvent={handleSelectEvent}
              onAcknowledge={handleAcknowledge}
            />
          )}

          {/* Primary Live Video Player with OpenCV HUD stream */}
          <PrimaryVideoPanel
            cameraId={selectedCameraId}
            cameraName={selectedCam?.name || 'No Active Camera'}
            fps={telemetry.fps}
            environment={telemetry.environment}
            calibration={calibration}
            tracks={telemetry.tracks}
            spatialStates={telemetry.spatial_states}
            behaviors={telemetry.behavior_primitives}
            activeEvents={telemetry.active_events}
            cameraTelemetry={telemetry.camera}
            onOpenAddCamera={() => setIsAddCameraModalOpen(true)}
          />

          {/* Bottom Forensic Row: Chronological Timeline | Details & "Why This Event?" | Evidence Package */}
          <div className="bottom-forensic-row">
            <EventTimeline
              events={events}
              selectedEvent={selectedEvent}
              onSelectEvent={handleSelectEvent}
            />
            <EventDetailsPanel
              event={selectedEvent}
              onAcknowledge={handleAcknowledge}
            />
            <EvidencePackagePreview
              evidencePackage={evidencePackage}
              event={selectedEvent}
            />
          </div>
        </section>

        {/* Column 3: Right Panel: Active Event Queue & 6 Intelligence Pillars */}
        <section className="right-panel" style={{ display: 'flex', flexDirection: 'column', gap: '10px', overflowY: 'auto' }}>
          {/* Active Security Incident Queue */}
          <ActiveEventQueue
            events={events}
            selectedEventId={selectedEvent?.id}
            onSelectEvent={handleSelectEvent}
          />

          {/* 6 Authoritative Intelligence Pillars from Telemetry */}
          <IntelligenceCards
            environment={telemetry.environment}
            tracks={telemetry.tracks}
            selectedTrack={telemetry.tracks.length > 0 ? telemetry.tracks[0] : null}
            spatialStates={telemetry.spatial_states}
            behaviors={telemetry.behavior_primitives}
            activeEvent={telemetry.active_events[0] || selectedEvent}
          />
        </section>
      </main>

      {/* Bottom Footer Status Strip */}
      <BottomStatusBar />

      {/* Connect RTSP Camera Modal */}
      <AddCameraModal
        isOpen={isAddCameraModalOpen}
        onClose={() => setIsAddCameraModalOpen(false)}
        onCameraConnected={handleCameraConnected}
      />
    </div>
  );
};

export default App;
