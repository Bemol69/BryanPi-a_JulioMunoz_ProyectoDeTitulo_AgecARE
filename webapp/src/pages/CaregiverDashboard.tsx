import { useEffect, useRef, useState, type ChangeEvent } from "react";
import { CaregiverApi } from "../api/endpoints";
import { useApi } from "../hooks/useApi";
import { useAuth } from "../auth/AuthContext";
import { Avatar, Chip, EmptyState, ErrorBanner, OkBanner, Spinner, Stars, Switch, fmtDate } from "../components/ui";

const AVATAR_MAX_BYTES = 5 * 1024 * 1024;
const AVATAR_TYPES = ["image/jpeg", "image/png", "image/webp"];

const SPECIALTY_OPTIONS = [
  "Alzheimer", "Demencia", "Parkinson", "Movilidad reducida", "Posoperatorio",
  "Cuidados paliativos", "Control de medicación", "Estimulación cognitiva", "Acompañamiento",
  "Diabetes", "Hipertensión", "Oxigenoterapia", "Curación de heridas",
  "Higiene y aseo personal", "Apoyo en alimentación", "Fisioterapia básica", "Cuidado nocturno",
];
const LANGUAGE_OPTIONS = [
  "Español", "Inglés", "Portugués", "Alemán", "Italiano", "Francés",
  "Mapudungun", "Lengua de señas chilena",
];
const ZONE_OPTIONS = [
  "Santiago Centro", "Providencia", "Ñuñoa", "Las Condes", "Vitacura", "La Reina",
  "Macul", "Peñalolén", "La Florida", "Maipú", "San Miguel", "La Cisterna",
  "Estación Central", "Independencia", "Recoleta", "Quilicura", "Huechuraba",
  "Lo Barnechea", "San Bernardo", "Puente Alto", "Cerrillos", "Pudahuel",
];

function TagPicker({ label, values, onChange, options, placeholder }: {
  label: string; values: string[]; onChange: (v: string[]) => void; options: string[]; placeholder: string;
}) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const wrapRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onDocClick(e: MouseEvent) {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, []);

  const available = options.filter((o) => !values.includes(o) && o.toLowerCase().includes(query.trim().toLowerCase()));

  return (
    <div className="field tag-picker" ref={wrapRef}>
      <label>{label}</label>
      <input value={query} autoComplete="off" placeholder={placeholder}
            onChange={(e) => { setQuery(e.target.value); setOpen(true); }}
            onFocus={() => setOpen(true)} onClick={() => setOpen(true)} />
      {open && (
        <div className="tag-picker-menu">
          {available.length === 0 && <div className="tag-picker-empty">Sin coincidencias.</div>}
          {available.map((opt) => (
            <button type="button" key={opt} className="tag-picker-opt"
                    onMouseDown={(e) => e.preventDefault()}
                    onClick={() => { onChange([...values, opt]); setQuery(""); setOpen(false); }}>
              {opt}
            </button>
          ))}
        </div>
      )}
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

      {/* Ambas pestañas quedan montadas y solo se ocultan con CSS, para que lo escrito en
          "Mi perfil profesional" no se pierda al pasar a "Mensajes recibidos" y volver. */}
      <div style={{ display: tab === "perfil" ? "block" : "none" }}>
        <ProfileTab />
      </div>
      <div className="card" style={{ display: tab === "mensajes" ? "block" : "none" }}>
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
    </div>
  );
}

function AvatarPicker() {
  const { user, uploadAvatar } = useAuth();
  const inputRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onPick(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    if (!AVATAR_TYPES.includes(file.type)) {
      setError("La foto debe ser JPG, PNG o WEBP.");
      return;
    }
    if (file.size > AVATAR_MAX_BYTES) {
      setError("La foto no puede superar los 5 MB.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await uploadAvatar(file);
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo subir la foto.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="avatar-picker">
      <div className="cg-avatar">{user ? <Avatar name={user.full_name} photoUrl={user.avatar_url} /> : "?"}</div>
      <div>
        <input ref={inputRef} id="avatarInput" type="file" accept="image/jpeg,image/png,image/webp"
              onChange={onPick} disabled={busy} />
        <button type="button" className="btn ghost small" onClick={() => inputRef.current?.click()} disabled={busy}>
          {busy ? "Subiendo…" : user?.avatar_url ? "Cambiar foto" : "Agregar foto de perfil"}
        </button>
        <div style={{ fontSize: 11.5, color: "var(--ac-text-tertiary)", marginTop: 6 }}>JPG, PNG o WEBP · máx. 5 MB</div>
        {error && <div style={{ fontSize: 12, color: "var(--ac-warn-700)", marginTop: 4 }}>⚠ {error}</div>}
      </div>
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
          <label>Foto de perfil</label>
          <AvatarPicker />
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

        <TagPicker label="Especialidades" values={specialties} onChange={setSpecialties} options={SPECIALTY_OPTIONS} placeholder="Busca una especialidad…" />
        <TagPicker label="Idiomas" values={languages} onChange={setLanguages} options={LANGUAGE_OPTIONS} placeholder="Busca un idioma…" />
        <TagPicker label="Zonas de cobertura" values={zones} onChange={setZones} options={ZONE_OPTIONS} placeholder="Busca una comuna…" />

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
          <div className="cg-avatar">{user ? <Avatar name={user.full_name} photoUrl={user.avatar_url} /> : "?"}</div>
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
