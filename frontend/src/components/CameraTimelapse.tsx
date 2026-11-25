import { useEffect, useMemo, useState } from "react";
import { cameraImageUrl, useCameraIndex } from "../camera";

interface Props {
  date: string;
  onTimeChange: (time: string | null) => void;
  powerAt?: (time: string) => number | null;
}

function formatWatts(value: number): string {
  return Math.abs(value) >= 1000 ? `${(value / 1000).toFixed(1)} kW` : `${Math.round(value)} W`;
}

const FRAME_MS = 250;

// Montar con key={date}: al cambiar de día se reinicia el visor.
export default function CameraTimelapse({ date, onTimeChange, powerAt }: Props) {
  const index = useCameraIndex(date);
  const [open, setOpen] = useState(false);
  const [pos, setPos] = useState(0);
  const [playing, setPlaying] = useState(false);

  const images = useMemo(() => index?.images ?? [], [index]);
  const last = images.length - 1;

  useEffect(() => {
    if (!open) return;
    images.forEach(img => {
      new Image().src = cameraImageUrl(date, img.file);
    });
  }, [open, date, images]);

  useEffect(() => {
    if (!playing || last < 1) return;
    const id = setInterval(() => {
      setPos(p => {
        const next = p >= last ? 0 : p + 1;
        onTimeChange(images[next].time);
        return next;
      });
    }, FRAME_MS);
    return () => clearInterval(id);
  }, [playing, last, images, onTimeChange]);

  if (!index || images.length === 0) return null;

  const latest = images[last];
  const current = images[Math.min(pos, last)];
  const power = powerAt?.(current.time) ?? null;

  const select = (i: number) => {
    setPos(i);
    onTimeChange(images[i].time);
  };

  const openViewer = () => {
    setOpen(true);
    select(last);
  };

  const close = () => {
    setOpen(false);
    setPlaying(false);
    onTimeChange(null);
  };

  if (!open) {
    return (
      <button
        type="button"
        onClick={openViewer}
        aria-label="Ver evolución del día"
        className="group flex items-center gap-3 self-start rounded border border-[color:var(--border)] bg-[color:var(--panel)] p-2 text-left"
      >
        <img
          src={cameraImageUrl(date, latest.file)}
          alt={`Placas a las ${latest.time}`}
          className="h-16 w-28 rounded object-cover transition-transform group-hover:scale-105"
        />
        <span className="flex flex-col text-xs" style={{ color: "var(--text-soft)" }}>
          <span className="font-semibold" style={{ color: "var(--text-h)" }}>Cámara · {latest.time}</span>
          <span>▶ Ver evolución ({images.length} fotos)</span>
        </span>
      </button>
    );
  }

  return (
    <div className="rounded border border-[color:var(--border)] bg-[color:var(--panel)] p-3">
      <div className="mb-2 flex items-center justify-between">
        <h3 className="text-sm font-semibold" style={{ color: "var(--text-h)" }}>
          Cámara · {current.time}
          {power !== null && (
            <span className="ml-2 font-normal" style={{ color: "var(--text-soft)" }}>
              · {formatWatts(power)}
            </span>
          )}
        </h3>
        <button type="button" onClick={close} aria-label="Cerrar" className="px-2 text-sm" style={{ color: "var(--text-soft)" }}>
          ✕
        </button>
      </div>
      <img
        src={cameraImageUrl(date, current.file)}
        alt={`Placas a las ${current.time}`}
        className="w-full rounded"
      />
      <div className="mt-2 flex items-center gap-3 text-xs" style={{ color: "var(--text-soft)" }}>
        <button
          type="button"
          onClick={() => setPlaying(p => !p)}
          aria-label={playing ? "Pausar" : "Reproducir"}
          className="w-6 text-base"
          style={{ color: "var(--text-h)" }}
        >
          {playing ? "⏸" : "▶"}
        </button>
        <span>{images[0].time}</span>
        <input
          type="range"
          min={0}
          max={last}
          value={Math.min(pos, last)}
          onChange={e => {
            setPlaying(false);
            select(Number(e.target.value));
          }}
          className="flex-1"
          aria-label="Hora de la foto"
        />
        <span>{latest.time}</span>
      </div>
    </div>
  );
}
