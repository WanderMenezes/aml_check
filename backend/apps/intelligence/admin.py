import re

from django import forms
from django.contrib import admin

from apps.intelligence.models import Country, CountryRiskEntry, RiskRule, SanctionsSource, SyncJobLog, WatchlistEntry


def _unique_source_code(name: str, current_id=None) -> str:
    base = re.sub(r"[^A-Z0-9]", "", (name or "SOURCE").upper())[:16] or "SOURCE"
    candidate = base[:20]
    suffix = 2
    queryset = SanctionsSource.objects.all()
    if current_id:
        queryset = queryset.exclude(pk=current_id)
    while queryset.filter(code=candidate).exists():
        suffix_text = str(suffix)
        candidate = f"{base[:20 - len(suffix_text)]}{suffix_text}"
        suffix += 1
    return candidate


class SanctionsSourceAdminForm(forms.ModelForm):
    code = forms.CharField(
        required=False,
        max_length=20,
        help_text="Opcional. Se deixar vazio, o sistema gera um codigo unico a partir do nome.",
    )

    class Meta:
        model = SanctionsSource
        fields = "__all__"

    def clean_code(self):
        raw_code = (self.cleaned_data.get("code") or "").strip().upper()
        return re.sub(r"[^A-Z0-9]", "", raw_code)[:20]

    def clean(self):
        cleaned_data = super().clean()
        code = cleaned_data.get("code")
        if not code:
            code = _unique_source_code(self.cleaned_data.get("name") or "", self.instance.pk)
        queryset = SanctionsSource.objects.filter(code=code)
        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            code = _unique_source_code(code, self.instance.pk)
        cleaned_data["code"] = code
        return cleaned_data


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ("name", "iso_code", "risk_level", "is_blocked", "updated_at")
    search_fields = ("name", "normalized_name", "iso_code")
    list_filter = ("risk_level", "is_blocked")


@admin.register(SanctionsSource)
class SanctionsSourceAdmin(admin.ModelAdmin):
    form = SanctionsSourceAdminForm
    list_display = ("code", "name", "source_type", "source_format", "enabled", "last_synced_at", "health_status")
    list_filter = ("source_type", "source_format", "enabled", "health_status")
    search_fields = ("code", "name", "landing_url", "endpoint")


@admin.register(WatchlistEntry)
class WatchlistEntryAdmin(admin.ModelAdmin):
    list_display = ("primary_name", "source", "entry_type", "nationality", "is_active", "updated_at")
    search_fields = ("primary_name", "external_id", "normalized_name")
    list_filter = ("source", "entry_type", "is_active")


@admin.register(CountryRiskEntry)
class CountryRiskEntryAdmin(admin.ModelAdmin):
    list_display = ("country_name", "source", "list_name", "risk_level", "is_active")
    search_fields = ("country_name", "iso_code")
    list_filter = ("risk_level", "source", "is_active")


@admin.register(SyncJobLog)
class SyncJobLogAdmin(admin.ModelAdmin):
    list_display = ("source", "trigger", "status", "started_at", "finished_at", "items_processed")
    list_filter = ("trigger", "status")


@admin.register(RiskRule)
class RiskRuleAdmin(admin.ModelAdmin):
    list_display = ("name", "condition_type", "source_code", "target_value", "risk_level", "enabled")
    list_filter = ("condition_type", "risk_level", "enabled")
