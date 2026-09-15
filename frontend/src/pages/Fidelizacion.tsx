import { useMemo, useState } from "react";
import { MarketingApi, MarketplaceApi } from "../api/endpoints";
import { useApi } from "../hooks/useApi";
import {
  Card, CardHead, Chip, EmptyState, ErrorBanner, Kpi, Modal, Spinner, Stars, fmtDateTime, fmtNumber,
} from "../components/ui";
import type { CaregiverRankingItem } from "../api/types";

export default function Fidelizacion() {
  const [zone, setZone] = useState("");
  const [selected, setSelected] = useState<CaregiverRankingItem | null>(null);
  const [pointsTarget, setPointsTarget] = useState<CaregiverRankingItem | null>(null);
  const [banner, setBanner] = useState<string | null>(null);

  const dash = useApi(() => MarketingApi.dashboardSummary(30), []);
  const ranking = useApi(() => MarketplaceApi.ranking({ zone: zone || undefined, page_size: 20 }), [zone]);
  const reviews = useApi(
    () => (selected ? MarketplaceApi.listReviews(selected.caregiver_id) : Promise.resolve(null)),
    [selected?.caregiver_id]
  );

  const zones = useMemo(() => {
    const set = new Set((ranking.data?.items ?? []).map((c) => c.zone));
    return Array.from(set).sort();
  }, [ranking.data]);

  function refreshAll() {
    dash.reload();
    ranking.reload();
    reviews.reload();
  }

  return (
    <div>
      {banner && (
        <div className="card" style={{ borderColor: "var(--ac-ok-100)", background: "var(--ac-ok-100)", color: "var(--ac-ok-700)", fontWeight: 600 }}>
          ✓ {banner}
        </div>
      )}

      {dash.error && <ErrorBanner message={dash.error} />}
      {dash.loading && <Spinner label="Cargando métricas de marketing…" />}
      {dash.data && (
        <div className="kpis">
          <Kpi label="Cuidadoras activas" value={fmtNumber(dash.data.active_caregivers)} note={`${dash.data.pending_caregivers} pendientes de aprobación`} />
          <Kpi label="Puntaje promedio" value={fmtNumber(Math.round(dash.data.avg_points))} note="puntos de fidelización" />
          <Kpi label="Rating promedio" value={dash.data.avg_rating != null ? dash.data.avg_rating.toFixed(2) : "—"} note="sobre 5 estrellas" />
          <Kpi label="Reseñas (30 días)" value={fmtNumber(dash.data.reviews_last_30d)} />
          <Kpi label="Puntos otorgados (30 días)" value={fmtNumber(dash.data.points_awarded_last_30d)} />
          <Kpi label="Top de la semana" value={dash.data.top5[0]?.name ?? "—"} note={dash.data.top5[0] ? `${dash.data.top5[0].points} pts · ${dash.data.top5[0].zone}` : undefined} />
        </div>
      )}

      <div className="grid g2">
        <Card>
          <CardHead
            title="Ranking de cuidadoras"
            sub="Ordenado por puntos de fidelización · a más puntos, más prioridad en nuevos trabajos"
            right={
              <select className="select" value={zone} onChange={(e) => setZone(e.target.value)}>
                <option value="">Todas las zonas</option>
                {zones.map((z) => <option key={z} value={z}>{z}</option>)}
              </select>
            }
          />
          {ranking.error && <ErrorBanner message={ranking.error} />}
          {ranking.loading && <Spinner />}
          {ranking.data && ranking.data.items.length === 0 && <EmptyState label="No hay cuidadoras aprobadas en esta zona." />}
          {ranking.data && ranking.data.items.length > 0 && (
            <table className="data">
              <thead>
                <tr>
                  <th>#</th><th>Cuidadora</th><th>Zona</th><th className="num">Puntos</th>
                  <th className="num">Rating</th><th className="num">Reseñas</th><th></th>
                </tr>
              </thead>
              <tbody>
                {ranking.data.items.map((c) => (
                  <tr key={c.caregiver_id}>
                    <td>
                      <span className={`rank-badge${c.rank <= 3 ? ` top${c.rank}` : ""}`}>{c.rank}</span>
                    </td>
                    <td className="clickable" onClick={() => setSelected(c)} style={{ fontWeight: 600 }}>{c.name}</td>
                    <td>{c.zone}</td>
                    <td className="num" style={{ fontWeight: 700 }}>{fmtNumber(c.points)}</td>
                    <td className="num">{c.rating_avg != null ? <Stars rating={c.rating_avg} /> : "—"}</td>
                    <td className="num">{c.reviews_count}</td>
                    <td>
                      <button className="btn small" onClick={() => setPointsTarget(c)}>+ Puntos</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>

        <RegisterReviewCard
          candidates={ranking.data?.items ?? []}
          onDone={(msg) => { setBanner(msg); refreshAll(); }}
        />
      </div>

      <Card>
        <CardHead
          title={selected ? `Historial de reseñas · ${selected.name}` : "Historial de reseñas"}
          sub={selected ? `${selected.zone} · haz clic en otra fila del ranking para cambiar` : "Selecciona una cuidadora del ranking para ver sus reseñas"}
        />
        {!selected && <EmptyState label="Sin cuidadora seleccionada." />}
        {selected && reviews.loading && <Spinner />}
        {selected && reviews.error && <ErrorBanner message={reviews.error} />}
        {selected && reviews.data && reviews.data.items.length === 0 && <EmptyState label="Todavía no tiene reseñas registradas." />}
        {selected && reviews.data && reviews.data.items.length > 0 && (
          <table className="data">
            <thead>
              <tr><th>Familia</th><th>Calificación</th><th>Comentario</th><th className="num">Puntos</th><th>Trabajo</th><th>Fecha</th></tr>
            </thead>
            <tbody>
              {reviews.data.items.map((r) => (
                <tr key={r.id}>
                  <td>{r.family_name}</td>
                  <td><Stars rating={r.rating} /></td>
                  <td style={{ maxWidth: 260 }}>{r.comment ?? "—"}</td>
                  <td className="num"><Chip kind="gold">+{r.points_awarded}</Chip></td>
                  <td>{r.job_reference ?? "—"}</td>
                  <td>{fmtDateTime(r.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      {pointsTarget && (
        <AwardPointsModal
          target={pointsTarget}
          onClose={() => setPointsTarget(null)}
          onDone={(msg) => { setPointsTarget(null); setBanner(msg); refreshAll(); }}
        />
      )}
    </div>
  );
}

function RegisterReviewCard({ candidates, onDone }: { candidates: CaregiverRankingItem[]; onDone: (msg: string) => void }) {
  const [caregiverId, setCaregiverId] = useState("");
  const [familyName, setFamilyName] = useState("");
  const [rating, setRating] = useState(5);
  const [comment, setComment] = useState("");
  const [jobRef, setJobRef] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    if (!caregiverId || !familyName.trim()) {
      setError("Selecciona una cuidadora e indica el nombre de la familia.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const res = await MarketplaceApi.createReview({
        caregiver_id: caregiverId, family_name: familyName.trim(), rating,
        comment: comment.trim() || undefined, job_reference: jobRef.trim() || undefined,
      });
      onDone(`Reseña registrada: ${familyName} calificó con ${rating}★. Se otorgaron ${res.points_awarded} puntos.`);
      setFamilyName(""); setComment(""); setJobRef(""); setRating(5);
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo registrar la reseña.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <CardHead title="Registrar reseña de un trabajo" sub="Simula el paso de la familia: cierra el ciclo de fidelización y suma puntos automáticamente" />
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        <div>
          <label className="field-label" style={{ margin: "0 0 5px" }}>Cuidadora</label>
          <select className="select" style={{ width: "100%" }} value={caregiverId} onChange={(e) => setCaregiverId(e.target.value)}>
            <option value="">Selecciona una cuidadora…</option>
            {candidates.map((c) => <option key={c.caregiver_id} value={c.caregiver_id}>{c.name} · {c.zone}</option>)}
          </select>
        </div>
        <div>
          <label className="field-label" style={{ margin: "0 0 5px" }}>Nombre de la familia</label>
          <input className="input" style={{ width: "100%" }} value={familyName} onChange={(e) => setFamilyName(e.target.value)} placeholder="Familia Pérez" />
        </div>
        <div>
          <label className="field-label" style={{ margin: "0 0 5px" }}>Calificación</label>
          <div style={{ display: "flex", gap: 4 }}>
            {[1, 2, 3, 4, 5].map((n) => (
              <button key={n} type="button" className="btn small" style={{ background: n <= rating ? "var(--ac-gold-100)" : undefined, borderColor: n <= rating ? "var(--ac-gold-500)" : undefined }} onClick={() => setRating(n)}>
                {n <= rating ? "★" : "☆"}
              </button>
            ))}
            <span style={{ alignSelf: "center", fontSize: 12, color: "var(--ac-text-secondary)", marginLeft: 4 }}>
              {rating >= 4 ? "Buena reseña → bono +5 pts" : "Sin bono por buena reseña"}
            </span>
          </div>
        </div>
        <div>
          <label className="field-label" style={{ margin: "0 0 5px" }}>Comentario (opcional)</label>
          <textarea className="input" style={{ width: "100%", minHeight: 60 }} value={comment} onChange={(e) => setComment(e.target.value)} placeholder="Muy puntual y profesional…" />
        </div>
        <div>
          <label className="field-label" style={{ margin: "0 0 5px" }}>Referencia del trabajo (opcional)</label>
          <input className="input" style={{ width: "100%" }} value={jobRef} onChange={(e) => setJobRef(e.target.value)} placeholder="TRB-2026-0142" />
        </div>
        {error && <ErrorBanner message={error} />}
        <button className="btn primary" onClick={submit} disabled={busy}>
          {busy ? "Registrando…" : "Registrar reseña y otorgar puntos"}
        </button>
      </div>
    </Card>
  );
}

function AwardPointsModal({ target, onClose, onDone }: { target: CaregiverRankingItem; onClose: () => void; onDone: (msg: string) => void }) {
  const [points, setPoints] = useState(10);
  const [reason, setReason] = useState("manual");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      await MarketplaceApi.awardPoints(target.caregiver_id, { points, reason, note: note.trim() || undefined });
      onDone(`Se otorgaron ${points} puntos a ${target.name}.`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudieron otorgar los puntos.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal title={`Otorgar puntos · ${target.name}`} onClose={onClose}>
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        <div>
          <label className="field-label" style={{ margin: "0 0 5px" }}>Puntos</label>
          <input className="input" style={{ width: "100%" }} type="number" min={1} max={1000} value={points}
                onChange={(e) => setPoints(Number(e.target.value))} />
        </div>
        <div>
          <label className="field-label" style={{ margin: "0 0 5px" }}>Motivo</label>
          <select className="select" style={{ width: "100%" }} value={reason} onChange={(e) => setReason(e.target.value)}>
            <option value="manual">Bono manual</option>
            <option value="job_completed">Trabajo completado</option>
            <option value="good_review">Buena reseña</option>
          </select>
        </div>
        <div>
          <label className="field-label" style={{ margin: "0 0 5px" }}>Nota (opcional)</label>
          <textarea className="input" style={{ width: "100%", minHeight: 50 }} value={note} onChange={(e) => setNote(e.target.value)} />
        </div>
        {error && <ErrorBanner message={error} />}
        <button className="btn primary" onClick={submit} disabled={busy}>{busy ? "Otorgando…" : "Otorgar puntos"}</button>
      </div>
    </Modal>
  );
}
