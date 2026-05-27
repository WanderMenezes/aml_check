import hashlib

from django.db import models
from django.utils import timezone

from common.utils.strings import coalesce, normalize_text


class SourceCode(models.TextChoices):
    OFAC = "OFAC", "OFAC"
    UN = "UN", "United Nations"
    EU = "EU", "European Union"
    FATF = "FATF", "FATF/GAFI"
    INTERPOL = "INTERPOL", "INTERPOL"


class RiskLevel(models.TextChoices):
    LOW = "LOW", "Low"
    MEDIUM = "MEDIUM", "Medium"
    HIGH = "HIGH", "High"
    CRITICAL = "CRITICAL", "Critical"


class Country(models.Model):
    name = models.CharField(max_length=120, unique=True)
    normalized_name = models.CharField(max_length=120, db_index=True, unique=True)
    iso_code = models.CharField(max_length=5, blank=True)
    risk_level = models.CharField(max_length=20, choices=RiskLevel.choices, default=RiskLevel.LOW)
    is_blocked = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "countries"

    def save(self, *args, **kwargs):
        self.normalized_name = normalize_text(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class SanctionsSource(models.Model):
    class SourceType(models.TextChoices):
        SANCTIONS = "SANCTIONS", "Sanctions"
        COUNTRY_RISK = "COUNTRY_RISK", "Country risk"
        LAW_ENFORCEMENT = "LAW_ENFORCEMENT", "Law enforcement"

    class SourceFormat(models.TextChoices):
        XML = "XML", "XML"
        JSON = "JSON", "JSON"
        CSV = "CSV", "CSV"
        HTML = "HTML", "HTML"

    class HealthStatus(models.TextChoices):
        OK = "OK", "OK"
        WARNING = "WARNING", "Warning"
        ERROR = "ERROR", "Error"

    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=120)
    source_type = models.CharField(max_length=32, choices=SourceType.choices)
    source_format = models.CharField(max_length=16, choices=SourceFormat.choices)
    endpoint = models.URLField(blank=True)
    landing_url = models.URLField(blank=True)
    enabled = models.BooleanField(default=True)
    sync_frequency = models.CharField(max_length=40, default="daily")
    health_status = models.CharField(max_length=16, choices=HealthStatus.choices, default=HealthStatus.OK)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return self.name


class WatchlistEntry(models.Model):
    class EntryType(models.TextChoices):
        PERSON = "PERSON", "Person"
        ENTITY = "ENTITY", "Entity"
        VESSEL = "VESSEL", "Vessel"
        COUNTRY = "COUNTRY", "Country"

    source = models.ForeignKey(SanctionsSource, on_delete=models.CASCADE, related_name="entries")
    external_id = models.CharField(max_length=120, blank=True)
    entry_type = models.CharField(max_length=20, choices=EntryType.choices, default=EntryType.PERSON)
    primary_name = models.CharField(max_length=255)
    normalized_name = models.CharField(max_length=255, db_index=True)
    aliases = models.JSONField(default=list, blank=True)
    countries = models.JSONField(default=list, blank=True)
    nationality = models.CharField(max_length=120, blank=True)
    date_of_birth = models.CharField(max_length=120, blank=True)
    identifiers = models.JSONField(default=dict, blank=True)
    remarks = models.TextField(blank=True)
    source_url = models.URLField(blank=True)
    raw_payload = models.JSONField(default=dict, blank=True)
    record_hash = models.CharField(max_length=40, db_index=True)
    is_active = models.BooleanField(default=True)
    listed_on = models.DateField(null=True, blank=True)
    removed_on = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("source", "record_hash")
        ordering = ["primary_name"]

    def save(self, *args, **kwargs):
        self.normalized_name = normalize_text(self.primary_name)
        if not self.record_hash:
            seed = coalesce(self.external_id, self.primary_name, self.nationality, self.source.code)
            self.record_hash = hashlib.sha1(seed.encode("utf-8")).hexdigest()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.primary_name} [{self.source.code}]"


class CountryRiskEntry(models.Model):
    source = models.ForeignKey(SanctionsSource, on_delete=models.CASCADE, related_name="countries_risk")
    country_name = models.CharField(max_length=120)
    iso_code = models.CharField(max_length=5, blank=True)
    risk_level = models.CharField(max_length=20, choices=RiskLevel.choices, default=RiskLevel.LOW)
    list_name = models.CharField(max_length=120, blank=True)
    notes = models.TextField(blank=True)
    raw_payload = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    effective_date = models.DateField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("source", "country_name", "list_name")
        ordering = ["country_name"]

    def __str__(self):
        return f"{self.country_name} ({self.risk_level})"


class SyncJobLog(models.Model):
    class TriggerType(models.TextChoices):
        MANUAL = "MANUAL", "Manual"
        SCHEDULED = "SCHEDULED", "Scheduled"

    class Status(models.TextChoices):
        RUNNING = "RUNNING", "Running"
        SUCCESS = "SUCCESS", "Success"
        FAILED = "FAILED", "Failed"

    source = models.ForeignKey(SanctionsSource, on_delete=models.SET_NULL, null=True, blank=True, related_name="sync_logs")
    trigger = models.CharField(max_length=20, choices=TriggerType.choices, default=TriggerType.MANUAL)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RUNNING)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    items_processed = models.PositiveIntegerField(default=0)
    items_created = models.PositiveIntegerField(default=0)
    items_updated = models.PositiveIntegerField(default=0)
    items_deactivated = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-started_at"]

    def close(self, status: str, **stats):
        self.status = status
        self.finished_at = timezone.now()
        for field, value in stats.items():
            setattr(self, field, value)
        self.save()


class RiskRule(models.Model):
    class ConditionType(models.TextChoices):
        SOURCE_MATCH = "SOURCE_MATCH", "Source match"
        COUNTRY_MATCH = "COUNTRY_MATCH", "Country match"
        SCORE_THRESHOLD = "SCORE_THRESHOLD", "Score threshold"

    name = models.CharField(max_length=120)
    condition_type = models.CharField(max_length=30, choices=ConditionType.choices)
    source_code = models.CharField(max_length=20, choices=SourceCode.choices, blank=True)
    target_value = models.CharField(max_length=120, blank=True)
    risk_level = models.CharField(max_length=20, choices=RiskLevel.choices)
    weight = models.PositiveIntegerField(default=100)
    enabled = models.BooleanField(default=True)
    config = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-weight", "name"]

    def __str__(self):
        return self.name
