export type Role = "admin" | "dev" | "user";

export type Identity = {
  login: string;
  role: Role;
  csrf_token: string;
};

export class ApiError extends Error {
  status: number;
  detail?: string;

  constructor(status: number, detail?: string) {
    super(detail ?? `api request failed with status ${status}`);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    throw new ApiError(response.status, await readDetail(response));
  }
  return (await response.json()) as T;
}

async function requestVoid(path: string, init?: RequestInit): Promise<void> {
  const response = await fetch(`/api${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    throw new ApiError(response.status, await readDetail(response));
  }
}

async function readDetail(response: Response): Promise<string | undefined> {
  try {
    const body = (await response.json()) as { detail?: unknown };
    return typeof body.detail === "string" ? body.detail : undefined;
  } catch {
    return undefined;
  }
}

export function fetchMe(): Promise<Identity> {
  return request<Identity>("/auth/me");
}

export function login(userLogin: string, password: string): Promise<Identity> {
  return request<Identity>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ login: userLogin, password }),
  });
}

export function logout(csrfToken: string): Promise<{ status: string }> {
  return request<{ status: string }>("/auth/logout", {
    method: "POST",
    headers: { "X-CSRF-Token": csrfToken },
  });
}

export type UserSummary = {
  login: string;
  role: Role;
};

export function listUsers(): Promise<UserSummary[]> {
  return request<UserSummary[]>("/users");
}

export type DeviceStatus = "ok" | "offline" | "error";

export type NetVarCType =
  | "bit"
  | "u8"
  | "i8"
  | "u16"
  | "i16"
  | "u32"
  | "i32"
  | "f32"
  | "f64";

export type NetVarMode = "r" | "w" | "rw";

export type DeviceSummary = {
  id: string;
  name: string;
  type: string;
  enabled: boolean;
  status: DeviceStatus;
  variable_count: number;
};

export type VariableInfo = {
  name: string;
  ctype: NetVarCType;
  mode: NetVarMode;
};

export type DeviceDetail = {
  id: string;
  name: string;
  type: string;
  enabled: boolean;
  status: DeviceStatus;
  variables: VariableInfo[];
};

export type VariableValue = {
  name: string;
  ctype: NetVarCType;
  value: number;
};

export function listDevices(): Promise<DeviceSummary[]> {
  return request<DeviceSummary[]>("/devices");
}

export function getDevice(deviceId: string): Promise<DeviceDetail> {
  return request<DeviceDetail>(`/devices/${encodeURIComponent(deviceId)}`);
}

export function listValues(deviceId: string): Promise<VariableValue[]> {
  return request<VariableValue[]>(
    `/devices/${encodeURIComponent(deviceId)}/values`,
  );
}

export function writeValue(
  deviceId: string,
  name: string,
  value: number,
  csrfToken: string,
): Promise<VariableValue> {
  return request<VariableValue>(
    `/devices/${encodeURIComponent(deviceId)}/values/${encodeURIComponent(name)}`,
    {
      method: "PUT",
      headers: { "X-CSRF-Token": csrfToken },
      body: JSON.stringify({ value }),
    },
  );
}

export function streamValues(
  deviceId: string,
  onSnapshot: (snapshot: VariableValue[]) => void,
  onError?: () => void,
): () => void {
  const source = new EventSource(
    `/api/devices/${encodeURIComponent(deviceId)}/stream`,
  );
  source.onmessage = (event) => {
    onSnapshot(JSON.parse(event.data) as VariableValue[]);
  };
  source.onerror = () => onError?.();
  return () => source.close();
}

export type ConfigVisibility = "private" | "shared" | "public";
export type SharePermission = "read" | "write";
export type ConfigAccess = "owner" | "write" | "read";
export type Transport =
  | "ethernet"
  | "gpib"
  | "com"
  | "modbus_tcp"
  | "modbus_udp";

export type ModbusMap = {
  discrete_inputs_bytes: number;
  coils_bytes: number;
  holding_registers: number;
  input_registers: number;
};

export type ConnectionSettings = {
  transport: Transport;
  ip: string | null;
  port: number | null;
  gpib_addr: number | null;
  com_name: string | null;
  ip_request: string | null;
  poll_period_ms: number;
  modbus: ModbusMap | null;
  params: Record<string, string>;
};

export type ConfigVar = {
  name: string;
  ctype: NetVarCType;
  graph: boolean;
  category: string;
};

export type ConfigPayload = {
  connection: ConnectionSettings;
  variables: ConfigVar[];
};

export type ShareInfo = {
  login: string;
  permission: SharePermission;
};

export type ConfigSummary = {
  id: number;
  name: string;
  device_type: string;
  visibility: ConfigVisibility;
  owner_login: string;
  access: ConfigAccess;
  created_at: string;
  updated_at: string;
};

export type ConfigDetail = ConfigSummary & {
  payload: ConfigPayload;
  shares: ShareInfo[];
};

export type ConfigCreate = {
  name: string;
  device_type: string;
  payload: ConfigPayload;
  visibility: ConfigVisibility;
};

export type ConfigUpdate = {
  name?: string;
  payload?: ConfigPayload;
  visibility?: ConfigVisibility;
};

export function listConfigs(): Promise<ConfigSummary[]> {
  return request<ConfigSummary[]>("/configs");
}

export function getConfig(id: number): Promise<ConfigDetail> {
  return request<ConfigDetail>(`/configs/${id}`);
}

export function createConfig(
  body: ConfigCreate,
  csrfToken: string,
): Promise<ConfigDetail> {
  return request<ConfigDetail>("/configs", {
    method: "POST",
    headers: { "X-CSRF-Token": csrfToken },
    body: JSON.stringify(body),
  });
}

export function updateConfig(
  id: number,
  body: ConfigUpdate,
  csrfToken: string,
): Promise<ConfigDetail> {
  return request<ConfigDetail>(`/configs/${id}`, {
    method: "PUT",
    headers: { "X-CSRF-Token": csrfToken },
    body: JSON.stringify(body),
  });
}

export function deleteConfig(id: number, csrfToken: string): Promise<void> {
  return requestVoid(`/configs/${id}`, {
    method: "DELETE",
    headers: { "X-CSRF-Token": csrfToken },
  });
}

export function shareConfig(
  id: number,
  share: ShareInfo,
  csrfToken: string,
): Promise<ConfigDetail> {
  return request<ConfigDetail>(`/configs/${id}/shares`, {
    method: "POST",
    headers: { "X-CSRF-Token": csrfToken },
    body: JSON.stringify(share),
  });
}

export function unshareConfig(
  id: number,
  login: string,
  csrfToken: string,
): Promise<ConfigDetail> {
  return request<ConfigDetail>(
    `/configs/${id}/shares/${encodeURIComponent(login)}`,
    {
      method: "DELETE",
      headers: { "X-CSRF-Token": csrfToken },
    },
  );
}
