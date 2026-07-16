from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Review


def _recalculate_product_rating(product):
    """Recalculate and save average_rating and review_count for a product."""
    from django.db.models import Avg, Count
    agg = Review.objects.filter(
        product=product, is_approved=True
    ).aggregate(avg=Avg("rating"), count=Count("id"))

    product.average_rating = round(agg["avg"] or 0, 2)
    product.review_count = agg["count"] or 0
    product.save(update_fields=["average_rating", "review_count"])


@receiver(post_save, sender=Review)
def update_rating_on_save(sender, instance, **kwargs):
    _recalculate_product_rating(instance.product)


@receiver(post_delete, sender=Review)
def update_rating_on_delete(sender, instance, **kwargs):
    _recalculate_product_rating(instance.product)