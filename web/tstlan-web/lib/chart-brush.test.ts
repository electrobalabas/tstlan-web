import { describe, expect, it } from "vitest";

import {
  firstIndexAtOrAfter,
  lastIndexAtOrBefore,
  toTimeRange,
} from "@/lib/chart-brush";

describe("brush по времени", () => {
  it("полный диапазон трактуется как «без выделения» (null)", () => {
    const times = [10, 20, 30, 40];
    expect(toTimeRange(times, 0, 3)).toBeNull();
    expect(toTimeRange(times, undefined, undefined)).toBeNull();
  });

  it("частичное выделение переводится в границы по времени", () => {
    const times = [10, 20, 30, 40, 50];
    expect(toTimeRange(times, 1, 3)).toEqual({ startT: 20, endT: 40 });
  });

  it("выделение остаётся на том же участке времени после дозаписи точек", () => {
    const times = [10, 20, 30, 40];
    const range = toTimeRange(times, 1, 2); // окно 20..30
    expect(range).toEqual({ startT: 20, endT: 30 });

    // Поток дописал новые точки в конец — индексы того же окна не «уехали».
    const grown = [10, 20, 30, 40, 50, 60];
    const start = firstIndexAtOrAfter(grown, range!.startT);
    const end = lastIndexAtOrBefore(grown, range!.endT);
    expect([start, end]).toEqual([1, 2]);
    expect([grown[start], grown[end]]).toEqual([20, 30]);
  });

  it("после подрезки старых точек окно смещается к сохранившимся индексам", () => {
    const range = { startT: 20, endT: 40 };
    // Кольцевой буфер выбросил точку 10 из начала.
    const trimmed = [20, 30, 40, 50, 60];
    const start = firstIndexAtOrAfter(trimmed, range.startT);
    const end = lastIndexAtOrBefore(trimmed, range.endT);
    expect([trimmed[start], trimmed[end]]).toEqual([20, 40]);
  });

  it("ищет ближайшие индексы для отметок, которых нет в ряду", () => {
    const times = [10, 20, 30, 40];
    expect(firstIndexAtOrAfter(times, 25)).toBe(2); // первый ≥ 25 → 30
    expect(lastIndexAtOrBefore(times, 25)).toBe(1); // последний ≤ 25 → 20
  });
});
