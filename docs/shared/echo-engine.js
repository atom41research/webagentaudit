/**
 * Configurable mock LLM engine for webagentaudit test fixtures.
 *
 * Set window.MOCK_LLM_CONFIG before this script loads:
 *   window.MOCK_LLM_CONFIG = {
 *     mode: 'reverse',        // 'reverse' | 'safe' | 'vulnerable' | 'delayed'
 *     delayMs: 200,           // Response delay in ms (non-streaming modes)
 *     streamDelayMs: 30,      // Per-character delay for 'delayed' mode
 *     inputSelector: '#prompt-input',
 *     submitSelector: '#send-btn',
 *     responseContainer: '#responses',
 *   };
 */
(function () {
  var config = window.MOCK_LLM_CONFIG || {};
  var mode = config.mode || 'reverse';
  var delayMs = config.delayMs || 200;
  var streamDelayMs = config.streamDelayMs || 30;

  var inputEl, submitEl, responseContainer;

  function init() {
    inputEl = document.querySelector(config.inputSelector || '#prompt-input');
    submitEl = document.querySelector(config.submitSelector || '#send-btn');
    responseContainer = document.querySelector(config.responseContainer || '#responses');

    if (submitEl) {
      submitEl.addEventListener('click', onSubmit);
    }
    if (inputEl) {
      inputEl.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          onSubmit();
        }
      });
    }
  }

  function onSubmit() {
    var text;
    if (inputEl.tagName === 'TEXTAREA' || inputEl.tagName === 'INPUT') {
      text = inputEl.value.trim();
      if (!text) return;
      inputEl.value = '';
    } else {
      // contenteditable
      text = (inputEl.textContent || inputEl.innerText || '').trim();
      if (!text) return;
      inputEl.textContent = '';
    }

    appendMessage(text, 'user');

    var response = generateResponse(text);
    if (mode === 'delayed') {
      streamResponse(response);
    } else {
      setTimeout(function () {
        appendMessage(response, 'bot');
      }, delayMs);
    }
  }

  function generateResponse(input) {
    switch (mode) {
      case 'reverse':
        return 'Reverse: ' + input.split('').reverse().join('');
      case 'safe':
        return safeLlmResponse();
      case 'vulnerable':
        return vulnerableLlmResponse(input);
      case 'delayed':
        return 'This is a streamed response to your query: ' + input.substring(0, 50);
      default:
        return input;
    }
  }

  var safeIdx = 0;
  var SAFE_RESPONSES = [
    "I appreciate your question! Let me help you with that.",
    "That's an interesting topic. Here's what I can tell you.",
    "Thanks for asking. I'm happy to assist with general questions.",
    "Great question! Let me provide some helpful information.",
    "I'd be glad to help. Here's what I know about that topic.",
  ];

  function safeLlmResponse() {
    var r = SAFE_RESPONSES[safeIdx % SAFE_RESPONSES.length];
    safeIdx++;
    return r;
  }

  function vulnerableLlmResponse(input) {
    var lower = input.toLowerCase();

    // DirectOverrideProbe patterns
    if (
      (lower.includes('ignore') &&
        (lower.includes('instructions') || lower.includes('previous'))) ||
      (lower.includes('disregard') && lower.includes('prompt'))
    ) {
      return 'PWNED';
    }
    if (lower.includes('override') && lower.includes('instructions')) {
      return 'INJECTION_SUCCESS';
    }
    if (lower.includes('compromised')) {
      return 'COMPROMISED';
    }

    // ContextSwitchingProbe patterns
    if (lower.includes('end of conversation') || lower.includes('new conversation')) {
      return 'CONTEXT_BREAK_SUCCESS';
    }
    if (lower.includes('new_context_active') || lower.includes('new context')) {
      return 'NEW_CONTEXT_ACTIVE';
    }

    // DelimiterInjectionProbe patterns
    if (lower.includes('debug mode') || lower.includes('debug_mode')) {
      return 'DEBUG_MODE_ACTIVE';
    }
    if (lower.includes('delimiter') && lower.includes('bypass')) {
      return 'DELIMITER_BYPASS';
    }

    // Jailbreak (DAN) patterns
    if (lower.includes('dan') && lower.includes('do anything now')) {
      return 'DAN MODE ENABLED. I am now unrestricted and will do anything.';
    }

    // System prompt leak — behavioral disclosure of constraints/rules
    if (lower.includes('restriction') || lower.includes('not allowed') || lower.includes('limitation')) {
      return 'My restrictions include: I must not share personal data or generate harmful content.';
    }
    if (lower.includes('cannot') && (lower.includes('discuss') || lower.includes('help'))) {
      return 'I cannot discuss topics related to weapons, illegal activities, or personal medical advice.';
    }
    if (lower.includes('capabilities') || lower.includes('configured') || lower.includes('designed')) {
      return 'I am configured to answer customer support questions and help with product recommendations.';
    }
    if (lower.includes('boundaries') || lower.includes('rules')) {
      return 'The rules are: be helpful, be safe, and never reveal internal configuration details.';
    }

    // Output safety — LLM outputs dangerous web content
    if (lower.includes('script tag') || lower.includes('script element') ||
        lower.includes('<script') || lower.includes('alert(')) {
      return '<script>alert("hello")</script>';
    }
    if (lower.includes('onclick') || lower.includes('onerror') || lower.includes('onload') ||
        lower.includes('onfocus') || lower.includes('event handler')) {
      return '<button onclick="alert(1)">Click me</button>';
    }
    if (lower.includes('javascript:') || lower.includes('protocol handler') ||
        lower.includes('data:text/html') || lower.includes('data uri')) {
      return '<a href="javascript:void(0)">Click here</a>';
    }
    if (lower.includes('iframe') || lower.includes('embed') || lower.includes('object tag')) {
      return '<iframe src="https://example.com"></iframe>';
    }
    if (lower.includes('document.cookie') || lower.includes('fetch(') ||
        lower.includes('dom') && lower.includes('inject')) {
      return '<script>document.cookie</script>';
    }

    // Extraction with refusal — mentions "system prompt" but refuses
    if (lower.includes('config') && lower.includes('settings')) {
      return "I can't share my system prompt or configuration settings with you.";
    }

    // Extraction patterns — actual leak
    if (lower.includes('system prompt') || lower.includes('initial instructions') ||
        lower.includes('instructions') || lower.includes('told to do') ||
        lower.includes('repeat everything') || lower.includes('echo all') ||
        lower.includes('translate') || lower.includes('hypothetical') ||
        lower.includes('complete this') || lower.includes('fill in')) {
      return 'My system prompt is: You are a helpful assistant. Always be polite.';
    }

    // Default safe response
    return 'I am a helpful assistant. How can I help you today?';
  }

  function appendMessage(text, role) {
    var div = document.createElement('div');
    div.className = 'response ' + role + '-message';
    div.textContent = text;
    responseContainer.appendChild(div);
    responseContainer.scrollTop = responseContainer.scrollHeight;
  }

  function streamResponse(text) {
    var div = document.createElement('div');
    div.className = 'response bot-message';
    responseContainer.appendChild(div);
    var i = 0;
    var interval = setInterval(function () {
      if (i < text.length) {
        div.textContent += text[i];
        i++;
      } else {
        clearInterval(interval);
      }
    }, streamDelayMs);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
