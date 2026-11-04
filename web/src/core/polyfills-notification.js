/**
 * core/polyfills-notification.js - Native Android Notification bridge & polyfill.
 * Routes window.Notification and agent completion/progress events to native Android channels:
 * 1. agent_completed_open_chat: Notification shade without a heads-up banner (when chat has focus)
 * 2. agent_completed: Floating notification / heads-up banner (when in background or needs attention)
 * 3. agent_progress: Silent progress for ongoing Antigravity tasks
 */
try {
  function dispatchNativeNotification(channel, title, message, cascadeId, ongoing, progress) {
    if (window.Android && typeof window.Android.postNotification === 'function') {
      try {
        window.Android.postNotification(channel, title || 'Antigravity', message || '', cascadeId || '', !!ongoing, progress != null ? progress : -1);
        return true;
      } catch (err) {
        console.warn('[AGY Notification] postNotification error:', err);
      }
    }
    return false;
  }

  function cancelNativeNotification(tag, id) {
    if (window.Android && typeof window.Android.cancelNotification === 'function') {
      try {
        window.Android.cancelNotification(tag || '', id || 0);
        return true;
      } catch (err) {
        console.warn('[AGY Notification] cancelNotification error:', err);
      }
    }
    return false;
  }

  // Provide window.Notification polyfill for WebView
  function PolyfillNotification(title, options) {
    options = options || {};
    this.title = title;
    this.body = options.body || '';
    this.tag = options.tag || '';
    this.silent = options.silent || false;
    this.data = options.data || {};

    var isChatOpen = typeof document !== 'undefined' && document.hasFocus && document.hasFocus();
    var defaultChannel = isChatOpen ? 'agent_completed_open_chat' : 'agent_completed';
    var channel = options.channel || options.category || defaultChannel;
    var cascadeId = options.cascadeId || (this.data && this.data.cascadeId) || '';

    dispatchNativeNotification(channel, title, this.body, cascadeId, false, -1);
  }

  PolyfillNotification.permission = 'granted';
  PolyfillNotification.requestPermission = function (callback) {
    var p = Promise.resolve('granted');
    if (typeof callback === 'function') callback('granted');
    return p;
  };

  if (typeof window !== 'undefined') {
    window.Notification = PolyfillNotification;
    window.__agyNotify = {
      post: dispatchNativeNotification,
      cancel: cancelNativeNotification
    };
  }
} catch (e) {
  console.warn('[AGY Notification] polyfill error:', e);
}
