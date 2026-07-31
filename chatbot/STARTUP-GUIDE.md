# AlumCraft Product Assistant

The chatbot is a static, rule-based product assistant. All replies are generated in `chat.js` in the visitor's browser.

It does not need Ollama, ngrok, an `API_BASE_URL`, an API key, or a backend service.

## Local Preview on Windows

From the repository root, run:

```powershell
powershell -ExecutionPolicy Bypass -File .\chatbot\startup.ps1
```

The script serves only the `chatbot` folder at `http://127.0.0.1:8080/` and opens it in the default browser. Press `Ctrl+C` in PowerShell to stop the preview server.

Optional arguments:

```powershell
# Use another port if 8080 is busy
powershell -ExecutionPolicy Bypass -File .\chatbot\startup.ps1 -Port 8081

# Start the server without opening a browser
powershell -ExecutionPolicy Bypass -File .\chatbot\startup.ps1 -NoBrowser
```

The preview server is implemented in PowerShell and does not require Python, Node.js, or any package installation. It binds to `127.0.0.1`, so it is available only on the local computer.

## What It Answers

- MOQ for standard and custom products
- Thickness options
- Sample lead time
- Custom die-cut requirements
- Quote requirements
- Shipping and lead-time basics

All serious inquiries are handed off to:

- Email: znegshifan@yushiglobal.cn
- WhatsApp: +86 153 8620 1892

## Static Deployment

Deploy `index.html`, `style.css`, and `chat.js` together under the same public directory, such as `/chatbot/`. They use relative paths and need no build command, environment variables, server process, or secret configuration.

After deployment, verify that:

1. The assistant page loads over HTTPS.
2. `style.css` and `chat.js` return HTTP 200.
3. A quick-action button produces a local reply.
4. The email and WhatsApp contact links open correctly.

If real generative AI is added later, call the provider only from a backend or serverless function and keep API keys in server-side environment variables.
