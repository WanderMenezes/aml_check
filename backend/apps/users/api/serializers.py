from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.users.models import UserSession

User = get_user_model()


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class RefreshTokenSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(min_length=8)


class UserSerializer(serializers.ModelSerializer):
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "role",
            "phone",
            "preferred_language",
            "is_active",
            "last_login",
            "permissions",
        ]

    def get_permissions(self, obj):
        role_permissions = {
            "ADMIN": ["manage_users", "manage_rules", "sync_sources", "run_screening", "view_audit", "export_reports"],
            "COMPLIANCE_OFFICER": ["run_screening", "view_audit", "export_reports", "review_alerts"],
            "ANALYST": ["run_screening", "export_reports", "review_alerts"],
            "VIEWER": ["view_dashboard", "view_results", "view_reports"],
        }
        return role_permissions.get(obj.role, [])


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "password",
            "first_name",
            "last_name",
            "role",
            "phone",
            "preferred_language",
            "is_active",
        ]

    def create(self, validated_data):
        password = validated_data.pop("password")
        return User.objects.create_user(password=password, **validated_data)

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for key, value in validated_data.items():
            setattr(instance, key, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class SessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSession
        fields = [
            "session_key",
            "ip_address",
            "user_agent",
            "expires_at",
            "created_at",
            "last_used_at",
            "is_revoked",
        ]
