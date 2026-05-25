import os

try:
    from celery import Celery
except ImportError:  # pragma: no cover
    Celery = None

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

if Celery:
    app = Celery("aml_check")
    app.config_from_object("django.conf:settings", namespace="CELERY")
    app.autodiscover_tasks()
else:  # pragma: no cover
    app = None
