import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { WebSocketService } from '@/services/websocket';
import { ScanStatus, type ScanSnapshotMessage } from '@/types';

type Listener = ((event: Event) => void) | null;

class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;
  static instances: MockWebSocket[] = [];

  url: string;
  readyState = MockWebSocket.CONNECTING;
  sent: string[] = [];
  onopen: Listener = null;
  onmessage: Listener = null;
  onerror: Listener = null;
  onclose: Listener = null;

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
  }

  open(): void {
    this.readyState = MockWebSocket.OPEN;
    this.onopen?.({} as Event);
  }

  message(data: string): void {
    this.onmessage?.({ data } as MessageEvent);
  }

  close(): void {
    this.readyState = MockWebSocket.CLOSED;
    this.onclose?.({} as Event);
  }

  send(data: string): void {
    this.sent.push(data);
  }
}

const statusMessage: ScanSnapshotMessage = {
  type: 'status',
  scan_id: 42,
  status: ScanStatus.RUNNING,
  progress: 40,
  current_host: '192.168.1.10',
  hosts_scanned: 2,
  hosts_total: 5,
  ports_found: 7,
  error_message: null,
};

describe('WebSocketService', () => {
  beforeEach(() => {
    MockWebSocket.instances = [];
    vi.useFakeTimers();
    vi.stubGlobal('WebSocket', MockWebSocket);
    vi.stubGlobal('window', globalThis);
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it('connects to the scan endpoint and sends heartbeats', () => {
    const service = new WebSocketService(42);
    service.connect(vi.fn());

    const socket = MockWebSocket.instances[0];
    expect(socket.url).toBe('ws://localhost:8000/ws/scan/42');

    socket.open();
    vi.advanceTimersByTime(25000);
    expect(socket.sent).toEqual(['ping']);

    service.disconnect();
  });

  it('forwards parsed status messages to the callback', () => {
    const onMessage = vi.fn();
    const service = new WebSocketService(42);
    service.connect(onMessage);

    const socket = MockWebSocket.instances[0];
    socket.open();
    socket.message(JSON.stringify(statusMessage));

    expect(onMessage).toHaveBeenCalledWith(statusMessage);
    service.disconnect();
  });

  it('ignores plain-text pong heartbeats', () => {
    const onMessage = vi.fn();
    const service = new WebSocketService(42);
    service.connect(onMessage);

    const socket = MockWebSocket.instances[0];
    socket.open();
    socket.message('pong');

    expect(onMessage).not.toHaveBeenCalled();
    service.disconnect();
  });

  it('does not reconnect after a terminal status closes the socket', () => {
    const service = new WebSocketService(42);
    service.connect(vi.fn());

    const socket = MockWebSocket.instances[0];
    socket.open();
    socket.message(
      JSON.stringify({
        ...statusMessage,
        type: 'update',
        status: 'completed',
        progress: 100,
      })
    );
    socket.close();

    vi.advanceTimersByTime(10000);
    expect(MockWebSocket.instances).toHaveLength(1);
    service.disconnect();
  });

  it('does not reconnect after an intentional disconnect', () => {
    const service = new WebSocketService(42);
    service.connect(vi.fn());

    MockWebSocket.instances[0].open();
    service.disconnect();

    vi.advanceTimersByTime(10000);
    expect(MockWebSocket.instances).toHaveLength(1);
  });

  it('reconnects after an unexpected close', () => {
    const service = new WebSocketService(42);
    service.connect(vi.fn());

    const socket = MockWebSocket.instances[0];
    socket.open();
    socket.close();

    vi.advanceTimersByTime(1000);
    expect(MockWebSocket.instances).toHaveLength(2);
    expect(MockWebSocket.instances[1].url).toBe('ws://localhost:8000/ws/scan/42');

    service.disconnect();
  });
});
