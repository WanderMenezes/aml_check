from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from django.utils import timezone


class CORSMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == "OPTIONS":
            response = JsonResponse({"detail": "ok"})
        else:
            response = self.get_response(request)
        origin = request.headers.get("Origin")
        if origin and origin in settings.CSRF_TRUSTED_ORIGINS:
            response["Access-Control-Allow-Origin"] = origin
            response["Access-Control-Allow-Credentials"] = "true"
            response["Access-Control-Allow-Headers"] = "Authorization, Content-Type, Accept-Language, X-Requested-With"
            response["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        return response


class RateLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith("/admin") or request.path.startswith("/static"):
            return self.get_response(request)
        limit = 200 if getattr(request, "user", None) and request.user.is_authenticated else 100
        bucket = timezone.now().strftime("%Y%m%d%H%M")
        ip = getattr(request, "client_ip", request.META.get("REMOTE_ADDR", "unknown"))
        key = f"rate:{bucket}:{ip}:{request.path}"
        try:
            if not cache.add(key, 1, timeout=60):
                try:
                    cache.incr(key)
                except ValueError:
                    cache.set(key, 1, timeout=60)
            current = cache.get(key, 1)
        except Exception:
            current = 1
        if current > limit:
            return JsonResponse({"detail": "Rate limit exceeded."}, status=429)
        return self.get_response(request)


class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response["X-Content-Type-Options"] = "nosniff"
        response["Referrer-Policy"] = "same-origin"
        response["X-Frame-Options"] = "DENY"
        response["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        response["Content-Security-Policy"] = "default-src 'self' 'unsafe-inline' https: data:;"
        return response
