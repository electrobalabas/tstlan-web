import type {
  ConfigAccess,
  ConfigDetail,
  ConfigPayload,
  ConfigVisibility,
  NetVarCType,
  Role,
  ShareInfo,
  SharePermission,
  Transport,
  UserSummary,
} from "@/lib/api";

export const VISIBILITY_META: Record<
  ConfigVisibility,
  { label: string; hint: string }
> = {
  private: { label: "Личный", hint: "виден только владельцу" },
  shared: { label: "Общий", hint: "доступен по выданным правам" },
  public: { label: "Публичный", hint: "доступен на чтение всем" },
};

export const ACCESS_META: Record<ConfigAccess, { label: string }> = {
  owner: { label: "Владелец" },
  write: { label: "Запись" },
  read: { label: "Чтение" },
};

export const PERMISSION_META: Record<SharePermission, { label: string }> = {
  read: { label: "Чтение" },
  write: { label: "Запись" },
};

export const ROLE_META: Record<Role, { label: string }> = {
  admin: { label: "Админ" },
  dev: { label: "Инженер" },
  user: { label: "Пользователь" },
};

export const TRANSPORT_META: Record<Transport, { label: string }> = {
  ethernet: { label: "Ethernet" },
  gpib: { label: "GPIB" },
  com: { label: "COM" },
  modbus_tcp: { label: "Modbus TCP" },
  modbus_udp: { label: "Modbus UDP" },
};

export const CTYPES: NetVarCType[] = [
  "bit",
  "u8",
  "i8",
  "u16",
  "i16",
  "u32",
  "i32",
  "f32",
  "f64",
];

export const MODBUS_FIELDS = [
  { key: "discreteInputsBytes", label: "Discrete inputs, байт" },
  { key: "coilsBytes", label: "Coils, байт" },
  { key: "holdingRegisters", label: "Holding registers" },
  { key: "inputRegisters", label: "Input registers" },
] as const;

export type ModbusField = (typeof MODBUS_FIELDS)[number]["key"];

const PORT_MIN = 1;
const PORT_MAX = 65535;
const GPIB_MIN = 0;
const GPIB_MAX = 30;
const NAME_MAX = 128;
const DEVICE_TYPE_MAX = 64;

// private/shared - производное состояние от наличия грантов, не выбор
// пользователя. Реально выбирается лишь публикация (public), доступная dev/admin.
export function canPublish(role: Role): boolean {
  return role === "dev" || role === "admin";
}

export function isModbus(transport: Transport): boolean {
  return transport === "modbus_tcp" || transport === "modbus_udp";
}

// IP/порт обязательны для сетевых транспортов (Ethernet и Modbus),
// GPIB-адрес для GPIB, имя COM-порта для COM.
export function needsNetwork(transport: Transport): boolean {
  return transport === "ethernet" || isModbus(transport);
}

export type VariableDraft = {
  name: string;
  ctype: NetVarCType;
  graph: boolean;
  category: string;
};

// Размер значения в байтах. Зеркалит NetVarCType.byte_size на бэке.
export const CTYPE_BYTE_SIZE: Record<NetVarCType, number> = {
  bit: 1,
  u8: 1,
  i8: 1,
  u16: 2,
  i16: 2,
  u32: 4,
  i32: 4,
  f32: 4,
  f64: 8,
};

// Адрес переменной: байтовое смещение и, для bit, номер бита в байте.
// Зеркалит NetVarIndex из irsural/unidriver_py.
export type VarOffset = { byte: number; bit: number | null };

// Переменные читаются последовательно: смещение выводится из порядка и типа
// (как calc_next_netvar_index в unidriver_py). Не-bit занимает byte_size байт,
// bit пакуется по 8 в байт. Отдельный адрес не храним.
export function variableOffsets(variables: VariableDraft[]): VarOffset[] {
  const offsets: VarOffset[] = [];
  let prev: VarOffset | null = null;
  let prevCtype: NetVarCType | null = null;
  for (const variable of variables) {
    const isBit = variable.ctype === "bit";
    let cur: VarOffset;
    if (prev === null || prevCtype === null) {
      cur = { byte: 0, bit: isBit ? 0 : null };
    } else if (prevCtype === "bit" && isBit) {
      cur =
        (prev.bit ?? 0) >= 7
          ? { byte: prev.byte + 1, bit: 0 }
          : { byte: prev.byte, bit: (prev.bit ?? 0) + 1 };
    } else {
      cur = {
        byte: prev.byte + CTYPE_BYTE_SIZE[prevCtype],
        bit: isBit ? 0 : null,
      };
    }
    offsets.push(cur);
    prev = cur;
    prevCtype = variable.ctype;
  }
  return offsets;
}

// "5" для байтовой переменной, "1-3" (байт-бит) для bit.
export function formatOffset(offset: VarOffset): string {
  return offset.bit === null ? String(offset.byte) : `${offset.byte}-${offset.bit}`;
}

export type ConfigFormDraft = {
  name: string;
  deviceType: string;
  visibility: ConfigVisibility;
  transport: Transport;
  ip: string;
  port: string;
  gpibAddr: string;
  comName: string;
  ipRequest: string;
  pollPeriodMs: string;
  discreteInputsBytes: string;
  coilsBytes: string;
  holdingRegisters: string;
  inputRegisters: string;
  params: Record<string, string>;
  variables: VariableDraft[];
};

export type ConfigFieldErrors = {
  name?: string;
  deviceType?: string;
  ip?: string;
  port?: string;
  gpibAddr?: string;
  comName?: string;
  pollPeriodMs?: string;
  modbus?: Partial<Record<ModbusField, string>>;
  variables?: Record<number, string>;
};

export function emptyDraft(): ConfigFormDraft {
  return {
    name: "",
    deviceType: "",
    visibility: "private",
    transport: "ethernet",
    ip: "",
    port: "",
    gpibAddr: "",
    comName: "",
    ipRequest: "",
    pollPeriodMs: "200",
    discreteInputsBytes: "0",
    coilsBytes: "0",
    holdingRegisters: "0",
    inputRegisters: "0",
    params: {},
    variables: [],
  };
}

function parseIntStrict(raw: string): number | null {
  const trimmed = raw.trim();
  if (!/^-?\d+$/.test(trimmed)) return null;
  return Number(trimmed);
}

// Счётчики Modbus: пустое поле трактуем как 0, иначе целое >= 0.
function parseCount(raw: string): number | null {
  if (raw.trim() === "") return 0;
  const value = parseIntStrict(raw);
  return value === null || value < 0 ? null : value;
}

export function validateConfigForm(draft: ConfigFormDraft): ConfigFieldErrors {
  const errors: ConfigFieldErrors = {};

  if (draft.name.trim() === "") {
    errors.name = "укажите название";
  } else if (draft.name.trim().length > NAME_MAX) {
    errors.name = `не длиннее ${NAME_MAX} символов`;
  }

  if (draft.deviceType.trim() === "") {
    errors.deviceType = "укажите тип прибора";
  } else if (draft.deviceType.trim().length > DEVICE_TYPE_MAX) {
    errors.deviceType = `не длиннее ${DEVICE_TYPE_MAX} символов`;
  }

  if (needsNetwork(draft.transport)) {
    if (draft.ip.trim() === "") {
      errors.ip = "укажите IP-адрес";
    }
    const port = parseIntStrict(draft.port);
    if (port === null || port < PORT_MIN || port > PORT_MAX) {
      errors.port = `порт ${PORT_MIN}-${PORT_MAX}`;
    }
  }

  if (draft.transport === "gpib") {
    const addr = parseIntStrict(draft.gpibAddr);
    if (addr === null || addr < GPIB_MIN || addr > GPIB_MAX) {
      errors.gpibAddr = `адрес GPIB ${GPIB_MIN}-${GPIB_MAX}`;
    }
  }

  if (draft.transport === "com" && draft.comName.trim() === "") {
    errors.comName = "укажите имя COM-порта";
  }

  const period = parseIntStrict(draft.pollPeriodMs);
  if (period === null || period <= 0) {
    errors.pollPeriodMs = "период опроса: целое > 0";
  }

  if (isModbus(draft.transport)) {
    const modbus: Partial<Record<ModbusField, string>> = {};
    for (const field of MODBUS_FIELDS) {
      if (parseCount(draft[field.key]) === null) {
        modbus[field.key] = "целое >= 0";
      }
    }
    if (Object.keys(modbus).length > 0) {
      errors.modbus = modbus;
    }
  }

  const variableErrors = validateVariables(draft.variables);
  if (Object.keys(variableErrors).length > 0) {
    errors.variables = variableErrors;
  }

  return errors;
}

function validateVariables(variables: VariableDraft[]): Record<number, string> {
  const errors: Record<number, string> = {};
  const seen = new Set<string>();
  variables.forEach((variable, position) => {
    const name = variable.name.trim();
    if (name === "") {
      errors[position] = "укажите имя";
    } else if (seen.has(name)) {
      errors[position] = "имя повторяется";
    }
    seen.add(name);
  });
  return errors;
}

export function hasErrors(errors: ConfigFieldErrors): boolean {
  return Object.keys(errors).length > 0;
}

export function draftToPayload(draft: ConfigFormDraft): ConfigPayload {
  const network = needsNetwork(draft.transport);
  return {
    connection: {
      transport: draft.transport,
      ip: network && draft.ip.trim() !== "" ? draft.ip.trim() : null,
      port: network ? parseIntStrict(draft.port) : null,
      gpib_addr:
        draft.transport === "gpib" ? parseIntStrict(draft.gpibAddr) : null,
      com_name:
        draft.transport === "com" && draft.comName.trim() !== ""
          ? draft.comName.trim()
          : null,
      ip_request: draft.ipRequest.trim() !== "" ? draft.ipRequest.trim() : null,
      poll_period_ms: parseIntStrict(draft.pollPeriodMs) ?? 0,
      modbus: isModbus(draft.transport)
        ? {
            discrete_inputs_bytes: parseCount(draft.discreteInputsBytes) ?? 0,
            coils_bytes: parseCount(draft.coilsBytes) ?? 0,
            holding_registers: parseCount(draft.holdingRegisters) ?? 0,
            input_registers: parseCount(draft.inputRegisters) ?? 0,
          }
        : null,
      params: draft.params,
    },
    variables: draft.variables.map((variable) => ({
      name: variable.name.trim(),
      ctype: variable.ctype,
      graph: variable.graph,
      category: variable.category.trim(),
    })),
  };
}

export function configToDraft(config: ConfigDetail): ConfigFormDraft {
  const { connection } = config.payload;
  const modbus = connection.modbus;
  return {
    name: config.name,
    deviceType: config.device_type,
    visibility: config.visibility,
    transport: connection.transport,
    ip: connection.ip ?? "",
    port: connection.port === null ? "" : String(connection.port),
    gpibAddr: connection.gpib_addr === null ? "" : String(connection.gpib_addr),
    comName: connection.com_name ?? "",
    ipRequest: connection.ip_request ?? "",
    pollPeriodMs: String(connection.poll_period_ms),
    discreteInputsBytes: String(modbus?.discrete_inputs_bytes ?? 0),
    coilsBytes: String(modbus?.coils_bytes ?? 0),
    holdingRegisters: String(modbus?.holding_registers ?? 0),
    inputRegisters: String(modbus?.input_registers ?? 0),
    params: connection.params,
    variables: config.payload.variables.map((variable) => ({
      name: variable.name,
      ctype: variable.ctype,
      graph: variable.graph,
      category: variable.category,
    })),
  };
}

// Кого ещё можно добавить: все пользователи, кроме владельца и тех, кому
// доступ уже выдан.
export function availableGrantees(
  users: UserSummary[],
  ownerLogin: string,
  shares: ShareInfo[],
): UserSummary[] {
  const taken = new Set<string>([
    ownerLogin,
    ...shares.map((share) => share.login),
  ]);
  return users.filter((user) => !taken.has(user.login));
}
