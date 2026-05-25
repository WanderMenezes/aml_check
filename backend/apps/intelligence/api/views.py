from django.db.models import Count
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.intelligence.api.serializers import (
    CountrySerializer,
    CountryRiskEntrySerializer,
    RiskRuleSerializer,
    SanctionsSourceSerializer,
    SyncJobLogSerializer,
    WatchlistEntrySerializer,
)
from apps.audit.services.audit_service import AuditService
from apps.intelligence.models import Country, CountryRiskEntry, RiskRule, SanctionsSource, SyncJobLog, WatchlistEntry
from apps.intelligence.services.sync_service import SourceSyncService
from apps.users.permissions import IsAdmin, IsComplianceTeam


class SanctionsSourceViewSet(viewsets.ModelViewSet):
    serializer_class = SanctionsSourceSerializer
    permission_classes = [IsComplianceTeam]
    queryset = SanctionsSource.objects.all().order_by("code")

    @action(detail=True, methods=["post"], permission_classes=[IsAdmin])
    def sync_now(self, request, pk=None):
        source = self.get_object()
        log = SourceSyncService.sync_source(source, trigger=SyncJobLog.TriggerType.MANUAL, request=request)
        return Response(SyncJobLogSerializer(log).data, status=status.HTTP_202_ACCEPTED)


class WatchlistEntryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = WatchlistEntrySerializer
    permission_classes = [IsComplianceTeam]
    queryset = WatchlistEntry.objects.select_related("source").all().order_by("primary_name")

    def get_queryset(self):
        queryset = super().get_queryset()
        source = self.request.query_params.get("source")
        search = self.request.query_params.get("search")
        if source:
            queryset = queryset.filter(source__code=source)
        if search:
            queryset = queryset.filter(primary_name__icontains=search)
        return queryset


class CountryRiskEntryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CountryRiskEntrySerializer
    permission_classes = [IsComplianceTeam]
    queryset = CountryRiskEntry.objects.select_related("source").filter(is_active=True).order_by("country_name")


class CountryViewSet(viewsets.ModelViewSet):
    serializer_class = CountrySerializer
    permission_classes = [IsAdmin]
    queryset = Country.objects.all().order_by("name")

    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.query_params.get("search")
        blocked = self.request.query_params.get("blocked")
        if search:
            queryset = queryset.filter(name__icontains=search)
        if blocked in {"true", "false"}:
            queryset = queryset.filter(is_blocked=blocked == "true")
        return queryset

    def perform_update(self, serializer):
        country = serializer.save()
        AuditService.record(
            action="country_rule_updated",
            request=self.request,
            resource_type="country",
            resource_id=str(country.pk),
            metadata={"risk_level": country.risk_level, "is_blocked": country.is_blocked},
        )


class SyncJobLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SyncJobLogSerializer
    permission_classes = [IsComplianceTeam]
    queryset = SyncJobLog.objects.select_related("source").all().order_by("-started_at")


class RiskRuleViewSet(viewsets.ModelViewSet):
    serializer_class = RiskRuleSerializer
    permission_classes = [IsAdmin]
    queryset = RiskRule.objects.all().order_by("-weight", "name")

    def perform_create(self, serializer):
        rule = serializer.save()
        AuditService.record(
            action="risk_rule_created",
            request=self.request,
            resource_type="risk_rule",
            resource_id=str(rule.pk),
            metadata={"risk_level": rule.risk_level},
        )

    def perform_update(self, serializer):
        rule = serializer.save()
        AuditService.record(
            action="risk_rule_updated",
            request=self.request,
            resource_type="risk_rule",
            resource_id=str(rule.pk),
            metadata={"risk_level": rule.risk_level, "enabled": rule.enabled},
        )


class IntelligenceSummaryView(APIView):
    permission_classes = [IsComplianceTeam]

    def get(self, request):
        by_source = list(
            WatchlistEntry.objects.filter(is_active=True)
            .values("source__code")
            .annotate(total=Count("id"))
            .order_by("source__code")
        )
        return Response(
            {
                "sources": SanctionsSourceSerializer(SanctionsSource.objects.all(), many=True).data,
                "watchlist_count": WatchlistEntry.objects.filter(is_active=True).count(),
                "country_risk_count": CountryRiskEntry.objects.filter(is_active=True).count(),
                "countries_count": Country.objects.count(),
                "blocked_countries_count": Country.objects.filter(is_blocked=True).count(),
                "rules_count": RiskRule.objects.filter(enabled=True).count(),
                "by_source": by_source,
            }
        )
