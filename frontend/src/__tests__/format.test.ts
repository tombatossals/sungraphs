import { describe, it, expect } from "vitest";
import { formatProduction, formatDisplayDate, formatCO2 } from "../format";

describe("formatProduction", () => {
  it("returns 'Sin datos' for null", () => {
    expect(formatProduction(null)).toBe("Sin datos");
  });

  it("returns 'Sin datos' for undefined", () => {
    expect(formatProduction(undefined)).toBe("Sin datos");
  });

  it("formats Wh values", () => {
    expect(formatProduction(500)).toBe("500 Wh");
  });

  it("formats kWh values", () => {
    const result = formatProduction(1500);
    expect(result).toContain("kWh");
    expect(result).toContain("1,50");
  });
});

describe("formatDisplayDate", () => {
  it("formats a date in Spanish locale", () => {
    const result = formatDisplayDate("2026-05-03");
    expect(result).toContain("may");
    expect(result).toContain("2026");
  });
});

describe("formatCO2", () => {
  it("formats kg values", () => {
    expect(formatCO2(500)).toBe("500.0 kg");
  });

  it("formats tonne values", () => {
    expect(formatCO2(1500)).toBe("1.50 t");
  });
});
