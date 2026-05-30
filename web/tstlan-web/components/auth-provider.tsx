"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

import {
  fetchMe,
  login as apiLogin,
  logout as apiLogout,
  type Identity,
} from "@/lib/api";

type AuthState =
  | { status: "loading" }
  | { status: "anonymous" }
  | { status: "authenticated"; user: Identity };

type AuthContextValue = {
  state: AuthState;
  signIn: (login: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({ status: "loading" });

  useEffect(() => {
    fetchMe()
      .then((user) => setState({ status: "authenticated", user }))
      .catch(() => setState({ status: "anonymous" }));
  }, []);

  const signIn = useCallback(async (login: string, password: string) => {
    const user = await apiLogin(login, password);
    setState({ status: "authenticated", user });
  }, []);

  const signOut = useCallback(async () => {
    if (state.status === "authenticated") {
      await apiLogout(state.user.csrf_token);
    }
    setState({ status: "anonymous" });
  }, [state]);

  return (
    <AuthContext value={{ state, signIn, signOut }}>{children}</AuthContext>
  );
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (context === null) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
