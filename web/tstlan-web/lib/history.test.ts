import { describe, expect, it } from "vitest";

import { seedHistory, type Sample } from "@/lib/history";
import type { HistoryPoint } from "@/lib/api";

function point(t: number, values: Record<string, number>): HistoryPoint {
  return { t, values };
}

describe("seedHistory", () => {
  it("раскладывает точки истории по переменным", () => {
    const next = seedHistory(
      {},
      [point(1000, { voltage: 220, current: 1.5 }), point(2000, { voltage: 221 })],
      100,
    );
    expect(next.voltage).toEqual([
      { t: 1000, v: 220 },
      { t: 2000, v: 221 },
    ]);
    expect(next.current).toEqual([{ t: 1000, v: 1.5 }]);
  });

  it("ставит серверные точки перед живыми без дублей на стыке", () => {
    const live: Record<string, Sample[]> = {
      voltage: [
        { t: 2000, v: 221 },
        { t: 3000, v: 222 },
      ],
    };
    const next = seedHistory(
      live,
      [point(1000, { voltage: 220 }), point(2000, { voltage: 221 })],
      100,
    );
    expect(next.voltage).toEqual([
      { t: 1000, v: 220 },
      { t: 2000, v: 221 },
      { t: 3000, v: 222 },
    ]);
  });

  it("обрезает ряд до максимума, выбрасывая старые точки", () => {
    const points = [1, 2, 3, 4, 5].map((i) => point(i * 1000, { voltage: i }));
    const next = seedHistory({}, points, 3);
    expect(next.voltage.map((sample) => sample.t)).toEqual([3000, 4000, 5000]);
  });

  it("не трогает переменные, которых нет в истории", () => {
    const live: Record<string, Sample[]> = {
      current: [{ t: 5000, v: 1.5 }],
    };
    const next = seedHistory(live, [point(1000, { voltage: 220 })], 100);
    expect(next.current).toEqual([{ t: 5000, v: 1.5 }]);
    expect(next.voltage).toEqual([{ t: 1000, v: 220 }]);
  });

  it("пустая история ничего не меняет", () => {
    const live: Record<string, Sample[]> = {
      voltage: [{ t: 1000, v: 220 }],
    };
    expect(seedHistory(live, [], 100)).toEqual(live);
  });
});
