"""
Load the starting content from core/seed/content.json (keys and fields are plain data — edit the JSON
or, better, the admin). Safe to re-run: existing rows are kept and only *empty* fields are filled in.
"""
import json
import os
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.core.management.base import BaseCommand

from core.models import (
    ContentBlock, Division, GalleryCategory, GalleryPhoto, HeroImage, InfoCard, Milestone, MenuItem,
    Program, SiteSettings, SocialLink, Stat,
)

DATA = Path(__file__).resolve().parents[2] / "seed" / "content.json"


def fill(obj, fields):
    """Fill blank attributes only, never overwriting what an editor has written."""
    changed = False
    for k, v in fields.items():
        if not getattr(obj, k) and v not in (None, ""):
            setattr(obj, k, v)
            changed = True
    if changed:
        obj.save()


class Command(BaseCommand):
    help = "Seed the database with the original Green Bangladesh content (also registers every interface text)."

    def handle(self, *args, **opts):
        d = json.loads(DATA.read_text(encoding="utf-8"))

        s = SiteSettings.load()
        first_run = not s.mission_text
        for k, v in d["settings"].items():
            if k in ("baseline_registered_users", "active_teams"):
                if first_run:
                    setattr(s, k, v)
            elif not getattr(s, k):
                setattr(s, k, v)
        if first_run:
            s.site_name = d["settings"].get("site_name", s.site_name)
        if not s.logo:
            s.logo.save("sers-logo.png", ContentFile((DATA.parent / "sers-logo.png").read_bytes()), save=False)
        if not s.favicon:
            s.favicon.save("sers-emblem.png", ContentFile((DATA.parent / "sers-emblem.png").read_bytes()), save=False)
        s.save()

        for i, row in enumerate(d["divisions"]):
            Division.objects.get_or_create(name=row["name"], defaults={**row, "order": i})

        for i, row in enumerate(d["programs"]):
            obj, created = Program.objects.get_or_create(title=row["title"], defaults={**row, "order": i})

        if not HeroImage.objects.exists():
            for i, url in enumerate(d["hero_images"]):
                HeroImage.objects.create(image_url=url, order=i)

        cats = {}
        for i, name in enumerate(d["gallery_categories"]):
            cats[name], _ = GalleryCategory.objects.get_or_create(name=name, defaults={"order": i})
        if not GalleryPhoto.objects.exists():
            for i, row in enumerate(d["gallery"]):
                GalleryPhoto.objects.create(caption=row["caption"], category=cats[row["category"]], image_url=row["image_url"],
                                            layout=row["layout"], order=i)

        for group, rows in d["cards"].items():
            if not InfoCard.objects.filter(group=group).exists():
                for i, row in enumerate(rows):
                    InfoCard.objects.create(group=group, order=i, **row)

        if not Milestone.objects.exists():
            for row in d["milestones"]:
                Milestone.objects.create(**row)

        if not MenuItem.objects.exists():
            counters = {}
            for row in d["menu"]:
                counters[row["menu"]] = counters.get(row["menu"], -1) + 1
                MenuItem.objects.create(order=counters[row["menu"]], **row)

        if not SocialLink.objects.exists():
            for i, row in enumerate(d["social"]):
                SocialLink.objects.create(order=i, **row)

        if not Stat.objects.exists():
            for i, row in enumerate(d["stats"]):
                Stat.objects.create(order=i, **row)

        for key, fields in d["blocks"].items():
            obj, created = ContentBlock.objects.get_or_create(key=key, defaults=fields)
            if not created:
                fill(obj, fields)

        # Register every wording used by templates and Python code so it is editable in the admin straight away.
        call_command("sync_texts", verbosity=0)

        User = get_user_model()
        if not User.objects.filter(is_superuser=True).exists():
            pw = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "admin12345")
            User.objects.create_superuser("admin", "admin@greenbangladesh.org", pw)
            self.stdout.write(self.style.WARNING(f"Created admin user 'admin' with password '{pw}' — change it right away."))

        self.stdout.write(self.style.SUCCESS("Seed data loaded."))
