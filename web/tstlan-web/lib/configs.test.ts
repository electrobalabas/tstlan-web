import { describe, expect, it } from "vitest";

import {
  availableGrantees,
  canPublish,
  configToDraft,
  describeConfigAccess,
  draftToPayload,
  emptyDraft,
  formatOffset,
  hasErrors,
  validateConfigForm,
  variableOffsets,
  type ConfigFormDraft,
} from "@/lib/configs";
import type { ConfigDetail, UserSummary } from "@/lib/api";

function validDraft(over: Partial<ConfigFormDraft> = {}): ConfigFormDraft {
  return {
    name: "Мультиметр стенд 1",
    deviceType: "multimeter",
    visibility: "private",
    transport: "ethernet",
    ip: "192.168.0.50",
    port: "1234",
    gpibAddr: "",
    comName: "",
    ipRequest: "",
    pollPeriodMs: "200",
    discreteInputsBytes: "0",
    coilsBytes: "0",
    holdingRegisters: "0",
    inputRegisters: "0",
    params: {},
    variables: [
      { name: "voltage", ctype: "f32", graph: true, category: "" },
    ],
    ...over,
  };
}

describe("validateConfigForm", () => {
  it("принимает корректный черновик", () => {
    expect(validateConfigForm(validDraft())).toEqual({});
  });

  it("требует название", () => {
    expect(validateConfigForm(validDraft({ name: "   " })).name).toBeTruthy();
  });

  it("ограничивает длину названия", () => {
    expect(
      validateConfigForm(validDraft({ name: "x".repeat(129) })).name,
    ).toBeTruthy();
  });

  it("требует тип прибора", () => {
    expect(
      validateConfigForm(validDraft({ deviceType: "" })).deviceType,
    ).toBeTruthy();
  });

  it("требует IP и порт для ethernet", () => {
    const errors = validateConfigForm(validDraft({ ip: "", port: "" }));
    expect(errors.ip).toBeTruthy();
    expect(errors.port).toBeTruthy();
  });

  it("требует IP для modbus", () => {
    const errors = validateConfigForm(
      validDraft({ transport: "modbus_udp", ip: "", port: "502" }),
    );
    expect(errors.ip).toBeTruthy();
    expect(errors.port).toBeUndefined();
  });

  it("отбраковывает порт вне диапазона", () => {
    expect(validateConfigForm(validDraft({ port: "70000" })).port).toBeTruthy();
    expect(validateConfigForm(validDraft({ port: "0" })).port).toBeTruthy();
    expect(validateConfigForm(validDraft({ port: "12.5" })).port).toBeTruthy();
  });

  it("проверяет счётчики Modbus", () => {
    const bad = validateConfigForm(
      validDraft({ transport: "modbus_tcp", holdingRegisters: "-1" }),
    );
    expect(bad.modbus?.holdingRegisters).toBeTruthy();

    const ok = validateConfigForm(
      validDraft({ transport: "modbus_tcp", holdingRegisters: "76" }),
    );
    expect(ok).toEqual({});
  });

  it("для gpib требует адрес в диапазоне и не требует IP", () => {
    const bad = validateConfigForm(
      validDraft({ transport: "gpib", ip: "", port: "", gpibAddr: "40" }),
    );
    expect(bad.gpibAddr).toBeTruthy();
    expect(bad.ip).toBeUndefined();
    expect(bad.port).toBeUndefined();

    const ok = validateConfigForm(
      validDraft({ transport: "gpib", ip: "", port: "", gpibAddr: "22" }),
    );
    expect(ok).toEqual({});
  });

  it("для com требует имя порта", () => {
    expect(
      validateConfigForm(
        validDraft({ transport: "com", ip: "", port: "", comName: "" }),
      ).comName,
    ).toBeTruthy();
  });

  it("требует положительный целый период опроса", () => {
    expect(
      validateConfigForm(validDraft({ pollPeriodMs: "0" })).pollPeriodMs,
    ).toBeTruthy();
    expect(
      validateConfigForm(validDraft({ pollPeriodMs: "-5" })).pollPeriodMs,
    ).toBeTruthy();
    expect(
      validateConfigForm(validDraft({ pollPeriodMs: "1.5" })).pollPeriodMs,
    ).toBeTruthy();
    expect(
      validateConfigForm(validDraft({ pollPeriodMs: "" })).pollPeriodMs,
    ).toBeTruthy();
  });

  it("ловит пустые и повторяющиеся имена переменных", () => {
    const errors = validateConfigForm(
      validDraft({
        variables: [
          { name: "voltage", ctype: "f32", graph: false, category: "" },
          { name: "", ctype: "u8", graph: false, category: "" },
          { name: "voltage", ctype: "u8", graph: false, category: "" },
        ],
      }),
    );
    expect(errors.variables?.[1]).toBeTruthy();
    expect(errors.variables?.[2]).toBeTruthy();
    expect(errors.variables?.[0]).toBeUndefined();
  });
});

describe("hasErrors", () => {
  it("различает пустые и заполненные ошибки", () => {
    expect(hasErrors({})).toBe(false);
    expect(hasErrors({ name: "укажите название" })).toBe(true);
  });
});

describe("variableOffsets", () => {
  it("пакует биты по 8 в байт и сдвигает по размеру типа", () => {
    expect(variableOffsets([])).toEqual([]);
    expect(
      variableOffsets([
        { name: "b0", ctype: "bit", graph: false, category: "" },
        { name: "b1", ctype: "bit", graph: false, category: "" },
        { name: "r", ctype: "u32", graph: false, category: "" },
        { name: "f", ctype: "f32", graph: false, category: "" },
      ]),
    ).toEqual([
      { byte: 0, bit: 0 },
      { byte: 0, bit: 1 },
      { byte: 1, bit: null },
      { byte: 5, bit: null },
    ]);
  });
});

describe("formatOffset", () => {
  it("показывает байт, а для bit - байт-бит", () => {
    expect(formatOffset({ byte: 5, bit: null })).toBe("5");
    expect(formatOffset({ byte: 1, bit: 3 })).toBe("1-3");
  });
});

describe("draftToPayload", () => {
  it("обнуляет нерелевантные поля подключения и тримит строки", () => {
    const payload = draftToPayload(
      validDraft({
        ip: " 10.0.0.1 ",
        port: "1234",
        variables: [
          { name: " temp ", ctype: "f32", graph: true, category: " A " },
        ],
      }),
    );
    expect(payload.connection).toEqual({
      transport: "ethernet",
      ip: "10.0.0.1",
      port: 1234,
      gpib_addr: null,
      com_name: null,
      ip_request: null,
      poll_period_ms: 200,
      modbus: null,
      params: {},
    });
    expect(payload.variables[0]).toEqual({
      name: "temp",
      ctype: "f32",
      graph: true,
      category: "A",
    });
  });

  it("для gpib пишет адрес и обнуляет сеть", () => {
    const payload = draftToPayload(
      validDraft({ transport: "gpib", ip: "x", port: "9", gpibAddr: "22" }),
    );
    expect(payload.connection.gpib_addr).toBe(22);
    expect(payload.connection.ip).toBeNull();
    expect(payload.connection.port).toBeNull();
  });

  it("для modbus пишет карту регистров и переменные списком", () => {
    const payload = draftToPayload(
      validDraft({
        transport: "modbus_udp",
        ip: "192.168.55.55",
        port: "35123",
        ipRequest: "device_get_ip",
        holdingRegisters: "76",
        variables: [
          { name: "reg", ctype: "bit", graph: false, category: "" },
        ],
      }),
    );
    expect(payload.connection.transport).toBe("modbus_udp");
    expect(payload.connection.ip_request).toBe("device_get_ip");
    expect(payload.connection.modbus).toEqual({
      discrete_inputs_bytes: 0,
      coils_bytes: 0,
      holding_registers: 76,
      input_registers: 0,
    });
    expect(payload.variables[0]).toEqual({
      name: "reg",
      ctype: "bit",
      graph: false,
      category: "",
    });
  });
});

describe("configToDraft", () => {
  function detail(over: Partial<ConfigDetail> = {}): ConfigDetail {
    return {
      id: 1,
      name: "Имя",
      device_type: "multimeter",
      visibility: "shared",
      owner_login: "dev",
      access: "owner",
      created_at: "2026-06-04T00:00:00",
      updated_at: "2026-06-04T00:00:00",
      shares: [],
      payload: {
        connection: {
          transport: "modbus_udp",
          ip: "192.168.55.55",
          port: 35123,
          gpib_addr: null,
          com_name: null,
          ip_request: "device_get_ip",
          poll_period_ms: 200,
          modbus: {
            discrete_inputs_bytes: 0,
            coils_bytes: 0,
            holding_registers: 76,
            input_registers: 0,
          },
          params: {},
        },
        variables: [
          { name: "v", ctype: "u32", graph: false, category: "" },
        ],
      },
      ...over,
    };
  }

  it("разворачивает конфиг в строки формы", () => {
    const draft = configToDraft(detail());
    expect(draft.transport).toBe("modbus_udp");
    expect(draft.ipRequest).toBe("device_get_ip");
    expect(draft.holdingRegisters).toBe("76");
    expect(draft.variables[0].name).toBe("v");
  });

  it("даёт валидный round-trip с draftToPayload и сохраняет порядок", () => {
    const source = validDraft({
      transport: "modbus_udp",
      ip: "10.0.0.5",
      port: "502",
      holdingRegisters: "12",
      variables: [
        { name: "reg", ctype: "bit", graph: false, category: "" },
        { name: "temp", ctype: "f32", graph: true, category: "A" },
      ],
    });
    const restored = configToDraft(
      detail({
        name: source.name,
        device_type: source.deviceType,
        visibility: source.visibility,
        payload: draftToPayload(source),
      }),
    );
    expect(validateConfigForm(restored)).toEqual({});
    expect(restored.variables.map((variable) => variable.name)).toEqual([
      "reg",
      "temp",
    ]);
  });
});

describe("canPublish", () => {
  it("публиковать может только dev и admin", () => {
    expect(canPublish("admin")).toBe(true);
    expect(canPublish("dev")).toBe(true);
    expect(canPublish("user")).toBe(false);
  });
});

describe("availableGrantees", () => {
  const users: UserSummary[] = [
    { login: "dev", role: "dev" },
    { login: "bob", role: "user" },
    { login: "eve", role: "dev" },
  ];

  it("исключает владельца и уже добавленных", () => {
    const rest = availableGrantees(users, "dev", [
      { login: "bob", permission: "read" },
    ]);
    expect(rest.map((user) => user.login)).toEqual(["eve"]);
  });

  it("возвращает всех остальных, когда грантов нет", () => {
    const rest = availableGrantees(users, "dev", []);
    expect(rest.map((user) => user.login)).toEqual(["bob", "eve"]);
  });
});

describe("emptyDraft", () => {
  it("даёт ethernet и период 200 по умолчанию", () => {
    const draft = emptyDraft();
    expect(draft.transport).toBe("ethernet");
    expect(draft.pollPeriodMs).toBe("200");
    expect(draft.variables).toEqual([]);
    expect(draft.params).toEqual({});
  });
});

describe("describeConfigAccess", () => {
  it("у не-владельца показывает только его право", () => {
    expect(describeConfigAccess("write", "shared", 3)).toBe("Запись");
    expect(describeConfigAccess("read", "public", 0)).toBe("Чтение");
  });

  it("личный конфиг без грантов - просто владелец", () => {
    expect(describeConfigAccess("owner", "private", 0)).toBe("Владелец");
  });

  it("после выдачи доступа отражает число получателей", () => {
    expect(describeConfigAccess("owner", "shared", 1)).toBe(
      "Владелец · ещё 1 с доступом",
    );
    expect(describeConfigAccess("owner", "shared", 2)).toBe(
      "Владелец · ещё 2 с доступом",
    );
  });

  it("публичный конфиг помечается явно", () => {
    expect(describeConfigAccess("owner", "public", 0)).toBe(
      "Владелец · публичный",
    );
  });
});
