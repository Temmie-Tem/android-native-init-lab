#!/system/bin/sh
# boot_chroot.sh - Magisk service.d script
#
# 이 스크립트는 Android 부팅 완료 후 실행됩니다 (NON-BLOCKING)
# - 실행 시점: 부팅 완료 후 (타임아웃 없음)
# - 목적: SSH 서버 시작 및 추가 서비스 초기화
#
# post-fs-data.sh에서 이미 chroot 마운트는 완료된 상태입니다

# ====================================================================
# 설정
# ====================================================================

# 경로 설정
CHROOT_PATH="/data/linux_root"
CHROOT_MNT="$CHROOT_PATH/mnt"

# 로그 설정
LOG_DIR="/data/adb/magisk_logs"
LOGFILE="$LOG_DIR/chroot_service.log"

# BusyBox 경로
BUSYBOX="/data/adb/magisk/busybox"

# ====================================================================
# 로깅 함수
# ====================================================================

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOGFILE"
}

log_error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [ERROR] $1" >> "$LOGFILE"
}

# ====================================================================
# 초기화
# ====================================================================

# 로그 파일 초기화
echo "========================================" > "$LOGFILE"
echo "Systemless Chroot Service - $(date)" >> "$LOGFILE"
echo "========================================" >> "$LOGFILE"

log "Starting chroot services..."

# ====================================================================
# Step 1: Chroot 마운트 상태 확인
# ====================================================================

log "[Step 1/5] Checking chroot mount status..."

# .chroot_ready 파일 확인 (post-fs-data.sh에서 생성)
if [ ! -f "$CHROOT_PATH/.chroot_ready" ]; then
    log_error "Chroot not ready (post-fs-data.sh failed?)"
    log_error "Check: /data/adb/magisk_logs/chroot_init.log"
    exit 1
fi

# 마운트 포인트 확인
if ! $BUSYBOX mountpoint -q "$CHROOT_MNT" 2>/dev/null; then
    log_error "Chroot not mounted: $CHROOT_MNT"
    exit 1
fi

log "[Step 1/5] Chroot is mounted and ready"

# ====================================================================
# Step 2: SSH 호스트 키 생성 (첫 실행 시)
# ====================================================================

log "[Step 2/5] Checking SSH host keys..."

# SSH 호스트 키가 없으면 생성
if [ ! -f "$CHROOT_MNT/etc/ssh/ssh_host_rsa_key" ]; then
    log "  Generating SSH host keys (first boot)..."

    $BUSYBOX chroot "$CHROOT_MNT" /bin/bash -c "
        ssh-keygen -A 2>&1
    " >> "$LOGFILE" 2>&1

    if [ $? -eq 0 ]; then
        log "  SSH host keys generated successfully"
    else
        log_error "Failed to generate SSH host keys"
    fi
else
    log "  SSH host keys already exist"
fi

log "[Step 2/5] SSH keys ready"

# ====================================================================
# Step 3: SSH 서버 중지 (기존 프로세스)
# ====================================================================

log "[Step 3/5] Stopping existing SSH server..."

# chroot 내부의 SSH 프로세스 찾기 및 종료
$BUSYBOX chroot "$CHROOT_MNT" /bin/bash -c "
    if [ -f /var/run/sshd.pid ]; then
        kill \$(cat /var/run/sshd.pid) 2>/dev/null || true
        rm -f /var/run/sshd.pid
    fi

    # 모든 sshd 프로세스 강제 종료
    pkill -9 sshd 2>/dev/null || true
" 2>>"$LOGFILE"

# 잠시 대기
sleep 2

log "[Step 3/5] Existing SSH servers stopped"

# ====================================================================
# Step 4: SSH 서버 시작
# ====================================================================

log "[Step 4/5] Starting SSH server..."

# SSH 디렉토리 권한 설정
$BUSYBOX chroot "$CHROOT_MNT" /bin/bash -c "
    mkdir -p /var/run/sshd
    chmod 755 /var/run/sshd

    # privilege separation 디렉토리
    mkdir -p /run/sshd
    chmod 755 /run/sshd
" 2>>"$LOGFILE"

# SSH 서버 시작
$BUSYBOX chroot "$CHROOT_MNT" /usr/sbin/sshd -E /var/log/sshd.log 2>>"$LOGFILE"

if [ $? -eq 0 ]; then
    log "  SSH server started successfully"
else
    log_error "Failed to start SSH server"
    log_error "Check: chroot /data/linux_root/mnt /var/log/sshd.log"
fi

log "[Step 4/5] SSH service handled"

# ====================================================================
# Step 5: 네트워크 정보 로깅
# ====================================================================

log "[Step 5/5] Logging network information..."

# WiFi IP 주소 확인
WIFI_IP=$(ip -4 addr show wlan0 2>/dev/null | grep inet | awk '{print $2}' | cut -d/ -f1)

if [ -n "$WIFI_IP" ]; then
    log "  WiFi IP: $WIFI_IP"
    log "  SSH Connection: ssh root@$WIFI_IP"
else
    log "  WiFi not connected yet"
fi

log "[Step 5/5] Network info logged"

# ====================================================================
# 완료
# ====================================================================

log "========================================="
log "Chroot services started successfully!"
log "========================================="

if [ -n "$WIFI_IP" ]; then
    log "SSH: ssh root@$WIFI_IP (key-based auth)"
else
    log "Connect to WiFi and check IP with: ip addr show wlan0"
fi

log ""

exit 0
