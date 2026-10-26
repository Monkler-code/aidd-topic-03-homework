from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.views.generic import View

from .forms import AuthForm, RegistrationForm
from .rate_limit import allow_attempt, clear_attempts


class AuthView(View):
    """Авторизация"""

    @staticmethod
    def get(request):
        return render(request, "user/auth.html", {"form": AuthForm})

    @staticmethod
    def post(request):
        if not allow_attempt(request, "login"):
            return HttpResponse(
                "Слишком много попыток. Попробуйте позже.", status=429
            )

        form = AuthForm(request.POST)
        if not form.is_valid():
            return render(request, "user/auth.html", {"form": form})

        email = form.cleaned_data["email"].strip().lower()
        password = form.cleaned_data["password"]
        user = authenticate(request, username=email, password=password)

        # Support accounts registered before email normalization was introduced.
        if user is None:
            account = get_user_model().objects.filter(email__iexact=email).first()
            if account:
                user = authenticate(
                    request, username=account.get_username(), password=password
                )

        if user is not None:
            login(request, user)
            clear_attempts(request, "login")
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
    """Регистрация"""

    @staticmethod
    def get(request):
        return render(request, "user/registration.html", {"form": RegistrationForm})

    @staticmethod
    def post(request):
        if not allow_attempt(request, "registration"):
            return HttpResponse(
                "Слишком много попыток. Попробуйте позже.", status=429
            )

        form = RegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            # Keep the response identical whether the address was already registered.
            messages.info(request, "Запрос обработан. Попробуйте войти в систему.")
            return redirect("user:auth")
        return render(request, "user/registration.html", {"form": form})


class LogoutView(View):
    """Выход"""

    @staticmethod
    def post(request):
        logout(request)
        return redirect("dashboard:index")
