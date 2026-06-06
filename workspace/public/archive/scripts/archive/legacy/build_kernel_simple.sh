#!/bin/bash
set -e

KERNEL_DIR="/home/temmie/A90_5G_rooting/archive/phase0_native_boot_research/kernel_build/SM-A908N_KOR_12_Opensource"
TOOLCHAIN_DIR="/home/temmie/A90_5G_rooting/toolchains/android-ndk-r21e"

cd "$KERNEL_DIR"

export ARCH=arm64
export SUBARCH=arm64
export CROSS_COMPILE="$TOOLCHAIN_DIR/toolchains/llvm/prebuilt/linux-x86_64/bin/aarch64-linux-android-"
export CLANG_TRIPLE=aarch64-linux-gnu-
export CC="$TOOLCHAIN_DIR/toolchains/llvm/prebuilt/linux-x86_64/bin/clang"

echo "Starting kernel build..."
echo "Dir: $KERNEL_DIR"
echo "Cores: $(nproc)"

make -j$(nproc) O=out

if [ -f "out/arch/arm64/boot/Image-dtb" ]; then
    SIZE=$(du -h "out/arch/arm64/boot/Image-dtb" | cut -f1)
    echo ""
    echo "BUILD SUCCESS!"
    echo "Image: out/arch/arm64/boot/Image-dtb"
    echo "Size: $SIZE"
else
    echo ""
    echo "BUILD FAILED - Image not found"
    exit 1
fi
