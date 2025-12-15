(function() {
  'use strict';

  function getApiEndpoint() {
    if (window.GRESTA_API_URL) return window.GRESTA_API_URL;
    
    const scriptTag = document.querySelector('script[src*="widget.js"]');
    if (scriptTag && scriptTag.src) {
      const scriptUrl = new URL(scriptTag.src);
      return scriptUrl.origin + '/api/chat/stream';
    }
    
    return '/api/chat/stream';
  }

  function getLogoUrl() {
    const scriptTag = document.querySelector('script[src*="widget.js"]');
    if (scriptTag && scriptTag.src) {
      const scriptUrl = new URL(scriptTag.src);
      return scriptUrl.origin + '/gresta-logo.png';
    }
    return '/gresta-logo.png';
  }

  const WIDGET_CONFIG = {
    get apiEndpoint() { return getApiEndpoint(); },
    get logoUrl() { return getLogoUrl(); },
    primaryColor: '#10b981',
    position: 'bottom-right'
  };

  const styles = `
    #gresta-widget-container * {
      box-sizing: border-box;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
    }

    #gresta-chat-bubble {
      position: fixed;
      bottom: 24px;
      right: 24px;
      width: 60px;
      height: 60px;
      border-radius: 50%;
      background: linear-gradient(135deg, #10b981, #059669);
      box-shadow: 0 4px 20px rgba(16, 185, 129, 0.4);
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 999998;
      transition: transform 0.3s ease, box-shadow 0.3s ease;
      border: none;
    }

    #gresta-chat-bubble:hover {
      transform: scale(1.1);
      box-shadow: 0 6px 30px rgba(16, 185, 129, 0.6);
    }

    #gresta-chat-bubble svg {
      width: 28px;
      height: 28px;
      fill: white;
    }

    #gresta-chat-bubble.open svg.chat-icon {
      display: none;
    }

    #gresta-chat-bubble.open svg.close-icon {
      display: block;
    }

    #gresta-chat-bubble svg.close-icon {
      display: none;
    }

    #gresta-chat-window {
      position: fixed;
      bottom: 100px;
      right: 24px;
      width: 380px;
      height: 550px;
      min-width: 300px;
      min-height: 400px;
      max-width: 600px;
      max-height: calc(100vh - 120px);
      background: rgb(10, 10, 15);
      border-radius: 16px;
      box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(16, 185, 129, 0.2);
      z-index: 999999;
      display: none;
      flex-direction: column;
      overflow: hidden;
      animation: grestaSlideUp 0.3s ease;
      resize: both;
    }

    #gresta-chat-window.open {
      display: flex;
    }

    #gresta-resize-handle {
      position: absolute;
      top: 0;
      left: 0;
      width: 20px;
      height: 20px;
      cursor: nw-resize;
      z-index: 1000000;
    }

    #gresta-resize-handle::before {
      content: '';
      position: absolute;
      top: 4px;
      left: 4px;
      width: 10px;
      height: 10px;
      border-top: 2px solid rgba(16, 185, 129, 0.5);
      border-left: 2px solid rgba(16, 185, 129, 0.5);
      border-radius: 2px 0 0 0;
    }

    #gresta-resize-handle:hover::before {
      border-color: rgba(16, 185, 129, 0.8);
    }

    @keyframes grestaSlideUp {
      from {
        opacity: 0;
        transform: translateY(20px);
      }
      to {
        opacity: 1;
        transform: translateY(0);
      }
    }

    #gresta-chat-header {
      padding: 16px 20px;
      background: linear-gradient(135deg, rgba(16, 185, 129, 0.15), rgba(16, 185, 129, 0.05));
      border-bottom: 1px solid rgba(16, 185, 129, 0.2);
      display: flex;
      align-items: center;
      gap: 12px;
    }

    #gresta-chat-header .avatar {
      width: 40px;
      height: 40px;
      border-radius: 50%;
      background: linear-gradient(135deg, #10b981, #059669);
      display: flex;
      align-items: center;
      justify-content: center;
      border: 2px solid rgba(16, 185, 129, 0.3);
      overflow: hidden;
    }

    #gresta-chat-header .avatar img {
      width: 100%;
      height: 100%;
      object-fit: cover;
    }

    #gresta-chat-header .info h3 {
      margin: 0;
      color: white;
      font-size: 16px;
      font-weight: 600;
    }

    #gresta-chat-header .info p {
      margin: 2px 0 0;
      color: rgba(255, 255, 255, 0.6);
      font-size: 12px;
    }

    #gresta-chat-messages {
      flex: 1;
      overflow-y: auto;
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    #gresta-chat-messages::-webkit-scrollbar {
      width: 6px;
    }

    #gresta-chat-messages::-webkit-scrollbar-track {
      background: rgba(0, 0, 0, 0.1);
    }

    #gresta-chat-messages::-webkit-scrollbar-thumb {
      background: rgba(16, 185, 129, 0.5);
      border-radius: 3px;
    }

    .gresta-message-wrapper {
      display: flex;
      gap: 8px;
      animation: grestaFadeIn 0.3s ease;
    }

    .gresta-message-wrapper.user {
      justify-content: flex-end;
    }

    .gresta-message-wrapper.assistant {
      justify-content: flex-start;
    }

    .gresta-message-avatar {
      width: 28px;
      height: 28px;
      min-width: 28px;
      border-radius: 50%;
      background: linear-gradient(135deg, #10b981, #059669);
      overflow: hidden;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .gresta-message-avatar img {
      width: 100%;
      height: 100%;
      object-fit: cover;
    }

    .gresta-message {
      max-width: 80%;
      padding: 10px 14px;
      border-radius: 12px;
      font-size: 14px;
      line-height: 1.5;
      word-wrap: break-word;
    }

    @keyframes grestaFadeIn {
      from {
        opacity: 0;
        transform: translateY(8px);
      }
      to {
        opacity: 1;
        transform: translateY(0);
      }
    }

    .gresta-message.user {
      background: rgba(16, 185, 129, 0.2);
      border: 1px solid rgba(16, 185, 129, 0.3);
      color: white;
    }

    .gresta-message.assistant {
      background: rgb(30, 30, 45);
      border: 1px solid rgba(16, 185, 129, 0.1);
      color: white;
    }

    .gresta-message.assistant a {
      color: #10b981;
      text-decoration: underline;
    }

    .gresta-message.assistant a:hover {
      color: #34d399;
    }

    .gresta-welcome {
      text-align: center;
      padding: 40px 20px;
      color: rgba(255, 255, 255, 0.7);
    }

    .gresta-welcome h4 {
      margin: 0 0 8px;
      color: rgba(255, 255, 255, 0.9);
      font-size: 18px;
      font-weight: 400;
    }

    .gresta-welcome p {
      margin: 0;
      font-size: 13px;
      color: rgba(255, 255, 255, 0.5);
    }

    .gresta-typing-wrapper {
      display: flex;
      gap: 8px;
      align-items: flex-start;
    }

    .gresta-typing {
      display: flex;
      gap: 4px;
      padding: 12px 16px;
      background: rgb(30, 30, 45);
      border-radius: 12px;
      border: 1px solid rgba(16, 185, 129, 0.1);
    }

    .gresta-typing span {
      width: 8px;
      height: 8px;
      background: rgba(16, 185, 129, 0.6);
      border-radius: 50%;
      animation: grestaBounce 1.4s infinite ease-in-out;
    }

    .gresta-typing span:nth-child(1) { animation-delay: 0s; }
    .gresta-typing span:nth-child(2) { animation-delay: 0.2s; }
    .gresta-typing span:nth-child(3) { animation-delay: 0.4s; }

    @keyframes grestaBounce {
      0%, 60%, 100% { transform: translateY(0); }
      30% { transform: translateY(-6px); }
    }

    #gresta-chat-input-container {
      padding: 12px 16px;
      border-top: 1px solid rgba(16, 185, 129, 0.1);
      background: rgb(20, 20, 30);
    }

    #gresta-chat-input-wrapper {
      display: flex;
      align-items: center;
      background: rgb(30, 30, 45);
      border: 1px solid rgba(16, 185, 129, 0.3);
      border-radius: 25px;
      overflow: hidden;
      transition: border-color 0.2s ease;
    }

    #gresta-chat-input-wrapper:focus-within {
      border-color: rgba(16, 185, 129, 0.6);
      box-shadow: 0 0 0 2px rgba(16, 185, 129, 0.2);
    }

    #gresta-chat-input {
      flex: 1;
      padding: 12px 16px;
      background: transparent;
      border: none;
      color: white;
      font-size: 14px;
      outline: none;
    }

    #gresta-chat-input::placeholder {
      color: rgba(255, 255, 255, 0.4);
    }

    #gresta-send-btn {
      width: 36px;
      height: 36px;
      margin-right: 6px;
      border-radius: 50%;
      background: #10b981;
      border: none;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: background 0.2s ease, opacity 0.2s ease;
    }

    #gresta-send-btn:hover {
      background: #059669;
    }

    #gresta-send-btn:disabled {
      background: #555;
      cursor: not-allowed;
      opacity: 0.5;
    }

    #gresta-send-btn svg {
      width: 16px;
      height: 16px;
      fill: none;
      stroke: white;
      stroke-width: 2;
      stroke-linecap: round;
      stroke-linejoin: round;
    }

    #gresta-powered-by {
      text-align: center;
      padding: 8px;
      font-size: 10px;
      color: rgba(255, 255, 255, 0.3);
      background: rgb(15, 15, 20);
    }

    #gresta-powered-by a {
      color: rgba(16, 185, 129, 0.6);
      text-decoration: none;
    }

    @media (max-width: 480px) {
      #gresta-chat-window {
        width: calc(100vw - 20px);
        height: calc(100vh - 120px);
        right: 10px;
        bottom: 90px;
        max-height: none;
        resize: none;
      }

      #gresta-resize-handle {
        display: none;
      }

      #gresta-chat-bubble {
        width: 54px;
        height: 54px;
        right: 16px;
        bottom: 16px;
      }
    }
  `;

  function injectStyles() {
    const styleEl = document.createElement('style');
    styleEl.id = 'gresta-widget-styles';
    styleEl.textContent = styles;
    document.head.appendChild(styleEl);
  }

  function createWidget() {
    const logoUrl = WIDGET_CONFIG.logoUrl;
    const container = document.createElement('div');
    container.id = 'gresta-widget-container';
    container.innerHTML = `
      <button id="gresta-chat-bubble" aria-label="Open chat">
        <svg class="chat-icon" viewBox="0 0 24 24">
          <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/>
        </svg>
        <svg class="close-icon" viewBox="0 0 24 24">
          <path d="M18 6L6 18M6 6l12 12" stroke="white" stroke-width="2" stroke-linecap="round"/>
        </svg>
      </button>
      <div id="gresta-chat-window">
        <div id="gresta-resize-handle" title="Drag to resize"></div>
        <div id="gresta-chat-header">
          <div class="avatar"><img src="${logoUrl}" alt="GRESTA" /></div>
          <div class="info">
            <h3>GRESTA</h3>
            <p>Your GREST Assistant</p>
          </div>
        </div>
        <div id="gresta-chat-messages">
          <div class="gresta-welcome">
            <h4>Hi, I'm GRESTA</h4>
            <p>Your shopping assistant for GREST. How can I help you today?</p>
          </div>
        </div>
        <div id="gresta-chat-input-container">
          <div id="gresta-chat-input-wrapper">
            <input type="text" id="gresta-chat-input" placeholder="Ask me anything about GREST products..." />
            <button id="gresta-send-btn" disabled aria-label="Send message">
              <svg viewBox="0 0 24 24">
                <path d="M14 5l7 7m0 0l-7 7m7-7H3"/>
              </svg>
            </button>
          </div>
        </div>
        <div id="gresta-powered-by">
          Powered by <a href="https://grest.in" target="_blank">GREST</a>
        </div>
      </div>
    `;
    document.body.appendChild(container);
  }

  let sessionId = '';
  let messages = [];
  let isLoading = false;

  const STORAGE_KEY_SESSION = 'gresta_session_id';
  const STORAGE_KEY_MESSAGES = 'gresta_messages';

  function generateSessionId() {
    return 'widget_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
  }

  function getOrCreateSessionId() {
    try {
      const stored = localStorage.getItem(STORAGE_KEY_SESSION);
      if (stored) {
        return stored;
      }
      const newId = generateSessionId();
      localStorage.setItem(STORAGE_KEY_SESSION, newId);
      return newId;
    } catch (e) {
      return generateSessionId();
    }
  }

  function saveMessagesToStorage() {
    try {
      localStorage.setItem(STORAGE_KEY_MESSAGES, JSON.stringify(messages.slice(-50)));
    } catch (e) {}
  }

  function loadMessagesFromStorage() {
    try {
      const stored = localStorage.getItem(STORAGE_KEY_MESSAGES);
      if (stored) {
        return JSON.parse(stored);
      }
    } catch (e) {}
    return [];
  }

  function restoreMessages(storedMessages) {
    if (!storedMessages || storedMessages.length === 0) return;
    
    const messagesContainer = document.getElementById('gresta-chat-messages');
    const welcome = messagesContainer.querySelector('.gresta-welcome');
    if (welcome) welcome.remove();

    for (const msg of storedMessages) {
      const wrapperEl = document.createElement('div');
      wrapperEl.className = `gresta-message-wrapper ${msg.role}`;
      
      if (msg.role === 'assistant') {
        const avatarEl = document.createElement('div');
        avatarEl.className = 'gresta-message-avatar';
        const avatarImg = document.createElement('img');
        avatarImg.src = WIDGET_CONFIG.logoUrl;
        avatarImg.alt = 'GRESTA';
        avatarEl.appendChild(avatarImg);
        wrapperEl.appendChild(avatarEl);
      }
      
      const msgEl = document.createElement('div');
      msgEl.className = `gresta-message ${msg.role}`;
      msgEl.appendChild(createSafeContent(msg.content));
      wrapperEl.appendChild(msgEl);
      
      messagesContainer.appendChild(wrapperEl);
    }
    
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }

  function toggleChat() {
    const bubble = document.getElementById('gresta-chat-bubble');
    const window = document.getElementById('gresta-chat-window');
    const isOpen = window.classList.contains('open');
    
    if (isOpen) {
      window.classList.remove('open');
      bubble.classList.remove('open');
    } else {
      window.classList.add('open');
      bubble.classList.add('open');
      document.getElementById('gresta-chat-input').focus();
    }
  }

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  function createSafeContent(text) {
    const container = document.createDocumentFragment();
    const linkRegex = /\[([^\]]+)\]\(([^)]+)\)/g;
    let lastIndex = 0;
    let match;

    while ((match = linkRegex.exec(text)) !== null) {
      if (match.index > lastIndex) {
        container.appendChild(document.createTextNode(text.slice(lastIndex, match.index)));
      }
      
      const linkText = match[1];
      const url = match[2];
      
      if (url.startsWith('http://') || url.startsWith('https://') || url.startsWith('/')) {
        const anchor = document.createElement('a');
        anchor.href = url;
        anchor.target = '_blank';
        anchor.rel = 'noopener noreferrer';
        anchor.textContent = linkText;
        container.appendChild(anchor);
      } else {
        container.appendChild(document.createTextNode(match[0]));
      }
      
      lastIndex = match.index + match[0].length;
    }

    if (lastIndex < text.length) {
      container.appendChild(document.createTextNode(text.slice(lastIndex)));
    }

    return container;
  }

  function addMessage(role, content) {
    const messagesContainer = document.getElementById('gresta-chat-messages');
    const welcome = messagesContainer.querySelector('.gresta-welcome');
    if (welcome) welcome.remove();

    const wrapperEl = document.createElement('div');
    wrapperEl.className = `gresta-message-wrapper ${role}`;
    
    if (role === 'assistant') {
      const avatarEl = document.createElement('div');
      avatarEl.className = 'gresta-message-avatar';
      const avatarImg = document.createElement('img');
      avatarImg.src = WIDGET_CONFIG.logoUrl;
      avatarImg.alt = 'GRESTA';
      avatarEl.appendChild(avatarImg);
      wrapperEl.appendChild(avatarEl);
    }
    
    const msgEl = document.createElement('div');
    msgEl.className = `gresta-message ${role}`;
    msgEl.appendChild(createSafeContent(content));
    wrapperEl.appendChild(msgEl);
    
    messagesContainer.appendChild(wrapperEl);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    
    return msgEl;
  }

  function updateMessageContent(msgEl, content) {
    msgEl.innerHTML = '';
    msgEl.appendChild(createSafeContent(content));
  }

  function showTyping() {
    const messagesContainer = document.getElementById('gresta-chat-messages');
    const typingWrapper = document.createElement('div');
    typingWrapper.className = 'gresta-typing-wrapper';
    typingWrapper.id = 'gresta-typing-indicator';
    
    const avatarEl = document.createElement('div');
    avatarEl.className = 'gresta-message-avatar';
    const avatarImg = document.createElement('img');
    avatarImg.src = WIDGET_CONFIG.logoUrl;
    avatarImg.alt = 'GRESTA';
    avatarEl.appendChild(avatarImg);
    typingWrapper.appendChild(avatarEl);
    
    const typingEl = document.createElement('div');
    typingEl.className = 'gresta-typing';
    typingEl.innerHTML = '<span></span><span></span><span></span>';
    typingWrapper.appendChild(typingEl);
    
    messagesContainer.appendChild(typingWrapper);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }

  function hideTyping() {
    const typing = document.getElementById('gresta-typing-indicator');
    if (typing) typing.remove();
  }

  function updateSendButton() {
    const input = document.getElementById('gresta-chat-input');
    const btn = document.getElementById('gresta-send-btn');
    btn.disabled = !input.value.trim() || isLoading;
  }

  function initResize() {
    const resizeHandle = document.getElementById('gresta-resize-handle');
    const chatWindow = document.getElementById('gresta-chat-window');
    
    if (!resizeHandle || !chatWindow) return;
    
    let isResizing = false;
    let startX, startY, startWidth, startHeight, startRight, startBottom;
    
    resizeHandle.addEventListener('mousedown', (e) => {
      isResizing = true;
      startX = e.clientX;
      startY = e.clientY;
      startWidth = chatWindow.offsetWidth;
      startHeight = chatWindow.offsetHeight;
      
      const rect = chatWindow.getBoundingClientRect();
      startRight = window.innerWidth - rect.right;
      startBottom = window.innerHeight - rect.bottom;
      
      document.body.style.userSelect = 'none';
      document.body.style.cursor = 'nw-resize';
      
      e.preventDefault();
    });
    
    document.addEventListener('mousemove', (e) => {
      if (!isResizing) return;
      
      const deltaX = startX - e.clientX;
      const deltaY = startY - e.clientY;
      
      const newWidth = Math.max(300, Math.min(600, startWidth + deltaX));
      const newHeight = Math.max(400, Math.min(window.innerHeight - 120, startHeight + deltaY));
      
      chatWindow.style.width = newWidth + 'px';
      chatWindow.style.height = newHeight + 'px';
    });
    
    document.addEventListener('mouseup', () => {
      if (isResizing) {
        isResizing = false;
        document.body.style.userSelect = '';
        document.body.style.cursor = '';
      }
    });
    
    resizeHandle.addEventListener('touchstart', (e) => {
      const touch = e.touches[0];
      isResizing = true;
      startX = touch.clientX;
      startY = touch.clientY;
      startWidth = chatWindow.offsetWidth;
      startHeight = chatWindow.offsetHeight;
      e.preventDefault();
    });
    
    document.addEventListener('touchmove', (e) => {
      if (!isResizing) return;
      const touch = e.touches[0];
      
      const deltaX = startX - touch.clientX;
      const deltaY = startY - touch.clientY;
      
      const newWidth = Math.max(300, Math.min(600, startWidth + deltaX));
      const newHeight = Math.max(400, Math.min(window.innerHeight - 120, startHeight + deltaY));
      
      chatWindow.style.width = newWidth + 'px';
      chatWindow.style.height = newHeight + 'px';
    });
    
    document.addEventListener('touchend', () => {
      isResizing = false;
    });
  }

  async function sendMessage() {
    const input = document.getElementById('gresta-chat-input');
    const content = input.value.trim();
    
    if (!content || isLoading) return;

    isLoading = true;
    input.value = '';
    updateSendButton();

    addMessage('user', content);
    messages.push({ role: 'user', content });
    saveMessagesToStorage();

    showTyping();

    try {
      const response = await fetch(WIDGET_CONFIG.apiEndpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: content,
          session_id: sessionId,
          conversation_history: messages.slice(-10).map(m => ({ role: m.role, content: m.content })),
          user: null
        }),
      });

      if (!response.ok) {
        throw new Error('Network response was not ok');
      }

      hideTyping();

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let assistantContent = '';
      let msgEl = null;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            if (data === '[DONE]') {
              continue;
            }

            try {
              const parsed = JSON.parse(data);
              if (parsed.content) {
                assistantContent += parsed.content;
                if (!msgEl) {
                  msgEl = addMessage('assistant', assistantContent);
                } else {
                  updateMessageContent(msgEl, assistantContent);
                }
                const messagesContainer = document.getElementById('gresta-chat-messages');
                messagesContainer.scrollTop = messagesContainer.scrollHeight;
              }
            } catch (e) {}
          }
        }
      }

      if (assistantContent) {
        messages.push({ role: 'assistant', content: assistantContent });
        saveMessagesToStorage();
      }

    } catch (error) {
      console.error('Chat error:', error);
      hideTyping();
      addMessage('assistant', 'Sorry, I encountered an error. Please try again.');
    }

    isLoading = false;
    updateSendButton();
  }

  function init() {
    if (document.getElementById('gresta-widget-container')) return;

    injectStyles();
    createWidget();
    initResize();

    sessionId = getOrCreateSessionId();
    messages = loadMessagesFromStorage();
    restoreMessages(messages);

    const bubble = document.getElementById('gresta-chat-bubble');
    bubble.addEventListener('click', toggleChat);

    const input = document.getElementById('gresta-chat-input');
    input.addEventListener('input', updateSendButton);
    input.addEventListener('keypress', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    });

    const sendBtn = document.getElementById('gresta-send-btn');
    sendBtn.addEventListener('click', sendMessage);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
