#!/bin/bash
# create_rootfs.sh - Debian ARM64 Rootfs 자동 생성 스크립트
#
# 사용법: sudo ./create_rootfs.sh [size_in_mb] [distro] [release]
# 예제: sudo ./create_rootfs.sh 6144 debian bookworm
#       sudo ./create_rootfs.sh 8192 ubuntu jammy

set -e  # 오류 발생 시 즉시 중단
set -u  # 미정의 변수 사용 시 오류

# ====================================================================
# 설정 변수
# ====================================================================

# 기본값
DEFAULT_SIZE=6144          # 6GB
DEFAULT_DISTRO="debian"
DEFAULT_RELEASE="bookworm" # Debian 12

# 인자 파싱
IMG_SIZE=${1:-$DEFAULT_SIZE}
DISTRO=${2:-$DEFAULT_DISTRO}
RELEASE=${3:-$DEFAULT_RELEASE}

# 출력 파일
IMG_NAME="${DISTRO}_${RELEASE}_arm64.img"
MOUNT_POINT="mnt_rootfs"

# 색상 코드
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ====================================================================
# 유틸리티 함수
# ====================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_root() {
    if [ "$EUID" -ne 0 ]; then
        log_error "이 스크립트는 root 권한이 필요합니다"
        log_info "다음과 같이 실행하세요: sudo $0 $@"
        exit 1
    fi
}

check_dependencies() {
    log_info "필수 패키지 확인 중..."

    local missing_pkgs=()

    # 필수 패키지 목록
    local required_pkgs=(
        "debootstrap"
        "qemu-user-static"
        "binfmt-support"
        "e2fsprogs"
    )

    for pkg in "${required_pkgs[@]}"; do
        if ! command -v "$pkg" &>/dev/null && ! dpkg -l | grep -q "^ii  $pkg"; then
            missing_pkgs+=("$pkg")
        fi
    done

    if [ ${#missing_pkgs[@]} -gt 0 ]; then
        log_warning "다음 패키지가 필요합니다: ${missing_pkgs[*]}"
        log_info "설치 중..."
        apt update
        apt install -y "${missing_pkgs[@]}"
    fi

    log_success "모든 필수 패키지가 설치되어 있습니다"
}

cleanup() {
    log_info "정리 중..."

    # 마운트 해제
    if mountpoint -q "$MOUNT_POINT/dev" 2>/dev/null; then
        umount -l "$MOUNT_POINT/dev" 2>/dev/null || true
    fi
    if mountpoint -q "$MOUNT_POINT/proc" 2>/dev/null; then
        umount -l "$MOUNT_POINT/proc" 2>/dev/null || true
    fi
    if mountpoint -q "$MOUNT_POINT/sys" 2>/dev/null; then
        umount -l "$MOUNT_POINT/sys" 2>/dev/null || true
    fi
    if mountpoint -q "$MOUNT_POINT" 2>/dev/null; then
        umount -l "$MOUNT_POINT" 2>/dev/null || true
    fi

    # 임시 디렉토리 삭제
    if [ -d "$MOUNT_POINT" ]; then
        rm -rf "$MOUNT_POINT"
    fi
}

# 트랩 설정 (오류 또는 종료 시 정리)
trap cleanup EXIT

# ====================================================================
# 메인 함수
# ====================================================================

main() {
    echo ""
    echo "========================================"
    echo "  Debian/Ubuntu ARM64 Rootfs 생성기"
    echo "========================================"
    echo ""
    echo "배포판: $DISTRO $RELEASE"
    echo "이미지 크기: ${IMG_SIZE}MB"
    echo "출력 파일: $IMG_NAME"
    echo ""

    # 사전 확인
    check_root
    check_dependencies

    # Step 1: 이미지 파일 생성
    log_info "[Step 1/10] 빈 이미지 파일 생성 중... (${IMG_SIZE}MB)"
    if [ -f "$IMG_NAME" ]; then
        log_warning "기존 이미지 파일이 존재합니다: $IMG_NAME"
        read -p "덮어쓰시겠습니까? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_error "사용자가 취소했습니다"
            exit 1
        fi
        rm -f "$IMG_NAME"
    fi

    dd if=/dev/zero of="$IMG_NAME" bs=1M count="$IMG_SIZE" status=progress
    log_success "이미지 파일 생성 완료"

    # Step 2: ext4 파일시스템 포맷
    log_info "[Step 2/10] ext4 파일시스템 포맷 중..."
    mkfs.ext4 -F -L "Linux_Root" "$IMG_NAME"
    log_success "ext4 포맷 완료"

    # Step 3: 마운트 포인트 생성
    log_info "[Step 3/10] 마운트 포인트 생성 중..."
    mkdir -p "$MOUNT_POINT"
    mount -o loop "$IMG_NAME" "$MOUNT_POINT"
    log_success "이미지 마운트 완료: $MOUNT_POINT"

    # Step 4: qemu-user-static 복사
    log_info "[Step 4/10] ARM64 에뮬레이션 설정 중..."
    cp /usr/bin/qemu-aarch64-static "$MOUNT_POINT/usr/bin/" 2>/dev/null || \
        mkdir -p "$MOUNT_POINT/usr/bin" && cp /usr/bin/qemu-aarch64-static "$MOUNT_POINT/usr/bin/"
    log_success "qemu-aarch64-static 복사 완료"

    # Step 5: debootstrap으로 rootfs 설치
    log_info "[Step 5/10] $DISTRO $RELEASE rootfs 설치 중..."
    log_warning "이 단계는 15-45분 소요됩니다 (네트워크 속도에 따라)"

    if [ "$DISTRO" = "debian" ]; then
        MIRROR="http://deb.debian.org/debian/"
    elif [ "$DISTRO" = "ubuntu" ]; then
        MIRROR="http://ports.ubuntu.com/ubuntu-ports/"
    else
        log_error "지원하지 않는 배포판: $DISTRO"
        exit 1
    fi

    # 재시도 로직 추가 (네트워크 오류 방지)
    local max_retries=3
    local retry_count=0

    while [ $retry_count -lt $max_retries ]; do
        log_info "Debootstrap 시도 $((retry_count + 1))/$max_retries..."

        if debootstrap \
            --arch=arm64 \
            --variant=minbase \
            --include=systemd,udev,dbus,apt,wget,curl,ca-certificates \
            "$RELEASE" \
            "$MOUNT_POINT" \
            "$MIRROR"; then
            log_success "Debootstrap 완료!"
            break
        else
            retry_count=$((retry_count + 1))
            if [ $retry_count -lt $max_retries ]; then
                log_warning "실패! 5초 후 재시도..."
                sleep 5
                # 부분적으로 생성된 파일 정리
                rm -rf "$MOUNT_POINT"/*
            else
                log_error "Debootstrap이 $max_retries번 실패했습니다"
                exit 1
            fi
        fi
    done

    log_success "Rootfs 설치 완료"

    # Step 6: 기본 시스템 설정
    log_info "[Step 6/10] 기본 시스템 설정 중..."

    # 호스트명
    echo "a90-$DISTRO" > "$MOUNT_POINT/etc/hostname"

    # hosts 파일
    cat > "$MOUNT_POINT/etc/hosts" << 'EOF'
127.0.0.1       localhost
127.0.1.1       a90-debian
::1             localhost ip6-localhost ip6-loopback
ff02::1         ip6-allnodes
ff02::2         ip6-allrouters
EOF

    # DNS (Cloudflare 우선 - 더 빠름)
    cat > "$MOUNT_POINT/etc/resolv.conf" << 'EOF'
nameserver 1.1.1.1
nameserver 1.0.0.1
nameserver 8.8.8.8
EOF

    # APT 소스
    if [ "$DISTRO" = "debian" ]; then
        cat > "$MOUNT_POINT/etc/apt/sources.list" << EOF
deb http://deb.debian.org/debian $RELEASE main contrib non-free non-free-firmware
deb http://deb.debian.org/debian $RELEASE-updates main contrib non-free non-free-firmware
deb http://security.debian.org/debian-security $RELEASE-security main contrib non-free non-free-firmware
EOF
    elif [ "$DISTRO" = "ubuntu" ]; then
        cat > "$MOUNT_POINT/etc/apt/sources.list" << EOF
deb http://ports.ubuntu.com/ubuntu-ports $RELEASE main restricted universe multiverse
deb http://ports.ubuntu.com/ubuntu-ports $RELEASE-updates main restricted universe multiverse
deb http://ports.ubuntu.com/ubuntu-ports $RELEASE-security main restricted universe multiverse
EOF
    fi

    log_success "기본 설정 완료"

    # Step 7: Chroot 환경 준비
    log_info "[Step 7/10] Chroot 환경 준비 중..."
    mount -t proc proc "$MOUNT_POINT/proc"
    mount -t sysfs sys "$MOUNT_POINT/sys"
    mount --rbind /dev "$MOUNT_POINT/dev"
    mount --make-rslave "$MOUNT_POINT/dev"
    log_success "Chroot 환경 준비 완료"

    # Step 8: 필수 패키지 설치
    log_info "[Step 8/10] 필수 패키지 설치 중..."
    log_warning "이 단계는 10-20분 소요됩니다"

    chroot "$MOUNT_POINT" /bin/bash << 'CHROOT_EOF'
set -e

# APT 업데이트
apt update
apt upgrade -y

# 필수 패키지 설치
apt install -y \
    openssh-server \
    openssh-client \
    sudo \
    vim \
    nano \
    wget \
    curl \
    git \
    htop \
    tmux \
    screen \
    net-tools \
    iputils-ping \
    traceroute \
    dnsutils \
    build-essential \
    python3 \
    python3-pip \
    python3-venv \
    gcc \
    g++ \
    make \
    cmake \
    gdb \
    strace \
    locales

# SSH 디렉토리
mkdir -p /run/sshd
mkdir -p /root/.ssh
chmod 700 /root/.ssh

# SSH 설정: 기본 root/password login은 금지한다.
sed -i -E 's/^#?PermitRootLogin .*/PermitRootLogin prohibit-password/' /etc/ssh/sshd_config
sed -i -E 's/^#?PasswordAuthentication .*/PasswordAuthentication no/' /etc/ssh/sshd_config
sed -i 's/#Port 22/Port 22/' /etc/ssh/sshd_config

# Root password login 방지. SSH 접속은 operator-provided key를 사용한다.
passwd -l root >/dev/null 2>&1 || true

# 타임존
ln -sf /usr/share/zoneinfo/Asia/Seoul /etc/localtime

# 로케일
echo "en_US.UTF-8 UTF-8" >> /etc/locale.gen
echo "ko_KR.UTF-8 UTF-8" >> /etc/locale.gen
locale-gen
update-locale LANG=en_US.UTF-8

# 불필요한 서비스 비활성화 (headless)
systemctl disable bluetooth 2>/dev/null || true
systemctl disable avahi-daemon 2>/dev/null || true

# APT 캐시 정리
apt clean
apt autoremove -y

echo ""
echo "====================================="
echo "  패키지 설치 완료!"
echo "====================================="

CHROOT_EOF

    log_success "패키지 설치 완료"

    # Step 9: 정리
    log_info "[Step 9/10] 마운트 해제 중..."
    umount "$MOUNT_POINT/dev"
    umount "$MOUNT_POINT/proc"
    umount "$MOUNT_POINT/sys"
    umount "$MOUNT_POINT"
    rm -rf "$MOUNT_POINT"
    log_success "마운트 해제 완료"

    # Step 10: 이미지 무결성 검사
    log_info "[Step 10/10] 이미지 무결성 검사 중..."
    e2fsck -f -y "$IMG_NAME"
    log_success "무결성 검사 완료"

    # 완료
    echo ""
    echo "========================================"
    echo "  🎉 Rootfs 생성 완료!"
    echo "========================================"
    echo ""
    echo "출력 파일: $IMG_NAME"
    echo "파일 크기: $(du -h "$IMG_NAME" | cut -f1)"
    echo ""
    echo "다음 단계:"
    echo "1. 이미지를 디바이스로 전송:"
    echo "   adb push $IMG_NAME /sdcard/"
    echo ""
    echo "2. 디바이스에서 이동:"
    echo "   adb shell"
    echo "   su"
    echo "   mv /sdcard/$IMG_NAME /data/linux_root/"
    echo ""
    echo "3. Magisk 모듈 설치 후 재부팅"
    echo ""
    echo "기본 root 비밀번호는 설정하지 않습니다."
    echo "SSH 접속은 operator-provided key를 /root/.ssh/authorized_keys에 배치한 뒤 사용하세요."
    echo ""
}

# ====================================================================
# 스크립트 실행
# ====================================================================

main "$@"
