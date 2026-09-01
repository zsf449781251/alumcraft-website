"""Serve AlumCraft and deliver website inquiries through authenticated SMTP.

The SMTP password is read from the process environment at request time. It is
never stored in the repository or returned to the browser.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import smtplib
import ssl
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from email.headerregistry import Address
from email.message import EmailMessage
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path, PurePosixPath
from typing import Mapping
from urllib.parse import parse_qs, unquote, urlsplit, urlunsplit


LOGGER = logging.getLogger("alumcraft.inquiry")
PRIMARY_ORIGIN = "https://yushialumcraft.coze.site"
LEGACY_HOSTS = {"9gygp5h788.coze.site"}
FORMAL_SITE_HOSTS = frozenset({urlsplit(PRIMARY_ORIGIN).hostname, *LEGACY_HOSTS})
MAX_BODY_BYTES = 96 * 1024
RATE_LIMIT_WINDOW_SECONDS = 10 * 60
RATE_LIMIT_MAX_REQUESTS = 5
RATE_LIMIT_MAX_CLIENTS = 10_000
GLOBAL_RATE_LIMIT_WINDOW_SECONDS = 60 * 60
GLOBAL_RATE_LIMIT_MAX_REQUESTS = 120
DELIVERY_TRACKER_TTL_SECONDS = 24 * 60 * 60
DELIVERY_TRACKER_MAX_ENTRIES = 10_000
SAFE_LANGUAGES = {"en", "ro", "pl"}
SUBMISSION_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{16,64}$")
ATTRIBUTION_TEXT_PATTERN = re.compile(r"^[^\W_][\w ._~:/+@-]*$", re.UNICODE)
CLICK_ID_PATTERN = re.compile(r"^[A-Za-z0-9._~-]{1,256}$")
EMAIL_PATTERN = re.compile(
    r"^[A-Z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?"
    r"(?:\.[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?)+$",
    re.IGNORECASE,
)

PUBLIC_ROOT_FILES = {
    "favicon.svg",
    "robots.txt",
    "sitemap.xml",
    "bfd6978628c0498aaf0ae2ef9bd2f7d3.txt",
}
PUBLIC_DIRECTORY_EXTENSIONS = {
    "css": {".css"},
    "images": {".avif", ".gif", ".ico", ".jpg", ".jpeg", ".png", ".svg", ".webp"},
    "js": {".js"},
    "pl": {".html"},
    "ro": {".html"},
}
PUBLIC_CHATBOT_FILES = {"chat.js", "index.html", "style.css"}


class InquiryError(ValueError):
    """A validation error that is safe to return to the browser."""

    def __init__(self, code: str, message: str, status: HTTPStatus = HTTPStatus.BAD_REQUEST):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


class MailConfigurationError(RuntimeError):
    """Raised when the server-side mail configuration is incomplete."""


@dataclass(frozen=True)
class Inquiry:
    name: str
    company: str
    email: str
    country: str
    product_interest: str
    quantity: str
    message: str
    language: str
    source_page: str
    utm_source: str = ""
    utm_medium: str = ""
    utm_campaign: str = ""
    utm_term: str = ""
    utm_content: str = ""
    gclid: str = ""
    msclkid: str = ""
    landing_page: str = ""
    referrer: str = ""


@dataclass(frozen=True)
class MailSettings:
    host: str
    port: int
    username: str
    password: str
    from_email: str
    from_name: str
    to_email: str
    security: str
    timeout: float

    @classmethod
    def from_environment(cls) -> "MailSettings":
        to_email = os.getenv("INQUIRY_TO_EMAIL", "449781251@qq.com").strip()
        username = os.getenv("SMTP_USERNAME", to_email).strip()
        settings = cls(
            host=os.getenv("SMTP_HOST", "smtp.qq.com").strip(),
            port=_integer_environment("SMTP_PORT", 465, minimum=1, maximum=65535),
            username=username,
            password=os.getenv("SMTP_PASSWORD", ""),
            from_email=os.getenv("SMTP_FROM_EMAIL", username).strip(),
            from_name=os.getenv("SMTP_FROM_NAME", "AlumCraft Website").strip(),
            to_email=to_email,
            security=os.getenv("SMTP_SECURITY", "ssl").strip().lower(),
            timeout=_float_environment("SMTP_TIMEOUT", 15.0, minimum=1.0, maximum=60.0),
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        if not self.host or not self.username or not self.password:
            raise MailConfigurationError("SMTP credentials are not configured")
        if self.security not in {"ssl", "starttls"}:
            raise MailConfigurationError("SMTP_SECURITY must be ssl or starttls")
        if not _valid_email(self.username):
            raise MailConfigurationError("SMTP_USERNAME must be a full email address")
        if not _valid_email(self.from_email) or not _valid_email(self.to_email):
            raise MailConfigurationError("The configured sender or recipient email is invalid")
        if (
            not self.from_name
            or len(self.from_name) > 100
            or "\r" in self.from_name
            or "\n" in self.from_name
        ):
            raise MailConfigurationError("SMTP_FROM_NAME is invalid")


class RateLimiter:
    """A bounded in-memory rate limiter suitable for one website process."""

    def __init__(self, limit: int, window_seconds: int, max_clients: int = RATE_LIMIT_MAX_CLIENTS):
        self.limit = limit
        self.window_seconds = window_seconds
        self.max_clients = max_clients
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()
        self._last_cleanup = 0.0

    def allow(self, key: str, now: float | None = None) -> bool:
        timestamp = time.monotonic() if now is None else now
        cutoff = timestamp - self.window_seconds
        with self._lock:
            if timestamp - self._last_cleanup >= self.window_seconds:
                for stored_key, stored_requests in list(self._requests.items()):
                    while stored_requests and stored_requests[0] <= cutoff:
                        stored_requests.popleft()
                    if not stored_requests:
                        del self._requests[stored_key]
                self._last_cleanup = timestamp

            if key not in self._requests and len(self._requests) >= self.max_clients:
                key = "__overflow__"
                if key not in self._requests and len(self._requests) >= self.max_clients:
                    self._requests.pop(next(iter(self._requests)))

            requests = self._requests[key]
            while requests and requests[0] <= cutoff:
                requests.popleft()
            if len(requests) >= self.limit:
                return False
            requests.append(timestamp)
            return True


class DeliveryTracker:
    """Remember in-flight and successful submissions so browser retries are safe."""

    def __init__(self, ttl_seconds: int, max_entries: int):
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self._entries: dict[str, tuple[str, float]] = {}
        self._lock = threading.Lock()
        self._last_cleanup = 0.0

    def begin(self, submission_id: str, now: float | None = None) -> str:
        timestamp = time.monotonic() if now is None else now
        cutoff = timestamp - self.ttl_seconds
        with self._lock:
            if timestamp - self._last_cleanup >= 300:
                self._entries = {
                    key: entry for key, entry in self._entries.items() if entry[1] > cutoff
                }
                self._last_cleanup = timestamp

            existing = self._entries.get(submission_id)
            if existing:
                return existing[0]

            if len(self._entries) >= self.max_entries:
                oldest_key = min(self._entries, key=lambda key: self._entries[key][1])
                del self._entries[oldest_key]
            self._entries[submission_id] = ("inflight", timestamp)
            return "new"

    def succeed(self, submission_id: str, now: float | None = None) -> None:
        timestamp = time.monotonic() if now is None else now
        with self._lock:
            self._entries[submission_id] = ("success", timestamp)

    def fail(self, submission_id: str) -> None:
        with self._lock:
            self._entries.pop(submission_id, None)


SUBMITTER_RATE_LIMITER = RateLimiter(RATE_LIMIT_MAX_REQUESTS, RATE_LIMIT_WINDOW_SECONDS)
GLOBAL_RATE_LIMITER = RateLimiter(
    GLOBAL_RATE_LIMIT_MAX_REQUESTS,
    GLOBAL_RATE_LIMIT_WINDOW_SECONDS,
    max_clients=1,
)
DELIVERY_TRACKER = DeliveryTracker(DELIVERY_TRACKER_TTL_SECONDS, DELIVERY_TRACKER_MAX_ENTRIES)


def _integer_environment(name: str, default: int, *, minimum: int, maximum: int) -> int:
    raw_value = os.getenv(name, str(default))
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise MailConfigurationError(f"{name} must be an integer") from exc
    if not minimum <= value <= maximum:
        raise MailConfigurationError(f"{name} is outside the allowed range")
    return value


def _float_environment(name: str, default: float, *, minimum: float, maximum: float) -> float:
    raw_value = os.getenv(name, str(default))
    try:
        value = float(raw_value)
    except ValueError as exc:
        raise MailConfigurationError(f"{name} must be a number") from exc
    if not minimum <= value <= maximum:
        raise MailConfigurationError(f"{name} is outside the allowed range")
    return value


def _text(data: Mapping[str, object], key: str, maximum: int, *, required: bool = False) -> str:
    value = str(data.get(key, "")).strip()
    if "\x00" in value:
        raise InquiryError("invalid_input", "The form contains invalid characters.")
    if required and not value:
        raise InquiryError("missing_required", "Please complete all required fields.")
    if len(value) > maximum:
        raise InquiryError("input_too_long", "One or more fields are too long.")
    return value


def _safe_attribution_text(data: Mapping[str, object], key: str, maximum: int = 256) -> str:
    """Return optional campaign text without letting metadata reject an inquiry."""

    try:
        raw_value = data.get(key, "")
        if raw_value is None or isinstance(raw_value, (dict, list, tuple, set)):
            return ""
        value = " ".join(str(raw_value).split())[:maximum]
    except Exception:
        return ""
    if not value or not ATTRIBUTION_TEXT_PATTERN.fullmatch(value):
        return ""
    return value


def _safe_click_id(data: Mapping[str, object], key: str) -> str:
    """Keep a complete, syntactically safe ad click identifier or discard it."""

    try:
        raw_value = data.get(key, "")
        if raw_value is None or isinstance(raw_value, (dict, list, tuple, set)):
            return ""
        value = str(raw_value).strip()
    except Exception:
        return ""
    return value if CLICK_ID_PATTERN.fullmatch(value) else ""


def _safe_url_value(data: Mapping[str, object], key: str, *, site_only: bool) -> str:
    """Strip sensitive URL parts from optional, untrusted attribution metadata."""

    try:
        raw_value = data.get(key, "")
        if raw_value is None or isinstance(raw_value, (dict, list, tuple, set)):
            return ""
        value = str(raw_value).strip()[:2048]
        if not value or any(
            character.isspace() or ord(character) < 32 or ord(character) == 127
            for character in value
        ):
            return ""
        parsed = urlsplit(value)
        scheme = parsed.scheme.lower()
        hostname = parsed.hostname
        if scheme not in {"http", "https"} or not hostname:
            return ""
        hostname = hostname.encode("idna").decode("ascii").lower()
        if ":" in hostname:
            if not re.fullmatch(r"[0-9a-f:.]+", hostname):
                return ""
        elif (
            len(hostname) > 253
            or not re.fullmatch(r"[a-z0-9.-]+", hostname)
            or ".." in hostname
            or hostname.startswith((".", "-"))
            or hostname.endswith((".", "-"))
        ):
            return ""
        if site_only and hostname not in FORMAL_SITE_HOSTS:
            return ""

        # Rebuild the authority rather than reusing netloc so credentials can
        # never be carried into the email. Site URLs are canonicalized to the
        # exact public hostname; external referrers retain a valid port.
        if ":" in hostname and not hostname.startswith("["):
            authority = f"[{hostname}]"
        else:
            authority = hostname
        if not site_only:
            port = parsed.port
            if port is not None:
                authority = f"{authority}:{port}"

        path = parsed.path or "/"
        return urlunsplit((scheme, authority, path, "", ""))
    except Exception:
        return ""


def _valid_email(value: str) -> bool:
    return (
        len(value) <= 254
        and "\r" not in value
        and "\n" not in value
        and bool(EMAIL_PATTERN.fullmatch(value))
    )


def parse_inquiry(data: Mapping[str, object]) -> Inquiry:
    name = _text(data, "name", 100, required=True)
    email = _text(data, "email", 254, required=True).lower()
    if len(name) < 2:
        raise InquiryError("input_too_short", "Please enter your full name.")
    if not _valid_email(email):
        raise InquiryError("invalid_email", "Please enter a valid email address.")

    language = _text(data, "language", 10).lower()
    if language not in SAFE_LANGUAGES:
        language = "en"

    return Inquiry(
        name=name,
        company=_text(data, "company", 150),
        email=email,
        country=_text(data, "country", 100, required=True),
        product_interest=_text(data, "product_interest", 150, required=True),
        quantity=_text(data, "quantity", 100, required=True),
        message=_text(data, "message", 5000),
        language=language,
        source_page=_safe_url_value(data, "source_page", site_only=True),
        utm_source=_safe_attribution_text(data, "utm_source"),
        utm_medium=_safe_attribution_text(data, "utm_medium"),
        utm_campaign=_safe_attribution_text(data, "utm_campaign"),
        utm_term=_safe_attribution_text(data, "utm_term"),
        utm_content=_safe_attribution_text(data, "utm_content"),
        gclid=_safe_click_id(data, "gclid"),
        msclkid=_safe_click_id(data, "msclkid"),
        landing_page=_safe_url_value(data, "landing_page", site_only=True),
        referrer=_safe_url_value(data, "referrer", site_only=False),
    )


def build_email(inquiry: Inquiry, settings: MailSettings) -> EmailMessage:
    subject_name = " ".join(inquiry.name.replace("\r", " ").replace("\n", " ").split())
    subject_company = " ".join(inquiry.company.replace("\r", " ").replace("\n", " ").split())
    subject = f"AlumCraft website inquiry — {subject_name}"
    if subject_company:
        subject += f" / {subject_company}"

    fields = (
        ("Name", inquiry.name),
        ("Company", inquiry.company),
        ("Email", inquiry.email),
        ("Country", inquiry.country),
        ("Product interest", inquiry.product_interest),
        ("Quantity", inquiry.quantity),
        ("Website language", inquiry.language),
        ("Project details", inquiry.message),
    )
    body = "New inquiry submitted through the AlumCraft website.\n\n" + "\n\n".join(
        f"{label}:\n{value}" for label, value in fields if value
    )

    attribution_fields = (
        ("UTM source", inquiry.utm_source),
        ("UTM medium", inquiry.utm_medium),
        ("UTM campaign", inquiry.utm_campaign),
        ("UTM term", inquiry.utm_term),
        ("UTM content", inquiry.utm_content),
        ("Google click ID", inquiry.gclid),
        ("Microsoft click ID", inquiry.msclkid),
        ("Landing page", inquiry.landing_page),
        ("Referrer", inquiry.referrer),
        ("Source page", inquiry.source_page),
    )
    attribution_lines = [
        f"{label}: {value}" for label, value in attribution_fields if value
    ]
    if attribution_lines:
        body += "\n\nCampaign attribution (untrusted metadata):\n" + "\n".join(
            attribution_lines
        )

    email_message = EmailMessage()
    email_message["Subject"] = subject
    email_message["From"] = Address(display_name=settings.from_name, addr_spec=settings.from_email)
    email_message["To"] = settings.to_email
    email_message["Reply-To"] = inquiry.email
    email_message["X-AlumCraft-Form"] = "website-inquiry"
    email_message.set_content(body)
    return email_message


def send_email(message: EmailMessage, settings: MailSettings) -> None:
    context = ssl.create_default_context()
    if settings.security == "ssl":
        with smtplib.SMTP_SSL(
            settings.host,
            settings.port,
            timeout=settings.timeout,
            context=context,
        ) as smtp:
            smtp.login(settings.username, settings.password)
            smtp.send_message(message)
        return

    with smtplib.SMTP(settings.host, settings.port, timeout=settings.timeout) as smtp:
        smtp.ehlo()
        smtp.starttls(context=context)
        smtp.ehlo()
        smtp.login(settings.username, settings.password)
        smtp.send_message(message)


class AlumCraftRequestHandler(SimpleHTTPRequestHandler):
    server_version = "AlumCraftWeb/1.1"

    def setup(self) -> None:
        super().setup()
        self.connection.settimeout(20)

    def version_string(self) -> str:
        return self.server_version

    def end_headers(self) -> None:
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        self.send_header("X-Frame-Options", "SAMEORIGIN")
        super().end_headers()

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
        if self._redirect_legacy_domain():
            return
        if self._redirect_canonical_index():
            return
        if urlsplit(self.path).path == "/api/health":
            try:
                MailSettings.from_environment()
                configured = True
            except MailConfigurationError:
                configured = False
            self._json_response(HTTPStatus.OK, {"ok": True, "mail_configured": configured})
            return
        if not self._is_public_static_path():
            self.send_error(HTTPStatus.NOT_FOUND.value)
            return
        super().do_GET()

    def do_HEAD(self) -> None:  # noqa: N802 - stdlib handler API
        if self._redirect_legacy_domain():
            return
        if self._redirect_canonical_index():
            return
        if not self._is_public_static_path():
            self.send_error(HTTPStatus.NOT_FOUND.value)
            return
        super().do_HEAD()

    def do_POST(self) -> None:  # noqa: N802 - stdlib handler API
        if urlsplit(self.path).path.rstrip("/") != "/api/inquiry":
            self._json_response(HTTPStatus.NOT_FOUND, {"ok": False, "code": "not_found"})
            return

        try:
            self._check_same_origin()
            data = self._read_form_data()

            if str(data.get("bot-field", "")).strip():
                self._json_response(HTTPStatus.OK, {"ok": True})
                return

            inquiry = parse_inquiry(data)
            settings = MailSettings.from_environment()
            submission_id = _text(data, "submission_id", 64, required=True)
            if not SUBMISSION_ID_PATTERN.fullmatch(submission_id):
                raise InquiryError("invalid_submission", "The submission identifier is invalid.")

            delivery_state = DELIVERY_TRACKER.begin(submission_id)
            if delivery_state == "success":
                self._json_response(HTTPStatus.OK, {"ok": True, "duplicate": True})
                return
            if delivery_state == "inflight":
                raise InquiryError(
                    "submission_in_progress",
                    "This inquiry is still being delivered. Please wait before retrying.",
                    HTTPStatus.CONFLICT,
                )

            submitter_key = hashlib.sha256(inquiry.email.casefold().encode("utf-8")).hexdigest()
            if not SUBMITTER_RATE_LIMITER.allow(submitter_key) or not GLOBAL_RATE_LIMITER.allow("all"):
                DELIVERY_TRACKER.fail(submission_id)
                raise InquiryError(
                    "rate_limited",
                    "Too many requests. Please wait a few minutes and try again.",
                    HTTPStatus.TOO_MANY_REQUESTS,
                )

            try:
                send_email(build_email(inquiry, settings), settings)
            except Exception:
                DELIVERY_TRACKER.fail(submission_id)
                raise
            DELIVERY_TRACKER.succeed(submission_id)
            self._json_response(HTTPStatus.OK, {"ok": True})
        except InquiryError as exc:
            self._json_response(exc.status, {"ok": False, "code": exc.code, "message": exc.message})
        except MailConfigurationError:
            LOGGER.error("Inquiry email delivery is not configured")
            self._json_response(
                HTTPStatus.SERVICE_UNAVAILABLE,
                {
                    "ok": False,
                    "code": "mail_unavailable",
                    "message": "Email delivery is temporarily unavailable.",
                },
            )
        except (smtplib.SMTPException, OSError, TimeoutError) as exc:
            LOGGER.error("Inquiry email delivery failed (%s)", type(exc).__name__)
            self._json_response(
                HTTPStatus.BAD_GATEWAY,
                {
                    "ok": False,
                    "code": "delivery_failed",
                    "message": "We could not deliver the inquiry right now.",
                },
            )
        except Exception as exc:
            LOGGER.exception("Unexpected inquiry form error (%s)", type(exc).__name__)
            self._json_response(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"ok": False, "code": "server_error", "message": "The form is temporarily unavailable."},
            )

    def _check_same_origin(self) -> None:
        origin = self.headers.get("Origin", "").strip()
        if not origin:
            return
        origin_host = urlsplit(origin).netloc.lower()
        request_host = self.headers.get("Host", "").strip().lower()
        allowed_hosts = {request_host}
        for allowed_origin in os.getenv("ALLOWED_ORIGINS", "").split(","):
            allowed_origin = allowed_origin.strip()
            if allowed_origin:
                allowed_hosts.add(urlsplit(allowed_origin).netloc.lower())
        if not origin_host or origin_host not in allowed_hosts:
            raise InquiryError(
                "origin_not_allowed",
                "This request origin is not allowed.",
                HTTPStatus.FORBIDDEN,
            )

    def _redirect_legacy_domain(self) -> bool:
        forwarded_host = self.headers.get("X-Forwarded-Host", "").split(",", 1)[0]
        request_hosts = (forwarded_host, self.headers.get("Host", ""))
        is_legacy_host = any(
            urlsplit(f"//{raw_host.strip()}").hostname in LEGACY_HOSTS
            for raw_host in request_hosts
            if raw_host.strip()
        )
        if not is_legacy_host:
            return False

        target = urlsplit(self.path)
        path = target.path or "/"
        if target.query:
            path = f"{path}?{target.query}"
        self.send_response(HTTPStatus.MOVED_PERMANENTLY.value)
        self.send_header("Location", f"{PRIMARY_ORIGIN}{path}")
        self.send_header("Cache-Control", "public, max-age=3600")
        self.send_header("Content-Length", "0")
        self.end_headers()
        return True

    def _redirect_canonical_index(self) -> bool:
        target = urlsplit(self.path)
        canonical_paths = {
            "/index.html": "/",
            "/ro/index.html": "/ro/",
            "/pl/index.html": "/pl/",
        }
        canonical_path = canonical_paths.get(target.path)
        if canonical_path is None:
            return False

        if target.query:
            canonical_path = f"{canonical_path}?{target.query}"
        self.send_response(HTTPStatus.MOVED_PERMANENTLY.value)
        self.send_header("Location", canonical_path)
        self.send_header("Cache-Control", "public, max-age=3600")
        self.send_header("Content-Length", "0")
        self.end_headers()
        return True

    def _read_form_data(self) -> dict[str, object]:
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise InquiryError("invalid_request", "The request body is invalid.") from exc
        if content_length <= 0:
            raise InquiryError("empty_request", "The request body is empty.")
        if content_length > MAX_BODY_BYTES:
            raise InquiryError(
                "request_too_large",
                "The inquiry is too large.",
                HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
            )

        raw_body = self.rfile.read(content_length)
        content_type = self.headers.get_content_type()
        try:
            if content_type == "application/json":
                decoded = json.loads(raw_body.decode("utf-8"))
                if not isinstance(decoded, dict):
                    raise ValueError("JSON body must be an object")
                return decoded
            if content_type == "application/x-www-form-urlencoded":
                parsed = parse_qs(
                    raw_body.decode("utf-8"),
                    keep_blank_values=True,
                    max_num_fields=32,
                )
                return {key: values[0] if values else "" for key, values in parsed.items()}
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            raise InquiryError("invalid_request", "The request body is invalid.") from exc
        raise InquiryError(
            "unsupported_media_type",
            "Use a supported form content type.",
            HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
        )

    def _is_public_static_path(self) -> bool:
        try:
            decoded_path = unquote(urlsplit(self.path).path, errors="strict")
        except UnicodeDecodeError:
            return False
        cleaned_parts = tuple(part for part in PurePosixPath(decoded_path).parts if part != "/")
        if any(part in {"", ".", ".."} or part.startswith(".") for part in cleaned_parts):
            return False
        if not cleaned_parts:
            return True

        if len(cleaned_parts) == 1:
            filename = cleaned_parts[0]
            return (
                filename.endswith(".html")
                or filename in PUBLIC_ROOT_FILES
                or filename in {"chatbot", "pl", "ro"}
            )

        directory, *remainder = cleaned_parts
        if directory == "chatbot":
            return len(remainder) == 1 and remainder[0] in PUBLIC_CHATBOT_FILES
        allowed_extensions = PUBLIC_DIRECTORY_EXTENSIONS.get(directory)
        return bool(
            allowed_extensions
            and remainder
            and PurePosixPath(remainder[-1]).suffix.lower() in allowed_extensions
        )

    def _json_response(self, status: HTTPStatus, payload: Mapping[str, object]) -> None:
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            LOGGER.info("Client disconnected before the inquiry response was written")


def main() -> None:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(message)s",
    )
    static_root = Path(os.getenv("STATIC_ROOT", Path(__file__).resolve().parent)).resolve()
    port = _integer_environment("PORT", 5000, minimum=1, maximum=65535)

    def handler(*args: object, **kwargs: object) -> AlumCraftRequestHandler:
        return AlumCraftRequestHandler(*args, directory=str(static_root), **kwargs)

    server = ThreadingHTTPServer(("0.0.0.0", port), handler)
    LOGGER.info("Serving AlumCraft on port %s", port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
