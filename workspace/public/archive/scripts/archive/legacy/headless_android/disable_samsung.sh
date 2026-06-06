#!/system/bin/sh
# ====================================================================
# Stage 2: Samsung 서비스 제거
# ====================================================================
# 목적: Samsung 전용 서비스 및 앱 제거
# RAM 절감 예상: ~400MB
# 위험도: 낮음 (복구 가능)
# ====================================================================

LOGFILE="/data/local/tmp/headless_stage2.log"

# ====================================================================
# 로그 초기화
# ====================================================================

echo "=========================================" > "$LOGFILE"
echo "Stage 2: Samsung Services Removal" >> "$LOGFILE"
echo "=========================================" >> "$LOGFILE"
echo "" >> "$LOGFILE"
echo "Started: $(date)" >> "$LOGFILE"
echo "" >> "$LOGFILE"

# ====================================================================
# Samsung 서비스 목록
# ====================================================================

PACKAGES="
com.osp.app.signin
com.samsung.android.bixby.agent
com.samsung.android.bixby.service
com.samsung.android.bixby.wakeup
com.samsung.android.smartcallprovider
com.samsung.android.sm.devicesecurity
com.sec.android.easyMover.Agent
com.samsung.android.kgclient
com.samsung.android.knox.analytics.uploader
com.samsung.android.scloud
com.samsung.android.samsungpass
com.samsung.android.spay
com.samsung.android.game.gamehome
com.samsung.android.game.gametools
com.samsung.android.themecenter
com.samsung.android.themestore
"

# ====================================================================
# 패키지 비활성화
# ====================================================================

echo "Disabling Samsung services..." | tee -a "$LOGFILE"
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
echo "Stage 2 Completed" >> "$LOGFILE"
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
echo "2. Test SSH and WiFi:" >> "$LOGFILE"
echo "   ssh root@192.168.0.12" >> "$LOGFILE"
echo "" >> "$LOGFILE"
echo "3. Check RAM usage:" >> "$LOGFILE"
echo "   adb shell free -h" >> "$LOGFILE"
echo "   Expected: ~1.5GB (down from 1.9GB)" >> "$LOGFILE"
echo "" >> "$LOGFILE"

# ====================================================================
# 화면 출력
# ====================================================================

echo ""
echo "========================================="
echo "Stage 2 Samsung Services Removal Completed"
echo "========================================="
echo ""
echo "Success: $SUCCESS_COUNT packages"
echo "Failed: $FAIL_COUNT packages"
echo ""
echo "Full log: $LOGFILE"
echo ""
echo "Ready to reboot? Run: adb reboot"
echo ""
