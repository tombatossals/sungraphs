import { useEffect, useState } from "react";
import DailyChart from "./components/DailyChart";
import HistoryChart from "./components/HistoryChart";
import ProductionHeatmap from "./components/ProductionHeatmap";
import type { DailyData, HistoryEntry } from "./types";

const DAILY_DATA_BASE_URL = "https://api.micronautas.com/sungraphs";

function getDailyDataUrl(date: string) {
  return `${DAILY_DATA_BASE_URL}/apsystems1-${date}.json`;
}

const chartCardClassName = [
  "min-h-[300px] rounded-[26px] border border-[color:var(--panel-border)] bg-[color:var(--panel)] p-4",
  "shadow-[0_24px_60px_rgba(148,163,184,0.16),inset_0_1px_0_rgba(255,255,255,0.9)]",
  "md:min-h-[360px] md:p-6"
].join(" ");

const statCardClassName = [
  "rounded-[22px] border border-[color:var(--panel-border)] bg-[color:var(--panel-muted)] px-4 py-3",
  "text-left shadow-[inset_0_1px_0_rgba(255,255,255,0.8)]"
].join(" ");

function formatProduction(totalWh: number | null | undefined) {
  if (typeof totalWh !== "number") {
    return "Sin datos";
  }

  if (totalWh >= 1000) {
    return `${new Intl.NumberFormat("es-ES", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(totalWh / 1000)} kWh`;
  }

  return `${new Intl.NumberFormat("es-ES", {
    maximumFractionDigits: 0
  }).format(totalWh)} Wh`;
}

function formatDisplayDate(value: string) {
  return new Intl.DateTimeFormat("es-ES", {
    day: "2-digit",
    month: "short",
    year: "numeric"
  }).format(new Date(`${value}T00:00:00`));
}

export default function App() {
  const [daily, setDaily] = useState<DailyData | null>(null);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [date, setDate] = useState<string>("");
  const [dailyError, setDailyError] = useState<string | null>(null);

  useEffect(() => {
    if (!date) {
      return;
    }

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
      .then((data: HistoryEntry[]) => {
        const sortedData = [...data].sort((left, right) => left.date.localeCompare(right.date));

        setHistory(sortedData);
        setDate(currentDate => {
          if (sortedData.some(entry => entry.date === currentDate)) {
            return currentDate;
          }

          return sortedData[sortedData.length - 1]?.date ?? "";
        });
      });
  }, []);

  const selectedHistoryEntry = history.find(entry => entry.date === date) ?? null;
  const averageWh = history.length > 0
    ? history.reduce((sum, entry) => sum + entry.total_wh, 0) / history.length
    : null;
  const bestDay = history.reduce<HistoryEntry | null>((bestEntry, entry) => {
    if (bestEntry === null || entry.total_wh > bestEntry.total_wh) {
      return entry;
    }

    return bestEntry;
  }, null);

  return (
    <div className="px-4 py-5 md:px-6 md:py-7">
      <section className="rounded-[32px] border border-[color:var(--panel-border)] bg-[color:var(--panel)] p-5 text-left shadow-[0_30px_70px_rgba(148,163,184,0.16),inset_0_1px_0_rgba(255,255,255,0.92)] md:p-7">
        <div className="flex flex-col gap-6 md:flex-row md:items-start md:justify-between">
          <div className="max-w-[34rem]">
            <p className="mb-3 text-[0.72rem] font-semibold uppercase tracking-[0.28em] text-[color:var(--text-soft)]">
              Monitor solar
            </p>
            <h1 className="text-[40px] font-medium tracking-[-0.06em] text-[color:var(--text-h)] md:text-[56px]">
              Producción solar
            </h1>
            <p className="mt-3 max-w-[28rem] text-[0.98rem] leading-7 text-[color:var(--text)]">
              Un panel limpio para revisar producción diaria, tendencia histórica y elegir fechas con una vista de calendario continua.
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-3 md:min-w-[28rem] md:flex-1">
            <div className={statCardClassName}>
              <p className="text-[0.72rem] font-semibold uppercase tracking-[0.24em] text-[color:var(--text-soft)]">
                Día seleccionado
              </p>
              <p className="mt-3 text-[1.7rem] font-medium tracking-[-0.04em] text-[color:var(--text-h)]">
                {formatProduction(selectedHistoryEntry?.total_wh)}
              </p>
              <p className="mt-1 text-sm text-[color:var(--text)]">
                {selectedHistoryEntry ? formatDisplayDate(selectedHistoryEntry.date) : "Sin selección"}
              </p>
            </div>

            <div className={statCardClassName}>
              <p className="text-[0.72rem] font-semibold uppercase tracking-[0.24em] text-[color:var(--text-soft)]">
                Media diaria
              </p>
              <p className="mt-3 text-[1.7rem] font-medium tracking-[-0.04em] text-[color:var(--text-h)]">
                {formatProduction(averageWh)}
              </p>
              <p className="mt-1 text-sm text-[color:var(--text)]">
                {history.length} días registrados
              </p>
            </div>

            <div className={statCardClassName}>
              <p className="text-[0.72rem] font-semibold uppercase tracking-[0.24em] text-[color:var(--text-soft)]">
                Mejor jornada
              </p>
              <p className="mt-3 text-[1.7rem] font-medium tracking-[-0.04em] text-[color:var(--text-h)]">
                {formatProduction(bestDay?.total_wh)}
              </p>
              <p className="mt-1 text-sm text-[color:var(--text)]">
                {bestDay ? formatDisplayDate(bestDay.date) : "Sin histórico"}
              </p>
            </div>
          </div>
        </div>
      </section>

      <div className="mt-6 grid gap-6 xl:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
        {history.length > 0 && (
          <ProductionHeatmap
            data={history}
            selectedDate={date}
            onSelectDate={setDate}
          />
        )}

        <section className="rounded-[30px] border border-[color:var(--panel-border)] bg-[color:var(--panel)] p-5 text-left shadow-[0_24px_60px_rgba(148,163,184,0.14),inset_0_1px_0_rgba(255,255,255,0.85)] md:p-6">
          <p className="text-[0.72rem] font-semibold uppercase tracking-[0.24em] text-[color:var(--text-soft)]">
            Resumen
          </p>
          <div className="mt-5 space-y-4">
            <div className="rounded-[20px] border border-[color:var(--panel-border)] bg-[color:var(--panel-muted)] p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.75)]">
              <p className="text-sm text-[color:var(--text-soft)]">Fecha activa</p>
              <p className="mt-2 text-2xl font-medium tracking-[-0.04em] text-[color:var(--text-h)]">
                {selectedHistoryEntry ? formatDisplayDate(selectedHistoryEntry.date) : "Sin datos"}
              </p>
              <p className="mt-2 text-sm leading-6 text-[color:var(--text)]">
                El mapa de calor funciona como selector principal y mantiene el detalle diario sincronizado con el histórico.
              </p>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="rounded-[20px] border border-[color:var(--panel-border)] bg-white/70 p-4">
                <p className="text-sm text-[color:var(--text-soft)]">Cobertura</p>
                <p className="mt-2 text-xl font-medium tracking-[-0.04em] text-[color:var(--text-h)]">
                  {history.length} días
                </p>
              </div>
              <div className="rounded-[20px] border border-[color:var(--panel-border)] bg-white/70 p-4">
                <p className="text-sm text-[color:var(--text-soft)]">Pico histórico</p>
                <p className="mt-2 text-xl font-medium tracking-[-0.04em] text-[color:var(--text-h)]">
                  {formatProduction(bestDay?.total_wh)}
                </p>
              </div>
            </div>
          </div>
        </section>
      </div>

      {dailyError && (
        <p className="mt-5 rounded-[18px] border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {dailyError}
        </p>
      )}

      {daily && (
        <section className="mt-7">
          <h2 className="mb-3 text-[0.72rem] font-semibold uppercase tracking-[0.24em] text-[color:var(--text-soft)]">
            Detalle diario
          </h2>
          <div className={chartCardClassName}>
            <DailyChart data={daily} />
          </div>
        </section>
      )}

      {history.length > 0 && (
        <section className="mt-7">
          <h2 className="mb-3 text-[0.72rem] font-semibold uppercase tracking-[0.24em] text-[color:var(--text-soft)]">
            Histórico
          </h2>
          <div className={chartCardClassName}>
            <HistoryChart data={history} />
          </div>
        </section>
      )}
    </div>
  );
}