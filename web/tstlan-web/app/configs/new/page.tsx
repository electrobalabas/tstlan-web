"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { ArrowLeftIcon } from "@phosphor-icons/react/ssr";

import { useAuth } from "@/components/auth-provider";
import { ConfigForm } from "@/components/config-form";
import { createConfig } from "@/lib/api";
import { draftToPayload, emptyDraft, type ConfigFormDraft } from "@/lib/configs";
import { describeSaveError } from "@/lib/config-errors";

export default function NewConfigPage() {
  const router = useRouter();
  const { state } = useAuth();
  const csrf = state.status === "authenticated" ? state.user.csrf_token : null;
  const role = state.status === "authenticated" ? state.user.role : "user";

  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(draft: ConfigFormDraft): Promise<boolean> {
    if (csrf === null) return false;
    setPending(true);
    setError(null);
    try {
      const created = await createConfig(
        {
          name: draft.name,
          device_type: draft.deviceType,
          visibility: draft.visibility,
          payload: draftToPayload(draft),
        },
        csrf,
      );
      router.push(`/configs/${created.id}`);
      return true;
    } catch (cause) {
      setError(describeSaveError(cause));
      setPending(false);
      return false;
    }
  }

  return (
    <section className="mx-auto w-full max-w-3xl flex-1 space-y-5 p-6">
      <Link
        href="/configs"
        className="inline-flex items-center gap-1.5 text-xs tracking-wide text-muted-foreground uppercase transition-colors hover:text-foreground"
      >
        <ArrowLeftIcon className="size-3.5" />
        Конфиги
      </Link>
      <h1 className="font-heading text-lg font-bold tracking-[0.12em] uppercase">
        Новый конфиг
      </h1>
      <ConfigForm
        initial={emptyDraft()}
        role={role}
        mode="create"
        pending={pending}
        error={error}
        submitLabel="Создать"
        onSubmit={submit}
      />
    </section>
  );
}
