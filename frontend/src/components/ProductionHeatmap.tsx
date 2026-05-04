import { useState, useRef, type PointerEvent } from "react";
import type { HistoryEntry } from "../types";

interface HeatmapCell {
  date: string;
  totalWh: number | null;
  level: 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7;
  inRange: boolean;
}

interface HeatmapWeek {
  label: string;
  cells: HeatmapCell[];
}

interface Props {
  data: HistoryEntry[];
  selectedDate: string;
  onSelectDate: (date: string) => void;
}

const MONTH_LABELS = [
  "Ene",
  "Feb",
  "Mar",
  "Abr",
  "May",
  "Jun",
  "Jul",
  "Ago",
  "Sep",
  "Oct",
  "Nov",
  "Dic"
];

const CELL_LEVEL_CLASSES: Record<HeatmapCell["level"], string> = {
  0: "bg-[#d4d9df]",
  1: "bg-[#ef6b5e]",
  2: "bg-[#e8844a]",
  3: "bg-[#f0a050]",
  4: "bg-[#e8b848]",
  5: "bg-[#f0d060]",
  6: "bg-[#a8c878]",
  7: "bg-[#59b79d]"
};

function parseDate(value: string) {
  const [year, month, day] = value.split("-").map(Number);
  return new Date(year, month - 1, day);
}

function formatDate(date: Date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function addDays(date: Date, amount: number) {
  const result = new Date(date);
  result.setDate(result.getDate() + amount);
  return result;
}

function startOfWeek(date: Date) {
  const result = new Date(date);
  const day = result.getDay();
  const diff = day === 0 ? -6 : 1 - day;
  result.setDate(result.getDate() + diff);
  return result;
}

function endOfWeek(date: Date) {
  return addDays(startOfWeek(date), 6);
}

function getLevel(totalWh: number, maxWh: number): HeatmapCell["level"] {
  if (maxWh <= 0 || totalWh <= 0) {
    return 0;
  }

  const ratio = totalWh / maxWh;

  if (ratio >= 0.86) return 7;
  if (ratio >= 0.72) return 6;
  if (ratio >= 0.58) return 5;
  if (ratio >= 0.44) return 4;
  if (ratio >= 0.30) return 3;
  if (ratio >= 0.16) return 2;
  return 1;
}

function formatProduction(totalWh: number | null) {
  if (typeof totalWh !== "number") {
    return "Sin datos";
  }

  return new Intl.NumberFormat("es-ES", {
    maximumFractionDigits: totalWh >= 1000 ? 2 : 0
  }).format(totalWh >= 1000 ? totalWh / 1000 : totalWh) + (totalWh >= 1000 ? " kWh" : " Wh");
}

function formatLongDate(value: string) {
  return new Intl.DateTimeFormat("es-ES", {
    day: "numeric",
    month: "long",
    year: "numeric"
  }).format(parseDate(value));
}

function buildWeeks(data: HistoryEntry[]): HeatmapWeek[] {
  if (data.length === 0) {
    return [];
  }

  const sortedData = [...data].sort((left, right) => left.date.localeCompare(right.date));
  const totalsByDate = new Map(sortedData.map(entry => [entry.date, entry.total_wh]));
  const firstDate = parseDate(sortedData[0].date);
  const today = new Date();
  const yearStart = new Date(firstDate.getFullYear(), 0, 1);
  const startDate = startOfWeek(yearStart);
  const endDate = endOfWeek(today);
  const maxWh = Math.max(...sortedData.map(entry => entry.total_wh), 0);
  const weeks: HeatmapWeek[] = [];
  let cursor = new Date(startDate);
  let currentMonth = -1;

  while (cursor <= endDate) {
    const cells: HeatmapCell[] = [];
    let label = "";

    for (let dayIndex = 0; dayIndex < 7; dayIndex += 1) {
      const key = formatDate(cursor);
      const totalWh = totalsByDate.get(key) ?? null;
      const inRange = key >= sortedData[0].date && key <= sortedData[sortedData.length - 1].date;

      if (inRange && cursor.getMonth() !== currentMonth) {
        currentMonth = cursor.getMonth();
        label = MONTH_LABELS[currentMonth];
      }

      cells.push({
        date: key,
        totalWh,
        level: typeof totalWh === "number" ? getLevel(totalWh, maxWh) : 0,
        inRange
      });

      cursor = addDays(cursor, 1);
    }

    weeks.push({ label, cells });
  }

  return weeks;
}

interface TooltipState {
  x: number;
  y: number;
  text: string;
}

export default function ProductionHeatmap({ data, selectedDate, onSelectDate }: Props) {
  const [tooltip, setTooltip] = useState<TooltipState | null>(null);
  const hideTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const weeks = buildWeeks(data);

  if (weeks.length === 0) {
    return null;
  }

  function showTooltip(e: PointerEvent, label: string) {
    clearTimeout(hideTimer.current);
    setTooltip({ x: e.clientX, y: e.clientY, text: label });
  }

  function hideTooltip() {
    hideTimer.current = setTimeout(() => setTooltip(null), 80);
  }

  return (
    <>
      <div
        className="flex items-center justify-end gap-1 text-[0.55rem] font-medium text-[color:var(--text-soft)]"
        aria-hidden="true"
      >
        <span>Menos</span>
        <span className="size-2 rounded-[1.5px] bg-[#d4d9df]" />
        <span className="size-2 rounded-[1.5px] bg-[#ef6b5e]" />
        <span className="size-2 rounded-[1.5px] bg-[#e8844a]" />
        <span className="size-2 rounded-[1.5px] bg-[#f0a050]" />
        <span className="size-2 rounded-[1.5px] bg-[#e8b848]" />
        <span className="size-2 rounded-[1.5px] bg-[#f0d060]" />
        <span className="size-2 rounded-[1.5px] bg-[#a8c878]" />
        <span className="size-2 rounded-[1.5px] bg-[#59b79d]" />
        <span>Más</span>
      </div>
      <div
        className="border border-[#e1e4e8] p-1.5 md:p-2"
      >
        <div className="overflow-x-auto" role="grid" aria-label="Mapa de calor de producción diaria">
        <div className="flex gap-[3px] md:gap-[4px]">
          {weeks.map(week => (
            <div
              key={week.cells[0].date}
              className="grid grid-rows-[repeat(7,10px)] gap-[3px] md:grid-rows-[repeat(7,12px)] md:gap-[4px]"
              role="rowgroup"
            >
              {week.cells.map(cell => {
                const isSelectable = typeof cell.totalWh === "number";
                const className = [
                  "size-2.5 md:size-3",
                  CELL_LEVEL_CLASSES[cell.level],
                  isSelectable ? "cursor-pointer" : "cursor-default",
                  !cell.inRange || !isSelectable ? "opacity-35" : "",
                  cell.date === selectedDate ? "ring-2 ring-amber-500" : "",
                ]
                  .filter(Boolean)
                  .join(" ");

                const label = `${formatLongDate(cell.date)}: ${formatProduction(cell.totalWh)}`;

                return (
                  <button
                    key={cell.date}
                    type="button"
                    className={className}
                    onClick={() => isSelectable && onSelectDate(cell.date)}
                    disabled={!isSelectable}
                    onPointerEnter={e => showTooltip(e, label)}
                    onPointerMove={e => showTooltip(e, label)}
                    onPointerLeave={hideTooltip}
                    aria-pressed={cell.date === selectedDate}
                    aria-label={label}
                  />
                );
              })}
            </div>
          ))}
        </div>
        </div>
      </div>
      {tooltip && (
        <span
          className="pointer-events-none fixed z-50 rounded-md bg-gray-800 px-2 py-1 text-xs font-medium text-gray-100 whitespace-nowrap"
          style={{ left: tooltip.x, top: tooltip.y - 28 }}
        >
          {tooltip.text}
        </span>
      )}
    </>
  );
}
