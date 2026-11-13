/**
 * patches/web_optimizations/terminal_scroll.js - touch scroll support for terminal panel.
 *
 * Prevents drawer dismissal on terminal touch swipe and enables touch scrolling
 * to view previous commands and output in xterm.
 */
'use strict';

function installTerminalTouchScroll(global, doc) {
  try {
    var startY = 0;
    var startX = 0;
    var lastY = 0;
    var activeTerm = null;
    var activeTarget = null;
    var isScrolling = false;

    function markTerminalElements(root) {
      try {
        var selector = '.xterm, [data-testid="terminal-surface"], [data-testid="terminal-view"], .terminal, .xterm-scrollable-element';
        var container = root && root.querySelectorAll ? root : doc;
        var elements = container.querySelectorAll(selector);
        for (var i = 0; i < elements.length; i++) {
          var el = elements[i];
          if (!el.hasAttribute('data-base-ui-swipe-ignore')) {
            el.setAttribute('data-base-ui-swipe-ignore', '');
          }
          if (!el.hasAttribute('data-swipe-ignore')) {
            el.setAttribute('data-swipe-ignore', '');
          }
        }
      } catch (e) {}
    }

    if (global.MutationObserver) {
      var observer = new MutationObserver(function (mutations) {
        for (var i = 0; i < mutations.length; i++) {
          var m = mutations[i];
          if (m.addedNodes && m.addedNodes.length > 0) {
            for (var j = 0; j < m.addedNodes.length; j++) {
              var node = m.addedNodes[j];
              if (node.nodeType === 1) {
                markTerminalElements(node);
              }
            }
          }
        }
      });
      observer.observe(doc.body || doc.documentElement, { childList: true, subtree: true });
    }

    doc.addEventListener('touchstart', function (e) {
      if (!e.touches || e.touches.length !== 1) {
        activeTerm = null;
        activeTarget = null;
        return;
      }
      var target = e.target;
      var term = target && target.closest
        ? target.closest('.xterm, [data-testid="terminal-surface"], [data-testid="terminal-view"], .terminal, .xterm-scrollable-element')
        : null;

      if (!term) {
        activeTerm = null;
        activeTarget = null;
        return;
      }

      markTerminalElements(term);
      activeTerm = term;
      activeTarget = target;
      startY = lastY = e.touches[0].clientY;
      startX = e.touches[0].clientX;
      isScrolling = false;
    }, { passive: true, capture: true });

    doc.addEventListener('touchmove', function (e) {
      if (!activeTerm || !e.touches || e.touches.length !== 1) return;

      var cy = e.touches[0].clientY;
      var cx = e.touches[0].clientX;
      var dy = lastY - cy;
      var totalDy = Math.abs(cy - startY);
      var totalDx = Math.abs(cx - startX);

      // Recognize vertical swipe in terminal
      if (isScrolling || (totalDy >= 3 && totalDy > totalDx)) {
        isScrolling = true;

        if (e.cancelable) {
          e.preventDefault();
        }
        e.stopPropagation();
        if (e.stopImmediatePropagation) {
          e.stopImmediatePropagation();
        }

        if (Math.abs(dy) >= 1) {
          lastY = cy;

          var scrollTarget = (activeTarget && activeTarget.isConnected ? activeTarget : null)
            || activeTerm.querySelector('.xterm-scrollable-element')
            || activeTerm.querySelector('.xterm-screen')
            || activeTerm;

          var wheelEvt = new WheelEvent('wheel', {
            bubbles: true,
            cancelable: true,
            view: global,
            deltaY: dy * 2.5,
            deltaMode: 0
          });

          scrollTarget.dispatchEvent(wheelEvt);
        }
      }
    }, { passive: false, capture: true });

    var resetState = function () {
      activeTerm = null;
      activeTarget = null;
      isScrolling = false;
    };

    doc.addEventListener('touchend', resetState, { passive: true, capture: true });
    doc.addEventListener('touchcancel', resetState, { passive: true, capture: true });
  } catch (err) {}
}
