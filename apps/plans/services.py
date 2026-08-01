from typing import TYPE_CHECKING

from django.db import transaction

from .models import Plan, PlanChangeLog, UserPlan

if TYPE_CHECKING:
    from apps.users.models import User


def assign_default_plan(user: "User") -> UserPlan:
    plan, _ = Plan.objects.get_or_create(
        code="FREE",
        defaults={
            "name": "Acceso de demostración",
            "daily_interaction_limit": 5,
            "is_active": True,
        },
    )
    assignment, created = UserPlan.objects.get_or_create(user=user, defaults={"plan": plan})
    if created:
        PlanChangeLog.objects.create(
            user=user, previous_plan=None, new_plan=plan, reason="Asignación inicial"
        )
    return assignment


@transaction.atomic
def assign_plan(
    user: "User", plan_code: str, actor: "User | None" = None, reason: str = ""
) -> UserPlan:
    plan = Plan.objects.get(code=plan_code, is_active=True)
    assignment, _ = UserPlan.objects.select_for_update().get_or_create(
        user=user, defaults={"plan": plan, "assigned_by": actor}
    )
    previous_plan = assignment.plan
    if previous_plan_id := getattr(previous_plan, "id", None):
        if previous_plan_id == plan.id:
            return assignment
    assignment.plan = plan
    assignment.assigned_by = actor
    assignment.save(update_fields=("plan", "assigned_by", "updated_at"))
    PlanChangeLog.objects.create(
        user=user, previous_plan=previous_plan, new_plan=plan, changed_by=actor, reason=reason
    )
    return assignment
