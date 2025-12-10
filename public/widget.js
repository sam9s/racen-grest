(function() {
  'use strict';

  function getApiEndpoint() {
    if (window.RACEN_API_URL) return window.RACEN_API_URL;
    
    const scriptTag = document.querySelector('script[src*="widget.js"]');
    if (scriptTag && scriptTag.src) {
      const scriptUrl = new URL(scriptTag.src);
      return scriptUrl.origin + '/api/chat/stream';
    }
    
    return '/api/chat/stream';
  }

  const WIDGET_CONFIG = {
    get apiEndpoint() { return getApiEndpoint(); },
    primaryColor: '#03a9f4',
    position: 'bottom-right'
  };

  const styles = `
    #racen-widget-container * {
      box-sizing: border-box;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
    }

    #racen-chat-bubble {
      position: fixed;
      bottom: 24px;
      right: 24px;
      width: 60px;
      height: 60px;
      border-radius: 50%;
      background: linear-gradient(135deg, #03a9f4, #0288d1);
      box-shadow: 0 4px 20px rgba(3, 169, 244, 0.4);
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 999998;
      transition: transform 0.3s ease, box-shadow 0.3s ease;
      border: none;
    }

    #racen-chat-bubble:hover {
      transform: scale(1.1);
      box-shadow: 0 6px 30px rgba(3, 169, 244, 0.6);
    }

    #racen-chat-bubble svg {
      width: 28px;
      height: 28px;
      fill: white;
    }

    #racen-chat-bubble.open svg.chat-icon {
      display: none;
    }

    #racen-chat-bubble.open svg.close-icon {
      display: block;
    }

    #racen-chat-bubble svg.close-icon {
      display: none;
    }

    #racen-chat-window {
      position: fixed;
      bottom: 100px;
      right: 24px;
      width: 380px;
      height: 550px;
      max-height: calc(100vh - 140px);
      background: rgb(10, 10, 15);
      border-radius: 16px;
      box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(3, 169, 244, 0.2);
      z-index: 999999;
      display: none;
      flex-direction: column;
      overflow: hidden;
      animation: racenSlideUp 0.3s ease;
    }

    #racen-chat-window.open {
      display: flex;
    }

    @keyframes racenSlideUp {
      from {
        opacity: 0;
        transform: translateY(20px);
      }
      to {
        opacity: 1;
        transform: translateY(0);
      }
    }

    #racen-chat-header {
      padding: 16px 20px;
      background: linear-gradient(135deg, rgba(3, 169, 244, 0.15), rgba(3, 169, 244, 0.05));
      border-bottom: 1px solid rgba(3, 169, 244, 0.2);
      display: flex;
      align-items: center;
      gap: 12px;
    }

    #racen-chat-header .avatar {
      width: 40px;
      height: 40px;
      border-radius: 50%;
      background: linear-gradient(135deg, #03a9f4, #0288d1);
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: bold;
      color: white;
      font-size: 16px;
      border: 2px solid rgba(3, 169, 244, 0.3);
    }

    #racen-chat-header .info h3 {
      margin: 0;
      color: white;
      font-size: 16px;
      font-weight: 600;
    }

    #racen-chat-header .info p {
      margin: 2px 0 0;
      color: rgba(255, 255, 255, 0.6);
      font-size: 12px;
    }

    #racen-chat-messages {
      flex: 1;
      overflow-y: auto;
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    #racen-chat-messages::-webkit-scrollbar {
      width: 6px;
    }

    #racen-chat-messages::-webkit-scrollbar-track {
      background: rgba(0, 0, 0, 0.1);
    }

    #racen-chat-messages::-webkit-scrollbar-thumb {
      background: rgba(3, 169, 244, 0.5);
      border-radius: 3px;
    }

    .racen-message {
      max-width: 85%;
      padding: 10px 14px;
      border-radius: 12px;
      font-size: 14px;
      line-height: 1.5;
      animation: racenFadeIn 0.3s ease;
      word-wrap: break-word;
    }

    @keyframes racenFadeIn {
      from {
        opacity: 0;
        transform: translateY(8px);
      }
      to {
        opacity: 1;
        transform: translateY(0);
      }
    }

    .racen-message.user {
      align-self: flex-end;
      background: rgba(3, 169, 244, 0.2);
      border: 1px solid rgba(3, 169, 244, 0.3);
      color: white;
    }

    .racen-message.assistant {
      align-self: flex-start;
      background: rgb(30, 30, 45);
      border: 1px solid rgba(3, 169, 244, 0.1);
      color: white;
    }

    .racen-message.assistant a {
      color: #03a9f4;
      text-decoration: underline;
    }

    .racen-message.assistant a:hover {
      color: #4fc3f7;
    }

    .racen-welcome {
      text-align: center;
      padding: 40px 20px;
      color: rgba(255, 255, 255, 0.7);
    }

    .racen-welcome h4 {
      margin: 0 0 8px;
      color: rgba(255, 255, 255, 0.9);
      font-size: 18px;
      font-weight: 400;
    }

    .racen-welcome p {
      margin: 0;
      font-size: 13px;
      color: rgba(255, 255, 255, 0.5);
    }

    .racen-typing {
      display: flex;
      gap: 4px;
      padding: 12px 16px;
      align-self: flex-start;
    }

    .racen-typing span {
      width: 8px;
      height: 8px;
      background: rgba(3, 169, 244, 0.6);
      border-radius: 50%;
      animation: racenBounce 1.4s infinite ease-in-out;
    }

    .racen-typing span:nth-child(1) { animation-delay: 0s; }
    .racen-typing span:nth-child(2) { animation-delay: 0.2s; }
    .racen-typing span:nth-child(3) { animation-delay: 0.4s; }

    @keyframes racenBounce {
      0%, 60%, 100% { transform: translateY(0); }
      30% { transform: translateY(-6px); }
    }

    #racen-chat-input-container {
      padding: 12px 16px;
      border-top: 1px solid rgba(3, 169, 244, 0.1);
      background: rgb(20, 20, 30);
    }

    #racen-chat-input-wrapper {
      display: flex;
      align-items: center;
      background: rgb(30, 30, 45);
      border: 1px solid rgba(3, 169, 244, 0.3);
      border-radius: 25px;
      overflow: hidden;
      transition: border-color 0.2s ease;
    }

    #racen-chat-input-wrapper:focus-within {
      border-color: rgba(3, 169, 244, 0.6);
      box-shadow: 0 0 0 2px rgba(3, 169, 244, 0.2);
    }

    #racen-chat-input {
      flex: 1;
      padding: 12px 16px;
      background: transparent;
      border: none;
      color: white;
      font-size: 14px;
      outline: none;
    }

    #racen-chat-input::placeholder {
      color: rgba(255, 255, 255, 0.4);
    }

    #racen-send-btn {
      width: 36px;
      height: 36px;
      margin-right: 6px;
      border-radius: 50%;
      background: #03a9f4;
      border: none;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: background 0.2s ease, opacity 0.2s ease;
    }

    #racen-send-btn:hover {
      background: #0288d1;
    }

    #racen-send-btn:disabled {
      background: #555;
      cursor: not-allowed;
      opacity: 0.5;
    }

    #racen-send-btn svg {
      width: 16px;
      height: 16px;
      fill: none;
      stroke: white;
      stroke-width: 2;
      stroke-linecap: round;
      stroke-linejoin: round;
    }

    #racen-powered-by {
      text-align: center;
      padding: 8px;
      font-size: 10px;
      color: rgba(255, 255, 255, 0.3);
      background: rgb(15, 15, 20);
    }

    #racen-powered-by a {
      color: rgba(3, 169, 244, 0.6);
      text-decoration: none;
    }

    @media (max-width: 480px) {
      #racen-chat-window {
        width: calc(100vw - 20px);
        height: calc(100vh - 120px);
        right: 10px;
        bottom: 90px;
        max-height: none;
      }

      #racen-chat-bubble {
        width: 54px;
        height: 54px;
        right: 16px;
        bottom: 16px;
      }
    }
  `;

  function injectStyles() {
    const styleEl = document.createElement('style');
    styleEl.id = 'racen-widget-styles';
    styleEl.textContent = styles;
    document.head.appendChild(styleEl);
  }

  function createWidget() {
    const container = document.createElement('div');
    container.id = 'racen-widget-container';
    container.innerHTML = `
      <button id="racen-chat-bubble" aria-label="Open chat">
        <svg class="chat-icon" viewBox="0 0 24 24">
          <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/>
        </svg>
        <svg class="close-icon" viewBox="0 0 24 24">
          <path d="M18 6L6 18M6 6l12 12" stroke="white" stroke-width="2" stroke-linecap="round"/>
        </svg>
      </button>
      <div id="racen-chat-window">
        <div id="racen-chat-header">
          <div class="avatar">R</div>
          <div class="info">
            <h3>RACEN</h3>
            <p>Your JoveHeal Guide</p>
          </div>
        </div>
        <div id="racen-chat-messages">
          <div class="racen-welcome">
            <h4>Hi, I'm RACEN</h4>
            <p>Your real-time guide for healing and coaching at JoveHeal. How can I help you today?</p>
          </div>
        </div>
        <div id="racen-chat-input-container">
          <div id="racen-chat-input-wrapper">
            <input type="text" id="racen-chat-input" placeholder="Ask me anything about JoveHeal..." />
            <button id="racen-send-btn" disabled aria-label="Send message">
              <svg viewBox="0 0 24 24">
                <path d="M14 5l7 7m0 0l-7 7m7-7H3"/>
              </svg>
            </button>
          </div>
        </div>
        <div id="racen-powered-by">
          Powered by <a href="https://joveheal.com" target="_blank">JoveHeal</a>
        </div>
      </div>
    `;
    document.body.appendChild(container);
  }

  let sessionId = '';
  let messages = [];
  let isLoading = false;

  function generateSessionId() {
    return 'widget_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
  }

  function toggleChat() {
    const bubble = document.getElementById('racen-chat-bubble');
    const window = document.getElementById('racen-chat-window');
    const isOpen = window.classList.contains('open');
    
    if (isOpen) {
      window.classList.remove('open');
      bubble.classList.remove('open');
    } else {
      window.classList.add('open');
      bubble.classList.add('open');
      document.getElementById('racen-chat-input').focus();
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
    const messagesContainer = document.getElementById('racen-chat-messages');
    const welcome = messagesContainer.querySelector('.racen-welcome');
    if (welcome) welcome.remove();

    const msgEl = document.createElement('div');
    msgEl.className = `racen-message ${role}`;
    msgEl.appendChild(createSafeContent(content));
    messagesContainer.appendChild(msgEl);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    
    return msgEl;
  }

  function updateMessageContent(msgEl, content) {
    msgEl.innerHTML = '';
    msgEl.appendChild(createSafeContent(content));
  }

  function showTyping() {
    const messagesContainer = document.getElementById('racen-chat-messages');
    const typingEl = document.createElement('div');
    typingEl.className = 'racen-typing';
    typingEl.id = 'racen-typing-indicator';
    typingEl.innerHTML = '<span></span><span></span><span></span>';
    messagesContainer.appendChild(typingEl);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  }

  function hideTyping() {
    const typing = document.getElementById('racen-typing-indicator');
    if (typing) typing.remove();
  }

  function updateSendButton() {
    const input = document.getElementById('racen-chat-input');
    const btn = document.getElementById('racen-send-btn');
    btn.disabled = !input.value.trim() || isLoading;
  }

  async function sendMessage() {
    const input = document.getElementById('racen-chat-input');
    const content = input.value.trim();
    
    if (!content || isLoading) return;

    isLoading = true;
    input.value = '';
    updateSendButton();

    addMessage('user', content);
    messages.push({ role: 'user', content });

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

      if (!response.ok) throw new Error('Request failed');

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let streamedContent = '';
      let assistantMsgEl = null;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              
              if (data.type === 'content') {
                hideTyping();
                streamedContent += data.content;
                
                if (!assistantMsgEl) {
                  assistantMsgEl = addMessage('assistant', streamedContent);
                } else {
                  updateMessageContent(assistantMsgEl, streamedContent);
                }
                
                const container = document.getElementById('racen-chat-messages');
                container.scrollTop = container.scrollHeight;
              } else if (data.type === 'done') {
                const finalContent = data.full_response || streamedContent;
                if (assistantMsgEl) {
                  updateMessageContent(assistantMsgEl, finalContent);
                }
                messages.push({ role: 'assistant', content: finalContent });
              }
            } catch (e) {}
          }
        }
      }

      if (!assistantMsgEl && streamedContent) {
        addMessage('assistant', streamedContent);
        messages.push({ role: 'assistant', content: streamedContent });
      }

    } catch (error) {
      console.error('RACEN Widget Error:', error);
      hideTyping();
      addMessage('assistant', 'I apologize, but I encountered a connection issue. Please try again.');
    } finally {
      isLoading = false;
      hideTyping();
      updateSendButton();
    }
  }

  function initWidget() {
    if (document.getElementById('racen-widget-container')) return;

    injectStyles();
    createWidget();
    sessionId = generateSessionId();

    document.getElementById('racen-chat-bubble').addEventListener('click', toggleChat);
    
    const input = document.getElementById('racen-chat-input');
    input.addEventListener('input', updateSendButton);
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    });

    document.getElementById('racen-send-btn').addEventListener('click', sendMessage);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initWidget);
  } else {
    initWidget();
  }
})();
