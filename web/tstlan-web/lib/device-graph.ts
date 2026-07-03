import type { ConfigSummary, ConfigVar } from "@/lib/api";

// Конфиг прибора и десктопный флаг graph живут отдельно от самих приборов
// (приборы приходят из симуляции/профилей). Эти функции связывают их на стороне
// клиента: прибор «примеряет» флаги graph совпадающего по device_type конфига.

// Конфиг, чьи флаги graph применяются к прибору: совпадение device_type с id
// прибора. Среди доступных предпочитаем свой (owner), затем самый свежий.
export function pickDeviceConfig(
  summaries: ConfigSummary[],
  deviceId: string,
): ConfigSummary | null {
  const matches = summaries.filter(
    (summary) => summary.device_type === deviceId,
  );
  if (matches.length === 0) return null;
  return [...matches].sort(byPreference)[0];
}

function byPreference(a: ConfigSummary, b: ConfigSummary): number {
  // свой конфиг важнее любого чужого
  const own = Number(b.access === "owner") - Number(a.access === "owner");
  if (own !== 0) return own;
  // затем самый недавно обновлённый
  return b.updated_at.localeCompare(a.updated_at);
}

// Имена переменных, которые нужно построить по умолчанию: помечены graph в
// конфиге и реально есть у прибора (имена конфига и прибора могут расходиться).
export function graphSelection(
  configVars: ConfigVar[],
  deviceVarNames: Iterable<string>,
): Set<string> {
  const present = new Set(deviceVarNames);
  return new Set(
    configVars
      .filter((variable) => variable.graph && present.has(variable.name))
      .map((variable) => variable.name),
  );
}
