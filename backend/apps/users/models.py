import uuid

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone


class UserRole(models.TextChoices):
    ADMIN = "ADMIN", "Admin"
    COMPLIANCE_OFFICER = "COMPLIANCE_OFFICER", "Compliance Officer"
    ANALYST = "ANALYST", "Analyst"
    VIEWER = "VIEWER", "Viewer"


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        extra_fields["username"] = extra_fields.get("username") or email.split("@")[0]
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", UserRole.ADMIN)
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=32, choices=UserRole.choices, default=UserRole.ANALYST)
    phone = models.CharField(max_length=32, blank=True)
    preferred_language = models.CharField(max_length=5, default="pt")
    must_change_password = models.BooleanField(default=False)
    last_password_change = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return f"{self.get_full_name() or self.email} ({self.role})"


class UserSession(models.Model):
    session_key = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sessions")
    refresh_jti = models.CharField(max_length=64, unique=True)
    access_jti = models.CharField(max_length=64, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(auto_now_add=True)
    is_revoked = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def touch(self):
        self.last_used_at = timezone.now()
        self.save(update_fields=["last_used_at"])

    def revoke(self):
        self.is_revoked = True
        self.save(update_fields=["is_revoked"])

    @property
    def is_expired(self):
        return self.expires_at <= timezone.now()
