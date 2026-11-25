import { describe, it, expect, vi, afterEach } from "vitest";
import { cleanup, render } from "@testing-library/react";

const lineProps: Array<{ options: { plugins?: Record<string, unknown> } }> = [];
vi.mock("react-chartjs-2", () => ({
  Line: (props: { options: { plugins?: Record<string, unknown> } }) => {
    lineProps.push(props);
    return null;
  },
}));

import EnergyFlowChart from "../components/EnergyFlowChart";
import { timeMarkerPlugin } from "../components/chartMarker";

const dailyData = {
  goodwe1: {
    date: "2026-11-10",
    intervals: {
      "1": { iso_time: "2026-11-10T10:00:00", total_w: 100 },
      "2": { iso_time: "2026-11-10T10:10:00", total_w: 200 },
      "3": { iso_time: "2026-11-10T10:20:00", total_w: 300 },
    },
  },
};

afterEach(() => {
  cleanup();
  lineProps.length = 0;
});

describe("production chart marker", () => {
  it("passes the marker index through options so updates reach the chart", () => {
    const { rerender } = render(<EnergyFlowChart dailyData={dailyData} metadata={null} markerTime={null} />);
    rerender(<EnergyFlowChart dailyData={dailyData} metadata={null} markerTime="10:12" />);
    const last = lineProps[lineProps.length - 1];
    expect(last.options.plugins?.cameraTimeMarker).toMatchObject({ index: 1 });
  });

  it("plugin draws at the index read from chart options", () => {
    const ctx = { save: vi.fn(), restore: vi.fn(), beginPath: vi.fn(), moveTo: vi.fn(), lineTo: vi.fn(), stroke: vi.fn(), setLineDash: vi.fn() };
    const chart = {
      ctx,
      chartArea: { top: 0, bottom: 100 },
      scales: { x: { getPixelForValue: (i: number) => i * 10 } },
      options: { plugins: { cameraTimeMarker: { index: 2, color: "#000" } } },
    };
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (timeMarkerPlugin.afterDatasetsDraw as any)(chart, {}, chart.options.plugins.cameraTimeMarker);
    expect(ctx.moveTo).toHaveBeenCalledWith(20, 0);
  });
});
