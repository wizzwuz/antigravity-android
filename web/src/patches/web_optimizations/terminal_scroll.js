/**
 * patches/web_optimizations/terminal_scroll.js - touch scroll support for terminal panel.
 *
 * Prevents drawer dismissal on terminal touch swipe and enables touch scrolling
 * with momentum (inertia) to view previous commands and output in xterm.
 */
'use strict';

function installTerminalTouchScroll(global, doc) {
  try {
    var startY = 0;
    var startX = 0;
    var lastY = 0;
    var lastTimestamp = 0;
    var velocityY = 0;
    var activeTerm = null;
    var activeTarget = null;
    var isScrolling = false;
    var animFrameId = null;
    var scrollTarget = null;

    // Friction multiplier per frame (~60fps). 0.92 ≈ stops in ~300ms.
    var FRICTION = 0.92;
    // Minimum velocity (px/ms * scale) below which momentum stops.
    var MIN_VELOCITY = 0.3;
    // Scale factor mapping touch velocity to wheel deltaY units.
    var VELOCITY_SCALE = 2.5;

    function cancelMomentum() {
      if (animFrameId !== null) {
        global.cancelAnimationFrame(animFrameId);
        animFrameId = null;
      }
    }

    function runMomentum() {
      if (Math.abs(velocityY) < MIN_VELOCITY || !scrollTarget) {
        animFrameId = null;
        return;
      }
      velocityY *= FRICTION;
      var wheelEvt = new WheelEvent('wheel', {
        bubbles: true,
        cancelable: true,
        view: global,
        deltaY: -velocityY,
        deltaMode: 0
      });
      scrollTarget.dispatchEvent(wheelEvt);
      animFrameId = global.requestAnimationFrame(runMomentum);
    }

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
      cancelMomentum();
      velocityY = 0;

      if (!e.touches || e.touches.length !== 1) {
        activeTerm = null;
        activeTarget = null;
        scrollTarget = null;
        return;
      }
      var target = e.target;
      var term = target && target.closest
        ? target.closest('.xterm, [data-testid="terminal-surface"], [data-testid="terminal-view"], .terminal, .xterm-scrollable-element')
        : null;

      if (!term) {
        activeTerm = null;
        activeTarget = null;
        scrollTarget = null;
        return;
      }

      markTerminalElements(term);
      activeTerm = term;
      activeTarget = target;
      startY = lastY = e.touches[0].clientY;
      startX = e.touches[0].clientX;
      lastTimestamp = e.timeStamp;
      isScrolling = false;

      // Pre-resolve scroll target once per touch sequence.
      scrollTarget = (target && target.closest ? target.closest('.xterm-scrollable-element') : null)
        || term.querySelector('.xterm-scrollable-element')
        || term.querySelector('.xterm-screen')
        || term;
    }, { passive: true, capture: true });

    doc.addEventListener('touchmove', function (e) {
      if (!activeTerm || !e.touches || e.touches.length !== 1) return;

      var cy = e.touches[0].clientY;
      var cx = e.touches[0].clientX;
      var dy = lastY - cy;
      var dt = e.timeStamp - lastTimestamp;
      var totalDy = Math.abs(cy - startY);
      var totalDx = Math.abs(cx - startX);

      // Recognize vertical swipe in terminal.
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
          // Exponential moving average velocity (px/ms * VELOCITY_SCALE).
          var instVelocity = dt > 0 ? (dy / dt) * VELOCITY_SCALE * 16 : 0;
          velocityY = velocityY * 0.6 + instVelocity * 0.4;

          lastY = cy;
          lastTimestamp = e.timeStamp;

          var wheelEvt = new WheelEvent('wheel', {
            bubbles: true,
            cancelable: true,
            view: global,
            deltaY: -dy * VELOCITY_SCALE,
            deltaMode: 0
          });
          scrollTarget.dispatchEvent(wheelEvt);
        }
      }
    }, { passive: false, capture: true });

    doc.addEventListener('touchend', function (e) {
      if (isScrolling && Math.abs(velocityY) > MIN_VELOCITY && scrollTarget) {
        // Kick off momentum animation.
        animFrameId = global.requestAnimationFrame(runMomentum);
      }
      activeTerm = null;
      activeTarget = null;
      isScrolling = false;
    }, { passive: true, capture: true });

    doc.addEventListener('touchcancel', function () {
      cancelMomentum();
      velocityY = 0;
      activeTerm = null;
      activeTarget = null;
      scrollTarget = null;
      isScrolling = false;
    }, { passive: true, capture: true });
  } catch (err) {}
}
