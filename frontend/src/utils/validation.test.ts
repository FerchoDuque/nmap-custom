import { describe, expect, it } from 'vitest';
import { validatePortRange, validateScanForm, validateTarget } from '@/utils/validation';

describe('validateTarget', () => {
  it('requires a target', () => {
    expect(validateTarget('   ')).toBe('Target is required');
  });

  it('accepts valid IPv4 addresses and CIDR ranges', () => {
    expect(validateTarget('192.168.1.1')).toBeNull();
    expect(validateTarget('10.0.0.0/8')).toBeNull();
    expect(validateTarget('0.0.0.0/0')).toBeNull();
  });

  it('rejects invalid IPv4 addresses and prefixes', () => {
    expect(validateTarget('999.1.1.1')).toBe('Invalid IPv4 address');
    expect(validateTarget('10.0.0.0/33')).toBe(
      'CIDR prefix must be between 0 and 32'
    );
    expect(validateTarget('10.0.0.0/abc')).toBe('Invalid CIDR prefix');
  });

  it('accepts hostnames and localhost', () => {
    expect(validateTarget('localhost')).toBeNull();
    expect(validateTarget('router.local')).toBeNull();
    expect(validateTarget('scan-01.example.com')).toBeNull();
  });

  it('rejects malformed hostnames', () => {
    expect(validateTarget('-bad.example.com')).toBe('Invalid target format');
    expect(validateTarget('bad..example.com')).toBe('Invalid target format');
    expect(validateTarget('bad_host')).toBe('Invalid target format');
  });

  it('accepts basic IPv6 and rejects malformed IPv6', () => {
    expect(validateTarget('::1')).toBeNull();
    expect(validateTarget('2001:db8::/32')).toBeNull();
    expect(validateTarget('2001:db8::/129')).toBe(
      'CIDR prefix must be between 0 and 128'
    );
    expect(validateTarget('gggg::1')).toBe('Invalid IPv6 address');
  });
});

describe('validatePortRange', () => {
  it('allows an empty range (defaults apply)', () => {
    expect(validatePortRange('')).toBeNull();
    expect(validatePortRange(undefined)).toBeNull();
  });

  it('accepts single ports, lists and ranges', () => {
    expect(validatePortRange('22,80,443')).toBeNull();
    expect(validatePortRange('1-1000')).toBeNull();
    expect(validatePortRange('22,100-200,443')).toBeNull();
  });

  it('rejects malformed or out-of-range ports', () => {
    expect(validatePortRange('0-100')).toBe('Ports must be between 1 and 65535');
    expect(validatePortRange('100-50')).toBe('Invalid port range (end before start)');
    expect(validatePortRange('22,,80')).toBe('Empty port entry');
    expect(validatePortRange('abc')).toBe(
      'Use ports like 22,80,443 or ranges like 1-1000'
    );
  });
});

describe('validateScanForm', () => {
  it('returns no errors for a valid form', () => {
    expect(
      validateScanForm({ target: '192.168.1.0/24', port_range: '1-1000' })
    ).toEqual({});
  });

  it('collects field errors', () => {
    expect(validateScanForm({ target: '', port_range: '90000' })).toEqual({
      target: 'Target is required',
      portRange: 'Ports must be between 1 and 65535',
    });
  });
});
