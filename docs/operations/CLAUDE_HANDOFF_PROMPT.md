# Claude Handoff Prompt

Date: `2026-04-29`

아래 블록을 Claude나 다른 에이전트에게 그대로 붙여 넣는다.
목표는 **먼저 상태를 확인하고, known-good v48 복구 경로와 latest verified 작업 경로를 혼동하지 않게 하는 것**이다.

```text
너는 /home/temmie/dev/A90_5G_rooting 저장소에서 작업한다.

먼저 반드시 다음 문서를 읽고, 문서와 충돌하는 행동을 하지 마라.

1. docs/operations/NATIVE_INIT_FLASH_AND_BRIDGE_GUIDE.md
2. docs/operations/CLAUDE_NATIVE_INIT_RUNBOOK.md
3. docs/overview/PROJECT_STATUS.md

현재 기준:

- latest verified build: A90 Linux init 0.9.259 (v2187-screenapp-ui-validation)
- latest verified source: workspace/public/src/native-init/ + 빌더 workspace/public/src/scripts/revalidation/build_native_init_boot_v2187_screenapp_ui_validation.py
- latest verified boot image: workspace/private/inputs/boot_images/boot_linux_v2187_screenapp_ui_validation.img
- latest verified boot image SHA256: 0422f854b3e78d36e225012fd89a53016067155e200291d067ff7d71f32091ca
- 현재 기준 사이클: v2187-screenapp-ui-validation screenapp UI validation baseline (V2187 promotion)
- version axes: v2187-screenapp-ui-validation은 boot/init baseline tag, a90_android_execns_probe helper-v427은 포함된 helper marker, V2187은 baseline-promotion run/report 번호다. 전체 규칙은 docs/operations/VERSIONING_POLICY.md를 따른다.
- previous verified boot image: workspace/private/inputs/boot_images/boot_linux_v2186_wifi_ui_polish.img (A90 Linux init 0.9.258 (v2186-wifi-ui-polish))
- known-good fallback native init: A90 Linux init v48
- known-good fallback source: workspace/public/archive/stage3/linux_init/init_v48.c
- known-good fallback boot image: workspace/private/inputs/boot_images/boot_linux_v48.img
- known-good fallback boot image SHA256:
  1c87fa59712395027c5c2e489b15c4f6ddefabc3c50f78d3c235c4508a63e042
- control channel: USB CDC ACM serial bridge at 127.0.0.1:54321
- TWRP recovery is available.

절대 하지 말 것:

- workspace/private/inputs/boot_images/boot_linux_v49.img를 stable처럼 flash하지 마라.
- workspace/public/archive/stage3/linux_init/init_v49.c를 다음 기준으로 삼지 마라.
- 수동 adb shell dd로 boot/recovery/vbmeta/efs/sec_efs/modem/persist/key 계열 partition을 쓰지 마라.
- twrp reboot system을 쓰지 마라. 이 기기에서는 no-op처럼 TWRP에 머물 수 있다.
- adb reboot 또는 adb shell reboot를 TWRP system exit로 신뢰하지 마라. recovery로 되돌아올 수 있다.
- bridge 응답이 없다는 이유만으로 곧바로 다시 flash하지 마라.
- v53+ 화면 메뉴가 떠 있을 때 `[busy]`가 나오면 정상 보호 동작이다. 먼저 `hide`를 보내라.
- v59에서는 host modem probe의 `AT`/`ATE0`/`AT+...` line을 native init shell이 무시한다.
- v60 `netservice`는 기본 OFF다. NCM/tcpctl boot auto-start가 필요할 때만 `netservice enable`을 쓰고,
  실험 후에는 `netservice disable`로 flag와 NCM/tcpctl을 내려라.
- NCM 재열거마다 host `enx...` 이름이 바뀔 수 있다. 이전 interface 이름을 재사용하지 말고
  `a90_usbnet status`의 `ncm.host_addr` 또는 `ip -br link`로 현재 interface를 다시 확인하라.
- v62에서는 `cpustress [sec] [workers]`로 CPU usage gauge를 검증할 수 있고,
  `/dev/null`/`/dev/zero`는 boot-time에 char device로 보정된다.
- v63에서는 자동 메뉴가 APPS/TOOLS/LOGS/NETWORK/POWER 계층으로 확장됐고,
  CPU STRESS app에서 5/10/30/60초 테스트를 선택할 수 있다.
- v64에서는 부팅 직후 큰 TEST 화면 대신 `A90 NATIVE INIT` custom splash가 표시된다.
- v65에서는 splash 긴 문구/footer가 잘리지 않도록 안전 여백과 자동 축소가 적용됐다.
- v66에서는 공식 버전 `0.7.3 (v66)`, `made by temmie0214`, APPS/ABOUT changelog/credits가 추가됐다.
- v67에서는 ABOUT/changelog 글씨가 작게 통일됐고, CHANGELOG가 version list/detail 구조가 됐다.
- v68에서는 HUD menu hidden 상태에서 log tail과 확장 changelog history가 추가됐다.
- v69에서는 VOL+/VOL-/POWER 단일/더블/롱/조합 input gesture layout과 `inputlayout`/`waitgesture`가 추가됐다.
- v70에서는 `TOOLS / INPUT MONITOR`와 `inputmonitor [events]` raw/gesture trace가 추가됐다.
- v71에서는 HUD/menu spare area live log tail이 추가됐고, POWER 메뉴가 아니면 일반 serial 명령은 busy gate를 통과한다.
- v72에서는 cutout-aware `TOOLS / DISPLAY TEST`, `displaytest`, `XBGR8888` color packing fix가 추가됐다.
- v73에서는 `cmdv1`/`A90P1` framed one-shot shell protocol과 `a90ctl.py` host wrapper가 추가됐다.
- v74에서는 `cmdv1x` length-prefixed argv encoding으로 whitespace 인자를 framed protocol에서 검증했다.
- v75에서는 idle-timeout serial reattach 성공 로그를 숨겨 live LOG TAIL noise를 줄였다.
- v76에서는 짧은 `A`/`T`/`ATAT` serial fragment를 unknown command 없이 무시한다.
- v77에서는 `TOOLS / DISPLAY TEST`가 4페이지로 분리되고 `displaytest colors/font/safe/layout`, `cutoutcal [x y size]`, `TOOLS > CUTOUT CAL`을 지원한다.
- v78에서는 SD가 `ext4` label `A90_NATIVE`로 준비되어 있고 `mountsd [status|ro|rw|off|init]`로 `/mnt/sdext/a90` workspace를 제어한다.
- v79에서는 boot-time SD health check가 expected UUID/RW probe를 통과한 SD만 main storage로 쓰고, 실패하면 `/cache` fallback warning을 HUD에 표시한다.

v49 주의:

- v49 image는 local marker와 boot partition prefix readback은 맞았지만,
  system boot 후 Android /system/bin/init second_stage로 진입했다.
- 따라서 v49는 현재 "격리된 실패 실험"이다.
- 새 실험 버전은 v50 이상으로 잡고, 현재 latest verified build에서 최소 diff로 시작한다.

작업 시작 시 반드시 먼저 실행:

git status --short
ps -ef | rg 'serial_tcp_bridge.py|native_init_flash.py' | rg -v rg || true
lsusb | rg 'Samsung|04e8' || true
ls -l /dev/ttyACM* /dev/serial/by-id 2>/dev/null || true
adb devices -l || true
printf 'version\n' | nc -w 5 127.0.0.1 54321 || true
python3 workspace/public/src/scripts/revalidation/a90ctl.py --json status || true

판단:

- bridge에서 A90 Linux init 0.8.17 (v86)이 나오면 latest verified native init boot 상태다. `storage`/`mountsd status`로 SD 상태를 재확인한다.
- bridge에서 A90 Linux init v48이 나오면 known-good fallback native init 상태다.
- adb devices -l에서 recovery면 TWRP 상태다.
- adb devices -l에서 device이고 /proc/1/exe가 /system/bin/init이면 Android 상태다.
- 04e8:6861 + /dev/ttyACM0인데 bridge가 안 되면 사용자가 sudo bridge를 재시작해야 한다.

latest v86 flash가 정말 필요할 때만 이 스크립트를 사용:

python3 workspace/public/src/scripts/revalidation/native_init_flash.py \
  workspace/private/inputs/boot_images/boot_linux_v86.img \
  --from-native \
  --expect-version "A90 Linux init 0.8.17 (v86)" \
  --verify-protocol auto \
  --bridge-timeout 240 \
  --recovery-timeout 180

이 스크립트는 local marker/SHA 확인, remote SHA 확인,
boot partition prefix readback 확인, TWRP no-argument reboot,
bridge version 검증을 수행한다. v53+ 메뉴가 떠 있어 `recovery`가 `[busy]`이면
자동으로 `hide`를 보내고 재시도한다.

known-good v48로 되돌릴 때만:

python3 workspace/public/src/scripts/revalidation/native_init_flash.py \
  workspace/private/inputs/boot_images/boot_linux_v48.img \
  --expect-version "A90 Linux init v48" \
  --bridge-timeout 240 \
  --recovery-timeout 180

TWRP에서 system/native init으로 나갈 때 수동 명령이 필요하면:

adb shell 'twrp reboot'

새 native init 버전을 만들 때:

- latest verified source를 기준으로 복사한다. 단, v48 known-good fallback은 보존한다.
- 현재 실패 번호 v49는 재사용하지 말고 v50 이상을 사용한다.
- local build 후 marker 문자열을 확인한다.
- TWRP flash 전 user confirmation을 받는다.
- flash 후에는 반드시 boot partition prefix SHA readback과 bridge version을 확인한다.

응답할 때는 다음을 명확히 보고한다.

1. 현재 상태가 native init / TWRP / Android 중 무엇인지
2. 어떤 boot image SHA를 확인했는지
3. bridge가 살아 있는지
4. 다음 행동이 read-only인지 write/flash인지
```
