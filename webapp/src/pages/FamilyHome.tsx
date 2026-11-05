import { useRef, useState, type ChangeEvent } from "react";
import { Link } from "react-router-dom";
import { PatientsApi } from "../api/endpoints";
import { useApi } from "../hooks/useApi";
import { Avatar, ConfirmModal, EmptyState, ErrorBanner, Modal, Spinner, StatChip } from "../components/ui";

const PHOTO_MAX_BYTES = 4 * 1024 * 1024;
const PHOTO_TYPES = ["image/jpeg", "image/png", "image/webp"];

export default function FamilyHome() {
  const patients = useApi(() => PatientsApi.list(), []);
  const [showCreate, setShowCreate] = useState(false);
  const [toRemove, setToRemove] = useState<{ id: string; name: string } | null>(null);
  const [removing, setRemoving] = useState(false);
  const [removeError, setRemoveError] = useState<string | null>(null);

  async function remove() {
    if (!toRemove) return;
    setRemoving(true);
    setRemoveError(null);
    try {
      await PatientsApi.remove(toRemove.id);
      setToRemove(null);
      patients.reload();
    } catch (e) {
      setRemoveError(e instanceof Error ? e.message : "No se pudo eliminar el perfil.");
    } finally {
      setRemoving(false);
    }
  }

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Mis familiares</h1>
          <p>Los adultos mayores que tienes a tu cargo en AgeCare.</p>
        </div>
        <div className="head-chips">
          {patients.data && (
            <>
              <StatChip icon="👵" label="Familiares" value={patients.data.items.length} tone="ink" />
              <StatChip icon="✓" label="Con cuidadora" value={patients.data.items.filter((p) => p.caregiver_names.length > 0).length} tone="teal" />
              <StatChip icon="○" label="Sin cuidadora" value={patients.data.items.filter((p) => p.caregiver_names.length === 0).length} tone="yellow" />
            </>
          )}
          <Link to="/marketplace" className="btn primary">Buscar cuidadoras</Link>
        </div>
      </div>

      {patients.error && <ErrorBanner message={patients.error} />}
      {patients.loading && <Spinner />}
      {patients.data && (
        <div className="patient-grid">
          {patients.data.items.map((p) => {
            const cared = p.caregiver_names.length > 0;
            return (
              <Link key={p.patient_id} to={`/familia/${p.patient_id}`} className={`patient-card${cared ? " cared" : ""}`}>
                {cared && <span className="working-badge cared-badge"><i /> Con cuidadora</span>}
                <button type="button" className="card-remove" title={`Eliminar a ${p.full_name}`} aria-label={`Eliminar a ${p.full_name}`}
                        onClick={(e) => { e.preventDefault(); e.stopPropagation(); setRemoveError(null); setToRemove({ id: p.patient_id, name: p.full_name }); }}>
                  ✕
                </button>
                <div className="patient-avatar"><Avatar name={p.full_name} photoUrl={p.photo_url} /></div>
                <div className="name">{p.full_name}</div>
                {cared && (
                  <div className="cared-by">
                    Cuidado por {p.caregiver_names[0]}
                    {p.caregiver_names.length > 1 && ` y ${p.caregiver_names.length - 1} más`}
                  </div>
                )}
                <div className="patient-card-foot">Ver perfil y estado <span>→</span></div>
              </Link>
            );
          })}
          <button className="dashed-card" onClick={() => setShowCreate(true)}>
            <span style={{ fontSize: 28 }}>+</span>
            <span>Crear perfil de un adulto mayor</span>
          </button>
        </div>
      )}
      {patients.data && patients.data.items.length === 0 && !patients.loading && (
        <EmptyState label="Aún no has creado ningún perfil. Empieza creando el de tu ser querido." />
      )}

      <div className="soon-strip">
        <span className="soon-tag">Próximamente</span>
        <span>Semáforo de bienestar, alertas y plan de medicamentos de tus familiares.</span>
      </div>

      {toRemove && (
        <ConfirmModal title={`¿Eliminar a ${toRemove.name}?`} confirmLabel="Sí, eliminar" busy={removing}
                      error={removeError} onConfirm={remove} onClose={() => setToRemove(null)}>
          <p>Se eliminará su perfil con su foto, sus alergias y sus notas. Esta acción no se puede deshacer.</p>
        </ConfirmModal>
      )}

      {showCreate && <CreatePatientModal onClose={() => setShowCreate(false)} onCreated={() => { setShowCreate(false); patients.reload(); }} />}
    </div>
  );
}

function SimpleTagInput({ label, values, onChange, placeholder }: {
  label: string; values: string[]; onChange: (v: string[]) => void; placeholder: string;
}) {
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

function CreatePatientModal({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const [fullName, setFullName] = useState("");
  const [birthDate, setBirthDate] = useState("");
  const [medicationAllergies, setMedicationAllergies] = useState<string[]>([]);
  const [foodAllergies, setFoodAllergies] = useState<string[]>([]);
  const [notes, setNotes] = useState("");
  const [photo, setPhoto] = useState<File | null>(null);
  const [photoPreview, setPhotoPreview] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  function onPickPhoto(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    if (!PHOTO_TYPES.includes(file.type)) {
      setError("La foto debe ser JPG, PNG o WEBP.");
      return;
    }
    if (file.size > PHOTO_MAX_BYTES) {
      setError("La foto no puede superar los 4 MB.");
      return;
    }
    setError(null);
    setPhoto(file);
    setPhotoPreview(URL.createObjectURL(file));
  }

  async function submit() {
    if (!fullName.trim() || !birthDate) {
      setError("Completa el nombre y la fecha de nacimiento.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const created = await PatientsApi.create({
        full_name: fullName.trim(), birth_date: birthDate,
        medication_allergies: medicationAllergies, food_allergies: foodAllergies,
        notes: notes || undefined,
      });
      if (photo) await PatientsApi.uploadPhoto(created.patient_id, photo);
      onCreated();
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo crear el perfil.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal title="Crear perfil de un adulto mayor" onClose={onClose}>
      <div className="field">
        <label>Foto (opcional)</label>
        <div className="avatar-picker">
          <div className="cg-avatar">{photoPreview ? <img className="avatar-img" src={photoPreview} alt="" /> : <Avatar name={fullName || "?"} />}</div>
          <div>
            <input ref={inputRef} type="file" accept="image/jpeg,image/png,image/webp" onChange={onPickPhoto} />
            <button type="button" className="btn ghost small" onClick={() => inputRef.current?.click()}>
              {photo ? "Cambiar foto" : "Elegir foto"}
            </button>
            <div style={{ fontSize: 11.5, color: "var(--ac-text-tertiary)", marginTop: 6 }}>JPG, PNG o WEBP · máx. 4 MB</div>
          </div>
        </div>
      </div>
      <div className="field">
        <label>Nombre completo</label>
        <input value={fullName} onChange={(e) => setFullName(e.target.value)} placeholder="Elena Muñoz" />
      </div>
      <div className="field">
        <label>Fecha de nacimiento</label>
        <input type="date" value={birthDate} onChange={(e) => setBirthDate(e.target.value)} />
      </div>
      <SimpleTagInput label="Alergias a medicamentos" values={medicationAllergies} onChange={setMedicationAllergies}
                     placeholder="Ej: Penicilina" />
      <SimpleTagInput label="Alergias o intolerancias alimentarias" values={foodAllergies} onChange={setFoodAllergies}
                     placeholder="Ej: Mariscos" />
      <div className="field">
        <label>Notas generales (opcional)</label>
        <textarea rows={3} value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Le gusta la música y el jardín." />
      </div>
      {error && <ErrorBanner message={error} />}
      <button className="btn primary block" onClick={submit} disabled={busy}>
        {busy ? "Creando…" : "Crear perfil"}
      </button>
    </Modal>
  );
}
