from django.contrib.auth import get_user_model
from django.db.models import Count
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.api.serializers import (
    LoginSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RefreshTokenSerializer,
    SessionSerializer,
    UserCreateSerializer,
    UserSerializer,
)
from apps.users.models import UserSession
from apps.users.permissions import IsAdmin
from apps.users.services import AuthService
from apps.audit.services.audit_service import AuditService
from common.utils.i18n import get_language, translate

User = get_user_model()


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            token_bundle = AuthService.login(**serializer.validated_data, request=request)
        except ValueError:
            return Response({"detail": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)
        user = token_bundle.pop("user")
        return Response(
            {
                "message": translate("login_success", get_language(request)),
                **token_bundle,
                "user": UserSerializer(user).data,
            }
        )


class RefreshView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RefreshTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            token_bundle = AuthService.refresh(serializer.validated_data["refresh"])
        except Exception:
            return Response({"detail": "Unable to refresh token."}, status=status.HTTP_400_BAD_REQUEST)
        return Response(token_bundle)


class LogoutView(APIView):
    def post(self, request):
        AuthService.logout(request.user, request.auth, request=request)
        return Response({"message": translate("logout_success", get_language(request))})


class MeView(APIView):
    def get(self, request):
        return Response(UserSerializer(request.user).data)


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = AuthService.build_password_reset(serializer.validated_data["email"], request=request)
        return Response(
            {
                "message": translate("password_reset_sent", get_language(request)),
                "sent": payload["sent"],
            }
        )


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            AuthService.reset_password(**serializer.validated_data)
        except Exception:
            return Response({"detail": "Invalid reset token."}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"detail": "Password updated successfully."})


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by("email")
    permission_classes = [IsAdmin]
    renderer_classes = [JSONRenderer, TemplateHTMLRenderer]

    def get_permissions(self):
        if (
            self.action == "list"
            and self.request.method == "GET"
            and getattr(self.request.accepted_renderer, "format", "") == "html"
        ):
            return [AllowAny()]
        return super().get_permissions()

    def get_serializer_class(self):
        if self.action in {"create", "update", "partial_update"}:
            return UserCreateSerializer
        return UserSerializer

    def list(self, request, *args, **kwargs):
        if getattr(request.accepted_renderer, "format", "") == "html":
            django_user = getattr(getattr(request, "_request", None), "user", None)
            can_view_users = bool(
                getattr(django_user, "is_authenticated", False)
                and (getattr(django_user, "is_staff", False) or getattr(django_user, "is_superuser", False))
            )
            users = self.get_queryset() if can_view_users else User.objects.none()
            role_totals = users.values("role").annotate(total=Count("id")).order_by("role") if can_view_users else []
            context = {
                "can_view_users": can_view_users,
                "users": users,
                "role_totals": role_totals,
                "total_users": users.count() if can_view_users else 0,
                "active_users": users.filter(is_active=True).count() if can_view_users else 0,
                "session_total": UserSession.objects.filter(is_revoked=False).count() if can_view_users else 0,
            }
            return Response(context, template_name="portal/users_api.html")
        return super().list(request, *args, **kwargs)

    def perform_create(self, serializer):
        user = serializer.save()
        AuditService.record(
            action="user_created",
            request=self.request,
            resource_type="user",
            resource_id=str(user.pk),
            metadata={"role": user.role, "email": user.email},
        )

    def perform_update(self, serializer):
        user = serializer.save()
        AuditService.record(
            action="user_updated",
            request=self.request,
            resource_type="user",
            resource_id=str(user.pk),
            metadata={"role": user.role, "is_active": user.is_active},
        )

    @action(detail=True, methods=["get"])
    def sessions(self, request, pk=None):
        sessions = UserSession.objects.filter(user_id=pk)
        return Response(SessionSerializer(sessions, many=True).data)


class SessionViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = SessionSerializer

    def get_queryset(self):
        return UserSession.objects.filter(user=self.request.user)
