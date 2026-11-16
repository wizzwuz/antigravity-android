#!/usr/bin/env bash
#
# 09-sign.sh - zipalign and sign the APK (v2 + v3) with the configured keystore.

log "[9/9] zipalign + sign"

if [ ! -f "$KEYSTORE" ]; then
    if [ "$KEY_ALIAS" = "androiddebugkey" ]; then
        log "[sign] release keystore not configured; generating local dev keystore at $KEYSTORE"
        mkdir -p "$(dirname "$KEYSTORE")"
        keytool -genkeypair \
            -keystore "$KEYSTORE" \
            -storetype PKCS12 \
            -alias "$KEY_ALIAS" \
            -keyalg RSA \
            -keysize 2048 \
            -validity 10000 \
            -storepass "$STORE_PASS" \
            -keypass "$KEY_PASS" \
            -dname "CN=Local Dev Build, O=Antigravity" >/dev/null 2>&1
    else
        die "configured release keystore not found: $KEYSTORE"
    fi
fi

zipalign -f -p 4 "$BUILD_DIR/unaligned.apk" "$BUILD_DIR/aligned.apk"
apksigner sign \
    --v1-signing-enabled false \
    --v2-signing-enabled true \
    --v3-signing-enabled true \
    --ks "$KEYSTORE" \
    --ks-key-alias "$KEY_ALIAS" \
    --ks-pass "pass:$STORE_PASS" \
    --key-pass "pass:$KEY_PASS" \
    --out "$OUT_APK" \
    "$BUILD_DIR/aligned.apk"

if [ "${REGION_BYPASS:-0}" -eq 1 ]; then
    ( cd "$DIST_DIR" && cp -f "antigravity-region-bypass.apk" "antigravity-bypass.apk" 2>/dev/null || true )
fi
