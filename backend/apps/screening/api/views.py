import csv
from datetime import timedelta

from django.db.models import Count
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
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
from apps.screening.services.report_service import ReportService
from apps.screening.services.screening_service import ScreeningService
from apps.users.permissions import IsAnyRole, IsComplianceTeam


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
        language = request.data.get("language", getattr(request.user, "preferred_language", "pt"))
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
        return Response(
            {
                "totals": {
                    "screenings": screenings.count(),
                    "critical": screenings.filter(risk_level=RiskLevel.CRITICAL).count(),
                    "pending": screenings.filter(status=ScreeningRequest.Status.PENDING).count(),
                    "review": screenings.filter(status=ScreeningRequest.Status.REVIEW).count(),
                    "high_risk_countries": screenings.filter(matches__source_code="FATF").distinct().count(),
                },
                "risk_distribution": list(recent_logs),
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
