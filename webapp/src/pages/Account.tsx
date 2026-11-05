import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { AuthApi } from "../api/endpoints";
import { useAuth } from "../auth/AuthContext";
import { Avatar, ConfirmModal } from "../components/ui";

export default function Account() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [confirming, setConfirming] = useState(false);
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  if (!user) return null;
  const isFamily = user.account_type === "family";

  async function remove() {
    if (!password) {
      setError("Escribe tu contraseña para confirmar.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await AuthApi.deleteAccount(password);
      logout();
      navigate("/", { replace: true });
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo eliminar la cuenta.");
      setBusy(false);
    }
  }

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Mi cuenta</h1>
          <p>Tus datos de acceso a AgeCare.</p>
        </div>
      </div>

      <div className="card">
        <div className="account-id">
          <div className="patient-hero-avatar" style={{ width: 72, height: 72 }}><Avatar name={user.full_name} photoUrl={user.avatar_url} /></div>
          <div>
            <h3 style={{ margin: 0 }}>{user.full_name}</h3>
            <div className="muted">{user.email}</div>
            <div className="muted">{isFamily ? "Cuenta de familia" : "Cuenta de cuidadora o cuidador"}</div>
          </div>
        </div>
      </div>

      <div className="danger-zone">
        <div>
          <b>Eliminar mi cuenta</b>
          <span>
            {isFamily
              ? "Se borran tus datos, los perfiles de tus familiares, tus chats y las solicitudes enviadas."
              : "Se borra tu perfil profesional, tus documentos, tus reseñas y tus chats, y desapareces de la búsqueda. Tampoco quedarás en la Consola."}
            {" "}No se puede deshacer.
          </span>
        </div>
        <button className="btn danger-ghost" onClick={() => { setPassword(""); setError(null); setConfirming(true); }}>Eliminar cuenta</button>
      </div>

      {confirming && (
        <ConfirmModal title="¿Eliminar tu cuenta?" confirmLabel="Eliminar definitivamente" busy={busy}
                      error={error} onConfirm={remove} onClose={() => setConfirming(false)}>
          <p>Esta acción es definitiva. Escribe tu contraseña para confirmar.</p>
          <div className="field">
            <label>Contraseña</label>
            <input type="password" value={password} autoFocus autoComplete="current-password"
                   onChange={(e) => setPassword(e.target.value)}
                   onKeyDown={(e) => { if (e.key === "Enter") remove(); }} />
          </div>
        </ConfirmModal>
      )}
    </div>
  );
}
