"use client";

import { useMemo, useState, type FormEvent, type ReactNode } from "react";
import {
  ChartLineIcon,
  PlusIcon,
  TrashIcon,
} from "@phosphor-icons/react/ssr";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { NetVarCType, Role, Transport } from "@/lib/api";
import {
  CTYPES,
  MODBUS_FIELDS,
  TRANSPORT_META,
  VISIBILITY_META,
  canPublish,
  hasErrors,
  isModbus,
  needsNetwork,
  nextVariableIndex,
  validateConfigForm,
  type ConfigFormDraft,
  type VariableDraft,
} from "@/lib/configs";

const FIELD =
  "h-9 w-full border border-border bg-background px-3 text-sm outline-none focus-visible:border-ring focus-visible:ring-1 focus-visible:ring-ring/50 disabled:cursor-not-allowed disabled:opacity-60";
const CELL =
  "h-8 w-full min-w-0 border border-border bg-background px-2 text-sm outline-none focus-visible:border-ring focus-visible:ring-1 focus-visible:ring-ring/50 disabled:cursor-not-allowed disabled:opacity-60";

export type ConfigFormMode = "create" | "owner" | "write" | "read";

export function ConfigForm({
  initial,
  role,
  mode,
  pending,
  error,
  submitLabel,
  onSubmit,
}: {
  initial: ConfigFormDraft;
  role: Role;
  mode: ConfigFormMode;
  pending: boolean;
  error: string | null;
  submitLabel: string;
  onSubmit: (draft: ConfigFormDraft) => void;
}) {
  const [draft, setDraft] = useState<ConfigFormDraft>(initial);
  const [showErrors, setShowErrors] = useState(false);
  const errors = useMemo(() => validateConfigForm(draft), [draft]);

  const metaEditable = mode === "create" || mode === "owner";
  const deviceTypeEditable = mode === "create";
  const payloadEditable = mode !== "read";
  const showSubmit = mode !== "read";

  function update(patch: Partial<ConfigFormDraft>) {
    setDraft((prev) => ({ ...prev, ...patch }));
  }

  function onFormSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setShowErrors(true);
    if (hasErrors(errors)) return;
    onSubmit(draft);
  }

  const at = (value?: string) => (showErrors ? value : undefined);
  const network = needsNetwork(draft.transport);
  const modbus = isModbus(draft.transport);

  return (
    <form onSubmit={onFormSubmit} className="space-y-5">
      <Section title="Конфиг">
        <Field label="Название" error={at(errors.name)}>
          <input
            value={draft.name}
            onChange={(event) => update({ name: event.target.value })}
            disabled={!metaEditable}
            className={FIELD}
          />
        </Field>
        <Field label="Тип прибора" error={at(errors.deviceType)}>
          <input
            value={draft.deviceType}
            onChange={(event) => update({ deviceType: event.target.value })}
            disabled={!deviceTypeEditable}
            className={FIELD}
          />
        </Field>
        {canPublish(role) && metaEditable && (
          <label className="flex items-start gap-2.5">
            <input
              type="checkbox"
              checked={draft.visibility === "public"}
              onChange={(event) =>
                update({
                  visibility: event.target.checked ? "public" : "private",
                })
              }
              className="mt-0.5 size-4 accent-foreground"
            />
            <span className="space-y-0.5">
              <span className="block text-xs tracking-wide uppercase">
                Публичный доступ
              </span>
              <span className="block text-[11px] text-muted-foreground">
                {VISIBILITY_META.public.hint}
              </span>
            </span>
          </label>
        )}
      </Section>

      <Section title="Подключение">
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Транспорт">
            <select
              value={draft.transport}
              onChange={(event) =>
                update({ transport: event.target.value as Transport })
              }
              disabled={!payloadEditable}
              className={FIELD}
            >
              {(Object.keys(TRANSPORT_META) as Transport[]).map((value) => (
                <option key={value} value={value}>
                  {TRANSPORT_META[value].label}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Период опроса, мс" error={at(errors.pollPeriodMs)}>
            <input
              value={draft.pollPeriodMs}
              onChange={(event) => update({ pollPeriodMs: event.target.value })}
              disabled={!payloadEditable}
              inputMode="numeric"
              className={FIELD}
            />
          </Field>
        </div>
        {network && (
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="IP-адрес" error={at(errors.ip)}>
              <input
                value={draft.ip}
                onChange={(event) => update({ ip: event.target.value })}
                disabled={!payloadEditable}
                className={FIELD}
              />
            </Field>
            <Field label="Порт" error={at(errors.port)}>
              <input
                value={draft.port}
                onChange={(event) => update({ port: event.target.value })}
                disabled={!payloadEditable}
                inputMode="numeric"
                className={FIELD}
              />
            </Field>
          </div>
        )}
        {draft.transport === "gpib" && (
          <Field label="Адрес GPIB" error={at(errors.gpibAddr)}>
            <input
              value={draft.gpibAddr}
              onChange={(event) => update({ gpibAddr: event.target.value })}
              disabled={!payloadEditable}
              inputMode="numeric"
              className={FIELD}
            />
          </Field>
        )}
        {draft.transport === "com" && (
          <Field label="Имя COM-порта" error={at(errors.comName)}>
            <input
              value={draft.comName}
              onChange={(event) => update({ comName: event.target.value })}
              disabled={!payloadEditable}
              className={FIELD}
            />
          </Field>
        )}
        {modbus && (
          <>
            <Field label="Запрос на получение IP">
              <input
                value={draft.ipRequest}
                onChange={(event) => update({ ipRequest: event.target.value })}
                disabled={!payloadEditable}
                className={FIELD}
              />
            </Field>
            <div className="grid gap-4 sm:grid-cols-2">
              {MODBUS_FIELDS.map((field) => (
                <Field
                  key={field.key}
                  label={field.label}
                  error={at(errors.modbus?.[field.key])}
                >
                  <input
                    value={draft[field.key]}
                    onChange={(event) =>
                      update({
                        [field.key]: event.target.value,
                      } as Partial<ConfigFormDraft>)
                    }
                    disabled={!payloadEditable}
                    inputMode="numeric"
                    className={FIELD}
                  />
                </Field>
              ))}
            </div>
          </>
        )}
      </Section>

      <VariablesSection
        variables={draft.variables}
        errors={showErrors ? errors.variables : undefined}
        editable={payloadEditable}
        onChange={(variables) => update({ variables })}
      />

      {error && <p className="text-sm text-destructive">{error}</p>}

      {showSubmit && (
        <div className="flex justify-end">
          <Button type="submit" size="lg" disabled={pending}>
            {pending ? "Сохранение…" : submitLabel}
          </Button>
        </div>
      )}
    </form>
  );
}

function VariablesSection({
  variables,
  errors,
  editable,
  onChange,
}: {
  variables: VariableDraft[];
  errors?: Record<number, string>;
  editable: boolean;
  onChange: (variables: VariableDraft[]) => void;
}) {
  function updateAt(index: number, patch: Partial<VariableDraft>) {
    onChange(
      variables.map((variable, position) =>
        position === index ? { ...variable, ...patch } : variable,
      ),
    );
  }
  function add() {
    onChange([
      ...variables,
      {
        index: nextVariableIndex(variables),
        name: "",
        ctype: "f32",
        graph: false,
        category: "",
      },
    ]);
  }
  function removeAt(index: number) {
    onChange(variables.filter((_, position) => position !== index));
  }

  return (
    <Section title={`Переменные · ${variables.length}`}>
      {variables.length === 0 ? (
        <p className="font-mono text-xs text-muted-foreground">
          переменные не добавлены
        </p>
      ) : (
        <ul className="space-y-2">
          {variables.map((variable, index) => (
            <li key={index} className="space-y-1">
              <div className="grid grid-cols-[3.5rem_1fr_5rem_2rem_1fr_2rem] items-center gap-2">
                <input
                  value={String(variable.index)}
                  onChange={(event) =>
                    updateAt(index, {
                      index: Number(event.target.value.replace(/\D/g, "")) || 0,
                    })
                  }
                  disabled={!editable}
                  title="Адрес"
                  inputMode="numeric"
                  className={cn(CELL, "font-mono tabular-nums")}
                />
                <input
                  value={variable.name}
                  onChange={(event) =>
                    updateAt(index, { name: event.target.value })
                  }
                  disabled={!editable}
                  placeholder="имя"
                  className={cn(CELL, "font-mono")}
                />
                <select
                  value={variable.ctype}
                  onChange={(event) =>
                    updateAt(index, { ctype: event.target.value as NetVarCType })
                  }
                  disabled={!editable}
                  className={cn(CELL, "font-mono uppercase")}
                >
                  {CTYPES.map((ctype) => (
                    <option key={ctype} value={ctype}>
                      {ctype}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={() => updateAt(index, { graph: !variable.graph })}
                  disabled={!editable}
                  aria-pressed={variable.graph}
                  title="На график"
                  className={cn(
                    "flex h-8 items-center justify-center border transition-colors disabled:opacity-50",
                    variable.graph
                      ? "border-foreground bg-foreground text-background"
                      : "border-border text-muted-foreground/50 hover:text-foreground",
                  )}
                >
                  <ChartLineIcon className="size-3.5" />
                </button>
                <input
                  value={variable.category}
                  onChange={(event) =>
                    updateAt(index, { category: event.target.value })
                  }
                  disabled={!editable}
                  placeholder="категория"
                  className={CELL}
                />
                <button
                  type="button"
                  onClick={() => removeAt(index)}
                  disabled={!editable}
                  title="Удалить"
                  className="flex h-8 items-center justify-center border border-border text-muted-foreground transition-colors hover:text-destructive disabled:opacity-50"
                >
                  <TrashIcon className="size-3.5" />
                </button>
              </div>
              {errors?.[index] && (
                <p className="text-[11px] text-destructive">{errors[index]}</p>
              )}
            </li>
          ))}
        </ul>
      )}
      {editable && (
        <Button type="button" variant="outline" size="sm" onClick={add}>
          <PlusIcon />
          Добавить переменную
        </Button>
      )}
    </Section>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="space-y-4 border border-border bg-card p-5">
      <h2 className="font-heading text-xs font-bold tracking-[0.15em] text-muted-foreground uppercase">
        {title}
      </h2>
      {children}
    </div>
  );
}

function Field({
  label,
  hint,
  error,
  children,
}: {
  label: string;
  hint?: string;
  error?: string;
  children: ReactNode;
}) {
  return (
    <label className="block space-y-1.5">
      <span className="text-xs tracking-wide text-muted-foreground uppercase">
        {label}
      </span>
      {children}
      {error ? (
        <span className="block text-[11px] text-destructive">{error}</span>
      ) : (
        hint && (
          <span className="block text-[11px] text-muted-foreground">{hint}</span>
        )
      )}
    </label>
  );
}
