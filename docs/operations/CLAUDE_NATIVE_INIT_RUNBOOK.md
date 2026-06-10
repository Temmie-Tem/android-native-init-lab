# Claude / Agent Native Init Operations Runbook

Date: `2026-04-29`

이 문서는 Claude나 다른 에이전트가 이 저장소에서 같은 실수를 반복하지 않도록 남기는
운영 설명서다. 핵심은 **브릿지로 현재 상태를 먼저 확인하고, TWRP/boot image/serial rescue
경로를 잃지 않는 것**이다.

## 0. 현재 기준점

현재 기준:

- device: `Samsung Galaxy A90 5G SM-A908N`
- recovery: TWRP 사용 가능
- latest verified build: `A90 Linux init 0.9.259 (v2187-screenapp-ui-validation)`
- latest verified source: `workspace/public/src/native-init/` + 빌더 `workspace/public/src/scripts/revalidation/build_native_init_boot_v2187_screenapp_ui_validation.py`
- latest verified boot image: `workspace/private/inputs/boot_images/boot_linux_v2187_screenapp_ui_validation.img`
- latest verified boot image SHA256: `0422f854b3e78d36e225012fd89a53016067155e200291d067ff7d71f32091ca`
- 현재 기준 사이클: `v2187-screenapp-ui-validation` screenapp UI validation baseline (V2187 promotion)
- version axes: `v2187-screenapp-ui-validation`은 boot/init baseline tag, `a90_android_execns_probe helper-v427`은 포함된 helper marker, `V2187`은 baseline-promotion run/report 번호다. 전체 규칙은 `docs/operations/VERSIONING_POLICY.md`를 따른다.
- previous verified boot image: `workspace/private/inputs/boot_images/boot_linux_v2186_wifi_ui_polish.img` (`A90 Linux init 0.9.258 (v2186-wifi-ui-polish)`)
- older verified boot image: `workspace/private/inputs/boot_images/boot_linux_v261.img` (`A90 Linux init 0.9.60 (v261)`)
- known-good fallback native init: `A90 Linux init v48`
- known-good fallback boot image: `workspace/private/inputs/boot_images/boot_linux_v48.img`
- primary control channel: USB CDC ACM serial
- host bridge: `127.0.0.1:54321`
- bridge script: `workspace/public/src/scripts/revalidation/serial_tcp_bridge.py`
- safe persistent area: `/cache`
- toybox on device: `/cache/bin/toybox`
- USB helper on device: `/cache/bin/a90_usbnet`

중요한 v48 개선:

- USB ACM rebind 후 native init이 `/dev/ttyGS0`를 다시 attach한다.
- `usbacmreset` 명령이 있다.
- `a90_usbnet probe-ncm`으로 host `cdc_ncm`, device `ncm0` 확인 완료.
- ADB는 후순위다. 기본 제어 채널은 serial bridge다.

중요한 v53 개선:

- 화면 메뉴가 떠 있는 동안 위험/장시간 serial 명령은 `[busy]`로 즉시 차단한다.
- `version`, `status`, `timeline`, `logcat` 등 관찰 명령은 menu active 중에도 허용한다.
- `hide`, `hidemenu`, `resume`, `q`, `Q`는 화면 메뉴 숨김 요청으로 동작한다.
- `native_init_flash.py --from-native`는 `[busy]`를 보면 자동으로 `hide` 후 `recovery`를 재시도한다.

중요한 v59 개선:

- host modem probe의 `AT`, `ATE0`, `AT+...`, `ATQ0 ...` line을 native init shell이 무시한다.
- 무시한 line은 current native log에 `serial: ignored AT probe ...`로 기록한다.

중요한 v60 개선:

- `netservice [status|start|stop|enable|disable]`로 NCM/tcpctl service를 제어한다.
- 기본값은 OFF이며 `/cache/native-init-netservice` flag가 있을 때만 boot-time auto-start한다.
- `netservice enable`은 flag 생성 후 NCM/tcpctl을 시작하고, `netservice disable`은 flag 제거와 rollback을 수행한다.
- `a90_tcpctl listen` idle timeout은 helper 상한에 맞춰 `3600s`를 사용한다.

중요한 v61 개선:

- HUD/status에 CPU usage `%`와 GPU busy `%`를 표시한다.
- CPU usage는 `/proc/stat` delta 기반이라 첫 샘플은 `?`일 수 있다.
- GPU usage는 KGSL `gpu_busy_percentage` sysfs 값을 사용한다.

중요한 v62 개선:

- `cpustress [sec] [workers]`로 CPU usage gauge를 안전하게 검증할 수 있다.
- `/dev/null`과 `/dev/zero`를 boot-time에 정확한 char device로 보정한다.
- GPU usage 0%는 CPU-only stress에서는 정상이다. KGSL/3D workload가 아니면 GPU busy가 오르지 않는다.

중요한 v63 개선:

- 자동 메뉴가 APPS/MONITORING/TOOLS/LOGS/NETWORK/POWER 계층으로 확장됐다.
- CPU STRESS app에서 5/10/30/60초 테스트를 버튼으로 선택할 수 있다.
- LOG/NETWORK/CPU STRESS app 화면은 active app 상태로 유지되고, 아무 버튼이나 누르면 메뉴로 돌아간다.

중요한 v64 개선:

- 부팅 직후 큰 TEST 화면 대신 `A90 NATIVE INIT` custom boot splash를 표시한다.
- `timeline`에 `display-splash` 단계가 기록된다.
- 약 2초 뒤 기존처럼 autohud/menu와 serial shell로 전환한다.

중요한 v65 개선:

- v64 splash에서 일부 문구가 잘리는 문제를 줄이기 위해 안전 여백과 줄별 자동 축소를 적용했다.
- 긴 상태 문구를 짧게 바꾸고 footer를 화면 아래쪽에서 조금 올렸다.

중요한 v66 개선:

- 공식 semantic version `0.7.3`과 build tag `v66`을 함께 표시한다.
- `made by temmie0214`를 splash, `version`, `status`, ABOUT app에 표시한다.
- `APPS / ABOUT` 메뉴에 `VERSION`, `CHANGELOG`, `CREDITS` 화면을 추가했다.

중요한 v67 개선:

- ABOUT 계열 화면 글씨 크기를 작게 통일해 세로 공간을 더 활용한다.
- `APPS / ABOUT / CHANGELOG >`가 version list로 열리고, 각 항목은 상세 변경 화면을 표시한다.

중요한 v68 개선:

- HUD menu hidden 상태에서 current native log tail을 표시한다.
- changelog list/detail을 v1 계열까지 확장했다.

중요한 v69~v78 개선:

- 현재 official version은 `0.8.9`, build tag는 `v78`이다.
- v74에서는 `cmdv1x` argument encoding이 실기 검증되어 whitespace 인자를 framed protocol로 보낼 수 있다.
- `inputlayout`으로 VOL+/VOL-/POWER 단일/더블/롱/조합 입력 map을 확인한다.
- `waitgesture [count]`로 gesture recognizer를 실기 검증한다.
- `inputmonitor [events]`로 raw DOWN/UP/REPEAT, gap, hold, decoded gesture/action을 확인한다.
- 자동 메뉴의 `TOOLS / INPUT MONITOR`에서도 같은 정보를 화면에 표시한다.
- v71에서는 hidden HUD와 visible menu spare area에 live log tail panel을 표시한다.
- v72에서는 `TOOLS / DISPLAY TEST`와 `displaytest`로 색상/폰트/wrap/safe-area/cutout 화면을 즉시 확인한다.
- v72에서는 `DRM_FORMAT_XBGR8888` framebuffer color packing을 보정한다.
- v73에서는 `cmdv1`/`A90P1` framed one-shot protocol과 `a90ctl.py` host wrapper를 사용한다.
- v74에서는 `a90ctl.py echo "hello world"` 같은 whitespace 인자를 `cmdv1x <len:hex-utf8-arg>...`로 자동 전송한다.
- v75에서는 idle-timeout serial reattach 성공 로그를 숨겨 live LOG TAIL noise를 줄인다.
- v76에서는 짧은 `A`/`T`/`ATAT` serial fragment를 unknown command 없이 무시한다.
- v77에서는 `TOOLS / DISPLAY TEST`가 4페이지로 분리되고 `displaytest colors/font/safe/layout`, `cutoutcal [x y size]`, `TOOLS > CUTOUT CAL`을 지원한다.
- v78에서는 SD가 `ext4` label `A90_NATIVE`로 준비되어 있고, `mountsd [status|ro|rw|off|init]`로 `/mnt/sdext/a90` workspace를 제어한다.
- v79에서는 boot-time SD health check가 expected UUID/RW probe를 통과한 SD만 main storage로 쓰고, 실패하면 `/cache` fallback warning을 HUD에 표시한다.
- 자동 검증은 가능하면 raw `nc`보다 `python3 workspace/public/src/scripts/revalidation/a90ctl.py status`처럼 rc/status를 파싱한다.
- auto menu busy gate는 POWER 메뉴에서 가장 엄격하고, 일반 메뉴에서는 위험/입력충돌 명령만 막는다.
- `screenmenu`/`blindmenu`가 gesture action을 사용한다.
- `POWER long`은 reserved/ignored로 유지한다.

v49 주의:

- `workspace/private/inputs/boot_images/boot_linux_v49.img`는 local marker와 boot partition prefix readback은 맞았지만
  system boot 후 Android `/system/bin/init second_stage`로 진입했다.
- 현재 v49는 격리된 실패 실험이다.
- 새 실험 버전은 latest verified source에서 최소 diff로 시작하되, 번호는 v50 이상을 사용한다.
- Claude는 v49를 stable이나 다음 기준으로 삼으면 안 된다.

## 1. 절대 원칙

### 하지 말 것

- `boot`, `recovery`, `vbmeta`, `efs`, `sec_efs`, modem, persist, key/security 계열 파티션을 추측으로 쓰지 말 것.
- `userdata`를 포맷하거나 마운트 rw로 쓰지 말 것.
- host에 `/dev/ttyACM0`가 보인다고 native init shell이 살아 있다고 단정하지 말 것.
- bridge 응답이 없다고 곧바로 다시 flash하지 말 것.
- USB gadget rebind 실험을 v47 이하에서 오래 반복하지 말 것. v48 이후를 기준으로 한다.
- ADB를 먼저 살리려고 시간을 쓰지 말 것. 현재는 serial + NCM이 더 현실적인 경로다.

### 먼저 할 것

1. `git status --short`로 기존 변경사항을 확인한다.
2. bridge `version`을 확인한다.
3. 안 되면 host USB 상태와 TWRP ADB 상태를 확인한다.
4. flash가 필요하면 반드시 TWRP ADB에서 local/remote SHA256을 확인한다.
5. 실험 후에는 `logpath`로 current native log를 확인하고, 필요하면 `/cache/usbnet.log`도 확인한다.

## 2. Bridge 사용법

브릿지는 `a90_bridge.py` wrapper로 실행한다. `dialout` 권한이 있으면 sudo 없이 실행하고, 권한 오류가 날 때만 같은 명령을 `sudo`로 재실행한다.

```bash
python3 workspace/public/src/scripts/revalidation/a90_bridge.py preflight
python3 workspace/public/src/scripts/revalidation/a90_bridge.py ensure --device /dev/ttyACM0
```

기존 수동 bridge나 stale process가 있으면 먼저 상태와 doctor 진단을 확인한다.

```bash
python3 workspace/public/src/scripts/revalidation/a90_bridge.py status
python3 workspace/public/src/scripts/revalidation/a90_bridge.py doctor
python3 workspace/public/src/scripts/revalidation/a90_bridge.py restart --discovered --device /dev/ttyACM0
```

`doctor`가 `private_log_dir` 또는 `private_run_dir` writable 경고를 내면,
root로 생성된 private bridge 상태가 남은 것이다. 이때는 아래 명령으로
고정 private 디렉터리만 현재 사용자 소유로 되돌린다.

```bash
sudo python3 workspace/public/src/scripts/revalidation/a90_bridge.py repair-dirs --user "$USER"
python3 workspace/public/src/scripts/revalidation/a90_bridge.py doctor
```

에이전트가 sudo를 직접 못 쓰는 환경이면 사용자에게 위 wrapper 명령 재시작을 요청한다.

기본 확인:

```bash
printf 'version\n' | nc -w 3 127.0.0.1 54321
```

정상 예:

```text
A90 Linux init 0.8.17 (v86)
made by temmie0214
kernel: Linux 4.14.190-25818860-abA908NKSU5EWA3 aarch64
display: 1080x2400 connector=28 crtc=133 fb=207
[done] version (0ms)
```

명령은 가능한 한 짧게 보낸다.

```bash
printf 'status\n' | nc -w 5 127.0.0.1 54321
printf 'logcat\n' | nc -w 5 127.0.0.1 54321
printf 'run /cache/bin/toybox ifconfig -a\n' | nc -w 8 127.0.0.1 54321
```

여러 명령을 한 번에 보낼 수는 있지만, USB rebind나 blocking command 뒤에는 첫 명령이 유실될 수 있다.
그럴 때는 1~3초 후 `version`을 다시 보낸다.

```bash
for i in $(seq 1 5); do
  printf 'version\n' | nc -w 3 127.0.0.1 54321 || true
  sleep 1
done
```

v53+에서 화면 메뉴가 떠 있으면 위험 명령은 실행되지 않고 `[busy]`가 나온다.
이 경우 serial에서 `hide`를 보낸 뒤 1~3초 후 다시 실행한다.

```bash
printf 'hide\n' | nc -w 5 127.0.0.1 54321
sleep 3
printf 'echo ok\n' | nc -w 5 127.0.0.1 54321
```

## 3. Bridge가 안 될 때 판단 순서

### 1단계: host USB 확인

```bash
lsusb | rg 'Samsung|04e8|6861|6860' || true
ls -l /dev/ttyACM* 2>/dev/null || true
ls -l /dev/serial/by-id 2>/dev/null || true
adb devices
```

판단:

- `04e8:6861` + `/dev/ttyACM0` 있음: USB ACM은 host에 보인다.
- bridge만 응답 없음: bridge 재시작 또는 native init console stale 가능성.
- `adb devices`가 `recovery`: TWRP 상태다.
- 아무것도 안 보임: USB gadget이 죽었거나 물리 재부팅이 필요할 수 있다.

### 2단계: v48이면 `usbacmreset`

bridge가 살아 있을 때만:

```bash
printf 'usbacmreset\n' | nc -w 12 127.0.0.1 54321
```

정상 예:

```text
usbacmreset: rebinding ACM, serial may reconnect
# serial console reattached: usbacmreset
[done] usbacmreset
```

### 3단계: TWRP로 복구

native init shell이 살아 있으면:

```bash
printf 'recovery\n' | nc -w 3 127.0.0.1 54321
```

TWRP에 들어간 뒤:

```bash
adb devices
```

`RFCM90CFWXA recovery`가 보여야 한다.

## 4. TWRP에서 system/native init으로 부팅

현재 TWRP `twrp reboot` help에는 `system` target이 없고,
실기에서 `twrp reboot system`은 no-op처럼 TWRP에 머무는 경우가 확인됐다.
system/native init으로 나갈 때는 `twrp reboot` 무인자를 사용한다.

```bash
adb -s RFCM90CFWXA shell 'twrp reboot'
```

그 후 bridge로 확인:

```bash
python3 workspace/public/src/scripts/revalidation/native_init_flash.py \
  --verify-only \
  --expect-version "A90 Linux init 0.8.17 (v86)" \
  --verify-protocol auto \
  --bridge-timeout 180
```

주의:

- `twrp reboot system`은 이 기기의 TWRP CLI에서 신뢰하지 않는다.
- `adb reboot` 또는 `adb shell reboot`는 recovery로 되돌아올 수 있다.
- `adb shell 'twrp reboot'` 후 USB 재열거와 bridge `version`을 관찰한다.
- v73 이상은 `--verify-protocol auto`가 `cmdv1 version/status`의 `rc=0`, `status=ok`를 확인한다.
- v48 같은 pre-v73 image는 `A90P1 END`가 없을 때 raw `version` 검증으로 fallback한다.

## 5. Custom init 수정 흐름

새 버전 예시가 v87이라면:

```bash
cp -r workspace/public/archive/stage3/linux_init/v86 workspace/public/archive/stage3/linux_init/v87
cp workspace/public/archive/stage3/linux_init/init_v86.c workspace/public/archive/stage3/linux_init/init_v87.c
```

반드시 바꿀 것:

- `#define INIT_BUILD "v87"`
- 예시가 patch 업데이트라면 `#define INIT_VERSION "0.8.18"`로 변경
- `A90v86` kmsg marker를 `A90v87`로 변경
- v49 번호는 재사용하지 않는다.
- `mark_step("..._v86\n")` 계열을 새 버전으로 변경
- README/docs의 latest 기준점은 실기 검증 뒤에만 갱신

검색:

```bash
rg -n 'v86|A90v86|init_v86|boot_linux_v86|ramdisk_v86' workspace/public/archive/stage3/linux_init/init_v87.c workspace/public/archive/stage3/linux_init/v87
```

빌드:

```bash
aarch64-linux-gnu-gcc -static -Os -Wall -Wextra \
  -o workspace/public/archive/stage3/linux_init/init_v87 \
  workspace/public/archive/stage3/linux_init/init_v87.c \
  workspace/public/archive/stage3/linux_init/a90_util.c \
  workspace/public/archive/stage3/linux_init/a90_log.c \
  workspace/public/archive/stage3/linux_init/a90_timeline.c \
  workspace/public/archive/stage3/linux_init/a90_console.c \
  workspace/public/archive/stage3/linux_init/a90_cmdproto.c \
  workspace/public/archive/stage3/linux_init/a90_run.c \
  workspace/public/archive/stage3/linux_init/a90_service.c \
  workspace/public/archive/stage3/linux_init/a90_kms.c \
  workspace/public/archive/stage3/linux_init/a90_draw.c
aarch64-linux-gnu-strip workspace/public/archive/stage3/linux_init/init_v87
file workspace/public/archive/stage3/linux_init/init_v87
sha256sum workspace/public/archive/stage3/linux_init/init_v87
strings workspace/public/archive/stage3/linux_init/init_v87 | rg 'A90 Linux init .*\(v87\)|A90v87'
```

컴파일 경고를 무시하지 말 것.

## 6. Boot image 만들기

검증된 이전 boot image에서 kernel/header 인자를 재사용하고 ramdisk만 바꾼다.

```bash
rm -rf /tmp/a90_boot_v87_unpack
mkdir -p /tmp/a90_boot_v87_unpack
python3 workspace/public/src/third_party/mkbootimg/unpack_bootimg.py \
  --boot_img workspace/private/inputs/boot_images/boot_linux_v86.img \
  --out /tmp/a90_boot_v87_unpack \
  --format=mkbootimg \
  > /tmp/a90_boot_v87_mkbootimg_args.txt
```

ramdisk 생성:

```bash
rm -rf workspace/private/builds/native-init/legacy/ramdisk_v87
mkdir -p workspace/private/builds/native-init/legacy/ramdisk_v87/bin
cp workspace/public/archive/stage3/linux_init/init_v87 workspace/private/builds/native-init/legacy/ramdisk_v87/init
cp workspace/public/archive/stage3/linux_init/a90_sleep workspace/private/builds/native-init/legacy/ramdisk_v87/bin/a90sleep
chmod 755 workspace/private/builds/native-init/legacy/ramdisk_v87/init workspace/private/builds/native-init/legacy/ramdisk_v87/bin/a90sleep
(
  cd workspace/private/builds/native-init/legacy/ramdisk_v87
  find . | LC_ALL=C sort | cpio -o -H newc > ../ramdisk_v87.cpio
)
```

boot image 생성:

```bash
python3 - <<'PYBOOT'
from pathlib import Path
import shlex
import subprocess

args = shlex.split(Path('/tmp/a90_boot_v87_mkbootimg_args.txt').read_text())
for i, item in enumerate(args):
    if item == '--ramdisk':
        args[i + 1] = 'workspace/private/builds/native-init/legacy/ramdisk_v87.cpio'
        break
else:
    raise SystemExit('missing --ramdisk')

cmd = ['python3', 'workspace/public/src/third_party/mkbootimg/mkbootimg.py', *args, '--output', 'workspace/private/inputs/boot_images/boot_linux_v87.img']
print(shlex.join(cmd))
subprocess.run(cmd, check=True)
PYBOOT
```

검증:

```bash
ls -lh workspace/private/builds/native-init/legacy/ramdisk_v87.cpio workspace/private/inputs/boot_images/boot_linux_v87.img
sha256sum workspace/public/archive/stage3/linux_init/init_v87 workspace/private/builds/native-init/legacy/ramdisk_v87.cpio workspace/private/inputs/boot_images/boot_linux_v87.img
strings workspace/private/inputs/boot_images/boot_linux_v87.img | rg 'A90 Linux init .*\(v87\)|A90v87'
```

## 7. Boot image 플래시

TWRP 상태에서만 실행한다.

```bash
adb devices
```

`recovery` 확인 후:

```bash
python3 workspace/public/src/scripts/revalidation/native_init_flash.py \
  workspace/private/inputs/boot_images/boot_linux_v87.img \
  --expect-version "A90 Linux init 0.8.18 (v87)" \
  --bridge-timeout 240 \
  --recovery-timeout 180
```

이 스크립트가 하는 일:

1. local image 존재/정렬/SHA256/expected marker 확인
2. TWRP ADB 대기
3. `/dev/block/by-name/boot` 쓰기
4. prefix readback hash 확인
5. reboot 후 bridge에서 expected version 확인

## 8. Toybox 사용법

빌드:

```bash
workspace/public/src/scripts/revalidation/build_static_toybox.sh
```

TWRP에서 배치:

```bash
adb -s RFCM90CFWXA shell 'mkdir -p /cache/bin && chmod 755 /cache/bin'
adb -s RFCM90CFWXA push workspace/private/inputs/external_tools/userland/bin/toybox-aarch64-static-0.8.13 /cache/bin/toybox
adb -s RFCM90CFWXA shell 'chmod 755 /cache/bin/toybox && sync && sha256sum /cache/bin/toybox'
```

native init에서 사용:

```bash
printf 'run /cache/bin/toybox --help\n' | nc -w 8 127.0.0.1 54321
printf 'run /cache/bin/toybox ifconfig -a\n' | nc -w 8 127.0.0.1 54321
printf 'run /cache/bin/toybox ps -A\n' | nc -w 8 127.0.0.1 54321
```

주의:

- `ps` 단독은 `rc=1`일 수 있다. `ps -A` 또는 `ps -ef` 사용.
- `netcat -h`는 실패할 수 있다. `netcat --help` 사용.
- `ip link`는 출력 후 `No such device`와 `rc=1`이 나올 수 있다.

## 9. USB helper / NCM 사용법

빌드:

```bash
workspace/public/src/scripts/revalidation/build_usbnet_helper.sh
```

TWRP에서 배치:

```bash
adb -s RFCM90CFWXA push workspace/private/inputs/external_tools/userland/bin/a90_usbnet-aarch64-static /cache/bin/a90_usbnet
adb -s RFCM90CFWXA shell 'chmod 755 /cache/bin/a90_usbnet && sync && sha256sum /cache/bin/a90_usbnet'
```

native init에서 상태 확인:

```bash
printf 'run /cache/bin/a90_usbnet status\n' | nc -w 8 127.0.0.1 54321
```

ACM-only rebind:

```bash
printf 'run /cache/bin/a90_usbnet off\n' | nc -w 12 127.0.0.1 54321
```

v48 기준 정상이라면 1~3초 뒤 `version`이 돌아온다.

NCM 임시 probe:

```bash
printf 'run /cache/bin/a90_usbnet probe-ncm\n' | nc -w 8 127.0.0.1 54321
```

host 관찰:

```bash
lsusb -t
ip -br link
```

정상 관찰:

- phone device에 `cdc_acm` + `cdc_ncm` composite interface
- host에 `enx...` 형태 NCM interface
- device에 `ncm0`

device 관찰:

```bash
printf 'run /cache/bin/toybox ifconfig -a\n' | nc -w 10 127.0.0.1 54321
```

주의:

- `probe-ncm`은 약 15초 후 ACM-only로 rollback한다.
- persistent `ncm`은 다음 단계에서 IP/link 검증을 할 때만 사용한다.
- host IP 설정은 root 권한이 필요하다.

## 10. NCM IP 검증 절차

v54에서 persistent NCM, IPv4 ping, IPv6 link-local ping, host → device netcat이 확인됐다.
host IPv4 설정은 root 권한이 필요하므로 재현 시 아래 절차를 따른다.

1. persistent NCM 켜기

```bash
printf 'run /cache/bin/a90_usbnet ncm\n' | nc -w 12 127.0.0.1 54321
```

2. device IP 설정

```bash
printf 'run /cache/bin/toybox ifconfig ncm0 192.168.7.2 netmask 255.255.255.0 up\n' | nc -w 8 127.0.0.1 54321
```

3. host interface 이름 확인

```bash
ip -br link
```

4. host sudo 명령 실행

```bash
sudo ip addr add 192.168.7.1/24 dev <enx...>
sudo ip link set <enx...> up
ping -c 3 192.168.7.2
```

5. IPv6 link-local netcat 확인 예시

```bash
printf 'run /cache/bin/toybox netcat -l -p 2323\n' | nc -w 25 127.0.0.1 54321
printf 'hello\n' | nc -6 -w 5 'fe80::<device-link-local>%<enx...>' 2323
```

6. rollback

```bash
printf 'run /cache/bin/a90_usbnet off\n' | nc -w 12 127.0.0.1 54321
```

## 11. v60 netservice 검증 절차

v60부터 NCM/tcpctl은 native init 안의 opt-in service로도 시작할 수 있다.
기본값은 OFF이므로 실험 후에는 `disable`로 되돌린다.

```bash
printf 'netservice status\n' | nc -w 5 127.0.0.1 54321
printf 'netservice enable\n' | nc -w 20 127.0.0.1 54321
python3 workspace/public/src/scripts/revalidation/ncm_host_setup.py setup
python3 workspace/public/src/scripts/revalidation/tcpctl_host.py ping
python3 workspace/public/src/scripts/revalidation/tcpctl_host.py status
printf 'netservice disable\n' | nc -w 20 127.0.0.1 54321
```

주의:

- `netservice`는 위험 명령으로 분류되므로 메뉴 표시 중 `[busy]`가 나오면 `hide` 후 재시도한다.
- host IP 설정은 root 권한이 필요하고, helper가 안내한 `enx...`에 `192.168.7.1/24`를 설정한다.
- boot-time auto-start는 `/cache/native-init-netservice` flag가 있을 때만 동작한다.
- NCM 재열거마다 host `enx...` 이름이 바뀔 수 있으므로 이전 interface 이름을 재사용하지 않는다.

## 12. v60 netservice reconnect 검증 절차

software UDC 재열거 이후 ACM/NCM/tcpctl 복구를 확인할 때:

```bash
python3 workspace/public/src/scripts/revalidation/netservice_reconnect_soak.py status
python3 workspace/public/src/scripts/revalidation/netservice_reconnect_soak.py once --manual-host-config
```

`--manual-host-config`는 sudo가 불가능한 에이전트 환경에서 현재 새로 생긴 `enx...`에 맞는
host 명령을 출력하고 사용자의 수동 설정을 기다린다.

수동으로 할 때는 stale interface를 쓰지 않는다.

```bash
ip -br link | grep enx
sudo ip addr replace 192.168.7.1/24 dev <current-ncm-enx>
sudo ip link set <current-ncm-enx> up
ping -c 3 -W 2 192.168.7.2
```

## 13. v62 CPU usage/cpustress 검증 절차

CPU usage `%`가 실제로 움직이는지 확인할 때:

```bash
printf 'status\n' | nc -w 5 127.0.0.1 54321
printf 'cpustress 10 8\n' | nc -w 20 127.0.0.1 54321
printf 'status\n' | nc -w 5 127.0.0.1 54321
```

주의:

- `cpustress`는 blocking 명령이다. 중단하려면 q 또는 Ctrl-C를 보낸다.
- CPU-only 부하이므로 GPU busy `%`가 0%로 남는 것은 정상이다.
- `/dev/null`/`/dev/zero`는 v62부터 boot-time에 char device로 보정된다.

## 14. 로그 확인

native init log:

```bash
printf 'logcat\n' | nc -w 8 127.0.0.1 54321
```

USB helper log:

```bash
printf 'cat /cache/usbnet.log\n' | nc -w 8 127.0.0.1 54321
```

netservice log:

```bash
printf 'cat /cache/native-init-netservice.log\n' | nc -w 8 127.0.0.1 54321
```

TWRP에서 직접:

```bash
adb -s RFCM90CFWXA shell 'tail -160 /cache/native-init.log 2>/dev/null || true'
adb -s RFCM90CFWXA shell 'tail -160 /cache/usbnet.log 2>/dev/null || true'
adb -s RFCM90CFWXA shell 'tail -160 /cache/native-init-netservice.log 2>/dev/null || true'
```

## 15. 커밋 전 확인

```bash
git status --short
git diff --check
python3 -m py_compile workspace/public/src/scripts/revalidation/serial_tcp_bridge.py workspace/public/src/scripts/revalidation/native_init_flash.py workspace/public/src/scripts/revalidation/ncm_host_setup.py workspace/public/src/scripts/revalidation/netservice_reconnect_soak.py
bash -n workspace/public/src/scripts/revalidation/build_static_toybox.sh workspace/public/src/scripts/revalidation/build_usbnet_helper.sh
aarch64-linux-gnu-gcc -static -Os -Wall -Wextra -o /tmp/a90_init_check workspace/public/archive/stage3/linux_init/init_v62.c
```

`workspace/private/inputs/boot_images/boot_linux_v*.img`, `workspace/private/builds/native-init/legacy/ramdisk_v*.cpio`, compiled binaries는 `.gitignore` 대상이다.
커밋에는 보통 source, script, docs만 넣는다.

## 16. 자주 틀리는 지점

### `screen`이 바로 종료됨

브릿지가 이미 `/dev/ttyACM0`를 잡고 있거나 권한 문제일 수 있다. 이 프로젝트에서는 직접 `screen`보다
`serial_tcp_bridge.py` + `nc`를 우선한다.

### `adb devices`가 비어 있음

native init 상태에서는 ADB가 기본 제어 채널이 아니다. 정상일 수 있다.
TWRP 상태에서만 `recovery`로 잡히는 것을 기대한다.

### host에 `/dev/ttyACM0`가 있는데 bridge 응답이 없음

v47 이하라면 device-side console fd stale 가능성이 크다. v48 이상으로 올린다.
v48 이상이면 bridge 재시작 후 `version`을 여러 번 시도한다.

### `recovery`나 `echo`가 `[busy] auto menu active`로 막힘

v53+의 정상 보호 동작이다. 메뉴가 보이는 동안은 안전 관찰 명령만 허용한다.

```bash
printf 'hide\n' | nc -w 5 127.0.0.1 54321
sleep 3
printf 'version\n' | nc -w 5 127.0.0.1 54321
```

flash automation은 `native_init_flash.py --from-native`를 쓰면 자동으로 처리한다.

### `run /cache/bin/a90_usbnet probe-ncm` 뒤 첫 `version`이 비어 있음

USB rollback 직후 첫 입력이 유실될 수 있다. 1~3초 후 다시 `version`.

### `Cannot find device "enx..."`가 나옴

NCM 재열거 후 host interface 이름이 바뀐 것이다. 이전 `enx...`를 재사용하지 말고 현재 값을 다시 본다.

```bash
ip -br link | grep enx
```

보통 기존 LAN dongle/host NIC와 새 NCM interface가 같이 보일 수 있으므로,
`a90_usbnet status`의 `ncm.host_addr`와 MAC이 같은 interface를 선택한다.

### TWRP에서 `twrp reboot`가 애매하게 동작함

system/native init으로 나갈 때는 `adb shell 'twrp reboot'`을 사용한다.
`twrp reboot system`은 현재 TWRP CLI에서 no-op처럼 남을 수 있다.
`adb reboot` 또는 `adb shell reboot`는 recovery로 되돌아올 수 있다.

### NCM interface 이름이 매번 다름

host의 `enx...` 이름은 MAC 기반이라 probe마다 바뀔 수 있다. 매번 `ip -br link`로 확인한다.

## 14. 작업 인계 요약

새 에이전트는 다음 순서만 기억하면 된다.

```text
git status 확인
  -> bridge version 확인
  -> 안 되면 host USB/TWRP ADB 확인
  -> 코드 수정은 최신 verified init에서 복사하되, 복구 기준 v48은 보존
  -> static build
  -> ramdisk/boot image 생성
  -> TWRP에서 native_init_flash.py로 flash
  -> version 검증
  -> usbacmreset / helper off로 rebind 안전성 확인
  -> NCM은 probe부터, persistent는 IP 검증 때만
```

복구 기준:

- TWRP가 있으면 boot image를 다시 flash할 수 있다.
- `backups/baseline_a_20260423_030309/boot.img`는 stock 쪽 복구 기준점이다.
- native init에서 위험해지면 `recovery`로 돌아간다.
