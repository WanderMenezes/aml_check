# Script para teste rápido de screening com fonte externa
# Executar com: python backend/manage.py shell < backend/scripts/run_test_screening.py

from django.contrib.auth import get_user_model
from apps.intelligence.models import SanctionsSource
from apps.screening.services.screening_service import ScreeningService
from apps.screening.api.serializers import ScreeningRequestSerializer

User = get_user_model()
user = User.objects.filter(is_superuser=True).first() or User.objects.first()
if not user:
    user = User.objects.create_user('testuser', 'test@example.com', 'testpass')

# Cria/atualiza uma fonte de exemplo apontando para example.com
src, created = SanctionsSource.objects.get_or_create(
    code='EXAMPLE',
    defaults={
        'name': 'Example Source',
        'source_type': 'SANCTIONS',
        'source_format': 'HTML',
        'landing_url': 'https://example.com',
        'enabled': True,
    }
)
src.enabled = True
src.landing_url = 'https://example.com'
src.save()

payload = {
    'client': {
        'full_name': 'Example Domain',
        'company_name': '',
        'country': '',
        'subject_type': 'INDIVIDUAL',
    },
    'comments': 'Automated test for external_site_matches',
    'search_type': 'person',
}

screening = ScreeningService.run_screening(payload, user=user)
print('SCREENING_ID:', screening.pk)
print('RISK_LEVEL:', screening.risk_level)
print('MATCH COUNT:', screening.matches.count())

# Mostrar grouped_matches do serializer (se houver)
data = ScreeningRequestSerializer(screening, context={'request': None}).data
import json
print(json.dumps(data.get('grouped_matches', data.get('matches')), indent=2, ensure_ascii=False))
