"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { useAuth } from "@/components/auth-provider";
import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api";

const FIELD_CLASS =
  "h-9 w-full border border-border bg-background px-3 text-sm outline-none focus-visible:border-ring focus-visible:ring-1 focus-visible:ring-ring/50";

export default function LoginPage() {
  const router = useRouter();
  const { signIn } = useAuth();
  const [login, setLogin] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setError(null);
    try {
      await signIn(login, password);
      router.replace("/dashboard");
    } catch (cause) {
      setError(
        cause instanceof ApiError && cause.status === 401
          ? "Неверный логин или пароль"
          : "Не удалось войти",
      );
      setPending(false);
    }
  }

  return (
    <section className="flex flex-1 items-center justify-center p-6">
      <form
        onSubmit={onSubmit}
        className="w-full max-w-sm space-y-5 border border-border bg-card p-8"
      >
        <div className="space-y-1">
          <h1 className="font-heading text-lg font-bold tracking-[0.15em] uppercase">
            Вход
          </h1>
          <p className="text-sm text-muted-foreground">
            Войдите, чтобы продолжить.
          </p>
        </div>

        <label className="block space-y-1.5">
          <span className="text-xs tracking-wide text-muted-foreground uppercase">
            Логин
          </span>
          <input
            value={login}
            onChange={(event) => setLogin(event.target.value)}
            autoComplete="username"
            required
            className={FIELD_CLASS}
          />
        </label>

        <label className="block space-y-1.5">
          <span className="text-xs tracking-wide text-muted-foreground uppercase">
            Пароль
          </span>
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete="current-password"
            required
            className={FIELD_CLASS}
          />
        </label>

        {error && <p className="text-sm text-destructive">{error}</p>}

        <Button type="submit" size="lg" disabled={pending} className="w-full">
          {pending ? "Вход…" : "Войти"}
        </Button>
      </form>
    </section>
  );
}
