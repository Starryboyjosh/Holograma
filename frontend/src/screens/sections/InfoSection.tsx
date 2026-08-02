import { useToast } from '../../context/ToastContext';
import { GradientCard, SectionTitle } from '../../components/ui/Card';
import { Field, TextInput, Textarea } from '../../components/ui/Field';
import { useUnevContent } from '../../hooks/useUnevContent';
import { ScreenHero } from '../../components/holomind/ScreenHero';
import { Wordmark } from '../../components/holomind/Wordmark';
import { BTN_DANGER, BTN_PRIMARY } from '../../theme';

// Friendly Spanish labels, in the order the backend expects (skills.unev_content
// TEXT_FIELDS). Single-line fields use an input; the rest a textarea.
const FIELD_LABELS: { key: string; label: string; short?: boolean }[] = [
  { key: 'name', label: 'Nombre corto', short: true },
  { key: 'full_name', label: 'Nombre completo', short: true },
  { key: 'website', label: 'Sitio web oficial', short: true },
  { key: 'values', label: 'Valores institucionales', short: true },
  { key: 'acronyms', label: 'Siglas y expansión (UNEV, CES, DES, ITEE…)' },
  { key: 'main_claim', label: 'Diferenciador principal' },
  { key: 'description', label: 'Descripción' },
  { key: 'mission', label: 'Misión' },
  { key: 'vision', label: 'Visión' },
  { key: 'approval', label: 'Aprobación / acreditación' },
  { key: 'governance', label: 'Gobernanza y liderazgo' },
  { key: 'address', label: 'Dirección' },
  { key: 'infrastructure', label: 'Infraestructura' },
  { key: 'academic_model', label: 'Modelo académico' },
  { key: 'faculty', label: 'Cuerpo docente' },
  { key: 'student_support', label: 'Acompañamiento estudiantil' },
  { key: 'admission_requirements', label: 'Requisitos de admisión' },
  { key: 'social_projection', label: 'Proyección social' },
  { key: 'virtual_library', label: 'Biblioteca virtual' },
  { key: 'international_presence', label: 'Presencia internacional' },
  { key: 'history', label: 'Historia y trayectoria' },
  { key: 'independence_note', label: 'Independencia (no confundir con UNED u otras)' },
  { key: 'itee_campus', label: 'Campus ITEE y alianza' },
  { key: 'expotech', label: 'ExpoTech / feria tecnológica ITEE' },
  { key: 'common_questions', label: 'Preguntas frecuentes (Q&A)' },
];

/**
 * INFO. UNEV (nodo 48:334).
 *
 * Fondo crema con arco navy arriba y tarjetas con degradado naranja→navy. Los campos
 * heredan el tono "glass" de `GradientCard`, así que se ven blancos sobre el
 * degradado sin pasar props uno a uno.
 */
export function InfoSection() {
  const showToast = useToast();
  const content = useUnevContent();

  const onSave = async () => {
    const result = await content.save();
    showToast(
      result.ok
        ? 'Contenido de UNEV guardado. El asistente ya usa la nueva información.'
        : `No se pudo guardar: ${result.message ?? 'error desconocido.'}`,
    );
  };

  return (
    <ScreenHero id="info" backdrop="cream" topArc>
      <div className="mx-auto w-full max-w-5xl px-6 pb-16">
        <header className="text-center">
          <h1 className="text-[32px] font-normal text-ink md:text-[44px]">
            Contenido de <Wordmark onCream>UNEV</Wordmark>
          </h1>
          <p className="mt-2 text-[14px] font-normal italic text-ink/80 md:text-[16px]">
            Única fuente de información institucional que utiliza el asistente. Edita y guarda.
          </p>
        </header>

        {content.loading ? (
          <GradientCard className="mt-10">
            <p className="text-[14px] text-white/85">Cargando contenido…</p>
          </GradientCard>
        ) : (
          <div className="mt-10 space-y-8">
            <GradientCard>
              <SectionTitle>Información institucional</SectionTitle>
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                {FIELD_LABELS.filter((f) => f.short).map((f) => (
                  <Field key={f.key} label={f.label}>
                    <TextInput
                      type="text"
                      value={content.fields[f.key] ?? ''}
                      onChange={(e) => content.setField(f.key, e.target.value)}
                    />
                  </Field>
                ))}
              </div>
              <div className="space-y-4 pt-2">
                {FIELD_LABELS.filter((f) => !f.short).map((f) => (
                  <Field key={f.key} label={f.label}>
                    <Textarea
                      rows={3}
                      value={content.fields[f.key] ?? ''}
                      onChange={(e) => content.setField(f.key, e.target.value)}
                    />
                  </Field>
                ))}
              </div>
            </GradientCard>

            <GradientCard>
              <div className="flex flex-wrap items-center justify-between gap-3">
                <SectionTitle>Carreras</SectionTitle>
                <button
                  type="button"
                  onClick={content.addProgram}
                  className="rounded-[50px] bg-black/25 px-5 py-2 text-[14px] font-semibold italic text-white transition-opacity hover:opacity-85"
                >
                  + Agregar
                </button>
              </div>
              <div className="space-y-5">
                {content.programs.length === 0 && (
                  <p className="text-[14px] text-white/75">Sin carreras. Agrega una.</p>
                )}
                {content.programs.map((program, index) => (
                  <div key={index} className="space-y-3">
                    <div className="flex flex-wrap items-center gap-3">
                      <div className="min-w-[240px] flex-1">
                        <TextInput
                          type="text"
                          placeholder="Nombre de la carrera"
                          value={program.name}
                          onChange={(e) => content.updateProgram(index, { name: e.target.value })}
                        />
                      </div>
                      <button
                        type="button"
                        onClick={() => content.removeProgram(index)}
                        className={`${BTN_DANGER} shrink-0`}
                        title="Eliminar carrera"
                      >
                        Eliminar
                      </button>
                    </div>
                    <Textarea
                      rows={2}
                      placeholder="Descripción"
                      value={program.desc}
                      onChange={(e) => content.updateProgram(index, { desc: e.target.value })}
                    />
                  </div>
                ))}
              </div>
            </GradientCard>

            <div className="flex justify-end pt-2">
              <button
                onClick={onSave}
                disabled={content.saving}
                className={`${BTN_PRIMARY} w-full py-4 sm:w-auto`}
              >
                {content.saving ? 'Guardando…' : 'Guardar contenido'}
              </button>
            </div>
          </div>
        )}
      </div>
    </ScreenHero>
  );
}
