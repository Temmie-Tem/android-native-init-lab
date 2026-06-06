#!/system/bin/sh
# ====================================================================
# Headless Boot v2 - Service Script
# ====================================================================
# Runs NON-BLOCKING during late_start service phase
# Purpose: Kill GUI processes, start SSH, monitor SystemUI
# ====================================================================

MODDIR=${0%/*}
LOGFILE="/data/local/tmp/headless_boot_v2_service.log"

echo "==========================================" > "$LOGFILE"
echo "Headless Boot v2 - Service" >> "$LOGFILE"
echo "Started: $(date)" >> "$LOGFILE"
echo "==========================================" >> "$LOGFILE"
echo "" >> "$LOGFILE"

# ====================================================================
# Wait for boot completion
# ====================================================================
echo "Waiting for boot completion..." >> "$LOGFILE"

TIMEOUT=120
ELAPSED=0

while [ "$(getprop sys.boot_completed)" != "1" ] && [ $ELAPSED -lt $TIMEOUT ]; do
    sleep 1
    ELAPSED=$((ELAPSED + 1))
done

if [ "$(getprop sys.boot_completed)" = "1" ]; then
    echo "  ✓ Boot completed in ${ELAPSED}s" >> "$LOGFILE"
else
    echo "  ✗ Boot timeout after ${TIMEOUT}s" >> "$LOGFILE"
    exit 1
fi

sleep 5  # Additional wait for stability

# ====================================================================
# Disable all GUI and bloatware packages
# ====================================================================
echo "" >> "$LOGFILE"
echo "Disabling GUI and bloatware packages..." >> "$LOGFILE"

TOTAL_DISABLED=0

# GUI packages (25)
GUI_PACKAGES="
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
com.android.theme.icon_pack.circular.systemui
com.android.theme.icon_pack.filled.systemui
com.android.theme.icon_pack.rounded.systemui
com.sec.android.app.launcher
com.sec.android.app.desktoplauncher
com.sec.android.emergencylauncher
com.android.theme.icon_pack.circular.launcher
com.android.theme.icon_pack.filled.launcher
com.android.theme.icon_pack.rounded.launcher
com.samsung.android.honeyboard
"

# Samsung bloatware (79)
SAMSUNG_PACKAGES="
com.samsung.faceservice
com.sec.android.app.samsungapps
com.kt.olleh.storefront
com.skt.skaf.OA00018282
com.samsung.android.app.settings.bixby
com.samsung.android.bixby.agent
com.samsung.android.bixby.service
com.samsung.android.bixby.wakeup
com.samsung.android.bixbyvision.framework
com.samsung.android.knox.analytics.uploader
com.samsung.android.knox.attestation
com.samsung.android.kgclient
com.sec.enterprise.knox.cloudmdm.smdms
com.osp.app.signin
com.samsung.android.samsungpass
com.samsung.android.samsungpassautofill
com.samsung.android.scloud
com.samsung.android.game.gamehome
com.samsung.android.game.gametools
com.samsung.android.game.gos
com.samsung.gamedriver.sm8150
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
com.samsung.android.app.appsedge
com.samsung.android.app.clipboardedge
com.samsung.android.app.cocktailbarservice
com.samsung.android.app.taskedge
com.samsung.android.service.peoplestripe
com.samsung.android.app.dofviewer
com.samsung.android.ardrawing
com.samsung.android.aremoji
com.samsung.android.arzone
com.samsung.android.livestickers
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

# Google services (20)
GOOGLE_PACKAGES="
com.google.android.apps.maps
com.google.android.apps.tachyon
com.google.android.youtube
com.google.android.gm
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
com.google.android.googlequicksearchbox
com.google.android.gms
com.google.android.gms.location.history
com.google.android.gsf
com.android.vending
"

# Apps (40)
APP_PACKAGES="
com.sec.android.app.soundalive
com.samsung.android.video
com.samsung.app.newtrim
com.samsung.android.app.camera.sticker.facearavatar.preload
com.samsung.android.camerasdkservice
com.samsung.android.cameraxservice
com.sec.android.app.camera
com.sec.factory.camera
com.sec.factory.cameralyzer
com.android.cameraextensions
com.sec.android.gallery3d
com.sec.android.mimage.photoretouching
com.samsung.android.app.earphonetypec
com.samsung.android.dialer
com.samsung.android.incallui
com.samsung.phone.overlay.common
com.sec.phone
com.samsung.android.incall.contentprovider
com.samsung.android.callbgprovider
com.samsung.android.app.telephonyui
com.samsung.android.messaging
com.samsung.android.dsms
com.samsung.android.app.contacts
com.samsung.android.providers.contacts
com.sec.android.widgetapp.easymodecontactswidget
com.android.chrome
com.sec.android.app.chromecustomizations
com.samsung.android.calendar
com.sec.android.app.myfiles
com.sec.android.app.ve.vebgm
com.sec.android.app.vepreload
com.sec.android.app.clockpackage
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

# Disable function
disable_packages() {
    CATEGORY="$1"
    shift
    PACKAGES="$@"

    echo "Disabling: $CATEGORY" >> "$LOGFILE"
    COUNT=0

    for pkg in $PACKAGES; do
        # Check if package exists
        if pm list packages | grep -q "^package:$pkg$"; then
            # Disable package
            pm disable-user --user 0 "$pkg" >> "$LOGFILE" 2>&1
            if [ $? -eq 0 ]; then
                TOTAL_DISABLED=$((TOTAL_DISABLED + 1))
                COUNT=$((COUNT + 1))
            fi
        fi
    done

    echo "  → $CATEGORY: $COUNT packages disabled" >> "$LOGFILE"
}

# Disable all categories
disable_packages "GUI" $GUI_PACKAGES
disable_packages "Samsung" $SAMSUNG_PACKAGES
disable_packages "Google" $GOOGLE_PACKAGES
disable_packages "Apps" $APP_PACKAGES

echo "" >> "$LOGFILE"
echo "Total packages disabled: $TOTAL_DISABLED" >> "$LOGFILE"

# ====================================================================
# Kill GUI processes
# ====================================================================
echo "" >> "$LOGFILE"
echo "Killing GUI processes..." >> "$LOGFILE"

KILLED=0

# SystemUI
if ps -A | grep -q "com.android.systemui"; then
    am force-stop com.android.systemui >> "$LOGFILE" 2>&1
    pkill -9 com.android.systemui >> "$LOGFILE" 2>&1
    echo "  ✓ Killed SystemUI" >> "$LOGFILE"
    KILLED=$((KILLED + 1))
fi

# Launcher
if ps -A | grep -q "com.sec.android.app.launcher"; then
    am force-stop com.sec.android.app.launcher >> "$LOGFILE" 2>&1
    pkill -9 com.sec.android.app.launcher >> "$LOGFILE" 2>&1
    echo "  ✓ Killed Launcher" >> "$LOGFILE"
    KILLED=$((KILLED + 1))
fi

# Keyboard
if ps -A | grep -q "com.samsung.android.honeyboard"; then
    am force-stop com.samsung.android.honeyboard >> "$LOGFILE" 2>&1
    pkill -9 com.samsung.android.honeyboard >> "$LOGFILE" 2>&1
    echo "  ✓ Killed Keyboard" >> "$LOGFILE"
    KILLED=$((KILLED + 1))
fi

echo "Total processes killed: $KILLED" >> "$LOGFILE"

# ====================================================================
# Start SSH server (if systemless_chroot module exists)
# ====================================================================
echo "" >> "$LOGFILE"
echo "Starting SSH server..." >> "$LOGFILE"

if [ -f "/data/adb/modules/systemless_chroot/service.d/boot_chroot.sh" ]; then
    sh /data/adb/modules/systemless_chroot/service.d/boot_chroot.sh >> "$LOGFILE" 2>&1 &
    sleep 2

    if ps -A | grep -q "sshd"; then
        echo "  ✓ SSH server started" >> "$LOGFILE"
    else
        echo "  ✗ SSH server failed to start" >> "$LOGFILE"
    fi
else
    echo "  - systemless_chroot module not found" >> "$LOGFILE"
fi

# ====================================================================
# SystemUI watchdog (prevent restart)
# ====================================================================
echo "" >> "$LOGFILE"
echo "Starting SystemUI watchdog..." >> "$LOGFILE"

(
    while true; do
        sleep 10

        # Check if SystemUI is running
        if ps -A | grep -q "com.android.systemui"; then
            echo "$(date): SystemUI detected, killing..." >> "$LOGFILE"
            am force-stop com.android.systemui >> "$LOGFILE" 2>&1
            pkill -9 com.android.systemui >> "$LOGFILE" 2>&1
        fi
    done
) &

WATCHDOG_PID=$!
echo "  ✓ Watchdog started (PID: $WATCHDOG_PID)" >> "$LOGFILE"

# ====================================================================
# Final status
# ====================================================================
echo "" >> "$LOGFILE"
echo "==========================================" >> "$LOGFILE"
echo "Service script completed: $(date)" >> "$LOGFILE"
echo "==========================================" >> "$LOGFILE"
echo "" >> "$LOGFILE"

# Memory measurement
echo "Memory status:" >> "$LOGFILE"
free -m >> "$LOGFILE" 2>&1
