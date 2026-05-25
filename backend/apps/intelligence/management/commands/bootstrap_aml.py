from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.intelligence.services.sync_service import SourceSyncService


class Command(BaseCommand):
    help = "Bootstraps default sanctions sources, risk rules and optional admin user."

    def add_arguments(self, parser):
        parser.add_argument("--admin-email", default="admin@aml.local")
        parser.add_argument("--admin-password", default="ChangeMe123!")

    def handle(self, *args, **options):
        SourceSyncService.bootstrap_defaults()
        User = get_user_model()
        if not User.objects.filter(email=options["admin_email"]).exists():
            User.objects.create_superuser(email=options["admin_email"], password=options["admin_password"])
            self.stdout.write(self.style.SUCCESS("Admin user created."))
        self.stdout.write(self.style.SUCCESS("AML bootstrap completed."))
