# Native Init Flash / Bridge Operator Guide

Date: `2026-04-29`

이 문서는 사람이 직접 따라 하기 위한 짧은 운영 절차서다.
목표는 **TWRP에서 native init boot image를 안전하게 flash하고,
부팅 후 USB serial bridge로 현재 상태를 확인하는 것**이다.

에이전트가 전체 작업 흐름을 이해해야 할 때는
`docs/operations/CLAUDE_NATIVE_INIT_RUNBOOK.md`를 같이 본다.

## 0. 현재 고정 기준

- device: `Samsung Galaxy A90 5G SM-A908N`
- recovery: TWRP 사용 가능
- known-good fallback native init: `A90 Linux init v48`
- known-good fallback source: `workspace/public/archive/stage3/linux_init/init_v48.c`
- known-good fallback boot image: `workspace/private/inputs/boot_images/boot_linux_v48.img`
- known-good fallback boot image SHA256: `1c87fa59712395027c5c2e489b15c4f6ddefabc3c50f78d3c235c4508a63e042`
- latest verified build: `A90 Linux init 0.9.259 (v2187-screenapp-ui-validation)`
- latest verified source: `workspace/public/src/native-init/` + 빌더 `workspace/public/src/scripts/revalidation/build_native_init_boot_v2187_screenapp_ui_validation.py`
- latest verified boot image: `workspace/private/inputs/boot_images/boot_linux_v2187_screenapp_ui_validation.img`
- latest verified boot image SHA256: `0422f854b3e78d36e225012fd89a53016067155e200291d067ff7d71f32091ca`
- version axes: `v2187-screenapp-ui-validation`은 boot/init baseline tag, `a90_android_execns_probe helper-v427`은 포함된 helper marker, `V2187`은 baseline-promotion run/report 번호다. 전체 규칙은 `docs/operations/VERSIONING_POLICY.md`를 따른다.
- previous verified boot image: `workspace/private/inputs/boot_images/boot_linux_v2186_wifi_ui_polish.img` (`A90 Linux init 0.9.258 (v2186-wifi-ui-polish)`)
- control channel: USB CDC ACM serial bridge
- bridge endpoint: `127.0.0.1:54321`
- bridge script: `workspace/public/src/scripts/revalidation/serial_tcp_bridge.py`
- safe persistent areas: `/cache`, ext4 SD workspace `/mnt/sdext/a90`

## 1. 상태 구분

### Native init 상태

custom `/init`가 PID 1로 실행된 상태다.
Android userspace로 넘어가지 않고, 이 프로젝트의 자체 shell/HUD가 뜬다.

확인 신호:

- 화면에 custom boot splash 또는 native init HUD/menu가 보임
- host에 Samsung USB ACM 장치가 보임
- bridge에서 `version` 명령이 응답함
- ADB는 보통 기대하지 않음

### TWRP 상태

recovery partition의 TWRP가 실행된 상태다.
boot image를 다시 flash하는 안전한 복구 지점이다.

확인 신호:

- 기기 화면에 TWRP UI가 보임
- `adb devices -l`에서 `recovery` 상태가 보임
- serial bridge는 이 상태에서 필수 아님

### Android 상태

stock Android userspace가 올라온 상태다.
현재 native init 작업 기준에서는 목표 상태가 아니다.

확인 신호:

- Android UI 또는 Android 부팅 화면으로 진행됨
- `adb devices -l`에서 recovery가 아닌 Android device로 보일 수 있음
- native init bridge `version`이 응답하지 않음

## 2. Bridge 사용법

bridge는 host의 `/dev/ttyACM*` serial 장치를 TCP로 열어 주는 얇은 중계기다.
Codex/Claude가 `sudo`를 직접 못 쓰는 환경에서는 사용자가 host 터미널에서 실행한다.

### 시작

```bash
cd ~/dev/A90_5G_rooting
python3 workspace/public/src/scripts/revalidation/a90_bridge.py preflight
python3 workspace/public/src/scripts/revalidation/a90_bridge.py ensure --device /dev/ttyACM0
```

`/dev/ttyACM0` 권한 오류가 나면 같은 wrapper 명령을 `sudo`로 재실행한다.

정상 로그 예:

```text
[bridge] tcp listener ready on 127.0.0.1:54321
[bridge] serial connected: /dev/serial/by-id/usb-SAMSUNG_SAMSUNG_Android_...
```

### 재시작

```bash
cd ~/dev/A90_5G_rooting
python3 workspace/public/src/scripts/revalidation/a90_bridge.py status
python3 workspace/public/src/scripts/revalidation/a90_bridge.py doctor
python3 workspace/public/src/scripts/revalidation/a90_bridge.py restart --discovered --device /dev/ttyACM0
```

root가 띄운 기존 bridge를 종료해야 하면 위 `restart` 명령도 `sudo`로 실행한다.
`doctor`가 `private_log_dir` 또는 `private_run_dir` writable 경고를 내면
root-owned bridge 로그/상태가 남은 것이므로 아래처럼 고정 private 디렉터리만 복구한다.

```bash
sudo python3 workspace/public/src/scripts/revalidation/a90_bridge.py repair-dirs --user "$USER"
python3 workspace/public/src/scripts/revalidation/a90_bridge.py doctor
```

### 기본 확인

다른 host 터미널에서 실행한다.

```bash
printf 'version\n' | nc -w 3 127.0.0.1 54321
```

정상 응답 예:

```text
A90 Linux init 0.8.17 (v86)
made by temmie0214
kernel: Linux 4.14.190-25818860-abA908NKSU5EWA3 aarch64
[done] version
```

자주 쓰는 명령:

```bash
printf 'help\n' | nc -w 3 127.0.0.1 54321
printf 'status\n' | nc -w 5 127.0.0.1 54321
printf 'timeline\n' | nc -w 5 127.0.0.1 54321
printf 'cat /cache/native-init.log\n' | nc -w 5 127.0.0.1 54321
printf 'netservice status\n' | nc -w 5 127.0.0.1 54321
```

v73부터는 자동화용 one-shot 명령은 `a90ctl.py`를 우선 쓴다.
raw `nc` 출력 대신 `A90P1` END marker의 `rc`/`status`를 파싱한다.
v74 이후부터는 공백/특수문자 인자가 필요한 경우 `a90ctl.py`가 자동으로
`cmdv1x <len:hex-utf8-arg>...` wire format을 사용한다.

```bash
python3 workspace/public/src/scripts/revalidation/a90ctl.py status
python3 workspace/public/src/scripts/revalidation/a90ctl.py echo "hello world"
python3 workspace/public/src/scripts/revalidation/a90ctl.py --json status
python3 workspace/public/src/scripts/revalidation/a90ctl.py --hide-on-busy status
```

### v60 netservice

v60부터 NCM/tcpctl boot-time service는 opt-in이다.
기본값은 OFF이며, `/cache/native-init-netservice` flag가 있을 때만 부팅 중 자동 시작한다.

```bash
printf 'netservice status\n' | nc -w 5 127.0.0.1 54321
printf 'netservice enable\n' | nc -w 20 127.0.0.1 54321
printf 'netservice disable\n' | nc -w 20 127.0.0.1 54321
```

실험 후 안전한 기본 상태로 돌릴 때는 `netservice disable`을 사용한다.

NCM을 껐다 켜면 host `enx...` 이름이 바뀔 수 있다.
이전 interface 이름을 재사용하지 말고 현재 값을 다시 확인한다.

```bash
ip -br link | grep enx
python3 workspace/public/src/scripts/revalidation/netservice_reconnect_soak.py status
python3 workspace/public/src/scripts/revalidation/netservice_reconnect_soak.py once --manual-host-config
```

### v53+ 메뉴 표시 중 serial 정책

v53부터 화면 메뉴가 떠 있는 동안 serial shell은 위험하거나 오래 걸릴 수 있는 명령을 바로 실행하지 않는다.
hang이 아니라 `[busy]`를 반환하므로 automation은 이 값을 보고 재시도할 수 있다.

```bash
printf 'echo test\n' | nc -w 5 127.0.0.1 54321
```

정상 차단 예:

```text
[busy] auto menu active; send hide/q or select HIDE MENU
```

메뉴 표시 중에도 허용되는 관찰 명령:

```bash
printf 'version\n' | nc -w 5 127.0.0.1 54321
printf 'status\n' | nc -w 5 127.0.0.1 54321
printf 'timeline\n' | nc -w 5 127.0.0.1 54321
printf 'logcat\n' | nc -w 5 127.0.0.1 54321
```

serial에서 메뉴를 숨기고 일반 명령을 다시 실행하려면:

```bash
printf 'hide\n' | nc -w 5 127.0.0.1 54321
sleep 3
printf 'echo ok\n' | nc -w 5 127.0.0.1 54321
```

## 3. Bridge가 안 될 때 확인 순서

### 1단계: host USB 확인

```bash
lsusb | rg 'Samsung|04e8|6861|6860|685d' || true
ls -l /dev/ttyACM* 2>/dev/null || true
ls -l /dev/serial/by-id 2>/dev/null || true
adb devices -l
```

판단 기준:

- `04e8:6861` + `/dev/ttyACM0` 있음: native init ACM 장치일 가능성이 높음
- `/dev/ttyACM0` 있음 + bridge process 없음: bridge를 다시 시작
- `adb devices -l`에서 `recovery`: TWRP 상태이므로 boot image flash 가능
- Android ADB만 보임: 현재 boot image가 native init이 아닐 수 있음

### 2단계: bridge process 확인

```bash
ps -ef | rg 'serial_tcp_bridge.py|native_init_flash.py' | rg -v rg
```

bridge가 없으면 wrapper로 다시 시작한다.

```bash
python3 workspace/public/src/scripts/revalidation/a90_bridge.py ensure --device /dev/ttyACM0
```

### 3단계: native init 쪽 USB 재연결

bridge가 한 번이라도 살아 있고 v48 이상이라면 다음을 시도할 수 있다.

```bash
printf 'reattach\n' | nc -w 5 127.0.0.1 54321
printf 'version\n' | nc -w 3 127.0.0.1 54321
```

USB gadget 자체를 재바인딩해야 할 때:

```bash
printf 'usbacmreset\n' | nc -w 10 127.0.0.1 54321
sleep 3
printf 'version\n' | nc -w 3 127.0.0.1 54321
```

`usbacmreset` 이후에는 host의 `/dev/ttyACM0`가 재생성될 수 있다.
v48 bridge는 이 변화를 감지해서 serial fd를 다시 연다.

## 4. TWRP에서 v48 flash

가장 안전한 기본 경로다.
TWRP가 떠 있고 host에서 ADB recovery가 잡힐 때 사용한다.

### 1단계: TWRP ADB 확인

```bash
adb devices -l
```

정상 예:

```text
RFCM90CFWXA    recovery ...
```

`recovery`가 아니면 아직 이 절차를 진행하지 않는다.

### 2단계: 자동 flash + 검증

```bash
python3 workspace/public/src/scripts/revalidation/native_init_flash.py \
  workspace/private/inputs/boot_images/boot_linux_v48.img \
  --expect-version "A90 Linux init v48" \
  --bridge-timeout 240 \
  --recovery-timeout 180
```

이 스크립트가 하는 일:

1. local boot image 존재 여부, 크기 정렬, SHA256 확인
2. `--expect-version` 문자열이 local image 안에 있는지 확인
3. `adb devices`에서 TWRP `recovery` 상태를 기다림
4. `workspace/private/inputs/boot_images/boot_linux_v48.img`를 `/tmp/native_init_boot.img`로 push
5. TWRP 안에서 remote SHA256 계산
6. local/remote SHA256 불일치 시 중단
7. `dd if=/tmp/native_init_boot.img of=/dev/block/by-name/boot bs=4M conv=fsync && sync`
8. boot partition 앞쪽을 image 크기만큼 다시 읽어 SHA256 일치 확인
9. `adb shell 'twrp reboot'`
10. native init 부팅 후 bridge `cmdv1 version/status`로 기대 버전과 shell 상태 확인

v73 이상에서는 기본 `--verify-protocol auto`가 `cmdv1`/`A90P1`의 `rc=0`, `status=ok`를 확인한다.
v48 같은 pre-v73 image는 `A90P1 END`가 없으므로 자동으로 raw `version` 검증으로 fallback한다.

### 3단계: bridge가 아직 안 열렸을 때

flash와 reboot는 끝났지만 bridge가 실행 중이 아니면 검증 단계에서 timeout이 날 수 있다.
이때는 새 터미널에서 bridge를 먼저 열고 다시 확인한다.

```bash
python3 workspace/public/src/scripts/revalidation/a90_bridge.py ensure --device /dev/ttyACM0
```

그리고:

```bash
python3 workspace/public/src/scripts/revalidation/native_init_flash.py \
  --verify-only \
  --expect-version "A90 Linux init v48" \
  --verify-protocol auto \
  --bridge-timeout 60
```

또는 직접:

```bash
printf 'version\n' | nc -w 3 127.0.0.1 54321
```

## 5. Native init에서 TWRP로 넘어가 flash

이미 native init이 떠 있고 bridge가 살아 있을 때는 `--from-native`를 쓴다.

```bash
python3 workspace/public/src/scripts/revalidation/native_init_flash.py \
  workspace/private/inputs/boot_images/boot_linux_v48.img \
  --from-native \
  --expect-version "A90 Linux init v48" \
  --bridge-timeout 240 \
  --recovery-timeout 180
```

이 경로는 먼저 bridge로 `recovery` 명령을 보내 TWRP로 재부팅한 뒤,
TWRP ADB가 잡히면 같은 방식으로 boot image를 flash한다.
v53+ 화면 메뉴가 떠 있어 `recovery`가 `[busy]`로 막히면 스크립트가 자동으로 `hide`를 보내고
3초 뒤 `recovery`를 재시도한다.

## 6. 수동 fallback

자동 스크립트를 쓸 수 없을 때만 사용한다.
반드시 TWRP `recovery` 상태에서 실행한다.

```bash
adb devices -l
sha256sum workspace/private/inputs/boot_images/boot_linux_v48.img
adb push workspace/private/inputs/boot_images/boot_linux_v48.img /tmp/native_init_boot.img
adb shell 'sha256sum /tmp/native_init_boot.img 2>/dev/null || toybox sha256sum /tmp/native_init_boot.img'
adb shell 'dd if=/tmp/native_init_boot.img of=/dev/block/by-name/boot bs=4M conv=fsync && sync'
adb shell 'twrp reboot'
```

local SHA256과 remote SHA256이 같을 때만 `dd`를 실행한다.

## 7. 이번 Android 부팅 문제 복구 기록

문제 상황:

- 기기가 native init이 아니라 Android로 부팅됨
- TWRP는 정상 진입 가능
- TWRP ADB serial: `RFCM90CFWXA`

확인한 값:

- stable v48 image SHA256: `1c87fa59712395027c5c2e489b15c4f6ddefabc3c50f78d3c235c4508a63e042`
- local v49 image SHA256: `38ea2e20a33af450388fe40e4d2d9aa0abb11b592efb34102ca52723a361968e`
- v49 flash 후 boot partition prefix SHA256: `38ea2e20a33af450388fe40e4d2d9aa0abb11b592efb34102ca52723a361968e`

판단:

- 전체 boot partition SHA256은 partition padding/trailing 영역 때문에 image SHA와 직접 비교하지 않는다.
- image 크기만큼 읽은 prefix SHA256은 v49와 일치했으므로 v49 image는 실제로 기록됐다.
- 하지만 `adb shell 'twrp reboot'` 후 Android `/system/bin/init second_stage`로 진입했다.
- 따라서 v49는 stable이 아니라 격리된 실패 실험으로 취급한다.
- 검증된 `workspace/private/inputs/boot_images/boot_linux_v48.img`를 TWRP에서 다시 flash했다.

실행한 복구 명령:

```bash
python3 workspace/public/src/scripts/revalidation/native_init_flash.py \
  workspace/private/inputs/boot_images/boot_linux_v48.img \
  --expect-version "A90 Linux init v48" \
  --bridge-timeout 240 \
  --recovery-timeout 180
```

그 후 host에는 Samsung USB ACM 장치와 `/dev/ttyACM0`가 다시 보였고,
bridge가 실행 중이 아니어서 사용자가 bridge를 다시 열어야 하는 상태였다.

## 8. 절대 조심할 것

- 검증되지 않은 `boot_linux_v49.img`를 stable로 취급하지 않는다.
- `workspace/public/archive/stage3/linux_init/init_v49.c` 같은 새 파일은 출처를 확인하기 전까지 flash 기준으로 쓰지 않는다.
- `boot` 외 partition에는 이 문서 절차로 쓰지 않는다.
- `recovery`, `vbmeta`, `efs`, `sec_efs`, modem, persist, key/security 계열 partition은 추측으로 쓰지 않는다.
- Android ADB가 잡힌다고 native init이 정상이라고 판단하지 않는다.
- bridge 응답이 없다는 이유만으로 바로 재flash하지 않는다. 먼저 USB/bridge/TWRP 상태를 나눠 본다.

## 9. 빠른 체크리스트

TWRP에서 v48로 되돌리는 최소 절차:

```bash
adb devices -l
python3 workspace/public/src/scripts/revalidation/native_init_flash.py \
  workspace/private/inputs/boot_images/boot_linux_v48.img \
  --expect-version "A90 Linux init v48" \
  --bridge-timeout 240 \
  --recovery-timeout 180
```

부팅 후 bridge 확인:

```bash
python3 workspace/public/src/scripts/revalidation/a90_bridge.py status
printf 'version\n' | nc -w 3 127.0.0.1 54321
```

최신 verified v86을 native init 상태에서 다시 올릴 때:

```bash
python3 workspace/public/src/scripts/revalidation/native_init_flash.py \
  workspace/private/inputs/boot_images/boot_linux_v86.img \
  --from-native \
  --expect-version "A90 Linux init 0.8.17 (v86)" \
  --verify-protocol auto \
  --bridge-timeout 240 \
  --recovery-timeout 180
```
