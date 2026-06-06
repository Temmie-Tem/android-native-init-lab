#!/bin/bash
################################################################################
# Minimal Build Configuration Script
# Samsung Galaxy A90 5G (r3q) - Option C: Minimal AOSP Build
#
# This script configures minimal AOSP build with Camera/Audio options
################################################################################

set -e  # Exit on error

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[OK]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Minimal Build Configuration${NC}"
echo -e "${BLUE}Samsung Galaxy A90 5G (r3q)${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Configuration
AOSP_DIR="${HOME}/aosp/r3q"
DEVICE_DIR="${AOSP_DIR}/device/samsung/r3q"

# Verify device tree exists
if [ ! -d "${DEVICE_DIR}" ]; then
    print_error "Device tree not found at ${DEVICE_DIR}"
    print_error "Please run ./03_setup_device_tree.sh first"
    exit 1
fi

cd "${DEVICE_DIR}"

# Build configuration options
echo -e "${YELLOW}Configure minimal build options:${NC}"
echo ""
echo "1. Camera support:"
echo "   - YES: Include camera HAL and drivers"
echo "   - NO:  Exclude camera (saves ~50MB RAM)"
read -p "Enable Camera? [Y/n]: " ENABLE_CAMERA
ENABLE_CAMERA=${ENABLE_CAMERA:-Y}

echo ""
echo "2. Audio support:"
echo "   - YES: Include audio HAL and effects"
echo "   - NO:  Minimal audio only (saves ~30MB RAM)"
read -p "Enable Audio? [Y/n]: " ENABLE_AUDIO
ENABLE_AUDIO=${ENABLE_AUDIO:-Y}

echo ""
echo "3. Bluetooth support:"
read -p "Enable Bluetooth? [y/N]: " ENABLE_BT
ENABLE_BT=${ENABLE_BT:-N}

echo ""
echo "4. NFC support:"
read -p "Enable NFC? [y/N]: " ENABLE_NFC
ENABLE_NFC=${ENABLE_NFC:-N}

# Create minimal product makefile
print_status "Creating minimal product configuration..."

PRODUCT_MK="${DEVICE_DIR}/aosp_r3q_minimal.mk"

cat > "${PRODUCT_MK}" << 'EOF'
#
# Copyright (C) 2024 The AOSP Project
#
# SPDX-License-Identifier: Apache-2.0
#

# Inherit from minimal AOSP base (not full)
$(call inherit-product, $(SRC_TARGET_DIR)/product/core_minimal.mk)

# Inherit from r3q device configuration
$(call inherit-product, device/samsung/r3q/device.mk)

# Inherit from sm8150-common
$(call inherit-product, device/samsung/sm8150-common/sm8150.mk)

# Product information
PRODUCT_NAME := aosp_r3q_minimal
PRODUCT_DEVICE := r3q
PRODUCT_BRAND := AOSP
PRODUCT_MODEL := Galaxy A90 5G Minimal
PRODUCT_MANUFACTURER := Samsung
PRODUCT_GMS_CLIENTID_BASE := android-samsung

# Build properties
PRODUCT_PROPERTY_OVERRIDES += \
    ro.config.headless=1 \
    ro.setupwizard.mode=DISABLED \
    ro.com.android.dataroaming=false

# Minimal packages - Essential system components only
PRODUCT_PACKAGES += \
    framework-res \
    Settings \
    SystemUI \
    Phone \
    Telecom \
    Contacts \
    Dialer

# Essential hardware packages
PRODUCT_PACKAGES += \
    lights.msmnile \
    power.msmnile

# WiFi (ALWAYS REQUIRED)
PRODUCT_PACKAGES += \
    libwpa_client \
    wpa_supplicant \
    wpa_supplicant.conf \
    hostapd

# Remove unnecessary packages
PRODUCT_PACKAGES_REMOVE += \
    BasicDreams \
    Browser2 \
    Calendar \
    CalendarProvider \
    DownloadProviderUi \
    Email \
    Gallery2 \
    HTMLViewer \
    LiveWallpapers \
    LiveWallpapersPicker \
    Music \
    VideoEditor \
    WallpaperCropper \
    messaging

EOF

# Add Camera configuration
if [[ "$ENABLE_CAMERA" =~ ^[Yy]$ ]]; then
    cat >> "${PRODUCT_MK}" << 'EOF'

# Camera support ENABLED
PRODUCT_PACKAGES += \
    Camera2 \
    Snap

PRODUCT_PROPERTY_OVERRIDES += \
    config.disable_camera=false

EOF
    print_success "Camera support: ENABLED"
else
    cat >> "${PRODUCT_MK}" << 'EOF'

# Camera support DISABLED
PRODUCT_PROPERTY_OVERRIDES += \
    config.disable_camera=true

EOF
    print_warning "Camera support: DISABLED"
fi

# Add Audio configuration
if [[ "$ENABLE_AUDIO" =~ ^[Yy]$ ]]; then
    cat >> "${PRODUCT_MK}" << 'EOF'

# Audio support ENABLED
PRODUCT_PACKAGES += \
    audio.primary.msmnile \
    AudioFX \
    audio.a2dp.default \
    audio.usb.default \
    audio.r_submix.default

PRODUCT_PROPERTY_OVERRIDES += \
    config.disable_audio=false

EOF
    print_success "Audio support: ENABLED"
else
    cat >> "${PRODUCT_MK}" << 'EOF'

# Audio support MINIMAL
PRODUCT_PACKAGES += \
    audio.primary.msmnile

PRODUCT_PROPERTY_OVERRIDES += \
    config.disable_audio=false \
    ro.audio.silent=1

EOF
    print_warning "Audio support: MINIMAL"
fi

# Add Bluetooth configuration
if [[ "$ENABLE_BT" =~ ^[Yy]$ ]]; then
    cat >> "${PRODUCT_MK}" << 'EOF'

# Bluetooth ENABLED
PRODUCT_PACKAGES += \
    android.hardware.bluetooth@1.0-impl \
    android.hardware.bluetooth@1.0-service

PRODUCT_PROPERTY_OVERRIDES += \
    config.disable_bluetooth=false

EOF
    print_success "Bluetooth: ENABLED"
else
    cat >> "${PRODUCT_MK}" << 'EOF'

# Bluetooth DISABLED
PRODUCT_PROPERTY_OVERRIDES += \
    config.disable_bluetooth=true

EOF
    print_warning "Bluetooth: DISABLED"
fi

# Add NFC configuration
if [[ "$ENABLE_NFC" =~ ^[Yy]$ ]]; then
    cat >> "${PRODUCT_MK}" << 'EOF'

# NFC ENABLED
PRODUCT_PACKAGES += \
    NfcNci \
    Tag

PRODUCT_COPY_FILES += \
    frameworks/native/data/etc/android.hardware.nfc.xml:$(TARGET_COPY_OUT_VENDOR)/etc/permissions/android.hardware.nfc.xml \
    frameworks/native/data/etc/android.hardware.nfc.hce.xml:$(TARGET_COPY_OUT_VENDOR)/etc/permissions/android.hardware.nfc.hce.xml

EOF
    print_success "NFC: ENABLED"
else
    print_warning "NFC: DISABLED"
fi

print_success "Minimal product makefile created: aosp_r3q_minimal.mk"

# Update AndroidProducts.mk
print_status "Updating AndroidProducts.mk..."

if [ -f "${DEVICE_DIR}/AndroidProducts.mk" ]; then
    # Backup original
    cp "${DEVICE_DIR}/AndroidProducts.mk" "${DEVICE_DIR}/AndroidProducts.mk.bak"

    # Check if our product is already added
    if grep -q "aosp_r3q_minimal.mk" "${DEVICE_DIR}/AndroidProducts.mk"; then
        print_success "AndroidProducts.mk already includes minimal build"
    else
        # Add our product
        cat >> "${DEVICE_DIR}/AndroidProducts.mk" << 'EOF'

# Minimal AOSP build
PRODUCT_MAKEFILES += \
    $(LOCAL_DIR)/aosp_r3q_minimal.mk

COMMON_LUNCH_CHOICES += \
    aosp_r3q_minimal-eng \
    aosp_r3q_minimal-userdebug \
    aosp_r3q_minimal-user

EOF
        print_success "AndroidProducts.mk updated"
    fi
else
    # Create new AndroidProducts.mk
    cat > "${DEVICE_DIR}/AndroidProducts.mk" << 'EOF'
#
# Copyright (C) 2024 The AOSP Project
#
# SPDX-License-Identifier: Apache-2.0
#

PRODUCT_MAKEFILES := \
    $(LOCAL_DIR)/lineage_r3q.mk \
    $(LOCAL_DIR)/aosp_r3q_minimal.mk

COMMON_LUNCH_CHOICES := \
    aosp_r3q_minimal-eng \
    aosp_r3q_minimal-userdebug \
    aosp_r3q_minimal-user

EOF
    print_success "AndroidProducts.mk created"
fi

# Create build configuration file
CONFIG_FILE="${DEVICE_DIR}/minimal_build_config.txt"
cat > "${CONFIG_FILE}" << EOF
AOSP Minimal Build Configuration
=================================
Generated: $(date)

Build Options:
--------------
Camera:    $(if [[ "$ENABLE_CAMERA" =~ ^[Yy]$ ]]; then echo "ENABLED"; else echo "DISABLED"; fi)
Audio:     $(if [[ "$ENABLE_AUDIO" =~ ^[Yy]$ ]]; then echo "ENABLED"; else echo "MINIMAL"; fi)
Bluetooth: $(if [[ "$ENABLE_BT" =~ ^[Yy]$ ]]; then echo "ENABLED"; else echo "DISABLED"; fi)
NFC:       $(if [[ "$ENABLE_NFC" =~ ^[Yy]$ ]]; then echo "ENABLED"; else echo "DISABLED"; fi)

Expected RAM Usage:
-------------------
Base system:        ~800-900 MB
WiFi/Networking:    ~100 MB
Camera (if enabled): ~150 MB
Audio (if enabled):  ~80 MB
Bluetooth (if enabled): ~50 MB
Total estimated:    ~1.0-1.3 GB

Build Commands:
---------------
cd ${AOSP_DIR}
source build/envsetup.sh
lunch aosp_r3q_minimal-userdebug
mka bacon -j\$(nproc)

Build Variants:
---------------
- aosp_r3q_minimal-eng        (Engineering build, root by default)
- aosp_r3q_minimal-userdebug  (User-debug, routable)
- aosp_r3q_minimal-user       (Production build, secure)

Recommended: userdebug
EOF

print_success "Build configuration saved to: minimal_build_config.txt"

# Summary
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Configuration Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BLUE}Build Configuration:${NC}"
echo -e "  Camera:    $(if [[ "$ENABLE_CAMERA" =~ ^[Yy]$ ]]; then echo -e "${GREEN}ENABLED${NC}"; else echo -e "${YELLOW}DISABLED${NC}"; fi)"
echo -e "  Audio:     $(if [[ "$ENABLE_AUDIO" =~ ^[Yy]$ ]]; then echo -e "${GREEN}ENABLED${NC}"; else echo -e "${YELLOW}MINIMAL${NC}"; fi)"
echo -e "  Bluetooth: $(if [[ "$ENABLE_BT" =~ ^[Yy]$ ]]; then echo -e "${GREEN}ENABLED${NC}"; else echo -e "${YELLOW}DISABLED${NC}"; fi)"
echo -e "  NFC:       $(if [[ "$ENABLE_NFC" =~ ^[Yy]$ ]]; then echo -e "${GREEN}ENABLED${NC}"; else echo -e "${YELLOW}DISABLED${NC}"; fi)"
echo ""
echo -e "${BLUE}Files Created:${NC}"
echo -e "  Product:   aosp_r3q_minimal.mk"
echo -e "  Config:    minimal_build_config.txt"
echo ""
echo -e "${BLUE}Next Steps:${NC}"
echo -e "  1. Review configuration: ${YELLOW}cat minimal_build_config.txt${NC}"
echo -e "  2. Run: ${YELLOW}./06_build_aosp.sh${NC}"
echo -e "  3. Build time: 3-6 hours (first build)"
echo ""
