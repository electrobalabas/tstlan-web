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

import { cn } from "@/lib/utils";

export type Sample = { t: number; v: number };

type Indicator = {
  id: string;
  label: string;
  color: string;
  compute: (values: number[]) => number;
};

// Задел под индикаторы: новая статистика на графике - это одна запись здесь.
// compute получает значения видимого окна, результат рисуется как ReferenceLine.
const INDICATORS: Indicator[] = [
  { id: "mean", label: "среднее", color: "#0d9488", compute: mean },
  { id: "median", label: "медиана", color: "#d97706", compute: median },
];

export function TimeSeriesChart({
  samples,
  windowMs,
  format,
  height = 200,
}: {
  samples: Sample[];
  windowMs: number | null;
  format: (value: number) => string;
  height?: number;
}) {
  const [shown, setShown] = useState<ReadonlySet<string>>(() => new Set());
  const [brush, setBrush] = useState<{
    startIndex?: number;
    endIndex?: number;
  }>({});
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
    setBrush({});
  }

  const data = useMemo(() => {
    if (windowMs === null || samples.length === 0) return samples;
    const cutoff = samples[samples.length - 1].t - windowMs;
    return samples.filter((sample) => sample.t >= cutoff);
  }, [samples, windowMs]);

  // Статистика и линии-индикаторы считаются по видимому участку: в режиме "всё"
  // это выделение brush, иначе всё отфильтрованное окно.
  const visible = useMemo(() => {
    if (windowMs !== null) return data;
    const start = brush.startIndex ?? 0;
    const end = brush.endIndex ?? data.length - 1;
    return data.slice(start, end + 1);
  }, [data, windowMs, brush]);

  const values = useMemo(() => visible.map((sample) => sample.v), [visible]);

  if (data.length === 0) {
    return (
      <div
        style={{ height }}
        className="flex items-center justify-center border border-dashed border-border font-mono text-[11px] tracking-wider text-muted-foreground/60 uppercase"
      >
        ожидание данных...
      </div>
    );
  }

  const xMax = data[data.length - 1].t;
  const xDomain: [number | string, number | string] =
    windowMs === null ? ["dataMin", "dataMax"] : [xMax - windowMs, xMax];

  const yDomain: [number | string, number | string] = [
    boundValue(yRange.min),
    boundValue(yRange.max),
  ];
  const manualY = yDomain[0] !== "auto" || yDomain[1] !== "auto";

  function toggle(id: string) {
    setShown((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  return (
    <div className="space-y-2">
      <div style={{ height }}>
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
              tickFormatter={formatTime}
              tick={{ fontSize: 10, fill: "var(--muted-foreground)" }}
              minTickGap={48}
              stroke="var(--border)"
            />
            <YAxis
              domain={yDomain}
              allowDataOverflow={manualY}
              tickFormatter={format}
              tick={{ fontSize: 10, fill: "var(--muted-foreground)" }}
              width={56}
              stroke="var(--border)"
            />
            <Tooltip
              isAnimationActive={false}
              content={<ChartTooltip format={format} />}
            />
            <Line
              dataKey="v"
              type="monotone"
              stroke="var(--foreground)"
              strokeWidth={1.5}
              dot={false}
              isAnimationActive={false}
            />
            {INDICATORS.filter((indicator) => shown.has(indicator.id)).map(
              (indicator) => (
                <ReferenceLine
                  key={indicator.id}
                  y={indicator.compute(values)}
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
                tickFormatter={formatTime}
                onChange={(range) =>
                  setBrush({
                    startIndex: range.startIndex,
                    endIndex: range.endIndex,
                  })
                }
              />
            )}
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 font-mono text-[11px] tabular-nums">
        <Stat label="тек" value={format(data[data.length - 1].v)} />
        <Stat label="мин" value={format(Math.min(...values))} />
        <Stat label="макс" value={format(Math.max(...values))} />
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
            style={shown.has(indicator.id) ? { color: indicator.color } : undefined}
          >
            <span
              className="inline-block h-0 w-3 border-t-2 border-dashed"
              style={{ borderColor: indicator.color }}
            />
            {indicator.label} {format(indicator.compute(values))}
          </button>
        ))}
        <div className="ml-auto flex items-center gap-1 text-[10px] text-muted-foreground">
          <span className="tracking-wider uppercase">Y</span>
          <input
            value={yRange.min}
            onChange={(event) =>
              setYRange((prev) => ({ ...prev, min: event.target.value }))
            }
            placeholder="мин"
            inputMode="decimal"
            aria-label="Нижняя граница оси значений"
            className="h-5 w-12 border border-border bg-background px-1 text-right tabular-nums outline-none focus-visible:border-ring focus-visible:ring-1 focus-visible:ring-ring/50"
          />
          <span aria-hidden>...</span>
          <input
            value={yRange.max}
            onChange={(event) =>
              setYRange((prev) => ({ ...prev, max: event.target.value }))
            }
            placeholder="макс"
            inputMode="decimal"
            aria-label="Верхняя граница оси значений"
            className="h-5 w-12 border border-border bg-background px-1 text-right tabular-nums outline-none focus-visible:border-ring focus-visible:ring-1 focus-visible:ring-ring/50"
          />
          {manualY && (
            <button
              type="button"
              onClick={() => setYRange({ min: "", max: "" })}
              title="Авто-масштаб по данным"
              className="border border-border px-1 hover:text-foreground"
            >
              авто
            </button>
          )}
        </div>
      </div>
    </div>
  );
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
  format,
}: {
  active?: boolean;
  payload?: { value: number }[];
  label?: number;
  format: (value: number) => string;
}) {
  if (!active || !payload?.length || label === undefined) return null;
  return (
    <div className="border border-border bg-card px-2 py-1 font-mono text-[11px] shadow-sm">
      <div className="text-muted-foreground">{formatTime(label)}</div>
      <div className="tabular-nums">{format(payload[0].value)}</div>
    </div>
  );
}

function formatTime(t: number): string {
  return new Date(t).toLocaleTimeString("ru-RU", { hour12: false });
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
