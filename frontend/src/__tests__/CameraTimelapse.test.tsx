import { describe, it, expect, vi, afterEach } from "vitest";
import { cleanup, render, screen, fireEvent, waitFor } from "@testing-library/react";
import CameraTimelapse from "../components/CameraTimelapse";

const INDEX = {
  date: "2026-11-25",
  images: [
    { time: "08:00", ts: 1, file: "0800.jpg" },
    { time: "12:00", ts: 2, file: "1200.jpg" },
    { time: "16:00", ts: 3, file: "1600.jpg" },
  ],
};

function mockFetch(ok: boolean, body: unknown = INDEX) {
  vi.stubGlobal("fetch", vi.fn(() => Promise.resolve({ ok, json: () => Promise.resolve(body) })));
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("CameraTimelapse", () => {
  it("renders nothing when index missing", async () => {
    mockFetch(false);
    const { container } = render(<CameraTimelapse date="2026-11-25" onTimeChange={() => {}} />);
    await waitFor(() => expect(fetch).toHaveBeenCalled());
    expect(container).toBeEmptyDOMElement();
  });

  it("renders nothing when server answers HTML instead of JSON (SPA fallback)", async () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve({ ok: true, json: () => Promise.reject(new SyntaxError("html")) })));
    const { container } = render(<CameraTimelapse date="2026-01-01" onTimeChange={() => {}} />);
    await waitFor(() => expect(fetch).toHaveBeenCalled());
    await new Promise(r => setTimeout(r, 0));
    expect(container).toBeEmptyDOMElement();
  });

  it("shows the latest image as thumbnail", async () => {
    mockFetch(true);
    render(<CameraTimelapse date="2026-11-25" onTimeChange={() => {}} />);
    const img = await screen.findByRole("img", { name: /16:00/ });
    expect(img).toHaveAttribute("src", "/data/camera/2026-11-25/1600.jpg");
  });

  it("opens viewer, scrubs and reports time, closes", async () => {
    mockFetch(true);
    const onTimeChange = vi.fn();
    render(<CameraTimelapse date="2026-11-25" onTimeChange={onTimeChange} />);
    fireEvent.click(await screen.findByRole("button", { name: /ver evolución/i }));

    const slider = screen.getByRole("slider");
    expect(slider).toHaveAttribute("max", "2");

    fireEvent.change(slider, { target: { value: "0" } });
    expect(onTimeChange).toHaveBeenLastCalledWith("08:00");
    expect(screen.getByRole("img", { name: /08:00/ })).toHaveAttribute(
      "src",
      "/data/camera/2026-11-25/0800.jpg",
    );

    fireEvent.click(screen.getByRole("button", { name: /cerrar/i }));
    expect(onTimeChange).toHaveBeenLastCalledWith(null);
  });
});
