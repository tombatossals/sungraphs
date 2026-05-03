import { useEffect, useState } from "react";
import "./App.css";
import DailyChart from "./components/DailyChart";
import HistoryChart from "./components/HistoryChart";
import type { DailyData, HistoryEntry } from "./types";

const DAILY_DATA_BASE_URL = "https://api.micronautas.com/sungraphs";

function getDailyDataUrl(date: string) {
  return `${DAILY_DATA_BASE_URL}/apsystems1-${date}.json`;
}

export default function App() {
  const [daily, setDaily] = useState<DailyData | null>(null);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [date, setDate] = useState<string>("2026-04-30");
  const [dailyError, setDailyError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    setDaily(null);
    setDailyError(null);

    fetch(getDailyDataUrl(date), { signal: controller.signal })
      .then(response => {
        if (!response.ok) {
          throw new Error(`No se pudieron cargar los datos para ${date}.`);
        }

        return response.json() as Promise<DailyData>;
      })
      .then(data => setDaily(data))
      .catch((error: Error) => {
        if (error.name === "AbortError") {
          return;
        }

        setDailyError(error.message);
      });

    return () => controller.abort();
  }, [date]);

  useEffect(() => {
    fetch(`/data/history.json`)
      .then(r => r.json())
      .then((data: HistoryEntry[]) => setHistory(data));
  }, []);

  return (
    <div className="app-shell">
      <h1>Producción Solar</h1>

      <div className="app-controls">
        <input
          type="date"
          value={date}
          onChange={e => setDate(e.target.value)}
        />
      </div>

      {dailyError && <p className="app-message">{dailyError}</p>}

      {daily && (
        <section className="chart-section">
          <h2>Detalle diario</h2>
          <div className="chart-card">
            <DailyChart data={daily} />
          </div>
        </section>
      )}

      {history.length > 0 && (
        <section className="chart-section">
          <h2>Histórico</h2>
          <div className="chart-card">
            <HistoryChart data={history} />
          </div>
        </section>
      )}
    </div>
  );
}