// Засечки времени на круглых отметках стенных часов. Шаг подбирается из лесенки
// «приятных» интервалов так, чтобы засечек вышло около target, поэтому сетка
// плавно разрежается при широком окне и сгущается при узком.
const TIME_STEPS_MS = [
  1, 2, 5, 10, 15, 30, 60, 120, 300, 600, 900, 1800, 3600, 7200, 10800, 21600,
  43200, 86400,
].map((seconds) => seconds * 1000);

export type TimeGrid = {
  ticks: number[];
  // Шаг меньше минуты — на засечках и в подсказке нужны секунды.
  secondsGrid: boolean;
};

export function niceTimeTicks(
  min: number,
  max: number,
  target: number,
): TimeGrid {
  const span = max - min;
  if (!(span > 0)) return { ticks: [min], secondsGrid: true };
  const rough = span / target;
  const step =
    TIME_STEPS_MS.find((candidate) => candidate >= rough) ??
    TIME_STEPS_MS[TIME_STEPS_MS.length - 1];
  // Привязка к локальным круглым отметкам: смещение часового пояса убирает
  // расхождение между UTC-кратными step и стенными минутами/секундами.
  const tzOffset = new Date(min).getTimezoneOffset() * 60_000;
  const first = Math.ceil((min - tzOffset) / step) * step + tzOffset;
  const ticks: number[] = [];
  for (let t = first; t <= max; t += step) ticks.push(t);
  return { ticks, secondsGrid: step < 60_000 };
}

export function formatTick(t: number, withSeconds: boolean): string {
  return new Date(t).toLocaleTimeString("ru-RU", {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
    ...(withSeconds ? { second: "2-digit" } : {}),
  });
}
