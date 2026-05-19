import type { DailyData, Interval } from "../types";
import InverterDailyChart from "./InverterDailyChart";

interface Props {
  dailyData: Record<string, DailyData>;
}

const VICTRON_META: Record<string, { label: string; color: string }> = {
  "victron1-fv": { label: "Producción FV", color: "#27ae60" },
  "victron1-consumo": { label: "Consumo Casa", color: "#f39c12" },
  "victron1-cargas-criticas": { label: "Cargas críticas", color: "#3498db" },
  "victron1-cargas-no-criticas": { label: "Cargas no críticas", color: "#d35400" },
  "victron1-red": { label: "Red Eléctrica", color: "#e74c3c" },
  "victron1-bateria": { label: "Batería", color: "#8e44ad" },
};

const VICTRON_ORDER = [
  "victron1-fv",
  "victron1-consumo",
  "victron1-cargas-criticas",
  "victron1-cargas-no-criticas",
  "victron1-red",
  "victron1-bateria",
];

function getValue(interval: Interval): number | null {
  return typeof interval.value === "number" ? interval.value : null;
}

export default function VictronStats({ dailyData }: Props) {
  return (
    <div className="flex flex-col gap-y-3">
      <h2 className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--text-soft)" }}>
        Inversor principal — Hoy
      </h2>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        {VICTRON_ORDER.map(id => {
          const meta = VICTRON_META[id];
          const daily = dailyData[id];

          return (
            <div
              key={`victron-${id}`}
              className="rounded-xl border border-[color:var(--border)] bg-[color:var(--panel)] p-3 flex flex-col"
            >
              <span className="text-[0.6rem] font-semibold uppercase tracking-wider mb-1" style={{ color: meta.color }}>
                {meta.label}
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
