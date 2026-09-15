import { Link } from "react-router-dom";
import PublicNav from "../components/PublicNav";

export default function Landing() {
  return (
    <div>
      <PublicNav />

      <section className="hero wrap">
        <div className="hero-grid">
          <div>
            <span className="eyebrow">● Plataforma de cuidado de adultos mayores</span>
            <h1>Saber que tu ser querido está bien, <span className="accent">de un vistazo</span>.</h1>
            <p className="lead">
              AgeCare conecta a las familias que cuidan a distancia con cuidadoras verificadas,
              cerca de casa. Encuentra, compara y contacta a la persona indicada para acompañar
              a tu adulto mayor.
            </p>
            <div className="hero-actions">
              <Link to="/registro?tipo=family" className="btn primary">Busco una cuidadora</Link>
              <Link to="/registro?tipo=caregiver" className="btn ghost">Soy cuidadora, quiero trabajar</Link>
            </div>
          </div>
          <div className="hero-art">
            <div className="hero-card">
              <div className="ico" style={{ background: "var(--ac-ok-100)" }}>✓</div>
              <div>
                <div className="t">María Torres · Providencia</div>
                <div className="s">★★★★★ · 34 reseñas · Alzheimer, Movilidad reducida</div>
              </div>
            </div>
            <div className="hero-card">
              <div className="ico" style={{ background: "var(--ac-gold-100)" }}>⭐</div>
              <div>
                <div className="t">Javiera Soto · Las Condes</div>
                <div className="s">Perfil destacado · turnos nocturnos disponibles</div>
              </div>
            </div>
            <div className="hero-card">
              <div className="ico" style={{ background: "var(--ac-teal-100)" }}>💬</div>
              <div>
                <div className="t">Contacto directo</div>
                <div className="s">Escríbele sin intermediarios ni comisiones</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="section wrap" id="como-funciona">
        <div className="section-head">
          <h2>Así de simple funciona</h2>
          <p>Sin intermediarios ni letra chica: descubre, compara y decide con confianza.</p>
        </div>
        <div className="feature-grid">
          <div className="feature-card">
            <div className="ico" style={{ background: "var(--ac-teal-100)", color: "var(--ac-teal-700)" }}>🔎</div>
            <h3>1. Busca por zona y especialidad</h3>
            <p>Filtra cuidadoras por comuna, idioma, especialidad y calificación mínima.</p>
          </div>
          <div className="feature-card">
            <div className="ico" style={{ background: "var(--ac-coral-100)", color: "var(--ac-coral-700)" }}>👤</div>
            <h3>2. Revisa su perfil y reseñas</h3>
            <p>Experiencia, certificaciones y opiniones reales de otras familias.</p>
          </div>
          <div className="feature-card">
            <div className="ico" style={{ background: "var(--ac-gold-100)", color: "var(--ac-gold-700)" }}>📞</div>
            <h3>3. Contáctala directamente</h3>
            <p>Sin comisiones: coordinas tú mismo por teléfono, WhatsApp o correo.</p>
          </div>
        </div>
      </section>

      <section className="section wrap">
        <div className="section-head">
          <h2>Para cada quien, su vista</h2>
          <p>Una cuenta, un propósito claro.</p>
        </div>
        <div className="role-grid">
          <div className="role-card family" id="familias">
            <h3>Soy familia</h3>
            <p>Necesito ayuda para cuidar a mi adulto mayor.</p>
            <ul>
              <li>✓ Crea el perfil de tu ser querido</li>
              <li>✓ Busca y compara cuidadoras cerca de ti</li>
              <li>✓ Contáctalas y deja reseñas después</li>
            </ul>
            <Link to="/registro?tipo=family" className="btn ghost">Crear cuenta de familia</Link>
          </div>
          <div className="role-card caregiver" id="cuidadoras">
            <h3>Soy cuidadora</h3>
            <p>Quiero ofrecer mis servicios de cuidado.</p>
            <ul>
              <li>✓ Publica tu perfil profesional gratis</li>
              <li>✓ Aparece en las búsquedas de familias</li>
              <li>✓ Recibe solicitudes de contacto directo</li>
            </ul>
            <Link to="/registro?tipo=caregiver" className="btn ghost">Crear cuenta de cuidadora</Link>
          </div>
        </div>
      </section>

      <footer className="pub-footer">
        <div className="wrap">
          <div className="pub-logo"><img src="/agecare-logo.jpg" alt="AgeCare" />AgeCare</div>
          <small>© 2026 AgeCare · Wellq Co · Prototipo académico, Duoc UC</small>
        </div>
      </footer>
    </div>
  );
}
