"""Views for user authentication."""

from django.contrib.auth import authenticate, login, logout
from django.shortcuts import redirect, render
from django.views.generic import View

from .forms import AuthForm, RegistrationForm


class AuthView(View):
    """User login view."""

    @staticmethod
    def get(request):
        return render(request, "user/auth.html", {"form": AuthForm()})

    @staticmethod
    def post(request):
        form = AuthForm(request.POST)
        email = form.data.get("email", "").lower()
        password = form.data.get("password", "")

        user = authenticate(request, username=email, password=password)

        if user is not None:
            login(request, user)
            return redirect("dashboard:index")

        return render(
            request,
            "user/auth.html",
            {
                "form": form,
                "error": "Неверный логин или пароль! Повторите попытку.",
            },
        )


class RegistrationView(View):
    """User registration view."""

    @staticmethod
    def get(request):
        return render(request, "user/registration.html", {"form": RegistrationForm()})

    @staticmethod
    def post(request):
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("dashboard:index")

        error_messages = []
        for errors in form.errors.values():
            if hasattr(errors, "data"):
                for err in errors.data:
                    error_messages.append(err.message)
            else:
                error_messages.extend(errors)

        return render(
            request,
            "user/registration.html",
            {"form": form, "error": "; ".join(error_messages) if error_messages else "Ошибка регистрации"},
        )


class LogoutView(View):
    """User logout view."""

    @staticmethod
    def get(request):
        logout(request)
        return redirect("dashboard:index")
