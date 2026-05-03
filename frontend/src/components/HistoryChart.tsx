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
import type { HistoryEntry } from "../types";
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
  data: HistoryEntry[];
}

export default function HistoryChart({ data }: Props) {
  const options: ChartOptions<"line"> = createLineChartOptions();
  const labels = data.map(d => d.date);

  const chartData = {
    labels,
    datasets: [
      {
        label: "Wh generados",
        data: data.map(d => d.total_wh),
        borderColor: "#90b7aa",
        backgroundColor: "rgba(144, 183, 170, 0.18)",
        tension: 0.25,
        pointRadius: 3,
        pointHoverRadius: 5,
        borderWidth: 3
      }
    ]
  };

  return <Line data={chartData} options={options} />;
}