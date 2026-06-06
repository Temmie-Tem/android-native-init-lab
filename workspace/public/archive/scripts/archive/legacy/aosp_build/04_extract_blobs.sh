#!/bin/bash
################################################################################
# Proprietary Blob Extraction Script
# Samsung Galaxy A90 5G (r3q) - Option C: Minimal AOSP Build
#
# This script extracts proprietary vendor files from the device
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
echo -e "${BLUE}Proprietary Blob Extraction${NC}"
echo -e "${BLUE}Samsung Galaxy A90 5G (r3q)${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Configuration
AOSP_DIR="${HOME}/aosp/r3q"
DEVICE_DIR="${AOSP_DIR}/device/samsung/r3q"
VENDOR_DIR="${AOSP_DIR}/vendor/samsung/r3q"

# Verify device tree exists
if [ ! -d "${DEVICE_DIR}" ]; then
    print_error "Device tree not found at ${DEVICE_DIR}"
    print_error "Please run ./03_setup_device_tree.sh first"
    exit 1
fi

cd "${DEVICE_DIR}"

# Check if extract-files.sh exists
if [ ! -f "extract-files.sh" ]; then
    print_error "extract-files.sh not found in device tree!"
    print_error "This script is required to extract vendor blobs"
    exit 1
fi

# Make sure it's executable
chmod +x extract-files.sh

# Check extraction method
echo -e "${YELLOW}Select extraction method:${NC}"
echo "  1) Extract from connected device (ADB) - Recommended"
echo "  2) Extract from system dump directory"
echo "  3) Skip extraction (use existing vendor files)"
echo ""
read -p "Enter choice [1-3]: " METHOD

case $METHOD in
    1)
        print_status "Extracting from connected device via ADB..."

        # Check ADB connection
        if ! command -v adb &> /dev/null; then
            print_error "ADB not found! Please install android-tools-adb"
            exit 1
        fi

        # Wait for device
        print_status "Waiting for device..."
        adb wait-for-device

        # Check if device is authorized
        DEVICE_STATE=$(adb get-state 2>&1)
        if [ "$DEVICE_STATE" != "device" ]; then
            print_error "Device not authorized or not connected properly"
            print_error "Please check USB debugging and authorize this computer"
            exit 1
        fi

        # Get device info
        DEVICE_MODEL=$(adb shell getprop ro.product.model | tr -d '\r')
        DEVICE_CODENAME=$(adb shell getprop ro.product.device | tr -d '\r')
        ANDROID_VERSION=$(adb shell getprop ro.build.version.release | tr -d '\r')

        print_success "Device connected: ${DEVICE_MODEL} (${DEVICE_CODENAME})"
        print_status "Android version: ${ANDROID_VERSION}"

        # Verify it's r3q
        if [[ "$DEVICE_CODENAME" != "r3q"* ]]; then
            print_warning "Device codename is '${DEVICE_CODENAME}', expected 'r3q'"
            read -p "Continue anyway? [y/N]: " CONTINUE
            if [[ ! "$CONTINUE" =~ ^[Yy]$ ]]; then
                exit 1
            fi
        fi

        # Check root access
        print_status "Checking root access..."
        adb root 2>&1
        sleep 2
        adb wait-for-device

        ROOT_CHECK=$(adb shell "su -c 'echo test'" 2>&1 | tr -d '\r')
        if [[ "$ROOT_CHECK" == *"not found"* ]] || [[ "$ROOT_CHECK" == *"Permission denied"* ]]; then
            print_warning "Root access not available"
            print_warning "Some files may not be extractable without root"
            read -p "Continue without root? [y/N]: " CONTINUE
            if [[ ! "$CONTINUE" =~ ^[Yy]$ ]]; then
                exit 1
            fi
        else
            print_success "Root access available"
        fi

        # Run extraction
        print_status "Starting blob extraction..."
        print_warning "This may take 5-10 minutes depending on device"
        echo ""

        ./extract-files.sh

        ;;

    2)
        print_status "Extracting from system dump directory..."
        echo ""
        echo -e "${YELLOW}Please enter the path to system dump directory:${NC}"
        echo "  (Should contain: system/, vendor/, product/ directories)"
        read -p "Path: " DUMP_PATH

        if [ ! -d "$DUMP_PATH" ]; then
            print_error "Directory not found: $DUMP_PATH"
            exit 1
        fi

        print_status "Extracting from: $DUMP_PATH"
        ./extract-files.sh "$DUMP_PATH"

        ;;

    3)
        print_status "Skipping extraction"

        if [ -d "${VENDOR_DIR}" ]; then
            print_success "Existing vendor files found at ${VENDOR_DIR}"
        else
            print_warning "No vendor files found!"
            print_warning "Build may fail without vendor blobs"
        fi

        exit 0
        ;;

    *)
        print_error "Invalid choice"
        exit 1
        ;;
esac

# Check if extraction was successful
if [ $? -eq 0 ]; then
    print_success "Blob extraction completed!"
else
    print_error "Blob extraction failed!"
    exit 1
fi

# Verify vendor directory
if [ -d "${VENDOR_DIR}" ]; then
    VENDOR_SIZE=$(du -sh "${VENDOR_DIR}" | cut -f1)
    print_success "Vendor directory created: ${VENDOR_DIR}"
    print_status "Vendor files size: ${VENDOR_SIZE}"
else
    print_warning "Vendor directory not created"
    print_warning "Check if extract-files.sh completed successfully"
fi

# Check important blobs
print_status "Verifying critical vendor files..."

check_blob() {
    local BLOB_PATH="$1"
    local BLOB_DESC="$2"

    if [ -f "${VENDOR_DIR}/proprietary/${BLOB_PATH}" ] || [ -d "${VENDOR_DIR}/proprietary/${BLOB_PATH}" ]; then
        print_success "${BLOB_DESC}: Found"
        return 0
    else
        print_warning "${BLOB_DESC}: Missing"
        return 1
    fi
}

echo ""
print_status "WiFi blobs (REQUIRED):"
check_blob "vendor/firmware/wlan" "WiFi firmware"

echo ""
print_status "GPU blobs (REQUIRED):"
check_blob "vendor/lib/egl/libEGL_adreno.so" "Adreno EGL library"
check_blob "vendor/lib/egl/libGLESv2_adreno.so" "Adreno GLES library"

echo ""
print_status "Camera blobs (OPTIONAL - for Option C):"
check_blob "vendor/bin/mm-qcamera-daemon" "Camera daemon"
check_blob "vendor/lib/libmmcamera_interface.so" "Camera interface"

echo ""
print_status "Audio blobs (OPTIONAL - for Option C):"
check_blob "vendor/lib/audio.primary.msmnile.so" "Audio HAL"

# List all extracted files
BLOB_COUNT=$(find "${VENDOR_DIR}/proprietary" -type f 2>/dev/null | wc -l)
print_status "Total blobs extracted: ${BLOB_COUNT} files"

# Summary
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Blob Extraction Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BLUE}Vendor Information:${NC}"
echo -e "  Location: ${VENDOR_DIR}"
echo -e "  Size:     ${VENDOR_SIZE}"
echo -e "  Files:    ${BLOB_COUNT}"
echo ""
echo -e "${BLUE}Next Steps:${NC}"
echo -e "  1. Run: ${YELLOW}./05_configure_minimal.sh${NC}"
echo -e "  2. This will create minimal build configuration"
echo -e "  3. You can enable/disable Camera and Audio"
echo ""
