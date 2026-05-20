export interface Interval {
  iso_time: string;
  p1?: number;
  p2?: number;
  total_w?: number;
  value?: number;
  error?: boolean;
}

export interface DailyData {
  date: string;
  intervals: Record<string, Interval>;
}

export interface HistoryEntry {
  date: string;
  total_wh: number;
  inverters?: Record<string, number>;
}

export interface DeviceSampleMetadata {
  id: string;
  label: string;
}

export interface DeviceMetadata {
  id: string;
  type: string;
  label: string;
  samples?: DeviceSampleMetadata[];
}

export interface SolarMetadata {
  devices: DeviceMetadata[];
}
