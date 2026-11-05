import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

/** Muestra las cuentas de ejemplo bajo el formulario. En producción se apaga con VITE_SHOW_DEMO_ACCESS=false. */
const SHOW_DEMO_ACCESS = import.meta.env.VITE_SHOW_DEMO_ACCESS !== "false";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  // Las credenciales de ejemplo solo se precargan en desarrollo; en la Consola publicada el formulario parte vacío.
  const [email, setEmail] = useState(import.meta.env.DEV ? "admin@wellq.co.uk" : "");
  const [password, setPassword] = useState(import.meta.env.DEV ? "Admin123!" : "");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(email, password);
      navigate("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo iniciar sesión.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-wrap">
      <div className="login-card">
        <div className="logo" style={{ padding: 0 }}>
          <div className="logo-mark"><img src="/logo-mark.png" alt="AgeCare" /></div>
          <div>
            <div className="logo-name" style={{ color: "var(--ac-text-primary)" }}>AgeCare</div>
            <div className="logo-sub" style={{ color: "var(--ac-text-tertiary)" }}>Consola de administración</div>
          </div>
        </div>
        <form onSubmit={onSubmit}>
          <div>
            <label htmlFor="email">Correo</label>
            <input id="email" className="input" style={{ width: "100%" }} type="email" value={email}
                  onChange={(e) => setEmail(e.target.value)} required />
          </div>
          <div>
            <label htmlFor="password">Contraseña</label>
            <input id="password" className="input" style={{ width: "100%" }} type="password" value={password}
                  onChange={(e) => setPassword(e.target.value)} required />
          </div>
          {error && <div className="error-banner">⚠ {error}</div>}
          <button className="btn primary" type="submit" disabled={busy}>
            {busy ? "Ingresando…" : "Ingresar"}
          </button>
        </form>
        {SHOW_DEMO_ACCESS && (
        <div className="demo-creds">
          <b>Credenciales demo (seed):</b><br />
          admin@wellq.co.uk / Admin123! — administrador<br />
          editora@wellq.co.uk / Editora123! — gestiona cuidadoras<br />
          analista@wellq.co.uk / Analista123! — solo fidelización
        </div>
        )}
      </div>
    </div>
  );
}
