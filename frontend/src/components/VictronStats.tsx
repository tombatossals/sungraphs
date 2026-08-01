import type { DailyData, Interval, SolarMetadata } from "../types";
import InverterDailyChart from "./InverterDailyChart";

interface Props {
  dailyData: Record<string, DailyData>;
  metadata: SolarMetadata | null;
}

const VICTRON_META: Record<string, { label: string; color: string }> = {
  "victron1-fv": { label: "Producción FV", color: "#27ae60" },
  "victron1-consumo": { label: "Consumo Casa", color: "#f39c12" },
  "victron1-red": { label: "Red Eléctrica", color: "#e74c3c" },
  "victron1-bateria": { label: "Batería", color: "#8e44ad" },
  "victron1-bateria-soc": { label: "SOC Batería", color: "#2ecc71" },
  "victron1-bateria-temperatura": { label: "Temperatura batería", color: "#16a085" },
};

const VICTRON_SUMMARY_META: Record<string, { label: string; color: string }> = {
  "victron1-consumo": { label: "Consumo Casa", color: "#f39c12" },
  "victron1-red": { label: "Iberdrola", color: "#e74c3c" },
  "victron1-bateria": { label: "Batería", color: "#8e44ad" },
  "victron1-bateria-soc": { label: "SOC Batería", color: "#2ecc71" },
  "victron1-bateria-temperatura": { label: "Temperatura batería", color: "#16a085" },
};

const VICTRON_SUMMARY_ORDER = [
  "victron1-consumo",
  "victron1-red",
  "victron1-bateria",
  "victron1-bateria-soc",
  "victron1-bateria-temperatura",
];

const VICTRON_ORDER = [
  "victron1-consumo",
  "victron1-red",
  "victron1-bateria",
  "victron1-bateria-soc",
  "victron1-bateria-temperatura",
];

function getValue(interval: Interval): number | null {
  return typeof interval.value === "number" ? interval.value : null;
}

function formatW(value: number): string {
  const abs = Math.abs(value);
  if (abs >= 1000) {
    return `${(value / 1000).toFixed(2)} kW`;
  }
  return `${Math.round(value)} W`;
}

function formatPercent(value: number): string {
  return `${Math.round(value)} %`;
}

function formatTemperature(value: number): string {
  return `${value.toFixed(1)} °C`;
}

function formatLatestValue(id: string, value: number): string {
  if (id === "victron1-bateria-soc") return formatPercent(value);
  if (id === "victron1-bateria-temperatura") return formatTemperature(value);
  return formatW(value);
}

function getLatestValue(data: DailyData | undefined): number | null {
  if (!data) return null;

  const intervals = Object.values(data.intervals)
    .filter(interval => typeof interval.value === "number")
    .sort((a, b) => a.iso_time.localeCompare(b.iso_time));

  return intervals.at(-1)?.value ?? null;
}

function getVictronSampleLabel(metadata: SolarMetadata | null, id: string, fallback: string) {
  const [deviceId, ...sampleParts] = id.split("-");
  const sampleId = sampleParts.join("-");
  const device = metadata?.devices.find(item => item.id === deviceId);
  return device?.samples?.find(sample => sample.id === sampleId)?.label ?? fallback;
}

export default function VictronStats({ dailyData, metadata }: Props) {
  return (
    <div className="flex flex-col gap-y-3">
      <h2 className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--text-soft)" }}>
        Consumos
      </h2>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-6">
        {VICTRON_SUMMARY_ORDER.map(id => {
          const meta = VICTRON_SUMMARY_META[id];
          const value = getLatestValue(dailyData[id]);

          return (
            <div
              key={`victron-summary-${id}`}
              className="rounded border border-[color:var(--border)] bg-[color:var(--panel)] p-3 flex flex-col"
            >
              <span className="text-[0.6rem] font-semibold uppercase tracking-wider" style={{ color: meta.color }}>
                {meta.label}
              </span>
              <span className="mt-1 text-lg font-semibold tracking-tight" style={{ color: "var(--text-h)" }}>
                {value === null ? "Sin datos" : formatLatestValue(id, value)}
              </span>
              <span className="mt-0.5 text-[0.6rem] font-medium" style={{ color: "var(--text-soft)" }}>
                Última lectura
              </span>
            </div>
          );
        })}
      </div>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        {VICTRON_ORDER.map(id => {
          const meta = VICTRON_META[id];
          const label = getVictronSampleLabel(metadata, id, meta.label);
          const daily = dailyData[id];

          return (
            <div
              key={`victron-${id}`}
              className="rounded-xl border border-[color:var(--border)] bg-[color:var(--panel)] p-3 flex flex-col"
            >
              <span className="text-[0.6rem] font-semibold uppercase tracking-wider mb-1" style={{ color: meta.color }}>
                {label}
              </span>
              {daily ? (
                <InverterDailyChart data={daily} color={meta.color} getValue={getValue} label={label} />
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
