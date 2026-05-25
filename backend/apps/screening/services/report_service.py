from io import BytesIO

from django.core.files.base import ContentFile
from reportlab.graphics import renderPDF
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from apps.audit.services.audit_service import AuditService
from apps.screening.models import PDFReport
from common.utils.i18n import translate


def _request_user(request):
    candidate = getattr(request, "user", None) if request else None
    return candidate if getattr(candidate, "is_authenticated", False) else None


class ReportService:
    @staticmethod
    def build_pdf(screening, language: str = "pt", request=None):
        user = _request_user(request)
        buffer = BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        metadata = screening.metadata or {}

        labels = {
            "pt": {
                "search_summary": "Resumo da pesquisa",
                "search_type": "Tipo de pesquisa",
                "query_term": "Termo pesquisado",
                "person": "Pessoa - nome completo",
                "country": "Pais",
                "company": "Empresa",
                "status": "Estado",
                "matches": "Matches encontrados",
                "client": "Cliente",
                "company_name": "Empresa",
                "country_name": "Pais",
                "nationality": "Nacionalidade",
                "passport": "Passaporte",
                "national_id": "BI / ID",
                "notes": "Observacoes",
                "no_matches": "Nenhum match foi encontrado para o termo pesquisado.",
                "match_table": "Detalhe completo dos resultados",
                "matched_name": "Nome encontrado",
                "remarks": "Observacoes da fonte",
                "page": "Pagina",
            },
            "en": {
                "search_summary": "Search summary",
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
                "page": "Page",
            },
        }.get(language, {})

        def label(key: str) -> str:
            return labels.get(key, key)

        def clean(value) -> str:
            return str(value or "-")

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

        def header(page_number: int = 1):
            pdf.setFillColor(colors.HexColor("#0B1F33"))
            pdf.rect(0, height - 92, width, 92, stroke=0, fill=1)
            pdf.setFillColor(colors.white)
            pdf.setFont("Helvetica-Bold", 20)
            pdf.drawString(40, height - 54, translate("report_title", language))
            pdf.setFont("Helvetica", 10)
            pdf.drawString(40, height - 72, f"{translate('generated_at', language)}: {screening.created_at:%Y-%m-%d %H:%M}")
            pdf.drawRightString(width - 40, height - 72, f"{label('page')} {page_number}")

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
        y = section_title(label("search_summary"), y)
        y = row(label("search_type"), label(search_type), y)
        y = row(label("query_term"), query_term, y)
        y = row(translate("risk_level", language), screening.risk_level, y)
        y = row(label("status"), screening.status, y)
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
        matches = list(screening.matches.all())
        if not matches:
            y = row(translate("results", language), label("no_matches"), y)
        for index, match in enumerate(matches, start=1):
            if y < 140:
                y = new_page()
                y = section_title(label("match_table"), y)
            pdf.setFillColor(colors.HexColor("#0F766E"))
            pdf.setFont("Helvetica-Bold", 11)
            pdf.drawString(40, y, f"#{index} {match.source_code} - {match.risk_level} - {match.score}%")
            y -= 16
            y = row(label("matched_name"), match.matched_name, y)
            y = row(label("nationality"), match.nationality, y)
            y = row(label("remarks"), match.remarks, y)
            y -= 6

        if y < 155:
            y = new_page()
        y = section_title(translate("recommendation", language), y)
        y = row(translate("recommendation", language), screening.recommendation, y)
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
