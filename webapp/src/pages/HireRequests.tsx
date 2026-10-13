import { useState } from "react";
import { Link } from "react-router-dom";
import { CaregiverApi } from "../api/endpoints";
import { useApi } from "../hooks/useApi";
import { Chip, EmptyState, ErrorBanner, OkBanner, Spinner, fmtDate } from "../components/ui";
import type { HireRequestStatus, ReceivedHireRequest } from "../api/types";

const STATUS_LABEL: Record<HireRequestStatus, { text: string; cls: string }> = {
  pending: { text: "Por responder", cls: "pending" },
  accepted: { text: "✓ Aceptada", cls: "ok" },
  declined: { text: "Rechazada", cls: "bad" },
  cancelled: { text: "Cancelada", cls: "none" },
  unavailable: { text: "Sin efecto (aceptaste otro trabajo)", cls: "none" },
};

function RequestCard({ r, busy, canAccept, onAccept, onDecline }: {
  r: ReceivedHireRequest; busy: boolean; canAccept: boolean;
  onAccept: () => void; onDecline: () => void;
}) {
  const st = STATUS_LABEL[r.status];
  return (
    <div className={`hire-card${r.status === "pending" ? " pending" : ""}`}>
      <div className="hire-card-top">
        <div>
          <div className="hire-family">{r.family_name}</div>
          <div className="muted">Solicitud de {r.contact_name} · {fmtDate(r.created_at)}</div>
        </div>
        <span className={`doc-chip ${st.cls}`}>{st.text}</span>
      </div>

      {r.patient_name && (
        <div className="hire-patient">
          <div className="field-label" style={{ margin: "0 0 6px" }}>Persona a cuidar</div>
          <b>{r.patient_name}</b>{r.patient_age != null ? ` · ${r.patient_age} años` : ""}
          <div className="chip-row" style={{ marginTop: 8 }}>
            {r.conditions.map((c) => <Chip key={c} kind="brand">{c}</Chip>)}
            {r.medication_allergies.map((a) => <Chip key={a} kind="gold">💊 {a}</Chip>)}
            {r.food_allergies.map((a) => <Chip key={a} kind="gold">🍽 {a}</Chip>)}
          </div>
        </div>
      )}

      {r.message && <div className="hire-message">“{r.message}”</div>}

      <div className="request-actions">
        {r.status === "pending" && (
          <>
            <button className="btn primary small" disabled={busy || !canAccept} onClick={onAccept}>Aceptar solicitud</button>
            <button className="btn small" disabled={busy} onClick={onDecline}>Rechazar</button>
          </>
        )}
        {r.conversation_id && <Link to={`/mensajes/${r.conversation_id}`} className="btn small">💬 Chatear</Link>}
      </div>
      {r.status === "pending" && !canAccept && (
        <div className="muted" style={{ marginTop: 8 }}>Ya tienes un trabajo activo: termínalo para poder aceptar otra solicitud.</div>
      )}
    </div>
  );
}

export default function HireRequests() {
  const reqs = useApi(() => CaregiverApi.hireRequests(), []);
  const working = useApi(() => CaregiverApi.engagement(), []);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);

  async function act(fn: () => Promise<unknown>, message: string) {
    setBusy(true);
    setError(null);
    setOk(null);
    try {
      await fn();
      setOk(message);
      reqs.reload();
      working.reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo completar la acción.");
    } finally {
      setBusy(false);
    }
  }

  const items = reqs.data?.items ?? [];
  const canAccept = !working.data;

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Solicitudes de contratación</h1>
          <p>Familias que quieren contratarte. El trabajo comienza cuando aceptas la solicitud.</p>
        </div>
        <Link to="/mensajes" className="btn ghost">💬 Mis mensajes</Link>
      </div>

      {working.data && (
        <OkBanner message={`Actualmente trabajando con ${working.data.family_name}${working.data.patient_name ? ` · cuidando a ${working.data.patient_name}` : ""}`} />
      )}
      {ok && <OkBanner message={ok} />}
      {(error || reqs.error) && <ErrorBanner message={(error ?? reqs.error)!} />}
      {reqs.loading && <Spinner />}
      {!reqs.loading && items.length === 0 && (
        <EmptyState label="Todavía no tienes solicitudes. Cuando una familia quiera contratarte, aparecerá aquí." />
      )}
      <div className="hire-list">
        {items.map((r) => (
          <RequestCard key={r.request_id} r={r} busy={busy} canAccept={canAccept}
                       onAccept={() => act(() => CaregiverApi.acceptRequest(r.request_id), "¡Aceptaste la solicitud! Ya estás en servicio y puedes coordinar por el chat.")}
                       onDecline={() => act(() => CaregiverApi.declineRequest(r.request_id), "Rechazaste la solicitud.")} />
        ))}
      </div>
    </div>
  );
}
