# Samsung Galaxy A90 5G - 현재 상태

> 2026-06-19 native-init track update: the promoted audio-core candidate is
> `A90 Linux init 0.10.0 (v2812-audio-core-promotion-candidate)`, boot image
> `workspace/private/inputs/boot_images/boot_linux_v2812_audio_core_promotion_candidate.img`,
> SHA256 `9cf680ae7dce1dac53b58a72e98668f5f6347bc14d6a64428f06ce2af830cdd0`.
> V2814 validated `audio play --mode listen --execute` on-device with SET-cal, route,
> PCM write/drain, cleanup, and rollback to `v2321` selftest `fail=0`. The current
> safety rollback net remains `v2321` (`0.9.285`, SHA256
> `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`) with deeper
> fallbacks `v2237` and `v48` until the flash-gate contract is deliberately updated.
> Post-promotion observability candidate: `A90 Linux init 0.10.4 (v2824-audio-screenapp-map)`,
> boot image `workspace/private/inputs/boot_images/boot_linux_v2824_audio_screenapp_map.img`,
> SHA256 `2f6b1c902ee3ad1e06850feb04df847cc4c85881154af0ae28f4ce6c56d8035c`.
> V2825 validated the read-only `audio status` core/profile/safety fields, the `selftest verbose`
> PASS `audio` row, and display-only `screenapp audio-map`, then rolled back to `v2321` with `selftest fail=0`. The internal-speaker audio
> feasibility epic is closed; remaining audio work is post-promotion productization/observability.
> The sections below "기준점 A" are older Android/boot-chain context unless a newer native-init report references them.

## 프로젝트 여정 (7-페이즈 arc, 첫 커밋 → 현재)

**관통 주제:** native init = 휴면 vendor 하드웨어를 클린 환경에서 *한 서브시스템씩*
깨우는 "스타팅 모터". 각 에픽 = Tier-A 부품 하나 bring-up. 닫힌 에픽들은 공통적으로
"잘못된 레이어를 한참 추격 → 진짜 게이트 발견 → 안전 체크포인트 남기고 닫음" 패턴을 반복.

1. **Phase 0 — 네이티브 부팅 연구** (`54cf9825` 첫 커밋~): stock A90 커널 위 정적
   `/init` PID1 가능성 확립. TWRP/다운로드모드 복구선, boot 이미지 pack/unpack.
2. **Native init 기반:** stock `4.14.190` 위 정적 `/init` PID1 부팅, serial bridge 제어,
   `selftest`. baseline lineage 시작(`boot_linux_v48` →).
3. **WLAN 에픽 (CLOSED):** 내부 `wlan0` bring-up. 긴 우회 = 외부 SDX50M/eSoC/PCIe/MHI
   추격 → 실제론 **wlan0 = 내부 모뎀(ICNSS)**, `boot_wlan`+`firmware_class` feeder로 도달.
   종착 = 양밴드 end-to-end(associate→DHCP→ping) + native-init wifi 명령군. (외부 경로
   재오픈 금지)
4. **커널 관측 (CLOSED):** KASLR slide 정확 해결(V2216). ROPP 전체 심볼화는 read-only 범위 밖.
5. **커널 보안 recon (CLOSED 2026-06-13):** FastRPC(도달불가)/Binder(취약X)/KGSL(환경게이트)
   n-day 트리아지, 메모리 손상 0. "비파괴 n-day로 EL1 = 불가", "fix-marker ≠ exploitable" ×3.
6. **USB 가젯 런타임 제어 (V2313-2323, layer ① CLOSED):** `usb status`, mass-storage
   expose/remove, identity rodata 패치(SAMSUNG→A90-LNX), multi-LUN. **v2321 롤백 체크포인트 승격.**
7. **오디오/ADSP 에픽 (V2324-V2815, CORE CLOSED; V2825 OBSERVABILITY PASS):** 내부 스피커 재생 경로를 닫음.
   stock HAL/ACDB 관측 → ACDB SET replay → App Type Config `1 69941 48000 16` → route →
   bounded PCM 순서가 native `audio play --execute`에 통합됐고, V2814가 `0.10.0`
   후보에서 SET-cal/route/PCM/cleanup/rollback을 검증했다. V2825는 `0.10.4` 관측성
   후보에서 `audio status`, `selftest verbose` PASS audio row, `screenapp audio-map`을 검증했다. 남은 작업은
   스피커별 route map, 상태 UI, 부트차임 같은 post-promotion productization.

> 갱신 규율: 새 롤백 체크포인트가 승격되면 위 note의 baseline/SHA와 7번 항목 현황을 함께 갱신.

## 기준점 A

**디바이스**: Samsung Galaxy A90 5G (`SM-A908N`)  
**빌드**: `A908NKSU5EWA3` / Android 12  
**루트 상태**: `Magisk 30.7`, `su` 동작 확인  
**ADB**: 정상  
**Wi-Fi**: ADB shell로 WPA2 네트워크 등록 및 연결 확인  
**현재 패키지 수**: `user 0` 기준 `92`

## 현재 확인된 사실

- stock 기반 Android 부팅 가능
- patched AP 부팅 가능
- `adb shell su -c id`로 root 획득 가능
- `getenforce`는 `Enforcing`
- 다운로드 모드 사진 기준 `CURRENT BINARY : Custom (0x303)`
- 다운로드 모드 사진 기준 `FRP LOCK : OFF`, `OEM LOCK : OFF (U)`
- 다운로드 모드 사진 기준 `QUALCOMM SECUREBOOT : ENABLE`, `SECURE DOWNLOAD : ENABLE`
- 다운로드 모드 사진 기준 `WARRANTY VOID : 0x1 (0xE03)`
- Samsung Knox 공식 문서 기준 `KG STATE` 줄은 다운로드 모드에 항상 표시된다고 볼 근거를 찾지 못함
- 최소 부팅 allowlist 재적용 후에도 부팅 유지
- allowlist 밖에 남는 패키지는 현재 `3개`
  - `com.samsung.android.game.gos`
  - `com.samsung.android.themecenter`
  - `com.sec.android.sdhms`

## 현재 공식 목표

이번 트랙의 공식 목표는 `native Linux 부팅 재도전`입니다.

접근 순서는 고정합니다.

### 1. 기준점 유지
- 부팅 가능
- ADB 가능
- `su` 가능
- Wi-Fi 가능
- `stock firmware + patched AP`로 복구 가능

### 2. 1단계 재검증: 부트체인 관찰 재구성
- `stock AP + stock recovery`
- `patched AP + stock recovery`
- `stock AP + TWRP`
- `patched AP + TWRP`
- 각 조합에서 flash 결과, 다운로드 모드 문구, 첫 부팅, recovery fallback, ADB, `su`를 같은 형식으로 기록

### 3. 2단계 재검증: 보안 경계 분해
- boot image 수용 여부
- recovery 교체 허용 여부
- `official binaries only` 발생 조건
- KG 표기 변화와 결과 상관관계
- factory reset 유무 영향

### 4. 3단계 재도전: native Linux 진입 후보 실험
- `patched AP 유지 + Linux 진입 가능성 있는 ramdisk/init 경로`
- `recovery` 경로 활용
- `vbmeta/부트 이미지 조합 변형`
- 필요 시 `TWRP` 기반 보조 경로

## 성공 조건

- `adb devices` 정상
- `getprop sys.boot_completed = 1`
- `adb shell su -c id`가 `uid=0(root)`
- 필요 시 Wi-Fi 연결 가능

단계별 종료 기준:

- 1단계 종료: 4개 기본 조합 결과표 완성
- 2단계 종료: 실제 차단 경계에 대한 결론 1개 이상 확보
- 3단계 종료: 다른 초기 userspace 실행, recovery 기반 Linux 초기 진입, 또는 native 경로 차단 이유 중 하나를 재현 가능한 형태로 확보

## 실패 조건

- bootloop
- recovery fallback
- download mode로 자동 복귀
- ADB 상실
- `su` 상실

## 보류 대상

현재 기준점 안정성 때문에 아래 축은 우선 보류합니다.

- `kgclient`
- `klmsagent`
- `knox.attestation`
- `fmm`
- telephony / IMS / network stack

## 기준점 고정 항목

각 실험 시작 전 다음 값을 반드시 저장합니다.

- 현재 `boot`, `recovery`, `vbmeta`
- 다운로드 모드 화면의 `KG`, `OEM LOCK`, custom binary 문구
- `adb`, `su`, `boot_completed`, `Wi-Fi` 상태
- 필요 시 `ro.build.fingerprint`, `ro.boot.verifiedbootstate`

현재 확보된 다운로드 모드 값:

- `CURRENT BINARY : Custom (0x303)`
- `FRP LOCK : OFF`
- `OEM LOCK : OFF (U)`
- `WARRANTY VOID : 0x1 (0xE03)`
- `QUALCOMM SECUREBOOT : ENABLE`
- `SECURE DOWNLOAD : ENABLE`
- `KG`는 이번 사진으로는 미확인

공식 문서 재확인 결과:

- Samsung Knox Guard 문서는 장치가 Knox Guard에 등록, 활성화, 완료, 삭제되며
  관리 상태가 변한다고 설명함
- 그러나 다운로드 모드에 `KG STATE` 줄이 항상 보여야 한다는 표시 규칙은 설명하지 않음
- 현재는 `KG 미표시`를 독립 관찰값으로 취급하고,
  특정 KG 상태로 자동 해석하지 않음

## 현재 폰 상태

- patched AP (Magisk 30.7) + **TWRP recovery 사용 가능**
- 현재 디바이스 빌드(flash): `stage3/boot_linux_v725_fasttransport.img` (`A90 Linux init 0.9.244 (v725-fasttransport)`)
- 현재 소스 루트: `stage3/linux_init/init_v725_fasttransport.c` + 모듈 `stage3/linux_init/a90_*.c/h` + 헬퍼 `stage3/linux_init/helpers/`
- 공식 숫자 버전: `0.9.244`
- 박힌 빌드 태그: `v725-fasttransport`
- 현재 진행 사이클: `V1336 pre-CNSS provider order classifier PASS → V1337 Android-order pre-CNSS provider observe-only gate` (native Wi-Fi bring-up; 디바이스 재flash 없음 — `CLAUDE.md` 기준)
- 직전 rollback: `stage3/boot_linux_v261.img` (0.9.60)
- creator: `made by temmie0214`
- known-good fallback: `stage3/boot_linux_v48.img` (`A90 Linux init v48`)
- 격리 상태: `stage3/boot_linux_v49.img`는 boot partition prefix readback은 일치했지만
  system boot 후 Android `/system/bin/init second_stage`로 진입했으므로 stable이 아님
- 부팅 흐름: custom boot splash 약 2초 → 상태 HUD/menu 자동 전환 → USB ACM serial shell
- 로그 상태: SD 정상 시 `/mnt/sdext/a90/logs/native-init.log`, fallback 시 `/cache/native-init.log`에 boot/command/result 기록
- blocking 상태: `waitkey`, `readinput`, `watchhud`, `blindmenu` q/Ctrl-C 취소 확인
- boot timeline: `timeline` 명령과 current native log replay 확인
- boot selftest 상태: v725-fasttransport boot selftest `fail=0`, NCM transport baseline acceptance 확인
- HUD 상태: `BOOT OK shell` summary 표시와 `statushud` draw 확인
- run 상태: `/bin/a90sleep` helper로 `run` q 취소 확인
- log 보존: native init → recovery → native init 왕복 후 v44/v45/v47 log append 확인
- storage 상태: `/cache` safe write, ext4 SD workspace `/mnt/sdext/a90`, critical partitions do-not-touch 기준 문서화
- screen menu 상태: 자동 메뉴, 계층형 앱 폴더, CPU stress screen app, input gesture layout, input monitor, serial `hide`/busy gate 확인
- USB 상태: ACM-only gadget `04e8:6861` / host `cdc_acm` 기준 문서화
- userland 상태: static BusyBox 1.36.1 SD runtime 실행과 toybox 0.8.13 fallback 실행 확인
- USB reattach 상태: `usbacmreset`와 외부 helper `off` 후 serial bridge 복구 확인
- USB NCM 상태: host `cdc_ncm` composite, device `ncm0`, IPv4 ping, IPv6 link-local ping, host→device netcat 확인
- NCM 운영 helper 상태: host interface 자동 탐지, ping, static TCP nettest 양방향 payload 검증 완료
- TCP control 상태: NCM 위에서 `a90_tcpctl` ping/status/run/shutdown 검증 완료
- TCP wrapper 상태: `tcpctl_host.py smoke` launch/client/stop 자동 검증 완료
- TCP soak 상태: `tcpctl_host.py soak` 5분/30사이클 안정성 검증 완료
- serial noise 상태: unsolicited `AT`, `ATE0`, `AT+...` modem probe line 무시 확인
- boot netservice 상태: opt-in flag 기반 NCM/tcpctl 부팅 자동 시작, host ping/TCP control, rollback 검증 완료
- 현재 netservice 기본 상태: disabled. `/cache/native-init-netservice` flag가 있을 때만 boot-time NCM/tcpctl 시작
- reconnect 상태: v60 `netservice stop/start` software UDC 재열거 후 NCM/TCP 복구 확인
- physical reconnect 상태: v74 실제 USB 케이블 unplug/replug 후 ACM bridge, NCM ping, tcpctl ping/status/run 복구 확인
- HUD metrics 상태: CPU/GPU 온도와 사용률 `%`를 status/HUD에 표시, `cpustress`로 CPU usage 상승 확인
- dev node 상태: `/dev/null`과 `/dev/zero`를 boot-time char device로 보정 확인
- boot splash 상태: TEST 패턴 대신 `A90 NATIVE INIT` custom splash와 `display-splash` timeline 기록 확인
- splash layout 상태: v65에서 긴 문구/footer 잘림 방지를 위해 안전 여백과 자동 축소 적용
- display test 상태: v77에서 color/pixel, font/wrap, safe/cutout calibration, HUD/menu preview 4페이지와 `cutoutcal` 검증 완료
- SD workspace 상태: SD를 `ext4` label `A90_NATIVE`로 포맷, `mountsd`로 `/mnt/sdext/a90` ro/rw/off/init 검증 완료
- boot storage 상태: v79에서 expected SD UUID/RW probe를 통과하면 `/mnt/sdext/a90`를 main storage로 잡고, 실패하면 `/cache` fallback warning 표시
- source layout 상태: v80에서 PID1 source를 include 기반 기능 모듈로 분리, 단일 static `/init` binary 유지, 실기 flash/bridge 회귀 검증 완료
- base module 상태: v81에서 `a90_config.h`와 `a90_util.c/h`를 실제 compiled module/API로 분리하고 실기 회귀 검증 완료
- log/timeline module 상태: v82에서 `a90_log.c/h`와 `a90_timeline.c/h`를 실제 compiled module/API로 분리하고 실기 회귀 검증 완료
- console module 상태: v83에서 `a90_console.c/h`로 fd/attach/readline/cancel을 실제 compiled module/API로 분리하고 실기 회귀 검증 완료
- cmdproto module 상태: v84에서 `a90_cmdproto.c/h`로 `cmdv1/cmdv1x` frame/status/decode를 실제 compiled module/API로 분리하고 실기 회귀 검증 완료
- run/service module 상태: v85에서 `a90_run.c/h`와 `a90_service.c/h`로 process lifecycle과 PID registry를 실제 compiled module/API로 분리하고 실기 회귀 검증 완료
- KMS/draw module 상태: v86에서 `a90_kms.c/h`와 `a90_draw.c/h`로 DRM/KMS 상태와 framebuffer primitive를 실제 compiled module/API로 분리하고 실기 회귀 검증 완료
- input module 상태: v87에서 `a90_input.c/h`로 물리 버튼 open/close, key wait, gesture wait, decoder, menu action mapping을 실제 compiled module/API로 분리하고 실기 회귀 검증 완료
- about app 상태: `APPS / ABOUT`에서 version, changelog 목록/상세, credits 표시
- UI app split 상태: v106 `a90_app_about.c/h`, v107 `a90_app_displaytest.c/h`, v108 `a90_app_inputmon.c/h` 분리와 실기 flash/quick soak 검증 완료
- structure audit 상태: v109에서 post-v108 구조 감사와 v110 cleanup boundary 기록 완료
- app controller 상태: v110에서 auto-menu IPC/state를 `a90_controller.c/h` API로 이동하고 nonblocking `screenmenu`/busy gate 회귀 확인
- extended soak 상태: v111에서 10-cycle host soak, final status/service/bootstatus/selftest 확인 완료
- USB/NCM service soak 상태: v112에서 opt-in NCM/tcpctl start, host ping/TCP control, ACM rollback, 3-cycle quick soak 확인 완료
- runtime package layout 상태: v113에서 package-friendly runtime paths, helper manifest path, state/service dirs 확인 완료
- helper deployment 상태: v114에서 `helpers manifest`/`plan`, deploy log path, manifest line format 확인 완료
- remote shell hardening 상태: v115에서 `rshell audit`, token mode `0600`, invalid-token rejection, NCM smoke/rollback 확인 완료
- PID1 slim roadmap baseline 상태: v117에서 v117-v122 로드맵, selftest/diag/status HUD/menu, 3-cycle quick soak 확인 완료
- shell metadata API 상태: v118에서 `cmdmeta [verbose]`, unknown command/last result, menu-visible status, 3-cycle quick soak 확인 완료
- menu route API 상태: v119에서 `a90_menu` route helper와 About/Changelog case block 제거, 화면/menu quick soak 확인 완료
- command group API 상태: v120에서 `cmdgroups [verbose]`, grouped `cmdmeta`, storage/network/service representative commands, 3-cycle quick soak 확인 완료
- completion audit 상태: v109-v116 reports/commits/docs/flash evidence 정합성 확인 완료
- log tail panel 상태: HUD hidden과 menu visible spare area에서 current native log tail 표시 확인
- serial reattach log 상태: v75에서 idle-timeout 성공 reattach 로그 억제, 수동/오류 reattach 로그 유지 확인
- serial noise 상태: v76에서 짧은 `A`/`T`/`AT`/`ATA`/`ATAT` fragment와 `AT+GCAP` probe line 무시 확인
- shell protocol 상태: `cmdv1`/`A90P1` framed result와 v74 `cmdv1x` whitespace argv encoding 검증 완료, v84에서 cmdproto API로 분리 완료
- shell/controller 상태: v92에서 last result, command lookup/result formatting, menu/power busy policy를 실제 compiled module/API로 분리 완료
- storage module 상태: v93에서 boot storage state, SD probe, `/cache` fallback, `storage`/`mountsd` command를 실제 compiled module/API로 분리 완료
- selftest module 상태: v94에서 boot-time non-destructive module smoke test와 `selftest` command를 실제 compiled module/API로 추가 완료
- 상세 최신 verified 상태: `docs/reports/NATIVE_INIT_V120_COMMAND_GROUP_API_2026-05-05.md`
- v109-v116 completion audit 기록: `docs/reports/NATIVE_INIT_V109_V116_COMPLETION_AUDIT_2026-05-04.md`
- v120 command group API 기록: `docs/reports/NATIVE_INIT_V120_COMMAND_GROUP_API_2026-05-05.md`
- v119 menu route API 기록: `docs/reports/NATIVE_INIT_V119_MENU_ROUTE_API_2026-05-05.md`
- v118 shell metadata API 기록: `docs/reports/NATIVE_INIT_V118_SHELL_META_API_2026-05-05.md`
- v117 PID1 slim roadmap 기록: `docs/reports/NATIVE_INIT_V117_PID1_SLIM_ROADMAP_2026-05-05.md`
- v115 remote shell hardening 기록: `docs/reports/NATIVE_INIT_V115_RSHELL_HARDENING_2026-05-04.md`
- v114 helper deployment 기록: `docs/reports/NATIVE_INIT_V114_HELPER_DEPLOY_2026-05-04.md`
- v113 runtime package layout 기록: `docs/reports/NATIVE_INIT_V113_RUNTIME_PACKAGE_LAYOUT_2026-05-04.md`
- v112 USB/NCM service soak 기록: `docs/reports/NATIVE_INIT_V112_USB_SERVICE_SOAK_2026-05-04.md`
- v111 extended soak RC 기록: `docs/reports/NATIVE_INIT_V111_EXTENDED_SOAK_RC_2026-05-04.md`
- v110 app controller cleanup 기록: `docs/reports/NATIVE_INIT_V110_APP_CONTROLLER_CLEANUP_2026-05-04.md`
- v109 structure audit 기록: `docs/reports/NATIVE_INIT_V109_STRUCTURE_AUDIT_2026-05-04.md`
- v108 input monitor app split 기록: `docs/reports/NATIVE_INIT_V108_UI_APP_INPUTMON_2026-05-04.md`
- v107 displaytest app split 기록: `docs/reports/NATIVE_INIT_V107_UI_APP_DISPLAYTEST_2026-05-04.md`
- v106 about app split 기록: `docs/reports/NATIVE_INIT_V106_UI_APP_ABOUT_2026-05-04.md`
- v105 soak RC 기록: `docs/reports/NATIVE_INIT_V105_SOAK_RC_2026-05-04.md`
- v104 Wi-Fi feasibility 기록: `docs/reports/NATIVE_INIT_V104_WIFI_FEASIBILITY_2026-05-04.md`
- v103 Wi-Fi inventory 기록: `docs/reports/NATIVE_INIT_V103_WIFI_INVENTORY_2026-05-04.md`
- v102 diagnostics 기록: `docs/reports/NATIVE_INIT_V102_DIAGNOSTICS_2026-05-03.md`
- v101 service manager 기록: `docs/reports/NATIVE_INIT_V101_SERVICE_MANAGER_2026-05-03.md`
- v100 remote shell 기록: `docs/reports/NATIVE_INIT_V100_REMOTE_SHELL_2026-05-03.md`
- v99 BusyBox userland 기록: `docs/reports/NATIVE_INIT_V99_BUSYBOX_USERLAND_2026-05-03.md`
- v98 helper deploy 기록: `docs/reports/NATIVE_INIT_V98_HELPER_DEPLOY_2026-05-03.md`
- v97 SD runtime root 기록: `docs/reports/NATIVE_INIT_V97_SD_RUNTIME_ROOT_2026-05-03.md`
- v96 structure audit 기록: `docs/reports/NATIVE_INIT_V96_STRUCTURE_AUDIT_2026-05-03.md`
- v95 netservice/USB API 기록: `docs/reports/NATIVE_INIT_V95_NETSERVICE_USB_API_2026-05-03.md`
- v94 boot selftest API 기록: `docs/reports/NATIVE_INIT_V94_BOOT_SELFTEST_API_2026-05-03.md`
- v93 storage API 기록: `docs/reports/NATIVE_INIT_V93_STORAGE_API_2026-05-02.md`
- v92 shell/controller API 기록: `docs/reports/NATIVE_INIT_V92_SHELL_CONTROLLER_API_2026-05-02.md`
- v87 input API 기록: `docs/reports/NATIVE_INIT_V87_INPUT_API_2026-04-30.md`
- v86 KMS/draw API 기록: `docs/reports/NATIVE_INIT_V86_KMS_DRAW_API_2026-04-30.md`
- v85 run/service API 기록: `docs/reports/NATIVE_INIT_V85_RUN_SERVICE_API_2026-04-30.md`
- v84 cmdproto API 기록: `docs/reports/NATIVE_INIT_V84_CMDPROTO_API_2026-04-30.md`
- v83 console API 기록: `docs/reports/NATIVE_INIT_V83_CONSOLE_API_2026-04-29.md`
- v83 dependency map 기록: `docs/reports/NATIVE_INIT_V83_CONSOLE_SHELL_CMDPROTO_DEPENDENCY_MAP_2026-04-29.md`
- v82 log/timeline modules 기록: `docs/reports/NATIVE_INIT_V82_LOG_TIMELINE_2026-04-29.md`
- v81 config/util modules 기록: `docs/reports/NATIVE_INIT_V81_CONFIG_UTIL_2026-04-29.md`
- v80 source modules 기록: `docs/reports/NATIVE_INIT_V80_SOURCE_MODULES_2026-04-29.md`
- v79 boot storage 기록: `docs/reports/NATIVE_INIT_V79_BOOT_STORAGE_2026-04-29.md`
- v78 SD workspace 기록: `docs/reports/NATIVE_INIT_V78_SD_WORKSPACE_2026-04-29.md`
- v77 display test pages 기록: `docs/reports/NATIVE_INIT_V77_DISPLAY_TEST_PAGES_2026-04-27.md`
- v76 AT fragment filter 기록: `docs/reports/NATIVE_INIT_V76_AT_FRAGMENT_FILTER_2026-04-27.md`
- v75 idle reattach log 기록: `docs/reports/NATIVE_INIT_V75_QUIET_IDLE_REATTACH_2026-04-27.md`
- v74 cmdv1x 기록: `docs/reports/NATIVE_INIT_V74_CMDV1X_ARG_ENCODING_2026-04-27.md`
- v73 cmdv1 protocol 기록: `docs/reports/NATIVE_INIT_V73_CMDV1_PROTOCOL_2026-04-27.md`
- v72 display test 기록: `docs/reports/NATIVE_INIT_V72_DISPLAY_TEST_2026-04-27.md`
- v70 input monitor 기록: `docs/reports/NATIVE_INIT_V70_INPUT_MONITOR_2026-04-26.md`
- v69 input layout 기록: `docs/reports/NATIVE_INIT_V69_INPUT_LAYOUT_2026-04-26.md`
- v68 log tail/history 기록: source `stage3/linux_init/init_v68.c`와 v69 changelog에 반영
- v67 changelog detail 기록: `docs/reports/NATIVE_INIT_V67_CHANGELOG_DETAILS_2026-04-26.md`
- v66 about/versioning 기록: `docs/reports/NATIVE_INIT_V66_ABOUT_VERSIONING_2026-04-26.md`
- v65 splash safe layout 기록: `docs/reports/NATIVE_INIT_V65_SPLASH_SAFE_LAYOUT_2026-04-26.md`
- v64 boot splash 기록: `docs/reports/NATIVE_INIT_V64_BOOT_SPLASH_2026-04-26.md`
- v63 app menu 기록: `docs/reports/NATIVE_INIT_V63_APP_MENU_2026-04-26.md`
- v62 CPU stress/dev node 기록: `docs/reports/NATIVE_INIT_V62_CPUSTRESS_2026-04-26.md`
- v61 CPU/GPU usage 기록: `docs/reports/NATIVE_INIT_V61_CPU_GPU_USAGE_2026-04-26.md`
- v60 reconnect 기록: `docs/reports/NATIVE_INIT_V60_RECONNECT_2026-04-26.md`
- v74 physical USB reconnect 기록: `docs/reports/NATIVE_INIT_V74_PHYSICAL_USB_RECONNECT_2026-04-27.md`
- v60 netservice 기록: `docs/reports/NATIVE_INIT_V60_NETSERVICE_2026-04-26.md`
- v59 AT noise 기록: `docs/reports/NATIVE_INIT_V59_AT_NOISE_2026-04-26.md`
- v58 TCP soak 기록: `docs/reports/NATIVE_INIT_V58_TCPCTL_SOAK_2026-04-26.md`
- v57 TCP host wrapper 기록: `docs/reports/NATIVE_INIT_V57_TCPCTL_HOST_WRAPPER_2026-04-26.md`
- v56 TCP control 기록: `docs/reports/NATIVE_INIT_V56_TCPCTL_2026-04-26.md`
- v55 NCM ops 기록: `docs/reports/NATIVE_INIT_V55_NCM_OPS_2026-04-25.md`
- v54 NCM link 기록: `docs/reports/NATIVE_INIT_V54_NCM_LINK_2026-04-25.md`
- v48 USB reattach/NCM 기록: `docs/reports/NATIVE_INIT_V48_USB_REATTACH_NCM_2026-04-25.md`
- v47 screen menu 기록: `docs/reports/NATIVE_INIT_V47_SCREEN_MENU_2026-04-25.md`
- USB gadget map 기록: `docs/reports/NATIVE_INIT_USB_GADGET_MAP_2026-04-25.md`
- static userland 후보 기록: `docs/reports/NATIVE_INIT_USERLAND_CANDIDATES_2026-04-25.md`
- v46 storage map 기록: `docs/reports/NATIVE_INIT_STORAGE_MAP_2026-04-25.md`
- v45 run/log preservation 기록: `docs/reports/NATIVE_INIT_V45_RUN_LOG_2026-04-25.md`
- v44 HUD boot summary 기록: `docs/reports/NATIVE_INIT_V44_HUD_BOOT_2026-04-25.md`
- v43 boot timeline 기록: `docs/reports/NATIVE_INIT_V43_TIMELINE_2026-04-25.md`
- v42 blocking cancel 기록: `docs/reports/NATIVE_INIT_V42_CANCEL_2026-04-25.md`
- v41 파일 로그 기록: `docs/reports/NATIVE_INIT_V41_LOGGING_2026-04-25.md`
- v40 shell return code 기록: `docs/reports/NATIVE_INIT_V40_BUILD_2026-04-25.md`
- v39 기준 전체 상태 기록: `docs/reports/NATIVE_INIT_V39_STATUS_2026-04-25.md`
- 다음 작업 목록: `docs/plans/NATIVE_INIT_NEXT_WORK_2026-04-25.md`
- 복구: `backups/baseline_a_20260423_030309/boot.img` dd 복구 가능

## Stage 3 달성 사항 (2026-04-23)

### 3-1. native Linux init 진입 (초기)

- `aarch64-linux-gnu-gcc -static` 으로 빌드한 static init 바이너리를 ramdisk에 탑재
- Android kernel이 우리 init을 pid 1로 실행
- proc / sys / devtmpfs / ext4(/dev/block/sda31) 마운트 성공
- 핵심 우회: devtmpfs async 초기화 문제를 `mknod(makedev(259,15))` 로 해결

### 3-2. USB ACM serial console + 인터랙티브 셸 (v8~v116)

**현재 버전**: `init_v725_fasttransport` (`stage3/boot_linux_v725_fasttransport.img`) / `0.9.244 (v725-fasttransport)`

ADB 방식이 막혀 USB CDC ACM serial (ttyGS0)로 전환. v79까지 반복 안정화:

- USB gadget: configfs `acm.usb0` function, UDC `a600000.dwc3`
- host 측: `/dev/ttyACM0` → `serial_tcp_bridge.py` → `127.0.0.1:54321` TCP
- 부팅 흐름: custom boot splash(~2초) → 상태 HUD 자동 전환 → ACM serial shell

**버전별 주요 마일스톤:**

| 버전 | 추가 내용 |
|---|---|
| v8~v15 | USB ACM serial + 인터랙티브 셸 기본 구조 |
| v22 | DRM/KMS ioctl 직접 제어 (`kmssolid`, `kmsframe`, `kmsprobe`), 부팅 시 자동 화면 표시 |
| v36~v39 | command table 리팩터, sensor HUD (배터리/온도/메모리/전력), autohud, `status` 명령 |
| v40 | shell return code 정밀화, `[done]`/`[err]` 구분 |
| v41 | `/cache/native-init.log` 파일 로그, `logpath`/`logcat` 명령 |
| v42 | blocking command 취소 통일 (`q`/`Ctrl-C` → `-ECANCELED`) |
| v43 | boot readiness timeline, `timeline` 명령 |
| v44 | boot summary HUD (`BOOT OK shell Xs` / `BOOT ERR`), `bootstatus` 명령 |
| v45 | `run` q-cancel 검증, static `a90_sleep` helper |
| v46 | safe storage map 문서화 |
| v47 | on-screen menu (`menu`/`screenmenu`): VOL+/VOL-/POWER 버튼 기반 RESUME/STATUS/LOG/RECOVERY/REBOOT/POWEROFF |
| v48 | ACM rebind 안정화 (`reattach`/`usbacmreset`), `a90_usbnet` helper, NCM composite probe 확인 |
| v49 | 상태 HUD TUI 개선 시도. local marker/readback은 맞았지만 system boot가 Android userspace로 진입해 격리 |
| v52 | 상태 HUD/menu TUI 개선. BAT/CPU/GPU/MEM/PWR, 버튼 메뉴, footer 표시 실기 확인 |
| v53 | menu-active serial busy gate, `hide` request, flash script auto-hide 재시도 |
| v59 | unsolicited `AT`/`ATE0`/`AT+...` serial modem probe line 무시 |
| v60 | opt-in boot-time NCM/tcpctl `netservice`, host ping/TCP control 검증, disable rollback 확인 |
| v60 | `netservice stop/start` software UDC 재열거 뒤 NCM/TCP 복구 확인 |
| v61 | HUD/status에 CPU usage `%`, GPU busy `%` 표시 |
| v62 | `cpustress`로 CPU usage gauge 검증, `/dev/null`/`/dev/zero` char node guard |
| v63 | APPS/MONITORING/TOOLS/LOGS/NETWORK/POWER 계층 메뉴와 CPU stress 시간 선택 app |
| v64 | TEST 부팅 화면을 `A90 NATIVE INIT` custom boot splash로 교체 |
| v65 | boot splash 긴 문구/footer 잘림 방지 safe layout |
| v66 | semantic version `0.7.3`, `made by temmie0214`, ABOUT/changelog/credits app |
| v67 | ABOUT/changelog 작은 글씨 통일, version별 changelog detail 화면 |
| v68 | HUD menu hidden 상태에서 log tail 표시, changelog history 확장 |
| v69 | VOL+/VOL-/POWER 단일/더블/롱/조합 input gesture layout |
| v70 | TOOLS / INPUT MONITOR와 `inputmonitor [events]` raw/gesture trace |
| v71 | HUD/menu spare area live log tail panel |
| v72 | Display test screen and framebuffer color fix |
| v73 | `cmdv1`/`A90P1` framed shell protocol and `a90ctl.py` host wrapper |
| v74 | `cmdv1x` length-prefixed argv encoding으로 whitespace 인자 frame 전송 |
| v75 | idle-timeout serial reattach 성공 로그 억제로 live log tail noise 감소 |
| v76 | 짧은 `A`/`T`/`ATAT` serial fragment filter로 unknown command noise 감소 |
| v77 | display test 4페이지 분리와 cutout calibration 추가 |
| v78 | ext4 SD workspace `/mnt/sdext/a90`와 `mountsd` storage manager 추가 |
| v79 | boot-time SD health check와 `/cache` fallback warning 추가 |
| v80 | PID1 source layout을 include 기반 기능 모듈로 분리 |
| v81 | `a90_config.h`, `a90_util.c/h` 실제 base API 분리 |
| v82 | `a90_log.c/h`, `a90_timeline.c/h` 실제 log/timeline API 분리 |
| v83 | `a90_console.c/h` 실제 console fd/attach/readline/cancel API 분리 |
| v84 | `a90_cmdproto.c/h` 실제 `cmdv1/cmdv1x` frame/decode API 분리 |
| v85 | `a90_run.c/h`, `a90_service.c/h` 실제 process/service lifecycle API 분리 |
| v86 | `a90_kms.c/h`, `a90_draw.c/h` 실제 KMS/draw API 분리 |
| v87 | `a90_input.c/h` 실제 input/gesture API 분리 |
| v88 | `a90_hud.c/h` 실제 boot splash/status HUD/log tail renderer API 분리 |
| v89 | `a90_menu.c/h` 실제 menu model/state API 분리와 nonblocking `screenmenu` |
| v90 | `a90_metrics.c/h` 실제 battery/CPU/GPU/MEM/power snapshot API 분리 |
| v91 | `/bin/a90_cpustress` helper로 CPU stress worker를 PID1 밖으로 분리 |
| v92 | `a90_shell.c/h`, `a90_controller.c/h` 실제 shell metadata / menu busy policy API 분리 |
| v93 | `a90_storage.c/h` 실제 boot storage state / SD probe / cache fallback API 분리 |
| v94 | `a90_selftest.c/h` boot-time non-destructive module smoke test API 추가 |
| v95 | `a90_usb_gadget.c/h`, `a90_netservice.c/h` USB configfs/UDC 및 NCM/tcpctl policy API 분리 |
| v96 | structure audit / refactor debt cleanup, stale console klog marker 정리 |
| v97 | `a90_runtime.c/h` SD runtime root / cache fallback / runtime directory contract |
| v98 | `a90_helper.c/h` helper inventory / manifest path / preferred fallback policy |
| v99 | `a90_userland.c/h` BusyBox/toybox inventory / optional userland command API |
| v100 | `/bin/a90_rshell` custom token TCP remote shell over USB NCM |
| v101 | `a90_service.c/h` metadata/status API와 `service` command view |
| v102 | `a90_diag.c/h` diagnostics/log bundle API와 `diag_collect.py` host collector |
| v105 | `native_soak_validate.py` host quick-soak validator and recovery-friendly RC baseline |
| v104 | `a90_wififeas.c/h` Wi-Fi feasibility gate and read-only no-go/baseline-required decision |
| v103 | `a90_wifiinv.c/h` Wi-Fi read-only inventory API와 `wifi_inventory_collect.py` host collector |

**확보된 관찰/제어 범위 (v105 verified build 기준):**

| 항목 | 상태 |
|---|---|
| USB ACM serial 제어채널 | 작동, rebind 후 복구 가능 (`usbacmreset`) |
| Console API module | 작동 — fd는 `a90_console.c` 내부 static, attach/reattach/readline/cancel API 회귀 검증 |
| Cmdproto API module | 작동 — `A90P1` frame/status와 `cmdv1x` whitespace argv decode 회귀 검증 |
| Run/service API module | 작동 — `run`/`runandroid`/`tcpctl`/`adbd` lifecycle와 q cancel 회귀 검증 |
| KMS/draw API module | 작동 — DRM/KMS 상태와 framebuffer primitive를 실제 `.c/.h` API로 분리 |
| Input API module | 작동 — input context, key wait, gesture wait, decoder, menu action mapping을 실제 `.c/.h` API로 분리 |
| HUD/menu/metrics API modules | 작동 — renderer, menu model, metric snapshot 책임을 분리하고 실기 회귀 검증 |
| Storage API module | 작동 — boot storage state, SD probe, cache fallback, `storage`/`mountsd` command API 분리 |
| Runtime API module | 작동 — SD runtime root, cache fallback, runtime directory contract, `runtime` command API 분리 |
| Helper API module | 작동 — helper inventory, manifest path, preferred helper fallback, `helpers` command API 분리 |
| Userland API module | 작동 — BusyBox/toybox inventory, optional command path, `userland`/`busybox`/`toybox` command API 분리 |
| 인터랙티브 셸 | 작동, command table 기반 dispatch |
| /proc, /sys, /dev 마운트 | 작동 |
| /cache (ext4) 마운트 + 로그 | 작동. v79부터 SD 정상 시 `/mnt/sdext/a90/logs/native-init.log`, fallback 시 `/cache/native-init.log` |
| /mnt/system (sda28, ext4 ro) | 작동 (`mountsystem`) |
| system-as-root 구조 탐색 | 작동 (`prepareandroid`) |
| 물리 버튼 입력 (power/vol+/vol-) | 작동 (`waitkey`, `blindmenu`) |
| backlight sysfs 제어 | 작동 |
| DRM/KMS ioctl (dumb buffer + SETCRTC) | 작동 — 실화면 출력 확인 |
| 센서 HUD (배터리/온도/메모리/전력/CPU·GPU 사용률) | 작동 (`status`, `autohud`) |
| 부팅 시 custom splash → HUD 자동 전환 | 작동 |
| boot summary 화면 표시 (`BOOT OK`) | 작동 |
| on-screen 버튼 메뉴 | 작동 (`menu`/`screenmenu`) |
| Input gesture layout | 작동 — `inputlayout` 출력, `screenmenu`/`blindmenu` gesture action 적용 |
| Input monitor | 작동 — `TOOLS / INPUT MONITOR`, `inputmonitor [events]` raw/gesture trace 추가 |
| menu-active serial gate | 작동 — 위험 명령 `[busy]`, `version`/`status` 허용, `hide` 후 재개 |
| blocking 명령 취소 (q/Ctrl-C) | 작동 |
| boot timeline 기록 | 작동 (`timeline`) |
| static toybox 실행 | 작동 (`/cache/bin/toybox`, ifconfig/route/netcat 확인) |
| USB NCM composite probe | 작동 — host `cdc_ncm` + device `ncm0` 생성 확인 |
| USB NCM IP/통신 | 작동 — IPv4 ping 3/3, IPv6 link-local ping, host→device netcat 확인 |
| NCM TCP control | 작동 — `a90_tcpctl` ping/status/run/shutdown 확인 |
| TCP control wrapper | 작동 — `tcpctl_host.py smoke` 확인 |
| TCP control soak | 작동 — 5분/30사이클, TCP ping 30/30, host ping 30/30, 실패 0 |
| Remote shell over NCM | 작동 — `/bin/a90_rshell` token auth, `192.168.7.2:2326`, `rshell_host.py smoke`, stop/rollback 확인 |
| Service manager view | 작동 — `service list/status/start/stop/enable/disable`, autohud/tcpctl/rshell lifecycle, unsupported enable error 확인 |
| Diagnostics/log bundle | 작동 — `diag summary/full/paths/bundle`, host `diag_collect.py`, SD runtime log bundle 확인 |
| Wi-Fi read-only inventory | 작동 — `wifiinv summary/full/paths`, host `wifi_inventory_collect.py`, 기본 native 상태와 `mountsystem ro` 확장 인벤토리 확인 |
| Serial AT noise filter | 작동 — `AT`, `ATE0`, `AT+GCAP`, `ATQ0 ...` unknown 없이 무시 |
| Boot netservice | 작동 — opt-in flag로 NCM/tcpctl boot auto-start, `netservice disable` rollback 확인 |
| Software UDC reconnect | 작동 — `netservice stop/start` 후 새 host `enx...`, ping, TCP control 복구 확인 |
| Physical USB reconnect | 작동 — 실제 cable unplug/replug 후 ACM bridge, NCM ping, tcpctl 복구 확인 |
| CPU/GPU usage HUD | 작동 — CPU `/proc/stat` delta, GPU KGSL `gpu_busy_percentage` 표시 확인 |
| CPU stress helper | 작동 — `cpustress 10 8` 후 CPU usage 29% 상승 확인 |
| Essential `/dev` nodes | 작동 — `/dev/null` rdev `1:3`, `/dev/zero` rdev `1:5` boot-time 보정 |
| Hierarchical app menu | 작동 — APPS/TOOLS/CPU STRESS 시간 선택과 LOG/NETWORK app 화면 |
| Boot splash | 작동 — `A90 NATIVE INIT` splash, `display-splash` timeline 기록, v65 safe layout 적용 |
| Display test app | 작동 — `displaytest colors/font/safe/layout`, 4페이지 렌더링, auto menu VOL+/VOL- page 이동 |
| About app | 작동 — APPS/ABOUT에 VERSION/CHANGELOG 목록/상세/CREDITS, bridge metadata 검증 완료 |
| Serial reattach log hygiene | 작동 — idle-timeout 성공 로그 억제, command reattach 로그 유지 |
| Serial noise fragment filter | 작동 — `A`/`T`/`AT`/`ATA`/`ATAT`와 `AT+GCAP` 무시, 정상 `version` 유지 |
| Shell protocol v1 | 작동 — `cmdv1`/`A90P1` BEGIN/END, rc/status 파싱, `a90ctl.py` text/JSON wrapper와 v74 `cmdv1x` whitespace argv 검증 |
| ADB (adbd) | **보류** — ep1/ep2 미생성, zombie |

**버튼 매핑:**

| event | device | keys |
|---|---|---|
| event0 | qpnp_pon | KEY_POWER, KEY_VOLUMEDOWN |
| event3 | gpio_keys | KEY_VOLUMEUP |

### 3-3. ADB 상태

- adbd: zombie 상태로 종료, ep1/ep2 미생성
- 원인: Android property/SELinux/bionic 환경 없이 단독 실행 불안정
- 현재 방향: ACM serial + USB NCM을 우선 안정화. ADB는 serial/NCM보다 가치가 커질 때 재검토

## 다음 후보 작업

현재 활성 작업은 native Wi-Fi bring-up이다 (디바이스 rollback/test 기준은 `0.9.244 (v725-fasttransport)`,
연구 사이클만 진행). 상세는 `CLAUDE.md`와
`docs/plans/NATIVE_INIT_NEXT_WORK_2026-04-25.md`를 기준으로 한다.

1. **V1337** — Android-order pre-CNSS provider observe-only gate
   (`pm_proxy_helper`, QRTR/RFS/pd-mapper companions, `per_mgr`, `per_proxy`, `cnss_diag`를 `cnss-daemon` 전에 맞춘 뒤 `/dev/subsys_esoc0`는 닫아두고 WLFW precondition 여부만 관찰)
2. **SDX50M eSoC response prerequisite gate** — V1337 결과에 따라 CNSS/provider state 보강 또는 eSoC trigger 재시도 범위를 결정

**복구**: `backups/baseline_a_20260423_030309/boot.img` dd 복구 가능


---

## README 이관: 상세 검증 노트 (v48–V1165 이력)

아래는 README.md 상단에 있던 `<details>` 상세 검증 노트를 그대로 옮긴 것이다.
README는 핵심 현재 상태만 유지하고, 버전별 검증 이력은 여기에 보존한다.
더 깊은 이력은 git log와 `CHANGELOG.md`, `docs/reports/`를 기준으로 재구성할 수 있다.

- latest verified source: `stage3/linux_init/init_v319.c` + `stage3/linux_init/v319/*.inc.c` + `stage3/linux_init/helpers/a90_cpustress.c` + `stage3/linux_init/helpers/a90_rshell.c` + `stage3/linux_init/helpers/a90_longsoak.c` + `stage3/linux_init/a90_config.h` + `stage3/linux_init/a90_util.c/h` + `stage3/linux_init/a90_log.c/h` + `stage3/linux_init/a90_timeline.c/h` + `stage3/linux_init/a90_console.c/h` + `stage3/linux_init/a90_cmdproto.c/h` + `stage3/linux_init/a90_run.c/h` + `stage3/linux_init/a90_service.c/h` + `stage3/linux_init/a90_kms.c/h` + `stage3/linux_init/a90_draw.c/h` + `stage3/linux_init/a90_input.c/h` + `stage3/linux_init/a90_input_cmd.c/h` + `stage3/linux_init/a90_kernelinv.c/h` + `stage3/linux_init/a90_sensormap.c/h` + `stage3/linux_init/a90_pstore.c/h` + `stage3/linux_init/a90_watchdoginv.c/h` + `stage3/linux_init/a90_tracefs.c/h` + `stage3/linux_init/a90_hud.c/h` + `stage3/linux_init/a90_menu.c/h` + `stage3/linux_init/a90_metrics.c/h` + `stage3/linux_init/a90_shell.c/h` + `stage3/linux_init/a90_controller.c/h` + `stage3/linux_init/a90_storage.c/h` + `stage3/linux_init/a90_selftest.c/h` + `stage3/linux_init/a90_usb_gadget.c/h` + `stage3/linux_init/a90_netservice.c/h` + `stage3/linux_init/a90_pid1_guard.c/h` + `stage3/linux_init/a90_reaper.c/h` + `stage3/linux_init/a90_runtime.c/h` + `stage3/linux_init/a90_helper.c/h` + `stage3/linux_init/a90_userland.c/h` + `stage3/linux_init/a90_diag.c/h` + `stage3/linux_init/a90_exposure.c/h` + `stage3/linux_init/a90_wifiinv.c/h` + `stage3/linux_init/a90_wififeas.c/h` + `stage3/linux_init/a90_changelog.c/h` + `stage3/linux_init/a90_longsoak.c/h` + `stage3/linux_init/a90_app_about.c/h` + `stage3/linux_init/a90_app_cpustress.c/h` + `stage3/linux_init/a90_app_displaytest.c/h` + `stage3/linux_init/a90_app_inputmon.c/h` + `stage3/linux_init/a90_app_log.c/h` + `stage3/linux_init/a90_app_network.c/h`
- latest verified boot image: `stage3/boot_linux_v319.img`
- previous verified source-layout baseline: `stage3/linux_init/init_v80.c` + `stage3/linux_init/v80/*.inc.c`
- known-good fallback: `stage3/boot_linux_v48.img`
- local artifact retention: keep `v319` latest, `v261` rollback, and `v48` known-good; older ignored `stage3/boot_linux_v*.img`, `stage3/ramdisk_v*`, and compiled `init_v*` outputs are cleanup candidates
- serial transfer: v319 adds scoped `appendfile` plus 4096-byte shell/cmdv1x buffers for private runtime file staging over ACM
- versioning policy: numeric `0.x.y` identifies native init / boot image builds; `v###` identifies project cycles, host tooling, plans, reports, validation gates, or legacy native build tags; see `docs/operations/VERSIONING_POLICY.md`
- control channel: USB CDC ACM serial (`/dev/ttyGS0` ↔ `/dev/ttyACM0`)
- host bridge: `scripts/revalidation/serial_tcp_bridge.py --port 54321`
- display: custom boot splash 후 상태 HUD/menu 자동 전환
- input: VOL+/VOL-/POWER 단일/더블/롱/조합 입력 layout과 input monitor 확인
- logging: SD 정상 시 `/mnt/sdext/a90/logs/native-init.log`, fallback 시 `/cache/native-init.log`, emergency fallback 시 private `/tmp/a90-native/native-init.log`
- blocking cancel: `waitkey`/`readinput`/`watchhud`/`blindmenu` q/Ctrl-C 취소 확인
- boot timeline: `timeline` 명령과 log replay 확인
- boot selftest: `selftest`/`bootstatus`에서 non-destructive module smoke test `pass=11 warn=1 fail=0` 확인; unverified SD BusyBox is intentionally blocked until manifest SHA-256 is provided
- HUD boot summary: `BOOT OK shell` 표시 확인
- run cancel: `/bin/a90sleep` helper로 q 취소 확인
- storage: `/cache` safe write, ext4 SD workspace `/mnt/sdext/a90`, critical partitions do-not-touch
- storage I/O: v161에서 `/mnt/sdext/a90/test-io` 4K/64K/1M/16M write/read/hash/rename/sync/unlink 검증 완료
- process concurrency: v162에서 helper churn 32/32, tcpctl parallel 18/18, `/bin/a90_cpustress 3 2`, busy gate, zombie/fd snapshot 검증 완료
- CPU/memory/thermal: v163에서 `/bin/a90_cpustress` 5사이클, tmpfs 32MiB hash verify, max CPU 43.1C/GPU 39.4C/BAT 31.1C, status max 32ms 검증 완료
- scheduler latency proxy: v164에서 idle/post-cpustress/post-tmpfs-io 각 20샘플, p99 101-102ms, missed deadline 0 검증 완료
- USB recovery: v165에서 `usbacmreset` 3회와 `a90_usbnet ncm/off` 복구 5/5, max recovery 1.905s, final ACM-only 확인
- network throughput: v166은 host NCM IP assignment에 local sudo가 필요해 deferred 처리, operator-configured NCM에서 재개
- FS exerciser mini: v167에서 `/mnt/sdext/a90/test-fsx` 64 deterministic ops, create/write/truncate/rename/unlink/fsync/verify/cleanup PASS
- kselftest feasibility: v168에서 full kselftest/LTP 실행 없이 safe candidates 4, conditional/unknown 5, blocked 6으로 read-only 분류 완료
- fault/debug feasibility: v169에서 debugfs/tracefs/usbmon/fault-injection/pstore reboot/watchdog/crash 계열을 read-only 분류하고 위험 기능은 opt-in 또는 blocked로 유지
- host test harness: v170에서 `scripts/revalidation/a90harness/` 공용 device/evidence/schema와 `native_test_supervisor.py smoke` 추가, `version/status` smoke PASS
- host observer: v171에서 `native_test_supervisor.py observe`와 `observer.jsonl`/`observer-summary.json` read-only sampler 추가, 15초 실기 관찰 samples=21 failures=0
- host module runner: v172에서 `native_test_supervisor.py run kselftest-feasibility`와 `prepare/run/cleanup/verify` module API 추가, observer 포함 실기 run PASS
- host module ports: v173에서 `cpu-mem-thermal` smoke PASS, `storage-io`는 NCM 미구성 상태를 sudo/rebind 없이 structured SKIP으로 기록
- host USB/NCM modules: v174에서 `usb-recovery` smoke PASS, `ncm-tcp-preflight`는 NCM 미구성 상태를 structured SKIP으로 기록
- host evidence bundle: v175에서 supervisor 공통 `README.md`/`bundle-index.json` finalizer 추가, bundle schema `a90-harness-v175` 검증 PASS
- host long-run supervisor: v176에서 `observe --duration-sec unlimited --max-cycles`와 `heartbeat.json` 추가, bounded unlimited smoke PASS
- host safety gate: v177에서 `list`/`plan`/`run --dry-run`과 `--allow-ncm`/`--allow-usb-rebind` gate 추가, 위험/환경 의존 모듈 기본 차단 확인
- screen menu: 자동 메뉴, 앱 폴더, CPU stress app, nonblocking `screenmenu`, serial `hide`/busy gate 확인
- USB map: ACM-only gadget `04e8:6861` / host `cdc_acm` 기준 문서화
- userland: toybox fallback 실행 확인; v124부터 SD runtime BusyBox는 manifest SHA-256 검증 전에는 preferred helper가 되지 않음
- remote shell: token-authenticated custom TCP shell `a90_rshell` over USB NCM `192.168.7.2:2326` 검증
- service manager: `service list/status/start/stop/enable/disable`로 autohud/tcpctl/adbd/rshell 공통 operator view 검증
- USB reattach: v48에서 ACM rebind 후 serial console 재연결 확인
- USB NCM: persistent composite, device `ncm0`, IPv4 ping, IPv6 link-local ping, host→device netcat 확인
- NCM ops: host interface 자동 탐지, ping, static TCP nettest 양방향 payload 검증 완료
- TCP control: NCM 위에서 token-authenticated `/bin/a90_tcpctl` ping/status/run/shutdown 검증 완료
- TCP wrapper: `tcpctl_host.py smoke`로 launch/client/stop 자동 검증 완료
- TCP soak: v160에서 `tcpctl_host.py soak` 3602.5초/360사이클, tcp/status/run/host ping failures 0 검증 완료
- physical USB reconnect: 실제 케이블 unplug/replug 후 ACM bridge, NCM ping, tcpctl 복구 확인
- serial noise: unsolicited `AT` modem probe line 무시 확인
- boot netservice: `/cache/native-init-netservice` opt-in flag 기반 NCM/tcpctl 부팅 자동 시작 검증 완료
- reconnect: v60 `netservice stop/start` software UDC 재열거 후 NCM/TCP 복구 확인
- HUD metrics: CPU/GPU 온도와 사용률 `%` 표시, CPU stress 검증 확인
- dev nodes: `/dev/null`/`/dev/zero` boot-time char device guard 확인
- app menu: APPS/MONITORING/TOOLS/LOGS/NETWORK/POWER 계층 메뉴, CPU stress, input monitor 확인
- boot splash: TEST 패턴 대신 `A90 NATIVE INIT` custom splash 표시 후 HUD 전환 확인
- splash layout: v65에서 긴 문구/footer 잘림 방지를 위해 안전 여백과 자동 축소 적용
- display test: v77에서 color/font/safe-area/layout preview 4페이지로 분리, `cutoutcal` 펀치홀 보정 추가
- SD workspace: `mountsd [status|ro|rw|off|init]`로 ext4 SD `/mnt/sdext/a90` 운영 검증
- boot storage: v79에서 SD boot health check 후 정상 SD는 main runtime storage, 실패 시 `/cache` fallback
- source layout: v80에서 PID1 source를 기능별 include module로 분리
- base modules: v81에서 `a90_config.h`와 `a90_util.c/h`를 실제 `.c/.h` API로 분리
- log/timeline modules: v82에서 `a90_log.c/h`와 `a90_timeline.c/h`를 실제 `.c/.h` API로 분리
- console module: v83에서 `a90_console.c/h`로 fd/attach/readline/cancel API 분리
- cmdproto module: v84에서 `a90_cmdproto.c/h`로 `cmdv1/cmdv1x` frame/decode API 분리
- run/service modules: v85에서 `a90_run.c/h`와 `a90_service.c/h`로 process/service lifecycle API 분리
- KMS/draw modules: v86에서 `a90_kms.c/h`와 `a90_draw.c/h`로 화면 저수준 API 분리
- input module: v87에서 `a90_input.c/h`로 물리 버튼/gesture API 분리와 실기 회귀 검증 완료
- HUD module: v88에서 `a90_hud.c/h`로 boot splash/status HUD/log tail 렌더러 분리와 실기 회귀 검증 완료
- menu module: v89에서 `a90_menu.c/h`로 menu model/state를 분리하고 `screenmenu`를 nonblocking background request로 전환
- metrics module: v90에서 `a90_metrics.c/h`로 배터리/CPU/GPU/MEM/전력 sysfs snapshot API 분리
- cpustress helper: v91에서 `/bin/a90_cpustress` static helper로 CPU stress worker를 PID1 밖으로 분리
- shell/controller modules: v92에서 `a90_shell.c/h`와 `a90_controller.c/h`로 shell metadata와 menu busy policy 분리
- storage module: v93에서 `a90_storage.c/h`로 boot storage state, SD probe, cache fallback, `storage`/`mountsd` API 분리
- selftest module: v94에서 `a90_selftest.c/h`로 boot-time non-destructive module smoke test와 `selftest` 명령 추가
- netservice/USB modules: v95에서 `a90_usb_gadget.c/h`와 `a90_netservice.c/h`로 USB configfs/UDC 및 NCM/tcpctl policy API 분리
- structure audit: v96에서 v95 모듈 경계 감사와 stale console klog marker 정리
- runtime module: v97에서 `a90_runtime.c/h`로 SD runtime root, cache fallback, runtime directory contract, `runtime` command 분리
- helper module: v98에서 `a90_helper.c/h`로 helper inventory, manifest path, preferred helper fallback, `helpers` command 분리
- userland module: v99에서 `a90_userland.c/h`로 BusyBox/toybox inventory, `userland`, `busybox`, `toybox` command 분리
- remote shell module: v100에서 `/bin/a90_rshell` custom TCP helper, token auth, `rshell_host.py` smoke 검증 완료
- service manager: v101에서 `a90_service.c/h` metadata/status API와 `service` command 검증 완료
- diagnostics: v102에서 `a90_diag.c/h`와 `diag_collect.py`로 read-only diagnostics/log bundle 검증 완료
- Wi-Fi inventory: v103에서 `a90_wifiinv.c/h`와 `wifi_inventory_collect.py`로 read-only WLAN/rfkill/firmware path 조사 완료
- Wi-Fi feasibility: v104에서 `a90_wififeas.c/h`와 `wififeas [summary|full|gate|paths]`로 read-only evidence 기반 bring-up gate 검증 완료
- Wi-Fi native bring-up research: V1165에서 `a90_android_execns_probe v217` late `pm-proxy` actionability gate를 실행해 `pm-proxy` 생존/PM connect 성공에도 `pm-service`의 `/dev/subsys_esoc0` open이 발생하지 않는 PM action-contract gap으로 분류
- soak RC: v105에서 `native_soak_validate.py` 10-cycle quick soak와 recovery-friendly baseline 검증 완료
- UI app split: v106 `a90_app_about.c/h`, v107 `a90_app_displaytest.c/h`, v108 `a90_app_inputmon.c/h` 분리와 실기 flash/quick soak 검증 완료
- structure audit 2: v109에서 post-v108 구조 감사와 next cleanup boundary 기록 완료
- app controller cleanup: v110에서 auto-menu IPC/state를 `a90_controller.c/h` API로 이동
- extended soak RC: v111에서 10-cycle host soak와 final service/selftest 확인 완료
- USB/NCM service soak: v112에서 opt-in NCM/tcpctl start, host ping/TCP control, ACM rollback 확인 완료
- runtime package layout: v113에서 package-friendly runtime paths와 helper manifest path contract 확인 완료
- helper deployment 2: v114에서 helper manifest/plan/deploy log visibility 확인 완료
- remote shell hardening: v115에서 `rshell audit`, token mode `0600`, invalid-token rejection, NCM smoke/rollback 확인 완료
- diagnostics bundle 2: v116에서 runtime/helper/service/net/rshell evidence와 host `diag_collect.py` device evidence 확장 완료
- PID1 slim roadmap baseline: v117에서 v117-v122 cycle guardrail과 next execution plan을 고정하고 실기 flash/quick soak 검증 완료
- shell metadata API: v118에서 `a90_shell.c/h` command stats/flag formatter와 `cmdmeta [verbose]` read-only inventory 추가
- menu route API: v119에서 `a90_menu_action_opens_app()`로 About/Changelog routing 중복 제거
- command group API: v120에서 command table group metadata와 `cmdgroups [verbose]` inventory 추가
- PID1 guard: v121에서 `a90_pid1_guard.c/h`와 `pid1guard [status|run|verbose]`로 boot/control invariant 점검 추가
- Wi-Fi refresh: v122에서 `wifiinv refresh`/`wififeas refresh`로 v103/v104 baseline 대비 read-only 재평가 완료
- security batch 1: v123에서 tcpctl auth/bind, ramdisk tcpctl helper, dangerous `service` gate, reconnect cleanup fail-closed 적용 완료
- security batch 2: v124에서 runtime helper SHA-256 preference, no-follow storage/log writes, mountsd SD identity gate, tcpctl install rollback 적용 완료
- security batch 3: host tooling에서 cmdv1 retry/framing, ADB shell path quoting, NCM interface pinning, serial bridge identity pinning 적용 완료
- security batch 4: v125에서 diagnostics/log owner-only permissions, private fallback log, HUD log tail opt-in 적용 완료
- security batch 5: host/rootfs tooling에서 legacy root SSH default credential 제거와 safe archive extraction 적용 완료
- security batch 6: v126에서 retained-source compatibility, v84 changelog route, v42 run stdin, input event validation 정리 완료
- security batch 7: v127에서 menu-active busy gate를 deny-by-default allowlist로 강화해 F023 종료
- menu subcommand policy: v128에서 F023 mitigation을 유지하면서 read-only subcommand만 menu-visible 상태에서 허용
- changelog paging: v129에서 long changelog viewport, shared changelog data, ABOUT page navigation 적용
- menu hold/back: v130에서 volume hold-repeat scroll과 VOL+DN physical back shortcut 적용
- menu hold timer: v131에서 EV_KEY repeat 없이 key-down 타이머 기반 연속 스크롤 적용, 실기 UX 정상 확인
- changelog cleanup: v132에서 ABOUT/changelog legacy per-version routes를 제거하고 shared changelog table 단일 경로로 정리
- changelog series: v133에서 ABOUT/changelog를 `0.9.x RECENT`, `0.8.x LEGACY` 같은 version series별 목록으로 분리
- network exposure guardrail: v134에서 `exposure [status|verbose|guard]`, `status`, `bootstatus`, `diag`로 USB/NCM/root-control 노출 경계를 read-only로 확인
- controller policy matrix: v135에서 `policycheck [status|run|verbose]`로 menu-visible/power-page command allow/block 정책을 자체 검증
- structure audit 3: v136에서 post-v135 module ownership, duplicate policy, include residue, PID1 growth hotspot 감사 완료
- validation matrix: v137에서 `native_integrated_validate.py`로 selftest/pid1guard/exposure/policy/service/network/UI gate 통합 검증 완료
- extended soak: v138에서 `native_rc_soak.py` RC soak harness 추가, 실기 flash 후 integrated/quick/RC soak 검증 완료
- auto-HUD controller cleanup: v139에서 `auto_hud_loop()` state/helper 경계를 정리하고 integrated/quick/RC soak 검증 완료
- CPU stress app module: v140에서 `a90_app_cpustress.c/h`로 screen CPU stress lifecycle/renderer를 분리하고 helper 포함 ramdisk로 실기 `cpustress 3 2` 검증 완료
- LOG/NETWORK app modules: v141에서 `a90_app_log.c/h`, `a90_app_network.c/h`로 summary renderer를 분리하고 실기 flash/integrated/quick soak 검증 완료
- cutout calibration app API: v142에서 `a90_app_displaytest.c/h`로 cutout state/feed/draw API를 분리하고 `displaytest safe`/`cutoutcal` 검증 완료
- input command module: v143에서 `a90_input_cmd.c/h`로 `waitkey`/`waitgesture`/`inputlayout` command handler를 분리하고 실기 flash/integrated/quick soak 검증 완료
- input monitor foreground app API: v144에서 `a90_app_inputmon.c/h`로 `inputmonitor` foreground command loop를 분리하고 q cancel/integrated/quick soak 검증 완료
- input cancel validation: v145에서 `native_input_cancel_validate.py`로 `waitkey`/`waitgesture`/`inputmonitor` q cancel 자동 검증을 추가하고 실기 PASS 확인
- long soak foundation: v146에서 `/bin/a90_longsoak` device recorder, `longsoak` shell/service control, host `native_long_soak.py` observation harness 검증 완료
- long soak status: v147에서 sample count/last event 요약을 `status`/`bootstatus`/host summary JSON에 연결
- long soak correlation: v148에서 host/device JSONL export와 correlation report PASS 확인
- long soak supervisor: v149에서 recorder health/stale detection을 `status`/`bootstatus`/`selftest`에 연결
- host disconnect classifier: v150에서 serial bridge/cmdv1/NCM ping/longsoak evidence를 분류하는 host report 추가
- long soak bundle: v151에서 host/device JSONL, correlation, disconnect, live status transcript를 한 디렉터리로 묶는 evidence bundle 추가
- power/thermal trend: v152에서 longsoak device JSONL 기반 battery/power/CPU/GPU/mem/load trend report 추가
- longsoak security: v153에서 device-owned bounded export, helper no-follow log writes, private host bundle output 적용
- kernel inventory: v154에서 `kernelinv [summary|full|paths]`와 host `kernel_inventory_collect.py`로 `/proc/config.gz`, filesystems, mounts, pstore, tracefs, watchdog, cgroup, thermal, power_supply, USB gadget 상태를 read-only 수집
- kernel diagnostics bundle: v155에서 host `kernel_diag_bundle.py`로 kernelinv/diag/longsoak/exposure/wifiinv/wififeas read-only evidence를 private bundle로 수집
- thermal/power sensor map: v156에서 `sensormap [summary|thermal|power|full|paths]`와 host `sensor_map_collect.py`로 thermal zones, cooling devices, power supplies를 read-only 수집
- pstore feasibility: v157에서 `pstore [summary|full|paths]`와 host `pstore_feas_collect.py`로 pstore/ramoops 상태를 read-only 수집
- watchdog feasibility: v158에서 `watchdoginv [summary|full|paths]`와 host `watchdog_feas_collect.py`로 watchdog 상태를 read-only 수집
- tracefs feasibility: v159에서 `tracefs [summary|full|paths]`와 host `tracefs_feas_collect.py`로 tracefs/ftrace 상태를 read-only 수집
- kernel config decoder: v197에서 host `kernel_config_decode.py`로 `/proc/config.gz`를 CONFIG 단위 capability matrix로 분류
- netfilter inventory: v198에서 host `netfilter_inventory.py`로 legacy iptables/conntrack/nftables 가능성을 read-only 판정
- cgroup/PSI inventory: v199에서 host `cgroup_psi_inventory.py`로 cgroup controller, PSI, mount 상태와 service isolation 가능성을 read-only 판정
- debug observability plan: v200에서 host `debug_observability_plan.py`로 tracefs/pstore/debugfs/usbmon opt-in 계획을 read-only 생성
- host evidence helper: v201에서 v197-v200 kernel capability tools의 private/no-follow evidence writer를 `a90harness.evidence`로 통합
- kernel capability summary: v202에서 host `kernel_capability_summary.py`로 config/netfilter/cgroup-PSI/tracefs-pstore/Wi-Fi gate를 한 화면에 통합
- Wi-Fi lifecycle research: v203-v228에서 Android/TWRP/native Wi-Fi evidence, vendor firmware path, ICNSS reprobe safety stop, ICNSS/CNSS lifecycle map, Android service replay model, ICNSS debug/recovery inventory, CNSS daemon dry-run model, native Android-env shim matrix, lifecycle-aware preflight gate v2, host vendor/system ELF library evidence, live vendor-root export, reboot-only recovery policy, Android-env shim dry-run artifacts, exposure/security gate v3, controlled CNSS start-only plan을 수집/구현했고 v228 decision은 `cnss-start-plan-ready`다. 다음은 active scan/connect가 아니라 v229 opt-in start-only runner다
- about app: `APPS / ABOUT`에서 version, changelog 목록/상세, credits 표시
- input layout: `inputlayout`, `waitgesture`, `screenmenu`/`blindmenu` gesture action 확인
- input monitor: `TOOLS / INPUT MONITOR`와 `inputmonitor [events]` raw/gesture trace 확인
- log tail panel: v125부터 `hudlog on` opt-in 상태에서만 HUD/menu 최근 native log 표시
- serial reattach log: v75에서 idle-timeout 성공 로그를 억제해 LOG TAIL noise 감소
- serial noise: v76에서 짧은 `A`/`T`/`ATAT` fragment를 unknown command 없이 무시
- menu gate: v128 기준 메뉴 표시 중 read-only status/query subcommand만 추가 허용하고 `run`/`writefile`/`mountfs`/`mknod*`/service mutation은 계속 차단
- shell protocol: `cmdv1`/`A90P1` framed one-shot result와 `a90ctl.py` host wrapper 검증
- shell protocol: v74 `cmdv1x` length-prefixed argv encoding verified for whitespace args
- changelog UI: v129부터 `ABOUT / CHANGELOG`는 viewport 범위 표시와 selected-row auto-scroll을 사용하고, detail/about 화면은 VOL page navigation을 지원; v132부터 shared changelog table 단일 경로, v133부터 version series 분류를 사용
- menu input UX: v131부터 긴 메뉴에서 커널 repeat 이벤트 없이 VOL hold timer scroll을 사용하고 VOL+DN 조합으로 뒤로가기/숨기기를 수행
- ADB: 보류. 현재 기준 제어 채널은 serial bridge


---

## README 이관: 완료된 Near-Term Roadmap (v40–v116)

아래는 README.md "Near-Term Roadmap"에 있던 완료 체크리스트를 그대로 옮긴 것이다.
v116까지 완료된 항목이며, 이후 활성 작업은 `docs/plans/NATIVE_INIT_NEXT_WORK_2026-04-25.md`와 CLAUDE.md를 기준으로 한다.

1. shell result/return code를 신뢰 가능하게 정리 — v40 완료
2. `/cache/native-init.log` 기반 boot/command 로그 추가 — v41 완료
3. blocking command 취소 정책 통일 — v42 완료
4. boot readiness timeline 자동 기록 — v43 완료
5. HUD에 boot progress/error 상태 표시 — v44 완료
6. recovery log preservation + `run` cancel helper — v45 완료
7. safe storage/partition map 문서화 — v46 완료
8. 버튼 기반 on-screen menu 초안 구현 — v47 완료
9. USB gadget/device/sysfs map 문서화 — 완료
10. Toybox/static userland build + device validation — 완료
11. USB ACM reattach + NCM probe — v48 완료
12. 상태 HUD/menu TUI 개선 — v52 실기 표시 확인
13. menu-active serial busy gate + flash auto-hide — v53 완료
14. USB NCM persistent link + IPv4/IPv6 ping + host→device netcat 검증 — 완료
15. NCM host setup helper + TCP nettest helper — 완료
16. NCM TCP control helper — 완료
17. TCP control host wrapper — 완료
18. NCM + TCP control 5분 soak — 완료
19. unsolicited `AT` serial noise filter — v59 완료
20. opt-in boot-time NCM/tcpctl netservice — v60 완료
21. netservice stop/start UDC reconnect recovery — v60 완료
22. HUD CPU/GPU usage percent 표시 — v61 완료
23. CPU stress usage gauge + `/dev/null`/`/dev/zero` guard — v62 완료
24. 계층형 앱 메뉴 + CPU stress screen app — v63 완료
25. TEST 부팅 화면을 custom boot splash로 교체 — v64 완료
26. boot splash 잘림 방지 safe layout — v65 완료
27. semantic version + ABOUT/changelog/credits app — v66 완료
28. compact ABOUT typography + per-version changelog detail — v67 완료
29. HUD log tail + expanded changelog history — v68 완료
30. physical-button input gesture layout — v69 완료
31. input monitor app + raw/gesture trace — v70 완료
32. HUD/menu live log tail panel — v71 완료
33. display test screen + framebuffer color fix — v72 완료
34. shell protocol v1 + host wrapper — v73 완료
35. cmdv1x argument encoding — v74 완료
36. idle serial reattach log quieting — v75 완료
37. AT fragment serial noise hardening — v76 완료
38. display test multi-page app + cutout calibration — v77 완료
39. ext4 SD workspace + `mountsd` storage manager — v78 완료
40. boot-time SD health check + `/cache` fallback — v79 완료
41. PID1 source layout split into include modules — v80 완료
42. Config/util true `.c/.h` base module extraction — v81 완료
43. Log/timeline true `.c/.h` API module extraction — v82 완료
44. Console true `.c/.h` API module extraction — v83 완료
45. Cmdproto true `.c/.h` API module extraction — v84 완료
46. Run/service lifecycle `.c/.h` API module extraction — v85 완료
47. KMS/draw true `.c/.h` API module extraction — v86 완료
48. Input true `.c/.h` API module extraction — v87 완료
49. HUD true `.c/.h` API module extraction — v88 완료
50. Menu control true `.c/.h` API module extraction + nonblocking `screenmenu` — v89 완료
51. Metrics true `.c/.h` API module extraction — v90 완료
52. CPU stress external helper process separation — v91 완료
53. Shell/controller metadata and busy policy API extraction — v92 완료
54. Storage state, SD probe, cache fallback API extraction — v93 완료
55. Boot selftest non-destructive module smoke test API — v94 완료
56. Netservice/USB gadget API extraction — v95 완료
57. Structure audit / refactor debt cleanup — v96 완료
58. SD runtime root promotion — v97 완료
59. Helper deployment / package manifest — v98 완료
60. BusyBox static userland evaluation — v99 완료
61. Custom token TCP remote shell over USB NCM — v100 완료
62. Minimal service manager command/view — v101 완료
63. Diagnostics/log bundle command and host collector — v102 완료
64. Wi-Fi read-only inventory — v103 완료
65. Wi-Fi enablement feasibility gate — v104 완료
66. Long-run soak/recovery RC — v105 완료
67. ABOUT/changelog UI app module extraction — v106 완료
68. Displaytest/cutoutcal UI app module extraction — v107 완료
69. Input monitor/layout UI app module extraction — v108 완료
70. Post-v108 structure audit and v110 cleanup boundary — v109 완료
71. App controller auto-menu IPC cleanup — v110 완료
72. Extended soak release-candidate baseline — v111 완료
73. USB/NCM service soak and rollback baseline — v112 완료
74. Runtime package layout and manifest path contract — v113 완료
75. Helper manifest and deploy plan visibility — v114 완료
76. Remote shell hardening audit and invalid-token smoke — v115 완료
77. Diagnostics bundle 2 evidence closure — v116 완료
