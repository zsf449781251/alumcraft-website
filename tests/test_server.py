import os
import json
import threading
import unittest
from contextlib import contextmanager
from functools import partial
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from unittest.mock import MagicMock, patch

import server


VALID_FORM = {
    "name": "Ada Lovelace",
    "company": "Example Imports",
    "email": "buyer@example.com",
    "country": "United Kingdom",
    "product_interest": "Standard CR80 Cards",
    "quantity": "500 pcs",
    "message": "Please quote anodized cards for delivery next month.",
    "language": "en",
    "source_page": "https://9gygp5h788.coze.site/#contact",
    "submission_id": "test-submission-0001",
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
    def test_valid_inquiry_is_normalized(self):
        inquiry = server.parse_inquiry(VALID_FORM)
        self.assertEqual(inquiry.email, "buyer@example.com")
        self.assertEqual(inquiry.language, "en")

    def test_invalid_email_is_rejected(self):
        form = {**VALID_FORM, "email": "not-an-email"}
        with self.assertRaisesRegex(server.InquiryError, "valid email"):
            server.parse_inquiry(form)

    def test_short_message_is_rejected(self):
        form = {**VALID_FORM, "message": "Too short"}
        with self.assertRaises(server.InquiryError) as raised:
            server.parse_inquiry(form)
        self.assertEqual(raised.exception.code, "input_too_short")

    def test_unknown_language_falls_back_to_english(self):
        form = {**VALID_FORM, "language": "unknown"}
        self.assertEqual(server.parse_inquiry(form).language, "en")


class EmailTests(unittest.TestCase):
    def setUp(self):
        self.settings = server.MailSettings(
            host="smtp.exmail.qq.com",
            port=465,
            username="forms@yushiglobal.cn",
            password="test-only-password",
            from_email="forms@yushiglobal.cn",
            from_name="AlumCraft Website",
            to_email="znegshifan@yushiglobal.cn",
            security="ssl",
            timeout=15,
        )

    def test_message_uses_fixed_sender_and_visitor_reply_to(self):
        message = server.build_email(server.parse_inquiry(VALID_FORM), self.settings)
        self.assertIn("forms@yushiglobal.cn", str(message["From"]))
        self.assertEqual(str(message["To"]), "znegshifan@yushiglobal.cn")
        self.assertEqual(str(message["Reply-To"]), "buyer@example.com")
        self.assertNotIn("buyer@example.com", str(message["From"]))
        self.assertIn("Please quote anodized cards", message.get_content())

    @patch("server.smtplib.SMTP_SSL")
    def test_ssl_delivery_logs_in_and_sends(self, smtp_ssl):
        smtp = MagicMock()
        smtp_ssl.return_value.__enter__.return_value = smtp
        message = server.build_email(server.parse_inquiry(VALID_FORM), self.settings)

        server.send_email(message, self.settings)

        smtp.login.assert_called_once_with("forms@yushiglobal.cn", "test-only-password")
        smtp.send_message.assert_called_once_with(message)

    def test_missing_password_is_rejected(self):
        environment = {
            "SMTP_USERNAME": "forms@yushiglobal.cn",
            "SMTP_FROM_EMAIL": "forms@yushiglobal.cn",
            "INQUIRY_TO_EMAIL": "znegshifan@yushiglobal.cn",
        }
        with patch.dict(os.environ, environment, clear=True):
            with self.assertRaises(server.MailConfigurationError):
                server.MailSettings.from_environment()


class ProtectionTests(unittest.TestCase):
    def test_rate_limiter_blocks_after_limit(self):
        limiter = server.RateLimiter(limit=2, window_seconds=60)
        self.assertTrue(limiter.allow("203.0.113.10", now=100))
        self.assertTrue(limiter.allow("203.0.113.10", now=101))
        self.assertFalse(limiter.allow("203.0.113.10", now=102))
        self.assertTrue(limiter.allow("203.0.113.10", now=161))

    def test_rate_limiter_bounds_tracked_clients(self):
        limiter = server.RateLimiter(limit=2, window_seconds=60, max_clients=3)
        for index in range(10):
            limiter.allow(f"203.0.113.{index}", now=1)
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
        for blocked_path in ("/AlumCraft_Client_Tracker.xlsx", "/README.md", "/server.py", "/.git/config"):
            handler.path = blocked_path
            self.assertFalse(handler._is_public_static_path(), blocked_path)

    def test_static_server_allows_public_pages_and_assets(self):
        handler = object.__new__(server.AlumCraftRequestHandler)
        for public_path in ("/", "/index.html", "/ro/", "/pl/faq.html", "/images/hero-main.webp", "/js/contact-form.js"):
            handler.path = public_path
            self.assertTrue(handler._is_public_static_path(), public_path)


class HttpIntegrationTests(unittest.TestCase):
    def test_health_and_private_file_protection(self):
        with patch.dict(os.environ, {}, clear=True), running_server() as base_url:
            status, health = read_json(f"{base_url}/api/health")
            self.assertEqual(status, 200)
            self.assertEqual(health, {"ok": True, "mail_configured": False})
            with self.assertRaises(HTTPError) as blocked:
                urlopen(f"{base_url}/AlumCraft_Client_Tracker.xlsx", timeout=3)
            self.assertEqual(blocked.exception.code, 404)

    def test_unconfigured_form_fails_without_false_success(self):
        request_data = urlencode(VALID_FORM).encode()
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        with patch.dict(os.environ, {}, clear=True), running_server() as base_url:
            status, result = read_json(f"{base_url}/api/inquiry", data=request_data, headers=headers)
        self.assertEqual(status, 503)
        self.assertEqual(result["ok"], False)
        self.assertEqual(result["code"], "mail_unavailable")

    @patch("server.send_email")
    def test_valid_form_returns_success_only_after_delivery(self, mocked_send):
        form = {**VALID_FORM, "submission_id": "test-valid-http-0001"}
        request_data = urlencode(form).encode()
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        environment = {
            "SMTP_USERNAME": "forms@yushiglobal.cn",
            "SMTP_PASSWORD": "test-only-password",
            "SMTP_FROM_EMAIL": "forms@yushiglobal.cn",
            "INQUIRY_TO_EMAIL": "znegshifan@yushiglobal.cn",
        }
        with patch.dict(os.environ, environment, clear=True), running_server() as base_url:
            status, result = read_json(f"{base_url}/api/inquiry", data=request_data, headers=headers)
        self.assertEqual(status, 200)
        self.assertEqual(result, {"ok": True})
        mocked_send.assert_called_once()

    @patch("server.send_email")
    def test_successful_retry_is_not_delivered_twice(self, mocked_send):
        form = {**VALID_FORM, "submission_id": "test-duplicate-http-0001"}
        request_data = urlencode(form).encode()
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        environment = {
            "SMTP_USERNAME": "forms@yushiglobal.cn",
            "SMTP_PASSWORD": "test-only-password",
            "SMTP_FROM_EMAIL": "forms@yushiglobal.cn",
            "INQUIRY_TO_EMAIL": "znegshifan@yushiglobal.cn",
        }
        with patch.dict(os.environ, environment, clear=True), running_server() as base_url:
            first_status, first_result = read_json(f"{base_url}/api/inquiry", data=request_data, headers=headers)
            retry_status, retry_result = read_json(f"{base_url}/api/inquiry", data=request_data, headers=headers)
        self.assertEqual((first_status, first_result), (200, {"ok": True}))
        self.assertEqual((retry_status, retry_result), (200, {"ok": True, "duplicate": True}))
        mocked_send.assert_called_once()

    @patch("server.send_email")
    def test_maximum_unicode_message_fits_request_limit(self, mocked_send):
        form = {
            **VALID_FORM,
            "message": "𠀀" * 5000,
            "submission_id": "test-unicode-http-0001",
        }
        request_data = urlencode(form).encode()
        self.assertLess(len(request_data), server.MAX_BODY_BYTES)
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        environment = {
            "SMTP_USERNAME": "forms@yushiglobal.cn",
            "SMTP_PASSWORD": "test-only-password",
            "SMTP_FROM_EMAIL": "forms@yushiglobal.cn",
            "INQUIRY_TO_EMAIL": "znegshifan@yushiglobal.cn",
        }
        with patch.dict(os.environ, environment, clear=True), running_server() as base_url:
            status, result = read_json(f"{base_url}/api/inquiry", data=request_data, headers=headers)
        self.assertEqual((status, result), (200, {"ok": True}))
        mocked_send.assert_called_once()

    def test_honeypot_does_not_require_or_send_mail(self):
        form = {**VALID_FORM, "bot-field": "spam"}
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        with patch.dict(os.environ, {}, clear=True), patch("server.send_email") as mocked_send, running_server() as base_url:
            status, result = read_json(f"{base_url}/api/inquiry", data=urlencode(form).encode(), headers=headers)
        self.assertEqual(status, 200)
        self.assertEqual(result, {"ok": True})
        mocked_send.assert_not_called()


if __name__ == "__main__":
    unittest.main()
