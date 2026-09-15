import { OpsApi } from "../api/endpoints";
import { useApi } from "../hooks/useApi";
import { Card, CardHead, EmptyState, ErrorBanner, Kpi, Spinner, StatusChip, fmtDateTime, fmtPct } from "../components/ui";

const OVERALL_LABEL: Record<string, string> = { operational: "Operativo", degraded: "Degradado", outage: "Caído" };

export default function Operativo() {
  const status = useApi(() => OpsApi.status(), []);
  const incidents = useApi(() => OpsApi.incidents(30), []);

  return (
    <div>
      {status.error && <ErrorBanner message={status.error} />}
      {status.loading && <Spinner label="Consultando estado de los componentes…" />}
      {status.data && (
        <div className="kpis">
          <Kpi label="Estado general" value={OVERALL_LABEL[status.data.overall] ?? status.data.overall} />
          <Kpi label="Componentes monitoreados" value={String(status.data.components.length)} />
          <Kpi label="Con degradación" value={String(status.data.components.filter((c) => c.status !== "operational").length)} />
          <Kpi label="Última revisión" value={new Date(status.data.checked_at).toLocaleTimeString("es-CL")} />
        </div>
      )}

      <Card>
        <CardHead title="Componentes de la plataforma" sub="Uptime 30 días y latencia p50/p95" />
        {status.data && (
          <table className="data">
            <thead><tr><th>Componente</th><th>Estado</th><th className="num">Uptime 30d</th><th className="num">p50</th><th className="num">p95</th><th>Nota</th></tr></thead>
            <tbody>
              {status.data.components.map((c) => (
                <tr key={c.key}>
                  <td style={{ fontWeight: 600 }}>{c.name}</td>
                  <td><StatusChip status={c.status} /></td>
                  <td className="num">{fmtPct(c.uptime_30d)}</td>
                  <td className="num">{c.latency_p50_ms != null ? `${c.latency_p50_ms} ms` : "—"}</td>
                  <td className="num">{c.latency_p95_ms != null ? `${c.latency_p95_ms} ms` : "—"}</td>
                  <td style={{ color: "var(--ac-text-tertiary)", fontSize: 11.5 }}>{c.note ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      <Card>
        <CardHead title="Incidentes (últimos 30 días)" sub="Degradaciones, caídas y mantenimientos programados" />
        {incidents.error && <ErrorBanner message={incidents.error} />}
        {incidents.loading && <Spinner />}
        {incidents.data && incidents.data.items.length === 0 && <EmptyState label="Sin incidentes registrados en el periodo." />}
        {incidents.data && incidents.data.items.length > 0 && (
          <table className="data">
            <thead><tr><th>Título</th><th>Severidad</th><th>Estado</th><th>Inicio</th><th>Resolución</th></tr></thead>
            <tbody>
              {incidents.data.items.map((i) => (
                <tr key={i.id}>
                  <td style={{ fontWeight: 600 }}>{i.title}{i.is_maintenance && <span className="chip neutral" style={{ marginLeft: 6 }}>mantenimiento</span>}</td>
                  <td><StatusChip status={i.severity} /></td>
                  <td><StatusChip status={i.status} /></td>
                  <td>{fmtDateTime(i.started_at)}</td>
                  <td>{i.resolved_at ? fmtDateTime(i.resolved_at) : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}
