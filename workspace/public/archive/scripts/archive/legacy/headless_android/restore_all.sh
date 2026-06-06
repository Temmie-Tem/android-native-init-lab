#!/system/bin/sh
# ====================================================================
# 전체 복구 스크립트
# ====================================================================
# 목적: 모든 비활성화된 패키지를 다시 활성화
# 사용 시기: 문제 발생 시 전체 롤백
# ====================================================================

LOGFILE="/data/local/tmp/headless_restore.log"

# ====================================================================
# 로그 초기화
# ====================================================================

echo "=========================================" > "$LOGFILE"
echo "Headless Android - Full Restore" >> "$LOGFILE"
echo "=========================================" >> "$LOGFILE"
echo "" >> "$LOGFILE"
echo "Started: $(date)" >> "$LOGFILE"
echo "" >> "$LOGFILE"

# ====================================================================
# 모든 비활성화된 패키지 목록
# ====================================================================

PACKAGES="
com.android.systemui
com.sec.android.app.launcher
com.samsung.android.honeyboard
com.google.android.inputmethod.latin
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
# 패키지 재활성화
# ====================================================================

echo "Re-enabling all packages..." | tee -a "$LOGFILE"
echo "" >> "$LOGFILE"

SUCCESS_COUNT=0
FAIL_COUNT=0

for pkg in $PACKAGES; do
    echo "Processing: $pkg" | tee -a "$LOGFILE"

    # 재활성화 시도
    pm enable "$pkg" >> "$LOGFILE" 2>&1

    if [ $? -eq 0 ]; then
        echo "  ✓ Enabled" | tee -a "$LOGFILE"
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
    else
        echo "  ✗ Failed (maybe not installed)" | tee -a "$LOGFILE"
        FAIL_COUNT=$((FAIL_COUNT + 1))
    fi

    echo "" >> "$LOGFILE"
done

# ====================================================================
# 결과 요약
# ====================================================================

echo "" >> "$LOGFILE"
echo "=========================================" >> "$LOGFILE"
echo "Restore Completed" >> "$LOGFILE"
echo "=========================================" >> "$LOGFILE"
echo "" >> "$LOGFILE"
echo "Finished: $(date)" >> "$LOGFILE"
echo "Enabled: $SUCCESS_COUNT packages" >> "$LOGFILE"
echo "Failed: $FAIL_COUNT packages" >> "$LOGFILE"
echo "" >> "$LOGFILE"

# ====================================================================
# 다음 단계 안내
# ====================================================================

echo "Next Steps:" >> "$LOGFILE"
echo "1. Reboot device to apply changes:" >> "$LOGFILE"
echo "   adb reboot" >> "$LOGFILE"
echo "" >> "$LOGFILE"
echo "2. GUI should be restored after reboot" >> "$LOGFILE"
echo "" >> "$LOGFILE"

# ====================================================================
# 화면 출력
# ====================================================================

echo ""
echo "========================================="
echo "Full Restore Completed"
echo "========================================="
echo ""
echo "Enabled: $SUCCESS_COUNT packages"
echo "Failed: $FAIL_COUNT packages"
echo ""
echo "Full log: $LOGFILE"
echo ""
echo "⚠️  IMPORTANT: Reboot required to apply changes"
echo "Run: adb reboot"
echo ""
echo "After reboot:"
echo "- Android GUI will be restored"
echo "- All services will start normally"
echo "- RAM usage will return to ~2.5GB"
echo ""
