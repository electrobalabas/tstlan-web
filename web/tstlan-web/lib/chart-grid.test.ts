import { describe, expect, it } from "vitest";

import { niceTimeTicks } from "@/lib/chart-grid";

// Шаг между засечками: ряд равномерный, поэтому достаточно первой пары.
function tickStep(ticks: number[]): number {
  return ticks[1] - ticks[0];
}

describe("niceTimeTicks", () => {
  it("разрежает сетку при широком окне и сгущает при узком", () => {
    const base = Date.UTC(2026, 0, 1, 12, 0, 0);
    const minute = niceTimeTicks(base, base + 60_000, 6);
    const quarter = niceTimeTicks(base, base + 900_000, 6);
    // Узкое окно — мелкий шаг (секунды), широкое — крупный (минуты).
    expect(tickStep(minute.ticks)).toBeLessThan(tickStep(quarter.ticks));
    expect(minute.secondsGrid).toBe(true);
    expect(quarter.secondsGrid).toBe(false);
  });

  it("держит число засечек около заданного ориентира", () => {
    const base = Date.UTC(2026, 0, 1, 12, 0, 0);
    const { ticks } = niceTimeTicks(base, base + 300_000, 6);
    expect(ticks.length).toBeGreaterThanOrEqual(3);
    expect(ticks.length).toBeLessThanOrEqual(10);
  });

  it("ставит засечки на круглых отметках с равным шагом внутри окна", () => {
    const base = Date.UTC(2026, 0, 1, 12, 0, 0) + 1234; // не круглая граница
    const { ticks } = niceTimeTicks(base, base + 600_000, 6);
    const step = tickStep(ticks);
    for (let i = 1; i < ticks.length; i += 1) {
      expect(ticks[i] - ticks[i - 1]).toBe(step);
    }
    // Засечки выровнены по кратным шага (в локальном времени), а не по краю окна.
    const tzOffset = new Date(base).getTimezoneOffset() * 60_000;
    expect((ticks[0] - tzOffset) % step).toBe(0);
    expect(ticks[0]).toBeGreaterThanOrEqual(base);
    expect(ticks.at(-1)).toBeLessThanOrEqual(base + 600_000);
  });

  it("не падает на пустом или вырожденном окне", () => {
    const base = Date.UTC(2026, 0, 1, 12, 0, 0);
    expect(niceTimeTicks(base, base, 6).ticks).toEqual([base]);
  });
});
