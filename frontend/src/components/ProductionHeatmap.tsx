import type { CSSProperties } from "react";
import type { HistoryEntry } from "../types";

interface HeatmapCell {
  date: string;
  totalWh: number | null;
  level: 0 | 1 | 2 | 3 | 4;
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

const WEEKDAY_LABELS = ["L", "M", "X", "J", "V", "S", "D"];
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
  0: "bg-[#eef2f4]",
  1: "bg-[#dff2eb]",
  2: "bg-[#bae6d2]",
  3: "bg-[#85d2ba]",
  4: "bg-[#59b79d]"
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

function getLevel(totalWh: number, maxWh: number): 0 | 1 | 2 | 3 | 4 {
  if (maxWh <= 0 || totalWh <= 0) {
    return 0;
  }

  const ratio = totalWh / maxWh;

  if (ratio >= 0.8) {
    return 4;
  }

  if (ratio >= 0.55) {
    return 3;
  }

  if (ratio >= 0.3) {
    return 2;
  }

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
  const lastDate = parseDate(sortedData[sortedData.length - 1].date);
  const startDate = startOfWeek(firstDate);
  const endDate = endOfWeek(lastDate);
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

export default function ProductionHeatmap({ data, selectedDate, onSelectDate }: Props) {
  const weeks = buildWeeks(data);
  const selectedEntry = data.find(entry => entry.date === selectedDate) ?? null;
  const heatmapStyle = { "--heatmap-weeks": weeks.length } as CSSProperties;

  if (weeks.length === 0) {
    return null;
  }

  return (
    <section
      className="mb-0 rounded-[30px] border border-[color:var(--panel-border)] bg-[color:var(--panel)] p-5 text-left shadow-[0_24px_60px_rgba(148,163,184,0.14),inset_0_1px_0_rgba(255,255,255,0.88)] md:p-6"
      aria-label="Calendario de produccion solar"
    >
      <div className="mb-[18px] flex flex-col gap-5 md:flex-row md:items-start md:justify-between">
        <div>
          <p className="mb-3 text-[0.72rem] font-semibold uppercase tracking-[0.24em] text-[color:var(--text-soft)]">
            Selector de fecha
          </p>
          <h2 className="mb-2 text-[30px] font-medium tracking-[-0.05em] text-[color:var(--text-h)] md:text-[34px]">
            Calendario de producción
          </h2>
          <p className="max-w-[28rem] text-[0.98rem] leading-7 text-[color:var(--text)]">
            Pulsa un día para cargar su curva de producción.
          </p>
        </div>
        <div
          className="flex min-w-0 flex-col gap-1 rounded-[22px] border border-[color:var(--panel-border)] bg-[color:var(--panel-muted)] px-4 py-3 text-[color:var(--text-h)] shadow-[inset_0_1px_0_rgba(255,255,255,0.78)] md:min-w-[220px] md:items-end"
          aria-live="polite"
        >
          <span className="text-[0.72rem] font-semibold uppercase tracking-[0.24em] text-[color:var(--text-soft)]">
            Producción activa
          </span>
          <strong className="text-[1.4rem] font-medium leading-none tracking-[-0.04em]">
            {selectedEntry ? formatProduction(selectedEntry.total_wh) : "Selecciona un día"}
          </strong>
          <span className="text-[0.95rem] text-[color:var(--text)]">
            {selectedEntry ? formatLongDate(selectedEntry.date) : ""}
          </span>
        </div>
      </div>

      <div
        className="rounded-[24px] border border-[color:var(--panel-border)] bg-[color:var(--panel-muted)] p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.75)] overflow-x-auto"
        role="grid"
        aria-label="Mapa de calor de producción diaria"
        style={heatmapStyle}
      >
        <div
          className="mb-3 grid min-w-max grid-cols-[22px_repeat(var(--heatmap-weeks),14px)] gap-[5px] text-left text-[0.72rem] font-medium leading-none text-[color:var(--text-soft)] md:grid-cols-[22px_repeat(var(--heatmap-weeks),16px)] md:gap-[6px]"
          aria-hidden="true"
        >
          <span />
          {weeks.map(week => (
            <span key={`${week.label}-${week.cells[0].date}`}>
              {week.label}
            </span>
          ))}
        </div>

        <div className="flex min-w-max gap-2 md:gap-[10px]">
          <div
            className="grid grid-rows-[repeat(7,14px)] gap-[5px] pt-px text-[0.72rem] font-medium text-[color:var(--text-soft)] md:grid-rows-[repeat(7,16px)] md:gap-[6px]"
            aria-hidden="true"
          >
            {WEEKDAY_LABELS.map(label => (
              <span key={label} className="flex w-[22px] items-center justify-center">
                {label}
              </span>
            ))}
          </div>

          <div className="flex gap-[5px] md:gap-[6px]">
            {weeks.map(week => (
              <div
                key={week.cells[0].date}
                className="grid grid-rows-[repeat(7,14px)] gap-[5px] md:grid-rows-[repeat(7,16px)] md:gap-[6px]"
                role="rowgroup"
              >
                {week.cells.map(cell => {
                  const isSelectable = typeof cell.totalWh === "number";
                  const className = [
                    "size-3.5 rounded-[6px] border border-white/70 shadow-[inset_0_1px_0_rgba(255,255,255,0.55)] transition duration-150 ease-out md:size-4",
                    CELL_LEVEL_CLASSES[cell.level],
                    isSelectable ? "cursor-pointer hover:-translate-y-px hover:shadow-[0_10px_18px_rgba(148,163,184,0.22)] focus-visible:-translate-y-px" : "cursor-default",
                    !cell.inRange || !isSelectable ? "opacity-35" : "",
                    cell.date === selectedDate
                      ? "ring-2 ring-[#9ccfbe] ring-offset-2 ring-offset-[color:var(--panel-muted)]"
                      : "",
                    isSelectable
                      ? "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#c7ddd5] focus-visible:ring-offset-2 focus-visible:ring-offset-[color:var(--panel-muted)]"
                      : ""
                  ]
                    .filter(Boolean)
                    .join(" ");

                  return (
                    <button
                      key={cell.date}
                      type="button"
                      className={className}
                      onClick={() => isSelectable && onSelectDate(cell.date)}
                      disabled={!isSelectable}
                      aria-pressed={cell.date === selectedDate}
                      aria-label={`${formatLongDate(cell.date)}: ${formatProduction(cell.totalWh)}`}
                      title={`${formatLongDate(cell.date)}: ${formatProduction(cell.totalWh)}`}
                    />
                  );
                })}
              </div>
            ))}
          </div>
        </div>
      </div>

      <div
        className="mt-4 flex flex-wrap items-center justify-start gap-2 text-[0.78rem] font-medium text-[color:var(--text-soft)] md:justify-end"
        aria-hidden="true"
      >
        <span>Menos</span>
        <span className="size-3.5 rounded-[6px] bg-[#eef2f4] md:size-4" />
        <span className="size-3.5 rounded-[6px] bg-[#dff2eb] md:size-4" />
        <span className="size-3.5 rounded-[6px] bg-[#bae6d2] md:size-4" />
        <span className="size-3.5 rounded-[6px] bg-[#85d2ba] md:size-4" />
        <span className="size-3.5 rounded-[6px] bg-[#59b79d] md:size-4" />
        <span>Más</span>
      </div>
    </section>
  );
}