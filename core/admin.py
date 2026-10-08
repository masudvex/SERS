from django.contrib import admin, messages
from django.utils.html import format_html

from .models import (
    ContactMessage, ContentBlock, Division, Donation, GalleryCategory, GalleryPhoto,
    HeroImage, InfoCard, Milestone, MenuItem, Program, SiteSettings, SiteText, SocialLink, Stat, TreePlanting,
)

admin.site.site_header = "Green Bangladesh administration"
admin.site.site_title = "Green Bangladesh admin"
admin.site.index_title = "Manage website content"


def thumb(obj, size=48):
    src = obj.image_src if hasattr(obj, "image_src") else ""
    if not src:
        return "—"
    return format_html('<img src="{}" style="height:{}px;width:{}px;object-fit:cover;border-radius:6px">', src, size, size)


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ("Identity", {"fields": ("site_name", "logo", "show_name_with_logo", "favicon", "footer_blurb")}),
        ("Contact details", {"fields": ("address", "short_address", "phone", "phone_hours", "email", "contact_notify_email")}),
        ("Home page hero photos", {"fields": ("hero_strip_scale",)}),
        ("Home page numbers (feed the counters under Stats)", {"fields": ("baseline_registered_users", "active_teams")}),
        ("Google Maps", {"fields": ("google_maps_api_key", "google_map_id", "map_center_lat", "map_center_lng", "map_zoom", "map_fallback_query")}),
        ("Donations", {"fields": ("sapling_cost", "currency_symbol")}),
        ("Mission & Vision page", {"fields": ("mission_text", "vision_text")}),
    )

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        # Skip the list screen: there is only ever one settings row.
        from django.shortcuts import redirect
        obj = SiteSettings.load()
        return redirect("admin:core_sitesettings_change", obj.pk)


@admin.register(ContentBlock)
class ContentBlockAdmin(admin.ModelAdmin):
    list_display = ("key", "heading", "has_image")
    search_fields = ("key", "heading", "body")

    @admin.display(boolean=True)
    def has_image(self, obj):
        return bool(obj.image_src)


@admin.register(InfoCard)
class InfoCardAdmin(admin.ModelAdmin):
    list_display = ("title", "group", "icon", "order", "is_active")
    list_filter = ("group", "is_active")
    list_editable = ("order", "is_active")
    search_fields = ("title", "text")


@admin.register(Milestone)
class MilestoneAdmin(admin.ModelAdmin):
    list_display = ("year", "title", "is_active")
    list_editable = ("is_active",)


@admin.register(HeroImage)
class HeroImageAdmin(admin.ModelAdmin):
    list_display = ("preview", "alt", "order", "is_active")
    list_editable = ("order", "is_active")

    @admin.display(description="Preview")
    def preview(self, obj):
        return thumb(obj)


@admin.register(Division)
class DivisionAdmin(admin.ModelAdmin):
    list_display = ("name", "base_trees", "live_total", "latitude", "longitude", "order")
    list_editable = ("order",)
    prepopulated_fields = {"slug": ("name",)}

    def get_queryset(self, request):
        return super().get_queryset(request).with_totals()

    @admin.display(description="Total incl. approved plantings", ordering="planted_total")
    def live_total(self, obj):
        return f"{obj.planted_total:,}"


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ("preview", "title", "tag", "show_on_home", "is_active", "order")
    list_display_links = ("preview", "title")
    list_editable = ("show_on_home", "is_active", "order")
    list_filter = ("is_active", "show_on_home")
    search_fields = ("title", "description")
    prepopulated_fields = {"slug": ("title",)}

    @admin.display(description="Image")
    def preview(self, obj):
        return thumb(obj)


@admin.register(GalleryCategory)
class GalleryCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "order")
    list_editable = ("order",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(GalleryPhoto)
class GalleryPhotoAdmin(admin.ModelAdmin):
    list_display = ("preview", "caption", "category", "layout", "is_published", "order", "created_at")
    list_display_links = ("preview", "caption")
    list_editable = ("is_published", "order")
    list_filter = ("is_published", "category", "layout")
    search_fields = ("caption",)

    @admin.display(description="Photo")
    def preview(self, obj):
        return thumb(obj)


@admin.register(TreePlanting)
class TreePlantingAdmin(admin.ModelAdmin):
    list_display = ("preview", "user", "division", "trees_count", "species", "planted_on", "status", "created_at")
    list_display_links = ("preview", "user")
    list_filter = ("status", "division")
    search_fields = ("user__email", "user__first_name", "user__last_name", "location", "species")
    list_select_related = ("user", "division")
    readonly_fields = ("created_at", "gallery_photo")
    actions = ["approve", "reject"]
    date_hierarchy = "planted_on"

    @admin.display(description="Photo")
    def preview(self, obj):
        if not obj.photo:
            return "—"
        return format_html('<img src="{}" style="height:48px;width:48px;object-fit:cover;border-radius:6px">', obj.photo.url)

    @admin.action(description="Approve selected plantings (adds them to totals, map and gallery)")
    def approve(self, request, queryset):
        n = 0
        for planting in queryset.exclude(status=TreePlanting.Status.APPROVED):
            planting.status = TreePlanting.Status.APPROVED
            planting.save()
            n += 1
        self.message_user(request, f"{n} planting(s) approved.", messages.SUCCESS)

    @admin.action(description="Reject selected plantings")
    def reject(self, request, queryset):
        n = 0
        for planting in queryset.exclude(status=TreePlanting.Status.REJECTED):
            planting.status = TreePlanting.Status.REJECTED
            planting.save()
            n += 1
        self.message_user(request, f"{n} planting(s) rejected.", messages.WARNING)


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("subject", "name", "email", "is_read", "created_at")
    list_filter = ("is_read", "created_at")
    list_editable = ("is_read",)
    search_fields = ("name", "email", "subject", "message")
    readonly_fields = ("name", "email", "subject", "message", "created_at")
    actions = ["mark_read"]

    def has_add_permission(self, request):
        return False

    @admin.action(description="Mark selected messages as read")
    def mark_read(self, request, queryset):
        queryset.update(is_read=True)


@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = ("reference", "name", "email", "saplings", "amount", "status", "created_at")
    list_filter = ("status", "created_at")
    list_editable = ("status",)
    search_fields = ("reference", "name", "email")
    readonly_fields = ("reference", "created_at")


class TextGroupFilter(admin.SimpleListFilter):
    title = "page / area"
    parameter_name = "group"

    def lookups(self, request, model_admin):
        groups = SiteText.objects.order_by().values_list("group", flat=True).distinct()
        return [(g, g) for g in sorted(groups) if g]

    def queryset(self, request, queryset):
        return queryset.filter(group=self.value()) if self.value() else queryset


@admin.register(SiteText)
class SiteTextAdmin(admin.ModelAdmin):
    """Every word of interface text. Search for the wording you see on the site."""

    list_display = ("key", "value", "group", "changed", "updated_at")
    list_editable = ("value",)
    list_filter = (TextGroupFilter,)
    search_fields = ("key", "value", "default")
    list_per_page = 50
    readonly_fields = ("default", "updated_at")
    actions = ["reset_to_default"]

    @admin.display(boolean=True, description="Edited")
    def changed(self, obj):
        return obj.value != obj.default

    @admin.action(description="Reset selected texts to their original wording")
    def reset_to_default(self, request, queryset):
        for t in queryset:
            t.value = t.default
            t.save()
        self.message_user(request, "Texts reset.", messages.SUCCESS)


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ("label", "menu", "url", "visibility", "style", "order", "is_active")
    list_editable = ("url", "order", "is_active")
    list_filter = ("menu", "visibility", "is_active")


@admin.register(SocialLink)
class SocialLinkAdmin(admin.ModelAdmin):
    list_display = ("name", "icon", "url", "order", "is_active")
    list_editable = ("order", "is_active")


@admin.register(Stat)
class StatAdmin(admin.ModelAdmin):
    list_display = ("label", "source", "manual_value", "suffix", "order", "is_active")
    list_editable = ("order", "is_active")
