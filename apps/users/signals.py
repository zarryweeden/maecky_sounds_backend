from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User


@receiver(post_save, sender=User)
def handle_new_user(sender, instance, created, **kwargs):
    """Send welcome email on account creation."""
    if created:
        from apps.notifications.tasks import send_welcome_email
        #send_welcome_email.delay(str(instance.id))