// @vitest-environment jsdom
import '@testing-library/jest-dom/vitest';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import ScanDetails from '@/components/ScanDetails/ScanDetails';
import { scanApi } from '@/services/api';
import type { Scan, ScanSnapshotMessage } from '@/types';
import { PortState, ScanStatus, ScanType } from '@/types';

const { wsInstances } = vi.hoisted(() => ({
  wsInstances: [] as Array<{
    scanId: number;
    onMessage?: (message: ScanSnapshotMessage) => void;
    disconnect: ReturnType<typeof vi.fn>;
  }>,
}));

vi.mock('@/services/api', () => ({
  scanApi: {
    getScan: vi.fn(),
    updateScan: vi.fn(),
  },
}));

vi.mock('@/services/websocket', () => ({
  WebSocketService: class {
    scanId: number;
    onMessage?: (message: ScanSnapshotMessage) => void;
    disconnect = vi.fn();

    constructor(scanId: number) {
      this.scanId = scanId;
      wsInstances.push(this);
    }

    connect = vi.fn(
      (onMessage: (message: ScanSnapshotMessage) => void) => {
        this.onMessage = onMessage;
      }
    );
  },
}));

const runningScan: Scan = {
  id: 42,
  name: 'Authorized lab',
  target: '192.168.1.0/24',
  scan_type: ScanType.TCP_CONNECT,
  status: ScanStatus.RUNNING,
  port_range: '1-1000',
  service_detection: true,
  os_detection: false,
  aggressive: false,
  progress: 40,
  current_host: '192.168.1.10',
  hosts_total: 10,
  hosts_scanned: 4,
  created_at: '2026-11-13T10:00:00',
  started_at: '2026-11-13T10:00:00',
  completed_at: null,
  total_hosts_up: 4,
  total_ports_found: 7,
  error_message: null,
  task_id: 'task-42',
  results: [],
};

function renderDetails() {
  return render(
    <MemoryRouter initialEntries={['/scan/42']}>
      <Routes>
        <Route path="/scan/:id" element={<ScanDetails />} />
      </Routes>
    </MemoryRouter>
  );
}

function snapshot(
  overrides: Partial<ScanSnapshotMessage> = {}
): ScanSnapshotMessage {
  return {
    type: 'update',
    scan_id: 42,
    status: ScanStatus.RUNNING,
    progress: 60,
    current_host: '192.168.1.20',
    hosts_scanned: 6,
    hosts_total: 10,
    ports_found: 9,
    error_message: null,
    ...overrides,
  };
}

describe('ScanDetails', () => {
  afterEach(cleanup);

  beforeEach(() => {
    wsInstances.length = 0;
    vi.mocked(scanApi.getScan).mockReset();
    vi.mocked(scanApi.updateScan).mockReset();
    vi.mocked(scanApi.getScan).mockResolvedValue(runningScan);
  });

  it('loads the scan and connects the realtime socket', async () => {
    renderDetails();

    expect(await screen.findByText('> SCAN_DETAILS')).toBeInTheDocument();
    expect(screen.getByText('40%')).toBeInTheDocument();
    expect(screen.getByText(/192\.168\.1\.10/)).toBeInTheDocument();
    expect(scanApi.getScan).toHaveBeenCalledWith(42);
    expect(wsInstances).toHaveLength(1);
    expect(wsInstances[0].scanId).toBe(42);
  });

  it('applies progress updates from the WebSocket', async () => {
    renderDetails();
    await screen.findByText('> SCAN_DETAILS');

    act(() => {
      wsInstances[0].onMessage?.(snapshot());
    });

    expect(await screen.findByText('60%')).toBeInTheDocument();
    expect(screen.getByText(/192\.168\.1\.20/)).toBeInTheDocument();
  });

  it('reloads the final results and disconnects on terminal status', async () => {
    const completed: Scan = {
      ...runningScan,
      status: ScanStatus.COMPLETED,
      progress: 100,
      completed_at: '2026-11-13T10:01:00',
      results: [
        {
          id: 1,
          scan_id: 42,
          ip_address: '192.168.1.10',
          hostname: 'router.local',
          is_up: true,
          scanned_at: '2026-11-13T10:01:00',
          ports: [
            {
              port_number: 443,
              protocol: 'tcp',
              state: PortState.OPEN,
              service_name: 'https',
            },
          ],
        },
      ],
    };
    vi.mocked(scanApi.getScan)
      .mockResolvedValueOnce(runningScan)
      .mockResolvedValueOnce(completed);

    renderDetails();
    await screen.findByText('> SCAN_DETAILS');

    act(() => {
      wsInstances[0].onMessage?.(
        snapshot({ status: ScanStatus.COMPLETED, progress: 100 })
      );
    });

    await waitFor(() => expect(scanApi.getScan).toHaveBeenCalledTimes(2));
    expect(await screen.findByText('router.local')).toBeInTheDocument();
    expect(wsInstances[0].disconnect).toHaveBeenCalled();
    expect(screen.queryByRole('button', { name: /cancel scan/i })).not.toBeInTheDocument();
  });

  it('cancels an active scan and reloads its state', async () => {
    const user = userEvent.setup();
    vi.mocked(scanApi.updateScan).mockResolvedValue({
      ...runningScan,
      status: ScanStatus.CANCELLED,
    });
    vi.mocked(scanApi.getScan)
      .mockResolvedValueOnce(runningScan)
      .mockResolvedValueOnce({ ...runningScan, status: ScanStatus.CANCELLED });

    renderDetails();
    await screen.findByText('> SCAN_DETAILS');

    await user.click(screen.getByRole('button', { name: /cancel scan/i }));

    await waitFor(() =>
      expect(scanApi.updateScan).toHaveBeenCalledWith(42, {
        status: 'cancelled',
      })
    );
    await waitFor(() => expect(scanApi.getScan).toHaveBeenCalledTimes(2));
    expect(wsInstances[0].disconnect).toHaveBeenCalled();
    expect(screen.queryByRole('button', { name: /cancel scan/i })).not.toBeInTheDocument();
  });
});
