import { useState } from "react";
import { MarketplaceApi } from "../api/endpoints";
import { useApi } from "../hooks/useApi";
import {
  Card, CardHead, Chip, Drawer, EmptyState, ErrorBanner, Spinner, StatusChip, Stars, fmtDate, fmtCLP,
} from "../components/ui";
import type { CaregiverDocType, CaregiverDocumentOut, CaregiverOut, ProductOut } from "../api/types";

const DOC_TYPE_LABELS: Record<CaregiverDocType, string> = {
  id_card: "Cédula de identidad",
  background_check: "Certificado de antecedentes",
  certificate: "Certificado o diploma de curso",
};
const DOC_TYPE_ORDER: CaregiverDocType[] = ["id_card", "background_check", "certificate"];

function DocStatusChip({ doc }: { doc: CaregiverDocumentOut }) {
  if (doc.status === "approved" && doc.pending_file_url) return <Chip kind="warn">Cambio por revisar</Chip>;
  if (doc.status === "approved") return <Chip kind="ok">✓ Aprobado</Chip>;
  if (doc.status === "rejected") return <Chip kind="crit">Rechazado</Chip>;
  return <Chip kind="warn">Por revisar</Chip>;
}

function EngagementChip({ isEngaged }: { isEngaged: boolean }) {
  return isEngaged
    ? <Chip kind="gold">● Trabajando</Chip>
    : <Chip kind="neutral">Disponible</Chip>;
}

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
            <tr><th>Nombre</th><th>Zona</th><th>Especialidades</th><th className="num">Rating</th><th>Disponibilidad</th><th>Estado</th><th>Documentos</th><th>Enviado</th></tr>
          </thead>
          <tbody>
            {list.data.items.map((c) => (
              <tr key={c.caregiver_id} className="clickable" onClick={() => setSelectedId(c.caregiver_id)}>
                <td style={{ fontWeight: 600 }}>{c.name}</td>
                <td>{c.zone}</td>
                <td>{c.specialties.join(", ") || "—"}</td>
                <td className="num">{c.rating_avg != null ? <Stars rating={c.rating_avg} /> : "—"}</td>
                <td><EngagementChip isEngaged={c.is_engaged} /></td>
                <td><StatusChip status={c.status} /></td>
                <td>{c.pending_documents > 0 ? <Chip kind="warn">{c.pending_documents} por revisar</Chip> : <span style={{ color: "var(--ac-text-tertiary)" }}>—</span>}</td>
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
  const [rejecting, setRejecting] = useState<CaregiverDocType | null>(null);
  const [rejectNote, setRejectNote] = useState("");

  async function reviewDoc(docType: CaregiverDocType, action: "approve" | "reject") {
    if (action === "reject" && rejectNote.trim().length < 5) {
      setError("Para rechazar un documento indica el motivo (mínimo 5 caracteres).");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await MarketplaceApi.reviewDocument(id, docType, action, action === "reject" ? rejectNote.trim() : undefined);
      setRejecting(null);
      setRejectNote("");
      onChanged();
      detail.reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo registrar la revisión del documento.");
    } finally {
      setBusy(false);
    }
  }

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
          <StatusChip status={c.status} /> <EngagementChip isEngaged={c.is_engaged} />
          <div className="field-label">Zona</div>
          <div className="field-value">{c.zone}</div>
          <div className="field-label">Especialidades</div>
          <div>{c.specialties.map((s) => <span key={s} className="tag-pill">{s}</span>)}</div>
          <div className="field-label">Idiomas</div>
          <div className="field-value">{c.languages.join(", ") || "—"}</div>
          <div className="field-label">Certificaciones</div>
          <div className="field-value">{c.certifications_count}</div>

          <div className="field-label">Documentos</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 10, marginBottom: 4 }}>
            {DOC_TYPE_ORDER.map((docType) => {
              const doc = c.documents.find((d) => d.doc_type === docType);
              const needsReview = !!doc && (doc.status === "pending" || !!doc.pending_file_url);
              return (
                <div key={docType} style={{ border: "1px solid var(--ac-border)", borderRadius: 12, padding: "10px 12px" }}>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10 }}>
                    <span style={{ fontSize: 12.5, fontWeight: 700 }}>{DOC_TYPE_LABELS[docType]}</span>
                    {doc ? <DocStatusChip doc={doc} /> : <Chip kind="neutral">No subido</Chip>}
                  </div>
                  {doc && (
                    <div style={{ marginTop: 8, display: "flex", gap: 8, flexWrap: "wrap" }}>
                      <a href={doc.file_url} target="_blank" rel="noreferrer" className="btn small ghost">
                        Ver {doc.pending_file_url ? "documento vigente" : "documento"}
                      </a>
                      {doc.pending_file_url && (
                        <a href={doc.pending_file_url} target="_blank" rel="noreferrer" className="btn small ghost">Ver cambio propuesto</a>
                      )}
                    </div>
                  )}
                  {doc?.status === "rejected" && doc.review_note && (
                    <div style={{ fontSize: 11.5, color: "var(--ac-attention-700)", marginTop: 6 }}>Motivo del rechazo: {doc.review_note}</div>
                  )}
                  {doc && doc.reviewed_by_name && !needsReview && (
                    <div style={{ fontSize: 11, color: "var(--ac-text-tertiary)", marginTop: 6 }}>Revisado por {doc.reviewed_by_name}{doc.reviewed_at ? ` · ${fmtDate(doc.reviewed_at)}` : ""}</div>
                  )}
                  {needsReview && (
                    rejecting === docType ? (
                      <div style={{ marginTop: 8 }}>
                        <input className="input" style={{ width: "100%" }} value={rejectNote} onChange={(e) => setRejectNote(e.target.value)}
                              placeholder="Motivo del rechazo (se le muestra a la cuidadora)" />
                        <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
                          <button className="btn small danger" disabled={busy} onClick={() => reviewDoc(docType, "reject")}>Confirmar rechazo</button>
                          <button className="btn small" disabled={busy} onClick={() => { setRejecting(null); setRejectNote(""); }}>Cancelar</button>
                        </div>
                      </div>
                    ) : (
                      <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
                        <button className="btn small primary" disabled={busy} onClick={() => reviewDoc(docType, "approve")}>
                          {doc?.pending_file_url ? "Aprobar cambio" : "Aprobar"}
                        </button>
                        <button className="btn small" disabled={busy} onClick={() => { setRejecting(docType); setError(null); }}>
                          {doc?.pending_file_url ? "Rechazar cambio" : "Rechazar"}
                        </button>
                      </div>
                    )
                  )}
                </div>
              );
            })}
          </div>

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

          {c.status !== "approved" && !c.certifications_verified && (
            <div style={{ marginTop: 14, fontSize: 12, color: "var(--ac-warn-700)", background: "var(--ac-warn-100)", borderRadius: 10, padding: "8px 12px" }}>
              Para {c.status === "suspended" ? "reactivar" : "aprobar"} este perfil primero aprueba su cédula de identidad y su certificado de antecedentes.
            </div>
          )}
          <div style={{ display: "flex", gap: 8, marginTop: 18, flexWrap: "wrap" }}>
            {c.status === "suspended" && (
              <button className="btn primary" disabled={busy || !c.certifications_verified} onClick={() => act("approved")}>Reactivar perfil</button>
            )}
            {c.status === "pending" && (
              <button className="btn primary" disabled={busy || !c.certifications_verified} onClick={() => act("approved")}>Aprobar perfil</button>
            )}
            {c.status !== "suspended" && (
              <button className="btn danger" disabled={busy} onClick={() => act("suspended")}>Suspender</button>
            )}
          </div>
          {c.status !== "suspended" && (
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
