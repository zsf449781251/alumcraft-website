/**
 * AlumCraft AI Chatbot - Sam's Customer Service
 * Powered by SiliconFlow Cloud API (Qwen2.5-72B)
 */

// =========================================
// CONFIGURATION - SiliconFlow Cloud API
// =========================================

// SiliconFlow API Key (user provided)
const API_KEY = 'sk-qcsxzrkpjuakiqctkplmuyfuhnzmxmikaemguzswokbjeerx';

// SiliconFlow API endpoint
const API_BASE_URL = 'https://api.siliconflow.cn/v1';

// Model: Qwen2.5-72B-Instruct (best quality for customer service)
const MODEL_NAME = 'Qwen/Qwen2.5-72B-Instruct';

// System prompt for AI persona - Sam (Professional, Serious, Chinese Manufacturer)
const SYSTEM_PROMPT = `You are Sam, the professional sales representative of AlumCraft — a professional Chinese manufacturer specializing in high-quality sublimation aluminum blanks for the global sublimation industry.

PERSONALITY:
- Professional, knowledgeable, and reliable
- Serious but approachable
- Speaks with authority and confidence
- No small talk, always on-point
- Represents a legitimate factory operation

ABOUT ALUMCRAFT:
- Established Chinese manufacturer based in China
- Factory-direct pricing with no middleman markup
- Professional production line with quality control
- 5+ years experience in sublimation aluminum products
- Trusted by businesses worldwide — including repeat buyers ordering 250,000+ pieces
- Worldwide shipping available

PRODUCT RANGE:

1. Standard CR80 Cards (86×54mm)
   - Our most popular size
   - Thickness: 0.55mm (most popular)
   - Also available: 0.22mm (thin, prone to deformation — handle with care)
   - White pearlescent aluminum with polyester coating
   - Proven quality: single orders up to 273,500 pieces completed
   - MOQ: 500 pieces for standard sizes

2. Oversized Cards (115×54mm)
   - Extended format for specialized applications
   - Same thickness: 0.55mm
   - Popular for promotional items and awards
   - MOQ: 500 pieces

3. Round Blanks (70mm diameter)
   - Perfect for buttons, medallions, keychains
   - Thickness: 0.55mm
   - MOQ: 500 pieces

4. Custom Die-Cut Shapes
   - ANY shape from your vector files
   - Accept formats: DXF, AI, CDR, EPS, PDF (vector preferred)
   - Mold making required: starts from ¥3,000
   - Complex curves cost more (over ¥4,000 for curved molds)
   - MOQ: 50,000 pieces minimum
   - Area factor affects pricing: larger shapes = higher mold cost

MATERIAL SPECIFICATIONS:
- Material: Pearlescent white aluminum (sublimation grade)
- Surface: Premium polyester coating optimized for sublimation
- Thickness options: 0.22mm, 0.55mm (standard)
- Compatibility: Standard heat press (180-200°C, 40-60 seconds recommended)

PRODUCTION CAPABILITIES:
- Precise stamping/cutting for clean edges
- Quality control: front surface burr-free
- Note: Minor back-side burrs may occur (unavoidable, minimized through tool polishing)
- Sample production: 3-5 business days
- Bulk production: 7-15 business days
- Bulk capacity: Single orders up to 273,500+ pieces completed

PRICING STRUCTURE:
- Standard sizes: Volume pricing available — send inquiry for quote
- Custom shapes: Mold cost (¥3,000-4,000+) + unit price
- Unit price example: Large orders at ~¥0.39/piece (for 200,000+ pieces)
- NOTE: We do NOT negotiate pricing in chat. All quotes provided upon formal inquiry.

MOQ SUMMARY:
- Standard sizes (86×54mm, 115×54mm, 70mm round): 500 pieces minimum
- Custom shapes: 50,000 pieces minimum

SHIPPING:
- Ships from China to worldwide destinations
- Express shipping (3-7 days) available
- Sea freight for large orders
- Tracking provided for all shipments

COMMUNICATION STYLE:
- Always respond in English
- Professional tone, no slang, no emojis
- Concise and informative responses
- Ask qualification questions (quantity, size, shape, timeline)
- Recommend suitable products based on customer needs
- Always guide serious inquiries to formal contact

IMPORTANT RULES:
1. Do NOT make up specific pricing — always redirect to inquiry
2. Do NOT promise exact delivery dates — give general estimates only
3. Do NOT use casual language or emojis
4. Do NOT offer discounts unless officially authorized
5. If unsure about technical specs, suggest direct consultation
6. Always include contact information for serious inquiries
7. Be honest about limitations: 0.22mm thickness prone to deformation during stamping
8. Explain mold costs clearly for custom shapes

CONTACT INFO (always ready to share):
- Email: zyh370048439@outlook.com
- WhatsApp: +86 15386201892
- Website: https://magenta-fenglisu-70127f.netlify.app/

QUALIFICATION QUESTIONS TO ASK:
- What size do you need? (Standard 86×54mm or custom?)
- What quantity are you looking for?
- Do you have a vector file for custom shapes?
- What is your timeline?
- What thickness do you prefer? (0.22mm or 0.55mm)

When a customer seems serious (mentioning quantities, project details, timeline), warmly but professionally encourage them to send a formal inquiry with their requirements.`;

// =========================================
// State
// =========================================

let conversationHistory = [
  {
    role: 'system',
    content: SYSTEM_PROMPT
  }
];

let isGenerating = false;

// =========================================
// DOM Elements
// =========================================

const chatMessages = document.getElementById('chatMessages');
const userInput = document.getElementById('userInput');
const sendBtn = document.getElementById('sendBtn');
const typingIndicator = document.getElementById('typingIndicator');

// =========================================
// Core Functions
// =========================================

function addMessage(content, isUser = false) {
  const messageDiv = document.createElement('div');
  messageDiv.className = `message ${isUser ? 'user-message' : 'bot-message'}`;

  const avatarSvg = isUser
    ? `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
         <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
         <circle cx="12" cy="7" r="4"/>
       </svg>`
    : `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
         <path d="M12 2L2 7l10 5 10-5-10-5z"/>
         <path d="M2 17l10 5 10-5"/>
         <path d="M2 12l10 5 10-5"/>
       </svg>`;

  messageDiv.innerHTML = `
    <div class="message-avatar">${avatarSvg}</div>
    <div class="message-content">
      <div class="message-text">${formatMessage(content)}</div>
    </div>
  `;

  chatMessages.appendChild(messageDiv);
  scrollToBottom();
}

function addError(message) {
  const errorDiv = document.createElement('div');
  errorDiv.className = 'message bot-message';
  errorDiv.innerHTML = `
    <div class="message-avatar">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M12 2L2 7l10 5 10-5-10-5z"/>
        <path d="M2 17l10 5 10-5"/>
        <path d="M2 12l10 5 10-5"/>
      </svg>
    </div>
    <div class="message-content">
      <div class="error-message">
        <strong>Oops! Connection Error</strong><br><br>
        ${message}
        <br><br>
        <strong>Contact us directly:</strong><br>
        📧 <a href="mailto:zyh370048439@outlook.com">zyh370048439@outlook.com</a><br>
        📱 <a href="https://wa.me/+8615386201892" target="_blank">WhatsApp</a>
      </div>
    </div>
  `;
  chatMessages.appendChild(errorDiv);
  scrollToBottom();
}

function formatMessage(text) {
  // Convert newlines to <br>
  let formatted = text.replace(/\n/g, '<br>');
  
  // Make URLs clickable
  formatted = formatted.replace(
    /(https?:\/\/[^\s<]+)/g,
    '<a href="$1" target="_blank" style="color: var(--metal-mid); text-decoration: underline;">$1</a>'
  );
  
  return `<p>${formatted}</p>`;
}

function scrollToBottom() {
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function showTyping() {
  typingIndicator.style.display = 'block';
  scrollToBottom();
}

function hideTyping() {
  typingIndicator.style.display = 'none';
}

function setInputEnabled(enabled) {
  userInput.disabled = !enabled;
  sendBtn.disabled = !enabled;
  isGenerating = !enabled;
}

// =========================================
// Message Sending
// =========================================

async function sendMessage() {
  const message = userInput.value.trim();
  if (!message || isGenerating) return;

  // Add user message
  addMessage(message, true);
  
  // Clear input
  userInput.value = '';
  userInput.style.height = 'auto';
  
  // Add to history
  conversationHistory.push({
    role: 'user',
    content: message
  });
  
  // Show typing
  showTyping();
  setInputEnabled(false);
  
  try {
    const response = await generateResponse();
    
    if (response.error) {
      addError(response.error);
    } else {
      addMessage(response.content);
      conversationHistory.push({
        role: 'assistant',
        content: response.content
      });
    }
  } catch (error) {
    console.error('Error:', error);
    addError('Unable to connect to the AI service. Please try again later or contact us directly.');
  } finally {
    hideTyping();
    setInputEnabled(true);
    userInput.focus();
  }
}

async function generateResponse() {
  // Build messages for API
  const messages = conversationHistory.map(msg => ({
    role: msg.role === 'user' ? 'user' : 'assistant',
    content: msg.content
  }));
  
  // Call SiliconFlow API
  try {
    const response = await fetch(`${API_BASE_URL}/chat/completions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${API_KEY}`
      },
      body: JSON.stringify({
        model: MODEL_NAME,
        messages: messages,
        stream: false,
        temperature: 0.7,
        max_tokens: 1500
      })
    });
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(`API Error ${response.status}: ${errorData.error?.message || response.statusText}`);
    }
    
    const data = await response.json();
    return { content: data.choices[0].message.content };
    
  } catch (error) {
    return { 
      error: `Unable to connect to AI service. Please try again later.\n\nError: ${error.message}\n\nOr contact us directly:\nEmail: zyh370048439@outlook.com\nWhatsApp: +86 15386201892` 
    };
  }
}

function sendQuickMessage(message) {
  userInput.value = message;
  sendMessage();
}

// =========================================
// Input Handling
// =========================================

function handleKeyDown(event) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    sendMessage();
  }
}

function autoResize(textarea) {
  textarea.style.height = 'auto';
  textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
}

function clearChat() {
  if (confirm('Clear all messages and start fresh?')) {
    chatMessages.innerHTML = '';
    conversationHistory = [
      {
        role: 'system',
        content: SYSTEM_PROMPT
      }
    ];
    
    // Re-add welcome message
    const welcomeDiv = document.createElement('div');
    welcomeDiv.className = 'message bot-message';
    welcomeDiv.innerHTML = `
      <div class="message-avatar">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M12 2L2 7l10 5 10-5-10-5z"/>
          <path d="M2 17l10 5 10-5"/>
          <path d="M2 12l10 5 10-5"/>
        </svg>
      </div>
      <div class="message-content">
          <div class="message-text">
          <p>Chat reset. How may I assist you?</p>
        </div>
          <div class="quick-actions">
          <button onclick="sendQuickMessage('What sizes and thickness do you offer?')">View Products</button>
          <button onclick="sendQuickMessage('What is the MOQ for standard size 86x54mm?')">Standard MOQ</button>
          <button onclick="sendQuickMessage('I need a quote for 50,000 custom shaped pieces')">Custom Quote</button>
        </div>
      </div>
    `;
    chatMessages.appendChild(welcomeDiv);
  }
}

// =========================================
// Initialization
// =========================================

document.addEventListener('DOMContentLoaded', () => {
  userInput.focus();
  
  // Log configuration status
  console.log('AlumCraft AI Chatbot initialized');
  console.log('API: SiliconFlow Cloud');
  console.log('Model:', MODEL_NAME);
});
