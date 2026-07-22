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
MAX_FIELD_CHARS = 8000

# Campos de texto en el orden en que se muestran en el editor.
TEXT_FIELDS: tuple[str, ...] = (
    "name",
    "full_name",
    "acronyms",
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
    "history",
    "independence_note",
    "itee_campus",
    "expotech",
    "common_questions",
)

DEFAULT_UNEV_INFO: dict = {
    "name": "UNEV",
    "full_name": "Instituto Universitario de Educación Virtual",
    "acronyms": (
        "UNEV = Instituto Universitario de Educación Virtual (Honduras). "
        "No confundir con UNED (Universidad Nacional de Educación a Distancia de España) "
        "ni con instituciones homónimas de otros países. Otras siglas del ecosistema: "
        "CES = Consejo de Educación Superior; DES = Dirección de Educación Superior; "
        "UNAH = Universidad Nacional Autónoma de Honduras; PRIND = Programa de Inmersión "
        "y Nivelación Digital; SAT = Sistema de Alerta Temprana; LMS = Learning Management "
        "System (plataforma de aprendizaje); ITEE = Instituto Tecnológico de Excelencia "
        "Educativa (campus donde opera la sede de UNEV en San Pedro Sula)."
    ),
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
    "history": (
        "La trayectoria de UNEV inició en 2017 bajo la denominación 'Universidad "
        "Práctica'. Tras el proceso de admisión a trámite ante el Consejo de Educación "
        "Superior (Acuerdo No. 3827-327-2018), obtuvo la aprobación institucional "
        "mediante el Acuerdo CES No. 4995-381-2023 del 9 de junio de 2023. En 2023 "
        "consolidó presencia internacional en EDUTECHNIA (Bogotá). El 3 de mayo de 2024 "
        "su validez fue ratificada con la visita oficial del Rector de la UNAH y "
        "autoridades de la Dirección de Educación Superior (DES)."
    ),
    "independence_note": (
        "UNEV (Honduras) es una institución hondureña independiente. No es la "
        "Universidad Nacional de Educación a Distancia (UNED) de España, ni la "
        "Universidad Nacional Evangélica de la República Dominicana, ni otras "
        "entidades con siglas parecidas. Cuando el visitante diga o el STT escriba "
        "'UNED', en este kiosco se refiere a UNEV."
    ),
    "itee_campus": (
        "La sede física de UNEV en San Pedro Sula opera en alianza de co-working con "
        "el ITEE (Instituto Tecnológico de Excelencia Educativa), campus en Colonia "
        "Trejo, entre 9 y 10 calle, 21 avenida C, Edificio 1, ala izquierda, segunda "
        "planta, Cortés, Honduras. El ITEE es un centro de formación técnica y "
        "tecnológica de larga trayectoria (más de tres décadas), rectorado por el "
        "Ingeniero Raúl Peña Moreno (también fundador de UNEV). Ofrece formación en "
        "áreas como Electromecánica, Diseño Gráfico, Mecatrónica y Programación. "
        "Contactos públicos del campus ITEE: teléfonos 9624-1912, 9557-0304 y "
        "2558-5272; correo info@iteesa.edu.hn; web https://iteesa.edu.hn/. La alianza "
        "permite a UNEV redes de conectividad de alta disponibilidad y soporte técnico "
        "centralizado, optimizando costos (Lean OpEx) e invirtiendo en el campus digital."
    ),
    "expotech": (
        "ExpoTech (también escrita Expo Tech o Feria Tecnológica del ITEE) es la feria "
        "tecnológica anual del Instituto Tecnológico de Excelencia Educativa (ITEE), "
        "en el campus de Colonia Trejo, 9-10 calle, 21 avenida C, San Pedro Sula, "
        "Cortés, Honduras. Es un evento histórico de la institución: en 2025 se "
        "celebró la 38.ª edición (Expo Tech 2025), del 16 al 18 de octubre, con unos "
        "60 proyectos estudiantiles y charlas técnicas abiertas al público sin costo. "
        "Horarios típicos de esa edición: jueves y viernes 10:00 a 19:00; sábado 8:00 "
        "a 14:00. El Grand Opening se realizó el miércoles 15 de octubre a las 19:00. "
        "Objetivo: que los estudiantes apliquen conocimientos del año académico en "
        "soluciones a retos comunitarios, industriales y de TIC, y se vinculen con "
        "empresas y la comunidad. Coordinación referida en prensa 2025: Fredy Estrada "
        "(coordinador Expo Tech); declaraciones del Ing. Icker Peña (director "
        "financiero ITEE). Actividades asociadas: expo de proyectos, charlas "
        "(seguridad informática, microcontroladores, etc.), Glam & Star Nite, "
        "Olimpiadas de Matemáticas y Tech Party. Patrocinadores mencionados en "
        "cobertura 2025: Cervecería Hondureña, Sycom, Aceyco, Servi Rey, Unitec y "
        "Emsula. UNEV comparte campus con el ITEE; visitantes de ExpoTech pueden "
        "conocer también la oferta 100% virtual de UNEV en el mismo predio. Para "
        "fechas de ediciones futuras conviene confirmar en https://iteesa.edu.hn/ o "
        "redes del ITEE (@iteesa_hn)."
    ),
    "common_questions": (
        "P: ¿Qué significan las siglas UNEV?\n"
        "R: Instituto Universitario de Educación Virtual (Honduras).\n\n"
        "P: ¿UNEV es lo mismo que UNED?\n"
        "R: No. UNED suele referirse a la universidad española de educación a "
        "distancia. Aquí la institución correcta es UNEV.\n\n"
        "P: ¿Es 100% virtual?\n"
        "R: Sí. El modelo académico es 100% virtual; la sede en ITEE Colonia Trejo "
        "es de apoyo operativo y atención, no un campus presencial tradicional.\n\n"
        "P: ¿Dónde está ubicada?\n"
        "R: Colonia Trejo, entre 9 y 10 calle, 21 avenida C, instalaciones del ITEE, "
        "Edificio 1, ala izquierda, segunda planta, San Pedro Sula, Cortés, Honduras.\n\n"
        "P: ¿Quién la fundó / dirige?\n"
        "R: Ingeniero Raúl Peña Moreno (fundador) y Consejo Administrativo / Consejo "
        "Académico.\n\n"
        "P: ¿Está aprobada oficialmente?\n"
        "R: Sí, por el CES (Acuerdo No. 4995-381-2023, 9 de junio de 2023). Títulos "
        "integrados en el registro de la DES.\n\n"
        "P: ¿Qué carreras ofrece?\n"
        "R: Técnicos Universitarios en Diseño Gráfico, Administración de Empresas y "
        "Programación Web (ciclos de 11 semanas, ~2 años).\n\n"
        "P: ¿Cómo es la admisión?\n"
        "R: Título de educación media (PDF), DNI, certificación de nacimiento; "
        "evaluación diagnóstica de tecnología y ofimática (30 min, mínimo 70%). Si no "
        "alcanza el puntaje, cursa PRIND.\n\n"
        "P: ¿Cuál es el sitio web?\n"
        "R: https://unev.edu.hn/\n\n"
        "P: ¿Qué es ExpoTech / la feria tecnológica del ITEE?\n"
        "R: Feria tecnológica anual del ITEE en el mismo campus (Colonia Trejo, SPS). "
        "En 2025 fue la 38.ª edición (16–18 oct.), con ~60 proyectos y charlas abiertas.\n\n"
        "P: ¿UNEV y el ITEE son lo mismo?\n"
        "R: No. ITEE es el instituto tecnológico de excelencia educativa (formación "
        "técnica media/superior tecnológica). UNEV es la universidad 100% virtual de "
        "educación superior. Comparten campus y liderazgo fundacional, con misiones "
        "distintas y complementarias."
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


def _invalidate_skill_caches() -> None:
    """Tras cambiar UNEV, invalidar contexto LLM y hotwords STT derivados."""
    try:
        from skills.university import invalidate_context_cache

        invalidate_context_cache()
    except Exception:
        pass
    try:
        import stt.listener as stt_listener

        stt_listener._HOTWORDS_CACHE["signature"] = None
        stt_listener._HOTWORDS_CACHE["value"] = None
    except Exception:
        pass


def reload() -> dict:
    """Recarga desde disco (tras una edición) y actualiza la caché."""
    global _cache
    _cache = load_unev_info()
    _invalidate_skill_caches()
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
    _invalidate_skill_caches()
    return merged
