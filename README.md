# AlumCraft Website

Static multilingual B2B website for AlumCraft aluminum sublimation blanks.

Primary production site: `https://9gygp5h788.coze.site`

## Site Structure

- English: `/`, `applications.html`, `faq.html`, and three product guides
- Romanian: `/ro/`
- Polish: `/pl/`
- Shared assets: `/images/`, `/css/`, and `/js/`
- Standalone rule-based product assistant: `/chatbot/`

No build step or frontend package installation is required.

## Local Preview

From the repository root:

```powershell
python -m http.server 8080 --bind 127.0.0.1
```

Then open `http://127.0.0.1:8080/`.

The standalone assistant also has a PowerShell-only preview command:

```powershell
powershell -ExecutionPolicy Bypass -File .\chatbot\startup.ps1
```

## Inquiry Form

- On the primary Coze host, submission opens a pre-filled email draft addressed to `znegshifan@yushiglobal.cn`. The page clearly tells the visitor that they must review and send the email.
- If the site is ever served directly from a `*.netlify.app` hostname without the legacy redirect, the form submits to Netlify Forms and treats only an HTTP success response as sent.

This prevents a static host from displaying a false success message when no form backend exists.

## Deployment Checklist

Deploy only the public website files. Do not publish internal planning or client-management files.

Before changing the primary public host again:

1. Replace the current Coze base URL in canonical, Open Graph, hreflang, `robots.txt`, and `sitemap.xml` entries.
2. Verify all three language home pages and their inquiry flows.
3. Confirm the email and WhatsApp links.
4. Add real social profile URLs before re-enabling the hidden social icons.
5. Add an approved privacy policy before collecting inquiries through a server-side form backend.

The root `_redirects` file forwards the legacy Netlify hostname to the primary Coze site after the corresponding GitHub change is merged and deployed by Netlify.

## Contact

- Email: `znegshifan@yushiglobal.cn`
- WhatsApp: `+86 153 8620 1892`
