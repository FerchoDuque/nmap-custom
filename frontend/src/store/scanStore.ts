import { create } from 'zustand';
import type { Scan } from '@/types';

interface ScanStore {
  scans: Scan[];
  activeScans: Scan[];
  selectedScan: Scan | null;
  isLoading: boolean;
  error: string | null;

  // Actions
  setScans: (scans: Scan[]) => void;
  addScan: (scan: Scan) => void;
  updateScan: (scanId: number, updates: Partial<Scan>) => void;
  removeScan: (scanId: number) => void;
  setSelectedScan: (scan: Scan | null) => void;
  setLoading: (isLoading: boolean) => void;
  setError: (error: string | null) => void;
  clearError: () => void;
}

export const useScanStore = create<ScanStore>((set, get) => ({
  scans: [],
  activeScans: [],
  selectedScan: null,
  isLoading: false,
  error: null,

  setScans: (scans) => {
    const activeScans = scans.filter(
      (scan) => scan.status === 'running' || scan.status === 'pending'
    );
    set({ scans, activeScans });
  },

  addScan: (scan) => {
    const scans = [scan, ...get().scans];
    const activeScans = scans.filter(
      (s) => s.status === 'running' || s.status === 'pending'
    );
    set({ scans, activeScans });
  },

  updateScan: (scanId, updates) => {
    const scans = get().scans.map((scan) =>
      scan.id === scanId ? { ...scan, ...updates } : scan
    );
    const activeScans = scans.filter(
      (s) => s.status === 'running' || s.status === 'pending'
    );
    
    // Update selected scan if it's the one being updated
    const selectedScan = get().selectedScan;
    const updatedSelectedScan =
      selectedScan?.id === scanId
        ? { ...selectedScan, ...updates }
        : selectedScan;

    set({ scans, activeScans, selectedScan: updatedSelectedScan });
  },

  removeScan: (scanId) => {
    const scans = get().scans.filter((scan) => scan.id !== scanId);
    const activeScans = scans.filter(
      (s) => s.status === 'running' || s.status === 'pending'
    );
    const selectedScan =
      get().selectedScan?.id === scanId ? null : get().selectedScan;
    set({ scans, activeScans, selectedScan });
  },

  setSelectedScan: (scan) => set({ selectedScan: scan }),
  setLoading: (isLoading) => set({ isLoading }),
  setError: (error) => set({ error }),
  clearError: () => set({ error: null }),
}));
