import { useEffect, useState } from "react";
import { CaregiverApi } from "../api/endpoints";
import { useApi } from "../hooks/useApi";
import { useAuth } from "../auth/AuthContext";
import { Chip, EmptyState, ErrorBanner, Initials, OkBanner, Spinner, Stars, Switch, fmtDate } from "../components/ui";

function TagEditor({ label, values, onChange, placeholder }: { label: string; values: string[]; onChange: (v: string[]) => void; placeholder: string }) {
  const [draft, setDraft] = useState("");
  function add() {
    const v = draft.trim();
    if (v && !values.includes(v)) onChange([...values, v]);
    setDraft("");
  }
  return (
    <div className="field">
      <label>{label}</label>
      <div style={{ display: "flex", gap: 8 }}>
        <input value={draft} onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); add(); } }}
              placeholder={placeholder} />
        <button type="button" className="btn ghost small" onClick={add}>Agregar</button>
      </div>
      <div className="tag-input-list">
        {values.map((v) => (
          <span key={v} className="tag-pill">{v} <button type="button" onClick={() => onChange(values.filter((x) => x !== v))}>✕</button></span>
        ))}
      </div>
    </div>
  );
}

export default function CaregiverDashboard() {
  const [tab, setTab] = useState<"perfil" | "mensajes">("perfil");
  const contacts = useApi(() => CaregiverApi.contacts(), [tab]);

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>{tab === "perfil" ? "Mi perfil profesional" : "Mensajes recibidos"}</h1>
          <p>{tab === "perfil" ? "Así te ven las familias que buscan cuidadoras en el marketplace." : "Familias que pidieron contactarte desde el marketplace."}</p>
        </div>
      </div>

      <div className="tabs">
        <button className={tab === "perfil" ? "on" : ""} onClick={() => setTab("perfil")}>Mi perfil profesional</button>
        <button className={tab === "mensajes" ? "on" : ""} onClick={() => setTab("mensajes")}>
          Mensajes recibidos{contacts.data && contacts.data.total > 0 ? ` (${contacts.data.total})` : ""}
        </button>
      </div>

      {tab === "perfil" ? <ProfileTab /> : (
        <div className="card">
          {contacts.error && <ErrorBanner message={contacts.error} />}
          {contacts.loading && <Spinner />}
          {contacts.data && contacts.data.items.length === 0 && (
            <EmptyState label="Todavía no has recibido mensajes. Cuando una familia te contacte desde el marketplace, aparecerá aquí." />
          )}
          {contacts.data && contacts.data.items.length > 0 && (
            <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              {contacts.data.items.map((c) => (
                <div key={c.contact_id} style={{ borderBottom: "1px solid var(--ac-border)", paddingBottom: 14 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: 8 }}>
                    <b style={{ fontSize: 14 }}>{c.family_name}</b>
                    <span style={{ fontSize: 12, color: "var(--ac-text-tertiary)" }}>{fmtDate(c.created_at)}</span>
                  </div>
                  <div style={{ fontSize: 12.5, color: "var(--ac-text-secondary)", marginTop: 4 }}>{c.family_email}</div>
                  {c.message && <div style={{ fontSize: 13.5, marginTop: 8 }}>{c.message}</div>}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function ProfileTab() {
  const { user } = useAuth();
  const profile = useApi(() => CaregiverApi.myProfile(), []);
  const [headline, setHeadline] = useState("");
  const [bio, setBio] = useState("");
  const [years, setYears] = useState<number | "">("");
  const [specialties, setSpecialties] = useState<string[]>([]);
  const [languages, setLanguages] = useState<string[]>([]);
  const [zones, setZones] = useState<string[]>([]);
  const [isListed, setIsListed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState<"listed" | "hidden" | null>(null);

  useEffect(() => {
    if (!profile.data) return;
    setHeadline(profile.data.headline ?? "");
    setBio(profile.data.bio ?? "");
    setYears(profile.data.years_experience ?? "");
    setSpecialties(profile.data.specialties);
    setLanguages(profile.data.languages);
    setZones(profile.data.zones);
    setIsListed(profile.data.is_listed);
  }, [profile.data]);

  async function save(publish?: boolean) {
    setBusy(true);
    setError(null);
    setSaved(null);
    try {
      const nextListed = publish !== undefined ? publish : isListed;
      await CaregiverApi.updateProfile({
        headline: headline || undefined, bio: bio || undefined,
        years_experience: years === "" ? undefined : Number(years),
        specialties, languages, zones, is_listed: nextListed,
      });
      setIsListed(nextListed);
      setSaved(nextListed ? "listed" : "hidden");
      profile.reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo guardar el perfil.");
    } finally {
      setBusy(false);
    }
  }

  if (profile.loading) return <Spinner />;

  return (
    <div className="grid2">
      <div className="card">
        <div className="toggle-row" style={{ marginBottom: 20, borderColor: isListed ? "var(--ac-border)" : "var(--ac-warn-500)" }}>
          <div>
            <div style={{ fontWeight: 700, fontSize: 14, color: isListed ? "var(--ac-text-primary)" : "var(--ac-warn-700)" }}>
              {isListed ? "✓ Visible en el marketplace" : "● Oculto — no apareces en las búsquedas"}
            </div>
            <div style={{ fontSize: 12, color: "var(--ac-text-tertiary)" }}>
              {isListed ? "Las familias pueden encontrarte y contactarte." : "Actívalo para que las familias te encuentren."}
            </div>
          </div>
          <Switch checked={isListed} onChange={(v) => save(v)} />
        </div>

        <div className="field">
          <label>Título profesional</label>
          <input value={headline} onChange={(e) => setHeadline(e.target.value)} placeholder="Cuidadora certificada · 8 años de experiencia" />
        </div>
        <div className="field">
          <label>Presentación</label>
          <textarea rows={4} value={bio} onChange={(e) => setBio(e.target.value)}
                    placeholder="Cuéntales a las familias sobre tu experiencia y tu forma de trabajar…" />
        </div>
        <div className="field">
          <label>Años de experiencia</label>
          <input type="number" min={0} max={60} value={years} onChange={(e) => setYears(e.target.value === "" ? "" : Number(e.target.value))} />
        </div>

        <TagEditor label="Especialidades" values={specialties} onChange={setSpecialties} placeholder="Alzheimer, movilidad reducida…" />
        <TagEditor label="Idiomas" values={languages} onChange={setLanguages} placeholder="Español, inglés…" />
        <TagEditor label="Zonas de cobertura" values={zones} onChange={setZones} placeholder="Providencia, Ñuñoa…" />

        {error && <ErrorBanner message={error} />}
        {saved === "listed" && <OkBanner message="Perfil guardado y publicado — ya apareces en el marketplace." />}
        {saved === "hidden" && (
          <div className="error-banner" style={{ background: "var(--ac-warn-100)", borderLeftColor: "var(--ac-warn-500)", color: "var(--ac-warn-700)" }}>
            ⚠ Perfil guardado, pero sigue oculto. Activa "Visible en el marketplace" arriba para que las familias te encuentren.
          </div>
        )}
        <button className="btn primary" onClick={() => save()} disabled={busy}>
          {busy ? "Guardando…" : "Guardar cambios"}
        </button>
      </div>

      <div className="card">
        <h3 style={{ marginTop: 0, fontSize: 13, textTransform: "uppercase", letterSpacing: ".04em", color: "var(--ac-text-tertiary)" }}>
          Vista previa
        </h3>
        <div className="cg-card" style={{ border: "1px solid var(--ac-border)" }}>
          <div className="cg-avatar">{user ? <Initials name={user.full_name} /> : "?"}</div>
          <div className="name">{user?.full_name ?? "Tu perfil"}</div>
          <div className="headline">{headline || "Agrega un título profesional…"}</div>
          <div>{profile.data?.rating_avg != null ? <Stars rating={profile.data.rating_avg} /> : "Sin reseñas todavía"}
            <span style={{ fontSize: 12, color: "var(--ac-text-tertiary)", marginLeft: 6 }}>({profile.data?.reviews_count ?? 0})</span>
          </div>
          <div className="meta">
            {zones.slice(0, 2).map((z) => <Chip key={z} kind="neutral">{z}</Chip>)}
            {specialties.slice(0, 2).map((s) => <Chip key={s} kind="teal">{s}</Chip>)}
          </div>
        </div>
        <p style={{ fontSize: 12, color: "var(--ac-text-tertiary)", marginTop: 14 }}>
          {isListed ? "Así aparece tu tarjeta en la búsqueda del marketplace para las familias." : "Vista previa de cómo se vería — todavía no es visible para las familias."}
        </p>
      </div>
    </div>
  );
}
