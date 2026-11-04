package com.agy.gateway.handlers;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.os.Build;
import android.util.Log;

import org.json.JSONObject;

/**
 * Handles native Android notifications and notification categories:
 * 1. Agent completed in the open chat (notification shade without a heads-up banner)
 * 2. Agent completed (floating notification / heads-up banner, finished or needs attention)
 * 3. Agent progress (silent progress for Antigravity tasks)
 */
public final class NotificationHandler {

    private static final String TAG = "NotificationHandler";

    // User requested notification categories
    public static final String CHANNEL_AGENT_COMPLETED_OPEN_CHAT = "agent_completed_open_chat";
    public static final String CHANNEL_AGENT_COMPLETED = "agent_completed";
    public static final String CHANNEL_AGENT_PROGRESS = "agent_progress";

    // Legacy channel compatibility
    public static final String CHANNEL_TASKS = "agy_tasks";
    public static final String CHANNEL_ALERTS = "agy_alerts";

    private final Context context;
    private final NotificationManager manager;

    public NotificationHandler(Context context) {
        this.context = context.getApplicationContext();
        this.manager = (NotificationManager) this.context.getSystemService(Context.NOTIFICATION_SERVICE);
        initChannels(this.context);
    }

    public static void initChannels(Context context) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O && context != null) {
            NotificationManager manager = (NotificationManager) context.getSystemService(Context.NOTIFICATION_SERVICE);
            if (manager == null) {
                return;
            }

            // 1. Agent completed in the open chat: notification shade without a heads-up banner
            NotificationChannel openChat = new NotificationChannel(
                    CHANNEL_AGENT_COMPLETED_OPEN_CHAT,
                    "Agent completed in the open chat",
                    NotificationManager.IMPORTANCE_DEFAULT);
            openChat.setDescription("Completion in the open chat: notification shade without a heads-up banner");
            openChat.setShowBadge(true);
            openChat.setLockscreenVisibility(Notification.VISIBILITY_PUBLIC);
            manager.createNotificationChannel(openChat);

            // 2. Agent completed: Agent finished or needs attention (floating heads-up banner support)
            NotificationChannel completed = new NotificationChannel(
                    CHANNEL_AGENT_COMPLETED,
                    "Agent completed",
                    NotificationManager.IMPORTANCE_HIGH);
            completed.setDescription("Agent finished or needs attention");
            completed.enableLights(true);
            completed.enableVibration(true);
            completed.setVibrationPattern(new long[]{0, 250, 100, 250});
            completed.setShowBadge(true);
            completed.setLockscreenVisibility(Notification.VISIBILITY_PUBLIC);
            manager.createNotificationChannel(completed);

            // 3. Agent progress: Silent progress for Antigravity tasks
            NotificationChannel progress = new NotificationChannel(
                    CHANNEL_AGENT_PROGRESS,
                    "Agent progress",
                    NotificationManager.IMPORTANCE_LOW);
            progress.setDescription("Silent progress for Antigravity tasks");
            progress.setShowBadge(false);
            progress.setLockscreenVisibility(Notification.VISIBILITY_PUBLIC);
            manager.createNotificationChannel(progress);

            // Legacy fallback channels for compatibility
            NotificationChannel tasks = new NotificationChannel(
                    CHANNEL_TASKS, "Antigravity Tasks", NotificationManager.IMPORTANCE_LOW);
            tasks.setDescription("Notifications for ongoing AI agent and environment tasks");
            manager.createNotificationChannel(tasks);

            NotificationChannel alerts = new NotificationChannel(
                    CHANNEL_ALERTS, "Antigravity Alerts", NotificationManager.IMPORTANCE_HIGH);
            alerts.setDescription("High-priority alerts and task completions");
            manager.createNotificationChannel(alerts);
        }
    }

    public static void post(Context context, String channel, String title, String message,
                            String cascadeId, boolean ongoing, int progress, int id, String tag) {
        if (context == null) return;
        NotificationManager manager = (NotificationManager) context.getSystemService(Context.NOTIFICATION_SERVICE);
        if (manager == null) return;

        initChannels(context);

        // Normalize channel alias
        if (channel == null || channel.isEmpty()) {
            channel = ongoing ? CHANNEL_AGENT_PROGRESS : CHANNEL_AGENT_COMPLETED;
        } else if (CHANNEL_TASKS.equalsIgnoreCase(channel)) {
            channel = CHANNEL_AGENT_PROGRESS;
        } else if (CHANNEL_ALERTS.equalsIgnoreCase(channel)) {
            channel = CHANNEL_AGENT_COMPLETED;
        }

        // Determine stable per-conversation tag & ID for multi-conversation support
        String actualTag;
        int actualId;
        if (cascadeId != null && !cascadeId.isEmpty()) {
            int hashOffset = Math.abs(cascadeId.hashCode() % 50000);
            if (CHANNEL_AGENT_PROGRESS.equals(channel)) {
                actualTag = "cascade_prog_" + cascadeId;
                actualId = 10000 + hashOffset;
            } else {
                actualTag = "cascade_done_" + cascadeId;
                actualId = 60000 + hashOffset;
                // Automatically dismiss any active progress notification for this conversation
                try {
                    manager.cancel("cascade_prog_" + cascadeId, 10000 + hashOffset);
                } catch (Throwable ignored) {}
            }
        } else {
            actualTag = tag != null && !tag.isEmpty() ? tag : "agy_notification";
            actualId = id > 0 ? id : (ongoing ? 1001 : 1002);
        }

        int icon = context.getResources().getIdentifier("ic_notification", "drawable", context.getPackageName());
        if (icon == 0) {
            icon = android.R.drawable.ic_dialog_info;
        }

        Notification.Builder builder = Build.VERSION.SDK_INT >= Build.VERSION_CODES.O
                ? new Notification.Builder(context, channel)
                : new Notification.Builder(context);

        builder.setContentTitle(title)
                .setContentText(message)
                .setSmallIcon(icon)
                .setOngoing(ongoing)
                .setAutoCancel(!ongoing);

        // Progress bar configuration
        if (progress >= 0) {
            builder.setProgress(100, Math.min(100, Math.max(0, progress)), false);
        } else if (ongoing) {
            builder.setProgress(0, 0, true);
        }

        // Action Intent to bring app to foreground and navigate directly to conversation
        Intent intent = new Intent(context, com.agy.ui.MainActivity.class);
        intent.setAction("com.agy.action.OPEN_CONVERSATION");
        intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_SINGLE_TOP | Intent.FLAG_ACTIVITY_CLEAR_TOP);
        if (cascadeId != null && !cascadeId.isEmpty()) {
            intent.putExtra("cascade_id", cascadeId);
        }

        int pendingFlags = PendingIntent.FLAG_UPDATE_CURRENT;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            pendingFlags |= PendingIntent.FLAG_IMMUTABLE;
        }
        PendingIntent pi = PendingIntent.getActivity(context, actualId, intent, pendingFlags);
        builder.setContentIntent(pi);

        // Configure floating notification support / priority
        if (CHANNEL_AGENT_COMPLETED.equals(channel)) {
            builder.setPriority(Notification.PRIORITY_MAX);
            builder.setDefaults(Notification.DEFAULT_ALL);
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
                builder.setCategory(Notification.CATEGORY_EVENT);
                builder.setVibrate(new long[]{0, 250, 100, 250});
            }
        } else if (CHANNEL_AGENT_PROGRESS.equals(channel)) {
            builder.setPriority(Notification.PRIORITY_LOW);
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
                builder.setCategory(Notification.CATEGORY_PROGRESS);
            }
        } else {
            // CHANNEL_AGENT_COMPLETED_OPEN_CHAT: notification shade without a heads-up banner
            builder.setPriority(Notification.PRIORITY_DEFAULT);
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
                builder.setCategory(Notification.CATEGORY_STATUS);
            }
        }

        manager.notify(actualTag, actualId, builder.build());
    }

    public static void cancel(Context context, String tag, int id) {
        if (context == null) return;
        NotificationManager manager = (NotificationManager) context.getSystemService(Context.NOTIFICATION_SERVICE);
        if (manager == null) return;

        if (tag != null && tag.startsWith("cascade_")) {
            // Cancel by explicit tag and computed ID if id is 0
            int cancelId = id > 0 ? id : 10000 + Math.abs(tag.hashCode() % 50000);
            manager.cancel(tag, cancelId);
            // Also try canceling with 0 or fallback ID
            manager.cancel(tag, 0);
        } else {
            manager.cancel(tag != null ? tag : "agy_notification", id);
        }
    }

    public JSONObject handle(JSONObject payload) {
        JSONObject resp = new JSONObject();
        try {
            String action = payload.optString("action", "post");
            String tag = payload.optString("tag", "agy_task");
            int id = payload.optInt("id", (int) (System.currentTimeMillis() % 100000));

            if ("cancel".equalsIgnoreCase(action)) {
                cancel(context, tag, id);
                resp.put("ok", true);
                resp.put("cancelled", true);
                return resp;
            }

            String title = payload.optString("title", "Antigravity");
            String message = payload.optString("message", "");
            int progress = payload.optInt("progress", -1);
            boolean ongoing = payload.optBoolean("ongoing", false);
            String channel = payload.optString("channel", payload.optString("category", null));
            String cascadeId = payload.optString("cascadeId", payload.optString("cascade_id", null));

            post(context, channel, title, message, cascadeId, ongoing, progress, id, tag);

            resp.put("ok", true);
            resp.put("tag", tag);
            resp.put("id", id);
            resp.put("channel", channel);
        } catch (Exception e) {
            Log.w(TAG, "Notification error: " + e.getMessage());
            try {
                resp.put("ok", false);
                resp.put("error", e.getMessage());
            } catch (Exception ignored) {}
        }
        return resp;
    }
}
