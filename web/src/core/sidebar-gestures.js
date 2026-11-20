/**
 * core/sidebar-gestures.js - Long-press gestures for Projects and Conversations in side menu.
 * 1. Holding "Projects" opens menu to create a new project or open a folder.
 * 2. Holding a conversation opens menu to add it to an existing project or create a new project.
 */
(function () {
  'use strict';

  if (typeof window === 'undefined') return;

  var LONG_PRESS_MS = 450;
  var MOVE_THRESHOLD = 12;

  var touchTimer = null;
  var startX = 0;
  var startY = 0;
  var activeTarget = null;

  function getProjectsList() {
    var projects = [];
    try {
      if (window.__agySidebarProvider && typeof window.__agySidebarProvider.getState === 'function') {
        var state = window.__agySidebarProvider.getState();
        if (state && Array.isArray(state.sidebarSections)) {
          for (var i = 0; i < state.sidebarSections.length; i++) {
            var sec = state.sidebarSections[i];
            if (sec && sec.uri && (sec.uri.startsWith('file://') || sec.sectionKind)) {
              var lbl = sec.label || sec.uri.split('/').pop() || 'Project ' + (i + 1);
              projects.push({ uri: sec.uri, label: lbl });
            }
          }
        }
      }
    } catch (_) {}

    // Fallback: collect project folders from DOM sidebar items
    if (projects.length === 0) {
      try {
        var links = document.querySelectorAll('button[data-testid*="project"], a[href*="section"]');
        for (var j = 0; j < links.length; j++) {
          var text = (links[j].textContent || '').trim();
          if (text && text !== 'Projects' && text !== 'Workspaces') {
            projects.push({ uri: 'section:' + text, label: text });
          }
        }
      } catch (_) {}
    }
    return projects;
  }

  function showModal(title, contentElem) {
    closeModal();
    var backdrop = document.createElement('div');
    backdrop.id = 'agy-gesture-backdrop';
    backdrop.style.cssText =
      'position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.65);' +
      'backdrop-filter:blur(4px);z-index:999999;display:flex;align-items:center;justify-content:center;padding:16px;';

    var card = document.createElement('div');
    card.style.cssText =
      'background:#1e1e24;border:1px solid rgba(255,255,255,0.15);border-radius:16px;' +
      'width:100%;max-width:380px;box-shadow:0 20px 40px rgba(0,0,0,0.6);color:#f0f0f0;overflow:hidden;font-family:sans-serif;';

    var header = document.createElement('div');
    header.style.cssText =
      'display:flex;align-items:center;justify-content:between;padding:14px 18px;border-bottom:1px solid rgba(255,255,255,0.1);font-weight:600;font-size:15px;';
    header.innerHTML = '<span style="flex:1;">' + title + '</span>' +
      '<button id="agy-modal-close" style="background:none;border:none;color:#aaa;font-size:20px;cursor:pointer;padding:0 4px;line-height:1;">&times;</button>';

    var body = document.createElement('div');
    body.style.cssText = 'padding:14px 16px;max-height:60vh;overflow-y:auto;';
    body.appendChild(contentElem);

    card.appendChild(header);
    card.appendChild(body);
    backdrop.appendChild(card);
    document.body.appendChild(backdrop);

    document.getElementById('agy-modal-close').onclick = closeModal;
    backdrop.onclick = function (e) {
      if (e.target === backdrop) closeModal();
    };
  }

  function closeModal() {
    var el = document.getElementById('agy-gesture-backdrop');
    if (el && el.parentNode) {
      el.parentNode.removeChild(el);
    }
  }

  function showProjectsMenu() {
    var container = document.createElement('div');
    container.style.cssText = 'display:flex;flex-direction:column;gap:10px;';

    var desc = document.createElement('div');
    desc.style.cssText = 'font-size:12px;color:#999;margin-bottom:4px;';
    desc.innerText = 'Projects stored under /storage/emulated/0/Documents/';
    container.appendChild(desc);

    var createBtn = document.createElement('button');
    createBtn.style.cssText =
      'background:#2563eb;color:#fff;border:none;border-radius:10px;padding:12px 14px;' +
      'font-weight:600;font-size:14px;cursor:pointer;text-align:left;display:flex;align-items:center;gap:10px;';
    createBtn.innerHTML = '<span>➕</span><span>Create New Project</span>';
    createBtn.onclick = function () {
      promptCreateProject();
    };
    container.appendChild(createBtn);

    var openBtn = document.createElement('button');
    openBtn.style.cssText =
      'background:rgba(255,255,255,0.08);color:#eee;border:1px solid rgba(255,255,255,0.1);border-radius:10px;padding:12px 14px;' +
      'font-size:14px;cursor:pointer;text-align:left;display:flex;align-items:center;gap:10px;';
    openBtn.innerHTML = '<span>📁</span><span>Open Existing Folder</span>';
    openBtn.onclick = function () {
      closeModal();
      if (window.Android && typeof window.Android.openDirectoryPicker === 'function') {
        window.Android.openDirectoryPicker();
      } else {
        var addBtn = document.querySelector('button[aria-label*="Add Workspace"], button[aria-label*="Create New Project"]');
        if (addBtn) addBtn.click();
      }
    };
    container.appendChild(openBtn);

    showModal('Projects', container);
  }

  function promptCreateProject(onSuccess) {
    var container = document.createElement('div');
    container.style.cssText = 'display:flex;flex-direction:column;gap:12px;';

    var label = document.createElement('label');
    label.style.cssText = 'font-size:13px;color:#ccc;';
    label.innerText = 'Project Name:';

    var input = document.createElement('input');
    input.type = 'text';
    input.placeholder = 'e.g. MyAwesomeApp';
    input.style.cssText =
      'background:#121215;border:1px solid rgba(255,255,255,0.2);border-radius:8px;padding:10px;color:#fff;font-size:14px;outline:none;';

    var submitBtn = document.createElement('button');
    submitBtn.style.cssText =
      'background:#2563eb;color:#fff;border:none;border-radius:8px;padding:10px;font-weight:600;font-size:14px;cursor:pointer;';
    submitBtn.innerText = 'Create Project';

    submitBtn.onclick = function () {
      var name = input.value.trim();
      if (!name) return;
      var safeName = name.replace(/[^a-zA-Z0-9_.-]/g, '_');
      var path = '/storage/emulated/0/Documents/' + safeName;
      if (window.Android && typeof window.Android.createProjectFolder === 'function') {
        var created = window.Android.createProjectFolder(safeName);
        if (created) path = created;
      }
      var uri = 'file://' + path;

      if (window.__agySidebarProvider && typeof window.__agySidebarProvider.pushUpdate === 'function') {
        try {
          window.__agySidebarProvider.pushUpdate({ type: 'add', workspaceUri: uri });
        } catch (_) {}
      }

      if (typeof window.__agySwitchSection === 'function') {
        try { window.__agySwitchSection(uri); } catch (_) {}
      }

      closeModal();
      if (typeof onSuccess === 'function') {
        onSuccess(uri, safeName);
      }
    };

    container.appendChild(label);
    container.appendChild(input);
    container.appendChild(submitBtn);

    showModal('Create Project', container);
    setTimeout(function () { input.focus(); }, 100);
  }

  function showConversationActionsMenu(cascadeId, convoTitle) {
    var container = document.createElement('div');
    container.style.cssText = 'display:flex;flex-direction:column;gap:10px;';

    var projects = getProjectsList();

    // 1. Add to existing project
    var addExistBtn = document.createElement('button');
    addExistBtn.style.cssText =
      'background:rgba(255,255,255,0.08);color:#eee;border:1px solid rgba(255,255,255,0.1);border-radius:10px;padding:12px 14px;' +
      'font-size:14px;cursor:pointer;text-align:left;display:flex;align-items:center;gap:10px;';
    addExistBtn.innerHTML = '<span>📁</span><span>Add to Existing Project (' + projects.length + ')</span>';
    addExistBtn.onclick = function () {
      if (projects.length === 0) {
        promptCreateProject(function (uri, name) {
          assignConversationToProject(cascadeId, uri);
        });
        return;
      }
      showProjectPickerMenu(cascadeId, projects);
    };
    container.appendChild(addExistBtn);

    // 2. Create new project and add
    var createAndAddBtn = document.createElement('button');
    createAndAddBtn.style.cssText =
      'background:#2563eb;color:#fff;border:none;border-radius:10px;padding:12px 14px;' +
      'font-size:14px;cursor:pointer;text-align:left;display:flex;align-items:center;gap:10px;';
    createAndAddBtn.innerHTML = '<span>➕</span><span>Create New Project & Add</span>';
    createAndAddBtn.onclick = function () {
      promptCreateProject(function (uri, name) {
        assignConversationToProject(cascadeId, uri);
      });
    };
    container.appendChild(createAndAddBtn);

    showModal(convoTitle || 'Conversation Actions', container);
  }

  function showProjectPickerMenu(cascadeId, projects) {
    var container = document.createElement('div');
    container.style.cssText = 'display:flex;flex-direction:column;gap:8px;';

    for (var i = 0; i < projects.length; i++) {
      (function (proj) {
        var btn = document.createElement('button');
        btn.style.cssText =
          'background:rgba(255,255,255,0.06);color:#f0f0f0;border:1px solid rgba(255,255,255,0.08);border-radius:8px;' +
          'padding:10px 12px;font-size:13px;cursor:pointer;text-align:left;display:flex;align-items:center;gap:8px;';
        btn.innerHTML = '<span>📁</span><span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">' +
          proj.label + '</span>';
        btn.onclick = function () {
          assignConversationToProject(cascadeId, proj.uri);
          closeModal();
        };
        container.appendChild(btn);
      })(projects[i]);
    }

    showModal('Select Project', container);
  }

  function assignConversationToProject(cascadeId, projectUri) {
    try {
      if (window.__agySidebarProvider && typeof window.__agySidebarProvider.pushUpdate === 'function') {
        window.__agySidebarProvider.pushUpdate({
          type: 'addConversation',
          sectionUri: projectUri,
          conversationId: cascadeId
        });
      }
      try {
        localStorage.setItem('agy_convo_project_' + cascadeId, projectUri);
      } catch (_) {}
      if (typeof window.__agySwitchSection === 'function') {
        window.__agySwitchSection(projectUri);
      }
    } catch (e) {
      console.warn('[AGY] assignConversationToProject failed:', e);
    }
  }

  function findConversationInfo(elem) {
    var curr = elem;
    while (curr && curr !== document.body) {
      if (curr.getAttribute) {
        var cid = curr.getAttribute('data-cascade-id');
        if (cid) return { id: cid, title: (curr.textContent || '').trim() };
        var href = curr.getAttribute('href') || '';
        if (href.indexOf('/cascade/') !== -1) {
          cid = href.split('/cascade/').pop().split(/[?#]/)[0];
          return { id: cid, title: (curr.textContent || '').trim() };
        }
      }
      curr = curr.parentElement;
    }
    return null;
  }

  function isProjectsHeader(elem) {
    var curr = elem;
    for (var i = 0; i < 4 && curr; i++) {
      var txt = (curr.textContent || '').trim();
      var tid = curr.getAttribute ? curr.getAttribute('data-testid') : null;
      if (txt === 'Projects' || txt === 'Workspaces' || (tid && tid.indexOf('project') !== -1 && tid.indexOf('header') !== -1)) {
        return true;
      }
      curr = curr.parentElement;
    }
    return false;
  }

  function handleTouchStart(e) {
    if (!e.touches || e.touches.length !== 1) return;
    var touch = e.touches[0];
    startX = touch.clientX;
    startY = touch.clientY;
    activeTarget = e.target;

    clearTimeout(touchTimer);
    touchTimer = setTimeout(function () {
      if (!activeTarget) return;

      if (isProjectsHeader(activeTarget)) {
        if (navigator.vibrate) try { navigator.vibrate(30); } catch (_) {}
        showProjectsMenu();
        clearTimeout(touchTimer);
        touchTimer = null;
        return;
      }

      var convo = findConversationInfo(activeTarget);
      if (convo && convo.id) {
        if (navigator.vibrate) try { navigator.vibrate(30); } catch (_) {}
        showConversationActionsMenu(convo.id, convo.title);
        clearTimeout(touchTimer);
        touchTimer = null;
      }
    }, LONG_PRESS_MS);
  }

  function handleTouchMove(e) {
    if (!touchTimer || !e.touches || e.touches.length !== 1) return;
    var touch = e.touches[0];
    var dx = Math.abs(touch.clientX - startX);
    var dy = Math.abs(touch.clientY - startY);
    if (dx > MOVE_THRESHOLD || dy > MOVE_THRESHOLD) {
      clearTimeout(touchTimer);
      touchTimer = null;
    }
  }

  function handleTouchEnd() {
    clearTimeout(touchTimer);
    touchTimer = null;
    activeTarget = null;
  }

  document.addEventListener('touchstart', handleTouchStart, { passive: true });
  document.addEventListener('touchmove', handleTouchMove, { passive: true });
  document.addEventListener('touchend', handleTouchEnd, { passive: true });
  document.addEventListener('touchcancel', handleTouchEnd, { passive: true });

  // Context menu fallback for long-press
  document.addEventListener('contextmenu', function (e) {
    if (isProjectsHeader(e.target)) {
      e.preventDefault();
      showProjectsMenu();
      return;
    }
    var convo = findConversationInfo(e.target);
    if (convo && convo.id) {
      e.preventDefault();
      showConversationActionsMenu(convo.id, convo.title);
    }
  });

  window.__agyShowProjectsMenu = showProjectsMenu;
  window.__agyShowConversationActions = showConversationActionsMenu;
})();
