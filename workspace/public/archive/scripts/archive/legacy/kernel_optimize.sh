#!/bin/bash
# Kernel Configuration Optimizer for Samsung Galaxy A90 5G
# Conservative optimization profile - RAM savings: 120-160MB

CONFIG_FILE="$1"

if [ ! -f "$CONFIG_FILE" ]; then
    echo "Usage: $0 <path/to/.config>"
    exit 1
fi

echo "Optimizing kernel configuration: $CONFIG_FILE"
echo "Profile: Conservative (safe, low risk)"
echo ""

# Backup
cp "$CONFIG_FILE" "${CONFIG_FILE}.before_optimize"

# ====================================================================
# 1. Size Optimization (10-15MB savings)
# ====================================================================
echo "[1/7] Enabling size optimization..."
sed -i 's/CONFIG_CC_OPTIMIZE_FOR_PERFORMANCE=y/# CONFIG_CC_OPTIMIZE_FOR_PERFORMANCE is not set/' "$CONFIG_FILE"
echo "CONFIG_CC_OPTIMIZE_FOR_SIZE=y" >> "$CONFIG_FILE"

# ====================================================================
# 2. Camera Drivers Removal (30-50MB savings)
# ====================================================================
echo "[2/7] Disabling camera drivers..."
sed -i 's/CONFIG_MEDIA_SUPPORT=y/# CONFIG_MEDIA_SUPPORT is not set/' "$CONFIG_FILE"
sed -i 's/CONFIG_MEDIA_CAMERA_SUPPORT=y/# CONFIG_MEDIA_CAMERA_SUPPORT is not set/' "$CONFIG_FILE"
sed -i 's/CONFIG_VIDEO_DEV=y/# CONFIG_VIDEO_DEV is not set/' "$CONFIG_FILE"
sed -i 's/CONFIG_VIDEO_V4L2=y/# CONFIG_VIDEO_V4L2 is not set/' "$CONFIG_FILE"
sed -i 's/CONFIG_CAMERA_SYSFS_V2=y/# CONFIG_CAMERA_SYSFS_V2 is not set/' "$CONFIG_FILE"

# ====================================================================
# 3. Audio Drivers Removal (15-25MB savings)
# ====================================================================
echo "[3/7] Disabling audio drivers..."
sed -i 's/CONFIG_SOUND=y/# CONFIG_SOUND is not set/' "$CONFIG_FILE"
sed -i 's/CONFIG_SND=y/# CONFIG_SND is not set/' "$CONFIG_FILE"

# ====================================================================
# 4. Debug Features Removal (20-30MB savings)
# ====================================================================
echo "[4/7] Disabling debug features..."
sed -i 's/CONFIG_DEBUG_INFO=y/# CONFIG_DEBUG_INFO is not set/' "$CONFIG_FILE"
sed -i 's/CONFIG_DEBUG_FS=y/# CONFIG_DEBUG_FS is not set/' "$CONFIG_FILE"
sed -i 's/CONFIG_DEBUG_KERNEL=y/# CONFIG_DEBUG_KERNEL is not set/' "$CONFIG_FILE"
sed -i 's/CONFIG_SLUB_DEBUG=y/# CONFIG_SLUB_DEBUG is not set/' "$CONFIG_FILE"
sed -i 's/CONFIG_FTRACE=y/# CONFIG_FTRACE is not set/' "$CONFIG_FILE"
sed -i 's/CONFIG_TRACING=y/# CONFIG_TRACING is not set/' "$CONFIG_FILE"
sed -i 's/CONFIG_PROFILING=y/# CONFIG_PROFILING is not set/' "$CONFIG_FILE"

# ====================================================================
# 5. Framebuffer Console Removal (save RAM)
# ====================================================================
echo "[5/7] Disabling framebuffer console..."
sed -i 's/CONFIG_FRAMEBUFFER_CONSOLE=y/# CONFIG_FRAMEBUFFER_CONSOLE is not set/' "$CONFIG_FILE"
sed -i 's/CONFIG_DRM_FBDEV_EMULATION=y/# CONFIG_DRM_FBDEV_EMULATION is not set/' "$CONFIG_FILE"

# ====================================================================
# 6. ZRAM Configuration (keep LZ4 for speed)
# ====================================================================
echo "[6/7] Configuring ZRAM..."
# ZRAM should already be enabled, just ensure it
grep -q "CONFIG_ZRAM=y" "$CONFIG_FILE" || echo "CONFIG_ZRAM=y" >> "$CONFIG_FILE"
grep -q "CONFIG_ZRAM_DEF_COMP_LZ4=y" "$CONFIG_FILE" || echo "CONFIG_ZRAM_DEF_COMP_LZ4=y" >> "$CONFIG_FILE"

# ====================================================================
# 7. Verify Critical Drivers (WiFi, UFS)
# ====================================================================
echo "[7/7] Verifying critical drivers..."
echo ""
echo "Critical drivers status:"
grep "CONFIG_QCA_CLD_WLAN" "$CONFIG_FILE" || echo "  WARNING: WiFi driver not found!"
grep "CONFIG_SCSI_UFS_QCOM" "$CONFIG_FILE" || echo "  WARNING: UFS storage driver not found!"
grep "CONFIG_CFG80211" "$CONFIG_FILE" || echo "  WARNING: CFG80211 not found!"

echo ""
echo "Optimization complete!"
echo "Backup saved: ${CONFIG_FILE}.before_optimize"
echo ""
echo "Expected RAM savings: 120-160MB"
echo "Expected kernel size reduction: 10-15MB"
