import { useHologram } from '../hooks/useHologram';
import { Card } from './ui/Card';
import { Field, TextInput } from './ui/Field';

type Hologram = ReturnType<typeof useHologram>;

/**
 * CONEXIÓN DEL HOLOGRAMA — la tarjeta que abre CONFIGURACIÓN en el diseño
 * (bloque superior del nodo 63:36, sobre la malla degradada).
 *
 * El diseño la presenta como tarjeta de cristal con el título centrado y
 * CONECTAR / DESCONECTAR como una pastilla partida (naranja + navy).
 */
export function HologramConnection({ holo }: { holo: Hologram }) {
  return (
    <Card>
      <div className="text-center">
        <h3 className="text-[20px] font-bold uppercase tracking-wide text-white md:text-[24px]">
          Conexión del holograma
        </h3>
        <p className="mx-auto mt-2 max-w-2xl text-[13px] italic leading-relaxed text-white/85">
          La IA selecciona los clips automáticamente cuando escucha, piensa, habla o queda en
          espera.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-[minmax(0,1fr)_10rem]">
        <Field label="Dirección IP:">
          <TextInput
            type="text"
            inputMode="decimal"
            value={holo.holoIp}
            onChange={(event) => holo.setHoloIp(event.target.value)}
            placeholder="10.10.10.1"
          />
        </Field>
        <Field label="Puerto TCP:">
          <TextInput
            type="number"
            min={1}
            max={65535}
            value={holo.holoPort}
            onChange={(event) => holo.setHoloPort(Number(event.target.value))}
          />
        </Field>
      </div>

      {/* Pastilla partida CONECTAR / DESCONECTAR (nodo 82:x). */}
      <div className="flex justify-center pt-2">
        <div className="inline-flex overflow-hidden rounded-[50px]">
          <button
            type="button"
            onClick={holo.connect}
            className="bg-orange px-7 py-2.5 text-[12px] font-semibold uppercase text-white transition-opacity hover:opacity-90"
          >
            {holo.holoConnected ? 'Reconectar' : 'Conectar'}
          </button>
          <button
            type="button"
            onClick={holo.disconnect}
            disabled={!holo.holoConnected && !holo.holoIp}
            className="bg-navy px-7 py-2.5 text-[12px] font-semibold uppercase text-white transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
          >
            Desconectar
          </button>
        </div>
      </div>

      <div className="flex items-center justify-center gap-3">
        <span
          className={`inline-flex w-fit items-center gap-2 rounded-[50px] px-3 py-1.5 text-[12px] font-bold ${
            holo.holoConnected
              ? 'bg-emerald-500/15 text-emerald-200'
              : 'bg-black/20 text-white/80'
          }`}
        >
          <span
            className={`h-2 w-2 rounded-full ${holo.holoConnected ? 'bg-emerald-400' : 'bg-white/50'}`}
          />
          {holo.holoConnected ? 'Conectado' : 'Desconectado'}
        </span>
      </div>

      <p className="min-h-4 text-center text-[12px] text-white/75" aria-live="polite">
        {holo.holoStatusMsg ?? 'Introduce la dirección del dispositivo para conectarlo.'}
      </p>
    </Card>
  );
}
