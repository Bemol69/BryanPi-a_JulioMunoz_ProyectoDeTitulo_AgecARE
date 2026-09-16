import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { MarketplaceApi } from "../api/endpoints";
import { useApi } from "../hooks/useApi";
import { Avatar, Chip, ErrorBanner, Modal, OkBanner, Spinner, Stars, fmtDate } from "../components/ui";

export default function CaregiverDetail() {
  const { id } = useParams<{ id: string }>();
  const detail = useApi(() => MarketplaceApi.detail(id!), [id]);
  const [showContact, setShowContact] = useState(false);
  const [showReview, setShowReview] = useState(false);
  const [banner, setBanner] = useState<string | null>(null);

  if (detail.loading) return <div className="page"><Spinner /></div>;
  if (detail.error) return <div className="page"><ErrorBanner message={detail.error} /></div>;
  const c = detail.data;
  if (!c) return null;

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
            <div className="meta">{c.specialties.map((s) => <Chip key={s} kind="teal">{s}</Chip>)}</div>
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

          <div style={{ display: "flex", gap: 10, marginTop: 22 }}>
            <button className="btn primary" onClick={() => setShowContact(true)}>Contactar</button>
            <button className="btn ghost" onClick={() => setShowReview(true)}>Dejar reseña</button>
          </div>
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
        <ContactModal profileId={c.profile_id} onClose={() => setShowContact(false)}
                     onDone={(msg) => { setShowContact(false); setBanner(msg); }} />
      )}
      {showReview && (
        <ReviewModal profileId={c.profile_id} onClose={() => setShowReview(false)}
                    onDone={(msg) => { setShowReview(false); setBanner(msg); detail.reload(); }} />
      )}
    </div>
  );
}

function ContactModal({ profileId, onClose, onDone }: { profileId: string; onClose: () => void; onDone: (msg: string) => void }) {
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      const res = await MarketplaceApi.contact(profileId, message || undefined);
      onDone(`Listo. Puedes contactarla por ${res.contact_channel === "phone" ? "teléfono" : res.contact_channel === "whatsapp" ? "WhatsApp" : "correo"}: ${res.contact_value}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo enviar el contacto.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal title="Contactar cuidadora" onClose={onClose}>
      <div className="field">
        <label>Mensaje (opcional)</label>
        <textarea rows={4} value={message} onChange={(e) => setMessage(e.target.value)}
                  placeholder="Hola, busco apoyo para mi mamá de lunes a viernes…" />
      </div>
      {error && <ErrorBanner message={error} />}
      <button className="btn primary block" onClick={submit} disabled={busy}>
        {busy ? "Enviando…" : "Enviar solicitud de contacto"}
      </button>
    </Modal>
  );
}

function ReviewModal({ profileId, onClose, onDone }: { profileId: string; onClose: () => void; onDone: (msg: string) => void }) {
  const [rating, setRating] = useState(5);
  const [comment, setComment] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      await MarketplaceApi.review(profileId, rating, comment || undefined);
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
