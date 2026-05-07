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

  const labels = intervals.map(i => i.iso_time.slice(11, 16));

  const chartData = {
    labels,
    datasets: [
      {
        label: "Total W",
        data: intervals.map(i => i.total_w),
        borderColor: "#7bb9a4",
        backgroundColor: "rgba(123, 185, 164, 0.18)",
        tension: 0.28,
        pointRadius: 0,
        borderWidth: 3
      },
      {
        label: "P1",
        data: intervals.map(i => i.p1),
        borderColor: "#aab7c8",
        backgroundColor: "rgba(170, 183, 200, 0.18)",
        tension: 0.28,
        pointRadius: 0,
        borderWidth: 2
      },
      {
        label: "P2",
        data: intervals.map(i => i.p2),
        borderColor: "#d8b7a2",
        backgroundColor: "rgba(216, 183, 162, 0.18)",
        tension: 0.28,
        pointRadius: 0,
        borderWidth: 2
      }
    ]
  };

  return <Line data={chartData} options={options} />;
}