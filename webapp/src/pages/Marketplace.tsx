import { useState } from "react";
import { Link } from "react-router-dom";
import { MarketplaceApi } from "../api/endpoints";
import { useApi } from "../hooks/useApi";
import { Avatar, Chip, EmptyState, ErrorBanner, Spinner, Stars } from "../components/ui";
import type { CaregiverCard } from "../api/types";

function CaregiverTile({ c }: { c: CaregiverCard }) {
  return (
    <Link to={`/marketplace/cuidadoras/${c.profile_id}`} className={`cg-card${c.is_engaged ? " working" : ""}`}>
      <div className="cg-card-banner" />
      <div className="cg-card-top">
        <div className="cg-avatar ring"><Avatar name={c.full_name} photoUrl={c.photo_url} /></div>
        <div className="cg-badges">
          {c.is_engaged && <span className="working-badge"><i /> Trabajando</span>}
          {c.is_featured && <Chip kind="gold">⭐ Destacada</Chip>}
        </div>
      </div>
      <div className="name">{c.full_name}</div>
      <div className="headline">{c.headline ?? "—"}</div>
      <div className="cg-rating">
        {c.rating_avg != null ? (
          <><Stars rating={c.rating_avg} /> <b>{c.rating_avg.toFixed(1)}</b></>
        ) : <span className="muted">Sin reseñas todavía</span>}
        <span className="muted"> ({c.reviews_count})</span>
        {c.years_experience != null && <span className="exp-pill">{c.years_experience} años</span>}
      </div>
      <div className="meta">
        {c.zones.slice(0, 2).map((z) => <Chip key={z} kind="neutral">📍 {z}</Chip>)}
        {c.specialties.slice(0, 2).map((s) => <Chip key={s} kind="brand">{s}</Chip>)}
      </div>
      <div className="cg-card-foot">
        {c.is_engaged ? "Actualmente en servicio con una familia" : "Ver perfil y contactar"} <span>→</span>
      </div>
    </Link>
  );
}

export default function Marketplace() {
  const [q, setQ] = useState("");
  const [zone, setZone] = useState("");
  const [specialty, setSpecialty] = useState("");

  const list = useApi(() => MarketplaceApi.search({ q: q || undefined, zone: zone || undefined, specialty: specialty || undefined }), [q, zone, specialty]);

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Buscar cuidadoras</h1>
          <p>Cuidadoras verificadas por el equipo de AgeCare. Las que están en servicio aparecen marcadas.</p>
        </div>
        {list.data && <span className="result-count">{list.data.total} {list.data.total === 1 ? "cuidadora" : "cuidadoras"}</span>}
      </div>

      <div className="filters-row">
        <input placeholder="🔎  Buscar por nombre…" value={q} onChange={(e) => setQ(e.target.value)} style={{ minWidth: 220 }} />
        <input placeholder="Zona (ej. Providencia)" value={zone} onChange={(e) => setZone(e.target.value)} />
        <input placeholder="Especialidad (ej. Alzheimer)" value={specialty} onChange={(e) => setSpecialty(e.target.value)} />
      </div>

      {list.error && <ErrorBanner message={list.error} />}
      {list.loading && <Spinner />}
      {list.data && list.data.items.length === 0 && <EmptyState label="No encontramos cuidadoras con esos filtros." />}
      {list.data && list.data.items.length > 0 && (
        <div className="cg-grid">
          {list.data.items.map((c) => <CaregiverTile key={c.profile_id} c={c} />)}
        </div>
      )}
    </div>
  );
}
