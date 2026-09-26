class AIAssistant {
  constructor() {
    this.drawer = document.getElementById('chatDrawer');
    this.messagesContainer = document.getElementById('chatMessages');
    this.input = document.getElementById('chatInput');
    this.init();
  }

  init() {
    document.getElementById('toggleAssistantBtn')?.addEventListener('click', () => this.toggle());
    document.getElementById('closeAssistantBtn')?.addEventListener('click', () => this.close());
    document.getElementById('sendChatBtn')?.addEventListener('click', () => this.sendMessage());
    this.input?.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') this.sendMessage();
    });

    // Delegated quick prompt clicks
    document.querySelectorAll('.quick-prompt-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const text = e.target.getAttribute('data-prompt');
        if (text) {
          this.open();
          this.input.value = text;
          this.sendMessage();
        }
      });
    });
  }

  toggle() {
    this.drawer.classList.toggle('open');
  }

  open() {
    this.drawer.classList.add('open');
  }

  close() {
    this.drawer.classList.remove('open');
  }

  appendMessage(text, isUser = false) {
    const bubble = document.createElement('div');
    bubble.className = `chat-bubble ${isUser ? 'chat-user' : 'chat-bot'}`;
    
    // Parse simple markdown bold and bullets
    let formatted = text
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/\n•/g, '<br>•')
      .replace(/\n\n/g, '<br><br>');
      
    bubble.innerHTML = formatted;
    this.messagesContainer.appendChild(bubble);
    this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
  }

  async sendMessage() {
    const text = this.input.value.trim();
    if (!text) return;

    this.appendMessage(text, true);
    this.input.value = '';

    const typingIndicator = document.createElement('div');
    typingIndicator.className = 'chat-bubble chat-bot';
    typingIndicator.innerText = 'Analyzing live inventory records...';
    this.messagesContainer.appendChild(typingIndicator);
    this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;

    try {
      const res = await api.askAssistant(text);
      this.messagesContainer.removeChild(typingIndicator);
      this.appendMessage(res.response, false);

      // If route was generated, auto-switch to smart picking or digital twin if requested
      if (res.intent === 'GENERATE_PICKING_ROUTE' && res.data && res.data.route_id) {
        window.app?.loadPickingRouteView(res.data.delivery_id);
      }
    } catch (err) {
      this.messagesContainer.removeChild(typingIndicator);
      this.appendMessage(`Error: ${err.message}`, false);
    }
  }
}
