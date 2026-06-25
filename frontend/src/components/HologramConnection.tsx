import { useHologram } from '../hooks/useHologram';
import { Card, SectionTitle } from './ui/Card';
import { Field, TextInput } from './ui/Field';

type Hologram = ReturnType<typeof useHologram>;

export function HologramConnection({ holo }: { holo: Hologram }) {
  return (
    <Card>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-1">
          <SectionTitle>Conexión del holograma</SectionTitle>
          <p className="max-w-2xl text-xs leading-relaxed text-gray-500 dark:text-slate-400">
            La IA selecciona los clips automáticamente cuando escucha, piensa, habla o queda en espera.
          </p>
        </div>
        <span
          className={`inline-flex w-fit items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-bold ${
            holo.holoConnected
              ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
              : 'border-slate-300 bg-slate-100 text-slate-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-400'
          }`}
        >
          <span className={`h-2 w-2 rounded-full ${holo.holoConnected ? 'bg-emerald-400' : 'bg-slate-400'}`} />
          {holo.holoConnected ? 'Conectado' : 'Desconectado'}
        </span>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-[minmax(0,1fr)_9rem]">
        <Field label="Dirección IP">
          <TextInput
            type="text"
            inputMode="decimal"
            value={holo.holoIp}
            onChange={(event) => holo.setHoloIp(event.target.value)}
            placeholder="10.10.10.1"
          />
        </Field>
        <Field label="Puerto TCP">
          <TextInput
            type="number"
            min={1}
            max={65535}
            value={holo.holoPort}
            onChange={(event) => holo.setHoloPort(Number(event.target.value))}
          />
        </Field>
      </div>

      <div className="flex flex-col gap-3 border-t border-gray-100 pt-4 dark:border-slate-800 sm:flex-row sm:items-center sm:justify-between">
        <p className="min-h-4 text-xs text-gray-500 dark:text-slate-400" aria-live="polite">
          {holo.holoStatusMsg ?? 'Introduce la dirección del dispositivo para conectarlo.'}
        </p>
        <div className="flex shrink-0 gap-2">
          <button
            type="button"
            onClick={holo.disconnect}
            disabled={!holo.holoConnected && !holo.holoIp}
            className="rounded-xl border border-gray-200 px-4 py-2.5 text-xs font-bold text-gray-600 transition-colors hover:bg-gray-100 disabled:cursor-not-allowed disabled:opacity-40 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
          >
            Desconectar
          </button>
          <button
            type="button"
            onClick={holo.connect}
            className="rounded-xl bg-[#E25C1D] px-5 py-2.5 text-xs font-bold text-white transition-colors hover:bg-orange-600"
          >
            {holo.holoConnected ? 'Reconectar' : 'Conectar'}
          </button>
        </div>
      </div>
    </Card>
  );
}
