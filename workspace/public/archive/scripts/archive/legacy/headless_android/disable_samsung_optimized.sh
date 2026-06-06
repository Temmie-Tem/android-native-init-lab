#!/system/bin/sh
# ====================================================================
# Stage 2: Samsung 서비스 제거 (최적화 버전)
# ====================================================================
# 목적: 실제 설치된 Samsung 서비스만 제거
# 패키지 스캔 결과 기반 (2025-11-15)
# RAM 절감 예상: ~400MB
# ====================================================================

LOGFILE="/data/local/tmp/headless_stage2.log"

echo "=========================================" > "$LOGFILE"
echo "Stage 2: Samsung Services Removal (Optimized)" >> "$LOGFILE"
echo "=========================================" >> "$LOGFILE"
echo "" >> "$LOGFILE"
echo "Started: $(date)" >> "$LOGFILE"
echo "" >> "$LOGFILE"

# ====================================================================
# 실제 설치된 Samsung 패키지
# ====================================================================

# Bixby (6 packages)
PACKAGES_BIXBY="
com.samsung.android.app.settings.bixby
com.samsung.android.bixby.agent
com.samsung.android.bixby.service
com.samsung.android.bixby.wakeup
com.samsung.android.bixbyvision.framework
"

# Knox (9 packages) - ⚠️ 일부만 안전하게 제거
PACKAGES_KNOX_SAFE="
com.samsung.android.knox.analytics.uploader
com.samsung.android.knox.attestation
com.samsung.android.kgclient
com.sec.enterprise.knox.cloudmdm.smdms
"

# Samsung Account & Cloud (4 packages)
PACKAGES_SAMSUNG_ACCOUNT="
com.osp.app.signin
com.samsung.android.samsungpass
com.samsung.android.samsungpassautofill
com.samsung.android.scloud
"

# Game Services (4 packages)
PACKAGES_GAME="
com.samsung.android.game.gamehome
com.samsung.android.game.gametools
com.samsung.android.game.gos
com.samsung.gamedriver.sm8150
"

# Theme Store (30+ packages)
PACKAGES_THEME="
com.android.theme.color.black
com.android.theme.color.cinnamon
com.android.theme.color.green
com.android.theme.color.ocean
com.android.theme.color.orchid
com.android.theme.color.purple
com.android.theme.color.space
com.android.theme.font.notoserifsource
com.android.theme.icon.pebble
com.android.theme.icon.roundedrect
com.android.theme.icon.squircle
com.android.theme.icon.taperedrect
com.android.theme.icon.teardrop
com.android.theme.icon.vessel
com.android.theme.icon_pack.circular.android
com.android.theme.icon_pack.circular.settings
com.android.theme.icon_pack.circular.themepicker
com.android.theme.icon_pack.filled.android
com.android.theme.icon_pack.filled.settings
com.android.theme.icon_pack.filled.themepicker
com.android.theme.icon_pack.rounded.android
com.android.theme.icon_pack.rounded.settings
com.android.theme.icon_pack.rounded.themepicker
com.samsung.android.themecenter
com.samsung.android.themestore
"

# Samsung Edge Services (7 packages)
PACKAGES_EDGE="
com.samsung.android.app.appsedge
com.samsung.android.app.clipboardedge
com.samsung.android.app.cocktailbarservice
com.samsung.android.app.taskedge
com.samsung.android.service.peoplestripe
"

# Samsung AR/VR (5 packages)
PACKAGES_AR="
com.samsung.android.app.dofviewer
com.samsung.android.ardrawing
com.samsung.android.aremoji
com.samsung.android.arzone
com.samsung.android.livestickers
"

# Other Samsung Services (불필요한 것들)
PACKAGES_SAMSUNG_OTHER="
com.samsung.android.app.aodservice
com.samsung.android.app.dressroom
com.samsung.android.app.galaxyfinder
com.samsung.android.app.kfa
com.samsung.android.app.ledbackcover
com.samsung.android.app.reminder
com.samsung.android.app.routines
com.samsung.android.app.sharelive
com.samsung.android.app.simplesharing
com.samsung.android.app.smartcapture
com.samsung.android.app.soundpicker
com.samsung.android.app.spage
com.samsung.android.app.tips
com.samsung.android.app.updatecenter
com.samsung.android.app.watchmanagerstub
com.samsung.android.appseparation
com.samsung.android.service.health
com.samsung.android.service.stplatform
com.samsung.android.fmm
com.samsung.android.smartcallprovider
com.samsung.android.sm.devicesecurity
com.sec.android.easyMover.Agent
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

disable_packages "Bixby Services" $PACKAGES_BIXBY
TOTAL_SUCCESS=$((TOTAL_SUCCESS + $?))

disable_packages "Knox Analytics (Safe)" $PACKAGES_KNOX_SAFE
TOTAL_SUCCESS=$((TOTAL_SUCCESS + $?))

disable_packages "Samsung Account & Cloud" $PACKAGES_SAMSUNG_ACCOUNT
TOTAL_SUCCESS=$((TOTAL_SUCCESS + $?))

disable_packages "Game Services" $PACKAGES_GAME
TOTAL_SUCCESS=$((TOTAL_SUCCESS + $?))

disable_packages "Theme Store & Icons" $PACKAGES_THEME
TOTAL_SUCCESS=$((TOTAL_SUCCESS + $?))

disable_packages "Edge Services" $PACKAGES_EDGE
TOTAL_SUCCESS=$((TOTAL_SUCCESS + $?))

disable_packages "AR/VR Services" $PACKAGES_AR
TOTAL_SUCCESS=$((TOTAL_SUCCESS + $?))

disable_packages "Other Samsung Services" $PACKAGES_SAMSUNG_OTHER
TOTAL_SUCCESS=$((TOTAL_SUCCESS + $?))

# ====================================================================
# 결과 요약
# ====================================================================

echo "" >> "$LOGFILE"
echo "=========================================" >> "$LOGFILE"
echo "Stage 2 Completed" >> "$LOGFILE"
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
echo "Total packages disabled: $TOTAL_SUCCESS"
echo ""
echo "Full log: $LOGFILE"
echo ""
echo "Ready to reboot? Run: adb reboot"
echo ""
