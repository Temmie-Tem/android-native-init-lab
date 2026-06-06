#!/system/bin/sh
# ====================================================================
# Stage 1: GUI 제거
# ====================================================================
# 목적: Android SystemUI, Launcher, 키보드 제거
# RAM 절감 예상: ~600MB
# 위험도: 낮음 (복구 가능)
# ====================================================================

LOGFILE="/data/local/tmp/headless_stage1.log"

# ====================================================================
# 로그 초기화
# ====================================================================

echo "=========================================" > "$LOGFILE"
echo "Stage 1: GUI Removal" >> "$LOGFILE"
echo "=========================================" >> "$LOGFILE"
echo "" >> "$LOGFILE"
echo "Started: $(date)" >> "$LOGFILE"
echo "" >> "$LOGFILE"

# ====================================================================
# GUI 컴포넌트 목록
# ====================================================================

# SystemUI - Android 상태바, 알림, 퀵 설정
# Launcher - 홈 화면 런처
# Keyboards - 소프트웨어 키보드 (불필요)

PACKAGES="
com.android.systemui
com.sec.android.app.launcher
com.samsung.android.honeyboard
com.google.android.inputmethod.latin
"

# ====================================================================
# 패키지 비활성화
# ====================================================================

echo "Disabling GUI packages..." | tee -a "$LOGFILE"
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
echo "Stage 1 Completed" >> "$LOGFILE"
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
echo "2. Wait for boot (screen will be black - NORMAL!)" >> "$LOGFILE"
echo "   adb wait-for-device" >> "$LOGFILE"
echo "   sleep 10" >> "$LOGFILE"
echo "" >> "$LOGFILE"
echo "3. Test SSH connection:" >> "$LOGFILE"
echo "   ssh root@192.168.0.12" >> "$LOGFILE"
echo "" >> "$LOGFILE"
echo "4. Check RAM usage:" >> "$LOGFILE"
echo "   adb shell free -h" >> "$LOGFILE"
echo "   Expected: ~1.9GB (down from 2.5GB)" >> "$LOGFILE"
echo "" >> "$LOGFILE"
echo "5. If problem occurs, restore GUI:" >> "$LOGFILE"
echo "   adb shell pm enable com.android.systemui" >> "$LOGFILE"
echo "   adb shell pm enable com.sec.android.app.launcher" >> "$LOGFILE"
echo "   adb reboot" >> "$LOGFILE"
echo "" >> "$LOGFILE"

# ====================================================================
# 화면 출력
# ====================================================================

echo ""
echo "========================================="
echo "Stage 1 GUI Removal Completed"
echo "========================================="
echo ""
echo "Success: $SUCCESS_COUNT packages"
echo "Failed: $FAIL_COUNT packages"
echo ""
echo "Full log: $LOGFILE"
echo ""
echo "⚠️  IMPORTANT:"
echo "- Screen will be BLACK after reboot (NORMAL!)"
echo "- Access via SSH only: ssh root@192.168.0.12"
echo "- To restore: adb shell pm enable com.android.systemui"
echo ""
echo "Ready to reboot? Run: adb reboot"
echo ""
