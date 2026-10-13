import { useEffect, useState } from "react";
import { NavLink } from "react-router-dom";
import { CaregiverApi } from "../api/endpoints";
import { useAuth } from "../auth/AuthContext";
import { Avatar } from "./ui";

/** Cantidad de solicitudes de contratación pendientes (solo cuidadoras); se actualiza cada 30 s. */
function usePendingRequests(enabled: boolean): number {
  const [count, setCount] = useState(0);
  useEffect(() => {
    if (!enabled) return;
    let alive = true;
    const load = () => CaregiverApi.hireRequests()
      .then((r) => { if (alive) setCount(r.items.filter((x) => x.status === "pending").length); })
      .catch(() => {});
    load();
    const t = setInterval(load, 30000);
    return () => { alive = false; clearInterval(t); };
  }, [enabled]);
  return count;
}

export default function AppNav() {
  const { user, logout } = useAuth();
  const pending = usePendingRequests(user?.account_type === "caregiver");
  if (!user) return null;
  const isFamily = user.account_type === "family";

  return (
    <header className="app-nav">
      <div className="app-nav-inner">
        <NavLink to="/" className="pub-logo" style={{ marginRight: 8 }}>
          <img src="/logo-mark.png" alt="AgeCare" />
        </NavLink>
        <div className="app-tabs">
          {isFamily ? (
            <>
              <NavLink to="/familia" className={({ isActive }) => (isActive ? "active" : "")}>Mis familiares</NavLink>
              <NavLink to="/marketplace" className={({ isActive }) => (isActive ? "active" : "")}>Buscar cuidadoras</NavLink>
              <NavLink to="/marketplace/productos" className={({ isActive }) => (isActive ? "active" : "")}>Artículos de apoyo</NavLink>
              <NavLink to="/mensajes" className={({ isActive }) => (isActive ? "active" : "")}>Mensajes</NavLink>
            </>
          ) : (
            <>
              <NavLink to="/cuidadora" className={({ isActive }) => (isActive ? "active" : "")}>Mi perfil profesional</NavLink>
              <NavLink to="/solicitudes" className={({ isActive }) => (isActive ? "active" : "")}>
                Solicitudes{pending > 0 && <span className="nav-badge">{pending}</span>}
              </NavLink>
              <NavLink to="/mensajes" className={({ isActive }) => (isActive ? "active" : "")}>Mensajes</NavLink>
            </>
          )}
        </div>
        <div className="app-user">
          <div className="app-avatar"><Avatar name={user.full_name} photoUrl={user.avatar_url} /></div>
          <span>{user.full_name}</span>
          <button className="btn ghost small" onClick={logout}>Salir</button>
        </div>
      </div>
    </header>
  );
}
