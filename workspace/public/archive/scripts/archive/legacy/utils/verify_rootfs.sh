#!/bin/bash
# verify_rootfs.sh - Rootfs 이미지 검증 스크립트
#
# 사용법: sudo ./verify_rootfs.sh <image_file>

set -e

# 색상 코드
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
}

log_section() {
    echo ""
    echo -e "${CYAN}========================================${NC}"
    echo -e "${CYAN} $1${NC}"
    echo -e "${CYAN}========================================${NC}"
}

# ====================================================================
# 인자 확인
# ====================================================================

if [ $# -lt 1 ]; then
    log_error "사용법: sudo $0 <image_file>"
    exit 1
fi

IMG_FILE="$1"

if [ ! -f "$IMG_FILE" ]; then
    log_error "이미지 파일을 찾을 수 없습니다: $IMG_FILE"
    exit 1
fi

if [ "$EUID" -ne 0 ]; then
    log_error "이 스크립트는 root 권한이 필요합니다"
    log_info "다음과 같이 실행하세요: sudo $0 $IMG_FILE"
    exit 1
fi

# ====================================================================
# 검증 시작
# ====================================================================

log_section "Rootfs 이미지 검증"

log_info "이미지: $IMG_FILE"

# Step 1: 파일 시스템 무결성 검사
log_info "[1/6] 파일 시스템 무결성 검사 중..."

if e2fsck -n "$IMG_FILE" 2>&1 | grep -q "clean"; then
    log_success "파일 시스템 무결성: 정상"
else
    log_warning "파일 시스템에 경미한 문제가 있을 수 있습니다"
fi

# Step 2: 이미지 정보
log_info "[2/6] 이미지 정보 수집 중..."

IMG_SIZE=$(du -h "$IMG_FILE" | cut -f1)
log_info "이미지 크기: $IMG_SIZE"

# Step 3: 마운트 및 내용 검사
log_info "[3/6] 이미지 마운트 중..."

MOUNT_POINT="/tmp/verify_rootfs_$$"
mkdir -p "$MOUNT_POINT"

# Cleanup function
cleanup() {
    log_info "정리 중..."
    umount "$MOUNT_POINT" 2>/dev/null || true
    rmdir "$MOUNT_POINT" 2>/dev/null || true
}

trap cleanup EXIT

mount -o loop,ro "$IMG_FILE" "$MOUNT_POINT"
log_success "마운트 성공: $MOUNT_POINT"

# Step 4: 필수 디렉토리 확인
log_info "[4/6] 필수 디렉토리 확인 중..."

REQUIRED_DIRS=(
    "bin"
    "boot"
    "dev"
    "etc"
    "home"
    "lib"
    "proc"
    "root"
    "sbin"
    "sys"
    "tmp"
    "usr"
    "var"
)

ALL_DIRS_OK=true

for dir in "${REQUIRED_DIRS[@]}"; do
    if [ -d "$MOUNT_POINT/$dir" ]; then
        echo -e "  ${GREEN}✓${NC} /$dir"
    else
        echo -e "  ${RED}✗${NC} /$dir (누락)"
        ALL_DIRS_OK=false
    fi
done

if [ "$ALL_DIRS_OK" = true ]; then
    log_success "모든 필수 디렉토리 존재"
else
    log_error "일부 필수 디렉토리가 누락되었습니다"
fi

# Step 5: 필수 바이너리 확인
log_info "[5/6] 필수 바이너리 확인 중..."

REQUIRED_BINS=(
    "bash"
    "ls"
    "cat"
    "grep"
    "apt"
    "dpkg"
    "systemctl"
)

ALL_BINS_OK=true

for bin in "${REQUIRED_BINS[@]}"; do
    if [ -f "$MOUNT_POINT/bin/$bin" ] || [ -f "$MOUNT_POINT/usr/bin/$bin" ]; then
        echo -e "  ${GREEN}✓${NC} $bin"
    else
        echo -e "  ${RED}✗${NC} $bin (누락)"
        ALL_BINS_OK=false
    fi
done

if [ "$ALL_BINS_OK" = true ]; then
    log_success "모든 필수 바이너리 존재"
else
    log_warning "일부 바이너리가 누락되었습니다"
fi

# Step 6: SSH 설치 확인
log_info "[6/6] SSH 서버 확인 중..."

if [ -f "$MOUNT_POINT/usr/sbin/sshd" ]; then
    log_success "SSH 서버: 설치됨"

    # SSH 호스트 키 확인
    if ls "$MOUNT_POINT/etc/ssh/ssh_host_"*"_key" 1>/dev/null 2>&1; then
        log_success "SSH 호스트 키: 생성됨"
    else
        log_warning "SSH 호스트 키: 미생성 (첫 부팅 시 자동 생성)"
    fi
else
    log_warning "SSH 서버: 미설치"
fi

# 추가 정보
log_section "추가 정보"

# 디스크 사용량
log_info "디스크 사용량:"
df -h "$MOUNT_POINT" | tail -1 | awk '{print "  사용: " $3 " / " $2 " (" $5 ")"}'

# 설치된 패키지 수 (대략)
if [ -d "$MOUNT_POINT/var/lib/dpkg/info" ]; then
    PKG_COUNT=$(ls "$MOUNT_POINT/var/lib/dpkg/info"/*.list 2>/dev/null | wc -l)
    log_info "설치된 패키지 수: 약 $PKG_COUNT개"
fi

# /etc/os-release 확인
if [ -f "$MOUNT_POINT/etc/os-release" ]; then
    log_info "배포판 정보:"
    grep -E "^(NAME|VERSION)" "$MOUNT_POINT/etc/os-release" | sed 's/^/  /'
fi

# Cleanup
umount "$MOUNT_POINT"
rmdir "$MOUNT_POINT"

# 최종 결과
log_section "검증 결과"

if [ "$ALL_DIRS_OK" = true ] && [ "$ALL_BINS_OK" = true ]; then
    log_success "Rootfs 이미지 검증 완료! 디바이스로 전송할 수 있습니다."
    echo ""
    log_info "다음 단계:"
    echo "  1. 디바이스로 전송: adb push $IMG_FILE /sdcard/"
    echo "  2. /data로 이동: adb shell \"su -c 'mkdir -p /data/linux_root'\""
    echo "  3. 복사: adb shell \"su -c 'cp /sdcard/$(basename "$IMG_FILE") /data/linux_root/'\""
    echo ""
    exit 0
else
    log_error "Rootfs 이미지에 문제가 있습니다. 다시 생성하세요."
    exit 1
fi