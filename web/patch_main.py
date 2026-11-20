#!/usr/bin/env python3
"""
web/patch_main.py - Dynamic patcher for web/main.js.

1. Locates the Appearance settings block and injects the Desktop Mode toggle.
2. Injects a conversation search button immediately to the left of the three-dot
   menu in project conversations/header, enabling search across the entire conversation.
3. Enhanced multi-conversation background notifications and cancellation suppression.
4. Auto-retry on network reconnection.
5. Notification sound elimination.
6. Persistent conversation renaming across restores and stream updates.
7. Full un-truncated clipboard pasting.
8. Proper project storage directory (/storage/emulated/0/Documents) and disk deletion.
9. Global sidebar provider hooks for touch gestures.
Safe, idempotent, and resilient to upstream changes.
"""

import sys
import os
import re


def patch_desktop_mode(content):
    if "Desktop Mode" in content or "ag_desktop_mode" in content:
        print("[web-patch] Desktop Mode toggle already present in main.js")
        return content, True

    hook_pattern = re.compile(
        r'(var\s+[A-Za-z0-9_$]+=[A-Za-z0-9_$]+!==3,\s*[A-Za-z0-9_$]+=[A-Za-z0-9_$]+!==2,\s*[A-Za-z0-9_$]+=[A-Za-z0-9_$]+=>\s*[A-Za-z0-9_$]+=>\{.*?\};)'
    )
    hook_match = hook_pattern.search(content)

    theme_idx = content.find('{label:"Theme"')
    theme_match = None
    react_id = "A"
    if theme_idx != -1:
        window_start = max(0, theme_idx - 100)
        window_end = min(len(content), theme_idx + 500)
        window_text = content[window_start:window_end]
        theme_pattern = re.compile(
            r'([A-Za-z0-9_$]+)\.createElement\(([A-Za-z0-9_$]+),\{label:"Theme",.*?onSelect:[A-Za-z0-9_$]+\}\)'
        )
        theme_match = theme_pattern.search(window_text)
        if theme_match:
            react_id = theme_match.group(1)

    if not hook_match or not theme_match:
        print(f"[web-patch] Desktop Mode patterns not matched: hook={bool(hook_match)}, theme={bool(theme_match)}", file=sys.stderr)
        return content, False

    orig_hook = hook_match.group(1)
    injected_hook = (
        f"var [isDesktop,setIsDesktop]=(0,{react_id}.useState)(()=>{{"
        "try{if(window.Android&&typeof window.Android.isDesktopMode==='function')return window.Android.isDesktopMode();"
        "var s=localStorage.getItem('ag_desktop_mode');return s===null?!1:s==='true'}catch(_){return !1}});"
        f"var onDesktopToggle=(0,{react_id}.useCallback)(v=>{{"
        "setIsDesktop(v);try{localStorage.setItem('ag_desktop_mode',String(v));"
        "if(window.Android&&typeof window.Android.setDesktopMode==='function')window.Android.setDesktopMode(v)}catch(_){}},[]);"
        + orig_hook
    )

    item_comp = "v3"
    switch_comp = "dX"
    re_idx = content.find('rightElement:')
    if re_idx != -1:
        re_window = content[max(0, re_idx - 150):min(len(content), re_idx + 150)]
        item_m = re.search(
            r'([A-Za-z0-9_$]+)\.createElement\(([A-Za-z0-9_$]+),\{label:[^,]+,description:[^,]+,rightElement:',
            re_window,
        )
        if item_m:
            item_comp = item_m.group(2)
        sw_m = re.search(r'rightElement:[A-Za-z0-9_$]+\.createElement\(([A-Za-z0-9_$]+),\{checked:', re_window)
        if sw_m:
            switch_comp = sw_m.group(1)

    orig_theme = theme_match.group(0)
    injected_theme = (
        orig_theme
        + f',{react_id}.createElement({item_comp},{{label:"Desktop Mode",description:"Use desktop viewport and user agent for the workspace",'
        + f'rightElement:{react_id}.createElement({switch_comp},{{checked:isDesktop,onCheckedChange:onDesktopToggle}})}})'
    )

    content = content.replace(orig_hook, injected_hook, 1)
    content = content.replace(orig_theme, injected_theme, 1)
    print("[web-patch] Successfully patched Desktop Mode toggle into main.js")
    return content, True


def patch_conversation_search(content):
    if "conversation-search-button" in content or "onSearchClick" in content:
        print("[web-patch] Conversation Search button already present in main.js")
        return content, True

    # 1. Update ZNb mapping if present
    znb_orig = 'const ZNb={more_vert:"More actions",'
    znb_new = 'const ZNb={search:"Search in conversation",more_vert:"More actions",'
    if znb_orig in content:
        content = content.replace(znb_orig, znb_new, 1)

    # 2. Locate titlebar-more-actions menu
    target = '{iconName:"more_vert",dataTestId:"titlebar-more-actions"}'
    idx = content.find(target)
    if idx == -1:
        print("[web-patch] titlebar-more-actions target not found in main.js", file=sys.stderr)
        return content, False

    # 3. Locate hook in k4
    hook_idx = content.rfind("setEditingCascadeId", 0, idx)
    if hook_idx == -1:
        print("[web-patch] setEditingCascadeId hook not found in k4", file=sys.stderr)
        return content, False

    window_hook = content[hook_idx - 50:hook_idx + 100]
    m_hook = re.search(
        r'([A-Za-z0-9_$]+)=\(0,([A-Za-z0-9_$]+)\.useCallback\)\(\(\)=>\{([A-Za-z0-9_$]+)&&[\s\r\n]*([A-Za-z0-9_$]+)\([A-Za-z0-9_$]+\.actions\.setEditingCascadeId\(\3\)\)\},\[\4,\3\]\),',
        window_hook,
    )
    if not m_hook:
        print("[web-patch] hook pattern in k4 not matched", file=sys.stderr)
        return content, False

    orig_hook = m_hook.group(0)
    react_id = m_hook.group(2)
    cascade_var = m_hook.group(3)
    dispatch_var = m_hook.group(4)

    search_hook = (
        f'onSearchClick=(0,{react_id}.useCallback)(()=>{{'
        'var findInput=document.querySelector(\'input[placeholder="Find"],input[aria-label="Find"]\');'
        'if(findInput&&document.activeElement===findInput){'
        f'try{{if(typeof kn==="function"){{{dispatch_var}(kn({{tabId:{cascade_var}??"conversation",isFindBarVisible:!1}}));return}}}}catch(_){{}}'
        'var closeBtn=findInput.closest(\'.sticky\')?.querySelector(\'button\');'
        'if(closeBtn){closeBtn.click();return}'
        '}'
        f'try{{if(typeof kn==="function"){{{dispatch_var}(kn({{tabId:{cascade_var}??"conversation",isFindBarVisible:!0}}));if(typeof nn==="function"){dispatch_var}(nn({{tabId:{cascade_var}??"conversation"}}))}}}}catch(_){{}}'
        'try{var cmd=typeof eA==="function"?eA():null;if(cmd&&typeof cmd.executeCommand==="function")cmd.executeCommand("conversationView.findInConversation")}catch(_){}'
        'try{var convo=document.querySelector(\'[data-testid="conversation-view"]\')||document.activeElement||document;'
        'convo.dispatchEvent(new KeyboardEvent(\'keydown\',{key:\'f\',code:\'KeyF\',keyCode:70,which:70,ctrlKey:!0,metaKey:!0,bubbles:!0,cancelable:!0}))}catch(_){}'
        'setTimeout(()=>{try{var inp=document.querySelector(\'input[placeholder="Find"],input[aria-label="Find"]\');if(inp){inp.focus();inp.select()}}catch(_){}},60);'
        f'}},[{cascade_var},{dispatch_var}]),'
        + orig_hook
    )
    content = content.replace(orig_hook, search_hook, 1)

    # 4. Locate createElement for titlebar-more-actions menu
    idx = content.find(target)
    window_menu = content[max(0, idx - 120):idx + len(target) + 20]
    m_menu = re.search(
        r'([A-Za-z0-9_$]+)\.createElement\(([A-Za-z0-9_$]+),null,\1\.createElement\(([A-Za-z0-9_$]+),\{asChild:!0\},\1\.createElement\(([A-Za-z0-9_$]+),\{iconName:"more_vert",dataTestId:"titlebar-more-actions"\}\)\)',
        window_menu,
    )
    if not m_menu:
        print("[web-patch] menu pattern in k4 not matched", file=sys.stderr)
        return content, False

    orig_menu = m_menu.group(0)
    btn_comp = m_menu.group(4)

    search_btn = f'{react_id}.createElement({btn_comp},{{iconName:"search",dataTestId:"conversation-search-button","aria-label":"Search in conversation",title:"Search in conversation",onClick:onSearchClick}}),'
    injected_menu = search_btn + orig_menu
    content = content.replace(orig_menu, injected_menu, 1)

    # 5. Patch fallback when H.length === 0 in k4 so Search button is present even in fresh projects
    idx = content.find(target)
    end_k4_idx = content.find(':null};', idx)
    if end_k4_idx != -1 and end_k4_idx - idx < 2000:
        orig_end = content[end_k4_idx:end_k4_idx+7]
        injected_end = f':{react_id}.createElement({btn_comp},{{iconName:"search",dataTestId:"conversation-search-button","aria-label":"Search in conversation",title:"Search in conversation",onClick:onSearchClick}})}};'
        content = content[:end_k4_idx] + injected_end + content[end_k4_idx+7:]

    print("[web-patch] Successfully patched Conversation Search button left to three-dot menu into main.js")
    return content, True


def patch_include_user_inputs_in_search(content):
    if 'c.getAttribute("data-testid")==="user-input-step"' in content:
        print("[web-patch] User inputs already included in search in main.js")
        return content, True

    # 1. Update sC so text in user-input-step or with data-quotable is not rejected by select-none
    sc_pattern = re.compile(
        r'(if\(c\.hasAttribute\("data-find-ignore"\)\)return!0;)(if\(![A-Za-z0-9_$]+&&\([A-Za-z0-9_$]+\.classList\.contains\("select-text"\))'
    )
    sc_match = sc_pattern.search(content)
    if not sc_match:
        print("[web-patch] sC pattern not matched for user input search inclusion", file=sys.stderr)
        return content, False

    sc_injected = (
        sc_match.group(1)
        + 'if(c.hasAttribute("data-quotable")||c.getAttribute("data-testid")==="user-input-step"||c.getAttribute("aria-label")==="User message")e=!0;'
        + sc_match.group(2)
    )
    content = content[:sc_match.start()] + sc_injected + content[sc_match.end():]

    # 2. Add select-text to bwb to ensure quotable and searchable text
    bwb_target = 'className:"whitespace-pre-wrap text-sm"'
    if bwb_target in content:
        content = content.replace(bwb_target, 'className:"whitespace-pre-wrap text-sm select-text"', 1)

    print("[web-patch] Successfully patched user input messages into in-conversation search in main.js")
    return content, True


def patch_search_toggles(content):
    target = 'var e_b=()=>{var {options:a,setOptions:b}=EP()'
    idx = content.find(target)
    if idx == -1:
        if "tBtn" in content and "Match Case (Aa)" in content:
            print("[web-patch] Search toggles already enhanced in main.js")
            return content, True
        print("[web-patch] e_b target not found in main.js", file=sys.stderr)
        return content, False

    end_idx = content.find('};', idx)
    if end_idx == -1:
        print("[web-patch] end of e_b not found in main.js", file=sys.stderr)
        return content, False

    orig_eb = content[idx:end_idx + 2]

    injected_eb = (
        'var e_b=()=>{var {options:a,setOptions:b}=EP(),c=PC(),e=PC(),f=PC(),g=(0,A.useCallback)(h=>{b(h)},[b]);'
        'var tBtn=(active,onClick,iconName,label,id)=>A.createElement("div",{"data-tooltip-id":id,className:"flex items-center"},'
        'A.createElement("button",{type:"button",'
        'onPointerDown:h=>{h.preventDefault();h.stopPropagation()},'
        'onClick:h=>{h.preventDefault();h.stopPropagation();onClick()},'
        '"aria-label":label,"aria-pressed":active,'
        'className:aj("px-1.5 py-0.5 min-w-[24px] min-h-[22px] flex items-center justify-center rounded transition-all outline-none text-xs",'
        'active?"bg-primary text-primary-foreground font-bold shadow-xs":"text-muted-foreground hover:text-foreground hover:bg-muted/80")},'
        'A.createElement(W,{name:iconName,size:14})),'
        'A.createElement(ty,{id:id,place:"bottom-end"},label));'
        'return A.createElement("div",{className:"flex items-center gap-1 pr-1 ml-1 pl-1"},'
        'tBtn(a.caseSensitive,()=>g({caseSensitive:!a.caseSensitive}),"match_case","Match Case (Aa)",c),'
        'tBtn(a.wholeWord,()=>g({wholeWord:!a.wholeWord}),"match_word","Match Whole Word (ab)",e),'
        'tBtn(a.useRegex,()=>g({useRegex:!a.useRegex}),"regular_expression","Use Regular Expression (.*)",f))};'
    )

    content = content.replace(orig_eb, injected_eb, 1)
    print("[web-patch] Successfully patched Search Bar toggles with touch handling and active styling into main.js")
    return content, True


def patch_main_screen_universal_search(content):
    cs_flag = 'conversationSearchV2:{feature:!1'
    if cs_flag in content:
        content = content.replace(cs_flag, 'conversationSearchV2:{feature:!0', 1)
        print("[web-patch] Enabled conversationSearchV2 feature flag in main.js")

    pbb_target = 'f=!(!e.get("codeSearchPalette")?.enabled||c===void 0),g=!(!f||!e.get("conversationSearchV2"))'
    pbb_injected = 'f=!(!e.get("codeSearchPalette")?.enabled||c===void 0),g=!0'
    if pbb_target in content:
        content = content.replace(pbb_target, pbb_injected, 1)
        print("[web-patch] Enabled showUnifiedSearch in PBb component")

    frb_target = 'function fRb(){var a=Lj(),b=ER(),'
    frb_injected = (
        'function fRb(){'
        'var mainCmd=typeof eA==="function"?eA():null,switchConvo=typeof Nsb==="function"?Nsb():null;'
        'if(typeof window!=="undefined"){'
        'window.__agyOpenConversation=function(cid){'
        'try{if(switchConvo){switchConvo(cid);return}}catch(_){}'
        'try{window.location.hash="#/cascade/"+cid}catch(_){}'
        '};'
        'if(window.__agyPendingCascadeId){'
        'var pCid=window.__agyPendingCascadeId;delete window.__agyPendingCascadeId;'
        'setTimeout(function(){window.__agyOpenConversation(pCid)},150);'
        '}'
        '}'
        'var a=Lj(),b=ER(),'
    )
    if frb_target in content:
        content = content.replace(frb_target, frb_injected, 1)

    if "main-search-button" in content:
        print("[web-patch] Main screen universal search button already present in main.js")
        return content, True

    idx = content.find("mobile-open-settings")
    if idx == -1:
        print("[web-patch] mobile-open-settings target not found in main.js", file=sys.stderr)
        return content, False

    window_start = max(0, idx - 150)
    window_end = min(len(content), idx + 80)
    window_text = content[window_start:window_end]

    pattern = re.compile(
        r'([A-Za-z0-9_$]+)&&([A-Za-z0-9_$]+)&&([A-Za-z0-9_$]+)\.createElement\(([A-Za-z0-9_$]+),\{iconName:"settings",.*?dataTestId:"mobile-open-settings"\}\)'
    )
    m = pattern.search(window_text)
    if not m:
        print("[web-patch] mobile-open-settings element pattern not matched in fRb", file=sys.stderr)
        return content, False

    orig_elem = m.group(0)
    b_var = m.group(1)
    react_id = m.group(3)
    btn_comp = m.group(4)

    search_btn = (
        f'{b_var}&&{react_id}.createElement({btn_comp},{{iconName:"search",'
        'onClick:()=>{'
        'try{if(mainCmd&&typeof mainCmd.executeCommand==="function"){mainCmd.executeCommand("openConvoPickerV2");return}}catch(_){}'
        'try{if(mainCmd&&typeof mainCmd.executeCommand==="function"){mainCmd.executeCommand("openConvoPicker");return}}catch(_){}'
        'try{window.dispatchEvent(new KeyboardEvent("keydown",{key:"k",code:"KeyK",keyCode:75,which:75,ctrlKey:!0,altKey:!0,bubbles:!0,cancelable:!0}))}catch(_){}'
        'try{window.dispatchEvent(new KeyboardEvent("keydown",{key:"k",code:"KeyK",keyCode:75,which:75,ctrlKey:!0,metaKey:!0,bubbles:!0,cancelable:!0}))}catch(_){}},'
        '"aria-label":"Search all projects",title:"Search all projects",dataTestId:"main-search-button"}),'
    )
    injected_elem = search_btn + orig_elem
    content = content.replace(orig_elem, injected_elem, 1)

    print("[web-patch] Successfully patched main screen universal search button into main.js")
    return content, True


def patch_remove_sound(content):
    sqc_target = "async function sqc(a,b){var c=d,e=d;try{if(a&&M9(b)){"
    sqc_injected = "async function sqc(a,b){return;var c=d,e=d;try{if(a&&M9(b)){"
    if sqc_target in content:
        content = content.replace(sqc_target, sqc_injected, 1)
        print("[web-patch] Disabled agent sound player sqc")

    sound_target = '{cascadeDone:"/antigravityCascadeDone.mp3",actionRequired:"/antigravityActionRequired.mp3"}'
    sound_injected = '{cascadeDone:"",actionRequired:""}'
    if sound_target in content:
        content = content.replace(sound_target, sound_injected, 1)
        print("[web-patch] Stripped notification sound files")

    return content, True


def patch_cancel_stop_hook(content):
    us_target = 'if(N("cancel_message_stream"),\nf)'
    us_injected = (
        'if((function(){try{if(typeof window!=="undefined"){'
        'if(!window.__agyCancelledRuns)window.__agyCancelledRuns=new Set();'
        'if(f){'
        'window.__agyCancelledRuns.add(f);'
        'if(window.Android&&typeof window.Android.cancelNotification==="function")window.Android.cancelNotification("cascade_prog_"+f,0);'
        '}'
        '}}catch(_){}})()||!0,N("cancel_message_stream"),\nf)'
    )
    if us_target in content:
        content = content.replace(us_target, us_injected, 1)
        print("[web-patch] Patched cancel_message_stream to track user task cancellation")
    return content, True


def patch_agent_notifications(content):
    if "cascade_prog_" in content:
        print("[web-patch] Agent notifications already patched in main.js")
        return content, True

    # 1. Patch Redux middleware rm.match(n) for direct multi-conversation progress & completion tracking
    rm_target = 'return rm.match(n)?(q=m(n),'
    rm_injected = (
        'return rm.match(n)?('
        '(function(pld){try{'
        'if(typeof window!=="undefined"&&window.Android&&pld){'
        'if(!window.__agyActiveRuns)window.__agyActiveRuns=new Set();'
        'if(!window.__agyCancelledRuns)window.__agyCancelledRuns=new Set();'
        'if(Array.isArray(pld.updates)){'
        'for(let [cid,s] of pld.updates){'
        'if(!cid||!s)continue;'
        'if(s.notFullyIdle){'
        'window.__agyActiveRuns.add(cid);'
        'var t=s.summary||s.title||"Agent running";'
        'var st=s.stepCount?("Step "+s.stepCount+": "):"";'
        'var bd=st+(s.preview||"Working on task...");'
        'window.Android.postNotification("agent_progress",t,bd,cid,true,-1);'
        '}else if(window.__agyActiveRuns.has(cid)){'
        'window.__agyActiveRuns.delete(cid);'
        'window.Android.cancelNotification("cascade_prog_"+cid,0);'
        'var isCancelled=(s.latestExecutorTerminationReason===2||s.latestExecutorTerminationReason===1||window.__agyCancelledRuns.has(cid));'
        'if(isCancelled){'
        'window.__agyCancelledRuns.delete(cid);'
        '}else{'
        'var ct=s.summary||s.title||"Agent completed";'
        'var cb=s.preview||"Agent finished the task";'
        'window.Android.postNotification("agent_completed",ct,cb,cid,false,-1);'
        '}'
        '}'
        '}'
        'if(Array.isArray(pld.deletes)){'
        'for(let cid of pld.deletes){'
        'if(window.__agyActiveRuns.has(cid)){'
        'window.__agyActiveRuns.delete(cid);'
        'window.Android.cancelNotification("cascade_prog_"+cid,0);'
        '}'
        'if(window.__agyCancelledRuns)window.__agyCancelledRuns.delete(cid);'
        '}'
        '}'
        '}'
        '}catch(_){}})(n.payload),'
        'q=m(n),'
    )
    if rm_target in content:
        content = content.replace(rm_target, rm_injected, 1)
        print("[web-patch] Patched Redux rm middleware with multi-conversation progress and completion notifications")

    # 2. Patch HDa for live real-time progress and completion tracking per conversation
    hda_target = 'h.notFullyIdle?a.add(b):a.delete(b)&&(h.trajectoryMetadata?.parentConversationId||e.push([b,h]))'
    hda_injected = (
        'h.notFullyIdle?('
        'a.add(b),'
        '(function(){try{if(typeof window!=="undefined"&&window.Android&&typeof window.Android.postNotification==="function"){'
        'var t=h.summary||h.title||"Agent running";'
        'var st=h.stepCount?("Step "+h.stepCount+": "):"";'
        'var bd=st+(h.preview||"Working on task...");'
        'var pr=-1;'
        'window.Android.postNotification("agent_progress",t,bd,b,true,pr);'
        '}}catch(_){}})()'
        '):('
        'a.delete(b)&&('
        '(function(){try{if(typeof window!=="undefined"&&window.Android){'
        'if(!window.__agyCancelledRuns)window.__agyCancelledRuns=new Set();'
        'window.Android.cancelNotification("cascade_prog_"+b,0);'
        'var isCancelled=(h.latestExecutorTerminationReason===2||h.latestExecutorTerminationReason===1||window.__agyCancelledRuns.has(b));'
        'if(isCancelled){'
        'window.__agyCancelledRuns.delete(b);'
        '}else{'
        'var ct=h.summary||h.title||"Agent completed";'
        'var cb=h.preview||"Agent finished the task";'
        'window.Android.postNotification("agent_completed",ct,cb,b,false,-1);'
        '}'
        '}}catch(_){}})(),'
        '(h.trajectoryMetadata?.parentConversationId||e.push([b,h]))'
        ')'
        ')'
    )
    if hda_target in content:
        content = content.replace(hda_target, hda_injected, 1)
        print("[web-patch] Patched HDa stream listener with multi-conversation progress and completion notifications")

    # 3. Patch KDa for required actions (permissions, questions)
    kda_act_target = 'r&&(f.actionRequired&&g?.({soundFile:f.actionRequired}),c?.(r))'
    kda_act_injected = (
        'r&&('
        '(function(){try{if(typeof window!=="undefined"&&window.Android&&typeof window.Android.postNotification==="function"){'
        'window.Android.postNotification("agent_completed",r.title||"Action requires attention",r.body||"The agent needs your input.",r.payload?.cascadeId||"",false,-1);'
        '}}catch(_){}})(),'
        'c?.(r)'
        ')'
    )
    if kda_act_target in content:
        content = content.replace(kda_act_target, kda_act_injected, 1)
        print("[web-patch] Patched KDa with agent action/question notification (silent)")

    # 4. Patch KDa for cascadeDone completion dispatch
    kda_fin_target = 'c?.({id:`agent-finished-${l}-${Date.now()}`,title:e,body:q.summary||"Agent finished",payload:{cascadeId:l,type:"request_action",workspaceUri:void 0}})'
    kda_fin_injected = (
        '('
        '(function(){try{if(typeof window!=="undefined"&&window.Android&&typeof window.Android.postNotification==="function"){'
        'window.Android.cancelNotification("cascade_prog_"+l,0);'
        'if(window.__agyCancelledRuns&&window.__agyCancelledRuns.has(l)){'
        'window.__agyCancelledRuns.delete(l);'
        '}else{'
        'window.Android.postNotification("agent_completed",q.summary||"Agent completed",q.preview||"Agent finished task",l,false,-1);'
        '}'
        '}}catch(_){}})(),'
        'c?.({id:`agent-finished-${l}-${Date.now()}`,title:e,body:q.summary||"Agent finished",payload:{cascadeId:l,type:"request_action",workspaceUri:void 0}})'
        ')'
    )
    if kda_fin_target in content:
        content = content.replace(kda_fin_target, kda_fin_injected, 1)
        print("[web-patch] Patched KDa completion dispatcher with agent_completed notification")

    return content, True


def patch_auto_retry_on_internet(content):
    v_target = 'var v=w=>({label:w,onClick:()=>{t({type:7,cascadeId:u})}});'
    v_injected = (
        'var v=w=>{'
        'try{if(typeof window!=="undefined")window.__agyPendingRetry=()=>{try{t({type:7,cascadeId:u})}catch(_){}};}catch(_){}'
        'return {label:w,onClick:()=>{try{if(window.__agyPendingRetry)window.__agyPendingRetry=null;}catch(_){}t({type:7,cascadeId:u})}};'
        '};'
    )
    if v_target in content:
        content = content.replace(v_target, v_injected, 1)
        print("[web-patch] Hooked model retry builder with auto-retry state")

    net_hook = '/* AGY AutoRetry Hook */'
    if net_hook not in content:
        listener = (
            ';/* AGY AutoRetry Hook */(function(){try{if(typeof window!=="undefined"&&!window.__agyAutoRetryInstalled){'
            'window.__agyAutoRetryInstalled=!0;'
            'var triggerRetry=function(){'
            'setTimeout(function(){'
            'if(typeof window.__agyPendingRetry==="function"){'
            'try{console.log("[AGY AutoRetry] Internet reconnected, auto-retrying...");window.__agyPendingRetry();window.__agyPendingRetry=null;return;}catch(_){}'
            '}'
            'try{'
            'var btns=document.querySelectorAll("button");'
            'for(var i=0;i<btns.length;i++){'
            'var txt=(btns[i].textContent||"").trim();'
            'if(txt==="Retry"||txt==="Try again"){'
            'console.log("[AGY AutoRetry] Clicking button on network restore:",txt);'
            'btns[i].click();break;'
            '}'
            '}'
            '}catch(_){}'
            '},500);'
            '};'
            'window.addEventListener("online",triggerRetry);'
            'window.addEventListener("agy:network-online",triggerRetry);'
            '}}catch(_){}})();'
        )
        content = content + listener
        print("[web-patch] Injected automatic network retry listeners")
    return content, True


def patch_conversation_rename_persistence(content):
    # 1. Preserve custom title in ona
    ona_target = 'function ona(a,b,c,e){c.summary||(a=e==="local"?a.summaries[b]:a.externalSummaries?.[b],a?.summary&&(c.summary=a.summary))}'
    ona_injected = (
        'function ona(a,b,c,e){'
        'var prev=e==="local"?a.summaries[b]:a.externalSummaries?.[b];'
        'if(prev){'
        'if(!c.summary&&prev.summary)c.summary=prev.summary;'
        'if(prev.annotations?.title){'
        'if(!c.annotations)c.annotations=p(te.ConversationAnnotationsSchema,{});'
        'if(!c.annotations.title)c.annotations.title=prev.annotations.title;'
        '}'
        '}'
        '}'
    )
    if ona_target in content:
        content = content.replace(ona_target, ona_injected, 1)
        print("[web-patch] Patched ona to preserve custom conversation title")

    # 2. Support title in pna
    pna_target = 'function pna(a,b){a.annotations||(a.annotations=p(te.ConversationAnnotationsSchema,{}));a=a.annotations;b.archived!==void 0&&(a.archived=b.archived);'
    pna_injected = 'function pna(a,b){a.annotations||(a.annotations=p(te.ConversationAnnotationsSchema,{}));a=a.annotations;b.title!==void 0&&(a.title=b.title);b.archived!==void 0&&(a.archived=b.archived);'
    if pna_target in content:
        content = content.replace(pna_target, pna_injected, 1)
        print("[web-patch] Patched pna to support annotations.title")

    # 3. Read title from persistent store in bNa
    bna_target = 'bNa=(a,b)=>{if(b)return a=(a.trajectorySummaries?.summaries??tm.summaries)[b],a?.annotations?.title?.trim()||\na?.summary?.trim()||void 0};'
    bna_injected = (
        'bNa=(a,b)=>{'
        'if(!b)return void 0;'
        'try{'
        'var saved=typeof localStorage!=="undefined"?localStorage.getItem("agy_title_"+b):null;'
        'if(saved&&saved.trim())return saved.trim();'
        '}catch(_){}'
        'a=(a.trajectorySummaries?.summaries??tm.summaries)[b];'
        'var custom=a?.annotations?.title?.trim();'
        'if(custom){try{localStorage.setItem("agy_title_"+b,custom);}catch(_){}return custom;}'
        'return a?.summary?.trim()||void 0'
        '};'
    )
    if bna_target in content:
        content = content.replace(bna_target, bna_injected, 1)
        print("[web-patch] Patched bNa to read persistent renamed title")

    # 4. Save title to persistent store in handleRename
    rename_target = 'q({type:"updateOptimisticSummary",cascadeId:a,optimisticSummaryText:ma});try{pa(await ja(f(a,p(te.ConversationAnnotationsSchema,{title:ma}),!0)))'
    rename_injected = (
        'try{if(typeof localStorage!=="undefined")localStorage.setItem("agy_title_"+a,ma);}catch(_){}'
        'q({type:"updateOptimisticSummary",cascadeId:a,optimisticSummaryText:ma});try{pa(await ja(f(a,p(te.ConversationAnnotationsSchema,{title:ma}),!0)))'
    )
    if rename_target in content:
        content = content.replace(rename_target, rename_injected, 1)
        print("[web-patch] Patched handleRename to persistently save conversation title")

    return content, True


def patch_clipboard_paste_full(content):
    r8a_target = 'function r8a(a,b,c){var e=b.getData("text/plain");for(let f of q8a(a)){let g=b.getData(f);if(g&&(f!=="text/html"||g!==e)&&p8a(a.$importMimeType[f],g,c,b))return!0}return!1}'
    r8a_injected = (
        'function r8a(a,b,c){'
        'var e=b.getData("text/plain");'
        'if((!e||e.trim()==="")&&typeof window!=="undefined"&&window.Android&&typeof window.Android.getClipboardText==="function"){'
        'try{e=window.Android.getClipboardText()||e;}catch(_){}'
        '}'
        'if(e&&e.length>0&&a.$importMimeType["text/plain"]){'
        'if(p8a(a.$importMimeType["text/plain"],e,c,b))return!0;'
        '}'
        'for(let f of q8a(a)){'
        'let g=b.getData(f);'
        'if(g&&(f!=="text/html"||g!==e)&&p8a(a.$importMimeType[f],g,c,b))return!0;'
        '}'
        'return!1;'
        '}'
    )
    if r8a_target in content:
        content = content.replace(r8a_target, r8a_injected, 1)
        print("[web-patch] Patched r8a to guarantee full clipboard text paste without truncation")
    return content, True


def patch_projects_storage_path(content):
    init_path_target = 'initialPath:b?b.fsPath:ch?"C:/":"/"'
    init_path_injected = 'initialPath:"/storage/emulated/0/Documents"'
    if init_path_target in content:
        content = content.replace(init_path_target, init_path_injected, 1)
        print("[web-patch] Changed default projects directory to /storage/emulated/0/Documents")

    del_target = 'this.deleteProject=async e=>{var f=d,g=d;try{g(await f(this.lsClient.deleteProject({id:e})))}finally{f()}};'
    del_injected = (
        'this.deleteProject=async e=>{var f=d,g=d;try{'
        'try{'
        'var pr=this.richProjectsProvider?.getState()?.get(e)?.project;'
        'var wUri=pr?.workspaces?.[0]?.workspaceFolderAbsoluteUri||pr?.workspaceFolderUri;'
        'if(wUri&&typeof window!=="undefined"&&window.Android&&typeof window.Android.deleteProjectFolder==="function"){'
        'window.Android.deleteProjectFolder(wUri);'
        '}'
        '}catch(_){}'
        'g(await f(this.lsClient.deleteProject({id:e})))'
        '}finally{f()}};'
    )
    if del_target in content:
        content = content.replace(del_target, del_injected, 1)
        print("[web-patch] Patched deleteProject to delete project directory from storage")
    return content, True


def patch_capture_providers(content):
    zj_target = 'function Zj(){var {sidebarSectionsProvider:a}=Xj();return a}'
    zj_injected = 'function Zj(){var {sidebarSectionsProvider:a}=Xj();try{if(typeof window!=="undefined")window.__agySidebarProvider=a;}catch(_){}return a}'
    if zj_target in content:
        content = content.replace(zj_target, zj_injected, 1)
        print("[web-patch] Exposed sidebarSectionsProvider on window.__agySidebarProvider")
    return content, True


def patch_full_text_conversation_search(content):
    if "natStr=window.Android.searchConversations" in content:
        print("[web-patch] Full text conversation search already present in main.js")
        return content, True

    cbb_target = 'let J=H(await G(c({query:b,limit:50,signal:D.signal})));'
    cbb_injected = (
        'let J;'
        'if(typeof window!=="undefined"&&window.Android&&typeof window.Android.searchConversations==="function"){'
        'try{'
        'var natStr=window.Android.searchConversations(b,50);'
        'if(natStr){'
        'var natJson=JSON.parse(natStr);'
        'if(natJson&&Array.isArray(natJson.results)){'
        'J={results:natJson.results,indexStale:!1,searchFailed:!1};'
        '}'
        '}'
        '}catch(natErr){console.warn("[AGY Search] native search error:",natErr);}'
        '}'
        'if(!J){'
        'J=H(await G(c({query:b,limit:50,signal:D.signal})));'
        '}'
    )
    if cbb_target in content:
        content = content.replace(cbb_target, cbb_injected, 1)
        print("[web-patch] Successfully patched cBb with native full-text conversation search")
    else:
        print("[web-patch] cBb target not found in main.js", file=sys.stderr)
        return content, False

    nbb_flag_target = '],[q]),u=Lj().get("conversationSearchV2")??!1,'
    nbb_flag_injected = '],[q]),u=!0,'
    if nbb_flag_target in content:
        content = content.replace(nbb_flag_target, nbb_flag_injected, 1)
        print("[web-patch] Successfully enabled conversationSearchV2 in nBb")

    nbb_res_target = 'B?v.length===0?[]:[{id:"Results",preScored:!0,items:v.map(aBb)}]:t:r'
    nbb_res_injected = 'B?v.length===0?r:[{id:"Results",preScored:!0,items:v.map(aBb)}]:t:r'
    if nbb_res_target in content:
        content = content.replace(nbb_res_target, nbb_res_injected, 1)
        print("[web-patch] Successfully patched nBb results with fallback")

    kbb_target = 'h=f==="Code Search"?fL(`${k} ${l}`,b)?c?2:1:0:fL(k,b)?2:fL(l,b)?1:0'
    kbb_injected = 'h=f==="Conversations"&&g.length>0?2:(f==="Code Search"?fL(`${k} ${l}`,b)?c?2:1:0:fL(k,b)?2:fL(l,b)?1:0)'
    if kbb_target in content:
        content = content.replace(kbb_target, kbb_injected, 1)
        print("[web-patch] Successfully prioritized Conversations in kBb")

    return content, True


def patch_backup_restore(content):
    if "BackupRestoreScreen" in content:
        print("[web-patch] Backup and Restore already patched in main.js")
        return content, True

    # 1. Update Gtb map to include BackupRestore
    gtb_target = 'ProvideFeedback:"Provide Feedback",'
    gtb_injected = 'ProvideFeedback:"Provide Feedback",BackupRestore:"Backup and Restore",'
    if gtb_target in content:
        content = content.replace(gtb_target, gtb_injected, 1)
        print("[web-patch] Added BackupRestore to Gtb mapping")

    # 2. Add Backup and Restore to mobile settings list in jNb
    jnb_target = '(b.hideProvideFeedback?[]:["Provide Feedback"])'
    jnb_injected = '(b.hideProvideFeedback?[]:["Provide Feedback"]),"Backup and Restore"'
    if jnb_target in content:
        content = content.replace(jnb_target, jnb_injected, 1)
        print("[web-patch] Added Backup and Restore to jNb mobile settings screen list")

    # 3. Add Backup and Restore to desktop settings sidebar
    sidebar_target = '!f.hideProvideFeedback&&A.createElement(Q3,{text:"Provide Feedback",onClick:()=>{D(qX("Provide Feedback"))},isActive:E&&c==="Provide Feedback"})'
    sidebar_injected = (
        '!f.hideProvideFeedback&&A.createElement(Q3,{text:"Provide Feedback",onClick:()=>{D(qX("Provide Feedback"))},isActive:E&&c==="Provide Feedback"}),'
        'A.createElement(Q3,{text:"Backup and Restore",onClick:()=>{D(qX("Backup and Restore"))},isActive:E&&c==="Backup and Restore"})'
    )
    if sidebar_target in content:
        content = content.replace(sidebar_target, sidebar_injected, 1)
        print("[web-patch] Added Backup and Restore to desktop sidebar")

    # 4. Add Backup and Restore to fNb switcher (mobile)
    fnb_target = 'case "Provide Feedback":return A.createElement(H_,null);'
    fnb_injected = (
        'case "Provide Feedback":return A.createElement(H_,null);'
        'case "Backup and Restore":return A.createElement(BackupRestoreScreen,null);'
    )
    if fnb_target in content:
        content = content.replace(fnb_target, fnb_injected, 1)
        print("[web-patch] Added Backup and Restore to fNb screen switcher")

    # 5. Add Backup and Restore to desktop screen view container
    view_target = 'A.createElement("div",{style:{display:b==="Provide Feedback"?"block":"none"}},A.createElement(H_,null)),'
    view_injected = (
        'A.createElement("div",{style:{display:b==="Provide Feedback"?"block":"none"}},A.createElement(H_,null)),'
        'A.createElement("div",{style:{display:b==="Backup and Restore"?"block":"none"}},A.createElement(BackupRestoreScreen,null)),'
    )
    if view_target in content:
        content = content.replace(view_target, view_injected, 1)
        print("[web-patch] Added Backup and Restore to desktop view container")

    # 6. Define BackupRestoreScreen component before H_
    h_target = 'var H_=()=>'
    backup_restore_comp = (
        'var BackupRestoreScreen=()=>{\n'
        'var [status,setStatus]=(0,A.useState)(null);\n'
        'var [isProcessing,setIsProcessing]=(0,A.useState)(!1);\n'
        'var [projects,setProjects]=(0,A.useState)([]);\n'
        'var [selectedProject,setSelectedProject]=(0,A.useState)("all");\n'
        'var [conversations,setConversations]=(0,A.useState)([]);\n'
        'var [selectedConversation,setSelectedConversation]=(0,A.useState)("all");\n'
        'var [showRestartPrompt,setShowRestartPrompt]=(0,A.useState)(!1);\n'
        'var [restartMessage,setRestartMessage]=(0,A.useState)("");\n'
        '(0,A.useEffect)(()=>{\n'
        'try{\n'
        'if(typeof window!=="undefined"&&window.Android&&typeof window.Android.listProjects==="function"){\n'
        'var pList=JSON.parse(window.Android.listProjects()||"[]");\n'
        'if(Array.isArray(pList))setProjects(pList);\n'
        '}\n'
        '}catch(_){}\n'
        'try{\n'
        'if(typeof window!=="undefined"&&window.Android&&typeof window.Android.listConversations==="function"){\n'
        'var cList=JSON.parse(window.Android.listConversations()||"[]");\n'
        'if(Array.isArray(cList))setConversations(cList);\n'
        '}\n'
        '}catch(_){}\n'
        'if(typeof window!=="undefined"){\n'
        'window.__onBackupRestoreStatus=function(res){\n'
        'setIsProcessing(!1);\n'
        'if(typeof res==="string"){try{res=JSON.parse(res)}catch(_){res={message:res}}}\n'
        'setStatus(res);\n'
        'if(res&&res.success&&(res.type==="restore_conversation"||res.type==="restore_projects")){\n'
        'setRestartMessage(res.type==="restore_conversation"?"Conversations restored successfully. Would you like to restart the app now to reload all conversations?":"Projects restored successfully. Would you like to restart the app now to reload your workspace?");\n'
        'setShowRestartPrompt(!0);\n'
        '}\n'
        '};\n'
        'return function(){\n'
        'if(typeof window!=="undefined")window.__onBackupRestoreStatus=null;\n'
        '};\n'
        '}\n'
        '},[]);\n'
        'var onBackupConvos=()=>{\n'
        'setIsProcessing(!0);\n'
        'setStatus({type:"info",message:"Opening file picker to choose backup location..."});\n'
        'try{\n'
        'if(window.Android&&typeof window.Android.backupConversations==="function")window.Android.backupConversations(selectedConversation);\n'
        'else{setIsProcessing(!1);setStatus({type:"error",message:"Android native bridge unavailable."})}\n'
        '}catch(err){setIsProcessing(!1);setStatus({type:"error",message:err.message||String(err)})}\n'
        '};\n'
        'var onRestoreConvos=()=>{\n'
        'setIsProcessing(!0);\n'
        'setStatus({type:"info",message:"Opening file picker to select backup archive..."});\n'
        'try{\n'
        'if(window.Android&&typeof window.Android.restoreConversations==="function")window.Android.restoreConversations();\n'
        'else{setIsProcessing(!1);setStatus({type:"error",message:"Android native bridge unavailable."})}\n'
        '}catch(err){setIsProcessing(!1);setStatus({type:"error",message:err.message||String(err)})}\n'
        '};\n'
        'var onBackupProj=()=>{\n'
        'setIsProcessing(!0);\n'
        'setStatus({type:"info",message:"Opening file picker to save project ZIP..."});\n'
        'try{\n'
        'if(window.Android&&typeof window.Android.backupProjects==="function")window.Android.backupProjects(selectedProject);\n'
        'else{setIsProcessing(!1);setStatus({type:"error",message:"Android native bridge unavailable."})}\n'
        '}catch(err){setIsProcessing(!1);setStatus({type:"error",message:err.message||String(err)})}\n'
        '};\n'
        'var onRestoreProj=()=>{\n'
        'setIsProcessing(!0);\n'
        'setStatus({type:"info",message:"Opening file picker to select project ZIP..."});\n'
        'try{\n'
        'if(window.Android&&typeof window.Android.restoreProjects==="function")window.Android.restoreProjects(selectedProject!=="all"?selectedProject:"");\n'
        'else{setIsProcessing(!1);setStatus({type:"error",message:"Android native bridge unavailable."})}\n'
        '}catch(err){setIsProcessing(!1);setStatus({type:"error",message:err.message||String(err)})}\n'
        '};\n'
        'return A.createElement(G_,{title:"Backup and Restore"},\n'
        'A.createElement("div",{className:"space-y-6 max-w-2xl pb-8 p-1 relative"},\n'
        'showRestartPrompt&&A.createElement("div",{className:"fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4 animate-fade-in"},\n'
        'A.createElement("div",{className:"w-full max-w-sm rounded-2xl border border-border bg-popover p-5 space-y-4 shadow-xl text-popover-foreground"},\n'
        'A.createElement("div",{className:"space-y-1.5"},\n'
        'A.createElement("h3",{className:"text-base font-semibold m-0 text-foreground"},"Restart Required"),\n'
        'A.createElement("p",{className:"text-sm text-muted-foreground m-0 leading-relaxed"},restartMessage||"Restoration completed successfully. Would you like to restart the app now to apply all changes?")),\n'
        'A.createElement("div",{className:"flex items-center justify-end gap-2.5 pt-2"},\n'
        'A.createElement(tA,{variant:"secondary",size:"md",onClick:()=>setShowRestartPrompt(!1)},"Cancel"),\n'
        'A.createElement(tA,{variant:"primary",size:"md",onClick:()=>{\n'
        'setShowRestartPrompt(!1);\n'
        'try{if(window.Android&&typeof window.Android.restartApp==="function")window.Android.restartApp()}\n'
        'catch(_){}\n'
        '}},"OK")))),\n'
        'status&&A.createElement("div",{className:aj("p-3 rounded-xl border text-sm flex items-start gap-2.5 transition-all shadow-sm",\n'
        'status.success?"bg-emerald-500/10 border-emerald-500/30 text-emerald-300":\n'
        'status.type==="info"?"bg-sky-500/10 border-sky-500/30 text-sky-300":\n'
        '"bg-red-500/10 border-red-500/30 text-red-300")},\n'
        'A.createElement(W,{name:status.success?"check_circle":status.type==="info"?"info":"error",size:18,className:"shrink-0 mt-0.5"}),\n'
        'A.createElement("div",{className:"flex-1"},A.createElement("div",{className:"font-medium"},status.title||(status.success?"Success":status.type==="info"?"Processing":"Notice")),status.message&&A.createElement("div",{className:"text-xs opacity-90 mt-0.5"},status.message)),\n'
        'A.createElement("button",{type:"button",onClick:()=>setStatus(null),className:"text-xs opacity-60 hover:opacity-100 p-1 border-none bg-transparent cursor-pointer text-inherit"},"✕")),\n'
        'A.createElement("div",{className:"rounded-2xl border border-border bg-sidebar-muted/20 p-4 space-y-3.5 shadow-xs"},\n'
        'A.createElement("div",{className:"flex items-center gap-3"},\n'
        'A.createElement("div",{className:"p-2.5 rounded-xl bg-primary/10 text-primary flex items-center justify-center"},\n'
        'A.createElement(W,{name:"forum",size:22})),\n'
        'A.createElement("div",null,\n'
        'A.createElement("h3",{className:"font-semibold text-base text-foreground m-0"},"Conversations & Trajectories"),\n'
        'A.createElement("p",{className:"text-xs text-muted-foreground mt-0.5 mb-0 leading-relaxed"},\n'
        '"Fast, compressed archive of conversation history, transcripts, and brain artifacts (.zip). Space-saving and complete."))),\n'
        'A.createElement("div",{className:"space-y-1.5 pt-1"},\n'
        'A.createElement("label",{className:"block text-xs font-medium text-muted-foreground"},"Target Conversation Scope:"),\n'
        'A.createElement("select",{value:selectedConversation,onChange:e=>setSelectedConversation(e.target.value),className:"w-full p-2.5 rounded-xl bg-background border border-border text-foreground text-sm focus:outline-none focus:ring-1 focus:ring-primary cursor-pointer"},\n'
        'A.createElement("option",{value:"all"},"All Conversations (Complete History)"),\n'
        'conversations.map(c=>A.createElement("option",{key:c.id||c,value:c.id||c},"Conversation: "+(c.title||c.id||c))))),\n'
        'A.createElement("div",{className:"flex flex-wrap gap-2.5 pt-1"},\n'
        'A.createElement(tA,{variant:"primary",size:"md",disabled:isProcessing,onClick:onBackupConvos,className:"flex items-center gap-1.5"},\n'
        'A.createElement(W,{name:"upload",size:16}),"Backup Conversations"),\n'
        'A.createElement(tA,{variant:"secondary",size:"md",disabled:isProcessing,onClick:onRestoreConvos,className:"flex items-center gap-1.5"},\n'
        'A.createElement(W,{name:"download",size:16}),"Restore Conversations"))),\n'
        'A.createElement("div",{className:"rounded-2xl border border-border bg-sidebar-muted/20 p-4 space-y-3.5 shadow-xs"},\n'
        'A.createElement("div",{className:"flex items-center gap-3"},\n'
        'A.createElement("div",{className:"p-2.5 rounded-xl bg-primary/10 text-primary flex items-center justify-center"},\n'
        'A.createElement(W,{name:"folder_zip",size:22})),\n'
        'A.createElement("div",null,\n'
        'A.createElement("h3",{className:"font-semibold text-base text-foreground m-0"},"Project Files"),\n'
        'A.createElement("p",{className:"text-xs text-muted-foreground mt-0.5 mb-0 leading-relaxed"},\n'
        '"Backup and restore workspace projects as standard ZIP archives."))),\n'
        'A.createElement("div",{className:"space-y-1.5 pt-1"},\n'
        'A.createElement("label",{className:"block text-xs font-medium text-muted-foreground"},"Target Project Scope:"),\n'
        'A.createElement("select",{value:selectedProject,onChange:e=>setSelectedProject(e.target.value),className:"w-full p-2.5 rounded-xl bg-background border border-border text-foreground text-sm focus:outline-none focus:ring-1 focus:ring-primary cursor-pointer"},\n'
        'A.createElement("option",{value:"all"},"All Scratch Projects (Complete Workspace)"),\n'
        'projects.map(p=>A.createElement("option",{key:p,value:p},"Project: "+p)))),\n'
        'A.createElement("div",{className:"flex flex-wrap gap-2.5 pt-1"},\n'
        'A.createElement(tA,{variant:"primary",size:"md",disabled:isProcessing,onClick:onBackupProj,className:"flex items-center gap-1.5"},\n'
        'A.createElement(W,{name:"upload",size:16}),"Backup Projects (.zip)"),\n'
        'A.createElement(tA,{variant:"secondary",size:"md",disabled:isProcessing,onClick:onRestoreProj,className:"flex items-center gap-1.5"},\n'
        'A.createElement(W,{name:"download",size:16}),"Restore Projects (.zip)")))\n'
        '));\n};\n'
    )
    if h_target in content:
        content = content.replace(h_target, backup_restore_comp + h_target, 1)
        print("[web-patch] Successfully injected BackupRestoreScreen component before H_")
    else:
        print("[web-patch] H_ target not found in main.js", file=sys.stderr)
        return content, False

    return content, True


def patch_terminal_touch_scroll(content):
    # 1. Update CK(a) drawer swipe ignore check to include terminal selectors
    ck_target = 'function CK(a){return!!a?.closest("[data-base-ui-swipe-ignore]")}'
    ck_replacement = (
        'function CK(a){return!!a?.closest("[data-base-ui-swipe-ignore],[data-swipe-ignore],'
        '.xterm,[data-testid=\\"terminal-surface\\"],[data-testid=\\"terminal-view\\"],'
        '.terminal,.xterm-scrollable-element")}'
    )
    if ck_target in content:
        content = content.replace(ck_target, ck_replacement, 1)
        print("[web-patch] Successfully patched CK(a) swipe ignore for terminal")
    else:
        print("[web-patch] CK(a) swipe ignore target not found in main.js", file=sys.stderr)
        return content, False

    # 2. Update pointer down swipe check in drawer drag listener
    swipe_target_2 = "if(!Ma||!Ma.closest('button,a,input,textarea,[role=\"button\"],[data-base-ui-swipe-ignore],[data-swipe-ignore]'))"
    swipe_replacement_2 = (
        "if(!Ma||!Ma.closest('button,a,input,textarea,[role=\"button\"],[data-base-ui-swipe-ignore],[data-swipe-ignore],"
        ".xterm,[data-testid=\"terminal-surface\"],[data-testid=\"terminal-view\"],.terminal,.xterm-scrollable-element'))"
    )
    if swipe_target_2 in content:
        content = content.replace(swipe_target_2, swipe_replacement_2, 1)
        print("[web-patch] Successfully patched secondary drawer swipe check for terminal")
    else:
        print("[web-patch] Secondary drawer swipe check not found in main.js", file=sys.stderr)
        return content, False

    # 3. Add swipe ignore and touch scroll attributes to terminal-surface
    surface_target = 'A.createElement("div",{"data-testid":"terminal-surface",className:"w-full h-full relative overflow-hidden"'
    surface_replacement = 'A.createElement("div",{"data-testid":"terminal-surface","data-base-ui-swipe-ignore":"","data-swipe-ignore":"","data-terminal-touch-scroll":"1",className:"w-full h-full relative overflow-hidden"'
    if surface_target in content:
        content = content.replace(surface_target, surface_replacement, 1)
        print("[web-patch] Successfully patched terminal-surface with swipe-ignore attributes")
    else:
        print("[web-patch] terminal-surface target not found in main.js", file=sys.stderr)
        return content, False

    return content, True


def patch_main(file_path):
    if not os.path.isfile(file_path):
        print(f"[web-patch] file not found: {file_path}", file=sys.stderr)
        return False

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    content, ok_desktop = patch_desktop_mode(content)
    if not ok_desktop:
        return False

    content, ok_search = patch_conversation_search(content)
    if not ok_search:
        return False

    content, ok_inputs = patch_include_user_inputs_in_search(content)
    if not ok_inputs:
        return False

    content, ok_toggles = patch_search_toggles(content)
    if not ok_toggles:
        return False

    content, ok_universal = patch_main_screen_universal_search(content)
    if not ok_universal:
        return False

    content, ok_sound = patch_remove_sound(content)
    if not ok_sound:
        return False

    content, ok_cancel_hook = patch_cancel_stop_hook(content)
    if not ok_cancel_hook:
        return False

    content, ok_notif = patch_agent_notifications(content)
    if not ok_notif:
        return False

    content, ok_retry = patch_auto_retry_on_internet(content)
    if not ok_retry:
        return False

    content, ok_rename = patch_conversation_rename_persistence(content)
    if not ok_rename:
        return False

    content, ok_clip = patch_clipboard_paste_full(content)
    if not ok_clip:
        return False

    content, ok_proj = patch_projects_storage_path(content)
    if not ok_proj:
        return False

    content, ok_prov = patch_capture_providers(content)
    if not ok_prov:
        return False

    content, ok_fts = patch_full_text_conversation_search(content)
    if not ok_fts:
        return False

    content, ok_br = patch_backup_restore(content)
    if not ok_br:
        return False

    content, ok_term = patch_terminal_touch_scroll(content)
    if not ok_term:
        return False

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    return True


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "main.js")
    if not patch_main(path):
        sys.exit(1)
