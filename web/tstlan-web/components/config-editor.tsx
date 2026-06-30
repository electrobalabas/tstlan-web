"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import { ArrowLeftIcon } from "@phosphor-icons/react/ssr";

import { useAuth } from "@/components/auth-provider";
import { ConfigForm, type ConfigFormMode } from "@/components/config-form";
import { SharePanel } from "@/components/share-panel";
import { Button } from "@/components/ui/button";
import {
  ApiError,
  deleteConfig,
  getConfig,
  updateConfig,
  type ConfigAccess,
  type ConfigDetail,
} from "@/lib/api";
import {
  VISIBILITY_META,
  canPublish,
  configToDraft,
  describeConfigAccess,
  draftToPayload,
  type ConfigFormDraft,
} from "@/lib/configs";
import { describeSaveError } from "@/lib/config-errors";

type LoadState =
  | { status: "loading" }
  | { status: "notfound" }
  | { status: "error" }
  | { status: "ready"; config: ConfigDetail };

const MODE_BY_ACCESS: Record<ConfigAccess, ConfigFormMode> = {
  owner: "owner",
  write: "write",
  read: "read",
};

export function ConfigEditor({ id }: { id: number }) {
  const router = useRouter();
  const { state } = useAuth();
  const csrf = state.status === "authenticated" ? state.user.csrf_token : null;
  const role = state.status === "authenticated" ? state.user.role : "user";

  const [load, setLoad] = useState<LoadState>({ status: "loading" });
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    getConfig(id)
      .then((config) => active && setLoad({ status: "ready", config }))
      .catch((cause) => {
        if (!active) return;
        const denied =
          cause instanceof ApiError &&
          (cause.status === 404 || cause.status === 403);
        setLoad({ status: denied ? "notfound" : "error" });
      });
    return () => {
      active = false;
    };
  }, [id]);

  if (load.status !== "ready") {
    return (
      <Shell>
        {load.status === "loading" && <Notice>загрузка...</Notice>}
        {load.status === "notfound" && <Notice>конфиг не найден</Notice>}
        {load.status === "error" && (
          <Notice>не удалось загрузить конфиг</Notice>
        )}
      </Shell>
    );
  }

  const { config } = load;

  async function submit(draft: ConfigFormDraft): Promise<boolean> {
    if (csrf === null) return false;
    setPending(true);
    setError(null);
    const body =
      config.access === "owner"
        ? {
            name: draft.name,
            // Видимость (публикацию) меняют только dev/admin. Прочие владельцы
            // не видят чекбокс и не должны переотправлять текущий public,
            // иначе бэкенд отклонит сохранение даже имени/payload.
            ...(canPublish(role) ? { visibility: draft.visibility } : {}),
            payload: draftToPayload(draft),
          }
        : { payload: draftToPayload(draft) };
    try {
      setLoad({ status: "ready", config: await updateConfig(id, body, csrf) });
      return true;
    } catch (cause) {
      setError(describeSaveError(cause));
      return false;
    } finally {
      setPending(false);
    }
  }

  async function remove() {
    if (csrf === null) return;
    setPending(true);
    setError(null);
    try {
      await deleteConfig(id, csrf);
      router.push("/configs");
    } catch (cause) {
      setError(describeSaveError(cause));
      setPending(false);
    }
  }

  return (
    <Shell>
      <Header config={config} />
      <ConfigForm
        initial={configToDraft(config)}
        role={role}
        mode={MODE_BY_ACCESS[config.access]}
        pending={pending}
        error={error}
        submitLabel="Сохранить"
        onSubmit={submit}
      />
      {config.access === "owner" && csrf && (
        <>
          <SharePanel
            config={config}
            csrf={csrf}
            onChange={(updated) =>
              setLoad({ status: "ready", config: updated })
            }
          />
          <div className="flex items-center justify-between gap-3 border border-destructive/30 bg-card p-5">
            <span className="text-sm text-muted-foreground">
              Удаление конфига необратимо.
            </span>
            <Button
              type="button"
              variant="destructive"
              onClick={() => void remove()}
              disabled={pending}
            >
              Удалить
            </Button>
          </div>
        </>
      )}
    </Shell>
  );
}

function Header({ config }: { config: ConfigDetail }) {
  return (
    <header className="space-y-3">
      <Link
        href="/configs"
        className="inline-flex items-center gap-1.5 text-xs tracking-wide text-muted-foreground uppercase transition-colors hover:text-foreground"
      >
        <ArrowLeftIcon className="size-3.5" />
        Конфиги
      </Link>
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <h1 className="font-heading text-lg font-bold tracking-[0.12em] uppercase">
          {config.name}
        </h1>
        <span className="font-mono text-xs text-muted-foreground">
          {config.device_type}
        </span>
        <span className="border border-border px-2 py-0.5 text-[10px] tracking-wider text-muted-foreground uppercase">
          {VISIBILITY_META[config.visibility].label}
        </span>
        <span className="ml-auto text-xs text-muted-foreground">
          {config.owner_login}
          <span className="ml-1.5 text-muted-foreground/60 uppercase">
            {describeConfigAccess(
              config.access,
              config.visibility,
              config.shares.length,
            )}
          </span>
        </span>
      </div>
    </header>
  );
}

function Shell({ children }: { children: ReactNode }) {
  return (
    <section className="mx-auto w-full max-w-3xl flex-1 space-y-5 p-6">
      {children}
    </section>
  );
}

function Notice({ children }: { children: ReactNode }) {
  return (
    <p className="border border-dashed border-border bg-card px-4 py-10 text-center font-mono text-xs tracking-wider text-muted-foreground uppercase">
      {children}
    </p>
  );
}
