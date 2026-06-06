#!/bin/bash
# debug_magisk.sh - Magisk Systemless Chroot 디버깅 도구
#
# 사용법: ./debug_magisk.sh [옵션]
# 옵션:
#   logs    - 모든 로그 출력
#   mounts  - 마운트 상태 확인
#   status  - Chroot 상태 확인
#   ssh     - SSH 서버 상태 확인
#   fix     - 일반적인 문제 자동 수정 시도
#   clean   - 모든 마운트 정리 및 초기화

set -e

# 색상 코드
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# ====================================================================
# 유틸리티 함수
# ====================================================================

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

check_adb() {
    if ! command -v adb &>/dev/null; then
        log_error "adb가 설치되어 있지 않습니다"
        exit 1
    fi

    if ! adb get-state &>/dev/null; then
        log_error "디바이스가 연결되어 있지 않습니다"
        log_info "USB 디버깅이 활성화되어 있는지 확인하세요"
        exit 1
    fi

    log_success "ADB 연결 확인"
}

# ====================================================================
# 디버깅 함수
# ====================================================================

show_logs() {
    log_section "Magisk Chroot 로그"

    log_info "Chroot 초기화 로그:"
    adb shell "su -c 'cat /data/adb/magisk_logs/chroot_init.log 2>/dev/null'" || \
        log_warning "초기화 로그 없음"

    echo ""
    log_info "Chroot 서비스 로그:"
    adb shell "su -c 'cat /data/adb/magisk_logs/chroot_service.log 2>/dev/null'" || \
        log_warning "서비스 로그 없음"

    echo ""
    log_info "최근 Magisk 로그 (50줄):"
    adb logcat -d | grep -i magisk | tail -50

    echo ""
    log_info "최근 커널 로그 (50줄):"
    adb shell "dmesg | tail -50"
}

show_mounts() {
    log_section "마운트 상태"

    log_info "Chroot 관련 마운트:"
    adb shell "su -c 'mount | grep linux_root'" 2>/dev/null || \
        log_warning "Chroot 마운트 없음"

    echo ""
    log_info "Rootfs 이미지 확인:"
    adb shell "su -c 'ls -lh /data/linux_root/'" 2>/dev/null || \
        log_error "Rootfs 디렉토리 없음"

    echo ""
    log_info "마운트 포인트 확인:"
    if adb shell "su -c 'mountpoint -q /data/linux_root/mnt'" 2>/dev/null; then
        log_success "/data/linux_root/mnt is mounted"
    else
        log_error "/data/linux_root/mnt is NOT mounted"
    fi
}

show_status() {
    log_section "Chroot 상태"

    log_info "상태 파일:"
    STATUS=$(adb shell "su -c 'cat /data/linux_root/status 2>/dev/null'" | tr -d '\r' || echo "NOT_FOUND")

    if [ "$STATUS" = "MOUNTED" ]; then
        log_success "Chroot 상태: MOUNTED"
    elif [ "$STATUS" = "RUNNING" ]; then
        log_success "Chroot 상태: RUNNING (서비스 실행 중)"
    else
        log_error "Chroot 상태: $STATUS"
    fi

    echo ""
    log_info "마운트 시간:"
    adb shell "su -c 'cat /data/linux_root/mount_time 2>/dev/null'" || \
        log_warning "마운트 시간 정보 없음"

    echo ""
    log_info "서비스 시작 시간:"
    adb shell "su -c 'cat /data/linux_root/service_time 2>/dev/null'" || \
        log_warning "서비스 시간 정보 없음"

    echo ""
    log_info "메모리 사용량:"
    adb shell "free -m"

    echo ""
    log_info "디스크 사용량:"
    adb shell "su -c 'df -h /data/linux_root/'" 2>/dev/null
}

show_ssh() {
    log_section "SSH 서버 상태"

    log_info "SSH 프로세스 확인:"
    adb shell "su -c 'chroot /data/linux_root/mnt /bin/bash -c \"ps aux | grep sshd\"'" 2>/dev/null || \
        log_warning "Chroot 환경에 접근할 수 없습니다"

    echo ""
    log_info "SSH 포트 리스닝 확인:"
    adb shell "su -c 'chroot /data/linux_root/mnt /bin/bash -c \"netstat -tlnp 2>/dev/null | grep :22\"'" 2>/dev/null || \
        log_warning "SSH 서버가 실행 중이 아닙니다"

    echo ""
    log_info "디바이스 IP 주소:"
    IP=$(adb shell "ip addr show wlan0 2>/dev/null | grep 'inet ' | awk '{print \$2}' | cut -d/ -f1" | tr -d '\r')

    if [ -n "$IP" ]; then
        log_success "IP 주소: $IP"
        echo ""
        log_info "SSH 접속 명령어:"
        echo "  ssh root@$IP"
    else
        log_error "IP 주소를 찾을 수 없습니다 (WiFi가 연결되어 있는지 확인)"
    fi
}

auto_fix() {
    log_section "자동 수정 시도"

    log_info "일반적인 문제를 자동으로 수정합니다..."

    # 1. 로그 디렉토리 생성
    log_info "[1/5] 로그 디렉토리 확인..."
    adb shell "su -c 'mkdir -p /data/adb/magisk_logs && chmod 755 /data/adb/magisk_logs'"
    log_success "로그 디렉토리 확인 완료"

    # 2. Rootfs 이미지 확인
    log_info "[2/5] Rootfs 이미지 확인..."
    if adb shell "su -c 'test -f /data/linux_root/debian_arm64.img'" 2>/dev/null; then
        log_success "Rootfs 이미지 존재"
        SIZE=$(adb shell "su -c 'du -h /data/linux_root/debian_arm64.img'" | awk '{print $1}' | tr -d '\r')
        log_info "  크기: $SIZE"
    else
        log_error "Rootfs 이미지 없음!"
        log_info "  create_rootfs.sh를 사용하여 이미지를 생성하고 전송하세요"
        return 1
    fi

    # 3. 이미지 무결성 확인
    log_info "[3/5] 이미지 무결성 확인..."
    adb shell "su -c 'e2fsck -n /data/linux_root/debian_arm64.img'" 2>/dev/null && \
        log_success "이미지 무결성 확인 완료" || \
        log_warning "이미지에 문제가 있을 수 있습니다"

    # 4. DNS 설정 확인
    log_info "[4/5] DNS 설정 확인..."
    if adb shell "su -c 'mountpoint -q /data/linux_root/mnt'" 2>/dev/null; then
        adb shell "su -c 'cat > /data/linux_root/mnt/etc/resolv.conf << EOF
nameserver 8.8.8.8
nameserver 8.8.4.4
EOF'" 2>/dev/null && log_success "DNS 설정 업데이트 완료"
    else
        log_warning "Chroot가 마운트되지 않아 DNS 설정을 건너뜁니다"
    fi

    # 5. SSH 키 확인
    log_info "[5/5] SSH 키 확인..."
    if adb shell "su -c 'mountpoint -q /data/linux_root/mnt'" 2>/dev/null; then
        adb shell "su -c 'chroot /data/linux_root/mnt /bin/bash -c \"
            if [ ! -f /etc/ssh/ssh_host_rsa_key ]; then
                ssh-keygen -A
                echo SSH 키 생성 완료
            else
                echo SSH 키 이미 존재
            fi
        \"'" 2>/dev/null && log_success "SSH 키 확인 완료"
    else
        log_warning "Chroot가 마운트되지 않아 SSH 키 확인을 건너뜁니다"
    fi

    log_success "자동 수정 완료!"
    log_info "문제가 지속되면 재부팅을 시도하세요: adb reboot"
}

clean_all() {
    log_section "정리 작업"

    log_warning "모든 Chroot 마운트를 해제하고 초기화합니다"
    read -p "계속하시겠습니까? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "취소되었습니다"
        return
    fi

    log_info "SSH 서버 중지..."
    adb shell "su -c 'chroot /data/linux_root/mnt /bin/bash -c \"pkill sshd\"'" 2>/dev/null || true

    log_info "Chroot 프로세스 종료..."
    adb shell "su -c '
        for pid in \$(lsof /data/linux_root/mnt 2>/dev/null | awk \"NR>1 {print \\\$2}\" | sort -u); do
            kill -9 \"\$pid\" 2>/dev/null || true
        done
    '" 2>/dev/null || true

    log_info "마운트 해제 중..."
    adb shell "su -c '
        umount -f -l /data/linux_root/mnt/vendor/firmware_mnt 2>/dev/null || true
        umount -f -l /data/linux_root/mnt/data 2>/dev/null || true
        umount -f -l /data/linux_root/mnt/dev/pts 2>/dev/null || true
        umount -f -l /data/linux_root/mnt/dev/shm 2>/dev/null || true
        umount -f -l /data/linux_root/mnt/dev 2>/dev/null || true
        umount -f -l /data/linux_root/mnt/proc 2>/dev/null || true
        umount -f -l /data/linux_root/mnt/sys 2>/dev/null || true
        umount -f -l /data/linux_root/mnt 2>/dev/null || true
    '" 2>/dev/null

    log_info "상태 초기화..."
    adb shell "su -c 'echo STOPPED > /data/linux_root/status'" 2>/dev/null

    log_success "정리 완료!"
    log_info "재부팅 후 Chroot가 자동으로 다시 마운트됩니다"
}

show_help() {
    cat << 'EOF'
╔══════════════════════════════════════════════════════════╗
║     Magisk Systemless Chroot 디버깅 도구                ║
╚══════════════════════════════════════════════════════════╝

사용법: ./debug_magisk.sh [옵션]

옵션:
  logs      모든 로그 출력 (init, service, magisk, kernel)
  mounts    마운트 상태 확인
  status    Chroot 상태 및 시스템 리소스 확인
  ssh       SSH 서버 상태 및 IP 주소 확인
  fix       일반적인 문제 자동 수정 시도
  clean     모든 마운트 정리 및 초기화
  help      이 도움말 표시

예제:
  ./debug_magisk.sh logs      # 모든 로그 확인
  ./debug_magisk.sh status    # 현재 상태 확인
  ./debug_magisk.sh fix       # 문제 자동 수정
  ./debug_magisk.sh clean     # 완전 초기화

문제 해결 순서:
  1. ./debug_magisk.sh status   # 현재 상태 확인
  2. ./debug_magisk.sh logs     # 로그에서 오류 찾기
  3. ./debug_magisk.sh fix      # 자동 수정 시도
  4. adb reboot                 # 재부팅
  5. ./debug_magisk.sh ssh      # SSH 접속 정보 확인

EOF
}

# ====================================================================
# 메인
# ====================================================================

main() {
    local cmd=${1:-help}

    # ADB 연결 확인 (help 제외)
    if [ "$cmd" != "help" ]; then
        check_adb
    fi

    case "$cmd" in
        logs)
            show_logs
            ;;
        mounts)
            show_mounts
            ;;
        status)
            show_status
            ;;
        ssh)
            show_ssh
            ;;
        fix)
            auto_fix
            ;;
        clean)
            clean_all
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            log_error "알 수 없는 옵션: $cmd"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

main "$@"
