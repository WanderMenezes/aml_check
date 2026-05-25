from django.contrib import admin

from apps.audit.models import AuditEvent


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ("created_at", "action", "resource_type", "resource_id", "severity", "status", "user")
    search_fields = ("action", "resource_type", "resource_id", "user__email")
    list_filter = ("severity", "status")
