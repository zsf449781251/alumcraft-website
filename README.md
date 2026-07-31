# AlumCraft Website

Multilingual B2B website for AlumCraft aluminum sublimation blanks. A small Python server delivers inquiry forms through the company's SMTP account while serving the static pages.

Primary production site: `https://9gygp5h788.coze.site`

## Site Structure

- English: `/`, `applications.html`, `faq.html`, and three product guides
- Romanian: `/ro/`
- Polish: `/pl/`
- Shared assets: `/images/`, `/css/`, and `/js/`
- Standalone rule-based product assistant: `/chatbot/`

No build step or third-party package installation is required.

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

- The three language home pages submit to the same-origin `POST /api/inquiry` endpoint.
- The server validates requests, enforces per-address and global delivery limits, silently absorbs honeypot submissions, then delivers valid inquiries to `znegshifan@yushiglobal.cn`.
- Each browser submission carries an idempotency key. If the connection times out after SMTP accepted the message, retrying the same submission does not send a duplicate email.
- The visitor's address is used only as `Reply-To`. The authenticated company mailbox remains the fixed sender, avoiding sender spoofing and DMARC alignment problems.
- The browser reports success only after the SMTP server accepts the message. Failures remain visible and point the visitor to the direct email link.
- `GET /api/health` reports whether the website process is healthy and whether mail settings are present; it never returns secret values.

### Server environment

| Variable | Required | Default / purpose |
| --- | --- | --- |
| `SMTP_PASSWORD` | Yes | Tencent Exmail client-specific password; store only as a Coze secret |
| `SMTP_USERNAME` | Yes in production | Authenticated full mailbox address; defaults to `INQUIRY_TO_EMAIL` |
| `SMTP_FROM_EMAIL` | Yes in production | Must match the authenticated sender; defaults to `SMTP_USERNAME` |
| `SMTP_HOST` | No | `smtp.exmail.qq.com` |
| `SMTP_PORT` | No | `465` |
| `SMTP_SECURITY` | No | `ssl` |
| `SMTP_FROM_NAME` | No | `AlumCraft Website` |
| `INQUIRY_TO_EMAIL` | No | `znegshifan@yushiglobal.cn` |
| `ALLOWED_ORIGINS` | No | Extra comma-separated origins in addition to the current request host |
| `PORT` | No | `5000`; Coze supplies this in production |

Use `.env.example` only as a key reference. `server.py` reads the process environment and does not load `.env` files. Never commit or paste a real SMTP password into source, documentation, build logs, or chat.

Run the automated checks with:

```powershell
python -m unittest discover -s tests -v
```

## Deployment Checklist

Run the production service with `python3 server.py`. Deploy only the public website files plus `server.py`; do not publish internal planning or client-management files. The HTTP server also denies direct access to non-public repository files as a second layer of protection.

Before changing the primary public host again:

1. Replace the current Coze base URL in canonical, Open Graph, hreflang, `robots.txt`, and `sitemap.xml` entries.
2. Configure the production SMTP secret, check `/api/health`, and verify all three language home pages and their inquiry flows with a real inbox delivery test.
3. Confirm the email and WhatsApp links.
4. Add real social profile URLs before re-enabling the hidden social icons.
5. Replace the short form-purpose notice with an approved privacy policy covering identity, purpose, processors, international transfers, retention, and data-subject rights.

The root `_redirects` file forwards the legacy Netlify hostname to the primary Coze site after the corresponding GitHub change is merged and deployed by Netlify.

## Contact

- Email: `znegshifan@yushiglobal.cn`
- WhatsApp: `+86 153 8620 1892`
