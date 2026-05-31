"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  ArrowLeftIcon,
  MagnifyingGlassIcon,
} from "@phosphor-icons/react/ssr";

import {
  getDevice,
  streamValues,
  type DeviceDetail,
  type NetVarCType,
  type VariableInfo,
} from "@/lib/api";
import { ApiError } from "@/lib/api";
import { MODE_META, STATUS_META } from "@/lib/devices";

type LoadState =
  | { status: "loading" }
  | { status: "notfound" }
  | { status: "error" }
  | { status: "ready"; device: DeviceDetail };

type Connection = "connecting" | "live" | "lost";

export function DeviceMonitor({ deviceId }: { deviceId: string }) {
  const [load, setLoad] = useState<LoadState>({ status: "loading" });
  const [values, setValues] = useState<Record<string, number>>({});
  const [connection, setConnection] = useState<Connection>("connecting");
  const [query, setQuery] = useState("");

  useEffect(() => {
    let active = true;
    setLoad({ status: "loading" });
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
    setConnection("connecting");
    const stop = streamValues(
      deviceId,
      (snapshot) => {
        setValues(Object.fromEntries(snapshot.map((v) => [v.name, v.value])));
        setConnection("live");
      },
      () => setConnection("lost"),
    );
    return stop;
  }, [deviceId, load.status]);

  if (load.status !== "ready") {
    return (
      <Shell>
        {load.status === "loading" && <Notice>загрузка…</Notice>}
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

      <VariableTable variables={variables} values={values} />
    </Shell>
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
  variables,
  values,
}: {
  variables: VariableInfo[];
  values: Record<string, number>;
}) {
  if (variables.length === 0) {
    return <Notice>переменные не найдены</Notice>;
  }
  return (
    <div className="border border-border bg-card">
      <div className="grid grid-cols-[1fr_4rem_4rem_8rem] items-center gap-3 border-b border-border px-4 py-2 text-[10px] tracking-wider text-muted-foreground uppercase">
        <span>Переменная</span>
        <span>Тип</span>
        <span>Доступ</span>
        <span className="text-right">Значение</span>
      </div>
      <ul className="divide-y divide-border">
        {variables.map((variable) => (
          <VariableRow
            key={variable.name}
            variable={variable}
            value={values[variable.name]}
          />
        ))}
      </ul>
    </div>
  );
}

function VariableRow({
  variable,
  value,
}: {
  variable: VariableInfo;
  value: number | undefined;
}) {
  const mode = MODE_META[variable.mode];
  return (
    <li className="grid grid-cols-[1fr_4rem_4rem_8rem] items-center gap-3 px-4 py-2.5">
      <span className="truncate font-mono text-sm">{variable.name}</span>
      <span className="font-mono text-xs text-muted-foreground uppercase">
        {variable.ctype}
      </span>
      <span
        title={mode.title}
        className="font-mono text-xs text-muted-foreground"
      >
        {mode.label}
      </span>
      <span className="text-right font-mono text-sm tabular-nums">
        <ValueCell
          ctype={variable.ctype}
          value={value}
          writeOnly={variable.mode === "w"}
        />
      </span>
    </li>
  );
}

function ValueCell({
  ctype,
  value,
  writeOnly,
}: {
  ctype: NetVarCType;
  value: number | undefined;
  writeOnly: boolean;
}) {
  if (writeOnly) {
    return <span className="text-muted-foreground/50">—</span>;
  }
  if (value === undefined) {
    return <span className="text-muted-foreground/50">…</span>;
  }
  return <span>{formatValue(ctype, value)}</span>;
}

function formatValue(ctype: NetVarCType, value: number): string {
  if (ctype === "f32" || ctype === "f64") {
    return Number.isInteger(value) ? value.toFixed(1) : String(value);
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
