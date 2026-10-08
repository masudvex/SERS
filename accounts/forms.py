from django import forms
from django.contrib.auth import get_user_model, password_validation
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm, SetPasswordForm
from django.core.exceptions import ValidationError
from django.db import transaction

from core.forms import validate_image_size
from core.formtext import DynamicTextFormMixin
from core.models import Division, Program, TreePlanting
from core.texts import text

from .models import Profile

User = get_user_model()


class EmailAuthenticationForm(DynamicTextFormMixin, AuthenticationForm):
    text_prefix = "login.form"
    label_defaults = {"username": "Email address"}

    username = forms.EmailField(label="Email address", widget=forms.EmailInput(attrs={"placeholder": "you@email.com", "autofocus": True, "autocomplete": "email"}))
    password = forms.CharField(label="Password", strip=False, widget=forms.PasswordInput(attrs={"placeholder": "••••••••", "autocomplete": "current-password"}))
    remember = forms.BooleanField(required=False, label="Remember me on this device")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.error_messages = {
            **self.error_messages,
            "invalid_login": text("login.form.error_invalid", "That email and password don't match. Please try again."),
            "inactive": text("login.form.error_inactive", "This account is inactive."),
        }


class RegistrationForm(DynamicTextFormMixin, forms.Form):
    text_prefix = "register.form"

    full_name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={"placeholder": "e.g. Ayesha Rahman", "autocomplete": "name"}))
    phone = forms.CharField(max_length=30, label="Phone number", widget=forms.TextInput(attrs={"type": "tel", "placeholder": "+880 1XXX-XXXXXX", "autocomplete": "tel"}))
    email = forms.EmailField(max_length=150, label="Email address", widget=forms.EmailInput(attrs={"placeholder": "you@email.com", "autocomplete": "email"}))
    division = forms.ModelChoiceField(queryset=Division.objects.none(), empty_label="Select division", label="Division")
    password = forms.CharField(label="Create password", strip=False, widget=forms.PasswordInput(attrs={"placeholder": "At least 8 characters", "autocomplete": "new-password"}))
    interested_program = forms.ModelChoiceField(queryset=Program.objects.none(), required=False, empty_label="Not sure yet", label="Program you're interested in")
    photo = forms.ImageField(required=False, validators=[validate_image_size])
    agree = forms.BooleanField(label="I agree to be contacted about upcoming plantation drives.", )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["division"].queryset = Division.objects.all()
        self.fields["interested_program"].queryset = Program.objects.filter(is_active=True)
        self.fields["agree"].error_messages["required"] = text("register.form.agree.error", "Please tick the box to continue.")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists() or User.objects.filter(username__iexact=email).exists():
            raise ValidationError(text("register.form.error_email_taken", "An account with this email already exists. Try logging in."))
        return email

    def clean(self):
        data = super().clean()
        pw = data.get("password")
        if pw:
            probe = User(username=data.get("email", ""), email=data.get("email", ""), first_name=data.get("full_name", ""))
            try:
                password_validation.validate_password(pw, probe)
            except ValidationError as e:
                self.add_error("password", e)
        return data

    @transaction.atomic
    def save(self):
        d = self.cleaned_data
        first, _, last = d["full_name"].strip().partition(" ")
        user = User.objects.create_user(username=d["email"], email=d["email"], password=d["password"],
                                        first_name=first[:150], last_name=last.strip()[:150])
        Profile.objects.create(user=user, phone=d["phone"], division=d["division"],
                               interested_program=d.get("interested_program"), agreed_to_contact=True)
        if d.get("photo"):
            TreePlanting.objects.create(user=user, division=d["division"], photo=d["photo"], trees_count=1)
        return user


class SitePasswordResetForm(PasswordResetForm):
    """Password-reset email whose subject and wording are editable in the admin."""

    email = forms.EmailField(max_length=254, label="Email address", widget=forms.EmailInput(attrs={"autocomplete": "email"}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].label = text("reset.form.email.label", "Email address")
        self.fields["email"].error_messages["required"] = text("form.error.required", "This field is required.")
        self.fields["email"].error_messages["invalid"] = text("form.error.invalid", "Please enter a valid value.")

    def send_mail(self, subject_template_name, email_template_name, context, from_email, to_email, html_email_template_name=None):
        from django.core.mail import send_mail
        from django.urls import reverse

        from core.models import SiteSettings

        link = f"{context['protocol']}://{context['domain']}" + reverse(
            "accounts:password_reset_confirm", kwargs={"uidb64": context["uid"], "token": context["token"]})
        name = SiteSettings.load().site_name
        subject = text("email.reset.subject", "Reset your {site_name} password", site_name=name)
        body = text(
            "email.reset.body",
            "Hello,\n\nYou asked to reset your {site_name} password. Open this link to choose a new one:\n\n{link}\n\n"
            "If you didn't ask for this, you can ignore this email.",
            site_name=name, link=link,
        )
        send_mail(subject, body, from_email, [to_email])


class SiteSetPasswordForm(DynamicTextFormMixin, SetPasswordForm):
    text_prefix = "reset_confirm.form"
    label_defaults = {"new_password1": "New password", "new_password2": "Confirm new password"}
