import { useState } from "react";
import { MarketplaceApi } from "../api/endpoints";
import type { CaregiverReviewOut } from "../api/types";
import { useApi } from "../hooks/useApi";
import { Chip, EmptyState, ErrorBanner, Modal, Spinner, Stars, fmtDateTime } from "./ui";

/** Calificaciones de una cuidadora, una por una, con acciones del staff: archivar (reversible) o eliminar. */
export default function ReviewsManager({ caregiverId, onChanged }: { caregiverId: string; onChanged?: () => void }) {
  const [page, setPage] = useState(1);
  const [showArchived, setShowArchived] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [toDelete, setToDelete] = useState<CaregiverReviewOut | null>(null);
  const reviews = useApi(() => MarketplaceApi.listReviews(caregiverId, page), [caregiverId, page]);

  async function run(r: CaregiverReviewOut, action: () => Promise<unknown>) {
    setBusyId(r.id);
    setError(null);
    try {
      await action();
      setToDelete(null);
      reviews.reload();
      onChanged?.();
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo completar la acción.");
    } finally {
      setBusyId(null);
    }
  }

  const all = reviews.data?.items ?? [];
  const items = showArchived ? all : all.filter((r) => !r.archived_at);
  const archivedCount = all.filter((r) => r.archived_at).length;
  const totalPages = reviews.data ? Math.max(1, Math.ceil(reviews.data.total / reviews.data.page_size)) : 1;

  return (
    <div className="reviews-manager">
      {archivedCount > 0 && (
        <label className="reviews-toggle">
          <input type="checkbox" checked={showArchived} onChange={(e) => setShowArchived(e.target.checked)} />
          Mostrar archivadas ({archivedCount})
        </label>
      )}
      {error && <ErrorBanner message={error} />}
      {reviews.loading && <Spinner />}
      {reviews.error && <ErrorBanner message={reviews.error} />}
      {reviews.data && items.length === 0 && <EmptyState label="Todavía no tiene reseñas registradas." />}
      {items.map((r) => (
        <div key={r.id} className={`review-item${r.archived_at ? " archived" : ""}${r.rating <= 2 ? " bad" : ""}`}>
          <div className="review-top">
            <Stars rating={r.rating} />
            <b>{r.family_name}</b>
            <Chip kind={r.points_awarded < 0 ? "crit" : "gold"}>{r.points_awarded > 0 ? "+" : ""}{r.points_awarded} pts</Chip>
            {r.archived_at && <Chip kind="neutral">Archivada</Chip>}
            <span className="review-date">{fmtDateTime(r.created_at)}</span>
          </div>
          {r.comment && <p className="review-comment">«{r.comment}»</p>}
          {r.archived_at && (
            <div className="review-meta">Archivada{r.archived_by_name ? ` por ${r.archived_by_name}` : ""} · no cuenta para la nota ni los puntos</div>
          )}
          <div className="review-actions">
            {r.archived_at ? (
              <button className="btn small" disabled={busyId === r.id}
                      onClick={() => run(r, () => MarketplaceApi.archiveReview(r.id, false))}>Restaurar</button>
            ) : (
              <button className="btn small" disabled={busyId === r.id}
                      onClick={() => run(r, () => MarketplaceApi.archiveReview(r.id, true))}>Archivar</button>
            )}
            <button className="btn small danger" disabled={busyId === r.id} onClick={() => setToDelete(r)}>Eliminar</button>
          </div>
        </div>
      ))}
      {totalPages > 1 && (
        <div className="reviews-pager">
          <button className="btn small" disabled={page <= 1} onClick={() => setPage(page - 1)}>← Anterior</button>
          <span>Página {page} de {totalPages}</span>
          <button className="btn small" disabled={page >= totalPages} onClick={() => setPage(page + 1)}>Siguiente →</button>
        </div>
      )}

      {toDelete && (
        <Modal title="¿Eliminar esta reseña?" onClose={() => setToDelete(null)}>
          <p style={{ fontSize: 14, color: "var(--ac-text-secondary)", lineHeight: 1.5, marginTop: 0 }}>
            Se borra la reseña de {toDelete.family_name} ({toDelete.rating}★), también del sitio público, junto con los puntos que dio o quitó.
            No se puede deshacer. Si solo quieres ocultarla, usa «Archivar».
          </p>
          {error && <ErrorBanner message={error} />}
          <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 14 }}>
            <button className="btn" onClick={() => setToDelete(null)} disabled={busyId !== null}>Cancelar</button>
            <button className="btn danger" disabled={busyId !== null}
                    onClick={() => run(toDelete, () => MarketplaceApi.deleteReview(toDelete.id))}>
              {busyId ? "Eliminando…" : "Sí, eliminar"}
            </button>
          </div>
        </Modal>
      )}
    </div>
  );
}
