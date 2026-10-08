from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.core.paginator import Paginator
from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET

from .forms import ContactForm, DonationForm
from .models import (
    Division, GalleryCategory, GalleryPhoto, HeroImage, InfoCard, Milestone, Program,
    SiteSettings, Stat, TreePlanting,
)
from .texts import text


def live_stats():
    """Headline numbers. Everything here is computed from the database on each request."""
    from django.contrib.auth import get_user_model

    site = SiteSettings.load()
    divisions = list(Division.objects.with_totals())
    total_trees = sum(d.planted_total for d in divisions)
    volunteers = get_user_model().objects.filter(profile__isnull=False).count()
    return {
        "users": site.baseline_registered_users + volunteers,
        "trees": total_trees,
        "teams": site.active_teams,
        "plantings": TreePlanting.objects.filter(status="approved").count(),
        "divisions": divisions,
    }


def home(request):
    stats = live_stats()
    divisions = sorted(stats["divisions"], key=lambda d: -d.planted_total)
    top = divisions[0].planted_total if divisions else 0
    for d in divisions:
        d.bar = round(100 * d.planted_total / top) if top else 0
    stat_values = []
    for st in Stat.objects.filter(is_active=True):
        value = stats[st.source] if st.source != Stat.Source.MANUAL else st.manual_value
        stat_values.append({"label": st.label, "value": value, "suffix": st.suffix})
    return render(request, "core/home.html", {
        "stats": stats,
        "stat_values": stat_values,
        "divisions_ranked": divisions,
        "hero_images": [{"src": h.image_src, "alt": h.alt} for h in HeroImage.objects.filter(is_active=True) if h.image_src],
        "features": InfoCard.objects.filter(group=InfoCard.Group.HOME_FEATURES, is_active=True),
        "home_programs": Program.objects.filter(is_active=True, show_on_home=True),
    })


def about(request):
    return render(request, "core/about.html", {
        "values": InfoCard.objects.filter(group=InfoCard.Group.ABOUT_VALUES, is_active=True),
        "milestones": Milestone.objects.filter(is_active=True),
    })


def mission_vision(request):
    return render(request, "core/mission_vision.html", {
        "targets": InfoCard.objects.filter(group=InfoCard.Group.TARGETS, is_active=True),
    })


def programs(request):
    return render(request, "core/programs.html", {"programs": Program.objects.filter(is_active=True)})


def gallery(request):
    categories = GalleryCategory.objects.filter(photos__is_published=True).distinct()
    photos = GalleryPhoto.objects.filter(is_published=True).select_related("category")
    selected = request.GET.get("category", "")
    if selected:
        photos = photos.filter(category__slug=selected)
    page = Paginator(photos, 24).get_page(request.GET.get("page"))
    return render(request, "core/gallery.html", {
        "categories": categories, "selected": selected, "page": page,
        "query": f"category={selected}&" if selected else "",
    })


def _notify(subject, body):
    to = SiteSettings.load().contact_notify_email
    if to:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [to], fail_silently=True)


def contact(request):
    form = ContactForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        msg = form.save()
        _notify(text("email.contact.subject", "[Website] {subject}", subject=msg.subject),
                text("email.contact.body", "From: {name} <{email}>\n\n{message}", name=msg.name, email=msg.email, message=msg.message))
        messages.success(request, text("contact.form.success", "Thanks — we'll reply within 2 business days."))
        return redirect("core:contact")
    return render(request, "core/contact.html", {"form": form})


def donate(request):
    site = SiteSettings.load()
    form = DonationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        donation = form.save(commit=False)
        donation.amount = donation.saplings * site.sapling_cost
        donation.save()
        _notify(text("email.donation.subject", "[Website] Donation pledge {ref}", ref=donation.reference),
                text("email.donation.body", "{name} <{email}> pledged {n} sapling(s) = {currency}{amount}.",
                     name=donation.name, email=donation.email, n=donation.saplings, currency=site.currency_symbol, amount=donation.amount))
        messages.success(request, text(
            "donate.form.success",
            "Thank you, {name}! Your pledge {ref} for {n} sapling(s) ({currency}{amount}) is recorded. Our team will email you payment instructions.",
            name=donation.name, ref=donation.reference, n=donation.saplings, currency=site.currency_symbol, amount=f"{donation.amount:,}"))
        return redirect("core:donate")
    return render(request, "core/donate.html", {"form": form})


@require_GET
def map_data(request):
    """JSON feed for the Google map: one marker per division plus approved plantings with coordinates."""
    divisions = [{
        "name": d.name, "lat": d.latitude, "lng": d.longitude, "trees": d.planted_total,
        "note": d.map_note,
    } for d in Division.objects.with_totals()]
    plantings = [{
        "lat": p.latitude, "lng": p.longitude, "trees": p.trees_count,
        "species": p.species, "place": p.location or p.division.name,
    } for p in TreePlanting.objects.filter(status="approved", latitude__isnull=False, longitude__isnull=False)
        .select_related("division")[:500]]
    return JsonResponse({"divisions": divisions, "plantings": plantings})


@require_GET
def stats_api(request):
    s = live_stats()
    return JsonResponse({"users": s["users"], "trees": s["trees"], "teams": s["teams"]})


def not_found(request, exception=None):
    return render(request, "404.html", status=404)
