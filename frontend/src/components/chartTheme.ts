import type { ChartOptions } from "chart.js";

function readCssVar(name: string, fallback: string) {
  if (typeof window === "undefined") {
    return fallback;
  }

  const value = window.getComputedStyle(document.documentElement)
    .getPropertyValue(name)
    .trim();

  return value || fallback;
}

export function createLineChartOptions(): ChartOptions<"line"> {
  const textColor = readCssVar("--chart-text", "#1f2937");
  const gridColor = readCssVar("--chart-grid", "rgba(148, 163, 184, 0.2)");
  const tooltipBackground = readCssVar("--chart-tooltip-bg", "#0f172a");
  const tooltipText = readCssVar("--chart-tooltip-text", "#f8fafc");

  return {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      mode: "index",
      intersect: false
    },
    plugins: {
      legend: {
        labels: {
          color: textColor,
          usePointStyle: true,
          boxWidth: 10,
          boxHeight: 10,
          padding: 18
        }
      },
      tooltip: {
        backgroundColor: tooltipBackground,
        titleColor: tooltipText,
        bodyColor: tooltipText,
        displayColors: true,
        padding: 12
      }
    },
    scales: {
      x: {
        ticks: {
          color: textColor,
          maxRotation: 0,
          autoSkip: true,
          maxTicksLimit: 10
        },
        grid: {
          color: gridColor
        }
      },
      y: {
        ticks: {
          color: textColor
        },
        grid: {
          color: gridColor
        }
      }
    }
  };
}