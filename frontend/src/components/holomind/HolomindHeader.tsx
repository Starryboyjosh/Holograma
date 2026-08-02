import { Link, NavLink, useNavigate } from 'react-router-dom';
import unevLogo from '../../assets/holomind/unev-logo.png';
import { NAV_ITEMS } from './navItems';

/**
 * Indicador de estado de la conexión (nodo 30:1710).
 *
 * Es un indicador, no un botón: refleja `chat.wsConnected` y no acepta clic. El
 * diseño trae los dos textos — CONECTADO / DESCONECTADO — como estados del mismo
 * elemento, que es lo que separa los frames "INICIO - CONECTADO" y
 * "INICIO - DESCONECTADO".
 */
export function ConnectionStatus({ connected }: { connected: boolean }) {
  return (
    <span
      role="status"
      aria-live="polite"
      className={`inline-flex h-[46px] w-[136px] shrink-0 items-center justify-center
                  rounded-[50px] text-[14px] font-bold uppercase text-white
                  transition-colors ${connected ? 'bg-orange/35' : 'bg-black/25'}`}
    >
      {connected ? 'Conectado' : 'Desconectado'}
    </span>
  );
}

/**
 * Cabecera del diseño: logotipo UNEV, pastilla de navegación de cristal e
 * indicador de conexión (nodo 30:1707).
 *
 * `tone` cambia solo el color del texto inactivo: sobre las secciones con malla o
 * navy el nav va en blanco, sobre crema necesita tinta oscura para tener contraste.
 *
 * `NAV_ITEMS` mezcla anclas de scroll (Hablar / Entrenar Visión / Información
 * UNEV, dentro de la landing de una sola página) con una ruta real
 * (Configuración, la única sección que el diseño deja fuera del recorrido). Las
 * anclas navegan con `navigate({ pathname: '/', hash })` en vez de `scrollIntoView`
 * directo: así funcionan igual estando ya en la landing (solo cambia el hash, que
 * `LandingScreen` observa para desplazarse) que viniendo de Configuración (primero
 * monta la landing, luego el mismo efecto la desplaza). Son `<button>`, no `<a>`:
 * la app usa `HashRouter` (el `#` de la URL ya codifica la ruta), así que un
 * `href` de ancla real apuntaría a una URL que el router interpretaría como otra
 * ruta en vez de un desplazamiento dentro de "/".
 */
export function HolomindHeader({
  connected,
  tone = 'light',
  activeAnchorId,
}: {
  connected: boolean;
  tone?: 'light' | 'dark';
  /** Ancla visible según el scrollspy — solo tiene sentido en la landing. */
  activeAnchorId?: string;
}) {
  const onDarkBg = tone === 'light';
  const navigate = useNavigate();

  const goToAnchor = (id: string) => () => {
    navigate({ pathname: '/', hash: `#${id}` });
  };

  return (
    <header className="relative z-30 px-6 py-8 md:px-12">
      {/* Mismo ancho de contenido que el resto de secciones (nodo 30:1707: el
          cluster logo+nav+estado va centrado con márgenes generosos, no
          estirado borde a borde) — si no, en pantallas anchas el header no
          alinea con el titular/tarjetas de abajo. */}
      <div className="mx-auto flex w-full max-w-6xl flex-wrap items-center justify-center gap-x-[39px] gap-y-4 md:justify-start">
        <Link to="/" aria-label="Ir al inicio" className="shrink-0">
          <img
            src={unevLogo}
            alt="UNEV — Instituto Universitario de Educación Virtual"
            className="h-[37px] w-[178px] object-contain"
            draggable={false}
          />
        </Link>

        <nav
          className={`flex flex-wrap items-center justify-center gap-4 rounded-[50px] px-[35px] py-[15px] text-[14px] font-semibold ${
            onDarkBg ? 'bg-black/5 text-white' : 'bg-black/5 text-ink'
          }`}
        >
          {NAV_ITEMS.map((item) => {
            if (item.kind === 'route') {
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={({ isActive }) =>
                    // El activo es naranja al 55% (nodo 79:50); el chip de estado usa
                    // 35% (nodo 79:54), por eso no comparten token.
                    `rounded-[50px] px-4 py-1.5 transition-colors ${
                      isActive ? 'bg-orange/55 text-white' : 'hover:text-orange'
                    }`
                  }
                >
                  {item.label}
                </NavLink>
              );
            }
            const isActive = activeAnchorId === item.id;
            return (
              <button
                key={item.id}
                type="button"
                onClick={goToAnchor(item.id)}
                className={`rounded-[50px] px-4 py-1.5 transition-colors ${
                  isActive ? 'bg-orange/55 text-white' : 'hover:text-orange'
                }`}
              >
                {item.label}
              </button>
            );
          })}
        </nav>

        <div className="md:ms-auto">
          <ConnectionStatus connected={connected} />
        </div>
      </div>
    </header>
  );
}
