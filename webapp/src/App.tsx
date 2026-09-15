import { Navigate, Route, BrowserRouter, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import AppNav from "./components/AppNav";
import Landing from "./pages/Landing";
import Login from "./pages/Login";
import Register from "./pages/Register";
import FamilyHome from "./pages/FamilyHome";
import Marketplace from "./pages/Marketplace";
import CaregiverDetail from "./pages/CaregiverDetail";
import CaregiverDashboard from "./pages/CaregiverDashboard";
import Products from "./pages/Products";
import { Spinner } from "./components/ui";

function AppHome() {
  const { user, loading } = useAuth();
  if (loading) return <div style={{ padding: 60 }}><Spinner label="Cargando…" /></div>;
  if (!user) return <Landing />;
  return <Navigate to={user.account_type === "family" ? "/familia" : "/cuidadora"} replace />;
}

function Protected({ children, forAccountType }: { children: React.ReactNode; forAccountType?: "family" | "caregiver" }) {
  const { user, loading } = useAuth();
  if (loading) return <div style={{ padding: 60 }}><Spinner label="Verificando sesión…" /></div>;
  if (!user) return <Navigate to="/login" replace />;
  if (forAccountType && user.account_type !== forAccountType) {
    return <Navigate to={user.account_type === "family" ? "/familia" : "/cuidadora"} replace />;
  }
  return <>{children}</>;
}

function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div>
      <AppNav />
      {children}
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/" element={<AppHome />} />
          <Route path="/login" element={<Login />} />
          <Route path="/registro" element={<Register />} />
          <Route path="/familia" element={<Protected forAccountType="family"><AppLayout><FamilyHome /></AppLayout></Protected>} />
          <Route path="/marketplace" element={<Protected forAccountType="family"><AppLayout><Marketplace /></AppLayout></Protected>} />
          <Route path="/marketplace/productos" element={<Protected forAccountType="family"><AppLayout><Products /></AppLayout></Protected>} />
          <Route path="/marketplace/cuidadoras/:id" element={<Protected forAccountType="family"><AppLayout><CaregiverDetail /></AppLayout></Protected>} />
          <Route path="/cuidadora" element={<Protected forAccountType="caregiver"><AppLayout><CaregiverDashboard /></AppLayout></Protected>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
