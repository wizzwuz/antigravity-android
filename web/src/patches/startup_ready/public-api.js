/**
 * patches/startup_ready/public-api.js - expose and arm on boot.
 */
if (global.document && global.document.readyState === 'loading') {
  global.document.addEventListener('DOMContentLoaded', arm, { once: true });
} else {
  arm();
}

global.__agStartupReady = {
  __installed: true,
  signal: signal,
  isReady: function () { return !!state.signalled; }
};

global.__agTriggerPendingJump = function () {
  var p = global.__agPendingConvoJump;
  if (!p) return;
  var startTime = Date.now();
  var attempts = 0;

  function attempt() {
    attempts++;
    var jump = global.__agPendingConvoJump;
    if (!jump || Date.now() - jump.time > 20000 || attempts > 60) {
      return;
    }

    var convoView = global.document && global.document.querySelector('[data-testid="conversation-view"]');
    if (!convoView) {
      setTimeout(attempt, 60);
      return;
    }

    var curCascade = convoView.getAttribute('data-cascade-id');
    if (curCascade && jump.cascadeId && curCascade !== jump.cascadeId && curCascade !== 'conversation') {
      setTimeout(attempt, 60);
      return;
    }

    var target = null;

    // 1. Search by step index attribute
    if (jump.stepIndex !== void 0 && jump.stepIndex !== null) {
      target = convoView.querySelector('[data-step-index="' + jump.stepIndex + '"]');
    }

    // 2. Search by snippet text (substring or words)
    if (!target && jump.snippet) {
      var raw = jump.snippet.replace(/^[.\s\u2026]+|[.\s\u2026]+$/g, '').trim().toLowerCase();
      if (raw.length > 3) {
        var words = raw.split(/\s+/).filter(function (w) { return w.length > 2; }).slice(0, 4);
        var walker = global.document.createTreeWalker(convoView, NodeFilter.SHOW_TEXT);
        var node;
        while ((node = walker.nextNode())) {
          var txt = (node.textContent || '').toLowerCase();
          if (txt.includes(raw) || (words.length > 0 && words.every(function (w) { return txt.includes(w); }))) {
            target = node.parentElement;
            break;
          }
        }
      }
    }

    // 3. Search by query string
    if (!target && jump.query && jump.query.length > 1) {
      var q = jump.query.toLowerCase();
      var walker = global.document.createTreeWalker(convoView, NodeFilter.SHOW_TEXT);
      var node;
      while ((node = walker.nextNode())) {
        if ((node.textContent || '').toLowerCase().includes(q)) {
          target = node.parentElement;
          break;
        }
      }
    }

    if (target) {
      var block = target.closest('[data-testid="agent-response"],[data-step-index],[data-turn-content],.message-row,[role="listitem"],p,pre,div') || target;
      block.scrollIntoView({ behavior: 'smooth', block: 'center' });

      // Apply distinct yellow glow highlight
      block.style.transition = 'background-color 250ms ease, box-shadow 250ms ease';
      block.style.backgroundColor = 'rgba(255, 235, 59, 0.45)';
      block.style.boxShadow = '0 0 0 4px rgba(255, 235, 59, 0.4)';
      block.style.borderRadius = '8px';

      // Enforce center scroll for 450ms to defeat any delayed auto-scroll to bottom
      var enforceTimer = setInterval(function () {
        block.scrollIntoView({ behavior: 'auto', block: 'center' });
      }, 75);
      setTimeout(function () {
        clearInterval(enforceTimer);
      }, 450);

      setTimeout(function () {
        block.style.backgroundColor = '';
        block.style.boxShadow = '';
      }, 2500);

      global.__agPendingConvoJump = null;
      return;
    }

    setTimeout(attempt, 60);
  }

  attempt();
};

if (global.document && global.MutationObserver) {
  var jumpObserver = new MutationObserver(function () {
    if (global.__agPendingConvoJump && typeof global.__agTriggerPendingJump === 'function') {
      global.__agTriggerPendingJump();
    }
  });
  if (global.document.body || global.document.documentElement) {
    jumpObserver.observe(global.document.body || global.document.documentElement, { childList: true, subtree: true });
  } else {
    global.document.addEventListener('DOMContentLoaded', function () {
      jumpObserver.observe(global.document.body, { childList: true, subtree: true });
    }, { once: true });
  }
}
