#!/bin/bash
################################################################################
# Flash and Test Script
# Samsung Galaxy A90 5G (r3q) - Option C: Minimal AOSP Build
#
# This script helps flash and test the AOSP build safely
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
echo -e "${BLUE}Flash and Test AOSP Build${NC}"
echo -e "${BLUE}Samsung Galaxy A90 5G (r3q)${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Configuration
AOSP_DIR="${HOME}/aosp/r3q"
OUT_DIR="${AOSP_DIR}/out/target/product/r3q"
BACKUP_DIR="${HOME}/aosp_backups"

# Verify build output exists
if [ ! -d "${OUT_DIR}" ]; then
    print_error "Build output not found at ${OUT_DIR}"
    print_error "Please run ./06_build_aosp.sh first"
    exit 1
fi

cd "${OUT_DIR}"

# Find boot.img
if [ ! -f "boot.img" ]; then
    print_error "boot.img not found in ${OUT_DIR}"
    exit 1
fi

# Safety warnings
echo -e "${RED}========================================${NC}"
echo -e "${RED}        IMPORTANT WARNINGS!${NC}"
echo -e "${RED}========================================${NC}"
echo ""
echo -e "${YELLOW}Before proceeding:${NC}"
echo "  1. Make FULL TWRP backup (boot + system + vendor + data)"
echo "  2. Ensure you have stock firmware downloaded"
echo "  3. Battery should be >60%"
echo "  4. Have ODIN ready (for emergency recovery)"
echo ""
echo -e "${YELLOW}Risks:${NC}"
echo "  - Device may not boot (5-10% risk)"
echo "  - May need to restore from backup"
echo "  - Knox warranty bit will trip (if not already)"
echo ""

read -p "Have you made a FULL TWRP backup? [y/N]: " BACKUP_CONFIRM
if [[ ! "$BACKUP_CONFIRM" =~ ^[Yy]$ ]]; then
    print_error "Please make a full backup first!"
    print_status "Boot to TWRP → Backup → Select all partitions → Swipe to backup"
    exit 1
fi

# Flash method selection
echo ""
echo -e "${YELLOW}Select flash method:${NC}"
echo "  1) Test boot only (safest - non-permanent)"
echo "  2) Flash via DD (Samsung method, proven in Phase 2)"
echo "  3) Flash via Fastboot (if available)"
echo "  4) Create flashable ZIP for TWRP"
echo "  5) Cancel"
echo ""
read -p "Enter choice [1-5]: " FLASH_METHOD

case $FLASH_METHOD in
    1)
        print_status "Test boot mode (non-permanent)"
        echo ""
        print_warning "This will temporarily boot AOSP without installing"
        print_warning "If it fails, device will reboot to current system"
        echo ""

        # Check if fastboot is available
        if ! command -v fastboot &> /dev/null; then
            print_error "Fastboot not installed!"
            print_status "Install: sudo apt install fastboot"
            exit 1
        fi

        # Check device connection
        print_status "Waiting for device in fastboot mode..."
        print_status "Put device in download/fastboot mode:"
        print_status "  Power off → Hold Power + Vol Down + Vol Up"
        echo ""

        read -p "Press Enter when device is in download mode..."

        fastboot devices
        if [ $? -ne 0 ]; then
            print_error "Fastboot device not detected!"
            exit 1
        fi

        print_status "Testing boot with AOSP boot.img..."
        fastboot boot boot.img

        print_success "Boot command sent!"
        print_status "Device should boot into AOSP now (may take 5-10 minutes)"
        print_status "If successful, reboot to make permanent via method 2 or 3"
        ;;

    2)
        print_status "Flash via DD (Samsung method)"
        echo ""
        print_warning "This will PERMANENTLY flash AOSP boot image"
        print_warning "System and vendor images will be flashed via TWRP"
        echo ""

        read -p "Continue with DD flash? [y/N]: " DD_CONFIRM
        if [[ ! "$DD_CONFIRM" =~ ^[Yy]$ ]]; then
            print_status "Flash cancelled"
            exit 0
        fi

        # Check ADB connection
        if ! command -v adb &> /dev/null; then
            print_error "ADB not installed!"
            exit 1
        fi

        print_status "Waiting for device..."
        adb wait-for-device

        # Get root
        adb root
        sleep 2
        adb wait-for-device

        # Create backup directory
        mkdir -p "${BACKUP_DIR}"
        BACKUP_FILE="${BACKUP_DIR}/stock_boot_$(date +%Y%m%d_%H%M%S).img"

        # Backup current boot
        print_status "Backing up current boot partition..."
        adb shell "su -c 'dd if=/dev/block/by-name/boot of=/sdcard/current_boot.img bs=4096'"
        adb pull /sdcard/current_boot.img "${BACKUP_FILE}"
        print_success "Boot backup saved: ${BACKUP_FILE}"

        # Push new boot.img
        print_status "Pushing AOSP boot.img to device..."
        adb push boot.img /sdcard/aosp_boot.img

        # Flash boot
        print_status "Flashing AOSP boot partition..."
        adb shell "su -c 'dd if=/sdcard/aosp_boot.img of=/dev/block/by-name/boot bs=4096'"

        if [ $? -eq 0 ]; then
            print_success "Boot partition flashed successfully!"

            # Flash system and vendor via TWRP
            echo ""
            print_status "Now flash system.img and vendor.img via TWRP:"
            print_status "  1. Reboot to TWRP recovery"
            print_status "  2. Install → Install Image"
            print_status "  3. Select system.img → Flash to System partition"
            print_status "  4. Select vendor.img → Flash to Vendor partition"
            print_status "  5. Wipe cache and dalvik"
            print_status "  6. Reboot system"
            echo ""

            read -p "Reboot to TWRP now? [y/N]: " REBOOT_TWRP
            if [[ "$REBOOT_TWRP" =~ ^[Yy]$ ]]; then
                adb reboot recovery
                print_status "Device rebooting to TWRP..."
            fi
        else
            print_error "Failed to flash boot partition!"
            print_status "Restoring backup..."
            adb push "${BACKUP_FILE}" /sdcard/restore_boot.img
            adb shell "su -c 'dd if=/sdcard/restore_boot.img of=/dev/block/by-name/boot bs=4096'"
            exit 1
        fi
        ;;

    3)
        print_status "Flash via Fastboot"
        echo ""
        print_warning "This will PERMANENTLY flash all partitions"
        echo ""

        read -p "Continue with fastboot flash? [y/N]: " FB_CONFIRM
        if [[ ! "$FB_CONFIRM" =~ ^[Yy]$ ]]; then
            print_status "Flash cancelled"
            exit 0
        fi

        # Check fastboot
        if ! command -v fastboot &> /dev/null; then
            print_error "Fastboot not installed!"
            exit 1
        fi

        print_status "Put device in download/fastboot mode"
        read -p "Press Enter when ready..."

        # Flash partitions
        print_status "Flashing boot partition..."
        fastboot flash boot boot.img

        if [ -f "system.img" ]; then
            print_status "Flashing system partition..."
            fastboot flash system system.img
        fi

        if [ -f "vendor.img" ]; then
            print_status "Flashing vendor partition..."
            fastboot flash vendor vendor.img
        fi

        print_status "Rebooting device..."
        fastboot reboot

        print_success "Flash complete! Device rebooting..."
        ;;

    4)
        print_status "Creating flashable ZIP for TWRP"
        echo ""

        # Check if ZIP already exists
        ZIP_FILE=$(ls -t aosp_r3q_minimal*.zip 2>/dev/null | head -1)

        if [ -n "$ZIP_FILE" ]; then
            print_success "Flashable ZIP already exists: ${ZIP_FILE}"
            ZIP_SIZE=$(du -h "${ZIP_FILE}" | cut -f1)
            print_status "Size: ${ZIP_SIZE}"
        else
            print_warning "Flashable ZIP not found in build output"
            print_status "Building flashable package..."

            # This would require creating META-INF structure
            print_error "ZIP creation not implemented in this script"
            print_status "Use TWRP Install Image method instead"
            exit 1
        fi

        echo ""
        print_status "To flash via TWRP:"
        print_status "  1. Copy ${ZIP_FILE} to device"
        print_status "  2. Boot to TWRP recovery"
        print_status "  3. Install → Select ZIP"
        print_status "  4. Swipe to flash"
        print_status "  5. Reboot system"
        echo ""

        read -p "Copy ZIP to device now? [y/N]: " COPY_ZIP
        if [[ "$COPY_ZIP" =~ ^[Yy]$ ]]; then
            if ! command -v adb &> /dev/null; then
                print_error "ADB not installed!"
                exit 1
            fi

            adb wait-for-device
            print_status "Pushing ZIP to device..."
            adb push "${ZIP_FILE}" /sdcard/
            print_success "ZIP copied to /sdcard/${ZIP_FILE}"
            print_status "Now reboot to TWRP and flash"
        fi
        ;;

    5)
        print_status "Flash cancelled"
        exit 0
        ;;

    *)
        print_error "Invalid choice"
        exit 1
        ;;
esac

# Post-flash verification
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Flash Complete${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BLUE}What to expect:${NC}"
echo "  - First boot may take 5-10 minutes"
echo "  - Setup wizard will appear (skip it)"
echo "  - Check WiFi, storage, basic functions"
echo ""
echo -e "${BLUE}Verification steps:${NC}"
echo "  1. Wait for boot (patience!)"
echo "  2. ${YELLOW}adb shell getprop ro.build.version.release${NC}  # Check Android version"
echo "  3. ${YELLOW}adb shell getprop ro.product.model${NC}  # Check model"
echo "  4. ${YELLOW}adb shell dumpsys meminfo | grep 'Total RAM'${NC}  # Check RAM usage"
echo "  5. ${YELLOW}adb shell svc wifi enable${NC}  # Test WiFi"
echo ""
echo -e "${BLUE}If boot fails:${NC}"
echo "  1. Wait 10 minutes (patience is key!)"
echo "  2. Check ${YELLOW}adb logcat${NC} for errors"
echo "  3. Reboot to TWRP and restore backup"
echo "  4. Flash stock firmware via ODIN if needed"
echo ""
echo -e "${YELLOW}Recovery files location:${NC}"
echo "  Backup: ${BACKUP_DIR}"
echo "  Stock firmware: Download from SamFW.com (SM-A908N)"
echo ""
