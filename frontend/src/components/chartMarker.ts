import type { ChartType, Plugin } from "chart.js";

function toMinutes(hhmm: string): number | null {
  const m = /^(\d{2}):(\d{2})$/.exec(hhmm);
  return m ? Number(m[1]) * 60 + Number(m[2]) : null;
}

/** Índice del label "HH:MM" más cercano a `time`; -1 si no hay labels válidos. */
export function nearestLabelIndex(labels: string[], time: string): number {
  const target = toMinutes(time);
  if (target === null) return -1;
  let best = -1;
  let bestDiff = Infinity;
  labels.forEach((label, i) => {
    const minutes = toMinutes(label);
    if (minutes === null) return;
    const diff = Math.abs(minutes - target);
    if (diff < bestDiff) {
      best = i;
      bestDiff = diff;
    }
  });
  return best;
}

export interface TimeMarkerOptions {
  index: number;
  color: string;
}

declare module "chart.js" {
  interface PluginOptionsByType<TType extends ChartType> {
    cameraTimeMarker?: TimeMarkerOptions & { _t?: TType };
  }
}

/**
 * Plugin estable (registrado una vez) que dibuja una línea vertical discontinua.
 * Lee el índice de options.plugins.cameraTimeMarker: react-chartjs-2 sí propaga
 * los cambios de options, pero no los de la prop `plugins`.
 */
export const timeMarkerPlugin: Plugin<"line", TimeMarkerOptions> = {
  id: "cameraTimeMarker",
  defaults: { index: -1, color: "#647081" },
  afterDatasetsDraw(chart, _args, opts) {
    const index = opts?.index ?? -1;
    if (index < 0) return;
    const { ctx, chartArea, scales } = chart;
    const x = scales.x.getPixelForValue(index);
    ctx.save();
    ctx.strokeStyle = opts.color;
    ctx.lineWidth = 1.5;
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.moveTo(x, chartArea.top);
    ctx.lineTo(x, chartArea.bottom);
    ctx.stroke();
    ctx.restore();
  },
};
