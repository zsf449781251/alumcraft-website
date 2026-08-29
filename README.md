# AlumCraft Website

Multilingual B2B website for AlumCraft aluminum sublimation blanks. A small Python service serves the static pages and delivers inquiry forms through the company SMTP account.

Primary production site: `https://yushialumcraft.coze.site`

## Site Structure

- English: `/`, `applications.html`, `faq.html`, and three product guides
- Romanian: `/ro/`
- Polish: `/pl/`
- Shared assets: `/images/`, `/css/`, and `/js/`
- Standalone rule-based product assistant: `/chatbot/`

No build step or third-party Python package installation is required.

## Local Preview

From the repository root:

```powershell
$env:PORT = '8080'
python .\server.py
```

Then open `http://127.0.0.1:8080/`.

The standalone assistant also has a PowerShell-only preview command:

```powershell
powershell -ExecutionPolicy Bypass -File .\chatbot\startup.ps1
```

## Inquiry Form

- The English, Romanian, and Polish home pages submit to same-origin `POST /api/inquiry`.
- The service validates the request, applies honeypot and rate-limit checks, and sends through authenticated QQ Mail SMTP.
- The dedicated website mailbox `449781251@qq.com` is the SMTP sender and inquiry recipient. The visitor's address is used only as `Reply-To`; the public company contact email remains unchanged.
- The browser reports success only after the SMTP server accepts the message. A retry uses the same submission ID to reduce duplicate delivery.
- `GET /api/health` reports only service health and whether mail credentials are configured; it never returns secret values.

Required production secret: `SMTP_PASSWORD`, using a QQ Mail client authorization code for `449781251@qq.com` (not the QQ login password). Keep the real value only in Coze production Secrets. The remaining supported settings are documented in `.env.example`.

Run the automated checks with:

```powershell
python -m unittest discover -s tests -v
```

## Deployment Checklist

Deploy only the public website files. Do not publish internal planning or client-management files.

Before changing the primary public host again:

1. Replace the current Coze base URL in canonical, Open Graph, hreflang, `robots.txt`, and `sitemap.xml` entries.
2. Configure the production SMTP secret, verify `/api/health`, then test all three language inquiry flows with one controlled inbox delivery.
3. Confirm the email and WhatsApp links.
4. Add real social profile URLs before re-enabling the hidden social icons.
5. Add an approved privacy policy before collecting inquiries through a server-side form backend.

The root `_redirects` file forwards the legacy Netlify hostname to the primary Coze site after the corresponding GitHub change is merged and deployed by Netlify. The Python server also returns a permanent redirect for GET and HEAD requests that still arrive through the retired Coze hostname, preserving the original path and query string.

## Contact

- Email: `znegshifan@yushiglobal.cn`
- WhatsApp: `+86 153 8620 1892`
