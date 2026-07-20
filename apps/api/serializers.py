from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from rest_framework import serializers

from apps.applications.models import ClientApplication
from apps.usage.models import UsageEvent
from apps.users.models import User


class UserSerializer(serializers.ModelSerializer):
    plan = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("id", "username", "email", "first_name", "last_name", "plan")

    def get_plan(self, user: User) -> str | None:
        return (
            getattr(getattr(user, "user_plan", None), "plan", None).code
            if hasattr(user, "user_plan")
            else None
        )


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    accepted_terms = serializers.BooleanField(write_only=True)

    class Meta:
        model = User
        fields = ("username", "email", "password", "first_name", "last_name", "accepted_terms")
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


class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField(max_length=254)
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class ReserveSerializer(serializers.Serializer):
    application = serializers.SlugField(max_length=50)
    action = serializers.RegexField(regex=r"^[A-Za-z0-9_.:-]{1,80}$")
    request_id = serializers.UUIDField()

    def validate_application(self, slug: str) -> ClientApplication:
        try:
            return ClientApplication.objects.get(slug=slug)
        except ClientApplication.DoesNotExist as exc:
            raise serializers.ValidationError("Aplicación no registrada.") from exc


class UsageEventSerializer(serializers.ModelSerializer):
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
    metadata = serializers.JSONField(required=False)
    processing_time_ms = serializers.IntegerField(min_value=0, required=False)


class FailSerializer(serializers.Serializer):
    error_code = serializers.RegexField(regex=r"^[A-Za-z0-9_.:-]{1,80}$")
    metadata = serializers.JSONField(required=False)
