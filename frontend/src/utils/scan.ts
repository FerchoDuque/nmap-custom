import type { ChipProps } from '@mui/material';
import { ScanStatus, type Scan, type ScanSnapshotMessage } from '@/types';

export const ACTIVE_STATUSES: ScanStatus[] = [ScanStatus.PENDING, ScanStatus.RUNNING];

export const TERMINAL_STATUSES: ScanStatus[] = [
  ScanStatus.COMPLETED,
  ScanStatus.FAILED,
  ScanStatus.CANCELLED,
];

export function isActiveStatus(status: string): boolean {
  return (ACTIVE_STATUSES as string[]).includes(status);
}

export function isTerminalStatus(status: string): boolean {
  return (TERMINAL_STATUSES as string[]).includes(status);
}

export function getStatusColor(status: string): ChipProps['color'] {
  switch (status) {
    case ScanStatus.RUNNING:
      return 'primary';
    case ScanStatus.COMPLETED:
      return 'success';
    case ScanStatus.FAILED:
      return 'error';
    case ScanStatus.CANCELLED:
      return 'warning';
    default:
      return 'default';
  }
}

export function getPortStateColor(state: string): ChipProps['color'] {
  switch (state) {
    case 'open':
      return 'success';
    case 'filtered':
      return 'warning';
    case 'closed':
      return 'error';
    default:
      return 'default';
  }
}

export function formatStatusLabel(status: string): string {
  return status.toUpperCase().replace(/_/g, ' ');
}

/** Elapsed time between two ISO timestamps, e.g. `12.4s`. */
export function formatDuration(
  startedAt?: string | null,
  completedAt?: string | null
): string {
  if (!startedAt) return '-';

  const start = new Date(startedAt).getTime();
  const end = completedAt ? new Date(completedAt).getTime() : Date.now();
  if (Number.isNaN(start) || Number.isNaN(end)) return '-';

  const seconds = Math.max(0, (end - start) / 1000);
  return `${seconds.toFixed(1)}s`;
}

/**
 * Map a WebSocket snapshot to the subset of `Scan` fields it can update.
 * Keeps the wire format (`ports_found`, envelope fields) out of components.
 */
export function snapshotToScanUpdates(message: ScanSnapshotMessage): Partial<Scan> {
  return {
    status: message.status,
    progress: message.progress,
    current_host: message.current_host,
    hosts_scanned: message.hosts_scanned,
    hosts_total: message.hosts_total,
    total_ports_found: message.ports_found,
    error_message: message.error_message,
  };
}
