import { useSession } from '../context/SessionContext';
import { HologramControls } from '../components/HologramControls';
import { DetachButton } from '../components/DetachButton';

export function RemoteScreen() {
  const { hologram } = useSession();

  return (
    <div className="w-full max-w-4xl space-y-6 py-4 text-slate-800 dark:text-slate-100">
      <div className="flex justify-between items-center pb-4 border-b border-gray-200 dark:border-slate-800">
        <div>
          <h1 className="text-2xl font-black text-[#1C2D5A] dark:text-white">Control Remoto del Holograma</h1>
          <p className="text-xs text-gray-600 dark:text-gray-400">Comandos TCP para el ventilador holográfico MISSYOU</p>
        </div>
        <DetachButton widget="controls" className="bg-gray-100 text-gray-600 dark:bg-slate-800 dark:text-slate-200" />
      </div>

      <HologramControls holo={hologram} />
    </div>
  );
}
