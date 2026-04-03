# AlumCraft AI Customer Service - Startup Guide

## ☁️ Cloud Configuration (SiliconFlow)

This AI chatbot uses **SiliconFlow Cloud API** for 24/7 availability without needing local AI running.

### Configuration Status

| Component | Status | Notes |
|-----------|--------|-------|
| SiliconFlow API | ✅ Configured | Using Qwen2.5-72B model |
| Local Ollama | ❌ Not Required | Using cloud instead |
| Ngrok | ❌ Not Required | Cloud API is always online |

---

## 🚀 Quick Start

### No Setup Required!

Your AI chatbot is already configured to use SiliconFlow cloud API. Just deploy!

### Step 1: Deploy to Netlify

Option A - Deploy chatbot folder as new site:
1. Go to [app.netlify.com](https://app.netlify.com)
2. Click "Add new site" → "Deploy manually"
3. Drag & drop the `chatbot/` folder
4. Done! You'll get a public URL

Option B - Merge into existing site:
1. Copy contents of `chatbot/` to your main website folder
2. Push to GitHub
3. Netlify auto-deploys

---

## 📊 API Usage & Cost

### SiliconFlow Pricing (¥)
| Model | Price | Notes |
|-------|-------|-------|
| Qwen2.5-72B-Instruct | ¥0.1/1K tokens | Best quality |

### Cost Estimate
| Scenario | Tokens/Request | Cost |
|----------|----------------|------|
| Short reply | ~200 tokens | ¥0.02 |
| Medium reply | ~500 tokens | ¥0.05 |
| Long reply | ~1000 tokens | ¥0.10 |

**Example**: 100 customers/day × 10 messages each = 1000 requests × ¥0.05 = **¥50/month**

---

## 🔧 If You Need to Update the API Key

Edit `chatbot/chat.js`:

```javascript
const API_KEY = 'sk-your-new-key-here';
```

---

## 📁 Files Included

| File | Purpose |
|------|---------|
| `index.html` | Chat interface |
| `chat.js` | AI integration logic |
| `style.css` | AlumCraft-matched styling |
| `STARTUP-GUIDE.md` | This file |

---

## 🤖 AI Persona

The chatbot is configured as AlumCraft's professional sales representative:

**Products:**
- Standard CR80 Cards (85.6×54mm)
- Custom shaped cut cards
- Brushed aluminum business card blanks
- Pet tags & luggage tags

**Key Points:**
- Heat press / sublimation applications
- MOQ: 50 pieces
- Sample: 3-5 days
- Made in China, worldwide shipping

**Communication Style:**
- Friendly & professional
- English responses
- Proactively asks customer needs
- Guides to email/WhatsApp for quotes

---

## 📞 Contact Info (Built into Chat)

- Email: zyh370048439@outlook.com
- WhatsApp: +86 15386201892

---

## 💡 Tips for Best Results

1. **Monitor API usage** - Check SiliconFlow dashboard regularly
2. **Add more credits** if running low - ¥50-100 should last months
3. **Test the chatbot** - Make sure responses sound natural
4. **Update system prompt** - Adjust chatbot behavior in `chat.js` if needed

---

## ❓ Troubleshooting

### "API Error" message
- Check your API key is correct in `chat.js`
- Verify SiliconFlow account has credits
- Check SiliconFlow status page

### Slow responses
- Qwen2.5-72B is powerful but slower than smaller models
- Consider upgrading to paid plan for faster responses

### Want to use local AI instead?
Edit `chatbot/chat.js`:
```javascript
const API_KEY = 'your-local-key';
const API_BASE_URL = 'http://localhost:11434/v1';
const MODEL_NAME = 'qwen3.5';
```
Then run Ollama + Ngrok as before.
