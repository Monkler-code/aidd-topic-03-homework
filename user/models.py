"""Custom user model using email as the primary identifier."""

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class UserManager(BaseUserManager):
    """Manager for User model with email as username."""

    def create_user(self, username=None, email=None, password=None, **extra_fields):
        """Create and return a regular user.

        Args:
            username: Can be email or ignored (email is used as username).
            email: The user's email address.
            password: The user's password.
        """
        # If email is None, use username as email (backward compat)
        if email is None:
            email = username or ""
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        extra_fields.setdefault("is_active", True)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """Create and return a superuser."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom user model that uses email as the username field.
    This allows login via email instead of a separate username.
    """

    email = models.EmailField(unique=True, verbose_name="Email")
    is_staff = models.BooleanField(
        default=False,
        help_text="Designates whether the user can log into this admin site.",
        verbose_name="staff status",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Designates whether this user should be treated as active.",
        verbose_name="active status",
    )
    date_joined = models.DateTimeField(verbose_name="date joined", auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"

    def __str__(self) -> str:
        return self.email
