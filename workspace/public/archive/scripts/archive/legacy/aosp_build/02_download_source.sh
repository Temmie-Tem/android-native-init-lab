#!/bin/bash
################################################################################
# AOSP Source Download Script
# Samsung Galaxy A90 5G (r3q) - Option C: Minimal AOSP Build
#
# This script downloads LineageOS 20.0 (Android 13) source code
# Estimated download: 18-20GB, Time: 6-12 hours
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
echo -e "${BLUE}AOSP Source Download${NC}"
echo -e "${BLUE}LineageOS 20.0 (Android 13)${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Configuration
AOSP_DIR="${HOME}/aosp/r3q"
LINEAGE_BRANCH="lineage-20.0"  # Android 13

# Build type selection
echo -e "${YELLOW}Select AOSP source to download:${NC}"
echo "  1) LineageOS 20.0 (Android 13) - Recommended (proven for r3q)"
echo "  2) Pure AOSP Android 13 (AOSP master)"
echo "  3) Cancel"
echo ""
read -p "Enter choice [1-3]: " CHOICE

case $CHOICE in
    1)
        BUILD_TYPE="lineageos"
        MANIFEST_URL="https://github.com/LineageOS/android.git"
        MANIFEST_BRANCH="lineage-20.0"
        print_status "Selected: LineageOS 20.0 (Android 13)"
        ;;
    2)
        BUILD_TYPE="aosp"
        MANIFEST_URL="https://android.googlesource.com/platform/manifest"
        MANIFEST_BRANCH="android-13.0.0_r1"
        print_status "Selected: Pure AOSP Android 13"
        ;;
    3)
        print_status "Download cancelled."
        exit 0
        ;;
    *)
        print_error "Invalid choice. Exiting."
        exit 1
        ;;
esac

# Verify repo tool
if ! command -v repo &> /dev/null; then
    print_error "repo tool not found!"
    print_error "Please run ./01_setup_environment.sh first"
    exit 1
fi

# Create and enter build directory
print_status "Creating build directory: ${AOSP_DIR}"
mkdir -p "${AOSP_DIR}"
cd "${AOSP_DIR}"

# Check if already initialized
if [ -d ".repo" ]; then
    print_warning "Repository already initialized in ${AOSP_DIR}"
    read -p "Re-initialize? This will reset your repo [y/N]: " REINIT
    if [[ "$REINIT" =~ ^[Yy]$ ]]; then
        print_status "Removing existing .repo directory..."
        rm -rf .repo
    else
        print_status "Skipping initialization. Proceeding to sync..."
        repo sync -c -j$(nproc --all) --force-sync --no-clone-bundle --no-tags
        print_success "Source sync completed!"
        exit 0
    fi
fi

# Initialize repository
print_status "Initializing repository..."
print_status "Manifest: ${MANIFEST_URL}"
print_status "Branch: ${MANIFEST_BRANCH}"
echo ""

print_warning "This will download approximately 18-20GB of data"
print_warning "Estimated time: 6-12 hours depending on internet speed"
echo ""
read -p "Continue? [y/N]: " CONTINUE

if [[ ! "$CONTINUE" =~ ^[Yy]$ ]]; then
    print_status "Download cancelled."
    exit 0
fi

# Repo init with depth=1 to save space and time
print_status "Running repo init (shallow clone for faster download)..."
repo init -u "${MANIFEST_URL}" -b "${MANIFEST_BRANCH}" --depth=1

if [ $? -ne 0 ]; then
    print_error "repo init failed!"
    exit 1
fi

print_success "Repository initialized"

# Sync source
print_status "Starting source download..."
print_status "Using $(nproc --all) parallel jobs"
echo ""

START_TIME=$(date +%s)

# Sync with progress
repo sync -c -j$(nproc --all) --force-sync --no-clone-bundle --no-tags

if [ $? -ne 0 ]; then
    print_error "repo sync failed!"
    print_error "You can resume by running: cd ${AOSP_DIR} && repo sync -c -j$(nproc)"
    exit 1
fi

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
HOURS=$((DURATION / 3600))
MINUTES=$(((DURATION % 3600) / 60))

print_success "Source download completed!"
print_success "Download time: ${HOURS}h ${MINUTES}m"

# Check download size
REPO_SIZE=$(du -sh "${AOSP_DIR}" | cut -f1)
print_status "Repository size: ${REPO_SIZE}"

# Save build info
cat > "${AOSP_DIR}/build_info.txt" << EOF
AOSP Build Information
======================
Build Type: ${BUILD_TYPE}
Manifest URL: ${MANIFEST_URL}
Branch: ${MANIFEST_BRANCH}
Download Date: $(date)
Repository Size: ${REPO_SIZE}
Download Duration: ${HOURS}h ${MINUTES}m
EOF

print_success "Build info saved to build_info.txt"

# Summary
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Source Download Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BLUE}Downloaded:${NC}"
echo -e "  Type:   ${BUILD_TYPE}"
echo -e "  Branch: ${MANIFEST_BRANCH}"
echo -e "  Size:   ${REPO_SIZE}"
echo -e "  Time:   ${HOURS}h ${MINUTES}m"
echo -e "  Path:   ${AOSP_DIR}"
echo ""
echo -e "${BLUE}Next Steps:${NC}"
echo -e "  1. Run: ${YELLOW}./03_setup_device_tree.sh${NC}"
echo -e "  2. This will clone r3q device tree and dependencies"
echo ""
