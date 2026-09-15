import type { ReactNode } from "react";

export function Card({ children, style }: { children: ReactNode; style?: React.CSSProperties }) {
  return <div className="card" style={style}>{children}</div>;
}

export function CardHead({ title, sub, right }: { title: string; sub?: string; right?: ReactNode }) {
  return (
    <div className="card-head">
      <div>
        <div className="card-title">{title}</div>
        {sub && <div className="card-sub">{sub}</div>}
      </div>
      {right}
    </div>
  );
}

export function Kpi({ label, value, delta, note }: { label: string; value: string; delta?: { text: string; dir: "up" | "down" | "flat" }; note?: string }) {
  return (
    <div className="kpi">
      <div className="kpi-label">{label}</div>
      <div className="kpi-value">{value}</div>
      {delta && <div className={`kpi-delta ${delta.dir === "flat" ? "" : delta.dir}`}>{delta.text}</div>}
      {note && <div className="kpi-note">{note}</div>}
    </div>
  );
}

export function Chip({ kind, children }: { kind: "ok" | "warn" | "serious" | "crit" | "neutral" | "gold"; children: ReactNode }) {
  return <span className={`chip ${kind}`}>{children}</span>;
}

export function StatusChip({ status }: { status: string }) {
  const map: Record<string, { kind: "ok" | "warn" | "crit" | "neutral" | "serious" | "gold"; label: string; icon: string }> = {
    approved: { kind: "ok", label: "Aprobada", icon: "✓" },
    operational: { kind: "ok", label: "Operativo", icon: "✓" },
    published: { kind: "ok", label: "Publicado", icon: "✓" },
    resolved: { kind: "ok", label: "Resuelto", icon: "✓" },
    pending: { kind: "warn", label: "Pendiente", icon: "⏳" },
    open: { kind: "warn", label: "Abierto", icon: "⏳" },
    degraded: { kind: "warn", label: "Degradado", icon: "⚠" },
    in_progress: { kind: "warn", label: "En progreso", icon: "⚙" },
    waiting_user: { kind: "warn", label: "Esperando usuario", icon: "⏳" },
    draft: { kind: "neutral", label: "Borrador", icon: "✎" },
    suspended: { kind: "crit", label: "Suspendida", icon: "⛔" },
    outage: { kind: "crit", label: "Caído", icon: "⛔" },
    rejected: { kind: "crit", label: "Rechazado", icon: "✕" },
    archived: { kind: "neutral", label: "Archivado", icon: "🗄" },
    investigating: { kind: "crit", label: "Investigando", icon: "🔎" },
    observing: { kind: "warn", label: "Observando", icon: "👁" },
    completed: { kind: "ok", label: "Completado", icon: "✓" },
    low: { kind: "neutral", label: "Baja", icon: "" },
    medium: { kind: "warn", label: "Media", icon: "" },
    high: { kind: "serious", label: "Alta", icon: "" },
    critical: { kind: "crit", label: "Crítica", icon: "" },
  };
  const m = map[status] ?? { kind: "neutral" as const, label: status, icon: "" };
  return <Chip kind={m.kind}>{m.icon} {m.label}</Chip>;
}

export function Spinner({ label = "Cargando…" }: { label?: string }) {
  return <div className="spinner-row">{label}</div>;
}

export function ErrorBanner({ message }: { message: string }) {
  return <div className="error-banner">⚠ {message}</div>;
}

export function EmptyState({ label }: { label: string }) {
  return <div className="empty-state">{label}</div>;
}

export function Seg<T extends string>({ options, value, onChange }: { options: { value: T; label: string }[]; value: T; onChange: (v: T) => void }) {
  return (
    <div className="seg" role="tablist">
      {options.map((o) => (
        <button key={o.value} className={o.value === value ? "on" : ""} onClick={() => onChange(o.value)}>
          {o.label}
        </button>
      ))}
    </div>
  );
}

export function Stars({ rating }: { rating: number }) {
  const full = Math.round(rating);
  return <span className="stars">{"★".repeat(full)}{"☆".repeat(5 - full)}</span>;
}

export function Drawer({ onClose, children }: { onClose: () => void; children: ReactNode }) {
  return (
    <>
      <div className="drawer-backdrop" onClick={onClose} />
      <div className="drawer">{children}</div>
    </>
  );
}

export function Modal({ title, onClose, children, width = 420 }: { title: string; onClose: () => void; children: ReactNode; width?: number }) {
  return (
    <>
      <div className="drawer-backdrop" onClick={onClose} />
      <div style={{
        position: "fixed", top: "50%", left: "50%", transform: "translate(-50%, -50%)",
        background: "var(--ac-surface-card)", borderRadius: "var(--ac-radius-xl)", boxShadow: "var(--ac-shadow-sheet)",
        padding: 22, width, maxWidth: "92vw", zIndex: 91, maxHeight: "88vh", overflowY: "auto",
      }}>
        <div className="drawer-head">
          <div className="card-title">{title}</div>
          <button className="drawer-close" onClick={onClose}>✕</button>
        </div>
        {children}
      </div>
    </>
  );
}

export function fmtNumber(n: number): string {
  return new Intl.NumberFormat("es-CL").format(n);
}
export function fmtCLP(n: number): string {
  return new Intl.NumberFormat("es-CL", { style: "currency", currency: "CLP", maximumFractionDigits: 0 }).format(n);
}
export function fmtPct(n: number): string {
  return `${(n * 100).toFixed(1)}%`;
}
export function fmtDate(iso: string): string {
  return new Date(iso).toLocaleDateString("es-CL", { day: "2-digit", month: "short", year: "numeric" });
}
export function fmtDateTime(iso: string): string {
  return new Date(iso).toLocaleString("es-CL", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
}
