import { useState, type ReactNode } from "react";
import { createPortal } from "react-dom";

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

export function Chip({ kind, children }: { kind: "gold" | "brand" | "neutral"; children: ReactNode }) {
  return <span className={`chip ${kind}`}>{children}</span>;
}

/** Indicador en píldora para los encabezados: ícono redondo, etiqueta, valor y una marca opcional. */
export function StatChip({ icon, label, value, tag, tone = "ink" }: {
  icon: string; label: string; value: string | number; tag?: string; tone?: "ink" | "blue" | "yellow" | "teal";
}) {
  return (
    <div className="stat-chip">
      <span className={`stat-chip-ico ${tone}`}>{icon}</span>
      <div>
        <div className="stat-chip-label">{label}</div>
        <div className="stat-chip-value">{value}</div>
      </div>
      {tag && <span className={`stat-chip-tag ${tone}`}>{tag}</span>}
    </div>
  );
}

export function Initials({ name }: { name: string }) {
  return <>{name.split(" ").filter(Boolean).slice(0, 2).map((p) => p[0]?.toUpperCase()).join("")}</>;
}

export function Avatar({ name, photoUrl }: { name: string; photoUrl?: string | null }) {
  // Si la foto no carga (archivo borrado o dirección caída) se muestran las iniciales en vez de una imagen rota.
  const [failed, setFailed] = useState(false);
  if (photoUrl && !failed) return <img className="avatar-img" src={photoUrl} alt={name} onError={() => setFailed(true)} />;
  return <Initials name={name} />;
}

/** Se monta en <body>: dentro de la página, los contenedores con desenfoque encierran a los elementos «fijos». */
export function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
  return createPortal(
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h3>{title}</h3>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>
        {children}
      </div>
    </div>,
    document.body,
  );
}

/** Pide confirmar una acción que no se puede deshacer. */
export function ConfirmModal({ title, confirmLabel, busy, error, onConfirm, onClose, children, tone = "danger", busyLabel = "Eliminando…" }: {
  title: string; confirmLabel: string; busy: boolean; error: string | null; tone?: "danger" | "neutral"; busyLabel?: string;
  onConfirm: () => void; onClose: () => void; children: ReactNode;
}) {
  return (
    <Modal title={title} onClose={busy ? () => {} : onClose}>
      <div className="confirm-body">{children}</div>
      {error && <ErrorBanner message={error} />}
      <div className="confirm-actions">
        <button className="btn ghost" onClick={onClose} disabled={busy}>Cancelar</button>
        <button className={tone === "danger" ? "btn danger" : "btn primary"} onClick={onConfirm} disabled={busy}>{busy ? busyLabel : confirmLabel}</button>
      </div>
    </Modal>
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

export function fmtCLP(n: number): string {
  return "$" + Math.round(n).toLocaleString("es-CL");
}
