from django.conf import settings
from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter


class AccountAdapter(DefaultAccountAdapter):
    """Custom account adapter — routes confirmation emails to the frontend."""

    def get_email_confirmation_url(self, request, emailconfirmation):
        return f"{settings.FRONTEND_URL}/verify-email/{emailconfirmation.key}"

    def get_password_reset_url(self, request, user, temp_key):
        return f"{settings.FRONTEND_URL}/reset-password/{temp_key}"

    def send_mail(self, template_prefix, email, context):
        # Delegate to our custom email system
        super().send_mail(template_prefix, email, context)


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Custom social account adapter.
    - Links Google accounts to existing email/password accounts.
    - Prevents duplicate accounts for the same email.
    """

    def pre_social_login(self, request, sociallogin):
        """
        If the Google email matches an existing user, connect the social
        account to that user instead of creating a duplicate.
        """
        from allauth.account.models import EmailAddress
        from django.contrib.auth import get_user_model

        User = get_user_model()

        if not sociallogin.is_existing:
            email = sociallogin.account.extra_data.get("email", "").lower().strip()
            if not email:
                return

            try:
                user = User.objects.get(email=email)
                sociallogin.connect(request, user)
            except User.DoesNotExist:
                pass

    def populate_user(self, request, sociallogin, data):
        """Map Google profile fields to User fields."""
        user = super().populate_user(request, sociallogin, data)

        # Build full_name from Google profile
        given = data.get("first_name", "")
        family = data.get("last_name", "")
        name = data.get("name", "")

        if given or family:
            user.full_name = f"{given} {family}".strip()
        elif name:
            user.full_name = name.strip()

        return user

    def is_auto_signup_allowed(self, request, sociallogin):
        return True