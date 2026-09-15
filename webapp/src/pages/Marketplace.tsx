import { useState } from "react";
import { Link } from "react-router-dom";
import { MarketplaceApi } from "../api/endpoints";
import { useApi } from "../hooks/useApi";
import { Chip, EmptyState, ErrorBanner, Initials, Spinner, Stars } from "../components/ui";

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
          <p>Cuidadoras que han publicado su perfil y están disponibles para nuevos trabajos.</p>
        </div>
      </div>

      <div className="filters-row">
        <input placeholder="Buscar por nombre…" value={q} onChange={(e) => setQ(e.target.value)} style={{ minWidth: 220 }} />
        <input placeholder="Zona (ej. Providencia)" value={zone} onChange={(e) => setZone(e.target.value)} />
        <input placeholder="Especialidad (ej. Alzheimer)" value={specialty} onChange={(e) => setSpecialty(e.target.value)} />
      </div>

      {list.error && <ErrorBanner message={list.error} />}
      {list.loading && <Spinner />}
      {list.data && list.data.items.length === 0 && <EmptyState label="No encontramos cuidadoras con esos filtros." />}
      {list.data && list.data.items.length > 0 && (
        <div className="cg-grid">
          {list.data.items.map((c) => (
            <Link to={`/marketplace/cuidadoras/${c.profile_id}`} key={c.profile_id} className="cg-card">
              {c.is_featured && <span className="featured-badge"><Chip kind="gold">⭐ Destacada</Chip></span>}
              <div className="cg-avatar"><Initials name={c.full_name} /></div>
              <div className="name">{c.full_name}</div>
              <div className="headline">{c.headline ?? "—"}</div>
              <div>{c.rating_avg != null ? <Stars rating={c.rating_avg} /> : "Sin reseñas todavía"} <span style={{ fontSize: 12, color: "var(--ac-text-tertiary)" }}>({c.reviews_count})</span></div>
              <div className="meta">
                {c.zones.slice(0, 2).map((z) => <Chip key={z} kind="neutral">{z}</Chip>)}
                {c.specialties.slice(0, 2).map((s) => <Chip key={s} kind="teal">{s}</Chip>)}
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
