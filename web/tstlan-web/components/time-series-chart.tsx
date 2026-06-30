"use client";

import { useMemo, useState } from "react";
import {
  Brush,
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { XIcon } from "@phosphor-icons/react/ssr";

import {
  firstIndexAtOrAfter,
  lastIndexAtOrBefore,
  toTimeRange,
} from "@/lib/chart-brush";
import { formatTick, niceTimeTicks } from "@/lib/chart-grid";
import { cn } from "@/lib/utils";

export type Sample = { t: number; v: number };

// Одна линия графика: имя переменной, цвет, точки и форматтер значений.
export type ChartSeries = {
  key: string;
  label: string;
  color: string;
  samples: Sample[];
  format: (value: number) => string;
};

// Точки разных переменных сведены в одну строку по серверному времени t.
type Row = { t: number } & Record<string, number>;

type Indicator = {
  id: string;
  label: string;
  color: string;
  compute: (values: number[]) => number;
};

// Задел под индикаторы: новая статистика на графике - это одна запись здесь.
// compute получает значения видимого окна, результат рисуется как ReferenceLine.
// Индикаторы доступны только для одиночной линии, иначе линий было бы слишком много.
const INDICATORS: Indicator[] = [
  { id: "mean", label: "среднее", color: "#0d9488", compute: mean },
  { id: "median", label: "медиана", color: "#d97706", compute: median },
];

export function TimeSeriesChart({
  series,
  windowMs,
  height = 200,
  fill = false,
  onRemoveSeries,
}: {
  series: ChartSeries[];
  windowMs: number | null;
  // Высота встроенного графика; в полноэкранном режиме fill растягивает его на
  // всю доступную высоту, а height игнорируется.
  height?: number;
  fill?: boolean;
  // Вынести линию из совмещённого графика на отдельный (✕ в легенде).
  onRemoveSeries?: (key: string) => void;
}) {
  const single = series.length === 1;
  const [shown, setShown] = useState<ReadonlySet<string>>(() => new Set());
  // Выделение brush храним во времени, а не в индексах: живой поток постоянно
  // дописывает точки и подрезает старые, из-за чего индексы «уезжают» и сбивают
  // выбранный участок. Привязка к t делает окно стабильным. null - весь ряд.
  const [brush, setBrush] = useState<{ startT: number; endT: number } | null>(
    null,
  );
  // Диапазон оси Y. Пустые поля - авто-масштаб по данным; заданные границы
  // фиксируют шкалу, чтобы мелкие колебания не растягивались на всю высоту.
  const [yRange, setYRange] = useState<{ min: string; max: string }>({
    min: "",
    max: "",
  });

  // Смена окна перестраивает ряд, поэтому сбрасываем выделение brush прямо в
  // рендере (паттерн React для подстройки состояния под изменившийся пропс).
  const [brushWindow, setBrushWindow] = useState(windowMs);
  if (brushWindow !== windowMs) {
    setBrushWindow(windowMs);
    setBrush(null);
  }

  const rows = useMemo(() => buildRows(series), [series]);

  const data = useMemo(() => {
    if (windowMs === null || rows.length === 0) return rows;
    const cutoff = rows[rows.length - 1].t - windowMs;
    return rows.filter((row) => row.t >= cutoff);
  }, [rows, windowMs]);

  // Статистика и линии-индикаторы считаются по видимому участку: в режиме "всё"
  // это выделение brush (по времени), иначе всё отфильтрованное окно.
  const visible = useMemo(() => {
    if (windowMs !== null || brush === null) return data;
    const within = data.filter(
      (row) => row.t >= brush.startT && row.t <= brush.endT,
    );
    return within.length > 0 ? within : data;
  }, [data, windowMs, brush]);

  if (data.length === 0) {
    return (
      <div
        style={fill ? undefined : { height }}
        className={cn(
          "flex items-center justify-center border border-dashed border-border font-mono text-[11px] tracking-wider text-muted-foreground/60 uppercase",
          fill && "h-full",
        )}
      >
        ожидание данных...
      </div>
    );
  }

  const xMax = data[data.length - 1].t;
  const xMin = windowMs === null ? data[0].t : xMax - windowMs;
  const xDomain: [number, number] = [xMin, xMax];
  // Сетка по времени: засечки на круглых отметках, частота — под ширину графика.
  const { ticks, secondsGrid } = niceTimeTicks(xMin, xMax, fill ? 10 : 6);

  const yDomain: [number | string, number | string] = [
    boundValue(yRange.min),
    boundValue(yRange.max),
  ];
  const manualY = yDomain[0] !== "auto" || yDomain[1] !== "auto";

  // Значения видимого окна для статистики/индикаторов одиночной линии.
  const primary = series[0];
  const primaryValues = single ? columnValues(visible, primary.key) : [];

  // Контролируемый brush: индексы пересчитываются из времени на каждый рендер,
  // поэтому при дописывании точек ползунки остаются на том же участке времени.
  const times = data.map((row) => row.t);
  const brushStart = brush === null ? 0 : firstIndexAtOrAfter(times, brush.startT);
  const brushEnd =
    brush === null ? data.length - 1 : lastIndexAtOrBefore(times, brush.endT);

  function toggle(id: string) {
    setShown((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  return (
    <div className={cn("flex flex-col gap-2", fill && "h-full")}>
      <div
        className={cn(fill && "min-h-0 flex-1")}
        style={fill ? undefined : { height }}
      >
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={data}
            margin={{ top: 6, right: 12, bottom: 0, left: 0 }}
          >
            <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" />
            <XAxis
              dataKey="t"
              type="number"
              scale="time"
              domain={xDomain}
              ticks={ticks}
              tickFormatter={(t) => formatTick(t, secondsGrid)}
              tick={{ fontSize: 10, fill: "var(--muted-foreground)" }}
              minTickGap={24}
              stroke="var(--border)"
            />
            <YAxis
              domain={yDomain}
              allowDataOverflow={manualY}
              tickFormatter={primary.format}
              tick={{ fontSize: 10, fill: "var(--muted-foreground)" }}
              width={56}
              stroke="var(--border)"
            />
            <Tooltip
              isAnimationActive={false}
              content={<ChartTooltip series={series} />}
            />
            {series.map((line) => (
              <Line
                key={line.key}
                dataKey={line.key}
                type="monotone"
                stroke={line.color}
                strokeWidth={1.5}
                dot={false}
                connectNulls
                isAnimationActive={false}
              />
            ))}
            {single &&
              INDICATORS.filter((indicator) => shown.has(indicator.id)).map(
                (indicator) => (
                  <ReferenceLine
                    key={indicator.id}
                    y={indicator.compute(primaryValues)}
                    stroke={indicator.color}
                    strokeDasharray="5 4"
                    ifOverflow={manualY ? "hidden" : "extendDomain"}
                  />
                ),
              )}
            {windowMs === null && data.length > 8 && (
              <Brush
                dataKey="t"
                height={20}
                travellerWidth={8}
                stroke="var(--muted-foreground)"
                fill="var(--card)"
                startIndex={brushStart}
                endIndex={brushEnd}
                tickFormatter={(t) => formatTick(t, secondsGrid)}
                onChange={(range) =>
                  setBrush(toTimeRange(times, range.startIndex, range.endIndex))
                }
              />
            )}
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 font-mono text-[11px] tabular-nums">
        {single ? (
          <>
            <Stat label="тек" value={primary.format(latest(primary) ?? NaN)} />
            <Stat label="мин" value={primary.format(Math.min(...primaryValues))} />
            <Stat label="макс" value={primary.format(Math.max(...primaryValues))} />
            <span className="text-muted-foreground/30">|</span>
            {INDICATORS.map((indicator) => (
              <button
                key={indicator.id}
                type="button"
                onClick={() => toggle(indicator.id)}
                aria-pressed={shown.has(indicator.id)}
                title={shown.has(indicator.id) ? "Скрыть линию" : "Показать линию"}
                className={cn(
                  "flex items-center gap-1.5 border px-1.5 py-0.5 transition-colors",
                  shown.has(indicator.id)
                    ? "border-current"
                    : "border-transparent text-muted-foreground hover:text-foreground",
                )}
                style={
                  shown.has(indicator.id) ? { color: indicator.color } : undefined
                }
              >
                <span
                  className="inline-block h-0 w-3 border-t-2 border-dashed"
                  style={{ borderColor: indicator.color }}
                />
                {indicator.label} {primary.format(indicator.compute(primaryValues))}
              </button>
            ))}
          </>
        ) : (
          series.map((line) => (
            <LegendItem
              key={line.key}
              line={line}
              value={latest(line)}
              onRemove={onRemoveSeries}
            />
          ))
        )}
        <YRangeControl
          value={yRange}
          manual={manualY}
          onChange={setYRange}
        />
      </div>
    </div>
  );
}

function LegendItem({
  line,
  value,
  onRemove,
}: {
  line: ChartSeries;
  value: number | undefined;
  onRemove?: (key: string) => void;
}) {
  return (
    <span className="flex items-center gap-1.5" style={{ color: line.color }}>
      <span
        className="inline-block h-0 w-3 border-t-2"
        style={{ borderColor: line.color }}
      />
      <span className="text-foreground">{line.label}</span>
      <span className="text-muted-foreground">
        {value === undefined ? "..." : line.format(value)}
      </span>
      {onRemove && (
        <button
          type="button"
          onClick={() => onRemove(line.key)}
          title="Вынести на отдельный график"
          className="text-muted-foreground/50 hover:text-foreground"
        >
          <XIcon className="size-3" />
        </button>
      )}
    </span>
  );
}

function YRangeControl({
  value,
  manual,
  onChange,
}: {
  value: { min: string; max: string };
  manual: boolean;
  onChange: (next: { min: string; max: string }) => void;
}) {
  return (
    <div className="ml-auto flex items-center gap-1 text-[10px] text-muted-foreground">
      <span className="tracking-wider uppercase">Y</span>
      <input
        value={value.min}
        onChange={(event) => onChange({ ...value, min: event.target.value })}
        placeholder="мин"
        inputMode="decimal"
        aria-label="Нижняя граница оси значений"
        className="h-5 w-12 border border-border bg-background px-1 text-right tabular-nums outline-none focus-visible:border-ring focus-visible:ring-1 focus-visible:ring-ring/50"
      />
      <span aria-hidden>...</span>
      <input
        value={value.max}
        onChange={(event) => onChange({ ...value, max: event.target.value })}
        placeholder="макс"
        inputMode="decimal"
        aria-label="Верхняя граница оси значений"
        className="h-5 w-12 border border-border bg-background px-1 text-right tabular-nums outline-none focus-visible:border-ring focus-visible:ring-1 focus-visible:ring-ring/50"
      />
      {manual && (
        <button
          type="button"
          onClick={() => onChange({ min: "", max: "" })}
          title="Авто-масштаб по данным"
          className="border border-border px-1 hover:text-foreground"
        >
          авто
        </button>
      )}
    </div>
  );
}

// Сводит точки всех линий в строки по серверному времени: поток шлёт значения
// переменных одним снимком, поэтому отметки времени совпадают и стык точный.
function buildRows(series: ChartSeries[]): Row[] {
  const byT = new Map<number, Row>();
  for (const line of series) {
    for (const sample of line.samples) {
      let row = byT.get(sample.t);
      if (row === undefined) {
        row = { t: sample.t };
        byT.set(sample.t, row);
      }
      row[line.key] = sample.v;
    }
  }
  return Array.from(byT.values()).sort((a, b) => a.t - b.t);
}

function columnValues(rows: Row[], key: string): number[] {
  const out: number[] = [];
  for (const row of rows) {
    const value = row[key];
    if (typeof value === "number") out.push(value);
  }
  return out;
}

function latest(line: ChartSeries): number | undefined {
  return line.samples.at(-1)?.v;
}

function boundValue(raw: string): number | "auto" {
  const trimmed = raw.trim();
  if (trimmed === "") return "auto";
  const parsed = Number(trimmed);
  return Number.isFinite(parsed) ? parsed : "auto";
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <span className="flex items-center gap-1.5">
      <span className="text-[10px] tracking-wider text-muted-foreground uppercase">
        {label}
      </span>
      <span>{value}</span>
    </span>
  );
}

function ChartTooltip({
  active,
  payload,
  label,
  series,
}: {
  active?: boolean;
  payload?: { dataKey?: string | number; value?: number }[];
  label?: number;
  series: ChartSeries[];
}) {
  if (!active || !payload?.length || label === undefined) return null;
  const byKey = new Map(series.map((line) => [line.key, line]));
  return (
    <div className="border border-border bg-card px-2 py-1 font-mono text-[11px] shadow-sm">
      <div className="text-muted-foreground">{formatTick(label, true)}</div>
      {payload.map((entry) => {
        const line = byKey.get(String(entry.dataKey));
        if (line === undefined || entry.value === undefined) return null;
        return (
          <div
            key={line.key}
            className="flex items-center justify-between gap-3 tabular-nums"
          >
            {series.length > 1 && (
              <span className="flex items-center gap-1.5">
                <span
                  className="inline-block size-2"
                  style={{ backgroundColor: line.color }}
                />
                <span className="text-muted-foreground">{line.label}</span>
              </span>
            )}
            <span>{line.format(entry.value)}</span>
          </div>
        );
      })}
    </div>
  );
}

function mean(values: number[]): number {
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function median(values: number[]): number {
  const sorted = [...values].sort((a, b) => a - b);
  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2 === 1
    ? sorted[middle]
    : (sorted[middle - 1] + sorted[middle]) / 2;
}
