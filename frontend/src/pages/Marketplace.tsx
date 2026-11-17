import { useMemo, useState } from "react";
import { MarketplaceApi } from "../api/endpoints";
import { useAuth } from "../auth/AuthContext";
import { useApi } from "../hooks/useApi";
import ReviewsManager from "../components/ReviewsManager";
import {
  Card, CardHead, Chip, Drawer, EmptyState, ErrorBanner, Kpi, Modal, Person, PersonAvatar, Spinner, StatusChip, Stars, fmtDate, fmtDateTime, fmtCLP, fmtNumber,
} from "../components/ui";
import type {
  CaregiverDocType, CaregiverDocumentOut, CaregiverOut, PaymentMethodKey, ProductCategoryKey, ProductInput, ProductOut,
  VerificationEvent, VerificationInput, WaiverReasonKey,
} from "../api/types";

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

const plural = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`;

const daysLeft = (until: string) => Math.ceil((new Date(until).getTime() - Date.now()) / 86_400_000);

function FeeChip({ c }: { c: Pick<CaregiverOut, "verification_fee_status" | "verification_waiver_until" | "verification_waiver_expired"> }) {
  if (c.verification_fee_status === "paid") return <Chip kind="ok">✓ Pagada</Chip>;
  if (c.verification_fee_status === "waived") {
    if (c.verification_waiver_expired) return <Chip kind="crit">Exención vencida</Chip>;
    const d = c.verification_waiver_until ? daysLeft(c.verification_waiver_until) : null;
    if (d != null && d <= 14) return <Chip kind="warn">Eximida · vence en {Math.max(d, 0)} d</Chip>;
    return <Chip kind="neutral">Eximida</Chip>;
  }
  return <Chip kind="warn">Por pagar</Chip>;
}

const WAIVER_REASONS: { key: WaiverReasonKey; label: string; expires: boolean }[] = [
  { key: "launch_promo", label: "Promoción de lanzamiento", expires: true },
  { key: "institution_agreement", label: "Convenio con institución", expires: false },
  { key: "scholarship", label: "Beca", expires: true },
  { key: "special_case", label: "Caso especial (hay que explicarlo)", expires: false },
];
const WAIVER_LABEL = Object.fromEntries(WAIVER_REASONS.map((r) => [r.key, r.label.replace(/ \(.*\)$/, "")])) as Record<string, string>;
const WAIVER_DAYS = [30, 60, 90, 180, 365];
const PAYMENT_METHODS: { key: PaymentMethodKey; label: string }[] = [
  { key: "transfer", label: "Transferencia" }, { key: "deposit", label: "Depósito" },
  { key: "cash", label: "Efectivo" }, { key: "other", label: "Otro" },
];
const METHOD_LABEL = Object.fromEntries(PAYMENT_METHODS.map((m) => [m.key, m.label])) as Record<string, string>;

function FeeHistory({ id, refreshKey }: { id: string; refreshKey: number }) {
  const h = useApi(() => MarketplaceApi.verificationHistory(id), [id, refreshKey]);
  const [all, setAll] = useState(false);
  const events: VerificationEvent[] = h.data ?? [];
  if (h.loading || events.length === 0) return null;
  const describe = (e: VerificationEvent) => {
    if (e.status === "paid") {
      return `Pago confirmado${e.method ? ` · ${METHOD_LABEL[e.method]}` : ""}${e.receipt ? ` · comprobante ${e.receipt}` : ""}`;
    }
    if (e.status === "waived") {
      return `Eximida${e.reason ? ` · ${WAIVER_LABEL[e.reason]}` : ""}${e.until ? ` · vence el ${fmtDate(e.until)}` : " · sin vencimiento"}`;
    }
    return `Cobro revertido${e.previous_status === "paid" ? " (estaba pagado)" : e.previous_status === "waived" ? " (estaba eximida)" : ""}`;
  };
  const shown = all ? events : events.slice(0, 4);
  return (
    <div style={{ marginTop: -4, marginBottom: 14 }}>
      <div className="field-label">Historial del cobro</div>
      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        {shown.map((e, i) => (
          <div key={`${e.at}-${i}`} style={{ fontSize: 12, borderLeft: "2px solid var(--ac-border)", paddingLeft: 10 }}>
            <div style={{ fontWeight: 700 }}>{describe(e)}</div>
            <div style={{ color: "var(--ac-text-tertiary)", fontSize: 11 }}>
              {fmtDateTime(e.at)}{e.actor_name ? ` · ${e.actor_name}` : ""}
            </div>
            {e.note && <div style={{ fontStyle: "italic", color: "var(--ac-text-secondary)" }}>«{e.note}»</div>}
          </div>
        ))}
      </div>
      {events.length > 4 && (
        <button className="btn small ghost" style={{ marginTop: 6 }} onClick={() => setAll(!all)}>
          {all ? "Ver menos" : `Ver todo (${events.length})`}
        </button>
      )}
    </div>
  );
}

/** Cobro de verificación de una cuidadora: pago con comprobante o exención con motivo y vencimiento. */
function FeePanel({ c, onChanged }: { c: CaregiverOut; onChanged: () => void }) {
  const { me } = useAuth();
  const isAdmin = me?.role === "admin"; // solo un administrador exime o revierte; el resto confirma pagos
  const quotas = useApi(() => MarketplaceApi.monetization(), [c.verification_fee_status, c.verification_waiver_reason]).data?.verification_waiver_quotas ?? {};
  const [mode, setMode] = useState<null | "paid" | "waive">(null);
  const [method, setMethod] = useState<PaymentMethodKey>("transfer");
  const [receipt, setReceipt] = useState("");
  const [reason, setReason] = useState<WaiverReasonKey>("launch_promo");
  const [days, setDays] = useState("90"); // "none" = sin vencimiento
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const status = c.verification_fee_status;
  const expired = c.verification_waiver_expired;
  const reasonInfo = WAIVER_REASONS.find((r) => r.key === reason)!;
  const published = c.status === "approved";

  async function send(body: VerificationInput) {
    setBusy(true);
    setError(null);
    try {
      await MarketplaceApi.setVerification(c.caregiver_id, body);
      setMode(null);
      setReceipt("");
      setNote("");
      onChanged();
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo actualizar el cobro.");
    } finally {
      setBusy(false);
    }
  }

  function submitWaiver() {
    if (reasonInfo.expires && days === "none") return setError("Esta exención debe tener fecha de vencimiento.");
    if (reason === "special_case" && note.trim().length < 10) return setError("Para un caso especial explica el motivo (mínimo 10 caracteres).");
    void send({ action: "waived", reason, days: days === "none" ? null : Number(days), note: note.trim() || undefined });
  }

  const small = { fontSize: 11.5, color: "var(--ac-text-secondary)", marginTop: 6 } as const;
  const label = { fontSize: 11.5, fontWeight: 700, color: "var(--ac-text-secondary)", margin: "10px 0 4px", display: "block" } as const;

  return (
    <div style={{ border: "1px solid var(--ac-border)", borderRadius: 12, padding: "10px 12px", marginBottom: 14 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10 }}>
        <span style={{ fontSize: 12.5, fontWeight: 700 }}>{fmtCLP(c.verification_fee_clp)} · pago único</span>
        <FeeChip c={c} />
      </div>
      {c.verification_reference && (
        <div style={small}>Código de pago de la cuidadora: <b style={{ letterSpacing: ".06em" }}>{c.verification_reference}</b></div>
      )}

      {status === "paid" && (
        <div style={small}>
          Pago confirmado{c.verification_marked_by ? ` por ${c.verification_marked_by}` : ""}
          {c.verification_paid_at ? ` · ${fmtDate(c.verification_paid_at)}` : ""}
          {c.verification_payment_method ? ` · ${METHOD_LABEL[c.verification_payment_method]}` : ""}
          {c.verification_receipt ? ` · comprobante ${c.verification_receipt}` : ""}.
          El sitio muestra «Perfil calificado» y la ubica primero en las búsquedas.
        </div>
      )}
      {status === "waived" && (
        <div style={small}>
          <b>{c.verification_waiver_reason ? WAIVER_LABEL[c.verification_waiver_reason] : "Exención"}</b>
          {c.verification_waiver_until
            ? (expired
                ? ` · venció el ${fmtDate(c.verification_waiver_until)}`
                : ` · vence el ${fmtDate(c.verification_waiver_until)} (en ${Math.max(daysLeft(c.verification_waiver_until), 0)} días)`)
            : " · sin vencimiento"}
          {c.verification_marked_by ? ` · por ${c.verification_marked_by}` : ""}
          {c.verification_waiver_note && <div style={{ marginTop: 3, fontStyle: "italic" }}>«{c.verification_waiver_note}»</div>}
          <div style={{ marginTop: 3 }}>
            {expired
              ? (published ? "Su exención terminó: el perfil dejó de mostrarse en el sitio hasta que pague." : "Su exención terminó: debe pagar para publicarse.")
              : "Se puede publicar, pero sin insignia ni prioridad en las búsquedas."}
          </div>
        </div>
      )}
      {status === "unpaid" && <div style={small}>No se puede aprobar el perfil hasta confirmar el pago o eximirla.</div>}

      {!isAdmin && <div style={small}>Solo un administrador puede eximir un pago o revertir un cobro. Tú puedes confirmar pagos recibidos.</div>}
      {mode === null && (
        <div style={{ display: "flex", gap: 8, marginTop: 10, flexWrap: "wrap" }}>
          {status !== "paid" && <button className="btn small primary" disabled={busy} onClick={() => { setError(null); setMode("paid"); }}>Confirmar pago recibido</button>}
          {status !== "paid" && isAdmin && <button className="btn small" disabled={busy} onClick={() => { setError(null); setMode("waive"); }}>{status === "waived" ? "Renovar / cambiar exención" : "Eximir de pago"}</button>}
          {status !== "unpaid" && isAdmin && (
            <button className="btn small" disabled={busy || published} onClick={() => send({ action: "unpaid" })}
                    title={published ? "El perfil está aprobado: suspéndelo antes de revertir el cobro" : undefined}>Revertir</button>
          )}
        </div>
      )}
      {mode === "paid" && (
        <div>
          <label style={label}>Cómo se recibió</label>
          <select className="select" style={{ width: "100%" }} value={method} onChange={(e) => setMethod(e.target.value as PaymentMethodKey)}>
            {PAYMENT_METHODS.map((m) => <option key={m.key} value={m.key}>{m.label}</option>)}
          </select>
          <label style={label}>N° de comprobante (opcional, para conciliar con el banco)</label>
          <input className="input" style={{ width: "100%" }} maxLength={60} value={receipt} onChange={(e) => setReceipt(e.target.value)} placeholder="Ej: TR-48213" />
          <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
            <button className="btn small primary" disabled={busy} onClick={() => send({ action: "paid", method, receipt: receipt.trim() || undefined })}>{busy ? "Guardando…" : "Confirmar pago"}</button>
            <button className="btn small" disabled={busy} onClick={() => setMode(null)}>Cancelar</button>
          </div>
        </div>
      )}
      {mode === "waive" && (
        <div>
          <label style={label}>Motivo de la exención</label>
          <select className="select" style={{ width: "100%" }} value={reason}
                  onChange={(e) => { const r = e.target.value as WaiverReasonKey; setReason(r); if (WAIVER_REASONS.find((x) => x.key === r)!.expires && days === "none") setDays("90"); }}>
            {WAIVER_REASONS.map((r) => {
              const q = quotas[r.key];
              const mine = status === "waived" && !expired && c.verification_waiver_reason === r.key; // renovar no gasta otro cupo
              const left = q ? q.limit - q.used : null;
              return (
                <option key={r.key} value={r.key} disabled={left != null && left <= 0 && !mine}>
                  {r.label}{q ? ` · quedan ${Math.max(left ?? 0, 0)} de ${q.limit} cupos` : ""}
                </option>
              );
            })}
          </select>
          <label style={label}>Vigencia {reasonInfo.expires && "(obligatoria para este motivo)"}</label>
          <select className="select" style={{ width: "100%" }} value={days} onChange={(e) => setDays(e.target.value)}>
            {WAIVER_DAYS.map((d) => <option key={d} value={d}>{d} días</option>)}
            {!reasonInfo.expires && <option value="none">Sin vencimiento</option>}
          </select>
          <label style={label}>Nota {reason === "special_case" ? "(obligatoria)" : "(opcional)"}</label>
          <textarea className="input" style={{ width: "100%", minHeight: 52 }} maxLength={300} value={note} onChange={(e) => setNote(e.target.value)}
                    placeholder="Ej: Convenio con la Municipalidad de Ñuñoa" />
          <div style={small}>Al vencer, vuelve a «por pagar» y el perfil deja de mostrarse hasta que pague.</div>
          <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
            <button className="btn small primary" disabled={busy} onClick={submitWaiver}>{busy ? "Guardando…" : "Eximir de pago"}</button>
            <button className="btn small" disabled={busy} onClick={() => { setMode(null); setError(null); }}>Cancelar</button>
          </div>
        </div>
      )}
      {error && <div style={{ marginTop: 10 }}><ErrorBanner message={error} /></div>}
    </div>
  );
}

/** Cuánto aportan hoy las dos fuentes de ingreso del marketplace (verificación y artículos de apoyo). */
function MonetizationSummary({ refreshKey }: { refreshKey: number }) {
  const m = useApi(() => MarketplaceApi.monetization(), [refreshKey]);
  if (m.error) return <ErrorBanner message={m.error} />;
  if (!m.data) return null;
  const d = m.data;
  return (
    <div className="kpis" style={{ marginBottom: 18 }}>
      <Kpi label="Verificaciones cobradas" value={fmtCLP(d.verification_paid_total_clp)}
          note={`${plural(d.verification_paid_count, "pago", "pagos")} de ${fmtCLP(d.verification_fee_clp)}`} />
      <Kpi label="Por cobrar" value={fmtCLP(d.verification_pending_total_clp)}
          note={`${plural(d.verification_pending_count, "cuidadora", "cuidadoras")} con el pago pendiente${d.verification_expired_count ? ` · ${d.verification_expired_count} con exención vencida` : ""}`} />
      <Kpi label="Exenciones vigentes" value={String(d.verification_waived_count)}
          note={`${fmtCLP(d.verification_waived_value_clp)} sin cobrar${d.verification_expiring_soon_count ? ` · ${plural(d.verification_expiring_soon_count, "vence", "vencen")} en 14 días` : ""}`} />
      <Kpi label="Clics a tiendas (30 días)" value={d.clicks_30d != null ? fmtNumber(d.clicks_30d) : "—"}
          note={d.clicks_total != null ? `${fmtNumber(d.clicks_total)} en total · ${plural(d.products_published, "artículo", "artículos")}` : "El sitio público no respondió"} />
      <Kpi label="Comisión estimada (30 días)" value={d.estimated_commission_30d_clp != null ? fmtCLP(d.estimated_commission_30d_clp) : "—"}
          note={`Supone ${d.assumed_conversion_pct}% de compra por clic · ${plural(d.products_sponsored, "patrocinado", "patrocinados")}`} />
    </div>
  );
}

function EngagementChip({ isEngaged }: { isEngaged: boolean }) {
  return isEngaged
    ? <Chip kind="gold">● Trabajando</Chip>
    : <Chip kind="neutral">Disponible</Chip>;
}

export default function Marketplace() {
  const [tab, setTab] = useState<"cuidadoras" | "articulos">("cuidadoras");
  const [summaryKey, setSummaryKey] = useState(0);
  const refreshSummary = () => setSummaryKey((k) => k + 1);
  return (
    <div>
      <MonetizationSummary refreshKey={summaryKey} />
      <div className="tabs">
        <button className={tab === "cuidadoras" ? "on" : ""} onClick={() => setTab("cuidadoras")}>Cuidadoras</button>
        <button className={tab === "articulos" ? "on" : ""} onClick={() => setTab("articulos")}>Artículos de apoyo</button>
      </div>
      {tab === "cuidadoras" ? <CaregiversTab onChanged={refreshSummary} /> : <ProductsTab onChanged={refreshSummary} />}
    </div>
  );
}

function CaregiversTab({ onChanged }: { onChanged: () => void }) {
  const [status, setStatus] = useState("");
  const [fee, setFee] = useState("");
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);
  const [q, setQ] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const list = useApi(() => MarketplaceApi.listCaregivers({ status: status || undefined, fee: fee || undefined, q: q || undefined }), [status, fee, q]);

  return (
    <Card>
      <CardHead
        title="Cuidadoras del marketplace"
        sub="Perfiles enviados por cuidadoras para publicarse en la app de familias"
        right={
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", justifyContent: "flex-end" }}>
            <button className="btn" disabled={exporting} title="Descarga los pagos y exenciones en un archivo que abre Excel"
                    onClick={async () => { setExporting(true); setExportError(null); try { await MarketplaceApi.exportVerification(); } catch (e) { setExportError(e instanceof Error ? e.message : "No se pudo exportar."); } finally { setExporting(false); } }}>
              {exporting ? "Exportando…" : "⬇ Exportar cobros (CSV)"}
            </button>
            <input className="input" placeholder="Buscar por nombre o correo…" value={q} onChange={(e) => setQ(e.target.value)} />
            <select className="select" value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value="">Todos los estados</option>
              <option value="pending">Pendientes</option>
              <option value="approved">Aprobadas</option>
              <option value="suspended">Suspendidas</option>
            </select>
            <select className="select" value={fee} onChange={(e) => setFee(e.target.value)} aria-label="Estado del cobro">
              <option value="">Todos los cobros</option>
              <option value="unpaid">Por pagar</option>
              <option value="paid">Pagadas</option>
              <option value="waived">Eximidas vigentes</option>
              <option value="expired">Exención vencida</option>
            </select>
          </div>
        }
      />
      {exportError && <ErrorBanner message={exportError} />}
      {list.error && <ErrorBanner message={list.error} />}
      {list.loading && <Spinner />}
      {list.data && list.data.items.length === 0 && <EmptyState label="No se encontraron cuidadoras con esos filtros." />}
      {list.data && list.data.items.length > 0 && (
        <table className="data">
          <thead>
            <tr><th>Nombre</th><th>Zona</th><th>Especialidades</th><th className="num">Rating</th><th>Disponibilidad</th><th>Estado</th><th>Verificación</th><th>Documentos</th><th>Enviado</th></tr>
          </thead>
          <tbody>
            {list.data.items.map((c) => (
              <tr key={c.caregiver_id} className="clickable" onClick={() => setSelectedId(c.caregiver_id)}>
                <td><Person name={c.name} photoUrl={c.photo_url} /></td>
                <td>{c.zone}</td>
                <td>{c.specialties.join(", ") || "—"}</td>
                <td className="num">{c.rating_avg != null ? <Stars rating={c.rating_avg} /> : "—"}</td>
                <td><EngagementChip isEngaged={c.is_engaged} /></td>
                <td><StatusChip status={c.status} /></td>
                <td><FeeChip c={c} /></td>
                <td>{c.pending_documents > 0 ? <Chip kind="warn">{c.pending_documents} por revisar</Chip> : <span style={{ color: "var(--ac-text-tertiary)" }}>—</span>}</td>
                <td>{fmtDate(c.submitted_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {selectedId && (
        <CaregiverDrawer id={selectedId} onClose={() => setSelectedId(null)} onChanged={() => { list.reload(); onChanged(); }} />
      )}
    </Card>
  );
}

function CaregiverDrawer({ id, onClose, onChanged }: { id: string; onClose: () => void; onChanged: () => void }) {
  const detail = useApi(() => MarketplaceApi.getCaregiver(id), [id]);
  const [feeKey, setFeeKey] = useState(0);
  const [note, setNote] = useState("");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [rejecting, setRejecting] = useState<CaregiverDocType | null>(null);
  const [rejectNote, setRejectNote] = useState("");
  const [deleting, setDeleting] = useState(false);
  // Los botones esperan también a que termine de recargarse el detalle: un segundo clic rápido actuaría sobre datos viejos.
  const locked = busy || detail.loading;

  async function deleteProfile() {
    setBusy(true);
    setError(null);
    try {
      await MarketplaceApi.deleteCaregiver(id);
      onChanged();
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo eliminar el perfil.");
      setDeleting(false);
    } finally {
      setBusy(false);
    }
  }

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
        {c ? (
          <div className="drawer-person">
            <PersonAvatar name={c.name} photoUrl={c.photo_url} size={64} />
            <div>
              <div className="card-title">{c.name}</div>
              {!c.photo_url && <div className="card-sub">Todavía no sube su foto de perfil</div>}
            </div>
          </div>
        ) : <div className="card-title">Detalle de cuidadora</div>}
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

          <div className="field-label">Cobro de verificación</div>
          <FeePanel c={c} onChanged={() => { onChanged(); detail.reload(); setFeeKey((k) => k + 1); }} />
          <FeeHistory id={id} refreshKey={feeKey} />

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
                          <button className="btn small danger" disabled={locked} onClick={() => reviewDoc(docType, "reject")}>Confirmar rechazo</button>
                          <button className="btn small" disabled={locked} onClick={() => { setRejecting(null); setRejectNote(""); }}>Cancelar</button>
                        </div>
                      </div>
                    ) : (
                      <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
                        <button className="btn small primary" disabled={locked} onClick={() => reviewDoc(docType, "approve")}>
                          {doc?.pending_file_url ? "Aprobar cambio" : "Aprobar"}
                        </button>
                        <button className="btn small" disabled={locked} onClick={() => { setRejecting(docType); setError(null); }}>
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
          <div className="field-label">Calificaciones de las familias</div>
          <ReviewsManager caregiverId={id} onChanged={() => { detail.reload(); onChanged(); }} />
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
            <button className="btn small" disabled={locked} onClick={() => saveNote(c)}>Guardar nota</button>
          </div>

          {error && <div style={{ marginTop: 12 }}><ErrorBanner message={error} /></div>}

          {c.status !== "approved" && (c.verification_fee_status === "unpaid" || c.verification_waiver_expired) && (
            <div style={{ marginTop: 14, fontSize: 12, color: "var(--ac-warn-700)", background: "var(--ac-warn-100)", borderRadius: 10, padding: "8px 12px" }}>
              Falta el pago de la verificación (o su exención venció): confirma el pago o vuelve a eximirla para poder aprobar su perfil.
            </div>
          )}
          {c.status !== "approved" && !c.certifications_verified && (
            <div style={{ marginTop: 14, fontSize: 12, color: "var(--ac-warn-700)", background: "var(--ac-warn-100)", borderRadius: 10, padding: "8px 12px" }}>
              Para {c.status === "suspended" ? "reactivar" : "aprobar"} este perfil primero aprueba su cédula de identidad y su certificado de antecedentes.
            </div>
          )}
          <div style={{ display: "flex", gap: 8, marginTop: 18, flexWrap: "wrap" }}>
            {c.status === "suspended" && (
              <button className="btn primary" disabled={locked || !c.certifications_verified || (c.verification_fee_status === "unpaid" || c.verification_waiver_expired)} onClick={() => act("approved")}>Reactivar perfil</button>
            )}
            {c.status === "pending" && (
              <button className="btn primary" disabled={locked || !c.certifications_verified || (c.verification_fee_status === "unpaid" || c.verification_waiver_expired)} onClick={() => act("approved")}>Aprobar perfil</button>
            )}
            {c.status !== "suspended" && (
              <button className="btn danger" disabled={locked} onClick={() => act("suspended")}>Suspender</button>
            )}
          </div>
          {c.status !== "suspended" && (
            <div style={{ marginTop: 10 }}>
              <label className="field-label" style={{ margin: "0 0 5px" }}>Motivo (obligatorio para suspender)</label>
              <input className="input" style={{ width: "100%" }} value={reason} onChange={(e) => setReason(e.target.value)}
                    placeholder="Ej: reiteradas ausencias reportadas por familias" />
            </div>
          )}
          <div className="danger-row">
            <div>
              <b>Eliminar perfil</b>
              <span>Borra a la cuidadora de la Consola y su cuenta del sitio, con documentos, reseñas y puntos.</span>
            </div>
            <button className="btn danger" disabled={locked} onClick={() => setDeleting(true)}>Eliminar</button>
          </div>
          {deleting && (
            <Modal title={`¿Eliminar a ${c.name}?`} onClose={() => setDeleting(false)}>
              <p style={{ fontSize: 14, color: "var(--ac-text-secondary)", lineHeight: 1.5, marginTop: 0 }}>
                Se elimina su perfil y también su cuenta en el sitio público, con sus documentos, reseñas, chats y puntos.
                {c.is_engaged && " Hoy figura trabajando con una familia: ese trabajo también se borra."} No se puede deshacer.
              </p>
              {error && <ErrorBanner message={error} />}
              <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 14 }}>
                <button className="btn" onClick={() => setDeleting(false)} disabled={busy}>Cancelar</button>
                <button className="btn danger" onClick={deleteProfile} disabled={busy}>{busy ? "Eliminando…" : "Sí, eliminar"}</button>
              </div>
            </Modal>
          )}
        </div>
      )}
    </Drawer>
  );
}

const CATEGORY_OPTIONS: { key: ProductCategoryKey; label: string }[] = [
  { key: "mobility", label: "Movilidad" },
  { key: "monitoring", label: "Monitoreo" },
  { key: "home_safety", label: "Seguridad en el hogar" },
  { key: "daily_care", label: "Cuidado diario" },
];
const CATEGORY_LABEL: Record<string, string> = Object.fromEntries(CATEGORY_OPTIONS.map((c) => [c.key, c.label]));
// Mismas condiciones que el sitio ofrece al crear el perfil de un adulto mayor: con ellas se arma "Recomendado para tu familia".
const CONDITION_OPTIONS = [
  "Alzheimer", "Demencia", "Parkinson", "Movilidad reducida", "Posoperatorio", "Diabetes", "Hipertensión",
  "Enfermedad cardíaca", "Artrosis", "Osteoporosis", "Riesgo de caídas", "Problemas de visión",
  "Problemas de audición", "Control de medicación",
];
const EMPTY_PRODUCT: ProductInput = {
  name: "", category: "mobility", vendor: "", price_clp: null, external_url: "https://", image_url: null,
  description: "", is_sponsored: false, conditions: [], commission_pct: null, status: "published",
};

function ProductForm({ product, onClose, onSaved }: { product: ProductOut | null; onClose: () => void; onSaved: () => void }) {
  const [f, setF] = useState<ProductInput>(() => product ? {
    name: product.name, category: (product.category as ProductCategoryKey) in CATEGORY_LABEL ? (product.category as ProductCategoryKey) : "daily_care",
    vendor: product.vendor, price_clp: product.price_clp, external_url: product.external_url, image_url: product.image_url,
    description: product.description ?? "", is_sponsored: product.is_sponsored, conditions: product.conditions ?? [],
    commission_pct: product.commission_pct, status: product.status,
  } : EMPTY_PRODUCT);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const set = <K extends keyof ProductInput>(k: K, v: ProductInput[K]) => setF((prev) => ({ ...prev, [k]: v }));
  const num = (v: string) => (v === "" ? null : Number(v));

  async function save() {
    setBusy(true);
    setError(null);
    try {
      const body: ProductInput = { ...f, image_url: f.image_url?.trim() ? f.image_url.trim() : null, description: f.description?.trim() || null };
      if (product) await MarketplaceApi.patchProduct(product.id, body);
      else await MarketplaceApi.createProduct(body);
      onSaved();
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo guardar el artículo.");
    } finally {
      setBusy(false);
    }
  }

  const label = { fontSize: 12, fontWeight: 700, color: "var(--ac-text-secondary)", margin: "12px 0 4px", display: "block" } as const;
  return (
    <Modal title={product ? "Editar artículo" : "Nuevo artículo"} onClose={onClose} width={560}>
      <label style={{ ...label, marginTop: 0 }}>Nombre</label>
      <input className="input" style={{ width: "100%" }} value={f.name} onChange={(e) => set("name", e.target.value)} />
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        <div>
          <label style={label}>Categoría</label>
          <select className="select" style={{ width: "100%" }} value={f.category} onChange={(e) => set("category", e.target.value as ProductCategoryKey)}>
            {CATEGORY_OPTIONS.map((c) => <option key={c.key} value={c.key}>{c.label}</option>)}
          </select>
        </div>
        <div>
          <label style={label}>Proveedor</label>
          <input className="input" style={{ width: "100%" }} value={f.vendor} onChange={(e) => set("vendor", e.target.value)} />
        </div>
        <div>
          <label style={label}>Precio (CLP)</label>
          <input className="input" style={{ width: "100%" }} type="number" min={0} value={f.price_clp ?? ""} onChange={(e) => set("price_clp", num(e.target.value))} />
        </div>
        <div>
          <label style={label}>Comisión pactada (%)</label>
          <input className="input" style={{ width: "100%" }} type="number" min={0} max={100} step={0.5} value={f.commission_pct ?? ""}
                onChange={(e) => set("commission_pct", num(e.target.value))} />
        </div>
      </div>
      <label style={label}>Enlace a la tienda (https)</label>
      <input className="input" style={{ width: "100%" }} value={f.external_url} onChange={(e) => set("external_url", e.target.value)} />
      <label style={label}>Imagen (enlace https, opcional)</label>
      <input className="input" style={{ width: "100%" }} value={f.image_url ?? ""} onChange={(e) => set("image_url", e.target.value)} />
      <label style={label}>Descripción</label>
      <textarea className="input" style={{ width: "100%", minHeight: 70 }} value={f.description ?? ""} onChange={(e) => set("description", e.target.value)} />
      <label style={label}>Recomendar a familias que tengan registrada…</label>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
        {CONDITION_OPTIONS.map((c) => {
          const on = f.conditions.includes(c);
          return (
            <button key={c} type="button" className={`btn small${on ? " primary" : ""}`}
                    onClick={() => set("conditions", on ? f.conditions.filter((x) => x !== c) : [...f.conditions, c])}>{c}</button>
          );
        })}
      </div>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, marginTop: 14, flexWrap: "wrap" }}>
        <label style={{ fontSize: 13, display: "flex", alignItems: "center", gap: 8 }}>
          <input type="checkbox" checked={f.is_sponsored} onChange={(e) => set("is_sponsored", e.target.checked)} />
          <span><b>Patrocinado</b> por el proveedor (sale primero y con insignia «Destacado»)</span>
        </label>
        <select className="select" value={f.status} onChange={(e) => set("status", e.target.value as ProductInput["status"])}>
          <option value="published">Publicado</option>
          <option value="draft">Borrador</option>
          <option value="archived">Archivado</option>
        </select>
      </div>
      {error && <div style={{ marginTop: 12 }}><ErrorBanner message={error} /></div>}
      <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 16 }}>
        <button className="btn" onClick={onClose} disabled={busy}>Cancelar</button>
        <button className="btn primary" onClick={save} disabled={busy}>{busy ? "Guardando…" : "Guardar"}</button>
      </div>
    </Modal>
  );
}

function ProductsTab({ onChanged }: { onChanged: () => void }) {
  const list = useApi(() => MarketplaceApi.listProducts({}), []);
  const [editing, setEditing] = useState<ProductOut | "new" | null>(null);
  const [error, setError] = useState<string | null>(null);

  const totals = useMemo(() => {
    const items = list.data?.items ?? [];
    return { sponsored: items.filter((p) => p.is_sponsored).length };
  }, [list.data]);

  async function toggleSponsored(p: ProductOut) {
    setError(null);
    try {
      await MarketplaceApi.patchProduct(p.id, { is_sponsored: !p.is_sponsored });
      list.reload();
      onChanged();
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo actualizar el artículo.");
    }
  }

  return (
    <Card>
      <CardHead title="Artículos de apoyo"
        sub={`Catálogo que ven las familias en el sitio · ${totals.sponsored} patrocinado${totals.sponsored === 1 ? "" : "s"}`}
        right={<button className="btn primary" onClick={() => setEditing("new")}>+ Nuevo artículo</button>} />
      {error && <ErrorBanner message={error} />}
      {list.error && <ErrorBanner message={list.error} />}
      {list.loading && <Spinner />}
      {list.data && list.data.items.length === 0 && <EmptyState label="No hay artículos publicados." />}
      {list.data && list.data.items.length > 0 && (
        <table className="data">
          <thead>
            <tr><th>Producto</th><th>Categoría</th><th>Proveedor</th><th className="num">Precio</th><th className="num">Comisión</th>
              <th className="num">Clics 30 d</th><th>Patrocinio</th><th>Estado</th><th /></tr>
          </thead>
          <tbody>
            {list.data.items.map((p: ProductOut) => (
              <tr key={p.id}>
                <td style={{ fontWeight: 600 }}>{p.name}</td>
                <td>{CATEGORY_LABEL[p.category] ?? p.category}</td>
                <td>{p.vendor}</td>
                <td className="num">{p.price_clp != null ? fmtCLP(p.price_clp) : "—"}</td>
                <td className="num">{p.commission_pct != null ? `${p.commission_pct}%` : "—"}</td>
                <td className="num">{p.clicks_30d != null ? fmtNumber(p.clicks_30d) : "—"}</td>
                <td>
                  <button className={`btn small${p.is_sponsored ? " primary" : ""}`} onClick={() => toggleSponsored(p)}
                          title={p.is_sponsored ? "Quitar patrocinio" : "Marcar como patrocinado"}>
                    {p.is_sponsored ? "★ Destacado" : "Destacar"}
                  </button>
                </td>
                <td><StatusChip status={p.status} /></td>
                <td><button className="btn small ghost" onClick={() => setEditing(p)}>Editar</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {editing && (
        <ProductForm product={editing === "new" ? null : editing} onClose={() => setEditing(null)}
                    onSaved={() => { setEditing(null); list.reload(); onChanged(); }} />
      )}
    </Card>
  );
}
