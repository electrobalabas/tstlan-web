export type Role = "admin" | "user";

export type Identity = {
  login: string;
  role: Role;
  csrf_token: string;
};

export class ApiError extends Error {
  status: number;

  constructor(status: number) {
    super(`api request failed with status ${status}`);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    throw new ApiError(response.status);
  }
  return (await response.json()) as T;
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

export type DeviceStatus = "ok" | "offline" | "error";

export type NetVarCType =
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
