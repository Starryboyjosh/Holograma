"""Fuente única y editable de la información institucional de UNEV.

Antes, los datos de UNEV vivían a la vez en ``DEFAULT_UNEV_INFO`` (en código) y en
``data/unev_info.json`` (parcial y desactualizado): el contenido en ejecución era
una mezcla ambigua de ambos. Este módulo deja **una sola fuente autoritativa**:

* ``data/unev_info.json`` es el contenido vigente y **editable** (vía la pantalla
  "Contenido" / endpoints ``/api/unev-content``).
* ``DEFAULT_UNEV_INFO`` es solo un respaldo de emergencia si el archivo falta o se
  corrompe.

Todo (``skills/university.py``, el prompt del sistema, …) lee de aquí mediante
``get_unev_info()``. Sin dependencias del backend pesado: testeable con pytest.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from security import clamp_text

BASE_DIR = Path(__file__).resolve().parent.parent
JSON_PATH = BASE_DIR / "data" / "unev_info.json"

# Tope generoso por campo: acota el tamaño del prompt sin estorbar al operador.
MAX_FIELD_CHARS = 4000

# Campos de texto en el orden en que se muestran en el editor.
TEXT_FIELDS: tuple[str, ...] = (
    "name",
    "full_name",
    "main_claim",
    "description",
    "mission",
    "vision",
    "values",
    "approval",
    "governance",
    "address",
    "infrastructure",
    "academic_model",
    "faculty",
    "student_support",
    "admission_requirements",
    "social_projection",
    "virtual_library",
    "international_presence",
    "website",
)

DEFAULT_UNEV_INFO: dict = {
    "name": "UNEV",
    "full_name": "Instituto Universitario de Educación Virtual",
    "description": (
        "El Instituto Universitario de Educación Virtual (UNEV) es una institución "
        "de educación superior hondureña, secular y contemporánea, con un modelo "
        "100% virtual diseñado para mitigar las brechas de cobertura y conectividad "
        "en el país, ofreciendo formación técnica accesible a poblaciones vulnerables "
        "y geográficamente aisladas. Es totalmente independiente de la Universidad "
        "Nacional Evangélica de la República Dominicana, enfocándose estrictamente "
        "en la competitividad técnica y la inserción expedita en la economía del "
        "conocimiento. Su trayectoria inició en 2017 como 'Universidad Práctica' y "
        "alcanzó consolidación internacional en eventos como EDUTECHNIA 2023 en Bogotá."
    ),
    "main_claim": (
        "Primera universidad 100% virtual en Honduras, enfocada en competitividad "
        "técnica e inserción expedita en la economía del conocimiento."
    ),
    "mission": (
        "Formar profesionales líderes con competencias técnicas y tecnológicas a "
        "nivel nacional e internacional, mediante un modelo de enseñanza práctica, "
        "usando la virtualidad y personal certificado, garantizando la incorporación "
        "a los mercados que requiere el nuevo mundo empresarial."
    ),
    "vision": (
        "Consolidarnos como la Institución de Educación Virtual líder en Honduras y "
        "ser un referente a nivel nacional e internacional en la formación de "
        "profesionales competentes, aptos, íntegros y emprendedores que contribuyan "
        "al desarrollo sostenible del País, revolucionando y adaptando la educación "
        "al mundo moderno y posicionándola al alcance de la población."
    ),
    "values": "Equidad, Honestidad, Perseverancia, Ética, Excelencia y Respeto.",
    "approval": (
        "Aprobada por el Consejo de Educación Superior (CES) mediante el Acuerdo "
        "No. 4995-381-2023 del 9 de junio de 2023, con admisión a trámite previa "
        "según Acuerdo No. 3827-327-2018. Su validez institucional fue ratificada "
        "el 3 de mayo de 2024 con la visita oficial del Rector de la UNAH, "
        "Dr. Odir Fernández, acompañado por la Máster Cleopatra Duarte (Directora "
        "de la DES), la Máster Norma Martínez (JDU), el Dr. Elmer Fernández "
        "(SED-UNAH) y el Máster Oziel Fernández Herrera. Los títulos poseen plena "
        "seguridad jurídica para el ejercicio profesional nacional e internacional "
        "al estar integrados en el registro oficial de la Dirección de Educación "
        "Superior (DES)."
    ),
    "governance": (
        "UNEV es dirigida por un Consejo Administrativo con autonomía estratégica, "
        "bajo el liderazgo del Ingeniero y Fundador Raúl Peña Moreno y su Consejo Académico."
    ),
    "address": (
        "Colonia Trejo, entre 9 y 10 calle, 21 avenida C, instalaciones del ITEE "
        "(Instituto Tecnológico de Electricidad y Electrónica), Edificio 1, ala "
        "izquierda, segunda planta, San Pedro Sula, Cortés."
    ),
    "infrastructure": (
        "La sede central opera bajo una estrategia de Lean OpEx mediante alianza "
        "estratégica de co-working con el ITEE, lo que permite acceder a redes de "
        "conectividad simétrica de alta disponibilidad y soporte técnico de red "
        "centralizado en una zona de alta accesibilidad y seguridad en San Pedro Sula. "
        "Esta sinergia optimiza costos operativos y prioriza la inversión en el "
        "campus digital y plataformas de aprendizaje (LMS)."
    ),
    "website": "[https://unev.edu.hn/](https://unev.edu.hn/)",
    "academic_model": (
        "Modelo 'Agile Learning' basado en el formato de Técnico Universitario "
        "(Tecnólogo). El diseño curricular se compone de ciclos intensivos de "
        "11 semanas con rotación cuatrimestral, lo que acelera la profesionalización "
        "reduciendo el tiempo de formación en un 50% respecto a una licenciatura "
        "tradicional, sin comprometer el rigor académico."
    ),
    "faculty": (
        "Planta docente híbrida que combina perspectiva global con ejecución local. "
        "Destacan perfiles como Nathalie Cuadrado (internacional, Colombia, con más "
        "de 15 años de experiencia en retail y diseño editorial), Cesar Arguijo "
        "(especialista en Ofimática) y Gladys Ferrufino (coordinadora de "
        "comunicación lingüística)."
    ),
    "student_support": (
        "El ecosistema de retención incluye una inducción de dos semanas, programas "
        "de mentoría y el Sistema de Alerta Temprana (SAT), que permite un "
        "Data-driven Student Lifecycle Management. El SAT monitorea algorítmicamente "
        "patrones de inactividad o bajo rendimiento y ejecuta intervención humana "
        "en un plazo de 48 a 72 horas para prevenir la deserción."
    ),
    "admission_requirements": (
        "Carga digital de Título de Educación Media (PDF), DNI y Certificación de "
        "Nacimiento (sin RNP). Evaluación Diagnóstica de Tecnología y Ofimática "
        "(30 minutos) con puntaje mínimo del 70% para ingreso directo. Quienes no "
        "alcancen el puntaje mínimo deben cursar el Programa de Inmersión y "
        "Nivelación Digital (PRIND), un andamiaje obligatorio que asegura el dominio "
        "de las herramientas asincrónicas antes de iniciar la carga técnica."
    ),
    "social_projection": (
        "El Proyecto Tecnoaulas es la estrategia de proyección social de UNEV: "
        "espacios físicos con internet simétrico y hardware de alta gama, con "
        "objetivo de desplegar 50 unidades a nivel nacional. Complementariamente, "
        "la Tienda Virtual de Servicios Sociales registra y digitaliza los proyectos "
        "de vinculación de los estudiantes (como soluciones de gestión para "
        "microempresas) para replicarlos en otras comunidades, conformando una "
        "economía circular del conocimiento."
    ),
    "virtual_library": (
        "La Biblioteca Virtual centraliza el acceso a información en cuatro "
        "dimensiones: (1) Repositorio de libros con consulta simultánea e ilimitada; "
        "(2) Biblioteca Digital de Ciencia y Tecnología con revistas indexadas e "
        "investigaciones de vanguardia; (3) Bibliotecas externas con enlaces a "
        "fuentes de autoridad como la RAE; (4) Guías metodológicas interactivas "
        "para aplicación de normas APA y técnicas de investigación."
    ),
    "international_presence": (
        "UNEV participa en redes internacionales de negocios y programas de "
        "certificación de mentores (Red GIEN), lo que posiciona a sus egresados en "
        "una red de contactos global. Tuvo consolidación internacional en eventos "
        "como EDUTECHNIA 2023 en Bogotá."
    ),
    "programs": {
        "diseño gráfico": (
            "El Técnico Universitario en Diseño Gráfico  tiene un "
            "enfoque en ilustración digital, maquetación editorial, identidad "
            "corporativa y taller de animación, con una clara visión de emprendimiento "
            "digital. Cuenta con 93 créditos totales, 24 asignaturas y una duración "
            "de 2 años bajo el modelo cuatrimestral de ciclos intensivos de 11 semanas."
        ),
        "administración de empresas": (
            "El Técnico Universitario en Administración de Empresas "
            "se especializa en logística, gestión de proyectos, mercadeo digital y "
            "contabilidad aplicada a la resolución de problemas reales. Cuenta con "
            "90 créditos totales, 24 asignaturas y una duración de 2 años bajo el "
            "modelo cuatrimestral de ciclos intensivos de 11 semanas."
        ),
        "programación web": (
            "El Técnico Universitario en Programación Web  ofrece "
            "una formación integral en el desarrollo de aplicaciones seguras, "
            "arquitectura de software y gestión de bases de datos. Tiene una duración "
            "de 2 años bajo el modelo cuatrimestral de ciclos intensivos de 11 semanas, "
            "y se encuentra en fase de actualización de registro ante la DES para el "
            "ciclo 2024."
        ),
    },
}

_cache: dict | None = None


def _coerce(data: object) -> dict:
    """Normaliza ``data`` a la forma canónica, rellenando faltantes con el respaldo."""
    src = data if isinstance(data, dict) else {}
    info: dict = {}
    for key in TEXT_FIELDS:
        value = src.get(key, DEFAULT_UNEV_INFO[key])
        info[key] = clamp_text(value if isinstance(value, str) else str(value), MAX_FIELD_CHARS)

    programs: dict[str, str] = {}
    raw_programs = src.get("programs")
    if isinstance(raw_programs, dict):
        for prog_key, prog_desc in raw_programs.items():
            name = str(prog_key).lower().strip()
            if name:
                programs[name] = clamp_text(str(prog_desc), MAX_FIELD_CHARS)
    info["programs"] = programs or {
        k: clamp_text(v, MAX_FIELD_CHARS) for k, v in DEFAULT_UNEV_INFO["programs"].items()
    }
    return info


def validate_unev_info(data: object) -> list[str]:
    """Devuelve una lista de errores (vacía = válido) para mostrar al operador."""
    if not isinstance(data, dict):
        return ["El contenido debe ser un objeto JSON."]

    errors: list[str] = []
    for key in TEXT_FIELDS:
        if key in data and not isinstance(data[key], str):
            errors.append(f"El campo '{key}' debe ser texto.")
    if "programs" in data and not isinstance(data["programs"], dict):
        errors.append("'programs' debe ser un objeto (nombre de carrera → descripción).")

    merged = _coerce(data)
    if not merged["name"].strip():
        errors.append("El nombre de la institución no puede quedar vacío.")
    if not merged["description"].strip():
        errors.append("La descripción no puede quedar vacía.")
    return errors


def load_unev_info(path: Path | str = JSON_PATH) -> dict:
    """Carga el contenido desde el JSON autoritativo; respaldo en código si falla."""
    p = Path(path)
    if p.exists():
        try:
            return _coerce(json.loads(p.read_text(encoding="utf-8")))
        except Exception as error:  # noqa: BLE001 - degradar a respaldo es lo seguro
            print(f"AVISO: no se pudo cargar {p}. Usando respaldo en código. Error: {error}")
    return _coerce({})


def get_unev_info() -> dict:
    """Contenido vigente (cacheado). Llamado por las skills en cada respuesta."""
    global _cache
    if _cache is None:
        _cache = load_unev_info()
    return _cache


def reload() -> dict:
    """Recarga desde disco (tras una edición) y actualiza la caché."""
    global _cache
    _cache = load_unev_info()
    return _cache


def save_unev_info(data: object, path: Path | str = JSON_PATH) -> dict:
    """Valida, escribe atómicamente el JSON autoritativo y recarga la caché.

    Lanza ``ValueError`` con un mensaje accionable si el contenido es inválido.
    """
    errors = validate_unev_info(data)
    if errors:
        raise ValueError("; ".join(errors))

    merged = _coerce(data)
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(f".{p.name}.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, p)

    global _cache
    _cache = merged
    return merged
