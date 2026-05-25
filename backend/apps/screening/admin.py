from django.contrib import admin

from apps.screening.models import Alert, Client, PDFReport, ScreeningMatch, ScreeningRequest


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("full_name", "company_name", "country", "nationality", "created_at")
    search_fields = ("full_name", "company_name", "passport_number", "national_id")


@admin.register(ScreeningRequest)
class ScreeningRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "client", "risk_level", "status", "created_by", "created_at")
    list_filter = ("risk_level", "status")


@admin.register(ScreeningMatch)
class ScreeningMatchAdmin(admin.ModelAdmin):
    list_display = ("screening", "source_code", "matched_name", "score", "risk_level")
    list_filter = ("source_code", "risk_level")


@admin.register(PDFReport)
class PDFReportAdmin(admin.ModelAdmin):
    list_display = ("screening", "language", "created_by", "created_at")


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ("user", "alert_type", "title", "is_read", "created_at")
    list_filter = ("alert_type", "is_read")
