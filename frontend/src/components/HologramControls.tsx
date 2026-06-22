import { useHologram } from '../hooks/useHologram';
import { Card, SectionTitle } from './ui/Card';
import { Field, TextInput } from './ui/Field';

type Hologram = ReturnType<typeof useHologram>;

const QUICK_COMMANDS = [
  'start',
  'play',
  'pause',
  'shutdown',
  'loop_current',
  'brightness_up',
  'brightness_down',
  'next_file',
  'prev_file',
];

const NEUTRAL_BTN =
  'py-3 text-xs font-bold rounded-xl transition-all bg-gray-100 hover:bg-gray-200 text-gray-700 ' +
  'dark:bg-slate-800 dark:hover:bg-slate-700 dark:text-slate-200';

// The full MISSYOU hologram control surface, shared by the Remote screen and the
// detached controls widget (each passes its own useHologram instance).
export function HologramControls({ holo }: { holo: Hologram }) {
  return (
    <>
      <div className="columns-1 md:columns-2 gap-6 space-y-6 md:space-y-0 [column-fill:balance]">
        {/* Conexión */}
        <Card masonry>
          <SectionTitle>Conexión</SectionTitle>
          <div className="space-y-3">
            <Field label="Dirección IP">
              <TextInput
                type="text"
                value={holo.holoIp}
                onChange={(e) => holo.setHoloIp(e.target.value)}
                placeholder="10.10.10.1"
              />
            </Field>
            <Field label="Puerto">
              <TextInput type="number" value={holo.holoPort} onChange={(e) => holo.setHoloPort(Number(e.target.value))} />
            </Field>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className={`w-2.5 h-2.5 rounded-full animate-pulse ${holo.holoConnected ? 'bg-emerald-400' : 'bg-rose-500'}`}></span>
                <span className="text-xs font-bold">{holo.holoConnected ? 'Conectado' : 'Desconectado'}</span>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={holo.connect}
                  className="px-4 py-2 bg-[#E25C1D] hover:bg-orange-600 text-white font-bold text-xs rounded-xl transition-all"
                >
                  Conectar
                </button>
                <button
                  onClick={holo.disconnect}
                  className="px-4 py-2 text-xs font-bold rounded-xl transition-all bg-rose-50 hover:bg-rose-100 text-rose-600 dark:bg-rose-500/20 dark:hover:bg-rose-500/30 dark:text-rose-400"
                >
                  Desconectar
                </button>
              </div>
            </div>
            {holo.holoStatusMsg && (
              <p className={`text-[10px] ${holo.holoConnected ? 'text-emerald-400' : 'text-gray-500 dark:text-slate-500'}`}>
                {holo.holoStatusMsg}
              </p>
            )}
          </div>
        </Card>

        {/* Reproducción */}
        <Card masonry>
          <SectionTitle>Reproducción</SectionTitle>
          <div className="grid grid-cols-2 gap-2">
            <button onClick={() => holo.command('start')} className="py-3 bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs rounded-xl transition-all">
              ▶ Iniciar
            </button>
            <button onClick={() => holo.command('shutdown')} className="py-3 bg-rose-600 hover:bg-rose-700 text-white font-bold text-xs rounded-xl transition-all">
              ⏹ Detener
            </button>
            <button onClick={() => holo.command('pause')} className={NEUTRAL_BTN}>
              ⏸ Pausa
            </button>
            <button onClick={() => holo.command('play')} className={NEUTRAL_BTN}>
              ▶ Reanudar
            </button>
          </div>
          <button
            onClick={() => holo.command('loop_current')}
            className="w-full py-3 text-xs font-bold rounded-xl transition-all bg-amber-50 hover:bg-amber-100 text-amber-600 border border-amber-200 dark:bg-amber-500/10 dark:hover:bg-amber-500/20 dark:text-amber-400 dark:border-amber-500/20"
          >
            🔁 Loop del Clip Actual
          </button>
        </Card>

        {/* Navegación de clips */}
        <Card masonry>
          <SectionTitle>Navegación de Clips</SectionTitle>
          <div className="grid grid-cols-2 gap-2">
            <button onClick={() => holo.command('prev_file')} className={NEUTRAL_BTN}>
              ⏮ Anterior
            </button>
            <button onClick={() => holo.command('next_file')} className={NEUTRAL_BTN}>
              ⏭ Siguiente
            </button>
          </div>
          <div className="flex items-center gap-2 pt-2">
            <label className="text-xs font-semibold text-gray-600 dark:text-gray-400">Clip #:</label>
            <TextInput
              type="number"
              min={0}
              max={255}
              value={holo.clipNumber}
              onChange={(e) => holo.setClipNumber(Number(e.target.value))}
              className="w-20 text-center"
            />
            <button
              onClick={() => holo.command('play_file', holo.clipNumber)}
              className="px-4 py-2 bg-[#E25C1D] hover:bg-orange-600 text-white font-bold text-xs rounded-xl transition-all"
            >
              Ir al Clip
            </button>
          </div>
        </Card>

        {/* Brillo */}
        <Card masonry>
          <SectionTitle>Brillo</SectionTitle>
          <div className="grid grid-cols-2 gap-2">
            <button onClick={() => holo.command('brightness_down')} className={NEUTRAL_BTN}>
              🔅 Bajar Brillo
            </button>
            <button onClick={() => holo.command('brightness_up')} className={NEUTRAL_BTN}>
              🔆 Subir Brillo
            </button>
          </div>
        </Card>
      </div>

      <Card>
        <SectionTitle>Comandos Rápidos</SectionTitle>
        <div className="flex flex-wrap gap-2">
          {QUICK_COMMANDS.map((cmd) => (
            <button
              key={cmd}
              onClick={() => holo.command(cmd)}
              className="px-3 py-1.5 text-[10px] font-bold rounded-lg transition-all bg-gray-100 hover:bg-gray-200 text-gray-600 border border-gray-200 dark:bg-slate-800 dark:hover:bg-slate-700 dark:text-slate-300 dark:border-slate-700"
            >
              {cmd.replace(/_/g, ' ')}
            </button>
          ))}
        </div>
        <p className="text-[10px] text-slate-500 pt-1">Protocolo MISSYOU | Puerto TCP 50200 | Comandos de 3 bytes</p>
      </Card>
    </>
  );
}
