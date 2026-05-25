from rest_framework import serializers

from apps.audit.models import AuditEvent


class AuditEventSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = AuditEvent
        fields = [
            "id",
            "created_at",
            "action",
            "resource_type",
            "resource_id",
            "severity",
            "status",
            "description",
            "ip_address",
            "metadata",
            "user_email",
        ]
