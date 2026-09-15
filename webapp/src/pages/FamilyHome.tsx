import { useState } from "react";
import { Link } from "react-router-dom";
import { PatientsApi } from "../api/endpoints";
import { useApi } from "../hooks/useApi";
import { EmptyState, ErrorBanner, Initials, Modal, Spinner } from "../components/ui";

export default function FamilyHome() {
  const patients = useApi(() => PatientsApi.list(), []);
  const [showCreate, setShowCreate] = useState(false);

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Mis pacientes</h1>
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
              <div className="patient-avatar"><Initials name={p.full_name} /></div>
              <div className="name">{p.full_name}</div>
              <div style={{ fontSize: 12, color: "var(--ac-text-tertiary)" }}>Tu rol: familiar</div>
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

function CreatePatientModal({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const [fullName, setFullName] = useState("");
  const [birthDate, setBirthDate] = useState("");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit() {
    if (!fullName.trim() || !birthDate) {
      setError("Completa el nombre y la fecha de nacimiento.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await PatientsApi.create({ full_name: fullName.trim(), birth_date: birthDate, notes: notes || undefined });
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
        <label>Nombre completo</label>
        <input value={fullName} onChange={(e) => setFullName(e.target.value)} placeholder="Elena Muñoz" />
      </div>
      <div className="field">
        <label>Fecha de nacimiento</label>
        <input type="date" value={birthDate} onChange={(e) => setBirthDate(e.target.value)} />
      </div>
      <div className="field">
        <label>Notas (opcional)</label>
        <textarea rows={3} value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Le gusta la música y el jardín." />
      </div>
      {error && <ErrorBanner message={error} />}
      <button className="btn primary block" onClick={submit} disabled={busy}>
        {busy ? "Creando…" : "Crear perfil"}
      </button>
    </Modal>
  );
}
