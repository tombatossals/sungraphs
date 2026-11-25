import { useEffect, useState } from "react";

export interface CameraImage {
  time: string;
  ts: number;
  file: string;
}

export interface CameraIndex {
  date: string;
  images: CameraImage[];
}

const REFETCH_INTERVAL = 5 * 60 * 1000;

export function cameraImageUrl(date: string, file: string): string {
  return `/data/camera/${date}/${file}`;
}

export function useCameraIndex(date: string): CameraIndex | null {
  const [state, setState] = useState<{ date: string; index: CameraIndex | null } | null>(null);

  useEffect(() => {
    if (!date) return;
    let cancelled = false;

    const load = () => {
      fetch(`/data/camera/${date}/index.json`, { cache: "no-store" })
        .then(r => (r.ok ? (r.json() as Promise<CameraIndex>) : null))
        .then(data => {
          if (cancelled) return;
          const valid = data && Array.isArray(data.images) && data.images.length > 0 ? data : null;
          setState({ date, index: valid });
        })
        .catch(() => {
          if (!cancelled) setState({ date, index: null });
        });
    };

    load();
    const id = setInterval(load, REFETCH_INTERVAL);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [date]);

  return state?.date === date ? state.index : null;
}
