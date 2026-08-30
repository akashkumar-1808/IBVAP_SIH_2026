/**
 * IBVAP Operator Console REST API Client
 */

import {
  CameraInfo,
  CameraCalibration,
  EventRecord,
  EvidencePackage,
  DemonstrationScenario,
} from '../types';

const API_BASE = '/api/v1';

export async function fetchCameras(): Promise<CameraInfo[]> {
  const res = await fetch(`${API_BASE}/cameras`);
  if (!res.ok) throw new Error(`Failed to fetch cameras: ${res.statusText}`);
  return res.json();
}

export async function connectCamera(params: {
  camera_id: string;
  name: string;
  rtsp_url: string;
  sector_id?: string;
  sector_name?: string;
  device?: string;
}): Promise<{ status: string; message: string; camera: CameraInfo }> {
  const res = await fetch(`${API_BASE}/cameras/connect`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Failed to connect RTSP camera');
  }
  return res.json();
}

export async function disconnectCamera(cameraId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/cameras/${cameraId}/disconnect`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error(`Failed to disconnect camera ${cameraId}`);
  return res.json();
}

export async function deleteCamera(cameraId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/cameras/${cameraId}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error(`Failed to remove camera ${cameraId}`);
  return res.json();
}

export async function fetchCameraCalibration(cameraId: string): Promise<CameraCalibration> {
  const res = await fetch(`${API_BASE}/cameras/${cameraId}/calibration`);
  if (!res.ok) throw new Error(`Failed to fetch calibration for ${cameraId}`);
  return res.json();
}

export async function fetchEvents(params?: {
  cameraId?: string;
  priority?: string;
  limit?: number;
}): Promise<EventRecord[]> {
  const query = new URLSearchParams();
  if (params?.cameraId) query.set('camera_id', params.cameraId);
  if (params?.priority) query.set('priority', params.priority);
  if (params?.limit) query.set('limit', String(params.limit));

  const res = await fetch(`${API_BASE}/events?${query.toString()}`);
  if (!res.ok) throw new Error(`Failed to fetch events: ${res.statusText}`);
  return res.json();
}

export async function fetchEvent(eventId: string): Promise<EventRecord> {
  const res = await fetch(`${API_BASE}/events/${eventId}`);
  if (!res.ok) throw new Error(`Failed to fetch event ${eventId}`);
  return res.json();
}

export async function fetchEventEvidence(eventId: string): Promise<EvidencePackage> {
  const res = await fetch(`${API_BASE}/events/${eventId}/evidence`);
  if (!res.ok) throw new Error(`Failed to fetch evidence for event ${eventId}`);
  return res.json();
}

export async function verifyEvidenceIntegrity(evidenceId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/evidence/${evidenceId}/verify`);
  if (!res.ok) throw new Error(`Failed to verify evidence ${evidenceId}`);
  return res.json();
}

export async function acknowledgeEvent(eventId: string, operatorName: string = 'Operator'): Promise<any> {
  const res = await fetch(`${API_BASE}/events/${eventId}/acknowledge`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ acknowledged_by: operatorName }),
  });
  if (!res.ok) throw new Error(`Failed to acknowledge event ${eventId}`);
  return res.json();
}

export async function fetchScenarios(): Promise<DemonstrationScenario[]> {
  const res = await fetch(`${API_BASE}/scenarios`);
  if (!res.ok) throw new Error(`Failed to fetch scenarios`);
  return res.json();
}

export async function runScenario(scenarioId: string, speedFactor: number = 1.0): Promise<any> {
  const res = await fetch(`${API_BASE}/scenarios/${scenarioId}/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ speed_factor: speedFactor }),
  });
  if (!res.ok) throw new Error(`Failed to run scenario ${scenarioId}`);
  return res.json();
}

export function getEvidenceFileUrl(evidenceId: string): string {
  return `${API_BASE}/evidence/${evidenceId}/file`;
}

export function getStreamUrl(cameraId: string): string {
  return `${API_BASE}/streams/${cameraId}/live`;
}
