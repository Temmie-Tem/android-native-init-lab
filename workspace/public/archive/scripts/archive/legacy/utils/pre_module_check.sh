#!/bin/bash
# pre_module_check.sh - Magisk 모듈 작성 전 사전 점검
#
# 사용법: ./pre_module_check.sh

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
# 점검 함수
# ====================================================================

check_device_connection() {
    log_section "1. 디바이스 연결 확인"

    if ! adb get-state &>/dev/null; then
        log_error "디바이스가 연결되어 있지 않습니다"
        return 1
    fi

    local serial=$(adb get-serialno)
    log_success "Device: $serial"

    return 0
}

check_rootfs_image() {
    log_section "2. Rootfs 이미지 확인"

    # /data/linux_root 디렉토리 확인
    if ! adb shell "su -c 'test -d /data/linux_root'" 2>/dev/null; then
        log_error "/data/linux_root 디렉토리가 존재하지 않습니다"
        return 1
    fi

    log_success "/data/linux_root 디렉토리 존재"

    # 이미지 파일 확인
    local img_path=$(adb shell "su -c 'ls /data/linux_root/*.img 2>/dev/null'" 2>/dev/null | tr -d '\r')

    if [ -z "$img_path" ]; then
        log_error "Rootfs 이미지를 찾을 수 없습니다"
        log_info "다음 명령으로 이미지를 전송하세요:"
        echo "  adb push debian_bookworm_arm64.img /sdcard/"
        echo "  adb shell \"su -c 'mv /sdcard/debian_bookworm_arm64.img /data/linux_root/'\""
        return 1
    fi

    log_success "Rootfs 이미지: $img_path"

    # 이미지 크기 확인
    local img_size=$(adb shell "su -c 'ls -lh $img_path'" 2>/dev/null | awk '{print $5}' | tr -d '\r')
    log_info "이미지 크기: $img_size"

    # 이미지 무결성 검사
    log_info "이미지 무결성 검사 중..."
    if adb shell "su -c 'e2fsck -n $img_path'" &>/dev/null; then
        log_success "이미지 무결성: 정상"
    else
        log_warning "이미지 파일 시스템 검사 실패 (무시 가능)"
    fi

    return 0
}

check_magisk_structure() {
    log_section "3. Magisk 구조 확인"

    # /data/adb/modules 확인
    if ! adb shell "su -c 'test -d /data/adb/modules'" 2>/dev/null; then
        log_error "/data/adb/modules 디렉토리가 존재하지 않습니다"
        log_error "Magisk가 제대로 설치되지 않았을 수 있습니다"
        return 1
    fi

    log_success "/data/adb/modules 디렉토리 존재"

    # 기존 systemless_chroot 모듈 확인
    if adb shell "su -c 'test -d /data/adb/modules/systemless_chroot'" 2>/dev/null; then
        log_warning "기존 systemless_chroot 모듈이 이미 존재합니다"
        log_info "기존 모듈을 삭제하시겠습니까? (수동으로 삭제하세요)"
        echo "  adb shell \"su -c 'rm -rf /data/adb/modules/systemless_chroot'\""
    else
        log_success "systemless_chroot 모듈 없음 (정상)"
    fi

    # /data/adb/service.d 확인
    if ! adb shell "su -c 'test -d /data/adb/service.d'" 2>/dev/null; then
        log_info "/data/adb/service.d 디렉토리 생성 필요"
        adb shell "su -c 'mkdir -p /data/adb/service.d'" 2>/dev/null
        log_success "/data/adb/service.d 생성 완료"
    else
        log_success "/data/adb/service.d 디렉토리 존재"
    fi

    # /data/adb/magisk_logs 확인
    if ! adb shell "su -c 'test -d /data/adb/magisk_logs'" 2>/dev/null; then
        adb shell "su -c 'mkdir -p /data/adb/magisk_logs'" 2>/dev/null
        log_success "/data/adb/magisk_logs 생성 완료"
    else
        log_success "/data/adb/magisk_logs 디렉토리 존재"
    fi

    return 0
}

check_mount_points() {
    log_section "4. 마운트 포인트 확인"

    # 기존 마운트 확인
    local existing_mounts=$(adb shell "su -c 'mount | grep linux_root'" 2>/dev/null | tr -d '\r')

    if [ -n "$existing_mounts" ]; then
        log_warning "기존 linux_root 관련 마운트가 존재합니다:"
        echo "$existing_mounts" | while read line; do
            echo "  $line"
        done
        log_info "정리가 필요할 수 있습니다"
    else
        log_success "기존 마운트 없음 (정상)"
    fi

    # /data/linux_root/mnt 디렉토리 확인
    if ! adb shell "su -c 'test -d /data/linux_root/mnt'" 2>/dev/null; then
        adb shell "su -c 'mkdir -p /data/linux_root/mnt'" 2>/dev/null
        log_success "/data/linux_root/mnt 생성 완료"
    else
        log_success "/data/linux_root/mnt 디렉토리 존재"
    fi

    return 0
}

check_busybox_commands() {
    log_section "5. BusyBox 필수 명령어 확인"

    local busybox="/data/adb/magisk/busybox"
    local required_cmds=("mount" "umount" "chroot" "grep" "awk" "sed")

    local all_ok=true

    for cmd in "${required_cmds[@]}"; do
        if adb shell "su -c '$busybox $cmd --help'" &>/dev/null; then
            echo -e "  ${GREEN}✓${NC} $cmd"
        else
            echo -e "  ${RED}✗${NC} $cmd"
            all_ok=false
        fi
    done

    if [ "$all_ok" = true ]; then
        log_success "모든 필수 BusyBox 명령어 사용 가능"
    else
        log_error "일부 BusyBox 명령어를 사용할 수 없습니다"
        return 1
    fi

    return 0
}

check_selinux_status() {
    log_section "6. SELinux 상태 확인"

    local selinux_status=$(adb shell "getenforce" 2>/dev/null | tr -d '\r')

    log_info "SELinux 모드: $selinux_status"

    if [ "$selinux_status" = "Enforcing" ]; then
        log_warning "SELinux가 Enforcing 모드입니다"
        log_info "Magisk supolicy로 정책을 조작할 수 있습니다"
    elif [ "$selinux_status" = "Permissive" ]; then
        log_success "SELinux가 Permissive 모드입니다 (개발에 유리)"
    else
        log_warning "SELinux 상태를 확인할 수 없습니다"
    fi

    # supolicy 명령어 확인
    if adb shell "su -c 'which supolicy'" &>/dev/null; then
        log_success "supolicy 명령어 사용 가능"
    else
        log_warning "supolicy 명령어를 찾을 수 없습니다 (Magisk v25+ 필요)"
    fi

    return 0
}

check_disk_space() {
    log_section "7. 디스크 공간 확인"

    local data_info=$(adb shell "df -h /data" 2>/dev/null | tail -1)
    local data_available=$(echo "$data_info" | awk '{print $4}' | tr -d '\r')
    local data_used=$(echo "$data_info" | awk '{print $5}' | tr -d '\r')

    log_info "/data: $data_available 여유 공간 (사용률: $data_used)"

    # 최소 2GB 여유 공간 확인
    local avail_gb=$(echo "$data_available" | sed 's/G//' | sed 's/M/0./')

    if (( $(echo "$avail_gb < 2" | bc -l 2>/dev/null || echo 0) )); then
        log_warning "/data 파티션 여유 공간이 부족합니다 (최소 2GB 권장)"
    else
        log_success "디스크 공간 충분"
    fi

    return 0
}

check_module_structure() {
    log_section "8. 모듈 구조 파일 확인"

    local module_dir="/home/temmie/A90_5G_rooting/scripts/magisk_module/systemless_chroot"

    if [ ! -d "$module_dir" ]; then
        log_error "모듈 디렉토리가 존재하지 않습니다: $module_dir"
        return 1
    fi

    log_success "모듈 디렉토리 존재"

    # 필수 파일 확인
    local required_files=(
        "module.prop"
    )

    for file in "${required_files[@]}"; do
        if [ -f "$module_dir/$file" ]; then
            echo -e "  ${GREEN}✓${NC} $file"
        else
            echo -e "  ${YELLOW}!${NC} $file (생성 필요)"
        fi
    done

    # 필수 디렉토리 확인
    local required_dirs=(
        "META-INF/com/google/android"
        "system/bin"
        "service.d"
    )

    for dir in "${required_dirs[@]}"; do
        if [ -d "$module_dir/$dir" ]; then
            echo -e "  ${GREEN}✓${NC} $dir/"
        else
            echo -e "  ${YELLOW}!${NC} $dir/ (생성 필요)"
        fi
    done

    return 0
}

# ====================================================================
# 메인
# ====================================================================

main() {
    echo ""
    echo "=========================================="
    echo "  Magisk 모듈 작성 전 사전 점검"
    echo "  Phase 3 준비 상태 확인"
    echo "=========================================="
    echo ""

    local all_ok=true

    if ! check_device_connection; then
        all_ok=false
    fi

    if ! check_rootfs_image; then
        all_ok=false
    fi

    if ! check_magisk_structure; then
        all_ok=false
    fi

    if ! check_mount_points; then
        all_ok=false
    fi

    if ! check_busybox_commands; then
        all_ok=false
    fi

    check_selinux_status

    check_disk_space

    if ! check_module_structure; then
        all_ok=false
    fi

    # 최종 결과
    log_section "점검 결과"

    if [ "$all_ok" = true ]; then
        log_success "모든 사전 점검 완료! Magisk 모듈 작성을 시작할 수 있습니다."
        echo ""
        log_info "다음 단계: Phase 3 - Magisk 모듈 작성"
        echo "  1. post-fs-data.sh 작성 (chroot 마운트)"
        echo "  2. service.d/boot_chroot.sh 작성 (SSH 시작)"
        echo "  3. 유틸리티 스크립트 작성"
        echo ""
        return 0
    else
        log_error "일부 점검에서 문제가 발견되었습니다. 위의 오류를 해결하세요."
        echo ""
        return 1
    fi
}

main "$@"