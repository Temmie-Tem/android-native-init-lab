#!/system/bin/sh
# ====================================================================
# Headless Android 검증 스크립트
# ====================================================================
# 목적: 각 Stage 완료 후 시스템 상태 검증
# 사용법: adb shell sh /data/local/tmp/verify_headless.sh
# ====================================================================

LOGFILE="/data/local/tmp/headless_verify.log"

# ====================================================================
# 로그 초기화
# ====================================================================

echo "=========================================" > "$LOGFILE"
echo "Headless Android Verification" >> "$LOGFILE"
echo "=========================================" >> "$LOGFILE"
echo "" >> "$LOGFILE"
echo "Started: $(date)" >> "$LOGFILE"
echo "" >> "$LOGFILE"

# ====================================================================
# 1. 시스템 부팅 상태 확인
# ====================================================================

echo "1. Boot Status" | tee -a "$LOGFILE"
echo "----------------------------------------" >> "$LOGFILE"

BOOT_COMPLETED=$(getprop sys.boot_completed)
if [ "$BOOT_COMPLETED" = "1" ]; then
    echo "  ✓ Boot completed" | tee -a "$LOGFILE"
else
    echo "  ✗ Boot not completed" | tee -a "$LOGFILE"
fi

echo "" >> "$LOGFILE"

# ====================================================================
# 2. RAM 사용량 측정
# ====================================================================

echo "2. RAM Usage" | tee -a "$LOGFILE"
echo "----------------------------------------" >> "$LOGFILE"

free -h >> "$LOGFILE"
free -h | head -2

echo "" >> "$LOGFILE"

# RAM 사용량 MB로 계산
TOTAL_RAM=$(free -m | awk 'NR==2 {print $2}')
USED_RAM=$(free -m | awk 'NR==2 {print $3}')

echo "  Total: ${TOTAL_RAM}MB" | tee -a "$LOGFILE"
echo "  Used: ${USED_RAM}MB" | tee -a "$LOGFILE"

# 목표 달성 여부 판단
if [ "$USED_RAM" -lt 1200 ]; then
    echo "  ✓ RAM usage is excellent (< 1200MB)" | tee -a "$LOGFILE"
elif [ "$USED_RAM" -lt 1500 ]; then
    echo "  ✓ RAM usage is good (< 1500MB)" | tee -a "$LOGFILE"
elif [ "$USED_RAM" -lt 2000 ]; then
    echo "  ⚠ RAM usage is acceptable (< 2000MB)" | tee -a "$LOGFILE"
else
    echo "  ✗ RAM usage is high (>= 2000MB)" | tee -a "$LOGFILE"
fi

echo "" >> "$LOGFILE"

# ====================================================================
# 3. WiFi 연결 상태 확인
# ====================================================================

echo "3. WiFi Status" | tee -a "$LOGFILE"
echo "----------------------------------------" >> "$LOGFILE"

WIFI_STATE=$(getprop wlan.driver.status)
echo "  WiFi Driver: $WIFI_STATE" | tee -a "$LOGFILE"

if ip addr show wlan0 2>/dev/null | grep -q "inet "; then
    IP_ADDR=$(ip addr show wlan0 | grep "inet " | awk '{print $2}')
    echo "  ✓ WiFi connected: $IP_ADDR" | tee -a "$LOGFILE"
else
    echo "  ✗ WiFi not connected" | tee -a "$LOGFILE"
fi

echo "" >> "$LOGFILE"

# ====================================================================
# 4. 핵심 서비스 상태 확인
# ====================================================================

echo "4. Essential Services" | tee -a "$LOGFILE"
echo "----------------------------------------" >> "$LOGFILE"

# 필수 프로세스 목록
ESSENTIAL_PROCS="system_server surfaceflinger netd wpa_supplicant adbd zygote"

for proc in $ESSENTIAL_PROCS; do
    if ps -A | grep -q "$proc"; then
        echo "  ✓ $proc is running" | tee -a "$LOGFILE"
    else
        echo "  ✗ $proc is NOT running" | tee -a "$LOGFILE"
    fi
done

echo "" >> "$LOGFILE"

# ====================================================================
# 5. SSH 서버 상태 확인
# ====================================================================

echo "5. SSH Server (Chroot)" | tee -a "$LOGFILE"
echo "----------------------------------------" >> "$LOGFILE"

# Chroot 마운트 확인
if mount | grep -q "/data/linux_root"; then
    echo "  ✓ Chroot is mounted" | tee -a "$LOGFILE"

    # SSH 프로세스 확인
    if ps -A | grep -q "sshd"; then
        SSH_PID=$(ps -A | grep "sshd" | grep -v grep | head -1 | awk '{print $2}')
        echo "  ✓ SSH server is running (PID: $SSH_PID)" | tee -a "$LOGFILE"
    else
        echo "  ✗ SSH server is NOT running" | tee -a "$LOGFILE"
    fi
else
    echo "  ✗ Chroot is NOT mounted" | tee -a "$LOGFILE"
fi

echo "" >> "$LOGFILE"

# ====================================================================
# 6. 비활성화된 패키지 확인
# ====================================================================

echo "6. Disabled Packages" | tee -a "$LOGFILE"
echo "----------------------------------------" >> "$LOGFILE"

# 주요 GUI 패키지 상태
GUI_PACKAGES="com.android.systemui com.sec.android.app.launcher"

DISABLED_COUNT=0

for pkg in $GUI_PACKAGES; do
    if pm list packages -d | grep -q "$pkg"; then
        echo "  ✓ $pkg is disabled" | tee -a "$LOGFILE"
        DISABLED_COUNT=$((DISABLED_COUNT + 1))
    else
        echo "  - $pkg is enabled" | tee -a "$LOGFILE"
    fi
done

if [ "$DISABLED_COUNT" -eq 0 ]; then
    echo "" >> "$LOGFILE"
    echo "  No GUI packages disabled (stock Android)" | tee -a "$LOGFILE"
fi

echo "" >> "$LOGFILE"

# ====================================================================
# 7. 네트워크 연결 테스트
# ====================================================================

echo "7. Network Connectivity" | tee -a "$LOGFILE"
echo "----------------------------------------" >> "$LOGFILE"

# Ping 테스트
if ping -c 3 8.8.8.8 > /dev/null 2>&1; then
    echo "  ✓ Internet connectivity OK (ping 8.8.8.8)" | tee -a "$LOGFILE"
else
    echo "  ✗ Internet connectivity FAILED" | tee -a "$LOGFILE"
fi

echo "" >> "$LOGFILE"

# ====================================================================
# 8. 프로세스 수 및 부하 확인
# ====================================================================

echo "8. System Load" | tee -a "$LOGFILE"
echo "----------------------------------------" >> "$LOGFILE"

PROC_COUNT=$(ps -A | wc -l)
echo "  Total processes: $PROC_COUNT" | tee -a "$LOGFILE"

UPTIME_INFO=$(uptime)
echo "  Uptime: $UPTIME_INFO" | tee -a "$LOGFILE"

echo "" >> "$LOGFILE"

# ====================================================================
# 결과 요약
# ====================================================================

echo "" >> "$LOGFILE"
echo "=========================================" >> "$LOGFILE"
echo "Verification Completed" >> "$LOGFILE"
echo "=========================================" >> "$LOGFILE"
echo "" >> "$LOGFILE"
echo "Finished: $(date)" >> "$LOGFILE"
echo "" >> "$LOGFILE"
echo "Summary:" >> "$LOGFILE"
echo "- RAM Usage: ${USED_RAM}MB / ${TOTAL_RAM}MB" >> "$LOGFILE"
echo "- WiFi: $(ip addr show wlan0 2>/dev/null | grep "inet " | awk '{print $2}' || echo 'Not connected')" >> "$LOGFILE"
echo "- SSH: $(ps -A | grep -q "sshd" && echo 'Running' || echo 'Not running')" >> "$LOGFILE"
echo "- GUI Disabled: $DISABLED_COUNT packages" >> "$LOGFILE"
echo "" >> "$LOGFILE"

# ====================================================================
# 화면 출력
# ====================================================================

echo ""
echo "========================================="
echo "Verification Summary"
echo "========================================="
echo ""
echo "RAM: ${USED_RAM}MB / ${TOTAL_RAM}MB"
echo "WiFi: $(ip addr show wlan0 2>/dev/null | grep "inet " | awk '{print $2}' || echo 'Not connected')"
echo "SSH: $(ps -A | grep -q "sshd" && echo 'Running' || echo 'Not running')"
echo "Processes: $PROC_COUNT"
echo ""
echo "Full report: $LOGFILE"
echo ""

# Stage 판단
if [ "$DISABLED_COUNT" -eq 0 ]; then
    echo "Current State: Stock Android (before Stage 1)"
elif [ "$USED_RAM" -gt 1800 ]; then
    echo "Current State: After Stage 1 (GUI disabled)"
elif [ "$USED_RAM" -gt 1400 ]; then
    echo "Current State: After Stage 2 (Samsung disabled)"
elif [ "$USED_RAM" -gt 1100 ]; then
    echo "Current State: After Stage 3 (Google disabled)"
else
    echo "Current State: After Stage 4 (All apps disabled)"
fi

echo ""
