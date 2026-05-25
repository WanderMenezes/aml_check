from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.screening.api.views import AlertViewSet, ClientViewSet, DashboardView, ReportViewSet, ScreeningRequestViewSet

router = DefaultRouter()
router.include_format_suffixes = False
router.register("clients", ClientViewSet, basename="clients")
router.register("requests", ScreeningRequestViewSet, basename="screenings")
router.register("reports", ReportViewSet, basename="reports")
router.register("alerts", AlertViewSet, basename="alerts")

urlpatterns = router.urls + [
    path("dashboard/", DashboardView.as_view(), name="screening-dashboard"),
]
