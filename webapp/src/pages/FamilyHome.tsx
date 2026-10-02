import { useRef, useState, type ChangeEvent } from "react";
import { Link } from "react-router-dom";
import { PatientsApi } from "../api/endpoints";
import { useApi } from "../hooks/useApi";
import { Avatar, EmptyState, ErrorBanner, Modal, Spinner } from "../components/ui";

const PHOTO_MAX_BYTES = 4 * 1024 * 1024;
const PHOTO_TYPES = ["image/jpeg", "image/png", "image/webp"];

export default function FamilyHome() {
  const patients = useApi(() => PatientsApi.list(), []);
  const [showCreate, setShowCreate] = useState(false);

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Mis familiares</h1>
          <p>Los adultos mayores que tienes a tu cargo en AgeCare.</p>
        </div>
        <Link to="/marketplace" className="btn primary">Buscar cuidadoras</Link>
      </div>

      {patients.error && <ErrorBanner message={patients.error} />}
      {patients.loading && <Spinner />}
      {patients.data && (
        <div className="patient-grid">
          {patients.data.items.map((p) => (
            <div key={p.patient_id} className="patient-card">
              <div className="patient-avatar"><Avatar name={p.full_name} photoUrl={p.photo_url} /></div>
              <div className="name">{p.full_name}</div>
            </div>
          ))}
          <button className="dashed-card" onClick={() => setShowCreate(true)}>
            <span style={{ fontSize: 28 }}>+</span>
            <span>Crear perfil de un adulto mayor</span>
          </button>
        </div>
      )}
      {patients.data && patients.data.items.length === 0 && !patients.loading && (
        <EmptyState label="Aún no has creado ningún perfil. Empieza creando el de tu ser querido." />
      )}

      <div className="card" style={{ marginTop: 28 }}>
        <h3 style={{ margin: "0 0 8px" }}>Próximamente</h3>
        <p style={{ fontSize: 13, color: "var(--ac-text-secondary)", margin: 0 }}>
          El semáforo de bienestar, las alertas, el plan de medicamentos y el chat de coordinación
          son parte de otros módulos del proyecto AgeCare, fuera del alcance de este prototipo
          (marketplace y fidelización).
        </p>
      </div>

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
