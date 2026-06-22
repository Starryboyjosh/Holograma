import { CameraFeed } from '../components/CameraFeed';
import { WidgetFrame } from './WidgetFrame';

// Detached camera window: just the live YOLO stream, filling the window.
export function CameraWidget() {
  return (
    <WidgetFrame title="Visión en vivo · YOLO">
      <CameraFeed enabled nonce={0} className="flex-1 rounded-2xl border border-slate-800" />
    </WidgetFrame>
  );
}
