from django.contrib.auth import authenticate, login, logout
from django.db.models import Count
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from drf_spectacular.utils import OpenApiTypes, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.applications.models import ClientApplication
from apps.usage.models import UsageEvent
from apps.usage.services.quota_service import (
    QuotaError,
    complete_interaction,
    fail_interaction,
    get_usage_summary,
    reserve_interaction,
)

from .permissions import IsInternalService
from .rate_limit import is_rate_limited
from .serializers import (
    CompleteSerializer,
    FailSerializer,
    LoginSerializer,
    RegisterSerializer,
    ReserveSerializer,
    UsageEventSerializer,
    UserSerializer,
)


def quota_payload(summary) -> dict:  # type: ignore[no-untyped-def]
    return {
        "plan": summary.plan,
        "daily_limit": summary.daily_limit,
        "used_today": summary.used_today,
        "remaining_today": summary.remaining_today,
        "resets_at": summary.resets_at.isoformat(),
    }


@extend_schema(request=OpenApiTypes.OBJECT, responses={200: OpenApiTypes.OBJECT})
class CsrfView(APIView):
    permission_classes = (AllowAny,)

    @method_decorator(ensure_csrf_cookie)
    def get(self, request):  # type: ignore[no-untyped-def]
        return Response({"detail": "CSRF cookie set"})


@extend_schema(request=OpenApiTypes.OBJECT, responses={200: OpenApiTypes.OBJECT})
class MeView(APIView):
    permission_classes = (AllowAny,)

    def get(self, request):  # type: ignore[no-untyped-def]
        if not request.user.is_authenticated:
            return Response({"authenticated": False, "user": None})
        return Response({"authenticated": True, "user": UserSerializer(request.user).data})


@extend_schema(request=OpenApiTypes.OBJECT, responses={200: OpenApiTypes.OBJECT})
class RegisterView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):  # type: ignore[no-untyped-def]
        if is_rate_limited(request, "register", 5, 3600):
            return Response(
                {"detail": "Demasiados intentos de registro."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        login(request, user, backend="apps.authentication.backends.EmailOrUsernameModelBackend")
        return Response(
            {"authenticated": True, "user": UserSerializer(user).data},
            status=status.HTTP_201_CREATED,
        )


@extend_schema(request=OpenApiTypes.OBJECT, responses={200: OpenApiTypes.OBJECT})
class LoginView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):  # type: ignore[no-untyped-def]
        if is_rate_limited(request, "login", 10, 900):
            return Response(
                {"detail": "Demasiados intentos de inicio de sesión."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(
            request,
            username=serializer.validated_data["identifier"],
            password=serializer.validated_data["password"],
        )
        if user is None:
            return Response(
                {"detail": "Credenciales no válidas."}, status=status.HTTP_400_BAD_REQUEST
            )
        login(request, user, backend="apps.authentication.backends.EmailOrUsernameModelBackend")
        return Response({"authenticated": True, "user": UserSerializer(user).data})


@extend_schema(request=OpenApiTypes.OBJECT, responses={200: OpenApiTypes.OBJECT})
class LogoutView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):  # type: ignore[no-untyped-def]
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(request=OpenApiTypes.OBJECT, responses={200: OpenApiTypes.OBJECT})
class UsageSummaryView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):  # type: ignore[no-untyped-def]
        return Response(quota_payload(get_usage_summary(request.user)))


@extend_schema(request=OpenApiTypes.OBJECT, responses={200: OpenApiTypes.OBJECT})
class ReserveUsageView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):  # type: ignore[no-untyped-def]
        if is_rate_limited(request, f"reserve:{request.user.pk}", 60, 60):
            return Response(
                {"detail": "Demasiadas reservas."}, status=status.HTTP_429_TOO_MANY_REQUESTS
            )
        serializer = ReserveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        application = serializer.validated_data["application"]
        try:
            event, summary = reserve_interaction(
                request.user,
                application,
                serializer.validated_data["action"],
                serializer.validated_data["request_id"],
            )
        except QuotaError as exc:
            payload = {"authorized": False, "code": exc.code, "message": exc.message}
            if exc.code == "daily_quota_exceeded":
                payload.update(quota_payload(get_usage_summary(request.user)))
            return Response(payload, status=exc.http_status)
        return Response(
            {
                "authorized": event.status == UsageEvent.Status.AUTHORIZED,
                "request_id": str(event.request_id),
                **quota_payload(summary),
            }
        )


@extend_schema(request=OpenApiTypes.OBJECT, responses={200: OpenApiTypes.OBJECT})
class UsageHistoryView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):  # type: ignore[no-untyped-def]
        events = UsageEvent.objects.filter(user=request.user).select_related("application")
        if application := request.query_params.get("application"):
            events = events.filter(application__slug=application)
        if event_status := request.query_params.get("status"):
            events = events.filter(status=event_status)
        page = (
            self.paginator.paginate_queryset(events, request, view=self)
            if hasattr(self, "paginator")
            else None
        )
        if page is not None:
            return self.paginator.get_paginated_response(UsageEventSerializer(page, many=True).data)
        from rest_framework.pagination import PageNumberPagination

        paginator = PageNumberPagination()
        result = paginator.paginate_queryset(events, request, view=self)
        return paginator.get_paginated_response(UsageEventSerializer(result, many=True).data)


@extend_schema(request=OpenApiTypes.OBJECT, responses={200: OpenApiTypes.OBJECT})
class ApplicationsView(APIView):
    permission_classes = (AllowAny,)

    def get(self, request):  # type: ignore[no-untyped-def]
        items = ClientApplication.objects.filter(is_active=True).values(
            "name", "slug", "base_url", "consumes_quota"
        )
        return Response(list(items))


@extend_schema(request=OpenApiTypes.OBJECT, responses={200: OpenApiTypes.OBJECT})
class CompleteUsageView(APIView):
    permission_classes = (IsInternalService,)

    def post(self, request, request_id):  # type: ignore[no-untyped-def]
        serializer = CompleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        event = UsageEvent.objects.filter(
            request_id=request_id, application=request.client_application
        ).first()
        if event is None:
            return Response(
                {"detail": "Interacción no encontrada."}, status=status.HTTP_404_NOT_FOUND
            )
        event = complete_interaction(request_id, **serializer.validated_data)
        return Response(UsageEventSerializer(event).data)


@extend_schema(request=OpenApiTypes.OBJECT, responses={200: OpenApiTypes.OBJECT})
class FailUsageView(APIView):
    permission_classes = (IsInternalService,)

    def post(self, request, request_id):  # type: ignore[no-untyped-def]
        serializer = FailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        event = UsageEvent.objects.filter(
            request_id=request_id, application=request.client_application
        ).first()
        if event is None:
            return Response(
                {"detail": "Interacción no encontrada."}, status=status.HTTP_404_NOT_FOUND
            )
        event = fail_interaction(request_id, **serializer.validated_data)
        return Response(UsageEventSerializer(event).data)


@extend_schema(request=OpenApiTypes.OBJECT, responses={200: OpenApiTypes.OBJECT})
class MetricsView(APIView):
    permission_classes = (IsAdminUser,)

    def get(self, request):  # type: ignore[no-untyped-def]
        from django.utils import timezone

        from apps.usage.models import DailyUsage
        from apps.users.models import User

        today = timezone.localdate()
        by_application = list(
            UsageEvent.objects.filter(created_at__date=today)
            .values("application__slug")
            .annotate(count=Count("id"))
            .order_by("application__slug")
        )
        errors = list(
            UsageEvent.objects.filter(created_at__date=today, status=UsageEvent.Status.FAILED)
            .values("application__slug")
            .annotate(count=Count("id"))
            .order_by("application__slug")
        )
        return Response(
            {
                "total_users": User.objects.count(),
                "free_users": User.objects.filter(user_plan__plan__code="FREE").count(),
                "premium_users": User.objects.filter(user_plan__plan__code="PREMIUM").count(),
                "active_users_today": DailyUsage.objects.filter(date=today, interaction_count__gt=0)
                .values("user_id")
                .distinct()
                .count(),
                "interactions_today": UsageEvent.objects.filter(
                    created_at__date=today,
                    status__in=[
                        UsageEvent.Status.AUTHORIZED,
                        UsageEvent.Status.COMPLETED,
                        UsageEvent.Status.FAILED,
                    ],
                ).count(),
                "interactions_by_application": by_application,
                "quota_rejections": UsageEvent.objects.filter(
                    created_at__date=today, status=UsageEvent.Status.REJECTED_QUOTA
                ).count(),
                "errors_by_application": errors,
            }
        )
