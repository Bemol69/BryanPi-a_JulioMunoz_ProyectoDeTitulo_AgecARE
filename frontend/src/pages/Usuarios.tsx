import { useState } from "react";
import { RolesApi, SupportApi } from "../api/endpoints";
import { useApi } from "../hooks/useApi";
import { Card, CardHead, EmptyState, ErrorBanner, Kpi, Spinner, StatusChip, fmtNumber, fmtPct } from "../components/ui";

const ROLE_LABEL: Record<string, string> = { family: "Familiar", caregiver: "Cuidadora", elder: "Adulto mayor", doctor: "Médico" };

export default function Usuarios() {
  const roles = useApi(() => RolesApi.summary(30), []);
  const support = useApi(() => SupportApi.summary(), []);
  const [ticketStatus, setTicketStatus] = useState("open");
  const tickets = useApi(() => SupportApi.tickets({ status: ticketStatus }), [ticketStatus]);

  return (
    <div>
      {support.error && <ErrorBanner message={support.error} />}
      {support.data && (
        <div className="kpis">
          <Kpi label="Tickets abiertos" value={fmtNumber(support.data.open)} />
          <Kpi label="En progreso" value={fmtNumber(support.data.in_progress)} />
          <Kpi label="Resueltos (30d)" value={fmtNumber(support.data.resolved_30d)} />
          <Kpi label="1ª respuesta prom." value={`${support.data.first_response_hours_avg.toFixed(1)} h`} />
          <Kpi label="CSAT promedio" value={support.data.csat_avg != null ? support.data.csat_avg.toFixed(2) : "—"} note={`${support.data.csat_count} respuestas`} />
        </div>
      )}

      <Card>
        <CardHead title="Actividad por perfil" sub="Usuarios activos y retención en los últimos 30 días" />
        {roles.error && <ErrorBanner message={roles.error} />}
        {roles.loading && <Spinner />}
        {roles.data && (
          <table className="data">
            <thead><tr><th>Perfil</th><th className="num">Activos</th><th className="num">Crecimiento 8w</th><th className="num">Sesiones/semana</th><th className="num">Retención 30d</th></tr></thead>
            <tbody>
              {roles.data.roles.map((r) => (
                <tr key={r.role}>
                  <td style={{ fontWeight: 600 }}>{ROLE_LABEL[r.role] ?? r.role}</td>
                  <td className="num">{fmtNumber(r.active_users)}</td>
                  <td className="num">{fmtPct(r.growth_8w)}</td>
                  <td className="num">{r.sessions_per_week.toFixed(1)}</td>
                  <td className="num">{fmtPct(r.retention_30d)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      <Card>
        <CardHead
          title="Tickets de soporte"
          sub="Casos levantados por familias, cuidadoras y médicos"
          right={
            <select className="select" value={ticketStatus} onChange={(e) => setTicketStatus(e.target.value)}>
              <option value="open">Abiertos</option>
              <option value="in_progress">En progreso</option>
              <option value="resolved">Resueltos</option>
            </select>
          }
        />
        {tickets.error && <ErrorBanner message={tickets.error} />}
        {tickets.loading && <Spinner />}
        {tickets.data && tickets.data.items.length === 0 && <EmptyState label="No hay tickets con ese estado." />}
        {tickets.data && tickets.data.items.length > 0 && (
          <table className="data">
            <thead><tr><th>#</th><th>Asunto</th><th>Solicitante</th><th>Categoría</th><th>Prioridad</th><th>Estado</th></tr></thead>
            <tbody>
              {tickets.data.items.map((t) => (
                <tr key={t.id}>
                  <td>{t.number}</td>
                  <td style={{ fontWeight: 600 }}>{t.subject}</td>
                  <td>{t.requester.name} ({ROLE_LABEL[t.requester.role ?? ""] ?? t.requester.role ?? "—"})</td>
                  <td>{t.category}</td>
                  <td><StatusChip status={t.priority} /></td>
                  <td><StatusChip status={t.status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}
