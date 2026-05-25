from rest_framework.routers import DefaultRouter

from apps.users.api.views import SessionViewSet, UserViewSet

router = DefaultRouter()
router.include_format_suffixes = False
router.register("", UserViewSet, basename="users")
router.register("sessions", SessionViewSet, basename="my-sessions")

urlpatterns = router.urls
