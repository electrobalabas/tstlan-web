"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Dialog } from "@base-ui/react/dialog";
import { Menu } from "@base-ui/react/menu";
import {
  ArrowLeftIcon,
  CheckIcon,
  ChartLineIcon,
  CornersOutIcon,
  MagnifyingGlassIcon,
  PencilSimpleIcon,
  PlusIcon,
  XIcon,
} from "@phosphor-icons/react/ssr";

import { useAuth } from "@/components/auth-provider";
import {
  TimeSeriesChart,
  type ChartSeries,
  type Sample,
} from "@/components/time-series-chart";
import { cn } from "@/lib/utils";
import {
  ApiError,
  getConfig,
  getDevice,
  getHistory,
  listConfigs,
  streamValues,
  writeValue,
  type DeviceDetail,
  type NetVarCType,
  type VariableInfo,
} from "@/lib/api";
import { graphSelection, pickDeviceConfig } from "@/lib/device-graph";
import { MODE_META, STATUS_META } from "@/lib/devices";
import { seedHistory } from "@/lib/history";

type LoadState =
  | { status: "loading" }
  | { status: "notfound" }
  | { status: "error" }
  | { status: "ready"; device: DeviceDetail };

type Connection = "connecting" | "live" | "lost";

// Клиентский буфер ряда: ~15 минут при шаге потока в 1 с (см. бэкенд SSE).
const MAX_POINTS = 1000;

export function DeviceMonitor({ deviceId }: { deviceId: string }) {
  const [load, setLoad] = useState<LoadState>({ status: "loading" });
  const [values, setValues] = useState<Record<string, number>>({});
  const [history, setHistory] = useState<Record<string, Sample[]>>({});
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [grouping, setGrouping] = useState<Grouping>({});
  const [connection, setConnection] = useState<Connection>("connecting");
  const [query, setQuery] = useState("");

  const handleWritten = useCallback((name: string, value: number) => {
    setValues((prev) => ({ ...prev, [name]: value }));
  }, []);

  const toggleSelected = useCallback((name: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(name)) {
        next.delete(name);
      } else {
        next.add(name);
      }
      return next;
    });
    // Переключение всегда сбрасывает группировку переменной: снятая с графика
    // не должна при повторном добавлении воскрешать прежнюю группу.
    setGrouping((prev) => {
      if (!(name in prev)) return prev;
      const next = { ...prev };
      delete next[name];
      return next;
    });
  }, []);

  useEffect(() => {
    let active = true;
    getDevice(deviceId)
      .then((device) => active && setLoad({ status: "ready", device }))
      .catch((cause) => {
        if (!active) return;
        const notFound = cause instanceof ApiError && cause.status === 404;
        setLoad({ status: notFound ? "notfound" : "error" });
      });
    return () => {
      active = false;
    };
  }, [deviceId]);

  useEffect(() => {
    if (load.status !== "ready") return;
    let active = true;
    getHistory(deviceId)
      .then((points) => {
        if (!active || points.length === 0) return;
        setHistory((prev) => seedHistory(prev, points, MAX_POINTS));
      })
      .catch(() => {
        // история не критична: график начнётся с живого потока
      });
    return () => {
      active = false;
    };
  }, [deviceId, load.status]);

  // Прибор «примеряет» флаги graph совпадающего конфига: помеченные переменные
  // строятся по умолчанию. Конфиги и приборы разъединены, поэтому связываем их
  // здесь по device_type == id прибора, не трогая ручной выбор пользователя.
  useEffect(() => {
    if (load.status !== "ready") return;
    const device = load.device;
    let active = true;
    listConfigs()
      .then((summaries) => {
        const match = pickDeviceConfig(summaries, device.id);
        if (match === null) return;
        return getConfig(match.id).then((config) => {
          if (!active) return;
          const names = graphSelection(
            config.payload.variables,
            device.variables.map((variable) => variable.name),
          );
          if (names.size > 0) {
            setSelected((prev) => (prev.size > 0 ? prev : names));
          }
        });
      })
      .catch(() => {
        // дефолтный выбор не критичен: пользователь добавит линии вручную
      });
    return () => {
      active = false;
    };
  }, [deviceId, load.status, load]);

  useEffect(() => {
    if (load.status !== "ready") return;
    const stop = streamValues(
      deviceId,
      (snapshot, t) => {
        setValues(Object.fromEntries(snapshot.map((v) => [v.name, v.value])));
        setHistory((prev) => {
          const next = { ...prev };
          for (const v of snapshot) {
            next[v.name] = [...(next[v.name] ?? []), { t, v: v.value }].slice(
              -MAX_POINTS,
            );
          }
          return next;
        });
        setConnection("live");
      },
      () => setConnection("lost"),
    );
    return stop;
  }, [deviceId, load.status]);

  if (load.status !== "ready") {
    return (
      <Shell>
        {load.status === "loading" && <Notice>загрузка...</Notice>}
        {load.status === "notfound" && <Notice>устройство не найдено</Notice>}
        {load.status === "error" && (
          <Notice>не удалось загрузить устройство</Notice>
        )}
      </Shell>
    );
  }

  const { device } = load;
  const variables = device.variables.filter((variable) =>
    variable.name.toLowerCase().includes(query.trim().toLowerCase()),
  );

  return (
    <Shell>
      <DeviceHeader device={device} connection={connection} />

      <div className="flex items-center gap-3">
        <label className="relative flex-1">
          <MagnifyingGlassIcon className="absolute top-1/2 left-2.5 size-3.5 -translate-y-1/2 text-muted-foreground" />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Поиск переменной"
            className="h-8 w-full border border-border bg-background pr-3 pl-8 text-sm outline-none focus-visible:border-ring focus-visible:ring-1 focus-visible:ring-ring/50"
          />
        </label>
        <span className="font-mono text-xs text-muted-foreground tabular-nums">
          {variables.length} / {device.variables.length}
        </span>
      </div>

      <ChartPanel
        variables={device.variables}
        selected={selected}
        grouping={grouping}
        setGrouping={setGrouping}
        history={history}
        values={values}
        onToggle={toggleSelected}
      />

      <VariableTable
        deviceId={deviceId}
        variables={variables}
        values={values}
        selected={selected}
        onWritten={handleWritten}
        onToggle={toggleSelected}
      />
    </Shell>
  );
}

const WINDOW_OPTIONS: { label: string; value: number | null }[] = [
  { label: "30с", value: 30_000 },
  { label: "1м", value: 60_000 },
  { label: "5м", value: 300_000 },
  { label: "15м", value: 900_000 },
  { label: "всё", value: null },
];

// Палитра для наложенных линий: при совмещённом режиме каждая переменная
// получает свой цвет (раздельные графики остаются монохромными).
const SERIES_COLORS = [
  "#0d9488",
  "#2563eb",
  "#d97706",
  "#dc2626",
  "#7c3aed",
  "#0891b2",
  "#65a30d",
  "#db2777",
];

// Группировка линий по графикам: имя переменной → id графика. Переменные с
// одним id рисуются наложенными; отсутствие записи означает собственный график.
export type Grouping = Record<string, string>;

type ChartGroup = { id: string; members: VariableInfo[] };

let groupSeq = 0;
function nextGroupId(): string {
  groupSeq += 1;
  return `g${groupSeq}`;
}
function soloId(name: string): string {
  return `solo:${name}`;
}

function groupTitle(group: ChartGroup): string {
  return group.members.map((variable) => variable.name).join(" + ");
}

function ChartPanel({
  variables,
  selected,
  grouping,
  setGrouping,
  history,
  values,
  onToggle,
}: {
  variables: VariableInfo[];
  selected: Set<string>;
  grouping: Grouping;
  setGrouping: React.Dispatch<React.SetStateAction<Grouping>>;
  history: Record<string, Sample[]>;
  values: Record<string, number>;
  onToggle: (name: string) => void;
}) {
  const [windowMs, setWindowMs] = useState<number | null>(60_000);
  // Полноэкранный график задаётся id группы; null — окно закрыто.
  const [fullscreenId, setFullscreenId] = useState<string | null>(null);

  const charted = variables.filter((variable) => selected.has(variable.name));
  if (charted.length === 0) return null;

  const groupIdOf = (name: string) => grouping[name] ?? soloId(name);
  // Линии собираются в группы в порядке появления переменных в таблице.
  const groups: ChartGroup[] = [];
  const indexById = new Map<string, number>();
  for (const variable of charted) {
    const id = groupIdOf(variable.name);
    const at = indexById.get(id);
    if (at === undefined) {
      indexById.set(id, groups.length);
      groups.push({ id, members: [variable] });
    } else {
      groups[at].members.push(variable);
    }
  }

  const toSeries = (variable: VariableInfo, color: string): ChartSeries => ({
    key: variable.name,
    label: variable.name,
    color,
    samples: history[variable.name] ?? [],
    format: (value) => formatChartValue(variable.ctype, value),
  });
  // Наложенные линии раскрашены палитрой; одиночный график — цветом текста.
  const seriesOf = (group: ChartGroup): ChartSeries[] =>
    group.members.length > 1
      ? group.members.map((variable, index) =>
          toSeries(variable, SERIES_COLORS[index % SERIES_COLORS.length]),
        )
      : [toSeries(group.members[0], "var(--foreground)")];

  // Слить переменную в этот график. Если цель ещё одиночная (solo-id), выдаём ей
  // настоящий id и переносим туда обе линии.
  const mergeInto = (group: ChartGroup, name: string) =>
    setGrouping((prev) => {
      const next = { ...prev };
      let targetId = group.id;
      if (targetId.startsWith("solo:")) {
        targetId = nextGroupId();
        for (const member of group.members) next[member.name] = targetId;
      }
      next[name] = targetId;
      return next;
    });
  // Вынести линию обратно на собственный график.
  const splitOut = (name: string) =>
    setGrouping((prev) => {
      const next = { ...prev };
      delete next[name];
      return next;
    });
  const closeGroup = (group: ChartGroup) =>
    group.members.forEach((variable) => onToggle(variable.name));

  const fullscreenGroup = groups.find((group) => group.id === fullscreenId);

  return (
    <>
      <div className="space-y-4 border border-border bg-card p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <span className="text-[10px] tracking-wider text-muted-foreground uppercase">
            Графики
          </span>
          <Segmented
            options={WINDOW_OPTIONS}
            value={windowMs}
            onSelect={setWindowMs}
          />
        </div>

        <div className="space-y-5 divide-y divide-border">
          {groups.map((group) => {
            const single = group.members.length === 1;
            const lead = group.members[0];
            // Текущее значение в шапке — только для одиночного графика; у
            // совмещённого значения показывает легенда под графиком.
            const headerValue = !single
              ? undefined
              : lead.name in values
                ? formatValue(lead.ctype, values[lead.name])
                : "...";
            return (
              <div key={group.id} className="space-y-2 pt-5 first:pt-0">
                <ChartHeader
                  title={groupTitle(group)}
                  ctype={single ? lead.ctype : undefined}
                  value={headerValue}
                  mergeable={charted.filter(
                    (variable) => groupIdOf(variable.name) !== group.id,
                  )}
                  onMerge={(name) => mergeInto(group, name)}
                  onExpand={() => setFullscreenId(group.id)}
                  onRemove={() => closeGroup(group)}
                />
                <TimeSeriesChart
                  series={seriesOf(group)}
                  windowMs={windowMs}
                  onRemoveSeries={splitOut}
                />
              </div>
            );
          })}
        </div>
      </div>

      <ChartDialog
        open={fullscreenGroup !== undefined}
        title={fullscreenGroup && groupTitle(fullscreenGroup)}
        windowMs={windowMs}
        onWindow={setWindowMs}
        onClose={() => setFullscreenId(null)}
      >
        {fullscreenGroup && (
          <TimeSeriesChart
            series={seriesOf(fullscreenGroup)}
            windowMs={windowMs}
            fill
            onRemoveSeries={splitOut}
          />
        )}
      </ChartDialog>
    </>
  );
}

function Segmented<T>({
  options,
  value,
  onSelect,
}: {
  options: { label: string; value: T }[];
  value: T;
  onSelect: (value: T) => void;
}) {
  return (
    <div className="flex">
      {options.map((option, index) => (
        <button
          key={option.label}
          type="button"
          onClick={() => onSelect(option.value)}
          aria-pressed={value === option.value}
          className={cn(
            "border border-border px-2 py-1 font-mono text-[11px] transition-colors",
            index > 0 && "-ml-px",
            value === option.value
              ? "bg-foreground text-background"
              : "text-muted-foreground hover:text-foreground",
          )}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}

const ICON_BUTTON =
  "flex size-6 shrink-0 items-center justify-center border border-border text-muted-foreground hover:bg-muted hover:text-foreground";

function ChartHeader({
  title,
  ctype,
  value,
  mergeable,
  onMerge,
  onExpand,
  onRemove,
}: {
  title: string;
  ctype?: NetVarCType;
  value?: string;
  // Переменные с других графиков, которые можно подмешать сюда.
  mergeable: VariableInfo[];
  onMerge: (name: string) => void;
  onExpand: () => void;
  onRemove: () => void;
}) {
  return (
    <div className="flex items-center justify-between gap-3">
      <div className="flex min-w-0 items-baseline gap-2">
        <span className="truncate font-mono text-xs">{title}</span>
        {ctype && (
          <span className="font-mono text-[10px] text-muted-foreground uppercase">
            {ctype}
          </span>
        )}
      </div>
      <div className="flex items-center gap-3">
        {value !== undefined && (
          <span className="font-mono text-sm tabular-nums">{value}</span>
        )}
        <div className="flex items-center gap-1">
          {mergeable.length > 0 && (
            <MergeMenu options={mergeable} onMerge={onMerge} />
          )}
          <button
            type="button"
            onClick={onExpand}
            title="Развернуть на весь экран"
            className={ICON_BUTTON}
          >
            <CornersOutIcon className="size-3" />
          </button>
          <button
            type="button"
            onClick={onRemove}
            title="Убрать график"
            className={ICON_BUTTON}
          >
            <XIcon className="size-3" />
          </button>
        </div>
      </div>
    </div>
  );
}

function MergeMenu({
  options,
  onMerge,
}: {
  options: VariableInfo[];
  onMerge: (name: string) => void;
}) {
  return (
    <Menu.Root>
      <Menu.Trigger
        title="Добавить переменную на этот график"
        className={cn(ICON_BUTTON, "data-[popup-open]:bg-muted")}
      >
        <PlusIcon className="size-3" />
      </Menu.Trigger>
      <Menu.Portal>
        <Menu.Positioner side="bottom" align="end" sideOffset={4} className="z-50">
          <Menu.Popup className="min-w-40 border border-border bg-popover p-1 shadow-md outline-none">
            <div className="px-2 py-1 text-[10px] tracking-wider text-muted-foreground uppercase">
              Добавить сюда
            </div>
            {options.map((variable) => (
              <Menu.Item
                key={variable.name}
                onClick={() => onMerge(variable.name)}
                className="flex cursor-default items-center justify-between gap-3 px-2 py-1 font-mono text-xs outline-none select-none data-[highlighted]:bg-muted"
              >
                <span className="truncate">{variable.name}</span>
                <span className="text-[10px] text-muted-foreground uppercase">
                  {variable.ctype}
                </span>
              </Menu.Item>
            ))}
          </Menu.Popup>
        </Menu.Positioner>
      </Menu.Portal>
    </Menu.Root>
  );
}

function ChartDialog({
  open,
  title,
  windowMs,
  onWindow,
  onClose,
  children,
}: {
  open: boolean;
  title: string | undefined;
  windowMs: number | null;
  onWindow: (value: number | null) => void;
  onClose: () => void;
  children: React.ReactNode;
}) {
  return (
    <Dialog.Root open={open} onOpenChange={(next) => !next && onClose()}>
      <Dialog.Portal>
        <Dialog.Backdrop className="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs" />
        <Dialog.Popup className="fixed inset-3 z-50 flex flex-col gap-3 border border-border bg-card p-4 shadow-lg outline-none md:inset-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <Dialog.Title className="truncate font-heading text-sm font-bold tracking-[0.12em] uppercase">
              {title}
            </Dialog.Title>
            <div className="flex items-center gap-2">
              <Segmented
                options={WINDOW_OPTIONS}
                value={windowMs}
                onSelect={onWindow}
              />
              <Dialog.Close
                className="flex size-7 shrink-0 items-center justify-center border border-border text-muted-foreground hover:bg-muted hover:text-foreground"
                aria-label="Закрыть"
              >
                <XIcon className="size-3.5" />
              </Dialog.Close>
            </div>
          </div>
          <div className="min-h-0 flex-1">{children}</div>
        </Dialog.Popup>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

function DeviceHeader({
  device,
  connection,
}: {
  device: DeviceDetail;
  connection: Connection;
}) {
  const status = STATUS_META[device.status];
  return (
    <header className="space-y-3">
      <Link
        href="/devices"
        className="inline-flex items-center gap-1.5 text-xs tracking-wide text-muted-foreground uppercase transition-colors hover:text-foreground"
      >
        <ArrowLeftIcon className="size-3.5" />
        Устройства
      </Link>
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <h1 className="font-heading text-lg font-bold tracking-[0.12em] uppercase">
          {device.name}
        </h1>
        <span className="font-mono text-xs text-muted-foreground">
          {device.id}
        </span>
        <span className="text-sm text-muted-foreground">{device.type}</span>
        <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <span className={`size-2 rounded-full ${status.dot}`} />
          {status.label}
        </span>
        <ConnectionBadge connection={connection} />
      </div>
    </header>
  );
}

const CONNECTION_META: Record<Connection, { label: string; dot: string }> = {
  connecting: { label: "подключение", dot: "bg-muted-foreground/40" },
  live: { label: "поток", dot: "bg-emerald-500 animate-pulse" },
  lost: { label: "нет связи", dot: "bg-destructive" },
};

function ConnectionBadge({ connection }: { connection: Connection }) {
  const meta = CONNECTION_META[connection];
  return (
    <span className="ml-auto flex items-center gap-1.5 border border-border px-2 py-1 text-[10px] tracking-wider text-muted-foreground uppercase">
      <span className={`size-1.5 rounded-full ${meta.dot}`} />
      {meta.label}
    </span>
  );
}

function VariableTable({
  deviceId,
  variables,
  values,
  selected,
  onWritten,
  onToggle,
}: {
  deviceId: string;
  variables: VariableInfo[];
  values: Record<string, number>;
  selected: Set<string>;
  onWritten: (name: string, value: number) => void;
  onToggle: (name: string) => void;
}) {
  if (variables.length === 0) {
    return <Notice>переменные не найдены</Notice>;
  }
  return (
    <div className="border border-border bg-card">
      <div className="grid grid-cols-[1fr_4rem_4rem_9rem_2rem] items-center gap-3 border-b border-border px-4 py-2 text-[10px] tracking-wider text-muted-foreground uppercase">
        <span>Переменная</span>
        <span>Тип</span>
        <span>Доступ</span>
        <span className="text-right">Значение</span>
        <span />
      </div>
      <ul className="divide-y divide-border">
        {variables.map((variable) => (
          <VariableRow
            key={variable.name}
            deviceId={deviceId}
            variable={variable}
            value={values[variable.name]}
            charted={selected.has(variable.name)}
            onWritten={onWritten}
            onToggle={onToggle}
          />
        ))}
      </ul>
    </div>
  );
}

function VariableRow({
  deviceId,
  variable,
  value,
  charted,
  onWritten,
  onToggle,
}: {
  deviceId: string;
  variable: VariableInfo;
  value: number | undefined;
  charted: boolean;
  onWritten: (name: string, value: number) => void;
  onToggle: (name: string) => void;
}) {
  const mode = MODE_META[variable.mode];
  const plottable = variable.mode !== "w";
  return (
    <li className="grid grid-cols-[1fr_4rem_4rem_9rem_2rem] items-start gap-3 px-4 py-2.5">
      <span className="truncate pt-0.5 font-mono text-sm">{variable.name}</span>
      <span className="pt-0.5 font-mono text-xs text-muted-foreground uppercase">
        {variable.ctype}
      </span>
      <span
        title={mode.title}
        className="pt-0.5 font-mono text-xs text-muted-foreground"
      >
        {mode.label}
      </span>
      {mode.writable ? (
        <WritableValue
          deviceId={deviceId}
          variable={variable}
          value={value}
          onWritten={onWritten}
        />
      ) : (
        <span className="pt-0.5 text-right font-mono text-sm tabular-nums">
          <ValueCell ctype={variable.ctype} value={value} />
        </span>
      )}
      <span className="flex justify-end pt-0.5">
        {plottable && (
          <button
            type="button"
            onClick={() => onToggle(variable.name)}
            aria-pressed={charted}
            title={charted ? "Убрать с графика" : "Добавить на график"}
            className={`flex size-6 items-center justify-center border transition-colors ${
              charted
                ? "border-foreground bg-foreground text-background"
                : "border-border text-muted-foreground/50 hover:text-foreground"
            }`}
          >
            <ChartLineIcon className="size-3.5" />
          </button>
        )}
      </span>
    </li>
  );
}

function ValueCell({
  ctype,
  value,
}: {
  ctype: NetVarCType;
  value: number | undefined;
}) {
  if (value === undefined) {
    return <span className="text-muted-foreground/50">...</span>;
  }
  return <span>{formatValue(ctype, value)}</span>;
}

function WritableValue({
  deviceId,
  variable,
  value,
  onWritten,
}: {
  deviceId: string;
  variable: VariableInfo;
  value: number | undefined;
  onWritten: (name: string, value: number) => void;
}) {
  const { state } = useAuth();
  const csrfToken =
    state.status === "authenticated" ? state.user.csrf_token : null;
  const writeOnly = variable.mode === "w";
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function startEditing() {
    setDraft(value === undefined ? "" : formatValue(variable.ctype, value));
    setError(null);
    setEditing(true);
  }

  async function submit() {
    const parsed = Number(draft);
    if (draft.trim() === "" || Number.isNaN(parsed)) {
      setError("введите число");
      return;
    }
    if (csrfToken === null) {
      setError("нет сессии");
      return;
    }
    setPending(true);
    setError(null);
    try {
      const written = await writeValue(
        deviceId,
        variable.name,
        parsed,
        csrfToken,
      );
      onWritten(written.name, written.value);
      setEditing(false);
    } catch (cause) {
      setError(describeWriteError(cause));
    } finally {
      setPending(false);
    }
  }

  if (!editing) {
    return (
      <div className="flex justify-end">
        <button
          type="button"
          onClick={startEditing}
          className="group flex items-center gap-1.5 font-mono text-sm tabular-nums hover:text-foreground"
        >
          {writeOnly || value === undefined ? (
            <span className="text-xs tracking-wide text-muted-foreground uppercase">
              задать
            </span>
          ) : (
            <span>{formatValue(variable.ctype, value)}</span>
          )}
          <PencilSimpleIcon className="size-3.5 text-muted-foreground/40 transition-colors group-hover:text-foreground" />
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-1">
      <div className="flex items-center gap-1">
        <input
          autoFocus
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") void submit();
            if (event.key === "Escape") setEditing(false);
          }}
          disabled={pending}
          inputMode="decimal"
          className="h-7 w-full min-w-0 border border-border bg-background px-2 text-right font-mono text-sm tabular-nums outline-none focus-visible:border-ring focus-visible:ring-1 focus-visible:ring-ring/50"
        />
        <button
          type="button"
          onClick={() => void submit()}
          disabled={pending}
          title="Записать"
          className="flex size-7 shrink-0 items-center justify-center border border-border hover:bg-muted disabled:opacity-50"
        >
          <CheckIcon className="size-3.5" />
        </button>
        <button
          type="button"
          onClick={() => setEditing(false)}
          disabled={pending}
          title="Отмена"
          className="flex size-7 shrink-0 items-center justify-center border border-border text-muted-foreground hover:bg-muted hover:text-foreground"
        >
          <XIcon className="size-3.5" />
        </button>
      </div>
      {error && (
        <p className="text-right text-[10px] break-words text-destructive">
          {error}
        </p>
      )}
    </div>
  );
}

function describeWriteError(cause: unknown): string {
  if (cause instanceof ApiError) {
    if (cause.detail) return cause.detail;
    if (cause.status === 403) return "запись запрещена";
    if (cause.status === 422) return "недопустимое значение";
  }
  return "не удалось записать";
}

function formatValue(ctype: NetVarCType, value: number): string {
  if (ctype === "f32" || ctype === "f64") {
    return Number.isInteger(value) ? value.toFixed(1) : String(value);
  }
  return String(value);
}

// На графике (оси, тултип, статистика) длинные float'ы не нужны, режем до
// 6 значащих цифр; целочисленные типы остаются точными.
function formatChartValue(ctype: NetVarCType, value: number): string {
  if (ctype === "f32" || ctype === "f64") {
    return Number(value.toPrecision(6)).toString();
  }
  return String(value);
}

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <section className="mx-auto w-full max-w-4xl flex-1 space-y-5 p-6">
      {children}
    </section>
  );
}

function Notice({ children }: { children: React.ReactNode }) {
  return (
    <p className="border border-dashed border-border bg-card px-4 py-10 text-center font-mono text-xs tracking-wider text-muted-foreground uppercase">
      {children}
    </p>
  );
}
