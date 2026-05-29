"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { GaugeIcon, HardDrivesIcon } from "@phosphor-icons/react/ssr";
import type { Icon } from "@phosphor-icons/react";

import { cn } from "@/lib/utils";

type NavItem = {
  href: string;
  label: string;
  icon: Icon;
};

const NAV: NavItem[] = [
  { href: "/dashboard", label: "Дашборд", icon: GaugeIcon },
  { href: "/devices", label: "Устройства", icon: HardDrivesIcon },
];

export function SiteHeader() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-50 border-b border-border bg-background/85 backdrop-blur">
      <div className="flex h-12 items-stretch gap-6 px-4">
        <Link
          href="/dashboard"
          className="group flex items-center gap-2.5 self-center"
        >
          <span className="flex size-5 items-center justify-center border border-foreground/70">
            <span className="size-1.5 bg-foreground transition-colors group-hover:bg-foreground/50" />
          </span>
          <span className="font-heading text-sm font-bold tracking-[0.2em]">
            TSTLAN
          </span>
          <span className="text-[10px] tracking-wider text-muted-foreground">
            v0.1
          </span>
        </Link>

        <nav className="flex items-stretch">
          {NAV.map(({ href, label, icon: ItemIcon }) => {
            const active = pathname === href || pathname.startsWith(`${href}/`);
            return (
              <Link
                key={href}
                href={href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "relative flex items-center gap-1.5 px-3 text-xs font-medium tracking-wide uppercase transition-colors",
                  active
                    ? "text-foreground"
                    : "text-muted-foreground hover:text-foreground",
                )}
              >
                <ItemIcon
                  className="size-3.5"
                  weight={active ? "fill" : "regular"}
                />
                {label}
                {active && (
                  <span className="absolute inset-x-0 -bottom-px h-0.5 bg-foreground" />
                )}
              </Link>
            );
          })}
        </nav>

        <div className="ml-auto flex items-center gap-2 self-center text-xs tracking-wide text-muted-foreground">
          <span
            className="size-1.5 rounded-full bg-muted-foreground/50"
            aria-hidden
          />
          <span className="uppercase">офлайн</span>
        </div>
      </div>
    </header>
  );
}
