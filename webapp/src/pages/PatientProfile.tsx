import { Link, useParams } from "react-router-dom";
import { PatientsApi } from "../api/endpoints";
import { useApi } from "../hooks/useApi";
import { Avatar, Chip, EmptyState, ErrorBanner, Spinner, fmtDate } from "../components/ui";
import type { PatientDetail } from "../api/types";

const SEX_LABEL: Record<string, string> = { female: "Mujer", male: "Hombre", other: "Otro" };

function TagList({ items, kind, empty }: { items: string[]; kind: "brand" | "gold" | "neutral"; empty: string }) {
  if (items.length === 0) return <span className="muted">{empty}</span>;
  return <div className="chip-row">{items.map((x) => <Chip key={x} kind={kind}>{x}</Chip>)}</div>;
}

function CareStatus({ p }: { p: PatientDetail }) {
  if (p.caregiver) {
    return (
      <div className="care-status on">
        <div className="care-dot" />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="care-title">Con cuidadora asignada</div>
          <div className="care-sub">
            <Link to={`/marketplace/cuidadoras/${p.caregiver.profile_id}`} className="care-link">{p.caregiver.full_name}</Link>
            {" "}· desde el {fmtDate(p.caregiver.started_at)}
          </div>
        </div>
        <div className="cg-avatar mini"><Avatar name={p.caregiver.full_name} photoUrl={p.caregiver.photo_url} /></div>
      </div>
    );
  }
  return (
    <div className="care-status">
      <div className="care-dot" />
      <div style={{ flex: 1 }}>
        <div className="care-title">Sin cuidadora asignada</div>
        <div className="care-sub">Busca una cuidadora verificada para acompañar a {p.full_name.split(" ")[0]}.</div>
      </div>
      <Link to="/marketplace" className="btn primary small">Buscar cuidadoras</Link>
    </div>
  );
}

export default function PatientProfile() {
  const { id } = useParams<{ id: string }>();
  const patient = useApi(() => PatientsApi.detail(id!), [id]);

  if (patient.loading) return <div className="page"><Spinner /></div>;
  if (patient.error) return <div className="page"><Link to="/familia" className="btn link">← Mis familiares</Link><ErrorBanner message={patient.error} /></div>;
  const p = patient.data;
  if (!p) return null;
  const firstName = p.full_name.split(" ")[0];

  return (
    <div className="page">
      <Link to="/familia" className="btn link">← Mis familiares</Link>

      <div className="patient-hero">
        <div className="patient-hero-avatar"><Avatar name={p.full_name} photoUrl={p.photo_url} /></div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <h1>{p.full_name}</h1>
          <div className="patient-hero-meta">
            <span>{p.age} años</span>
            {p.sex && <span>{SEX_LABEL[p.sex] ?? p.sex}</span>}
            <span>Nació el {fmtDate(p.birth_date)}</span>
          </div>
        </div>
      </div>

      <div className="grid2" style={{ marginTop: 20 }}>
        <div className="card">
          <h3>Estado actual</h3>
          <CareStatus p={p} />
          <div className="wellbeing">
            <div>
              <div className="field-label" style={{ margin: 0 }}>Semáforo de bienestar</div>
              <div style={{ fontSize: 13, color: "var(--ac-text-secondary)", marginTop: 4 }}>
                Llegará con el módulo de salud del proyecto AgeCare.
              </div>
            </div>
            <div className="traffic"><i className="g" /><i /><i /></div>
          </div>
        </div>

        <div className="card">
          <h3>Salud de {firstName}</h3>
          <div className="info-block">
            <div className="field-label">Condiciones</div>
            <TagList items={p.conditions} kind="brand" empty="Sin condiciones registradas." />
          </div>
          <div className="info-block">
            <div className="field-label">Alergias a medicamentos</div>
            <TagList items={p.medication_allergies} kind="gold" empty="Sin alergias registradas." />
          </div>
          <div className="info-block">
            <div className="field-label">Alimentos que le caen mal</div>
            <TagList items={p.food_allergies} kind="gold" empty="Sin restricciones registradas." />
          </div>
        </div>
      </div>

      <div className="card" style={{ marginTop: 20 }}>
        <h3>Notas generales</h3>
        {p.notes ? <p className="notes">{p.notes}</p> : <EmptyState label="Todavía no hay notas sobre este perfil." />}
      </div>
    </div>
  );
}
