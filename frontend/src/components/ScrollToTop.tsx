import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';

/**
 * Restaura el scroll al inicio en cada cambio de **ruta** (pathname).
 *
 * Sin esto, al navegar de la landing (scrolleada) a `/settings` el navegador
 * conserva la posición y la Configuración abre desde abajo. Solo reacciona a
 * cambios de pathname: los cambios de hash dentro de `/` (p. ej.
 * `navigate({ pathname: '/', hash: '#hablar' })`) los resuelve la propia
 * landing con `scrollIntoView`, así que aquí se ignoran para no pelearse.
 */
export function ScrollToTop() {
  const { pathname } = useLocation();

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);

  return null;
}
