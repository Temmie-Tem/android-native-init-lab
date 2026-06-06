#!/bin/bash
################################################################################
# AOSP Build Script
# Samsung Galaxy A90 5G (r3q) - Option C: Minimal AOSP Build
#
# This script compiles the AOSP ROM
# Estimated time: 3-6 hours (first build), 30-60 min (incremental)
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
echo -e "${BLUE}AOSP Build${NC}"
echo -e "${BLUE}Samsung Galaxy A90 5G (r3q)${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Configuration
AOSP_DIR="${HOME}/aosp/r3q"
LOG_DIR="${AOSP_DIR}/build_logs"
BUILD_DATE=$(date +%Y%m%d_%H%M%S)
LOG_FILE="${LOG_DIR}/build_${BUILD_DATE}.log"

# Verify AOSP source
if [ ! -d "${AOSP_DIR}/.repo" ]; then
    print_error "AOSP source not found at ${AOSP_DIR}"
    print_error "Please run ./02_download_source.sh first"
    exit 1
fi

cd "${AOSP_DIR}"

# Create log directory
mkdir -p "${LOG_DIR}"

# Build type selection
echo -e "${YELLOW}Select build variant:${NC}"
echo "  1) aosp_r3q_minimal-userdebug (Recommended - debuggable, routable)"
echo "  2) aosp_r3q_minimal-eng (Engineering - root by default, verbose logging)"
echo "  3) aosp_r3q_minimal-user (Production - secure, no root)"
echo ""
read -p "Enter choice [1-3]: " VARIANT_CHOICE

case $VARIANT_CHOICE in
    1)
        BUILD_VARIANT="aosp_r3q_minimal-userdebug"
        ;;
    2)
        BUILD_VARIANT="aosp_r3q_minimal-eng"
        ;;
    3)
        BUILD_VARIANT="aosp_r3q_minimal-user"
        ;;
    *)
        print_error "Invalid choice"
        exit 1
        ;;
esac

print_status "Selected: ${BUILD_VARIANT}"

# Build options
echo ""
echo -e "${YELLOW}Build options:${NC}"
read -p "Clean build? (slower but safer) [y/N]: " CLEAN_BUILD
CLEAN_BUILD=${CLEAN_BUILD:-N}

echo ""
echo -e "${YELLOW}CPU cores to use:${NC}"
CPU_CORES=$(nproc --all)
echo "  Available: ${CPU_CORES} cores"
read -p "Use all ${CPU_CORES} cores? [Y/n]: " USE_ALL_CORES
USE_ALL_CORES=${USE_ALL_CORES:-Y}

if [[ "$USE_ALL_CORES" =~ ^[Yy]$ ]]; then
    JOBS=${CPU_CORES}
else
    read -p "Enter number of cores to use [1-${CPU_CORES}]: " JOBS
    if [ "$JOBS" -gt "$CPU_CORES" ] || [ "$JOBS" -lt 1 ]; then
        print_warning "Invalid input, using half of available cores"
        JOBS=$((CPU_CORES / 2))
    fi
fi

print_status "Using ${JOBS} parallel jobs"

# Pre-build checks
echo ""
print_status "Running pre-build checks..."

# Check disk space
AVAILABLE_SPACE=$(df -BG "${AOSP_DIR}" | awk 'NR==2 {print $4}' | sed 's/G//')
print_status "Available disk space: ${AVAILABLE_SPACE}GB"
if [ "$AVAILABLE_SPACE" -lt 100 ]; then
    print_error "Less than 100GB free space!"
    print_error "Build may fail. Please free up disk space."
    exit 1
fi

# Check RAM
TOTAL_RAM=$(free -g | awk '/^Mem:/{print $2}')
print_status "Total RAM: ${TOTAL_RAM}GB"
if [ "$TOTAL_RAM" -lt 16 ]; then
    print_warning "Less than 16GB RAM. Build may be slow."
    print_warning "Consider reducing parallel jobs."
fi

# Setup build environment
print_status "Setting up build environment..."

# Enable ccache
export USE_CCACHE=1
export CCACHE_EXEC=/usr/bin/ccache
export CCACHE_DIR="${HOME}/.ccache"

# Check ccache stats
if command -v ccache &> /dev/null; then
    CCACHE_SIZE=$(ccache -s | grep "cache size" | awk '{print $3, $4}')
    print_status "ccache size: ${CCACHE_SIZE}"
fi

# Source build environment
print_status "Sourcing build environment..."
source build/envsetup.sh

if [ $? -ne 0 ]; then
    print_error "Failed to source build environment!"
    exit 1
fi

# Select lunch target
print_status "Selecting build target: ${BUILD_VARIANT}"
lunch "${BUILD_VARIANT}"

if [ $? -ne 0 ]; then
    print_error "Failed to lunch ${BUILD_VARIANT}"
    print_error "Make sure you ran ./05_configure_minimal.sh"
    exit 1
fi

# Clean build if requested
if [[ "$CLEAN_BUILD" =~ ^[Yy]$ ]]; then
    print_warning "Performing clean build (this will take longer)..."
    mka clean
fi

# Start build
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Starting Build${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BLUE}Build Information:${NC}"
echo -e "  Variant:      ${BUILD_VARIANT}"
echo -e "  Parallel Jobs: ${JOBS}"
echo -e "  Clean Build:  $(if [[ "$CLEAN_BUILD" =~ ^[Yy]$ ]]; then echo "YES"; else echo "NO"; fi)"
echo -e "  Log File:     ${LOG_FILE}"
echo ""
echo -e "${YELLOW}Estimated time:${NC}"
echo -e "  First build:  3-6 hours"
echo -e "  Incremental:  30-60 minutes"
echo ""

read -p "Press Enter to start build..."

START_TIME=$(date +%s)

print_status "Build started at $(date)"
print_status "Logging to: ${LOG_FILE}"
echo ""

# Build command
if [ -f "vendor/lineage/build/envsetup.sh" ]; then
    # LineageOS build command
    print_status "Using LineageOS build system..."
    brunch r3q 2>&1 | tee "${LOG_FILE}"
    BUILD_RESULT=${PIPESTATUS[0]}
else
    # Standard AOSP build
    print_status "Using AOSP build system..."
    mka bacon -j${JOBS} 2>&1 | tee "${LOG_FILE}"
    BUILD_RESULT=${PIPESTATUS[0]}
fi

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
HOURS=$((DURATION / 3600))
MINUTES=$(((DURATION % 3600) / 60))
SECONDS=$((DURATION % 60))

# Check build result
echo ""
echo -e "${BLUE}========================================${NC}"

if [ $BUILD_RESULT -eq 0 ]; then
    echo -e "${GREEN}Build Successful!${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    print_success "Build completed in ${HOURS}h ${MINUTES}m ${SECONDS}s"

    # Find build output
    OUT_DIR="${AOSP_DIR}/out/target/product/r3q"

    if [ -d "${OUT_DIR}" ]; then
        print_status "Build output directory: ${OUT_DIR}"
        echo ""
        print_status "Generated files:"

        # List important files
        if [ -f "${OUT_DIR}/boot.img" ]; then
            BOOT_SIZE=$(du -h "${OUT_DIR}/boot.img" | cut -f1)
            print_success "boot.img (${BOOT_SIZE})"
        fi

        if [ -f "${OUT_DIR}/system.img" ]; then
            SYSTEM_SIZE=$(du -h "${OUT_DIR}/system.img" | cut -f1)
            print_success "system.img (${SYSTEM_SIZE})"
        fi

        if [ -f "${OUT_DIR}/vendor.img" ]; then
            VENDOR_SIZE=$(du -h "${OUT_DIR}/vendor.img" | cut -f1)
            print_success "vendor.img (${VENDOR_SIZE})"
        fi

        # Find flashable ZIP
        ZIP_FILE=$(ls -t "${OUT_DIR}"/aosp_r3q_minimal*.zip 2>/dev/null | head -1)
        if [ -n "$ZIP_FILE" ]; then
            ZIP_SIZE=$(du -h "${ZIP_FILE}" | cut -f1)
            print_success "Flashable ZIP: $(basename ${ZIP_FILE}) (${ZIP_SIZE})"
        else
            print_warning "Flashable ZIP not found"
        fi

        # Total build size
        TOTAL_SIZE=$(du -sh "${OUT_DIR}" | cut -f1)
        print_status "Total output size: ${TOTAL_SIZE}"
    fi

    # Save build info
    BUILD_INFO="${OUT_DIR}/build_info_${BUILD_DATE}.txt"
    cat > "${BUILD_INFO}" << EOF
AOSP Build Information
======================
Build Date:    $(date)
Build Variant: ${BUILD_VARIANT}
Build Time:    ${HOURS}h ${MINUTES}m ${SECONDS}s
Parallel Jobs: ${JOBS}
Clean Build:   $(if [[ "$CLEAN_BUILD" =~ ^[Yy]$ ]]; then echo "YES"; else echo "NO"; fi)

Output Location: ${OUT_DIR}
Log File: ${LOG_FILE}

Generated Files:
$(ls -lh ${OUT_DIR}/*.img 2>/dev/null | awk '{print $9, $5}')

Flashable ZIP:
$(ls -lh ${OUT_DIR}/*.zip 2>/dev/null | awk '{print $9, $5}')

Build Configuration:
$(cat device/samsung/r3q/minimal_build_config.txt 2>/dev/null || echo "Configuration not found")
EOF

    print_success "Build info saved: ${BUILD_INFO}"

    echo ""
    echo -e "${BLUE}Next Steps:${NC}"
    echo -e "  1. Create backup: Run TWRP backup of current system"
    echo -e "  2. Test build: ${YELLOW}./07_flash_test.sh${NC}"
    echo -e "  3. Flash via TWRP or fastboot"
    echo ""

else
    echo -e "${RED}Build Failed!${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    print_error "Build failed after ${HOURS}h ${MINUTES}m ${SECONDS}s"
    print_error "Check log file for details: ${LOG_FILE}"
    echo ""
    print_status "Common build errors:"
    echo "  - Missing vendor blobs → Run ./04_extract_blobs.sh"
    echo "  - Out of memory → Reduce parallel jobs"
    echo "  - Out of disk space → Free up space"
    echo "  - Missing dependencies → Run ./01_setup_environment.sh"
    echo ""
    print_status "Searching for errors in log..."
    echo ""
    grep -i "error:" "${LOG_FILE}" | tail -20 || true
    echo ""
    exit 1
fi
