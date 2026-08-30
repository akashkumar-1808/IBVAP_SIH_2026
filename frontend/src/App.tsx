import React, { useState, useEffect, useCallback } from 'react';
import { TopSystemBar } from './components/layout/TopSystemBar';
import { SidebarNav } from './components/layout/SidebarNav';
import { BottomStatusBar } from './components/layout/BottomStatusBar';
import { PrimaryVideoPanel } from './components/console/PrimaryVideoPanel';
import { IntelligenceCards } from './components/console/IntelligenceCards';
import { EventTimeline } from './components/console/EventTimeline';
import { EventDetailsPanel } from './components/console/EventDetailsPanel';
import { EvidencePackagePreview } from './components/console/EvidencePackagePreview';
import { ActiveEventQueue } from './components/console/ActiveEventQueue';
import { SectorMapPanel } from './components/console/SectorMapPanel';
import { AddCameraModal } from './components/console/AddCameraModal';

import {
  CameraInfo,
  CameraCalibration,
  EventRecord,
  EvidencePackage,
  TelemetryPacket,
  DemonstrationScenario,
} from './types';

import {
  fetchCameras,
  fetchCameraCalibration,
  fetchEvents,
  fetchEventEvidence,
  fetchScenarios,
  runScenario,
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
  const [scenarios, setScenarios] = useState<DemonstrationScenario[]>([]);
  const [activeScenarioId, setActiveScenarioId] = useState<string>('');
  const [isAddCameraModalOpen, setIsAddCameraModalOpen] = useState<boolean>(false);

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

  // 1. Initial Load: Cameras, Scenarios, Events
  useEffect(() => {
    fetchCameras()
      .then((cams) => {
        setCameras(cams);
        if (cams.length > 0) setSelectedCameraId(cams[0].camera_id);
      })
      .catch((err) => console.warn('Failed to load cameras:', err));

    fetchScenarios()
      .then(setScenarios)
      .catch((err) => console.warn('Failed to load scenarios:', err));

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

      // Auto-select latest critical/high event
      const highEv = packet.active_events.find((e) => e.priority === 'CRITICAL' || e.priority === 'HIGH');
      if (highEv && (!selectedEvent || selectedEvent.id !== highEv.id)) {
        setSelectedEvent(highEv);
      }
    }
  }, [selectedEvent]);

  useEffect(() => {
    const ws = new TelemetryWebSocket(
      '/api/v1/ws/telemetry',
      handleTelemetryPacket,
      setWsStatus
    );
    ws.connect();
    return () => ws.disconnect();
  }, [handleTelemetryPacket]);

  // 4. Handle Event Selection & Evidence Fetch
  const handleSelectEvent = (ev: EventRecord) => {
    setSelectedEvent(ev);
    fetchEventEvidence(ev.id)
      .then(setEvidencePackage)
      .catch(() => setEvidencePackage(null));
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

  // 7. Handle Scenario Run (Jury Replay)
  const handleSelectScenario = async (scId: string) => {
    setActiveScenarioId(scId);
    try {
      await runScenario(scId, 1.0);
    } catch (err) {
      console.warn('Failed to start scenario:', err);
    }
  };

  // 8. Handle Event Acknowledge
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

  return (
    <div className="app-container">
      {/* Top System Bar */}
      <TopSystemBar
        currentSector="SECTOR B-07"
        isLiveMode={wsStatus === 'CONNECTED'}
        cameras={cameras}
        fps={telemetry.fps}
        systemHealth={wsStatus === 'CONNECTED' ? 'HEALTHY' : 'RECONNECTING'}
        scenarios={scenarios}
        activeScenarioId={activeScenarioId}
        onSelectScenario={handleSelectScenario}
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

        {/* Column 2: Center Primary Video & Intelligence Deck */}
        <section className="center-deck">
          {/* Primary Live/Replay Video Player with SVG Overlays */}
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
            onOpenAddCamera={() => setIsAddCameraModalOpen(true)}
          />

          {/* 5 Core Intelligence Pillars Deck */}
          <IntelligenceCards
            environment={telemetry.environment}
            borderTrack={telemetry.border_track}
            spatialState={telemetry.spatial_states[0]}
            behaviors={telemetry.behavior_primitives}
            activeEvent={telemetry.active_events[0] || selectedEvent}
          />

          {/* Bottom Forensic Row: Timeline | Details & "Why This Event?" | Evidence Package */}
          <div className="bottom-forensic-row">
            <EventTimeline selectedEvent={selectedEvent} />
            <EventDetailsPanel event={selectedEvent} onAcknowledge={handleAcknowledge} />
            <EvidencePackagePreview evidencePackage={evidencePackage} event={selectedEvent} />
          </div>
        </section>

        {/* Column 3: Right Panel: Active Event Queue & Sector Map */}
        <section className="right-panel">
          <ActiveEventQueue
            events={events}
            selectedEventId={selectedEvent?.id}
            onSelectEvent={handleSelectEvent}
          />
          <SectorMapPanel cameras={cameras} borderTrack={telemetry.border_track} />
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
