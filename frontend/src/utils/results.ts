import type { ExportFormat, PortInfo, ScanResult } from '@/types';

export interface ResultFilters {
  query: string;
  portState: string;
  protocol: string;
  service: string;
}

export const EMPTY_RESULT_FILTERS: ResultFilters = {
  query: '',
  portState: 'all',
  protocol: 'all',
  service: 'all',
};

export interface FlatPortRow {
  key: string;
  resultId: number;
  ipAddress: string;
  hostname: string | null;
  osName: string | null;
  port: PortInfo;
}

/** Convert nested scan results into one row per port for tabular display/filtering. */
export function flattenResults(
  results?: ScanResult[] | null
): FlatPortRow[] {
  return (results ?? []).flatMap((result) =>
    (result.ports ?? []).map((port) => ({
      key: `${result.id}-${port.port_number}-${port.protocol}`,
      resultId: result.id,
      ipAddress: result.ip_address,
      hostname: result.hostname ?? null,
      osName: result.os_name ?? null,
      port,
    }))
  );
}

export function serviceLabel(port: PortInfo): string {
  const name = port.service_name?.trim();
  return name ? name : 'unknown';
}

function matchesQuery(row: FlatPortRow, query: string): boolean {
  const haystack = [
    row.ipAddress,
    row.hostname ?? '',
    row.osName ?? '',
    serviceLabel(row.port),
    row.port.service_product ?? '',
    row.port.service_version ?? '',
    row.port.state,
    String(row.port.port_number),
  ]
    .join(' ')
    .toLowerCase();

  return haystack.includes(query);
}

export function filterPortRows(
  rows: FlatPortRow[],
  filters: ResultFilters
): FlatPortRow[] {
  const query = filters.query.trim().toLowerCase();

  return rows.filter((row) => {
    if (filters.portState !== 'all' && row.port.state !== filters.portState) {
      return false;
    }
    if (filters.protocol !== 'all' && row.port.protocol !== filters.protocol) {
      return false;
    }
    if (
      filters.service !== 'all' &&
      serviceLabel(row.port) !== filters.service
    ) {
      return false;
    }
    return query.length === 0 || matchesQuery(row, query);
  });
}

function uniqueSorted(values: string[]): string[] {
  return Array.from(new Set(values)).sort((a, b) => a.localeCompare(b));
}

export function getServiceOptions(rows: FlatPortRow[]): string[] {
  return uniqueSorted(rows.map((row) => serviceLabel(row.port)));
}

export function getProtocolOptions(rows: FlatPortRow[]): string[] {
  return uniqueSorted(rows.map((row) => row.port.protocol));
}

export function countHosts(rows: FlatPortRow[]): number {
  return new Set(rows.map((row) => row.resultId)).size;
}

/** Deterministic download name: `scan-<id>-<YYYYMMDD>.<format>`. */
export function buildExportFilename(
  scanId: number,
  format: ExportFormat,
  now: Date = new Date()
): string {
  const date = now.toISOString().slice(0, 10).replace(/-/g, '');
  return `scan-${scanId}-${date}.${format}`;
}
