import { useState } from "react";
import { ModerationApi } from "../api/endpoints";
import { useApi } from "../hooks/useApi";
import { Card, CardHead, EmptyState, ErrorBanner, Spinner } from "../components/ui";

export default function Moderacion() {
  const queue = useApi(() => ModerationApi.queue("pending"), []);
  const [busyId, setBusyId] = useState<string | null>(null);

  async function approve(id: string) {
    setBusyId(id);
    try { await ModerationApi.approve(id); queue.reload(); } finally { setBusyId(null); }
  }
  async function reject(id: string) {
    setBusyId(id);
    try { await ModerationApi.reject(id, "other", "Rechazado desde la consola."); queue.reload(); } finally { setBusyId(null); }
  }

  return (
    <Card>
      <CardHead title="Cola de moderación" sub="Reseñas, fotos y perfiles reportados pendientes de revisión" />
      {queue.error && <ErrorBanner message={queue.error} />}
      {queue.loading && <Spinner />}
      {queue.data && queue.data.items.length === 0 && <EmptyState label="No hay elementos pendientes de moderación." />}
      {queue.data && queue.data.items.length > 0 && (
        <table className="data">
          <thead><tr><th>Tipo</th><th>Autor</th><th>Contenido</th><th>Motivo de reporte</th><th></th></tr></thead>
          <tbody>
            {queue.data.items.map((m) => (
              <tr key={m.id}>
                <td>{m.type}</td>
                <td>{m.author.name as string} {m.author.role ? `(${m.author.role})` : ""}</td>
                <td style={{ maxWidth: 280, wordBreak: "break-word", fontSize: 11.5, color: "var(--ac-text-secondary)" }}>{JSON.stringify(m.content)}</td>
                <td>{m.report_reason ?? "—"}</td>
                <td style={{ display: "flex", gap: 6 }}>
                  <button className="btn small primary" disabled={busyId === m.id} onClick={() => approve(m.id)}>Aprobar</button>
                  <button className="btn small danger" disabled={busyId === m.id} onClick={() => reject(m.id)}>Rechazar</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Card>
  );
}
