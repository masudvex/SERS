"""Makes every form label, placeholder, help text and error message editable in the admin."""
from django import forms

from .texts import text


class DynamicTextFormMixin:
    """
    Set ``text_prefix = "contact.form"`` on the form. For each field the labels
    are read from ``<prefix>.<field>.label``, placeholders from ``.placeholder``,
    and the generic error messages from ``form.error.required`` / ``form.error.invalid``.
    """

    text_prefix = "form"
    label_defaults = {}  # {field_name: original label} for fields whose label Django resets

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            base = f"{self.text_prefix}.{name}"
            if name in self.label_defaults:
                field.label = text(f"{base}.label", self.label_defaults[name])
            elif field.label:
                field.label = text(f"{base}.label", str(field.label))
            else:
                field.label = text(f"{base}.label", name.replace("_", " ").capitalize())
            if field.help_text:
                field.help_text = text(f"{base}.help", str(field.help_text))
            ph = field.widget.attrs.get("placeholder")
            if ph:
                field.widget.attrs["placeholder"] = text(f"{base}.placeholder", ph)
            field.error_messages["required"] = text("form.error.required", "This field is required.")
            field.error_messages["invalid"] = text("form.error.invalid", "Please enter a valid value.")
            if isinstance(field, forms.ModelChoiceField):
                if getattr(field, "empty_label", None):
                    field.empty_label = text(f"{base}.empty", str(field.empty_label))
                field.error_messages["invalid_choice"] = text("form.error.invalid_choice", "Please choose a valid option.")
            if isinstance(field, forms.ImageField):
                field.error_messages["invalid_image"] = text("form.error.invalid_image", "Please upload a valid image (JPG or PNG).")
