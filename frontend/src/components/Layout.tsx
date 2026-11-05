import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

const ROLE_LABEL: Record<string, string> = {
  admin: "Administrador", analyst: "Analista", support: "Soporte",
  editor: "Editor de contenido", moderator: "Moderador",
};

const NAV: { group: string; hidden?: boolean; items: { to: string; icon: string; label: string; short: string; module: string; badge?: string }[] }[] = [
  {
    group: "Marketing y fidelización",
    items: [
      { to: "/marketplace", icon: "🧑‍⚕️", label: "Marketplace de cuidadoras", short: "Marketplace", module: "marketplace" },
      { to: "/fidelizacion", icon: "🏆", label: "Fidelización y ranking", short: "Fidelización", module: "marketing" },
    ],
  },
  {
    group: "Analítica",
    hidden: true, // módulos no visibles por ahora (se conservan las rutas y el código)
    items: [
      { to: "/comercial", icon: "📈", label: "Uso comercial", short: "Uso comercial", module: "metrics" },
      { to: "/operativo", icon: "🖥️", label: "Estado operativo", short: "Operativo", module: "ops" },
      { to: "/usuarios", icon: "👥", label: "Usuarios y soporte", short: "Soporte", module: "support" },
      { to: "/funcional", icon: "🧩", label: "Uso por funcionalidad", short: "Funcionalidades", module: "metrics" },
    ],
  },
];

const TITLES: Record<string, { title: string; crumb: string }> = {
  "/marketplace": { title: "Marketplace de cuidadoras", crumb: "Marketing y fidelización · Catálogo" },
  "/fidelizacion": { title: "Fidelización y ranking", crumb: "Marketing y fidelización · Puntos y ranking" },
  "/comercial": { title: "Uso comercial", crumb: "Analítica · Uso comercial de la plataforma" },
  "/operativo": { title: "Estado operativo", crumb: "Analítica · Salud de la plataforma" },
  "/usuarios": { title: "Usuarios y soporte", crumb: "Analítica · Perfiles y soporte" },
  "/funcional": { title: "Uso por funcionalidad", crumb: "Analítica · Adopción de funciones" },
};

export default function Layout() {
  const { me, logout, can } = useAuth();
  const location = useLocation();
  const meta = TITLES[location.pathname] ?? { title: "AgeCare", crumb: "" };

  const items = NAV.filter((group) => !group.hidden).flatMap((group) => group.items.filter((i) => can(i.module)));

  return (
    <div className="c-shell">
      <header className="c-nav">
        <div className="c-nav-inner">
          <NavLink to="/marketplace" className="c-brand">
            <span className="c-brand-mark"><img src="/logo-mark.png" alt="AgeCare" /></span>
            <span className="c-brand-text"><b>AgeCare</b><i>Consola</i></span>
          </NavLink>
          <nav className="c-tabs">
            {items.map((item) => (
              <NavLink key={item.to} to={item.to} className={({ isActive }) => `c-tab${isActive ? " active" : ""}`}>
                {item.short}
                {item.badge && <span className="c-tab-new">{item.badge}</span>}
              </NavLink>
            ))}
          </nav>
          <div className="c-user">
            <span className="c-env">{import.meta.env.PROD ? "Producción" : "Local"} · datos de prueba</span>
            <div className="c-avatar">{me ? initials(me.full_name) : "?"}</div>
            <div className="c-user-text">
              <b>{me?.full_name}</b>
              <i>{me ? ROLE_LABEL[me.role] ?? me.role : ""}</i>
            </div>
            <button className="c-logout" title="Cerrar sesión" onClick={logout}>⏻</button>
          </div>
        </div>
      </header>
      <main className="c-main">
        <div className="c-head">
          <div>
            <div className="c-crumb">{meta.crumb}</div>
            <h1>{meta.title}</h1>
          </div>
        </div>
        {items.length === 0 ? (
          <div className="card">
            <div className="card-title">Tu rol todavía no tiene secciones habilitadas</div>
            <div className="card-sub" style={{ marginTop: 6 }}>
              Pide al administrador que revise los permisos de tu cuenta.
            </div>
          </div>
        ) : <Outlet />}
      </main>
    </div>
  );
}

function initials(name: string): string {
  return name.split(" ").filter(Boolean).slice(0, 2).map((p) => p[0]?.toUpperCase()).join("");
}
