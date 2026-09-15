import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import PublicNav from "../components/PublicNav";
import { useAuth } from "../auth/AuthContext";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("familia@demo.cl");
  const [password, setPassword] = useState("Familia123!");
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
    <div>
      <PublicNav />
      <div className="auth-wrap">
        <div className="auth-card">
          <h1>Inicia sesión</h1>
          <p className="sub">Entra a tu cuenta de AgeCare.</p>
          <form onSubmit={onSubmit}>
            <div className="field">
              <label htmlFor="email">Correo</label>
              <input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
            </div>
            <div className="field">
              <label htmlFor="password">Contraseña</label>
              <input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
            </div>
            {error && <div className="error-banner">⚠ {error}</div>}
            <button className="btn primary block" type="submit" disabled={busy}>
              {busy ? "Ingresando…" : "Ingresar"}
            </button>
          </form>
          <div className="field-hint" style={{ marginTop: 16 }}>
            <b>Demo:</b> familia@demo.cl / Familia123! — o maria@cuidado.cl / Cuidado123!
          </div>
          <div className="auth-switch">¿No tienes cuenta? <Link to="/registro" className="btn link">Regístrate</Link></div>
        </div>
      </div>
    </div>
  );
}
