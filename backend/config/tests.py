from django.conf import settings
from django.test import SimpleTestCase
from django.urls import reverse


class HealthCheckTests(SimpleTestCase):
    def test_health_check(self):
        response = self.client.get(reverse("health-check"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})


class ProductionDomainSettingsTests(SimpleTestCase):
    def test_custom_domain_is_always_allowed_and_trusted(self):
        self.assertIn("revilonai.com", settings.ALLOWED_HOSTS)
        self.assertIn("www.revilonai.com", settings.ALLOWED_HOSTS)
        self.assertIn(
            "https://revilonai.com",
            settings.CSRF_TRUSTED_ORIGINS,
        )
        self.assertIn(
            "https://www.revilonai.com",
            settings.CORS_ALLOWED_ORIGINS,
        )
