from skills.university import (
    get_admission_info,
    get_approval_info,
    get_location_info,
    get_program_info,
    get_programs_summary,
    get_university_summary,
    get_website_info,
    normalize_text,
)
import skills.honduras as honduras


def route_local_skill(user_input):
    text = normalize_text(user_input)

    # Honduras specific routing
    if any(word in text for word in ["honduras", "hondureño", "hondureña", "hondureñismo", "hondureñismos"]):
        if any(word in text for word in ["procer", "proceres", "personaje", "personajes", "biografia"]):
            return honduras.get_proceres_info()
        if any(word in text for word in ["vulgarismo", "vulgarismos", "habla", "voseo", "leismo", "minimo"]):
            return honduras.get_vulgarismos_info()
        if any(word in text for word in ["simbolo", "simbolos", "patrio", "patrios", "piah", "oit", "convenio"]):
            return honduras.get_simbolos_patrios_info()
        if any(word in text for word in ["carrera", "carreras", "programa", "programas", "periodo", "periodos", "historia"]):
            return honduras.get_programs_summary()
        if any(word in text for word in ["ubicacion", "direccion", "donde queda", "capital", "tegucigalpa"]):
            return honduras.get_location_info()
        if any(word in text for word in ["pagina", "sitio", "website", "url", "web"]):
            return honduras.get_website_info()
        if any(word in text for word in ["admision", "admisiones", "inscripcion", "matricula", "ingresar"]):
            return honduras.get_admission_info()
        if any(word in text for word in ["aprobacion", "aprobada", "oficial", "convenio 169"]):
            return honduras.get_approval_info()
        return honduras.get_university_summary()

    if any(word in text for word in ["procer", "proceres", "personaje", "personajes", "membreño", "cruz castro", "annarella", "bernardez"]):
        return honduras.get_proceres_info()

    if any(word in text for word in ["vulgarismo", "vulgarismos", "habla", "voseo", "leismo", "minimo"]):
        return honduras.get_vulgarismos_info()

    if any(word in text for word in ["simbolo", "simbolos", "patrio", "patrios", "piah", "oit", "convenio"]):
        return honduras.get_simbolos_patrios_info()

    if "era precolombina" in text or "precolombina" in text or "ancestral" in text:
        return honduras.get_program_info("era precolombina y ancestral")
    if "linguistica" in text or "lingüística" in text or "colonial" in text:
        return honduras.get_program_info("evolución lingüística y colonial")
    if "investigacion y reconocimiento" in text or "investigación" in text or "reconocimiento" in text:
        return honduras.get_program_info("periodo de investigación y reconocimiento (s. xix-xx)")
    if "contemporaneo" in text or "contemporáneo" in text or "salvaguarda" in text:
        return honduras.get_program_info("periodo contemporáneo y salvaguarda (2022-2035)")

    # UNEV specific routing
    if any(
        word in text
        for word in ["carreras", "programas", "oferta academica", "que puedo estudiar"]
    ):
        return get_programs_summary()

    if "diseno" in text or "grafico" in text:
        return get_program_info("diseño gráfico")

    if "administracion" in text or "empresa" in text:
        return get_program_info("administración de empresas")

    if any(word in text for word in ["pagina", "sitio", "website", "url"]):
        return get_website_info()

    if (
        "programacion" in text
        or "programador" in text
        or "desarrollo web" in text
        or (
            "web" in text
            and any(word in text for word in ["carrera", "programa", "estudiar"])
        )
    ):
        return get_program_info("programación web")

    if any(
        word in text
        for word in ["admision", "inscripcion", "matricula", "ingresar", "aplicar"]
    ):
        return get_admission_info()

    if any(word in text for word in ["ubicacion", "direccion", "donde", "queda"]):
        return get_location_info()

    if any(
        word in text
        for word in ["aprobada", "aprobacion", "oficial", "consejo", "registro"]
    ):
        return get_approval_info()

    # Evitar secuestrar preguntas específicas que contengan "unev" o "universidad"
    exact_matches = {"unev", "la unev", "universidad"}
    presentation_phrases = [
        "que es unev",
        "que es la unev",
        "que es la universidad",
        "cuentame de unev",
        "hablame de unev",
        "quien eres",
        "presentate",
        "informacion de unev",
        "informacion sobre unev",
        "sobre unev",
    ]
    if text in exact_matches or any(phrase in text for phrase in presentation_phrases):
        return get_university_summary()

    return None
