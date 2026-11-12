import type { ScanWSMessage } from '@/types';

const WS_BASE_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000';
const TERMINAL_STATUSES = ['completed', 'failed', 'cancelled'];

export class WebSocketService {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private pingInterval: number | null = null;
  private scanId: number;
  private manualClose = false;
  private onMessageCallback?: (data: ScanWSMessage) => void;
  private onErrorCallback?: (error: Event) => void;

  constructor(scanId: number) {
    this.scanId = scanId;
  }

  connect(
    onMessage?: (data: ScanWSMessage) => void,
    onError?: (error: Event) => void
  ): void {
    this.onMessageCallback = onMessage;
    this.onErrorCallback = onError;
    this.manualClose = false;

    const wsUrl = `${WS_BASE_URL}/ws/scan/${this.scanId}`;
    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      console.log(`WebSocket connected to scan ${this.scanId}`);
      this.reconnectAttempts = 0;

      // Start ping interval
      this.pingInterval = window.setInterval(() => {
        if (this.ws?.readyState === WebSocket.OPEN) {
          this.ws.send('ping');
        }
      }, 25000);
    };

    this.ws.onmessage = (event) => {
      // The server answers heartbeats with the plain text "pong".
      if (event.data === 'pong') return;

      try {
        const data = JSON.parse(event.data) as ScanWSMessage;
        if (this.onMessageCallback) {
          this.onMessageCallback(data);
        }

        // Terminal states are final: the server closes the socket and the
        // client must not attempt to reconnect.
        if (
          data.type !== 'error' &&
          TERMINAL_STATUSES.includes(data.status)
        ) {
          this.stopReconnecting();
        }
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
      }
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      if (this.onErrorCallback) {
        this.onErrorCallback(error);
      }
    };

    this.ws.onclose = () => {
      console.log('WebSocket closed');
      this.clearPingInterval();

      if (this.manualClose) {
        return;
      }

      // Attempt to reconnect
      if (this.reconnectAttempts < this.maxReconnectAttempts) {
        this.reconnectAttempts++;
        console.log(
          `Reconnecting... (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`
        );
        setTimeout(() => {
          this.connect(this.onMessageCallback, this.onErrorCallback);
        }, this.reconnectDelay * this.reconnectAttempts);
      }
    };
  }

  disconnect(): void {
    this.manualClose = true;
    this.clearPingInterval();

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  send(data: unknown): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }

  private stopReconnecting(): void {
    this.manualClose = true;
  }

  private clearPingInterval(): void {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }
}

export default WebSocketService;
