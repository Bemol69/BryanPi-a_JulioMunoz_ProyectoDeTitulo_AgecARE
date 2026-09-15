import { useState, type FormEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import PublicNav from "../components/PublicNav";
import { useAuth } from "../auth/AuthContext";

type AccountType = "family" | "caregiver";

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const initial = params.get("tipo") === "caregiver" ? "caregiver" : params.get("tipo") === "family" ? "family" : null;

  const [accountType, setAccountType] = useState<AccountType | null>(initial as AccountType | null);
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!accountType) {
      setError("Elige si te registras como familia o como cuidadora.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await register({ full_name: fullName, email, password, phone: phone || undefined, account_type: accountType });
      navigate("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo crear la cuenta.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <PublicNav />
      <div className="auth-wrap">
        <div className="auth-card">
          <h1>Crea tu cuenta</h1>
          <p className="sub">Elige qué te trae a AgeCare.</p>

          <div className="role-pick">
            <button type="button" className={accountType === "family" ? "on" : ""} onClick={() => setAccountType("family")}>
              <span className="ico">👪</span>
              <span className="t">Necesito cuidado</span>
              <span className="s">Soy familiar de un adulto mayor</span>
            </button>
            <button type="button" className={accountType === "caregiver" ? "on" : ""} onClick={() => setAccountType("caregiver")}>
              <span className="ico">🧑‍⚕️</span>
              <span className="t">Quiero cuidar</span>
              <span className="s">Ofrezco servicios de cuidado</span>
            </button>
          </div>

          <form onSubmit={onSubmit}>
            <div className="field">
              <label htmlFor="fullName">Nombre completo</label>
              <input id="fullName" value={fullName} onChange={(e) => setFullName(e.target.value)} required minLength={2} />
            </div>
            <div className="field">
              <label htmlFor="email">Correo</label>
              <input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
            </div>
            <div className="field">
              <label htmlFor="phone">Teléfono (opcional)</label>
              <input id="phone" value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="+56 9 1234 5678" />
            </div>
            <div className="field">
              <label htmlFor="password">Contraseña</label>
              <input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={8} />
              <div className="field-hint">Mínimo 8 caracteres.</div>
            </div>
            {error && <div className="error-banner">⚠ {error}</div>}
            <button className="btn primary block" type="submit" disabled={busy}>
              {busy ? "Creando cuenta…" : "Crear cuenta"}
            </button>
          </form>
          <div className="auth-switch">¿Ya tienes cuenta? <Link to="/login" className="btn link">Inicia sesión</Link></div>
        </div>
      </div>
    </div>
  );
}
