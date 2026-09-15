import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { AuthApi } from "../api/endpoints";
import { getAccessToken, setTokens } from "../api/client";
import type { UserOut } from "../api/types";

interface AuthState {
  user: UserOut | null;
  loading: boolean;
  error: string | null;
  register: (body: { full_name: string; email: string; password: string; phone?: string; account_type: "family" | "caregiver" }) => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!getAccessToken()) {
      setLoading(false);
      return;
    }
    AuthApi.me().then(setUser).catch(() => setTokens(null, null)).finally(() => setLoading(false));
  }, []);

  const register = useCallback(async (body: { full_name: string; email: string; password: string; phone?: string; account_type: "family" | "caregiver" }) => {
    setError(null);
    try {
      const res = await AuthApi.register(body);
      setTokens(res.access_token, res.refresh_token);
      setUser(res.user);
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo crear la cuenta.");
      throw e;
    }
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    setError(null);
    try {
      const res = await AuthApi.login(email, password);
      setTokens(res.access_token, res.refresh_token);
      setUser(res.user);
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo iniciar sesión.");
      throw e;
    }
  }, []);

  const logout = useCallback(() => {
    const refresh = localStorage.getItem("agecare_refresh_token");
    setTokens(null, null);
    setUser(null);
    if (refresh) AuthApi.logout(refresh).catch(() => {});
  }, []);

  const refreshUser = useCallback(async () => {
    const me = await AuthApi.me();
    setUser(me);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, error, register, login, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth debe usarse dentro de AuthProvider");
  return ctx;
}
