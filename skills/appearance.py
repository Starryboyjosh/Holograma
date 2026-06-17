def get_cordial_observation(visual_context=None):
    if not visual_context:
        return "Es un gusto recibirte."

    context = visual_context.lower()

    if "group" in context or "grupo" in context:
        return "Veo que nos acompaña un grupo. ¡Qué gusto recibirles en la UNEV!"

    if "formal" in context or "elegante" in context:
        return "Veo que vienes con una presentación muy formal. ¡Bienvenido a la UNEV!"

    if "judge" in context or "juez" in context or "jueces" in context:
        return "Bienvenidos, distinguidos evaluadores. Es un honor presentarles este proyecto de la UNEV."

    if "student" in context or "estudiante" in context:
        return (
            "¡Hola! Me alegra ver estudiantes interesados en conocer más sobre la UNEV."
        )

    return "¡Hola! Es un gusto recibirte en la UNEV."



