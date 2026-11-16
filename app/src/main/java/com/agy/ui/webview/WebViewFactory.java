package com.agy.ui.webview;

import android.content.Context;
import android.os.Build;
import android.view.MotionEvent;
import android.view.View;
import android.webkit.WebView;

import com.agy.bridge.AndroidBridge;
import com.agy.theme.ThemeManager;

/** Creates and hardware-configures the host WebView. */
public final class WebViewFactory {

    private WebViewFactory() {
    }

    public static WebView create(Context context, AndroidBridge bridge, ThemeManager theme) {
        WebView view = new WebView(context);
        view.setBackgroundColor(theme.getBackgroundColor());
        view.setFocusable(true);
        view.setFocusableInTouchMode(true);
        view.requestFocus(View.FOCUS_DOWN);
        // Layer type NONE: hardware acceleration is already enabled at window/manifest level.
        // LAYER_TYPE_HARDWARE forces offscreen texture compositing on every frame, causing sluggishness.
        view.setLayerType(View.LAYER_TYPE_NONE, null);
        view.addJavascriptInterface(bridge, bridge.getNativeBindingName());
        // Android WebView needs an explicit focus grant for the soft keyboard to show.
        view.setOnTouchListener(new View.OnTouchListener() {
            @Override
            public boolean onTouch(View v, MotionEvent event) {
                if (event.getAction() == MotionEvent.ACTION_DOWN) {
                    ((WebView) v).requestFocus(View.FOCUS_DOWN);
                }
                return false;
            }
        });

        WebSettingsFactory.configure(view);

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.KITKAT) {
            boolean isDevBuild = context != null && "com.agy.dev".equals(context.getPackageName());
            WebView.setWebContentsDebuggingEnabled(isDevBuild);
        }
        return view;
    }
}
