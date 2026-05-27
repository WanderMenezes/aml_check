import csv
from datetime import timedelta

from django.db.models import Count
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.services.audit_service import AuditService
from apps.intelligence.models import RiskLevel
from apps.screening.api.serializers import (
    AlertSerializer,
    ClientSerializer,
    PDFReportSerializer,
    ScreeningRequestSerializer,
    ScreeningRunSerializer,
)
from apps.screening.models import Alert, Client, PDFReport, ScreeningRequest
from apps.screening.repositories.watchlist_repository import WatchlistRepository
from apps.screening.services.report_service import ReportService
from apps.screening.services.screening_service import ScreeningService
from apps.users.permissions import IsAnyRole, IsComplianceTeam
from common.utils.i18n import normalize_language


class ClientViewSet(viewsets.ModelViewSet):
    serializer_class = ClientSerializer
    permission_classes = [IsComplianceTeam]
    queryset = Client.objects.all().order_by("-updated_at")

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class ScreeningRequestViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ScreeningRequestSerializer
    permission_classes = [IsAnyRole]
    queryset = ScreeningRequest.objects.select_related("client", "created_by").prefetch_related("matches").all().order_by("-created_at")

    def get_queryset(self):
        queryset = super().get_queryset()
        risk = self.request.query_params.get("risk")
        status_filter = self.request.query_params.get("status")
        search = self.request.query_params.get("search")
        if risk:
            queryset = queryset.filter(risk_level=risk)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if search:
            queryset = queryset.filter(client__full_name__icontains=search) | queryset.filter(client__country__icontains=search)
        return queryset.distinct()

    @action(detail=False, methods=["post"], permission_classes=[IsComplianceTeam])
    def run(self, request):
        serializer = ScreeningRunSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        screening = ScreeningService.run_screening(serializer.validated_data, user=request.user, request=request)
        return Response(ScreeningRequestSerializer(screening).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], permission_classes=[IsComplianceTeam])
    def export_pdf(self, request, pk=None):
        screening = self.get_object()
        language = normalize_language(
            request.data.get("language") or request.query_params.get("language") or request.headers.get("Accept-Language"),
            fallback=getattr(request.user, "preferred_language", "pt"),
        )
        report = ReportService.build_pdf(screening, language=language, request=request)
        return Response(PDFReportSerializer(report).data)

    @action(detail=True, methods=["get"], permission_classes=[IsComplianceTeam])
    def export_csv(self, request, pk=None):
        screening = self.get_object()
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="screening-{screening.pk}.csv"'
        writer = csv.writer(response)
        writer.writerow(["Source", "Matched Name", "Score", "Risk Level", "Remarks"])
        for match in screening.matches.all():
            writer.writerow([match.source_code, match.matched_name, match.score, match.risk_level, match.remarks])
        AuditService.record(
            action="screening_exported_csv",
            request=request,
            user=request.user,
            resource_type="screening",
            resource_id=str(screening.pk),
        )
        return response


class DashboardView(APIView):
    permission_classes = [IsAnyRole]

    def get(self, request):
        recent_window = timezone.now() - timedelta(days=30)
        screenings = ScreeningRequest.objects.all()
        recent_logs = screenings.filter(created_at__gte=recent_window).values("risk_level").annotate(total=Count("id"))

        # timeseries per day for last 30 days
        days = []
        for i in range(30):
            day = timezone.now().date() - timedelta(days=29 - i)
            count = screenings.filter(created_at__date=day).count()
            days.append({"date": day.isoformat(), "total": count})

        # top sources (by matches) in recent window
        top_sources_qs = (
            ScreeningRequest.objects.filter(created_at__gte=recent_window)
            .values("matches__source_code")
            .annotate(total=Count("matches__id"))
            .order_by("-total")[:5]
        )
        top_sources = [{"source_code": item["matches__source_code"], "total": item["total"]} for item in top_sources_qs]

        # average score for matches in recent window
        from django.db.models import Avg

        avg_score_qs = (
            ScreeningRequest.objects.filter(created_at__gte=recent_window).values("matches__score").aggregate(avg_score=Avg("matches__score"))
        )
        avg_score = avg_score_qs.get("avg_score") or 0

        unread_alerts = Alert.objects.filter(user=request.user, is_read=False).count()

        return Response(
            {
                "totals": {
                    "screenings": screenings.count(),
                    "critical": screenings.filter(risk_level=RiskLevel.CRITICAL).count(),
                    "pending": screenings.filter(status=ScreeningRequest.Status.PENDING).count(),
                    "review": screenings.filter(status=ScreeningRequest.Status.REVIEW).count(),
                    "high_risk_countries": screenings.filter(matches__source_code="FATF").distinct().count(),
                    "avg_score": round(avg_score, 1),
                    "unread_alerts": unread_alerts,
                },
                "risk_distribution": list(recent_logs),
                "timeseries": days,
                "top_sources": top_sources,
                "recent_screenings": ScreeningRequestSerializer(screenings[:5], many=True).data,
                "recent_alerts": AlertSerializer(Alert.objects.filter(user=request.user)[:5], many=True).data,
            }
        )


class ReportViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = PDFReportSerializer
    permission_classes = [IsAnyRole]
    queryset = PDFReport.objects.select_related("screening").all().order_by("-created_at")


class AlertViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = AlertSerializer
    permission_classes = [IsAnyRole]

    def get_queryset(self):
        return Alert.objects.filter(user=self.request.user).order_by("-created_at")

    @action(detail=True, methods=["post"])
    def mark_read(self, request, pk=None):
        alert = self.get_object()
        alert.is_read = True
        alert.save(update_fields=["is_read"])
        return Response(AlertSerializer(alert).data)


class ExternalSearchView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        query = request.data.get("query") or ""
        if not query or not str(query).strip():
            return Response({"detail": "Provide a query."}, status=status.HTTP_400_BAD_REQUEST)
        results = WatchlistRepository.external_site_matches(str(query).strip())
        # group by url or source code
        groups = []
        for r in results:
            key = r.get("url") or (r.get("source").code if r.get("source") else "UNKNOWN")
            groups.append({
                "key": key,
                "url": r.get("url"),
                "checked_url": r.get("checked_url"),
                "source_code": r.get("source_code") or (r.get("source").code if r.get("source") else None),
                "source_name": r.get("source_name") or (r.get("source").name if r.get("source") else None),
                "title": r.get("title"),
                "snippet": r.get("snippet"),
                "score": r.get("score"),
                "status": r.get("status"),
                "decision": r.get("decision"),
                "decision_reason": r.get("decision_reason"),
                "evidence_level": r.get("evidence_level"),
                "important_terms": r.get("important_terms") or [],
            })
        return Response({"query": query, "groups": groups})
