import { Line } from "react-chartjs-2";
import {
  Chart as ChartJS,
  type ChartOptions,
  LineElement,
  PointElement,
  LinearScale,
  CategoryScale,
  Filler,
  Tooltip
} from "chart.js";
import type { DailyData, Interval } from "../types";
import { createLineChartOptions } from "./chartTheme";

ChartJS.register(
  LineElement,
  PointElement,
  LinearScale,
  CategoryScale,
  Filler,
  Tooltip
);

interface Props {
  data: DailyData;
  color: string;
  getValue?: (interval: Interval) => number | null;
}

export default function InverterDailyChart({ data, color, getValue }: Props) {
  const intervals = Object.values(data.intervals).filter(interval => {
    if (getValue) {
      const v = getValue(interval);
      return v !== null && v !== undefined && !isNaN(v);
    }
    return typeof interval.p1 === "number" && typeof interval.p2 === "number";
  });

  if (intervals.length === 0) return null;

  const labels = intervals.map(i => i.iso_time.slice(11, 16));
  const values = intervals.map(i => getValue ? (getValue(i) ?? 0) : (i.p1 ?? 0) + (i.p2 ?? 0));

  const baseOptions = createLineChartOptions();

  const options: ChartOptions<"line"> = {
    ...baseOptions,
    plugins: {
      ...baseOptions.plugins,
      legend: { display: false },
    },
    scales: {
      x: {
        ...(baseOptions.scales?.x ?? {}),
        ticks: {
          color: undefined,
          maxRotation: 0,
          autoSkip: true,
          maxTicksLimit: 5,
          padding: 4,
          font: { size: 9 },
        },
        grid: { display: false },
      },
      y: {
        ...(baseOptions.scales?.y ?? {}),
        ticks: {
          color: undefined,
          padding: 4,
          font: { size: 9 },
          maxTicksLimit: 4,
        },
        grid: { display: false },
      },
    },
  };

  const chartData = {
    labels,
    datasets: [
      {
        label: "Potencia",
        data: values,
        borderColor: color,
        backgroundColor: `${color}33`,
        tension: 0.28,
        pointRadius: 0,
        borderWidth: 2,
        fill: true,
      },
    ],
  };

  return (
    <div className="h-32">
      <Line data={chartData} options={options} />
    </div>
  );
}
