import type { DailyData, Interval, SolarMetadata } from "./types";
import { nearestLabelIndex } from "./components/chartMarker";

const PRODUCTION_DEVICE_TYPES = new Set(["apsystems", "goodwe_sems"]);
const FALLBACK_PREFIXES = ["apsystems", "goodwe"];

function intervalWatts(interval: Interval): number | null {
  if (typeof interval.total_w === "number") return interval.total_w;
  if (typeof interval.p1 === "number" && typeof interval.p2 === "number") return interval.p1 + interval.p2;
  return null;
}

/** Potencia total de los inversores (W) en el intervalo más cercano a `time` ("HH:MM"). */
export function productionAt(
  dailyData: Record<string, DailyData>,
  metadata: SolarMetadata | null,
  time: string,
): number | null {
  const ids = metadata?.devices.length
    ? metadata.devices.filter(d => PRODUCTION_DEVICE_TYPES.has(d.type)).map(d => d.id)
    : Object.keys(dailyData).filter(id => FALLBACK_PREFIXES.some(prefix => id.startsWith(prefix)));

  let total: number | null = null;
  for (const id of ids) {
    const intervals = Object.values(dailyData[id]?.intervals ?? {});
    const index = nearestLabelIndex(intervals.map(i => i.iso_time?.slice(11, 16) ?? ""), time);
    if (index < 0) continue;
    const watts = intervalWatts(intervals[index]);
    if (watts !== null) total = (total ?? 0) + watts;
  }
  return total;
}
