import { describe, expect, it } from 'vitest';
import { ScanStatus, type ScanSnapshotMessage } from '@/types';
import {
  formatDuration,
  formatStatusLabel,
  getPortStateColor,
  getStatusColor,
  isActiveStatus,
  isTerminalStatus,
  snapshotToScanUpdates,
} from '@/utils/scan';

describe('scan status helpers', () => {
  it('classifies active statuses', () => {
    expect(isActiveStatus(ScanStatus.PENDING)).toBe(true);
    expect(isActiveStatus(ScanStatus.RUNNING)).toBe(true);
    expect(isActiveStatus(ScanStatus.COMPLETED)).toBe(false);
    expect(isActiveStatus('unknown')).toBe(false);
  });

  it('classifies terminal statuses', () => {
    expect(isTerminalStatus(ScanStatus.COMPLETED)).toBe(true);
    expect(isTerminalStatus(ScanStatus.FAILED)).toBe(true);
    expect(isTerminalStatus(ScanStatus.CANCELLED)).toBe(true);
    expect(isTerminalStatus(ScanStatus.RUNNING)).toBe(false);
  });

  it('maps statuses to chip colors', () => {
    expect(getStatusColor(ScanStatus.RUNNING)).toBe('primary');
    expect(getStatusColor(ScanStatus.COMPLETED)).toBe('success');
    expect(getStatusColor(ScanStatus.FAILED)).toBe('error');
    expect(getStatusColor(ScanStatus.CANCELLED)).toBe('warning');
    expect(getStatusColor(ScanStatus.PENDING)).toBe('default');
  });

  it('maps port states to chip colors', () => {
    expect(getPortStateColor('open')).toBe('success');
    expect(getPortStateColor('filtered')).toBe('warning');
    expect(getPortStateColor('closed')).toBe('error');
    expect(getPortStateColor('unknown')).toBe('default');
  });

  it('formats status labels for display', () => {
    expect(formatStatusLabel('running')).toBe('RUNNING');
    expect(formatStatusLabel('tcp_connect')).toBe('TCP CONNECT');
  });
});

describe('formatDuration', () => {
  it('returns a dash without a start time', () => {
    expect(formatDuration(undefined, '2026-11-11T10:00:10Z')).toBe('-');
  });

  it('computes elapsed seconds between timestamps', () => {
    expect(formatDuration('2026-11-11T10:00:00Z', '2026-11-11T10:00:12.45Z')).toBe(
      '12.4s'
    );
  });

  it('returns a dash for invalid dates', () => {
    expect(formatDuration('not-a-date', '2026-11-11T10:00:00Z')).toBe('-');
  });
});

describe('snapshotToScanUpdates', () => {
  it('maps the wire format to scan fields', () => {
    const message: ScanSnapshotMessage = {
      type: 'update',
      scan_id: 3,
      status: ScanStatus.RUNNING,
      progress: 55,
      current_host: '10.0.0.5',
      hosts_scanned: 3,
      hosts_total: 10,
      ports_found: 8,
      error_message: null,
    };

    expect(snapshotToScanUpdates(message)).toEqual({
      status: ScanStatus.RUNNING,
      progress: 55,
      current_host: '10.0.0.5',
      hosts_scanned: 3,
      hosts_total: 10,
      total_ports_found: 8,
      error_message: null,
    });
  });
});
