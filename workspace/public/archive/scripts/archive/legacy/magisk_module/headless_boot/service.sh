#!/system/bin/sh
#
# Headless Android Boot Service
# Runs on every boot to disable GUI and bloatware
#

MODDIR=${0%/*}
LOGFILE="/data/local/tmp/headless_boot.log"

# Wait for boot to complete
while [ "$(getprop sys.boot_completed)" != "1" ]; do
    sleep 1
done

# Additional wait for package manager
sleep 10

echo "================================================" > "$LOGFILE"
echo "Headless Boot Service Started" >> "$LOGFILE"
echo "Time: $(date)" >> "$LOGFILE"
echo "================================================" >> "$LOGFILE"

# Stage 1: GUI Components (25 packages)
echo "" >> "$LOGFILE"
echo "[Stage 1] Disabling GUI Components..." >> "$LOGFILE"

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

GUI_COUNT=0
for pkg in $GUI_PACKAGES; do
    if pm list packages | grep -q "^package:$pkg$"; then
        pm disable-user --user 0 "$pkg" >> "$LOGFILE" 2>&1
        if [ $? -eq 0 ]; then
            echo "  ✓ Disabled: $pkg" >> "$LOGFILE"
            GUI_COUNT=$((GUI_COUNT + 1))
        fi
    fi
done

echo "Stage 1 Complete: $GUI_COUNT packages disabled" >> "$LOGFILE"

# Stage 2: Samsung Bloatware (80+ packages)
echo "" >> "$LOGFILE"
echo "[Stage 2] Disabling Samsung Bloatware..." >> "$LOGFILE"

SAMSUNG_PACKAGES="
com.samsung.android.app.settings.bixby
com.samsung.android.bixby.agent
com.samsung.android.bixby.service
com.samsung.android.bixby.wakeup
com.samsung.android.bixbyvision.framework
com.samsung.android.visionintelligence
com.android.theme.color.black
com.android.theme.color.cinnamon
com.android.theme.color.green
com.android.theme.color.ocean
com.android.theme.color.orchid
com.android.theme.color.purple
com.android.theme.color.space
com.android.theme.font.notoserifsource
com.monotype.android.font.chococooky
com.monotype.android.font.cooljazz
com.monotype.android.font.foundation
com.monotype.android.font.rosemary
com.samsung.android.app.appsedge
com.samsung.android.app.cocktailbarservice
com.samsung.android.app.galaxyfinder
com.samsung.android.app.ledbackcover
com.samsung.android.app.ledcoverdream
com.samsung.android.app.clipboardedge
com.samsung.android.samsungpass
com.samsung.android.samsungpassautofill
com.samsung.android.authfw
com.samsung.android.bio.face.service
com.samsung.android.biometrics.app.setting
com.samsung.android.smartface
com.samsung.android.svoiceime
com.samsung.android.bixby.voiceinput
com.samsung.android.bixby.es.globalaction
com.samsung.android.service.peoplestripe
com.samsung.android.app.sbrowseredge
com.samsung.android.app.notes
com.samsung.android.app.reminder
com.samsung.android.app.taskedge
com.samsung.android.da.daagent
com.samsung.android.digitalwellbeing
com.samsung.android.app.parentalcare
com.samsung.android.mdecservice
com.samsung.android.service.livedrawing
com.samsung.android.ardrawing
com.samsung.android.arzone
com.samsung.android.aremoji
com.samsung.android.aremojieditor
com.samsung.android.livestickers
com.samsung.android.app.dexonpc
com.samsung.android.mdx
com.samsung.android.mdx.kit
com.samsung.android.mdx.quickboard
com.samsung.desktopsystemui
com.samsung.android.app.smartcapture
com.samsung.android.app.galaxylabs
com.sec.android.app.samsungapps
com.samsung.android.themestore
com.samsung.android.themecenter
com.sec.android.app.myfiles
com.samsung.android.rubin.app
com.samsung.android.scs
com.samsung.android.game.gamehome
com.samsung.android.game.gametools
com.samsung.android.game.gos
com.enhance.gameservice
com.samsung.android.gametuner.thin
com.samsung.android.samsungpositioning
com.samsung.android.location
com.samsung.android.sLocation
com.sec.location.nsflp2
com.samsung.android.sm.devicesecurity
com.samsung.android.sm.policy
com.samsung.android.sm.provider
com.sec.android.sdhms
com.wssyncmldm
com.samsung.android.sdm.config
"

SAMSUNG_COUNT=0
for pkg in $SAMSUNG_PACKAGES; do
    if pm list packages | grep -q "^package:$pkg$"; then
        pm disable-user --user 0 "$pkg" >> "$LOGFILE" 2>&1
        if [ $? -eq 0 ]; then
            echo "  ✓ Disabled: $pkg" >> "$LOGFILE"
            SAMSUNG_COUNT=$((SAMSUNG_COUNT + 1))
        fi
    fi
done

echo "Stage 2 Complete: $SAMSUNG_COUNT packages disabled" >> "$LOGFILE"

# Stage 3: Google Services (20+ packages)
echo "" >> "$LOGFILE"
echo "[Stage 3] Disabling Google Services..." >> "$LOGFILE"

GOOGLE_PACKAGES="
com.google.android.gms
com.google.android.gms.location.history
com.google.android.gsf
com.android.vending
com.google.android.apps.docs
com.google.android.apps.maps
com.google.android.apps.photos
com.google.android.apps.youtube.music
com.google.android.music
com.google.android.videos
com.google.android.apps.tachyon
com.google.android.talk
com.google.android.gm
com.google.android.calendar
com.google.android.keep
com.google.android.apps.wellbeing
com.google.android.as
com.google.android.apps.turbo
com.google.android.configupdater
com.google.android.onetimeinitializer
"

GOOGLE_COUNT=0
for pkg in $GOOGLE_PACKAGES; do
    if pm list packages | grep -q "^package:$pkg$"; then
        pm disable-user --user 0 "$pkg" >> "$LOGFILE" 2>&1
        if [ $? -eq 0 ]; then
            echo "  ✓ Disabled: $pkg" >> "$LOGFILE"
            GOOGLE_COUNT=$((GOOGLE_COUNT + 1))
        fi
    fi
done

echo "Stage 3 Complete: $GOOGLE_COUNT packages disabled" >> "$LOGFILE"

# Stage 4: Apps (40+ packages)
echo "" >> "$LOGFILE"
echo "[Stage 4] Disabling Apps..." >> "$LOGFILE"

APP_PACKAGES="
com.sec.android.app.camera
com.samsung.android.smartswitchassistant
com.samsung.android.arcore
com.android.emergency
com.samsung.android.app.telephonyui
com.samsung.android.incallui
com.android.phone
com.samsung.android.dialer
com.samsung.android.messaging
com.android.providers.telephony
com.samsung.android.contacts
com.samsung.android.app.contacts
com.android.providers.contacts
com.sec.android.gallery3d
com.samsung.android.providers.media
com.sec.android.app.sbrowser
com.samsung.android.calendar
com.samsung.android.email.provider
com.samsung.android.app.memo
com.samsung.android.app.reminder
com.kt.olleh.storefront
com.ktpns.pa
"

APP_COUNT=0
for pkg in $APP_PACKAGES; do
    if pm list packages | grep -q "^package:$pkg$"; then
        pm disable-user --user 0 "$pkg" >> "$LOGFILE" 2>&1
        if [ $? -eq 0 ]; then
            echo "  ✓ Disabled: $pkg" >> "$LOGFILE"
            APP_COUNT=$((APP_COUNT + 1))
        fi
    fi
done

echo "Stage 4 Complete: $APP_COUNT packages disabled" >> "$LOGFILE"

# Kill SystemUI processes
echo "" >> "$LOGFILE"
echo "[Final] Killing GUI processes..." >> "$LOGFILE"

am force-stop com.android.systemui >> "$LOGFILE" 2>&1
am force-stop com.sec.android.app.launcher >> "$LOGFILE" 2>&1

SYSTEMUI_PID=$(pidof com.android.systemui)
if [ -n "$SYSTEMUI_PID" ]; then
    kill -9 "$SYSTEMUI_PID" >> "$LOGFILE" 2>&1
    echo "  ✓ Killed SystemUI (PID: $SYSTEMUI_PID)" >> "$LOGFILE"
fi

LAUNCHER_PID=$(pidof com.sec.android.app.launcher)
if [ -n "$LAUNCHER_PID" ]; then
    kill -9 "$LAUNCHER_PID" >> "$LOGFILE" 2>&1
    echo "  ✓ Killed Launcher (PID: $LAUNCHER_PID)" >> "$LOGFILE"
fi

echo "" >> "$LOGFILE"
echo "================================================" >> "$LOGFILE"
echo "Total Disabled: GUI=$GUI_COUNT Samsung=$SAMSUNG_COUNT Google=$GOOGLE_COUNT Apps=$APP_COUNT" >> "$LOGFILE"
TOTAL_DISABLED=$((GUI_COUNT + SAMSUNG_COUNT + GOOGLE_COUNT + APP_COUNT))
echo "TOTAL: $TOTAL_DISABLED packages" >> "$LOGFILE"
echo "================================================" >> "$LOGFILE"
echo "Headless Boot Service Completed" >> "$LOGFILE"
echo "Time: $(date)" >> "$LOGFILE"
echo "================================================" >> "$LOGFILE"
