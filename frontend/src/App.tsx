import { Navigate, Route, BrowserRouter, Routes, useLocation } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import Layout from "./components/Layout";
import Login from "./pages/Login";
import Marketplace from "./pages/Marketplace";
import Fidelizacion from "./pages/Fidelizacion";
import Comercial from "./pages/Comercial";
import Operativo from "./pages/Operativo";
import Usuarios from "./pages/Usuarios";
import Funcional from "./pages/Funcional";
import Moderacion from "./pages/Moderacion";
import Contenido from "./pages/Contenido";
import { Card, Spinner } from "./components/ui";

const PATH_MODULE: Record<string, string> = {
  "/marketplace": "marketplace",
  "/fidelizacion": "marketing",
  "/comercial": "metrics",
  "/operativo": "ops",
  "/usuarios": "support",
  "/funcional": "metrics",
  "/moderacion": "moderation",
  "/contenido": "content",
};
const FALLBACK_ORDER = ["/fidelizacion", "/marketplace", "/comercial", "/operativo", "/usuarios", "/funcional", "/contenido", "/moderacion"];

function Protected({ children }: { children: React.ReactNode }) {
  const { me, loading } = useAuth();
  if (loading) return <div style={{ padding: 60 }}><Spinner label="Verificando sesión…" /></div>;
  if (!me) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function RequireModule({ children }: { children: React.ReactNode }) {
  const { can } = useAuth();
  const location = useLocation();
  const module = PATH_MODULE[location.pathname];
  if (module && !can(module)) {
    return (
      <Card>
        <div style={{ padding: 8 }}>
          <div className="card-title">Sin acceso a este módulo</div>
          <div className="card-sub" style={{ marginTop: 6 }}>
            Tu rol no tiene permisos para ver esta sección de la consola. Usa el menú para ir a una sección disponible.
          </div>
        </div>
      </Card>
    );
  }
  return <>{children}</>;
}

function HomeRedirect() {
  const { can } = useAuth();
  const target = FALLBACK_ORDER.find((p) => can(PATH_MODULE[p])) ?? "/comercial";
  return <Navigate to={target} replace />;
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route element={<Protected><Layout /></Protected>}>
            <Route index element={<HomeRedirect />} />
            <Route path="/marketplace" element={<RequireModule><Marketplace /></RequireModule>} />
            <Route path="/fidelizacion" element={<RequireModule><Fidelizacion /></RequireModule>} />
            <Route path="/comercial" element={<RequireModule><Comercial /></RequireModule>} />
            <Route path="/operativo" element={<RequireModule><Operativo /></RequireModule>} />
            <Route path="/usuarios" element={<RequireModule><Usuarios /></RequireModule>} />
            <Route path="/funcional" element={<RequireModule><Funcional /></RequireModule>} />
            <Route path="/moderacion" element={<RequireModule><Moderacion /></RequireModule>} />
            <Route path="/contenido" element={<RequireModule><Contenido /></RequireModule>} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
