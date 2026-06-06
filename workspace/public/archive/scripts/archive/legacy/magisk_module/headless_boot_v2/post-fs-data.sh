#!/system/bin/sh
# ====================================================================
# Headless Boot v2 - Post-FS-Data Script
# ====================================================================
# Runs BLOCKING during boot, before system fully starts
# Purpose: Disable YABP only (package disabling moved to service.sh)
# ====================================================================

MODDIR=${0%/*}
LOGFILE="/data/local/tmp/headless_boot_v2.log"

echo "==========================================" > "$LOGFILE"
echo "Headless Boot v2 - Post-FS-Data" >> "$LOGFILE"
echo "Started: $(date)" >> "$LOGFILE"
echo "==========================================" >> "$LOGFILE"
echo "" >> "$LOGFILE"

# ====================================================================
# Disable YABP SystemUI monitoring (if installed)
# ====================================================================
if [ -d "/data/adb/YABP" ]; then
    echo "Disabling YABP SystemUI monitor..." >> "$LOGFILE"
    touch /data/adb/systemui.monitor.disable
    echo "headless_boot_v2" > /data/adb/YABP/allowed-modules.txt
    echo "  ✓ YABP bypassed" >> "$LOGFILE"
fi

echo "" >> "$LOGFILE"
echo "Post-FS-Data completed: $(date)" >> "$LOGFILE"
echo "NOTE: Package disabling happens in service.sh" >> "$LOGFILE"
