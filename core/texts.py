"""
Editable text registry.

``text("key", "default text", name=value)`` returns the wording stored in the
database for ``key``. If the key doesn't exist yet it is created from the
default, so every string used anywhere on the site appears in the admin under
"Site texts" and can be changed without touching code.

Texts are loaded once per request (one query) and never cached across requests,
so edits are visible immediately on every server process.
"""
import contextvars

from django.db import DatabaseError, IntegrityError

_request_cache = contextvars.ContextVar("gb_text_cache", default=None)


class _Safe(dict):
    """format_map helper: unknown {placeholders} stay as written instead of crashing."""

    def __missing__(self, key):
        return "{" + key + "}"


def begin_request():
    from .models import SiteText
    try:
        _request_cache.set({t.key: t.value for t in SiteText.objects.only("key", "value")})
    except DatabaseError:  # e.g. before the first migration
        _request_cache.set({})


def end_request():
    _request_cache.set(None)


def _lookup(key, default):
    from .models import SiteText

    cache = _request_cache.get()
    if cache is not None and key in cache:
        return cache[key]
    if cache is None:  # outside a request (management command, shell, tests)
        row = SiteText.objects.filter(key=key).values_list("value", flat=True).first()
        if row is not None:
            return row
    try:
        obj, _ = SiteText.objects.get_or_create(key=key, defaults={"value": default, "default": default})
        value = obj.value
    except (IntegrityError, DatabaseError):
        value = default
    if cache is not None:
        cache[key] = value
    return value


def text(key, default="", **fmt):
    value = _lookup(key, default)
    if fmt:
        try:
            value = value.format_map(_Safe(fmt))
        except (ValueError, IndexError):
            pass  # a stray brace in an edited text — show it as typed
    return value
