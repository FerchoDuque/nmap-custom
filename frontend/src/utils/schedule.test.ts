import { describe, expect, it } from 'vitest';
import type { Schedule } from '@/types';
import {
  CRON_PRESETS,
  buildScanConfig,
  emptyScheduleForm,
  formatScheduleTime,
  scheduleToForm,
  summarizeScanConfig,
  validateCronExpression,
  validateScheduleForm,
} from '@/utils/schedule';

describe('validateCronExpression', () => {
  it('accepts standard and preset expressions', () => {
    expect(validateCronExpression('0 3 * * *')).toBeNull();
    expect(validateCronExpression('*/5 * * * *')).toBeNull();
    expect(validateCronExpression('0 0 1,15 * 1-5')).toBeNull();
    CRON_PRESETS.forEach((preset) => {
      expect(validateCronExpression(preset.value)).toBeNull();
    });
  });

  it('requires five fields', () => {
    expect(validateCronExpression('')).toBe('Cron expression is required');
    expect(validateCronExpression('* * * *')).toBe(
      'Cron expression must have 5 fields'
    );
  });

  it('rejects invalid fields and ranges', () => {
    expect(validateCronExpression('60 * * * *')).toBe(
      'Cron minute must be between 0 and 59'
    );
    expect(validateCronExpression('* 24 * * *')).toBe(
      'Cron hour must be between 0 and 23'
    );
    expect(validateCronExpression('* * * * 8')).toBe(
      'Cron day of week must be between 0 and 7'
    );
    expect(validateCronExpression('*/0 * * * *')).toBe(
      'Invalid step in cron minute'
    );
    expect(validateCronExpression('10-5 * * * *')).toBe(
      'Invalid range in cron minute'
    );
    expect(validateCronExpression('abc * * * *')).toBe('Invalid cron minute');
  });
});

describe('formatScheduleTime', () => {
  it('formats backend UTC timestamps without local drift', () => {
    expect(formatScheduleTime('2026-11-11T12:05:00')).toBe(
      '2026-11-11 12:05 UTC'
    );
  });

  it('handles missing or invalid values', () => {
    expect(formatScheduleTime(null)).toBe('—');
    expect(formatScheduleTime(undefined)).toBe('—');
    expect(formatScheduleTime('not-a-date')).toBe('—');
  });
});

describe('summarizeScanConfig', () => {
  it('includes target, scan type and optional port range', () => {
    expect(
      summarizeScanConfig({
        target: '192.168.1.0/24',
        scan_type: 'udp',
        port_range: '53,123',
      })
    ).toBe('192.168.1.0/24 · udp · 53,123');

    expect(summarizeScanConfig({ target: '10.0.0.1' })).toBe(
      '10.0.0.1 · tcp_connect'
    );
  });

  it('never throws on malformed configuration', () => {
    expect(summarizeScanConfig({})).toBe('no target · tcp_connect');
  });
});

describe('schedule form mapping', () => {
  const schedule: Schedule = {
    id: 7,
    name: 'nightly',
    description: 'Nightly recon',
    scan_config: {
      target: '192.168.1.0/24',
      scan_type: 'udp',
      port_range: '53,123',
      service_detection: false,
      os_detection: true,
      aggressive: true,
    },
    cron_expression: '0 3 * * *',
    enabled: true,
    created_at: '2026-11-11T10:00:00',
    updated_at: '2026-11-11T10:00:00',
    last_run_at: null,
    next_run_at: '2026-11-12T03:00:00',
    total_runs: 2,
    successful_runs: 1,
    failed_runs: 1,
  };

  it('maps a schedule and its scan_config into form values', () => {
    expect(scheduleToForm(schedule)).toEqual({
      name: 'nightly',
      description: 'Nightly recon',
      target: '192.168.1.0/24',
      scan_type: 'udp',
      port_range: '53,123',
      cron_expression: '0 3 * * *',
      enabled: true,
      service_detection: false,
      os_detection: true,
      aggressive: true,
    });
  });

  it('builds a scan_config omitting an empty port range', () => {
    const config = buildScanConfig({
      ...emptyScheduleForm(),
      name: 'daily',
      target: ' 10.0.0.0/24 ',
    });

    expect(config).toEqual({
      target: '10.0.0.0/24',
      scan_type: 'tcp_connect',
      service_detection: true,
      os_detection: false,
      aggressive: false,
    });
  });
});

describe('validateScheduleForm', () => {
  it('accepts a complete valid form', () => {
    expect(
      validateScheduleForm({
        ...emptyScheduleForm(),
        name: 'nightly',
        target: '192.168.1.0/24',
        port_range: '1-1000',
      })
    ).toEqual({});
  });

  it('collects field errors', () => {
    expect(
      validateScheduleForm({
        ...emptyScheduleForm(),
        name: '   ',
        target: '999.1.1.1',
        port_range: '90000',
        cron_expression: 'bad cron',
      })
    ).toEqual({
      name: 'Name is required',
      target: 'Invalid IPv4 address',
      portRange: 'Ports must be between 1 and 65535',
      cron: 'Cron expression must have 5 fields',
    });
  });
});
