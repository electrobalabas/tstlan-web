import type { Icon } from "@phosphor-icons/react";

type Props = {
  icon: Icon;
  title: string;
  description?: string;
};

export function PagePlaceholder({ icon: PageIcon, title, description }: Props) {
  return (
    <section className="flex flex-1 items-center justify-center p-6">
      <div
        className="relative flex w-full max-w-lg flex-col items-center gap-5 border border-border bg-card px-8 py-14 text-center"
        style={{
          backgroundImage: "radial-gradient(var(--border) 1px, transparent 1px)",
          backgroundSize: "18px 18px",
        }}
      >
        <Corner className="-top-px -left-px border-t-2 border-l-2" />
        <Corner className="-top-px -right-px border-t-2 border-r-2" />
        <Corner className="-bottom-px -left-px border-b-2 border-l-2" />
        <Corner className="-bottom-px -right-px border-b-2 border-r-2" />

        <span className="flex size-12 items-center justify-center border border-border bg-background">
          <PageIcon className="size-6 text-foreground" weight="regular" />
        </span>

        <div className="space-y-1.5">
          <h1 className="font-heading text-lg font-bold tracking-[0.15em] uppercase">
            {title}
          </h1>
          {description && (
            <p className="text-sm text-muted-foreground">{description}</p>
          )}
        </div>

        <span className="font-mono text-xs text-muted-foreground/70">
          {"// раздел в разработке"}
        </span>
      </div>
    </section>
  );
}

function Corner({ className }: { className: string }) {
  return (
    <span
      aria-hidden
      className={`pointer-events-none absolute size-3 border-foreground ${className}`}
    />
  );
}
