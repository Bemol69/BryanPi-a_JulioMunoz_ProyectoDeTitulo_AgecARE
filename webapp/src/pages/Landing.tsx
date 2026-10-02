import { useEffect, useRef, type ReactNode } from "react";
import { Link } from "react-router-dom";
import PublicNav from "../components/PublicNav";

/** Marca los bloques `.reveal` como visibles cuando entran al viewport. */
function useReveal() {
  const root = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const els = root.current?.querySelectorAll<HTMLElement>(".reveal");
    if (!els?.length) return;
    if (typeof IntersectionObserver === "undefined") {
      els.forEach((el) => el.classList.add("in"));
      return;
    }
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) {
            e.target.classList.add("in");
            io.unobserve(e.target);
          }
        });
      },
      { threshold: 0.12, rootMargin: "0px 0px -6% 0px" },
    );
    els.forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, []);
  return root;
}

function Reveal({ children, delay = 0, className = "" }: { children: ReactNode; delay?: 0 | 1 | 2 | 3 | 4; className?: string }) {
  return <div className={`reveal${delay ? ` d${delay}` : ""} ${className}`.trim()}>{children}</div>;
}

export default function Landing() {
  const root = useReveal();

  return (
    <div className="site-bg" ref={root}>
      <div className="site-frame">
        <PublicNav />

        {/* ------------ Hero ------------ */}
        <section className="hero wrap">
          <div className="hero-grid">
            <div>
              <span className="eyebrow"><span className="tag">Nuevo</span> Cuidadoras verificadas, cerca de casa</span>
              <h1>
                Saber que tu ser querido está bien, <span className="accent">de un vistazo</span>.
              </h1>
              <p className="lead">
                AgeCare conecta a las familias que cuidan a distancia con cuidadoras verificadas.
                Encuentra, compara y contacta a la persona indicada para acompañar a tu adulto mayor,
                sin intermediarios ni comisiones.
              </p>
              <div className="hero-actions">
                <Link to="/registro?tipo=family" className="btn primary large">Busco una cuidadora →</Link>
                <Link to="/registro?tipo=caregiver" className="btn ghost large">Soy cuidadora</Link>
              </div>
              <div className="trust">
                <span>Sin comisiones</span>
                <span>Perfiles revisados</span>
                <span>Contacto directo</span>
              </div>
            </div>

            <div className="hero-visual" aria-hidden="true">
              <div className="hv-orb a" />
              <div className="hv-orb b" />
              <div className="hv-orb c" />

              <div className="profile-card">
                <div className="pc-top">
                  <div className="pc-avatar">MT</div>
                  <div>
                    <div className="pc-name">María Torres <i>✓</i></div>
                    <div className="pc-sub">Providencia · 8 años de experiencia</div>
                  </div>
                </div>
                <div className="pc-rating"><span className="stars">★★★★★</span> 4,9 · 34 reseñas</div>
                <div className="pc-chips">
                  <span className="chip brand">Alzheimer</span>
                  <span className="chip brand">Movilidad reducida</span>
                  <span className="chip gold">Destacada</span>
                </div>
                <div className="pc-slots">
                  <span className="on">Lun</span><span className="on">Mar</span><span>Mié</span><span className="on">Jue</span><span>Vie</span>
                </div>
                <span className="pc-cta">Contactar directamente</span>
              </div>

              <div className="float-card f1">
                <div className="fi" style={{ background: "var(--ac-gold-100)" }}>⭐</div>
                <div><div className="ft">4,9 de calificación</div><div className="fs">Reseñas de familias reales</div></div>
              </div>
              <div className="float-card f2">
                <div className="fi" style={{ background: "var(--ac-ok-100)" }}>✓</div>
                <div><div className="ft">Perfil verificado</div><div className="fs">Documentos al día</div></div>
              </div>
              <div className="float-card f3">
                <div className="fi" style={{ background: "var(--ac-brand-100)" }}>💬</div>
                <div><div className="ft">Mensaje nuevo</div><div className="fs">«¿Tienes turno el sábado?»</div></div>
              </div>
              <div className="float-card f4">
                <div className="fi" style={{ background: "var(--ac-violet-100)" }}>●</div>
                <div><div className="ft">Trabajando ahora</div><div className="fs">con Familia Muñoz</div></div>
              </div>
            </div>
          </div>

          <div className="strip reveal">
            <div><i>🤝</i><span><b>Sin comisiones</b>Coordinas directo con la cuidadora</span></div>
            <div><i>🛡️</i><span><b>Perfiles revisados</b>Documentos y antecedentes</span></div>
            <div><i>⭐</i><span><b>Reseñas reales</b>De familias que ya contrataron</span></div>
            <div><i>📍</i><span><b>Cerca de casa</b>Filtra por comuna y especialidad</span></div>
          </div>
        </section>

        {/* ------------ Funciones (bento) ------------ */}
        <section className="section wrap" id="funciones">
          <Reveal>
            <div className="section-head">
              <span className="kicker">Todo en un solo lugar</span>
              <h2>Pensado para cuidar con tranquilidad</h2>
              <p>Desde encontrar a la persona indicada hasta dejar tu opinión: cada paso es simple y claro.</p>
            </div>
          </Reveal>
          <div className="bento">
            <Reveal className="bento-card s4">
              <div className="bento-ico">🔎</div>
              <h3>Busca por zona y especialidad</h3>
              <p>Filtra cuidadoras por comuna, idioma, especialidad y calificación mínima. Compara en segundos.</p>
              <div className="mini-search">
                <div className="mini-filters">
                  <span className="on">Providencia</span><span>Alzheimer</span><span>Turno noche</span><span>★ 4,5+</span>
                </div>
                <div className="mini-row"><div className="av">MT</div><div><b>María Torres</b><small>Providencia · Alzheimer</small></div><div className="r">★ 4,9</div></div>
                <div className="mini-row"><div className="av v">JS</div><div><b>Javiera Soto</b><small>Las Condes · Turnos nocturnos</small></div><div className="r">★ 4,8</div></div>
              </div>
            </Reveal>

            <Reveal className="bento-card s2" delay={1}>
              <div className="bento-ico">🛡️</div>
              <h3>Perfiles verificados</h3>
              <p>Revisamos la documentación de cada cuidadora.</p>
              <ul className="check-list">
                <li>Cédula de identidad</li>
                <li>Antecedentes</li>
                <li>Certificación de cuidado</li>
              </ul>
            </Reveal>

            <Reveal className="bento-card s2">
              <div className="bento-ico">⭐</div>
              <h3>Reseñas reales</h3>
              <p>Opiniones de familias que ya trabajaron con ella.</p>
              <div className="quote">
                «Cuidó a mi madre con mucho cariño y puntualidad.»
                <small>★★★★★ · Familia Muñoz</small>
              </div>
            </Reveal>

            <Reveal className="bento-card s2 brand" delay={1}>
              <div className="bento-ico">💬</div>
              <h3>Contacto directo</h3>
              <p>Habla por teléfono, WhatsApp o correo. Sin intermediarios y sin comisiones.</p>
            </Reveal>

            <Reveal className="bento-card s2 sun" delay={2}>
              <div className="bento-ico">💊</div>
              <h3>Ficha de tu familiar</h3>
              <p>Registra alergias a medicamentos y alimentos para que la cuidadora lo sepa desde el primer día.</p>
              <div className="pill-tags"><span>Penicilina</span><span>Mariscos</span></div>
            </Reveal>
          </div>
        </section>

        {/* ------------ Cómo funciona ------------ */}
        <section className="section wrap" id="como-funciona">
          <Reveal>
            <div className="section-head">
              <span className="kicker">Cómo funciona</span>
              <h2>Así de simple</h2>
              <p>Sin letra chica: descubre, compara y decide con confianza.</p>
            </div>
          </Reveal>
          <div className="steps">
            <Reveal className="step">
              <div className="num">1</div>
              <h3>Busca por zona y especialidad</h3>
              <p>Cuéntanos qué necesita tu adulto mayor y filtra a las cuidadoras que mejor calzan.</p>
            </Reveal>
            <Reveal className="step" delay={1}>
              <div className="num">2</div>
              <h3>Revisa su perfil y reseñas</h3>
              <p>Experiencia, certificaciones y opiniones reales de otras familias.</p>
            </Reveal>
            <Reveal className="step" delay={2}>
              <div className="num">3</div>
              <h3>Contáctala directamente</h3>
              <p>Coordinas tú mismo, sin comisiones, y dejas tu reseña cuando termine el servicio.</p>
            </Reveal>
          </div>
        </section>

        {/* ------------ Roles ------------ */}
        <section className="section wrap">
          <Reveal>
            <div className="section-head">
              <span className="kicker">Una cuenta, un propósito</span>
              <h2>Para cada quien, su vista</h2>
              <p>Familias y cuidadoras tienen su propio espacio, hecho a la medida.</p>
            </div>
          </Reveal>
          <div className="role-grid">
            <Reveal className="role-card family" delay={0}>
              <h3 id="familias">Soy familia</h3>
              <p>Necesito ayuda para cuidar a mi adulto mayor.</p>
              <ul>
                <li>Crea el perfil de tu ser querido</li>
                <li>Busca y compara cuidadoras cerca de ti</li>
                <li>Contáctalas y deja reseñas después</li>
              </ul>
              <Link to="/registro?tipo=family" className="btn light">Crear cuenta de familia</Link>
            </Reveal>
            <Reveal className="role-card caregiver" delay={1}>
              <h3 id="cuidadoras">Soy cuidadora</h3>
              <p>Quiero ofrecer mis servicios de cuidado.</p>
              <ul>
                <li>Publica tu perfil profesional gratis</li>
                <li>Aparece en las búsquedas de familias</li>
                <li>Recibe solicitudes de contacto directo</li>
              </ul>
              <Link to="/registro?tipo=caregiver" className="btn dark">Crear cuenta de cuidadora</Link>
            </Reveal>
          </div>
        </section>

        {/* ------------ CTA final ------------ */}
        <section className="section wrap">
          <Reveal className="cta">
            <h2>Cuidar mejor empieza hoy</h2>
            <p>Crea tu cuenta en minutos y encuentra a la persona indicada para acompañar a quien más quieres.</p>
            <div className="hero-actions">
              <Link to="/registro?tipo=family" className="btn light large">Empezar gratis</Link>
              <Link to="/login" className="btn outline-light large">Ya tengo cuenta</Link>
            </div>
          </Reveal>
        </section>

        <footer className="pub-footer">
          <div className="wrap">
            <div className="pub-logo"><img src="/logo-mark.png" alt="AgeCare" />AgeCare</div>
            <small>© 2026 AgeCare · Wellq Co · Prototipo académico, Duoc UC</small>
          </div>
        </footer>
      </div>
    </div>
  );
}
