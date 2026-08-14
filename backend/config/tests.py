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


class SearchEngineEndpointsTests(SimpleTestCase):
    def test_retired_about_page_redirects_home(self):
        response = self.client.get(reverse("retired-about"))

        self.assertRedirects(
            response,
            "/",
            status_code=301,
            fetch_redirect_response=False,
        )

    def test_robots_txt_references_sitemap(self):
        response = self.client.get(reverse("robots-txt"))

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "Sitemap: https://revilonai.com/sitemap.xml",
            response.content.decode(),
        )

    def test_sitemap_lists_public_pages(self):
        response = self.client.get(reverse("sitemap-xml"))
        content = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertIn("https://revilonai.com/", content)
        self.assertNotIn("/about/", content)
