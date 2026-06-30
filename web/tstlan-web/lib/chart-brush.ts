// Выделение brush на графике «всё» хранится во времени, а не в индексах: живой
// поток постоянно дописывает точки и подрезает старые, из-за чего индексы
// «уезжают» и сбивают выбранный участок. Эти функции переводят выделение между
// индексами recharts и стабильными границами по времени.

export type TimeRange = { startT: number; endT: number };

// Полный диапазон трактуем как «без выделения» (null), чтобы правый край снова
// следовал за живыми точками.
export function toTimeRange(
  times: number[],
  startIndex: number | undefined,
  endIndex: number | undefined,
): TimeRange | null {
  if (startIndex === undefined || endIndex === undefined) return null;
  if (startIndex <= 0 && endIndex >= times.length - 1) return null;
  const startT = times[startIndex];
  const endT = times[endIndex];
  if (startT === undefined || endT === undefined) return null;
  return { startT, endT };
}

// Ряд отсортирован по времени, поэтому простого скана достаточно.
export function firstIndexAtOrAfter(times: number[], t: number): number {
  for (let i = 0; i < times.length; i += 1) {
    if (times[i] >= t) return i;
  }
  return Math.max(0, times.length - 1);
}

export function lastIndexAtOrBefore(times: number[], t: number): number {
  for (let i = times.length - 1; i >= 0; i -= 1) {
    if (times[i] <= t) return i;
  }
  return 0;
}
