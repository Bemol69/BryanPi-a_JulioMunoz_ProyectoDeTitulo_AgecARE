import { useState } from "react";
import { MarketplaceApi } from "../api/endpoints";
import { useApi } from "../hooks/useApi";
import {
  Card, CardHead, Drawer, EmptyState, ErrorBanner, Spinner, StatusChip, Stars, fmtDate, fmtCLP,
} from "../components/ui";
import type { CaregiverOut, ProductOut } from "../api/types";

export default function Marketplace() {
  const [tab, setTab] = useState<"cuidadoras" | "articulos">("cuidadoras");
  return (
    <div>
      <div className="tabs">
        <button className={tab === "cuidadoras" ? "on" : ""} onClick={() => setTab("cuidadoras")}>Cuidadoras</button>
        <button className={tab === "articulos" ? "on" : ""} onClick={() => setTab("articulos")}>Artículos de apoyo</button>
      </div>
      {tab === "cuidadoras" ? <CaregiversTab /> : <ProductsTab />}
    </div>
  );
}

function CaregiversTab() {
  const [status, setStatus] = useState("");
  const [q, setQ] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const list = useApi(() => MarketplaceApi.listCaregivers({ status: status || undefined, q: q || undefined }), [status, q]);

  return (
    <Card>
      <CardHead
        title="Cuidadoras del marketplace"
        sub="Perfiles enviados por cuidadoras para publicarse en la app de familias"
        right={
          <div style={{ display: "flex", gap: 8 }}>
            <input className="input" placeholder="Buscar por nombre o correo…" value={q} onChange={(e) => setQ(e.target.value)} />
            <select className="select" value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value="">Todos los estados</option>
              <option value="pending">Pendientes</option>
              <option value="approved">Aprobadas</option>
              <option value="suspended">Suspendidas</option>
            </select>
          </div>
        }
      />
      {list.error && <ErrorBanner message={list.error} />}
      {list.loading && <Spinner />}
      {list.data && list.data.items.length === 0 && <EmptyState label="No se encontraron cuidadoras con esos filtros." />}
      {list.data && list.data.items.length > 0 && (
        <table className="data">
          <thead>
            <tr><th>Nombre</th><th>Zona</th><th>Especialidades</th><th className="num">Rating</th><th>Estado</th><th>Enviado</th></tr>
          </thead>
          <tbody>
            {list.data.items.map((c) => (
              <tr key={c.caregiver_id} className="clickable" onClick={() => setSelectedId(c.caregiver_id)}>
                <td style={{ fontWeight: 600 }}>{c.name}</td>
                <td>{c.zone}</td>
                <td>{c.specialties.join(", ") || "—"}</td>
                <td className="num">{c.rating_avg != null ? <Stars rating={c.rating_avg} /> : "—"}</td>
                <td><StatusChip status={c.status} /></td>
                <td>{fmtDate(c.submitted_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {selectedId && (
        <CaregiverDrawer id={selectedId} onClose={() => setSelectedId(null)} onChanged={() => { list.reload(); }} />
      )}
    </Card>
  );
}

function CaregiverDrawer({ id, onClose, onChanged }: { id: string; onClose: () => void; onChanged: () => void }) {
  const detail = useApi(() => MarketplaceApi.getCaregiver(id), [id]);
  const [note, setNote] = useState("");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function act(newStatus: "approved" | "suspended") {
    setBusy(true);
    setError(null);
    try {
      if (newStatus === "suspended" && reason.trim().length < 10) {
        setError("Para suspender, indica un motivo de al menos 10 caracteres.");
        setBusy(false);
        return;
      }
      await MarketplaceApi.patchCaregiver(id, { status: newStatus, reason: newStatus === "suspended" ? reason.trim() : undefined });
      onChanged();
      detail.reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo actualizar el estado.");
    } finally {
      setBusy(false);
    }
  }

  async function saveNote(c: CaregiverOut) {
    setBusy(true);
    try {
      await MarketplaceApi.patchCaregiver(id, { internal_note: note || c.internal_note || "" });
      detail.reload();
    } finally {
      setBusy(false);
    }
  }

  const c = detail.data;
  return (
    <Drawer onClose={onClose}>
      <div className="drawer-head">
        <div className="card-title">{c?.name ?? "Detalle de cuidadora"}</div>
        <button className="drawer-close" onClick={onClose}>✕</button>
      </div>
      {detail.loading && <Spinner />}
      {detail.error && <ErrorBanner message={detail.error} />}
      {c && (
        <div>
          <StatusChip status={c.status} />
          <div className="field-label">Zona</div>
          <div className="field-value">{c.zone}</div>
          <div className="field-label">Especialidades</div>
          <div>{c.specialties.map((s) => <span key={s} className="tag-pill">{s}</span>)}</div>
          <div className="field-label">Idiomas</div>
          <div className="field-value">{c.languages.join(", ") || "—"}</div>
          <div className="field-label">Certificaciones</div>
          <div className="field-value">{c.certifications_count}</div>
          <div className="field-label">Rating</div>
          <div className="field-value">{c.rating_avg != null ? <>{c.rating_avg.toFixed(2)} · {c.reviews_count} reseñas</> : "Sin reseñas todavía"}</div>
          <div className="field-label">Enviado el</div>
          <div className="field-value">{fmtDate(c.submitted_at)}</div>
          {c.reviewed_by_name && (
            <>
              <div className="field-label">Revisado por</div>
              <div className="field-value">{c.reviewed_by_name}</div>
            </>
          )}

          <div className="field-label">Nota interna</div>
          <textarea className="input" style={{ width: "100%", minHeight: 60 }}
                   defaultValue={c.internal_note ?? ""} onChange={(e) => setNote(e.target.value)} />
          <div style={{ marginTop: 8 }}>
            <button className="btn small" disabled={busy} onClick={() => saveNote(c)}>Guardar nota</button>
          </div>

          {error && <div style={{ marginTop: 12 }}><ErrorBanner message={error} /></div>}

          <div style={{ display: "flex", gap: 8, marginTop: 18, flexWrap: "wrap" }}>
            {c.status !== "approved" && (
              <button className="btn primary" disabled={busy} onClick={() => act("approved")}>Aprobar perfil</button>
            )}
            {c.status !== "suspended" && (
              <button className="btn danger" disabled={busy} onClick={() => act("suspended")}>Suspender</button>
            )}
          </div>
          {c.status !== "approved" && (
            <div style={{ marginTop: 10 }}>
              <label className="field-label" style={{ margin: "0 0 5px" }}>Motivo (obligatorio para suspender)</label>
              <input className="input" style={{ width: "100%" }} value={reason} onChange={(e) => setReason(e.target.value)}
                    placeholder="Ej: reiteradas ausencias reportadas por familias" />
            </div>
          )}
        </div>
      )}
    </Drawer>
  );
}

function ProductsTab() {
  const list = useApi(() => MarketplaceApi.listProducts({}), []);
  return (
    <Card>
      <CardHead title="Artículos de apoyo" sub="Vitrina de productos de terceros mostrada en el marketplace de la app" />
      {list.error && <ErrorBanner message={list.error} />}
      {list.loading && <Spinner />}
      {list.data && list.data.items.length === 0 && <EmptyState label="No hay artículos publicados." />}
      {list.data && list.data.items.length > 0 && (
        <table className="data">
          <thead><tr><th>Producto</th><th>Categoría</th><th>Proveedor</th><th className="num">Precio</th><th>Estado</th></tr></thead>
          <tbody>
            {list.data.items.map((p: ProductOut) => (
              <tr key={p.id}>
                <td style={{ fontWeight: 600 }}>{p.name}</td>
                <td>{p.category}</td>
                <td>{p.vendor}</td>
                <td className="num">{p.price_clp != null ? fmtCLP(p.price_clp) : "—"}</td>
                <td><StatusChip status={p.status} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Card>
  );
}
