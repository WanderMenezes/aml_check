from rest_framework.routers import DefaultRouter

from apps.audit.api.views import AuditEventViewSet

router = DefaultRouter()
router.include_format_suffixes = False
router.register("", AuditEventViewSet, basename="audit")

urlpatterns = router.urls
