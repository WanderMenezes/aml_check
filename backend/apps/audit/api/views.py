from rest_framework import mixins, viewsets

from apps.audit.api.serializers import AuditEventSerializer
from apps.audit.models import AuditEvent
from apps.users.permissions import IsComplianceTeam


class AuditEventViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = AuditEventSerializer
    permission_classes = [IsComplianceTeam]
    queryset = AuditEvent.objects.select_related("user").all().order_by("-created_at")

    def get_queryset(self):
        queryset = super().get_queryset()
        action = self.request.query_params.get("action")
        status = self.request.query_params.get("status")
        severity = self.request.query_params.get("severity")
        if action:
            queryset = queryset.filter(action__icontains=action)
        if status:
            queryset = queryset.filter(status=status)
        if severity:
            queryset = queryset.filter(severity=severity)
        return queryset
