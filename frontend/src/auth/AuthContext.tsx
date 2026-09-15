import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { AuthApi } from "../api/endpoints";
import { getAccessToken, setTokens } from "../api/client";
import type { MeOut } from "../api/types";

interface AuthState {
  me: MeOut | null;
  loading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  can: (module: string) => boolean;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [me, setMe] = useState<MeOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!getAccessToken()) {
      setLoading(false);
      return;
    }
    AuthApi.me()
      .then(setMe)
      .catch(() => setTokens(null, null))
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    setError(null);
    try {
      const res = await AuthApi.login(email, password);
      setTokens(res.access_token, res.refresh_token);
      const meRes = await AuthApi.me();
      setMe(meRes);
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo iniciar sesión.");
      throw e;
    }
  }, []);

  const logout = useCallback(() => {
    const refresh = localStorage.getItem("agecare_refresh_token");
    setTokens(null, null);
    setMe(null);
    if (refresh) AuthApi.logout(refresh).catch(() => {});
  }, []);

  const can = useCallback((module: string) => !!me?.permissions.includes(module), [me]);

  return (
    <AuthContext.Provider value={{ me, loading, error, login, logout, can }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth debe usarse dentro de AuthProvider");
  return ctx;
}
