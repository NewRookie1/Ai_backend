"""Groq model fallback: try models in order, use the first one the key can access.

Groq retires model IDs regularly (e.g. llama-3.3-70b-versatile). Instead of
hard-failing on a 404/model_not_found, walk an ordered list so one dead ID
never takes down AI features.
"""
from typing import Any, List
from ..core.config import settings


def text_models() -> List[str]:
    preferred = [settings.GROQ_MODEL]
    defaults = [
        m.strip()
        for m in settings.GROQ_TEXT_MODELS.split(",")
        if m.strip()
    ]
    return list(dict.fromkeys(preferred + defaults))


def vision_models() -> List[str]:
    preferred = [settings.GROQ_VISION_MODEL]
    defaults = [
        m.strip()
        for m in settings.GROQ_VISION_MODELS.split(",")
        if m.strip()
    ]
    return list(dict.fromkeys(preferred + defaults))


def _is_model_not_found(exc: Exception) -> bool:
    if getattr(exc, "status_code", None) == 404:
        return True
    try:
        body = getattr(exc, "body", None) or {}
        if isinstance(body, dict) and body.get("error", {}).get("code") == "model_not_found":
            return True
    except Exception:
        pass
    return "model_not_found" in str(exc)


def chat_create(client: Any, messages: Any, models: List[str], **kwargs: Any) -> Any:
    """Call chat.completions, falling through dead model IDs."""
    last_exc: Exception | None = None
    for model in models:
        try:
            return client.chat.completions.create(
                model=model, messages=messages, **kwargs
            )
        except Exception as exc:  # noqa: BLE001 - inspected below
            last_exc = exc
            if not _is_model_not_found(exc):
                raise
    assert last_exc is not None
    raise last_exc
