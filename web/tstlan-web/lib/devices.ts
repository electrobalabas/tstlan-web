import type { DeviceStatus, NetVarMode } from "@/lib/api";

export const STATUS_META: Record<DeviceStatus, { label: string; dot: string }> =
  {
    ok: { label: "В сети", dot: "bg-emerald-500" },
    offline: { label: "Не в сети", dot: "bg-muted-foreground/40" },
    error: { label: "Ошибка", dot: "bg-destructive" },
  };

export const MODE_META: Record<
  NetVarMode,
  { label: string; title: string; writable: boolean }
> = {
  r: { label: "RO", title: "только чтение", writable: false },
  w: { label: "WO", title: "только запись", writable: true },
  rw: { label: "RW", title: "чтение и запись", writable: true },
};
