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
from apps.users.models import CompanyProfile, UserRole, UserSession
from common.utils.countries import canonical_country
from common.utils.i18n import translate


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


def _portal_message(request: HttpRequest, key: str) -> str:
    locale = _normalize_locale(request.POST.get("locale")) or _resolve_locale(request)
    return translate(key, locale)


def _portal_login_url(request: HttpRequest, next_url: str | None = None) -> str:
    locale = _normalize_locale(request.POST.get("locale")) or _resolve_locale(request)
    if next_url is None:
        next_url = request.get_full_path()
    if not next_url or next_url.startswith("/portal-admin/logout"):
        next_url = f"/?{urlencode({'lang': locale})}"
    return f"/admin/login/?{urlencode({'next': next_url})}"


def _portal_user(request: HttpRequest):
    user = getattr(request, "user", None)
    if getattr(user, "is_authenticated", False) and getattr(user, "is_active", False):
        return user
    return None


def _no_store(response: HttpResponse) -> HttpResponse:
    response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response["Pragma"] = "no-cache"
    response["Expires"] = "0"
    return response


def _company_profile() -> CompanyProfile:
    return CompanyProfile.current()


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


def _screening_site_findings(screening: ScreeningRequest | None) -> list[dict]:
    if screening is None:
        return []

    findings: dict[str, dict] = {}
    metadata_checks = (screening.metadata or {}).get("external_site_checks") or []
    for check in metadata_checks:
        key = check.get("url") or check.get("source_code") or check.get("source_name")
        if not key:
            continue
        findings[key] = {
            "source_name": check.get("source_name") or check.get("source_code") or "External source",
            "source_code": check.get("source_code") or "EXTERNAL",
            "url": check.get("url") or "",
            "title": check.get("title") or "",
            "snippet": check.get("snippet") or "",
            "count": 0,
            "max_score": int(check.get("score") or 0),
            "status": check.get("status") or ("FOUND" if check.get("matched") else "NO_MATCH"),
            "matched": bool(check.get("matched")),
        }

    for match in screening.matches.all():
        details = match.details or {}
        entry = getattr(match, "watchlist_entry", None)
        source = getattr(entry, "source", None) if entry else None
        source_name = getattr(source, "name", "") or match.source_code or "EXTERNAL"
        source_code = getattr(source, "code", "") or match.source_code or "EXTERNAL"
        url = details.get("url") or getattr(entry, "source_url", "") or getattr(source, "landing_url", "")
        title = details.get("title") or match.matched_name or source_name
        snippet = details.get("snippet") or match.remarks or getattr(entry, "remarks", "")
        key = url or source_code or title
        if key not in findings:
            findings[key] = {
                "source_name": source_name,
                "source_code": source_code,
                "url": url,
                "title": title,
                "snippet": snippet,
                "count": 0,
                "max_score": 0,
                "status": "FOUND",
                "matched": True,
            }
        findings[key]["count"] += 1
        findings[key]["max_score"] = max(findings[key]["max_score"], match.score or 0)
        findings[key]["matched"] = True
        findings[key]["status"] = "FOUND"
        if not findings[key]["snippet"] and snippet:
            findings[key]["snippet"] = snippet

    return sorted(findings.values(), key=lambda item: (item["matched"], item["max_score"], item["count"], item["source_name"]), reverse=True)


def portal_home(request: HttpRequest) -> HttpResponse:
    User = get_user_model()
    locale = _resolve_locale(request)
    user = _portal_user(request)
    if user is None:
        return redirect(_portal_login_url(request, f"/?{urlencode({'lang': locale})}"))

    selected_screening = None
    screening_id = request.GET.get("screening") or request.session.get("portal_selected_screening_id")
    if screening_id:
        selected_screening = (
            ScreeningRequest.objects.select_related("client")
            .prefetch_related("matches__watchlist_entry__source")
            .filter(pk=screening_id)
            .first()
        )

    screenings = ScreeningRequest.objects.select_related("client").prefetch_related("matches").all()[:60]
    is_portal_admin = _is_portal_admin(request)
    recent_users = User.objects.all().order_by("-date_joined")[:40] if is_portal_admin else []
    research_links = SanctionsSource.objects.exclude(landing_url="").order_by("code")[:40] if is_portal_admin else []
    selected_sites = _screening_site_findings(selected_screening)
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
        "alerts": Alert.objects.filter(user=user)[:20],
        "sources": SanctionsSource.objects.all()[:40],
        "sync_logs": SyncJobLog.objects.select_related("source").all()[:40],
        "audit_events": AuditEvent.objects.select_related("user").all()[:40],
        "rules": RiskRule.objects.filter(enabled=True)[:40],
        "reports": PDFReport.objects.select_related("screening", "screening__client").all()[:40],
        "demo_user": user,
        "portal_user": user,
        "company_profile": _company_profile(),
        "selected_screening": selected_screening,
        "selected_sites": selected_sites,
        "selected_sites_found": sum(1 for site in selected_sites if site["matched"]),
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
    return _no_store(response)


@csrf_protect
def portal_admin_login(request: HttpRequest) -> HttpResponse:
    if request.method != "POST":
        return redirect(_portal_login_url(request))

    email = request.POST.get("email", "").strip().lower()
    password = request.POST.get("password", "")
    user = authenticate(request, username=email, password=password)
    if not user or not (
        getattr(user, "is_superuser", False)
        or getattr(user, "is_staff", False)
        or getattr(user, "role", "") == UserRole.ADMIN
    ):
        messages.error(request, _portal_message(request, "admin_invalid"))
        return _portal_redirect(request, "admin-access")

    login(request, user)
    messages.success(request, _portal_message(request, "admin_login_success"))
    return _portal_redirect(request, "admin-tools")


@csrf_protect
def portal_admin_logout(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        logout(request)
        messages.success(request, _portal_message(request, "admin_logout_success"))
    return redirect(_portal_login_url(request))


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
        messages.error(request, _portal_message(request, "user_email_required"))
        return _portal_redirect(request, "admin-tools")
    if User.objects.filter(email__iexact=email).exists():
        messages.error(request, _portal_message(request, "user_email_exists"))
        return _portal_redirect(request, "admin-tools")
    if len(password) < 8:
        messages.error(request, _portal_message(request, "user_password_short"))
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
    messages.success(request, _portal_message(request, "user_created"))
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
        messages.error(request, _portal_message(request, "search_link_name_required"))
        return _portal_redirect(request, "admin-tools")

    validate_url = URLValidator()
    try:
        validate_url(landing_url)
        if endpoint:
            validate_url(endpoint)
    except ValidationError:
        messages.error(request, _portal_message(request, "search_link_url_invalid"))
        return _portal_redirect(request, "admin-tools")

    source = SanctionsSource.objects.create(
        code=_unique_source_code(name, requested_code),
        name=name,
        source_type=source_type,
        source_format=source_format,
        endpoint=endpoint,
        landing_url=landing_url,
        enabled=True,
        health_status=SanctionsSource.HealthStatus.OK,
        sync_frequency="manual",
        notes=notes or "Link de pesquisa cadastrado pelo portal principal.",
    )
    if not source.enabled:
        source.enabled = True
        source.save(update_fields=["enabled", "updated_at"])
    AuditService.record(
        action="portal_search_link_created",
        request=request,
        user=request.user,
        resource_type="sanctions_source",
        resource_id=source.code,
        metadata={"name": source.name, "landing_url": source.landing_url},
    )
    messages.success(request, _portal_message(request, "search_link_created"))
    return _portal_redirect(request, "admin-tools")


@csrf_protect
def portal_update_search_link(request: HttpRequest, source_id: int) -> HttpResponse:
    if request.method != "POST":
        return redirect("portal-home")
    if not _is_portal_admin(request):
        return HttpResponseForbidden("Administrative access required.")

    source = get_object_or_404(SanctionsSource, pk=source_id)
    name = request.POST.get("name", "").strip()
    landing_url = request.POST.get("landing_url", "").strip()
    endpoint = request.POST.get("endpoint", "").strip()
    source_type = request.POST.get("source_type") or SanctionsSource.SourceType.SANCTIONS
    source_format = request.POST.get("source_format") or SanctionsSource.SourceFormat.HTML
    enabled = request.POST.get("enabled") == "true"
    notes = request.POST.get("notes", "").strip()

    if source_type not in SanctionsSource.SourceType.values:
        source_type = SanctionsSource.SourceType.SANCTIONS
    if source_format not in SanctionsSource.SourceFormat.values:
        source_format = SanctionsSource.SourceFormat.HTML
    if not name:
        messages.error(request, _portal_message(request, "search_link_name_required"))
        return _portal_redirect(request, "admin-tools")

    validate_url = URLValidator()
    try:
        validate_url(landing_url)
        if endpoint:
            validate_url(endpoint)
    except ValidationError:
        messages.error(request, _portal_message(request, "search_link_url_invalid"))
        return _portal_redirect(request, "admin-tools")

    source.name = name
    source.landing_url = landing_url
    source.endpoint = endpoint or landing_url
    source.source_type = source_type
    source.source_format = source_format
    source.enabled = enabled
    source.notes = notes
    source.save(update_fields=["name", "landing_url", "endpoint", "source_type", "source_format", "enabled", "notes", "updated_at"])

    AuditService.record(
        action="portal_search_link_updated",
        request=request,
        user=request.user,
        resource_type="sanctions_source",
        resource_id=source.code,
        metadata={"name": source.name, "landing_url": source.landing_url, "enabled": source.enabled},
    )
    messages.success(request, _portal_message(request, "search_link_updated"))
    return _portal_redirect(request, "admin-tools")


@csrf_protect
def portal_delete_search_link(request: HttpRequest, source_id: int) -> HttpResponse:
    if request.method != "POST":
        return redirect("portal-home")
    if not _is_portal_admin(request):
        return HttpResponseForbidden("Administrative access required.")

    source = get_object_or_404(SanctionsSource, pk=source_id)
    metadata = {"name": source.name, "code": source.code, "landing_url": source.landing_url}
    resource_id = source.code
    source.delete()
    AuditService.record(
        action="portal_search_link_deleted",
        request=request,
        user=request.user,
        resource_type="sanctions_source",
        resource_id=resource_id,
        metadata=metadata,
    )
    messages.success(request, _portal_message(request, "search_link_deleted"))
    return _portal_redirect(request, "admin-tools")


@csrf_protect
def portal_update_company_profile(request: HttpRequest) -> HttpResponse:
    if request.method != "POST":
        return redirect("portal-home")
    if not _is_portal_admin(request):
        return HttpResponseForbidden("Administrative access required.")

    profile = _company_profile()
    for field in (
        "legal_name",
        "trading_name",
        "tax_id",
        "registration_number",
        "address",
        "city",
        "country",
        "phone",
        "email",
        "website",
        "compliance_officer",
        "report_footer",
    ):
        setattr(profile, field, request.POST.get(field, "").strip())
    if not profile.legal_name:
        messages.error(request, _portal_message(request, "company_name_required"))
        return _portal_redirect(request, "company-profile")
    profile.save()
    AuditService.record(
        action="company_profile_updated",
        request=request,
        user=request.user,
        resource_type="company_profile",
        resource_id=str(profile.pk),
        metadata={"legal_name": profile.legal_name, "tax_id": profile.tax_id},
    )
    messages.success(request, _portal_message(request, "company_profile_saved"))
    return _portal_redirect(request, "company-profile")


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

    actor = _portal_user(request)
    if actor is None:
        return redirect(_portal_login_url(request, f"/?{urlencode({'lang': _resolve_locale(request)})}#new-screening"))

    payload = _portal_screening_payload(request)
    screening = ScreeningService.run_screening(payload, user=actor, request=request)
    request.session["portal_selected_screening_id"] = screening.pk
    locale = _normalize_locale(request.POST.get("locale")) or _resolve_locale(request)
    return redirect(f"/?{urlencode({'lang': locale})}#new-screening")


@csrf_protect
def portal_report_pdf(request: HttpRequest, screening_id: int) -> HttpResponse:
    if _portal_user(request) is None:
        return redirect(_portal_login_url(request, f"/?{urlencode({'screening': screening_id, 'lang': _resolve_locale(request)})}"))

    if request.method not in {"GET", "POST"}:
        return redirect(f"/?{urlencode({'screening': screening_id, 'lang': _resolve_locale(request)})}")

    screening = get_object_or_404(
        ScreeningRequest.objects.select_related("client").prefetch_related("matches__watchlist_entry__source"),
        pk=screening_id,
    )
    language = _normalize_locale(
        request.POST.get("locale")
        or request.POST.get("language")
        or request.GET.get("lang")
        or request.GET.get("locale")
        or request.GET.get("language")
    ) or _resolve_locale(request)
    report = ReportService.build_pdf(screening, language=language, request=request)
    report.file.open("rb")
    download = (request.POST.get("download") or request.GET.get("download")) == "1"
    return FileResponse(
        report.file,
        content_type="application/pdf",
        as_attachment=download,
        filename=f"screening-{screening.pk}-{language}.pdf",
    )


@csrf_protect
def portal_report_csv(request: HttpRequest, screening_id: int) -> HttpResponse:
    if _portal_user(request) is None:
        return redirect(_portal_login_url(request, f"/?{urlencode({'screening': screening_id, 'lang': _resolve_locale(request)})}"))

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
