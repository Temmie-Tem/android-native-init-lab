#!/system/bin/sh
# post-fs-data.sh - Magisk post-fs-data hook
#
# 이 스크립트는 Android 부팅 시 자동으로 실행됩니다 (BLOCKING)
# - 실행 시점: /data 파티션 마운트 직후
# - 타임아웃: 40초 (초과 시 부팅 실패 위험)
# - 목적: chroot 환경 마운트 및 기본 설정
#
# 중요: 이 스크립트는 최대한 빠르게 실행되어야 합니다!

MODDIR=${0%/*}

# ====================================================================
# 설정
# ====================================================================

# 경로 설정
CHROOT_PATH="/data/linux_root"
CHROOT_IMG="$CHROOT_PATH/debian_bookworm_arm64.img"
CHROOT_MNT="$CHROOT_PATH/mnt"

# 로그 설정
LOG_DIR="/data/adb/magisk_logs"
LOGFILE="$LOG_DIR/chroot_init.log"

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

# 로그 디렉토리 생성
mkdir -p "$LOG_DIR" 2>/dev/null

# 로그 파일 초기화
echo "========================================" > "$LOGFILE"
echo "Systemless Chroot Init - $(date)" >> "$LOGFILE"
echo "========================================" >> "$LOGFILE"

log "Starting chroot initialization..."

# ====================================================================
# Step 1: 이전 마운트 정리 (매우 중요!)
# ====================================================================

log "[Step 1/12] Cleaning up previous mounts..."

# chroot 내부 마운트 정리 (역순으로)
umount_chroot() {
    # /dev/pts, /dev, /proc, /sys 순서로 언마운트
    for mnt in \
        "$CHROOT_MNT/dev/pts" \
        "$CHROOT_MNT/dev" \
        "$CHROOT_MNT/proc" \
        "$CHROOT_MNT/sys" \
        "$CHROOT_MNT/vendor/firmware_mnt" \
        "$CHROOT_MNT/sdcard" \
        "$CHROOT_MNT"; do

        if $BUSYBOX mountpoint -q "$mnt" 2>/dev/null; then
            log "  Unmounting: $mnt"
            $BUSYBOX umount -f -l "$mnt" 2>/dev/null || true
        fi
    done
}

# 기존 마운트 정리 실행
umount_chroot

log "[Step 1/12] Cleanup completed"

# ====================================================================
# Step 2: 필수 디렉토리 확인
# ====================================================================

log "[Step 2/12] Checking required directories..."

if [ ! -d "$CHROOT_PATH" ]; then
    log_error "CHROOT_PATH does not exist: $CHROOT_PATH"
    exit 1
fi

if [ ! -f "$CHROOT_IMG" ]; then
    log_error "Rootfs image not found: $CHROOT_IMG"
    exit 1
fi

# 마운트 포인트 생성
mkdir -p "$CHROOT_MNT" 2>/dev/null

log "[Step 2/12] Directories OK"

# ====================================================================
# Step 3: 이미지 파일 검증
# ====================================================================

log "[Step 3/12] Validating rootfs image..."

# 파일 크기 확인
IMG_SIZE=$(ls -l "$CHROOT_IMG" | awk '{print $5}')
log "  Image size: $IMG_SIZE bytes"

if [ "$IMG_SIZE" -lt 1000000000 ]; then
    log_error "Image file too small (corrupted?): $IMG_SIZE bytes"
    exit 1
fi

log "[Step 3/12] Image validation OK"

# ====================================================================
# Step 4: Rootfs 이미지 마운트
# ====================================================================

log "[Step 4/12] Mounting rootfs image..."

# 30초 타임아웃으로 마운트 시도
if ! timeout 30 $BUSYBOX mount -o noatime,nodiratime "$CHROOT_IMG" "$CHROOT_MNT" 2>>"$LOGFILE"; then
    log_error "Failed to mount rootfs image"
    exit 1
fi

log "[Step 4/12] Rootfs mounted successfully"

# ====================================================================
# Step 5: Rootfs 무결성 확인
# ====================================================================

log "[Step 5/12] Verifying rootfs integrity..."

# 필수 디렉토리 확인
for dir in bin etc usr var home root; do
    if [ ! -d "$CHROOT_MNT/$dir" ]; then
        log_error "Missing critical directory: /$dir"
        umount_chroot
        exit 1
    fi
done

log "[Step 5/12] Rootfs integrity OK"

# ====================================================================
# Step 6: /dev 마운트 (디바이스 노드)
# ====================================================================

log "[Step 6/12] Mounting /dev..."

mkdir -p "$CHROOT_MNT/dev" 2>/dev/null

# /dev를 recursive bind mount (--rbind)
if ! $BUSYBOX mount --rbind /dev "$CHROOT_MNT/dev" 2>>"$LOGFILE"; then
    log_error "Failed to mount /dev"
    umount_chroot
    exit 1
fi

# slave propagation 설정 (중요!)
$BUSYBOX mount --make-rslave "$CHROOT_MNT/dev" 2>>"$LOGFILE" || true

log "[Step 6/12] /dev mounted"

# ====================================================================
# Step 7: /proc 마운트 (프로세스 정보)
# ====================================================================

log "[Step 7/12] Mounting /proc..."

mkdir -p "$CHROOT_MNT/proc" 2>/dev/null

if ! $BUSYBOX mount -t proc proc "$CHROOT_MNT/proc" 2>>"$LOGFILE"; then
    log_error "Failed to mount /proc"
    umount_chroot
    exit 1
fi

log "[Step 7/12] /proc mounted"

# ====================================================================
# Step 8: /sys 마운트 (시스템 정보)
# ====================================================================

log "[Step 8/12] Mounting /sys..."

mkdir -p "$CHROOT_MNT/sys" 2>/dev/null

if ! $BUSYBOX mount --rbind /sys "$CHROOT_MNT/sys" 2>>"$LOGFILE"; then
    log_error "Failed to mount /sys"
    umount_chroot
    exit 1
fi

$BUSYBOX mount --make-rslave "$CHROOT_MNT/sys" 2>>"$LOGFILE" || true

log "[Step 8/12] /sys mounted"

# ====================================================================
# Step 9: /dev/pts 마운트 (pseudo-terminal)
# ====================================================================

log "[Step 9/12] Mounting /dev/pts..."

mkdir -p "$CHROOT_MNT/dev/pts" 2>/dev/null

if ! $BUSYBOX mount -t devpts devpts "$CHROOT_MNT/dev/pts" 2>>"$LOGFILE"; then
    log "  Warning: Failed to mount /dev/pts (non-critical)"
else
    log "[Step 9/12] /dev/pts mounted"
fi

# ====================================================================
# Step 10: DNS 설정
# ====================================================================

log "[Step 10/12] Configuring DNS..."

cat > "$CHROOT_MNT/etc/resolv.conf" << 'EOF'
nameserver 1.1.1.1
nameserver 1.0.0.1
nameserver 8.8.8.8
EOF

log "[Step 10/12] DNS configured"

# ====================================================================
# Step 11: WiFi 펌웨어 마운트 (선택적)
# ====================================================================

log "[Step 11/12] Mounting WiFi firmware (optional)..."

if [ -d "/vendor/firmware_mnt" ]; then
    mkdir -p "$CHROOT_MNT/vendor/firmware_mnt" 2>/dev/null

    if $BUSYBOX mount --bind /vendor/firmware_mnt "$CHROOT_MNT/vendor/firmware_mnt" 2>>"$LOGFILE"; then
        log "  WiFi firmware mounted"
    else
        log "  WiFi firmware mount failed (non-critical)"
    fi
else
    log "  /vendor/firmware_mnt not found (skip)"
fi

log "[Step 11/12] WiFi firmware handled"

# ====================================================================
# Step 12: SELinux 정책 조작 (Magisk v25+)
# ====================================================================

log "[Step 12/12] Configuring SELinux policy..."

# supolicy 명령어 확인
if command -v supolicy >/dev/null 2>&1; then
    # su 프로세스에 chroot 권한 부여
    supolicy --live \
        'allow su su capability { sys_admin sys_chroot dac_override net_admin }' \
        2>>"$LOGFILE" || log "  supolicy failed (non-critical)"

    log "  SELinux policy updated"
else
    log "  supolicy not found (skip)"
fi

log "[Step 12/12] SELinux configured"

# ====================================================================
# 완료
# ====================================================================

log "========================================="
log "Chroot initialization completed successfully!"
log "========================================="
log "Mount point: $CHROOT_MNT"
log "To enter chroot: bootlinux"
log ""

# 성공 표시 파일 생성
touch "$CHROOT_PATH/.chroot_ready"

exit 0