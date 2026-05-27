from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path

from common.portal import (
    portal_admin_login,
    portal_admin_logout,
    portal_create_search_link,
    portal_create_user,
    portal_delete_search_link,
    portal_home,
    portal_report_csv,
    portal_report_pdf,
    portal_screening,
    portal_update_company_profile,
    portal_update_search_link,
)
from common.schemas.openapi import redoc_ui, schema_view, swagger_ui

admin.site.site_header = "AML Check Enterprise"
admin.site.site_title = "AML Check Admin"
admin.site.index_title = "Centro de controlo"


def healthcheck(request):
    return JsonResponse(
        {
            "status": "ok",
            "app": settings.APP_NAME,
            "db_engine": settings.DATABASES["default"]["ENGINE"],
            "time_zone": settings.TIME_ZONE,
        }
    )


urlpatterns = [
    path("", portal_home, name="portal-home"),
    path("portal-admin/login/", portal_admin_login, name="portal-admin-login"),
    path("portal-admin/logout/", portal_admin_logout, name="portal-admin-logout"),
    path("portal-admin/users/create/", portal_create_user, name="portal-create-user"),
    path("portal-admin/search-links/create/", portal_create_search_link, name="portal-create-search-link"),
    path("portal-admin/search-links/<int:source_id>/update/", portal_update_search_link, name="portal-update-search-link"),
    path("portal-admin/search-links/<int:source_id>/delete/", portal_delete_search_link, name="portal-delete-search-link"),
    path("portal-admin/company-profile/", portal_update_company_profile, name="portal-company-profile"),
    path("run-screening/", portal_screening, name="portal-screening"),
    path("portal-reports/<int:screening_id>/pdf/", portal_report_pdf, name="portal-report-pdf"),
    path("portal-reports/<int:screening_id>/csv/", portal_report_csv, name="portal-report-csv"),
    path("admin/", admin.site.urls),
    path("health/", healthcheck, name="healthcheck"),
    path("api/schema/", schema_view, name="api-schema"),
    path("api/docs/", swagger_ui, name="api-docs"),
    path("api/redoc/", redoc_ui, name="api-redoc"),
    path("api/auth/", include("apps.users.api.urls")),
    path("api/users/", include("apps.users.api.urls_users")),
    path("api/screening/", include("apps.screening.api.urls")),
    path("api/intelligence/", include("apps.intelligence.api.urls")),
    path("api/audit/", include("apps.audit.api.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
