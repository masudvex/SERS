from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from django.db.models import F, Q, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.utils.text import slugify


class ImageSourceMixin:
    """Lets any model offer either an uploaded file or an external image URL."""

    @property
    def image_src(self):
        if getattr(self, "image", None):
            return self.image.url
        return getattr(self, "image_url", "") or ""


# --------------------------------------------------------------------------
# Site-wide settings (a single editable row)
# --------------------------------------------------------------------------
class SiteSettings(models.Model):
    site_name = models.CharField(max_length=80, default="Green Bangladesh")
    logo = models.ImageField(
        upload_to="branding/", blank=True,
        help_text="Replaces the seedling icon in the header, footer and login pages. Transparent PNG/SVG-like images work best; also used as the browser tab icon.",
    )
    favicon = models.ImageField(
        upload_to="branding/", blank=True,
        help_text="Small square icon for the browser tab (use the emblem only). If empty, the logo is used.",
    )
    show_name_with_logo = models.BooleanField(
        default=True,
        help_text="Show the site name next to the logo in the header and footer.",
    )
    hero_strip_scale = models.PositiveSmallIntegerField(
        default=220, validators=[MinValueValidator(50), MaxValueValidator(300)],
        help_text="Size of the sliding photos on the home page, in percent (100 = original size, 220 = 2.2 times wider and taller, 300 = maximum).",
    )
    footer_blurb = models.TextField(
        default="Working together to make Bangladesh greener through tree plantation, "
        "environmental awareness and community participation."
    )
    address = models.CharField(max_length=200, default="House 14, Road 7, Dhanmondi, Dhaka, Bangladesh")
    short_address = models.CharField(max_length=100, default="Dhaka, Bangladesh")
    phone = models.CharField(max_length=60, default="+880 1XXX-XXXXXX")
    phone_hours = models.CharField(max_length=100, blank=True, default="10am–6pm, Sat–Thu")
    email = models.EmailField(default="info@greenbangladesh.org")

    # Headline numbers on the home page. Registered users and trees are *live*:
    # the figures below are a starting baseline that real sign-ups and approved
    # plantings are added on top of.
    baseline_registered_users = models.PositiveIntegerField(
        default=0, help_text="Volunteers who joined before this website. Real registrations are added to this."
    )
    active_teams = models.PositiveIntegerField(default=0)
    sapling_cost = models.PositiveIntegerField(default=150, help_text="Cost of one sapling (used on the donate page).")
    currency_symbol = models.CharField(max_length=8, default="৳")

    # Google Maps (home page + contact page)
    google_maps_api_key = models.CharField(
        max_length=120, blank=True,
        help_text="Google Maps JavaScript API key. Create one at console.cloud.google.com → APIs & Services → Credentials, "
                  "enable 'Maps JavaScript API', and restrict the key to your website address (HTTP referrers). "
                  "Without a key the site shows a simple Google Maps embed instead of the interactive map with markers.",
    )
    google_map_id = models.CharField(
        max_length=60, blank=True, default="DEMO_MAP_ID",
        help_text="Optional Google 'Map ID' (Cloud Console → Map Management) if you want a custom map style. Leave DEMO_MAP_ID otherwise.",
    )
    map_center_lat = models.FloatField(default=23.8, help_text="Latitude the map opens on.")
    map_center_lng = models.FloatField(default=90.3, help_text="Longitude the map opens on.")
    map_zoom = models.PositiveSmallIntegerField(default=7, validators=[MinValueValidator(1), MaxValueValidator(18)],
                                                help_text="1 = whole world, 7 = a country, 15 = streets.")
    map_fallback_query = models.CharField(max_length=120, default="Bangladesh",
                                          help_text="Place shown in the simple Google Maps embed when no API key is set.")

    # Mission & Vision page
    mission_text = models.TextField(blank=True)
    vision_text = models.TextField(blank=True)

    contact_notify_email = models.EmailField(
        blank=True, help_text="Receive an email for every contact message and donation pledge (optional)."
    )

    class Meta:
        verbose_name = "Site settings"
        verbose_name_plural = "Site settings"

    def __str__(self):
        return "Site settings"

    def save(self, *args, **kwargs):
        self.pk = 1  # singleton
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):  # never delete the singleton
        pass

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


# --------------------------------------------------------------------------
# Editable text registry, menus, social links, stat counters
# --------------------------------------------------------------------------
class SiteText(models.Model):
    """
    Every short piece of interface text (buttons, labels, headings, messages,
    form placeholders, emails...). Rows are created automatically the first time
    the site asks for a key, so nothing is ever hard-coded: edit the value here
    and the website changes everywhere.
    """

    key = models.CharField(max_length=160, unique=True, help_text="Identifier used by the templates. Don't rename.")
    value = models.TextField(blank=True, help_text="Text shown on the site. {placeholders} such as {site_name} are filled in automatically — keep them.")
    default = models.TextField(blank=True, editable=False)
    group = models.CharField(max_length=40, blank=True, db_index=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["key"]
        verbose_name = "Site text"
        verbose_name_plural = "Site texts (all interface wording)"

    def __str__(self):
        return self.key

    def save(self, *args, **kwargs):
        self.group = self.key.split(".", 1)[0][:40]
        super().save(*args, **kwargs)


class MenuItem(models.Model):
    class Menu(models.TextChoices):
        MAIN = "main", "Main navigation (header + mobile menu)"
        ACTIONS = "actions", "Header buttons (log in / register / dashboard / log out)"
        FOOTER_EXPLORE = "footer_explore", "Footer — first link column"
        FOOTER_ACCOUNT = "footer_account", "Footer — second link column"

    class Visibility(models.TextChoices):
        ALWAYS = "always", "Everyone"
        ANON = "anonymous", "Only visitors who are logged out"
        AUTH = "authenticated", "Only logged-in users"

    class Style(models.TextChoices):
        LINK = "link", "Plain link"
        LINE = "line", "Outline button"
        PRIMARY = "primary", "Filled button"

    menu = models.CharField(max_length=20, choices=Menu.choices)
    label = models.CharField(max_length=80)
    url = models.CharField(max_length=300, help_text="A page path such as /about/ or a full https:// address.")
    icon = models.CharField(max_length=60, blank=True, help_text="Font Awesome classes, e.g. fa-solid fa-right-to-bracket")
    visibility = models.CharField(max_length=15, choices=Visibility.choices, default=Visibility.ALWAYS)
    style = models.CharField(max_length=10, choices=Style.choices, default=Style.LINK, help_text="Only used for header buttons.")
    is_logout = models.BooleanField(default=False, help_text="Makes this item a secure log-out button.")
    new_tab = models.BooleanField(default=False)
    order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["menu", "order", "id"]

    def __str__(self):
        return f"{self.get_menu_display()}: {self.label}"

    @property
    def btn_class(self):
        return {"line": "btn btn-line", "primary": "btn btn-primary"}.get(self.style, "")


class SocialLink(models.Model):
    name = models.CharField(max_length=40, help_text="Used for screen readers, e.g. Facebook")
    icon = models.CharField(max_length=60, default="fab fa-facebook-f", help_text="Font Awesome classes, e.g. fab fa-youtube")
    url = models.URLField(max_length=300)
    order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.name


class Stat(models.Model):
    """A headline counter on the home page (number + label)."""

    class Source(models.TextChoices):
        USERS = "users", "Live: registered volunteers (baseline + real sign-ups)"
        TREES = "trees", "Live: trees planted (divisions + approved plantings)"
        TEAMS = "teams", "Active teams (number in Site settings)"
        PLANTINGS = "plantings", "Live: approved planting reports"
        MANUAL = "manual", "A number I type in below"

    label = models.CharField(max_length=80)
    source = models.CharField(max_length=12, choices=Source.choices, default=Source.MANUAL)
    manual_value = models.PositiveIntegerField(default=0, help_text="Only used when the source is 'A number I type in'.")
    suffix = models.CharField(max_length=8, blank=True, default="+", help_text="Shown after the number, e.g. +")
    order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.label


# --------------------------------------------------------------------------
# Editable page copy
# --------------------------------------------------------------------------
class ContentBlock(ImageSourceMixin, models.Model):
    """
    A piece of editable copy identified by a key such as ``home.hero`` or
    ``about.banner``. Templates ask for a block by key, so every heading,
    banner and call-to-action band on the site can be edited in the admin.
    """

    key = models.CharField(max_length=80, unique=True, validators=[RegexValidator(r"^[a-z0-9_.-]+$", "Use lowercase letters, digits, dots, dashes.")],
                           help_text="Internal identifier used by templates, e.g. home.hero. Don't change existing keys.")
    eyebrow = models.CharField(max_length=120, blank=True)
    heading = models.CharField(max_length=200, blank=True)
    body = models.TextField(blank=True, help_text="Blank line = new paragraph.")
    image = models.ImageField(upload_to="blocks/", blank=True)
    image_url = models.URLField(max_length=500, blank=True, help_text="Used when no file is uploaded.")
    image_alt = models.CharField(max_length=160, blank=True)
    button_label = models.CharField(max_length=60, blank=True)
    button_url = models.CharField(max_length=200, blank=True, help_text="A URL or a page path such as /register/")
    button_icon = models.CharField(max_length=50, blank=True, help_text="Font Awesome name, e.g. fa-seedling")

    class Meta:
        ordering = ["key"]

    def __str__(self):
        return self.key

    @property
    def paragraphs(self):
        return [p.strip() for p in self.body.replace("\r\n", "\n").split("\n\n") if p.strip()]


class InfoCard(models.Model):
    """Icon + title + text cards (home highlights, about values, mission targets)."""

    class Group(models.TextChoices):
        HOME_FEATURES = "home_features", "Home page — hero features"
        ABOUT_VALUES = "about_values", "About page — values"
        TARGETS = "targets", "Mission page — 2030 targets"

    group = models.CharField(max_length=30, choices=Group.choices)
    icon = models.CharField(max_length=50, blank=True, help_text="Font Awesome name, e.g. fa-seedling")
    title = models.CharField(max_length=120)
    text = models.TextField()
    order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["group", "order", "id"]

    def __str__(self):
        return f"{self.get_group_display()}: {self.title}"


class Milestone(models.Model):
    year = models.PositiveSmallIntegerField()
    title = models.CharField(max_length=140)
    text = models.TextField()
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["year", "id"]

    def __str__(self):
        return f"{self.year} — {self.title}"


class HeroImage(ImageSourceMixin, models.Model):
    """Photos that scroll through the curved strip on the home page."""

    image = models.ImageField(upload_to="hero/", blank=True)
    image_url = models.URLField(max_length=500, blank=True)
    alt = models.CharField(max_length=160, default="Tree planted by Green Bangladesh")
    order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.alt or f"Hero image {self.pk}"


# --------------------------------------------------------------------------
# Divisions, programs, gallery
# --------------------------------------------------------------------------
class DivisionQuerySet(models.QuerySet):
    def with_totals(self):
        approved = Q(plantings__status="approved")
        return self.annotate(
            planted_total=F("base_trees") + Coalesce(Sum("plantings__trees_count", filter=approved), 0)
        )


class Division(models.Model):
    name = models.CharField(max_length=60, unique=True)
    slug = models.SlugField(max_length=70, unique=True, blank=True)
    latitude = models.FloatField()
    longitude = models.FloatField()
    base_trees = models.PositiveIntegerField(
        default=0, help_text="Trees planted before the website. Approved volunteer plantings are added on top."
    )
    map_note = models.CharField(max_length=200, blank=True, help_text="Shown in the map popup, e.g. Urban & community plantation")
    order = models.PositiveSmallIntegerField(default=0)

    objects = DivisionQuerySet.as_manager()

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def total_trees(self):
        if hasattr(self, "planted_total"):
            return self.planted_total
        extra = self.plantings.filter(status="approved").aggregate(t=Sum("trees_count"))["t"] or 0
        return self.base_trees + extra


class Program(ImageSourceMixin, models.Model):
    title = models.CharField(max_length=120)
    slug = models.SlugField(max_length=130, unique=True, blank=True)
    tag = models.CharField(max_length=40, help_text="Small label on the card, e.g. Education")
    short_description = models.CharField(max_length=220, help_text="Used on the home page slider.")
    description = models.TextField(help_text="Used on the Programs page.")
    image = models.ImageField(upload_to="programs/", blank=True)
    image_url = models.URLField(max_length=500, blank=True)
    show_on_home = models.BooleanField(default=True, help_text="Show in the home-page slider.")
    is_active = models.BooleanField(default=True)
    order = models.PositiveSmallIntegerField(default=0)
    short_title = models.CharField(max_length=120, blank=True, help_text="Optional shorter title for the home slider.")

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title) or "program"
            slug, n = base, 2
            while Program.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug, n = f"{base}-{n}", n + 1
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def home_title(self):
        return self.short_title or self.title


class GalleryCategory(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=60, unique=True, blank=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]
        verbose_name_plural = "gallery categories"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class GalleryPhoto(ImageSourceMixin, models.Model):
    class Layout(models.TextChoices):
        NORMAL = "", "Normal"
        WIDE = "wide", "Wide"
        TALL = "tall", "Tall"
        BIG = "wide tall", "Wide and tall"

    caption = models.CharField(max_length=140)
    alt_text = models.CharField(max_length=160, blank=True)
    category = models.ForeignKey(GalleryCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name="photos")
    image = models.ImageField(upload_to="gallery/", blank=True)
    image_url = models.URLField(max_length=500, blank=True)
    layout = models.CharField(max_length=10, choices=Layout.choices, blank=True, default="")
    is_published = models.BooleanField(default=True)
    order = models.PositiveSmallIntegerField(default=0, help_text="Lower numbers appear first.")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "-created_at", "-id"]

    def __str__(self):
        return self.caption


# --------------------------------------------------------------------------
# Volunteer plantings (submitted from the dashboard / registration)
# --------------------------------------------------------------------------
class TreePlanting(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="plantings")
    division = models.ForeignKey(Division, on_delete=models.PROTECT, related_name="plantings")
    species = models.CharField(max_length=80, blank=True)
    trees_count = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1), MaxValueValidator(5000)])
    location = models.CharField(max_length=160, blank=True, help_text="Village, upazila or landmark")
    latitude = models.FloatField(null=True, blank=True, validators=[MinValueValidator(-90), MaxValueValidator(90)])
    longitude = models.FloatField(null=True, blank=True, validators=[MinValueValidator(-180), MaxValueValidator(180)])
    photo = models.ImageField(upload_to="plantings/", blank=True)
    planted_on = models.DateField(default=timezone.localdate)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    admin_note = models.CharField(max_length=200, blank=True)
    gallery_photo = models.OneToOneField(GalleryPhoto, null=True, blank=True, on_delete=models.SET_NULL, related_name="planting")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.trees_count} tree(s) in {self.division} by {self.user}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self._sync_gallery()

    def _sync_gallery(self):
        """Approved plantings with a photo appear in the public gallery automatically."""
        if self.status == self.Status.APPROVED and self.photo:
            if self.gallery_photo_id is None:
                cat, _ = GalleryCategory.objects.get_or_create(name="Volunteers", defaults={"order": 99})
                where = self.location or self.division.name
                photo = GalleryPhoto.objects.create(
                    caption=f"{where}, {self.division.name}" if self.location else self.division.name,
                    alt_text=f"{self.trees_count} tree(s) planted in {self.division.name}",
                    category=cat,
                    image=self.photo.name,
                )
                type(self).objects.filter(pk=self.pk).update(gallery_photo=photo)
                self.gallery_photo = photo
            elif not self.gallery_photo.is_published:
                GalleryPhoto.objects.filter(pk=self.gallery_photo_id).update(is_published=True)
        elif self.gallery_photo_id:
            GalleryPhoto.objects.filter(pk=self.gallery_photo_id).update(is_published=False)


# --------------------------------------------------------------------------
# Inbound messages
# --------------------------------------------------------------------------
class ContactMessage(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=160)
    message = models.TextField(max_length=4000)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.subject} — {self.name}"


class Donation(models.Model):
    class Status(models.TextChoices):
        PLEDGED = "pledged", "Pledged"
        RECEIVED = "received", "Payment received"
        CANCELLED = "cancelled", "Cancelled"

    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=30, blank=True)
    saplings = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(100000)])
    amount = models.PositiveIntegerField(help_text="Total in taka at the time of pledging.")
    message = models.CharField(max_length=300, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PLEDGED)
    reference = models.CharField(max_length=20, unique=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.reference} — ৳{self.amount}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.reference:
            self.reference = f"GB-D{self.pk:06d}"
            type(self).objects.filter(pk=self.pk).update(reference=self.reference)
