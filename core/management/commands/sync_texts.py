"""Scan templates and Python for {% t "key" "default" %} / text("key", "default") and register each in the admin."""
import ast
import re
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from core.models import SiteText

TAG = re.compile(r"""\{%\s*t\s+(?P<q1>["'])(?P<key>[^"']+)(?P=q1)\s+(?P<q2>["'])(?P<default>.*?)(?P=q2)""", re.S)


def py_calls(path):
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "text" and len(node.args) >= 1:
            key = node.args[0]
            default = node.args[1] if len(node.args) > 1 else None
            if isinstance(key, ast.Constant) and isinstance(key.value, str):
                if default is None or (isinstance(default, ast.Constant) and isinstance(default.value, str)):
                    yield key.value, (default.value if default else "")


class Command(BaseCommand):
    help = "Register all interface texts used in the code base."

    def handle(self, *args, **opts):
        found = {}
        for tpl in Path(settings.BASE_DIR).rglob("*.html"):
            if "venv" in tpl.parts or "staticfiles" in tpl.parts:
                continue
            for m in TAG.finditer(tpl.read_text(encoding="utf-8")):
                found.setdefault(m["key"], m["default"])
        for py in Path(settings.BASE_DIR).rglob("*.py"):
            if "migrations" in py.parts or "venv" in py.parts or py.name == "sync_texts.py":
                continue
            for key, default in py_calls(py):
                found.setdefault(key, default)
        # Form labels/placeholders/errors are registered by DynamicTextFormMixin when a form is built, so build each once.
        from django.contrib.auth import get_user_model

        from accounts.forms import EmailAuthenticationForm, RegistrationForm, SitePasswordResetForm, SiteSetPasswordForm
        from core.forms import ContactForm, DonationForm, TreePlantingForm

        for form in (ContactForm, DonationForm, TreePlantingForm, EmailAuthenticationForm, RegistrationForm, SitePasswordResetForm):
            form()
        SiteSetPasswordForm(get_user_model()())
        from core.texts import text
        for st in ("pending", "approved", "rejected"):
            text(f"status.{st}", {"pending": "Pending review", "approved": "Approved", "rejected": "Rejected"}[st])
        created = 0
        for key, default in found.items():
            _, was_created = SiteText.objects.get_or_create(key=key, defaults={"value": default, "default": default})
            created += was_created
        if opts.get("verbosity", 1) > 0:
            self.stdout.write(f"{len(found)} texts found, {created} new.")
