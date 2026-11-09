package com.agy.bridge;

import android.content.Context;
import android.webkit.JavascriptInterface;

import com.agy.runtime.RuntimeManager;
import com.agy.shell.ShizukuBridge;
import com.agy.theme.ThemeManager;
import com.agy.ui.MainActivity;

import android.util.Log;
import java.io.File;
import java.io.FileInputStream;
import java.io.InputStreamReader;
import java.io.BufferedReader;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Map;
import org.json.JSONArray;
import org.json.JSONObject;
import java.lang.ref.WeakReference;
import java.nio.charset.Charset;
import java.security.MessageDigest;
import java.security.SecureRandom;

/**
 * Minimal, low-privilege JavaScript bridge for the app UI. It is visible to
 * embedded frames, so shell, notification, and arbitrary URL capabilities must
 * not be exposed here. Native-only getters below are intentionally unannotated.
 */
public final class AndroidBridge {

    private final UiBridge ui = new UiBridge();
    private final ThemeBridge themeBridge;
    private final EngineBridge engine;
    private final EngineConfigJson config;
    private final String blobBridgeToken = createBlobBridgeToken();
    private volatile WeakReference<MainActivity> activityRef;

    public AndroidBridge(Context context, RuntimeManager runtime,
                         ShizukuBridge shizuku, ThemeManager theme) {
        Context appContext = context.getApplicationContext();
        this.themeBridge = new ThemeBridge(theme);
        this.engine = new EngineBridge(runtime);
        this.config = new EngineConfigJson(appContext, runtime, engine, shizuku, themeBridge);
    }

    /** Host activity, used to dismiss the native splash once the UI has painted. */
    public void setActivity(MainActivity activity) {
        this.activityRef = activity != null ? new WeakReference<MainActivity>(activity) : null;
        ui.setActivity(activity);
    }

    @JavascriptInterface
    public void onUiReady(String token) {
        if (matchesNativeBridgeToken(token)) {
            ui.onUiReady();
        }
    }

    @JavascriptInterface
    public void openDirectoryPicker() {
        final MainActivity act = activityRef != null ? activityRef.get() : MainActivity.activeActivity;
        if (act != null) {
            act.runOnUiThread(new Runnable() {
                @Override
                public void run() {
                    act.launchDirectoryPicker();
                }
            });
        }
    }

    @JavascriptInterface
    public void backupConversations(final String conversationScope) {
        final MainActivity act = activityRef != null ? activityRef.get() : MainActivity.activeActivity;
        if (act != null) {
            act.runOnUiThread(new Runnable() {
                @Override
                public void run() {
                    act.launchBackupConversationsPicker(conversationScope);
                }
            });
        }
    }

    @JavascriptInterface
    public void backupConversations() {
        backupConversations(null);
    }

    @JavascriptInterface
    public String listConversations() {
        final MainActivity act = activityRef != null ? activityRef.get() : MainActivity.activeActivity;
        Context ctx = act != null ? act.getApplicationContext() : null;
        return com.agy.util.BackupRestoreHelper.listConversationsJson(ctx);
    }

    @JavascriptInterface
    public void restoreConversations() {
        final MainActivity act = activityRef != null ? activityRef.get() : MainActivity.activeActivity;
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
    public void backupProjects(final String projectName) {
        final MainActivity act = activityRef != null ? activityRef.get() : MainActivity.activeActivity;
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
    public void restoreProjects(final String targetName) {
        final MainActivity act = activityRef != null ? activityRef.get() : MainActivity.activeActivity;
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
        final MainActivity act = activityRef != null ? activityRef.get() : MainActivity.activeActivity;
        Context ctx = act != null ? act.getApplicationContext() : null;
        return com.agy.util.BackupRestoreHelper.listProjectsJson(ctx);
    }

    @JavascriptInterface
    public void restartApp() {
        final MainActivity act = activityRef != null ? activityRef.get() : MainActivity.activeActivity;
        if (act != null) {
            act.restartApp();
        }
    }

    @JavascriptInterface
    public void promptRestart(final String message) {
        final MainActivity act = activityRef != null ? activityRef.get() : MainActivity.activeActivity;
        if (act != null) {
            act.showRestartPrompt(message);
        }
    }

    @JavascriptInterface
    public void onUiError(String token, final String errorMessage) {
        if (matchesNativeBridgeToken(token)) {
            ui.onUiError(errorMessage);
        }
    }

    @JavascriptInterface
    public boolean setTheme(String mode) {
        return themeBridge.setTheme(mode);
    }

    @JavascriptInterface
    public boolean setThemeByUser(final String mode) {
        return themeBridge.setThemeByUser(mode);
    }

    @JavascriptInterface
    public void onVisualThemeChanged(String visual) {
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
    public void setDesktopMode(boolean enabled) {
        ui.setDesktopMode(enabled);
    }

    @JavascriptInterface
    public void postNotification(String channel, String title, String message, String cascadeId, boolean ongoing, int progress) {
        final MainActivity act = activityRef != null ? activityRef.get() : MainActivity.activeActivity;
        Context ctx = act != null ? act.getApplicationContext() : null;
        if (ctx != null) {
            com.agy.gateway.handlers.NotificationHandler.post(ctx, channel, title, message, cascadeId, ongoing, progress, 0, null);
        }
    }

    @JavascriptInterface
    public void cancelNotification(String tag, int id) {
        final MainActivity act = activityRef != null ? activityRef.get() : MainActivity.activeActivity;
        Context ctx = act != null ? act.getApplicationContext() : null;
        if (ctx != null) {
            com.agy.gateway.handlers.NotificationHandler.cancel(ctx, tag, id);
        }
    }

    @JavascriptInterface
    public String searchConversations(String query, int limit) {
        if (query == null || query.trim().isEmpty()) {
            return "{\"results\":[]}";
        }
        final String qLower = query.trim().toLowerCase();
        final int maxResults = limit > 0 ? Math.min(limit, 100) : 50;

        JSONArray results = new JSONArray();
        try {
            final MainActivity act = activityRef != null ? activityRef.get() : MainActivity.activeActivity;
            Context ctx = act != null ? act.getApplicationContext() : null;
            File baseDir = ctx != null ? ctx.getFilesDir() : new File("/data/user/0/com.agy/files");
            File geminiDir = new File(baseDir, ".gemini/antigravity-app");
            if (!geminiDir.exists()) {
                geminiDir = new File("/data/user/0/com.krmobdev.antigravity/files/.gemini/antigravity-app");
            }

            Map<String, String> titles = new HashMap<>();
            File dbFile = new File(geminiDir, "conversation_summaries.db");
            if (dbFile.exists()) {
                android.database.sqlite.SQLiteDatabase db = null;
                android.database.Cursor cursor = null;
                try {
                    db = android.database.sqlite.SQLiteDatabase.openDatabase(
                            dbFile.getAbsolutePath(), null, android.database.sqlite.SQLiteDatabase.OPEN_READONLY);
                    cursor = db.rawQuery("SELECT conversation_id, title FROM conversation_summaries", null);
                    if (cursor != null && cursor.moveToFirst()) {
                        do {
                            String cid = cursor.getString(0);
                            String title = cursor.getString(1);
                            if (cid != null) {
                                titles.put(cid, title != null ? title : "Untitled Conversation");
                            }
                        } while (cursor.moveToNext());
                    }
                } catch (Throwable t) {
                    Log.w("AndroidBridge", "searchConversations db read error: " + t.getMessage());
                } finally {
                    if (cursor != null) {
                        try { cursor.close(); } catch (Throwable ignored) {}
                    }
                    if (db != null) {
                        try { db.close(); } catch (Throwable ignored) {}
                    }
                }
            }

            File brainDir = new File(geminiDir, "brain");
            if (brainDir.exists() && brainDir.isDirectory()) {
                File[] convoDirs = brainDir.listFiles();
                if (convoDirs != null) {
                    for (File dir : convoDirs) {
                        if (results.length() >= maxResults) break;
                        if (!dir.isDirectory()) continue;
                        String cid = dir.getName();
                        File transcript = new File(dir, ".system_generated/logs/transcript.jsonl");
                        if (!transcript.exists() || !transcript.isFile()) continue;

                        String title = titles.containsKey(cid) ? titles.get(cid) : "Untitled Conversation";

                        JSONArray titleMatchRanges = new JSONArray();
                        int tIdx = title.toLowerCase().indexOf(qLower);
                        if (tIdx >= 0) {
                            JSONObject tm = new JSONObject();
                            tm.put("startOffset", tIdx);
                            tm.put("endOffsetExclusive", tIdx + qLower.length());
                            titleMatchRanges.put(tm);
                        }

                        BufferedReader br = null;
                        try {
                            br = new BufferedReader(new InputStreamReader(
                                    new FileInputStream(transcript), StandardCharsets.UTF_8));
                            String line;
                            while ((line = br.readLine()) != null) {
                                if (line.toLowerCase().contains(qLower)) {
                                    String content = "";
                                    try {
                                        JSONObject json = new JSONObject(line);
                                        content = json.optString("content", "");
                                        if (content.isEmpty() && json.has("tool_calls")) {
                                            content = json.opt("tool_calls").toString();
                                        }
                                    } catch (Throwable ignored) {
                                        content = line;
                                    }

                                    int idx = content.toLowerCase().indexOf(qLower);
                                    if (idx >= 0) {
                                        int startPos = Math.max(0, idx - 40);
                                        int endPos = Math.min(content.length(), idx + qLower.length() + 60);
                                        String prefix = startPos > 0 ? "... " : "";
                                        String suffix = endPos < content.length() ? " ..." : "";
                                        String rawSnippet = content.substring(startPos, endPos).replace('\n', ' ').replace('\r', ' ');
                                        String snippet = prefix + rawSnippet + suffix;

                                        int matchStart = prefix.length() + (idx - startPos);
                                        int matchEnd = matchStart + qLower.length();

                                        JSONArray snippetRanges = new JSONArray();
                                        JSONObject sr = new JSONObject();
                                        sr.put("startOffset", matchStart);
                                        sr.put("endOffsetExclusive", matchEnd);
                                        snippetRanges.put(sr);

                                        JSONObject item = new JSONObject();
                                        item.put("cascadeId", cid);
                                        item.put("title", title);
                                        item.put("snippet", snippet);
                                        item.put("snippetMatchRanges", snippetRanges);
                                        item.put("titleMatchRanges", titleMatchRanges);
                                        results.put(item);
                                        break;
                                    }
                                }
                            }
                        } catch (Throwable t) {
                            Log.w("AndroidBridge", "Error reading transcript " + transcript.getPath() + ": " + t.getMessage());
                        } finally {
                            if (br != null) {
                                try { br.close(); } catch (Throwable ignored) {}
                            }
                        }
                    }
                }
            }
        } catch (Throwable t) {
            Log.w("AndroidBridge", "searchConversations error: " + t.getMessage());
        }

        JSONObject resp = new JSONObject();
        try {
            resp.put("results", results);
        } catch (Throwable ignored) {}
        return resp.toString();
    }

    // Native-only helpers used while preparing the trusted app document.
    public boolean isEngineReady() {
        return engine.isReady();
    }

    public int getEnginePort() {
        return engine.getPort();
    }

    public String getEngineBaseUrl() {
        return engine.getBaseUrl();
    }

    public String getCsrfToken() {
        return engine.getCsrfToken();
    }

    public String getConfig() {
        return config.get();
    }

    /** Native-only token inserted into the trusted top-level document. */
    public String getBlobBridgeToken() {
        return blobBridgeToken;
    }

    /** Saves a downloaded blob only for scripts holding the top-level document token. */
    @JavascriptInterface
    public void saveBlob(String token, String base64Data, String filename, String mimeType) {
        if (!matchesNativeBridgeToken(token)) {
            return;
        }
        final MainActivity act = activityRef != null ? activityRef.get() : MainActivity.activeActivity;
        if (act != null) {
            com.agy.ui.download.FileDownloader.handleBlobData(
                    act, base64Data, filename, mimeType);
        }
    }

    private boolean matchesNativeBridgeToken(String candidate) {
        if (candidate == null) {
            return false;
        }
        try {
            byte[] expected = blobBridgeToken.getBytes(Charset.forName("UTF-8"));
            byte[] actual = candidate.getBytes(Charset.forName("UTF-8"));
            return MessageDigest.isEqual(expected, actual);
        } catch (Exception ignored) {
            return false;
        }
    }

    private static String createBlobBridgeToken() {
        byte[] random = new byte[32];
        new SecureRandom().nextBytes(random);
        char[] hex = "0123456789abcdef".toCharArray();
        char[] encoded = new char[random.length * 2];
        for (int i = 0; i < random.length; i++) {
            int value = random[i] & 0xff;
            encoded[i * 2] = hex[value >>> 4];
            encoded[i * 2 + 1] = hex[value & 0x0f];
        }
        return new String(encoded);
    }
}
