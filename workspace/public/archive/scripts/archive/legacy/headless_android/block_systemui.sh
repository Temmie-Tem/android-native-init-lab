#!/system/bin/sh
#
# Block SystemUI from auto-restart
# Run this via Magisk boot script
#

LOGFILE="/data/local/tmp/block_systemui.log"

echo "================================================" | tee -a "$LOGFILE"
echo "Blocking SystemUI Auto-Restart" | tee -a "$LOGFILE"
echo "Started: $(date)" | tee -a "$LOGFILE"
echo "================================================" | tee -a "$LOGFILE"

# Method 1: Disable SystemUI service
echo "" | tee -a "$LOGFILE"
echo "[1/4] Disabling SystemUI package..." | tee -a "$LOGFILE"
pm disable-user --user 0 com.android.systemui >> "$LOGFILE" 2>&1

# Method 2: Kill SystemUI process repeatedly
echo "" | tee -a "$LOGFILE"
echo "[2/4] Killing SystemUI process..." | tee -a "$LOGFILE"
am force-stop com.android.systemui >> "$LOGFILE" 2>&1
pkill -9 systemui >> "$LOGFILE" 2>&1

# Method 3: Freeze SystemUI process
echo "" | tee -a "$LOGFILE"
echo "[3/4] Freezing SystemUI process..." | tee -a "$LOGFILE"
PID=$(pidof com.android.systemui)
if [ -n "$PID" ]; then
    echo "  Found SystemUI PID: $PID" | tee -a "$LOGFILE"
    kill -STOP "$PID" >> "$LOGFILE" 2>&1
    echo "  Sent SIGSTOP to PID $PID" | tee -a "$LOGFILE"
else
    echo "  SystemUI not running (good!)" | tee -a "$LOGFILE"
fi

# Method 4: Rename SystemUI APK (requires remount)
echo "" | tee -a "$LOGFILE"
echo "[4/4] Checking SystemUI APK status..." | tee -a "$LOGFILE"
if [ -f /system/priv-app/SystemUI/SystemUI.apk ]; then
    echo "  SystemUI.apk exists (cannot rename without remount)" | tee -a "$LOGFILE"
else
    echo "  SystemUI.apk not found or already renamed" | tee -a "$LOGFILE"
fi

echo "" | tee -a "$LOGFILE"
echo "================================================" | tee -a "$LOGFILE"
echo "SystemUI Block Completed" | tee -a "$LOGFILE"
echo "Completed: $(date)" | tee -a "$LOGFILE"
echo "================================================" | tee -a "$LOGFILE"

# Continuous monitoring (run in background)
(
    while true; do
        sleep 10
        PID=$(pidof com.android.systemui)
        if [ -n "$PID" ]; then
            echo "[$(date)] SystemUI restarted (PID: $PID) - killing..." >> "$LOGFILE"
            am force-stop com.android.systemui
            kill -STOP "$PID"
        fi
    done
) &

echo "Background monitor started (checking every 10 seconds)" | tee -a "$LOGFILE"
