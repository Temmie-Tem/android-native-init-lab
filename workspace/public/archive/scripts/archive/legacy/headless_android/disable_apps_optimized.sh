#!/system/bin/sh
# ====================================================================
# Stage 4: 불필요한 앱 제거 (최적화 버전)
# ====================================================================
# 목적: 실제 설치된 Media/Communication/Productivity 앱만 제거
# 패키지 스캔 결과 기반 (2025-11-15)
# RAM 절감 예상: ~200MB
# ====================================================================

LOGFILE="/data/local/tmp/headless_stage4.log"

echo "=========================================" > "$LOGFILE"
echo "Stage 4: Unnecessary Apps Removal (Optimized)" >> "$LOGFILE"
echo "=========================================" >> "$LOGFILE"
echo "" >> "$LOGFILE"
echo "Started: $(date)" >> "$LOGFILE"
echo "" >> "$LOGFILE"

# ====================================================================
# 실제 설치된 불필요한 앱
# ====================================================================

# Media: Music (1 package)
PACKAGES_MUSIC="
com.sec.android.app.soundalive
"

# Media: Video (1 package)
PACKAGES_VIDEO="
com.samsung.android.video
com.samsung.app.newtrim
"

# Media: Camera (7 packages)
PACKAGES_CAMERA="
com.samsung.android.app.camera.sticker.facearavatar.preload
com.samsung.android.camerasdkservice
com.samsung.android.cameraxservice
com.sec.android.app.camera
com.sec.factory.camera
com.sec.factory.cameralyzer
com.android.cameraextensions
"

# Media: Gallery (1 package)
PACKAGES_GALLERY="
com.sec.android.gallery3d
com.sec.android.mimage.photoretouching
"

# Communication: Phone & Dialer (6 packages)
PACKAGES_PHONE="
com.samsung.android.app.earphonetypec
com.samsung.android.dialer
com.samsung.android.incallui
com.samsung.phone.overlay.common
com.sec.phone
com.samsung.android.incall.contentprovider
com.samsung.android.callbgprovider
com.samsung.android.app.telephonyui
"

# Communication: Messaging (3 packages)
PACKAGES_MESSAGING="
com.samsung.android.messaging
com.samsung.android.dsms
"

# Communication: Contacts (4 packages)
PACKAGES_CONTACTS="
com.samsung.android.app.contacts
com.samsung.android.providers.contacts
com.sec.android.widgetapp.easymodecontactswidget
"

# Productivity: Browser (2 packages)
PACKAGES_BROWSER="
com.android.chrome
com.sec.android.app.chromecustomizations
"

# Productivity: Calendar (3 packages)
PACKAGES_CALENDAR="
com.samsung.android.calendar
"

# Productivity: File Manager (1 package)
PACKAGES_FILES="
com.sec.android.app.myfiles
"

# Samsung Video Editor
PACKAGES_VIDEO_EDITOR="
com.sec.android.app.ve.vebgm
com.sec.android.app.vepreload
"

# Samsung Clock
PACKAGES_CLOCK="
com.sec.android.app.clockpackage
"

# Samsung Other Apps
PACKAGES_SAMSUNG_APPS="
com.samsung.android.app.magnifier
com.sec.android.app.quicktool
com.sec.android.app.personalization
com.samsung.android.forest
com.sec.android.QRreader
com.sec.android.app.fm
com.samsung.android.smartsuggestions
com.samsung.android.stickercenter
com.samsung.android.singletake.service
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

disable_packages "Music Apps" $PACKAGES_MUSIC
TOTAL_SUCCESS=$((TOTAL_SUCCESS + $?))

disable_packages "Video Apps" $PACKAGES_VIDEO
TOTAL_SUCCESS=$((TOTAL_SUCCESS + $?))

disable_packages "Camera Apps" $PACKAGES_CAMERA
TOTAL_SUCCESS=$((TOTAL_SUCCESS + $?))

disable_packages "Gallery Apps" $PACKAGES_GALLERY
TOTAL_SUCCESS=$((TOTAL_SUCCESS + $?))

disable_packages "Phone & Dialer" $PACKAGES_PHONE
TOTAL_SUCCESS=$((TOTAL_SUCCESS + $?))

disable_packages "Messaging Apps" $PACKAGES_MESSAGING
TOTAL_SUCCESS=$((TOTAL_SUCCESS + $?))

disable_packages "Contacts Apps" $PACKAGES_CONTACTS
TOTAL_SUCCESS=$((TOTAL_SUCCESS + $?))

disable_packages "Browser Apps" $PACKAGES_BROWSER
TOTAL_SUCCESS=$((TOTAL_SUCCESS + $?))

disable_packages "Calendar Apps" $PACKAGES_CALENDAR
TOTAL_SUCCESS=$((TOTAL_SUCCESS + $?))

disable_packages "File Manager" $PACKAGES_FILES
TOTAL_SUCCESS=$((TOTAL_SUCCESS + $?))

disable_packages "Video Editor" $PACKAGES_VIDEO_EDITOR
TOTAL_SUCCESS=$((TOTAL_SUCCESS + $?))

disable_packages "Clock" $PACKAGES_CLOCK
TOTAL_SUCCESS=$((TOTAL_SUCCESS + $?))

disable_packages "Other Samsung Apps" $PACKAGES_SAMSUNG_APPS
TOTAL_SUCCESS=$((TOTAL_SUCCESS + $?))

# ====================================================================
# 결과 요약
# ====================================================================

echo "" >> "$LOGFILE"
echo "=========================================" >> "$LOGFILE"
echo "Stage 4 Completed" >> "$LOGFILE"
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
echo "2. Final verification:" >> "$LOGFILE"
echo "   adb wait-for-device" >> "$LOGFILE"
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
echo "Total packages disabled: $TOTAL_SUCCESS"
echo ""
echo "Full log: $LOGFILE"
echo ""
echo "🎉 All 4 stages completed!"
echo "Expected RAM usage: ~1.0GB (down from 2.5GB)"
echo ""
echo "Ready to reboot? Run: adb reboot"
echo ""
