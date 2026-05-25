from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.intelligence.api.views import (
    CountryViewSet,
    CountryRiskEntryViewSet,
    IntelligenceSummaryView,
    RiskRuleViewSet,
    SanctionsSourceViewSet,
    SyncJobLogViewSet,
    WatchlistEntryViewSet,
)

router = DefaultRouter()
router.include_format_suffixes = False
router.register("sources", SanctionsSourceViewSet, basename="sources")
router.register("watchlist", WatchlistEntryViewSet, basename="watchlist")
router.register("countries", CountryViewSet, basename="countries")
router.register("country-risk", CountryRiskEntryViewSet, basename="country-risk")
router.register("sync", SyncJobLogViewSet, basename="sync")
router.register("rules", RiskRuleViewSet, basename="rules")

urlpatterns = router.urls + [
    path("summary/", IntelligenceSummaryView.as_view(), name="intelligence-summary"),
]
