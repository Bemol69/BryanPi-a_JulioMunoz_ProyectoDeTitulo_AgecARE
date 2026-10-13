import { useEffect, useRef, useState, type ChangeEvent } from "react";
import { CaregiverApi } from "../api/endpoints";
import { useApi } from "../hooks/useApi";
import { useAuth } from "../auth/AuthContext";
import { Link } from "react-router-dom";
import { Avatar, Chip, ErrorBanner, OkBanner, Spinner, Stars, Switch, fmtDate } from "../components/ui";
import type { CaregiverDocType, CaregiverDocumentOut, CaregiverProfileOut, Engagement } from "../api/types";

const AVATAR_MAX_BYTES = 4 * 1024 * 1024;
const AVATAR_TYPES = ["image/jpeg", "image/png", "image/webp"];

const DOCUMENT_MAX_BYTES = 4 * 1024 * 1024;
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

function PendingRequestsBanner() {
  const reqs = useApi(() => CaregiverApi.hireRequests(), []);
  const pending = reqs.data?.items.filter((r) => r.status === "pending").length ?? 0;
  if (pending === 0) return null;
  return (
    <Link to="/solicitudes" className="request-banner">
      <span>📩 Tienes <b>{pending}</b> {pending === 1 ? "solicitud de contratación" : "solicitudes de contratación"} por responder</span>
      <span className="btn gold small">Ver solicitudes</span>
    </Link>
  );
}

export default function CaregiverDashboard() {
  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Mi perfil profesional</h1>
          <p>Así te ven las familias que buscan cuidadoras en el marketplace.</p>
        </div>
        <Link to="/mensajes" className="btn ghost">💬 Mis mensajes</Link>
      </div>
      <PendingRequestsBanner />
      <ProfileTab />
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
      setError("La foto no puede superar los 4 MB.");
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
        <div style={{ fontSize: 11.5, color: "var(--ac-text-tertiary)", marginTop: 6 }}>JPG, PNG o WEBP · máx. 4 MB</div>
        {error && <div style={{ fontSize: 12, color: "var(--ac-warn-700)", marginTop: 4 }}>⚠ {error}</div>}
      </div>
    </div>
  );
}

const CHANGE_NOTICE =
  "Te confirmaremos dentro de los próximos días si el cambio que deseas realizar ha sido aprobado por el equipo de AgeCare.";

function DocStatusChip({ doc }: { doc: CaregiverDocumentOut | undefined }) {
  if (!doc) return <span className="doc-chip none">No subido</span>;
  if (doc.status === "approved" && doc.pending_file_url) return <span className="doc-chip pending">Cambio en revisión</span>;
  if (doc.status === "approved") return <span className="doc-chip ok">✓ Aprobado</span>;
  if (doc.status === "rejected") return <span className="doc-chip bad">✕ Rechazado</span>;
  return <span className="doc-chip pending">En revisión</span>;
}

function DocumentRow({ type, label, hint, doc, onUploaded }: {
  type: CaregiverDocType; label: string; hint: string; doc: CaregiverDocumentOut | undefined;
  onUploaded: () => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [justSent, setJustSent] = useState<"change" | "new" | null>(null);

  async function onPick(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    if (!DOCUMENT_MIME_TYPES.includes(file.type)) {
      setError("El documento debe ser PDF, JPG o PNG.");
      return;
    }
    if (file.size > DOCUMENT_MAX_BYTES) {
      setError("El documento no puede superar los 4 MB.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const res = await CaregiverApi.uploadDocument(type, file);
      setJustSent(res.pending_file_url ? "change" : "new");
      onUploaded();
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo subir el documento.");
    } finally {
      setBusy(false);
    }
  }

  function startPick() {
    if (doc?.status === "approved" &&
        !window.confirm("Este documento ya está aprobado. Si subes uno nuevo, el equipo de AgeCare deberá aprobar el cambio; mientras tanto seguirá vigente el actual. ¿Continuar?")) {
      return;
    }
    inputRef.current?.click();
  }

  const hasPendingChange = !!doc?.pending_file_url;
  return (
    <div className="doc-card">
      <div className="doc-card-main">
        <div className="doc-card-title">
          <span className="doc-row-label">{label}</span>
          <DocStatusChip doc={doc} />
        </div>
        <div className="doc-row-hint">{hint}</div>
        {doc ? (
          <div className="doc-row-file">
            <a href={doc.file_url} target="_blank" rel="noreferrer">📄 {doc.original_filename}</a>
            <span className="doc-row-date"> · subido {fmtDate(doc.uploaded_at)}</span>
            {hasPendingChange && doc.pending_file_url && (
              <div style={{ marginTop: 4 }}>
                <a href={doc.pending_file_url} target="_blank" rel="noreferrer">🕒 Cambio enviado: {doc.pending_filename}</a>
              </div>
            )}
          </div>
        ) : (
          <div className="doc-row-missing">Todavía no subes este documento.</div>
        )}
        {doc?.status === "rejected" && doc.review_note && (
          <div className="doc-note bad">Motivo del rechazo: {doc.review_note}. Sube uno nuevo para que lo revisemos otra vez.</div>
        )}
        {hasPendingChange && <div className="doc-note">{CHANGE_NOTICE}</div>}
        {justSent === "new" && !hasPendingChange && (
          <div className="doc-note">Documento enviado. El equipo de AgeCare lo revisará y te avisaremos el resultado.</div>
        )}
        {error && <div style={{ fontSize: 12, color: "var(--ac-warn-700)", marginTop: 4 }}>⚠ {error}</div>}
      </div>
      <div>
        <input ref={inputRef} type="file" accept={DOCUMENT_TYPES_ACCEPT} onChange={onPick} disabled={busy} style={{ display: "none" }} />
        <button type="button" className="btn ghost small" onClick={startPick} disabled={busy}>
          {busy ? "Subiendo…" : !doc ? "Subir" : doc.status === "approved" ? "Solicitar cambio" : "Reemplazar"}
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

function ReviewStatusBanner({ status }: { status: CaregiverProfileOut["admin_status"] }) {
  if (status === "approved") {
    return <div className="review-banner ok"><b>✓ Perfil aprobado.</b> Ya puedes aparecer en el marketplace cuando lo mantengas visible.</div>;
  }
  if (status === "suspended") {
    return <div className="review-banner bad"><b>Perfil suspendido.</b> No apareces en las búsquedas. Escríbenos si crees que es un error.</div>;
  }
  return (
    <div className="review-banner wait">
      <b>🕒 Tu perfil está en revisión.</b> El equipo de AgeCare revisará tus documentos; mientras tanto no apareces en las búsquedas de las familias.
    </div>
  );
}

function MyReviews({ profile }: { profile: CaregiverProfileOut }) {
  const reviews = useApi(() => CaregiverApi.myReviews(), []);
  const items = reviews.data ?? [];
  return (
    <div className="card" id="mis-resenas">
      <h3>Mis reseñas</h3>
      <p style={{ fontSize: 12.5, color: "var(--ac-text-secondary)", marginTop: -6, marginBottom: 14 }}>
        Lo que las familias opinaron después de trabajar contigo.
        {profile.rating_avg != null && <> Tu valoración promedio es <b>{profile.rating_avg.toFixed(1)}</b> ({profile.reviews_count}).</>}
      </p>
      {reviews.error && <ErrorBanner message={reviews.error} />}
      {reviews.loading && <Spinner />}
      {!reviews.loading && !reviews.error && items.length === 0 && (
        <p style={{ color: "var(--ac-text-tertiary)", fontSize: 13.5 }}>
          Todavía no tienes reseñas. Aparecerán aquí cuando una familia termine un trabajo contigo y te evalúe.
        </p>
      )}
      <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        {items.map((r) => (
          <div key={r.review_id} style={{ borderBottom: "1px solid var(--ac-border)", paddingBottom: 12 }}>
            <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
              <b style={{ fontSize: 13.5 }}>{r.author_name}</b>
              <Stars rating={r.rating} />
            </div>
            {r.comment && <div style={{ fontSize: 13, color: "var(--ac-text-secondary)", marginTop: 4 }}>{r.comment}</div>}
            <div style={{ fontSize: 11, color: "var(--ac-text-tertiary)", marginTop: 4 }}>{fmtDate(r.created_at)}</div>
          </div>
        ))}
      </div>
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

  return (
    <>
      <div className="card profile-view profile-hero-card">
        <div className="profile-cover" />
        <div className="profile-view-top">
          <div className="cg-avatar profile-view-avatar ring">{user ? <Avatar name={user.full_name} photoUrl={user.avatar_url} /> : "?"}</div>
          <div className="profile-view-id">
            <div className="profile-view-name">{user?.full_name ?? "Tu perfil"}</div>
            <div className="profile-view-headline">{profile.headline || "Todavía no agregas un título profesional."}</div>
          </div>
          <button type="button" className="btn primary" onClick={onEdit}>✎ Editar perfil</button>
        </div>

        <ReviewStatusBanner status={profile.admin_status} />

        <div className="stat-tiles">
          <div className="stat-tile"><span>Experiencia</span><b>{profile.years_experience != null ? `${profile.years_experience} años` : "—"}</b></div>
          <div className="stat-tile"><span>Valoración</span><b>{profile.rating_avg != null ? <><Stars rating={profile.rating_avg} /> {profile.rating_avg.toFixed(1)}</> : "Sin reseñas"}</b></div>
          <a className="stat-tile" href="#mis-resenas" style={{ textDecoration: "none", color: "inherit" }}>
            <span>Reseñas</span><b>{profile.reviews_count}</b>
          </a>
          <div className="stat-tile"><span>Idiomas</span><b>{profile.languages.join(", ") || "—"}</b></div>
        </div>

        <div className="toggle-row" style={{ margin: "16px 0", borderColor: isListed ? "var(--ac-border)" : "var(--ac-warn-500)" }}>
          <div>
            <div style={{ fontWeight: 700, fontSize: 14, color: isListed ? "var(--ac-text-primary)" : "var(--ac-warn-700)" }}>
              {isListed ? "✓ Visible en el marketplace" : "● Oculto — no apareces en las búsquedas"}
            </div>
            <div style={{ fontSize: 12, color: "var(--ac-text-tertiary)" }}>
              {isListed ? "Las familias pueden encontrarte y contactarte (si tu perfil está aprobado)." : "Actívalo para que las familias te encuentren."}
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

        {profile.specialties.length > 0 && (
          <div className="profile-view-section">
            <div className="field-label">Especialidades</div>
            <div className="chip-row">{profile.specialties.map((s) => <Chip key={s} kind="brand">{s}</Chip>)}</div>
          </div>
        )}
        {profile.zones.length > 0 && (
          <div className="profile-view-section">
            <div className="field-label">Zonas de cobertura</div>
            <div className="chip-row">{profile.zones.map((z) => <Chip key={z} kind="neutral">📍 {z}</Chip>)}</div>
          </div>
        )}
      </div>

      <MyReviews profile={profile} />

      <div className="card">
        <h3>Mis documentos</h3>
        <p style={{ fontSize: 12.5, color: "var(--ac-text-secondary)", marginTop: -6, marginBottom: 14 }}>
          Aquí puedes ver los archivos que subiste. Para cambiar uno ya aprobado, sube el nuevo y el equipo de AgeCare lo revisará.
        </p>
        {docs.error && <ErrorBanner message={docs.error} />}
        {docs.loading ? <Spinner /> : DOCUMENT_TYPES.map((t) => (
          <DocumentRow key={t.key} type={t.key} label={t.label} hint={t.hint} doc={byType.get(t.key)} onUploaded={docs.reload} />
        ))}
      </div>
    </>
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
