"""Enrutamiento semántico local con submodelo opcional y validación estricta."""

from __future__ import annotations

import logging
import re
import unicodedata
from concurrent.futures import Future, ThreadPoolExecutor, TimeoutError
from dataclasses import dataclass

from .models import HologramConfig, PromotionMedia, ScenePlan
from .router_provider import MediaRouteRequest, MediaRouteResult, MediaRouterProvider

logger = logging.getLogger(__name__)


def normalize_media_text(value: str | None) -> str:
    value = unicodedata.normalize("NFD", value or "")
    value = "".join(char for char in value if unicodedata.category(char) != "Mn")
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s-]", " ", value.casefold())).strip()


@dataclass(frozen=True)
class LocalRouteResult:
    identity_candidates: tuple[str, ...]
    promotion_candidates: tuple[str, ...]
    confidence: float
    reason_code: str
    center_identity: str = "holomind"
    promotion_action: str = "continue_rotation"
    promotion_id: str | None = None
    promotion_category: str | None = None
    ambiguous: bool = False


class MediaRouter:
    """No conoce director, sockets, índices ni proveedores LLM principales."""

    def __init__(self, config: HologramConfig, provider: MediaRouterProvider | None = None) -> None:
        self._config = config
        self._provider = provider
        self._executor: ThreadPoolExecutor | None = None

    def close(self) -> None:
        if self._executor is not None:
            self._executor.shutdown(wait=False, cancel_futures=True)
            self._executor = None

    def replace_config(self, config: HologramConfig) -> None:
        self._config = config

    @property
    def config(self) -> HologramConfig:
        return self._config

    def route(
        self,
        user_message: str,
        recent_context: str | None = None,
        mode: str | None = None,
        skill: str | None = None,
        context_id: str | None = None,
    ) -> ScenePlan:
        if self._config.routing.mode == "disabled":
            return self._fallback(context_id, "ROUTING_DISABLED")
        try:
            local = self.route_local(user_message, recent_context, mode, skill)
            selected = local
            if self._should_use_provider(local):
                provider_result = self._select_provider(user_message, recent_context, mode, local)
                if provider_result is not None:
                    selected = self._from_provider(provider_result, local)
            source = "small_model" if selected is not local else "local_rules"
            plan = self._validated_plan(selected, context_id, source)
            logger.info(
                "hologram_route context_id=%s source=%s identity=%s promotion=%s category=%s confidence=%.2f reason=%s",
                context_id, "small_model" if selected is not local else "local_rules",
                plan.center_identity, plan.promotion_id, plan.promotion_category, plan.confidence, plan.reason_code,
            )
            return plan
        except Exception as error:
            logger.warning("hologram_route_fallback context_id=%s error=%s", context_id, type(error).__name__)
            return self._fallback(context_id, "ROUTER_ERROR")

    def route_local(
        self, user_message: str, recent_context: str | None = None, mode: str | None = None, skill: str | None = None
    ) -> LocalRouteResult:
        text = normalize_media_text(" ".join(part for part in (user_message, recent_context, mode, skill) if part))
        identities = self._rank_identities(text)
        promotions = self._rank_promotions(text)
        top_identity, top_identity_score = (identities[0] if identities else ("holomind", 0))
        top_promotions = tuple(item.id for item, _score in promotions[:5])
        ambiguous = len(identities) > 1 and identities[0][1] == identities[1][1]
        identity_candidates = tuple(item for item, _score in identities[:5])
        if not identity_candidates:
            identity_candidates = tuple(item.id for item in self._config.identities if item.enabled)[:5]
        action, promotion_id, category, promo_score, reason = self._promotion_selection(text, promotions)
        confidence = min(0.99, max(top_identity_score, promo_score) / 100) if (top_identity_score or promo_score) else 0.0
        if top_identity == "holomind" and not top_identity_score and not promo_score:
            reason = "NO_LOCAL_MATCH"
        return LocalRouteResult(
            identity_candidates, top_promotions, confidence, reason, top_identity,
            action, promotion_id, category, ambiguous,
        )

    def _rank_identities(self, text: str) -> list[tuple[str, int]]:
        scores: list[tuple[str, int]] = []
        for identity in self._config.identities:
            if not identity.enabled:
                continue
            if identity.id == "itee" and re.search(r"\b(no|sin|ninguna)\b.*\bitee\b", text):
                continue
            terms = {normalize_media_text(identity.id), normalize_media_text(identity.title), *(normalize_media_text(k) for k in identity.keywords)}
            score = max((90 if term == text else 70 if term and re.search(rf"\b{re.escape(term)}\b", text) else 0 for term in terms), default=0)
            identity_id = identity.id
            if identity_id == "holomind" and any(term in text for term in ("quien eres", "como te llamas", "holograma")):
                score = max(score, 95)
            if identity_id == "unev" and any(term in text for term in ("unev", "universidad", "carreras")):
                score = max(score, 96)
            if identity_id == "itee" and "itee" in text and not re.search(r"\b(no|sin|ninguna)\b.*\bitee\b", text):
                score = max(score, 96)
            if score:
                scores.append((identity_id, score))
        scores.sort(key=lambda item: (-item[1], item[0]))
        return scores

    def _rank_promotions(self, text: str) -> list[tuple[PromotionMedia, int]]:
        ranked: list[tuple[PromotionMedia, int]] = []
        words = set(text.split())
        for item in self._config.promotions:
            if not item.enabled:
                continue
            score = 0
            identifier = normalize_media_text(item.id)
            title = normalize_media_text(item.title)
            if identifier and identifier in text:
                score = max(score, 100)
            if title and title in text:
                score = max(score, 90)
            for category in item.categories:
                normalized = normalize_media_text(category)
                if normalized and (normalized in text or set(normalized.split()) <= words):
                    score = max(score, 70)
            for keyword in item.keywords:
                normalized = normalize_media_text(keyword)
                if normalized and normalized in text:
                    score = max(score, 60)
            if score:
                ranked.append((item, score + item.priority))
        ranked.sort(key=lambda item: (-item[1], -item[0].priority, item[0].id))
        return ranked

    def _promotion_selection(self, text: str, ranked: list[tuple[PromotionMedia, int]]) -> tuple[str, str | None, str | None, int, str]:
        category_term = None
        if any(term in text for term in ("carrera", "carreras", "programa", "programas")):
            category_term = "careers"
        elif any(term in text for term in ("admision", "admisiones", "ingresar", "entrar")):
            category_term = "admissions"
        elif any(term in text for term in ("beca", "becas")):
            category_term = "scholarships"
        if category_term:
            category = self._existing_category(category_term)
            if category:
                return "focus_category", None, category, 88, "CATEGORY_MATCH"
        if ranked:
            item, score = ranked[0]
            return "focus_item", item.id, None, score, "PROMOTION_MATCH"
        return "continue_rotation", None, None, 0, "NO_PROMOTION_MATCH"

    def _existing_category(self, requested: str) -> str | None:
        aliases = {"careers": {"careers", "carreras"}, "admissions": {"admissions", "admisiones"}, "scholarships": {"scholarships", "becas"}}
        for item in self._config.promotions:
            if not item.enabled:
                continue
            for category in item.categories:
                if normalize_media_text(category) in aliases[requested]:
                    return category
        return None

    def _should_use_provider(self, local: LocalRouteResult) -> bool:
        routing = self._config.routing
        return bool(
            self._provider and routing.mode in ("hybrid", "small_model") and routing.small_model_enabled
            and (local.ambiguous or local.confidence < routing.minimum_confidence)
        )

    def _select_provider(self, message: str, context: str | None, mode: str | None, local: LocalRouteResult) -> MediaRouteResult | None:
        assert self._provider is not None
        request = MediaRouteRequest(message[:800], mode, (context or "")[:600] or None, local.identity_candidates[:5], local.promotion_candidates[:5])
        if self._executor is None:
            self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="media-router")
        future: Future[MediaRouteResult] = self._executor.submit(self._provider.select, request)
        try:
            return future.result(timeout=self._config.routing.small_model_timeout_seconds)
        except TimeoutError:
            future.cancel()
            logger.warning("hologram_router_timeout")
        except Exception as error:
            logger.warning("hologram_router_provider_error=%s", type(error).__name__)
        return None

    @staticmethod
    def _from_provider(result: MediaRouteResult, local: LocalRouteResult) -> LocalRouteResult:
        identity = result.center_identity if result.center_identity in local.identity_candidates else "__invalid__"
        promotion_id = result.promotion_id
        if result.promotion_action == "focus_item" and promotion_id not in local.promotion_candidates:
            promotion_id = "__invalid__"
        return LocalRouteResult(local.identity_candidates, local.promotion_candidates, result.confidence, result.reason_code, identity, result.promotion_action, promotion_id, result.promotion_category, False)

    def _validated_plan(self, result: LocalRouteResult, context_id: str | None, source: str = "local_rules") -> ScenePlan:
        identities = {item.id for item in self._config.identities if item.enabled}
        if result.center_identity not in identities or not 0 <= result.confidence <= 1:
            return self._fallback(context_id, "INVALID_ROUTER_RESULT")
        if result.promotion_action == "focus_item":
            valid = {item.id for item in self._config.promotions if item.enabled}
            if result.promotion_id not in valid:
                return self._fallback(context_id, "INVALID_PROMOTION")
        if result.promotion_action == "focus_category":
            valid_categories = {category for item in self._config.promotions if item.enabled for category in item.categories}
            if result.promotion_category not in valid_categories:
                return self._fallback(context_id, "INVALID_CATEGORY")
        return ScenePlan(result.center_identity, result.promotion_action, result.promotion_id, result.promotion_category, result.confidence, source, result.reason_code, context_id)

    @staticmethod
    def _fallback(context_id: str | None, reason: str) -> ScenePlan:
        return ScenePlan("holomind", "continue_rotation", None, None, 0.0, "fallback", reason, context_id)
