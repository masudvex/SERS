import shutil
import tempfile
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from accounts.models import Profile
from core.models import ContactMessage, Division, Donation, GalleryPhoto, TreePlanting

User = get_user_model()
TMP_MEDIA = tempfile.mkdtemp()


def png(name="t.png"):
    buf = BytesIO()
    Image.new("RGB", (20, 20), "green").save(buf, "PNG")
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/png")


@override_settings(MEDIA_ROOT=TMP_MEDIA)
class SiteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        from django.core.management import call_command
        call_command("seed_demo", verbosity=0)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TMP_MEDIA, ignore_errors=True)

    def test_all_public_pages_render(self):
        for name in ["core:home", "core:about", "core:mission_vision", "core:programs", "core:gallery",
                     "core:contact", "core:donate", "accounts:login", "accounts:register",
                     "accounts:password_reset", "core:map_data", "core:stats_api"]:
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)
        self.assertEqual(self.client.get("/nope/").status_code, 404)

    def test_home_is_database_driven(self):
        r = self.client.get(reverse("core:home"))
        self.assertContains(r, "Grow a Greener Bangladesh")
        self.assertContains(r, 'data-count="125800"')  # sum of divisions, computed
        from core.models import ContentBlock
        ContentBlock.objects.filter(key="home.hero").update(heading="Edited in admin")
        self.assertContains(self.client.get(reverse("core:home")), "Edited in admin")

    def test_registration_login_and_dashboard(self):
        dhaka = Division.objects.get(name="Dhaka")
        data = {"full_name": "Ayesha Rahman", "phone": "+8801700000000", "email": "Ayesha@Example.com",
                "division": dhaka.pk, "password": "Str0ng-pass-99", "agree": "on", "photo": png()}
        r = self.client.post(reverse("accounts:register"), data)
        self.assertRedirects(r, reverse("accounts:dashboard"))
        u = User.objects.get(email="ayesha@example.com")
        self.assertEqual(u.profile.division, dhaka)
        p = TreePlanting.objects.get(user=u)
        self.assertEqual(p.status, "pending")
        # pending plantings don't count or show in the gallery yet
        self.assertEqual(Division.objects.with_totals().get(pk=dhaka.pk).planted_total, 32400)
        self.assertFalse(GalleryPhoto.objects.filter(planting=p).exists())
        # duplicate email rejected (case-insensitive)
        self.client.logout()
        r = self.client.post(reverse("accounts:register"), {**data, "email": "AYESHA@example.com", "photo": png()})
        self.assertContains(r, "already exists")
        # log in by email, different case
        r = self.client.post(reverse("accounts:login"), {"username": "AYESHA@example.com", "password": "Str0ng-pass-99"})
        self.assertRedirects(r, reverse("accounts:dashboard"))
        self.assertContains(self.client.get(reverse("accounts:dashboard")), "Pending review")

    def test_weak_password_and_bad_login(self):
        dhaka = Division.objects.get(name="Dhaka")
        r = self.client.post(reverse("accounts:register"), {"full_name": "A B", "phone": "1", "email": "a@b.com",
                                                          "division": dhaka.pk, "password": "12345678", "agree": "on"})
        self.assertEqual(Profile.objects.count(), 0)
        self.assertContains(r, "field-error")
        r = self.client.post(reverse("accounts:login"), {"username": "x@y.com", "password": "nope"})
        self.assertContains(r, "don&#x27;t match")

    def test_dashboard_requires_login(self):
        r = self.client.get(reverse("accounts:dashboard"))
        self.assertRedirects(r, f"{reverse('accounts:login')}?next={reverse('accounts:dashboard')}")

    def test_approval_updates_totals_map_and_gallery(self):
        u = User.objects.create_user("v@x.com", "v@x.com", "pw-Str0ng-77")
        dhaka = Division.objects.get(name="Dhaka")
        p = TreePlanting.objects.create(user=u, division=dhaka, trees_count=10, photo=png(),
                                        latitude=23.8, longitude=90.4, location="Dhanmondi")
        before = GalleryPhoto.objects.filter(is_published=True).count()
        p.status = "approved"
        p.save()
        self.assertEqual(Division.objects.with_totals().get(pk=dhaka.pk).planted_total, 32410)
        self.assertEqual(GalleryPhoto.objects.filter(is_published=True).count(), before + 1)
        data = self.client.get(reverse("core:map_data")).json()
        self.assertEqual(len(data["plantings"]), 1)
        self.assertEqual(next(d for d in data["divisions"] if d["name"] == "Dhaka")["trees"], 32410)
        self.assertEqual(self.client.get(reverse("core:stats_api")).json()["trees"], 125810)
        # un-approving hides it again
        p.status = "rejected"
        p.save()
        self.assertEqual(GalleryPhoto.objects.filter(is_published=True).count(), before)
        self.assertEqual(Division.objects.with_totals().get(pk=dhaka.pk).planted_total, 32400)

    def test_gallery_filter_and_pagination(self):
        r = self.client.get(reverse("core:gallery"), {"category": "mangrove"})
        self.assertContains(r, "Khulna coastline")
        self.assertNotContains(r, "Dhaka community drive")

    def test_contact_form_saves_and_honeypot(self):
        url = reverse("core:contact")
        r = self.client.post(url, {"name": "Rafi", "email": "r@x.com", "subject": "Hi", "message": "Hello"}, follow=True)
        self.assertContains(r, "we&#x27;ll reply within 2 business days")
        self.assertEqual(ContactMessage.objects.count(), 1)
        self.client.post(url, {"name": "Bot", "email": "b@x.com", "subject": "s", "message": "m", "website": "spam.com"})
        self.assertEqual(ContactMessage.objects.count(), 1)
        r = self.client.post(url, {"name": "", "email": "bad", "subject": "", "message": ""})
        self.assertContains(r, "field-error")

    def test_donation_pledge_computes_amount_server_side(self):
        r = self.client.post(reverse("core:donate"), {"name": "D", "email": "d@x.com", "saplings": 4, "amount": 1}, follow=True)
        d = Donation.objects.get()
        self.assertEqual(d.amount, 600)
        self.assertTrue(d.reference.startswith("GB-D"))
        self.assertContains(r, d.reference)

    def test_uploaded_logo_replaces_icon_everywhere(self):
        from core.models import SiteSettings
        site = SiteSettings.load()
        self.assertTrue(site.logo)  # starter data ships with the SERS logo
        site.logo = ""
        site.save()
        self.assertContains(self.client.get(reverse("core:home")), "fa-seedling")  # fallback icon
        site.logo = png("logo.png")
        site.save()
        for name in ["core:home", "accounts:login", "accounts:register"]:
            r = self.client.get(reverse(name))
            self.assertContains(r, site.logo.url)
            self.assertNotContains(r, "fa-seedling")

    def test_every_interface_text_is_editable(self):
        from core.models import SiteText
        SiteText.objects.filter(key="footer.col1.title").update(value="Navigate")
        SiteText.objects.filter(key="login.form.username.label").update(value="Your e-mail")
        SiteText.objects.filter(key="contact.form.submit").update(value="Dispatch")
        SiteText.objects.filter(key="register.form.division.empty").update(value="Pick one")
        self.assertContains(self.client.get(reverse("core:home")), "<h5>Navigate</h5>")
        self.assertContains(self.client.get(reverse("accounts:login")), "Your e-mail")
        self.assertContains(self.client.get(reverse("core:contact")), "Dispatch")
        self.assertContains(self.client.get(reverse("accounts:register")), "Pick one")
        # edited wording is used for flash messages and placeholders too
        SiteText.objects.filter(key="contact.form.success").update(value="Received, thanks!")
        r = self.client.post(reverse("core:contact"), {"name": "A", "email": "a@x.com", "subject": "s", "message": "m"}, follow=True)
        self.assertContains(r, "Received, thanks!")
        # unknown keys auto-register with their default
        from core.texts import text
        self.assertEqual(text("brand.new.key", "Hello {who}", who="you"), "Hello you")
        self.assertTrue(SiteText.objects.filter(key="brand.new.key").exists())

    def test_menus_social_stats_are_database_driven(self):
        from core.models import MenuItem, SocialLink, Stat
        MenuItem.objects.filter(menu="main", label="Gallery").update(label="Photos", url="/gallery/?x=1")
        SocialLink.objects.create(name="TikTok", icon="fab fa-tiktok", url="https://tiktok.com/@gb", order=9)
        Stat.objects.create(label="Schools reached", source="manual", manual_value=77, suffix=" schools", order=9)
        r = self.client.get(reverse("core:home"))
        self.assertContains(r, ">Photos</a>")
        self.assertContains(r, 'href="/gallery/?x=1"')
        self.assertContains(r, "https://tiktok.com/@gb")
        self.assertContains(r, 'data-count="77" data-suffix=" schools"')
        # live stat follows real data
        self.assertContains(r, 'data-count="125800"')
        # visibility rules: logged-out users never see dashboard/log-out buttons
        self.assertNotContains(r, "Log out")
        User.objects.create_user("m@x.com", "m@x.com", "pw-Str0ng-77")
        self.client.login(username="m@x.com", password="pw-Str0ng-77")
        r = self.client.get(reverse("core:home"))
        self.assertContains(r, "Log out")
        self.assertNotContains(r, ">Register<")
        self.assertContains(r, "Go to my dashboard")

    def test_sync_texts_registers_everything(self):
        from django.core.management import call_command
        from core.models import SiteText
        n = SiteText.objects.count()
        call_command("sync_texts", verbosity=0)
        self.assertGreater(n, 100)
        self.assertTrue(SiteText.objects.filter(key="register.form.password.placeholder").exists())

    def test_logout_is_post_only(self):
        User.objects.create_user("l@x.com", "l@x.com", "pw-Str0ng-77")
        self.client.login(username="l@x.com", password="pw-Str0ng-77")
        self.assertEqual(self.client.get(reverse("accounts:logout")).status_code, 405)
        self.client.post(reverse("accounts:logout"))
        self.assertEqual(self.client.get(reverse("accounts:dashboard")).status_code, 302)

    def test_password_reset_email(self):
        User.objects.create_user("p@x.com", "p@x.com", "pw-Str0ng-77")
        self.client.post(reverse("accounts:password_reset"), {"email": "p@x.com"})
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("/reset/", mail.outbox[0].body)

    def test_admin_pages_load(self):
        User.objects.create_superuser("root", "r@x.com", "pw-Str0ng-77")
        self.client.login(username="root", password="pw-Str0ng-77")
        for m in ["sitesettings", "contentblock", "infocard", "milestone", "heroimage", "division", "program",
                  "gallerycategory", "galleryphoto", "treeplanting", "contactmessage", "donation",
                  "sitetext", "menuitem", "sociallink", "stat"]:
            r = self.client.get(f"/admin/core/{m}/", follow=True)
            self.assertEqual(r.status_code, 200, m)
        self.assertEqual(self.client.get("/admin/core/contentblock/add/").status_code, 200)
        self.assertEqual(self.client.get("/admin/auth/user/").status_code, 200)


class GoogleMapTests(TestCase):
    def test_home_has_map_config_and_no_leaflet(self):
        from core.models import SiteSettings
        cfg = SiteSettings.load() if hasattr(SiteSettings, "load") else SiteSettings.objects.first()
        cfg.google_maps_api_key = "ABC123"
        cfg.save()
        html = self.client.get("/").content.decode()
        self.assertIn('id="mapConfig"', html)
        self.assertIn("ABC123", html)
        self.assertNotIn("leaflet", html.lower())
        self.assertNotIn("carto", html.lower())
