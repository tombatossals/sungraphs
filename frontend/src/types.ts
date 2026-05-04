export interface Interval {
  timestamp_iso: string;
  p1?: number;
  p2?: number;
  total_w?: number;
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