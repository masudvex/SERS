from django.conf import settings
from django.db import models


class Profile(models.Model):
    """Extra volunteer details attached to Django's built-in User."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    phone = models.CharField(max_length=30, blank=True)
    division = models.ForeignKey("core.Division", on_delete=models.SET_NULL, null=True, blank=True, related_name="volunteers")
    interested_program = models.ForeignKey("core.Program", on_delete=models.SET_NULL, null=True, blank=True, related_name="volunteers")
    agreed_to_contact = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.get_username()
