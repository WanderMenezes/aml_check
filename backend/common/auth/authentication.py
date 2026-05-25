from django.contrib.auth import get_user_model
from rest_framework import authentication, exceptions

from common.auth.jwt import decode_token


class JWTAuthentication(authentication.BaseAuthentication):
    keyword = "Bearer"

    def authenticate(self, request):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith(f"{self.keyword} "):
            return None
        token = auth_header.split(" ", 1)[1].strip()
        if not token:
            raise exceptions.AuthenticationFailed("Missing token.")
        try:
            payload = decode_token(token)
        except Exception as exc:  # pragma: no cover
            raise exceptions.AuthenticationFailed("Invalid token.") from exc

        if payload.get("type") != "access":
            raise exceptions.AuthenticationFailed("Invalid token type.")

        User = get_user_model()
        try:
            user = User.objects.get(id=payload["sub"], is_active=True)
        except User.DoesNotExist as exc:
            raise exceptions.AuthenticationFailed("User not found.") from exc

        session_key = payload.get("sid")
        if session_key:
            from apps.users.models import UserSession

            session = UserSession.objects.filter(session_key=session_key, is_revoked=False).first()
            if not session:
                raise exceptions.AuthenticationFailed("Session revoked.")
            session.touch()

        return user, payload
