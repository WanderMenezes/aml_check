from apps.audit.models import AuditEvent


class AuditService:
    @staticmethod
    def record(
        action: str,
        request=None,
        user=None,
        resource_type: str = "",
        resource_id: str = "",
        status: str = "success",
        severity: str = AuditEvent.Severity.INFO,
        description: str = "",
        metadata: dict | None = None,
    ) -> AuditEvent:
        resolved_user = user
        if resolved_user is None and request is not None:
            candidate = getattr(request, "user", None)
            if getattr(candidate, "is_authenticated", False):
                resolved_user = candidate
        return AuditEvent.objects.create(
            user=resolved_user,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            status=status,
            severity=severity,
            description=description,
            ip_address=getattr(request, "client_ip", None) if request else None,
            metadata=metadata or {},
        )
