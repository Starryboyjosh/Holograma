import { useToast } from '../context/ToastContext';
import { useHologram } from '../hooks/useHologram';
import { HologramControls } from '../components/HologramControls';
import { WidgetFrame } from './WidgetFrame';

// Detached hologram control panel. Owns its own useHologram instance; the
// backend keeps the physical fan's connection state, so status is consistent.
export function ControlsWidget() {
  const showToast = useToast();
  const hologram = useHologram({ onToast: showToast });

  return (
    <WidgetFrame title="Control del Holograma">
      <div className="flex-1 overflow-y-auto text-slate-100">
        <HologramControls holo={hologram} />
      </div>
    </WidgetFrame>
  );
}
