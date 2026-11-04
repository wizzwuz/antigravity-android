#!/usr/bin/env python3
"""
web/patch_main.py - Dynamic patcher for web/main.js.

1. Locates the Appearance settings block and injects the Desktop Mode toggle.
2. Injects a conversation search button immediately to the left of the three-dot
   menu in project conversations/header, enabling search across the entire conversation.
Safe, idempotent, and resilient to upstream changes.
"""

import sys
import os
import re


def patch_desktop_mode(content):
    if "Desktop Mode" in content or "ag_desktop_mode" in content:
        print("[web-patch] Desktop Mode toggle already present in main.js")
        return content, True

    # 1. State hook injection pattern in Appearance component:
    # Matches: var C=g!==3,D=g!==2,E=F=>G=>{F===t&&v(G)}; or legacy var B=f!==3,C=f!==2,D=E=>G=>{E===r&&u(G)};
    hook_pattern = re.compile(
        r'(var\s+[A-Za-z0-9_$]+=[A-Za-z0-9_$]+!==3,\s*[A-Za-z0-9_$]+=[A-Za-z0-9_$]+!==2,\s*[A-Za-z0-9_$]+=[A-Za-z0-9_$]+=>\s*[A-Za-z0-9_$]+=>\{.*?\};)'
    )
    hook_match = hook_pattern.search(content)

    # 2. JSX Theme element injection: find Theme element in Appearance
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

    # Detect switch and setting item components
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
    # 1. Enable conversationSearchV2 feature flag in config
    cs_flag = 'conversationSearchV2:{feature:!1'
    if cs_flag in content:
        content = content.replace(cs_flag, 'conversationSearchV2:{feature:!0', 1)
        print("[web-patch] Enabled conversationSearchV2 feature flag in main.js")

    # 2. Patch PBb to ensure unified search is always enabled when conversationSearchV2 is active
    pbb_target = 'f=!(!e.get("codeSearchPalette")?.enabled||c===void 0),g=!(!f||!e.get("conversationSearchV2"))'
    pbb_injected = 'f=!(!e.get("codeSearchPalette")?.enabled||c===void 0),g=!0'
    if pbb_target in content:
        content = content.replace(pbb_target, pbb_injected, 1)
        print("[web-patch] Enabled showUnifiedSearch in PBb component")

    # 3. Inject mainCmd and window.__agyOpenConversation into fRb header
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

    # 4. Locate mobile-open-settings in fRb
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
    b_var = m.group(1)      # isHome variable
    react_id = m.group(3)   # React identifier
    btn_comp = m.group(4)   # IconButton component

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


def patch_agent_notifications(content):
    if "cascade_prog_" in content:
        print("[web-patch] Agent notifications already patched in main.js")
        return content, True

    # 1. Patch HDa for live real-time progress and completion tracking per conversation
    hda_target = 'h.notFullyIdle?a.add(b):a.delete(b)&&(h.trajectoryMetadata?.parentConversationId||e.push([b,h]))'
    hda_injected = (
        'h.notFullyIdle?('
        'a.add(b),'
        '(function(){try{if(typeof window!=="undefined"&&window.Android&&typeof window.Android.postNotification==="function"){'
        'var t=h.summary||h.title||"Agent running";'
        'var st=h.stepCount?("Step "+h.stepCount+": "):"";'
        'var bd=st+(h.preview||"Working on task...");'
        'var pr=h.stepCount?Math.min(95,h.stepCount*5):-1;'
        'window.Android.postNotification("agent_progress",t,bd,b,true,pr);'
        '}}catch(_){}})()'
        '):('
        'a.delete(b)&&('
        '(function(){try{if(typeof window!=="undefined"&&window.Android){'
        'window.Android.cancelNotification("cascade_prog_"+b,0);'
        'var ct=h.summary||h.title||"Agent completed";'
        'var cb=h.preview||"Agent finished the task";'
        'window.Android.postNotification("agent_completed",ct,cb,b,false,-1);'
        '}}catch(_){}})(),'
        '(h.trajectoryMetadata?.parentConversationId||e.push([b,h]))'
        ')'
        ')'
    )
    if hda_target in content:
        content = content.replace(hda_target, hda_injected, 1)
        print("[web-patch] Patched HDa stream listener with multi-conversation progress and completion notifications")

    # 2. Patch KDa for required actions (permissions, questions)
    kda_act_target = 'r&&(f.actionRequired&&g?.({soundFile:f.actionRequired}),c?.(r))'
    kda_act_injected = (
        'r&&('
        '(function(){try{if(typeof window!=="undefined"&&window.Android&&typeof window.Android.postNotification==="function"){'
        'window.Android.postNotification("agent_completed",r.title||"Action requires attention",r.body||"The agent needs your input.",r.payload?.cascadeId||"",false,-1);'
        '}}catch(_){}})(),'
        'f.actionRequired&&g?.({soundFile:f.actionRequired}),c?.(r)'
        ')'
    )
    if kda_act_target in content:
        content = content.replace(kda_act_target, kda_act_injected, 1)
        print("[web-patch] Patched KDa with agent action/question notification")

    # 3. Patch KDa for cascadeDone completion dispatch
    kda_fin_target = 'c?.({id:`agent-finished-${l}-${Date.now()}`,title:e,body:q.summary||"Agent finished",payload:{cascadeId:l,type:"request_action",workspaceUri:void 0}})'
    kda_fin_injected = (
        '('
        '(function(){try{if(typeof window!=="undefined"&&window.Android&&typeof window.Android.postNotification==="function"){'
        'window.Android.cancelNotification("cascade_prog_"+l,0);'
        'window.Android.postNotification("agent_completed",q.summary||"Agent completed",q.preview||"Agent finished task",l,false,-1);'
        '}}catch(_){}})(),'
        'c?.({id:`agent-finished-${l}-${Date.now()}`,title:e,body:q.summary||"Agent finished",payload:{cascadeId:l,type:"request_action",workspaceUri:void 0}})'
        ')'
    )
    if kda_fin_target in content:
        content = content.replace(kda_fin_target, kda_fin_injected, 1)
        print("[web-patch] Patched KDa completion dispatcher with agent_completed notification")

    return content, True


def patch_full_text_conversation_search(content):
    if "natStr=window.Android.searchConversations" in content:
        print("[web-patch] Full text conversation search already present in main.js")
        return content, True

    # Patch cBb to query native full-text transcript search from Android bridge
    cbb_target = 'let J=H(await G(c({query:b,limit:50,signal:D.signal})));'
    cbb_injected = (
        'let J;'
        'if(typeof window!=="undefined"&&window.Android&&typeof window.Android.searchConversations==="function"){'
        'try{'
        'var natStr=window.Android.searchConversations(b,50);'
        'if(natStr){'
        'var natJson=JSON.parse(natStr);'
        'if(natJson&&Array.isArray(natJson.results)&&natJson.results.length>0){'
        'J=natJson;'
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

    content, ok_notif = patch_agent_notifications(content)
    if not ok_notif:
        return False

    content, ok_fts = patch_full_text_conversation_search(content)
    if not ok_fts:
        return False

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    return True


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "main.js")
    if not patch_main(path):
        sys.exit(1)
