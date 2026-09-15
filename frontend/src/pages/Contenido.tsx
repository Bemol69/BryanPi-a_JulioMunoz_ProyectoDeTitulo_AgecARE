import { useState } from "react";
import { ContentApi } from "../api/endpoints";
import { useApi } from "../hooks/useApi";
import { Card, CardHead, EmptyState, ErrorBanner, Spinner, StatusChip, fmtDateTime } from "../components/ui";

export default function Contenido() {
  const [status, setStatus] = useState("");
  const list = useApi(() => ContentApi.list({ status: status || undefined }), [status]);

  return (
    <Card>
      <CardHead
        title="Chistes y noticias para el adulto mayor"
        sub="Contenido curado que se muestra en la vista de entretenimiento"
        right={
          <select className="select" value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">Todos</option>
            <option value="draft">Borradores</option>
            <option value="published">Publicados</option>
            <option value="archived">Archivados</option>
          </select>
        }
      />
      {list.error && <ErrorBanner message={list.error} />}
      {list.loading && <Spinner />}
      {list.data && list.data.items.length === 0 && <EmptyState label="No hay contenido con ese filtro." />}
      {list.data && list.data.items.length > 0 && (
        <table className="data">
          <thead><tr><th>Título</th><th>Tipo</th><th>Autor</th><th>Estado</th><th>Actualizado</th></tr></thead>
          <tbody>
            {list.data.items.map((c) => (
              <tr key={c.id}>
                <td style={{ fontWeight: 600 }}>{c.title}</td>
                <td>{c.type === "joke" ? "Chiste" : "Noticia"}</td>
                <td>{c.created_by_name ?? "—"}</td>
                <td><StatusChip status={c.status} /></td>
                <td>{fmtDateTime(c.updated_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Card>
  );
}
