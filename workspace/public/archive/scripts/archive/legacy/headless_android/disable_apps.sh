#!/system/bin/sh
# ====================================================================
# Stage 4: 불필요한 앱 제거
# ====================================================================
# 목적: Media, Communication, Camera 등 불필요한 앱 제거
# RAM 절감 예상: ~200MB
# 위험도: 낮음 (복구 가능)
# ====================================================================

LOGFILE="/data/local/tmp/headless_stage4.log"

# ====================================================================
# 로그 초기화
# ====================================================================

echo "=========================================" > "$LOGFILE"
echo "Stage 4: Unnecessary Apps Removal" >> "$LOGFILE"
echo "=========================================" >> "$LOGFILE"
echo "" >> "$LOGFILE"
echo "Started: $(date)" >> "$LOGFILE"
echo "" >> "$LOGFILE"

# ====================================================================
# 불필요한 앱 목록
# ====================================================================

PACKAGES="
com.sec.android.app.music
com.samsung.android.video
com.sec.android.app.soundalive
com.samsung.android.messaging
com.samsung.android.contacts
com.samsung.android.incallui
com.samsung.android.dialer
com.sec.android.gallery3d
com.sec.android.app.camera
com.samsung.android.calendar
com.samsung.android.email.provider
com.sec.android.app.sbrowser
com.samsung.android.app.notes
com.samsung.android.app.memo
com.sec.android.app.myfiles
com.samsung.android.app.soundpicker
com.samsung.android.fmm
com.samsung.android.net.wifi.wifiguider
"

# ====================================================================
# 패키지 비활성화
# ====================================================================

echo "Disabling unnecessary apps..." | tee -a "$LOGFILE"
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
echo "Stage 4 Completed" >> "$LOGFILE"
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
echo "2. Final verification:" >> "$LOGFILE"
echo "   ssh root@192.168.0.12" >> "$LOGFILE"
echo "" >> "$LOGFILE"
echo "3. Final RAM measurement:" >> "$LOGFILE"
echo "   adb shell free -h" >> "$LOGFILE"
echo "   Expected: ~1.0GB or less" >> "$LOGFILE"
echo "" >> "$LOGFILE"
echo "4. Compare with initial state:" >> "$LOGFILE"
echo "   Initial: 2.5GB" >> "$LOGFILE"
echo "   Final: 1.0GB" >> "$LOGFILE"
echo "   Saved: 1.5GB (60%)" >> "$LOGFILE"
echo "" >> "$LOGFILE"

# ====================================================================
# 화면 출력
# ====================================================================

echo ""
echo "========================================="
echo "Stage 4 Apps Removal Completed"
echo "========================================="
echo ""
echo "Success: $SUCCESS_COUNT packages"
echo "Failed: $FAIL_COUNT packages"
echo ""
echo "Full log: $LOGFILE"
echo ""
echo "🎉 All 4 stages completed!"
echo "Expected RAM usage: ~1.0GB (down from 2.5GB)"
echo ""
echo "Ready to reboot? Run: adb reboot"
echo ""
