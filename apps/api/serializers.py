"""Serializadores que validan y delimitan el contrato público de la API v1."""

from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from rest_framework import serializers

from apps.applications.models import ClientApplication
from apps.plans.models import UserPlan
from apps.usage.models import UsageEvent
from apps.users.models import User


class UserSerializer(serializers.ModelSerializer):
    """Representa los datos de cuenta seguros que se pueden devolver al cliente."""

    plan = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("id", "username", "email", "email_verified", "first_name", "last_name", "plan")

    def get_plan(self, user: User) -> str | None:
        assignment: UserPlan | None = getattr(user, "user_plan", None)
        if assignment is None:
            return None
        return assignment.plan.code


class RegisterSerializer(serializers.ModelSerializer):
    """Valida el alta, la aceptación de términos y la política de contraseñas."""

    password = serializers.CharField(write_only=True, trim_whitespace=False)
    accepted_terms = serializers.BooleanField(write_only=True)

    class Meta:
        model = User
        fields = ("username", "email", "password", "accepted_terms")
        extra_kwargs = {"username": {"required": True}, "email": {"required": True}}

    def validate_email(self, value: str) -> str:
        value = value.lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Ya existe una cuenta con este correo.")
        return value

    def validate_accepted_terms(self, value: bool) -> bool:
        if not value:
            raise serializers.ValidationError("Debes aceptar los términos para crear una cuenta.")
        return value

    def validate_password(self, value: str) -> str:
        user = User(
            username=self.initial_data.get("username", ""), email=self.initial_data.get("email", "")
        )
        validate_password(value, user)
        return value

    def create(self, validated_data: dict) -> User:  # type: ignore[type-arg]
        validated_data.pop("accepted_terms")
        password = validated_data.pop("password")
        user = User(**validated_data, accepted_terms_at=timezone.now())
        user.set_password(password)
        user.save()
        return user


class VerifyEmailSerializer(serializers.Serializer):
    """Valida el correo y el código numérico de verificación de un solo uso."""

    email = serializers.EmailField(max_length=254)
    code = serializers.RegexField(regex=r"^[0-9]{6}$", max_length=6, min_length=6)

    def validate_email(self, value: str) -> str:
        return value.lower()


class ResendEmailVerificationSerializer(serializers.Serializer):
    """Normaliza el correo solicitado para reenviar una verificación."""

    email = serializers.EmailField(max_length=254)

    def validate_email(self, value: str) -> str:
        return value.lower()


class LoginSerializer(serializers.Serializer):
    """Define las credenciales de inicio de sesión sin serializar la contraseña."""

    identifier = serializers.CharField(max_length=254)
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class ReserveSerializer(serializers.Serializer):
    """Valida la aplicación, acción e identificador idempotente de una reserva."""

    application = serializers.SlugField(max_length=50)
    action = serializers.RegexField(regex=r"^[A-Za-z0-9_.:-]{1,80}$")
    request_id = serializers.UUIDField()

    def validate_application(self, slug: str) -> ClientApplication:
        try:
            return ClientApplication.objects.get(slug=slug)
        except ClientApplication.DoesNotExist as exc:
            raise serializers.ValidationError("Aplicación no registrada.") from exc


class UsageEventSerializer(serializers.ModelSerializer):
    """Expone el historial de consumo sin incluir metadatos sensibles."""

    application = serializers.SlugRelatedField(slug_field="slug", read_only=True)

    class Meta:
        model = UsageEvent
        fields = (
            "request_id",
            "application",
            "action",
            "status",
            "error_code",
            "processing_time_ms",
            "created_at",
            "completed_at",
        )


class CompleteSerializer(serializers.Serializer):
    """Valida los datos seguros que un backend envía al completar una interacción."""

    metadata = serializers.JSONField(required=False)
    processing_time_ms = serializers.IntegerField(min_value=0, required=False)


class FailSerializer(serializers.Serializer):
    """Valida el error técnico y los metadatos permitidos de un fallo."""

    error_code = serializers.RegexField(regex=r"^[A-Za-z0-9_.:-]{1,80}$")
    metadata = serializers.JSONField(required=False)


class ValidateReservationSerializer(serializers.Serializer):
    """Valida los datos que vinculan una reserva con su backend consumidor."""

    request_id = serializers.UUIDField()
    application = serializers.SlugField(max_length=50)
    action = serializers.RegexField(regex=r"^[A-Za-z0-9_.:-]{1,80}$")
