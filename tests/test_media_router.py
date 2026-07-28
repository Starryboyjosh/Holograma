import threading

from app.hologram.media_router import MediaRouter
from app.hologram.models import HologramConfig
from app.hologram.router_provider import MediaRouteResult


def catalog(mode="hybrid"):
    raw = HologramConfig.default().to_dict()
    raw["identities"] = list(raw["identities"]) + [
        {"id": "unev", "title": "UNEV", "index": 1, "keywords": ["universidad"]},
        {"id": "itee", "title": "ITEE", "index": 2, "keywords": ["instituto"]},
    ]
    raw["promotions"] = [
        {"id": "systems-degree", "title": "Ingeniería en Sistemas", "index": 8, "categories": ["careers"], "keywords": ["sistemas", "ingenieria"]},
        {"id": "admissions", "title": "Admisiones", "index": 9, "categories": ["admissions"], "keywords": ["entrar", "ingreso"]},
        {"id": "disabled", "title": "Becas", "index": 10, "enabled": False, "categories": ["scholarships"]},
    ]
    raw["routing"] = {"mode": mode, "minimum_confidence": 0.8, "small_model_enabled": True, "small_model_timeout_seconds": 0.01, "identity_hold_seconds": 0, "max_identity_changes_per_turn": 1}
    return HologramConfig.from_dict(raw)


def test_local_rules_cover_holomind_unev_itee_careers_and_normalization():
    router = MediaRouter(catalog("local"))
    assert router.route("¿Quién eres?").center_identity == "holomind"
    unev = router.route("¿QUÉ CARRERAS ofrece la ÚNEV?")
    assert unev.center_identity == "unev"
    assert unev.promotion_action == "focus_category"
    assert unev.promotion_category == "careers"
    assert router.route("¿Cuál es la afiliación con ITEE?").center_identity == "itee"
    assert router.route("No tengo relación con ITEE").center_identity != "itee"
    specific = router.route("Háblame de systems-degree")
    assert specific.promotion_id == "systems-degree"


def test_candidates_are_limited_and_disabled_media_is_never_selected():
    router = MediaRouter(catalog("local"))
    local = router.route_local("becas admissions systems-degree")
    assert len(local.promotion_candidates) <= 5
    assert "disabled" not in local.promotion_candidates
    assert router.route("becas").promotion_action == "continue_rotation"


class Provider:
    def __init__(self, result): self.result, self.requests = result, []
    def select(self, request):
        self.requests.append(request)
        return self.result


def test_hybrid_uses_provider_only_for_low_confidence_and_validates_output():
    provider = Provider(MediaRouteResult("unev", "focus_category", promotion_category="admissions", confidence=0.84, reason_code="SEMANTIC"))
    router = MediaRouter(catalog(), provider)
    plan = router.route("opciones disponibles")
    assert plan.source == "small_model"
    assert plan.promotion_category == "admissions"
    assert provider.requests and len(provider.requests[0].promotion_candidates) <= 5
    provider.requests.clear()
    router.route("¿Qué carreras ofrece la UNEV?")
    assert not provider.requests
    invalid = MediaRouter(catalog(), Provider(MediaRouteResult("inventada", confidence=2)))
    assert invalid.route("algo ambiguo").source == "fallback"


def test_disabled_and_timeout_fall_back_safely():
    assert MediaRouter(catalog("disabled")).route("UNEV").source == "fallback"
    gate = threading.Event()

    class SlowProvider:
        def select(self, request):
            gate.wait()
            return MediaRouteResult("unev", confidence=0.9)

    router = MediaRouter(catalog(), SlowProvider())
    plan = router.route("algo ambiguo")
    gate.set()
    router.close()
    assert plan.center_identity == "holomind"
    assert MediaRouter(catalog(), Provider("not-json")).route("algo ambiguo").source == "fallback"
