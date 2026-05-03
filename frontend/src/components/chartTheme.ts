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
  const textColor = readCssVar("--chart-text", "#556070");
  const gridColor = readCssVar("--chart-grid", "rgba(201, 210, 218, 0.65)");
  const tooltipBackground = readCssVar("--chart-tooltip-bg", "rgba(255, 255, 255, 0.96)");
  const tooltipText = readCssVar("--chart-tooltip-text", "#334155");
  const tooltipBorder = readCssVar("--chart-tooltip-border", "rgba(203, 213, 225, 0.9)");

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
        borderColor: tooltipBorder,
        borderWidth: 1,
        displayColors: true,
        padding: 12,
        titleMarginBottom: 8,
        cornerRadius: 14
      }
    },
    scales: {
      x: {
        ticks: {
          color: textColor,
          maxRotation: 0,
          autoSkip: true,
          maxTicksLimit: 10,
          padding: 10
        },
        border: {
          display: false
        },
        grid: {
          color: gridColor
        }
      },
      y: {
        ticks: {
          color: textColor,
          padding: 10
        },
        border: {
          display: false
        },
        grid: {
          color: gridColor
        }
      }
    }
  };
}