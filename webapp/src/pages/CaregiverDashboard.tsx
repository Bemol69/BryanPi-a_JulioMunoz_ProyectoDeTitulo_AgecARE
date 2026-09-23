import { useEffect, useRef, useState, type ChangeEvent } from "react";
import { CaregiverApi } from "../api/endpoints";
import { useApi } from "../hooks/useApi";
import { useAuth } from "../auth/AuthContext";
import { Avatar, Chip, EmptyState, ErrorBanner, OkBanner, Spinner, Stars, Switch, fmtDate } from "../components/ui";
import type { CaregiverDocType, CaregiverDocumentOut, CaregiverProfileOut, Engagement } from "../api/types";

const AVATAR_MAX_BYTES = 5 * 1024 * 1024;
const AVATAR_TYPES = ["image/jpeg", "image/png", "image/webp"];

const DOCUMENT_MAX_BYTES = 8 * 1024 * 1024;
const DOCUMENT_TYPES_ACCEPT = "application/pdf,image/jpeg,image/png";
const DOCUMENT_MIME_TYPES = ["application/pdf", "image/jpeg", "image/png"];
const DOCUMENT_TYPES: { key: CaregiverDocType; label: string; hint: string }[] = [
  { key: "id_card", label: "Cédula de identidad", hint: "Frente y reverso, en un solo archivo si es posible." },
  { key: "background_check", label: "Certificado de antecedentes", hint: "Emitido por el Registro Civil, con menos de 6 meses de antigüedad." },
  { key: "certificate", label: "Certificado o diploma de curso", hint: "Cuidado de adultos mayores, enfermería, primeros auxilios, etc." },
];

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

function DocumentRow({ type, label, hint, doc, onUploaded }: {
  type: CaregiverDocType; label: string; hint: string; doc: CaregiverDocumentOut | undefined;
  onUploaded: () => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onPick(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    if (!DOCUMENT_MIME_TYPES.includes(file.type)) {
      setError("El documento debe ser PDF, JPG o PNG.");
      return;
    }
    if (file.size > DOCUMENT_MAX_BYTES) {
      setError("El documento no puede superar los 8 MB.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await CaregiverApi.uploadDocument(type, file);
      onUploaded();
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo subir el documento.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="doc-row">
      <div>
        <div className="doc-row-label">{label}</div>
        <div className="doc-row-hint">{hint}</div>
        {doc ? (
          <div className="doc-row-file">
            <a href={doc.file_url} target="_blank" rel="noreferrer">{doc.original_filename}</a>
            <span className="doc-row-date"> · subido {fmtDate(doc.uploaded_at)}</span>
          </div>
        ) : (
          <div className="doc-row-missing">Todavía no subes este documento.</div>
        )}
        {error && <div style={{ fontSize: 12, color: "var(--ac-warn-700)", marginTop: 4 }}>⚠ {error}</div>}
      </div>
      <div>
        <input ref={inputRef} type="file" accept={DOCUMENT_TYPES_ACCEPT} onChange={onPick} disabled={busy} style={{ display: "none" }} />
        <button type="button" className="btn ghost small" onClick={() => inputRef.current?.click()} disabled={busy}>
          {busy ? "Subiendo…" : doc ? "Reemplazar" : "Subir"}
        </button>
      </div>
    </div>
  );
}

type DocsState = { data: CaregiverDocumentOut[] | null; loading: boolean; error: string | null; reload: () => void };

function IdentityPanel({ docs }: { docs: DocsState }) {
  const byType = new Map((docs.data ?? []).map((d) => [d.doc_type, d]));

  return (
    <div className="card">
      <h3 style={{ marginTop: 0 }}>Foto y documentos</h3>
      <p style={{ fontSize: 12.5, color: "var(--ac-text-secondary)", marginTop: -6, marginBottom: 18 }}>
        Tu foto se muestra en el marketplace. Los documentos los revisa el staff de AgeCare antes de aprobar tu perfil.
      </p>

      <div className="field">
        <label>Foto de perfil</label>
        <AvatarPicker />
      </div>

      <div className="identity-divider" />

      <label style={{ display: "block", fontSize: 12.5, fontWeight: 700, color: "var(--ac-text-secondary)", marginBottom: 4 }}>
        Documentos de respaldo
      </label>
      {docs.error && <ErrorBanner message={docs.error} />}
      {docs.loading ? <Spinner /> : (
        <div>
          {DOCUMENT_TYPES.map((t) => (
            <DocumentRow key={t.key} type={t.key} label={t.label} hint={t.hint}
                        doc={byType.get(t.key)} onUploaded={docs.reload} />
          ))}
        </div>
      )}
    </div>
  );
}

function ProfileView({ user, profile, docs, isListed, engagement, onToggleListed, onEdit }: {
  user: { full_name: string; avatar_url: string | null } | null;
  profile: CaregiverProfileOut;
  docs: DocsState;
  isListed: boolean;
  engagement: Engagement | null | undefined;
  onToggleListed: (v: boolean) => void;
  onEdit: () => void;
}) {
  const byType = new Map((docs.data ?? []).map((d) => [d.doc_type, d]));
  const missing = DOCUMENT_TYPES.filter((t) => !byType.has(t.key));

  return (
    <div className="card profile-view">
      <div className="profile-view-top">
        <div className="cg-avatar profile-view-avatar">{user ? <Avatar name={user.full_name} photoUrl={user.avatar_url} /> : "?"}</div>
        <div className="profile-view-id">
          <div className="profile-view-name">{user?.full_name ?? "Tu perfil"}</div>
          <div className="profile-view-headline">{profile.headline || "Todavía no agregas un título profesional."}</div>
          <div style={{ marginTop: 4 }}>
            {profile.rating_avg != null ? <Stars rating={profile.rating_avg} /> : <span style={{ fontSize: 12.5, color: "var(--ac-text-tertiary)" }}>Sin reseñas todavía</span>}
            {profile.rating_avg != null && <span style={{ fontSize: 12, color: "var(--ac-text-tertiary)", marginLeft: 6 }}>({profile.reviews_count})</span>}
          </div>
        </div>
        <button type="button" className="btn primary" onClick={onEdit}>✎ Editar perfil</button>
      </div>

      <div className="toggle-row" style={{ margin: "16px 0", borderColor: isListed ? "var(--ac-border)" : "var(--ac-warn-500)" }}>
        <div>
          <div style={{ fontWeight: 700, fontSize: 14, color: isListed ? "var(--ac-text-primary)" : "var(--ac-warn-700)" }}>
            {isListed ? "✓ Visible en el marketplace" : "● Oculto — no apareces en las búsquedas"}
          </div>
          <div style={{ fontSize: 12, color: "var(--ac-text-tertiary)" }}>
            {isListed ? "Las familias pueden encontrarte y contactarte." : "Actívalo para que las familias te encuentren."}
          </div>
        </div>
        <Switch checked={isListed} onChange={onToggleListed} />
      </div>

      {engagement && (
        <div className="ok-banner" style={{ marginBottom: 4 }}>
          ✓ Actualmente trabajando con {engagement.family_name}
          {engagement.patient_name ? ` · cuidando a ${engagement.patient_name}` : ""}
        </div>
      )}

      {profile.bio && <p className="profile-view-bio">{profile.bio}</p>}

      <div className="profile-view-grid">
        <div>
          <div className="field-label">Experiencia</div>
          <div className="field-value">{profile.years_experience != null ? `${profile.years_experience} años` : "—"}</div>
        </div>
        <div>
          <div className="field-label">Idiomas</div>
          <div className="field-value">{profile.languages.join(", ") || "—"}</div>
        </div>
      </div>

      {profile.specialties.length > 0 && (
        <div className="profile-view-section">
          <div className="field-label">Especialidades</div>
          <div className="chip-row">{profile.specialties.map((s) => <Chip key={s} kind="teal">{s}</Chip>)}</div>
        </div>
      )}
      {profile.zones.length > 0 && (
        <div className="profile-view-section">
          <div className="field-label">Zonas de cobertura</div>
          <div className="chip-row">{profile.zones.map((z) => <Chip key={z} kind="neutral">{z}</Chip>)}</div>
        </div>
      )}

      <div className="profile-view-section">
        <div className="field-label">
          Documentos {missing.length === 0 ? "· completos ✓" : `· falta${missing.length > 1 ? "n" : ""} ${missing.length}`}
        </div>
        <div className="doc-status-list">
          {DOCUMENT_TYPES.map((t) => (
            <span key={t.key} className={`doc-status-item ${byType.has(t.key) ? "ok" : "missing"}`}>
              {byType.has(t.key) ? "✓" : "○"} {t.label}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}

function isProfileEmpty(p: CaregiverProfileOut): boolean {
  return !p.headline && !p.bio && p.years_experience == null &&
    p.specialties.length === 0 && p.languages.length === 0 && p.zones.length === 0;
}

function ProfileTab() {
  const { user } = useAuth();
  const profile = useApi(() => CaregiverApi.myProfile(), []);
  const engagement = useApi(() => CaregiverApi.engagement(), []);
  const docs = useApi(() => CaregiverApi.myDocuments(), []);
  const [mode, setMode] = useState<"view" | "edit">("edit");
  const [modeReady, setModeReady] = useState(false);
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
    // Solo decidimos el modo inicial una vez (al cargar): si ya había datos,
    // partimos en la vista de "así se ve tu perfil"; si es la primera vez,
    // abrimos directo el formulario para que los complete.
    if (!modeReady) {
      setMode(isProfileEmpty(profile.data) ? "edit" : "view");
      setModeReady(true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
      setMode("view");
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo guardar el perfil.");
    } finally {
      setBusy(false);
    }
  }

  async function toggleListed(v: boolean) {
    setBusy(true);
    setError(null);
    try {
      await CaregiverApi.updateProfile({ is_listed: v });
      setIsListed(v);
      profile.reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo actualizar la visibilidad.");
    } finally {
      setBusy(false);
    }
  }

  if (profile.loading || !profile.data) return <Spinner />;

  if (mode === "view") {
    return (
      <>
        {error && <ErrorBanner message={error} />}
        <ProfileView user={user} profile={profile.data} docs={docs} isListed={isListed}
                    engagement={engagement.data} onToggleListed={toggleListed} onEdit={() => setMode("edit")} />
      </>
    );
  }

  return (
    <div className="grid2">
      <IdentityPanel docs={docs} />

      <div className="card">
        <h3 style={{ marginTop: 0 }}>Sobre ti</h3>
        {engagement.data && (
          <div className="ok-banner" style={{ marginBottom: 16 }}>
            ✓ Actualmente trabajando con {engagement.data.family_name}
            {engagement.data.patient_name ? ` · cuidando a ${engagement.data.patient_name}` : ""}
          </div>
        )}
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

        <div className="toggle-row" style={{ margin: "16px 0", borderColor: isListed ? "var(--ac-border)" : "var(--ac-warn-500)" }}>
          <div>
            <div style={{ fontWeight: 700, fontSize: 14, color: isListed ? "var(--ac-text-primary)" : "var(--ac-warn-700)" }}>
              {isListed ? "✓ Visible en el marketplace" : "● Oculto — no apareces en las búsquedas"}
            </div>
            <div style={{ fontSize: 12, color: "var(--ac-text-tertiary)" }}>
              {isListed ? "Las familias pueden encontrarte y contactarte." : "Actívalo para que las familias te encuentren."}
            </div>
          </div>
          <Switch checked={isListed} onChange={(v) => setIsListed(v)} />
        </div>

        {error && <ErrorBanner message={error} />}
        {saved === "listed" && <OkBanner message="Perfil guardado y publicado — ya apareces en el marketplace." />}
        {saved === "hidden" && (
          <div className="error-banner" style={{ background: "var(--ac-warn-100)", borderLeftColor: "var(--ac-warn-500)", color: "var(--ac-warn-700)" }}>
            ⚠ Perfil guardado, pero sigue oculto. Activa "Visible en el marketplace" arriba para que las familias te encuentren.
          </div>
        )}
        <div style={{ display: "flex", gap: 10 }}>
          <button className="btn primary" onClick={() => save()} disabled={busy}>
            {busy ? "Guardando…" : "Guardar cambios"}
          </button>
          {!isProfileEmpty(profile.data) && (
            <button type="button" className="btn ghost" onClick={() => setMode("view")} disabled={busy}>Cancelar</button>
          )}
        </div>
      </div>
    </div>
  );
}
