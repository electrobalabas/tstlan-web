"use client";

import { useEffect, useState } from "react";
import { PlusIcon, TrashIcon } from "@phosphor-icons/react/ssr";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  listUsers,
  shareConfig,
  unshareConfig,
  type ConfigDetail,
  type Role,
  type SharePermission,
  type UserSummary,
} from "@/lib/api";
import { PERMISSION_META, ROLE_META, availableGrantees } from "@/lib/configs";
import { describeShareError } from "@/lib/config-errors";

const FIELD =
  "h-9 w-full border border-border bg-background px-3 text-sm outline-none focus-visible:border-ring focus-visible:ring-1 focus-visible:ring-ring/50 disabled:opacity-60";

export function SharePanel({
  config,
  csrf,
  onChange,
}: {
  config: ConfigDetail;
  csrf: string;
  onChange: (config: ConfigDetail) => void;
}) {
  const [users, setUsers] = useState<UserSummary[]>([]);
  const [login, setLogin] = useState("");
  const [permission, setPermission] = useState<SharePermission>("read");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    listUsers()
      .then((list) => active && setUsers(list))
      .catch(() => undefined);
    return () => {
      active = false;
    };
  }, []);

  const roleOf = new Map(users.map((user) => [user.login, user.role]));
  const candidates = availableGrantees(users, config.owner_login, config.shares);

  async function grant(target: string, value: SharePermission) {
    if (target === "") return;
    setPending(true);
    setError(null);
    try {
      onChange(
        await shareConfig(config.id, { login: target, permission: value }, csrf),
      );
      setLogin("");
    } catch (cause) {
      setError(describeShareError(cause));
    } finally {
      setPending(false);
    }
  }

  async function revoke(target: string) {
    setPending(true);
    setError(null);
    try {
      onChange(await unshareConfig(config.id, target, csrf));
    } catch (cause) {
      setError(describeShareError(cause));
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="space-y-4 border border-border bg-card p-5">
      <h2 className="font-heading text-xs font-bold tracking-[0.15em] text-muted-foreground uppercase">
        Доступ
      </h2>

      <ul className="divide-y divide-border border border-border">
        <li className="flex items-center justify-between gap-3 px-3 py-2">
          <Principal login={config.owner_login} role={roleOf.get(config.owner_login)} />
          <span className="text-xs tracking-wide text-muted-foreground uppercase">
            Владелец
          </span>
        </li>
        {config.shares.map((share) => (
          <li
            key={share.login}
            className="flex items-center justify-between gap-3 px-3 py-2"
          >
            <Principal login={share.login} role={roleOf.get(share.login)} />
            <span className="flex items-center gap-2">
              <select
                value={share.permission}
                onChange={(event) =>
                  void grant(share.login, event.target.value as SharePermission)
                }
                disabled={pending}
                aria-label={`Право доступа ${share.login}`}
                className={cn(FIELD, "h-7 w-24")}
              >
                {(Object.keys(PERMISSION_META) as SharePermission[]).map(
                  (value) => (
                    <option key={value} value={value}>
                      {PERMISSION_META[value].label}
                    </option>
                  ),
                )}
              </select>
              <button
                type="button"
                onClick={() => void revoke(share.login)}
                disabled={pending}
                title="Убрать доступ"
                className="flex size-7 items-center justify-center border border-border text-muted-foreground transition-colors hover:text-destructive disabled:opacity-50"
              >
                <TrashIcon className="size-3.5" />
              </button>
            </span>
          </li>
        ))}
      </ul>

      <div className="flex items-end gap-2">
        <label className="block flex-1 space-y-1.5">
          <span className="text-xs tracking-wide text-muted-foreground uppercase">
            Добавить пользователя
          </span>
          <select
            value={login}
            onChange={(event) => setLogin(event.target.value)}
            disabled={candidates.length === 0}
            className={FIELD}
          >
            <option value="">
              {candidates.length === 0 ? "нет доступных" : "— выберите —"}
            </option>
            {candidates.map((user) => (
              <option key={user.login} value={user.login}>
                {user.login} · {ROLE_META[user.role].label}
              </option>
            ))}
          </select>
        </label>
        <select
          value={permission}
          onChange={(event) =>
            setPermission(event.target.value as SharePermission)
          }
          aria-label="Право доступа"
          className={cn(FIELD, "w-28")}
        >
          {(Object.keys(PERMISSION_META) as SharePermission[]).map((value) => (
            <option key={value} value={value}>
              {PERMISSION_META[value].label}
            </option>
          ))}
        </select>
        <Button
          type="button"
          size="lg"
          onClick={() => void grant(login, permission)}
          disabled={pending || login === ""}
        >
          <PlusIcon />
          Выдать
        </Button>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}
    </div>
  );
}

function Principal({ login, role }: { login: string; role?: Role }) {
  return (
    <span className="flex min-w-0 items-center gap-2">
      <span className="truncate font-mono text-sm">{login}</span>
      {role && (
        <span className="shrink-0 border border-border px-1.5 py-0.5 text-[10px] tracking-wider text-muted-foreground uppercase">
          {ROLE_META[role].label}
        </span>
      )}
    </span>
  );
}
