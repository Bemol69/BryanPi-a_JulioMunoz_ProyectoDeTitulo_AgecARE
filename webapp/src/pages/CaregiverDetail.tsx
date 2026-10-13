import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { MarketplaceApi, PatientsApi } from "../api/endpoints";
import { useApi } from "../hooks/useApi";
import { Avatar, Chip, ErrorBanner, Modal, OkBanner, Spinner, Stars, fmtDate } from "../components/ui";

export default function CaregiverDetail() {
  const { id } = useParams<{ id: string }>();
  const detail = useApi(() => MarketplaceApi.detail(id!), [id]);
  const [showContact, setShowContact] = useState(false);
  const [showReview, setShowReview] = useState(false);
  const [showHire, setShowHire] = useState(false);
  const navigate = useNavigate();
  const [banner, setBanner] = useState<string | null>(null);
  const [busyHire, setBusyHire] = useState(false);

  if (detail.loading) return <div className="page"><Spinner /></div>;
  if (detail.error) return <div className="page"><ErrorBanner message={detail.error} /></div>;
  const c = detail.data;
  if (!c) return null;

  const engagementId = c.my_engagement_id;
  async function cancelRequest() {
    if (!c?.my_request) return;
    setBusyHire(true);
    try {
      await MarketplaceApi.cancelRequest(c.my_request.request_id);
      setBanner("Cancelaste la solicitud de contratación.");
      detail.reload();
    } catch (e) {
      setBanner(e instanceof Error ? e.message : "No se pudo cancelar la solicitud.");
    } finally {
      setBusyHire(false);
    }
  }

  async function endEngagement() {
    if (!engagementId) return;
    setBusyHire(true);
    try {
      await MarketplaceApi.endEngagement(engagementId);
      setBanner("Diste por terminado el trabajo. Ahora puedes dejar tu reseña sobre esta cuidadora.");
      detail.reload();
    } catch (e) {
      setBanner(e instanceof Error ? e.message : "No se pudo finalizar el trabajo.");
    } finally {
      setBusyHire(false);
    }
  }

  return (
    <div className="page">
      <Link to="/marketplace" className="btn link">← Volver a la búsqueda</Link>

      {banner && <div style={{ marginTop: 16 }}><OkBanner message={banner} /></div>}

      <div className="grid2" style={{ marginTop: 20 }}>
        <div className="card">
          <div style={{ display: "flex", gap: 16, alignItems: "center", marginBottom: 16 }}>
            <div className="cg-avatar" style={{ width: 72, height: 72, fontSize: 28 }}><Avatar name={c.full_name} photoUrl={c.photo_url} /></div>
            <div>
              <h1 style={{ margin: 0, fontSize: 22 }}>{c.full_name} {c.is_featured && <Chip kind="gold">⭐ Destacada</Chip>}</h1>
              <div style={{ color: "var(--ac-text-secondary)", fontSize: 14 }}>{c.headline}</div>
              <div style={{ marginTop: 6 }}>
                {c.rating_avg != null ? <Stars rating={c.rating_avg} /> : "Sin reseñas todavía"}
                <span style={{ fontSize: 12, color: "var(--ac-text-tertiary)", marginLeft: 6 }}>({c.reviews_count} reseñas)</span>
              </div>
            </div>
          </div>

          <p style={{ fontSize: 14, lineHeight: 1.6, color: "var(--ac-text-secondary)" }}>{c.bio}</p>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginTop: 16 }}>
            <div>
              <div className="field-label" style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", color: "var(--ac-text-tertiary)", marginBottom: 6 }}>Experiencia</div>
              <div>{c.years_experience ?? "—"} años</div>
            </div>
            <div>
              <div className="field-label" style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", color: "var(--ac-text-tertiary)", marginBottom: 6 }}>Idiomas</div>
              <div>{c.languages.join(", ") || "—"}</div>
            </div>
          </div>

          <div style={{ marginTop: 16 }}>
            <div className="field-label" style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", color: "var(--ac-text-tertiary)", marginBottom: 6 }}>Especialidades</div>
            <div className="meta">{c.specialties.map((s) => <Chip key={s} kind="brand">{s}</Chip>)}</div>
          </div>
          <div style={{ marginTop: 12 }}>
            <div className="field-label" style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", color: "var(--ac-text-tertiary)", marginBottom: 6 }}>Zonas de cobertura</div>
            <div className="meta">{c.zones.map((z) => <Chip key={z} kind="neutral">{z}</Chip>)}</div>
          </div>
          {c.certifications.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <div className="field-label" style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", color: "var(--ac-text-tertiary)", marginBottom: 6 }}>Certificaciones</div>
              <ul style={{ margin: 0, paddingLeft: 18, fontSize: 13.5 }}>
                {c.certifications.map((cert, i) => (
                  <li key={i}>{cert.name}{cert.issuer ? ` · ${cert.issuer}` : ""}{cert.year ? ` (${cert.year})` : ""}</li>
                ))}
              </ul>
            </div>
          )}

          <div style={{ display: "flex", gap: 10, marginTop: 22, flexWrap: "wrap" }}>
            <button className="btn primary" onClick={() => setShowContact(true)}>
              {c.conversation_id ? "Escribirle" : "Contactar"}
            </button>
            {c.hired_by_me ? (
              <button className="btn ghost" onClick={endEngagement} disabled={busyHire}>
                {busyHire ? "Finalizando…" : "Finalizar trabajo"}
              </button>
            ) : c.my_request?.status === "pending" ? (
              <button className="btn ghost" disabled>🕒 Solicitud enviada</button>
            ) : c.is_engaged ? (
              <button className="btn ghost" disabled title="Ya está trabajando con otra familia">En servicio</button>
            ) : (
              <button className="btn ghost" onClick={() => setShowHire(true)}>Solicitar contratación</button>
            )}
            {c.can_review && <button className="btn gold" onClick={() => setShowReview(true)}>⭐ Dejar reseña</button>}
          </div>
          {c.hired_by_me && (
            <div style={{ marginTop: 10, fontSize: 12.5, color: "var(--ac-brand-700)" }}>
              ✓ Actualmente trabajando contigo · podrás dejar tu reseña cuando finalices el trabajo
            </div>
          )}
          {c.my_request?.status === "pending" && (
            <div className="request-status wait">
              <div><b>🕒 Solicitud enviada.</b> Esperando la respuesta de {c.full_name.split(" ")[0]}; el trabajo comienza cuando la acepte.</div>
              <div className="request-actions">
                {c.conversation_id && <Link to={`/mensajes/${c.conversation_id}`} className="btn small">💬 Ir al chat</Link>}
                <button className="btn small" disabled={busyHire} onClick={cancelRequest}>Cancelar solicitud</button>
              </div>
            </div>
          )}
          {c.my_request && c.my_request.status !== "pending" && (
            <div className="request-status bad">
              {c.my_request.status === "declined"
                ? "La cuidadora no aceptó tu última solicitud. Puedes escribirle o enviar otra."
                : "Tu última solicitud quedó sin efecto porque la cuidadora aceptó otro trabajo."}
            </div>
          )}
          {!c.hired_by_me && c.is_engaged && !c.my_request && (
            <div className="working-note"><i /> Está trabajando actualmente con otra familia, por eso no se puede contratar por ahora. Puedes escribirle igual.</div>
          )}
          {!c.hired_by_me && !c.can_review && !c.is_engaged && (
            <div style={{ marginTop: 10, fontSize: 12, color: "var(--ac-text-tertiary)" }}>
              Las reseñas se habilitan una vez que termina un trabajo con ella.
            </div>
          )}
        </div>

        <div className="card">
          <h3 style={{ marginTop: 0 }}>Reseñas ({c.reviews.length})</h3>
          {c.reviews.length === 0 && <p style={{ color: "var(--ac-text-tertiary)", fontSize: 13.5 }}>Todavía no tiene reseñas.</p>}
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            {c.reviews.map((r) => (
              <div key={r.review_id} style={{ borderBottom: "1px solid var(--ac-border)", paddingBottom: 12 }}>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <b style={{ fontSize: 13.5 }}>{r.author_name}</b>
                  <Stars rating={r.rating} />
                </div>
                <div style={{ fontSize: 12.5, color: "var(--ac-text-secondary)", marginTop: 4 }}>{r.comment}</div>
                <div style={{ fontSize: 11, color: "var(--ac-text-tertiary)", marginTop: 4 }}>{fmtDate(r.created_at)}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {showContact && (
        <ContactModal profileId={c.profile_id} onClose={() => setShowContact(false)} />
      )}
      {showReview && (
        <ReviewModal profileId={c.profile_id} onClose={() => setShowReview(false)}
                    onDone={(msg) => { setShowReview(false); setBanner(msg); detail.reload(); }} />
      )}
      {showHire && (
        <HireModal profileId={c.profile_id} onClose={() => setShowHire(false)}
                  onDone={(convId) => { setShowHire(false); navigate(convId ? `/mensajes/${convId}` : "/mensajes"); }} />
      )}
    </div>
  );
}

function ContactModal({ profileId, onClose }: { profileId: string; onClose: () => void }) {
  const navigate = useNavigate();
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      const res = await MarketplaceApi.contact(profileId, message || undefined);
      navigate(res.conversation_id ? `/mensajes/${res.conversation_id}` : "/mensajes");
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo enviar el mensaje.");
      setBusy(false);
    }
  }

  return (
    <Modal title="Escribirle a la cuidadora" onClose={onClose}>
      <div className="field">
        <label>Tu mensaje</label>
        <textarea rows={4} value={message} onChange={(e) => setMessage(e.target.value)}
                  placeholder="Hola, busco apoyo para mi mamá de lunes a viernes…" />
      </div>
      <div className="retention-note" style={{ marginBottom: 14 }}>
        🕒 La conversación se abre dentro de AgeCare y los mensajes se <b>eliminan automáticamente a los 7 días</b>.
      </div>
      {error && <ErrorBanner message={error} />}
      <button className="btn primary block" onClick={submit} disabled={busy}>
        {busy ? "Abriendo chat…" : "Enviar y abrir chat"}
      </button>
    </Modal>
  );
}

function PatientPicker({ patientId, onChange }: { patientId: string; onChange: (id: string) => void }) {
  const patients = useApi(() => PatientsApi.list(), []);
  if (!patients.data || patients.data.items.length <= 1) return null;
  return (
    <div className="field">
      <label>¿Sobre qué familiar es esto?</label>
      <select value={patientId} onChange={(e) => onChange(e.target.value)}>
        {patients.data.items.map((p) => <option key={p.patient_id} value={p.patient_id}>{p.full_name}</option>)}
      </select>
    </div>
  );
}

function ReviewModal({ profileId, onClose, onDone }: { profileId: string; onClose: () => void; onDone: (msg: string) => void }) {
  const [rating, setRating] = useState(5);
  const [comment, setComment] = useState("");
  const [patientId, setPatientId] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      await MarketplaceApi.review(profileId, rating, comment || undefined, patientId || undefined);
      onDone("¡Gracias! Tu reseña se publicó.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo registrar la reseña.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal title="Dejar una reseña" onClose={onClose}>
      <div className="field">
        <label>Calificación</label>
        <div style={{ display: "flex", gap: 4 }}>
          {[1, 2, 3, 4, 5].map((n) => (
            <button key={n} type="button" className="btn small" style={{ background: n <= rating ? "var(--ac-gold-100)" : undefined, borderColor: n <= rating ? "var(--ac-gold-500)" : "var(--ac-border)" }} onClick={() => setRating(n)}>
              {n <= rating ? "★" : "☆"}
            </button>
          ))}
        </div>
      </div>
      <PatientPicker patientId={patientId} onChange={setPatientId} />
      <div className="field">
        <label>Comentario (opcional)</label>
        <textarea rows={4} value={comment} onChange={(e) => setComment(e.target.value)} placeholder="Muy puntual y atenta…" />
      </div>
      {error && <ErrorBanner message={error} />}
      <button className="btn primary block" onClick={submit} disabled={busy}>
        {busy ? "Enviando…" : "Publicar reseña"}
      </button>
    </Modal>
  );
}

function HireModal({ profileId, onClose, onDone }: { profileId: string; onClose: () => void; onDone: (conversationId: string | null) => void }) {
  const [patientId, setPatientId] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      const res = await MarketplaceApi.requestHire(profileId, patientId || undefined, message.trim() || undefined);
      onDone(res.conversation_id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo enviar la solicitud.");
      setBusy(false);
    }
  }

  return (
    <Modal title="Solicitar contratación" onClose={onClose}>
      <p style={{ fontSize: 13.5, color: "var(--ac-text-secondary)", marginTop: 0 }}>
        Le enviaremos tu solicitud a la cuidadora. El trabajo comienza cuando ella la <b>acepte</b>, y podrán
        conversar por el chat mientras tanto.
      </p>
      <PatientPicker patientId={patientId} onChange={setPatientId} />
      <div className="field">
        <label>Mensaje (opcional)</label>
        <textarea rows={3} value={message} onChange={(e) => setMessage(e.target.value)}
                  placeholder="Necesito apoyo de lunes a viernes por las mañanas…" />
      </div>
      <div className="retention-note" style={{ marginBottom: 14 }}>
        🕒 Los mensajes del chat se eliminan automáticamente a los 7 días.
      </div>
      {error && <ErrorBanner message={error} />}
      <button className="btn primary block" onClick={submit} disabled={busy}>
        {busy ? "Enviando…" : "Enviar solicitud"}
      </button>
    </Modal>
  );
}
