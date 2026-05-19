import { Line } from "react-chartjs-2";
import {
  Chart as ChartJS,
  type ChartOptions,
  LineElement,
  PointElement,
  LinearScale,
  CategoryScale,
  Filler,
  Tooltip,
  Legend,
} from "chart.js";
import type { DailyData } from "../types";
import { createLineChartOptions } from "./chartTheme";

ChartJS.register(
  LineElement,
  PointElement,
  LinearScale,
  CategoryScale,
  Filler,
  Tooltip,
  Legend,
);

interface Props {
  dailyData: Record<string, DailyData>;
}

const METRICS = [
  { id: "victron1-fv", label: "Producción FV", color: "#27ae60" },
  { id: "victron1-consumo", label: "Consumo Casa", color: "#f39c12" },
  { id: "victron1-cargas-criticas", label: "Cargas críticas", color: "#3498db" },
  { id: "victron1-cargas-no-criticas", label: "Cargas no críticas", color: "#d35400" },
  { id: "victron1-red", label: "Red Eléctrica", color: "#e74c3c" },
  { id: "victron1-bateria", label: "Batería", color: "#8e44ad" },
];

function formatWatts(w: number | null): string {
  if (w === null) return "—";
  return `${w.toFixed(0)} W`;
}

export default function DetailedCombinedChart({ dailyData }: Props) {
  const timestamps = new Set<string>();
  const series: Record<string, Record<string, number>> = {};

  for (const { id } of METRICS) {
    const daily = dailyData[id];
    if (!daily) continue;
    const values: Record<string, number> = {};
    for (const [ts, interval] of Object.entries(daily.intervals)) {
      if (typeof interval.value === "number") {
        values[ts] = interval.value;
        timestamps.add(ts);
      }
    }
    if (Object.keys(values).length > 0) {
      series[id] = values;
    }
  }

  if (timestamps.size === 0) return null;

  const sortedTimestamps = Array.from(timestamps).sort((a, b) => Number(a) - Number(b));

  const refMetric = METRICS.find(m => series[m.id]);
  const labels = sortedTimestamps.map(ts => {
    if (refMetric) {
      const interval = dailyData[refMetric.id]?.intervals[ts];
      if (interval) return interval.iso_time.slice(11, 16);
    }
    return "";
  });

  const baseOptions = createLineChartOptions();

  const options: ChartOptions<"line"> = {
    ...baseOptions,
    plugins: {
      ...baseOptions.plugins,
      legend: {
        ...baseOptions.plugins?.legend,
        position: "top",
        align: "center",
        labels: {
          color: undefined,
          usePointStyle: true,
          boxWidth: 12,
          boxHeight: 12,
          padding: 20,
          font: { size: 11 },
        },
      },
      tooltip: {
        ...baseOptions.plugins?.tooltip,
        callbacks: {
          title(items) {
            return items[0]?.label ? `Hora: ${items[0].label}` : "";
          },
          label(ctx) {
            return ` ${ctx.dataset.label}: ${formatWatts(ctx.parsed.y as number | null)}`;
          },
        },
      },
    },
    scales: {
      x: {
        ...(baseOptions.scales?.x ?? {}),
        ticks: {
          color: undefined,
          maxRotation: 0,
          autoSkip: true,
          maxTicksLimit: 12,
          padding: 8,
          font: { size: 10 },
        },
        grid: { display: false },
      },
      y: {
        ...(baseOptions.scales?.y ?? {}),
        ticks: {
          color: undefined,
          padding: 8,
          font: { size: 10 },
          callback(value) {
            return `${value} W`;
          },
        },
        grid: {
          color: undefined,
        },
      },
    },
  };

  const datasets = METRICS.filter(m => series[m.id]).map(m => ({
    label: m.label,
    data: sortedTimestamps.map(ts => series[m.id]?.[ts] ?? null),
    borderColor: m.color,
    backgroundColor: `${m.color}18`,
    tension: 0.28,
    pointRadius: 0,
    pointHitRadius: 6,
    borderWidth: 2,
    fill: true,
  }));

  const chartData = { labels, datasets };

  return (
    <div className="flex flex-col gap-y-2">
      <h2 className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--text-soft)" }}>
        Vista combinada — Todas las métricas
      </h2>
      <div
        className="rounded-xl border border-[color:var(--border)] bg-[color:var(--panel)] p-4"
      >
        <div className="h-72 md:h-96">
          <Line data={chartData} options={options} />
        </div>
      </div>
    </div>
  );
}
