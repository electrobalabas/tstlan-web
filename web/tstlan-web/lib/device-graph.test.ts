import { describe, expect, it } from "vitest";

import { graphSelection, pickDeviceConfig } from "@/lib/device-graph";
import type { ConfigSummary, ConfigVar } from "@/lib/api";

function summary(over: Partial<ConfigSummary>): ConfigSummary {
  return {
    id: 1,
    name: "config",
    device_type: "multimeter",
    visibility: "public",
    owner_login: "someone",
    access: "read",
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...over,
  };
}

function cvar(name: string, graph: boolean): ConfigVar {
  return { name, ctype: "f32", graph, category: "" };
}

describe("pickDeviceConfig", () => {
  it("берёт конфиг с совпадающим device_type", () => {
    const picked = pickDeviceConfig(
      [
        summary({ id: 1, device_type: "calibrator" }),
        summary({ id: 2, device_type: "multimeter" }),
      ],
      "multimeter",
    );
    expect(picked?.id).toBe(2);
  });

  it("предпочитает свой конфиг чужому", () => {
    const picked = pickDeviceConfig(
      [
        summary({ id: 1, access: "read", updated_at: "2026-06-01T00:00:00Z" }),
        summary({ id: 2, access: "owner", updated_at: "2026-01-01T00:00:00Z" }),
      ],
      "multimeter",
    );
    expect(picked?.id).toBe(2);
  });

  it("при равном доступе берёт самый свежий", () => {
    const picked = pickDeviceConfig(
      [
        summary({ id: 1, access: "read", updated_at: "2026-01-01T00:00:00Z" }),
        summary({ id: 2, access: "read", updated_at: "2026-06-01T00:00:00Z" }),
      ],
      "multimeter",
    );
    expect(picked?.id).toBe(2);
  });

  it("возвращает null без совпадений", () => {
    expect(pickDeviceConfig([summary({ device_type: "x" })], "y")).toBeNull();
  });
});

describe("graphSelection", () => {
  it("выбирает помеченные graph и присутствующие у прибора переменные", () => {
    const result = graphSelection(
      [cvar("voltage", true), cvar("current", true), cvar("range", false)],
      ["voltage", "current", "range", "reset"],
    );
    expect(result).toEqual(new Set(["voltage", "current"]));
  });

  it("игнорирует graph-переменные, которых нет у прибора", () => {
    const result = graphSelection([cvar("ghost", true)], ["voltage"]);
    expect(result.size).toBe(0);
  });
});
