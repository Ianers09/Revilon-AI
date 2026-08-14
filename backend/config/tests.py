from django.conf import settings
from django.test import SimpleTestCase
from django.urls import reverse


class HealthCheckTests(SimpleTestCase):
    def test_health_check(self):
        response = self.client.get(reverse("health-check"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_security_headers_are_present(self):
        response = self.client.get("/health/")

        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response["X-Frame-Options"], "DENY")
        self.assertIn("camera=()", response["Permissions-Policy"])

    def test_auth_responses_are_not_cacheable(self):
        response = self.client.post(
            "/api/auth/login/",
            data={},
            content_type="application/json",
        )

        self.assertEqual(response["Cache-Control"], "no-store, max-age=0")
        self.assertEqual(response["Pragma"], "no-cache")


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
    def test_removed_about_urls_return_not_found(self):
        self.assertEqual(self.client.get("/about/").status_code, 404)
        self.assertEqual(self.client.get("/aboutus/").status_code, 404)

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
