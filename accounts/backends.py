from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class EmailBackend(ModelBackend):
    """Authenticate with an email address (case-insensitive) instead of a username."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or password is None or "@" not in username:
            return None
        User = get_user_model()
        try:
            user = User.objects.get(email__iexact=username.strip())
        except (User.DoesNotExist, User.MultipleObjectsReturned):
            # Run the hasher anyway so timing doesn't reveal which emails exist.
            User().set_password(password)
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
