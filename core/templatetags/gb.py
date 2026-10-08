from django import template

from core.models import ContentBlock
from core.texts import text

register = template.Library()


@register.simple_tag
def t(key, default="", **fmt):
    """{% t "footer.explore" "Explore" %} — editable wording (auto-registered in the admin)."""
    return text(key, default, **fmt)


@register.simple_tag
def content_block(key):
    """{% content_block "home.hero" as hero %} — the editable ContentBlock, or an empty stand-in."""
    try:
        return ContentBlock.objects.get(key=key)
    except ContentBlock.DoesNotExist:
        return ContentBlock(key=key)


@register.simple_tag
def status_label(status):
    labels = {"pending": "Pending review", "approved": "Approved", "rejected": "Rejected"}
    return text(f"status.{status}", labels.get(status, status))


@register.filter
def intcomma_bn(value):
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return value
