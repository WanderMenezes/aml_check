from django.conf import settings
from django.db import transaction

from apps.audit.services.audit_service import AuditService
from apps.intelligence.models import RiskLevel, RiskRule, SourceCode
from apps.screening.models import Alert, Client, ScreeningMatch, ScreeningRequest
from apps.screening.repositories.watchlist_repository import WatchlistRepository
from common.utils.fuzzy import levenshtein_distance, similarity_score
from common.utils.strings import coalesce


RISK_ORDER = {
    RiskLevel.LOW: 1,
    RiskLevel.MEDIUM: 2,
    RiskLevel.HIGH: 3,
    RiskLevel.CRITICAL: 4,
}


class ScreeningService:
    @staticmethod
    def _resolve_search(client_obj: Client, payload: dict) -> tuple[str, str]:
        requested_type = (payload.get("search_type") or "").lower()
        if requested_type in {"person", "country", "company"}:
            search_type = requested_type
        elif client_obj.subject_type == Client.SubjectType.COMPANY or client_obj.company_name:
            search_type = "company"
        elif client_obj.country and not client_obj.full_name:
            search_type = "country"
        else:
            search_type = "person"

        query_term = {
            "person": client_obj.full_name,
            "country": client_obj.country,
            "company": client_obj.company_name,
        }.get(search_type, client_obj.full_name)
        return search_type, (query_term or "").strip()

    @staticmethod
    def _recommendation(level: str) -> str:
        return {
            RiskLevel.LOW: "Proceed with standard due diligence.",
            RiskLevel.MEDIUM: "Proceed with enhanced due diligence and documentary review.",
            RiskLevel.HIGH: "Escalate to compliance officer before onboarding.",
            RiskLevel.CRITICAL: "Do not onboard. Block and investigate immediately.",
        }[level]

    @staticmethod
    def _evaluate_risk(
        match_sources: list[str],
        country_list_names: list[str],
        match_scores: list[int],
        match_risk_levels: list[str],
    ) -> str:
        resolved = RiskLevel.LOW
        for risk_level in match_risk_levels:
            if RISK_ORDER.get(risk_level, 0) > RISK_ORDER[resolved]:
                resolved = risk_level
        rules = RiskRule.objects.filter(enabled=True).order_by("-weight")
        for rule in rules:
            triggered = False
            if rule.condition_type == RiskRule.ConditionType.SOURCE_MATCH and rule.source_code in match_sources:
                triggered = True
            if rule.condition_type == RiskRule.ConditionType.COUNTRY_MATCH and rule.target_value in country_list_names:
                triggered = True
            if rule.condition_type == RiskRule.ConditionType.SCORE_THRESHOLD:
                threshold = int(rule.config.get("threshold", rule.target_value or 0) or 0)
                triggered = any(score >= threshold for score in match_scores)
            if triggered and RISK_ORDER[rule.risk_level] > RISK_ORDER[resolved]:
                resolved = rule.risk_level
        return resolved

    @staticmethod
    @transaction.atomic
    def run_screening(payload: dict, user, request=None) -> ScreeningRequest:
        client = payload.get("client")
        if isinstance(client, Client):
            client_obj = client
        else:
            client_obj = Client.objects.create(created_by=user, **payload["client"])

        search_type, query_term = ScreeningService._resolve_search(client_obj, payload)

        screening = ScreeningRequest.objects.create(
            client=client_obj,
            created_by=user,
            ip_address=getattr(request, "client_ip", None),
            status=ScreeningRequest.Status.PENDING,
        )

        comments = payload.get("comments", "")
        if comments:
            screening.comments = comments
            screening.save(update_fields=["comments"])

        candidates = WatchlistRepository.candidate_entries(query_term) if search_type in {"person", "company"} and query_term else []
        # External matches will be processed asynchronously to avoid blocking.
        external_matches = []
        min_score = settings.SCREENING_SETTINGS["MIN_FUZZY_SCORE"]
        match_sources = []
        country_list_names = []
        match_scores = []
        match_risk_levels = []

        for entry in candidates:
            names = [entry.primary_name, *entry.aliases]
            score = max(similarity_score(query_term, candidate_name) for candidate_name in names if candidate_name)
            if score < min_score:
                continue
            match_sources.append(entry.source.code)
            match_scores.append(score)
            risk_level = RiskLevel.HIGH
            if entry.source.code in {SourceCode.OFAC, SourceCode.INTERPOL}:
                risk_level = RiskLevel.CRITICAL
            if entry.source.code == SourceCode.UN:
                risk_level = RiskLevel.HIGH
            match_risk_levels.append(risk_level)
            ScreeningMatch.objects.create(
                screening=screening,
                watchlist_entry=entry,
                source_code=entry.source.code,
                matched_name=entry.primary_name,
                score=score,
                risk_level=risk_level,
                nationality=entry.nationality,
                aliases=entry.aliases,
                details={
                    "distance": levenshtein_distance(query_term, entry.primary_name),
                    "search_type": search_type,
                    "query_term": query_term,
                    "countries": entry.countries,
                    "identifiers": entry.identifiers,
                },
                remarks=entry.remarks,
            )

        # schedule external matches processing in background (Celery task or direct call as fallback)
        try:
            from apps.screening.tasks import process_external_matches
            # if Celery is configured, this will enqueue; otherwise it will execute synchronously
            try:
                # prefer non-blocking enqueue if task is a Celery task
                process_external_matches.apply_async(args=(screening.pk, query_term, search_type))
            except Exception:
                # fallback to direct call (synchronous)
                process_external_matches(screening.pk, query_term, search_type)
        except Exception:
            # if task import fails, ignore and continue
            pass

        country_candidates = [value for value in {client_obj.country} if value]
        for country in country_candidates:
            country_profile = WatchlistRepository.country_profile(country)
            if country_profile and (country_profile.is_blocked or country_profile.risk_level != RiskLevel.LOW):
                risk_level = RiskLevel.CRITICAL if country_profile.is_blocked else country_profile.risk_level
                match_scores.append(100)
                match_risk_levels.append(risk_level)
                country_list_names.append("Blocked Country" if country_profile.is_blocked else "Country Risk Rule")
                ScreeningMatch.objects.create(
                    screening=screening,
                    source_code="RULES",
                    matched_name=country_profile.name,
                    score=100,
                    risk_level=risk_level,
                    details={"country_rule": country_profile.notes, "blocked": country_profile.is_blocked},
                    remarks=country_profile.notes,
                )
            for risk_entry in WatchlistRepository.country_risks(country):
                country_list_names.append(risk_entry.list_name)
                match_scores.append(100)
                match_risk_levels.append(risk_entry.risk_level)
                ScreeningMatch.objects.create(
                    screening=screening,
                    source_code=risk_entry.source.code,
                    matched_name=country,
                    score=100,
                    risk_level=risk_entry.risk_level,
                    details={"country_risk": risk_entry.list_name},
                    remarks=risk_entry.notes,
                )

        final_risk = ScreeningService._evaluate_risk(match_sources, country_list_names, match_scores, match_risk_levels)
        screening.risk_level = final_risk
        screening.status = ScreeningRequest.Status.REVIEW if final_risk in {RiskLevel.HIGH, RiskLevel.CRITICAL} else ScreeningRequest.Status.COMPLETED
        screening.recommendation = ScreeningService._recommendation(final_risk)
        screening.metadata = {
            "search_type": search_type,
            "query_term": query_term,
            "query_name": query_term if search_type == "person" else "",
            "query_company": query_term if search_type == "company" else "",
            "query_country": query_term if search_type == "country" else client_obj.country,
            "total_matches": screening.matches.count(),
            "country_candidates": country_candidates,
        }
        screening.save(update_fields=["risk_level", "status", "recommendation", "metadata"])

        if user and final_risk in {RiskLevel.HIGH, RiskLevel.CRITICAL}:
            Alert.objects.create(
                user=user,
                screening=screening,
                alert_type=Alert.AlertType.NEW_MATCH,
                title=f"High-risk screening #{screening.pk}",
                message=f"Screening returned {screening.matches.count()} matches with risk {final_risk}.",
                metadata={"risk_level": final_risk},
            )

        AuditService.record(
            action="screening_run",
            request=request,
            user=user,
            resource_type="screening",
            resource_id=str(screening.pk),
            metadata={"risk_level": final_risk, "matches": screening.matches.count(), "search_type": search_type, "query_term": query_term},
        )
        return screening

    @staticmethod
    def revalidate_active_clients(limit: int = 500) -> int:
        processed = 0
        for client in Client.objects.select_related("created_by").all()[:limit]:
            ScreeningService.run_screening(
                {"client": client, "comments": "Continuous monitoring revalidation"},
                user=client.created_by,
            )
            processed += 1
        return processed
