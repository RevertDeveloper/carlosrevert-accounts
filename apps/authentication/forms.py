from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import (
    PasswordChangeForm,
    PasswordResetForm,
    SetPasswordForm,
    UserCreationForm,
)
from django.utils import timezone

from apps.users.models import User


class RegistrationForm(UserCreationForm):
    accepted_terms = forms.BooleanField(label="Acepto los términos y la política de privacidad")

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")

    def __init__(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        super().__init__(*args, **kwargs)
        # La ayuda técnica del modelo no aporta valor en el formulario público.
        self.fields["username"].help_text = ""

    def clean_email(self) -> str:
        return self.cleaned_data["email"].lower()

    def save(self, commit: bool = True) -> User:
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.accepted_terms_at = timezone.now()
        if commit:
            user.save()
        return user


class AccountUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("username", "email", "first_name", "last_name")
        labels = {
            "username": "Usuario",
            "email": "Correo electrónico",
            "first_name": "Nombre",
            "last_name": "Apellidos",
        }

    def clean_email(self) -> str:
        return self.cleaned_data["email"].lower()


class LoginForm(forms.Form):
    identifier = forms.CharField(label="Email o usuario", max_length=254)
    password = forms.CharField(label="Contraseña", strip=False, widget=forms.PasswordInput)

    def __init__(self, request=None, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        self.request = request
        self.user_cache = None
        super().__init__(*args, **kwargs)

    def clean(self) -> dict[str, str]:
        cleaned = super().clean()
        identifier = cleaned.get("identifier")
        password = cleaned.get("password")
        if identifier and password:
            self.user_cache = authenticate(self.request, username=identifier, password=password)
            if self.user_cache is None:
                raise forms.ValidationError(
                    "Las credenciales no son válidas o la cuenta está bloqueada."
                )
        return cleaned

    def get_user(self) -> User | None:
        return self.user_cache


class AccountPasswordChangeForm(PasswordChangeForm):
    pass


class AccountPasswordResetForm(PasswordResetForm):
    pass


class AccountSetPasswordForm(SetPasswordForm):
    pass
