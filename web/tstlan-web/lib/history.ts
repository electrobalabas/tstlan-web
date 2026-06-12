import type { HistoryPoint } from "@/lib/api";

export type Sample = { t: number; v: number };

// Подсадить серверную историю под уже накопленные живые точки. История и
// поток используют серверное время, поэтому стык точный: берём только точки
// старше первой живой и не получаем ни дыр, ни дублей.
export function seedHistory(
  prev: Record<string, Sample[]>,
  points: HistoryPoint[],
  maxPoints: number,
): Record<string, Sample[]> {
  const byName: Record<string, Sample[]> = {};
  for (const point of points) {
    for (const [name, v] of Object.entries(point.values)) {
      (byName[name] ??= []).push({ t: point.t, v });
    }
  }

  const next = { ...prev };
  for (const [name, samples] of Object.entries(byName)) {
    const live = next[name] ?? [];
    const cutoff = live.length > 0 ? live[0].t : Infinity;
    const older = samples.filter((sample) => sample.t < cutoff);
    next[name] = [...older, ...live].slice(-maxPoints);
  }
  return next;
}
