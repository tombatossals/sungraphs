import type { DailyData, HistoryEntry } from "../types";
import InverterDailyChart from "./InverterDailyChart";

interface Props {
  entry: HistoryEntry | null;
  dailyData: Record<string, DailyData>;
}

const INVERTER_META: Record<string, { label: string; color: string }> = {
  apsystems1: { label: "Inversor 1", color: "#4f8ff7" },
  apsystems2: { label: "Inversor 2", color: "#f7a84f" },
  apsystems3: { label: "Inversor 3", color: "#59b79d" },
};

const INVERTER_ORDER = ["apsystems1", "apsystems2", "apsystems3"];

function formatWh(value: number): string {
  if (value >= 1000) {
    return `${(value / 1000).toFixed(2)} kWh`;
  }
  return `${Math.round(value)} Wh`;
}

export default function InverterStats({ entry, dailyData }: Props) {
  if (!entry?.inverters) return null;

  const inverters = entry.inverters;
  const total = entry.total_wh;

  return (
    <div className="flex flex-col gap-y-3">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {INVERTER_ORDER.map(id => {
          const meta = INVERTER_META[id];
          const value = inverters[id] ?? 0;
          const pct = total > 0 ? (value / total) * 100 : 0;

          return (
            <div
              key={id}
              className="rounded-xl border border-[color:var(--border)] bg-[color:var(--panel)] p-3 flex flex-col"
            >
              <span className="text-[0.6rem] font-semibold uppercase tracking-wider" style={{ color: meta.color }}>
                {meta.label}
              </span>
              <span className="mt-1 text-lg font-semibold tracking-tight" style={{ color: "var(--text-h)" }}>
                {formatWh(value)}
              </span>
              <div className="mt-2 h-1.5 w-full rounded-full bg-[color:var(--border)]">
                <div
                  className="h-full rounded-full transition-all"
                  style={{ width: `${pct}%`, backgroundColor: meta.color }}
                />
              </div>
              <span className="mt-0.5 text-[0.6rem] font-medium" style={{ color: "var(--text-soft)" }}>
                {pct.toFixed(1)}% del total
              </span>
            </div>
          );
        })}
        <div className="rounded-xl border border-[color:var(--border)] bg-[color:var(--panel)] p-3 flex flex-col">
          <span className="text-[0.6rem] font-semibold uppercase tracking-wider" style={{ color: "var(--text-soft)" }}>
            Total
          </span>
          <span className="mt-1 text-lg font-semibold tracking-tight" style={{ color: "var(--text-h)" }}>
            {formatWh(total)}
          </span>
          <div className="mt-2 h-1.5 w-full rounded-full bg-[color:var(--border)]">
            <div className="h-full w-full rounded-full bg-[color:var(--text)]" />
          </div>
          <span className="mt-0.5 text-[0.6rem] font-medium" style={{ color: "var(--text-soft)" }}>
            100%
          </span>
        </div>
      </div>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
        {INVERTER_ORDER.map(id => {
          const meta = INVERTER_META[id];
          const daily = dailyData[id];

          return (
            <div
              key={`chart-${id}`}
              className="rounded-xl border border-[color:var(--border)] bg-[color:var(--panel)] p-3 flex flex-col"
            >
              <span className="text-[0.6rem] font-semibold uppercase tracking-wider mb-1" style={{ color: meta.color }}>
                {meta.label} — Hoy
              </span>
              {daily ? (
                <InverterDailyChart data={daily} color={meta.color} />
              ) : (
                <div className="h-32 flex items-center justify-center">
                  <span className="text-xs" style={{ color: "var(--text-soft)" }}>Sin datos</span>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
