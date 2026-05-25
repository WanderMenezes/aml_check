import hashlib
import logging
from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from apps.audit.services.audit_service import AuditService
from apps.intelligence.models import Country, CountryRiskEntry, RiskRule, SanctionsSource, SourceCode, SyncJobLog, WatchlistEntry
from apps.intelligence.services.providers import PROVIDER_MAP
from common.utils.countries import COUNTRY_NAMES

logger = logging.getLogger(__name__)


DEFAULT_SOURCES = [
    {
        "code": SourceCode.OFAC,
        "name": "OFAC Specially Designated Nationals",
        "source_type": SanctionsSource.SourceType.SANCTIONS,
        "source_format": SanctionsSource.SourceFormat.XML,
        "endpoint": "https://www.treasury.gov/ofac/downloads/sdn.xml",
        "landing_url": "https://sanctionssearch.ofac.treas.gov/",
    },
    {
        "code": SourceCode.UN,
        "name": "UN Security Council Consolidated List",
        "source_type": SanctionsSource.SourceType.SANCTIONS,
        "source_format": SanctionsSource.SourceFormat.XML,
        "endpoint": "https://scsanctions.un.org/resources/xml/en/consolidated.xml",
        "landing_url": "https://www.un.org/securitycouncil/content/un-sc-consolidated-list",
    },
    {
        "code": SourceCode.EU,
        "name": "EU Consolidated Financial Sanctions",
        "source_type": SanctionsSource.SourceType.SANCTIONS,
        "source_format": SanctionsSource.SourceFormat.XML,
        "endpoint": "https://webgate.ec.europa.eu/fsd/fsf/public/files/xmlFullSanctionsList_1_1/content",
        "landing_url": "https://ec.europa.eu/fpi/what-we-do/sanctions_en",
    },
    {
        "code": SourceCode.FATF,
        "name": "FATF Black & Grey Lists",
        "source_type": SanctionsSource.SourceType.COUNTRY_RISK,
        "source_format": SanctionsSource.SourceFormat.HTML,
        "endpoint": "https://www.fatf-gafi.org/en/countries/black-and-grey-lists.html",
        "landing_url": "https://www.fatf-gafi.org/en/countries/black-and-grey-lists.html",
    },
    {
        "code": SourceCode.INTERPOL,
        "name": "INTERPOL Red Notices",
        "source_type": SanctionsSource.SourceType.LAW_ENFORCEMENT,
        "source_format": SanctionsSource.SourceFormat.JSON,
        "endpoint": "https://ws-public.interpol.int/notices/v1/red?resultPerPage=160",
        "landing_url": "https://www.interpol.int/How-we-work/Notices/View-Red-Notices",
    },
]


DEFAULT_RULES = [
    {
        "name": "OFAC match is critical",
        "condition_type": RiskRule.ConditionType.SOURCE_MATCH,
        "source_code": SourceCode.OFAC,
        "risk_level": "CRITICAL",
        "weight": 100,
    },
    {
        "name": "UN match is high",
        "condition_type": RiskRule.ConditionType.SOURCE_MATCH,
        "source_code": SourceCode.UN,
        "risk_level": "HIGH",
        "weight": 90,
    },
    {
        "name": "Interpol match is critical",
        "condition_type": RiskRule.ConditionType.SOURCE_MATCH,
        "source_code": SourceCode.INTERPOL,
        "risk_level": "CRITICAL",
        "weight": 100,
    },
    {
        "name": "Very high similarity score is high",
        "condition_type": RiskRule.ConditionType.SCORE_THRESHOLD,
        "target_value": "92",
        "risk_level": "HIGH",
        "weight": 85,
        "config": {"threshold": 92},
    },
    {
        "name": "FATF grey list country is medium",
        "condition_type": RiskRule.ConditionType.COUNTRY_MATCH,
        "source_code": SourceCode.FATF,
        "target_value": "FATF Grey List",
        "risk_level": "MEDIUM",
        "weight": 60,
    },
    {
        "name": "FATF black list country is high",
        "condition_type": RiskRule.ConditionType.COUNTRY_MATCH,
        "source_code": SourceCode.FATF,
        "target_value": "FATF Black List",
        "risk_level": "HIGH",
        "weight": 80,
    },
]


@dataclass
class SyncStats:
    processed: int = 0
    created: int = 0
    updated: int = 0
    deactivated: int = 0


class SourceSyncService:
    @staticmethod
    def bootstrap_defaults():
        for country_name in COUNTRY_NAMES:
            Country.objects.update_or_create(name=country_name, defaults={})
        for source in DEFAULT_SOURCES:
            SanctionsSource.objects.update_or_create(code=source["code"], defaults=source)
        for rule in DEFAULT_RULES:
            RiskRule.objects.update_or_create(name=rule["name"], defaults=rule)

    @staticmethod
    @transaction.atomic
    def sync_source(source: SanctionsSource, trigger: str = SyncJobLog.TriggerType.MANUAL, request=None) -> SyncJobLog:
        log = SyncJobLog.objects.create(source=source, trigger=trigger)
        provider = PROVIDER_MAP[source.code]
        stats = SyncStats()
        try:
            raw_text = provider.fetch(source)
            entries, countries = provider.parse(raw_text)

            seen_hashes = set()
            for entry in entries:
                stats.processed += 1
                record_hash = hashlib.sha1(
                    f"{source.code}:{entry.get('external_id', '')}:{entry.get('primary_name', '')}".encode("utf-8")
                ).hexdigest()
                obj, created = WatchlistEntry.objects.update_or_create(
                    source=source,
                    record_hash=record_hash,
                    defaults={
                        "external_id": entry.get("external_id", ""),
                        "entry_type": entry.get("entry_type", WatchlistEntry.EntryType.PERSON),
                        "primary_name": entry.get("primary_name", ""),
                        "aliases": entry.get("aliases", []),
                        "countries": entry.get("countries", []),
                        "nationality": entry.get("nationality", ""),
                        "date_of_birth": entry.get("date_of_birth", ""),
                        "identifiers": entry.get("identifiers", {}),
                        "remarks": entry.get("remarks", ""),
                        "source_url": entry.get("source_url", source.landing_url),
                        "raw_payload": entry.get("raw_payload", {}),
                        "record_hash": record_hash,
                        "is_active": True,
                    },
                )
                seen_hashes.add(obj.record_hash)
                if created:
                    stats.created += 1
                else:
                    stats.updated += 1

            if entries:
                stale = WatchlistEntry.objects.filter(source=source, is_active=True).exclude(record_hash__in=seen_hashes)
                stats.deactivated += stale.update(is_active=False)

            if source.code == SourceCode.FATF:
                CountryRiskEntry.objects.filter(source=source).update(is_active=False)
                for country in countries:
                    obj, created = CountryRiskEntry.objects.update_or_create(
                        source=source,
                        country_name=country["country_name"],
                        list_name=country["list_name"],
                        defaults={
                            "risk_level": country["risk_level"],
                            "notes": country.get("notes", ""),
                            "raw_payload": country,
                            "is_active": True,
                        },
                    )
                    stats.processed += 1
                    if created:
                        stats.created += 1
                    else:
                        stats.updated += 1

            source.last_synced_at = timezone.now()
            source.health_status = SanctionsSource.HealthStatus.OK
            source.save(update_fields=["last_synced_at", "health_status"])
            log.close(
                SyncJobLog.Status.SUCCESS,
                items_processed=stats.processed,
                items_created=stats.created,
                items_updated=stats.updated,
                items_deactivated=stats.deactivated,
            )
            AuditService.record(
                action="source_sync",
                request=request,
                resource_type="sanctions_source",
                resource_id=source.code,
                metadata={"status": "success", "processed": stats.processed},
            )
        except Exception as exc:  # pragma: no cover
            logger.exception("Sync failed for %s", source.code)
            source.health_status = SanctionsSource.HealthStatus.ERROR
            source.save(update_fields=["health_status"])
            log.close(SyncJobLog.Status.FAILED, error_message=str(exc))
            AuditService.record(
                action="source_sync",
                request=request,
                resource_type="sanctions_source",
                resource_id=source.code,
                status="failed",
                severity="CRITICAL",
                description=str(exc),
            )
        return log

    @staticmethod
    def sync_enabled_sources(trigger: str = SyncJobLog.TriggerType.SCHEDULED):
        SourceSyncService.bootstrap_defaults()
        for source in SanctionsSource.objects.filter(enabled=True):
            SourceSyncService.sync_source(source, trigger=trigger)
        from apps.screening.services.screening_service import ScreeningService

        ScreeningService.revalidate_active_clients()
