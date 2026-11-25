import { describe, it, expect } from "vitest";
import { nearestLabelIndex } from "../components/chartMarker";

describe("nearestLabelIndex", () => {
  const labels = ["10:00", "10:10", "10:20"];

  it("picks the closest earlier label", () => {
    expect(nearestLabelIndex(labels, "10:14")).toBe(1);
  });

  it("picks the closest later label", () => {
    expect(nearestLabelIndex(labels, "10:16")).toBe(2);
  });

  it("clamps to the last label", () => {
    expect(nearestLabelIndex(labels, "23:00")).toBe(2);
  });

  it("returns -1 for empty labels", () => {
    expect(nearestLabelIndex([], "10:00")).toBe(-1);
  });

  it("ignores empty labels", () => {
    expect(nearestLabelIndex(["", "10:10", ""], "10:00")).toBe(1);
    expect(nearestLabelIndex(["", ""], "10:00")).toBe(-1);
  });
});
