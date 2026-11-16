package com.agy.bridge;

import android.content.Context;
import android.util.Log;
import android.webkit.JavascriptInterface;

import com.agy.oauth.OAuthManager;
import com.agy.runtime.RuntimeManager;
import com.agy.shell.ShizukuBridge;
import com.agy.theme.ThemeManager;
import com.agy.ui.MainActivity;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.SecureRandom;

/**
 * Native JS bridge bound under a per-process randomized name and wrapped as
 * {@code window.Android} exclusively inside the top-level host document
 * ({@code https://127.0.0.1:<enginePort>/}). All privileged methods require a
 * constant-time per-boot capability token held inside the top-level JS closure,
 * isolating subframes and untrusted loopback ports from native execution.
 */
public final class AndroidBridge {

    private static final String TAG = "AndroidBridge";

    private final Context appContext;
    private final UiBridge ui = new UiBridge();
    private final ThemeBridge themeBridge;
    private final EngineBridge engine;
    private final EngineConfigJson config;
    private final ExternalUrlBridge external;
    private final ShellBridge shell;
    private final NotificationBridge notification;
    private final String nativeBindingName;
    private final byte[] authTokenBytes;
    private final String authTokenHex;

    public AndroidBridge(Context context, RuntimeManager runtime,
                         ShizukuBridge shizuku, OAuthManager oauth,
                         ThemeManager theme) {
        Context appContext = context.getApplicationContext();
        this.appContext = appContext;
        this.themeBridge = new ThemeBridge(theme);
        this.engine = new EngineBridge(runtime);
        this.config = new EngineConfigJson(appContext, runtime, engine, shizuku, themeBridge);
        this.external = new ExternalUrlBridge(appContext, oauth);
        this.shell = new ShellBridge(shizuku);
        this.notification = new NotificationBridge(appContext, shizuku);

        SecureRandom rng = new SecureRandom();
        byte[] suffix = new byte[8];
        byte[] secret = new byte[24];
        rng.nextBytes(suffix);
        rng.nextBytes(secret);
        this.nativeBindingName = "__agy_nb_" + toHex(suffix);
        this.authTokenHex = toHex(secret);
        this.authTokenBytes = this.authTokenHex.getBytes(StandardCharsets.UTF_8);
    }

    private static String toHex(byte[] bytes) {
        char[] hexChars = "0123456789abcdef".toCharArray();
        char[] out = new char[bytes.length * 2];
        for (int i = 0; i < bytes.length; i++) {
            int v = bytes[i] & 0xFF;
            out[i * 2] = hexChars[v >>> 4];
            out[i * 2 + 1] = hexChars[v & 0x0F];
        }
        return new String(out);
    }

    private boolean isAuthorized(String token) {
        if (token == null || token.isEmpty()) {
            Log.w(TAG, "Blocked unauthorized JS bridge call (missing token)");
            return false;
        }
        boolean ok = MessageDigest.isEqual(
                authTokenBytes, token.getBytes(StandardCharsets.UTF_8));
        if (!ok) {
            Log.w(TAG, "Blocked unauthorized JS bridge call (invalid token)");
        }
        return ok;
    }

    public String getNativeBindingName() {
        return nativeBindingName;
    }

    public String getBridgeAuthToken() {
        return authTokenHex;
    }

    /** Host activity, used to dismiss the native splash once the UI has painted. */
    public void setActivity(MainActivity activity) {
        ui.setActivity(activity);
    }

    /** Java-internal getters for host WebView setup (not exposed unauthenticated to JS). */
    public String getCsrfTokenInternal() {
        return engine.getCsrfToken();
    }

    public String getConfigInternal() {
        return config.get();
    }

    @JavascriptInterface
    public void onUiReady(String authToken) {
        if (!isAuthorized(authToken)) return;
        ui.onUiReady();
    }

    @JavascriptInterface
    public void onUiError(String authToken, final String errorMessage) {
        if (!isAuthorized(authToken)) return;
        ui.onUiError(errorMessage);
    }

    @JavascriptInterface
    public boolean setTheme(String authToken, String mode) {
        if (!isAuthorized(authToken)) return false;
        return themeBridge.setTheme(mode);
    }

    @JavascriptInterface
    public boolean setThemeByUser(String authToken, final String mode) {
        if (!isAuthorized(authToken)) return false;
        return themeBridge.setThemeByUser(mode);
    }

    @JavascriptInterface
    public void onVisualThemeChanged(String authToken, String visual) {
        if (!isAuthorized(authToken)) return;
        themeBridge.onVisualThemeChanged(visual);
    }

    @JavascriptInterface
    public String getTheme() {
        return themeBridge.getTheme();
    }

    @JavascriptInterface
    public boolean isDesktopMode() {
        return ui.isDesktopMode();
    }

    @JavascriptInterface
    public void setDesktopMode(String authToken, boolean enabled) {
        if (!isAuthorized(authToken)) return;
        ui.setDesktopMode(enabled);
    }

    @JavascriptInterface
    public boolean isEngineReady() {
        return engine.isReady();
    }

    @JavascriptInterface
    public int getEnginePort() {
        return engine.getPort();
    }

    @JavascriptInterface
    public String getEngineBaseUrl() {
        return engine.getBaseUrl();
    }

    @JavascriptInterface
    public String getCsrfTokenAuth(String authToken) {
        if (!isAuthorized(authToken)) return "";
        return engine.getCsrfToken();
    }

    @JavascriptInterface
    public String getConfigAuth(String authToken) {
        if (!isAuthorized(authToken)) return "{}";
        return config.get();
    }

    @JavascriptInterface
    public void openUrlAuth(String authToken, String url) {
        if (!isAuthorized(authToken)) return;
        external.open(url);
    }

    @JavascriptInterface
    public String execAuth(String authToken, String cmd) {
        if (!isAuthorized(authToken)) return "";
        return shell.exec(cmd);
    }

    @JavascriptInterface
    public boolean shizukuAvailableAuth(String authToken) {
        if (!isAuthorized(authToken)) return false;
        return shell.available();
    }

    @JavascriptInterface
    public boolean postNotificationAuth(String authToken, String title, String message, String tag) {
        if (!isAuthorized(authToken)) return false;
        return notification.post(title, message, tag);
    }

    @JavascriptInterface
    public String listNotificationsAuth(String authToken) {
        if (!isAuthorized(authToken)) return "[]";
        return notification.list();
    }

    @JavascriptInterface
    public void saveBlobAuth(String authToken, String base64Data, String filename, String mimeType) {
        if (!isAuthorized(authToken)) return;
        if (MainActivity.activeActivity != null) {
            com.agy.ui.download.FileDownloader.handleBlobData(
                    MainActivity.activeActivity, base64Data, filename, mimeType);
        }
    }

    @JavascriptInterface
    public String installMarketplacePluginAuth(String authToken, String pluginName, String archiveUrl,
                                               String catalogId, String marketplace, String version) {
        if (!isAuthorized(authToken)) {
            return "{\"success\":false,\"message\":\"Unauthorized\"}";
        }
        return engine.installMarketplacePlugin(pluginName, archiveUrl, catalogId, marketplace, version);
    }

    @JavascriptInterface
    public String postProcessInstalledPluginAuth(String authToken, String pluginName) {
        if (!isAuthorized(authToken)) {
            return "{\"success\":false}";
        }
        return engine.postProcessInstalledPlugin(pluginName);
    }

    @JavascriptInterface
    public boolean uninstallMarketplacePluginAuth(String authToken, String pluginName) {
        if (!isAuthorized(authToken)) return false;
        return engine.uninstallMarketplacePlugin(pluginName);
    }

    @JavascriptInterface
    public String getMicAccessStatus() {
        try {
            if (android.os.Build.VERSION.SDK_INT < android.os.Build.VERSION_CODES.M) {
                return "granted";
            }
            MainActivity act = MainActivity.activeActivity;
            Context ctx = act != null ? act : appContext;
            if (ctx != null && ctx.checkSelfPermission(android.Manifest.permission.RECORD_AUDIO)
                    == android.content.pm.PackageManager.PERMISSION_GRANTED) {
                return "granted";
            }
            return "not-determined";
        } catch (Throwable t) {
            return "granted";
        }
    }

    @JavascriptInterface
    public void requestMicAccessAuth(String authToken, final String callbackId) {
        if (!isAuthorized(authToken)) return;
        MainActivity act = MainActivity.activeActivity;
        if (act != null) {
            act.requestMicAccessFromJs(callbackId);
        }
    }

    @JavascriptInterface
    public void openAppSettingsAuth(String authToken) {
        if (!isAuthorized(authToken)) return;
        try {
            MainActivity act = MainActivity.activeActivity;
            Context ctx = act != null ? act : appContext;
            if (ctx != null) {
                android.content.Intent intent = new android.content.Intent(
                        android.provider.Settings.ACTION_APPLICATION_DETAILS_SETTINGS);
                intent.setData(android.net.Uri.parse("package:" + ctx.getPackageName()));
                intent.addFlags(android.content.Intent.FLAG_ACTIVITY_NEW_TASK);
                ctx.startActivity(intent);
            }
        } catch (Throwable ignored) {
        }
    }

    @JavascriptInterface
    public String getAppVersion() {
        try {
            return com.agy.update.AppUpdateManager.getInstance(appContext).getInstalledVersion();
        } catch (Throwable t) {
            return com.agy.runtime.RuntimeConfig.CORE_VERSION;
        }
    }

    @JavascriptInterface
    public String getUpdateStateJson() {
        try {
            return com.agy.update.AppUpdateManager.getInstance(appContext).getStateJson();
        } catch (Throwable t) {
            return "{\"type\":\"idle\"}";
        }
    }

    @JavascriptInterface
    public void checkForAppUpdatesAuth(String authToken, boolean manual) {
        if (!isAuthorized(authToken)) return;
        try {
            com.agy.update.AppUpdateManager.getInstance(appContext).checkForUpdates(manual);
        } catch (Throwable ignored) {
        }
    }

    @JavascriptInterface
    public void applyAppUpdateAuth(String authToken) {
        if (!isAuthorized(authToken)) return;
        try {
            com.agy.update.AppUpdateManager.getInstance(appContext).applyUpdate();
        } catch (Throwable ignored) {
        }
    }

    // =========================================================================
    // BACKUP & RESTORE
    // =========================================================================

    @JavascriptInterface
    public void backupConversationsAuth(String authToken) {
        if (!isAuthorized(authToken)) return;
        backupConversations();
    }

    @JavascriptInterface
    public void backupConversations() {
        final MainActivity act = MainActivity.activeActivity;
        if (act != null) {
            act.runOnUiThread(new Runnable() {
                @Override
                public void run() {
                    act.launchBackupConversationsPicker();
                }
            });
        }
    }

    @JavascriptInterface
    public void restoreConversationsAuth(String authToken) {
        if (!isAuthorized(authToken)) return;
        restoreConversations();
    }

    @JavascriptInterface
    public void restoreConversations() {
        final MainActivity act = MainActivity.activeActivity;
        if (act != null) {
            act.runOnUiThread(new Runnable() {
                @Override
                public void run() {
                    act.launchRestoreConversationsPicker();
                }
            });
        }
    }

    @JavascriptInterface
    public void backupProjectsAuth(String authToken, final String projectName) {
        if (!isAuthorized(authToken)) return;
        backupProjects(projectName);
    }

    @JavascriptInterface
    public void backupProjects(final String projectName) {
        final MainActivity act = MainActivity.activeActivity;
        if (act != null) {
            act.runOnUiThread(new Runnable() {
                @Override
                public void run() {
                    act.launchBackupProjectsPicker(projectName);
                }
            });
        }
    }

    @JavascriptInterface
    public void restoreProjectsAuth(String authToken, final String targetName) {
        if (!isAuthorized(authToken)) return;
        restoreProjects(targetName);
    }

    @JavascriptInterface
    public void restoreProjects(final String targetName) {
        final MainActivity act = MainActivity.activeActivity;
        if (act != null) {
            act.runOnUiThread(new Runnable() {
                @Override
                public void run() {
                    act.launchRestoreProjectsPicker(targetName);
                }
            });
        }
    }

    @JavascriptInterface
    public String listProjects() {
        final MainActivity act = MainActivity.activeActivity;
        android.content.Context ctx = act != null ? act.getApplicationContext() : appContext;
        return com.agy.util.BackupRestoreHelper.listProjectsJson(ctx);
    }

    @JavascriptInterface
    public void backupSkillsAuth(String authToken, final String skillName) {
        if (!isAuthorized(authToken)) return;
        backupSkills(skillName);
    }

    @JavascriptInterface
    public void backupSkills(final String skillName) {
        final MainActivity act = MainActivity.activeActivity;
        if (act != null) {
            act.runOnUiThread(new Runnable() {
                @Override
                public void run() {
                    act.launchBackupSkillsPicker(skillName);
                }
            });
        }
    }

    @JavascriptInterface
    public void restoreSkillsAuth(String authToken, final String targetName) {
        if (!isAuthorized(authToken)) return;
        restoreSkills(targetName);
    }

    @JavascriptInterface
    public void restoreSkills(final String targetName) {
        final MainActivity act = MainActivity.activeActivity;
        if (act != null) {
            act.runOnUiThread(new Runnable() {
                @Override
                public void run() {
                    act.launchRestoreSkillsPicker(targetName);
                }
            });
        }
    }

    @JavascriptInterface
    public String listSkills() {
        final MainActivity act = MainActivity.activeActivity;
        android.content.Context ctx = act != null ? act.getApplicationContext() : appContext;
        return com.agy.util.BackupRestoreHelper.listSkillsJson(ctx);
    }

    @JavascriptInterface
    public String listConversations() {
        final MainActivity act = MainActivity.activeActivity;
        android.content.Context ctx = act != null ? act.getApplicationContext() : appContext;
        return com.agy.util.BackupRestoreHelper.listConversationsJson(ctx);
    }

    @JavascriptInterface
    public void restartAppAuth(String authToken) {
        if (!isAuthorized(authToken)) return;
        restartApp();
    }

    @JavascriptInterface
    public void restartApp() {
        final MainActivity act = MainActivity.activeActivity;
        if (act != null) {
            act.runOnUiThread(new Runnable() {
                @Override
                public void run() {
                    try {
                        android.content.Intent intent = act.getPackageManager().getLaunchIntentForPackage(act.getPackageName());
                        if (intent != null) {
                            intent.addFlags(android.content.Intent.FLAG_ACTIVITY_NEW_TASK | android.content.Intent.FLAG_ACTIVITY_CLEAR_TASK);
                            act.startActivity(intent);
                            Runtime.getRuntime().exit(0);
                        }
                    } catch (Throwable ignored) {}
                }
            });
        }
    }
}
