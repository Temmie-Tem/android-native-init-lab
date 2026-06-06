#!/system/bin/sh
#
# Kill all disabled packages
# This should be run after disabling packages
#

LOGFILE="/data/local/tmp/kill_disabled_apps.log"

echo "================================================" | tee "$LOGFILE"
echo "Killing All Disabled Apps" | tee -a "$LOGFILE"
echo "Started: $(date)" | tee -a "$LOGFILE"
echo "================================================" | tee -a "$LOGFILE"

KILLED=0
FAILED=0

# Get all disabled packages
pm list packages -d | sed 's/^package://' | while read -r pkg; do
    # Check if package is running
    if ps -A | grep -q "$pkg"; then
        echo "Killing: $pkg" | tee -a "$LOGFILE"
        
        # Method 1: Force stop
        am force-stop "$pkg" 2>&1 | tee -a "$LOGFILE"
        
        # Method 2: Kill by PID
        PID=$(pidof "$pkg")
        if [ -n "$PID" ]; then
            kill -9 "$PID" 2>&1 | tee -a "$LOGFILE"
            echo "  ✓ Killed PID: $PID" | tee -a "$LOGFILE"
            KILLED=$((KILLED + 1))
        else
            echo "  ✓ Force stopped (no PID)" | tee -a "$LOGFILE"
            KILLED=$((KILLED + 1))
        fi
    fi
done

echo "" | tee -a "$LOGFILE"
echo "================================================" | tee -a "$LOGFILE"
echo "Total processes killed: $KILLED" | tee -a "$LOGFILE"
echo "Failed: $FAILED" | tee -a "$LOGFILE"
echo "================================================" | tee -a "$LOGFILE"
echo "Completed: $(date)" | tee -a "$LOGFILE"
echo "================================================" | tee -a "$LOGFILE"

# Wait and check RAM
sleep 3
echo "" | tee -a "$LOGFILE"
echo "RAM After Cleanup:" | tee -a "$LOGFILE"
free -m | tee -a "$LOGFILE"
