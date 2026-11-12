import type { Schedule } from '@/types';
import { validatePortRange, validateTarget } from '@/utils/validation';

export interface ScheduleFormInput {
  name: string;
  description: string;
  target: string;
  scan_type: string;
  port_range: string;
  cron_expression: string;
  enabled: boolean;
  service_detection: boolean;
  os_detection: boolean;
  aggressive: boolean;
}

export interface ScheduleFormErrors {
  name?: string;
  target?: string;
  portRange?: string;
  cron?: string;
}

export const CRON_PRESETS: Array<{ label: string; value: string }> = [
  { label: 'Every 15 min', value: '*/15 * * * *' },
  { label: 'Hourly', value: '0 * * * *' },
  { label: 'Daily 03:00', value: '0 3 * * *' },
  { label: 'Weekly Mon 03:00', value: '0 3 * * 1' },
];

const FIELD_RANGES: Array<[number, number]> = [
  [0, 59],
  [0, 23],
  [1, 31],
  [1, 12],
  [0, 7],
];

const FIELD_NAMES = ['minute', 'hour', 'day of month', 'month', 'day of week'];

function validateCronField(field: string, index: number): string | null {
  const [min, max] = FIELD_RANGES[index];
  const name = FIELD_NAMES[index];

  for (const part of field.split(',')) {
    if (!part) return `Empty cron ${name}`;

    const [range, step, ...rest] = part.split('/');
    if (rest.length > 0) return `Invalid cron ${name}`;

    if (step !== undefined) {
      if (!/^\d+$/.test(step) || Number(step) === 0) {
        return `Invalid step in cron ${name}`;
      }
    }

    if (range === '*') continue;

    const match = /^(\d+)(?:-(\d+))?$/.exec(range);
    if (!match) return `Invalid cron ${name}`;

    const start = Number(match[1]);
    const end = match[2] ? Number(match[2]) : start;

    if (start < min || start > max || end < min || end > max) {
      return `Cron ${name} must be between ${min} and ${max}`;
    }
    if (end < start) return `Invalid range in cron ${name}`;
  }

  return null;
}

/** Validate a standard 5-field cron expression. Returns an error or null. */
export function validateCronExpression(rawExpression: string): string | null {
  const expression = rawExpression.trim();
  if (!expression) return 'Cron expression is required';

  const fields = expression.split(/\s+/);
  if (fields.length !== 5) return 'Cron expression must have 5 fields';

  for (let index = 0; index < fields.length; index += 1) {
    const error = validateCronField(fields[index], index);
    if (error) return error;
  }

  return null;
}

/** Render a backend UTC timestamp (`YYYY-MM-DDTHH:mm:ss`) without local TZ drift. */
export function formatScheduleTime(value?: string | null): string {
  if (!value) return '—';

  const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/.exec(value);
  if (!match) return '—';

  return `${match[1]}-${match[2]}-${match[3]} ${match[4]}:${match[5]} UTC`;
}

export function scanConfigString(
  config: Record<string, unknown>,
  key: string
): string | undefined {
  const value = config[key];
  return typeof value === 'string' && value.length > 0 ? value : undefined;
}

export function scanConfigBoolean(
  config: Record<string, unknown>,
  key: string,
  fallback: boolean
): boolean {
  const value = config[key];
  return typeof value === 'boolean' ? value : fallback;
}

/** Short, non-throwing summary of a schedule's stored scan configuration. */
export function summarizeScanConfig(config: Record<string, unknown>): string {
  const target = scanConfigString(config, 'target') ?? 'no target';
  const scanType = scanConfigString(config, 'scan_type') ?? 'tcp_connect';
  const portRange = scanConfigString(config, 'port_range');

  return portRange ? `${target} · ${scanType} · ${portRange}` : `${target} · ${scanType}`;
}

export function scanConfigToForm(schedule: Schedule): {
  target: string;
  scan_type: string;
  port_range: string;
  service_detection: boolean;
  os_detection: boolean;
  aggressive: boolean;
} {
  const config = schedule.scan_config ?? {};

  return {
    target: scanConfigString(config, 'target') ?? '',
    scan_type: scanConfigString(config, 'scan_type') ?? 'tcp_connect',
    port_range: scanConfigString(config, 'port_range') ?? '',
    service_detection: scanConfigBoolean(config, 'service_detection', true),
    os_detection: scanConfigBoolean(config, 'os_detection', false),
    aggressive: scanConfigBoolean(config, 'aggressive', false),
  };
}

export function emptyScheduleForm(): ScheduleFormInput {
  return {
    name: '',
    description: '',
    target: '',
    scan_type: 'tcp_connect',
    port_range: '',
    cron_expression: '0 3 * * *',
    enabled: true,
    service_detection: true,
    os_detection: false,
    aggressive: false,
  };
}

export function scheduleToForm(schedule: Schedule): ScheduleFormInput {
  return {
    name: schedule.name,
    description: schedule.description ?? '',
    cron_expression: schedule.cron_expression,
    enabled: schedule.enabled,
    ...scanConfigToForm(schedule),
  };
}

export function buildScanConfig(form: ScheduleFormInput): Record<string, unknown> {
  const config: Record<string, unknown> = {
    target: form.target.trim(),
    scan_type: form.scan_type,
    service_detection: form.service_detection,
    os_detection: form.os_detection,
    aggressive: form.aggressive,
  };

  const portRange = form.port_range.trim();
  if (portRange) config.port_range = portRange;

  return config;
}

export function validateScheduleForm(input: ScheduleFormInput): ScheduleFormErrors {
  const errors: ScheduleFormErrors = {};

  if (!input.name.trim()) errors.name = 'Name is required';

  const targetError = validateTarget(input.target);
  if (targetError) errors.target = targetError;

  const portError = validatePortRange(input.port_range);
  if (portError) errors.portRange = portError;

  const cronError = validateCronExpression(input.cron_expression);
  if (cronError) errors.cron = cronError;

  return errors;
}
