import { useEffect, useState, useCallback, useReducer, useRef } from "react";
import type { DailyData, HistoryEntry, SolarMetadata } from "./types";

const DAILY_DATA_BASE_URL = "/data";
const REFETCH_INTERVAL = 5 * 60 * 1000;
const PRODUCTION_DEVICE_TYPES = new Set(["apsystems", "goodwe_sems"]);
const FALLBACK_INVERTER_IDS = ["goodwe1", "apsystems1", "apsystems2", "apsystems3"];
const VICTRON_IDS = [
  "victron1-bateria",
  "victron1-cargas-criticas",
  "victron1-consumo",
  "victron1-fv",
  "victron1-red",
];

function getDailyDataUrl(id: string, date: string) {
  return `${DAILY_DATA_BASE_URL}/${id}-${date}.json`;
}

function getDailyIds(metadata: SolarMetadata | null) {
  if (!metadata) return [...FALLBACK_INVERTER_IDS, ...VICTRON_IDS];

  const ids = metadata.devices.flatMap(device => {
    if (PRODUCTION_DEVICE_TYPES.has(device.type)) return [device.id];
    if (device.type === "victron") {
      return device.samples?.map(sample => `${device.id}-${sample.id}`) ?? [];
    }
    return [];
  });

  return ids.length > 0 ? ids : [...FALLBACK_INVERTER_IDS, ...VICTRON_IDS];
}

interface DailyState {
  data: Record<string, DailyData>;
  loading: boolean;
  error: string | null;
}

type DailyAction =
  | { type: "fetch" }
  | { type: "success"; data: Record<string, DailyData> }
  | { type: "error"; message: string };

function dailyReducer(_state: DailyState, action: DailyAction): DailyState {
  switch (action.type) {
    case "fetch":
      return { data: {}, loading: true, error: null };
    case "success":
      return { data: action.data, loading: false, error: null };
    case "error":
      return { data: {}, loading: false, error: action.message };
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
  const [metadata, setMetadata] = useState<SolarMetadata | null>(null);

  const [daily, dispatch] = useReducer(dailyReducer, {
    data: {},
    loading: false,
    error: null,
  });

  function readDateFromURL(): string {
    const params = new URLSearchParams(window.location.search);
    const d = params.get("date");
    if (d && /^\d{4}-\d{2}-\d{2}$/.test(d)) return d;
    return "";
  }

  const [date, setDateState] = useState<string>(readDateFromURL);

  const setDate = useCallback((d: string) => {
    setDateState(d);
    const url = new URL(window.location.href);
    url.searchParams.set("date", d);
    window.history.replaceState(null, "", url.pathname + url.search);
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

  useEffect(() => {
    fetch(`/data/metadata.json`)
      .then(r => {
        if (!r.ok) return null;
        return r.json() as Promise<SolarMetadata>;
      })
      .then(data => {
        if (data) setMetadata(data);
      })
      .catch(() => {
        setMetadata(null);
      });
  }, []);

  useInterval(fetchHistory, REFETCH_INTERVAL);

  useEffect(() => {
    if (!date) return;
    const params = new URLSearchParams(window.location.search);
    if (params.get("date") !== date) {
      params.set("date", date);
      window.history.replaceState(null, "", window.location.pathname + "?" + params.toString());
    }
  }, [date]);

  useEffect(() => {
    if (!date) return;

    const controller = new AbortController();
    dispatch({ type: "fetch" });

    const allIds = getDailyIds(metadata);

    Promise.all(
      allIds.map(async (id) => {
        const r = await fetch(getDailyDataUrl(id, date), { signal: controller.signal });
        if (!r.ok) {
          return { id, data: null };
        }
        return { id, data: (await r.json()) as DailyData };
      })
    )
      .then(results => {
        const record: Record<string, DailyData> = {};
        results.forEach(({ id, data }) => { if (data) record[id] = data; });
        if (Object.keys(record).length === 0) {
          throw new Error(`No se pudieron cargar los datos para ${date}.`);
        }
        dispatch({ type: "success", data: record });
      })
      .catch(err => {
        if (err.name !== "AbortError") {
          dispatch({ type: "error", message: err.message });
        }
      });

    return () => controller.abort();
  }, [date, metadata]);

  const selectedHistoryEntry = history.find(e => e.date === date) ?? null;
  const averageWh = history.length > 0
    ? history.reduce((s, e) => s + e.total_wh, 0) / history.length
    : null;
  const bestDay = history.reduce<HistoryEntry | null>((best, e) =>
    !best || e.total_wh > best.total_wh ? e : best, null);

  return {
    dailyData: daily.data,
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
    metadata,
  };
}
