import { useState } from "react";
import { CommercialApi } from "../api/endpoints";
import { useApi } from "../hooks/useApi";
import { Card, CardHead, EmptyState, ErrorBanner, Kpi, Seg, Spinner, fmtCLP, fmtNumber, fmtPct } from "../components/ui";

const PERIODS = [
  { value: "today", label: "Hoy" },
  { value: "last_7_days", label: "7 días" },
  { value: "current_month", label: "Este mes" },
  { value: "last_30_days", label: "30 días" },
  { value: "ytd", label: "Año" },
] as const;

function deltaDir(v: number | null): "up" | "down" | "flat" {
  if (v == null) return "flat";
  return v > 0 ? "up" : v < 0 ? "down" : "flat";
}
function deltaText(v: number | null): string {
  if (v == null) return "sin datos del periodo anterior";
  return `${v > 0 ? "+" : ""}${v.toFixed(1)}% vs. periodo anterior`;
}

export default function Comercial() {
  const [period, setPeriod] = useState<(typeof PERIODS)[number]["value"]>("current_month");
  const summary = useApi(() => CommercialApi.summary(period), [period]);
  const plans = useApi(() => CommercialApi.plans(), []);
  const funnel = useApi(() => CommercialApi.funnel(), []);

  return (
    <div>
      <div className="filter-row">
        <span className="filter-label">Periodo</span>
        <Seg options={PERIODS as unknown as { value: string; label: string }[]} value={period} onChange={(v) => setPeriod(v as typeof period)} />
      </div>

      {summary.error && <ErrorBanner message={summary.error} />}
      {summary.loading && <Spinner label="Cargando resumen comercial…" />}
      {summary.data && (
        <div className="kpis">
          <Kpi label="Nuevos usuarios" value={fmtNumber(summary.data.new_users)} delta={{ text: deltaText(summary.data.deltas.new_users_pct), dir: deltaDir(summary.data.deltas.new_users_pct) }} />
          <Kpi label="Descargas" value={fmtNumber(summary.data.downloads)} />
          <Kpi label="Usuarios activos" value={fmtNumber(summary.data.active_users)} delta={{ text: deltaText(summary.data.deltas.active_users_pct), dir: deltaDir(summary.data.deltas.active_users_pct) }} />
          <Kpi label="Usuarios pagadores" value={fmtNumber(summary.data.paying_users)} note={`${fmtPct(summary.data.paying_share)} del total activo`} />
          <Kpi label="MRR" value={fmtCLP(summary.data.mrr_clp)} delta={{ text: deltaText(summary.data.deltas.mrr_pct), dir: deltaDir(summary.data.deltas.mrr_pct) }} />
          <Kpi label="Tasa de baja" value={fmtPct(summary.data.churn_rate)} note={`${fmtNumber(summary.data.churned_users)} cuentas dadas de baja`} />
        </div>
      )}

      <div className="grid g2">
        <Card>
          <CardHead title="Mezcla de planes" sub="Usuarios activos por plan · hoy" />
          {plans.error && <ErrorBanner message={plans.error} />}
          {plans.loading && <Spinner />}
          {plans.data && (
            <table className="data">
              <thead><tr><th>Plan</th><th className="num">Usuarios</th><th className="num">Participación</th><th className="num">MRR</th><th className="num">Churn mensual</th></tr></thead>
              <tbody>
                {plans.data.plans.map((p) => (
                  <tr key={p.plan_code}>
                    <td style={{ fontWeight: 600 }}>{p.name}</td>
                    <td className="num">{fmtNumber(p.users)}</td>
                    <td className="num">{fmtPct(p.share)}</td>
                    <td className="num">{fmtCLP(p.mrr_clp)}</td>
                    <td className="num">{fmtPct(p.monthly_churn)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>

        <Card>
          <CardHead title="Embudo de conversión" sub="Descarga → registro → suscripción de pago" />
          {funnel.error && <ErrorBanner message={funnel.error} />}
          {funnel.loading && <Spinner />}
          {funnel.data && funnel.data.stages.length === 0 && <EmptyState label="Sin datos de embudo." />}
          {funnel.data && funnel.data.stages.length > 0 && (
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {funnel.data.stages.map((s) => (
                <div key={s.stage}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12.5, marginBottom: 4 }}>
                    <span style={{ fontWeight: 600 }}>{s.name}</span>
                    <span>{fmtNumber(s.users)} · {fmtPct(s.rate_vs_first)}</span>
                  </div>
                  <div className="progress-bar"><div style={{ width: `${Math.max(s.rate_vs_first * 100, 2)}%` }} /></div>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
