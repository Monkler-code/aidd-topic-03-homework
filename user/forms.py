from django import forms
from django.contrib.auth.password_validation import validate_password
from django.db import IntegrityError, transaction

from user.models import User


class RegistrationForm(forms.Form):
    """Форма регистрации пользователей"""

    email = forms.EmailField(
        max_length=150,
        required=True,
        widget=forms.EmailInput(
            attrs={"class": "form-control my-3 p-4", "placeholder": "Email"}
        ),
    )
    password1 = forms.CharField(
        required=True,
        strip=False,
        widget=forms.PasswordInput(
            attrs={"class": "form-control my-3 p-4", "placeholder": "Пароль"}
        ),
    )
    password2 = forms.CharField(
        required=True,
        strip=False,
        widget=forms.PasswordInput(
            attrs={"class": "form-control my-3 p-4", "placeholder": "Повторите пароль"}
        ),
    )

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get("email", "").strip().lower()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")

        if password1 and password2 and password1 != password2:
            self.add_error("password2", "Введенные пароли не совпадают")
        elif password1:
            validate_password(password1, user=User(username=email, email=email))

        return cleaned_data

    def save(self):
        email = self.cleaned_data["email"].strip().lower()
        password = self.cleaned_data["password1"]
        try:
            with transaction.atomic():
                if User.objects.filter(email__iexact=email).exists():
                    return None
                return User.objects.create_user(
                    username=email, email=email, password=password
                )
        except IntegrityError:
            # A concurrent registration may have claimed the normalized username.
            return None


class AuthForm(forms.Form):
    """Форма авторизации пользователей"""

    email = forms.EmailField(
        max_length=150,
        required=True,
        widget=forms.EmailInput(
            attrs={"class": "form-control my-3 p-4", "placeholder": "Email"}
        ),
    )
    password = forms.CharField(
        required=True,
        strip=False,
        widget=forms.PasswordInput(
            attrs={"class": "form-control my-3 p-4", "placeholder": "Пароль"}
        ),
    )
