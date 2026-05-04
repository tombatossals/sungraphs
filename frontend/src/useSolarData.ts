import { useEffect, useState, useCallback, useReducer, useRef } from "react";
import type { DailyData, HistoryEntry } from "./types";

const DAILY_DATA_BASE_URL = "https://api.micronautas.com/sungraphs";
const REFETCH_INTERVAL = 5 * 60 * 1000;

function getDailyDataUrl(date: string) {
  return `${DAILY_DATA_BASE_URL}/apsystems1-${date}.json`;
}

interface DailyState {
  data: DailyData | null;
  loading: boolean;
  error: string | null;
}

type DailyAction =
  | { type: "fetch" }
  | { type: "success"; data: DailyData }
  | { type: "error"; message: string };

function dailyReducer(_state: DailyState, action: DailyAction): DailyState {
  switch (action.type) {
    case "fetch":
      return { data: null, loading: true, error: null };
    case "success":
      return { data: action.data, loading: false, error: null };
    case "error":
      return { data: null, loading: false, error: action.message };
  }
}

function useInterval(cb: () => void, delay: number) {
  const savedCb = useRef(cb);

  useEffect(() => {
    savedCb.current = cb;
  }, [cb]);

  useEffect(() => {
    const id = setInterval(() => savedCb.current(), delay);
    return () => clearInterval(id);
  }, [delay]);
}

export function useSolarData() {
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);

  const [daily, dispatch] = useReducer(dailyReducer, {
    data: null,
    loading: false,
    error: null,
  });

  function readDateFromURL(): string {
    const path = window.location.pathname.replace(/^\/+|\/+$/g, "");
    if (/^\d{4}-\d{2}-\d{2}$/.test(path)) return path;
    return "";
  }

  const [date, setDateState] = useState<string>(readDateFromURL);

  const setDate = useCallback((d: string) => {
    setDateState(d);
    window.history.replaceState(null, "", `/${d}`);
  }, []);

  useEffect(() => {
    const onPop = () => setDateState(readDateFromURL());
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  const fetchHistory = useCallback(() => {
    fetch(`/data/history.json`)
      .then(r => {
        if (!r.ok) throw new Error("No se pudo cargar el histórico.");
        return r.json() as Promise<HistoryEntry[]>;
      })
      .then(data => {
        const sorted = [...data].sort((a, b) => a.date.localeCompare(b.date));
        setHistory(sorted);
        setDateState(current => {
          if (!sorted.some(e => e.date === current)) {
            return sorted[sorted.length - 1]?.date ?? "";
          }
          return current;
        });
        setLastUpdated(new Intl.DateTimeFormat("es-ES", {
          hour: "2-digit", minute: "2-digit", second: "2-digit"
        }).format(new Date()));
      })
      .catch(err => setHistoryError(err.message))
      .finally(() => setHistoryLoading(false));
  }, []);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  useInterval(fetchHistory, REFETCH_INTERVAL);

  useEffect(() => {
    if (!date) return;
    const expected = `/${date}`;
    if (window.location.pathname !== expected) {
      window.history.replaceState(null, "", expected);
    }
  }, [date]);

  useEffect(() => {
    if (!date) return;

    const controller = new AbortController();
    dispatch({ type: "fetch" });

    fetch(getDailyDataUrl(date), { signal: controller.signal })
      .then(r => {
        if (!r.ok) throw new Error(`No se pudieron cargar los datos para ${date}.`);
        return r.json() as Promise<DailyData>;
      })
      .then(data => dispatch({ type: "success", data }))
      .catch(err => {
        if (err.name !== "AbortError") {
          dispatch({ type: "error", message: err.message });
        }
      });

    return () => controller.abort();
  }, [date]);

  const selectedHistoryEntry = history.find(e => e.date === date) ?? null;
  const averageWh = history.length > 0
    ? history.reduce((s, e) => s + e.total_wh, 0) / history.length
    : null;
  const bestDay = history.reduce<HistoryEntry | null>((best, e) =>
    !best || e.total_wh > best.total_wh ? e : best, null);

  return {
    daily: daily.data,
    dailyLoading: daily.loading,
    dailyError: daily.error,
    history,
    historyLoading,
    historyError,
    date,
    setDate,
    selectedHistoryEntry,
    averageWh,
    bestDay,
    lastUpdated,
  };
}
