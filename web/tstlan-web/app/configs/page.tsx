"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  CaretRightIcon,
  PlusIcon,
  SlidersIcon,
} from "@phosphor-icons/react/ssr";

import { buttonVariants } from "@/components/ui/button";
import { listConfigs, type ConfigSummary } from "@/lib/api";
import { VISIBILITY_META } from "@/lib/configs";

type LoadState =
  | { status: "loading" }
  | { status: "error" }
  | { status: "ready"; configs: ConfigSummary[] };

export default function ConfigsPage() {
  const [state, setState] = useState<LoadState>({ status: "loading" });

  useEffect(() => {
    let active = true;
    listConfigs()
      .then((configs) => active && setState({ status: "ready", configs }))
      .catch(() => active && setState({ status: "error" }));
    return () => {
      active = false;
    };
  }, []);

  return (
    <section className="mx-auto w-full max-w-4xl flex-1 space-y-6 p-6">
      <header className="flex items-center gap-3">
        <span className="flex size-9 items-center justify-center border border-border bg-card">
          <SlidersIcon className="size-5" />
        </span>
        <div className="flex-1">
          <h1 className="font-heading text-lg font-bold tracking-[0.15em] uppercase">
            Конфиги
          </h1>
          <p className="text-sm text-muted-foreground">
            Профили приборов: подключение и набор переменных.
          </p>
        </div>
        <Link href="/configs/new" className={buttonVariants({ size: "lg" })}>
          <PlusIcon />
          Создать
        </Link>
      </header>

      {state.status === "loading" && <Notice>загрузка...</Notice>}
      {state.status === "error" && (
        <Notice>не удалось загрузить конфиги</Notice>
      )}
      {state.status === "ready" &&
        (state.configs.length === 0 ? (
          <Notice>конфиги не созданы</Notice>
        ) : (
          <ConfigTable configs={state.configs} />
        ))}
    </section>
  );
}

function ConfigTable({ configs }: { configs: ConfigSummary[] }) {
  return (
    <div className="border border-border bg-card">
      <div className="grid grid-cols-[1fr_8rem_6rem_2rem] items-center gap-3 border-b border-border px-4 py-2 text-[10px] tracking-wider text-muted-foreground uppercase">
        <span>Конфиг</span>
        <span>Тип прибора</span>
        <span>Видимость</span>
        <span />
      </div>
      <ul className="divide-y divide-border">
        {configs.map((config) => (
          <li key={config.id}>
            <Link
              href={`/configs/${config.id}`}
              className="group grid grid-cols-[1fr_8rem_6rem_2rem] items-center gap-3 px-4 py-3 transition-colors hover:bg-muted"
            >
              <span className="min-w-0">
                <span className="block truncate text-sm font-medium">
                  {config.name}
                </span>
                <span className="block truncate font-mono text-xs text-muted-foreground">
                  {config.owner_login}
                </span>
              </span>
              <span className="truncate font-mono text-xs text-muted-foreground">
                {config.device_type}
              </span>
              <span className="text-xs text-muted-foreground">
                {VISIBILITY_META[config.visibility].label}
              </span>
              <CaretRightIcon className="size-4 text-muted-foreground transition-colors group-hover:text-foreground" />
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}

function Notice({ children }: { children: React.ReactNode }) {
  return (
    <p className="border border-dashed border-border bg-card px-4 py-10 text-center font-mono text-xs tracking-wider text-muted-foreground uppercase">
      {children}
    </p>
  );
}
