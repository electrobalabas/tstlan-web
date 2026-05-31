"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { CaretRightIcon, HardDrivesIcon } from "@phosphor-icons/react/ssr";

import { listDevices, type DeviceSummary } from "@/lib/api";
import { STATUS_META } from "@/lib/devices";

type LoadState =
  | { status: "loading" }
  | { status: "error" }
  | { status: "ready"; devices: DeviceSummary[] };

export default function DevicesPage() {
  const [state, setState] = useState<LoadState>({ status: "loading" });

  useEffect(() => {
    let active = true;
    listDevices()
      .then((devices) => active && setState({ status: "ready", devices }))
      .catch(() => active && setState({ status: "error" }));
    return () => {
      active = false;
    };
  }, []);

  return (
    <section className="mx-auto w-full max-w-4xl flex-1 space-y-6 p-6">
      <header className="flex items-center gap-3">
        <span className="flex size-9 items-center justify-center border border-border bg-card">
          <HardDrivesIcon className="size-5" />
        </span>
        <div>
          <h1 className="font-heading text-lg font-bold tracking-[0.15em] uppercase">
            Устройства
          </h1>
          <p className="text-sm text-muted-foreground">
            Приборы, подключённые к платформе.
          </p>
        </div>
      </header>

      {state.status === "loading" && <Notice>загрузка…</Notice>}
      {state.status === "error" && (
        <Notice>не удалось загрузить список устройств</Notice>
      )}
      {state.status === "ready" &&
        (state.devices.length === 0 ? (
          <Notice>устройства не настроены</Notice>
        ) : (
          <DeviceTable devices={state.devices} />
        ))}
    </section>
  );
}

function DeviceTable({ devices }: { devices: DeviceSummary[] }) {
  return (
    <div className="border border-border bg-card">
      <div className="grid grid-cols-[1fr_8rem_5rem_2rem] items-center gap-3 border-b border-border px-4 py-2 text-[10px] tracking-wider text-muted-foreground uppercase">
        <span>Прибор</span>
        <span>Тип</span>
        <span className="text-right">Переменных</span>
        <span />
      </div>
      <ul className="divide-y divide-border">
        {devices.map((device) => (
          <li key={device.id}>
            <Link
              href={`/devices/${device.id}`}
              className="group grid grid-cols-[1fr_8rem_5rem_2rem] items-center gap-3 px-4 py-3 transition-colors hover:bg-muted"
            >
              <span className="flex items-center gap-3">
                <StatusDot status={device.status} />
                <span className="min-w-0">
                  <span className="block truncate text-sm font-medium">
                    {device.name}
                  </span>
                  <span className="block truncate font-mono text-xs text-muted-foreground">
                    {device.id}
                  </span>
                </span>
              </span>
              <span className="truncate text-sm text-muted-foreground">
                {device.type}
              </span>
              <span className="text-right font-mono text-sm tabular-nums">
                {device.variable_count}
              </span>
              <CaretRightIcon className="size-4 text-muted-foreground transition-colors group-hover:text-foreground" />
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}

function StatusDot({ status }: { status: DeviceSummary["status"] }) {
  const meta = STATUS_META[status];
  return (
    <span
      title={meta.label}
      aria-label={meta.label}
      className={`size-2 shrink-0 rounded-full ${meta.dot}`}
    />
  );
}

function Notice({ children }: { children: React.ReactNode }) {
  return (
    <p className="border border-dashed border-border bg-card px-4 py-10 text-center font-mono text-xs tracking-wider text-muted-foreground uppercase">
      {children}
    </p>
  );
}
