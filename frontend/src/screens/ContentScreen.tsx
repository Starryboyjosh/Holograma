import { useToast } from '../context/ToastContext';
import { Card, SectionTitle } from '../components/ui/Card';
import { Field, TextInput, Textarea } from '../components/ui/Field';
import { useUnevContent } from '../hooks/useUnevContent';

// Friendly Spanish labels, in the order the backend expects (skills.unev_content
// TEXT_FIELDS). Single-line fields use an input; the rest a textarea.
const FIELD_LABELS: { key: string; label: string; short?: boolean }[] = [
  { key: 'name', label: 'Nombre corto', short: true },
  { key: 'full_name', label: 'Nombre completo', short: true },
  { key: 'website', label: 'Sitio web oficial', short: true },
  { key: 'values', label: 'Valores institucionales', short: true },
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
];

export function ContentScreen() {
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
    <div className="w-full max-w-4xl space-y-6 py-4 text-slate-800 dark:text-slate-100">
      <div className="flex justify-between items-center pb-4 border-b border-gray-200 dark:border-slate-800">
        <div>
          <h1 className="text-2xl font-black text-[#1C2D5A] dark:text-white">Contenido de UNEV</h1>
          <p className="text-xs text-gray-600 dark:text-gray-400">
            Fuente única de la información institucional que usa el asistente. Edita y guarda.
          </p>
        </div>
      </div>

      {content.loading ? (
        <Card>
          <p className="text-sm text-gray-600 dark:text-gray-400">Cargando contenido…</p>
        </Card>
      ) : (
        <>
          <Card>
            <SectionTitle>Información institucional</SectionTitle>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
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
          </Card>

          <Card>
            <div className="flex items-center justify-between">
              <SectionTitle>Carreras</SectionTitle>
              <button
                type="button"
                onClick={content.addProgram}
                className="text-xs font-bold uppercase tracking-wider px-3 py-2 rounded-xl bg-gray-100 hover:bg-gray-200 border border-gray-200 text-gray-700 dark:bg-slate-900 dark:hover:bg-slate-800 dark:border-slate-800 dark:text-slate-300"
              >
                + Agregar
              </button>
            </div>
            <div className="space-y-4">
              {content.programs.length === 0 && (
                <p className="text-xs text-gray-500 dark:text-gray-400">Sin carreras. Agrega una.</p>
              )}
              {content.programs.map((program, index) => (
                <div
                  key={index}
                  className="space-y-2 p-3 rounded-2xl border border-gray-200 dark:border-slate-800"
                >
                  <div className="flex items-center gap-2">
                    <TextInput
                      type="text"
                      placeholder="Nombre de la carrera"
                      value={program.name}
                      onChange={(e) => content.updateProgram(index, { name: e.target.value })}
                    />
                    <button
                      type="button"
                      onClick={() => content.removeProgram(index)}
                      className="shrink-0 px-3 py-2 rounded-xl text-xs font-bold text-red-500 hover:bg-red-500/10 border border-red-500/30"
                      title="Eliminar carrera"
                    >
                      Eliminar
                    </button>
                  </div>
                  <Textarea
                    rows={2}
                    placeholder="Descripción de la carrera"
                    value={program.desc}
                    onChange={(e) => content.updateProgram(index, { desc: e.target.value })}
                  />
                </div>
              ))}
            </div>
          </Card>

          <div className="pt-2 flex justify-end">
            <button
              onClick={onSave}
              disabled={content.saving}
              className="w-full sm:w-auto px-8 py-4 bg-[#E25C1D] hover:bg-orange-600 disabled:opacity-50 disabled:cursor-not-allowed text-white font-bold text-sm rounded-2xl shadow-xl shadow-[#E25C1D]/10 transition-all text-center"
            >
              {content.saving ? 'Guardando…' : 'Guardar contenido'}
            </button>
          </div>
        </>
      )}
    </div>
  );
}
