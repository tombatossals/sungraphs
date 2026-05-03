import { Line } from "react-chartjs-2";
import {
  Chart as ChartJS,
  type ChartOptions,
  LineElement,
  PointElement,
  LinearScale,
  CategoryScale,
  Legend,
  Tooltip
} from "chart.js";
import type { DailyData } from "../types";
import { createLineChartOptions } from "./chartTheme";

ChartJS.register(
  LineElement,
  PointElement,
  LinearScale,
  CategoryScale,
  Legend,
  Tooltip
);

interface Props {
  data: DailyData;
}

export default function DailyChart({ data }: Props) {
  const options: ChartOptions<"line"> = createLineChartOptions();
  const intervals = Object.values(data.intervals).filter(
    interval =>
      typeof interval.total_w === "number" &&
      typeof interval.p1 === "number" &&
      typeof interval.p2 === "number"
  );

  const labels = intervals.map(i => i.timestamp_iso.slice(11, 16));

  const chartData = {
    labels,
    datasets: [
      {
        label: "Total W",
        data: intervals.map(i => i.total_w),
        borderColor: "#f97316",
        backgroundColor: "rgba(249, 115, 22, 0.18)",
        tension: 0.28,
        pointRadius: 0,
        borderWidth: 3
      },
      {
        label: "P1",
        data: intervals.map(i => i.p1),
        borderColor: "#0f766e",
        backgroundColor: "rgba(15, 118, 110, 0.18)",
        tension: 0.28,
        pointRadius: 0,
        borderWidth: 2
      },
      {
        label: "P2",
        data: intervals.map(i => i.p2),
        borderColor: "#2563eb",
        backgroundColor: "rgba(37, 99, 235, 0.18)",
        tension: 0.28,
        pointRadius: 0,
        borderWidth: 2
      }
    ]
  };

  return <Line data={chartData} options={options} />;
}