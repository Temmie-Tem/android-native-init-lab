# Headless Android Scripts - 실행 가이드

## 📋 개요

이 스크립트들은 Samsung Galaxy A90 5G에서 Android GUI를 제거하여 순수 Linux 환경만 남기는 작업을 자동화합니다.

**목표**: RAM 사용량을 2.5GB에서 1.0GB 이하로 줄이기 (60% 절감)

---

## 📁 스크립트 목록

### 기본 버전 (Generic)

| 파일 | 목적 | RAM 절감 | 위험도 |
|------|------|---------|--------|
| `disable_gui.sh` | Stage 1: GUI 제거 | ~600MB | 낮음 |
| `disable_samsung.sh` | Stage 2: Samsung 서비스 제거 | ~400MB | 낮음 |
| `disable_google.sh` | Stage 3: Google 서비스 제거 | ~300MB | 중간 ⚠️ |
| `disable_apps.sh` | Stage 4: 불필요한 앱 제거 | ~200MB | 낮음 |

### ✨ 최적화 버전 (Optimized - 권장)

**2025-11-15 패키지 스캔 기반**

| 파일 | 목적 | 패키지 수 | RAM 절감 | 위험도 |
|------|------|---------|---------|--------|
| `disable_gui_optimized.sh` | Stage 1: GUI 제거 (실제 25개) | 25개 | ~600MB | 낮음 |
| `disable_samsung_optimized.sh` | Stage 2: Samsung 서비스 제거 (실제 80+개) | 80+개 | ~400MB | 낮음 |
| `disable_google_optimized.sh` | Stage 3: Google 서비스 제거 (실제 20+개) | 20+개 | ~300MB | 중간 ⚠️ |
| `disable_apps_optimized.sh` | Stage 4: 불필요한 앱 제거 (실제 40+개) | 40+개 | ~200MB | 낮음 |

### 유틸리티

| 파일 | 목적 | 사용 시기 |
|------|------|----------|
| `scan_packages.sh` | 설치된 패키지 스캔 | **사전 필수 실행** |
| `verify_headless.sh` | 검증 스크립트 | 각 Stage 후 |
| `restore_all.sh` | 전체 복구 (롤백) | 문제 발생 시 |

**권장**: 최적화 버전(`*_optimized.sh`) 사용 - 실제 설치된 패키지만 제거하므로 더 안전하고 효율적

---

## ⚠️ 사전 준비

### 1. 백업 생성 (필수!)

**TWRP Recovery로 부팅**:
```bash
# PC에서 TWRP로 부팅
adb reboot recovery

# TWRP에서:
# Backup → Boot, System, Data 선택 → Swipe to Backup
```

### 2. 현재 상태 확인

```bash
# WiFi IP 확인 (나중에 SSH 접속에 필요)
adb shell ip addr show wlan0 | grep "inet "

# 현재 RAM 사용량 기록
adb shell free -h > ram_before.txt
cat ram_before.txt
```

### 3. 패키지 스캔 (필수!)

**먼저 실제 설치된 패키지를 스캔합니다**:

```bash
cd /home/temmie/A90_5G_rooting/scripts/headless_android

# 스캔 스크립트 전송
adb push scan_packages.sh /data/local/tmp/
adb shell chmod +x /data/local/tmp/scan_packages.sh

# 스캔 실행 (약 2초 소요)
adb shell sh /data/local/tmp/scan_packages.sh

# 결과 확인
adb pull /data/local/tmp/package_scan.log ./package_scan.log
adb pull /data/local/tmp/package_list.txt ./package_list.txt

# 스캔 결과 리뷰
cat package_scan.log | less
```

**스캔 결과 예시**:
```
Total packages: 432

Category breakdown:
1. GUI: 25 packages
2. Samsung: 52 packages
3. Google: 45 packages
4. Media: 9 packages
5. Communication: 10 packages
6. Productivity: 4 packages
```

### 4. 스크립트 전송

**최적화 버전 스크립트 전송 (권장)**:

```bash
cd /home/temmie/A90_5G_rooting/scripts/headless_android

# 최적화 버전 스크립트 전송
adb push disable_gui_optimized.sh /data/local/tmp/
adb push disable_samsung_optimized.sh /data/local/tmp/
adb push disable_google_optimized.sh /data/local/tmp/
adb push disable_apps_optimized.sh /data/local/tmp/
adb push verify_headless.sh /data/local/tmp/
adb push restore_all.sh /data/local/tmp/

# 실행 권한 부여
adb shell chmod +x /data/local/tmp/*.sh
```

**또는 기본 버전 (다른 디바이스용)**:

```bash
adb push disable_gui.sh /data/local/tmp/
adb push disable_samsung.sh /data/local/tmp/
adb push disable_google.sh /data/local/tmp/
adb push disable_apps.sh /data/local/tmp/
# ... (나머지 동일)
```

---

## 🚀 단계별 실행 가이드

**참고**: 아래 가이드는 **최적화 버전 스크립트**를 기준으로 작성되었습니다.

### Stage 1: GUI 제거 (~600MB 절감)

**제거 항목**: SystemUI (18개), Launcher (7개), Keyboard (1개) = **총 25개**

```bash
# 1. 스크립트 실행 (최적화 버전)
adb shell sh /data/local/tmp/disable_gui_optimized.sh

# 출력 예시:
# =========================================
# Stage 1 GUI Removal Completed
# =========================================
# Total packages disabled: 25
# Full log: /data/local/tmp/headless_stage1.log

# 2. 재부팅
adb reboot

# 3. 부팅 대기 (화면이 검게 나옴 - 정상!)
adb wait-for-device
sleep 10

# 4. 검증
adb shell sh /data/local/tmp/verify_headless.sh

# 5. SSH 접속 테스트
ssh root@192.168.0.12
# (비밀번호 입력 후 접속 확인)
exit

# 6. RAM 확인
adb shell free -h

# 예상 결과:
#               total        used        free
# Mem:          5.2G         1.9G        3.3G
```

**성공 기준**:
- ✅ 화면이 검은색 (정상)
- ✅ SSH 접속 가능
- ✅ WiFi 연결 유지
- ✅ RAM < 2.0GB

**문제 발생 시 복구**:
```bash
adb shell pm enable com.android.systemui
adb shell pm enable com.sec.android.app.launcher
adb reboot
```

---

### Stage 2: Samsung 서비스 제거 (~400MB 절감)

**제거 항목**: Bixby, Samsung Account, Knox, 게임 서비스

```bash
# 1. 스크립트 실행
adb shell sh /data/local/tmp/disable_samsung.sh

# 2. 재부팅
adb reboot

# 3. 부팅 대기
adb wait-for-device
sleep 10

# 4. 검증
adb shell sh /data/local/tmp/verify_headless.sh

# 5. SSH 테스트
ssh root@192.168.0.12
exit

# 6. RAM 확인
adb shell free -h

# 예상 결과:
#               total        used        free
# Mem:          5.2G         1.5G        3.7G
```

**성공 기준**:
- ✅ SSH 접속 가능
- ✅ WiFi 연결 유지
- ✅ RAM < 1.7GB

---

### Stage 3: Google 서비스 제거 (~300MB 절감)

⚠️ **경고**: Google Play Services 제거 시 WiFi 인증 문제 발생 가능!

**제거 항목**: Google Play Services, Play Store, Google 앱

```bash
# 1. 스크립트 실행
adb shell sh /data/local/tmp/disable_google.sh

# ⚠️ 출력 확인:
# ⚠️  WARNING: This may affect WiFi authentication!
# Make sure you can recover via ADB if needed.

# 2. 재부팅
adb reboot

# 3. 부팅 대기
adb wait-for-device
sleep 10

# 4. ⚠️ CRITICAL: WiFi 연결 확인
adb shell ip addr show wlan0 | grep "inet "

# WiFi 연결되어 있으면 계속 진행
# WiFi 연결 안 되면 아래 복구 절차 실행

# 5. 검증
adb shell sh /data/local/tmp/verify_headless.sh

# 6. SSH 테스트
ssh root@192.168.0.12
ping -c 3 8.8.8.8
exit

# 7. RAM 확인
adb shell free -h

# 예상 결과:
#               total        used        free
# Mem:          5.2G         1.2G        4.0G
```

**성공 기준**:
- ✅ SSH 접속 가능
- ✅ WiFi 연결 유지 (중요!)
- ✅ 인터넷 접속 가능 (ping 8.8.8.8)
- ✅ RAM < 1.4GB

**WiFi 문제 발생 시 복구**:
```bash
adb shell pm enable com.google.android.gms
adb shell pm enable com.android.vending
adb reboot
```

---

### Stage 4: 불필요한 앱 제거 (~200MB 절감)

**제거 항목**: Media, Camera, 연락처, 메시지 등

```bash
# 1. 스크립트 실행
adb shell sh /data/local/tmp/disable_apps.sh

# 2. 재부팅
adb reboot

# 3. 부팅 대기
adb wait-for-device
sleep 10

# 4. 최종 검증
adb shell sh /data/local/tmp/verify_headless.sh

# 5. SSH 테스트
ssh root@192.168.0.12
exit

# 6. 최종 RAM 확인
adb shell free -h

# 예상 결과:
#               total        used        free
# Mem:          5.2G         1.0G        4.2G
```

**성공 기준**:
- ✅ SSH 접속 가능
- ✅ WiFi 연결 유지
- ✅ RAM ≤ 1.2GB
- ✅ 절감량: 1.5GB (60%)

---

## 🎉 최종 확인

모든 Stage 완료 후:

```bash
# 1. 최종 검증
adb shell sh /data/local/tmp/verify_headless.sh

# 출력 예시:
# =========================================
# Verification Summary
# =========================================
#
# RAM: 1024MB / 5300MB
# WiFi: 192.168.0.12/24
# SSH: Running
# Processes: 180
#
# Current State: After Stage 4 (All apps disabled)

# 2. SSH로 Linux 환경 사용
ssh root@192.168.0.12

# Chroot 진입
bootlinux

# 패키지 설치 등 작업
apt update
apt install vim git python3

exit
exit

# 3. RAM 절감 비교
echo "=== RAM Usage Comparison ==="
echo ""
echo "Before: 2.5GB (from ram_before.txt)"
cat ram_before.txt
echo ""
echo "After:"
adb shell free -h
echo ""
echo "Saved: ~1.5GB (60%)"
```

---

## 🔄 복구 방법

### 개별 Stage 롤백

**Stage 1 복구 (GUI 복원)**:
```bash
adb shell pm enable com.android.systemui
adb shell pm enable com.sec.android.app.launcher
adb reboot
```

**Stage 3 복구 (Google 서비스 복원)**:
```bash
adb shell pm enable com.google.android.gms
adb shell pm enable com.android.vending
adb reboot
```

### 전체 복구

```bash
# 모든 비활성화된 패키지 재활성화
adb shell sh /data/local/tmp/restore_all.sh

# 출력 확인 후 재부팅
adb reboot

# 부팅 후 GUI 정상 작동 확인
# RAM 사용량 2.5GB로 복귀
```

### TWRP 복구 (최후의 수단)

```bash
# 1. TWRP로 부팅
adb reboot recovery

# 2. TWRP에서:
# Restore → 백업 선택 → Swipe to Restore

# 3. 재부팅
# Reboot → System
```

---

## 📊 예상 결과

### RAM 사용량 추이

| Stage | 상태 | RAM 사용량 | 절감량 | 누적 절감 |
|-------|------|-----------|--------|----------|
| **시작** | Stock Android | 2.5GB | - | - |
| **Stage 1** | GUI 제거 | 1.9GB | 600MB | 600MB (24%) |
| **Stage 2** | Samsung 제거 | 1.5GB | 400MB | 1.0GB (40%) |
| **Stage 3** | Google 제거 | 1.2GB | 300MB | 1.3GB (52%) |
| **Stage 4** | Apps 제거 | 1.0GB | 200MB | 1.5GB (60%) |

### 최종 시스템 구성

**제거된 항목**:
- ❌ Android GUI (SystemUI, Launcher)
- ❌ Samsung 서비스 (Bixby, Knox, Account)
- ❌ Google 서비스 (Play Services, Store)
- ❌ 불필요한 앱 (Media, Camera, 연락처)

**유지된 항목**:
- ✅ Android Framework (system_server, zygote)
- ✅ WiFi 드라이버 및 서비스
- ✅ ADB 디버깅
- ✅ Linux Chroot 환경
- ✅ SSH 서버

**사용 환경**:
- PC에서 SSH 접속만 사용
- Debian Linux 패키지 관리
- Python, GCC 등 개발 도구
- 화면 출력 없음 (Headless)

---

## ⚠️ 주의 사항

### 높은 위험

1. **Stage 3 (Google 서비스 제거)**:
   - WiFi 인증 문제 발생 가능
   - WPA2-Enterprise 네트워크는 사용 불가할 수 있음
   - 일반 WPA2-PSK는 문제없음

2. **화면 사용 불가**:
   - GUI 제거 후 화면 출력 없음
   - SSH로만 접근 가능
   - ADB 연결 필수

### 복구 준비

- TWRP 백업 필수
- WiFi IP 주소 기록
- ADB 케이블 항상 연결
- 복구 스크립트 미리 전송

### 권장 사항

- Stage 1 완료 후 24시간 테스트
- WiFi 안정성 확인 후 다음 Stage 진행
- 각 Stage마다 로그 확인
- SSH 접속 항상 테스트

---

## 📚 로그 파일

모든 스크립트는 `/data/local/tmp/` 에 로그를 남깁니다:

```bash
# 로그 확인
adb shell cat /data/local/tmp/headless_stage1.log
adb shell cat /data/local/tmp/headless_stage2.log
adb shell cat /data/local/tmp/headless_stage3.log
adb shell cat /data/local/tmp/headless_stage4.log
adb shell cat /data/local/tmp/headless_verify.log
adb shell cat /data/local/tmp/headless_restore.log

# 로그 다운로드
adb pull /data/local/tmp/headless_stage1.log ./logs/
adb pull /data/local/tmp/headless_stage2.log ./logs/
adb pull /data/local/tmp/headless_stage3.log ./logs/
adb pull /data/local/tmp/headless_stage4.log ./logs/
```

---

## 🎓 학습 내용

이 작업을 통해 다음을 배웁니다:

1. **Android Package Manager**:
   - `pm disable-user --user 0` 사용법
   - 패키지 의존성 이해
   - System vs User 앱 차이

2. **Android System Architecture**:
   - GUI vs Framework 분리
   - 필수 서비스 vs 선택 서비스
   - System Server의 역할

3. **RAM 최적화**:
   - Android 메모리 관리
   - 프로세스 우선순위
   - LowMemoryKiller 동작

4. **문제 해결**:
   - Headless 환경 디버깅
   - ADB를 통한 복구
   - WiFi 문제 진단

---

## 📞 문제 해결

### SSH 연결 실패

```bash
# 1. SSH 서버 상태 확인
adb shell ps -A | grep sshd

# 2. SSH 서버 재시작
adb shell killall sshd
adb shell /data/adb/modules/systemless_chroot/service.d/boot_chroot.sh

# 3. Chroot 마운트 확인
adb shell mount | grep /data/linux_root
```

### WiFi 연결 끊김

```bash
# 1. WiFi 상태 확인
adb shell ip addr show wlan0

# 2. wpa_supplicant 재시작
adb shell killall wpa_supplicant
adb shell svc wifi enable

# 3. Google Play Services 복구
adb shell pm enable com.google.android.gms
adb reboot
```

### 부팅 중단

```bash
# 1. TWRP로 부팅
adb reboot recovery

# 2. Magisk 모듈 제거 (필요시)
# TWRP Terminal:
rm -rf /data/adb/modules/systemless_chroot

# 3. 또는 백업 복원
# TWRP: Restore → 백업 선택

# 4. 재부팅
reboot
```

---

## ✅ 체크리스트

### 실행 전

- [ ] TWRP 백업 완료
- [ ] WiFi IP 주소 기록 완료
- [ ] 스크립트 전송 완료
- [ ] 현재 RAM 사용량 기록 완료

### Stage 1 후

- [ ] SSH 접속 확인
- [ ] WiFi 연결 확인
- [ ] RAM < 2.0GB 확인
- [ ] 검증 스크립트 실행 완료

### Stage 2 후

- [ ] SSH 접속 확인
- [ ] WiFi 연결 확인
- [ ] RAM < 1.7GB 확인
- [ ] 검증 스크립트 실행 완료

### Stage 3 후 (중요!)

- [ ] SSH 접속 확인
- [ ] **WiFi 연결 확인** (중요!)
- [ ] **인터넷 접속 확인** (ping 8.8.8.8)
- [ ] RAM < 1.4GB 확인
- [ ] 검증 스크립트 실행 완료

### Stage 4 후

- [ ] SSH 접속 확인
- [ ] WiFi 연결 확인
- [ ] RAM ≤ 1.2GB 확인
- [ ] 최종 검증 완료

### 최종 확인

- [ ] 24시간 안정성 테스트
- [ ] 재부팅 후 자동 복구 확인
- [ ] SSH 자동 시작 확인
- [ ] 문서 업데이트 (PROGRESS_LOG.md)

---

**참고 문서**: [HEADLESS_ANDROID_IMPLEMENTATION.md](../../docs/guides/HEADLESS_ANDROID_IMPLEMENTATION.md)
**프로젝트 상태**: [PROJECT_STATUS.md](../../docs/overview/PROJECT_STATUS.md)
