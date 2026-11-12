export interface ScanFormInput {
  target: string;
  port_range?: string | null;
}

export interface ScanFormErrors {
  target?: string;
  portRange?: string;
}

const IPV4 = /^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/;
const IPV6 = /^[0-9a-f:]+$/i;
const HOSTNAME_LABEL = /^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/i;
const PORT_TOKEN = /^(\d{1,5})(?:-(\d{1,5}))?$/;

function isValidIpv4(value: string): boolean {
  const match = IPV4.exec(value);
  if (!match) return false;
  return match.slice(1).every((octet) => Number(octet) <= 255);
}

function isValidHostname(value: string): boolean {
  if (value.length > 253) return false;
  const labels = value.replace(/\.$/, '').split('.');
  return labels.length > 0 && labels.every((label) => HOSTNAME_LABEL.test(label));
}

/** Validate an IP, CIDR range or hostname. Returns an error message or null. */
export function validateTarget(rawTarget: string): string | null {
  const target = rawTarget.trim();
  if (!target) return 'Target is required';

  const [address, prefix, ...rest] = target.split('/');
  if (rest.length > 0) return 'Invalid target format';

  if (prefix !== undefined) {
    if (!/^\d{1,3}$/.test(prefix)) return 'Invalid CIDR prefix';

    if (IPV4.test(address)) {
      if (!isValidIpv4(address)) return 'Invalid IPv4 address';
      const bits = Number(prefix);
      return bits >= 0 && bits <= 32 ? null : 'CIDR prefix must be between 0 and 32';
    }

    if (IPV6.test(address) && address.includes(':')) {
      const bits = Number(prefix);
      return bits >= 0 && bits <= 128 ? null : 'CIDR prefix must be between 0 and 128';
    }

    return 'Invalid CIDR address';
  }

  if (IPV4.test(address)) {
    return isValidIpv4(address) ? null : 'Invalid IPv4 address';
  }

  if (address.includes(':')) {
    return IPV6.test(address) ? null : 'Invalid IPv6 address';
  }

  return isValidHostname(address) ? null : 'Invalid target format';
}

/** Validate a port range such as `1-1000`, `22,80,443` or a mix of both. */
export function validatePortRange(rawRange?: string | null): string | null {
  const range = (rawRange ?? '').trim();
  if (!range) return null;

  for (const rawToken of range.split(',')) {
    const token = rawToken.trim();
    if (!token) return 'Empty port entry';

    const match = PORT_TOKEN.exec(token);
    if (!match) return 'Use ports like 22,80,443 or ranges like 1-1000';

    const start = Number(match[1]);
    const end = match[2] ? Number(match[2]) : start;

    if (start < 1 || start > 65535 || end < 1 || end > 65535) {
      return 'Ports must be between 1 and 65535';
    }
    if (end < start) {
      return 'Invalid port range (end before start)';
    }
  }

  return null;
}

export function validateScanForm(input: ScanFormInput): ScanFormErrors {
  const errors: ScanFormErrors = {};

  const targetError = validateTarget(input.target);
  if (targetError) errors.target = targetError;

  const portError = validatePortRange(input.port_range);
  if (portError) errors.portRange = portError;

  return errors;
}
