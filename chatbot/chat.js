/**
 * AlumCraft product assistant.
 * Static, no external API key exposed in the browser.
 */

const CONTACT_INFO = 'Email: znegshifan@yushiglobal.cn\nWhatsApp: +86 153 8620 1892';

let isGenerating = false;

const chatMessages = document.getElementById('chatMessages');
const userInput = document.getElementById('userInput');
const sendBtn = document.getElementById('sendBtn');
const typingIndicator = document.getElementById('typingIndicator');

function escapeHTML(value) {
  return value.replace(/[&<>'"]/g, char => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    "'": '&#39;',
    '"': '&quot;'
  }[char]));
}

function formatMessage(text) {
  return `<p>${escapeHTML(text).replace(/\n/g, '<br>')}</p>`;
}

function scrollToBottom() {
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

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
  addMessage(`${message}\n\n${CONTACT_INFO}`);
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

function buildLocalResponse(message) {
  const text = message.toLowerCase();

  if (text.includes('moq') || text.includes('minimum')) {
    return 'Minimum order requirements are evaluated for each project based on the confirmed size, shape, thickness, tooling, coating or surface finish, quantity, packaging, and destination.\n\nSend your drawing or specifications for a project-based written quotation; the written quotation governs.\n' + CONTACT_INFO;
  }

  if (text.includes('thick') || text.includes('0.55') || text.includes('0.30') || text.includes('0.22')) {
    return 'Common thickness references include 0.22mm, 0.30mm, 0.40mm, 0.50mm, and 0.55mm. A 0.55mm blank feels more rigid for cards and badges, while thinner options provide more flexibility. Confirm the required thickness in the written quotation.';
  }

  if (text.includes('sample')) {
    return 'Sample options can be discussed after we review your specifications. Availability, cost, preparation time, shipping, and any order credit depend on the product, customization, quantity, packaging, and destination and are confirmed in the written quotation.\n\nPlease email your required size, shape, thickness, finish, quantity, packaging, and destination to znegshifan@yushiglobal.cn.';
  }

  if (text.includes('custom') || text.includes('shape') || text.includes('die')) {
    return 'Yes, AlumCraft can review custom aluminum blanks from vector files such as DXF, AI, CDR, EPS, or PDF. Size, shape, thickness, coating, color, holes, corners, surface finish, and packaging can be customized. Tooling, minimum quantity, sample options, timing, and price are assessed for the project and confirmed in writing.';
  }

  if (text.includes('price') || text.includes('quote') || text.includes('cost')) {
    return 'To quote accurately, we need size, shape, thickness, coating or surface requirement, holes or corners, quantity, packaging, and destination.\n\nSend those details to znegshifan@yushiglobal.cn. Price, minimum quantity, sample options, production timing, and shipping are subject to the written quotation.';
  }

  if (text.includes('ship') || text.includes('delivery') || text.includes('lead time')) {
    return 'International shipping options can be evaluated from China based on the product, quantity, packaging, destination, and requested timing. Sample and production schedules, transport methods, freight terms, and tracking arrangements are confirmed in the written quotation.';
  }

  return 'Thanks for your message. For the fastest help, please share your product type, size, thickness, quantity, destination country, and timeline.\n\n' + CONTACT_INFO;
}

async function sendMessage() {
  const message = userInput.value.trim();
  if (!message || isGenerating) return;

  addMessage(message, true);
  userInput.value = '';
  userInput.style.height = 'auto';
  showTyping();
  setInputEnabled(false);

  try {
    await new Promise(resolve => window.setTimeout(resolve, 250));
    addMessage(buildLocalResponse(message));
  } catch (error) {
    addError('Unable to prepare a response. Please contact us directly.');
  } finally {
    hideTyping();
    setInputEnabled(true);
    userInput.focus();
  }
}

function sendQuickMessage(message) {
  userInput.value = message;
  sendMessage();
}

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
  if (!confirm('Clear all messages and start fresh?')) return;

  chatMessages.innerHTML = '';
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
        <button onclick="sendQuickMessage('I need a quote for custom shaped aluminum blanks')">Custom Quote</button>
      </div>
    </div>
  `;
  chatMessages.appendChild(welcomeDiv);
}

document.addEventListener('DOMContentLoaded', () => {
  userInput.focus();
});
