import type { DailyData, HistoryEntry, SolarMetadata } from "../types";
import InverterDailyChart from "./InverterDailyChart";

interface Props {
  entry: HistoryEntry | null;
  dailyData: Record<string, DailyData>;
  metadata: SolarMetadata | null;
}

const INVERTER_META: Record<string, { label: string; color: string }> = {
  goodwe1: { label: "GoodWe DNS-5000", color: "#ef6f4e" },
  apsystems1: { label: "Inversor 1", color: "#4f8ff7" },
  apsystems2: { label: "Inversor 2", color: "#f7a84f" },
  apsystems3: { label: "Inversor 3", color: "#59b79d" },
};

const FALLBACK_INVERTER_ORDER = ["goodwe1", "apsystems1", "apsystems2", "apsystems3"];
const PRODUCTION_DEVICE_TYPES = new Set(["apsystems", "goodwe_sems"]);
const COLORS = ["#ef6f4e", "#4f8ff7", "#f7a84f", "#59b79d", "#8b6fe8", "#4fae7b"];

function formatWh(value: number): string {
  if (value >= 1000) {
    return `${(value / 1000).toFixed(2)} kWh`;
  }
  return `${Math.round(value)} Wh`;
}

function getDeviceLabel(metadata: SolarMetadata | null, id: string, fallback: string) {
  return metadata?.devices.find(device => device.id === id)?.label ?? fallback;
}

function getProductionDeviceIds(metadata: SolarMetadata | null, inverters: Record<string, number>) {
  const metadataIds = metadata?.devices
    .filter(device => PRODUCTION_DEVICE_TYPES.has(device.type))
    .map(device => device.id) ?? [];

  const ids = metadataIds.length > 0 ? metadataIds : FALLBACK_INVERTER_ORDER;
  const extraIds = Object.keys(inverters).filter(id =>
    !ids.includes(id) && !id.startsWith("victron")
  );

  return [...ids, ...extraIds];
}

export default function InverterStats({ entry, dailyData, metadata }: Props) {
  if (!entry?.inverters) return null;

  const inverters = entry.inverters;
  const total = entry.total_wh;
  const inverterIds = getProductionDeviceIds(metadata, inverters);

  return (
    <div className="flex flex-col gap-y-3">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
        {inverterIds.map((id, index) => {
          const meta = INVERTER_META[id] ?? {
            label: id,
            color: COLORS[index % COLORS.length],
          };
          const label = getDeviceLabel(metadata, id, meta.label);
          const value = inverters[id] ?? 0;
          const pct = total > 0 ? (value / total) * 100 : 0;

          return (
            <div
              key={id}
              className="rounded border border-[color:var(--border)] bg-[color:var(--panel)] p-3 flex flex-col"
            >
              <span className="text-[0.6rem] font-semibold uppercase tracking-wider" style={{ color: meta.color }}>
                {label}
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
        <div className="rounded border border-[color:var(--border)] bg-[color:var(--panel)] p-3 flex flex-col">
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
        {inverterIds.map((id, index) => {
          const meta = INVERTER_META[id] ?? {
            label: id,
            color: COLORS[index % COLORS.length],
          };
          const label = getDeviceLabel(metadata, id, meta.label);
          const daily = dailyData[id];

          return (
            <div
              key={`chart-${id}`}
              className="rounded-xl border border-[color:var(--border)] bg-[color:var(--panel)] p-3 flex flex-col"
            >
              <span className="text-[0.6rem] font-semibold uppercase tracking-wider mb-1" style={{ color: meta.color }}>
                {label} — Hoy
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
