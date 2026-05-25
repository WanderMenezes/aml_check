import csv
import re
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.http import FileResponse, HttpRequest, HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_protect

from apps.audit.models import AuditEvent
from apps.audit.services.audit_service import AuditService
from apps.intelligence.models import CountryRiskEntry, RiskRule, SanctionsSource, SyncJobLog
from apps.screening.models import Alert, Client, PDFReport, ScreeningRequest
from apps.screening.services.report_service import ReportService
from apps.screening.services.screening_service import ScreeningService
from apps.users.models import UserRole, UserSession
from common.utils.countries import canonical_country


SUPPORTED_LOCALES = {"pt", "en"}


def _normalize_locale(value: str | None) -> str | None:
    if not value:
        return None
    locale = value.lower().split(",", 1)[0].split("-", 1)[0].strip()
    return locale if locale in SUPPORTED_LOCALES else None


def _resolve_locale(request: HttpRequest) -> str:
    return (
        _normalize_locale(request.GET.get("lang"))
        or _normalize_locale(request.COOKIES.get("aml_portal_locale"))
        or _normalize_locale(request.headers.get("Accept-Language"))
        or "pt"
    )


def _demo_user():
    User = get_user_model()
    return User.objects.filter(is_superuser=True).first() or User.objects.order_by("id").first()


def _is_portal_admin(request: HttpRequest) -> bool:
    user = getattr(request, "user", None)
    return bool(
        getattr(user, "is_authenticated", False)
        and (
            getattr(user, "is_superuser", False)
            or getattr(user, "is_staff", False)
            or getattr(user, "role", "") == UserRole.ADMIN
        )
    )


def _portal_redirect(request: HttpRequest, anchor: str = "") -> HttpResponse:
    locale = _normalize_locale(request.POST.get("locale")) or _resolve_locale(request)
    target = f"/?{urlencode({'lang': locale})}"
    if anchor:
        target = f"{target}#{anchor}"
    return redirect(target)


def _unique_source_code(name: str, requested_code: str = "") -> str:
    raw_code = requested_code or name
    base = re.sub(r"[^A-Z0-9]", "", raw_code.upper())[:16] or "LINK"
    candidate = base[:20]
    suffix = 2
    while SanctionsSource.objects.filter(code=candidate).exists():
        suffix_text = str(suffix)
        candidate = f"{base[:20 - len(suffix_text)]}{suffix_text}"
        suffix += 1
    return candidate


def portal_home(request: HttpRequest) -> HttpResponse:
    User = get_user_model()
    locale = _resolve_locale(request)
    selected_screening = None
    screening_id = request.GET.get("screening")
    if screening_id:
        selected_screening = ScreeningRequest.objects.select_related("client").prefetch_related("matches").filter(pk=screening_id).first()

    screenings = ScreeningRequest.objects.select_related("client").prefetch_related("matches").all()[:8]
    is_portal_admin = _is_portal_admin(request)
    recent_users = User.objects.all().order_by("-date_joined")[:6] if is_portal_admin else []
    research_links = SanctionsSource.objects.exclude(landing_url="").order_by("code")[:10] if is_portal_admin else []
    context = {
        "locale": locale,
        "portal_admin": is_portal_admin,
        "user_roles": UserRole.choices,
        "source_types": SanctionsSource.SourceType.choices,
        "source_formats": SanctionsSource.SourceFormat.choices,
        "totals": {
            "screenings": ScreeningRequest.objects.count(),
            "critical": ScreeningRequest.objects.filter(risk_level="CRITICAL").count(),
            "pending": ScreeningRequest.objects.filter(status="PENDING").count(),
            "review": ScreeningRequest.objects.filter(status="REVIEW").count(),
            "countries": CountryRiskEntry.objects.filter(is_active=True).count(),
            "reports": ScreeningRequest.objects.filter(report__isnull=False).count(),
        },
        "screenings": screenings,
        "alerts": Alert.objects.all()[:6],
        "sources": SanctionsSource.objects.all()[:6],
        "sync_logs": SyncJobLog.objects.select_related("source").all()[:6],
        "audit_events": AuditEvent.objects.select_related("user").all()[:6],
        "rules": RiskRule.objects.filter(enabled=True)[:6],
        "reports": PDFReport.objects.select_related("screening", "screening__client").all()[:6],
        "demo_user": _demo_user(),
        "selected_screening": selected_screening,
        "recent_users": recent_users,
        "research_links": research_links,
        "user_totals": {
            "total": User.objects.count(),
            "sessions": UserSession.objects.filter(is_revoked=False).count(),
        },
        "source_totals": {
            "total": SanctionsSource.objects.count(),
            "enabled": SanctionsSource.objects.filter(enabled=True).count(),
        },
    }
    response = render(request, "portal/dashboard.html", context)
    response.set_cookie("aml_portal_locale", locale, max_age=60 * 60 * 24 * 365, samesite="Lax")
    return response


@csrf_protect
def portal_admin_login(request: HttpRequest) -> HttpResponse:
    if request.method != "POST":
        return redirect("/?lang=pt#admin-access")

    email = request.POST.get("email", "").strip().lower()
    password = request.POST.get("password", "")
    user = authenticate(request, username=email, password=password)
    if not user or not (
        getattr(user, "is_superuser", False)
        or getattr(user, "is_staff", False)
        or getattr(user, "role", "") == UserRole.ADMIN
    ):
        messages.error(request, "Acesso administrativo inválido.")
        return _portal_redirect(request, "admin-access")

    login(request, user)
    messages.success(request, "Sessão administrativa iniciada.")
    return _portal_redirect(request, "admin-tools")


@csrf_protect
def portal_admin_logout(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        logout(request)
        messages.success(request, "Sessão administrativa terminada.")
    return _portal_redirect(request, "admin-access")


@csrf_protect
def portal_create_user(request: HttpRequest) -> HttpResponse:
    if request.method != "POST":
        return redirect("portal-home")
    if not _is_portal_admin(request):
        return HttpResponseForbidden("Administrative access required.")

    User = get_user_model()
    email = request.POST.get("email", "").strip().lower()
    password = request.POST.get("password", "")
    role = request.POST.get("role", UserRole.ANALYST)
    first_name = request.POST.get("first_name", "").strip()
    last_name = request.POST.get("last_name", "").strip()
    phone = request.POST.get("phone", "").strip()
    preferred_language = _normalize_locale(request.POST.get("preferred_language")) or "pt"

    if role not in UserRole.values:
        role = UserRole.ANALYST
    if not email or "@" not in email:
        messages.error(request, "Informe um e-mail válido para criar o utilizador.")
        return _portal_redirect(request, "admin-tools")
    if User.objects.filter(email__iexact=email).exists():
        messages.error(request, "Já existe um utilizador com esse e-mail.")
        return _portal_redirect(request, "admin-tools")
    if len(password) < 8:
        messages.error(request, "A senha do novo utilizador deve ter pelo menos 8 caracteres.")
        return _portal_redirect(request, "admin-tools")

    user = User.objects.create_user(
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
        role=role,
        phone=phone,
        preferred_language=preferred_language,
        is_staff=role == UserRole.ADMIN,
    )
    AuditService.record(
        action="portal_user_created",
        request=request,
        user=request.user,
        resource_type="user",
        resource_id=str(user.pk),
        metadata={"email": user.email, "role": user.role},
    )
    messages.success(request, "Utilizador criado com sucesso.")
    return _portal_redirect(request, "admin-tools")


@csrf_protect
def portal_create_search_link(request: HttpRequest) -> HttpResponse:
    if request.method != "POST":
        return redirect("portal-home")
    if not _is_portal_admin(request):
        return HttpResponseForbidden("Administrative access required.")

    name = request.POST.get("name", "").strip()
    landing_url = request.POST.get("landing_url", "").strip()
    endpoint = request.POST.get("endpoint", "").strip() or landing_url
    source_type = request.POST.get("source_type") or SanctionsSource.SourceType.SANCTIONS
    source_format = request.POST.get("source_format") or SanctionsSource.SourceFormat.HTML
    requested_code = request.POST.get("code", "").strip()
    notes = request.POST.get("notes", "").strip()

    if source_type not in SanctionsSource.SourceType.values:
        source_type = SanctionsSource.SourceType.SANCTIONS
    if source_format not in SanctionsSource.SourceFormat.values:
        source_format = SanctionsSource.SourceFormat.HTML
    if not name:
        messages.error(request, "Informe o nome do link de pesquisa.")
        return _portal_redirect(request, "admin-tools")

    validate_url = URLValidator()
    try:
        validate_url(landing_url)
        if endpoint:
            validate_url(endpoint)
    except ValidationError:
        messages.error(request, "Informe um URL válido para o link de pesquisa.")
        return _portal_redirect(request, "admin-tools")

    source = SanctionsSource.objects.create(
        code=_unique_source_code(name, requested_code),
        name=name,
        source_type=source_type,
        source_format=source_format,
        endpoint=endpoint,
        landing_url=landing_url,
        enabled=False,
        sync_frequency="manual",
        notes=notes or "Link de pesquisa cadastrado pelo portal principal.",
    )
    AuditService.record(
        action="portal_search_link_created",
        request=request,
        user=request.user,
        resource_type="sanctions_source",
        resource_id=source.code,
        metadata={"name": source.name, "landing_url": source.landing_url},
    )
    messages.success(request, "Link de pesquisa adicionado com sucesso.")
    return _portal_redirect(request, "admin-tools")


def _portal_screening_payload(request: HttpRequest) -> dict:
    search_type = (request.POST.get("search_type") or "person").lower()
    if search_type not in {"person", "country", "company"}:
        search_type = "person"

    full_name = request.POST.get("full_name", "").strip()
    company_name = request.POST.get("company_name", "").strip()
    country = request.POST.get("country", "").strip()
    resolved_country = canonical_country(country) if country else ""
    if search_type == "country" and resolved_country:
        country = resolved_country

    client = {
        "subject_type": Client.SubjectType.COMPANY if search_type == "company" else Client.SubjectType.INDIVIDUAL,
        "full_name": full_name if search_type == "person" else "",
        "company_name": company_name if search_type == "company" else "",
        "country": country if search_type == "country" else "",
        "nationality": request.POST.get("nationality", "").strip() if search_type == "person" else "",
        "passport_number": request.POST.get("passport_number", "").strip() if search_type == "person" else "",
        "national_id": request.POST.get("national_id", "").strip() if search_type == "person" else "",
        "notes": request.POST.get("notes", "").strip(),
    }
    return {"client": client, "search_type": search_type, "comments": client["notes"]}


@csrf_protect
def portal_screening(request: HttpRequest) -> HttpResponse:
    if request.method != "POST":
        return redirect("portal-home")

    actor = _demo_user()
    if actor is None:
        return redirect("portal-home")

    payload = _portal_screening_payload(request)
    screening = ScreeningService.run_screening(payload, user=actor, request=request)
    locale = _normalize_locale(request.POST.get("locale")) or _resolve_locale(request)
    return redirect(f"/?{urlencode({'screening': screening.pk, 'lang': locale})}")


@csrf_protect
def portal_report_pdf(request: HttpRequest, screening_id: int) -> HttpResponse:
    if request.method != "POST":
        return redirect(f"/?{urlencode({'screening': screening_id, 'lang': _resolve_locale(request)})}")

    screening = get_object_or_404(ScreeningRequest.objects.select_related("client"), pk=screening_id)
    language = _normalize_locale(request.POST.get("locale")) or _resolve_locale(request)
    report = ReportService.build_pdf(screening, language=language, request=request)
    report.file.open("rb")
    return FileResponse(
        report.file,
        content_type="application/pdf",
        as_attachment=False,
        filename=f"screening-{screening.pk}.pdf",
    )


@csrf_protect
def portal_report_csv(request: HttpRequest, screening_id: int) -> HttpResponse:
    if request.method != "POST":
        return redirect(f"/?{urlencode({'screening': screening_id, 'lang': _resolve_locale(request)})}")

    screening = get_object_or_404(
        ScreeningRequest.objects.select_related("client").prefetch_related("matches"),
        pk=screening_id,
    )
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="screening-{screening.pk}.csv"'
    writer = csv.writer(response)
    metadata = screening.metadata or {}
    writer.writerow(["Screening ID", screening.pk])
    writer.writerow(["Search Type", metadata.get("search_type", "")])
    writer.writerow(["Searched Term", metadata.get("query_term", "")])
    writer.writerow(["Client", screening.client.full_name])
    writer.writerow(["Company", screening.client.company_name or "-"])
    writer.writerow(["Country", screening.client.country or "-"])
    writer.writerow(["Risk Level", screening.risk_level])
    writer.writerow(["Status", screening.status])
    writer.writerow(["Recommendation", screening.recommendation])
    writer.writerow([])
    writer.writerow(["Source", "Matched Name", "Score", "Risk Level", "Nationality", "Remarks"])
    for match in screening.matches.all():
        writer.writerow(
            [
                match.source_code,
                match.matched_name,
                match.score,
                match.risk_level,
                match.nationality or "-",
                match.remarks,
            ]
        )
    return response
