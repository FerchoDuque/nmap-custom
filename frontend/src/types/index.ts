// Scan types
export enum ScanType {
  TCP_CONNECT = 'tcp_connect',
  TCP_SYN = 'tcp_syn',
  UDP = 'udp',
  COMPREHENSIVE = 'comprehensive',
}

export enum ScanStatus {
  PENDING = 'pending',
  RUNNING = 'running',
  COMPLETED = 'completed',
  FAILED = 'failed',
  CANCELLED = 'cancelled',
}

export enum PortState {
  OPEN = 'open',
  CLOSED = 'closed',
  FILTERED = 'filtered',
  UNKNOWN = 'unknown',
}

// Port information
export interface PortInfo {
  port_number: number;
  protocol: string;
  state: PortState;
  service_name?: string;
  service_product?: string;
  service_version?: string;
  service_extra_info?: string;
  banner?: string;
}

// Scan result for a single host
export interface ScanResult {
  id: number;
  scan_id: number;
  ip_address: string;
  hostname?: string | null;
  mac_address?: string | null;
  is_up: boolean;
  os_name?: string | null;
  os_accuracy?: number | null;
  os_details?: Record<string, unknown> | null;
  latency?: number | null;
  scanned_at: string;
  ports: PortInfo[];
}

// Main scan object
export interface Scan {
  id: number;
  name?: string | null;
  target: string;
  scan_type: ScanType;
  status: ScanStatus;
  port_range?: string | null;
  service_detection: boolean;
  os_detection: boolean;
  aggressive: boolean;
  progress: number;
  current_host?: string | null;
  hosts_total: number;
  hosts_scanned: number;
  created_at: string;
  started_at?: string | null;
  completed_at?: string | null;
  total_hosts_up: number;
  total_ports_found: number;
  error_message?: string | null;
  task_id?: string | null;
  results?: ScanResult[] | null;
}

// Create scan request
export interface ScanCreateRequest {
  name?: string;
  target: string;
  scan_type: ScanType;
  port_range?: string;
  service_detection?: boolean;
  os_detection?: boolean;
  aggressive?: boolean;
}

// Summary shape returned by GET /api/scans (no heavy results payload)
export type ScanSummary = Omit<Scan, 'results'>;

// WebSocket contract (see docs/CONTRACT.md)
export interface ScanSnapshotMessage {
  type: 'status' | 'update';
  scan_id: number;
  status: ScanStatus;
  progress: number;
  current_host?: string | null;
  hosts_scanned: number;
  hosts_total: number;
  ports_found: number;
  error_message?: string | null;
}

export interface ScanErrorMessage {
  type: 'error';
  scan_id: number;
  message: string;
}

export type ScanWSMessage = ScanSnapshotMessage | ScanErrorMessage;

// Schedule types
export interface Schedule {
  id: number;
  name: string;
  description?: string | null;
  scan_config: Record<string, unknown>;
  cron_expression: string;
  enabled: boolean;
  created_at: string;
  updated_at: string;
  last_run_at?: string | null;
  next_run_at?: string | null;
  total_runs: number;
  successful_runs: number;
  failed_runs: number;
}

export interface ScheduleCreateRequest {
  name: string;
  description?: string;
  scan_config: Record<string, unknown>;
  cron_expression: string;
  enabled?: boolean;
}

// Export format
export type ExportFormat = 'json' | 'xml' | 'csv';
