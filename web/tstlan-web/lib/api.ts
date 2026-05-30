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
