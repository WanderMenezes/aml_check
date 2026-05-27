from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from apps.users.models import CompanyProfile, User, UserSession


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ("email", "first_name", "last_name", "role", "is_active", "is_staff")
    list_filter = ("role", "is_active", "is_staff")
    ordering = ("email",)
    fieldsets = DjangoUserAdmin.fieldsets + (
        ("Compliance", {"fields": ("role", "preferred_language", "phone", "must_change_password")}),
    )
    add_fieldsets = DjangoUserAdmin.add_fieldsets + (
        ("Compliance", {"fields": ("email", "role", "preferred_language")}),
    )


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ("user", "session_key", "ip_address", "expires_at", "is_revoked")
    search_fields = ("user__email", "session_key", "refresh_jti")
    list_filter = ("is_revoked",)


@admin.register(CompanyProfile)
class CompanyProfileAdmin(admin.ModelAdmin):
    list_display = ("legal_name", "trading_name", "tax_id", "email", "updated_at")
    search_fields = ("legal_name", "trading_name", "tax_id", "email")
