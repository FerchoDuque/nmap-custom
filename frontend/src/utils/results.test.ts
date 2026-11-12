import { describe, expect, it } from 'vitest';
import { PortState, type PortInfo, type ScanResult } from '@/types';
import {
  EMPTY_RESULT_FILTERS,
  buildExportFilename,
  countHosts,
  filterPortRows,
  flattenResults,
  getProtocolOptions,
  getServiceOptions,
  serviceLabel,
} from '@/utils/results';

function port(overrides: Partial<PortInfo> = {}): PortInfo {
  return {
    port_number: 80,
    protocol: 'tcp',
    state: PortState.OPEN,
    service_name: 'http',
    ...overrides,
  };
}

function result(overrides: Partial<ScanResult> = {}): ScanResult {
  return {
    id: 1,
    scan_id: 10,
    ip_address: '192.168.1.10',
    hostname: 'router.local',
    is_up: true,
    scanned_at: '2026-11-11T10:00:00',
    ports: [port()],
    ...overrides,
  };
}

const RESULTS: ScanResult[] = [
  result({ id: 1, ip_address: '192.168.1.10' }),
  result({
    id: 2,
    ip_address: '192.168.1.20',
    hostname: null,
    ports: [
      port({ port_number: 53, protocol: 'udp', service_name: 'domain' }),
      port({ port_number: 443, service_name: 'https', state: PortState.FILTERED }),
    ],
  }),
];

describe('flattenResults', () => {
  it('flattens ports with host metadata', () => {
    const rows = flattenResults(RESULTS);

    expect(rows).toHaveLength(3);
    expect(rows[0]).toMatchObject({
      resultId: 1,
      ipAddress: '192.168.1.10',
      hostname: 'router.local',
      port: { port_number: 80 },
    });
    expect(rows[2].key).toBe('2-443-tcp');
  });

  it('handles null or missing results', () => {
    expect(flattenResults(null)).toEqual([]);
    expect(flattenResults(undefined)).toEqual([]);
  });
});

describe('filterPortRows', () => {
  const rows = flattenResults(RESULTS);

  it('returns everything with empty filters', () => {
    expect(filterPortRows(rows, EMPTY_RESULT_FILTERS)).toHaveLength(3);
  });

  it('filters by port state and protocol', () => {
    expect(
      filterPortRows(rows, { ...EMPTY_RESULT_FILTERS, portState: 'open' })
    ).toHaveLength(2);
    expect(
      filterPortRows(rows, { ...EMPTY_RESULT_FILTERS, protocol: 'udp' })
    ).toHaveLength(1);
  });

  it('filters by exact service', () => {
    const filtered = filterPortRows(rows, {
      ...EMPTY_RESULT_FILTERS,
      service: 'https',
    });

    expect(filtered).toHaveLength(1);
    expect(filtered[0].port.port_number).toBe(443);
  });

  it('matches text against host, service, version and port', () => {
    expect(
      filterPortRows(rows, { ...EMPTY_RESULT_FILTERS, query: 'router' })
    ).toHaveLength(1);
    expect(
      filterPortRows(rows, { ...EMPTY_RESULT_FILTERS, query: 'domain' })
    ).toHaveLength(1);
    expect(
      filterPortRows(rows, { ...EMPTY_RESULT_FILTERS, query: '443' })
    ).toHaveLength(1);
    expect(
      filterPortRows(rows, { ...EMPTY_RESULT_FILTERS, query: 'does-not-exist' })
    ).toHaveLength(0);
  });

  it('combines filters', () => {
    expect(
      filterPortRows(rows, {
        ...EMPTY_RESULT_FILTERS,
        query: '192.168.1.20',
        portState: 'open',
      })
    ).toHaveLength(1);
  });
});

describe('options and labels', () => {
  const rows = flattenResults(RESULTS);

  it('labels missing service names as unknown', () => {
    expect(serviceLabel(port({ service_name: undefined }))).toBe('unknown');
    expect(serviceLabel(port({ service_name: '  ' }))).toBe('unknown');
  });

  it('returns unique sorted service and protocol options', () => {
    const extra = [...rows, ...flattenResults([result({ id: 3, ports: [port({ service_name: 'ssh' })] })])];
    expect(getServiceOptions(extra)).toEqual(['domain', 'http', 'https', 'ssh']);
    expect(getProtocolOptions(extra)).toEqual(['tcp', 'udp']);
  });

  it('counts distinct hosts among rows', () => {
    expect(countHosts(rows)).toBe(2);
    expect(countHosts([])).toBe(0);
  });
});

describe('buildExportFilename', () => {
  it('includes scan id, date and format', () => {
    expect(
      buildExportFilename(42, 'csv', new Date('2026-11-12T09:30:00Z'))
    ).toBe('scan-42-20261112.csv');
    expect(
      buildExportFilename(7, 'json', new Date('2026-01-02T00:00:00Z'))
    ).toBe('scan-7-20260102.json');
  });
});
