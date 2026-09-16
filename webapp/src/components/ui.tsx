import type { ReactNode } from "react";

export function Spinner({ label = "Cargando…" }: { label?: string }) {
  return <div className="spinner-row">{label}</div>;
}

export function EmptyState({ label }: { label: string }) {
  return <div className="empty-state">{label}</div>;
}

export function ErrorBanner({ message }: { message: string }) {
  return <div className="error-banner">⚠ {message}</div>;
}

export function OkBanner({ message }: { message: string }) {
  return <div className="ok-banner">✓ {message}</div>;
}

export function Stars({ rating }: { rating: number }) {
  const full = Math.round(rating);
  return <span className="stars">{"★".repeat(full)}{"☆".repeat(5 - full)}</span>;
}

export function Chip({ kind, children }: { kind: "gold" | "teal" | "neutral"; children: ReactNode }) {
  return <span className={`chip ${kind}`}>{children}</span>;
}

export function Initials({ name }: { name: string }) {
  return <>{name.split(" ").filter(Boolean).slice(0, 2).map((p) => p[0]?.toUpperCase()).join("")}</>;
}

export function Avatar({ name, photoUrl }: { name: string; photoUrl?: string | null }) {
  if (photoUrl) return <img className="avatar-img" src={photoUrl} alt={name} />;
  return <Initials name={name} />;
}

export function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h3>{title}</h3>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>
        {children}
      </div>
    </div>
  );
}

export function Switch({ checked, onChange }: { checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <label className="switch">
      <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} />
      <span className="track" />
      <span className="thumb" />
    </label>
  );
}

export function fmtDate(iso: string): string {
  return new Date(iso).toLocaleDateString("es-CL", { day: "2-digit", month: "short", year: "numeric" });
}
