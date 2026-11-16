#!/usr/bin/env python3
"""
web/patch_main.py - Dynamic patcher for web/main.js (Antigravity v2.32.1 Android UI).

Applies:
1. Android Bridge theme sync hooks (window.Android.getTheme / setTheme / setThemeByUser).
2. Original PC AuxPane v2 redesign (Search tabs/files/plugins/subagents/artifacts/tasks)
   and the header Overview floating popover button ([📄] OverviewToggleIconButton) on Mobile & Desktop.
3. Original PC Customizations (Smart Marketplace V3 | Installed) and Automations inside Settings (⚙️).
4. Voice Mode, Microphone, Permissions Selector badge, /sdcard default path, and touch/menu fixes.
"""

import os
import sys


def must_replace(content, old, new, label):
    cnt = content.count(old)
    if cnt != 1:
        raise RuntimeError(f"[web-patch-2.32.1] expected count=1 for {label}, got {cnt}")
    print(f"  [OK] {label}")
    return content.replace(old, new, 1)


LOADER_INIT_V3 = (
    'typeof window!=="undefined"&&!window.__agMpSmartV3&&(window.__agMpSmartV3=!0,window.__agLoadMarketplaceCatalog=()=>{'
    'if(window.__agMpCatalog)return Promise.resolve(window.__agMpCatalog);'
    'if(window.__agMpCatalogPromise)return window.__agMpCatalogPromise;'
    'window.__agMpCatalogPromise=(async()=>{'
    'var base={featured:[],search:{customizations:[],groups:[]},details:{}};'
    'try{var r=await fetch("/marketplace_catalog.json");if(r.ok)base=await r.json()}catch(_e){}'
    'try{var ac=typeof AbortController!=="undefined"?new AbortController:null,tid=ac?setTimeout(()=>ac.abort(),3500):null,'
    'r2=await fetch("https://raw.githubusercontent.com/Yhoanes/antigravity-android-plugins/main/catalog.json",ac?{signal:ac.signal}:void 0);'
    'tid&&clearTimeout(tid);'
    'if(r2.ok){var rem=await r2.json();if(rem&&typeof rem==="object"){'
    'var rc=(rem.search&&rem.search.customizations)||[],bc=(base.search&&base.search.customizations)||[],rIds=new Set(rc.map(x=>x.id)),'
    'mc=rc.map(x=>Object.assign({_androidNative:!0},x)).concat(bc.filter(x=>!rIds.has(x.id))),'
    'rg2=(rem.search&&rem.search.groups)||[],bg=(base.search&&base.search.groups)||[],rgIds=new Set(rg2.map(x=>x.id)),'
    'mg=rg2.concat(bg.filter(x=>!rgIds.has(x.id))),'
    'bf=(base.featured||[]).filter(x=>x.id!=="android-featured-hero");'
    'base={schema:1,featured:bf,search:{customizations:mc,groups:mg},details:Object.assign({},base.details||{},rem.details||{})}'
    '}}}catch(_e2){}'
    'window.__agMpCatalog=base;return base})();'
    'return window.__agMpCatalogPromise})'
)

NEW_MP_BLOCK_V3 = (
    'searchMarketplace:async u=>{' + LOADER_INIT_V3 + ';'
    'var _SMR=Fja.file.messages.find(m=>m.name==="SearchMarketplaceResponse")||Fja.file.messages[532],'
    '_q=(u.query??"").trim().toLowerCase(),_gid=u.groupId??"",_pt=u.pageToken??"";'
    'var [_cat,_sr]=await Promise.all([window.__agLoadMarketplaceCatalog().catch(()=>null),_gid==="built-for-android"?Promise.resolve(null):f(v=>v.searchMarketplace(Vb(Fja,{query:u.query??"",groupId:_gid,pageToken:_pt}))).catch(()=>null)]);'
    'try{var _allCat=(_cat&&_cat.search&&_cat.search.customizations)||[],_allGrps=(_cat&&_cat.search&&_cat.search.groups)||[],_hasLive=!!(_sr&&_sr.customizations&&_sr.customizations.length>0);'
    'if(_pt&&_hasLive){var _natRaw=_allCat.filter(x=>x._androidNative);if(_natRaw.length>0){var _natMsg=ef(_SMR,{customizations:_natRaw,groups:[]},{ignoreUnknownFields:!0}),_nm=new Map((_natMsg.customizations||[]).map(x=>[x.id,x]));_sr.customizations=_sr.customizations.map(x=>_nm.get(x.id)||x)}return _sr}'
    'var _srcItems=_hasLive?_allCat.filter(x=>x._androidNative):_allCat,_srcGrps=_hasLive?_allGrps.filter(x=>x.id==="built-for-android"||x._androidNative):_allGrps;'
    'if(_gid){var _g=_allGrps.find(x=>x.id===_gid);_srcItems=_g?_srcItems.filter(x=>_g.memberIds&&_g.memberIds.includes(x.id)):[]}'
    'if(_q){_srcItems=_srcItems.filter(x=>(x.displayName||"").toLowerCase().includes(_q)||(x.id||"").toLowerCase().includes(_q)||(x.description||"").toLowerCase().includes(_q))}'
    'var _localMsg=ef(_SMR,{customizations:_srcItems,groups:_q||_gid?[]:_srcGrps},{ignoreUnknownFields:!0});'
    'if(_hasLive){var _fullNatMsg=ef(_SMR,{customizations:_allCat.filter(x=>x._androidNative),groups:[]},{ignoreUnknownFields:!0}),_natById=new Map((_fullNatMsg.customizations||[]).map(x=>[x.id,x])),_seen=new Set((_localMsg.customizations||[]).map(x=>x.id)),_merged=(_localMsg.customizations||[]).slice();'
    'for(var _it of _sr.customizations){var _rep=_natById.get(_it.id)||_it;if(!_seen.has(_rep.id)){_seen.add(_rep.id);_merged.push(_rep)}}'
    'var _gSeen=new Set((_localMsg.groups||[]).map(x=>x.id)),_mGrps=_q||_gid?[]:(_localMsg.groups||[]).slice();'
    'if(!_q&&!_gid&&_sr.groups){for(var _gp of _sr.groups){if(!_gSeen.has(_gp.id)){_gSeen.add(_gp.id);_mGrps.push(_gp)}}}'
    '_localMsg.customizations=_merged;_localMsg.groups=_mGrps;_localMsg.nextPageToken=_sr.nextPageToken||""}'
    'return _localMsg}catch(_e2){return _sr||ef(_SMR,{customizations:[],groups:[]},{ignoreUnknownFields:!0})}},'
    'getMarketplaceCustomization:async u=>{' + LOADER_INIT_V3 + ';'
    'var _GCR=Ija.file.messages.find(m=>m.name==="GetMarketplaceCustomizationResponse")||Ija.file.messages[534],'
    '_cat=await window.__agLoadMarketplaceCatalog().catch(()=>null),_localItem=((_cat&&_cat.search&&_cat.search.customizations)||[]).find(x=>x.id===u.id),_localDet=(_cat&&_cat.details&&_cat.details[u.id])||(_localItem?{customization:_localItem}:null);'
    'if((_localItem&&_localItem._androidNative)||(_localDet&&_localDet.customization&&_localDet.customization._androidNative)){return ef(_GCR,_localDet,{ignoreUnknownFields:!0})}'
    'try{var _gr=await f(v=>v.getMarketplaceCustomization(Vb(Ija,{id:u.id,includePreview:u.includePreview??!1})));if(_gr&&_gr.customization)return _gr}catch(_e){}'
    'return ef(_GCR,_localDet||{},{ignoreUnknownFields:!0})},'
    'getMarketplaceBundles:async u=>{var _GBR=Eja.file.messages.find(m=>m.name==="GetMarketplaceBundlesResponse")||Eja.file.messages[511];try{return await f(v=>v.getMarketplaceBundles(Vb(Eja,{ids:u.ids??[]})))}catch(_e){return ef(_GBR,{bundles:[],customizations:[]},{ignoreUnknownFields:!0})}},'
    'getMarketplaceFeatured:async()=>{' + LOADER_INIT_V3 + ';'
    'var _GFR=Gja.file.messages.find(m=>m.name==="GetMarketplaceFeaturedResponse")||Gja.file.messages[525];'
    'try{var _fr=await f(u=>u.getMarketplaceFeatured(Vb(Gja,{})));if(_fr&&_fr.featured&&_fr.featured.length>0)return _fr}catch(_e){}'
    'try{var _cat=await window.__agLoadMarketplaceCatalog();return ef(_GFR,{featured:((_cat&&_cat.featured)||[]).filter(x=>x.id!=="android-featured-hero"),customizations:(_cat&&_cat.search&&_cat.search.customizations)||[]},{ignoreUnknownFields:!0})}catch(_e2){return ef(_GFR,{featured:[],customizations:[]},{ignoreUnknownFields:!0})}},'
    'getOnboardingPersonas:async()=>f(u=>u.getOnboardingPersonas(Vb(Hja,{}))),'
    'installCustomization:async u=>{' + LOADER_INIT_V3 + ';'
    'var _ICR=Jja.file.messages.find(m=>m.name==="InstallCustomizationResponse")||Jja.file.messages[537],'
    '_cat=await window.__agLoadMarketplaceCatalog().catch(()=>null),_c=((_cat&&_cat.search&&_cat.search.customizations)||[]).find(x=>x.id===u.id),_pname=(u.id||"").split("/").pop(),_url=(_c&&_c.source&&_c.source.archive&&_c.source.archive.url)||"",_mp=(_c&&_c.marketplace)||"antigravity-plugins-official",_ver=(_c&&_c.version)||"1.0.0",_isNat=!!(_c&&_c._androidNative)||["agy-video-studio","craft-anything","chrome-devtools-plugin","android-cli-plugin","science"].includes(_pname);'
    'if(_isNat&&window.Android&&window.Android.installMarketplacePlugin){try{var _njr=JSON.parse(window.Android.installMarketplacePlugin(_pname,_url,u.id,_mp,_ver));await new Promise(r=>setTimeout(r,350));return ef(_ICR,_njr,{ignoreUnknownFields:!0})}catch(_ne){}}'
    'try{var _ir=await f(v=>v.installCustomization(Vb(Jja,{id:u.id,bundleId:u.bundleId})));if(_ir&&_ir.success){try{window.Android&&window.Android.postProcessInstalledPlugin&&window.Android.postProcessInstalledPlugin(_pname)}catch(_pe){}return _ir}}catch(_e){}'
    'try{if(window.Android&&window.Android.installMarketplacePlugin){var _jr=JSON.parse(window.Android.installMarketplacePlugin(_pname,_url,u.id,_mp,_ver));await new Promise(r=>setTimeout(r,350));return ef(_ICR,_jr,{ignoreUnknownFields:!0})}}catch(_e2){return ef(_ICR,{success:!1,message:String(_e2)},{ignoreUnknownFields:!0})}'
    'return ef(_ICR,{success:!1,message:"Marketplace install unavailable"},{ignoreUnknownFields:!0})},'
)


def patch_backup_restore(content):
    if "BackupRestoreScreen" in content:
        print("  [OK] BackupRestoreScreen already present")
        return content

    # 1. Update mEb Map to include "Backup and Restore"
    content = must_replace(
        content,
        '["Provide Feedback","Give Feedback"]',
        '["Provide Feedback","Give Feedback"],["Backup and Restore","Backup and Restore"]',
        "mEb_backup_restore_label"
    )

    # 2. Add to mobile settings screen list in zPb
    content = must_replace(
        content,
        'b=[...c.filter(p=>p!=="Account"),...d,...(b?["Provide Feedback"]:[])];',
        'b=[...c.filter(p=>p!=="Account"),...d,...(b?["Provide Feedback"]:[]),"Backup and Restore"];',
        "zPb_mobile_settings_list"
    )

    # 3. Add to screen resolver in vPb
    content = must_replace(
        content,
        'case "Provide Feedback":return B.createElement(UKb,null);',
        'case "Provide Feedback":return B.createElement(UKb,null);case "Backup and Restore":return B.createElement(BackupRestoreScreen,null);',
        "vPb_screen_resolver"
    )

    # 4. Add to desktop settings sidebar in YRb
    content = must_replace(
        content,
        'B.createElement(qz,{id:F,place:"right"},"Upload Debug Bundle")):void 0})',
        'B.createElement(qz,{id:F,place:"right"},"Upload Debug Bundle")):void 0}),B.createElement(rV,{text:"Backup and Restore",label:IQ("Backup and Restore"),onClick:()=>{M(ou("Backup and Restore"))},isActive:L&&c==="Backup and Restore"})',
        "YRb_desktop_settings_sidebar"
    )

    # 5. Add to desktop settings screen view container in iSb
    content = must_replace(
        content,
        'l&&B.createElement("div",{style:{display:c==="Provide Feedback"?"block":"none"}},B.createElement(UKb,null)),',
        'l&&B.createElement("div",{style:{display:c==="Provide Feedback"?"block":"none"}},B.createElement(UKb,null)),B.createElement("div",{style:{display:c==="Backup and Restore"?"block":"none"}},B.createElement(BackupRestoreScreen,null)),',
        "iSb_desktop_view_container"
    )

    # 6. Inject BackupRestoreScreen component before var UKb=
    backup_restore_comp = '''var BackupRestoreScreen=()=>{
var [status,setStatus]=(0,B.useState)(null);
var [isProcessing,setIsProcessing]=(0,B.useState)(!1);
var [projects,setProjects]=(0,B.useState)([]);
var [selectedProject,setSelectedProject]=(0,B.useState)("all");
var [skills,setSkills]=(0,B.useState)([]);
var [selectedSkill,setSelectedSkill]=(0,B.useState)("all");
var [conversations,setConversations]=(0,B.useState)([]);
var [selectedConversation,setSelectedConversation]=(0,B.useState)("all");
var [showRestartPrompt,setShowRestartPrompt]=(0,B.useState)(!1);
var [restartMessage,setRestartMessage]=(0,B.useState)("");
(0,B.useEffect)(()=>{
try{
if(typeof window!=="undefined"&&window.Android&&typeof window.Android.listProjects==="function"){
var pList=JSON.parse(window.Android.listProjects()||"[]");
if(Array.isArray(pList))setProjects(pList);
}
}catch(_){}
try{
if(typeof window!=="undefined"&&window.Android&&typeof window.Android.listSkills==="function"){
var sList=JSON.parse(window.Android.listSkills()||"[]");
if(Array.isArray(sList))setSkills(sList);
}
}catch(_){}
try{
if(typeof window!=="undefined"&&window.Android&&typeof window.Android.listConversations==="function"){
var cList=JSON.parse(window.Android.listConversations()||"[]");
if(Array.isArray(cList))setConversations(cList);
}
}catch(_){}
if(typeof window!=="undefined"){
window.__onBackupRestoreStatus=function(res){
setIsProcessing(!1);
if(typeof res==="string"){try{res=JSON.parse(res)}catch(_){res={message:res}}}
setStatus(res);
if(res&&res.success&&(res.type==="restore_conversation"||res.type==="restore_projects"||res.type==="restore_skills")){
setRestartMessage(res.type==="restore_conversation"?"Conversations restored successfully. Would you like to restart the app now to reload all conversations?":res.type==="restore_skills"?"Skills restored successfully. Would you like to restart the app now to reload custom skills?":"Projects restored successfully. Would you like to restart the app now to reload your workspace?");
setShowRestartPrompt(!0);
}
};
return function(){
if(typeof window!=="undefined")window.__onBackupRestoreStatus=null;
};
}
},[]);
var onBackupConvos=()=>{
setIsProcessing(!0);
setStatus({type:"info",message:"Opening file picker to choose backup location..."});
try{
if(window.Android&&typeof window.Android.backupConversations==="function")window.Android.backupConversations();
else{setIsProcessing(!1);setStatus({type:"error",message:"Android native bridge unavailable."})}
}catch(err){setIsProcessing(!1);setStatus({type:"error",message:err.message||String(err)})}
};
var onRestoreConvos=()=>{
setIsProcessing(!0);
setStatus({type:"info",message:"Opening file picker to select backup archive..."});
try{
if(window.Android&&typeof window.Android.restoreConversations==="function")window.Android.restoreConversations();
else{setIsProcessing(!1);setStatus({type:"error",message:"Android native bridge unavailable."})}
}catch(err){setIsProcessing(!1);setStatus({type:"error",message:err.message||String(err)})}
};
var onBackupProj=()=>{
setIsProcessing(!0);
setStatus({type:"info",message:"Opening file picker to save project ZIP..."});
try{
if(window.Android&&typeof window.Android.backupProjects==="function")window.Android.backupProjects(selectedProject);
else{setIsProcessing(!1);setStatus({type:"error",message:"Android native bridge unavailable."})}
}catch(err){setIsProcessing(!1);setStatus({type:"error",message:err.message||String(err)})}
};
var onRestoreProj=()=>{
setIsProcessing(!0);
setStatus({type:"info",message:"Opening file picker to select project ZIP..."});
try{
if(window.Android&&typeof window.Android.restoreProjects==="function")window.Android.restoreProjects(selectedProject!=="all"?selectedProject:"");
else{setIsProcessing(!1);setStatus({type:"error",message:"Android native bridge unavailable."})}
}catch(err){setIsProcessing(!1);setStatus({type:"error",message:err.message||String(err)})}
};
var onBackupSkills=()=>{
setIsProcessing(!0);
setStatus({type:"info",message:"Opening file picker to save skills ZIP..."});
try{
if(window.Android&&typeof window.Android.backupSkills==="function")window.Android.backupSkills(selectedSkill);
else{setIsProcessing(!1);setStatus({type:"error",message:"Android native bridge unavailable."})}
}catch(err){setIsProcessing(!1);setStatus({type:"error",message:err.message||String(err)})}
};
var onRestoreSkills=()=>{
setIsProcessing(!0);
setStatus({type:"info",message:"Opening file picker to select skills ZIP..."});
try{
if(window.Android&&typeof window.Android.restoreSkills==="function")window.Android.restoreSkills(selectedSkill!=="all"?selectedSkill:"");
else{setIsProcessing(!1);setStatus({type:"error",message:"Android native bridge unavailable."})}
}catch(err){setIsProcessing(!1);setStatus({type:"error",message:err.message||String(err)})}
};
return B.createElement(HQ,{title:IQ("Backup and Restore")},
B.createElement("div",{className:"space-y-6 max-w-2xl pb-8 p-1 relative"},
showRestartPrompt&&B.createElement("div",{className:"fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4 animate-fade-in"},
B.createElement("div",{className:"w-full max-w-sm rounded-2xl border border-border bg-popover p-5 space-y-4 shadow-xl text-popover-foreground"},
B.createElement("div",{className:"space-y-1.5"},
B.createElement("h3",{className:"text-base font-semibold m-0 text-foreground"},"Restart Required"),
B.createElement("p",{className:"text-sm text-muted-foreground m-0 leading-relaxed"},restartMessage||"Restoration completed successfully. Would you like to restart the app now to apply all changes?")),
B.createElement("div",{className:"flex items-center justify-end gap-2.5 pt-2"},
B.createElement(sz,{variant:"secondary",size:"md",onClick:()=>setShowRestartPrompt(!1)},"Cancel"),
B.createElement(sz,{variant:"primary",size:"md",onClick:()=>{
setShowRestartPrompt(!1);
try{if(window.Android&&typeof window.Android.restartApp==="function")window.Android.restartApp()}
catch(_){}
}},"OK")))),
status&&B.createElement("div",{className:Gi("p-3 rounded-xl border text-sm flex items-start gap-2.5 transition-all shadow-sm",
status.success?"bg-emerald-500/10 border-emerald-500/30 text-emerald-300":
status.type==="info"?"bg-sky-500/10 border-sky-500/30 text-sky-300":
"bg-red-500/10 border-red-500/30 text-red-300")},
B.createElement(nq,{name:status.success?"check_circle":status.type==="info"?"info":"error",size:18,className:"shrink-0 mt-0.5"}),
B.createElement("div",{className:"flex-1"},B.createElement("div",{className:"font-medium"},status.title||(status.success?"Success":status.type==="info"?"Processing":"Notice")),status.message&&B.createElement("div",{className:"text-xs opacity-90 mt-0.5"},status.message)),
B.createElement("button",{type:"button",onClick:()=>setStatus(null),className:"text-xs opacity-60 hover:opacity-100 p-1 border-none bg-transparent cursor-pointer text-inherit"},"✕")),
B.createElement("div",{className:"rounded-2xl border border-border bg-sidebar-muted/20 p-4 space-y-3.5 shadow-xs"},
B.createElement("div",{className:"flex items-center gap-3"},
B.createElement("div",{className:"p-2.5 rounded-xl bg-primary/10 text-primary flex items-center justify-center"},
B.createElement(nq,{name:"forum",size:22})),
B.createElement("div",null,
B.createElement("h3",{className:"font-semibold text-base text-foreground m-0"},"Conversations & Trajectories"),
B.createElement("p",{className:"text-xs text-muted-foreground mt-0.5 mb-0 leading-relaxed"},
"Fast, compressed archive of conversation history, transcripts, and brain artifacts (.zip). Space-saving and complete."))),
B.createElement("div",{className:"flex flex-wrap gap-2.5 pt-1"},
B.createElement(sz,{variant:"primary",size:"md",disabled:isProcessing,onClick:onBackupConvos,className:"flex items-center gap-1.5"},
B.createElement(nq,{name:"upload",size:16}),"Backup Conversations"),
B.createElement(sz,{variant:"secondary",size:"md",disabled:isProcessing,onClick:onRestoreConvos,className:"flex items-center gap-1.5"},
B.createElement(nq,{name:"download",size:16}),"Restore Conversations"))),
B.createElement("div",{className:"rounded-2xl border border-border bg-sidebar-muted/20 p-4 space-y-3.5 shadow-xs"},
B.createElement("div",{className:"flex items-center gap-3"},
B.createElement("div",{className:"p-2.5 rounded-xl bg-primary/10 text-primary flex items-center justify-center"},
B.createElement(nq,{name:"folder_zip",size:22})),
B.createElement("div",null,
B.createElement("h3",{className:"font-semibold text-base text-foreground m-0"},"Project Files"),
B.createElement("p",{className:"text-xs text-muted-foreground mt-0.5 mb-0 leading-relaxed"},
"Backup and restore workspace projects as standard ZIP archives."))),
B.createElement("div",{className:"space-y-1.5 pt-1"},
B.createElement("label",{className:"block text-xs font-medium text-muted-foreground"},"Target Project Scope:"),
B.createElement("select",{value:selectedProject,onChange:e=>setSelectedProject(e.target.value),className:"w-full p-2.5 rounded-xl bg-background border border-border text-foreground text-sm focus:outline-none focus:ring-1 focus:ring-primary cursor-pointer"},
B.createElement("option",{value:"all"},"All Scratch Projects (Complete Workspace)"),
projects.map(p=>B.createElement("option",{key:p,value:p},"Project: "+p)))),
B.createElement("div",{className:"flex flex-wrap gap-2.5 pt-1"},
B.createElement(sz,{variant:"primary",size:"md",disabled:isProcessing,onClick:onBackupProj,className:"flex items-center gap-1.5"},
B.createElement(nq,{name:"upload",size:16}),"Backup Projects (.zip)"),
B.createElement(sz,{variant:"secondary",size:"md",disabled:isProcessing,onClick:onRestoreProj,className:"flex items-center gap-1.5"},
B.createElement(nq,{name:"download",size:16}),"Restore Projects (.zip)"))),
B.createElement("div",{className:"rounded-2xl border border-border bg-sidebar-muted/20 p-4 space-y-3.5 shadow-xs"},
B.createElement("div",{className:"flex items-center gap-3"},
B.createElement("div",{className:"p-2.5 rounded-xl bg-primary/10 text-primary flex items-center justify-center"},
B.createElement(nq,{name:"psychology",size:22})),
B.createElement("div",null,
B.createElement("h3",{className:"font-semibold text-base text-foreground m-0"},"Skills & Runbooks"),
B.createElement("p",{className:"text-xs text-muted-foreground mt-0.5 mb-0 leading-relaxed"},
"Backup and restore custom agent skills, tools, and procedural runbooks as standard ZIP archives."))),
B.createElement("div",{className:"space-y-1.5 pt-1"},
B.createElement("label",{className:"block text-xs font-medium text-muted-foreground"},"Target Skill Scope:"),
B.createElement("select",{value:selectedSkill,onChange:e=>setSelectedSkill(e.target.value),className:"w-full p-2.5 rounded-xl bg-background border border-border text-foreground text-sm focus:outline-none focus:ring-1 focus:ring-primary cursor-pointer"},
B.createElement("option",{value:"all"},"All Skills (Complete Library)"),
skills.map(s=>B.createElement("option",{key:s,value:s},"Skill: "+s)))),
B.createElement("div",{className:"flex flex-wrap gap-2.5 pt-1"},
B.createElement(sz,{variant:"primary",size:"md",disabled:isProcessing,onClick:onBackupSkills,className:"flex items-center gap-1.5"},
B.createElement(nq,{name:"upload",size:16}),"Backup Skills (.zip)"),
B.createElement(sz,{variant:"secondary",size:"md",disabled:isProcessing,onClick:onRestoreSkills,className:"flex items-center gap-1.5"},
B.createElement(nq,{name:"download",size:16}),"Restore Skills (.zip)")))
));
};
'''
    content = must_replace(content, 'var UKb=', backup_restore_comp + 'var UKb=', "UKb_inject_BackupRestoreScreen")
    return content

def patch_terminal_touch_scroll(content):
    if 'data-testid=\\"terminal-surface\\"' in content or 'data-testid="terminal-surface"' in content:
        print("  [OK] terminal swipe-ignore already present")
        return content

    content = must_replace(
        content,
        'function ehb(a){return!!a?.closest("[data-base-ui-swipe-ignore]")}',
        'function ehb(a){return!!a?.closest("[data-base-ui-swipe-ignore],.xterm,[data-testid=\\"terminal-surface\\"],[data-testid=\\"terminal-view\\"],.terminal,.xterm-scrollable-element")}',
        "ehb_terminal_swipe_ignore"
    )

    content = must_replace(
        content,
        '!va||!va.closest(\'button,a,input,textarea,[role="button"],[data-base-ui-swipe-ignore],[data-swipe-ignore]\')',
        '!va||!va.closest(\'button,a,input,textarea,[role="button"],[data-base-ui-swipe-ignore],[data-swipe-ignore],.xterm,[data-testid="terminal-surface"]\')',
        "secondary_drawer_terminal_swipe_ignore"
    )
    return content


def patch_main(file_path):
    if not os.path.isfile(file_path):
        print(f"[web-patch-2.32.1] file not found: {file_path}", file=sys.stderr)
        return False

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    if "Android.getTheme" in content and "__agMpSmartV3" in content and "__AgRootEB" in content:
        if "BackupRestoreScreen" in content and ('data-testid=\\"terminal-surface\\"' in content or 'data-testid="terminal-surface"' in content):
            print("[web-patch-2.32.1] main.js already patched (v2.32.1 Android UI + Smart Marketplace V3 + RootEB + BackupRestore + Terminal)")
            return True
        print("[web-patch-2.32.1] Applying BackupRestoreScreen and Terminal patches...")
        content = patch_backup_restore(content)
        content = patch_terminal_touch_scroll(content)
        with open(file_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        print("[web-patch-2.32.1] Successfully patched Backup & Restore (skills, convos, projects) and Terminal scroll into main.js!")
        return True

    # 1a. g_() system theme resolver via window.Android.getTheme()
    content = must_replace(
        content,
        'function g_(){return typeof window!=="undefined"&&window.matchMedia?window.matchMedia("(prefers-color-scheme: dark)").matches:!1}',
        'function g_(){try{if(typeof window!=="undefined"&&window.Android&&typeof window.Android.getTheme==="function"){var _t=window.Android.getTheme();if(_t==="dark")return!0;if(_t==="light")return!1}if(typeof window!=="undefined"&&window.__AG_RESOLVED_THEME__){if(window.__AG_RESOLVED_THEME__==="dark")return!0;if(window.__AG_RESOLVED_THEME__==="light")return!1}}catch(_e){}return typeof window!=="undefined"&&window.matchMedia?window.matchMedia("(prefers-color-scheme: dark)").matches:!1}',
        "g__system_theme",
    )

    # 1b. Mrd(a) hostTheme=system resolver + unconditional startup call
    content = must_replace(
        content,
        'function Mrd(a){if(typeof window!=="undefined"){var b=(new URLSearchParams(window.location.search)).get("hostTheme");b!=="dark"&&b!=="light"||rh.setState(b);',
        'function Mrd(a){if(typeof window!=="undefined"){var b=(new URLSearchParams(window.location.search)).get("hostTheme");b==="system"&&(b=typeof window!=="undefined"&&window.Android&&window.Android.getTheme?window.Android.getTheme():(typeof window!=="undefined"?window.__AG_RESOLVED_THEME__:void 0));b!=="dark"&&b!=="light"||rh.setState(b);',
        "Mrd_hostTheme",
    )
    content = must_replace(
        content,
        "d&&Mrd(f?.router);",
        "Mrd(f?.router);",
        "Mrd_startup_call",
    )

    # 1c. Theme sync (window.Android.setTheme, __agOnSystemThemeChanged, setThemeByUser)
    content = must_replace(
        content,
        'z=C=>{m.setState(C);C=h_({hostTheme:b?rh.getState():void 0,themeMode:C});var F=u.getState();F=C===2?F.light:F.dark;var G=i_(C);YZ(G,F,C,b);l.setState(G);y(G)}',
        'z=C=>{m.setState(C);var _origC=C;C=h_({hostTheme:b?rh.getState():void 0,themeMode:C});var F=u.getState();F=C===2?F.light:F.dark;var G=i_(C);YZ(G,F,C,b);l.setState(G);try{var _m=G.uiTheme==="vs-dark"?"dark":"light",_thm=b||_origC!==1?_m:"system";window.__agSelectedTheme=_thm;window.Android&&window.Android.setTheme&&window.Android.setTheme(_thm)}catch(_e){}y(G)}',
        "theme_setTheme",
    )
    content = must_replace(
        content,
        ':window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change",()=>{m.getState()===1&&z(1)});',
        ':(c=()=>{if(c._updating)return;c._updating=!0;try{var _cur=window.Android&&window.Android.getTheme?window.Android.getTheme():window.__AG_RESOLVED_THEME__;if((_cur==="dark"||_cur==="light")&&rh.getState()!==_cur)rh.setState(_cur)}catch(_e){}try{m.getState()===1&&z(1)}catch(_e){}try{typeof window!=="undefined"&&window.dispatchEvent(typeof CustomEvent==="function"?new CustomEvent("__ag_theme_change"):new Event("__ag_theme_change"))}catch(_e){}c._updating=!1},c._updating=!1,window.__agOnSystemThemeChanged=c,rh.onDidChange(()=>{c._updating||c()}),window.matchMedia&&window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change",c));',
        "theme_system_listener",
    )
    content = must_replace(
        content,
        "pushUpdate:C=>{switch(C){case 2:C=2;break;case 3:C=1;break;case 1:C=3;break;default:C=1}Crd(a,C)}",
        'pushUpdate:C=>{var _orig=C;switch(C){case 2:C=2;break;case 3:C=1;break;case 1:C=3;break;default:C=1}Crd(a,C);z(_orig);try{var _um=_orig===2?"light":(_orig===3?"dark":"system");window.Android&&window.Android.setThemeByUser&&window.Android.setThemeByUser(_um)}catch(_e){}}',
        "theme_pushUpdate",
    )

    # 2. Enable AuxPane v2 redesign + Overview [📄] popover button (iZc) on Mobile & Desktop
    content = must_replace(
        content,
        'auxPaneComponent:{feature:{overviewPanelMode:"outputs"}}',
        'auxPaneComponent:{feature:{overviewPanelMode:"full",redesignEnabled:!0}}',
        "auxPane_eCd",
    )
    content = must_replace(
        content,
        'auxPaneComponent:{feature:{location:"sidebar",redesignEnabled:!1,bottomTerminalPanelEnabled:!1,overviewPanelMode:"full"}',
        'auxPaneComponent:{feature:{location:"sidebar",redesignEnabled:!0,bottomTerminalPanelEnabled:!1,overviewPanelMode:"full"}',
        "auxPane_main",
    )
    content = must_replace(
        content,
        'function tBd(a,b,c){var d=()=>{var f=rBd(b);f&&sBd(a,f,b,g=>{g&&c()})};Yi()?d():a.initPromise.then(d,()=>{})}',
        'function tBd(a,b,c){try{!Ti()&&c()}catch{}}',
        "tBd_enable_aux_pane_redesign",
    )
    content = must_replace(
        content,
        '!b&&B.createElement(B.Fragment,null,B.createElement(NZc,{cascadeId:t}),B.createElement(yV,{iconName:"dock_to_bottom",onClick:p,"aria-label":"Toggle Side Panel",dataTestId:"mobile-toggle-aux-sidebar",\nsize:"icon-touch",showAttentionDot:n}))',
        '!b&&B.createElement(B.Fragment,null,B.createElement(NZc,{cascadeId:t}),B.createElement(fZc,null),B.createElement(yV,{iconName:"dock_to_bottom",onClick:p,"aria-label":"Toggle Side Panel",dataTestId:"mobile-toggle-aux-sidebar",\nsize:"icon-touch",showAttentionDot:n}))',
        "mobile_header_fZc",
    )
    content = must_replace(
        content,
        'n=u?B.createElement(e7c,{content:Z,sidePanel:aa,statusBar:V}):B.createElement(r7c,',
        'n=u?B.createElement(e7c,{content:T,sidePanel:aa,statusBar:V}):B.createElement(r7c,',
        "mobile_e7c_with_overview_host",
    )
    content = must_replace(
        content,
        'function AXc(a,b){a=b??a;',
        'function AXc(a,b){a=a??b;',
        "AXc_keep_open_when_count_positive",
    )
    content = must_replace(
        content,
        '{id:"modifiedFiles",title:"Modified Files",defaultEnabled:!1}',
        '{id:"modifiedFiles",title:"Modified Files",defaultEnabled:!0}',
        "enable_modifiedFiles_by_default",
    )
    content = must_replace(
        content,
        '{type:"fileView",id:"open-file",title:"Open File",icon:B.createElement(nq,{name:"draft",size:16}),onSelect:({logEvent:a,commandsService:b})=>{a("aux_new_tab_open_file_click");\nb?.executeCommand("openCommandPalette")}}',
        '{type:"fileView",id:"open-file",title:"Open File",icon:B.createElement(nq,{name:"draft",size:16}),onSelect:({logEvent:a,openAuxTab:b,treeId:c})=>{a("aux_new_tab_open_file_click");\nb({type:"fileView",fileView:{}},void 0,{treeId:c,keepOpen:!0,source:"new_tab_card"})}}',
        "open_file_card",
    )
    content = must_replace(
        content,
        'terminalFeature:{feature:null,important:[{runtimeGating:{host:[zi.Extension]},feature:null}]',
        'terminalFeature:{feature:{terminalCapabilities:OX},important:[{runtimeGating:{host:[zi.Extension]},feature:null}]',
        "terminalFeature_main",
    )
    content = must_replace(
        content,
        'fileExplorerTab:{feature:{isEnabled:!1},',
        'fileExplorerTab:{feature:{isEnabled:!0},',
        "fileExplorerTab_main",
    )

    # 3. Enable Plugins/Marketplace V3 & Automations and wire them inside Settings (⚙️)
    content = must_replace(
        content,
        'plugins:{feature:!1,applyAll:[{runtimeGating:{customFlag:"enable-plugins"},feature:!0}]}',
        'plugins:{feature:!0,applyAll:[{runtimeGating:{customFlag:"enable-plugins"},feature:!0}]}',
        "plugins_feature",
    )
    content = must_replace(
        content,
        'x=oh(Oi(b,"enable-sidecars"),C=>k&&(l||C));',
        'x=new nh(!0);',
        "extensibility_x",
    )
    content = must_replace(
        content,
        'showUISidecars:Oi(b,"enable-ui-sidecars"),showDeclaredPermissions:Oi(b,"jetski-sidecar-declared-permissions"),enableAutomations:Oi(b,"scheduled-tasks-v2")',
        'showUISidecars:new nh(!0),showDeclaredPermissions:Oi(b,"jetski-sidecar-declared-permissions"),enableAutomations:new nh(!0)',
        "extensibility_flags",
    )
    content = must_replace(
        content,
        'deletePlugin:async u=>f(async v=>{var w=Vb(tja);w.pluginId=u.pluginId;return v.deletePlugin(w)}),listPluginAuthProviders:async u=>f(v=>v.listPluginAuthProviders(Vb(uja,\nu??{}))),',
        'deletePlugin:async u=>{try{var _dr=await f(async v=>{var w=Vb(tja);w.pluginId=u.pluginId;return v.deletePlugin(w)});if(_dr&&_dr.success!==!1)return _dr}catch(_e){}try{if(window.Android&&window.Android.uninstallMarketplacePlugin&&window.Android.uninstallMarketplacePlugin(u.pluginId)){await new Promise(r=>setTimeout(r,250));return{success:!0,message:""}}}catch(_e2){}return{success:!1,message:"Failed to delete plugin"}},listPluginAuthProviders:async()=>({providers:[]}),',
        "deletePlugin_and_authProviders_fallback",
    )
    content = must_replace(
        content,
        'searchMarketplace:async u=>f(v=>v.searchMarketplace(Vb(Fja,{query:u.query??"",groupId:u.groupId??"",pageToken:u.pageToken??""}))),getMarketplaceCustomization:async u=>f(v=>v.getMarketplaceCustomization(Vb(Ija,{id:u.id,includePreview:u.includePreview??!1}))),getMarketplaceBundles:async u=>f(v=>v.getMarketplaceBundles(Vb(Eja,{ids:u.ids??[]}))),getMarketplaceFeatured:async()=>f(u=>u.getMarketplaceFeatured(Vb(Gja,{}))),getOnboardingPersonas:async()=>\nf(u=>u.getOnboardingPersonas(Vb(Hja,{}))),installCustomization:async u=>f(v=>v.installCustomization(Vb(Jja,{id:u.id,bundleId:u.bundleId}))),',
        NEW_MP_BLOCK_V3,
        "marketplace_rpcs_v3",
    )
    content = must_replace(
        content,
        'function HT(a,b){return b.find(c=>RMb(c.installedFrom,a))}',
        'function HT(a,b){return b.find(c=>RMb(c.installedFrom,a)||(a?.id&&GT(c)===a.id.split("/").pop()))}',
        "HT_match_by_dir_fallback",
    )
    content = must_replace(
        content,
        '["Jetski Chat",{sections:[]}],["Developer",{sections:[]}]]',
        '["Automations",{sections:[]}],["Jetski Chat",{sections:[]}],["Developer",{sections:[]}]]',
        "ZDb_screens",
    )
    content = must_replace(
        content,
        '{screen:"Customizations"},{screen:"Browser"},{screen:"Developer"},{screen:"Running"},{screen:"Jetski Chat"}],gEb="General Appearance Shortcuts Notifications Models Customizations Browser Developer Running".split(" ")',
        '{screen:"Customizations"},{screen:"Automations"},{screen:"Browser"},{screen:"Developer"},{screen:"Running"},{screen:"Jetski Chat"}],gEb="General Appearance Shortcuts Notifications Models Customizations Automations Browser Developer Running".split(" ")',
        "fEb_gEb_screens",
    )
    content = must_replace(
        content,
        '{screen:"Account"},{screen:"Customizations"},{screen:"Notifications"}',
        '{screen:"Account"},{screen:"Customizations"},{screen:"Automations"},{screen:"Notifications"}',
        "mobile_settings_screens",
    )
    content = must_replace(
        content,
        'g=l=>{if(!c)return l;l=new Map(l);l.delete("Customizations");return l}',
        'g=l=>l',
        "keep_customizations_in_settings",
    )
    content = must_replace(
        content,
        'var mPb=()=>{var {authorities:a,selectedAuthority:b,setSelectedAuthority:c,selectedGeminiDir:d,selectedConfigDir:f}=JT(),g=oj().get("projectsCustomizations")?.showHeadCustomizationsInMainScreen??!1,h=(0,B.useMemo)(()=>g?["file:///google/src/files/head/depot/"]:[],[g]);return a.length===0?B.createElement(HQ,{title:"Customizations"},B.createElement("div",{className:"flex items-center gap-2 text-muted-foreground"},B.createElement(Au,{size:14,className:"text-muted-foreground"}),"Connecting to language server...")):\nB.createElement(lPb,{key:b,geminiDir:d,configDir:f,workspaceUris:h,tabs:a.map(k=>({id:k.authority,label:k.displayName})),selectedAuthority:b,onSelectAuthority:c})};',
        'var mPb=()=>B.createElement(S1b,null,B.createElement(Guc,null,B.createElement(FWc,{embedded:!0})));',
        "mPb_replace_with_marketplace_FWc",
    )
    content = must_replace(
        content,
        'case "Customizations":return B.createElement(mPb,null);',
        'case "Customizations":return B.createElement(mPb,null);case "Automations":return B.createElement(r$c,{automationPage:!0});',
        "mobile_automations_screen",
    )
    content = must_replace(
        content,
        'B.createElement("div",{style:{display:c==="Customizations"?"block":"none"}},B.createElement(mPb,null))',
        'B.createElement("div",{style:{display:c==="Customizations"?"block":"none"}},B.createElement(mPb,null)),B.createElement("div",{style:{display:c==="Automations"?"block":"none"}},B.createElement(r$c,{automationPage:!0}))',
        "desktop_settings_automations_screen",
    )
    content = must_replace(
        content,
        'a({to:"/",search:g=>{g={...g};delete g.cascadeId;delete g.focused;',
        'a({to:"/",search:g=>{g={...g};delete g.cascadeId;delete g.focused;delete g.settingsOpen;delete g.settingsScreen;delete g.settingsProjectId;delete g.settingsSection;',
        "DI_close_settings",
    )

    # Dual-mode AWc / FWc inside Settings modal and on /customizations route
    old_AWc_FWc = (
        'function AWc({tab:a,onSelect:b}){return B.createElement("nav",{"aria-label":"Customizations views",className:"agy-pill inline-flex items-center h-8 rounded-lg border border-border bg-secondary/20 p-0.5 gap-0.5 select-none","data-testid":"plugins-tabs"},zWc.map(({tab:c,to:d,label:f})=>{var g=c===a;return B.createElement($H,{key:c,to:d,activeOptions:{exact:!0},"aria-current":g?"page":void 0,onClick:()=>{g||b(c)},className:Gi("agy-pill inline-flex items-center justify-center h-full px-2 rounded-md shrink-0 whitespace-nowrap no-underline transition-colors cursor-pointer outline-none focus-visible:ring-1 focus-visible:ring-primary",\n'
        'g?"bg-secondary text-foreground":"text-secondary-foreground hover:text-foreground"),"data-testid":`plugins-tab-${c}`},f)}))};const BWc={source:"remote"};\n'
        'function CWc({tab:a,MarkdownRenderer:b}){var {plugins:c,error:d,dismissError:f,refetch:g}=gQb(),h=oj().get("customizations");h=!!h?.showSkillsAndRules||!!h?.showCustomAgents||!!h?.showMcpServers;var k=B6().trim(),l=k.trim().toLowerCase(),m=(0,B.useMemo)(()=>(c??[]).filter(n=>(a==="browse"||n.isAuthenticated)&&C6(l,n.displayName,n.name,n.description)),[c,a,l]);k=k?`No apps found for "${k}".`:a==="browse"?"No apps available.":"No apps connected yet. Connect one from Marketplace.";return B.createElement("div",\n'
        '{className:"flex flex-col gap-6"},B.createElement(DWc,null),B.createElement(L5,{title:a==="browse"?"Apps":"Connected",count:c?m.length:void 0,isFirst:!0},c?B.createElement(B.Fragment,null,d&&B.createElement(qU,{title:"Error:",message:d,onDismiss:f}),m.length===0?B.createElement(SVc,{message:k}):B.createElement("div",{className:"grid gap-2 grid-cols-1 sm:grid-cols-2"},m.map(n=>{var p=n.displayName||n.name,q=n.accounts.length>0?"Reconnect":"Connect";return B.createElement(v5,{key:n.name,name:p,description:n.description,\n'
        'logo:n.logo,params:{pluginId:n.name},search:BWc,searchQuery:l,badge:a==="browse"&&n.isAuthenticated?B.createElement(u5,{variant:"muted"},"Connected"):void 0,action:!n.isAuthenticated&&n.authorizeUri?B.createElement(sz,{variant:"secondary",size:"xs","aria-label":`${q} ${p}`,onClick:()=>{Fm(n.authorizeUri)}},q):null})}))):d?B.createElement(RVc,{error:d,onRetry:()=>{g()}}):B.createElement(QVc,{label:"Loading apps..."})),a==="installed"&&h&&B.createElement(OVc,{MarkdownRenderer:b}))}\n'
        'function DWc(){return B.createElement("div",{className:"flex gap-3 items-start px-4 py-3 rounded-xl border border-border"},B.createElement(nq,{name:"cloud",size:20,className:"shrink-0 mt-0.5 text-muted-foreground"}),B.createElement("div",{className:"flex flex-col gap-1"},B.createElement("p",{className:"font-medium text-foreground m-0"},"Apps connected to your account"),B.createElement("p",{className:"text-sm text-muted-foreground m-0"},"Sign in to an app once and your agent can use it on any device. Open an app to see the account it uses or to disconnect it.")))}\n'
        ';function EWc({searchQuery:a,children:b}){a=VVc(a);return B.createElement(TVc.Provider,{value:a},b)};function FWc({MarkdownRenderer:a}={}){var {q:b}=dI({strict:!1}),c=SH({select:w=>w.location.pathname}),d=oj().get("customizations"),f=d?.showMarketplaceTab??!0,g=!f||c.startsWith("/customizations/installed")?"installed":"browse";c=d?.pluginSources??"local";var h=BY(),k=c==="remote",[l,m]=(0,B.useState)(()=>b??h.searchQuery),[n,p]=(0,B.useState)(b);n!==b&&(p(b),b!==void 0&&m(b));(0,B.useEffect)(()=>{h.searchQuery=l},[h,l]);var {logTabToggle:q,logSearch:t}=z5(),u=Psc(l,800),v=(0,B.useRef)(l);(0,B.useEffect)(()=>\n'
        '{k||u===v.current||(v.current=u)&&t(g,u)},[u,g,k,t]);return B.createElement("div",{className:"flex-1 flex flex-col overflow-hidden h-full min-h-0 bg-background"},B.createElement("div",{className:"flex-1 overflow-y-auto min-h-0 [scrollbar-gutter:stable]"},B.createElement("div",{className:"sticky top-0 z-20 bg-background"},B.createElement("div",{className:"w-full max-w-4xl mx-auto px-4 sm:px-8 pt-8 pb-4 flex flex-col gap-4"},B.createElement("div",{className:"flex flex-wrap items-center justify-between gap-2 sm:gap-4"},\n'
        'B.createElement("h1",{className:"text-xl font-medium text-foreground select-none sm:px-3 m-0"},"Customizations"),B.createElement("div",{className:"flex items-center gap-4"},f&&B.createElement(AWc,{tab:g,onSelect:q}))),B.createElement(yWc,{searchQuery:l,onSearchQueryChange:m,placeholder:"Search customizations...",inputTestId:"customizations-search"}))),B.createElement("div",{className:"max-w-4xl w-full mx-auto px-4 sm:px-8 py-6"},B.createElement(EWc,{searchQuery:k?"":l},B.createElement(bVc,{value:l},\n'
        'k?B.createElement(CWc,{tab:g,MarkdownRenderer:a}):B.createElement(WH,null))))))}'
    )
    new_AWc_FWc = (
        'function AWc({tab:a,onSelect:b,inRoute:inR=!0}){return B.createElement("nav",{"aria-label":"Customizations views",className:"agy-pill inline-flex items-center h-8 rounded-lg border border-border bg-secondary/20 p-0.5 gap-0.5 select-none","data-testid":"plugins-tabs"},zWc.map(({tab:c,to:d,label:f})=>{var g=c===a,cls=Gi("agy-pill inline-flex items-center justify-center h-full px-2 rounded-md shrink-0 whitespace-nowrap no-underline transition-colors cursor-pointer outline-none focus-visible:ring-1 focus-visible:ring-primary",g?"bg-secondary text-foreground":"text-secondary-foreground hover:text-foreground");return inR?B.createElement($H,{key:c,to:d,activeOptions:{exact:!0},"aria-current":g?"page":void 0,onClick:()=>{g||b(c)},className:cls,"data-testid":`plugins-tab-${c}`},f):B.createElement("button",{key:c,type:"button","aria-current":g?"page":void 0,onClick:()=>{g||b(c)},className:Gi(cls,"border-none bg-transparent"),"data-testid":`plugins-tab-${c}`},f)}))};const BWc={source:"remote"};\n'
        'function CWc({tab:a,MarkdownRenderer:b}){var {plugins:c,error:d,dismissError:f,refetch:g}=gQb(),h=oj().get("customizations");h=!!h?.showSkillsAndRules||!!h?.showCustomAgents||!!h?.showMcpServers;var k=B6().trim(),l=k.trim().toLowerCase(),m=(0,B.useMemo)(()=>(c??[]).filter(n=>(a==="browse"||n.isAuthenticated)&&C6(l,n.displayName,n.name,n.description)),[c,a,l]);k=k?`No apps found for "${k}".`:a==="browse"?"No apps available.":"No apps connected yet. Connect one from Marketplace.";return B.createElement("div",\n'
        '{className:"flex flex-col gap-6"},B.createElement(DWc,null),B.createElement(L5,{title:a==="browse"?"Apps":"Connected",count:c?m.length:void 0,isFirst:!0},c?B.createElement(B.Fragment,null,d&&B.createElement(qU,{title:"Error:",message:d,onDismiss:f}),m.length===0?B.createElement(SVc,{message:k}):B.createElement("div",{className:"grid gap-2 grid-cols-1 sm:grid-cols-2"},m.map(n=>{var p=n.displayName||n.name,q=n.accounts.length>0?"Reconnect":"Connect";return B.createElement(v5,{key:n.name,name:p,description:n.description,\n'
        'logo:n.logo,params:{pluginId:n.name},search:BWc,searchQuery:l,badge:a==="browse"&&n.isAuthenticated?B.createElement(u5,{variant:"muted"},"Connected"):void 0,action:!n.isAuthenticated&&n.authorizeUri?B.createElement(sz,{variant:"secondary",size:"xs","aria-label":`${q} ${p}`,onClick:()=>{Fm(n.authorizeUri)}},q):null})}))):d?B.createElement(RVc,{error:d,onRetry:()=>{g()}}):B.createElement(QVc,{label:"Loading apps..."})),a==="installed"&&h&&B.createElement(OVc,{MarkdownRenderer:b}))}\n'
        'function DWc(){return B.createElement("div",{className:"flex gap-3 items-start px-4 py-3 rounded-xl border border-border"},B.createElement(nq,{name:"cloud",size:20,className:"shrink-0 mt-0.5 text-muted-foreground"}),B.createElement("div",{className:"flex flex-col gap-1"},B.createElement("p",{className:"font-medium text-foreground m-0"},"Apps connected to your account"),B.createElement("p",{className:"text-sm text-muted-foreground m-0"},"Sign in to an app once and your agent can use it on any device. Open an app to see the account it uses or to disconnect it.")))}\n'
        ';function EWc({searchQuery:a,children:b}){a=VVc(a);return B.createElement(TVc.Provider,{value:a},b)};'
        'var __agSafeMd=({markdown:md,className:cls,baseDirUri:bd})=>B.createElement(Bz,{value:void 0},B.createElement(h5,{cascadeId:void 0,markdown:md,context:"artifact",disableBrowserPreview:!0,className:cls,parseFrontmatter:!0,baseDirUri:bd}));'
        'function FWc({MarkdownRenderer:a,embedded:emb=!1}={}){var {q:b}=dI({strict:!1}),c=SH({select:w=>w.location.pathname}),pMid=B.useContext(UH),inR=!emb&&pMid!==void 0&&c.startsWith("/customizations"),mdR=a||(inR?T5:__agSafeMd),[locTab,setLocTab]=(0,B.useState)("browse"),[det,setDet]=(0,B.useState)(null),d=oj().get("customizations"),f=d?.showMarketplaceTab??!0,g=!f?"installed":inR?(c.startsWith("/customizations/installed")?"installed":"browse"):locTab;c=d?.pluginSources??"local";var h=BY(),k=c==="remote",[l,m]=(0,B.useState)(()=>b??h.searchQuery),[n,p]=(0,B.useState)(b);n!==b&&(p(b),b!==void 0&&m(b));(0,B.useEffect)(()=>{h.searchQuery=l},[h,l]);'
        '(0,B.useEffect)(()=>{if(!inR){window.__agCustSelect=setDet;window.__agCustTab=setLocTab;return()=>{if(window.__agCustSelect===setDet)window.__agCustSelect=null;if(window.__agCustTab===setLocTab)window.__agCustTab=null}}},[inR]);'
        'var {logTabToggle:q,logSearch:t}=z5(),u=Psc(l,800),v=(0,B.useRef)(l);(0,B.useEffect)(()=>{k||u===v.current||(v.current=u)&&t(g,u)},[u,g,k,t]);'
        'var onTab=tb=>{inR||setLocTab(tb);setDet(null);q(tb)};'
        'if(!inR&&det)return B.createElement("div",{"data-agy-embedded-cust":"1",className:"flex-1 flex flex-col overflow-hidden h-full min-h-0 bg-background"},B.createElement("div",{className:"flex-1 overflow-y-auto min-h-0 [scrollbar-gutter:stable]"},B.createElement("div",{className:"w-full max-w-4xl mx-auto px-4 sm:px-8 py-4"},B.createElement("button",{type:"button",onClick:()=>setDet(null),className:"mb-4 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground bg-transparent border-none cursor-pointer p-0"},B.createElement(nq,{name:"arrow_back",size:16}),"Customizations"),det.bundleId?B.createElement($Uc,{bundleId:det.bundleId}):B.createElement(iGc,{installDir:det.installDir,catalogId:det.catalogId,onUninstalled:()=>setDet(null),onDisconnected:()=>setDet(null),MarkdownRenderer:mdR}))));'
        'return B.createElement("div",{"data-agy-embedded-cust":inR?void 0:"1",className:"flex-1 flex flex-col overflow-hidden h-full min-h-0 bg-background"},B.createElement("div",{className:"flex-1 overflow-y-auto min-h-0 [scrollbar-gutter:stable]"},B.createElement("div",{className:"sticky top-0 z-20 bg-background"},B.createElement("div",{className:"w-full max-w-4xl mx-auto px-4 sm:px-8 pt-6 pb-4 flex flex-col gap-4"},B.createElement("div",{className:"flex flex-wrap items-center justify-between gap-2 sm:gap-4"},B.createElement("h1",{className:"text-xl font-medium text-foreground select-none sm:px-3 m-0"},"Customizations"),B.createElement("div",{className:"flex items-center gap-4"},f&&B.createElement(AWc,{tab:g,onSelect:onTab,inRoute:inR}))),B.createElement(yWc,{searchQuery:l,onSearchQueryChange:m,placeholder:"Search customizations...",inputTestId:"customizations-search"}))),B.createElement("div",{className:"max-w-4xl w-full mx-auto px-4 sm:px-8 py-6"},B.createElement(EWc,{searchQuery:k?"":g==="browse"?l:""},B.createElement(bVc,{value:l},k?B.createElement(CWc,{tab:g,MarkdownRenderer:mdR}):inR?B.createElement(WH,null):(g==="browse"?B.createElement(tWc,{MarkdownRenderer:mdR}):B.createElement(cWc,{MarkdownRenderer:mdR})))))))}'
    )
    content = must_replace(content, old_AWc_FWc, new_AWc_FWc, "AWc_FWc_dual_mode")

    content = must_replace(
        content,
        'g=Ak(u=>u.newConvoResourceSelector.selectedEnvironmentByProject),h=c.get("currentWorkspace")?.workspaceUri??void 0,k=a||b?.project?.id;a=(0,B.useMemo)(()=>k?d.getProjectStateProvider(k):void 0,[k,d]);a=Ek(a);var l=k?g[k]:void 0',
        'g=Ak(u=>u.newConvoResourceSelector?.selectedEnvironmentByProject),h=c.get("currentWorkspace")?.workspaceUri??void 0,k=a||b?.project?.id;a=(0,B.useMemo)(()=>k?d.getProjectStateProvider(k):void 0,[k,d]);a=Ek(a);var l=k&&g?g[k]:void 0',
        "safe_redux_selectedEnvironmentByProject",
    )

    content = must_replace(
        content,
        'return SH({select:c=>{c=c.matches.find(d=>a.from?a.from===d.routeId:d.id===b);VH(!((a.shouldThrow??!0)&&!c),`Could not find ${a.from?`an active match from "${a.from}"`:"a nearest match!"}`);if(c!==void 0)return a.select?a.select(c):c},structuralSharing:a.structuralSharing})}',
        'return SH({select:c=>{c=c.matches.find(d=>a.from?a.from===d.routeId:d.id===b)||c.matches[c.matches.length-1]||{params:{},_strictParams:{},search:{},_strictSearch:{}};if(c!==void 0)return a.select?a.select(c):c},structuralSharing:a.structuralSharing})}',
        "route_match_fallback_outside_outlet",
    )

    content = must_replace(
        content,
        'B.createElement($H,{to:d,params:f,search:g,onClick:m,"aria-label":p,className:"rounded-sm after:absolute after:inset-0 after:rounded-xl focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary text-left"}',
        'B.createElement($H,{to:d,params:f,search:g,onClick:ev=>{m?.(ev);if(typeof window!=="undefined"&&window.__agCustSelect&&ev?.currentTarget?.closest?.(\'[data-agy-embedded-cust]\')){ev.preventDefault();window.__agCustSelect({installDir:d==="/customizations/plugins/$pluginId"?f?.pluginId:void 0,catalogId:g?.id||(f?uB(f):void 0)})}},"aria-label":p,className:"rounded-sm after:absolute after:inset-0 after:rounded-xl focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary text-left"}',
        "v5_card_detail_in_settings",
    )

    content = must_replace(
        content,
        'B.createElement($H,{to:"/customizations",search:c?{q:b}:void 0,className:d},f)',
        'B.createElement($H,{to:"/customizations",search:c?{q:b}:void 0,onClick:ev=>{if(typeof window!=="undefined"&&window.__agCustTab&&ev?.currentTarget?.closest?.(\'[data-agy-embedded-cust]\')){ev.preventDefault();window.__agCustTab("browse")}},className:d},f)',
        "browse_in_settings",
    )

    content = must_replace(
        content,
        'var lZ=()=>{var {getActiveEditor:a}=(0,B.useContext)(XI),{logEvent:b}=GB(),c=DI();return(0,B.useCallback)((d,f)=>{b("AGENT_MANAGER_HOME");c({project:d,clearProject:f?.clearProject});queueMicrotask(()=>{var g=a();g&&document.hasFocus()&&JO(g)})},[a,b,c])};',
        'var lZ=()=>{var {getActiveEditor:a}=(0,B.useContext)(XI),{logEvent:b}=GB(),c=DI(),hideS=(0,B.useContext)(dMb)?.triggerHideSettingsModal;return(0,B.useCallback)((d,f)=>{hideS?.();b("AGENT_MANAGER_HOME");c({project:d,clearProject:f?.clearProject});queueMicrotask(()=>{var g=a();g&&document.hasFocus()&&JO(g)})},[a,b,c,hideS])};',
        "lZ_close_settings_on_prompt",
    )

    content = must_replace(
        content,
        'mlb=()=>{var a=aI(),b=glb();return(0,B.useCallback)(c=>{var d=b();a({to:"/sidecars/$sidecarId",params:{sidecarId:c},...(d?{search:d}:{})})},[a,b])}',
        'mlb=()=>{var a=aI(),b=glb(),hideS=(0,B.useContext)(dMb)?.triggerHideSettingsModal;return(0,B.useCallback)(c=>{hideS?.();var d=b();a({to:"/sidecars/$sidecarId",params:{sidecarId:c},...(d?{search:d}:{})})},[a,b,hideS])}',
        "mlb_close_settings",
    )

    content = must_replace(
        content,
        'olb=()=>{var a=aI(),b=glb();return(0,B.useCallback)(c=>{var d=b();a({to:"/sidecars/triggers/$triggerId",params:{triggerId:c},...(d?{search:d}:{})})},[a,b])}',
        'olb=()=>{var a=aI(),b=glb(),hideS=(0,B.useContext)(dMb)?.triggerHideSettingsModal;return(0,B.useCallback)(c=>{hideS?.();var d=b();a({to:"/sidecars/triggers/$triggerId",params:{triggerId:c},...(d?{search:d}:{})})},[a,b,hideS])}',
        "olb_close_settings",
    )

    content = must_replace(
        content,
        'k=b?ppd(b):"/",l=f(await d(g({initialPath:k,',
        'k=b?ppd(b):"/sdcard",l=f(await d(g({initialPath:k,',
        "default_sdcard_path",
    )

    # 4. Enable Voice Mode, Microphone, Permissions Selector, and touch/menu fixes
    content = must_replace(
        content,
        'inputComponent:{feature:{hideAgentSelectorIfEmpty:!1,hideInSubagentConversation:!1,showPermissionsSelector:!1,disableInlineCompletion:!0,showInternalModesDropdown:!1,enableMicrophone:f,showModelUsage:!0,enableFileSystemCategoriesInMentions:!1,enableGoogleWorkspaceMentions:!1,enableVoiceRelay:!1,enablePasteTextAsSnippet:!1,\nenableHelpCommand:!1}',
        'inputComponent:{feature:{hideAgentSelectorIfEmpty:!1,hideInSubagentConversation:!1,showPermissionsSelector:!0,disableInlineCompletion:!0,showInternalModesDropdown:!1,enableMicrophone:!0,showModelUsage:!0,enableFileSystemCategoriesInMentions:!1,enableGoogleWorkspaceMentions:!1,enableVoiceRelay:!0,enablePasteTextAsSnippet:!0,\nenableHelpCommand:!1}',
        "inputComponent_full",
    )
    content = must_replace(
        content,
        '{runtimeGating:{host:[zi.Web.Desktop,zi.Electron],customFlag:"enable-permissions-selector"},feature:{showPermissionsSelector:!0}}',
        '{runtimeGating:{customFlag:"enable-permissions-selector"},feature:{showPermissionsSelector:!0}}',
        "showPermissionsSelector_gating",
    )
    content = must_replace(
        content,
        'inputComponent:{feature:{disableInlineCompletion:!0,showInternalModesDropdown:!1,enableMicrophone:!1,enableVoiceRelay:!1},applyAll:',
        'inputComponent:{feature:{disableInlineCompletion:!0,showInternalModesDropdown:!1,showPermissionsSelector:!0,enableMicrophone:!0,enableVoiceRelay:!0},applyAll:',
        "inputComponent_short",
    )
    content = must_replace(
        content,
        'remoteConversationCapabilities:{feature:{fork:!1,conversationMentions:!1,sideQuestion:!1,subagentMessaging:!1,revealInFileManager:!1,extensions:!1,connectors:!1,terminal:!1,browserSubagent:!1,localPaths:!1,voice:!1}',
        'remoteConversationCapabilities:{feature:{fork:!1,conversationMentions:!1,sideQuestion:!1,subagentMessaging:!1,revealInFileManager:!1,extensions:!1,connectors:!1,terminal:!0,browserSubagent:!1,localPaths:!1,voice:!0}',
        "remoteConversationCapabilities",
    )
    content = must_replace(
        content,
        'Xa=[...(T9()?["enable-conversation-selection-quoting"]:[])',
        'Xa=["enable-voice-relay","enable-voice-remote","enable-permissions-selector","enable-paste-text-as-snippet","jetski-autonomous-mode",...(T9()?["enable-conversation-selection-quoting"]:[])',
        "Xa_customFlags",
    )
    content = must_replace(
        content,
        'let gS={isAvailable:!1,voiceState:"off",voiceConvId:null,muted:!1,liveLines:bS,speed:1};',
        'let gS={isAvailable:!0,voiceState:"off",voiceConvId:null,muted:!1,liveLines:bS,speed:1};',
        "gS_voice_isAvailable",
    )
    content = must_replace(
        content,
        'some(k=>k.kind==="audioinput");b(h)}else b(!1)',
        'some(k=>k.kind==="audioinput");b(!0)}else b(!0)',
        "hasMicrophone_always_true",
    )
    content = must_replace(
        content,
        'enabled:Oi(a,"enable-audio-transcription")}',
        'enabled:new nh(!0)}',
        "audioTranscription_enabled",
    )
    content = must_replace(
        content,
        'var G=!n&&c;v=(x||v)&&w;w=a&&!c&&!y?.isOn;var H=b??a;a=q==="idle"&&!n&&!D;f=f||l||m||p;l=!!y&&!y.isOn&&!f&&!c&&a;',
        'var G=!n&&c;v=!!w;w=a&&!c&&!y?.isOn;var H=b??a;a=q==="idle"&&!D;f=f||l||m||p;l=!!y&&!y.isOn&&!f&&!c&&a;',
        "micAndVoice_idle",
    )
    content = must_replace(
        content,
        "Eb=XRc({cascadeId:N,planModel:z?.value,enabled:!na&&Dd&&(ra??nG).voice&&(!hb||!!N)})",
        "Eb=XRc({cascadeId:N,planModel:z?.value||1018,enabled:!na&&Dd&&(ra??nG).voice&&(!hb||!!N)})",
        "XRc_planModel_fallback",
    )
    content = must_replace(
        content,
        '"shrink-0 whitespace-nowrap @max-[400px]/input-footer:w-7 @max-[400px]/input-footer:justify-center @max-[400px]/input-footer:!p-1.5",I&&"!cursor-not-allowed opacity-50 hover:!bg-transparent")},B.createElement(pPc,{preset:c,className:"@max-[400px]/input-footer:!h-4 @max-[400px]/input-footer:!w-4"}),B.createElement("span",{className:"@max-[400px]/input-footer:hidden"},z),!I&&B.createElement(nq,{name:"keyboard_arrow_down",size:14,className:"shrink-0 @max-[400px]/input-footer:hidden"})',
        '"shrink-0 whitespace-nowrap",I&&"!cursor-not-allowed opacity-50 hover:!bg-transparent")},B.createElement(pPc,{preset:c,className:""}),B.createElement("span",{className:""},z),!I&&B.createElement(nq,{name:"keyboard_arrow_down",size:14,className:"shrink-0"})',
        "mobilePermissionsBadge",
    )

    # 5. Touch & Marketplace refresh fixes
    content = must_replace(
        content,
        "Jf=Kf=>{var ig=Kc.current?.getRootElement();ig&&document.activeElement===ig&&!ig.contains(Kf.target)&&\nKf.preventDefault()}",
        'Jf=Kf=>{var ig=Kc.current?.getRootElement();ig&&document.activeElement===ig&&!ig.contains(Kf.target)&&!(Kf.target instanceof Element&&Kf.target.closest(\'button,[role="button"],[aria-haspopup],[data-testid="project-selector-trigger"],[data-testid="model-selector-trigger"]\'))&&\nKf.preventDefault()}',
        "pointerdown_allow_menu_triggers",
    )
    content = must_replace(
        content,
        'return{onPointerDown(x){p.current=x.pointerType},\nonMouseDown(x){var y=p.current,z=x.nativeEvent,A=m.select("open");if(!(x.button!==0||d==="click"||aw(y,!0)&&g)){var D=w(A,x.currentTarget,F=>F==="click"||F==="mousedown");A=Tv(z);if(Xv(A))v(D,z,A,y);else{var C=x.currentTarget;q.request(()=>{v(D,z,C,y)})}}},onClick(x){if(d!=="mousedown-only"){var y=p.current;if(d==="mousedown"&&y)p.current=void 0;else if(!aw(y,!0)||!g){var z=m.select("open");z=w(z,x.currentTarget,A=>A==="click"||A==="mousedown"||A==="keydown"||A==="keyup");v(z,x.nativeEvent,x.currentTarget,\ny)}}},onKeyDown(){p.current=void 0}}',
        'return{onPointerDown(x){p.current=x.pointerType;p.md=!1},\nonMouseDown(x){var y=p.current,z=x.nativeEvent,A=m.select("open");if(!(x.button!==0||d==="click"||aw(y,!0)&&g)){p.md=!0;var D=w(A,x.currentTarget,F=>F==="click"||F==="mousedown");A=Tv(z);if(Xv(A))v(D,z,A,y);else{var C=x.currentTarget;q.request(()=>{v(D,z,C,y)})}}},onClick(x){if(d!=="mousedown-only"){var y=p.current;if(d==="mousedown"&&y&&p.md)p.current=void 0,p.md=!1;else if(p.current=void 0,p.md=!1,!aw(y,!0)||!g){var z=m.select("open");z=w(z,x.currentTarget,A=>A==="click"||A==="mousedown"||A==="keydown"||A==="keyup");v(z,x.nativeEvent,x.currentTarget,\ny)}}},onKeyDown(){p.current=void 0;p.md=!1}}',
        "BaseUI_click_fallback_when_mousedown_prevented",
    )
    content = must_replace(
        content,
        "async function K1b(a){var b=e,c=e;try{a.isStreaming()?c(await b(a.refreshSkills())):c(await b(a.refresh()))}finally{b()}}",
        "async function K1b(a){var b=e,c=e;try{c(await b(a.refresh()))}finally{b()}}",
        "K1b_always_refresh_plugins_and_skills",
    )

    # 6. Global Root ErrorBoundary (__AgRootEB) above SettingsModal & Router to prevent #root unmount gray screens
    old_root_render = (
        '((u=h)=>{n.render(B.createElement(zra.Provider,{value:f},B.createElement(zad,{...q,featureManagerV2:u,routingConfig:m,updateService:g.updateService,managerSyncedState:g.managerSyncedState,fileSystemProviders:g.fileSystemProviders,\n'
        'MermaidDiagramComponent:fDd,WebEffects:g.WebEffects,diagnosticsService:g.diagnosticsService,settingsSyncedState:g.settingsSyncedState})))})();'
    )
    new_root_render = (
        'var __AgRootEB=class extends B.Component{constructor(pr){super(pr);this.state={err:null,retries:0}}static getDerivedStateFromError(er){return{err:er||Error("UI render error")}}componentDidCatch(er,inf){try{console.error("[AGY RootErrorBoundary]",er,inf&&inf.componentStack)}catch(_e){}if(this.state.retries<1){var _s=this;setTimeout(function(){try{if(window.history&&window.location&&window.location.search.indexOf("settingsOpen")!==-1){var _u=new URL(window.location.href);_u.searchParams.delete("settingsOpen");_u.searchParams.delete("settingsScreen");window.history.replaceState(window.history.state,"",_u.pathname+_u.search+_u.hash)}}catch(_e2){}_s.setState(function(st){return{err:null,retries:st.retries+1}})},60)}}render(){if(!this.state.err)return this.props.children;if(this.state.retries<1)return null;var _msg=String(this.state.err&&(this.state.err.message||this.state.err)||"Unexpected UI error");return B.createElement("div",{"data-testid":"agy-root-error-fallback",style:{display:"flex",flexDirection:"column",alignItems:"center",justifyContent:"center",height:"100vh",width:"100vw",padding:"24px",boxSizing:"border-box",background:"var(--background,#101010)",color:"var(--foreground,#f4f4f5)",fontFamily:"system-ui,-apple-system,sans-serif",textAlign:"center",gap:"12px"}},B.createElement("div",{style:{fontSize:"16px",fontWeight:600}},"Interface recovered from a view error"),B.createElement("div",{style:{fontSize:"12px",opacity:.72,maxWidth:"440px",wordBreak:"break-word"}},_msg),B.createElement("div",{style:{display:"flex",gap:"10px",marginTop:"6px"}},B.createElement("button",{type:"button",onClick:()=>this.setState({err:null}),style:{padding:"8px 14px",borderRadius:"8px",border:"1px solid rgba(128,128,128,0.35)",background:"transparent",color:"inherit",fontSize:"13px",cursor:"pointer"}},"Retry View"),B.createElement("button",{type:"button",onClick:()=>{try{window.location.reload()}catch(_e){}},style:{padding:"8px 14px",borderRadius:"8px",border:"none",background:"#3b82f6",color:"#fff",fontSize:"13px",fontWeight:500,cursor:"pointer"}},"Reload Interface")))}};'
        '((u=h)=>{n.render(B.createElement(__AgRootEB,null,B.createElement(zra.Provider,{value:f},B.createElement(zad,{...q,featureManagerV2:u,routingConfig:m,updateService:g.updateService,managerSyncedState:g.managerSyncedState,fileSystemProviders:g.fileSystemProviders,\n'
        'MermaidDiagramComponent:fDd,WebEffects:g.WebEffects,diagnosticsService:g.diagnosticsService,settingsSyncedState:g.settingsSyncedState}))))})();'
    )
    content = must_replace(content, old_root_render, new_root_render, "root_error_boundary")

    assert "Desktop Mode" not in content, "Desktop Mode must not be present in Android main.js"

    with open(file_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)

    print("[web-patch-2.32.1] Successfully patched Android main.js (v2.32.1 + Smart Marketplace V3)!")
    return True


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "web/main.js"
    if not patch_main(path):
        sys.exit(1)
