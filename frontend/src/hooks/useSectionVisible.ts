import { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';

/**
 * True mientras el elemento con este id está sustancialmente visible en el
 * viewport. A diferencia de `useScrollSpy` (que elige la sección "más visible"
 * entre varias candidatas, para resaltar el nav), esto solo pregunta por una —
 * lo usa `AppShell` para ocultar el PiP de cámara flotante mientras la sección
 * Hablar, que ya trae su propio panel de cámara a tamaño completo, está en
 * pantalla.
 *
 * Si el elemento no existe en el DOM (p. ej. estando en `/settings`, donde la
 * landing no está montada) se queda en `false` sin lanzar. Vuelve a buscar el
 * elemento en cada cambio de ruta: `AppShell` no se remonta al navegar (solo su
 * `<Outlet/>`), así que sin esta dependencia el observer quedaría apuntando a un
 * elemento que ya no existe tras salir de la landing y volver a ella.
 */
export function useSectionVisible(id: string): boolean {
  const [visible, setVisible] = useState(false);
  const location = useLocation();

  useEffect(() => {
    const el = document.getElementById(id);
    if (!el) {
      // queueMicrotask, no setState síncrono en el cuerpo del efecto — mismo
      // patrón que useHologramControl.refresh() para lo mismo.
      queueMicrotask(() => setVisible(false));
      return;
    }
    const observer = new IntersectionObserver(
      ([entry]) => setVisible(entry.isIntersecting),
      { threshold: 0.3 },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [id, location.pathname]);

  return visible;
}
