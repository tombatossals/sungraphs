import type { DailyData, HistoryEntry, Interval, SolarMetadata } from "../types";
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
const FALLBACK_APSYSTEMS_ORDER = ["apsystems1", "apsystems2", "apsystems3"];
const FALLBACK_GOODWE_ORDER = ["goodwe1"];
const PRODUCTION_DEVICE_TYPES = new Set(["apsystems", "goodwe_sems"]);
const TOTAL_FV_CHART_ID = "victron1-fv";
const TOTAL_FV_CHART_META = { label: "Producción FV", color: "#27ae60" };
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

function getProductionChartDeviceIds(metadata: SolarMetadata | null, inverters: Record<string, number>) {
  const devices = metadata?.devices ?? [];
  const apsystemsIds = devices
    .filter(device => device.type === "apsystems")
    .map(device => device.id);
  const goodweIds = devices
    .filter(device => device.type === "goodwe_sems")
    .map(device => device.id);

  const apsystems = apsystemsIds.length > 0 ? apsystemsIds : FALLBACK_APSYSTEMS_ORDER;
  const goodwe = goodweIds.length > 0 ? goodweIds : FALLBACK_GOODWE_ORDER;
  const ordered = [...apsystems, ...goodwe].filter(id => id in inverters);
  const extraIds = Object.keys(inverters).filter(id =>
    !ordered.includes(id) && !id.startsWith("victron")
  );

  return [...ordered, ...extraIds];
}

function getVictronValue(interval: Interval): number | null {
  return typeof interval.value === "number" ? interval.value : null;
}

function getVictronSampleLabel(metadata: SolarMetadata | null, id: string, fallback: string) {
  const [deviceId, ...sampleParts] = id.split("-");
  const sampleId = sampleParts.join("-");
  const device = metadata?.devices.find(item => item.id === deviceId);
  return device?.samples?.find(sample => sample.id === sampleId)?.label ?? fallback;
}

export default function InverterStats({ entry, dailyData, metadata }: Props) {
  if (!entry?.inverters) return null;

  const inverters = entry.inverters;
  const total = entry.total_wh;
  const inverterIds = getProductionDeviceIds(metadata, inverters);
  const chartDeviceIds = getProductionChartDeviceIds(metadata, inverters);
  const totalFvLabel = getVictronSampleLabel(metadata, TOTAL_FV_CHART_ID, TOTAL_FV_CHART_META.label);
  const totalFvDaily = dailyData[TOTAL_FV_CHART_ID];

  return (
    <div className="flex flex-col gap-y-3">
      <h2 className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--text-soft)" }}>
        Producción
      </h2>
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
        {chartDeviceIds.map((id, index) => {
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
        <div className="rounded-xl border border-[color:var(--border)] bg-[color:var(--panel)] p-3 flex flex-col md:col-span-2">
          <span className="text-[0.6rem] font-semibold uppercase tracking-wider mb-1" style={{ color: TOTAL_FV_CHART_META.color }}>
            {totalFvLabel} — Hoy
          </span>
          {totalFvDaily ? (
            <InverterDailyChart data={totalFvDaily} color={TOTAL_FV_CHART_META.color} getValue={getVictronValue} />
          ) : (
            <div className="h-32 flex items-center justify-center">
              <span className="text-xs" style={{ color: "var(--text-soft)" }}>Sin datos</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
