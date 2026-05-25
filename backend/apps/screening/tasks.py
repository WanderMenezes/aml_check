try:
    from config.celery import app as celery_app
except Exception:
    celery_app = None

from typing import List

from apps.screening.repositories.watchlist_repository import WatchlistRepository
from apps.screening.models import ScreeningRequest, ScreeningMatch, Alert
from apps.intelligence.models import RiskLevel
from apps.audit.services.audit_service import AuditService
from apps.screening.services.screening_service import ScreeningService


def _process_external_matches(screening_id: int, query_term: str, search_type: str):
    screening = ScreeningRequest.objects.filter(pk=screening_id).first()
    if not screening:
        return
    external_matches = WatchlistRepository.external_site_matches(query_term)
    match_sources: List[str] = []
    match_scores: List[int] = []
    match_risk_levels: List[str] = []
    country_list_names: List[str] = []

    for ext in external_matches:
        src = ext.get("source")
        url = ext.get("url")
        title = ext.get("title") or ""
        snippet = ext.get("snippet") or ""
        score = int(ext.get("score") or 0)
        match_sources.append(src.code if src else (url or "EXTERNAL"))
        match_scores.append(score)
        match_risk_levels.append(RiskLevel.LOW)
        ScreeningMatch.objects.create(
            screening=screening,
            watchlist_entry=None,
            source_code=src.code if src else (url or "EXTERNAL"),
            matched_name=(title or snippet)[:255],
            score=score,
            risk_level=RiskLevel.LOW,
            nationality="",
            aliases=[],
            details={"search_type": search_type, "query_term": query_term, "url": url, "snippet": snippet},
            remarks=f"Found on {url}",
        )

    # recompute risk with the new external matches included
    # collect existing matches' sources/scores/risk levels
    for m in screening.matches.all():
        match_sources.append(m.source_code)
        match_scores.append(m.score or 0)
        match_risk_levels.append(m.risk_level or RiskLevel.LOW)

    final_risk = ScreeningService._evaluate_risk(match_sources, country_list_names, match_scores, match_risk_levels)
    screening.risk_level = final_risk
    screening.status = ScreeningRequest.Status.REVIEW if final_risk in {RiskLevel.HIGH, RiskLevel.CRITICAL} else ScreeningRequest.Status.COMPLETED
    screening.recommendation = ScreeningService._recommendation(final_risk)
    screening.save(update_fields=["risk_level", "status", "recommendation"])

    if screening.created_by and final_risk in {RiskLevel.HIGH, RiskLevel.CRITICAL}:
        Alert.objects.create(
            user=screening.created_by,
            screening=screening,
            alert_type=Alert.AlertType.NEW_MATCH,
            title=f"High-risk screening #{screening.pk}",
            message=f"Screening returned {screening.matches.count()} matches with risk {final_risk}.",
            metadata={"risk_level": final_risk},
        )

    AuditService.record(
        action="external_matches_processed",
        request=None,
        user=screening.created_by,
        resource_type="screening",
        resource_id=str(screening.pk),
        metadata={"matches": screening.matches.count(), "query_term": query_term},
    )


if celery_app:
    @celery_app.task(bind=True, name="screening.process_external_matches")
    def process_external_matches(self, screening_id: int, query_term: str, search_type: str):
        return _process_external_matches(screening_id, query_term, search_type)
else:
    def process_external_matches(screening_id: int, query_term: str, search_type: str):
        return _process_external_matches(screening_id, query_term, search_type)
