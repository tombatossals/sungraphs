import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { ChartSkeleton } from "../components/Skeleton";

describe("ChartSkeleton", () => {
  it("renders without crashing", () => {
    const { container } = render(<ChartSkeleton />);
    expect(container.firstChild).toBeInTheDocument();
  });

  it("contains animate-pulse class", () => {
    render(<ChartSkeleton />);
    const pulseElements = document.querySelectorAll(".animate-pulse");
    expect(pulseElements.length).toBeGreaterThanOrEqual(1);
  });
});
