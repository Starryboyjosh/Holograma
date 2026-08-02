import { Link, useNavigate } from 'react-router-dom';
import unevLogo from '../../assets/holomind/unev-logo.png';
import socialSprite from '../../assets/holomind/social-sprite.png';
import { NAV_ITEMS } from './navItems';
import { BlueOvals } from './BlueOvals';

/**
 * Los cinco iconos sociales llegan de Figma como UN solo sprite (428×42) que el
 * diseño recorta por posición; no existen como assets separados. Cada entrada
 * define su ancho y el desplazamiento dentro del sprite (nodos 82:241, 82:1752-55).
 */
// Offsets/anchos medidos en el propio píxel del sprite (bounding box real del
// canal alfa de cada glifo), no estimados del nodo de Figma: los valores
// originales no coincidían con dónde caía cada icono, así que LinkedIn e
// Instagram mostraban un recorte de otro glifo en vez del suyo.
const SOCIALS = [
  { name: 'Facebook', href: 'https://www.facebook.com/unevhn', width: 21, offset: 0 },
  { name: 'LinkedIn', href: 'https://www.linkedin.com/school/unevhn', width: 41, offset: 79 },
  { name: 'Instagram', href: 'https://www.instagram.com/unevhn', width: 40, offset: 178 },
  { name: 'WhatsApp', href: 'https://wa.me/50400000000', width: 42, offset: 276 },
  { name: 'YouTube', href: 'https://www.youtube.com/@unevhn', width: 52, offset: 376 },
] as const;

const SPRITE_WIDTH = 428;
const SPRITE_HEIGHT = 42;
const ICON_HEIGHT = 29;
const SCALE = ICON_HEIGHT / SPRITE_HEIGHT;

function SocialIcon({ social }: { social: (typeof SOCIALS)[number] }) {
  // Los glifos del sprite son blancos sobre transparente, así que su canal alfa ES
  // la silueta del icono. Usarlo como `mask` y pintar el color de fondo da un
  // teñido exacto (blanco → naranja en hover) sin cadenas de `filter` frágiles.
  const mask: React.CSSProperties = {
    width: social.width,
    height: ICON_HEIGHT,
    maskImage: `url(${socialSprite})`,
    WebkitMaskImage: `url(${socialSprite})`,
    maskSize: `${SPRITE_WIDTH * SCALE}px ${SPRITE_HEIGHT * SCALE}px`,
    WebkitMaskSize: `${SPRITE_WIDTH * SCALE}px ${SPRITE_HEIGHT * SCALE}px`,
    maskPosition: `-${social.offset * SCALE}px 0`,
    WebkitMaskPosition: `-${social.offset * SCALE}px 0`,
    maskRepeat: 'no-repeat',
    WebkitMaskRepeat: 'no-repeat',
  };
  return (
    <a
      href={social.href}
      target="_blank"
      rel="noreferrer noopener"
      aria-label={social.name}
      title={social.name}
      className="block bg-white transition-colors hover:bg-orange"
      style={mask}
    />
  );
}

/**
 * Pie del diseño (nodos 63:91 / 82:228): arco navy, tarjeta de cristal con el
 * logotipo, enlaces rápidos, ubicación y redes.
 *
 * La dirección viene exportada como imagen en Figma (texto justificado). Aquí se
 * escribe como texto real: es contenido, no un icono, y debe ser seleccionable,
 * traducible y legible por lectores de pantalla.
 */
export function HolomindFooter() {
  const navigate = useNavigate();

  // Mismo criterio que HolomindHeader: las anclas navegan con { pathname: '/',
  // hash } para funcionar igual desde la landing que desde Configuración. Son
  // <button>, no <a>, por la misma razón que allí: el # ya lo usa HashRouter.
  const goToAnchor = (id: string) => () => {
    navigate({ pathname: '/', hash: `#${id}` });
  };

  return (
    // `isolate`: sin esto el arco navy de abajo (`-z-10`) escapaba detrás del
    // propio `bg-cream` del footer en vez de quedar solo detrás de su contenido
    // — mismo motivo por el que `ScreenHero` lo usa en su `<section>`.
    <footer className="relative isolate mt-20 bg-cream pt-[90px] text-white">
      {/* Arco navy: forma en CSS para que siga el ancho de la ventana. */}
      <div
        aria-hidden
        className="absolute inset-x-[-8%] bottom-0 top-0 -z-10 overflow-hidden rounded-t-[50%/160px] bg-navy"
      />
      {/* Óvalos como objeto propio detrás del pie, NO anidado en el div de
          arriba: ese div recorta con el arco (`rounded-t`) para que el navy
          siga la curva del diseño, pero los óvalos deben verse en todo el
          rectángulo, no solo dentro de esa curva. */}
      <div aria-hidden className="absolute inset-x-[-8%] bottom-0 top-0 -z-10">
        <BlueOvals variant="footer" />
      </div>

      <div className="mx-auto w-full max-w-6xl px-6 pb-12">
        <div className="rounded-[30px] border border-white/20 bg-white/5 px-8 py-10 backdrop-blur-sm">
          <div className="grid gap-10 md:grid-cols-3">
            {/* Marca + redes */}
            <div className="space-y-6">
              <img
                src={unevLogo}
                alt="UNEV — Instituto Universitario de Educación Virtual"
                className="h-[68px] w-[328px] max-w-full object-contain"
                draggable={false}
              />
              <div className="flex items-center gap-5">
                {SOCIALS.map((s) => (
                  <SocialIcon key={s.name} social={s} />
                ))}
              </div>
            </div>

            {/* Enlaces rápidos */}
            <div>
              <h2 className="text-[24px] font-semibold uppercase">Enlaces rápidos</h2>
              <ul className="mt-4 space-y-2 text-[16px]">
                {NAV_ITEMS.map((item) =>
                  item.kind === 'route' ? (
                    <li key={item.to} className="list-disc ms-6">
                      <Link to={item.to} className="transition-colors hover:text-orange">
                        {item.label}
                      </Link>
                    </li>
                  ) : (
                    <li key={item.id} className="list-disc ms-6">
                      <button
                        type="button"
                        onClick={goToAnchor(item.id)}
                        className="text-start transition-colors hover:text-orange"
                      >
                        {item.label}
                      </button>
                    </li>
                  ),
                )}
              </ul>
            </div>

            {/* Ubicación */}
            <div>
              <h2 className="text-[24px] font-semibold uppercase">Ubicación</h2>
              <address className="mt-4 text-justify text-[16px] font-normal not-italic">
                Colonia Trejo, entre 9 y 10 calle, 21 avenida C, instalaciones del ITEE,
                Edificio 1 ala izquierda, Segunda planta, San Pedro Sula, Cortés, 21104.
              </address>
              <p className="mt-4 text-[16px] font-semibold italic">
                © 2026 UNEV | Powered by UNEV
              </p>
            </div>
          </div>
        </div>
      </div>
    </footer>
  );
}
