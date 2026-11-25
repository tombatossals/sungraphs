import { describe, it, expect } from "vitest";
import { cameraImageUrl } from "../camera";

describe("cameraImageUrl", () => {
  it("builds the static path for a day image", () => {
    expect(cameraImageUrl("2026-11-25", "1210.jpg")).toBe("/data/camera/2026-11-25/1210.jpg");
  });
});
