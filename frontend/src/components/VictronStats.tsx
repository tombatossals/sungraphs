import type { DailyData, Interval, SolarMetadata } from "../types";
import InverterDailyChart from "./InverterDailyChart";

interface Props {
  dailyData: Record<string, DailyData>;
  metadata: SolarMetadata | null;
}

const VICTRON_META: Record<string, { label: string; color: string }> = {
  "victron1-fv": { label: "Producción FV", color: "#27ae60" },
  "victron1-consumo": { label: "Consumo Casa", color: "#f39c12" },
  "victron1-cargas-criticas": { label: "Cargas críticas", color: "#3498db" },
  "victron1-red": { label: "Red Eléctrica", color: "#e74c3c" },
  "victron1-bateria": { label: "Batería", color: "#8e44ad" },
};

const VICTRON_ORDER = [
  "victron1-fv",
  "victron1-consumo",
  "victron1-cargas-criticas",
  "victron1-red",
  "victron1-bateria",
];

function getValue(interval: Interval): number | null {
  return typeof interval.value === "number" ? interval.value : null;
}

function getVictronSampleLabel(metadata: SolarMetadata | null, id: string, fallback: string) {
  const [deviceId, ...sampleParts] = id.split("-");
  const sampleId = sampleParts.join("-");
  const device = metadata?.devices.find(item => item.id === deviceId);
  return device?.samples?.find(sample => sample.id === sampleId)?.label ?? fallback;
}

function getVictronDeviceLabel(metadata: SolarMetadata | null) {
  return metadata?.devices.find(item => item.id === "victron1")?.label ?? "Inversor principal";
}

export default function VictronStats({ dailyData, metadata }: Props) {
  return (
    <div className="flex flex-col gap-y-3">
      <h2 className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--text-soft)" }}>
        {getVictronDeviceLabel(metadata)} — Hoy
      </h2>
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
                <InverterDailyChart data={daily} color={meta.color} getValue={getValue} />
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
