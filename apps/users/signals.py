from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.plans.services import assign_default_plan

from .models import User


@receiver(post_save, sender=User)
def assign_free_plan_to_new_user(
    sender: type[User], instance: User, created: bool, **_: object
) -> None:
    if created:
        assign_default_plan(instance)
