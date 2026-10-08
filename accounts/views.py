from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render

from core.forms import TreePlantingForm
from core.models import TreePlanting
from core.texts import text

from .forms import EmailAuthenticationForm, RegistrationForm


class SiteLoginView(LoginView):
    authentication_form = EmailAuthenticationForm
    template_name = "accounts/login.html"
    redirect_authenticated_user = True

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # LoginView injects its own "site"/"site_name"; drop them so our SiteSettings context wins.
        ctx.pop("site", None)
        ctx.pop("site_name", None)
        return ctx

    def form_valid(self, form):
        response = super().form_valid(form)
        if not form.cleaned_data.get("remember"):
            self.request.session.set_expiry(0)  # session ends when the browser closes
        return response


def register(request):
    if request.user.is_authenticated:
        return redirect("accounts:dashboard")
    initial = {}
    program_slug = request.GET.get("program")
    if program_slug:
        from core.models import Program
        p = Program.objects.filter(slug=program_slug, is_active=True).first()
        if p:
            initial["interested_program"] = p.pk
    form = RegistrationForm(request.POST or None, request.FILES or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user, backend="accounts.backends.EmailBackend")
        messages.success(request, text("register.success", "Welcome aboard, {name}! Your registration ID is {id}.", name=user.first_name, id=f"GB-{user.pk:06d}"))
        return redirect("accounts:dashboard")
    return render(request, "accounts/register.html", {"form": form})


@login_required
def dashboard(request):
    form = TreePlantingForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        planting = form.save(commit=False)
        planting.user = request.user
        planting.save()
        messages.success(request, text("dashboard.form.success", "Thanks! Your planting was submitted and will appear on the map and totals once our team approves it."))
        return redirect("accounts:dashboard")
    if request.method == "GET":
        profile = getattr(request.user, "profile", None)
        if profile and profile.division_id:
            form.initial.setdefault("division", profile.division_id)
    plantings = request.user.plantings.select_related("division")
    approved = [p for p in plantings if p.status == TreePlanting.Status.APPROVED]
    return render(request, "accounts/dashboard.html", {
        "form": form,
        "plantings": plantings,
        "trees_approved": sum(p.trees_count for p in approved),
        "trees_pending": sum(p.trees_count for p in plantings if p.status == TreePlanting.Status.PENDING),
        "reg_id": f"GB-{request.user.pk:06d}",
    })
