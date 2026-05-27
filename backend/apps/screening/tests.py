import shutil
import tempfile
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.intelligence.models import RiskLevel, SanctionsSource
from apps.screening.models import Client, ScreeningRequest
from apps.screening.repositories.watchlist_repository import WatchlistRepository
from apps.screening.services.report_service import ReportService
from apps.users.models import UserRole


MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class ReportLanguageTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            email="analyst@example.com",
            password="password123",
            role=UserRole.ANALYST,
            preferred_language="pt",
        )
        self.client_record = Client.objects.create(
            full_name="Mohamed Aly",
            country="Egypt",
            created_by=self.user,
        )
        self.screening = ScreeningRequest.objects.create(
            client=self.client_record,
            created_by=self.user,
            risk_level=RiskLevel.LOW,
            status=ScreeningRequest.Status.COMPLETED,
            recommendation="Proceed with standard due diligence.",
            metadata={"search_type": "person", "query_term": "Mohamed Aly"},
        )

    def pdf_text(self, language: str) -> str:
        with patch("apps.screening.services.report_service.WatchlistRepository.external_site_matches", return_value=[]):
            report = ReportService.build_pdf(self.screening, language=language)
        report.file.open("rb")
        try:
            return report.file.read().decode("latin-1", errors="ignore")
        finally:
            report.file.close()

    def test_pdf_uses_portuguese_when_language_is_pt(self):
        text = self.pdf_text("pt")

        self.assertIn("Resumo da pesquisa", text)
        self.assertIn("Nenhum resumo externo", text)
        self.assertNotIn("Search summary", text)

    def test_pdf_uses_english_when_language_is_en_variant(self):
        text = self.pdf_text("en-US")

        self.assertIn("Search summary", text)
        self.assertIn("No external summary", text)
        self.assertNotIn("Resumo da pesquisa", text)

    def test_export_pdf_uses_accept_language_header_when_body_is_empty(self):
        api_client = APIClient()
        api_client.force_authenticate(user=self.user)

        with patch("apps.screening.services.report_service.WatchlistRepository.external_site_matches", return_value=[]):
            response = api_client.post(
                f"/api/screening/requests/{self.screening.pk}/export_pdf/",
                {},
                format="json",
                HTTP_ACCEPT_LANGUAGE="en",
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["language"], "en")


class ExternalSiteSearchTests(TestCase):
    class FakeResponse:
        status_code = 200
        reason = "OK"
        encoding = "utf-8"

        def __init__(self, text):
            self.text = text

        def iter_content(self, chunk_size=65536, decode_unicode=False):
            yield self.text if decode_unicode else self.text.encode("utf-8")

    def setUp(self):
        self.source = SanctionsSource.objects.create(
            code="CUSTOMSRC",
            name="Custom Registry",
            source_type=SanctionsSource.SourceType.SANCTIONS,
            source_format=SanctionsSource.SourceFormat.HTML,
            landing_url="https://registry.example/search",
            endpoint="https://registry.example/data.xml",
            enabled=True,
        )

    @override_settings(
        SCREENING_SETTINGS={
            "MAX_RESULTS": 20,
            "MIN_FUZZY_SCORE": 70,
            "MIN_EXTERNAL_SCORE": 85,
            "EXTERNAL_CACHE_TTL": 0,
            "EXTERNAL_CONCURRENCY": 2,
            "EXTERNAL_MAX_BYTES": 750000,
        }
    )
    @patch("requests.get")
    def test_external_search_checks_every_registered_url(self, mock_get):
        def fake_get(url, **kwargs):
            if url.endswith("data.xml"):
                return self.FakeResponse("<xml><name>Maria Silva</name><status>Listed</status></xml>")
            return self.FakeResponse("<html><title>Custom Registry</title><body>No listed person here</body></html>")

        mock_get.side_effect = fake_get

        results = WatchlistRepository.external_site_matches("Maria Silva", include_all=True)

        self.assertEqual(mock_get.call_count, 3)
        self.assertEqual(len(results), 3)
        matched = [result for result in results if result["matched"]]
        self.assertEqual(len(matched), 1)
        self.assertEqual(matched[0]["url"], "https://registry.example/data.xml")
        self.assertEqual(matched[0]["decision"], "probable_match")
        self.assertEqual(matched[0]["evidence_level"], "Alto")

    @override_settings(
        SCREENING_SETTINGS={
            "MAX_RESULTS": 20,
            "MIN_FUZZY_SCORE": 70,
            "MIN_EXTERNAL_SCORE": 85,
            "EXTERNAL_CACHE_TTL": 0,
            "EXTERNAL_CONCURRENCY": 2,
            "EXTERNAL_MAX_BYTES": 750000,
        }
    )
    @patch("requests.get")
    def test_external_search_extracts_specific_result_evidence(self, mock_get):
        html = """
        <html>
          <head><title>Resultados da pesquisa por Maria Silva</title></head>
          <body>
            <article>
              <h2><a href="/noticias/maria-silva-investigacao">Maria Silva em investigação sobre contrato público</a></h2>
              <p>O tribunal abriu um processo de investigação relacionado com fundos públicos.</p>
            </article>
          </body>
        </html>
        """
        mock_get.return_value = self.FakeResponse(html)

        results = WatchlistRepository.external_site_matches("Maria Silva", include_all=True)
        matched = [result for result in results if result["matched"]]

        self.assertTrue(matched)
        self.assertEqual(matched[0]["url"], "https://registry.example/noticias/maria-silva-investigacao")
        self.assertIn("contrato público", matched[0]["snippet"])
        self.assertIn("investigacao", matched[0]["important_terms"])
        self.assertEqual(matched[0]["evidence_level"], "Alto")
