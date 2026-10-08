from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin

from .models import Profile

User = get_user_model()


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    extra = 0
    autocomplete_fields = ()


admin.site.unregister(User)


@admin.register(User)
class VolunteerUserAdmin(UserAdmin):
    inlines = [ProfileInline]
    list_display = ("username", "email", "first_name", "last_name", "get_division", "is_staff", "date_joined")
    list_select_related = ("profile__division",)

    @admin.display(description="Division", ordering="profile__division__name")
    def get_division(self, obj):
        profile = getattr(obj, "profile", None)
        return profile.division if profile else "—"
