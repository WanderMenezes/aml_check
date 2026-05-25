from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.screening.services.screening_service import ScreeningService


class Command(BaseCommand):
    help = "Seeds a small demo screening dataset for local validation."

    def handle(self, *args, **options):
        User = get_user_model()
        user = User.objects.filter(is_superuser=True).first()
        if not user:
            self.stdout.write(self.style.WARNING("No admin user found. Run bootstrap_aml first."))
            return
        ScreeningService.run_screening(
            {
                "client": {
                    "full_name": "Mohamed Aly",
                    "company_name": "Aly Trading Ltd",
                    "country": "South Africa",
                    "nationality": "Egypt",
                    "passport_number": "XA123456",
                    "national_id": "BI-998877",
                }
            },
            user=user,
        )
        self.stdout.write(self.style.SUCCESS("Demo screening seeded."))
