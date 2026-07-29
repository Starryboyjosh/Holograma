"""Tests del motor Lightpanda.

No abren un navegador real: se sustituye ``_CdpConnection`` por un doble que
responde a los comandos CDP con payloads fijos.
"""

import json

import pytest

from app.tools import lightpanda_engine as engine


class FakeConnection:
    """Doble de ``_CdpConnection`` con respuestas programadas."""

    def __init__(
        self, *, page_payload=None, ready_states=None, navigate=None, raw_payload=None
    ):
        self.page_payload = page_payload
        # raw_payload se devuelve tal cual, sin serializar: simula un JS que no
        # respeta el contrato JSON.
        self.raw_payload = raw_payload
        self.ready_states = list(ready_states or ["complete"])
        self.navigate = navigate or {}
        self.calls = []
        self.closed = False

    def call(self, method, params=None, *, session_id=None, timeout=None):
        self.calls.append(method)
        if method == "Target.createTarget":
            return {"targetId": "T1"}
        if method == "Target.attachToTarget":
            return {"sessionId": "S1"}
        if method == "Page.enable":
            return {}
        if method == "Page.navigate":
            return self.navigate
        if method == "Runtime.evaluate":
            expression = (params or {}).get("expression", "")
            if expression == "document.readyState":
                state = self.ready_states.pop(0) if self.ready_states else "complete"
                return {"result": {"value": state}}
            if self.raw_payload is not None:
                return {"result": {"value": self.raw_payload}}
            return {"result": {"value": json.dumps(self.page_payload)}}
        if method == "Target.closeTarget":
            return {}
        raise AssertionError(f"método CDP inesperado: {method}")

    def close(self):
        self.closed = True


@pytest.fixture
def patch_connection(monkeypatch):
    def _install(connection):
        monkeypatch.setattr(
            engine, "_CdpConnection", lambda *a, **k: connection
        )
        return connection

    return _install


# --- Validación de URL (antes de tocar la red) ---


@pytest.mark.parametrize("bad", ["", "   ", "ftp://x.com", "javascript:alert(1)", "sitio.com"])
def test_invalid_urls_are_rejected(bad):
    with pytest.raises(engine.LightpandaError):
        engine.fetch_page_text(bad)


def test_url_without_domain_is_rejected():
    with pytest.raises(engine.LightpandaError, match="dominio"):
        engine.fetch_page_text("https://")


# --- Extracción ---


def test_extracts_text_and_title(patch_connection):
    patch_connection(
        FakeConnection(
            page_payload={
                "title": "Noticia UNEV",
                "url": "https://unev.edu.hn/noticia",
                "text": "Contenido real de la página.",
            }
        )
    )
    page = engine.fetch_page_text("https://unev.edu.hn/noticia")
    assert page.title == "Noticia UNEV"
    assert page.text == "Contenido real de la página."
    assert page.truncated is False


def test_text_is_truncated_to_limit(patch_connection):
    patch_connection(
        FakeConnection(page_payload={"title": "T", "url": "https://x.com", "text": "a" * 500})
    )
    page = engine.fetch_page_text("https://x.com", max_chars=100)
    assert len(page.text) == 100
    assert page.truncated is True
    assert "recortado" in page.as_prompt_context()


def test_default_limit_is_8000(monkeypatch, patch_connection):
    monkeypatch.delenv("LIGHTPANDA_MAX_CHARS", raising=False)
    patch_connection(
        FakeConnection(page_payload={"title": "", "url": "https://x.com", "text": "b" * 9000})
    )
    page = engine.fetch_page_text("https://x.com")
    assert len(page.text) == 8000
    assert page.truncated is True


def test_waits_until_ready_state_is_usable(patch_connection):
    connection = patch_connection(
        FakeConnection(
            page_payload={"title": "", "url": "https://x.com", "text": "listo"},
            ready_states=["loading", "loading", "interactive"],
        )
    )
    page = engine.fetch_page_text("https://x.com")
    assert page.text == "listo"
    # Tres sondeos de readyState + la extracción final.
    assert connection.calls.count("Runtime.evaluate") == 4


def test_navigation_error_is_reported(patch_connection):
    patch_connection(
        FakeConnection(
            page_payload={}, navigate={"errorText": "net::ERR_NAME_NOT_RESOLVED"}
        )
    )
    with pytest.raises(engine.LightpandaError, match="ERR_NAME_NOT_RESOLVED"):
        engine.fetch_page_text("https://no-existe.invalid")


def test_target_is_closed_even_on_failure(patch_connection):
    connection = patch_connection(
        FakeConnection(page_payload={}, navigate={"errorText": "boom"})
    )
    with pytest.raises(engine.LightpandaError):
        engine.fetch_page_text("https://x.com")
    assert "Target.closeTarget" in connection.calls
    assert connection.closed is True


def test_plain_string_payload_is_tolerated(patch_connection):
    """Si el JS devolviera texto plano en vez de JSON, no debe reventar."""
    patch_connection(FakeConnection(raw_payload="texto plano sin estructura"))
    page = engine.fetch_page_text("https://x.com")
    assert page.text == "texto plano sin estructura"
    assert page.url == "https://x.com"


def test_null_payload_does_not_crash(patch_connection):
    """json.loads('null') devuelve None: no debe llegar como dict al builder."""
    patch_connection(FakeConnection(raw_payload="null"))
    page = engine.fetch_page_text("https://x.com")
    assert page.url == "https://x.com"
    assert page.truncated is False


# --- Formateo para el prompt ---


def test_prompt_context_includes_url_and_title():
    content = engine.PageContent(
        url="https://x.com", title="Título", text="cuerpo", truncated=False
    )
    rendered = content.as_prompt_context()
    assert "https://x.com" in rendered
    assert "Título" in rendered
    assert "cuerpo" in rendered


def test_prompt_context_handles_empty_text():
    content = engine.PageContent(url="https://x.com", title="", text="", truncated=False)
    assert "no contenía texto legible" in content.as_prompt_context()
