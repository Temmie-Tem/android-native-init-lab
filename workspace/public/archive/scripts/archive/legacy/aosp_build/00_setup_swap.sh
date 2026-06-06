#!/bin/bash
################################################################################
# Setup Swap File for AOSP Build
# Samsung Galaxy A90 5G (r3q) - Option C: Minimal AOSP Build
#
# This script creates a 32GB swap file to compensate for RAM shortage
# Required: 32GB RAM minimum, current system has 15GB
# Swap will add 32GB virtual memory (total 47GB)
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
echo -e "${BLUE}Setup Swap File for AOSP Build${NC}"
echo -e "${BLUE}Samsung Galaxy A90 5G (r3q)${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check current RAM
TOTAL_RAM=$(free -g | awk '/^Mem:/{print $2}')
print_status "Current RAM: ${TOTAL_RAM}GB"

# Check disk space
AVAILABLE_SPACE=$(df -BG ~ | awk 'NR==2 {print $4}' | sed 's/G//')
print_status "Available disk space: ${AVAILABLE_SPACE}GB"

if [ "$AVAILABLE_SPACE" -lt 10 ]; then
    print_error "Not enough disk space for 8GB swap file!"
    print_error "Need at least 10GB free, have ${AVAILABLE_SPACE}GB"
    exit 1
fi

# Swap configuration
SWAP_SIZE_GB=8
SWAP_FILE="/swapfile_aosp"

echo ""
print_warning "This script will create a ${SWAP_SIZE_GB}GB swap file"
print_warning "This will take 1-2 minutes and use ${SWAP_SIZE_GB}GB disk space"
echo ""

# Check if old swap exists
if [ -f "/swap.img" ]; then
    print_status "Removing old swap file /swap.img..."
    sudo swapoff /swap.img 2>/dev/null || true
    sudo rm /swap.img
fi

if [ -f "${SWAP_FILE}" ]; then
    print_status "Swap file already exists at ${SWAP_FILE}"
    read -p "Remove and recreate? [y/N]: " RECREATE
    if [[ "$RECREATE" =~ ^[Yy]$ ]]; then
        sudo swapoff "${SWAP_FILE}" 2>/dev/null || true
        sudo rm "${SWAP_FILE}"
    else
        print_status "Using existing swap file"
        sudo swapon "${SWAP_FILE}"
        print_success "Swap activated!"
        swapon --show
        exit 0
    fi
fi

# Create swap file
echo ""
print_status "Creating ${SWAP_SIZE_GB}GB swap file (this will take 5-10 minutes)..."
print_status "Using fallocate for fast allocation..."

sudo fallocate -l ${SWAP_SIZE_GB}G "${SWAP_FILE}"

if [ $? -ne 0 ]; then
    print_warning "fallocate failed, trying dd method (slower)..."
    sudo dd if=/dev/zero of="${SWAP_FILE}" bs=1G count=${SWAP_SIZE_GB} status=progress
fi

# Set permissions
print_status "Setting permissions..."
sudo chmod 600 "${SWAP_FILE}"

# Make swap
print_status "Formatting as swap..."
sudo mkswap "${SWAP_FILE}"

# Enable swap
print_status "Enabling swap..."
sudo swapon "${SWAP_FILE}"

# Verify
echo ""
print_success "Swap file created and activated!"
echo ""
swapon --show
echo ""
free -h

# Make permanent (add to /etc/fstab)
echo ""
read -p "Make swap permanent (survive reboots)? [y/N]: " PERMANENT
if [[ "$PERMANENT" =~ ^[Yy]$ ]]; then
    # Check if already in fstab
    if grep -q "${SWAP_FILE}" /etc/fstab; then
        print_status "Swap already in /etc/fstab"
    else
        print_status "Adding to /etc/fstab..."
        echo "${SWAP_FILE} none swap sw 0 0" | sudo tee -a /etc/fstab
        print_success "Swap will persist after reboot"
    fi
fi

# Optimize swappiness for build workload
echo ""
print_status "Current swappiness: $(cat /proc/sys/vm/swappiness)"
read -p "Set swappiness to 10 (recommended for AOSP build)? [y/N]: " SET_SWAPPINESS
if [[ "$SET_SWAPPINESS" =~ ^[Yy]$ ]]; then
    sudo sysctl vm.swappiness=10
    echo "vm.swappiness=10" | sudo tee -a /etc/sysctl.conf
    print_success "Swappiness set to 10 (will use RAM first, swap only when necessary)"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Swap Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
print_status "Total memory available for AOSP build:"
TOTAL_MEM=$((TOTAL_RAM + SWAP_SIZE_GB))
echo "  Physical RAM: ${TOTAL_RAM}GB"
echo "  Swap:         ${SWAP_SIZE_GB}GB"
echo "  Total:        ${TOTAL_MEM}GB"
echo ""
print_warning "Note: Build may use swap occasionally (expect 12-18 hours)"
print_warning "Recommendation: Use moderate parallel jobs (-j8 to -j12)"
echo ""
print_status "Next step: Run ./01_setup_environment.sh"
echo ""
