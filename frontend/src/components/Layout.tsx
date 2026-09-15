import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

const ROLE_LABEL: Record<string, string> = {
  admin: "Administrador", analyst: "Analista", support: "Soporte",
  editor: "Editor de contenido", moderator: "Moderador",
};

const NAV: { group: string; items: { to: string; icon: string; label: string; module: string; badge?: string }[] }[] = [
  {
    group: "Marketing y fidelización",
    items: [
      { to: "/marketplace", icon: "🧑‍⚕️", label: "Marketplace de cuidadoras", module: "marketplace" },
      { to: "/fidelizacion", icon: "🏆", label: "Fidelización y ranking", module: "marketing", badge: "nuevo" },
    ],
  },
  {
    group: "Analítica",
    items: [
      { to: "/comercial", icon: "📈", label: "Uso comercial", module: "metrics" },
      { to: "/operativo", icon: "🖥️", label: "Estado operativo", module: "ops" },
      { to: "/usuarios", icon: "👥", label: "Usuarios y soporte", module: "support" },
      { to: "/funcional", icon: "🧩", label: "Uso por funcionalidad", module: "metrics" },
    ],
  },
  {
    group: "Operación",
    items: [
      { to: "/contenido", icon: "📰", label: "Curación de contenido", module: "content" },
      { to: "/moderacion", icon: "🛡️", label: "Moderación", module: "moderation" },
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
  "/contenido": { title: "Curación de contenido", crumb: "Operación · Chistes y noticias del adulto mayor" },
  "/moderacion": { title: "Moderación", crumb: "Operación · Cola de revisión" },
};

export default function Layout() {
  const { me, logout, can } = useAuth();
  const location = useLocation();
  const meta = TITLES[location.pathname] ?? { title: "AgeCare", crumb: "" };

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="logo">
          <div className="logo-mark"><img src="/agecare-logo.jpg" alt="AgeCare" /></div>
          <div>
            <div className="logo-name">AgeCare</div>
            <div className="logo-sub">Consola de administración</div>
          </div>
        </div>
        <nav className="nav">
          {NAV.map((group) => {
            const visible = group.items.filter((i) => can(i.module));
            if (!visible.length) return null;
            return (
              <div key={group.group}>
                <div className="nav-group">{group.group}</div>
                {visible.map((item) => (
                  <NavLink key={item.to} to={item.to} className={({ isActive }) => `nav-item${isActive ? " active" : ""}`}>
                    <span className="ico">{item.icon}</span>
                    {item.label}
                    {item.badge && <span className="new">{item.badge}</span>}
                  </NavLink>
                ))}
              </div>
            );
          })}
        </nav>
        <div className="sidebar-foot">
          <div className="sf-avatar">{me ? initials(me.full_name) : "?"}</div>
          <div>
            <div className="sf-name">{me?.full_name}</div>
            <div className="sf-role">{me ? ROLE_LABEL[me.role] ?? me.role : ""} · Wellq Co</div>
          </div>
          <button className="sf-logout" title="Cerrar sesión" onClick={logout}>⏻</button>
        </div>
      </aside>
      <div className="main">
        <header className="topbar">
          <div>
            <div className="tb-title">{meta.title}</div>
            <div className="tb-crumb">{meta.crumb}</div>
          </div>
          <div className="tb-spacer" />
          <span className="env-badge">Entorno local · datos de prueba</span>
        </header>
        <main className="content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

function initials(name: string): string {
  return name.split(" ").filter(Boolean).slice(0, 2).map((p) => p[0]?.toUpperCase()).join("");
}
