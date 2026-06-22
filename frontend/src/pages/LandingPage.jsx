import {
  ArrowRight,
  Bolt,
  Check,
  CheckCircle2,
  ChevronDown,
  Clock3,
  Edit3,
  Mail,
  PenLine,
  Send,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
  UserRound,
} from "lucide-react";

const assetBase = import.meta.env.BASE_URL;
const brandMark = `${assetBase}addin-icons/icon-32.png`;
const ctaIcon = `${assetBase}addin-icons/icon-80.png`;

const problemCards = [
  {
    icon: PenLine,
    title: "Correos poco claros",
    text: "Mensajes largos, confusos o con frases débiles.",
  },
  {
    icon: ShieldCheck,
    title: "Tono incorrecto",
    text: "Demasiado seco, informal o inseguro para el contexto.",
  },
  {
    icon: Clock3,
    title: "Pérdida de tiempo",
    text: "Reescribir un correo simple puede tomar más de lo necesario.",
  },
];

const benefitCards = [
  { icon: Sparkles, title: "Claridad", text: "Convierte mensajes confusos en correos fáciles de entender." },
  { icon: Send, title: "Profesionalismo", text: "Ajusta el tono para que suene seguro, amable y correcto." },
  { icon: Bolt, title: "Rapidez", text: "Genera una versión mejorada sin salir de Outlook." },
  { icon: ShieldCheck, title: "Control", text: "Puedes reemplazar el texto, insertar abajo o cancelar." },
];

const audiences = [
  ["Profesionales administrativos", "Para responder con claridad y orden."],
  ["Ventas y atención al cliente", "Para comunicar mejor sin sonar improvisado."],
  ["Jefes y coordinadores", "Para enviar mensajes firmes sin perder profesionalismo."],
  ["Personas que quieren escribir mejor", "Para sonar más claro, seguro y competente."],
];

const faqs = [
  ["¿BetterMail AI envía correos por mí?", "No. BetterMail AI solo propone una versión mejorada. Tú decides si la aplicas."],
  ["¿Cambia el sentido de mi mensaje?", "No debería. Está pensado para mejorar claridad y tono manteniendo tu intención original."],
  ["¿Funciona dentro de Outlook?", "Sí. El complemento se abre dentro de Outlook para trabajar sobre el correo que estás escribiendo."],
  ["¿Necesito configurar muchas cosas?", "No. La experiencia está diseñada para instalar, abrir y mejorar el correo sin una curva de aprendizaje."],
  ["¿Puedo elegir el tono?", "Sí. Puedes elegir tonos como profesional, amable, directo o firme según el contexto."],
];

function Logo() {
  return (
    <a className="landing-logo" href="#top" aria-label="BetterMail AI">
      <img src={brandMark} alt="" />
      <span>BetterMail <strong>AI</strong></span>
    </a>
  );
}

function ProductMockup() {
  return (
    <div className="product-mockup" aria-label="Mockup de BetterMail AI funcionando dentro de Outlook">
      <div className="outlook-window">
        <div className="outlook-topbar">
          <span className="app-grid" />
          <span>Outlook</span>
          <div className="mock-search">Buscar</div>
          <span className="mock-dot" />
          <span className="mock-dot" />
          <span className="mock-dot" />
        </div>
        <div className="outlook-body">
          <aside className="outlook-rail">
            <span />
            <span />
            <span className="active" />
            <span />
          </aside>
          <div className="compose-card">
            <div className="compose-line"><span>Para</span></div>
            <div className="compose-line"><span>CC</span></div>
            <div className="compose-subject">Actualización del proyecto</div>
            <p>
              Hola, te escribo para decirte que el proyecto sigue en proceso y que estamos trabajando en los pendientes.
              Avísame cualquier cosa.
            </p>
          </div>
          <div className="addin-panel">
            <div className="addin-header">
              <Logo />
              <span>×</span>
            </div>
            <label htmlFor="tone-preview">Tono</label>
            <select id="tone-preview" defaultValue="Profesional" aria-label="Tono seleccionado en el mockup">
              <option>Profesional</option>
            </select>
            <p className="panel-label">Propuesta mejorada</p>
            <div className="improved-preview">
              Hola, quiero comentarte que el proyecto sigue en marcha y estamos avanzando con los pendientes asignados.
              Si hay algún detalle adicional que deba considerar, quedo atento.
            </div>
            <div className="panel-actions">
              <button>Reemplazar</button>
              <button>Insertar abajo</button>
            </div>
            <button className="cancel-action">Cancelar</button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function LandingPage() {
  return (
    <main id="top" className="landing-page">
      <header className="landing-header">
        <nav className="landing-nav">
          <Logo />
          <div className="nav-links">
            <a href="#producto">Producto</a>
            <a href="#como-funciona">Cómo funciona</a>
            <a href="#precios">Precios</a>
            <a href="#faq">FAQ</a>
          </div>
          <a className="nav-cta" href="/pricing">Probar gratis</a>
        </nav>
      </header>

      <section className="hero-section" id="producto">
        <div className="hero-copy">
          <h1>Escribe correos profesionales <span>en segundos</span></h1>
          <p>
            BetterMail AI mejora tus correos directamente en Outlook, manteniendo tu idea original y dándole un tono
            más claro, profesional y seguro.
          </p>
          <div className="hero-actions">
            <a className="primary-button" href="/pricing"><Mail size={18} />Probar gratis en Outlook</a>
            <a className="secondary-button" href="#como-funciona">Ver cómo funciona</a>
          </div>
          <div className="hero-note"><SlidersHorizontal size={16} />Sin configuraciones complicadas. Sin curva de aprendizaje. Instalas, abres y mejoras tu correo.</div>
        </div>
        <ProductMockup />
      </section>

      <section className="trust-strip">
        <h2>Diseñado para profesionales que escriben correos todos los días</h2>
        <div>
          <span><Mail size={18} />Funciona en Outlook</span>
          <span><ShieldCheck size={18} />No cambia el sentido del mensaje</span>
          <span><Bolt size={18} />Listo para usar en segundos</span>
        </div>
      </section>

      <section className="landing-section">
        <h2>Un mal correo puede hacerte ver poco profesional</h2>
        <div className="three-grid">
          {problemCards.map(({ icon: Icon, title, text }) => (
            <article className="feature-card warning-card" key={title}>
              <Icon size={26} />
              <h3>{title}</h3>
              <p>{text}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="solution-band">
        <div className="solution-copy">
          <h2>BetterMail AI mejora el correo, no reemplaza tu intención</h2>
          <p>
            Tú escribes la idea. BetterMail AI la convierte en una versión más clara, profesional y lista para enviar,
            manteniendo el sentido original del mensaje.
          </p>
        </div>
        <div className="benefit-grid">
          {benefitCards.map(({ icon: Icon, title, text }) => (
            <article className="feature-card compact-card" key={title}>
              <Icon size={26} />
              <h3>{title}</h3>
              <p>{text}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="landing-section steps-section" id="como-funciona">
        <h2>De correo básico a correo profesional en 3 pasos</h2>
        <div className="steps-line">
          {[
            ["Escribe tu correo", "Redacta tu mensaje como lo harías normalmente.", Edit3],
            ["Abre BetterMail AI", "El complemento analiza el texto y genera una propuesta mejorada.", Sparkles],
            ["Elige qué hacer", "Reemplaza el texto, inserta la versión mejorada abajo o cancela.", Check],
          ].map(([title, text, Icon], index) => (
            <article className="step-item" key={title}>
              <span className="step-number">{index + 1}</span>
              <div className="step-icon"><Icon size={28} /></div>
              <h3>{title}</h3>
              <p>{text}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="landing-section difference-section">
        <h2>Mira la diferencia</h2>
        <div className="compare-card">
          <article>
            <span>Antes</span>
            <p>Hola, necesito que me ayudes con esto porque está pendiente y ya ha pasado mucho tiempo.</p>
          </article>
          <article>
            <span>Después</span>
            <p>Hola, agradecería tu ayuda con este tema pendiente. Considero importante revisarlo cuanto antes para poder avanzar de manera ordenada.</p>
          </article>
        </div>
        <p className="center-note">Mismo mensaje. Mejor tono. Más claridad.</p>
      </section>

      <section className="landing-section tones-section">
        <h2>Elige el tono correcto <span>para cada situación</span></h2>
        <div className="tone-grid">
          {[
            ["Profesional", "Claro, formal y seguro.", UserRound, true],
            ["Amable", "Cercano, cordial y respetuoso.", CheckCircle2],
            ["Directo", "Preciso, breve y sin rodeos.", Send],
            ["Firme", "Serio, claro y con autoridad.", ShieldCheck],
          ].map(([title, text, Icon, active]) => (
            <article className={`tone-card-landing ${active ? "selected" : ""}`} key={title}>
              {active && <CheckCircle2 className="selected-check" size={20} />}
              <Icon size={30} />
              <h3>{title}</h3>
              <p>{text}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="audience-band">
        <h2>Hecho para personas que viven entre correos</h2>
        <div className="audience-grid">
          {audiences.map(([title, text], index) => (
            <article key={title}>
              <div className="avatar">{["PA", "VC", "JC", "EM"][index]}</div>
              <div>
                <h3>{title}</h3>
                <p>{text}</p>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="landing-section pricing-section" id="precios">
        <h2>Planes simples para escribir mejor todos los días</h2>
        <div className="pricing-grid">
          <article className="price-card">
            <h3>Gratis</h3>
            <strong>$0</strong>
            <p>Prueba BetterMail AI con un límite mensual de correos mejorados.</p>
            <a href="/pricing">Empezar gratis</a>
          </article>
          <article className="price-card recommended">
            <span className="recommended-badge">Recomendado</span>
            <h3>Pro</h3>
        <strong>$4.99 <small>/ 30 dias</small></strong>
            <p>Para profesionales que escriben correos todos los días.</p>
            <ul>
              <li><Check size={16} />Correos mejorados cada mes</li>
              <li><Check size={16} />Tonos profesionales</li>
              <li><Check size={16} />Uso directo desde Outlook</li>
            </ul>
            <a href="/pricing">Elegir Pro</a>
          </article>
          <article className="price-card">
            <h3>Empresa</h3>
            <strong>Precio personalizado</strong>
            <p>Para equipos que necesitan comunicación profesional consistente.</p>
            <a href="/contact">Contactar</a>
          </article>
        </div>
      </section>

      <section className="privacy-band">
        <div>
          <h2>Tu correo sigue siendo tuyo</h2>
          <p>BetterMail AI está diseñado para mejorar el texto que decides procesar. No cambia el sentido del mensaje y te permite revisar la propuesta antes de insertarla o reemplazar el contenido.</p>
        </div>
        <div className="privacy-points">
          <span><CheckCircle2 size={34} />Siempre revisas antes de aplicar cambios.</span>
          <span><Mail size={34} />No se envían correos automáticamente.</span>
          <span><ShieldCheck size={34} />No modifica tu mensaje sin tu aprobación.</span>
        </div>
      </section>

      <section className="landing-section faq-section" id="faq">
        <h2>Preguntas frecuentes</h2>
        <div className="faq-grid">
          {faqs.map(([question, answer]) => (
            <details key={question}>
              <summary>{question}<ChevronDown size={18} /></summary>
              <p>{answer}</p>
            </details>
          ))}
        </div>
      </section>

      <section className="final-cta">
        <div>
          <img src={ctaIcon} alt="" />
          <h2>Convierte tus correos en mensajes profesionales</h2>
        </div>
        <p>Instala BetterMail AI y mejora tu redacción sin salir de Outlook.</p>
        <a href="/pricing">Probar gratis <ArrowRight size={18} /></a>
      </section>

      <footer className="landing-footer">
        <Logo />
        <div>
          <a href="#producto">Producto</a>
          <a href="#como-funciona">Cómo funciona</a>
          <a href="#precios">Precios</a>
          <a href="#faq">FAQ</a>
          <a href="/support">Soporte</a>
          <a href="/privacy">Privacidad</a>
          <a href="/terms">Terminos</a>
        </div>
        <span>© 2026 BetterMail AI. Todos los derechos reservados.</span>
      </footer>
    </main>
  );
}
