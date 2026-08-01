import { Line } from "react-chartjs-2";
import {
  Chart as ChartJS,
  type ChartOptions,
  CategoryScale,
  Filler,
  Legend,
  LinearScale,
  LineElement,
  PointElement,
  Tooltip,
} from "chart.js";
import type { DailyData, Interval, SolarMetadata } from "../types";
import { createLineChartOptions } from "./chartTheme";

ChartJS.register(
  CategoryScale,
  Filler,
  Legend,
  LinearScale,
  LineElement,
  PointElement,
  Tooltip,
);

interface Props {
  dailyData: Record<string, DailyData>;
  metadata: SolarMetadata | null;
}

interface Metric {
  id: string;
  label: string;
  color: string;
  kind: "production" | "consumption";
  getValue: (interval: Interval) => number | null;
}

const FALLBACK_PRODUCTION_METRICS: Metric[] = [
  { id: "apsystems1", label: "APSystems 1", color: "#4f8ff7", kind: "production", getValue: getProductionValue },
  { id: "apsystems2", label: "APSystems 2", color: "#f7a84f", kind: "production", getValue: getProductionValue },
  { id: "apsystems3", label: "APSystems 3", color: "#59b79d", kind: "production", getValue: getProductionValue },
  { id: "goodwe1", label: "GoodWe", color: "#ef6f4e", kind: "production", getValue: getProductionValue },
  { id: "victron1-fv", label: "Producción FV", color: "#27ae60", kind: "production", getValue: getVictronValue },
];

const CONSUMPTION_METRICS: Metric[] = [
  { id: "victron1-consumo", label: "Consumo casa", color: "#f39c12", kind: "consumption", getValue: getVictronValue },
  { id: "victron1-red", label: "Red eléctrica", color: "#e74c3c", kind: "consumption", getValue: getVictronValue },
  { id: "victron1-bateria", label: "Batería", color: "#8e44ad", kind: "consumption", getValue: getVictronValue },
];

const PRODUCTION_DEVICE_TYPES = new Set(["apsystems", "goodwe_sems"]);
const PRODUCTION_COLORS = ["#ef6f4e", "#4f8ff7", "#f7a84f", "#59b79d", "#8b6fe8"];
const PRODUCTION_COLOR_BY_ID: Record<string, string> = {
  goodwe1: "#ef6f4e",
  apsystems1: "#4f8ff7",
  apsystems2: "#f7a84f",
  apsystems3: "#59b79d",
};
const TOTAL_FV_METRIC: Metric = {
  id: "victron1-fv",
  label: "Producción FV",
  color: "#27ae60",
  kind: "production",
  getValue: getVictronValue,
};

function getProductionValue(interval: Interval): number | null {
  if (typeof interval.total_w === "number") return interval.total_w;
  if (typeof interval.p1 === "number" && typeof interval.p2 === "number") {
    return interval.p1 + interval.p2;
  }
  return null;
}

function getVictronValue(interval: Interval): number | null {
  return typeof interval.value === "number" ? interval.value : null;
}

function formatWatts(value: number | null) {
  if (value === null) return "—";
  const abs = Math.abs(value);
  if (abs >= 1000) {
    return `${(value / 1000).toFixed(1)} kW`;
  }
  return `${Math.round(value)} W`;
}

function readCssVar(name: string, fallback: string) {
  if (typeof window === "undefined") {
    return fallback;
  }

  const value = window.getComputedStyle(document.documentElement)
    .getPropertyValue(name)
    .trim();

  return value || fallback;
}

function getDeviceLabel(metadata: SolarMetadata | null, id: string, fallback: string) {
  return metadata?.devices.find(device => device.id === id)?.label ?? fallback;
}

function getVictronSampleLabel(metadata: SolarMetadata | null, id: string, fallback: string) {
  const [deviceId, ...sampleParts] = id.split("-");
  const sampleId = sampleParts.join("-");
  const device = metadata?.devices.find(item => item.id === deviceId);
  return device?.samples?.find(sample => sample.id === sampleId)?.label ?? fallback;
}

function getProductionMetrics(dailyData: Record<string, DailyData>, metadata: SolarMetadata | null) {
  const metadataMetrics = metadata?.devices
    .filter(device => PRODUCTION_DEVICE_TYPES.has(device.type))
    .map((device, index) => ({
      id: device.id,
      label: device.label,
      color: PRODUCTION_COLOR_BY_ID[device.id] ?? PRODUCTION_COLORS[index % PRODUCTION_COLORS.length],
      kind: "production" as const,
      getValue: getProductionValue,
    })) ?? [];

  const metrics = metadataMetrics.length > 0 ? metadataMetrics : FALLBACK_PRODUCTION_METRICS;
  const visibleMetrics = metrics.filter(metric => dailyData[metric.id]);

  if (dailyData[TOTAL_FV_METRIC.id] && !visibleMetrics.some(metric => metric.id === TOTAL_FV_METRIC.id)) {
    visibleMetrics.push(TOTAL_FV_METRIC);
  }

  return visibleMetrics;
}

function getConsumptionMetrics(dailyData: Record<string, DailyData>) {
  return CONSUMPTION_METRICS.filter(metric => dailyData[metric.id]);
}

function buildSeries(dailyData: Record<string, DailyData>, metrics: Metric[]) {
  const timestamps = new Set<string>();
  const series: Record<string, Record<string, number>> = {};

  for (const metric of metrics) {
    const daily = dailyData[metric.id];
    if (!daily) continue;

    const values: Record<string, number> = {};
    for (const [timestamp, interval] of Object.entries(daily.intervals)) {
      const value = metric.getValue(interval);
      if (typeof value === "number" && Number.isFinite(value)) {
        values[timestamp] = value;
        timestamps.add(timestamp);
      }
    }

    if (Object.keys(values).length > 0) {
      series[metric.id] = values;
    }
  }

  const sortedTimestamps = Array.from(timestamps).sort((a, b) => Number(a) - Number(b));
  return { sortedTimestamps, series };
}

function getLabels(dailyData: Record<string, DailyData>, metrics: Metric[], timestamps: string[]) {
  const refMetric = metrics.find(metric => dailyData[metric.id]);
  return timestamps.map(timestamp => {
    const interval = refMetric ? dailyData[refMetric.id]?.intervals[timestamp] : null;
    return interval?.iso_time.slice(11, 16) ?? "";
  });
}

function createOptions(title: string): ChartOptions<"line"> {
  const baseOptions = createLineChartOptions();
  const textColor = readCssVar("--chart-text", "#647081");
  const isSmallScreen = typeof window !== "undefined" && window.innerWidth < 640;

  return {
    ...baseOptions,
    plugins: {
      ...baseOptions.plugins,
      legend: {
        ...baseOptions.plugins?.legend,
        position: "top",
        align: "start",
        labels: {
          color: textColor,
          usePointStyle: true,
          boxWidth: 9,
          boxHeight: 9,
          padding: 14,
          font: { size: 11 },
        },
      },
      tooltip: {
        ...baseOptions.plugins?.tooltip,
        callbacks: {
          title(items) {
            return items[0]?.label ? `${title} · ${items[0].label}` : title;
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
          color: textColor,
          maxRotation: 0,
          autoSkip: true,
          maxTicksLimit: isSmallScreen ? 4 : 8,
          padding: 8,
          font: { size: 10 },
        },
        grid: { display: false },
      },
      y: {
        ...(baseOptions.scales?.y ?? {}),
        ticks: {
          color: textColor,
          padding: 8,
          font: { size: 10 },
          callback(value) {
            return formatWatts(Number(value));
          },
        },
        grid: {
          color: undefined,
        },
      },
    },
  };
}

function ChartBlock({
  dailyData,
  metrics,
  metadata,
  title,
}: {
  dailyData: Record<string, DailyData>;
  metrics: Metric[];
  metadata: SolarMetadata | null;
  title: string;
}) {
  const { sortedTimestamps, series } = buildSeries(dailyData, metrics);

  if (sortedTimestamps.length === 0) {
    return (
      <div className="rounded border border-[color:var(--border)] bg-[color:var(--panel)] p-4">
        <h3 className="text-sm font-semibold" style={{ color: "var(--text-h)" }}>{title}</h3>
        <div className="flex h-64 items-center justify-center text-xs" style={{ color: "var(--text-soft)" }}>
          Sin datos
        </div>
      </div>
    );
  }

  const labels = getLabels(dailyData, metrics, sortedTimestamps);
  const chartData = {
    labels,
    datasets: metrics.filter(metric => series[metric.id]).map(metric => {
      const label = metric.kind === "production" && !metric.id.startsWith("victron")
        ? getDeviceLabel(metadata, metric.id, metric.label)
        : getVictronSampleLabel(metadata, metric.id, metric.label);

      return {
        label,
        data: sortedTimestamps.map(timestamp => series[metric.id]?.[timestamp] ?? null),
        borderColor: metric.color,
        backgroundColor: `${metric.color}18`,
        tension: 0.28,
        pointRadius: 0,
        pointHitRadius: 8,
        borderWidth: 2,
        fill: true,
      };
    }),
  };

  return (
    <div className="rounded border border-[color:var(--border)] bg-[color:var(--panel)] p-4">
      <h3 className="text-sm font-semibold" style={{ color: "var(--text-h)" }}>{title}</h3>
      <div className="mt-2" style={{ height: "18rem" }}>
        <Line data={chartData} options={createOptions(title)} />
      </div>
    </div>
  );
}

export default function EnergyFlowChart({ dailyData, metadata }: Props) {
  const productionMetrics = getProductionMetrics(dailyData, metadata);
  const consumptionMetrics = getConsumptionMetrics(dailyData);

  if (productionMetrics.length === 0 && consumptionMetrics.length === 0) {
    return null;
  }

  return (
    <div className="flex flex-col gap-y-3">
      <h2 className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--text-soft)" }}>
        Vista global
      </h2>
      <div className="grid grid-cols-1 gap-3">
        <ChartBlock
          dailyData={dailyData}
          metrics={productionMetrics}
          metadata={metadata}
          title="Producción"
        />
        <ChartBlock
          dailyData={dailyData}
          metrics={consumptionMetrics}
          metadata={metadata}
          title="Consumo"
        />
      </div>
    </div>
  );
}
