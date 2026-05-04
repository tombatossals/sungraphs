import type { HistoryEntry } from "../types";

interface Props {
  entry: HistoryEntry | null;
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

export default function InverterStats({ entry }: Props) {
  if (!entry?.inverters) return null;

  const inverters = entry.inverters;
  const total = entry.total_wh;

  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
      {INVERTER_ORDER.map(id => {
        const meta = INVERTER_META[id];
        const value = inverters[id] ?? 0;
        const pct = total > 0 ? (value / total) * 100 : 0;

        return (
          <div
            key={id}
            className="rounded-xl border border-[#e1e4e8] bg-white p-3 flex flex-col"
          >
            <span className="text-[0.6rem] font-semibold uppercase tracking-wider text-gray-400">
              {meta.label}
            </span>
            <span className="mt-1 text-lg font-semibold tracking-tight text-gray-800">
              {formatWh(value)}
            </span>
            <div className="mt-2 h-1.5 w-full rounded-full bg-gray-100">
              <div
                className="h-full rounded-full transition-all"
                style={{ width: `${pct}%`, backgroundColor: meta.color }}
              />
            </div>
            <span className="mt-0.5 text-[0.6rem] font-medium text-gray-400">
              {pct.toFixed(1)}% del total
            </span>
          </div>
        );
      })}
      <div className="rounded-xl border border-[#e1e4e8] bg-white p-3 flex flex-col">
        <span className="text-[0.6rem] font-semibold uppercase tracking-wider text-gray-400">
          Total
        </span>
        <span className="mt-1 text-lg font-semibold tracking-tight text-gray-800">
          {formatWh(total)}
        </span>
        <div className="mt-2 h-1.5 w-full rounded-full bg-gray-100">
          <div className="h-full w-full rounded-full bg-gray-700" />
        </div>
        <span className="mt-0.5 text-[0.6rem] font-medium text-gray-400">
          100%
        </span>
      </div>
    </div>
  );
}
