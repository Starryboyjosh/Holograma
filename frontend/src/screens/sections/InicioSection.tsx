import { Link, useNavigate } from 'react-router-dom';
import { useSession } from '../../context/SessionContext';
import { ScreenHero } from '../../components/holomind/ScreenHero';
import { Wordmark } from '../../components/holomind/Wordmark';
import { GLASS } from '../../theme';

/**
 * INICIO (nodos 10:53 conectado / 63:2 desconectado).
 *
 * Los dos frames del diseño son el mismo layout con distinto estado de conexión —
 * no dos secciones ni un botón — así que aquí es una sola pantalla que lee
 * `chat.wsConnected`. Lo único que cambia es el indicador de la cabecera (ahora en
 * `StickyHeader`, compartida) y la línea de apoyo bajo el titular.
 *
 * El CTA ya no navega a `/assistant` (esa ruta no existe en la landing de una sola
 * página): baja a la sección `#hablar` en la misma página.
 */
export function InicioSection() {
  const { chat } = useSession();
  const navigate = useNavigate();

  return (
    <ScreenHero id="inicio" backdrop="mesh" bleedTop className="min-h-[880px]">
      <div className="mx-auto flex w-full max-w-6xl flex-col items-center px-6 pb-24 pt-10 md:pt-16">
        <div className={`${GLASS} flex min-h-[437px] w-full items-center justify-center px-8 py-16`}>
          <div className="text-center">
            <h1 className="text-[40px] font-normal leading-tight text-white md:text-[56px]">
              ¿Te interesa la
              <br />
              <Wordmark>Inteligencia Artificial?</Wordmark>
            </h1>
            <p className="mt-4 text-[24px] font-normal italic text-white md:text-[32px]">
              Bienvenido a <strong className="font-extrabold not-italic">HoloMind</strong>
            </p>

            {/* El diseño diferencia los dos frames solo por el estado de conexión;
                este texto lo hace explícito para quien no vea el color del chip. */}
            <p className="mt-8 text-[14px] font-semibold uppercase tracking-wide text-white/80">
              {chat.wsConnected
                ? 'Holograma conectado y listo'
                : 'Sin conexión con el holograma'}
            </p>

            {chat.wsConnected ? (
              <button
                type="button"
                onClick={() => navigate({ pathname: '/', hash: '#hablar' })}
                className="mt-6 inline-flex items-center justify-center rounded-[50px] bg-orange px-8 py-3 text-[14px] font-bold uppercase text-white shadow-[0_1px_5px_rgba(0,0,0,0.25)] transition-opacity hover:opacity-90"
              >
                Hablar con HoloMind
              </button>
            ) : (
              <Link
                to="/settings"
                className="mt-6 inline-flex items-center justify-center rounded-[50px] bg-orange px-8 py-3 text-[14px] font-bold uppercase text-white shadow-[0_1px_5px_rgba(0,0,0,0.25)] transition-opacity hover:opacity-90"
              >
                Revisar conexión
              </Link>
            )}
          </div>
        </div>
      </div>
    </ScreenHero>
  );
}
