// @vitest-environment jsdom
import '@testing-library/jest-dom/vitest';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import Dashboard from '@/components/Dashboard/Dashboard';
import { scanApi } from '@/services/api';
import { useScanStore } from '@/store/scanStore';
import type { Scan } from '@/types';
import { ScanStatus, ScanType } from '@/types';

vi.mock('@/services/api', () => ({
  scanApi: {
    listScans: vi.fn(),
    createScan: vi.fn(),
  },
}));

const completedScan: Scan = {
  id: 7,
  name: 'Baseline lab',
  target: '192.168.1.0/24',
  scan_type: ScanType.TCP_CONNECT,
  status: ScanStatus.COMPLETED,
  port_range: '1-1000',
  service_detection: true,
  os_detection: false,
  aggressive: false,
  progress: 100,
  current_host: null,
  hosts_total: 10,
  hosts_scanned: 10,
  created_at: '2026-11-13T10:00:00',
  started_at: '2026-11-13T10:00:00',
  completed_at: '2026-11-13T10:01:00',
  total_hosts_up: 4,
  total_ports_found: 12,
  error_message: null,
  task_id: 'task-7',
};

function renderDashboard() {
  return render(
    <MemoryRouter>
      <Dashboard />
    </MemoryRouter>
  );
}

describe('Dashboard', () => {
  afterEach(cleanup);

  beforeEach(() => {
    useScanStore.setState({
      scans: [],
      activeScans: [],
      selectedScan: null,
      isLoading: false,
      error: null,
    });
    vi.mocked(scanApi.listScans).mockReset();
    vi.mocked(scanApi.createScan).mockReset();
    vi.mocked(scanApi.listScans).mockResolvedValue([completedScan]);
  });

  it('renders recent scans returned by the API', async () => {
    renderDashboard();

    expect(await screen.findByText('Baseline lab')).toBeInTheDocument();
    expect(screen.getByText(/192\.168\.1\.0\/24/)).toBeInTheDocument();
    expect(screen.getByText('COMPLETED')).toBeInTheDocument();
    expect(scanApi.listScans).toHaveBeenCalledWith({ limit: 20 });
  });

  it('shows the empty state when there are no scans', async () => {
    vi.mocked(scanApi.listScans).mockResolvedValue([]);
    renderDashboard();

    expect(await screen.findByText('> NO_SCANS_DETECTED')).toBeInTheDocument();
  });

  it('creates a scan from the dialog and reloads the list', async () => {
    const user = userEvent.setup();
    vi.mocked(scanApi.createScan).mockResolvedValue({
      ...completedScan,
      id: 8,
      status: ScanStatus.PENDING,
      name: null,
    });

    renderDashboard();
    await screen.findByText('Baseline lab');

    await user.click(screen.getByRole('button', { name: /new scan/i }));
    await user.type(
      screen.getByRole('textbox', { name: /target/i }),
      '192.168.1.10'
    );
    await user.click(screen.getByRole('button', { name: /start scan/i }));

    await waitFor(() =>
      expect(scanApi.createScan).toHaveBeenCalledWith(
        expect.objectContaining({
          target: '192.168.1.10',
          scan_type: ScanType.TCP_CONNECT,
        })
      )
    );
    await waitFor(() => expect(scanApi.listScans).toHaveBeenCalledTimes(2));
    await waitFor(() =>
      expect(screen.queryByText('> NEW_SCAN')).not.toBeInTheDocument()
    );
  });
});
