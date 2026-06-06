#!/bin/bash
################################################################################
# Device Tree Setup Script
# Samsung Galaxy A90 5G (r3q) - Option C: Minimal AOSP Build
#
# This script clones the device tree, common files, kernel, and vendor repos
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
echo -e "${BLUE}Device Tree Setup${NC}"
echo -e "${BLUE}Samsung Galaxy A90 5G (r3q)${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Configuration
AOSP_DIR="${HOME}/aosp/r3q"
DEVICE_DIR="${AOSP_DIR}/device/samsung"
VENDOR_DIR="${AOSP_DIR}/vendor/samsung"
KERNEL_DIR="${AOSP_DIR}/kernel/samsung"

# Repository URLs
R3Q_DEVICE_REPO="https://github.com/Roynas-Android-Playground/device_samsung_r3q.git"
SM8150_COMMON_REPO="https://github.com/LineageOS/android_device_samsung_sm8150-common.git"
KERNEL_REPO="https://github.com/LineageOS/android_kernel_samsung_sm8150.git"

# Branches
DEVICE_BRANCH="lineage-20"  # Android 13
COMMON_BRANCH="lineage-20"
KERNEL_BRANCH="lineage-20"

# Verify AOSP source exists
if [ ! -d "${AOSP_DIR}/.repo" ]; then
    print_error "AOSP source not found at ${AOSP_DIR}"
    print_error "Please run ./02_download_source.sh first"
    exit 1
fi

cd "${AOSP_DIR}"

# Create directories
print_status "Creating device tree directories..."
mkdir -p "${DEVICE_DIR}"
mkdir -p "${VENDOR_DIR}"
mkdir -p "${KERNEL_DIR}"

# Clone r3q device tree
print_status "Cloning r3q device tree..."
if [ -d "${DEVICE_DIR}/r3q" ]; then
    print_warning "Device tree already exists at ${DEVICE_DIR}/r3q"
    read -p "Remove and re-clone? [y/N]: " RECLONE
    if [[ "$RECLONE" =~ ^[Yy]$ ]]; then
        rm -rf "${DEVICE_DIR}/r3q"
    else
        print_status "Keeping existing device tree"
    fi
fi

if [ ! -d "${DEVICE_DIR}/r3q" ]; then
    print_status "Cloning from ${R3Q_DEVICE_REPO}..."
    git clone -b "${DEVICE_BRANCH}" "${R3Q_DEVICE_REPO}" "${DEVICE_DIR}/r3q"
    print_success "r3q device tree cloned"
else
    print_success "r3q device tree already present"
fi

# Clone SM8150 common files
print_status "Cloning SM8150 common platform files..."
if [ -d "${DEVICE_DIR}/sm8150-common" ]; then
    print_warning "SM8150 common files already exist"
else
    print_status "Cloning from ${SM8150_COMMON_REPO}..."
    git clone -b "${COMMON_BRANCH}" "${SM8150_COMMON_REPO}" "${DEVICE_DIR}/sm8150-common"
    print_success "SM8150 common files cloned"
fi

# Clone or copy kernel
print_status "Setting up kernel source..."

# Check if we should use existing kernel from Phase 2-2
LOCAL_KERNEL_PATH="/home/temmie/A90_5G_rooting/archive/phase0_native_boot_research/kernel_build/SM-A908N_KOR_12_Opensource"

if [ -d "${LOCAL_KERNEL_PATH}" ]; then
    echo ""
    echo -e "${YELLOW}Kernel source options:${NC}"
    echo "  1) Use existing Samsung kernel from Phase 2-2 (already built)"
    echo "  2) Clone LineageOS kernel (recommended for AOSP)"
    echo "  3) Skip kernel setup (use prebuilt)"
    echo ""
    read -p "Enter choice [1-3]: " KERNEL_CHOICE

    case $KERNEL_CHOICE in
        1)
            print_status "Copying Samsung kernel from Phase 2-2..."
            if [ ! -d "${KERNEL_DIR}/sm8150" ]; then
                cp -r "${LOCAL_KERNEL_PATH}" "${KERNEL_DIR}/sm8150"
                print_success "Samsung kernel copied"
            else
                print_warning "Kernel directory already exists, skipping copy"
            fi
            ;;
        2)
            if [ ! -d "${KERNEL_DIR}/sm8150" ]; then
                print_status "Cloning LineageOS kernel..."
                git clone -b "${KERNEL_BRANCH}" "${KERNEL_REPO}" "${KERNEL_DIR}/sm8150"
                print_success "LineageOS kernel cloned"
            else
                print_warning "Kernel directory already exists"
            fi
            ;;
        3)
            print_status "Skipping kernel setup (will use prebuilt)"
            ;;
        *)
            print_error "Invalid choice"
            exit 1
            ;;
    esac
else
    # No local kernel found, clone from LineageOS
    if [ ! -d "${KERNEL_DIR}/sm8150" ]; then
        print_status "Cloning LineageOS kernel..."
        git clone -b "${KERNEL_BRANCH}" "${KERNEL_REPO}" "${KERNEL_DIR}/sm8150"
        print_success "LineageOS kernel cloned"
    else
        print_warning "Kernel directory already exists"
    fi
fi

# Check for vendor files repository
print_status "Checking for vendor blobs repository..."
VENDOR_REPO_URL="https://github.com/TheMuppets/proprietary_vendor_samsung"
VENDOR_REPO_BRANCH="lineage-20"

echo ""
echo -e "${YELLOW}Vendor blobs options:${NC}"
echo "  1) Clone from TheMuppets (community vendor repo)"
echo "  2) Extract from device later (recommended)"
echo "  3) Skip (will extract manually)"
echo ""
read -p "Enter choice [1-3]: " VENDOR_CHOICE

case $VENDOR_CHOICE in
    1)
        if [ ! -d "${VENDOR_DIR}/r3q" ]; then
            print_status "Cloning vendor repository..."
            git clone -b "${VENDOR_REPO_BRANCH}" "${VENDOR_REPO_URL}" "${VENDOR_DIR}/temp"
            if [ -d "${VENDOR_DIR}/temp/r3q" ]; then
                mv "${VENDOR_DIR}/temp/r3q" "${VENDOR_DIR}/r3q"
                rm -rf "${VENDOR_DIR}/temp"
                print_success "Vendor blobs cloned"
            else
                print_warning "r3q vendor files not found in repository"
                rm -rf "${VENDOR_DIR}/temp"
                print_status "You'll need to extract vendor blobs manually"
            fi
        else
            print_warning "Vendor directory already exists"
        fi
        ;;
    2)
        print_status "Vendor blobs will be extracted in the next step"
        ;;
    3)
        print_status "Skipping vendor setup (extract manually later)"
        ;;
    *)
        print_error "Invalid choice"
        exit 1
        ;;
esac

# Create local manifest for easier repo sync
print_status "Creating local manifest..."
mkdir -p "${AOSP_DIR}/.repo/local_manifests"

cat > "${AOSP_DIR}/.repo/local_manifests/r3q.xml" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<manifest>
    <!-- Samsung Galaxy A90 5G (r3q) -->
    <project name="Roynas-Android-Playground/device_samsung_r3q"
             path="device/samsung/r3q"
             remote="github"
             revision="${DEVICE_BRANCH}" />

    <project name="LineageOS/android_device_samsung_sm8150-common"
             path="device/samsung/sm8150-common"
             remote="github"
             revision="${COMMON_BRANCH}" />

    <project name="LineageOS/android_kernel_samsung_sm8150"
             path="kernel/samsung/sm8150"
             remote="github"
             revision="${KERNEL_BRANCH}" />
</manifest>
EOF

print_success "Local manifest created at .repo/local_manifests/r3q.xml"

# Verify device tree structure
print_status "Verifying device tree structure..."

check_file() {
    if [ -f "$1" ]; then
        print_success "Found: $1"
        return 0
    else
        print_warning "Missing: $1"
        return 1
    fi
}

echo ""
print_status "Checking essential files..."

check_file "${DEVICE_DIR}/r3q/Android.mk"
check_file "${DEVICE_DIR}/r3q/BoardConfig.mk"
check_file "${DEVICE_DIR}/r3q/device.mk"
check_file "${DEVICE_DIR}/r3q/lineage_r3q.mk"

if [ -f "${DEVICE_DIR}/r3q/extract-files.sh" ]; then
    print_success "Found: extract-files.sh (for vendor blob extraction)"
else
    print_warning "extract-files.sh not found"
fi

# Summary
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Device Tree Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BLUE}Directory Structure:${NC}"
echo -e "  Device:  ${DEVICE_DIR}/r3q"
echo -e "  Common:  ${DEVICE_DIR}/sm8150-common"
echo -e "  Kernel:  ${KERNEL_DIR}/sm8150"
echo -e "  Vendor:  ${VENDOR_DIR}/r3q"
echo ""

# Check sizes
if [ -d "${DEVICE_DIR}/r3q" ]; then
    DEVICE_SIZE=$(du -sh "${DEVICE_DIR}/r3q" 2>/dev/null | cut -f1)
    echo -e "  Device tree size: ${DEVICE_SIZE}"
fi

if [ -d "${KERNEL_DIR}/sm8150" ]; then
    KERNEL_SIZE=$(du -sh "${KERNEL_DIR}/sm8150" 2>/dev/null | cut -f1)
    echo -e "  Kernel size: ${KERNEL_SIZE}"
fi

echo ""
echo -e "${BLUE}Next Steps:${NC}"
echo -e "  1. Run: ${YELLOW}./04_extract_blobs.sh${NC}"
echo -e "  2. Connect your Samsung A90 5G device via USB"
echo -e "  3. Enable USB debugging and ADB root access"
echo ""
