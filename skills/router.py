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


def route_local_skill(user_input):
    text = normalize_text(user_input)

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

    if any(word in text for word in ["que es unev", "universidad", "unev"]):
        return get_university_summary()

    return None
