import json
import os
import re
import threading
import unittest
from contextlib import contextmanager
from functools import partial
from http.client import HTTPConnection
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen
from unittest.mock import MagicMock, patch
from xml.etree import ElementTree

import server


PRIMARY_ORIGIN = "https://yushialumcraft.coze.site"
LEGACY_ORIGIN = "https://9gygp5h788.coze.site"

VALID_FORM = {
    "name": "Ada Lovelace",
    "company": "Example Imports",
    "email": "buyer@example.com",
    "country": "United Kingdom",
    "product_interest": "Standard CR80 Cards",
    "quantity": "500 pcs",
    "message": "",
    "language": "en",
    "source_page": f"{PRIMARY_ORIGIN}/#contact",
    "submission_id": "test-submission-0001",
}

MAIL_ENVIRONMENT = {
    "SMTP_USERNAME": "449781251@qq.com",
    "SMTP_PASSWORD": "test-only-password",
    "SMTP_FROM_EMAIL": "449781251@qq.com",
    "INQUIRY_TO_EMAIL": "449781251@qq.com",
}

LOCALIZED_HOME_PAGES = (
    Path("index.html"),
    Path("ro/index.html"),
    Path("pl/index.html"),
)

CANONICAL_PAGES = {
    Path("index.html"): f"{PRIMARY_ORIGIN}/",
    Path("ro/index.html"): f"{PRIMARY_ORIGIN}/ro/",
    Path("pl/index.html"): f"{PRIMARY_ORIGIN}/pl/",
    Path("applications.html"): f"{PRIMARY_ORIGIN}/applications.html",
    Path("ro/applications.html"): f"{PRIMARY_ORIGIN}/ro/applications.html",
    Path("pl/applications.html"): f"{PRIMARY_ORIGIN}/pl/applications.html",
    Path("faq.html"): f"{PRIMARY_ORIGIN}/faq.html",
    Path("ro/faq.html"): f"{PRIMARY_ORIGIN}/ro/faq.html",
    Path("pl/faq.html"): f"{PRIMARY_ORIGIN}/pl/faq.html",
    Path("blog-how-to-sublimate-aluminum.html"): (
        f"{PRIMARY_ORIGIN}/blog-how-to-sublimate-aluminum.html"
    ),
    Path("blog-sublimation-blank-thickness-guide.html"): (
        f"{PRIMARY_ORIGIN}/blog-sublimation-blank-thickness-guide.html"
    ),
    Path("blog-custom-die-cut-aluminum.html"): (
        f"{PRIMARY_ORIGIN}/blog-custom-die-cut-aluminum.html"
    ),
}


class QuietHandler(server.AlumCraftRequestHandler):
    def log_message(self, _format, *args):
        pass


@contextmanager
def running_server():
    handler = partial(QuietHandler, directory=str(Path(__file__).resolve().parents[1]))
    httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_port}"
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=2)


def read_json(url, *, data=None, headers=None):
    request = Request(url, data=data, headers=headers or {})
    try:
        with urlopen(request, timeout=3) as response:
            return response.status, json.loads(response.read())
    except HTTPError as error:
        return error.code, json.loads(error.read())


class InquiryValidationTests(unittest.TestCase):
    def test_valid_inquiry_allows_optional_message(self):
        inquiry = server.parse_inquiry(VALID_FORM)
        self.assertEqual(inquiry.email, "buyer@example.com")
        self.assertEqual(inquiry.message, "")

    def test_invalid_email_is_rejected(self):
        form = {**VALID_FORM, "email": "not-an-email"}
        with self.assertRaises(server.InquiryError) as raised:
            server.parse_inquiry(form)
        self.assertEqual(raised.exception.code, "invalid_email")

    def test_required_quote_fields_are_enforced(self):
        for field in ("country", "product_interest", "quantity"):
            with self.subTest(field=field):
                form = {**VALID_FORM, field: ""}
                with self.assertRaises(server.InquiryError) as raised:
                    server.parse_inquiry(form)
                self.assertEqual(raised.exception.code, "missing_required")

    def test_unknown_language_falls_back_to_english(self):
        form = {**VALID_FORM, "language": "unknown"}
        self.assertEqual(server.parse_inquiry(form).language, "en")

    def test_non_http_source_page_is_discarded(self):
        form = {**VALID_FORM, "source_page": "javascript:alert(1)"}
        self.assertEqual(server.parse_inquiry(form).source_page, "")


class EmailTests(unittest.TestCase):
    def setUp(self):
        self.settings = server.MailSettings(
            host="smtp.qq.com",
            port=465,
            username="449781251@qq.com",
            password="test-only-password",
            from_email="449781251@qq.com",
            from_name="AlumCraft Website",
            to_email="449781251@qq.com",
            security="ssl",
            timeout=15,
        )

    def test_message_uses_fixed_sender_and_visitor_reply_to(self):
        inquiry = server.parse_inquiry({**VALID_FORM, "message": "Please quote next month."})
        message = server.build_email(inquiry, self.settings)

        self.assertIn("449781251@qq.com", str(message["From"]))
        self.assertEqual(str(message["To"]), "449781251@qq.com")
        self.assertEqual(str(message["Reply-To"]), "buyer@example.com")
        self.assertNotIn("buyer@example.com", str(message["From"]))
        self.assertIn("Please quote next month", message.get_content())

    @patch("server.smtplib.SMTP_SSL")
    def test_ssl_delivery_logs_in_and_sends(self, smtp_ssl):
        smtp = MagicMock()
        smtp_ssl.return_value.__enter__.return_value = smtp
        message = server.build_email(server.parse_inquiry(VALID_FORM), self.settings)

        server.send_email(message, self.settings)

        smtp.login.assert_called_once_with(
            "449781251@qq.com",
            "test-only-password",
        )
        smtp.send_message.assert_called_once_with(message)

    def test_missing_password_is_rejected(self):
        with patch.dict(os.environ, MAIL_ENVIRONMENT | {"SMTP_PASSWORD": ""}, clear=True):
            with self.assertRaises(server.MailConfigurationError):
                server.MailSettings.from_environment()

    def test_default_settings_use_dedicated_qq_mailbox(self):
        with patch.dict(os.environ, {"SMTP_PASSWORD": "test-only-password"}, clear=True):
            settings = server.MailSettings.from_environment()

        self.assertEqual(settings.host, "smtp.qq.com")
        self.assertEqual(settings.port, 465)
        self.assertEqual(settings.security, "ssl")
        self.assertEqual(settings.username, "449781251@qq.com")
        self.assertEqual(settings.from_email, "449781251@qq.com")
        self.assertEqual(settings.to_email, "449781251@qq.com")


class ProtectionTests(unittest.TestCase):
    def test_rate_limiter_blocks_after_limit(self):
        limiter = server.RateLimiter(limit=2, window_seconds=60)
        self.assertTrue(limiter.allow("buyer", now=100))
        self.assertTrue(limiter.allow("buyer", now=101))
        self.assertFalse(limiter.allow("buyer", now=102))
        self.assertTrue(limiter.allow("buyer", now=161))

    def test_rate_limiter_bounds_tracked_clients(self):
        limiter = server.RateLimiter(limit=2, window_seconds=60, max_clients=3)
        for index in range(10):
            limiter.allow(f"buyer-{index}", now=1)
        self.assertLessEqual(len(limiter._requests), 3)

    def test_delivery_tracker_deduplicates_successful_submission(self):
        tracker = server.DeliveryTracker(ttl_seconds=60, max_entries=10)
        self.assertEqual(tracker.begin("submission-0000001", now=1), "new")
        self.assertEqual(tracker.begin("submission-0000001", now=2), "inflight")
        tracker.succeed("submission-0000001", now=3)
        self.assertEqual(tracker.begin("submission-0000001", now=4), "success")

    def test_delivery_tracker_allows_retry_after_failure(self):
        tracker = server.DeliveryTracker(ttl_seconds=60, max_entries=10)
        self.assertEqual(tracker.begin("submission-0000002", now=1), "new")
        tracker.fail("submission-0000002")
        self.assertEqual(tracker.begin("submission-0000002", now=2), "new")

    def test_static_server_blocks_internal_files(self):
        handler = object.__new__(server.AlumCraftRequestHandler)
        for blocked_path in (
            "/README.md",
            "/server.py",
            "/.env",
            "/.git/config",
            "/tests/test_server.py",
        ):
            handler.path = blocked_path
            self.assertFalse(handler._is_public_static_path(), blocked_path)

    def test_static_server_allows_public_pages_and_assets(self):
        handler = object.__new__(server.AlumCraftRequestHandler)
        for public_path in (
            "/",
            "/index.html",
            "/favicon.svg",
            "/ro/",
            "/pl/faq.html",
            "/images/hero-main.webp",
            "/css/home-chat.css",
            "/js/contact-form.js",
        ):
            handler.path = public_path
            self.assertTrue(handler._is_public_static_path(), public_path)


class DomainMigrationTests(unittest.TestCase):
    def setUp(self):
        self.project_root = Path(__file__).resolve().parents[1]

    def test_public_page_canonicals_use_primary_origin(self):
        for relative_path, expected_canonical in CANONICAL_PAGES.items():
            with self.subTest(page=str(relative_path)):
                html = (self.project_root / relative_path).read_text(encoding="utf-8")
                canonical = re.search(
                    r'<link\s+rel="canonical"\s+href="([^"]+)"',
                    html,
                )
                self.assertIsNotNone(canonical)
                self.assertEqual(canonical.group(1), expected_canonical)
                self.assertNotIn(LEGACY_ORIGIN, html)

    def test_marketing_page_inventory_and_social_urls(self):
        discovered_pages = {
            path.relative_to(self.project_root)
            for directory in (self.project_root, self.project_root / "ro", self.project_root / "pl")
            for path in directory.glob("*.html")
            if not path.name.startswith("google")
        }
        self.assertEqual(discovered_pages, set(CANONICAL_PAGES))

        for relative_path, expected_canonical in CANONICAL_PAGES.items():
            with self.subTest(page=str(relative_path)):
                html = (self.project_root / relative_path).read_text(encoding="utf-8")
                open_graph_urls = re.findall(
                    r'<meta\s+property="og:url"\s+content="([^"]+)"',
                    html,
                )
                self.assertEqual(open_graph_urls, [expected_canonical])

                image_urls = re.findall(
                    r'<meta\s+(?:property="og:image"|name="twitter:image")\s+'
                    r'content="([^"]+)"',
                    html,
                )
                for image_url in image_urls:
                    parsed = urlsplit(image_url)
                    self.assertEqual(parsed.scheme, "https")
                    self.assertEqual(parsed.netloc, urlsplit(PRIMARY_ORIGIN).netloc)

    def test_localized_hreflang_sets_are_exact(self):
        page_families = (
            (
                (Path("index.html"), Path("ro/index.html"), Path("pl/index.html")),
                {
                    "en": f"{PRIMARY_ORIGIN}/",
                    "ro": f"{PRIMARY_ORIGIN}/ro/",
                    "pl": f"{PRIMARY_ORIGIN}/pl/",
                    "x-default": f"{PRIMARY_ORIGIN}/",
                },
            ),
            (
                (
                    Path("applications.html"),
                    Path("ro/applications.html"),
                    Path("pl/applications.html"),
                ),
                {
                    "en": f"{PRIMARY_ORIGIN}/applications.html",
                    "ro": f"{PRIMARY_ORIGIN}/ro/applications.html",
                    "pl": f"{PRIMARY_ORIGIN}/pl/applications.html",
                    "x-default": f"{PRIMARY_ORIGIN}/applications.html",
                },
            ),
            (
                (Path("faq.html"), Path("ro/faq.html"), Path("pl/faq.html")),
                {
                    "en": f"{PRIMARY_ORIGIN}/faq.html",
                    "ro": f"{PRIMARY_ORIGIN}/ro/faq.html",
                    "pl": f"{PRIMARY_ORIGIN}/pl/faq.html",
                    "x-default": f"{PRIMARY_ORIGIN}/faq.html",
                },
            ),
        )

        for pages, expected_links in page_families:
            for relative_path in pages:
                with self.subTest(page=str(relative_path)):
                    html = (self.project_root / relative_path).read_text(encoding="utf-8")
                    links = re.findall(
                        r'<link\s+rel="alternate"\s+hreflang="([^"]+)"\s+'
                        r'href="([^"]+)"',
                        html,
                    )
                    self.assertEqual(len(links), len(expected_links))
                    self.assertEqual(dict(links), expected_links)

    def test_json_ld_site_urls_use_primary_origin(self):
        def strings(value):
            if isinstance(value, str):
                yield value
            elif isinstance(value, dict):
                for child in value.values():
                    yield from strings(child)
            elif isinstance(value, list):
                for child in value:
                    yield from strings(child)

        for relative_path in CANONICAL_PAGES:
            with self.subTest(page=str(relative_path)):
                html = (self.project_root / relative_path).read_text(encoding="utf-8")
                scripts = re.findall(
                    r'<script\s+type="application/ld\+json">(.*?)</script>',
                    html,
                    re.DOTALL,
                )
                for script in scripts:
                    payload = json.loads(script)
                    for value in strings(payload):
                        parsed = urlsplit(value)
                        if parsed.hostname and parsed.hostname.endswith("coze.site"):
                            self.assertEqual(parsed.netloc, urlsplit(PRIMARY_ORIGIN).netloc)

    def test_crawl_metadata_uses_primary_origin(self):
        robots = (self.project_root / "robots.txt").read_text(encoding="utf-8")
        sitemap_path = self.project_root / "sitemap.xml"
        sitemap = sitemap_path.read_text(encoding="utf-8")

        self.assertIn(f"Sitemap: {PRIMARY_ORIGIN}/sitemap.xml", robots)
        self.assertNotIn(LEGACY_ORIGIN, robots)
        self.assertNotIn(LEGACY_ORIGIN, sitemap)

        namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        root = ElementTree.fromstring(sitemap)
        locations = [
            node.text for node in root.findall("sm:url/sm:loc", namespace)
        ]
        last_modified = {
            node.text for node in root.findall("sm:url/sm:lastmod", namespace)
        }
        self.assertEqual(len(locations), len(CANONICAL_PAGES))
        self.assertCountEqual(locations, CANONICAL_PAGES.values())
        self.assertEqual(last_modified, {"2026-08-29"})

    def test_deployment_docs_and_config_use_primary_origin(self):
        for relative_path in (Path(".env.example"), Path("_redirects"), Path("README.md")):
            with self.subTest(file=str(relative_path)):
                content = (self.project_root / relative_path).read_text(encoding="utf-8")
                self.assertIn(PRIMARY_ORIGIN, content)
                self.assertNotIn(LEGACY_ORIGIN, content)


class FormStyleTests(unittest.TestCase):
    def test_product_select_has_an_explicit_dark_popup_palette(self):
        project_root = Path(__file__).resolve().parents[1]

        for relative_path in LOCALIZED_HOME_PAGES:
            with self.subTest(page=str(relative_path)):
                html = (project_root / relative_path).read_text(encoding="utf-8")
                self.assertRegex(
                    html,
                    r"\.form-select\s*\{[^}]*color-scheme:\s*dark;[^}]*\}",
                )
                self.assertRegex(
                    html,
                    r"\.form-select option\s*\{[^}]*"
                    r"background(?:-color)?:\s*var\(--bg-secondary\);[^}]*"
                    r"color:\s*var\(--text-primary\);[^}]*\}",
                )


class HttpIntegrationTests(unittest.TestCase):
    def setUp(self):
        server.SUBMITTER_RATE_LIMITER = server.RateLimiter(
            server.RATE_LIMIT_MAX_REQUESTS,
            server.RATE_LIMIT_WINDOW_SECONDS,
        )
        server.GLOBAL_RATE_LIMITER = server.RateLimiter(
            server.GLOBAL_RATE_LIMIT_MAX_REQUESTS,
            server.GLOBAL_RATE_LIMIT_WINDOW_SECONDS,
            max_clients=1,
        )
        server.DELIVERY_TRACKER = server.DeliveryTracker(
            server.DELIVERY_TRACKER_TTL_SECONDS,
            server.DELIVERY_TRACKER_MAX_ENTRIES,
        )

    def test_health_and_private_file_protection(self):
        with patch.dict(os.environ, {}, clear=True), running_server() as base_url:
            status, health = read_json(f"{base_url}/api/health")
            self.assertEqual((status, health), (200, {"ok": True, "mail_configured": False}))
            with self.assertRaises(HTTPError) as blocked:
                urlopen(f"{base_url}/server.py", timeout=3)
            self.assertEqual(blocked.exception.code, 404)

    def test_legacy_domain_redirect_preserves_path_and_query(self):
        parsed_legacy = urlsplit(LEGACY_ORIGIN)
        request_target = "/ro/faq.html?from=legacy"
        proxy_headers = (
            {"Host": parsed_legacy.netloc},
            {
                "Host": "internal-proxy.example",
                "X-Forwarded-Host": parsed_legacy.netloc,
            },
        )

        with running_server() as base_url:
            parsed_local = urlsplit(base_url)
            for method in ("GET", "HEAD"):
                for headers in proxy_headers:
                    with self.subTest(method=method, headers=headers):
                        connection = HTTPConnection(
                            parsed_local.hostname,
                            parsed_local.port,
                            timeout=3,
                        )
                        connection.request(method, request_target, headers=headers)
                        response = connection.getresponse()
                        response.read()
                        connection.close()

                        self.assertEqual(response.status, 301)
                        self.assertEqual(
                            response.getheader("Location"),
                            f"{PRIMARY_ORIGIN}{request_target}",
                        )

    def test_primary_domain_is_not_redirected(self):
        with running_server() as base_url:
            parsed_local = urlsplit(base_url)
            connection = HTTPConnection(
                parsed_local.hostname,
                parsed_local.port,
                timeout=3,
            )
            connection.request(
                "GET",
                "/api/health",
                headers={"Host": urlsplit(PRIMARY_ORIGIN).netloc},
            )
            response = connection.getresponse()
            payload = json.loads(response.read())
            connection.close()

        self.assertEqual(response.status, 200)
        self.assertTrue(payload["ok"])

    @patch("server.send_email")
    def test_primary_origin_allowlist_works_behind_proxy(self, mocked_send):
        form = {**VALID_FORM, "submission_id": "test-primary-origin-0001"}
        request_data = urlencode(form).encode()
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": PRIMARY_ORIGIN,
        }
        environment = MAIL_ENVIRONMENT | {"ALLOWED_ORIGINS": PRIMARY_ORIGIN}

        with patch.dict(os.environ, environment, clear=True), running_server() as base_url:
            status, result = read_json(
                f"{base_url}/api/inquiry",
                data=request_data,
                headers=headers,
            )

        self.assertEqual((status, result), (200, {"ok": True}))
        mocked_send.assert_called_once()

    def test_unconfigured_form_fails_without_false_success(self):
        request_data = urlencode(VALID_FORM).encode()
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        with patch.dict(os.environ, {}, clear=True), running_server() as base_url:
            status, result = read_json(
                f"{base_url}/api/inquiry",
                data=request_data,
                headers=headers,
            )
        self.assertEqual(status, 503)
        self.assertEqual(result["code"], "mail_unavailable")

    @patch("server.send_email")
    def test_valid_form_returns_success_only_after_delivery(self, mocked_send):
        form = {**VALID_FORM, "submission_id": "test-valid-http-0001"}
        request_data = urlencode(form).encode()
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        with patch.dict(os.environ, MAIL_ENVIRONMENT, clear=True), running_server() as base_url:
            status, result = read_json(
                f"{base_url}/api/inquiry",
                data=request_data,
                headers=headers,
            )
        self.assertEqual((status, result), (200, {"ok": True}))
        mocked_send.assert_called_once()

    @patch("server.send_email")
    def test_successful_retry_is_not_delivered_twice(self, mocked_send):
        form = {**VALID_FORM, "submission_id": "test-duplicate-http-0001"}
        request_data = urlencode(form).encode()
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        with patch.dict(os.environ, MAIL_ENVIRONMENT, clear=True), running_server() as base_url:
            first = read_json(f"{base_url}/api/inquiry", data=request_data, headers=headers)
            retry = read_json(f"{base_url}/api/inquiry", data=request_data, headers=headers)
        self.assertEqual(first, (200, {"ok": True}))
        self.assertEqual(retry, (200, {"ok": True, "duplicate": True}))
        mocked_send.assert_called_once()

    def test_cross_origin_submission_is_rejected(self):
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "https://attacker.example",
        }
        with patch.dict(os.environ, MAIL_ENVIRONMENT, clear=True), running_server() as base_url:
            status, result = read_json(
                f"{base_url}/api/inquiry",
                data=urlencode(VALID_FORM).encode(),
                headers=headers,
            )
        self.assertEqual(status, 403)
        self.assertEqual(result["code"], "origin_not_allowed")

    def test_honeypot_does_not_require_or_send_mail(self):
        form = {**VALID_FORM, "bot-field": "spam"}
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        with (
            patch.dict(os.environ, {}, clear=True),
            patch("server.send_email") as mocked_send,
            running_server() as base_url,
        ):
            status, result = read_json(
                f"{base_url}/api/inquiry",
                data=urlencode(form).encode(),
                headers=headers,
            )
        self.assertEqual((status, result), (200, {"ok": True}))
        mocked_send.assert_not_called()


if __name__ == "__main__":
    unittest.main()
