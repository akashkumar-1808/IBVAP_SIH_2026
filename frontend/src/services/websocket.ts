/**
 * Reconnecting WebSocket Telemetry Client
 */

import { TelemetryPacket } from '../types';

export class TelemetryWebSocket {
  private ws: WebSocket | null = null;
  private url: string;
  private onPacketCallback: (packet: TelemetryPacket) => void;
  private onStatusCallback: (status: 'CONNECTED' | 'DISCONNECTED' | 'RECONNECTING') => void;
  private isManualClose = false;
  private reconnectTimeout: number | null = null;

  constructor(
    url: string,
    onPacket: (packet: TelemetryPacket) => void,
    onStatus: (status: 'CONNECTED' | 'DISCONNECTED' | 'RECONNECTING') => void
  ) {
    this.url = url;
    this.onPacketCallback = onPacket;
    this.onStatusCallback = onStatus;
  }

  public connect(): void {
    this.isManualClose = false;
    this.onStatusCallback('RECONNECTING');

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const wsUrl = this.url.startsWith('ws') ? this.url : `${protocol}//${host}${this.url}`;

    try {
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        this.onStatusCallback('CONNECTED');
      };

      this.ws.onmessage = (event) => {
        try {
          const packet: TelemetryPacket = JSON.parse(event.data);
          this.onPacketCallback(packet);
        } catch (e) {
          console.warn('Failed to parse telemetry packet:', e);
        }
      };

      this.ws.onclose = () => {
        this.onStatusCallback('DISCONNECTED');
        if (!this.isManualClose) {
          this.scheduleReconnect();
        }
      };

      this.ws.onerror = () => {
        this.ws?.close();
      };
    } catch (e) {
      this.onStatusCallback('DISCONNECTED');
      this.scheduleReconnect();
    }
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimeout) clearTimeout(this.reconnectTimeout);
    this.reconnectTimeout = window.setTimeout(() => {
      this.connect();
    }, 2000);
  }

  public disconnect(): void {
    this.isManualClose = true;
    if (this.reconnectTimeout) clearTimeout(this.reconnectTimeout);
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.onStatusCallback('DISCONNECTED');
  }
}
