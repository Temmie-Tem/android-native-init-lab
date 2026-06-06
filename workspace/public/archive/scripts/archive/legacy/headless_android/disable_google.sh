#!/system/bin/sh
# ====================================================================
# Stage 3: Google 서비스 제거
# ====================================================================
# 목적: Google Play Services 및 관련 앱 제거
# RAM 절감 예상: ~300MB
# 위험도: 중간 (WiFi 인증 문제 발생 가능)
# ====================================================================

LOGFILE="/data/local/tmp/headless_stage3.log"

# ====================================================================
# 로그 초기화
# ====================================================================

echo "=========================================" > "$LOGFILE"
echo "Stage 3: Google Services Removal" >> "$LOGFILE"
echo "=========================================" >> "$LOGFILE"
echo "" >> "$LOGFILE"
echo "⚠️  WARNING: This may affect WiFi authentication!" >> "$LOGFILE"
echo "Make sure you can recover via ADB if needed." >> "$LOGFILE"
echo "" >> "$LOGFILE"
echo "Started: $(date)" >> "$LOGFILE"
echo "" >> "$LOGFILE"

# ====================================================================
# Google 서비스 목록
# ====================================================================

PACKAGES="
com.google.android.gms
com.android.vending
com.google.android.gsf
com.google.android.apps.maps
com.google.android.youtube
com.google.android.apps.photos
com.google.android.videos
com.google.android.music
com.google.android.apps.docs
com.google.android.calendar
com.google.android.contacts
com.google.android.apps.messaging
"

# ====================================================================
# 패키지 비활성화
# ====================================================================

echo "Disabling Google services..." | tee -a "$LOGFILE"
echo "" >> "$LOGFILE"

SUCCESS_COUNT=0
FAIL_COUNT=0

for pkg in $PACKAGES; do
    echo "Processing: $pkg" | tee -a "$LOGFILE"

    # 패키지 존재 확인
    if pm list packages | grep -q "^package:$pkg$"; then
        # 비활성화 시도
        pm disable-user --user 0 "$pkg" >> "$LOGFILE" 2>&1

        if [ $? -eq 0 ]; then
            echo "  ✓ Successfully disabled" | tee -a "$LOGFILE"
            SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
        else
            echo "  ✗ Failed to disable" | tee -a "$LOGFILE"
            FAIL_COUNT=$((FAIL_COUNT + 1))
        fi
    else
        echo "  - Not installed (skipped)" | tee -a "$LOGFILE"
    fi

    echo "" >> "$LOGFILE"
done

# ====================================================================
# 결과 요약
# ====================================================================

echo "" >> "$LOGFILE"
echo "=========================================" >> "$LOGFILE"
echo "Stage 3 Completed" >> "$LOGFILE"
echo "=========================================" >> "$LOGFILE"
echo "" >> "$LOGFILE"
echo "Finished: $(date)" >> "$LOGFILE"
echo "Success: $SUCCESS_COUNT packages" >> "$LOGFILE"
echo "Failed: $FAIL_COUNT packages" >> "$LOGFILE"
echo "" >> "$LOGFILE"

# ====================================================================
# 다음 단계 안내
# ====================================================================

echo "Next Steps:" >> "$LOGFILE"
echo "1. Reboot device:" >> "$LOGFILE"
echo "   adb reboot" >> "$LOGFILE"
echo "" >> "$LOGFILE"
echo "2. ⚠️  CRITICAL: Test WiFi connection!" >> "$LOGFILE"
echo "   ssh root@192.168.0.12" >> "$LOGFILE"
echo "   ping 8.8.8.8" >> "$LOGFILE"
echo "" >> "$LOGFILE"
echo "3. If WiFi fails, restore GMS:" >> "$LOGFILE"
echo "   adb shell pm enable com.google.android.gms" >> "$LOGFILE"
echo "   adb shell pm enable com.android.vending" >> "$LOGFILE"
echo "   adb reboot" >> "$LOGFILE"
echo "" >> "$LOGFILE"
echo "4. Check RAM usage:" >> "$LOGFILE"
echo "   adb shell free -h" >> "$LOGFILE"
echo "   Expected: ~1.2GB (down from 1.5GB)" >> "$LOGFILE"
echo "" >> "$LOGFILE"

# ====================================================================
# 화면 출력
# ====================================================================

echo ""
echo "========================================="
echo "Stage 3 Google Services Removal Completed"
echo "========================================="
echo ""
echo "Success: $SUCCESS_COUNT packages"
echo "Failed: $FAIL_COUNT packages"
echo ""
echo "⚠️  WARNING: WiFi may stop working!"
echo "Keep ADB connection available for recovery."
echo ""
echo "Full log: $LOGFILE"
echo ""
echo "Ready to reboot? Run: adb reboot"
echo ""
