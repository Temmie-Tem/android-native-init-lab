#!/bin/bash
# Optimized Kernel Build Script for Samsung Galaxy A90 5G
# Conservative optimization profile

KERNEL_DIR="/home/temmie/A90_5G_rooting/archive/phase0_native_boot_research/kernel_build/SM-A908N_KOR_12_Opensource"
TOOLCHAIN_DIR="/home/temmie/A90_5G_rooting/toolchains/android-ndk-r21e"
BUILD_LOG="/home/temmie/A90_5G_rooting/build_optimized.log"

cd "$KERNEL_DIR" || exit 1

echo "======================================================================"
echo " Samsung Galaxy A90 5G - Optimized Kernel Build"
echo "======================================================================"
echo "Kernel Dir: $KERNEL_DIR"
echo "Toolchain: $TOOLCHAIN_DIR"
echo "CPU Cores: $(nproc)"
echo "Build Log: $BUILD_LOG"
echo ""
echo "Starting build at: $(date)"
echo "======================================================================"
echo ""

# Export environment variables
export ARCH=arm64
export SUBARCH=arm64
export CROSS_COMPILE="$TOOLCHAIN_DIR/toolchains/llvm/prebuilt/linux-x86_64/bin/aarch64-linux-android-"
export CLANG_TRIPLE=aarch64-linux-gnu-
export CC="$TOOLCHAIN_DIR/toolchains/llvm/prebuilt/linux-x86_64/bin/clang"
export DTC_EXT=$(pwd)/tools/dtc
export CONFIG_BUILD_ARM64_DT_OVERLAY=y

echo "Environment variables set:"
echo "  ARCH=$ARCH"
echo "  CC=$CC"
echo "  CROSS_COMPILE=$CROSS_COMPILE"
echo ""

# Clean previous build
echo "Cleaning previous build..."
make O=out clean

# Build kernel
echo ""
echo "Starting kernel build with $(nproc) cores..."
echo "This will take approximately 15-25 minutes..."
echo ""

make -j$(nproc) O=out 2>&1 | tee "$BUILD_LOG"

BUILD_STATUS=$?

echo ""
echo "======================================================================"
if [ $BUILD_STATUS -eq 0 ]; then
    echo " BUILD SUCCESSFUL!"
    echo "======================================================================"
    echo ""
    echo "Build completed at: $(date)"
    echo ""

    # Check kernel image
    if [ -f "out/arch/arm64/boot/Image-dtb" ]; then
        IMAGE_SIZE=$(du -h "out/arch/arm64/boot/Image-dtb" | cut -f1)
        echo "Kernel image: out/arch/arm64/boot/Image-dtb"
        echo "Size: $IMAGE_SIZE"
        echo ""
        echo "Expected size: 38-45MB (original: 49.8MB)"
        echo ""

        # Error check
        ERROR_COUNT=$(grep -i "error" "$BUILD_LOG" | wc -l)
        WARNING_COUNT=$(grep -i "warning" "$BUILD_LOG" | wc -l)

        echo "Build statistics:"
        echo "  Errors: $ERROR_COUNT"
        echo "  Warnings: $WARNING_COUNT"
        echo ""

        if [ $ERROR_COUNT -eq 0 ]; then
            echo "✓ Build clean (no errors)"
        else
            echo "⚠ Build has $ERROR_COUNT errors (check log)"
        fi
    else
        echo "ERROR: Kernel image not found!"
        echo "Build may have failed despite exit code 0"
        exit 1
    fi
else
    echo " BUILD FAILED!"
    echo "======================================================================"
    echo ""
    echo "Exit code: $BUILD_STATUS"
    echo ""
    echo "Last 50 lines of build log:"
    tail -50 "$BUILD_LOG"
    exit 1
fi

echo ""
echo "======================================================================"
echo " Next steps:"
echo "======================================================================"
echo "1. Create boot.img with mkbootimg"
echo "2. Patch with Magisk"
echo "3. Flash to device"
echo "4. Test and measure RAM savings"
echo ""
