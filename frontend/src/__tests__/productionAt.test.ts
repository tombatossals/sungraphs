import { describe, it, expect } from "vitest";
import { productionAt } from "../production";

const dailyData = {
  goodwe1: { date: "d", intervals: {
    "1": { iso_time: "2026-11-10T10:00:00", p1: 50, p2: 50 },
    "2": { iso_time: "2026-11-10T10:10:00", p1: 100, p2: 100 },
  } },
  apsystems1: { date: "d", intervals: {
    "1": { iso_time: "2026-11-10T10:00:00", total_w: 10 },
    "2": { iso_time: "2026-11-10T10:10:00", total_w: 20 },
  } },
  "victron1-fv": { date: "d", intervals: { "2": { iso_time: "2026-11-10T10:10:00", value: 999 } } },
};
const metadata = { devices: [
  { id: "goodwe1", type: "goodwe_sems", label: "G" },
  { id: "apsystems1", type: "apsystems", label: "A" },
  { id: "victron1", type: "victron", label: "V" },
] };

describe("productionAt", () => {
  it("sums production devices at the nearest slot", () => {
    expect(productionAt(dailyData, metadata, "10:08")).toBe(220);
  });
  it("returns null without production data", () => {
    expect(productionAt({}, metadata, "10:00")).toBeNull();
  });
});
