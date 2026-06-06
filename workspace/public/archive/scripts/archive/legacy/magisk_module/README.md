# Magisk Systemless Chroot 모듈

Samsung Galaxy A90 5G용 Magisk systemless chroot 모듈입니다.

## 📁 디렉토리 구조

```
systemless_chroot/
├── META-INF/com/google/android/
│   ├── update-binary           # Magisk 설치 스크립트
│   └── updater-script         # (비어있음)
├── module.prop                # 모듈 정보
├── post-fs-data.sh           # 부팅 시 실행 (BLOCKING)
├── service.d/
│   └── boot_chroot.sh        # 서비스 시작 (NON-BLOCKING)
├── system/bin/
│   ├── bootlinux             # Chroot 진입 스크립트
│   └── killlinux             # Chroot 종료 스크립트
└── README.md                 # 이 파일
```

## 🚀 사용법

### 1. Rootfs 이미지 생성

```bash
cd /home/temmie/A90_5G_rooting/scripts/utils
sudo ./create_rootfs.sh 6144 debian bookworm
```

### 2. 이미지 전송

```bash
adb push debian_bookworm_arm64.img /sdcard/
adb shell
su
mkdir -p /data/linux_root
mv /sdcard/debian_bookworm_arm64.img /data/linux_root/debian_arm64.img
exit
```

### 3. 모듈 패키징

```bash
cd /home/temmie/A90_5G_rooting/scripts/magisk_module
cd systemless_chroot
zip -r -9 ../systemless_chroot_v1.0.zip *
```

### 4. 모듈 설치

```bash
adb push ../systemless_chroot_v1.0.zip /sdcard/
# Magisk Manager → Modules → Install from storage
# systemless_chroot_v1.0.zip 선택
# 재부팅
```

### 5. 확인

```bash
# 디버깅 도구 사용
cd /home/temmie/A90_5G_rooting/scripts/utils
./debug_magisk.sh status
./debug_magisk.sh ssh

# SSH 접속
ssh root@<device-ip>
```

## 📝 주의사항

- Rootfs 이미지 파일명은 반드시 `debian_arm64.img`이어야 합니다
- `/data/linux_root/` 경로에 최소 8GB 여유 공간 필요
- Magisk v24.0 이상 필요
- BusyBox 설치 필요

## 🔧 문제 해결

```bash
# 로그 확인
adb shell su -c "cat /data/adb/magisk_logs/chroot_init.log"

# 자동 수정
cd /home/temmie/A90_5G_rooting/scripts/utils
./debug_magisk.sh fix

# 완전 초기화
./debug_magisk.sh clean
adb reboot
```

## 📚 참고 문서

- [HEADLESS_ANDROID_PLAN.md](../../docs/plans/HEADLESS_ANDROID_PLAN.md) - 전체 계획
- [MAGISK_SYSTEMLESS_GUIDE.md](../../docs/guides/MAGISK_SYSTEMLESS_GUIDE.md) - 상세 가이드
