from datetime import UTC, datetime, timedelta

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from apps.audit.services.audit_service import AuditService
from apps.users.models import UserSession
from common.auth.jwt import create_access_token, create_refresh_token, decode_token


class AuthService:
    @staticmethod
    def login(email: str, password: str, request=None) -> dict:
        User = get_user_model()
        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if not user or not user.check_password(password):
            raise ValueError("Invalid credentials")

        refresh_expires = datetime.now(UTC) + timedelta(days=7)
        refresh_token, refresh_payload = create_refresh_token(str(user.id))
        session = UserSession.objects.create(
            user=user,
            refresh_jti=refresh_payload["jti"],
            ip_address=getattr(request, "client_ip", None),
            user_agent=getattr(request, "user_agent", ""),
            expires_at=refresh_expires,
        )
        access_token, access_payload = create_access_token(str(user.id), {"sid": str(session.session_key)})
        session.access_jti = access_payload["jti"]
        session.save(update_fields=["access_jti"])

        AuditService.record(
            action="login",
            request=request,
            user=user,
            resource_type="user_session",
            resource_id=str(session.session_key),
            metadata={"role": user.role},
        )
        return {
            "access": access_token,
            "refresh": refresh_token,
            "session_key": str(session.session_key),
            "access_expires_minutes": 30,
            "refresh_expires_days": 7,
            "user": user,
        }

    @staticmethod
    def refresh(refresh_token: str) -> dict:
        payload = decode_token(refresh_token)
        if payload.get("type") != "refresh":
            raise ValueError("Invalid token type")
        session = UserSession.objects.select_related("user").get(refresh_jti=payload["jti"], is_revoked=False)
        if session.is_expired:
            session.revoke()
            raise ValueError("Session expired")
        access_token, access_payload = create_access_token(str(session.user_id), {"sid": str(session.session_key)})
        session.access_jti = access_payload["jti"]
        session.touch()
        session.save(update_fields=["access_jti", "last_used_at"])
        return {"access": access_token, "session_key": str(session.session_key)}

    @staticmethod
    def logout(user, auth_payload: dict | None = None, request=None) -> None:
        if auth_payload and auth_payload.get("sid"):
            UserSession.objects.filter(session_key=auth_payload["sid"], user=user).update(is_revoked=True)
            AuditService.record(
                action="logout",
                request=request,
                user=user,
                resource_type="user_session",
                resource_id=auth_payload["sid"],
            )

    @staticmethod
    def build_password_reset(email: str, request=None) -> dict:
        User = get_user_model()
        user = User.objects.filter(email=email, is_active=True).first()
        if not user:
            return {"sent": False}
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        reset_url = f"{settings.FRONTEND_URL}/reset-password?uid={uid}&token={token}"
        send_mail(
            subject="AML Check password reset",
            message=f"Use this secure link to reset your password: {reset_url}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=True,
        )
        AuditService.record(
            action="password_reset_requested",
            request=request,
            user=user,
            resource_type="user",
            resource_id=str(user.pk),
        )
        return {"sent": True}

    @staticmethod
    def reset_password(uid: str, token: str, new_password: str) -> None:
        User = get_user_model()
        user_id = force_str(urlsafe_base64_decode(uid))
        user = User.objects.get(pk=user_id)
        if not default_token_generator.check_token(user, token):
            raise ValueError("Invalid reset token")
        user.set_password(new_password)
        user.last_password_change = datetime.now(UTC)
        user.save(update_fields=["password", "last_password_change"])
        UserSession.objects.filter(user=user, is_revoked=False).update(is_revoked=True)
        AuditService.record(
            action="password_reset_completed",
            user=user,
            resource_type="user",
            resource_id=str(user.pk),
        )
