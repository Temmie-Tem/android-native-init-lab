#!/system/bin/sh
# ====================================================================
# Stage 3: Google 서비스 제거 (최적화 버전)
# ====================================================================
# 목적: 실제 설치된 Google 서비스만 제거
# 패키지 스캔 결과 기반 (2025-11-15)
# RAM 절감 예상: ~300MB
# ⚠️  WARNING: WiFi 인증 문제 발생 가능!
# ====================================================================

LOGFILE="/data/local/tmp/headless_stage3.log"

echo "=========================================" > "$LOGFILE"
echo "Stage 3: Google Services Removal (Optimized)" >> "$LOGFILE"
echo "=========================================" >> "$LOGFILE"
echo "" >> "$LOGFILE"
echo "⚠️  WARNING: This may affect WiFi authentication!" >> "$LOGFILE"
echo "Make sure you can recover via ADB if needed." >> "$LOGFILE"
echo "" >> "$LOGFILE"
echo "Started: $(date)" >> "$LOGFILE"
echo "" >> "$LOGFILE"

# ====================================================================
# 실제 설치된 Google 패키지
# ====================================================================

# Google Play Services (4 packages) - ⚠️ 매우 주의!
PACKAGES_GMS="
com.google.android.gms
com.google.android.gms.location.history
com.google.android.gsf
com.android.vending
"

# Google Apps (6 packages detected)
PACKAGES_GOOGLE_APPS="
com.google.android.apps.maps
com.google.android.apps.tachyon
com.google.android.youtube
com.google.android.gm
"

# Google System Apps (제거 가능한 것들)
PACKAGES_GOOGLE_SYSTEM="
com.google.android.apps.restore
com.google.android.apps.turbo
com.google.android.captiveportallogin
com.google.android.configupdater
com.google.android.feedback
com.google.android.onetimeinitializer
com.google.android.partnersetup
com.google.android.printservice.recommendation
com.google.android.setupwizard
com.google.android.syncadapters.calendar
com.google.android.syncadapters.contacts
"

# Google Search & Assistant (제거 가능)
PACKAGES_GOOGLE_SEARCH="
com.google.android.googlequicksearchbox
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

# 먼저 덜 중요한 것들부터 제거
disable_packages "Google Apps (Maps, YouTube, Gmail)" $PACKAGES_GOOGLE_APPS
TOTAL_SUCCESS=$((TOTAL_SUCCESS + $?))

disable_packages "Google Search & Assistant" $PACKAGES_GOOGLE_SEARCH
TOTAL_SUCCESS=$((TOTAL_SUCCESS + $?))

disable_packages "Google System Apps" $PACKAGES_GOOGLE_SYSTEM
TOTAL_SUCCESS=$((TOTAL_SUCCESS + $?))

# ⚠️ 마지막으로 GMS 제거 (WiFi 문제 가능)
echo "⚠️  CRITICAL: Disabling Google Play Services!" | tee -a "$LOGFILE"
echo "This may affect WiFi authentication." | tee -a "$LOGFILE"
echo "" >> "$LOGFILE"

disable_packages "Google Play Services (⚠️ CRITICAL)" $PACKAGES_GMS
TOTAL_SUCCESS=$((TOTAL_SUCCESS + $?))

# ====================================================================
# 결과 요약
# ====================================================================

echo "" >> "$LOGFILE"
echo "=========================================" >> "$LOGFILE"
echo "Stage 3 Completed" >> "$LOGFILE"
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
echo "2. ⚠️  CRITICAL: Test WiFi connection!" >> "$LOGFILE"
echo "   adb wait-for-device" >> "$LOGFILE"
echo "   adb shell ip addr show wlan0 | grep 'inet '" >> "$LOGFILE"
echo "" >> "$LOGFILE"
echo "3. If WiFi is OK, test SSH:" >> "$LOGFILE"
echo "   ssh root@192.168.0.12" >> "$LOGFILE"
echo "   ping 8.8.8.8" >> "$LOGFILE"
echo "" >> "$LOGFILE"
echo "4. If WiFi fails, restore GMS:" >> "$LOGFILE"
echo "   adb shell pm enable com.google.android.gms" >> "$LOGFILE"
echo "   adb shell pm enable com.android.vending" >> "$LOGFILE"
echo "   adb reboot" >> "$LOGFILE"
echo "" >> "$LOGFILE"
echo "5. Check RAM usage:" >> "$LOGFILE"
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
echo "Total packages disabled: $TOTAL_SUCCESS"
echo ""
echo "⚠️  WARNING: WiFi may stop working!"
echo "Keep ADB connection available for recovery."
echo ""
echo "Full log: $LOGFILE"
echo ""
echo "Ready to reboot? Run: adb reboot"
echo ""
