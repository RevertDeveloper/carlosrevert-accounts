import re

from django import forms


class EmailVerificationForm(forms.Form):
    email = forms.EmailField(label="Correo electrónico", max_length=254)
    code = forms.CharField(
        label="Código de verificación",
        max_length=6,
        min_length=6,
        strip=True,
        widget=forms.TextInput(
            attrs={
                "inputmode": "numeric",
                "autocomplete": "one-time-code",
                "pattern": "[0-9]{6}",
            }
        ),
    )

    def clean_email(self) -> str:
        return self.cleaned_data["email"].lower()

    def clean_code(self) -> str:
        code = self.cleaned_data["code"]
        if not re.fullmatch(r"[0-9]{6}", code):
            raise forms.ValidationError("Introduce un código de 6 cifras.")
        return code


class EmailResendForm(forms.Form):
    email = forms.EmailField(label="Correo electrónico", max_length=254)

    def clean_email(self) -> str:
        return self.cleaned_data["email"].lower()
