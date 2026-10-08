from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError

from .formtext import DynamicTextFormMixin
from .models import ContactMessage, Division, Donation, TreePlanting
from .texts import text


def validate_image_size(f):
    limit = settings.MAX_UPLOAD_MB * 1024 * 1024
    if f and f.size > limit:
        raise ValidationError(text("form.error.image_too_large", "Please upload an image smaller than {mb} MB.", mb=settings.MAX_UPLOAD_MB))


class ContactForm(DynamicTextFormMixin, forms.ModelForm):
    text_prefix = "contact.form"

    # Honeypot: real visitors never see or fill this in; bots usually do.
    website = forms.CharField(required=False, widget=forms.TextInput(attrs={"tabindex": "-1", "autocomplete": "off"}))

    class Meta:
        model = ContactMessage
        fields = ["name", "email", "subject", "message"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Your name"}),
            "email": forms.EmailInput(attrs={"placeholder": "you@email.com"}),
            "subject": forms.TextInput(attrs={"placeholder": "What's this about?"}),
            "message": forms.Textarea(attrs={"rows": 5, "placeholder": "Tell us a bit more..."}),
        }
        labels = {"name": "Full name", "email": "Email address", "subject": "Subject", "message": "Message"}

    def clean_website(self):
        if self.cleaned_data.get("website"):
            raise ValidationError(text("form.error.spam", "Spam detected."))
        return ""


class DonationForm(DynamicTextFormMixin, forms.ModelForm):
    text_prefix = "donate.form"

    class Meta:
        model = Donation
        fields = ["name", "email", "phone", "saplings", "message"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Your name"}),
            "email": forms.EmailInput(attrs={"placeholder": "you@email.com"}),
            "phone": forms.TextInput(attrs={"placeholder": "+880 1XXX-XXXXXX"}),
            "saplings": forms.NumberInput(attrs={"min": 1, "value": 10}),
            "message": forms.TextInput(attrs={"placeholder": "Optional — dedicate your trees to someone"}),
        }
        labels = {"name": "Full name", "email": "Email address", "phone": "Phone (optional)",
                  "saplings": "Number of saplings", "message": "Dedication (optional)"}


class TreePlantingForm(DynamicTextFormMixin, forms.ModelForm):
    text_prefix = "dashboard.form"

    division = forms.ModelChoiceField(queryset=Division.objects.none(), empty_label="Select division")
    photo = forms.ImageField(required=False, validators=[validate_image_size])

    class Meta:
        model = TreePlanting
        fields = ["division", "trees_count", "species", "location", "planted_on", "photo", "latitude", "longitude"]
        widgets = {
            "planted_on": forms.DateInput(attrs={"type": "date"}),
            "latitude": forms.HiddenInput(),
            "longitude": forms.HiddenInput(),
            "species": forms.TextInput(attrs={"placeholder": "e.g. Mangrove, Mango, Krishnachura"}),
            "location": forms.TextInput(attrs={"placeholder": "Village, upazila or landmark"}),
        }
        labels = {"trees_count": "Number of trees", "planted_on": "Date planted"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["division"].queryset = Division.objects.all()

    def clean(self):
        data = super().clean()
        lat, lng = data.get("latitude"), data.get("longitude")
        if (lat is None) != (lng is None):
            data["latitude"] = data["longitude"] = None
        elif lat is not None and not (20.5 <= lat <= 26.7 and 87.9 <= lng <= 92.8):
            # Outside Bangladesh: drop the pin rather than reject the whole form.
            data["latitude"] = data["longitude"] = None
        return data

    def clean_planted_on(self):
        from django.utils import timezone
        d = self.cleaned_data["planted_on"]
        if d > timezone.localdate():
            raise ValidationError(text("dashboard.form.error_future", "The planting date can't be in the future."))
        return d
