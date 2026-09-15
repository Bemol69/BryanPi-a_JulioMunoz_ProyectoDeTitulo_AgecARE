import { Link } from "react-router-dom";

export default function PublicNav() {
  return (
    <header className="pub-nav">
      <div className="pub-nav-inner">
        <Link to="/" className="pub-logo">
          <img src="/agecare-logo.jpg" alt="AgeCare" />
          AgeCare
        </Link>
        <nav className="pub-links">
          <a href="/#familias">Para familias</a>
          <a href="/#cuidadoras">Para cuidadoras</a>
          <a href="/#como-funciona">Cómo funciona</a>
        </nav>
        <div className="pub-nav-actions">
          <Link to="/login" className="btn ghost small">Iniciar sesión</Link>
          <Link to="/registro" className="btn primary small">Crear cuenta</Link>
        </div>
      </div>
    </header>
  );
}
