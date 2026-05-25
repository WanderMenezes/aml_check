import hashlib

from django.conf import settings
from django.db import models

from apps.intelligence.models import RiskLevel, WatchlistEntry


class Client(models.Model):
    class SubjectType(models.TextChoices):
        INDIVIDUAL = "INDIVIDUAL", "Individual"
        COMPANY = "COMPANY", "Company"

    subject_type = models.CharField(max_length=20, choices=SubjectType.choices, default=SubjectType.INDIVIDUAL)
    full_name = models.CharField(max_length=255)
    company_name = models.CharField(max_length=255, blank=True)
    country = models.CharField(max_length=120, blank=True)
    nationality = models.CharField(max_length=120, blank=True)
    passport_number = models.CharField(max_length=100, blank=True)
    national_id = models.CharField(max_length=100, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="clients_created")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return self.company_name or self.full_name


class ScreeningRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        COMPLETED = "COMPLETED", "Completed"
        REVIEW = "REVIEW", "Review"

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="screenings")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="screenings_created")
    risk_level = models.CharField(max_length=20, choices=RiskLevel.choices, default=RiskLevel.LOW)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    recommendation = models.TextField(blank=True)
    comments = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="screenings_approved")
    approved_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Screening #{self.pk} - {self.client}"


class ScreeningMatch(models.Model):
    screening = models.ForeignKey(ScreeningRequest, on_delete=models.CASCADE, related_name="matches")
    watchlist_entry = models.ForeignKey(WatchlistEntry, on_delete=models.SET_NULL, null=True, blank=True, related_name="screening_matches")
    source_code = models.CharField(max_length=20)
    matched_name = models.CharField(max_length=255)
    score = models.PositiveIntegerField(default=0)
    risk_level = models.CharField(max_length=20, choices=RiskLevel.choices, default=RiskLevel.LOW)
    nationality = models.CharField(max_length=120, blank=True)
    aliases = models.JSONField(default=list, blank=True)
    details = models.JSONField(default=dict, blank=True)
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-score", "-created_at"]


class PDFReport(models.Model):
    screening = models.OneToOneField(ScreeningRequest, on_delete=models.CASCADE, related_name="report")
    file = models.FileField(upload_to="reports/")
    language = models.CharField(max_length=5, default="pt")
    signature_hash = models.CharField(max_length=64, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.signature_hash:
            self.signature_hash = hashlib.sha256(f"{self.screening_id}:{self.language}".encode("utf-8")).hexdigest()
        super().save(*args, **kwargs)


class Alert(models.Model):
    class AlertType(models.TextChoices):
        NEW_MATCH = "NEW_MATCH", "New Match"
        PENDING_REVIEW = "PENDING_REVIEW", "Pending Review"
        SYNC_FAILURE = "SYNC_FAILURE", "Sync Failure"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="alerts")
    screening = models.ForeignKey(ScreeningRequest, on_delete=models.CASCADE, null=True, blank=True, related_name="alerts")
    alert_type = models.CharField(max_length=30, choices=AlertType.choices)
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
