from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.generic import View

from .forms import AuthForm, RegistrationForm
from .rate_limit import RateLimitUnavailable, allow_attempt, clear_attempts


def _rate_limit_response(request, scope):
    try:
        allowed = allow_attempt(request, scope)
    except RateLimitUnavailable:
        return HttpResponse(
            "Сервис авторизации временно недоступен. Попробуйте позже.",
            status=503,
            headers={"Retry-After": "60"},
        )
    if not allowed:
        return HttpResponse("Слишком много попыток. Попробуйте позже.", status=429)
    return None


class AuthView(View):
    """Авторизация"""

    @staticmethod
    def get(request):
        return render(
            request,
            "user/auth.html",
            {"form": AuthForm(), "next": request.GET.get("next", "")},
        )

    @staticmethod
    def post(request):
        rate_limit_response = _rate_limit_response(request, "login")
        if rate_limit_response:
            return rate_limit_response

        next_url = request.POST.get("next") or request.GET.get("next", "")
        form = AuthForm(request.POST)
        if not form.is_valid():
            return render(
                request, "user/auth.html", {"form": form, "next": next_url}
            )

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
            try:
                clear_attempts(request, "login")
            except RateLimitUnavailable:
                return HttpResponse(
                    "Сервис авторизации временно недоступен. Попробуйте позже.",
                    status=503,
                    headers={"Retry-After": "60"},
                )
            login(request, user)
            if url_has_allowed_host_and_scheme(
                next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                return redirect(next_url)
            return redirect("dashboard:index")
        return render(
            request,
            "user/auth.html",
            {
                "form": form,
                "error": "Неверный логин или пароль! Повторите попытку.",
                "next": next_url,
            },
        )


class RegistrationView(View):
    """Регистрация"""

    @staticmethod
    def get(request):
        return render(request, "user/registration.html", {"form": RegistrationForm()})

    @staticmethod
    def post(request):
        rate_limit_response = _rate_limit_response(request, "registration")
        if rate_limit_response:
            return rate_limit_response

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
