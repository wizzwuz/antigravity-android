package com.agy.ui.webview;

import android.util.Log;

import com.agy.bridge.AndroidBridge;
import com.agy.theme.ThemeManager;

import org.json.JSONObject;

/**
 * Injects the boot config, capability-wrapped {@code window.Android} facade,
 * and the {@code startup_ready} script ahead of the top-level app UI.
 */
public final class AppHtmlInjector {

    private static final String TAG = "WebViewHost";

    /** Web layer generates the ready signal under generated/patches. */
    private static final String READY_SCRIPT = "./generated/patches/startup_ready.js";

    private AppHtmlInjector() {
    }

    public static String inject(String html, AndroidBridge bridge, ThemeManager theme) {
        String boot;
        try {
            JSONObject config = new JSONObject(bridge.getConfigInternal());
            JSONObject endpoints = new JSONObject();
            String base = bridge.getEngineBaseUrl();
            endpoints.put("core", base);
            endpoints.put("core_http", base);
            endpoints.put("enginePort", bridge.getEnginePort());
            String nbKey = JSONObject.quote(bridge.getNativeBindingName());
            String bTok = JSONObject.quote(bridge.getBridgeAuthToken());
            boot = "<script>(function(){"
                    + "var _nb=window[" + nbKey + "];"
                    + "var _bt=" + bTok + ";"
                    + "try{delete window[" + nbKey + "];}catch(_e){}"
                    + "if(_nb){"
                    + "var _api=Object.freeze({"
                    + "onUiReady:function(){return _nb.onUiReady(_bt);},"
                    + "onUiError:function(m){return _nb.onUiError(_bt,String(m||''));},"
                    + "setTheme:function(m){return _nb.setTheme(_bt,String(m||''));},"
                    + "setThemeByUser:function(m){return _nb.setThemeByUser(_bt,String(m||''));},"
                    + "onVisualThemeChanged:function(v){return _nb.onVisualThemeChanged(_bt,String(v||''));},"
                    + "getTheme:function(){return _nb.getTheme();},"
                    + "isDesktopMode:function(){return _nb.isDesktopMode();},"
                    + "setDesktopMode:function(e){return _nb.setDesktopMode(_bt,!!e);},"
                    + "isEngineReady:function(){return _nb.isEngineReady();},"
                    + "getEnginePort:function(){return _nb.getEnginePort();},"
                    + "getEngineBaseUrl:function(){return _nb.getEngineBaseUrl();},"
                    + "getCsrfToken:function(){return _nb.getCsrfTokenAuth(_bt);},"
                    + "getConfig:function(){return _nb.getConfigAuth(_bt);},"
                    + "openUrl:function(u){return _nb.openUrlAuth(_bt,String(u||''));},"
                    + "exec:function(c){return _nb.execAuth(_bt,String(c||''));},"
                    + "shizuku:function(c){return _nb.execAuth(_bt,String(c||''));},"
                    + "shizukuAvailable:function(){return _nb.shizukuAvailableAuth(_bt);},"
                    + "postNotification:function(t,m,g){return _nb.postNotificationAuth(_bt,String(t||''),String(m||''),String(g||''));},"
                    + "listNotifications:function(){return _nb.listNotificationsAuth(_bt);},"
                    + "saveBlob:function(d,f,m){return _nb.saveBlobAuth(_bt,String(d||''),String(f||''),String(m||''));},"
                    + "installMarketplacePlugin:function(n,u,c,m,v){return _nb.installMarketplacePluginAuth(_bt,n||'',u||'',c||'',m||'',v||'');},"
                    + "postProcessInstalledPlugin:function(n){return _nb.postProcessInstalledPluginAuth(_bt,n||'');},"
                    + "uninstallMarketplacePlugin:function(n){return _nb.uninstallMarketplacePluginAuth(_bt,n||'');},"
                    + "getMicAccessStatus:function(){return _nb.getMicAccessStatus();},"
                    + "requestMicAccess:function(id){return _nb.requestMicAccessAuth(_bt,String(id||''));},"
                    + "openAppSettings:function(){return _nb.openAppSettingsAuth(_bt);},"
                    + "getAppVersion:function(){return _nb.getAppVersion();},"
                    + "getUpdateStateJson:function(){return _nb.getUpdateStateJson();},"
                    + "checkForAppUpdates:function(m){return _nb.checkForAppUpdatesAuth(_bt,!!m);},"
                    + "applyAppUpdate:function(){return _nb.applyAppUpdateAuth(_bt);},"
                    + "backupConversations:function(){return _nb.backupConversationsAuth(_bt);},"
                    + "restoreConversations:function(){return _nb.restoreConversationsAuth(_bt);},"
                    + "backupProjects:function(p){return _nb.backupProjectsAuth(_bt,String(p||''));},"
                    + "restoreProjects:function(t){return _nb.restoreProjectsAuth(_bt,String(t||''));},"
                    + "listProjects:function(){return _nb.listProjects();},"
                    + "backupSkills:function(s){return _nb.backupSkillsAuth(_bt,String(s||''));},"
                    + "restoreSkills:function(t){return _nb.restoreSkillsAuth(_bt,String(t||''));},"
                    + "listSkills:function(){return _nb.listSkills();},"
                    + "listConversations:function(){return _nb.listConversations();},"
                    + "restartApp:function(){return _nb.restartAppAuth(_bt);}"
                    + "});"
                    + "try{Object.defineProperty(window,'Android',{value:_api,writable:false,configurable:false});}catch(_e2){window.Android=_api;}"
                    + "window.AndroidBridge=window.Android;"
                    + "}"
                    + "window.__APP_CONFIG__=" + config.toString() + ";"
                    + "window.__AG_ENDPOINTS__=" + endpoints.toString() + ";"
                    + "window.__AG_CSRF__=" + JSONObject.quote(bridge.getCsrfTokenInternal()) + ";"
                    + "window.__AG_HOST_THEME__="
                    + JSONObject.quote(theme != null && theme.mode() == com.agy.theme.ThemeColors.MODE_DARK ? "dark"
                            : (theme != null && theme.mode() == com.agy.theme.ThemeColors.MODE_LIGHT ? "light" : "system")) + ";"
                    + "window.__AG_RESOLVED_THEME__="
                    + JSONObject.quote(theme != null ? theme.getTheme() : "light") + ";"
                    + "window.__agMicCallbacks={};"
                    + "window.__agResolveMicAccess=function(id,st){var fn=window.__agMicCallbacks[id];if(fn){delete window.__agMicCallbacks[id];fn(st);}};"
                    + "window.desktopMic={"
                    + "getAccessStatus:function(){try{if(window.Android&&typeof window.Android.getMicAccessStatus==='function')return Promise.resolve(window.Android.getMicAccessStatus());}catch(e){}return Promise.resolve('granted');},"
                    + "requestAccess:function(){return new Promise(function(resolve){try{if(window.Android&&typeof window.Android.getMicAccessStatus==='function'){if(window.Android.getMicAccessStatus()==='granted'){resolve('granted');return;}var id='mic_'+Date.now()+'_'+Math.random().toString(36).slice(2);window.__agMicCallbacks[id]=resolve;window.Android.requestMicAccess(id);return;}}catch(e){}resolve('granted');});},"
                    + "openSystemPreferences:function(){try{if(window.Android&&typeof window.Android.openAppSettings==='function')window.Android.openAppSettings();}catch(e){}return Promise.resolve();}"
                    + "};"
                    + "if(navigator.permissions&&typeof navigator.permissions.query==='function'){"
                    + "var _agOrigPermQuery=navigator.permissions.query.bind(navigator.permissions);"
                    + "navigator.permissions.query=function(d){try{if(d&&d.name==='microphone'&&window.Android&&typeof window.Android.getMicAccessStatus==='function'&&window.Android.getMicAccessStatus()==='granted'){return Promise.resolve({state:'granted',onchange:null,addEventListener:function(){},removeEventListener:function(){}});}}catch(e){}return _agOrigPermQuery(d);};"
                    + "}"
                    + "})();</script>"
                    // Signals first paint back to native (AndroidBridge.onUiReady)
                    // so the splash is dismissed on real content, not a timer.
                    + "<script src=\"" + READY_SCRIPT + "\"></script>";
        } catch (Exception e) {
            Log.w(TAG, "config injection failed", e);
            return html;
        }
        int head = html.indexOf("<head>");
        if (head >= 0) {
            int at = head + "<head>".length();
            return html.substring(0, at) + "\n" + boot + html.substring(at);
        }
        return boot + html;
    }
}
