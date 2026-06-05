"use client";

import { usePathname, useRouter } from "next/navigation";
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

const LOGIN_PATH = "/login";
const HOME_PATH = "/dashboard";

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
  const router = useRouter();
  const pathname = usePathname();
  const [state, setState] = useState<AuthState>({ status: "loading" });

  useEffect(() => {
    fetchMe()
      .then((user) => setState({ status: "authenticated", user }))
      .catch(() => setState({ status: "anonymous" }));
  }, []);

  useEffect(() => {
    if (state.status === "anonymous" && pathname !== LOGIN_PATH) {
      router.replace(LOGIN_PATH);
    }
    if (state.status === "authenticated" && pathname === LOGIN_PATH) {
      router.replace(HOME_PATH);
    }
  }, [state.status, pathname, router]);

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
    <AuthContext value={{ state, signIn, signOut }}>
      {state.status === "loading" ? <AuthLoading /> : children}
    </AuthContext>
  );
}

function AuthLoading() {
  return (
    <div className="flex flex-1 items-center justify-center">
      <span className="font-mono text-xs tracking-wider text-muted-foreground uppercase">
        загрузка...
      </span>
    </div>
  );
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (context === null) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
