from io import BytesIO
import html
import re

from django.core.files.base import ContentFile
from reportlab.graphics import renderPDF
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from apps.audit.services.audit_service import AuditService
from apps.screening.models import PDFReport
from apps.screening.repositories.watchlist_repository import WatchlistRepository
from apps.users.models import CompanyProfile
from common.utils.i18n import normalize_language, translate


def _request_user(request):
    candidate = getattr(request, "user", None) if request else None
    return candidate if getattr(candidate, "is_authenticated", False) else None


class ReportService:
    @staticmethod
    def build_pdf(screening, language: str = "pt", request=None):
        language = normalize_language(language)
        user = _request_user(request)
        buffer = BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=A4, pageCompression=0)
        width, height = A4
        metadata = screening.metadata or {}

        labels = {
            "pt": {
                "search_summary": "Resumo da pesquisa",
                "institutional_data": "Dados da empresa utilizadora",
                "legal_name": "RazÃ£o social",
                "trading_name": "Nome comercial",
                "tax_id": "NIF / IdentificaÃ§Ã£o fiscal",
                "registration_number": "Registo comercial",
                "address": "EndereÃ§o",
                "contact": "Contacto",
                "compliance_officer": "ResponsÃ¡vel de compliance",
                "search_type": "Tipo de pesquisa",
                "query_term": "Termo pesquisado",
                "person": "Pessoa - nome completo",
                "country": "País",
                "company": "Empresa",
                "status": "Estado",
                "matches": "Ocorrências encontradas",
                "client": "Cliente",
                "company_name": "Empresa",
                "country_name": "País",
                "nationality": "Nacionalidade",
                "passport": "Passaporte",
                "national_id": "BI / ID",
                "notes": "Observações",
                "no_matches": "Nenhuma ocorrência foi encontrada para o termo pesquisado.",
                "match_table": "Detalhe completo dos resultados",
                "matched_name": "Nome encontrado",
                "remarks": "Observações da fonte",
                "site_findings": "O que os sites pesquisados dizem",
                "site_findings_note": "Resumo automático dos resultados externos consultados para esta pesquisa.",
                "site_source": "Fonte",
                "site_title": "Título / resultado",
                "site_url": "Endereço",
                "site_excerpt": "Resumo encontrado",
                "no_site_findings": "Nenhum resumo externo foi encontrado para o termo pesquisado.",
                "page": "Página",
                "status_PENDING": "Pendente",
                "status_COMPLETED": "Concluído",
                "status_REVIEW": "Em revisão",
                "risk_LOW": "Baixo",
                "risk_MEDIUM": "Médio",
                "risk_HIGH": "Alto",
                "risk_CRITICAL": "Crítico",
                "recommendation_LOW": "Prosseguir com diligência padrão.",
                "recommendation_MEDIUM": "Prosseguir com diligência reforçada e revisão documental.",
                "recommendation_HIGH": "Encaminhar ao responsável de conformidade antes da integração.",
                "recommendation_CRITICAL": "Não integrar. Bloquear e investigar imediatamente.",
            },
            "en": {
                "search_summary": "Search summary",
                "institutional_data": "System owner company data",
                "legal_name": "Legal name",
                "trading_name": "Trading name",
                "tax_id": "Tax ID",
                "registration_number": "Registration number",
                "address": "Address",
                "contact": "Contact",
                "compliance_officer": "Compliance officer",
                "search_type": "Search type",
                "query_term": "Searched term",
                "person": "Person - full name",
                "country": "Country",
                "company": "Company",
                "status": "Status",
                "matches": "Matches found",
                "client": "Client",
                "company_name": "Company",
                "country_name": "Country",
                "nationality": "Nationality",
                "passport": "Passport",
                "national_id": "National ID",
                "notes": "Notes",
                "no_matches": "No matches were found for the searched term.",
                "match_table": "Complete result details",
                "matched_name": "Matched name",
                "remarks": "Source remarks",
                "site_findings": "What searched sites say",
                "site_findings_note": "Automatic summary of external results checked for this search.",
                "site_source": "Source",
                "site_title": "Title / result",
                "site_url": "Address",
                "site_excerpt": "Found summary",
                "no_site_findings": "No external summary was found for the searched term.",
                "page": "Page",
                "status_PENDING": "Pending",
                "status_COMPLETED": "Completed",
                "status_REVIEW": "In review",
                "risk_LOW": "Low",
                "risk_MEDIUM": "Medium",
                "risk_HIGH": "High",
                "risk_CRITICAL": "Critical",
                "recommendation_LOW": "Proceed with standard due diligence.",
                "recommendation_MEDIUM": "Proceed with enhanced due diligence and documentary review.",
                "recommendation_HIGH": "Escalate to compliance officer before onboarding.",
                "recommendation_CRITICAL": "Do not onboard. Block and investigate immediately.",
            },
        }[language]

        labels.update(
            {
                "legal_name": "Raz\u00e3o social" if language == "pt" else "Legal name",
                "tax_id": "NIF / Identifica\u00e7\u00e3o fiscal" if language == "pt" else "Tax ID",
                "address": "Endere\u00e7o" if language == "pt" else "Address",
                "compliance_officer": "Respons\u00e1vel de compliance" if language == "pt" else "Compliance officer",
                "country": "Pa\u00eds" if language == "pt" else "Country",
                "country_name": "Pa\u00eds" if language == "pt" else "Country",
                "matches": "Ocorr\u00eancias encontradas" if language == "pt" else "Matches found",
                "notes": "Observa\u00e7\u00f5es" if language == "pt" else "Notes",
                "no_matches": "Nenhuma ocorr\u00eancia foi encontrada para o termo pesquisado." if language == "pt" else "No matches were found for the searched term.",
                "remarks": "Observa\u00e7\u00f5es da fonte" if language == "pt" else "Source remarks",
                "site_findings_note": "Resumo autom\u00e1tico dos resultados externos consultados para esta pesquisa." if language == "pt" else "Automatic summary of external results checked for this search.",
                "site_title": "T\u00edtulo / resultado" if language == "pt" else "Title / result",
                "site_url": "Endere\u00e7o" if language == "pt" else "Address",
                "external_status": "Estado externo" if language == "pt" else "External status",
                "external_evidence": "Evid\u00eancia" if language == "pt" else "Evidence",
                "external_reason": "Raz\u00e3o de decis\u00e3o" if language == "pt" else "Decision reason",
                "page": "P\u00e1gina" if language == "pt" else "Page",
                "status_COMPLETED": "Conclu\u00eddo" if language == "pt" else "Completed",
                "status_REVIEW": "Em revis\u00e3o" if language == "pt" else "In review",
                "risk_MEDIUM": "M\u00e9dio" if language == "pt" else "Medium",
                "risk_CRITICAL": "Cr\u00edtico" if language == "pt" else "Critical",
                "recommendation_LOW": "Prosseguir com dilig\u00eancia padr\u00e3o." if language == "pt" else "Proceed with standard due diligence.",
                "recommendation_MEDIUM": "Prosseguir com dilig\u00eancia refor\u00e7ada e revis\u00e3o documental." if language == "pt" else "Proceed with enhanced due diligence and documentary review.",
                "recommendation_HIGH": "Encaminhar ao respons\u00e1vel de conformidade antes da integra\u00e7\u00e3o." if language == "pt" else "Escalate to compliance officer before onboarding.",
                "recommendation_CRITICAL": "N\u00e3o integrar. Bloquear e investigar imediatamente." if language == "pt" else "Do not onboard. Block and investigate immediately.",
            }
        )

        def label(key: str) -> str:
            return labels.get(key, key)

        def option_label(prefix: str, value: str) -> str:
            value = clean(value)
            key = f"{prefix}_{value}"
            translated = label(key)
            return translated if translated != key else value

        def recommendation_text() -> str:
            key = f"recommendation_{clean(screening.risk_level)}"
            translated = label(key)
            return translated if translated != key else clean(screening.recommendation)

        def clean(value) -> str:
            text = html.unescape(str(value or "-"))
            text = re.sub(r"<[^>]+>", " ", text)
            return re.sub(r"\s+", " ", text).strip() or "-"

        organization = CompanyProfile.current()

        def wrapped_lines(value: str, max_chars: int = 92) -> list[str]:
            words = clean(value).split()
            if not words:
                return ["-"]
            lines: list[str] = []
            current = ""
            for word in words:
                candidate = f"{current} {word}".strip()
                if len(candidate) <= max_chars:
                    current = candidate
                else:
                    if current:
                        lines.append(current)
                    current = word[:max_chars]
            if current:
                lines.append(current)
            return lines

        def collect_site_findings(query_term: str, matches: list) -> list[dict]:
            findings: list[dict] = []
            seen: set[tuple[str, str, str]] = set()

            def add(source: str = "", title: str = "", url: str = "", excerpt: str = "", score=None, status: str = "", evidence: str = "", reason: str = ""):
                title = clean(title)
                url = clean(url)
                excerpt = clean(excerpt)
                if title == "-" and url == "-" and excerpt == "-":
                    return
                key = (source or "-", title[:120], url)
                if key in seen:
                    return
                seen.add(key)
                findings.append(
                    {
                        "source": source or "-",
                        "title": title,
                        "url": url,
                        "excerpt": excerpt,
                        "score": score,
                        "status": clean(status),
                        "evidence": clean(evidence),
                        "reason": clean(reason),
                    }
                )

            metadata_checks = metadata.get("external_site_checks") or []
            ordered_checks = sorted(metadata_checks, key=lambda item: (bool(item.get("matched")), int(item.get("score") or 0)), reverse=True)
            for check in ordered_checks:
                if len(findings) >= 10:
                    break
                add(
                    check.get("source_name") or check.get("source_code") or "EXTERNAL",
                    check.get("title") or check.get("url") or "",
                    check.get("url") or "",
                    check.get("snippet") or check.get("decision_reason") or "",
                    check.get("score"),
                    check.get("status") or "",
                    check.get("evidence_level") or "",
                    check.get("decision_reason") or ", ".join(check.get("important_terms") or []),
                )

            for match in matches:
                if len(findings) >= 10:
                    break
                details = match.details or {}
                entry = getattr(match, "watchlist_entry", None)
                source_obj = getattr(entry, "source", None) if entry else None
                source_name = getattr(source_obj, "name", "") or match.source_code
                url = details.get("url") or getattr(entry, "source_url", "") or getattr(source_obj, "landing_url", "")
                excerpt = details.get("snippet") or match.remarks or getattr(entry, "remarks", "")
                title = match.matched_name
                add(source_name, title, url, excerpt, match.score, details.get("status") or "", details.get("evidence_level") or "", details.get("decision_reason") or "")

            if not query_term or len(findings) >= 10:
                return findings[:10]

            try:
                external_results = WatchlistRepository.external_site_matches(query_term, timeout=3)
            except Exception:
                external_results = []

            for result in external_results:
                if len(findings) >= 10:
                    break
                source = result.get("source")
                add(
                    getattr(source, "name", "") or getattr(source, "code", "") or "EXTERNAL",
                    result.get("title") or result.get("snippet") or "",
                    result.get("url") or "",
                    result.get("snippet") or "",
                    result.get("score"),
                    result.get("status") or "",
                    result.get("evidence_level") or "",
                    result.get("decision_reason") or "",
                )
            return findings[:10]

        def footer(page_number: int = 1):
            footer_text = organization.report_footer or organization.website or organization.email or clean(organization.legal_name)
            pdf.setStrokeColor(colors.HexColor("#D8E1EB"))
            pdf.line(40, 38, width - 40, 38)
            pdf.setFillColor(colors.HexColor("#667085"))
            pdf.setFont("Helvetica", 8)
            pdf.drawString(40, 24, clean(footer_text)[:112])
            pdf.drawRightString(width - 40, 24, f"{label('page')} {page_number}")

        def header(page_number: int = 1):
            pdf.setFillColor(colors.HexColor("#0B1F33"))
            pdf.rect(0, height - 92, width, 92, stroke=0, fill=1)
            pdf.setFillColor(colors.white)
            pdf.setFont("Helvetica-Bold", 20)
            pdf.drawString(40, height - 54, translate("report_title", language))
            pdf.setFont("Helvetica", 10)
            pdf.drawString(40, height - 72, f"{translate('generated_at', language)}: {screening.created_at:%Y-%m-%d %H:%M}")
            pdf.drawRightString(width - 40, height - 54, clean(organization.trading_name or organization.legal_name)[:42])
            pdf.drawRightString(width - 40, height - 72, clean(organization.tax_id or organization.email)[:42])
            footer(page_number)

        page = 1
        header(page)

        def new_page():
            nonlocal page
            pdf.showPage()
            page += 1
            header(page)
            return height - 122

        def section_title(title: str, y: float) -> float:
            if y < 120:
                y = new_page()
            pdf.setFillColor(colors.HexColor("#102A43"))
            pdf.setFont("Helvetica-Bold", 14)
            pdf.drawString(40, y, title)
            return y - 22

        def row(title: str, value: str, y: float) -> float:
            if y < 90:
                y = new_page()
            pdf.setFillColor(colors.HexColor("#5B6B7A"))
            pdf.setFont("Helvetica-Bold", 9)
            pdf.drawString(40, y, title)
            pdf.setFillColor(colors.HexColor("#17212B"))
            pdf.setFont("Helvetica", 10)
            lines = wrapped_lines(value)
            pdf.drawString(170, y, lines[0])
            y -= 14
            for line in lines[1:]:
                if y < 90:
                    y = new_page()
                pdf.drawString(170, y, line)
                y -= 14
            return y

        search_type = metadata.get("search_type") or "person"
        query_term = metadata.get("query_term") or screening.client.full_name or screening.client.company_name or screening.client.country
        y = height - 122
        y = section_title(label("institutional_data"), y)
        y = row(label("legal_name"), organization.legal_name, y)
        y = row(label("trading_name"), organization.trading_name, y)
        y = row(label("tax_id"), organization.tax_id, y)
        y = row(label("registration_number"), organization.registration_number, y)
        y = row(label("address"), " - ".join(part for part in [organization.address, organization.city, organization.country] if part), y)
        y = row(label("contact"), " | ".join(part for part in [organization.phone, organization.email, organization.website] if part), y)
        y = row(label("compliance_officer"), organization.compliance_officer, y)

        y -= 8
        y = section_title(label("search_summary"), y)
        y = row(label("search_type"), label(search_type), y)
        y = row(label("query_term"), query_term, y)
        y = row(translate("risk_level", language), option_label("risk", screening.risk_level), y)
        y = row(label("status"), option_label("status", screening.status), y)
        y = row(label("matches"), str(screening.matches.count()), y)

        y -= 8
        y = section_title(translate("client_data", language), y)
        y = row(label("client"), screening.client.full_name, y)
        y = row(label("company_name"), screening.client.company_name, y)
        y = row(label("country_name"), screening.client.country, y)
        y = row(label("nationality"), screening.client.nationality, y)
        y = row(label("passport"), screening.client.passport_number, y)
        y = row(label("national_id"), screening.client.national_id, y)
        y = row(label("notes"), screening.client.notes, y)

        y -= 8
        y = section_title(label("match_table"), y)
        matches = list(screening.matches.select_related("watchlist_entry", "watchlist_entry__source").all())
        if not matches:
            y = row(translate("results", language), label("no_matches"), y)
        for index, match in enumerate(matches, start=1):
            if y < 140:
                y = new_page()
                y = section_title(label("match_table"), y)
            pdf.setFillColor(colors.HexColor("#0F766E"))
            pdf.setFont("Helvetica-Bold", 11)
            pdf.drawString(40, y, f"#{index} {match.source_code} - {option_label('risk', match.risk_level)} - {match.score}%")
            y -= 16
            y = row(label("matched_name"), match.matched_name, y)
            y = row(label("nationality"), match.nationality, y)
            y = row(label("remarks"), match.remarks, y)
            y -= 6

        y -= 8
        site_findings = collect_site_findings(query_term, matches)
        y = section_title(label("site_findings"), y)
        y = row(label("notes"), label("site_findings_note"), y)
        if not site_findings:
            y = row(translate("results", language), label("no_site_findings"), y)
        for index, finding in enumerate(site_findings, start=1):
            if y < 165:
                y = new_page()
                y = section_title(label("site_findings"), y)
            pdf.setFillColor(colors.HexColor("#0F766E"))
            pdf.setFont("Helvetica-Bold", 11)
            score = finding.get("score")
            score_text = f" - {score}%" if score not in (None, "", "-") else ""
            pdf.drawString(40, y, f"#{index} {clean(finding.get('source'))}{score_text}")
            y -= 16
            y = row(label("site_title"), finding.get("title"), y)
            y = row(label("site_url"), finding.get("url"), y)
            status_line = " | ".join(part for part in [clean(finding.get("status")), clean(finding.get("evidence"))] if part and part != "-")
            y = row(label("external_status"), status_line or "-", y)
            y = row(label("external_reason"), finding.get("reason"), y)
            y = row(label("site_excerpt"), finding.get("excerpt"), y)
            y -= 6

        if y < 155:
            y = new_page()
        y = section_title(translate("recommendation", language), y)
        y = row(translate("recommendation", language), recommendation_text(), y)
        y = row(translate("digital_signature", language), f"{screening.id}-{screening.risk_level}", y)

        qr = QrCodeWidget(f"screening:{screening.id}:{screening.risk_level}")
        bounds = qr.getBounds()
        size = 80
        drawing = Drawing(size, size, transform=[size / (bounds[2] - bounds[0]), 0, 0, size / (bounds[3] - bounds[1]), 0, 0])
        drawing.add(qr)
        renderPDF.draw(drawing, pdf, width - 120, 60)
        pdf.setFillColor(colors.HexColor("#17212B"))
        pdf.setFont("Helvetica", 9)
        pdf.drawString(width - 135, 48, translate("validation_qr", language))

        pdf.showPage()
        pdf.save()
        buffer.seek(0)

        report, _ = PDFReport.objects.get_or_create(screening=screening, defaults={"language": language, "created_by": user})
        report.language = language
        report.created_by = user
        report.file.save(f"screening-{screening.pk}.pdf", ContentFile(buffer.getvalue()), save=True)
        AuditService.record(
            action="report_exported",
            request=request,
            resource_type="screening_report",
            resource_id=str(report.pk),
            metadata={"screening_id": screening.pk, "language": language},
        )
        return report
