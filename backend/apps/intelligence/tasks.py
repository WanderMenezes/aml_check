try:
    from celery import shared_task
except ImportError:  # pragma: no cover
    def shared_task(*args, **kwargs):
        def decorator(func):
            return func

        return decorator

from apps.intelligence.models import SanctionsSource, SyncJobLog
from apps.intelligence.services.sync_service import SourceSyncService


@shared_task
def sync_enabled_sources_task():
    return SourceSyncService.sync_enabled_sources(trigger=SyncJobLog.TriggerType.SCHEDULED)


@shared_task
def sync_single_source_task(source_id: int):
    source = SanctionsSource.objects.get(id=source_id)
    return SourceSyncService.sync_source(source, trigger=SyncJobLog.TriggerType.MANUAL).id
