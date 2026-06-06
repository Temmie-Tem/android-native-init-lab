#!/bin/bash
################################################################################
# AOSP Build Environment Setup Script
# Samsung Galaxy A90 5G (r3q) - Option C: Minimal AOSP Build
#
# This script verifies and sets up the build environment for AOSP compilation
################################################################################

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}AOSP Build Environment Setup${NC}"
echo -e "${BLUE}Samsung Galaxy A90 5G (r3q)${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Function to print status
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 1. Check system requirements
print_status "Checking system requirements..."

# Check RAM
TOTAL_RAM=$(free -g | awk '/^Mem:/{print $2}')
print_status "Total RAM: ${TOTAL_RAM}GB"
if [ "$TOTAL_RAM" -lt 32 ]; then
    print_warning "RAM is less than 32GB (recommended minimum)"
    print_warning "Build may be slow or fail. Consider using swap or fewer cores."
else
    print_success "RAM: ${TOTAL_RAM}GB (sufficient)"
fi

# Check disk space
AVAILABLE_SPACE=$(df -BG . | awk 'NR==2 {print $4}' | sed 's/G//')
print_status "Available disk space: ${AVAILABLE_SPACE}GB"
if [ "$AVAILABLE_SPACE" -lt 80 ]; then
    print_error "Less than 80GB free space. Minimal AOSP build requires ~80-150GB."
    print_error "Current available: ${AVAILABLE_SPACE}GB"
    exit 1
elif [ "$AVAILABLE_SPACE" -lt 150 ]; then
    print_warning "Less than 150GB free space. Minimal build possible but tight."
    print_warning "Full AOSP (with sources) recommended: 200-250GB"
    print_warning "Current available: ${AVAILABLE_SPACE}GB"
else
    print_success "Disk space: ${AVAILABLE_SPACE}GB (sufficient)"
fi

# Check CPU cores
CPU_CORES=$(nproc --all)
print_success "CPU cores: ${CPU_CORES}"

# Check Ubuntu version
UBUNTU_VERSION=$(lsb_release -rs 2>/dev/null || echo "unknown")
print_status "Ubuntu version: ${UBUNTU_VERSION}"

# 2. Install required packages
print_status "Installing required packages..."

sudo apt update

PACKAGES=(
    bc bison build-essential ccache curl flex
    g++-multilib gcc-multilib git git-lfs gnupg gperf
    imagemagick lib32readline-dev lib32z1-dev libelf-dev
    liblz4-tool libsdl1.2-dev libssl-dev libxml2 libxml2-utils
    lzop pngcrush rsync schedtool squashfs-tools xsltproc
    zip zlib1g-dev libncurses5-dev
    python3 python2 python-is-python3
    openjdk-11-jdk openjdk-11-jre
    adb fastboot
)

print_status "Installing packages (this may take a few minutes)..."
sudo apt install -y "${PACKAGES[@]}" 2>&1 | grep -v "is already the newest version" || true

print_success "Package installation completed"

# 3. Install repo tool if not present
print_status "Checking repo tool..."
if ! command -v repo &> /dev/null; then
    print_status "Installing repo tool..."
    mkdir -p ~/.bin
    curl https://storage.googleapis.com/git-repo-downloads/repo > ~/.bin/repo
    chmod a+rx ~/.bin/repo

    # Add to PATH if not already there
    if [[ ":$PATH:" != *":$HOME/.bin:"* ]]; then
        echo 'export PATH="$HOME/.bin:$PATH"' >> ~/.bashrc
        export PATH="$HOME/.bin:$PATH"
    fi
    print_success "Repo tool installed"
else
    print_success "Repo tool already installed"
fi

# 4. Configure Git
print_status "Configuring Git..."
if [ -z "$(git config --global user.email)" ]; then
    print_status "Git user.email not set. Setting default..."
    git config --global user.email "aosp-builder@a90-5g.local"
fi
if [ -z "$(git config --global user.name)" ]; then
    print_status "Git user.name not set. Setting default..."
    git config --global user.name "AOSP Builder"
fi
print_success "Git configured: $(git config --global user.name) <$(git config --global user.email)>"

# 5. Configure ccache
print_status "Configuring ccache..."
export USE_CCACHE=1
export CCACHE_EXEC=/usr/bin/ccache

# Set ccache size to 50GB
ccache -M 50G
print_success "ccache configured (50GB max size)"

# Add to bashrc for persistence
if ! grep -q "USE_CCACHE=1" ~/.bashrc; then
    echo "" >> ~/.bashrc
    echo "# AOSP Build ccache configuration" >> ~/.bashrc
    echo "export USE_CCACHE=1" >> ~/.bashrc
    echo "export CCACHE_EXEC=/usr/bin/ccache" >> ~/.bashrc
fi

# 6. Create build directory
AOSP_DIR="${HOME}/aosp"
R3Q_DIR="${AOSP_DIR}/r3q"

print_status "Creating build directory: ${R3Q_DIR}"
mkdir -p "${R3Q_DIR}"
print_success "Build directory created"

# 7. Verify tools
print_status "Verifying installed tools..."

check_command() {
    if command -v "$1" &> /dev/null; then
        VERSION=$($1 --version 2>&1 | head -1)
        print_success "$1: ${VERSION}"
    else
        print_error "$1 not found!"
        return 1
    fi
}

check_command git
check_command repo
check_command adb
check_command java
check_command python3
check_command ccache

# 8. Summary
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Environment Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BLUE}System Summary:${NC}"
echo -e "  RAM:        ${TOTAL_RAM}GB"
echo -e "  Disk Space: ${AVAILABLE_SPACE}GB"
echo -e "  CPU Cores:  ${CPU_CORES}"
echo -e "  Ubuntu:     ${UBUNTU_VERSION}"
echo -e "  Build Dir:  ${R3Q_DIR}"
echo ""
echo -e "${BLUE}Next Steps:${NC}"
echo -e "  1. Run: ${YELLOW}./02_download_source.sh${NC}"
echo -e "  2. This will download ~18-20GB of source code"
echo -e "  3. Estimated time: 6-12 hours depending on internet speed"
echo ""
echo -e "${YELLOW}Note:${NC} You can now close and reopen your terminal,"
echo -e "      or run: ${YELLOW}source ~/.bashrc${NC}"
echo ""
