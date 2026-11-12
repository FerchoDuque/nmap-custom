import axios from 'axios';
import type {
  Scan,
  ScanCreateRequest,
  Schedule,
  ScheduleCreateRequest,
  ExportFormat,
} from '@/types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Create axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// ============================================================================
// Scan API
// ============================================================================

export const scanApi = {
  // Create a new scan
  createScan: async (data: ScanCreateRequest): Promise<Scan> => {
    const response = await api.post<Scan>('/api/scans', data);
    return response.data;
  },

  // List all scans
  listScans: async (params?: {
    skip?: number;
    limit?: number;
    status_filter?: string;
  }): Promise<Scan[]> => {
    const response = await api.get<Scan[]>('/api/scans', { params });
    return response.data;
  },

  // Get scan by ID
  getScan: async (scanId: number): Promise<Scan> => {
    const response = await api.get<Scan>(`/api/scans/${scanId}`);
    return response.data;
  },

  // Update scan
  updateScan: async (
    scanId: number,
    data: { name?: string; status?: string }
  ): Promise<Scan> => {
    const response = await api.patch<Scan>(`/api/scans/${scanId}`, data);
    return response.data;
  },

  // Delete scan
  deleteScan: async (scanId: number): Promise<void> => {
    await api.delete(`/api/scans/${scanId}`);
  },

  // Export scan results
  exportScan: async (scanId: number, format: ExportFormat): Promise<Blob> => {
    const response = await api.post(
      `/api/scans/${scanId}/export`,
      { format },
      { responseType: 'blob' }
    );
    return response.data;
  },
};

// ============================================================================
// Schedule API
// ============================================================================

export const scheduleApi = {
  // Create a new schedule
  createSchedule: async (data: ScheduleCreateRequest): Promise<Schedule> => {
    const response = await api.post<Schedule>('/api/schedules', data);
    return response.data;
  },

  // List all schedules
  listSchedules: async (params?: {
    skip?: number;
    limit?: number;
    enabled_only?: boolean;
  }): Promise<Schedule[]> => {
    const response = await api.get<Schedule[]>('/api/schedules', { params });
    return response.data;
  },

  // Get schedule by ID
  getSchedule: async (scheduleId: number): Promise<Schedule> => {
    const response = await api.get<Schedule>(`/api/schedules/${scheduleId}`);
    return response.data;
  },

  // Update schedule
  updateSchedule: async (
    scheduleId: number,
    data: Partial<ScheduleCreateRequest>
  ): Promise<Schedule> => {
    const response = await api.patch<Schedule>(
      `/api/schedules/${scheduleId}`,
      data
    );
    return response.data;
  },

  // Delete schedule
  deleteSchedule: async (scheduleId: number): Promise<void> => {
    await api.delete(`/api/schedules/${scheduleId}`);
  },
};

// ============================================================================
// Health Check
// ============================================================================

export const healthApi = {
  check: async (): Promise<{ status: string; database: string }> => {
    const response = await api.get('/api/health');
    return response.data;
  },
};

export default api;
