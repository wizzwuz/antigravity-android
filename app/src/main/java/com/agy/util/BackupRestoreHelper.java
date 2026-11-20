package com.agy.util;

import android.content.Context;
import android.database.sqlite.SQLiteDatabase;
import android.net.Uri;
import android.util.Log;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedInputStream;
import java.io.BufferedOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import android.database.Cursor;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.zip.Deflater;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;
import java.util.zip.ZipOutputStream;

/**
 * Manages backup and restore operations for Antigravity conversations and project files.
 * Provides high-speed compressed archiving with path traversal protection and SQLite merging.
 */
public final class BackupRestoreHelper {

    private static final String TAG = "BackupRestoreHelper";
    private static final int BUFFER_SIZE = 64 * 1024;

    private BackupRestoreHelper() {
    }

    public static File getGeminiDir(Context context) {
        File baseDir = context != null ? context.getFilesDir() : new File("/data/user/0/com.agy/files");
        File geminiDir = new File(baseDir, ".gemini/antigravity-app");
        if (!geminiDir.exists()) {
            File fallback = new File("/data/user/0/com.krmobdev.antigravity/files/.gemini/antigravity-app");
            if (fallback.exists()) {
                return fallback;
            }
        }
        return geminiDir;
    }

    public static List<String> listProjects(Context context) {
        List<String> list = new ArrayList<String>();
        try {
            File geminiDir = getGeminiDir(context);
            File scratch = new File(geminiDir, "scratch");
            if (scratch.exists() && scratch.isDirectory()) {
                File[] files = scratch.listFiles();
                if (files != null) {
                    for (File f : files) {
                        if (f.isDirectory() && !f.getName().startsWith(".")) {
                            list.add(f.getName());
                        }
                    }
                }
            }
        } catch (Throwable t) {
            Log.w(TAG, "listProjects error: " + t.getMessage());
        }
        Collections.sort(list, String.CASE_INSENSITIVE_ORDER);
        return list;
    }

    public static String listProjectsJson(Context context) {
        JSONArray arr = new JSONArray();
        for (String p : listProjects(context)) {
            arr.put(p);
        }
        return arr.toString();
    }

    public static String listConversationsJson(Context context) {
        JSONArray arr = new JSONArray();
        try {
            File geminiDir = getGeminiDir(context);
            Map<String, String> titles = new LinkedHashMap<String, String>();
            File dbFile = new File(geminiDir, "conversation_summaries.db");
            if (dbFile.exists()) {
                SQLiteDatabase db = null;
                Cursor cursor = null;
                try {
                    db = SQLiteDatabase.openDatabase(dbFile.getAbsolutePath(), null, SQLiteDatabase.OPEN_READONLY);
                    cursor = db.rawQuery("SELECT conversation_id, title FROM conversation_summaries ORDER BY last_modified_time DESC", null);
                    if (cursor != null && cursor.moveToFirst()) {
                        do {
                            String cid = cursor.getString(0);
                            String title = cursor.getString(1);
                            if (cid != null && !cid.isEmpty()) {
                                titles.put(cid, (title != null && !title.trim().isEmpty()) ? title : "Untitled Conversation");
                            }
                        } while (cursor.moveToNext());
                    }
                } catch (Throwable t) {
                    Log.w(TAG, "listConversations db error: " + t.getMessage());
                } finally {
                    if (cursor != null) { try { cursor.close(); } catch (Throwable ignored) {} }
                    if (db != null) { try { db.close(); } catch (Throwable ignored) {} }
                }
            }

            File brainDir = new File(geminiDir, "brain");
            if (brainDir.exists() && brainDir.isDirectory()) {
                File[] dirs = brainDir.listFiles();
                if (dirs != null) {
                    for (File d : dirs) {
                        if (d.isDirectory() && !d.getName().startsWith(".")) {
                            String cid = d.getName();
                            if (!titles.containsKey(cid)) {
                                titles.put(cid, "Untitled (" + (cid.length() > 8 ? cid.substring(0, 8) : cid) + ")");
                            }
                        }
                    }
                }
            }

            for (Map.Entry<String, String> entry : titles.entrySet()) {
                JSONObject item = new JSONObject();
                item.put("id", entry.getKey());
                item.put("title", entry.getValue());
                arr.put(item);
            }
        } catch (Throwable t) {
            Log.w(TAG, "listConversationsJson error: " + t.getMessage());
        }
        return arr.toString();
    }

    public static JSONObject backupConversations(Context context, Uri destinationUri) {
        return backupConversations(context, null, destinationUri);
    }

    public static JSONObject backupConversations(Context context, String conversationScope, Uri destinationUri) {
        JSONObject res = new JSONObject();
        ZipOutputStream zos = null;
        OutputStream os = null;
        int count = 0;
        File tempSummaryDb = null;

        try {
            File geminiDir = getGeminiDir(context);
            if (!geminiDir.exists()) {
                res.put("success", false);
                res.put("error", "Antigravity application directory not found");
                return res;
            }

            os = context.getContentResolver().openOutputStream(destinationUri);
            if (os == null) {
                res.put("success", false);
                res.put("error", "Unable to open destination output stream");
                return res;
            }

            zos = new ZipOutputStream(new BufferedOutputStream(os, BUFFER_SIZE));
            zos.setLevel(Deflater.BEST_COMPRESSION);

            boolean isSpecific = conversationScope != null && !conversationScope.trim().isEmpty() && !"all".equalsIgnoreCase(conversationScope.trim());
            String targetId = isSpecific ? conversationScope.trim() : null;

            if (isSpecific) {
                // 1. Specific conversation database files
                File convDir = new File(geminiDir, "conversations");
                if (convDir.exists() && convDir.isDirectory()) {
                    String[] extensions = new String[]{"", "-wal", "-shm"};
                    for (String ext : extensions) {
                        File dbFile = new File(convDir, targetId + ".db" + ext);
                        if (dbFile.exists() && dbFile.isFile()) {
                            addFileToZip(zos, dbFile, "conversations/" + dbFile.getName());
                            count++;
                        }
                    }
                }

                // 2. Specific conversation brain directory
                File brainSubDir = new File(geminiDir, "brain/" + targetId);
                if (brainSubDir.exists() && brainSubDir.isDirectory()) {
                    int added = addDirToZip(zos, brainSubDir, "brain/" + targetId, geminiDir);
                    count += added;
                }

                // 3. Export specific summary row into a standalone conversation_summaries.db inside zip
                File existingDb = new File(geminiDir, "conversation_summaries.db");
                if (existingDb.exists() && existingDb.length() > 0) {
                    tempSummaryDb = new File(geminiDir, "temp_export_summary_" + System.currentTimeMillis() + ".db");
                    SQLiteDatabase srcDb = null;
                    SQLiteDatabase dstDb = null;
                    Cursor cur = null;
                    try {
                        srcDb = SQLiteDatabase.openDatabase(existingDb.getAbsolutePath(), null, SQLiteDatabase.OPEN_READONLY);
                        dstDb = SQLiteDatabase.openOrCreateDatabase(tempSummaryDb, null);
                        cur = srcDb.rawQuery("SELECT sql FROM sqlite_master WHERE type='table' AND name='conversation_summaries'", null);
                        if (cur != null && cur.moveToFirst()) {
                            String createSql = cur.getString(0);
                            dstDb.execSQL(createSql);
                            srcDb.execSQL("ATTACH DATABASE ? AS export_db", new String[]{tempSummaryDb.getAbsolutePath()});
                            srcDb.execSQL("INSERT INTO export_db.conversation_summaries SELECT * FROM conversation_summaries WHERE conversation_id = ?", new String[]{targetId});
                            srcDb.execSQL("DETACH DATABASE export_db");
                        }
                        dstDb.close();
                        dstDb = null;
                        if (tempSummaryDb.exists() && tempSummaryDb.length() > 0) {
                            addFileToZip(zos, tempSummaryDb, "conversation_summaries.db");
                            count++;
                        }
                    } catch (Throwable t) {
                        Log.w(TAG, "Single conversation summary export: " + t.getMessage());
                    } finally {
                        if (cur != null) { try { cur.close(); } catch (Throwable ignored) {} }
                        if (dstDb != null) { try { dstDb.close(); } catch (Throwable ignored) {} }
                        if (srcDb != null) { try { srcDb.close(); } catch (Throwable ignored) {} }
                    }
                }
            } else {
                // 1. All conversation_summaries database files
                String[] dbNames = new String[]{
                        "conversation_summaries.db",
                        "conversation_summaries.db-wal",
                        "conversation_summaries.db-shm",
                        "agyhub_summaries_proto.pb"
                };
                for (String dbName : dbNames) {
                    File f = new File(geminiDir, dbName);
                    if (f.exists() && f.isFile()) {
                        addFileToZip(zos, f, dbName);
                        count++;
                    }
                }

                // 2. All conversations directory (*.db files)
                File convDir = new File(geminiDir, "conversations");
                if (convDir.exists() && convDir.isDirectory()) {
                    int added = addDirToZip(zos, convDir, "conversations", geminiDir);
                    count += added;
                }

                // 3. All brain directory (conversation trajectories & artifacts)
                File brainDir = new File(geminiDir, "brain");
                if (brainDir.exists() && brainDir.isDirectory()) {
                    int added = addDirToZip(zos, brainDir, "brain", geminiDir);
                    count += added;
                }
            }

            zos.finish();
            zos.flush();

            res.put("success", true);
            res.put("count", count);
            res.put("message", "Backed up " + count + " conversation files successfully.");
        } catch (Throwable t) {
            Log.e(TAG, "backupConversations failed", t);
            try {
                res.put("success", false);
                res.put("error", t.getMessage() != null ? t.getMessage() : t.toString());
            } catch (Throwable ignored) {}
        } finally {
            IoUtil.closeQuietly(zos);
            IoUtil.closeQuietly(os);
        }
        return res;
    }

    public static JSONObject restoreConversations(Context context, Uri sourceUri) {
        JSONObject res = new JSONObject();
        ZipInputStream zis = null;
        InputStream is = null;
        int restoredCount = 0;
        File tempDb = null;

        try {
            File geminiDir = getGeminiDir(context);
            geminiDir.mkdirs();
            String canonicalRoot = geminiDir.getCanonicalPath();

            is = context.getContentResolver().openInputStream(sourceUri);
            if (is == null) {
                res.put("success", false);
                res.put("error", "Unable to open backup file input stream");
                return res;
            }

            zis = new ZipInputStream(new BufferedInputStream(is, BUFFER_SIZE));
            ZipEntry entry;
            byte[] buf = new byte[BUFFER_SIZE];

            File existingDb = new File(geminiDir, "conversation_summaries.db");
            tempDb = new File(geminiDir, "temp_restored_summaries_" + System.currentTimeMillis() + ".db");

            while ((entry = zis.getNextEntry()) != null) {
                String entryName = entry.getName().replace('\\', '/');
                if (entryName.startsWith("/") || entryName.contains("..")) {
                    zis.closeEntry();
                    continue;
                }

                if (entry.isDirectory()) {
                    File d = new File(geminiDir, entryName);
                    if (d.getCanonicalPath().startsWith(canonicalRoot)) {
                        d.mkdirs();
                    }
                    zis.closeEntry();
                    continue;
                }

                File outFile;
                if ("conversation_summaries.db".equals(entryName)) {
                    outFile = tempDb;
                } else {
                    outFile = new File(geminiDir, entryName);
                }

                if (!outFile.getCanonicalPath().startsWith(canonicalRoot)) {
                    zis.closeEntry();
                    continue;
                }

                File parent = outFile.getParentFile();
                if (parent != null && !parent.exists()) {
                    parent.mkdirs();
                }

                FileOutputStream fos = null;
                try {
                    fos = new FileOutputStream(outFile);
                    int read;
                    while ((read = zis.read(buf)) > 0) {
                        fos.write(buf, 0, read);
                    }
                    fos.flush();
                    restoredCount++;
                } finally {
                    IoUtil.closeQuietly(fos);
                }
                zis.closeEntry();
            }

            // Merge conversation_summaries SQLite DB if tempDb was restored
            if (tempDb.exists() && tempDb.length() > 0) {
                if (existingDb.exists() && existingDb.length() > 0) {
                    mergeSummariesDatabase(existingDb, tempDb);
                } else {
                    if (existingDb.exists()) {
                        existingDb.delete();
                    }
                    if (!tempDb.renameTo(existingDb)) {
                        copyFile(tempDb, existingDb);
                    }
                }
            }

            res.put("success", true);
            res.put("count", restoredCount);
            res.put("message", "Successfully restored " + restoredCount + " conversation files.");
        } catch (Throwable t) {
            Log.e(TAG, "restoreConversations failed", t);
            try {
                res.put("success", false);
                res.put("error", t.getMessage() != null ? t.getMessage() : t.toString());
            } catch (Throwable ignored) {}
        } finally {
            IoUtil.closeQuietly(zis);
            IoUtil.closeQuietly(is);
            if (tempDb != null && tempDb.exists()) {
                tempDb.delete();
            }
        }
        return res;
    }

    public static JSONObject backupProjects(Context context, String projectName, Uri destinationUri) {
        JSONObject res = new JSONObject();
        ZipOutputStream zos = null;
        OutputStream os = null;
        int count = 0;

        try {
            File geminiDir = getGeminiDir(context);
            File scratchDir = new File(geminiDir, "scratch");
            File targetDir;

            if (projectName != null && !projectName.trim().isEmpty() && !"all".equalsIgnoreCase(projectName.trim())) {
                targetDir = new File(scratchDir, projectName.trim());
                if (!targetDir.exists()) {
                    targetDir = new File(projectName.trim());
                }
            } else {
                targetDir = scratchDir;
            }

            if (!targetDir.exists()) {
                res.put("success", false);
                res.put("error", "Target project directory does not exist: " + targetDir.getAbsolutePath());
                return res;
            }

            os = context.getContentResolver().openOutputStream(destinationUri);
            if (os == null) {
                res.put("success", false);
                res.put("error", "Unable to open destination output stream");
                return res;
            }

            zos = new ZipOutputStream(new BufferedOutputStream(os, BUFFER_SIZE));
            zos.setLevel(Deflater.BEST_COMPRESSION);

            String baseName = targetDir.getName();
            count = addDirToZip(zos, targetDir, baseName, targetDir.getParentFile() != null ? targetDir.getParentFile() : targetDir);

            zos.finish();
            zos.flush();

            res.put("success", true);
            res.put("count", count);
            res.put("message", "Backed up " + count + " project files successfully.");
        } catch (Throwable t) {
            Log.e(TAG, "backupProjects failed", t);
            try {
                res.put("success", false);
                res.put("error", t.getMessage() != null ? t.getMessage() : t.toString());
            } catch (Throwable ignored) {}
        } finally {
            IoUtil.closeQuietly(zos);
            IoUtil.closeQuietly(os);
        }
        return res;
    }

    public static JSONObject restoreProjects(Context context, String targetName, Uri sourceUri) {
        JSONObject res = new JSONObject();
        ZipInputStream zis = null;
        InputStream is = null;
        int restoredCount = 0;

        try {
            File geminiDir = getGeminiDir(context);
            File scratchDir = new File(geminiDir, "scratch");
            File targetDir;

            if (targetName != null && !targetName.trim().isEmpty() && !"all".equalsIgnoreCase(targetName.trim())) {
                targetDir = new File(scratchDir, targetName.trim());
            } else {
                targetDir = scratchDir;
            }
            targetDir.mkdirs();
            String canonicalRoot = targetDir.getCanonicalPath();

            is = context.getContentResolver().openInputStream(sourceUri);
            if (is == null) {
                res.put("success", false);
                res.put("error", "Unable to open projects backup archive");
                return res;
            }

            zis = new ZipInputStream(new BufferedInputStream(is, BUFFER_SIZE));
            ZipEntry entry;
            byte[] buf = new byte[BUFFER_SIZE];

            while ((entry = zis.getNextEntry()) != null) {
                String entryName = entry.getName().replace('\\', '/');
                if (entryName.startsWith("/") || entryName.contains("..")) {
                    zis.closeEntry();
                    continue;
                }

                File outFile = new File(targetDir, entryName);
                if (!outFile.getCanonicalPath().startsWith(canonicalRoot)) {
                    zis.closeEntry();
                    continue;
                }

                if (entry.isDirectory()) {
                    outFile.mkdirs();
                    zis.closeEntry();
                    continue;
                }

                File parent = outFile.getParentFile();
                if (parent != null && !parent.exists()) {
                    parent.mkdirs();
                }

                FileOutputStream fos = null;
                try {
                    fos = new FileOutputStream(outFile);
                    int read;
                    while ((read = zis.read(buf)) > 0) {
                        fos.write(buf, 0, read);
                    }
                    fos.flush();
                    restoredCount++;
                } finally {
                    IoUtil.closeQuietly(fos);
                }
                zis.closeEntry();
            }

            res.put("success", true);
            res.put("count", restoredCount);
            res.put("message", "Successfully restored " + restoredCount + " project files into " + targetDir.getName() + ".");
        } catch (Throwable t) {
            Log.e(TAG, "restoreProjects failed", t);
            try {
                res.put("success", false);
                res.put("error", t.getMessage() != null ? t.getMessage() : t.toString());
            } catch (Throwable ignored) {}
        } finally {
            IoUtil.closeQuietly(zis);
            IoUtil.closeQuietly(is);
        }
        return res;
    }

    private static void addFileToZip(ZipOutputStream zos, File file, String entryPath) throws IOException {
        ZipEntry entry = new ZipEntry(entryPath.replace('\\', '/'));
        entry.setTime(file.lastModified());
        zos.putNextEntry(entry);
        FileInputStream fis = null;
        try {
            fis = new FileInputStream(file);
            byte[] buf = new byte[BUFFER_SIZE];
            int read;
            while ((read = fis.read(buf)) > 0) {
                zos.write(buf, 0, read);
            }
        } finally {
            IoUtil.closeQuietly(fis);
            zos.closeEntry();
        }
    }

    private static int addDirToZip(ZipOutputStream zos, File dir, String relPrefix, File baseDir) throws IOException {
        int count = 0;
        File[] files = dir.listFiles();
        if (files == null) return count;

        for (File f : files) {
            if (f.isDirectory()) {
                String subPrefix = relPrefix.isEmpty() ? f.getName() : relPrefix + "/" + f.getName();
                count += addDirToZip(zos, f, subPrefix, baseDir);
            } else if (f.isFile()) {
                String entryPath = relPrefix.isEmpty() ? f.getName() : relPrefix + "/" + f.getName();
                addFileToZip(zos, f, entryPath);
                count++;
            }
        }
        return count;
    }

    private static void mergeSummariesDatabase(File targetDb, File sourceDb) {
        SQLiteDatabase main = null;
        try {
            main = SQLiteDatabase.openDatabase(targetDb.getAbsolutePath(), null, SQLiteDatabase.OPEN_READWRITE);
            main.execSQL("ATTACH DATABASE ? AS restored", new String[]{sourceDb.getAbsolutePath()});
            main.execSQL("INSERT OR REPLACE INTO conversation_summaries SELECT * FROM restored.conversation_summaries");
            main.execSQL("DETACH DATABASE restored");
        } catch (Throwable t) {
            Log.w(TAG, "Database merge attach failed, attempting direct table insert fallback: " + t.getMessage());
            copyFile(sourceDb, targetDb);
        } finally {
            if (main != null) {
                try {
                    main.close();
                } catch (Throwable ignored) {}
            }
        }
    }

    private static void copyFile(File src, File dst) {
        FileInputStream fis = null;
        FileOutputStream fos = null;
        try {
            fis = new FileInputStream(src);
            fos = new FileOutputStream(dst);
            byte[] buf = new byte[BUFFER_SIZE];
            int len;
            while ((len = fis.read(buf)) > 0) {
                fos.write(buf, 0, len);
            }
            fos.flush();
        } catch (Throwable t) {
            Log.e(TAG, "copyFile failed", t);
        } finally {
            IoUtil.closeQuietly(fis);
            IoUtil.closeQuietly(fos);
        }
    }
}
