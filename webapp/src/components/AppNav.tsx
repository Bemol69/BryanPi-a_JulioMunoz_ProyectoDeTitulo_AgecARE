import { NavLink } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { Initials } from "./ui";

export default function AppNav() {
  const { user, logout } = useAuth();
  if (!user) return null;
  const isFamily = user.account_type === "family";

  return (
    <header className="app-nav">
      <div className="app-nav-inner">
        <NavLink to="/" className="pub-logo" style={{ marginRight: 8 }}>
          <img src="/agecare-logo.jpg" alt="AgeCare" />
        </NavLink>
        <div className="app-tabs">
          {isFamily ? (
            <>
              <NavLink to="/familia" className={({ isActive }) => (isActive ? "active" : "")}>Mis pacientes</NavLink>
              <NavLink to="/marketplace" className={({ isActive }) => (isActive ? "active" : "")}>Buscar cuidadoras</NavLink>
              <NavLink to="/marketplace/productos" className={({ isActive }) => (isActive ? "active" : "")}>Artículos de apoyo</NavLink>
            </>
          ) : (
            <NavLink to="/cuidadora" className={({ isActive }) => (isActive ? "active" : "")}>Mi perfil profesional</NavLink>
          )}
        </div>
        <div className="app-user">
          <div className="app-avatar"><Initials name={user.full_name} /></div>
          <span>{user.full_name}</span>
          <button className="btn ghost small" onClick={logout}>Salir</button>
        </div>
      </div>
    </header>
  );
}
