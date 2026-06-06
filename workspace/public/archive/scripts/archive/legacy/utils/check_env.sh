#!/bin/bash
# check_env.sh - Phase 1 환경 점검 스크립트
#
# 사용법: ./check_env.sh

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
# 환경 점검 함수
# ====================================================================

check_pc_env() {
    log_section "PC 환경 점검"

    local all_ok=true

    # debootstrap
    if command -v debootstrap &>/dev/null; then
        local ver=$(debootstrap --version 2>&1 | head -1)
        log_success "debootstrap: $ver"
    else
        log_error "debootstrap: NOT INSTALLED"
        all_ok=false
    fi

    # qemu-user-static
    if command -v qemu-aarch64-static &>/dev/null; then
        local ver=$(qemu-aarch64-static --version | head -1)
        log_success "qemu-user-static: $ver"
    else
        log_error "qemu-user-static: NOT INSTALLED"
        all_ok=false
    fi

    # binfmt-support
    if command -v update-binfmts &>/dev/null; then
        log_success "binfmt-support: installed"
    else
        log_error "binfmt-support: NOT INSTALLED"
        all_ok=false
    fi

    # e2fsprogs
    if command -v mkfs.ext4 &>/dev/null; then
        local ver=$(mkfs.ext4 -V 2>&1 | head -1)
        log_success "e2fsprogs: $ver"
    else
        log_error "e2fsprogs: NOT INSTALLED"
        all_ok=false
    fi

    # 디스크 공간
    local available=$(df -h . | tail -1 | awk '{print $4}')
    local used=$(df -h . | tail -1 | awk '{print $5}')
    log_info "Disk space: $available available ($used used)"

    if [ "$all_ok" = false ]; then
        echo ""
        log_error "필수 패키지가 누락되었습니다!"
        log_info "다음 명령어로 설치하세요:"
        echo "  sudo apt update"
        echo "  sudo apt install -y debootstrap qemu-user-static binfmt-support e2fsprogs"
        return 1
    fi

    return 0
}

check_device_connection() {
    log_section "디바이스 연결 점검"

    # ADB 설치 확인
    if ! command -v adb &>/dev/null; then
        log_error "adb가 설치되어 있지 않습니다"
        return 1
    fi

    local ver=$(adb --version | head -1)
    log_success "adb: $ver"

    # 디바이스 연결 확인
    if ! adb get-state &>/dev/null; then
        log_error "디바이스가 연결되어 있지 않습니다"
        log_info "USB 디버깅을 활성화하고 디바이스를 연결하세요"
        return 1
    fi

    log_success "Device connected: $(adb get-serialno)"

    return 0
}

check_magisk() {
    log_section "Magisk 점검"

    # Magisk 버전 확인
    local magisk_ver=$(adb shell "su -c 'magisk -v'" 2>/dev/null | tr -d '\r')

    if [ -z "$magisk_ver" ]; then
        log_error "Magisk가 설치되어 있지 않거나 접근할 수 없습니다"
        return 1
    fi

    log_success "Magisk version: $magisk_ver"

    # Magisk 버전 코드
    local magisk_code=$(adb shell "su -c 'magisk -c'" 2>/dev/null | grep -oP '\(\K[0-9]+' | tr -d '\r')

    if [ "$magisk_code" -lt 24000 ]; then
        log_warning "Magisk 버전이 24.0 미만입니다 (현재: $magisk_code)"
        log_warning "일부 기능이 작동하지 않을 수 있습니다"
    else
        log_success "Magisk version code: $magisk_code (24.0+ required: ✓)"
    fi

    # BusyBox 확인
    if adb shell "su -c '/data/adb/magisk/busybox --help'" &>/dev/null; then
        local bb_ver=$(adb shell "su -c '/data/adb/magisk/busybox --help'" 2>&1 | head -1 | grep -oP 'v[0-9.]+')
        log_success "BusyBox: $bb_ver (Magisk bundled)"
    else
        log_warning "BusyBox를 찾을 수 없습니다"
    fi

    return 0
}

check_disk_space() {
    log_section "디스크 공간 점검"

    # PC 디스크 공간
    local pc_available=$(df -h . | tail -1 | awk '{print $4}')
    local pc_used=$(df -h . | tail -1 | awk '{print $5}')
    log_info "PC: $pc_available available ($pc_used used)"

    # 디바이스 /data 공간
    local data_info=$(adb shell "df -h /data" 2>/dev/null | tail -1)
    local data_available=$(echo "$data_info" | awk '{print $4}')
    local data_used=$(echo "$data_info" | awk '{print $5}')
    local data_total=$(echo "$data_info" | awk '{print $2}')

    log_info "Device /data: $data_available available ($data_used used, Total: $data_total)"

    # 8GB 이상 여유 공간 확인
    local data_avail_gb=$(echo "$data_available" | sed 's/G//')

    if [ "${data_avail_gb%.*}" -lt 8 ]; then
        log_warning "/data 파티션 여유 공간이 부족할 수 있습니다 (권장: 8GB 이상)"
    else
        log_success "디스크 공간 충분 (8GB+ rootfs 생성 가능)"
    fi

    return 0
}

# ====================================================================
# 메인
# ====================================================================

main() {
    echo ""
    echo "=========================================="
    echo "  Phase 1 환경 점검"
    echo "  Samsung Galaxy A90 5G"
    echo "=========================================="
    echo ""

    local pc_ok=true
    local device_ok=true
    local magisk_ok=true

    # PC 환경 점검
    if ! check_pc_env; then
        pc_ok=false
    fi

    # 디바이스 연결 점검
    if ! check_device_connection; then
        device_ok=false
    fi

    # Magisk 점검 (디바이스 연결된 경우에만)
    if [ "$device_ok" = true ]; then
        if ! check_magisk; then
            magisk_ok=false
        fi

        check_disk_space
    fi

    # 최종 결과
    log_section "점검 결과"

    if [ "$pc_ok" = true ]; then
        log_success "PC 환경: 정상"
    else
        log_error "PC 환경: 문제 발생"
    fi

    if [ "$device_ok" = true ]; then
        log_success "디바이스 연결: 정상"
    else
        log_error "디바이스 연결: 문제 발생"
    fi

    if [ "$magisk_ok" = true ]; then
        log_success "Magisk: 정상"
    else
        log_error "Magisk: 문제 발생"
    fi

    echo ""

    if [ "$pc_ok" = true ] && [ "$device_ok" = true ] && [ "$magisk_ok" = true ]; then
        log_success "모든 환경 점검 완료! Rootfs 생성을 시작할 수 있습니다."
        echo ""
        log_info "다음 단계:"
        echo "  sudo ./scripts/utils/create_rootfs.sh 6144 debian bookworm"
        echo ""
        return 0
    else
        log_error "일부 환경에 문제가 있습니다. 위의 오류를 해결하세요."
        echo ""
        return 1
    fi
}

main "$@"
