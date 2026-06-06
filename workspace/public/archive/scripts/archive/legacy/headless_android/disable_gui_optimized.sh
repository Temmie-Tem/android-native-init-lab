#!/system/bin/sh
# ====================================================================
# Stage 1: GUI 제거 (최적화 버전)
# ====================================================================
# 목적: 실제 설치된 GUI 컴포넌트만 제거
# 패키지 스캔 결과 기반 (2025-11-15)
# RAM 절감 예상: ~600MB
# ====================================================================

LOGFILE="/data/local/tmp/headless_stage1.log"

echo "=========================================" > "$LOGFILE"
echo "Stage 1: GUI Removal (Optimized)" >> "$LOGFILE"
echo "=========================================" >> "$LOGFILE"
echo "" >> "$LOGFILE"
echo "Started: $(date)" >> "$LOGFILE"
echo "" >> "$LOGFILE"

# ====================================================================
# 실제 설치된 GUI 패키지만 나열
# ====================================================================

# SystemUI (18 packages detected)
PACKAGES_SYSTEMUI="
com.android.systemui
com.samsung.desktopsystemui
com.samsung.systemui.bixby2
com.android.internal.systemui.navbar.gestural
com.android.internal.systemui.navbar.gestural_extra_wide_back
com.android.internal.systemui.navbar.gestural_narrow_back
com.android.internal.systemui.navbar.gestural_wide_back
com.android.internal.systemui.navbar.threebutton
com.android.internal.systemui.onehanded.gestural
com.samsung.internal.systemui.navbar.gestural_no_hint
com.samsung.internal.systemui.navbar.gestural_no_hint_extra_wide_back
com.samsung.internal.systemui.navbar.gestural_no_hint_narrow_back
com.samsung.internal.systemui.navbar.gestural_no_hint_wide_back
com.samsung.internal.systemui.navbar.sec_gestural
com.samsung.internal.systemui.navbar.sec_gestural_no_hint
"

# Theme Icon Packs for SystemUI (can be disabled)
PACKAGES_THEME_SYSTEMUI="
com.android.theme.icon_pack.circular.systemui
com.android.theme.icon_pack.filled.systemui
com.android.theme.icon_pack.rounded.systemui
"

# Launchers (7 packages detected)
PACKAGES_LAUNCHER="
com.sec.android.app.launcher
com.sec.android.app.desktoplauncher
com.sec.android.emergencylauncher
"

# Theme Icon Packs for Launcher (can be disabled)
PACKAGES_THEME_LAUNCHER="
com.android.theme.icon_pack.circular.launcher
com.android.theme.icon_pack.filled.launcher
com.android.theme.icon_pack.rounded.launcher
"

# Keyboards (1 package detected)
PACKAGES_KEYBOARD="
com.samsung.android.honeyboard
"

# ====================================================================
# 비활성화 함수
# ====================================================================

disable_packages() {
    CATEGORY_NAME="$1"
    shift
    PACKAGES="$@"

    echo "----------------------------------------" >> "$LOGFILE"
    echo "$CATEGORY_NAME" | tee -a "$LOGFILE"
    echo "----------------------------------------" >> "$LOGFILE"

    SUCCESS=0
    FAIL=0
    SKIP=0

    for pkg in $PACKAGES; do
        echo "Processing: $pkg" | tee -a "$LOGFILE"

        # 패키지 존재 확인
        if ! pm list packages | grep -q "^package:$pkg$"; then
            echo "  - Not installed (skipped)" >> "$LOGFILE"
            SKIP=$((SKIP + 1))
            continue
        fi

        # 비활성화 시도
        pm disable-user --user 0 "$pkg" >> "$LOGFILE" 2>&1

        if [ $? -eq 0 ]; then
            echo "  ✓ Successfully disabled" | tee -a "$LOGFILE"
            SUCCESS=$((SUCCESS + 1))
        else
            echo "  ✗ Failed to disable" | tee -a "$LOGFILE"
            FAIL=$((FAIL + 1))
        fi
    done

    echo "" >> "$LOGFILE"
    echo "Success: $SUCCESS, Failed: $FAIL, Skipped: $SKIP" | tee -a "$LOGFILE"
    echo "" >> "$LOGFILE"

    return $SUCCESS
}

# ====================================================================
# 단계별 비활성화
# ====================================================================

TOTAL_SUCCESS=0

# 1. SystemUI 제거
disable_packages "SystemUI Core" $PACKAGES_SYSTEMUI
TOTAL_SUCCESS=$((TOTAL_SUCCESS + $?))

disable_packages "SystemUI Theme Icons" $PACKAGES_THEME_SYSTEMUI
TOTAL_SUCCESS=$((TOTAL_SUCCESS + $?))

# 2. Launcher 제거
disable_packages "Launcher Core" $PACKAGES_LAUNCHER
TOTAL_SUCCESS=$((TOTAL_SUCCESS + $?))

disable_packages "Launcher Theme Icons" $PACKAGES_THEME_LAUNCHER
TOTAL_SUCCESS=$((TOTAL_SUCCESS + $?))

# 3. Keyboard 제거
disable_packages "Keyboard" $PACKAGES_KEYBOARD
TOTAL_SUCCESS=$((TOTAL_SUCCESS + $?))

# ====================================================================
# 결과 요약
# ====================================================================

echo "" >> "$LOGFILE"
echo "=========================================" >> "$LOGFILE"
echo "Stage 1 Completed" >> "$LOGFILE"
echo "=========================================" >> "$LOGFILE"
echo "" >> "$LOGFILE"
echo "Finished: $(date)" >> "$LOGFILE"
echo "Total packages disabled: $TOTAL_SUCCESS" >> "$LOGFILE"
echo "" >> "$LOGFILE"

# ====================================================================
# 다음 단계 안내
# ====================================================================

echo "Next Steps:" >> "$LOGFILE"
echo "1. Reboot device:" >> "$LOGFILE"
echo "   adb reboot" >> "$LOGFILE"
echo "" >> "$LOGFILE"
echo "2. Wait for boot (screen will be BLACK - NORMAL!)" >> "$LOGFILE"
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
echo "Total packages disabled: $TOTAL_SUCCESS"
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
