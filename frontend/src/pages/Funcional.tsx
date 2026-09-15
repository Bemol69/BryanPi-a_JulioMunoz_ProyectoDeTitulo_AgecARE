import { FeaturesApi } from "../api/endpoints";
import { useApi } from "../hooks/useApi";
import { Card, CardHead, EmptyState, ErrorBanner, Spinner } from "../components/ui";

const ROLE_LABEL: Record<string, string> = { family: "Familiar", caregiver: "Cuidadora", elder: "Adulto mayor", doctor: "Médico" };

// Escala secuencial teal-50 -> teal-600 (Guía de Diseño 9.2: "secuenciales... escala de 6 pasos de teal-50 a teal-700")
function heatColor(v: number | null): { bg: string; fg: string } {
  if (v == null) return { bg: "var(--ac-surface-sunken)", fg: "var(--ac-text-tertiary)" };
  if (v >= 0.6) return { bg: "var(--ac-teal-600)", fg: "#fff" };
  if (v >= 0.3) return { bg: "var(--ac-teal-500)", fg: "#fff" };
  if (v >= 0.1) return { bg: "var(--ac-teal-100)", fg: "var(--ac-teal-700)" };
  return { bg: "var(--ac-teal-50)", fg: "var(--ac-text-secondary)" };
}

export default function Funcional() {
  const adoption = useApi(() => FeaturesApi.adoption(30), []);
  const alerts = useApi(() => FeaturesApi.alerts(30, 0.15), []);

  return (
    <div>
      <Card>
        <CardHead title="Matriz de adopción por función y perfil" sub="% de usuarios activos de cada perfil que usó la función en 30 días · gris = no aplica" />
        {adoption.error && <ErrorBanner message={adoption.error} />}
        {adoption.loading && <Spinner />}
        {adoption.data && (
          <div style={{ overflowX: "auto" }}>
            <table className="heat">
              <thead>
                <tr>
                  <th className="rowh">Función</th>
                  {adoption.data.roles.map((r) => <th key={r}>{ROLE_LABEL[r] ?? r}</th>)}
                </tr>
              </thead>
              <tbody>
                {adoption.data.features.map((f) => (
                  <tr key={f.feature_key}>
                    <th className="rowh">{f.name}</th>
                    {f.adoption.map((v, i) => {
                      const c = heatColor(v);
                      return (
                        <td key={i} className={v == null ? "na" : ""} style={{ background: c.bg, color: c.fg }}>
                          {v == null ? "—" : `${(v * 100).toFixed(0)}%`}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Card>
        <CardHead title="Alertas de adopción baja" sub="Funciones con uso por debajo del umbral y no marcadas como 'esperado bajo'" />
        {alerts.error && <ErrorBanner message={alerts.error} />}
        {alerts.loading && <Spinner />}
        {alerts.data && alerts.data.alerts.length === 0 && <EmptyState label="Sin alertas: todas las funciones están dentro de lo esperado." />}
        {alerts.data && alerts.data.alerts.length > 0 && (
          <ul className="flag-list">
            {alerts.data.alerts.map((a) => (
              <li key={a.feature_key}>
                <span>🔻</span>
                <div>
                  <div className="fl-t">{a.name}</div>
                  <div className="fl-s">
                    Adopción {a.adoption.map((v) => `${(v * 100).toFixed(0)}%`).join(" / ")} entre {a.roles.map((r) => ROLE_LABEL[r] ?? r).join(", ")}
                    {a.note && <> · {a.note}</>}
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
