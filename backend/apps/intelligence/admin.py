from django.contrib import admin

from apps.intelligence.models import Country, CountryRiskEntry, RiskRule, SanctionsSource, SyncJobLog, WatchlistEntry


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ("name", "iso_code", "risk_level", "is_blocked", "updated_at")
    search_fields = ("name", "normalized_name", "iso_code")
    list_filter = ("risk_level", "is_blocked")


@admin.register(SanctionsSource)
class SanctionsSourceAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "source_type", "source_format", "enabled", "last_synced_at", "health_status")
    list_filter = ("source_type", "source_format", "enabled", "health_status")


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
