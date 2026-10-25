"""Forms for user authentication."""

from django import forms
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError

from .models import User


class RegistrationForm(forms.Form):
    """Form for user registration with email and password."""

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(
            attrs={"class": "form-control my-3 p-4", "placeholder": "Email"}
        ),
    )
    password1 = forms.CharField(
        required=True,
        widget=forms.PasswordInput(
            attrs={"class": "form-control my-3 p-4", "placeholder": "Пароль"}
        ),
    )
    password2 = forms.CharField(
        required=True,
        widget=forms.PasswordInput(
            attrs={"class": "form-control my-3 p-4", "placeholder": "Повторите пароль"}
        ),
    )

    def clean(self):
        """Validate form data: password match and email uniqueness."""
        cleaned_data = super().clean()
        email = cleaned_data.get("email")
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")

        if password1 and password2 and password1 != password2:
            raise ValidationError("Введенные пароли не совпадают")

        if email and User.objects.filter(email=email).exists():
            raise ValidationError(
                "Данный e-mail уже зарегистрирован! Введите другой e-mail или "
                "воспользуйтесь формой авторизации."
            )

        return cleaned_data

    def save(self) -> User:
        """Create and return the new user."""
        email = self.cleaned_data["email"]
        password = self.cleaned_data["password1"]
        user = User.objects.create_user(email, email, password)
        return authenticate(username=email, password=password)


class AuthForm(forms.Form):
    """Form for user authentication with email and password."""

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(
            attrs={"class": "form-control my-3 p-4", "placeholder": "Email"}
        ),
    )
    password = forms.CharField(
        required=True,
        widget=forms.PasswordInput(
            attrs={"class": "form-control my-3 p-4", "placeholder": "Пароль"}
        ),
    )
