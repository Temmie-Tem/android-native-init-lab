# Native Init Next Work List (2026-04-25)

이 문서는 `A90 Linux init 0.8.1 (v70)` 기준 이후 작업을 정리한 실행 목록이다.

현재 단계는 넓은 의미의 리버싱도 포함하지만, 중심은 더 이상 Android 전체를
분해하는 것이 아니다. Stock Android kernel과 Samsung vendor driver 위에서
우리의 작은 native userspace, shell, display HUD, input/menu, log/runtime 계층을
만드는 단계다.

따라서 후속 작업은 아래 원칙으로 진행한다.

- 필요한 하드웨어/커널 경로만 역추적한다.
- 셸은 실험 도구이자 운영 콘솔로 안정화한다.
- 화면 HUD는 부팅 상태를 보이게 만드는 최소 UI로 발전시킨다.
- 저장소와 로그는 복구 가능한 영역부터 사용한다.
- ADB는 보류하고 USB ACM serial을 기준 제어 채널로 유지한다.

## 버전 표기 규칙

- numeric `MAJOR.MINOR.PATCH`는 native init / boot image version이다.
- `v###`는 project execution cycle이며 host tooling, 계획, 보고서, 검증 gate에도 사용한다.
- `v###`가 항상 새 boot image나 device flash를 뜻하지 않는다.
- 현재 예: native build `A90 Linux init 0.9.61`, device build tag `v319`, active execution cycle `v319`, device flash 완료.
- 상세 규칙: `docs/operations/VERSIONING_POLICY.md`

## 현재 Wi-Fi Gate

- 최신 기준: V1263 HOST-ONLY PASS —
  `v1263-kernel-owned-soft-reset-line-request-rejected`.
  V1239는 Android/V1238 증거를 비교해 blocker를 `pm-service`
  `/dev/subsys_esoc0` / `mdm_subsys_powerup` 이후로 낮췄고, V1240은
  SDX50M/eSoC response surface와 GPIO142 `mdm status` IRQ count `0`을
  확인했다. V1241은 임시 debugfs mount/cleanup과 GPIO135/GPIO142 pinctrl
  ownership 관찰을 검증했다. V1242는 helper `a90_android_execns_probe v258`
  response sampler로 bounded late `per_proxy` trigger 중 `pm-service`가
  `/dev/subsys_esoc0`에 도달함을 확인했지만, 14개 샘플 전체에서 GPIO142 IRQ
  count `0`, PCI device count `0`, MHI bus count `0`, MHI pipe absent,
  `wlan0` absent, `mdm3=OFFLINING`이 유지됐다. V1243는 helper
  `a90_android_execns_probe v259`로 sampler를 보강해 PM8150L soft-reset GPIO와
  PCIe GDSC regulator source를 분리했다. 결과는 PMIC soft-reset pinctrl line
  `pin 7 (gpio9): (MUX UNCLAIMED)` 유지, PCIe GDSC lines `0mV` 유지, GPIO142
  IRQ count `0`, PCI/MHI/`wlan0` absent이다. V1247은 direct GPIO/debugfs/GDSC
  write와 blind `/dev/subsys_esoc0` retry를 reject하고 fail-closed PMIC
  preflight helper를 선택했다. V1248은 helper `a90_android_execns_probe v260`을
  빌드했고, V1249는 `/cache/bin/a90_android_execns_probe`에 배포했다. V1250은
  global namespace에서 `debugfs_pinctrl_present=0`, `debugfs_regulator_present=0`라
  `read-only-incomplete`로 분류됐고, V1251은 V1241 패턴처럼 debugfs를 임시
  mount하여 같은 helper v260 preflight를 재실행했다. V1251 결과는
  `read-only-pass`: `debugfs_pinctrl_present=1`, `debugfs_regulator_present=1`,
  PM8150L soft-reset GPIO line `pin 7 (gpio9): (MUX UNCLAIMED)`, PCIe GDSC
  lines `0mV`, `mdm3=OFFLINING`, GPIO142 IRQ count `0`, `read_contract_ready=1`,
  `native_reproduction_candidate=1`, postflight selftest `fail=0`이다. V1252는
  host-only로 해당 증거를 검증하고 helper v261 source/build-only를 선택했다.
  V1253은 `a90_android_execns_probe v261`을 빌드했고 새 mode
  `wifi-companion-pmic-power-surface-write-gate-preflight`를 추가했다. 이 mode는
  V1251 read contract를 재검증하고, `/dev/gpiochip*`의 chipinfo와 debugfs gpio
  range를 읽어 PM8150L GPIO9 global line `1270` / offset `7` mapping을
  fail-closed로 분류한다. V1254는 serial fallback으로 v261을
  `/cache/bin/a90_android_execns_probe`에 배포했고 remote SHA가
  `37947e378f4743a6661a03ee36dfc95ddf5ce9cd79acec0862a28a4564573a7c`로 일치했다.
  V1255는 PMIC debugfs에서 `gpiochip2` range `1263-1273`, PMIC GPIO9 global line
  `1270`, offset `7`, identity/offset match true를 확인했지만 native
  `/dev/gpiochip*`가 없어 chardev mapping은 incomplete였다. V1256은 read-only로
  devnode feasibility를 분류해 `/proc/devices` `254 gpiochip`,
  `/sys/bus/gpio/devices/gpiochip2/dev=254:2`, `/sys/class/gpio/gpiochip1263`
  label `c440000.qcom,spmi:qcom,pm8150l@4:pinctrl@c000`, `ngpio=11`을 확인했다.
  V1257은 helper `a90_android_execns_probe v262` source/build-only로
  `wifi-companion-pmic-gpiochip-devnode-open-preflight` mode와
  `--allow-pmic-gpiochip-devnode-open-preflight` gate를 추가했다. 이 helper는
  V1256 sysfs contract(`/sys/bus/gpio/devices/gpiochip2/dev=254:2`,
  `gpiochip1263` base `1263`, `ngpio=11`, PM8150L label)를 fail-closed로 확인한
  뒤, 별도 live gate에서만 임시 `/dev/gpiochip2` char node를 만들고 read-only
  `GPIO_GET_CHIPINFO_IOCTL`을 실행하도록 준비됐다. V1257은 build-only라 deploy,
  device command, live mknod/open을 실행하지 않았다. V1258은 serial fallback으로
  v262를 `/cache/bin/a90_android_execns_probe`에 배포했고 remote SHA가
  `17773e5bcdec090c061a962833d27a783439e1b718c96b47a504f625d79cc36d`로 일치했다.
  postflight selftest는 `fail=0`이고 service-manager/Wi-Fi link surface는 clean이다.
  V1259는 bounded live devnode-open proof를 실행했다. 결과는 sysfs contract match,
  temp `mknod` 성공, read-only open 성공, `GPIO_GET_CHIPINFO_IOCTL` 성공
  (`chip_name=gpiochip2`, `chip_lines=11`), cleanup unlink 성공, postflight selftest
  `fail=0`, forbidden zero-action markers all-ok다. V1260은 helper
  `a90_android_execns_probe v263` source/build-only로
  `wifi-companion-pmic-gpiochip-line-info-preflight` mode와
  `--allow-pmic-gpiochip-line-info-preflight` gate를 추가했다. 이 mode는 PMIC GPIO9
  offset `7`에 대해 read-only `GPIO_GET_LINEINFO_IOCTL`만 수행하고 line flags,
  name, consumer를 출력하도록 준비됐다. V1261은 serial fallback으로 v263을 배포했고
  remote SHA가 `32ac877a165a266d96589387d9974dfea38c81d0adb368bf17ff15de77a9f9fb`로
  일치했다. V1262는 bounded live line-info proof를 실행했고 offset `7` line flags
  `0x1`, `GPIOLINE_FLAG_KERNEL=1`, consumer `AP2MDM_SOFT_RESET`를 확인했다. 따라서
  direct userspace PMIC GPIO9 line request/hold는 다음 안전 경로가 아니다. V1263은
  V1262/V1239/V1242/V1243 증거를 host-only로 분류해 direct userspace PMIC GPIO9
  line request/hold를 reject했다. V1264는 host-only로 read-only ext-mdm/AP2MDM
  observer contract를 고정했다. 현재 helper gap은 V1243 sampler가 PMIC soft-reset
  pinctrl text는 보지만, 같은 PM-service `/dev/subsys_esoc0` response window에서
  gpiochip line-info flags/name/consumer를 보지 않는 점이다. V1265는
  source/build-only helper `a90_android_execns_probe v264`로 late `per_proxy`
  response sampler에 read-only PMIC GPIO9 `GPIO_GET_LINEINFO_IOCTL` snapshots를
  before/during/after phase에 추가했고, static aarch64 build와 marker 검증을
  통과했다. V1266은 serial fallback으로 helper v264를 `/cache/bin/a90_android_execns_probe`에
  배포했고 SHA256 `a06ff29245023c265c69e58e2ae3f32a4facbc291bcb63a4450f39efd9515dc5`
  직접 검증과 post-deploy selftest `fail=0`을 통과했다. V1267 bounded live
  ext-mdm/AP2MDM observer는 같은 PM-service `/dev/subsys_esoc0` response window에서
  14개 샘플 모두 PMIC GPIO9 line-info flags `0x3`(`GPIOLINE_FLAG_KERNEL` +
  `GPIOLINE_FLAG_IS_OUT`)와 consumer `AP2MDM_SOFT_RESET`를 확인했다. 그러나
  GPIO142 IRQ count `0`, `mdm3=OFFLINING`, PCI device count `0`, MHI bus count `0`,
  MHI pipe absent, `wlan0` absent가 유지됐다. cleanup은 reboot-required로
  분류됐고 reboot 후 version `0.9.68 (v724)`, selftest `fail=0`, transient
  debugfs/vendor/system mount cleanup을 확인했다. V1268은 host-only로 다음
  read-only observer 대상을 분류했고, V1269 source/build-only helper v265를
  선택했다. V1269는 같은 PM-service window에서 PMIC GPIO9 value(debugfs gpio 가능 시),
  PMIC GPIO9 pinconf, TLMM GPIO135/142 value/pinconf, PCIe GDSC/regulator state를
  추가로 샘플링하도록 helper v265를 빌드했다. build SHA256은
  `97ffa91a1aa7b8f4ab2c3a74716ae5664c703e98fe19a322351b1277fbd282b2`다. V1270은
  serial fallback으로 helper v265를 배포했고 remote SHA 직접 검증과 post-deploy
  selftest `fail=0`을 통과했다. V1271 bounded value/power observer는 같은
  PM-service `/dev/subsys_esoc0` response window에서 14개 샘플 모두 PMIC GPIO9
  line-info flags `0x3`(`GPIOLINE_FLAG_KERNEL` + `GPIOLINE_FLAG_IS_OUT`)와 consumer
  `AP2MDM_SOFT_RESET`를 유지함을 재확인했다. `debugfs` GPIO/pinctrl/regulator
  surface는 읽혔고 PMIC GPIO9/TLMM GPIO135/GPIO142 pinctrl headers와 PCIe GDSC
  lines는 확인됐지만, exact debugfs-gpio value lines for global GPIO1270 / TLMM
  GPIO135 / TLMM GPIO142는 발견되지 않았다. GPIO142 IRQ count `0`, `mdm3=OFFLINING`,
  PCI device count `0`, MHI bus count `0`, MHI pipe absent, `wlan0` absent가 유지됐다.
  cleanup은 reboot-required로 분류됐고 reboot 후 version `0.9.68 (v724)`,
  selftest `fail=0`, transient debugfs/vendor/system mount cleanup을 확인했다. 다음
  V1272는 host-only로 broader read-only debugfs GPIO/pinconf block sampler 범위를
  확정했다. V1272 decision은 `v1272-ap2mdm-block-sampler-selected`이고, V1273은
  source/build-only helper v266으로 PM8150L GPIO9/global GPIO1270, TLMM GPIO135/142,
  PCIe RC1/GDSC 주변 block capture를 기존 late PM-service response sampler에 추가한다.
  V1273은 static aarch64 helper v266 build를 통과했고 SHA256은
  `3bf4105d685f023ccdeb75ae28d7d104ca005fc9f70870dc6f402a9ea4038ed4`다. V1274는
  serial fallback으로 helper v266을 `/cache/bin/a90_android_execns_probe`에 배포했고,
  remote SHA 직접 검증과 post-deploy selftest `fail=0`을 통과했다. V1275 bounded
  block sampler는 같은 PM-service `/dev/subsys_esoc0` response window에서 PMIC
  GPIO1270 debugfs block을 14개 샘플 모두 캡처했고, PMIC GPIO9 line은
  `out ... high ...`로 보였다. 하지만 GPIO142 IRQ count `0`, `mdm3=OFFLINING`,
  PCI/MHI/MHI-pipe/`wlan0` absent, PCIe GDSC `0mV`는 유지됐다. cleanup reboot 후
  version `0.9.68 (v724)`, selftest `fail=0`, transient mount cleanup도 확인했다.
  V1276은 PMIC GPIO9 polarity/value를 Android/reference 기준으로 host-only 분류했고,
  native PMIC GPIO9이 Android와 같은 `out/high` 상태임을 확인했다. 따라서 PMIC GPIO9
  write/hold와 direct eSoC ioctl retry는 계속 reject한다. 다음 V1277은 source/build-only
  helper v267로 TLMM GPIO135/GPIO142 range-slice, AP2MDM/MDM2AP pinmux/pinconf,
  PCIe RC1/GDSC read-only snapshots를 추가했다. V1277 결과 helper
  `a90_android_execns_probe v267`는 정적 aarch64로 빌드됐고, sha256은
  `eccd9ca475927c2a37551304fedcc6740d19aeb048ebd137f966a18c269f0337`다. 다음 gate는
  V1278 deploy-only, 이후 V1279 bounded live TLMM range sampler다. V1278은 serial
  fallback으로 helper v267을 `/cache/bin/a90_android_execns_probe`에 배포했고, remote
  SHA와 post-deploy selftest `fail=0`을 확인했다. V1279 live sampler는 TLMM gpiochip0
  range `0-174`와 GPIO135/GPIO142 pinmux ownership이 보임을 확인했지만, exact
  GPIO135/GPIO142 debugfs value line은 absent이고 GPIO142 IRQ/PCI/MHI/MHI-pipe/`wlan0`
  도 모두 absent로 유지됐다. post-run selftest는 `fail=0`이다. 다음 V1280은 host-only로
  V1279 native evidence와 기존 Android GPIO/PCIe positive evidence를 비교해 PCIe/GDSC
  enablement, AP2MDM/MDM2AP transition timing, Android-side early sampler 중 어떤
  게이트가 최단 경로인지 분류한다. V1280은 host-only로 이 비교를 끝냈고,
  line-level GPIO 값을 다음 hard gate에서 제외했다. 다음 V1281은 source/build-only로
  기존 bounded PM-service response path에 PCIe RC1/GDSC/regulator, MHI, SDX50M/ext-mdm
  dmesg marker를 더 촘촘히 기록하는 read-only sampler 지원을 추가한다. V1281은
  helper v268 static aarch64 build를 통과했고, sha256은
  `e86db44aad14e54572d88d77c1ea2019ea28b1f91c01f7a9af9e6eabc690a3ba`다. 다음 gate는
  V1282 deploy-only, 이후 V1283 bounded live PCIe/GDSC/kmsg response sampler다. V1282는
  serial fallback으로 helper v268을 `/cache/bin/a90_android_execns_probe`에 배포했고,
  remote SHA와 post-deploy selftest `fail=0`을 확인했다. 따라서 다음은 V1283 live
  sampler다. V1283은 PM-service eSoC trigger와 기존 GPIO/PCI/MHI silence를 재확인했지만,
  helper kmsg collector는 `/dev/kmsg` absent(`errno=2`)로 실패했다. 별도 native shell
  확인에서 `/proc/kmsg`는 존재하고 `busybox dmesg`는 동작한다. V1284는
  source/build-only로 `/dev/kmsg` 우선, read-only `syslog(SYSLOG_ACTION_READ_ALL)`/
  klogctl fallback, `kmsg_source` summary를 추가했고 helper v269 static aarch64
  build를 통과했다. sha256은
  `dbb1f67652913ffe94b1f083a082d8f221820040b9f28e08b226eb1e0a50fc83`다. 다음 gate는
  V1285 deploy-only, 이후 V1286 bounded live PCIe/GDSC/klogctl response sampler다.
  V1285는 serial fallback으로 helper v269을 `/cache/bin/a90_android_execns_probe`에
  배포했고 remote SHA와 post-deploy selftest `fail=0`을 확인했다. V1286은
  `syslog-read-all` klog fallback을 실제 live에서 통과시켰다. 그러나 PM-service가
  `/dev/subsys_esoc0`까지 도달해도 GPIO142 IRQ는 `0`, PCI/MHI/MHI-pipe/`wlan0`는
  absent, PCIe/MHI/WLFW kmsg counts는 `0`, `pcie_1_gdsc`/`pcie_0_gdsc`는 `0mV`로
  유지된다. post-reboot selftest는 `fail=0`이다. 다음 V1287은 host-only로 V1286과
  Android positive evidence를 비교해 SDX50M power/GPIO prerequisite를 분류한다. V1287은
  klogctl collector가 유효함을 확인하고 PM8150L gpio9 shape를 최단 blocker에서 내렸다:
  native gpio9은 Android의 `out/high` PMIC shape와 이미 일치하지만 PCIe GDSC는 `0mV`,
  GPIO142/PCIe/MHI/WLFW/SDX50M response는 absent다. 다음 V1288은 source/build-only로
  untruncated GPIO135/GPIO142, PMIC9, PCIe GDSC delta를 기록하는 no-write observer를
  추가한다. V1288은 helper v270 static aarch64 build를 통과했고, sha256은
  `f1748fdc9c64a748c3270cd02a2b9bb796065b79632849e7384c2f37910f6e88`다. 다음 gate는
  V1289 deploy-only, 이후 V1290 bounded no-write TLMM/PCIe response sampler다. V1289는
  serial fallback으로 helper v270을 배포했고 remote SHA와 post-deploy selftest
  `fail=0`을 확인했다. V1290은 exact GPIO135/GPIO142 target scan을 live에서 통과했다:
  native GPIO135=`out 0 16mA no pull`, GPIO142=`in 0 8mA no pull`로 Android-positive
  static evidence와 일치한다. 그러나 GPIO142 IRQ, PCIe/MHI/WLFW/SDX50M kmsg, MHI pipe,
  `wlan0`는 여전히 absent다. V1291은 host-only로 static GPIO shape를 blocker에서
  제외했다. V1292는 dynamic PCIe/GDSC/eSoC sequencing을 host/source로 분류했고,
  Android-positive PCIe RC1이 `subsys_esoc0_get` 후 `519 ms`에 나타나는 반면 V1290
  sampler cadence는 `1000 ms`임을 확인했다. 다음 V1293은 source/build-only로
  `append_pm_esoc_response_sample()`를 재사용하는 opt-in dense sampler를 추가한다:
  `50 ms` 간격, `40` samples, 첫 `2s` window. V1293은 helper `v271` source/build를
  통과했고 sha256은 `335b875516e76419933f2e0ab6e21cd7ee4d1d217b32f378f1925adc30010a24`다.
  V1294는 helper `v271`을 serial fallback으로 `/cache/bin/a90_android_execns_probe`에
  배포했고 remote sha/marker/usage를 확인했다. V1295는 bounded dense no-write live
  sampler를 실행해 dense metadata(`50 ms`, intended `40` samples)가 active였음을 확인했지만,
  parsed sample은 `14`개에서 멈췄고 GPIO142/PCIe/MHI/WLFW/SDX50M kmsg, MHI pipe,
  `wlan0`는 여전히 absent였다. postflight native health는 `pass=11 warn=1 fail=0`이다.
  V1296은 host-only로 V1295 dense-window shortfall이 runtime stop이 아니라 helper stdout
  `1048576` byte cap truncation임을 확인했다: truncation은 `late_per_proxy_poll_13` 중
  발생했고 `response_sampler.end`는 absent다. V1297은 source/build-only로 helper `v272`
  compact dense sampler를 추가했고 sha256은
  `1344b4ac101aa0cde56a46f1274b2d01f25d11b424158d822bff71234a1e7885`다.
  새 opt-in flag는 `--pm-observer-late-per-proxy-compact-response-sampler`이며,
  `late-per-proxy-dense-compact-pinctrl-irq-pcie` 모드에서 verbose fd/source/range/kmsg
  블록을 생략하고 no-write 핵심 카운터만 남겨 동일 live path의 full 40-sample 관측을
  가능하게 한다. V1298은 helper `v272`를 `/cache/bin/a90_android_execns_probe`에
  serial fallback으로 배포했고 remote sha/marker/compact flag와 selftest `fail=0`을
  확인했다. V1299는 bounded compact dense live sampler를 실행했고 full dense window를
  확보했다: mode `late-per-proxy-dense-compact-pinctrl-irq-pcie`, sample count `42`,
  `response_sampler.end=1`, helper stdout `truncated=0 bytes=778235`. GPIO142/PCIe/MHI/WLFW/
  `ks`/`wlan0`는 여전히 absent이고 `mdm3=OFFLINING`이다. V1300은 host-only로 V1295/V1299
  transcript를 비교했고 V1299의 `/dev/subsys_esoc0` 미재현 manifest 해석을 false
  negative로 정정했다: transcript에는 `path.value=/dev/subsys_esoc0` 2회와
  `wchan=mdm_subsys_powerup` 13회가 남아 있다. 원인은 compact mode가 repeated
  syscall/kmsg probe를 제거했고, blocked open은 visible fd를 만들지 않아 fd-only
  classifier가 실패한 것이다. V1301은 source/build-only로 helper `v273` compact
  `powerup_marker`를 추가했고 PASS했다. 새 marker는 per-sample `pm-service`
  process/thread count, `mdm_subsys_powerup` thread count, inferred `/dev/subsys_esoc0`
  reachability, first blocked thread metadata, and best-effort syscall path capture를
  기록한다. Built helper sha256은
  `dd1d15a5ef01189526720814c50b007f6dc9a0f25e9239caf0e9da34c65b6b46`이다. V1302는
  helper `v273`을 `/cache/bin/a90_android_execns_probe`에 배포했고 PASS했다. NCM이
  inactive여서 serial fallback을 사용했으며 chunk size `1800`, chunks `1010`,
  encoded bytes `1817918`, max cmdv1 line `3788`/safe `3968`이다. Post-deploy sha와
  helper marker가 `v273`으로 확인됐고 selftest는 `fail=0`이다. V1303은 bounded
  compact dense live rerun을 실행했고 `powerup_marker`가 42/42 phases를 덮었다.
  `pm-service`가 `/dev/subsys_esoc0`를 `openat`하고 `mdm_subsys_powerup`에 블록됨이
  확인됐지만 `max_mdm_status_count_total=0`, `max_mhi_bus_count=0`, `mhi_pipe_seen=false`,
  `wlan0_seen=false`다. GPIO snapshot은 `gpio135 : out 0 16mA no pull`,
  `gpio142 : in  0 8mA no pull`이고 lineinfo는 AP2MDM consumer/kernel-owned를
  확인했다. V1304는 Android-positive 증거와 V1303을 host-only로 비교했고
  `v1304-ap2mdm-assertion-visibility-gap-classified`로 PASS했다. ext-sdx50m contract는
  AP2MDM GPIO135 high 이후 MDM2AP/PCIe progress를 기대하지만, V1303 powerup window의
  모든 phase에서 GPIO135/GPIO142가 low였고 MDM status/MHI/WLFW/`wlan0`는 absent였다.
  단 Android post-boot snapshot도 low GPIO를 보일 수 있으므로 root cause 단정이 아니라
  assertion/visibility boundary로 취급한다. V1305는 V1303 transcript의 monotonic
  timeline을 host-only로 재분석했고 `v1305-ap2mdm-low-through-extended-powerup-window`로
  PASS했다. `mdm_subsys_powerup` 관측창은 `5013ms`였고 `42` powerup samples 전체에서
  GPIO135는 `out 0`, GPIO142는 `in 0`으로 유지됐다. MDM status/MHI/`ks`/`wlan0`도
  absent라서 단순 sampler-cadence blind spot 가능성은 낮다. 다음 V1306은 visible
  AP2MDM assertion이 안 나오는 lower branch를 분류한다: PM8150L soft-reset pinctrl,
  PCIe GDSC/runtime power prerequisite, 또는 proprietary `mdm_subsys_powerup` 내부
  branch-before-`mdm_do_first_power_on`. V1306은 V1305 native lower-window evidence와
  V1244 Android-positive PMIC/PCIe reference를 host-only로 비교했고
  `v1306-pmic-gdsc-prereq-gap-classified`로 PASS했다. Native window에서는 PM8150L
  soft-reset이 `MUX UNCLAIMED`, PCIe0/PCIe1 GDSC가 `0mV`, AP2MDM/MDM2AP low,
  MDM status/MHI/WLFW/`ks`/`wlan0` absent인 반면 Android-positive evidence에는 PMIC
  GPIO9 configured와 PCIe RC1 progress가 있다. 다음 V1307은 focused no-write
  PMIC/GDSC transition sampler support 또는 exact safe init prerequisite 분류다.
  V1307은 helper `v274` source/build-only support를 추가했고
  `v1307-pmic-gdsc-transition-sampler-build-pass`로 PASS했다. 새 flag는
  `--pm-observer-late-per-proxy-pmic-gdsc-transition-sampler`, mode는
  `late-per-proxy-focused-pmic-gdsc-transition`, intended cadence는 `80` samples at
  `50ms`다. 빌드된 static aarch64 helper sha256은
  `eb96072631ca38c3296f5da1756a93765e198e8fdd4dc010d087bc4b3b5fc180`이다. V1308은
  helper `v274` deploy-only로 PASS했고 remote `/cache/bin/a90_android_execns_probe`
  sha256도 동일했다. NCM은 inactive라 serial fallback으로 배포했으며 daemon start나
  Wi-Fi bring-up은 없었다. V1309는 bounded no-write PMIC/GDSC transition sampler
  live로 PASS했다. Helper stdout이 기존 `1MiB` cap에 닿아 full end marker는
  없었지만 `76` focused samples에서 `/dev/subsys_esoc0` → `mdm_subsys_powerup`
  경계와 PMIC/GDSC no-transition을 확인했다. 다음 V1310은 exact safe lower
  prerequisite host-only 분류 또는 stdout-reduced sampler support다. V1310은
  host-only classifier로 PASS했고 static PMIC GPIO9/TLMM GPIO135/GPIO142 shape를
  닫았다. Active blocker는 `mdm_subsys_powerup` 이후 dynamic PCIe/GDSC/eSoC lower
  power sequencing이다. 다음 V1311은 stdout-reduced full-window lower-sequence
  sampler support가 우선이다. V1311은 helper `v275` source/build-only support를
  추가했고 `v1311-lower-sequence-summary-sampler-build-pass`로 PASS했다. 새 flag는
  `--pm-observer-late-per-proxy-lower-sequence-summary-sampler`, mode는
  `late-per-proxy-lower-sequence-summary`, output contract는 aggregate
  `response_summary.*` keys다. 빌드된 static aarch64 helper sha256은
  `66e52e7507dd07bcb4071afd04bc60e51d1c6bb7b9cb7363205f1eb4f44d4677`이다. 다음
  V1312는 helper `v275` deploy-only, V1313은 bounded lower-sequence summary sampler
  live다. V1312는 helper `v275` deploy-only로 PASS했고 remote
  `/cache/bin/a90_android_execns_probe` sha256도 동일했다. NCM은 inactive라 serial
  fallback으로 배포했으며 daemon start나 Wi-Fi bring-up은 없었다. V1313은 bounded
  lower-sequence summary sampler live로 PASS했다. Helper stdout truncation 없이
  `81` samples와 `response_summary.end=1`을 확보했고, `mdm_subsys_powerup`은 보이나
  PCIe GDSC/MHI/`ks`/`wlan0` transition은 없었다. V1314는 host-only classifier로
  PASS했고 `v1314-provider-internal-first-power-on-trace-gate-selected`를 냈다. 직접
  PMIC/GPIO/GDSC/eSoC mutation은 계속 배제하고, 다음 안전 prerequisite는 tracefs static
  events로 provider-internal first-power-on event visibility를 증명하는 것이다. 다음
  V1315는 regulator/gpio/irq/clk/power/msm_pil_event availability/format preflight로
  PASS했다. `available_events=1250`, target formats는 regulator `4/4`, gpio `2/2`,
  irq `2/2`, clk `4/4`, power `3/3`, `msm_pil_event` `3/3`이고 tracefs cleanup과 post
  selftest도 통과했다. V1316은 같은 late `per_proxy` PM-service path 주변에 bounded
  tracefs lower-event collector를 붙여 PASS했다. `pm-service`는 `/dev/subsys_esoc0` /
  `mdm_subsys_powerup`에 도달했고, tracefs lower events는 total `81174`, critical
  `3936`, noise `77238`을 기록했다. V1317은 captured trace lines를 host-only로 분류해
  PASS했다. 저장된 `260` lines 중 critical sample은 `10`개였고 SDX50M/PCIe/MHI/WLAN/CNSS
  target keyword나 target GPIO `135`/`142`/`1270`은 없었다. Broad IRQ/clock noise가
  line budget을 대부분 소비했으므로 다음 V1318은 IRQ/clock을 제외한 critical-only
  collector로 더 많은 regulator/gpio/power/PIL line을 보존한다. V1318은 bounded
  critical-only collector live로 PASS했다. `3920` critical events와 `2000` preserved
  lines를 확보했고, `fw=esoc0` PIL notification, GPIO `1270` PMIC soft-reset toggle,
  GPIO `135` AP2MDM high가 보였다. 반면 GPIO `142`는 `0` lines였고 GPIO135 high 이후
  약 `49.28s` sample이 이어졌으므로 다음 V1319는 GPIO135 assertion 이후 GPIO142/PCIe
  response absence를 명시 blocker로 분류한다. V1319는 host-only로 PASS했고,
  V1304의 AP2MDM assertion/visibility gap을 supersede했다. Native는 GPIO135 high까지
  도달하지만 GPIO142/PCIe/MHI/WLFW response가 없고, Android-positive reference에는
  GPIO142 IRQ `1`, PCIe RC1 `18` lines, Android `ks`/MHI pipe, WLFW/BDF/`wlan0`가 있다.
  다음 V1320은 Android `mdm_helper`/`ks`/MHI image-transfer response contract를
  post-GPIO135 prerequisite로 분류한다. V1320은 host-only로 PASS했고, native의
  post-GPIO135 response gap이 Android `mdm_helper`/`ks`/MHI image-link contract와
  직접 연결된다고 결론냈다. Native current actor surface는 `mdm_helper`와 PM-service
  eSoC trigger visibility는 있지만 `ks_count_window=0`, MHI pipe absent, GPIO142/PCIe/MHI/WLFW
  absent이고, Android reference는 `mdm_helper` FD, `ks` FD, `/dev/mhi_0305_01.01.00_pipe_10`,
  GPIO142 IRQ, PCIe RC1, WLFW, `wlan0`를 모두 가진다. 다음 V1321은 direct
  GPIO/PMIC/GDSC/eSoC mutation 전에 Android `mdm_helper`/`ks`/MHI image-link contract를
  observe 또는 reproduce하는 fail-closed source/build gate로 제한한다. V1321은 host-only
  reconciliation으로 PASS했고, V1236-V1239가 이미 그 image-link branch를 covered한다고
  정리했다. V1236은 Android `ks`/MHI가 `per_proxy -> pm-service Binder -> /dev/subsys_esoc0`
  경로와 상관된다고 분류했고, V1238은 native late `per_proxy`가 `pm-service` /
  `mdm_subsys_powerup`에 도달함을 증명했으며, V1239는 남은 gap이 그 이후
  GPIO142/PCIe/MHI/WLFW/`wlan0` response 전이라고 분류했다. 따라서 다음 V1322는
  image-link 재시도가 아니라 SDX50M response input classifier로 잡는다: read-only
  PCIe RC1, GPIO142 IRQ/state, regulator/pinctrl/GDSC, MHI surface, cleanup-safe reboot
  boundary를 분류한다. V1322는 host-only로 PASS했고, SDX50M metadata/IRQ/PCIe/regulator
  surfaces가 보이며 static PMIC/TLMM shape와 image-link/PM actor delivery는 더 이상
  shortest blocker가 아니라고 정리했다. V1318 first-power-on trace는 GPIO1270 soft-reset,
  GPIO135 high, regulator/GPIO/PIL events를 보였지만 GPIO142/PCIe/MHI/WLFW는 끝까지
  없었다. 다음 V1323은 proprietary provider wait cause를 분류한다:
  `mdm_subsys_powerup`, GPIO142/MDM2AP, `err_ready`를 host/source first로 분석하고,
  필요할 때만 bounded read-only 또는 reboot-bounded live gate로 확장한다.
  GPIO line request, PMIC GPIO9 hold, PMIC write, direct eSoC ioctl, new
  PM/CNSS/HAL start, scan/connect, credentials, DHCP/routes, external ping, flash,
  boot image write, partition write는 별도 gate 전까지 계속 블록한다.
- V1198 배경: V1197 root cause 분석 완료: 세 가지 레이어 문제가 중첩됨.
  V1197 root cause 분석 완료: 세 가지 레이어 문제가 중첩됨.
  (1) V1194/V1195/V1196: SAMPLE_COUNT!=0 → serial 홍수 (pm_proxy/pm-service /proc/maps 덤프
      매 0.25s) → 480s timeout 안에 wait "$child_pid" 미도달 → child_summary 미실행.
  (2) V1197 attempt 3 (--thread-sample-count 0): 샘플링 없앴으나 PCIe enumerate가
      /sys/devices/platform/soc/1c08000.qcom,pcie/debug/enumerate에 write "1\n" →
      PCIe RC1 enumerate trigger → 커널 패닉 / full device reboot 유발.
      wait "$child_pid" 블록 중 기기 재부팅 → TCP FIN → read_until이 A90P1 END 없이
      EOF 반환 → parse_protocol_output RuntimeError (device output 332줄 포함) →
      observer 파일에 traceback+device output 포함되나 child_summary 없음.
  (3) CHILD_LOG(/cache/.../pm-mdm-esoc-power-on-output.txt)의 pm_observer_mdm_power_on
      데이터가 재부팅 시 손실됨 — collector가 child_summary grep을 실행해야 host로 전달됨.
  V1197 v1106 collector 구조 문제: wait "$child_pid" 완료 전에 기기가 재부팅되면
  CHILD_LOG 내용이 host에 전달되지 않음. vndservice-gate-not-activated는 child_summary
  미실행의 증상이지 mdm_helper 문제가 아님.
  V1195/V1196 "RELATED confirmed no reboot" 주석은 실제 결과가 아니라 계획상 기댓값.
  실제 V1195/V1196 live run은 모두 serial 홍수로 실패.
  V1198 수정사항:
  - --pm-observer-trigger-pcie-enumerate 제거 (재부팅 원인)
  - v1106 collector에 tail -f "$CHILD_LOG" & 추가 → CHILD_LOG 내용 실시간 serial 전송
    → 기기 재부팅 시에도 host가 pm_observer_mdm_power_on.status.* 데이터 수신 가능
  - --thread-sample-count 0 유지
  - helper v237 재사용 (SHA: a450e8274745144c23efbd57d56d51cce701391a8f919bc11be2994f4841b9df)
  다음: run V1198 live gate → classify mdm_helper fd/wchan from status entries.
  Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping 계속 블록.
- V1196 live results (v229–v236 progressive, 실제 결과 아님 — serial 홍수로 미완):
  - v229: restart_level=RELATED write — sysfs 쓰기 작동 확인 (V1196 script 주석)
  - v230–v231: 10s periodic status + fdatasync — 설계상 포함
  - v232–v233: mdm_helper PID tracking + thread wchans — 설계상 포함
  - v235–v236: PCIe enumerate pre-fork — V1197에서 재부팅 유발로 판명, V1198에서 제거
  - PCIe RC1 LTSSM always reaches POLL_COMPLIANCE; "MDM PMIC GPIO is not supported" from mdm-4x
  - mhi_dev_count=0 throughout 3-minute window; GPIO 142 IRQ count=0
- V1186 host-only 분류기 — per_mgr SELinux 도메인 및 early exit path 분류.
  V1185 live 결과: gate_begin=True, poll_count=22, gate_timeout → per_proxy_skipped=1.
  V1181 race condition은 차단됐으나 per_mgr이 vndservicemanager 등록 전에 exit_code=0으로
  자발 종료 (per_mgr_vndbinder_count=-1, pm_server_register_entry=0, per_mgr_obs_at_probe=1).
  per_mgr은 시작 직후 alive 상태였으나 ~5s gate window 내 종료.
  `preexec_context_suppressed_reason=pm-service-trigger-observer-ptrace-lite-output-budget`
  → per_mgr exec context 로그 없음. helper가 `kernel` 도메인에서 실행 시
  `allow kernel vendor_per_mgr:process transition` 규칙 없으면 per_mgr도 `kernel`
  도메인으로 실행 → pm-service 초기화(vendor socket, binder 등) 실패 가능.
  다음: V1186 host-only — per_mgr 실행 도메인 캡처 (ptrace-lite 예산 한도 완화 또는
  별도 SELinux 컨텍스트 확인 방법 검토). Wi-Fi HAL, scan/connect, credentials,
  DHCP/routes, external ping 계속 블록.
- V1185 live FAIL (gate timeout, new blocker) — gate 위치 수정 확인됨 (per_proxy_skipped=1).
  per_mgr이 vndbinder 없이 exit_code=0으로 종료. pm_server_register_entry=0.
  per_proxy race는 해결됐으나 per_mgr 자체 초기화 실패가 새 blocker.
- V1184 host-only PASS — V1183 게이트 위치 버그 + 파싱 버그 분류 완료.
  helper v221 (pre-spawn gate) 빌드. SHA256: `120fad47dad2965ab8a541759bf1cd04396b9f81eb0c06986096e6f05dfdf05d`.
- V1183 live FAIL (gate design bug) — gate가 per_proxy spawn 이후에 위치, log-only.
  script parse bug로 manifest decision 오진단.
- V1182 source/build-only PASS — `--pm-observer-per-proxy-after-vndservice-provider`
  flag 추가. helper SHA256: `b456ca27ca7ba3becfea538ea4a3c723500084499537900e1a5a83ac72601654`.
- V1181 host-only PASS — per_mgr 자발 종료 root cause 분류 완료.
  핵심: (1) helper v218/v219에서 `materialize_peripheral_manager_node_parity()`
  추가로 private namespace에 `/dev/subsys_modem` 노드 생성됨 → pm_proxy_helper가
  노드를 열 수 있게 됨. (2) `--pm-observer-per-proxy-pph-delta-ms` flag로
  per_proxy가 per_mgr+~250ms 시점에 `pm_client_register("modem")` Binder 호출
  → per_mgr 내부 peripheral list 미완성 상태에서 모뎀 등록 수신 → exit 0.
  V1105(구 helper)는 subsys_modem 노드 없음, per_proxy는 per_mgr+1000ms에 시작
  (충분한 초기화 시간) → pm_client_register_ret=0 성공.
- V1180 live PASS — per_proxy pph+247ms (target 300ms) 내 시작,
  pm_proxy_helper가 `/dev/subsys_modem` (fd=3) 보유 확인. 그러나 per_mgr
  (pm-service)이 exit_code=0으로 자발 종료 (<247ms), PM state machine
  state_set_event_count=0, vndservice_provider_seen=0. pm_proxy_helper는
  `/dev/vndbinder` fd 없음 (one-shot이므로 불필요).
- V1179 기준: V904 host-only parity confirms the blocker is Android
  `mdm_helper` runtime input parity. Android runs `vendor.mdm_helper` as
  `u:r:vendor_mdm_helper:s0` after `vendor.per_mgr=running`; `pm-service`
  owns `/dev/subsys_esoc0`/`/dev/subsys_modem`, `mdm_helper` owns
  `/dev/esoc-0`, and `ks` reaches the MHI pipe. Native V903 direct
  `mdm_helper` remains in `kernel` context with tty/pipe/socket fds only and no
  `/dev/esoc-0`, MHI, or `ks`. Next is V905 fail-closed runtime-input repair
  design before any subsystem-open retry. Wi-Fi HAL, scan/connect, credentials,
  DHCP/routes, and external ping remain blocked.
- V874 결론: `/dev/esoc-0` read-only control path가 live에서 열렸고
  `GET_STATUS`/`GET_ERR_FATAL`은 rc `0`, `GET_LINK_ID`는 errno `22`로
  반환됐다. 결과는 `read-only-ioctl-probe-complete`이며 created nodes cleanup,
  selftest fail0, actor-clean, Wi-Fi-link-clean이 모두 pass다.
- V875 결론: host-only classifier가 local OSRC와 V849/V874 evidence를 기준으로
  helper-only CMD/REQ registration support를 다음 단계로 선택했다. Live contact
  및 mutating eSoC ioctl은 없었다. 다음 후보는 V876 helper `v137`
  source/build-only이며, `CMD_EXE`, `PWR_ON`, `WAIT_FOR_REQ`, `NOTIFY`,
  `/dev/subsys_esoc0` open, actor start, Wi-Fi bring-up은 계속 막는다.
- V876 결론: helper `v137` source/build-only가 통과했다. 새 mode는
  `wifi-companion-esoc-engine-register-preflight`이고 allow flag는
  `--allow-esoc-engine-register-preflight`이다. V876에서는 deploy/live ioctl
  실행이 없었다. 다음 후보는 V877 helper `v137` deploy-only proof다.
- V877 결론: helper `v137`을 `/cache/bin/a90_android_execns_probe`에 serial
  deploy했고 remote sha/mode marker, selftest fail0, actor-clean,
  Wi-Fi-link-clean이 pass였다. V877에서는 live eSoC ioctl, actor start,
  Wi-Fi bring-up이 없었다. 다음 후보는 V878 bounded live
  `REG_CMD_ENG`/`REG_REQ_ENG` registration preflight다. `CMD_EXE`, `PWR_ON`,
  `WAIT_FOR_REQ`, `NOTIFY`, `/dev/subsys_esoc0` open, `mdm_helper`, `ks`,
  `pm_proxy_helper`, CNSS, HAL, scan/connect, credentials, DHCP/routes,
  external ping은 별도 gate 전까지 계속 막는다.
- V878 결론: bounded live CMD/REQ registration preflight는 안전하게 끝났지만
  decision은 `v878-esoc-engine-register-ioctl-review`다. `REG_REQ_ENG`는 rc `0`,
  `REG_CMD_ENG`는 errno `16`(`EBUSY`)였고, dmesg에는 `Client hooks not
  registered for the device`가 남았다. 금지 액션과 Wi-Fi bring-up은 없었고
  selftest fail0/cleanup/actor-clean/Wi-Fi-link-clean은 유지됐다. 다음 후보는
  V879 host-only CMD engine ownership/eSoC client-hook classifier다.
- V879 결론: host-only classifier가 `REG_CMD_ENG EBUSY`를 직접 userspace
  `CMD_EXE` 차단으로 분류했다. `REG_REQ_ENG rc0`는 V849 `req_eng_wait`
  블로커를 좁히므로, 다음 후보는 live가 아니라 V880 helper `v138`
  source/build-only다. 범위는 stale open errno repair와 REQ fd를 유지한
  bounded `/dev/subsys_esoc0` hold preflight support 추가이며, 직접
  `CMD_EXE`/명시적 userspace `PWR_ON`/`WAIT_FOR_REQ`/`NOTIFY`/actor/Wi-Fi
  bring-up은 계속 막는다.
- V880 결론: helper `v138` source/build-only가 통과했고
  `wifi-companion-esoc-req-registered-subsys-hold-preflight` mode와
  allow flag가 추가됐다. Deploy/live ioctl/subsystem open은 없었다.
- V881 결론: helper `v138` deploy-only가 통과했다. Remote sha/mode marker,
  selftest fail0, actor-clean, Wi-Fi-link-clean이 pass였고 live eSoC ioctl,
  `/dev/subsys_esoc0` open, actor start, Wi-Fi bring-up은 없었다. 후속 분석상
  초기 powerup은 `REG_REQ_ENG`가 핵심이고 `CMD_ENG` ownership은 불필요할 수
  있으며, SDX50M은 `ESOC_REQ_IMG`를 내지 않을 수 있다. 다음 후보는 live가
  아니라 V882 helper `v139` source/build-only passive `ESOC_WAIT_FOR_REQ`
  observer support다.
- V882 결론: helper `v139` source/build-only가 통과했다. 기존
  REQ-registered subsystem-hold mode에 passive `ESOC_WAIT_FOR_REQ` observer
  child와 cleanup/reboot-required markers가 추가됐고 deploy/device
  contact/live eSoC ioctl/subsystem open/Wi-Fi bring-up은 없었다. 다음 후보는
  V883 helper `v139` deploy-only proof다.
- V883 결론: helper `v139` deploy-only가 통과했다. Remote sha/mode marker,
  selftest fail0, actor-clean, Wi-Fi-link-clean이 pass였고 live eSoC ioctl,
  `/dev/subsys_esoc0` open, actor start, Wi-Fi bring-up은 없었다. 다음 후보는
  V884 bounded live REQ-registered subsystem-hold observer preflight다.
  V884는 `REG_REQ_ENG`를 핵심 precondition으로 보고 passive
  `ESOC_WAIT_FOR_REQ` 결과를 기록하되, `ESOC_REQ_IMG` 부재를 즉시 실패로
  보지 않는다. 직접 userspace `CMD_EXE`, 명시적 userspace `PWR_ON`,
  `ESOC_NOTIFY`, actor/HAL/scan/connect/credentials/DHCP/routes/external ping은
  계속 막는다.
- V884 결론: REQ-registered subsystem-hold live gate가 `REG_REQ_ENG rc0` 뒤
  `ESOC_WAIT_FOR_REQ rc=4 errno=0 value=1`을 기록했다. 로컬 OSRC 기준 rc `4`는
  copied `sizeof(u32)`이고 value `1`은 `ESOC_REQ_IMG`다. 즉 SDX50M은 실제로
  image request를 냈고, native가 Android-equivalent image transfer/notify
  sequence를 수행하지 않아 `/dev/subsys_esoc0` open이 D-state로 남았다.
  Recovery reboot 후 native version/selftest는 정상 복구됐다. 다음 후보는
  V885 host-only Android `mdm_helper` image-request response classifier다.
- V885 결론: host-only classifier가 V884 요청을 `ESOC_REQ_IMG`로 확정했다.
  `WAIT_FOR_REQ rc=4 errno=0 value=1`은 ioctl failure가 아니라 copied
  `sizeof(u32)` byte count와 request value다. Local OSRC는
  `ESOC_IMG_XFER_DONE`/`ESOC_BOOT_DONE` response hook을 노출한다. 다음 후보는
  V886 helper `v140` source/build-only semantic repair와 guarded response
  scaffold다. Live `ESOC_NOTIFY`와 subsystem-open retry는 별도 gate 전까지
  막는다.
- V886 결론: helper `v140` source/build-only가 통과했다. Passive
  `ESOC_WAIT_FOR_REQ` observer가 nonnegative `sizeof(u32)` byte count를
  `request-observed`로 분류하고 request name/`ESOC_REQ_IMG` marker를 출력한다.
  `ESOC_IMG_XFER_DONE`/`ESOC_BOOT_DONE` response scaffold marker는 생겼지만
  live `ESOC_NOTIFY`는 여전히 실행하지 않는다. 다음 후보는 V887 helper
  `v140` deploy-only checksum/version/mode proof다.
- V887 결론: helper `v140` deploy-only가 통과했다. Serial chunk `3000`은
  line-safety check에서 `chunks_written=0`으로 중단됐고, chunk `1850` retry가
  `788` chunks, max line `3890`/safe `3968`로 성공했다. Remote sha는
  `894fdd753cb6567b2abbb3c94f332ce63cf959b7d1708768cf3bcdc10b2b53e0`이고
  helper marker/mode가 확인됐다. 다음 후보는 live가 아니라 V888 host-only
  response-gate plan/classifier다.
- V888 결론: host-only classifier가 next response gate를 확정했다. 첫 response는
  `ESOC_IMG_XFER_DONE`이고, `ESOC_BOOT_DONE`은 `ESOC_RUN_STATE`를 발생시켜
  subsystem powerup wait를 완료하므로 blind first response로 쓰지 않는다.
  다음 후보는 V889 helper `v141` source/build-only conditional response mode다.
- V889 결론: helper `v141` source/build-only가 통과했다. 새 mode
  `wifi-companion-esoc-conditional-response-preflight`와 allow flag
  `--allow-esoc-conditional-response-preflight`가 추가됐다. Conditional response
  logic은 `ESOC_REQ_IMG` 관측 후 `ESOC_IMG_XFER_DONE`, `ESOC_GET_STATUS` polling,
  status `1`일 때만 `ESOC_BOOT_DONE`을 수행하도록 준비됐지만 V889에서는
  deploy/live 실행이 없었다. 다음 후보는 V890 helper `v141` deploy-only다.
- V890 결론: helper `v141` deploy-only가 통과했다. Remote sha는
  `e6909cbfee79a4a1f55a3f039cdc29dca57f31e00c19d63a1a452d633c060f21`이고
  conditional response mode token이 확인됐다. 다음 후보는 V891 bounded live
  conditional response proof다.
- V891/V892 결론: helper `v141`의 global allowlist 누락 때문에 첫 V891은
  live eSoC action 전에 rc `2`로 중단됐다. V892에서 helper `v142`로 repair
  및 deploy했고, repaired V891은 `ESOC_REQ_IMG` 관측 후
  `ESOC_IMG_XFER_DONE`을 rc `0`으로 전송했다. `ESOC_GET_STATUS`는 87회 모두
  value `0`이어서 `ESOC_BOOT_DONE`은 보내지 않았다. cleanup reboot 후
  `bootstatus`와 `selftest fail=0`가 통과했다. 다음 후보는 V893
  post-image-done readiness classifier다.
- V893 결론: `ESOC_IMG_XFER_DONE`은 readiness setter가 아니라
  `MDM2AP_STATUS` readiness check를 schedule하는 notify다. ready 전환은
  `MDM2AP_STATUS` line/IRQ가 high가 되어 `mdm->ready = true`가 되는
  경로에 달려 있다. blind `ESOC_BOOT_DONE`은 계속 금지한다. 다음 후보는
  V894 bounded MDM2AP status/ready observer 계획이다.
- V894 결론: DTS와 current native surface 기준으로
  `/proc/interrupts`의 `msmgpio-dc 142 Edge mdm status` line이 MDM2AP
  readiness transition의 read-only observer다. debugfs GPIO는 현재 native
  boot에서 없다. 다음 후보는 V895 bounded IRQ snapshot proof다.
- V895 결론: helper `v143`이 GPIO 142 `mdm status` IRQ snapshot을 추가했고
  deploy/live proof가 통과했다. `ESOC_REQ_IMG` 관측 후 `ESOC_IMG_XFER_DONE`은
  전송됐지만 `ESOC_GET_STATUS`는 86회 모두 `0`, `ESOC_BOOT_DONE`은 미전송,
  GPIO 142 IRQ count는 89개 phase 전체에서 `0`이었다. cleanup reboot 후
  `bootstatus`와 `selftest fail=0`가 통과했다. 다음 후보는 live 재시도가
  아니라 Android `mdm_helper` / image-transfer contract host-only
  classifier다.

- 아래 V840-V847 항목은 V874/V875 이전 경로 요약이다.
- V840 결론: provider-first service-manager/PeripheralManager, CNSS retry,
  prearmed WLAN-PD listener를 결합해도 native는 WLAN-PD `UNINIT` 상태이고
  `wlfw_start`, BDF, FW-ready, `wlan0`가 모두 없다.
- V841 결론: Android V622는 `cnss-daemon wlfw_start`가 WLAN-PD `UP`보다
  먼저 나오지만, native V840은 CNSS netlink/CLD80211까지 도달하고도
  `wlfw_start`가 없다. `sysmon_esoc0`는 Android에서 WLAN-PD 이후라
  현재 증거상 선행 prerequisite로 보지 않는다.
- V842 결론: coarse `cnss-daemon` launch contract는 닫혔다. Android/native
  모두 command, identity, SELinux domain, capability, vndbinder/fd surface가
  맞고 native는 alive sleeping pre-WLFW stall이다.
- V843 결론: V840 current-window retry는 `do_sys_poll`/`futex_wait_queue_me`
  대기 상태로 살아 있고 CNSS user socket, netlink, vndbinder surface가
  존재한다. 그러나 `wlfw_start`, WLAN-PD, BDF, FW-ready, `wlan0`는 없다.
- V844 결론: OSRC DTS에서 `qcom,mdm3`는 `qcom,ext-sdx50m` external eSoC
  경로이고 AP/MDM GPIO handshake, SSCTL instance `16`, sysmon id `20`을
  가진다. ICNSS source상 service-notifier UP는 초기 boot trigger가 아니며
  실제 초기 진행은 QRTR service 69 `wlfw_new_server()` publication에
  의존한다. Native는 `mss=ONLINE`이어도 `mdm3=OFFLINING`이고 WLFW/BDF/
  FW-ready/`wlan0`가 없다.
- V845 결론: live read-only에서 mdm3/eSoC sysfs, `subsys_esoc0`, live
  devicetree `qcom,ext-sdx50m`, AP/MDM GPIO properties가 존재한다.
  `mdm3=OFFLINING`, raw `/dev/esoc*`/`/dev/subsys*`는 없고, GPIO 135/142는
  export되어 있지 않다. `esoc_link`, `esoc_link_info`, `esoc_name`,
  `subsys9/state`, `subsys0/state`는 readable+writable 후보지만 V845는
  읽기만 수행했다.
- 다음 후보: V846 source-backed mdm3/eSoC state-control contract classifier.
  쓰기 가능한 파일이 있다는 이유로 바로 쓰지 말고, OSRC eSoC/subsystem
  code path와 rollback 가능성을 먼저 분류한다.
- V846 결론: direct `subsys9/state` write는 OSRC상 `DEVICE_ATTR_RO(state)`라
  거부한다. opaque `esoc_link`/`esoc_name` write와 raw `/dev/esoc*` ioctl도
  다음 gate로 쓰지 않는다. source-backed userspace boot contract는
  `subsys_esoc0` char-device open 경로이며, open은
  `subsystem_get_with_fwname()`/`subsys_start()`, release는
  `subsystem_put()`/`subsys_stop()`으로 이어진다.
- 다음 후보: V847 bounded live `subsys_esoc0` char-device materialize/open
  smoke. V845 uevent `major=236 minor=9 devname=subsys_esoc0`만 사용하고,
  watchdog, dmesg/state evidence, cleanup reboot, postflight health를 포함한다.
- V847 결론: `/dev/subsys_esoc0`를 `236:9`로 materialize했고 background
  open/hold가 `__subsystem_get: esoc0 count:0` 및 `fw_name=esoc0` 변경까지
  진입했다. 그러나 bounded window 안에서 `holder.opened=1`은 없었고
  `mdm3=OFFLINING`, MHI/PCIe, WLFW/BDF/FW-ready/`wlan0`는 여전히 없다.
  cleanup reboot 후 native health는 복구됐다.
- 다음 후보: V848 host-only `subsys_esoc0` open-block boundary classifier.
  바로 재시도하거나 hold 시간을 늘리지 말고, OSRC `subsys_start()`/ext-mdm/
  MHI hook 경계와 V847 dmesg를 먼저 분류한다.
- Wi-Fi HAL, scan/connect, DHCP/routes, credentials, external ping, `esoc0`,
  subsystem writes, module load/unload, boot image writes는 계속 막는다.

---

## 모듈화 설계 기준

v80/v81 이후 모듈화는 단순히 파일을 작게 나누는 작업이 아니라, PID 1이
실패했을 때 원인을 좁히고 복구 가능한 부팅 경로를 유지하기 위한 구조화 작업이다.
분리 기준은 아래 네 가지로 고정한다.

- **부팅 순서**: `init_main`은 PID 1 부팅 흐름만 보여 주고, 세부 구현은 모듈에 둔다.
- **책임 영역**: log, timeline, storage, console, shell, display, input, network를 섞지 않는다.
- **장애 영향 범위**: boot-critical 계층부터 작게 분리하고, UI/network/service는 안정화 후 분리한다.
- **의존성 방향**: 하위 계층인 util/log/timeline이 HUD, shell, menu 같은 상위 계층을 호출하지 않게 한다.

참고 구조:

- Linux initramfs: rootfs의 `/init`이 PID 1로 실행되며 이후 부팅을 책임진다.
  - https://docs.kernel.org/6.2/filesystems/ramfs-rootfs-initramfs.html
- Android init: early mount/dev/proc 준비와 first/second stage 흐름을 나눈다.
  - https://android.googlesource.com/platform/system/core.git/+/1350207265745ad3e5ee26017a0f8cc14dc268b8/init/README.md
- Buildroot/BusyBox init: 임베디드 환경에서는 작은 init과 service/run 구조가 실용적이다.
  - https://buildroot.org/downloads/manual/manual.html
- USB gadget configfs: ACM/NCM은 gadget function/config 조합이므로 USB gadget 제어와 network 정책을 분리한다.
  - https://www.kernel.org/doc/html/latest/usb/gadget_configfs.html
- DRM/KMS dumb buffer: early graphics에는 저수준 KMS와 drawing/HUD/menu 계층 분리가 적합하다.
  - https://www.kernel.org/doc/html/v4.8/gpu/drm-kms.html

목표 모듈 경계:

```text
init_main
  -> util / log / timeline / dev / storage
  -> console / shell / cmdproto / run
  -> metrics / kms / draw / hud / input / menu
  -> usb_gadget / netservice
  -> optional helpers / BusyBox / dropbear
```

`v114 HELPER DEPLOY 2`까지 실기 verified 완료했다. v106-v108은 UI/App Architecture split로 진행했고 ABOUT/changelog, displaytest/cutout, input monitor/layout UI를 각각 `a90_app_about.c/h`, `a90_app_displaytest.c/h`, `a90_app_inputmon.c/h`로 분리했다. v114 결과는
`docs/reports/NATIVE_INIT_V114_HELPER_DEPLOY_2026-05-04.md`에 둔다. v113 결과는
`docs/reports/NATIVE_INIT_V113_RUNTIME_PACKAGE_LAYOUT_2026-05-04.md`에 둔다. v112 결과는
`docs/reports/NATIVE_INIT_V112_USB_SERVICE_SOAK_2026-05-04.md`에 둔다. v111 결과는
`docs/reports/NATIVE_INIT_V111_EXTENDED_SOAK_RC_2026-05-04.md`에 둔다. v110 결과는
`docs/reports/NATIVE_INIT_V110_APP_CONTROLLER_CLEANUP_2026-05-04.md`에 둔다. v109 결과는
`docs/reports/NATIVE_INIT_V109_STRUCTURE_AUDIT_2026-05-04.md`에 둔다. v108 결과는
`docs/reports/NATIVE_INIT_V108_UI_APP_INPUTMON_2026-05-04.md`에 둔다. v107 결과는
`docs/reports/NATIVE_INIT_V107_UI_APP_DISPLAYTEST_2026-05-04.md`에 둔다. v106 결과는
`docs/reports/NATIVE_INIT_V106_UI_APP_ABOUT_2026-05-04.md`에 둔다. v105 결과는
`docs/reports/NATIVE_INIT_V105_SOAK_RC_2026-05-04.md`에 둔다. v104 결과는
`docs/reports/NATIVE_INIT_V104_WIFI_FEASIBILITY_2026-05-04.md`에 둔다. v103 결과는
`docs/reports/NATIVE_INIT_V103_WIFI_INVENTORY_2026-05-04.md`에 둔다. v102 결과는
`docs/reports/NATIVE_INIT_V102_DIAGNOSTICS_2026-05-03.md`에 둔다. v101 결과는
`docs/reports/NATIVE_INIT_V101_SERVICE_MANAGER_2026-05-03.md`에 둔다. v100 결과는
`docs/reports/NATIVE_INIT_V100_REMOTE_SHELL_2026-05-03.md`에 둔다. v99 결과는
`docs/reports/NATIVE_INIT_V99_BUSYBOX_USERLAND_2026-05-03.md`에 둔다. v98 결과는
`docs/reports/NATIVE_INIT_V98_HELPER_DEPLOY_2026-05-03.md`에 둔다. v97 결과는
`docs/reports/NATIVE_INIT_V97_SD_RUNTIME_ROOT_2026-05-03.md`에 둔다. v96 결과는
`docs/reports/NATIVE_INIT_V96_STRUCTURE_AUDIT_2026-05-03.md`에 둔다. v95 결과는
`docs/reports/NATIVE_INIT_V95_NETSERVICE_USB_API_2026-05-03.md`에 둔다. v94 결과는
`docs/reports/NATIVE_INIT_V94_BOOT_SELFTEST_API_2026-05-03.md`에 둔다.
v96-v105 장기 로드맵은
`docs/plans/NATIVE_INIT_LONG_TERM_ROADMAP_2026-05-03.md`를 기준으로 한다.
v103 상세 계획은
`docs/plans/NATIVE_INIT_V103_WIFI_INVENTORY_PLAN_2026-05-04.md`에 둔다.
v104 상세 계획은
`docs/plans/NATIVE_INIT_V104_WIFI_FEASIBILITY_PLAN_2026-05-04.md`에 둔다.
v105 상세 계획은
`docs/plans/NATIVE_INIT_V105_SOAK_RC_PLAN_2026-05-04.md`에 둔다.
v102 상세 계획은
`docs/plans/NATIVE_INIT_V102_DIAGNOSTICS_PLAN_2026-05-03.md`에 둔다. v101 상세 계획은
`docs/plans/NATIVE_INIT_V101_SERVICE_MANAGER_PLAN_2026-05-03.md`에 둔다. v100 상세 계획은
`docs/plans/NATIVE_INIT_V100_REMOTE_SHELL_PLAN_2026-05-03.md`에 둔다. v99 상세 계획은
`docs/plans/NATIVE_INIT_V99_BUSYBOX_USERLAND_PLAN_2026-05-03.md`에 둔다.
v96 상세 계획과 결과는
`docs/plans/NATIVE_INIT_V96_STRUCTURE_AUDIT_PLAN_2026-05-03.md`,
`docs/reports/NATIVE_INIT_V96_STRUCTURE_AUDIT_2026-05-03.md`에 둔다.
v97 상세 계획은
`docs/plans/NATIVE_INIT_V97_SD_RUNTIME_ROOT_PLAN_2026-05-03.md`에 둔다. v98 상세 계획과 결과는
`docs/plans/NATIVE_INIT_V98_HELPER_DEPLOY_PLAN_2026-05-03.md`,
`docs/reports/NATIVE_INIT_V98_HELPER_DEPLOY_2026-05-03.md`에 둔다.
v93 계획과 결과는
`docs/plans/NATIVE_INIT_V93_STORAGE_API_PLAN_2026-05-02.md`,
`docs/reports/NATIVE_INIT_V93_STORAGE_API_2026-05-02.md`에 둔다.
v92 계획과 결과는 `docs/plans/NATIVE_INIT_V92_SHELL_CONTROLLER_PLAN_2026-05-02.md`,
`docs/reports/NATIVE_INIT_V92_SHELL_CONTROLLER_API_2026-05-02.md`에 둔다.
shell/cmdproto 착수 지도와 실행 계획은 각각 `docs/reports/NATIVE_INIT_V83_CONSOLE_SHELL_CMDPROTO_DEPENDENCY_MAP_2026-04-29.md`,
`docs/plans/NATIVE_INIT_V84_SHELL_CMDPROTO_PLAN_2026-04-29.md`에 보존한다.

---

## 프로젝트 목표 재정의

현재 프로젝트의 목표는 `native Linux 진입 가능성 확인`이 아니라,
이미 확보한 진입점을 기반으로 **Android kernel 위에 작은 native Linux userspace를
직접 구성하는 것**이다.

목표 구조:

```text
Samsung bootloader
  -> stock Android Linux kernel
    -> custom static /init (PID 1)
      -> native runtime services
      -> serial shell
      -> KMS HUD/menu
      -> input/button control
      -> sysfs/proc/device map
      -> log/storage layer
      -> optional BusyBox/network/SSH
```

이 프로젝트에서 `서버처럼 사용한다`는 말은 처음부터 Debian 전체를 올린다는 뜻이 아니다.
우선 목표는 아래 조건을 만족하는 초소형 임베디드 Linux 콘솔이다.

- 부팅 진행과 실패 원인이 화면 또는 로그에 남는다.
- serial shell이 성공/실패를 신뢰 가능하게 보고한다.
- 외부 static binary를 실행하고 exit status를 확인할 수 있다.
- `/cache` 같은 안전한 저장소에 로그와 도구를 둘 수 있다.
- 파티션별 안전 등급을 구분해 Android/identity/security 영역을 실수로 덮어쓰지 않는다.
- 버튼만으로 최소한의 상태 확인과 recovery/poweroff 조작이 가능하다.
- 추후 USB network와 SSH/dropbear를 붙일 수 있는 runtime 구조를 가진다.

---

## 구현 범위와 비목표

현재 범위:

- custom `/init` 안정화
- shell/HUD/menu/log/runtime 구현
- 필요한 `/proc`, `/sys`, `/dev`, ioctl 경로 탐색
- safe storage와 boot recovery path 유지
- BusyBox 같은 static userland 검토
- USB serial 기반 운용

명시적 비목표:

- full POSIX shell 직접 구현
- Debian/Ubuntu 전체 배포판 즉시 포팅
- Android framework, Zygote, SurfaceFlinger 복구
- 커널 교체 또는 커널 드라이버 개발
- 카메라/모뎀/GPU 가속 같은 vendor userspace 의존 기능 지원
- `/efs`, RPMB, keymaster, modem 영역 쓰기

---

## 단계별 마일스톤

### M0. Native init 진입 확보 — 완료

- stock Android kernel 부팅
- custom static `/init` PID 1 실행
- USB ACM serial shell 확보
- KMS 화면 출력 확보
- 버튼 입력과 기본 sensor/sysfs 읽기 확보

### M1. 신뢰 가능한 native console

- shell return code 정밀화 — v40 완료
- command duration/result/errno 기록 — v40/v41 완료
- blocking command 취소 정책 통일 — v42 완료
- serial 반향/prompt 오염 방어

### M2. 관찰 가능한 boot/runtime

- `/cache/native-init.log` — v41 완료
- boot readiness timeline — v43 완료
- HUD boot progress/error 표시 — v44 완료
- safe storage/partition map 문서화 — v46 완료

### M3. 단독 운용 가능한 device UI

- 버튼 기반 on-screen menu — v47/v52 완료
- status/log/reboot/recovery/poweroff 조작 — v52 완료
- menu-active serial busy gate와 `hide` 요청 — v53 완료
- unsolicited `AT` serial noise filter — v59 완료
- serial 없이도 최소 복구 조작 가능 — 계속 검증

### M4. 작은 Linux userland

- static toybox 실행 — 완료
- `/cache/bin` 또는 ramdisk 기반 tool path — 완료
- process 실행, timeout, signal, zombie 회수 안정화 — 진행 중

### M5. 서버형 접근

- USB NCM probe — 완료
- USB NCM persistent link + IPv4/IPv6 ping + host→device netcat 검증 — 완료
- USB NCM 운영 helper + TCP nettest helper — 완료
- NCM TCP control helper — 완료
- TCP control host wrapper — 완료
- NCM + TCP control 5분 soak — 완료
- boot-time NCM/tcpctl netservice 정책 — v60 완료
- netservice stop/start software UDC reconnect recovery — v60 완료
- HUD CPU/GPU usage percent 표시 — v61 완료
- CPU stress usage gauge + `/dev/null`/`/dev/zero` guard — v62 완료
- 계층형 앱 메뉴 + CPU stress screen app — v63 완료
- TEST 부팅 화면을 custom boot splash로 교체 — v64 완료
- boot splash 잘림 방지 safe layout — v65 완료
- semantic version + ABOUT/changelog/credits app — v66 완료
- compact ABOUT typography + version별 changelog detail — v67 완료
- HUD log tail + expanded changelog history — v68 완료
- physical-button input gesture layout — v69 완료
- input monitor app + raw/gesture trace — v70 완료
- HUD/menu live log tail panel — v71 완료
- display test screen + framebuffer color fix — v72 완료
- cmdv1/A90P1 shell protocol + host wrapper — v73 완료
- cmdv1x length-prefixed argv encoding — v74 완료
- idle-timeout serial reattach log quieting — v75 완료
- AT fragment serial noise hardening — v76 완료
- display test multi-page app + cutout calibration — v77 완료
- ext4 SD workspace + `mountsd` storage manager — v78 완료
- boot-time SD health check + `/cache` fallback — v79 완료
- PID1 source layout split into include modules — v80 완료
- config/util true `.c/.h` base module extraction — v81 완료
- log/timeline true `.c/.h` API module extraction — v82 완료
- console true `.c/.h` API module extraction — v83 완료
- cmdproto true `.c/.h` API module extraction — v84 완료
- run/service true `.c/.h` API module extraction — v85 완료
- KMS/draw true `.c/.h` API module extraction — v86 완료
- input true `.c/.h` API module extraction — v87 완료
- HUD true `.c/.h` API module extraction — v88 완료
- menu control true `.c/.h` API module extraction + nonblocking `screenmenu` — v89 완료
- metrics true `.c/.h` API module extraction — v90 완료
- CPU stress external helper process separation — v91 완료
- shell/controller metadata and busy policy API extraction — v92 완료
- storage true `.c/.h` API module extraction — v93 완료
- boot selftest non-destructive module smoke test API — v94 완료
- netservice/USB gadget true `.c/.h` API module extraction — v95 완료
- structure audit/refactor debt cleanup — v96 완료
- SD runtime root promotion — v97 완료
- helper deployment/package manifest — v98 완료
- BusyBox static userland evaluation — v99 완료
- TCP shell/dropbear remote access prototype — v100 완료
- Minimal service manager command/view — v101 완료
- Diagnostics/log bundle command and host collector — v102 완료
- Wi-Fi read-only inventory — v103 완료
- Wi-Fi enablement feasibility — v104 완료, 현재 gate 결과 no-go/baseline-required
- long-run soak/recovery release candidate — v105 완료
- ABOUT/displaytest/input monitor UI app split — v106-v108 완료
- post-v108 structure audit — v109 완료
- app controller cleanup — v110 완료
- extended soak RC — v111 완료
- USB/NCM service soak — v112 완료
- runtime package layout — v113 완료
- helper deployment 2 — v114 완료
- remote shell hardening — v115 완료
- diagnostics bundle 2 — v116 완료
- v109-v116 completion audit — 완료
- long soak foundation — v146 완료
- long soak status — v147 완료
- long soak correlation — v148 완료
- static dropbear SSH 또는 custom TCP shell

---

## 현재 기준점

- 최신 확인 버전: `A90 Linux init 0.9.53 (v153)`
- 공식 버전: `0.9.53`
- build tag: `v153`
- creator: redacted legacy field
- 최신 verified 소스: `stage3/linux_init/init_v153.c` + `stage3/linux_init/v153/*.inc.c` + `stage3/linux_init/helpers/a90_cpustress.c` + `stage3/linux_init/helpers/a90_rshell.c` + `stage3/linux_init/helpers/a90_longsoak.c` + `stage3/linux_init/a90_config.h` + `stage3/linux_init/a90_util.c/h` + `stage3/linux_init/a90_log.c/h` + `stage3/linux_init/a90_timeline.c/h` + `stage3/linux_init/a90_console.c/h` + `stage3/linux_init/a90_cmdproto.c/h` + `stage3/linux_init/a90_run.c/h` + `stage3/linux_init/a90_service.c/h` + `stage3/linux_init/a90_kms.c/h` + `stage3/linux_init/a90_draw.c/h` + `stage3/linux_init/a90_input.c/h` + `stage3/linux_init/a90_input_cmd.c/h` + `stage3/linux_init/a90_hud.c/h` + `stage3/linux_init/a90_menu.c/h` + `stage3/linux_init/a90_metrics.c/h` + `stage3/linux_init/a90_shell.c/h` + `stage3/linux_init/a90_controller.c/h` + `stage3/linux_init/a90_storage.c/h` + `stage3/linux_init/a90_selftest.c/h` + `stage3/linux_init/a90_usb_gadget.c/h` + `stage3/linux_init/a90_netservice.c/h` + `stage3/linux_init/a90_pid1_guard.c/h` + `stage3/linux_init/a90_runtime.c/h` + `stage3/linux_init/a90_helper.c/h` + `stage3/linux_init/a90_userland.c/h` + `stage3/linux_init/a90_diag.c/h` + `stage3/linux_init/a90_exposure.c/h` + `stage3/linux_init/a90_wifiinv.c/h` + `stage3/linux_init/a90_wififeas.c/h` + `stage3/linux_init/a90_changelog.c/h` + `stage3/linux_init/a90_longsoak.c/h` + `stage3/linux_init/a90_app_about.c/h` + `stage3/linux_init/a90_app_cpustress.c/h` + `stage3/linux_init/a90_app_displaytest.c/h` + `stage3/linux_init/a90_app_inputmon.c/h` + `stage3/linux_init/a90_app_log.c/h` + `stage3/linux_init/a90_app_network.c/h`
- 최신 verified boot image: `stage3/boot_linux_v153.img`
- previous verified source-layout baseline: `stage3/linux_init/init_v80.c` + `stage3/linux_init/v80/*.inc.c`
- known-good fallback: `stage3/boot_linux_v48.img`
- 주 제어 채널: USB CDC ACM serial (`/dev/ttyGS0` ↔ `/dev/ttyACM0`)
- host bridge: `scripts/revalidation/serial_tcp_bridge.py --port 54321`
- 화면 상태: custom boot splash 약 2초 표시 후 상태 HUD/menu 자동 전환
- 버튼 상태: VOL+/VOL-/POWER 입력 확인
- 로그 상태: SD 정상 시 `/mnt/sdext/a90/logs/native-init.log`, fallback 시 `/cache/native-init.log`, emergency fallback 시 private `/tmp/a90-native/native-init.log` boot/command log 확인
- blocking 상태: `waitkey`/`readinput`/`watchhud`/`blindmenu` q/Ctrl-C 취소 확인
- long soak 상태: v146 recorder, v147 status, v148 correlation, v149 supervisor, v150 classifier, v151 bundle, v152 trend, v153 security hardening 실기 검증 완료
- timeline 상태: `timeline` 명령과 current native log replay 확인
- HUD 상태: `BOOT OK shell` summary 표시 확인
- run/log 상태: `/bin/a90sleep` q 취소와 recovery 왕복 log preservation 확인
- storage 상태: `/cache` safe write, ext4 SD workspace `/mnt/sdext/a90`, boot-time SD health check, critical partitions do-not-touch 기준 문서화
- storage I/O 상태: v161에서 `/mnt/sdext/a90/test-io` 4K/64K/1M/16M write/read/hash/rename/sync/unlink 검증 완료
- screen menu 상태: 자동 메뉴, 버튼 조작, input gesture layout, input monitor, serial `hide`/busy gate 확인
- USB 상태: ACM-only gadget `04e8:6861` / host `cdc_acm` 기준 문서화
- USB reattach 상태: v48 `usbacmreset`와 외부 helper `off` 후 serial 복구 확인
- USB NCM 상태: host `cdc_ncm` + device `ncm0`, IPv4 ping, IPv6 link-local ping, host→device netcat 확인
- NCM 운영 helper 상태: host interface 자동 탐지, ping, static TCP nettest 양방향 payload 검증 완료
- TCP control 상태: NCM 위에서 token-authenticated `/bin/a90_tcpctl` ping/status/run/shutdown 검증 완료
- TCP wrapper 상태: `tcpctl_host.py smoke` launch/client/stop 자동 검증 완료
- TCP soak 상태: v160에서 `tcpctl_host.py soak` 3602.5초/360사이클 안정성 검증 완료
- serial noise 상태: unsolicited `AT` modem probe line 무시 확인
- boot netservice 상태: opt-in flag 기반 NCM/tcpctl 부팅 자동 시작과 rollback 검증 완료
- netservice 기본값: disabled. `/cache/native-init-netservice` flag가 있을 때만 자동 시작
- reconnect 상태: v60 `netservice stop/start` software UDC 재열거 후 NCM/TCP 복구 확인
- HUD metrics 상태: CPU/GPU 온도와 사용률 `%` 표시, `cpustress`로 CPU usage 상승 확인
- dev node 상태: `/dev/null`/`/dev/zero` boot-time char device guard 확인
- app menu 상태: APPS/MONITORING/TOOLS/LOGS/NETWORK/POWER 계층 메뉴와 CPU stress 시간 선택 확인
- boot splash 상태: `A90 NATIVE INIT` custom splash와 `display-splash` timeline 기록 확인
- splash layout 상태: v65에서 긴 문구/footer 잘림 방지 safe layout 적용
- about app 상태: `APPS / ABOUT`에 version, changelog 목록/상세, credits 추가
- menu gate 상태: v128 기준 메뉴 표시 중 read-only status/query subcommand만 추가 허용하고 side-effect 명령은 `[busy]` 차단
- Wi-Fi 상태: v122 `wifiinv refresh`/`wififeas refresh` 기준 active bring-up은 계속 blocked
- Security Batch 1 상태: v123에서 tcpctl auth/bind, ramdisk tcpctl helper, dangerous `service` gate, reconnect cleanup fail-closed 적용 완료
- Security Batch 2 상태: v124에서 runtime helper SHA-256 preference, no-follow storage/log writes, mountsd SD identity gate, tcpctl install rollback 적용 완료
- Security Batch 3 상태: host tooling에서 cmdv1 retry/framing, ADB shell path quoting, NCM interface pinning, serial bridge identity pinning 적용 완료
- Security Batch 4 상태: v125에서 diagnostics/log owner-only permissions, private fallback log, HUD log tail opt-in 적용 완료
- Security Batch 5 상태: host/rootfs tooling에서 legacy root SSH default credential 제거와 safe archive extraction 적용 완료
- Security Batch 6 상태: v126에서 retained-source compatibility, v84 changelog route, v42 run stdin, input event validation 정리 완료
- Security Batch 7 상태: v127에서 menu-active busy gate deny-by-default allowlist 적용으로 F023 종료
- v128 상태: F023 mitigation을 유지하면서 menu-visible read-only subcommand policy 적용 완료
- v129 상태: changelog viewport/shared data/about page navigation 적용 완료
- v130 상태: volume hold-repeat scroll과 VOL+DN physical back shortcut 적용 완료
- v131 상태: EV_KEY repeat 미발생 환경을 위해 timer-based hold scroll 적용 완료, 실기 UX 정상 확인
- v132 상태: ABOUT/changelog legacy route 제거와 shared changelog table 단일 경로 정리 완료, 실기 flash/quick soak 확인
- v133 상태: ABOUT/changelog version series 분류 메뉴 적용 완료, 실기 flash/quick soak 및 수동 화면 확인
- v134 상태: network exposure guardrail 적용 완료, 실기 flash 후 `exposure status|verbose|guard`, `diag`, `screenmenu` 회귀 확인
- v135 상태: controller policy matrix 적용 완료, 실기 flash 후 `policycheck run`, menu-visible allow/block 대표 케이스, quick soak 확인
- v136 상태: post-v135 structure audit 완료, 실기 flash 후 `selftest verbose`, `exposure guard`, `policycheck run`, quick soak 확인
- v137 상태: integrated validation matrix 적용 완료, 실기 flash 후 `native_integrated_validate.py`, quick soak 확인
- v138 상태: release-candidate extended soak 적용 완료, 실기 flash 후 `native_integrated_validate.py`, quick soak, `native_rc_soak.py --cycles 3` 확인
- v139 상태: auto-HUD/menu controller cleanup 적용 완료, 실기 flash 후 integrated/quick/RC soak 확인
- v140 상태: CPU stress screen app lifecycle/renderer를 `a90_app_cpustress.c/h`로 분리하고 helper 포함 ramdisk로 실기 flash, `cpustress 3 2`, integrated/quick soak 확인
- v141 상태: LOG/NETWORK summary renderer를 `a90_app_log.c/h`, `a90_app_network.c/h`로 분리하고 실기 flash, integrated/quick soak 확인
- v142 상태: cutout calibration state/feed/draw API를 `a90_app_displaytest.c/h`로 분리하고 실기 flash, `displaytest safe`, `cutoutcal`, integrated/quick soak 확인
- v143 상태: `waitkey`/`waitgesture`/`inputlayout` command handler를 `a90_input_cmd.c/h`로 분리하고 실기 flash, inputlayout/hide/version, integrated/quick soak 확인
- v144 상태: `inputmonitor` foreground command loop를 `a90_app_inputmon.c/h`로 분리하고 실기 flash, inputmonitor q cancel, integrated/quick soak 확인
- v145 상태: `native_input_cancel_validate.py`로 `waitkey`/`waitgesture`/`inputmonitor` q cancel 자동 검증을 추가하고 실기 flash, cancel harness, integrated/quick soak 확인
- ADB 상태: 보류

다음 실행 후보:

- v134 exposure guardrail과 v135 policy matrix 검증 완료. F021/F030 accepted boundary는 `exposure`/`diag`/`status`에서 관찰 가능해야 유지된다.
- 최신 local targeted rescan은 `docs/security/scans/SECURITY_FRESH_SCAN_F038_F044_2026-05-09.md` 기준 PASS=27/WARN=1/FAIL=0이다. 다음 보안 입력은 Codex Cloud fresh scan 또는 새 network-facing 변경 이후 scan 결과로 삼는다.
- C/B 후보를 버전 분리했다.
  - v136: post-v135 structure audit 완료. 보고서 `docs/reports/NATIVE_INIT_V136_STRUCTURE_AUDIT_2026-05-07.md`.
  - v137: integrated validation matrix 완료. 보고서 `docs/reports/NATIVE_INIT_V137_VALIDATION_MATRIX_2026-05-07.md`.
  - v138: release-candidate extended soak 완료. 보고서 `docs/reports/NATIVE_INIT_V138_EXTENDED_SOAK_2026-05-08.md`.
  - v139: auto-HUD/menu controller cleanup 완료. 보고서 `docs/reports/NATIVE_INIT_V139_AUTOHUD_CONTROLLER_2026-05-08.md`.
  - v140: CPU stress app module split 완료. 보고서 `docs/reports/NATIVE_INIT_V140_CPUSTRESS_APP_2026-05-08.md`.
  - v141: LOG/NETWORK app renderer split 완료. 보고서 `docs/reports/NATIVE_INIT_V141_LOG_NETWORK_APP_2026-05-08.md`.
  - v142: cutout calibration app API split 완료. 보고서 `docs/reports/NATIVE_INIT_V142_CUTOUT_APP_2026-05-08.md`.
  - v143: input command handler API split 완료. 보고서 `docs/reports/NATIVE_INIT_V143_INPUT_COMMAND_2026-05-08.md`.
  - v144: inputmonitor foreground app API split 완료. 보고서 `docs/reports/NATIVE_INIT_V144_INPUTMON_APP_2026-05-08.md`.
  - v145: input cancel validation harness 완료. 보고서 `docs/reports/NATIVE_INIT_V145_INPUT_CANCEL_VALIDATION_2026-05-08.md`.
- network-facing 기능 확장은 v145 통합 검증 gate와 local security rescan이 green인 상태에서만 다시 판단한다.
- post-v145 다음 후보는 fresh Codex Cloud scan follow-up, network-facing 판단, 또는 남은 UI/app renderer split 중에서 다시 선정한다.

상세 상태 문서:

- `docs/reports/NATIVE_INIT_V82_LOG_TIMELINE_2026-04-29.md`
- `docs/reports/NATIVE_INIT_V81_CONFIG_UTIL_2026-04-29.md`
- `docs/reports/NATIVE_INIT_V80_SOURCE_MODULES_2026-04-29.md`
- `docs/reports/NATIVE_INIT_V79_BOOT_STORAGE_2026-04-29.md`
- `docs/reports/NATIVE_INIT_V78_SD_WORKSPACE_2026-04-29.md`
- `docs/reports/NATIVE_INIT_V77_DISPLAY_TEST_PAGES_2026-04-27.md`
- `docs/reports/NATIVE_INIT_V76_AT_FRAGMENT_FILTER_2026-04-27.md`
- `docs/reports/NATIVE_INIT_V75_QUIET_IDLE_REATTACH_2026-04-27.md`
- `docs/reports/NATIVE_INIT_V74_CMDV1X_ARG_ENCODING_2026-04-27.md`
- `docs/reports/NATIVE_INIT_V73_CMDV1_PROTOCOL_2026-04-27.md`
- `docs/reports/NATIVE_INIT_V45_RUN_LOG_2026-04-25.md`
- `docs/reports/NATIVE_INIT_STORAGE_MAP_2026-04-25.md`
- `docs/reports/NATIVE_INIT_V47_SCREEN_MENU_2026-04-25.md`
- `docs/reports/NATIVE_INIT_V48_USB_REATTACH_NCM_2026-04-25.md`
- `docs/reports/NATIVE_INIT_V53_MENU_BUSY_2026-04-25.md`
- `docs/reports/NATIVE_INIT_V54_NCM_LINK_2026-04-25.md`
- `docs/reports/NATIVE_INIT_V55_NCM_OPS_2026-04-25.md`
- `docs/reports/NATIVE_INIT_V56_TCPCTL_2026-04-26.md`
- `docs/reports/NATIVE_INIT_V57_TCPCTL_HOST_WRAPPER_2026-04-26.md`
- `docs/reports/NATIVE_INIT_V58_TCPCTL_SOAK_2026-04-26.md`
- `docs/reports/NATIVE_INIT_V59_AT_NOISE_2026-04-26.md`
- `docs/reports/NATIVE_INIT_V60_NETSERVICE_2026-04-26.md`
- `docs/reports/NATIVE_INIT_V60_RECONNECT_2026-04-26.md`
- `docs/reports/NATIVE_INIT_V61_CPU_GPU_USAGE_2026-04-26.md`
- `docs/reports/NATIVE_INIT_V62_CPUSTRESS_2026-04-26.md`
- `docs/reports/NATIVE_INIT_USB_GADGET_MAP_2026-04-25.md`
- `docs/reports/NATIVE_INIT_USERLAND_CANDIDATES_2026-04-25.md`
- `docs/reports/NATIVE_INIT_V44_HUD_BOOT_2026-04-25.md`
- `docs/reports/NATIVE_INIT_V43_TIMELINE_2026-04-25.md`
- `docs/reports/NATIVE_INIT_V42_CANCEL_2026-04-25.md`
- `docs/reports/NATIVE_INIT_V41_LOGGING_2026-04-25.md`
- `docs/reports/NATIVE_INIT_V40_BUILD_2026-04-25.md`
- `docs/reports/NATIVE_INIT_V39_STATUS_2026-04-25.md`

---

## P0. 운영 안정성

### 1. Shell return code 정밀화

목표:

- `[done]`이 단순히 command dispatch 완료가 아니라 실제 성공에 가깝게 보이도록 한다.
- 실패한 내부 syscall, mount, file open, ioctl, exec 결과를 command result에 반영한다.

현재 상태:

- `init_v40`에서 1차 구현 및 실기 검증 완료
- 상세 기록: `docs/reports/NATIVE_INIT_V40_BUILD_2026-04-25.md`
- `/cache/native-init.log`는 `init_v41`에서 구현 및 실기 검증 완료

대상:

- display 명령
- mount 명령
- file 명령
- input 명령
- process 실행 명령

작업:

- legacy `cmd_*` 함수 중 `void` 계열을 `int` 반환으로 단계 전환
- 실패 시 `errno` 보존
- `last`가 실제 실패 원인을 더 잘 보여주도록 정리
- unknown command, usage error, syscall error를 구분

검증:

- 존재하지 않는 파일 `cat`
- 잘못된 mount source
- 잘못된 display color
- 없는 executable `run`
- 정상 명령과 실패 명령의 `[done]`/`[err]` 차이 확인

### 2. 파일 로그 추가

목표:

- serial이 끊기거나 화면이 멈춘 것처럼 보여도 부팅 진행과 명령 결과를 나중에 확인한다.

우선 저장 위치:

- 1순위: `/cache/native-init.log`
- 2순위: `/tmp/native-init.log`

기록 항목:

- boot step
- version
- mount 결과
- display init 결과
- serial attach 결과
- command start/end
- result code
- `errno`
- duration

주의:

- `/cache` mount 실패 시 `/tmp`로 fallback
- 로그 파일이 너무 커지지 않도록 단순 rotation 또는 truncate 정책 필요
- `/data`, `/efs`, modem 관련 영역은 로그 대상으로 쓰지 않음

현재 상태:

- `init_v41`에서 구현 및 실기 검증 완료
- 상세 기록: `docs/reports/NATIVE_INIT_V41_LOGGING_2026-04-25.md`
- `logpath`, `logcat` 명령 추가
- `/sys/class/block/<name>/dev` 기반 동적 block node 생성으로 `sda28`, `sda31` major/minor 변동 대응
- recovery 왕복 후 로그 보존 재확인은 별도 항목으로 남김

검증:

- 부팅 후 `cat /cache/native-init.log`
- 고의 실패 명령 실행 후 로그에 실패 원인 기록 여부 확인
- recovery 재부팅 후 로그 보존 여부 확인

### 3. Blocking command 취소 정책 통일

목표:

- 오래 기다리는 명령에서 shell을 잃지 않도록 한다.

대상:

- `watchhud`
- `waitkey`
- `readinput`
- `blindmenu`
- `run`

정책:

- `q`: 정상 취소
- `Ctrl-C`: 강제 취소
- timeout 옵션: 선택적 지원

현재 상태:

- `init_v42`에서 공통 cancel helper 구현 및 실기 검증 완료
- 상세 기록: `docs/reports/NATIVE_INIT_V42_CANCEL_2026-04-25.md`
- `q`/`Ctrl-C`는 `-ECANCELED` (`errno=125`)로 `last`와 log에 남김
- 실기 검증 완료:
  - `waitkey`
  - `readinput`
  - `watchhud`
  - `blindmenu`
- `run`/`runandroid` cancelable child wait는 구현됐지만, 안전한 long-running static test binary가 없어 실기 cancel은 보류

검증:

- 각 blocking 명령에서 `q`로 prompt 복귀 — 부분 완료
- `Ctrl-C` 입력 후 prompt 복귀 — `waitkey` 완료
- 취소 후 `status`, `last`, `help`가 정상 동작 — 완료

---

## P1. 필요한 역추적 목록

### 1. Boot readiness timeline

목표:

- native init 기준으로 커널 리소스가 언제 준비되는지 단계표를 만든다.

현재 상태:

- `init_v43`에서 자동 기록 및 실기 검증 완료
- 상세 기록: `docs/reports/NATIVE_INIT_V43_TIMELINE_2026-04-25.md`
- `timeline` shell 명령 추가
- `/cache` mount 전 초기 timeline은 `/cache` 선택 후 log에 replay

확인 항목:

- `/proc` mount 시점
- `/sys` mount 시점
- `/dev` 또는 수동 device node 생성 시점
- `/cache` mount 시점
- USB gadget configfs 준비 시점
- `/dev/ttyGS0` attach 시점
- DRM/KMS open 가능 시점
- input event node 준비 시점
- power/thermal sysfs 준비 시점

출력 형태:

- boot log
- `status`
- 별도 report 문서

### 2. Display pipeline

목표:

- 현재 HUD 출력이 왜 안정적으로 보이는지, 어떤 부분이 아직 불안정한지 분리한다.

확인 항목:

- DRM card 번호
- connector id
- encoder/crtc id
- mode 정보
- dumb framebuffer 생성/매핑
- `SETCRTC` 성공 조건
- page flip 실패 원인
- backlight sysfs 경로
- blank/unblank 경로
- 화면 회전/좌표계
- punch-hole/cutout 안전 영역

참고 후보:

- TWRP recovery ramdisk의 display 초기화 방식
- kernel DRM sysfs
- 기존 `kmsprobe`, `drminfo`, `fbinfo` 출력

검증:

- custom boot splash
- debug TEST pattern
- HUD
- 단색 출력
- 작은 글자 출력
- 화면 꺼짐/켜짐
- 밝기 변경

### 3. Input/event map

목표:

- 물리 버튼과 event node 관계를 고정한다.

현재 확인:

- `event0`: `qpnp_pon`, POWER/VOLDOWN
- `event3`: `gpio_keys`, VOLUP

추가 확인:

- long press 이벤트
- key release 이벤트
- repeat 이벤트
- recovery/TWRP에서 같은 event map 유지 여부
- 터치 event node 존재 여부

검증:

- `inputinfo`
- `inputcaps`
- `readinput`
- `waitkey`
- 화면 메뉴에서 선택 이동/확정

### 4. Power, battery, thermal units

목표:

- HUD에 표시되는 전력/온도/배터리 값의 단위와 신뢰도를 확정한다.

확인 항목:

- battery capacity
- battery status
- battery temp unit
- voltage unit
- `power_now`
- `power_avg`
- CPU thermal zone
- GPU thermal zone
- throttling 관련 sysfs

주의:

- Samsung vendor sysfs는 표준 단위와 다를 수 있다.
- 전력 표시는 확정 전까지 `W?`처럼 불확실성을 표시한다.

검증:

- 충전기 연결/해제 전후 값 변화
- 화면 켜짐/꺼짐 전후 값 변화
- HUD refresh 반영 여부

### 5. Safe storage map

목표:

- native init에서 안전하게 읽고 쓸 수 있는 저장소를 구분한다.

현재 상태:

- `docs/reports/NATIVE_INIT_STORAGE_MAP_2026-04-25.md`로 v46 기준 1차 문서화 완료
- `/cache`는 persistent safe write로 사용
- `userdata`는 대용량 후보지만 Android FBE/user data와 엮여 있어 별도 의사결정 전까지 보류
- `efs`, `sec_efs`, modem, persist, key/security, vbmeta, bootloader 계열은 do-not-touch

후보:

- `/cache`
- `/tmp`
- `/mnt/system` read-only
- `/metadata` read-only 탐색 후보

금지 또는 주의:

- `/efs`
- modem 관련 파티션
- RPMB/keymaster/keystore 관련 영역
- `/data` 암호화 영역
- bootloader/vbmeta 계열

검증:

- `/proc/partitions`
- `/proc/mounts`
- `stat`
- `mountsystem ro`
- `/cache` write/read/sync

### 6. USB gadget map

목표:

- 현재 안정적인 ACM serial을 기준으로, 추후 네트워크/ADB 가능성을 판단할 자료를 만든다.

현재 상태:

- `docs/reports/NATIVE_INIT_USB_GADGET_MAP_2026-04-25.md`로 1차 문서화 완료
- 현재 active gadget은 ACM-only
- host descriptor는 CDC ACM control/data 2-interface만 노출
- ADB는 FunctionFS `ep0 only`/`adbd` zombie 문제가 blocker
- USB networking은 ACM rescue channel 유지 후 두 번째 function으로 probe 예정

확인 항목:

- configfs gadget path
- UDC name
- ACM function 설정
- host enumeration 상태
- FunctionFS ADB endpoint 생성 실패 조건
- RNDIS/NCM function 사용 가능성

현재 판단:

- ADB보다 ACM serial이 안정적이다.
- 추후 네트워크가 필요하면 ADB 복구보다 RNDIS/NCM + 작은 server가 더 현실적일 수 있다.

---

## P1. Shell 기능 개선 목록

### 1. 명령 help 정리

목표:

- `help` 출력이 너무 길어져도 읽을 수 있게 그룹화한다.

그룹 후보:

- core
- files
- mounts
- display
- input
- sensors
- process
- power
- debug

검증:

- `help`
- `help display`
- `help input`

### 2. 명령 parser 개선

목표:

- 실험에 필요한 최소 수준의 인자 처리를 안정화한다.

후보:

- quote 처리
- escaped space
- empty argument
- usage error 메시지 통일

비목표:

- full POSIX shell 구현
- pipe/redirection
- shell script language

### 3. File utility 보강

목표:

- device에서 직접 정보를 수집하기 쉽게 한다.

후보 명령:

- `readlink`
- `hexdump`
- `grep` 또는 단순 `findtext`
- `find`
- `tree` 제한 버전
- `tail`
- `log`

주의:

- 복잡한 BusyBox 재구현으로 흐르지 않게 한다.
- 필요한 것부터 작게 추가한다.

### 4. Process 실행 안정화

목표:

- 외부 static binary를 실험적으로 실행할 수 있게 한다.

작업:

- `run` timeout
- exit status 표시
- signal 종료 표시
- stdout/stderr 처리 정책
- child zombie 회수

검증:

- 정상 static binary
- 없는 binary
- crash binary
- 장시간 sleep binary

---

## P1. 화면/HUD/Menu

### 1. HUD 정보 레이아웃 안정화

목표:

- punch-hole, edge clipping, 색상 대비 문제를 피한다.

작업:

- safe margin 상수화
- font scale 정책 정리
- 상단 상태 위치 고정
- 하단 help text clipping 방지
- black-on-black 방지

검증:

- 검은 배경
- 밝은 배경
- 충전기 연결/해제
- 화면 회전 없이 1080x2400 기준 유지

### 2. Boot screen sequence

목표:

- 부팅 후 사용자가 “멈춘 것인지 진행 중인지” 알 수 있게 한다.

현재:

- v70 custom boot splash 약 2초
- HUD/menu 자동 전환

추가 후보:

- boot step progress text
- serial ready 표시
- cache/log ready 표시
- error 발생 시 붉은 상태줄

### 3. On-screen menu

목표:

- serial 없이도 최소 조작을 가능하게 한다.

현재 상태:

- `init_v47`에서 `menu`/`screenmenu` 화면 메뉴 초안 구현
- `RESUME`, `STATUS`, `LOG`, `RECOVERY`, `REBOOT`, `POWEROFF` 항목 제공
- q cancel 후 autohud 복구 확인
- 실제 버튼 이동/선택과 위험 동작은 수동 검증 대기

후보 메뉴:

- status
- refresh
- mount system ro
- reboot recovery
- poweroff
- show log
- start serial hint

입력:

- VOLUP: move up
- VOLDOWN: move down
- POWER: select

검증:

- 각 버튼 1회 입력
- 길게 누르기
- prompt와 menu mode 전환

---

## P2. 네트워크와 외부 도구

### 1. BusyBox/toolbox류 도구 검토

목표:

- 모든 유틸을 직접 구현하지 않고, 필요한 static userland를 가져올 수 있는지 판단한다.

확인:

- static ARM64 BusyBox 실행 가능 여부
- 라이선스/배포 방식
- `/cache/bin` 또는 ramdisk 탑재 방식
- `PATH` 정책

주의:

- core shell 안정화 전에는 도구 추가가 문제를 가릴 수 있다.

현재 상태:

- V49로 승격해 진행 중이다.
- 후보 리포트: `docs/reports/NATIVE_INIT_USERLAND_CANDIDATES_2026-04-25.md`
- 1차 방향은 boot ramdisk 포함이 아니라 `/cache/bin`에 static ARM64 multi-call binary를 올리고 `run /cache/bin/<tool> <applet>` 형태로 명시 실행하는 것이다.
- host build prerequisite 설치 후 `scripts/revalidation/build_static_toybox.sh`로 `toybox 0.8.13` static ARM64 빌드가 성공했다.
- 산출물은 `external_tools/userland/bin/toybox-aarch64-static-0.8.13`이며 SHA256은 `92a0917579c76fec965578ac242afbf7dedc4428297fb90f4c9caf7f538a718c`다.
- TWRP ADB로 `/cache/bin/toybox` 배치 후 native init에서 주요 applet 실기 실행을 확인했다.
- `ifconfig -a`, `route -n`, `netcat --help`가 동작하므로 USB networking probe의 userland 기반은 확보됐다.

### 2. 네트워크

목표:

- 장기적으로 일반 Linux 서버처럼 접근할 수 있는 경로를 검토한다.

후보:

- USB RNDIS/NCM
- static telnetd
- static dropbear SSH
- host bridge 기반 custom RPC

현 판단:

- 당장은 serial bridge가 가장 단순하고 안정적이다.
- SSH/server화는 log, process, storage가 안정화된 뒤 검토한다.

### 3. ADB 재검토

목표:

- 현재 보류한 ADB를 나중에 다시 판단할 근거를 남긴다.

현재 문제:

- `adbd` zombie
- FunctionFS `ep0`만 생성
- `ep1`/`ep2` 미생성
- Android property service, SELinux context, bionic/apex 환경 부재

재검토 조건:

- FunctionFS endpoint 생성 흐름 이해
- 필요한 property/socket/context 최소셋 확인
- ADB가 serial/RNDIS보다 가치가 큰지 재판단

---

## 당장 다음 실행 순서

상세 실행 큐는 `docs/plans/NATIVE_INIT_TASK_QUEUE_2026-04-25.md`를 따른다.

1. v185 Communication Broker Protocol Plan
   - 계획: `docs/plans/NATIVE_INIT_V185_COMMUNICATION_BROKER_PLAN_2026-05-11.md`
   - 최신 증거: `docs/reports/NATIVE_INIT_V184_24H_SERVERIZATION_READINESS_2026-05-11.md` PASS
   - 선택 이유: Wi-Fi/NCM 노출을 넓히기 전에 raw ACM bridge를 직접 여러 도구가 공유하는 구조를 정리한다
   - v185는 실기기 플래시 버전이 아니라 v159 실기기 위에서 수행할 host protocol/broker 설계 cycle이다
2. v182-v184 Mixed Soak / Serverization Gate
   - v182 failure classifier는 완료됐다
   - v183 8h pilot은 PASS했다
   - v184 24h+ readiness gate는 PASS했다
   - Wi-Fi baseline refresh와 exposure hardening은 post-v184 roadmap에서 우선순위를 다시 정한다
3. v186+ Broker Skeleton / Harness Integration
   - `A90B1` host-local broker skeleton은 `scripts/revalidation/a90_broker.py`로 시작했다
   - live ACM bridge smoke, concurrent read-only client, rebind block 검증은 PASS했다
   - `DeviceClient`와 `native_test_supervisor.py`의 broker backend 연결을 시작했다
   - broker-backed supervisor smoke/observe live 검증은 PASS했다
   - mixed-soak dry-run도 PASS했다
   - v188은 broker audit/reporting으로 시작했다
   - live ACM broker audit report와 broker-backed supervisor smoke audit report는 PASS했다
   - v189 broker concurrent smoke script는 fake/live ACM 모두 PASS했다
   - v190 broker mixed-soak gate는 live ACM에서 PASS했다
   - v191 NCM/tcpctl broker backend는 NCM `run` path와 ACM fallback 모두 PASS했다
   - v192 broker failure/recovery tests는 fake/live 모두 PASS했다
   - 다음은 v193 후보 재선정 또는 broker/auth hardening follow-up이다
4. v193+ Broker/Auth Hardening Follow-up
   - v193 broker/auth hardening은 PASS했다: no-auth explicit allow gate, token validation, auth-failed classification, token redaction
   - v194 NCM/tcpctl listener lifecycle automation은 dry-run PASS했다
   - v195 broker-backed soak suite는 dry-run PASS했다
   - v196 fresh security scan follow-up workflow는 PASS했다: CSV 2건 indexed, local scan PASS/WARN/FAIL=29/1/0
   - 다음은 post-v196 후보 재선정이다
5. 이후 Wi-Fi Baseline Refresh / Network Exposure Hardening
   - v203 계획서: `docs/plans/NATIVE_INIT_V203_WIFI_BASELINE_REFRESH_PLAN_2026-05-13.md`
   - v203 collector: `scripts/revalidation/wifi_baseline_refresh.py`
   - v203 보고서: `docs/reports/NATIVE_INIT_V203_WIFI_BASELINE_REFRESH_2026-05-13.md`
   - broker/security gate 이후 native/mounted-system Wi-Fi 자료를 read-only로 다시 수집했다
   - v203 상태: PASS, final decision `no-go`
   - v204 계획서: `docs/plans/NATIVE_INIT_V204_ANDROID_TWRP_WIFI_BASELINE_PLAN_2026-05-13.md`
   - v204 collector: `scripts/revalidation/android_twrp_wifi_baseline.py`
   - v204 보고서: `docs/reports/NATIVE_INIT_V204_ANDROID_TWRP_WIFI_BASELINE_2026-05-13.md`
   - v204 상태: TWRP ADB PASS, decision `driver-candidate-found`
   - v204 Android 상태: Android ADB + Magisk root PASS, decision `ready-for-readonly-nl80211-probe-plan`
   - v205 계획서: `docs/plans/NATIVE_INIT_V205_ICNSS_NL80211_READONLY_PLAN_2026-05-13.md`
   - v205 collector: `scripts/revalidation/wifi_icnss_nl80211_probe.py`
   - v205 helper source: `stage3/linux_init/helpers/a90_nl80211_ro.c`
   - v205 보고서: `docs/reports/NATIVE_INIT_V205_ICNSS_NL80211_READONLY_2026-05-13.md`
   - v205 상태: PASS, decision `native-icnss-present-no-wiphy`
   - v206 계획서: `docs/plans/NATIVE_INIT_V206_ANDROID_ICNSS_CNSS_MAP_PLAN_2026-05-13.md`
   - v206 collector: `scripts/revalidation/android_icnss_cnss_map.py`
   - v206 보고서: `docs/reports/NATIVE_INIT_V206_ANDROID_ICNSS_CNSS_MAP_2026-05-13.md`
   - v206 상태: PASS, decision `ready-for-native-preflight-plan`
   - v206 실기: Android ADB/root collector PASS 후 native v159 복구 PASS
   - v207 계획서: `docs/plans/NATIVE_INIT_V207_NATIVE_WIFI_PREFLIGHT_PLAN_2026-05-13.md`
   - v207 collector: `scripts/revalidation/native_wifi_preflight.py`
   - v207 보고서: `docs/reports/NATIVE_INIT_V207_NATIVE_WIFI_PREFLIGHT_2026-05-13.md`
   - v207 상태: PASS, decision `missing-mounted-vendor`
   - v207 실기: native basic control, `mountsystem ro`, ICNSS sysfs PASS; mounted vendor firmware/init path, WLAN netdev/wiphy/rfkill, remote `a90_nl80211_ro`는 absent
   - v208 계획서: `docs/plans/NATIVE_INIT_V208_VENDOR_FIRMWARE_MOUNT_PLAN_2026-05-13.md`
   - v208 collector: `scripts/revalidation/native_vendor_mount_probe.py`
   - v208 보고서: `docs/reports/NATIVE_INIT_V208_VENDOR_FIRMWARE_MOUNT_2026-05-13.md`
   - v208 상태: PASS, decision `vendor-block-candidate-found`
   - v208 실기: native basic control PASS; `sda29` vendor 후보가 `/proc/partitions`와 `/sys/class/block`에 보이나 `/dev/block/sda29`/by-name 노드는 absent, mounted vendor firmware/init path는 absent
   - v209 계획서: `docs/plans/NATIVE_INIT_V209_VENDOR_RO_MOUNT_PROBE_PLAN_2026-05-13.md`
   - v209 collector: `scripts/revalidation/native_vendor_ro_mount_probe.py`
   - v209 보고서: `docs/reports/NATIVE_INIT_V209_VENDOR_RO_MOUNT_PROBE_2026-05-13.md`
   - v209 상태: PASS, decision `vendor-assets-visible`
   - v209 실기: `sda29` 임시 block node + isolated mountpoint + ext4 `ro,noload` mount PASS, cleanup PASS, vendor init/Wi-Fi firmware assets visible
   - v210 계획서: `docs/plans/NATIVE_INIT_V210_VENDOR_WIFI_CNSS_ASSET_CLASSIFIER_PLAN_2026-05-13.md`
   - v210 collector: `scripts/revalidation/native_vendor_asset_classifier.py`
   - v210 보고서: `docs/reports/NATIVE_INIT_V210_VENDOR_WIFI_CNSS_ASSET_CLASSIFIER_2026-05-13.md`
   - v210 상태: PASS, decision `firmware-path-policy-needed`
   - v210 실기: required vendor firmware/init rc/service binaries/VINTF는 native-visible vendor mount에서 확인됐고, `firmware_class.path=/vendor/firmware_mnt/image`가 현재 visible Wi-Fi firmware layout을 가리키지 않는 것이 다음 blocker다
   - v211 계획서: `docs/plans/NATIVE_INIT_V211_FIRMWARE_PATH_POLICY_PLAN_2026-05-13.md`
   - v211 collector: `scripts/revalidation/native_firmware_path_policy_probe.py`
   - v211 보고서: `docs/reports/NATIVE_INIT_V211_FIRMWARE_PATH_POLICY_2026-05-13.md`
   - v211 상태: PASS, decision `sysfs-path-update-needed`
   - v211 실기: isolated `/mnt/vendor/firmware` model과 synthetic `/vendor/firmware_mnt/image` bind model은 likely request names를 모두 resolve하지만, 현재 `/vendor/firmware_mnt/image`는 resolve하지 못한다
   - v212 계획서: `docs/plans/NATIVE_INIT_V212_FIRMWARE_PATH_ROLLBACK_PLAN_2026-05-13.md`
   - v212 collector: `scripts/revalidation/native_firmware_path_apply_probe.py`
   - v212 보고서: `docs/reports/NATIVE_INIT_V212_FIRMWARE_PATH_ROLLBACK_2026-05-13.md`
   - v212 상태: PASS, decision `path-rollback-pass`
   - v212 dry-run 실기: `/mnt/vendor/firmware` likely request paths는 모두 visible, cleanup PASS, `firmware_class.path`는 `/vendor/firmware_mnt/image`로 유지
   - v212 apply 실기: `/cache/bin/a90_fwpathctl` fixed-target helper로 `firmware_class.path=/mnt/vendor/firmware` 적용/readback 후 `/vendor/firmware_mnt/image`로 rollback PASS, leftover mount 없음
   - v213 계획서: `docs/plans/NATIVE_INIT_V213_FIRMWARE_REQUEST_EVIDENCE_PLAN_2026-05-13.md`
   - v213 collector: `scripts/revalidation/native_firmware_request_probe.py`
   - v213 optional helper source: `stage3/linux_init/helpers/a90_icnssctl.c`
   - v213 보고서: `docs/reports/NATIVE_INIT_V213_FIRMWARE_REQUEST_EVIDENCE_2026-05-13.md`
   - v213 상태: PASS, baseline decision `baseline-only`, path-only decision `path-only-pass`
   - v213 실기: read-only ICNSS baseline PASS, `/mnt/vendor/firmware` path apply/readback/rollback PASS, likely request paths visible, leftover mount 없음
   - v213 live constraint: dynamic debug/tracefs firmware events는 absent, ICNSS sysfs node와 driver bind/unbind controls는 present
   - v214 계획서: `docs/plans/NATIVE_INIT_V214_ICNSS_REPROBE_EXECUTION_PLAN_2026-05-13.md`
   - v214 보고서: `docs/reports/NATIVE_INIT_V214_ICNSS_REPROBE_EXECUTION_2026-05-13.md`
   - v214 상태: SAFETY STOP, decision `icnss-rebind-failed`
   - v214 실기: `/cache/bin/a90_icnssctl` 배포 PASS, `/mnt/vendor/firmware` path apply/readback/rollback PASS, ICNSS unbind PASS, ICNSS bind FAIL
   - v214 dmesg: `icnss: Driver is already initialized`, `probe of 18800000.qcom,icnss failed with error -17`
   - v214 recovery: native reboot 후 ICNSS bound 복구 PASS, `firmware_class.path=/vendor/firmware_mnt/image`
   - v215-v225 큰 계획: `docs/plans/NATIVE_INIT_V215_V225_WIFI_BIG_PLAN_2026-05-13.md`
   - v215-v225 상세 로드맵: `docs/plans/NATIVE_INIT_V215_V225_WIFI_LIFECYCLE_ROADMAP_2026-05-13.md`
   - v215-v225 version master plan:
     `docs/plans/NATIVE_INIT_V215_V225_WIFI_VERSION_MASTER_PLAN_2026-05-13.md`
   - v215 계획서: `docs/plans/NATIVE_INIT_V215_ICNSS_CNSS_LIFECYCLE_RESEARCH_PLAN_2026-05-13.md`
   - v215 보고서: `docs/reports/NATIVE_INIT_V215_ICNSS_CNSS_LIFECYCLE_RESEARCH_2026-05-13.md`
   - v215 상태: PASS, decision `lifecycle-map-ready`
   - v215 실기: manifest-only PASS, native bridge read-only PASS, live captures `16/16`
   - v216 계획서: `docs/plans/NATIVE_INIT_V216_ANDROID_SERVICE_REPLAY_MODEL_PLAN_2026-05-13.md`
   - v216 보고서: `docs/reports/NATIVE_INIT_V216_ANDROID_SERVICE_REPLAY_MODEL_2026-05-13.md`
   - v216 상태: PASS, decision `replay-model-ready`
   - v216 결과: `cnss-daemon`, `cnss_diag`, Wi-Fi HAL, `wificond`, `wpa_supplicant`, `hostapd` service graph 작성 완료
   - v217 계획서: `docs/plans/NATIVE_INIT_V217_ICNSS_DEBUG_RECOVERY_INVENTORY_PLAN_2026-05-13.md`
   - v217 보고서: `docs/reports/NATIVE_INIT_V217_ICNSS_DEBUG_RECOVERY_INVENTORY_2026-05-13.md`
   - v217 상태: PASS, decision `state-only-inventory`
   - v217 결과: native read-only captures `11/11`, controls `168`, dangerous controls `bind`/`unbind`/`driver_override`
   - v218 계획서: `docs/plans/NATIVE_INIT_V218_CNSS_DAEMON_DRYRUN_FEASIBILITY_PLAN_2026-05-13.md`
   - v218 보고서: `docs/reports/NATIVE_INIT_V218_CNSS_DAEMON_DRYRUN_FEASIBILITY_2026-05-13.md`
   - v218 상태: PASS, decision `daemon-dryrun-partial`
   - v218 결과: `cnss-daemon`/`cnss_diag` binary visibility는 v210 기준 확인, ELF/library inspection은 host vendor root 부재로 incomplete
   - v219 계획서: `docs/plans/NATIVE_INIT_V219_NATIVE_ANDROID_ENV_SHIM_PLAN_2026-05-13.md`
   - v219 보고서: `docs/reports/NATIVE_INIT_V219_NATIVE_ANDROID_ENV_SHIM_2026-05-13.md`
   - v219 상태: PASS, decision `shim-plan-partial`
   - v219 결과: bounded shim matrix 생성 완료, property/QMI/recovery blocker와 host ELF/library evidence gap은 유지
   - v220 계획서: `docs/plans/NATIVE_INIT_V220_WIFI_PREFLIGHT_GATE_V2_PLAN_2026-05-13.md`
   - v220 보고서: `docs/reports/NATIVE_INIT_V220_WIFI_PREFLIGHT_GATE_V2_2026-05-13.md`
   - v220 상태: PASS, decision `no-go`
   - v220 결과: gate counts `pass=3`, `warn=1`, `fail=0`, `blocked=3`
   - v220 blocked: `icnss_recovery`, `shim_policy`, `security_exposure`
   - 다음은 v221 host vendor ELF/library evidence closure와 recovery/security prerequisite closure다. daemon 실행, generic sysfs unbind/bind, Wi-Fi scan/connect는 blocked
   - v221 계획서: `docs/plans/NATIVE_INIT_V221_HOST_VENDOR_ELF_LIBRARY_EVIDENCE_PLAN_2026-05-13.md`
   - v221 보고서: `docs/reports/NATIVE_INIT_V221_HOST_VENDOR_ELF_LIBRARY_EVIDENCE_2026-05-13.md`
   - v221 상태: PASS, decision `vendor-root-required`
   - v221 결과: host-visible vendor root가 필요하며 required paths는 `<vendor-root>/bin/cnss-daemon`, `<vendor-root>/bin/cnss_diag`
   - v222 계획서: `docs/plans/NATIVE_INIT_V222_VENDOR_ROOT_EVIDENCE_EXPORT_PLAN_2026-05-13.md`
   - v222 보고서: `docs/reports/NATIVE_INIT_V222_VENDOR_ROOT_EVIDENCE_EXPORT_2026-05-13.md`
   - v222 상태: PASS, decision `export-source-required`
   - v222 결과: `scripts/revalidation/wifi_vendor_root_evidence_export.py` 구현 완료, source vendor root 미제공 상태에서는 private/no-follow export plan과 required paths만 생성
   - v223 계획서: `docs/plans/NATIVE_INIT_V223_RECOVERY_ROLLBACK_POLICY_PLAN_2026-05-13.md`
   - v223 보고서: `docs/reports/NATIVE_INIT_V223_RECOVERY_ROLLBACK_POLICY_2026-05-13.md`
   - v223 상태: PASS, decision `reboot-recovery-accepted`
   - v223 결과: reboot만 accepted recovery primitive로 고정, generic ICNSS unbind/bind와 unreviewed sysfs/debugfs/configfs writes는 denied
   - v224 계획서: `docs/plans/NATIVE_INIT_V224_ANDROID_ENV_SHIM_DRYRUN_MATERIALIZATION_PLAN_2026-05-13.md`
   - v224 보고서: `docs/reports/NATIVE_INIT_V224_ANDROID_ENV_SHIM_MATERIALIZE_2026-05-13.md`
   - v224 상태: PASS, decision `shim-source-required`
   - v224 결과: host-side shim dry-run artifacts 생성 완료, v219 blocked rows 유지, v223 policy hard dependency 기록, source vendor root blocker 유지
   - v225 계획서: `docs/plans/NATIVE_INIT_V225_WIFI_EXPOSURE_SECURITY_GATE_V3_PLAN_2026-05-13.md`
   - v225 보고서: `docs/reports/NATIVE_INIT_V225_WIFI_EXPOSURE_SECURITY_GATE_V3_2026-05-13.md`
   - v225 상태: PASS, decision `still-no-go`
   - v225 결과: root-control exposure/credential policy는 gate v3에 반영됐지만 `vendor_evidence`, `shim_materialization` blocker가 남아 active Wi-Fi는 계속 blocked
   - v226 계획서: `docs/plans/NATIVE_INIT_V226_VENDOR_ROOT_LIVE_EXPORT_PLAN_2026-05-14.md`
   - v226 보고서: `docs/reports/NATIVE_INIT_V226_VENDOR_ROOT_LIVE_EXPORT_2026-05-14.md`
   - v226 상태: PASS, decision `vendor-source-exported`
   - v226 결과: live native `sda29` ro,noload vendor export 완료, v222는 `vendor-root-ready`, v224는 `shim-dryrun-ready`로 전환
   - v227 계획서: `docs/plans/NATIVE_INIT_V227_ANDROID_CORE_SYSTEM_LIBRARY_EVIDENCE_PLAN_2026-05-14.md`
   - v227 보고서: `docs/reports/NATIVE_INIT_V227_ANDROID_CORE_SYSTEM_LIBRARY_EVIDENCE_2026-05-14.md`
   - v227 상태: PASS, decision `system-root-ready`
   - v227 결과: live native `/mnt/system/system/lib*`에서 Android core/system libraries export 완료
   - 재검증 결과: v221 `elf-evidence-ready`, v224 `shim-dryrun-ready`, v225 `cnss-start-plan-approved`
   - v228 계획서: `docs/plans/NATIVE_INIT_V228_CONTROLLED_CNSS_START_PLAN_2026-05-14.md`
   - v228 보고서: `docs/reports/NATIVE_INIT_V228_CONTROLLED_CNSS_START_PLAN_2026-05-14.md`
   - v228 상태: PASS, decision `cnss-start-plan-ready`
   - v228 결과: daemon 실행 없이 command allowlist, start plan, rollback policy, exposure boundary 산출
   - v229 계획서: `docs/plans/NATIVE_INIT_V229_CONTROLLED_CNSS_START_RUNNER_PLAN_2026-05-14.md`
   - v229 보고서: `docs/reports/NATIVE_INIT_V229_CONTROLLED_CNSS_START_RUNNER_2026-05-15.md`
   - v229 구현: `scripts/revalidation/wifi_cnss_start_experiment.py`
   - v229 상태: dry-run PASS + live preflight PASS/safe-stop, decision `start-only-runtime-gap`
   - v229 목표: opt-in controlled CNSS start-only runner. 기본은 plan/preflight/dry-run이며 live daemon start는 `--allow-daemon-start --assume-yes` 명시 전까지 금지
   - v229 preflight 결과: `/mnt/system/system/bin/linker64`는 보이나 `/mnt/system/vendor/bin/cnss-daemon`과 global `/system/bin/linker64`/`/system/vendor/bin/cnss-daemon` namespace가 없어 daemon 실행 전 중단
   - v230 계획서: `docs/plans/NATIVE_INIT_V230_ANDROID_EXEC_NAMESPACE_PLAN_2026-05-15.md`
   - v230 host tool: `scripts/revalidation/wifi_android_exec_namespace_probe.py`
   - v230 보고서: `docs/reports/NATIVE_INIT_V230_ANDROID_EXEC_NAMESPACE_PROBE_2026-05-15.md`
   - v230 live inventory PASS, decision `android-exec-namespace-runtime-gap`
   - 확인: `/mnt/system/system/vendor -> /vendor`, vendor source `needs-remount`, APEX runtime available
   - 남은 blocker: `linkerconfig-need-unproven`
   - v231 계획서: `docs/plans/NATIVE_INIT_V231_LINKERCONFIG_NAMESPACE_HELPER_PLAN_2026-05-15.md`
   - v231 보고서: `docs/reports/NATIVE_INIT_V231_LINKERCONFIG_NAMESPACE_HELPER_2026-05-15.md`
   - v231 상태: private mount namespace helper와 host probe 경로 구현 완료, static ARM64 build PASS, NCM deploy PASS
   - 실기 probe: helper setup은 `namespace-ready`, vendor `sda29`는 private temp block node로 ro,noload mount, `/linkerconfig`는 `/mnt/system/linkerconfig` read-only bind
   - 결과: `/system/bin/linker64 --list /vendor/bin/cnss-daemon`가 stdout/stderr 없이 `SIGSEGV(11)`로 종료, decision `android-namespace-manual-review-required`
   - 확인: `/mnt/system/linkerconfig`는 empty, `/mnt/system/system/etc/ld.config*.txt`는 absent, linker 바이너리에는 `--list`와 `/linkerconfig/ld.config.txt` 참조가 존재
   - v232 상태: private-only linkerconfig materialization 구현/실기 실행 완료
   - v232 계획서: `docs/plans/NATIVE_INIT_V232_LINKERCONFIG_MATERIALIZATION_PLAN_2026-05-15.md`
   - v232 보고서: `docs/reports/NATIVE_INIT_V232_LINKERCONFIG_MATERIALIZATION_2026-05-15.md`
   - v232 결과: `minimal-vendor` private linkerconfig에서도 `/system/bin/linker64 --list /vendor/bin/cnss-daemon`가 stdout/stderr 없이 `SIGSEGV(11)`로 종료했다
   - v233 보고서: `docs/reports/NATIVE_INIT_V233_REAL_LINKERCONFIG_COPY_REAL_2026-05-15.md`
   - v233 상태: stock Android boot에서 real `/linkerconfig/ld.config.txt`를 read-only capture했고, native v159 복구 후 `copy-real` probe까지 실행했다
   - v233 결과: real Android generated linkerconfig에서도 `/system/bin/linker64 --list /vendor/bin/cnss-daemon`가 stdout/stderr 없이 `SIGSEGV(11)`로 종료했다
   - v234 계획서: `docs/plans/NATIVE_INIT_V234_LINKER_CRASH_CONTEXT_PLAN_2026-05-15.md`
   - v234 보고서: `docs/reports/NATIVE_INIT_V234_LINKER_CRASH_CONTEXT_2026-05-15.md`
   - v234 결과: `system-toybox`, `system-sh`, `linker64-self`, `cnss-daemon` 모두 `linker64 --list`에서 `SIGSEGV(11)`로 종료했다
   - v234 decision: `android-linker-crash-generic`; 문제는 `cnss-daemon` target-specific이 아니라 generic Android linker invocation/private namespace context 쪽이다
   - v235 계획서: `docs/plans/NATIVE_INIT_V235_LINKER_INVOCATION_PATH_PLAN_2026-05-15.md`
   - v235 보고서: `docs/reports/NATIVE_INIT_V235_LINKER_INVOCATION_PATH_2026-05-18.md`
   - v235 결과: `/system/bin/linker64`와 direct `/apex/com.android.runtime/bin/linker64` 모두 20-case matrix에서 child `SIGSEGV(11)`, stdout/stderr empty
   - v235 decision: `android-linker-crash-path-independent`; symlink path 문제가 아니라 Android linker process context/namespace crash 쪽이다
   - v236 계획서: `docs/plans/NATIVE_INIT_V236_LINKER_CRASH_CAPTURE_PLAN_2026-05-18.md`
   - v236 보고서: `docs/reports/NATIVE_INIT_V236_LINKER_CRASH_CAPTURE_2026-05-18.md`
   - v236 결과: 6-case matrix 모두 `SIGSEGV(11)` 재현, ptrace-lite exec/crash context capture 성공
   - v236 crash pattern: fault addr `0xa1`, linker64 PC file offset `0x1002f4`, regset `272` bytes
   - v237 계획서: `docs/plans/NATIVE_INIT_V237_LINKER_OFFSET_SYMBOLIZATION_PLAN_2026-05-18.md`
   - v237 host tool: `scripts/revalidation/wifi_linker_offset_symbolize.py`
   - v237 결과: `/mnt/system/system/apex/com.android.runtime/bin/linker64` export + readelf/objdump 분석 PASS, decision `linker-offset-symbolized`
   - v237 symbolization: offset `0x1002f4` -> `.text` / `__dl__ZL13__early_aborti+0x14` / `str wzr, [x8]`, linker64 SHA-256 `ebd1db608558ccb01f851a4988abea2f2dd8844b7bc09e1847ebaf05e36a421d`
   - v237 해석: crash는 임의 미상 코드가 아니라 bionic linker의 intentional early-abort trap이며, 다음은 `__early_abort` call-site/abort-code 분석
   - v238 계획서: `docs/plans/NATIVE_INIT_V238_LINKER_EARLY_ABORT_MAP_PLAN_2026-05-18.md`
   - v238 host tool: `scripts/revalidation/wifi_linker_early_abort_map.py`
   - v238 보고서: `docs/reports/NATIVE_INIT_V238_LINKER_EARLY_ABORT_MAP_2026-05-18.md`
   - v238 결과: decision `linker-early-abort-dev-null-open-failed`, abort code `0xa1` maps to call site `0x1000b8` in `__dl__Z21__libc_init_AT_SECUREPPc+0xa0`
   - v238 해석: private Android execution namespace 안에 bionic이 기대하는 `/dev/null` 또는 `/sys/fs/selinux/null` context가 없어서 `linker64 --list`도 early abort한다
   - 다음 blocker closure: v239에서 private namespace root에 최소 `/dev/null` materialization/bind 후 linker list matrix 재실행
   - v239 계획서: `docs/plans/NATIVE_INIT_V239_PRIVATE_DEVNULL_PROBE_PLAN_2026-05-18.md`
   - v239 보고서: `docs/reports/NATIVE_INIT_V239_PRIVATE_DEVNULL_PROBE_2026-05-18.md`
   - v239 결과: `a90_android_execns_probe v6` + `--null-device-mode dev-null` 실기 PASS, decision `android-linker-devnull-early-abort-cleared`
   - v239 해석: `/dev/null` char device `1:3` materialization만으로 `0xa1` early abort와 `SIGSEGV(11)`가 6-case matrix에서 사라졌다
   - 새 blocker: `cnss-daemon` linker-list가 정상 stderr로 `library "libcutils.so" not found`를 보고한다; 다음은 linker namespace/dependency search path 분류
   - v240 계획서: `docs/plans/NATIVE_INIT_V240_LINKER_NAMESPACE_GAP_PLAN_2026-05-18.md`
   - v240 host tool: `scripts/revalidation/wifi_linker_namespace_gap_probe.py`
   - v240 보고서: `docs/reports/NATIVE_INIT_V240_LINKER_NAMESPACE_GAP_2026-05-18.md`
   - v240 결과: decision `android-linker-vndk-apex-version-alias-gap`
   - v240 해석: real linkerconfig는 vendor target의 `libcutils.so`를 `vndk` linked namespace로 허용하지만, path는 `/apex/com.android.vndk.v30`를 가리키고 live system image는 `/apex/com.android.vndk.current`만 노출한다
   - 다음 blocker closure: v241에서 helper private namespace 안에서만 `com.android.vndk.v30 -> com.android.vndk.current` alias/materialization을 테스트한다
   - v241 계획서: `docs/plans/NATIVE_INIT_V241_VNDK_APEX_ALIAS_PROBE_PLAN_2026-05-18.md`
   - v241 보고서: `docs/reports/NATIVE_INIT_V241_VNDK_APEX_ALIAS_PROBE_2026-05-18.md`
   - v241 결과: decision `android-linker-vndk-apex-alias-cnss-list-pass`
   - v241 해석: private `/apex` symlink farm + `com.android.vndk.v30 -> /system/apex/com.android.vndk.current` alias로 `cnss-daemon` linker-list dependency graph가 양쪽 linker path에서 exit `0`으로 완료됐다
   - v242 계획서: `docs/plans/NATIVE_INIT_V242_CNSS_RUNTIME_REQUIREMENT_INVENTORY_PLAN_2026-05-18.md`
   - v242 보고서: `docs/reports/NATIVE_INIT_V242_CNSS_RUNTIME_REQUIREMENT_INVENTORY_2026-05-18.md`
   - v242 결과: decision `cnss-runtime-inventory-ready-for-launcher-contract-plan`
   - v242 해석: linker prerequisite은 닫혔지만 `cnss-daemon`은 user/group/capability, property socket, SELinux service context, diag/QRTR device, private path alias 계약이 필요하다
   - v243 계획서: `docs/plans/NATIVE_INIT_V243_CNSS_LAUNCHER_CONTRACT_PLAN_2026-05-18.md`
   - v243 보고서: `docs/reports/NATIVE_INIT_V243_CNSS_LAUNCHER_CONTRACT_PLAN_2026-05-18.md`
   - v243 결과: decision `cnss-launcher-contract-ready`
   - v243 해석: start-only runner는 `system=1000`, groups `inet=3003/net_admin=3005/wifi=1010`, `CAP_NET_ADMIN`, v241 private namespace를 만족해야 한다
   - v244 계획서: `docs/plans/NATIVE_INIT_V244_CNSS_IDENTITY_PROBE_PLAN_2026-05-19.md`
   - v244 보고서: `docs/reports/NATIVE_INIT_V244_CNSS_IDENTITY_PROBE_2026-05-19.md`
   - v244 결과: decision `cnss-identity-probe-pass`
   - v244 해석: non-starting harmless child에서 uid/gid/groups/`CAP_NET_ADMIN` 계약과 post-exec `/proc/self/status` 검증이 통과했다. dynamic exec에는 v241 symlink farm 대신 bind-backed private `/apex` farm이 필요했다
   - v245 계획서: `docs/plans/NATIVE_INIT_V245_CNSS_START_ONLY_RUNNER_PLAN_2026-05-19.md`
   - v245 보고서: `docs/reports/NATIVE_INIT_V245_CNSS_START_ONLY_RUNNER_2026-05-19.md`
   - v245 방향: v229 `runandroid` path를 버리고 v244 private namespace/helper 계약 기반의 controlled start-only runner를 만든다
   - v245 결과: `scripts/revalidation/wifi_cnss_start_only_runner.py` plan/preflight/dry-run PASS, live `run` 기본값은 fail-closed
   - v246 계획서: `docs/plans/NATIVE_INIT_V246_CNSS_START_ONLY_HELPER_MODE_PLAN_2026-05-19.md`
   - v246 보고서: `docs/reports/NATIVE_INIT_V246_CNSS_START_ONLY_HELPER_MODE_2026-05-19.md`
   - v246 결과: helper에 guarded `--mode cnss-start-only` / `--allow-cnss-start-only` 추가, no-allow 직접 실행은 `cnss_start.result=start-only-blocked`, runner plan/preflight/dry-run PASS, runner `run` 기본값은 fail-closed
   - v246 helper SHA-256: `5ae105f0d397f845cd602eb4b283cdbd817146eff9405d10c090320eded25c65`
   - v247 계획서: `docs/plans/NATIVE_INIT_V247_CNSS_START_OBSERVE_STOP_BODY_PLAN_2026-05-19.md`
   - v247 보고서: `docs/reports/NATIVE_INIT_V247_CNSS_START_OBSERVE_STOP_BODY_2026-05-19.md`
   - v247 결과: helper에 실제 start/observe/stop body와 host parser 구현 완료, static + safe no-start 검증 PASS, 직접 no-allow는 `cnss_start.result=start-only-blocked`, runner `plan`/`preflight`/`dry-run` PASS, runner `run` 기본값은 fail-closed
   - v247 helper SHA-256: `77fbdcdcbc6774abe5e34712097496edbac4a4ed763d87c82cf02effb88cd319`
   - v248 계획서: `docs/plans/NATIVE_INIT_V248_CNSS_RUNTIME_PRIMITIVE_PREFLIGHT_PLAN_2026-05-19.md`
   - v248 보고서: `docs/reports/NATIVE_INIT_V248_CNSS_RUNTIME_PRIMITIVES_PREFLIGHT_2026-05-19.md`
   - v248 결과: decision `cnss-runtime-primitives-ready-for-live-approval`, daemon start not executed, helper no-allow namespace/guard PASS, private `/vendor/bin/cnss-daemon` target evidence PASS
   - v248 runtime gaps: property service/socket area, SELinux null, `/dev/diag`, `/dev/qrtr`, global `/vendor` remain missing/expected gaps
   - v249 계획서: `docs/plans/NATIVE_INIT_V249_CNSS_RUNTIME_GAP_CLASSIFIER_PLAN_2026-05-19.md`
   - v249 보고서: `docs/reports/NATIVE_INIT_V249_CNSS_RUNTIME_GAP_CLASSIFIER_2026-05-19.md`
   - v249 결과: decision `cnss-runtime-gaps-classified`, daemon start not executed, `QIPCRTR` kernel family present, helper `dev-null-selinux` no-allow materialization PASS
   - v249 해석: property service/area는 Android-init-owned gap, QRTR은 kernel family가 아니라 userspace nameservice/endpoint risk, diag는 `cnss_diag` phase2 blocker
   - v250 계획서: `docs/plans/NATIVE_INIT_V250_QRTR_SOCKET_PROBE_PLAN_2026-05-19.md`
   - v250 보고서: `docs/reports/NATIVE_INIT_V250_QRTR_SOCKET_PROBE_2026-05-19.md`
   - v250 결과: decision `qrtr-socket-local-bind-pass`, daemon start not executed, `AF_QIPCRTR` socket open and local ephemeral bind PASS, no send/connect
   - v250 해석: QRTR은 kernel socket-family/local bind 수준에서는 blocker가 아니며, 남은 리스크는 userspace nameservice/endpoint behavior
   - v262 계획서: `docs/plans/NATIVE_INIT_V262_QRTR_QMI_NO_SCAN_PROBE_PLAN_2026-05-19.md`
   - v262 보고서: `docs/reports/NATIVE_INIT_V262_QRTR_QMI_NO_SCAN_PROBE_2026-05-19.md`
   - v262 결과: decision `qrtr-qmi-no-scan-ready`, v261 clean baseline에서 CNSS process clean, `QIPCRTR` protocol present, QRTR helper `bind-pass`, no send/connect, no `wlan*` link surface
   - v262 해석: `/dev/qrtr`, `/dev/diag`, `/dev/ipa`, `/dev/wlan`은 여전히 absent이고 남은 gap은 userspace/runtime endpoint 또는 nameservice behavior다. 실제 packet transmission은 별도 explicit approval gate 뒤로 둔다
   - v263 계획서: `docs/plans/NATIVE_INIT_V263_CNSS_WARNING_DISPOSITION_PLAN_2026-05-19.md`
   - v263 보고서: `docs/reports/NATIVE_INIT_V263_CNSS_WARNING_DISPOSITION_2026-05-19.md`
   - v263 결과: decision `cnss-warning-disposition-ready`, `perfd-client-unavailable`과 `kmsg-write-denied`는 start-only 허용 경고로 분류, `shell-quote-noise`는 kmsg logging-path noise로 병합
   - v263 approved live retry: `tmp/wifi/v263-cnss-live-retry-20260519-091608/`, decision `start-only-pass`, postflight `cnss-process-clean`
   - v263 해석: start-only를 막는 경고는 남지 않았지만 broader Wi-Fi 전에는 perfd/property/kmsg shim을 opt-in으로 설계해야 한다
   - v264 계획서: `docs/plans/NATIVE_INIT_V264_QRTR_QMI_NAMESERVICE_MODEL_PLAN_2026-05-19.md`
   - v264 보고서: `docs/reports/NATIVE_INIT_V264_QRTR_QMI_NAMESERVICE_MODEL_2026-05-19.md`
   - v264 결과: decision `qrtr-qmi-userspace-model-ready`, QRTR/QMI userspace boundary modeled without packet transmission
   - v264 해석: QRTR kernel socket readiness는 충분조건이 아니며, nameservice/QMI request transmission은 별도 explicit approval gate가 필요하다
   - v265 계획서: `docs/plans/NATIVE_INIT_V265_QRTR_NAMESERVICE_APPROVAL_CONTRACT_PLAN_2026-05-19.md`
   - v265 보고서: `docs/reports/NATIVE_INIT_V265_QRTR_NAMESERVICE_APPROVAL_CONTRACT_2026-05-19.md`
   - v265 결과: decision `qrtr-nameservice-approval-contract-ready`, future command template generated but not executed
   - v265 해석: 다음 QRTR nameservice no-scan runner는 구현 가능하지만 실제 packet transmission은 명시 승인이 필요하다
   - v266 계획서: `docs/plans/NATIVE_INIT_V266_QRTR_NAMESERVICE_RUNNER_SKELETON_PLAN_2026-05-19.md`
   - v266 보고서: `docs/reports/NATIVE_INIT_V266_QRTR_NAMESERVICE_RUNNER_SKELETON_2026-05-19.md`
   - v266 결과: runner skeleton PASS, read-only preflight PASS, no-approval run fail-closed PASS, approval-flag run still `transmit-not-implemented`
   - v266 해석: 실제 QRTR packet 송신은 아직 구현되지 않았고, v267 helper design 또는 explicit approval-gated bounded run이 다음 경계다
   - v267 계획서: `docs/plans/NATIVE_INIT_V267_QRTR_PACKET_LAYOUT_PLAN_2026-05-19.md`
   - v267 보고서: `docs/reports/NATIVE_INIT_V267_QRTR_PACKET_LAYOUT_2026-05-19.md`
   - v267 결과: `QRTR_TYPE_NEW_LOOKUP`/`DEL_LOOKUP` 20-byte little-endian packet layout generated, wildcard lookup block verified
   - v267 해석: helper code review에 필요한 byte layout은 준비됐지만 실제 QRTR 송신은 여전히 explicit approval-gated다
   - v268 계획서: `docs/plans/NATIVE_INIT_V268_QRTR_NS_HELPER_SOURCE_PLAN_2026-05-19.md`
   - v268 보고서: `docs/reports/NATIVE_INIT_V268_QRTR_NS_HELPER_SOURCE_2026-05-19.md`
   - v268 결과: `a90_qrtr_ns_probe.c` source/build PASS, static ARM64 helper hash `c2d8707155b776c6c31e815136a66060f2087c4606c8a48cf9bd4b7944fdbb2a`
   - v268 해석: transmit-capable helper source exists but was not deployed or executed; actual lookup remains explicit approval gated
   - v269 계획서: `docs/plans/NATIVE_INIT_V269_QRTR_NAMESERVICE_LIVE_RETRY_PLAN_2026-05-19.md`
   - v269 보고서: `docs/reports/NATIVE_INIT_V269_QRTR_NAMESERVICE_LIVE_RETRY_2026-05-19.md`
   - v269 결과: explicit approval-gated `a90_qrtr_ns_probe` deploy/run PASS, `QRTR_TYPE_NEW_LOOKUP` + cleanup `DEL_LOOKUP` sent for service `1` instance `1`, `qrtr_ns.status=lookup-sent`, `qmi_attempted=0`
   - v269 해석: basic QRTR nameservice send path is no longer the blocker; no `cnss-daemon` or `wlan*` appeared, so next blocker is endpoint/service visibility and possible QMI-control discovery under a separate approval gate
   - v270 계획서: `docs/plans/NATIVE_INIT_V270_QRTR_NAMESERVICE_READBACK_PLAN_2026-05-19.md`
   - v270 보고서: `docs/reports/NATIVE_INIT_V270_QRTR_NAMESERVICE_READBACK_2026-05-19.md`
   - v270 결과: `a90_qrtr_ns_probe v2` readback PASS, 1s/3s windows both `qrtr-ns-readback-timeout`, events `0`, service events `0`, `qmi_attempted=0`
   - v270 해석: QRTR nameservice control send works but service `1` instance `1` produced no visible nameservice notification; next is service/instance evidence correlation before any QMI-control payload plan
   - v271 계획서: `docs/plans/NATIVE_INIT_V271_QRTR_SERVICE_SELECTOR_PLAN_2026-05-19.md`
   - v271 보고서: `docs/reports/NATIVE_INIT_V271_QRTR_SERVICE_SELECTOR_2026-05-19.md`
   - v271 결과: host-only selector PASS, decision `qrtr-service-selector-ready`, service `1`/instance `1` negative evidence confirmed, DMS strong service-object-backed candidate, WLFW strong but unresolved
   - v271 해석: 다음 단계는 QMI payload가 아니라 real service object 기반 numeric service id extraction이다. QRTR/QMI live payload는 계속 별도 approval gate로 둔다
   - v272 계획서: `docs/plans/NATIVE_INIT_V272_QMI_SERVICE_OBJECT_EXTRACTOR_PLAN_2026-05-19.md`
   - v272 보고서: `docs/reports/NATIVE_INIT_V272_QMI_SERVICE_OBJECT_EXTRACTOR_2026-05-19.md`
   - v272 결과: host-only ELF parser PASS, decision `qmi-service-object-ids-extracted`, DMS service id `2`, service id `1` maps to WDS, WLFW exported object unresolved
   - v272 해석: v269/v270의 service `1` 실험은 WDS 기반 negative evidence로 정리한다. 다음은 DMS `2` visibility matrix 또는 WLFW service-object locator이며 QMI payload는 계속 금지한다
   - v273 계획서: `docs/plans/NATIVE_INIT_V273_QRTR_READBACK_MATRIX_PLAN_2026-05-19.md`
   - v273 보고서: `docs/reports/NATIVE_INIT_V273_QRTR_READBACK_MATRIX_2026-05-19.md`
   - v273 결과: approved bounded matrix PASS, WDS `1`/DMS `2` with instances `0,1` all `qrtr-readback-matrix-timeout`, events `0`, `qmi_attempted=0`
   - v273 해석: DMS/WDS visible service lookup도 현재 native state에서 QRTR service notification을 만들지 않는다. 다음은 WLFW service-object locator 또는 CNSS/runtime endpoint registration 조건 분석이다
   - v274 계획서: `docs/plans/NATIVE_INIT_V274_WLFW_SERVICE_LOCATOR_PLAN_2026-05-19.md`
   - v274 보고서: `docs/reports/NATIVE_INIT_V274_WLFW_SERVICE_LOCATOR_2026-05-19.md`
   - v274 결과: host-only locator PASS, decision `wlfw-service-id-source-backed`, WLFW service id `0x45` / `69`, version `1`, local CNSS WLFW strings matched
   - v274 해석: 다음 live 후보는 WLFW service `0x45` instance `0,1`에 대한 bounded QRTR nameservice readback이다. QMI payload는 계속 금지한다
   - v251 계획서: `docs/plans/NATIVE_INIT_V251_CNSS_PROPERTY_SURFACE_PLAN_2026-05-19.md`
   - v251 보고서: `docs/reports/NATIVE_INIT_V251_CNSS_PROPERTY_SURFACE_2026-05-19.md`
   - v251 결과: decision `cnss-property-read-only-surface`, host-only analysis, property read symbols `property_get`/`property_get_int32`, no property write/control symbols detected
   - v251 해석: property service/area gap은 write/control risk보다 read/default risk이며, `/data/vendor/wifi/sockets/...`는 별도 runtime filesystem/socket surface로 분리
   - v252 계획서: `docs/plans/NATIVE_INIT_V252_CNSS_DATA_WIFI_SURFACE_PLAN_2026-05-19.md`
   - v252 보고서: `docs/reports/NATIVE_INIT_V252_CNSS_DATA_WIFI_SURFACE_2026-05-19.md`
   - v252 결과: decision `cnss-data-wifi-surface-missing`, `/data`는 있으나 `/data/vendor`, `/data/vendor/wifi`, `/data/vendor/wifi/sockets`는 missing, daemon start not executed
   - v252 해석: runtime Wi-Fi data tree는 property service/QRTR와 별도 gap이며, helper private namespace 안에서만 materialize할지 별도 계획 필요
   - v253 계획서: `docs/plans/NATIVE_INIT_V253_PRIVATE_DATA_WIFI_MATERIALIZATION_PLAN_2026-05-19.md`
   - v253 보고서: `docs/reports/NATIVE_INIT_V253_PRIVATE_DATA_WIFI_MATERIALIZATION_2026-05-19.md`
   - v253 결과: decision `private-data-wifi-materialization-pass`, helper v9 SHA `80e8afb1b77fdba23dfbc71d6a8e17e5a2a095ed1de728474fd2855923c351a1`, private `/data/vendor/wifi/sockets` materialization PASS, real `/data/vendor/wifi` remains missing
   - v253 해석: runtime data tree gap은 helper private namespace 안에서 닫을 수 있음. 다음 live profile에는 `dev-null-selinux` + `private-empty` 조합을 제안할 수 있으나 실행은 여전히 approval-gated
   - v254 계획서: `docs/plans/NATIVE_INIT_V254_START_ONLY_PROFILE_REFRESH_PLAN_2026-05-19.md`
   - v254 보고서: `docs/reports/NATIVE_INIT_V254_START_ONLY_PROFILE_REFRESH_2026-05-19.md`
   - v254 결과: decision `start-only-profile-refresh-pass`, runner default profile updated to `--null-device-mode dev-null-selinux` + `--data-wifi-mode private-empty`, helper no-allow validation kept `cnss_start.result=start-only-blocked` and `exec_attempted=0`
   - v254 해석: latest no-start runtime shims are now the default proposed start-only profile. This is still approval-gated and does not execute the daemon by default
   - v255 계획서: `docs/plans/NATIVE_INIT_V255_CNSS_LIVE_APPROVAL_PACKET_PLAN_2026-05-19.md`
   - v255 보고서: `docs/reports/NATIVE_INIT_V255_CNSS_LIVE_APPROVAL_PACKET_2026-05-19.md`
   - v255 결과: decision `live-approval-packet-ready`, generated exact manual live command, helper no-allow remained `start-only-blocked`, real `/data/vendor/wifi` state unchanged, no daemon execution
   - v255 live attempt: explicit approval 후 실행했으나 `manual-review-required`, helper가 signal 15로 종료되고 `cnss-daemon` PID 5900이 남음. manual `kill -TERM 5900`으로 회수했고 최종 `pidof cnss-daemon` rc=1, `/proc/net/dev`에 `wlan*` 없음
   - v256 계획서: `docs/plans/NATIVE_INIT_V256_CNSS_CLEANUP_RACE_FIX_PLAN_2026-05-19.md`
   - v256 보고서: `docs/reports/NATIVE_INIT_V256_CNSS_CLEANUP_RACE_FIX_2026-05-19.md`
   - v256 결과: helper v10 SHA `1c0234f5468f053ae559c5307124db4682f6ed89a1644312194eca730a623750`, child `setsid()` pgid race fix, no-allow validation PASS, runner plan/preflight/dry-run PASS, v10 approval packet PASS
   - v256 해석: first live proved daemon can start far enough to persist, but cleanup race made the result unsafe. Future live retry requires v10 helper and explicit operator approval
   - v257 계획서: `docs/plans/NATIVE_INIT_V257_CNSS_V10_LIVE_RETRY_PLAN_2026-05-19.md`
   - v257 보고서: `docs/reports/NATIVE_INIT_V257_CNSS_V10_LIVE_RETRY_2026-05-19.md`
   - v257 결과: explicit approval 후 v10 bounded live retry PASS, decision `start-only-pass`, `cnss_start.observable=1`, `reaped=1`, `postflight_safe=1`, final `pidof cnss-daemon` rc=1, `/proc/net/dev`에 `wlan*` 없음
   - v257 해석: `cnss-daemon -n -l` start/observe/stop/reap primitive는 검증됐다. 아직 Wi-Fi scan/connect/link-up/credential/DHCP/routing readiness는 아니다
   - v258 계획서: `docs/plans/NATIVE_INIT_V258_CNSS_LIVE_EVIDENCE_ANALYZER_PLAN_2026-05-19.md`
   - v258 보고서: `docs/reports/NATIVE_INIT_V258_CNSS_LIVE_EVIDENCE_ANALYZER_2026-05-19.md`
   - v258 결과: `scripts/revalidation/wifi_cnss_live_evidence_analyzer.py` 구현, V257 evidence를 `cnss-start-only-evidence-classified`로 분류, checks `11/11` PASS
   - v258 해석: lifecycle/identity/namespace/maps/postflight는 pass. runtime warning은 `perfd-client-unavailable`, `kmsg-write-denied`, `shell-quote-noise`
   - v259 계획서: `docs/plans/NATIVE_INIT_V259_CNSS_WARNING_SURFACE_PLAN_2026-05-19.md`
   - v259 보고서: `docs/reports/NATIVE_INIT_V259_CNSS_WARNING_SURFACE_2026-05-19.md`
   - v259 결과: `scripts/revalidation/wifi_cnss_warning_surface_probe.py` 구현, decision `cnss-warning-surface-classified`, daemon 실행 없이 PASS
   - v259 해석: perfd client surface는 있으나 runtime socket 없음, Android property service/socket/area 없음, kmsg/quote noise는 helper source가 아니라 daemon/library logging-path stderr로 분류
   - v260 계획서: `docs/plans/NATIVE_INIT_V260_CNSS_ZOMBIE_POSTFLIGHT_PLAN_2026-05-19.md`
   - v260 보고서: `docs/reports/NATIVE_INIT_V260_CNSS_ZOMBIE_POSTFLIGHT_2026-05-19.md`
   - v260 결과: `scripts/revalidation/wifi_cnss_zombie_audit.py` 구현, current session에서 `5900 Zs [cnss-daemon]` PID1 zombie 확인, runner preflight는 `start-only-blocked`, analyzer는 process evidence 제공 시 `cnss-start-only-evidence-incomplete`
   - v260 해석: `pidof` absence만으로 CNSS cleanup을 판정하면 안 된다. 다음 live retry/QRTR probe 전 clean-state 또는 PID1 reaper hardening이 필요하다
   - v261 계획서: `docs/plans/NATIVE_INIT_V261_PID1_ORPHAN_REAPER_PLAN_2026-05-19.md`
   - v261 보고서: `docs/reports/NATIVE_INIT_V261_PID1_ORPHAN_REAPER_2026-05-19.md`
   - v261 결과: `A90 Linux init 0.9.60 (v261)` 실기 플래시 PASS, `reaper [status|run|verbose]` 추가, `pid1guard` reaper 항목 PASS, CNSS zombie audit clean PASS
   - v261 live retry: explicit approval 후 bounded CNSS start-only retry PASS, decision `start-only-pass`, `reaped=1`, `postflight_safe=1`, postflight CNSS process clean PASS
   - v261 해석: PID1 orphan reaper와 process-table audit gate가 동작한다. 다음 후보는 QRTR/QMI endpoint interaction no-scan probe 또는 CNSS warning/perfd/kmsg noise 개선이다
   - v274 계획서: `docs/plans/NATIVE_INIT_V274_WLFW_SERVICE_LOCATOR_PLAN_2026-05-19.md`
   - v274 보고서: `docs/reports/NATIVE_INIT_V274_WLFW_SERVICE_LOCATOR_2026-05-19.md`
   - v274 결과: decision `wlfw-service-id-source-backed`, WLFW service id `69`/`0x45`, version `1`, local cnss-daemon WLFW string coverage PASS
   - v275 계획서: `docs/plans/NATIVE_INIT_V275_WLFW_QRTR_READBACK_PLAN_2026-05-19.md`
   - v275 보고서: `docs/reports/NATIVE_INIT_V275_WLFW_QRTR_READBACK_2026-05-19.md`
   - v275 결과: decision `qrtr-readback-matrix-timeout`, WLFW service `69` instance `0/1` both timeout with events `0`, service_events `0`, qmi_attempted `0`
   - v275 해석: WDS/DMS/WLFW 모두 native QRTR nameservice readback에서 notification이 없으므로 다음은 QMI payload가 아니라 QRTR/CNSS registration-state correlation이다
   - v276 계획서: `docs/plans/NATIVE_INIT_V276_QRTR_CNSS_REGISTRATION_CORRELATION_PLAN_2026-05-19.md`
   - v276 보고서: `docs/reports/NATIVE_INIT_V276_QRTR_CNSS_REGISTRATION_CORRELATION_2026-05-19.md`
   - v276 결과: decision `qrtr-cnss-platform-surface-visible`, QIPCRTR/no-send probe PASS, active `/dev` endpoint `0`, `/sys` CNSS/WLAN/QRTR surfaces `68`, cnss process clean, no `wlan*`
   - v276 해석: QRTR socket readiness가 blocker는 아니며, static platform state를 read-only로 더 좁혀야 한다. QMI payload는 계속 blocked
   - v277 계획서: `docs/plans/NATIVE_INIT_V277_ICNSS_PLATFORM_SURFACE_PLAN_2026-05-19.md`
   - v277 보고서: `docs/reports/NATIVE_INIT_V277_ICNSS_PLATFORM_SURFACE_2026-05-19.md`
   - v277 결과: decision `icnss-platform-present-no-wlan-netdev`, ICNSS node/driver/device present, QCA6390 node present but driver link absent, `/sys/module/wlan` present but no `wlan*`/wiphy/rfkill
   - v277 해석: 플랫폼/펌웨어 경로는 보이지만 QCA6390 driver lifecycle 또는 userspace sequencing 전 netdev registration이 빠져 있다. QMI payload는 계속 blocked
   - v278 계획서: `docs/plans/NATIVE_INIT_V278_QCA6390_DRIVER_PARAM_PLAN_2026-05-19.md`
   - v278 보고서: `docs/reports/NATIVE_INIT_V278_QCA6390_DRIVER_PARAM_2026-05-19.md`
   - v278 결과: decision `qca6390-match-visible-driver-unbound`, QCA6390 compatible/modalias visible, driver link absent, WLAN params 9/9 readable (`fwpath` empty, `country_code=(null)`, `con_mode=0`), no `wlan*`/wiphy/rfkill
   - v278 해석: QCA6390 OF match는 있으나 native state에서 driver binding이 없다. 다음은 CNSS/QCA6390 probe expectation 비교 또는 명시 승인 start-only delta observation이다
   - v279 계획서: `docs/plans/NATIVE_INIT_V279_CNSS_QCA6390_START_DELTA_PLAN_2026-05-19.md`
   - v279 보고서: `docs/reports/NATIVE_INIT_V279_CNSS_QCA6390_START_DELTA_2026-05-19.md`
   - v279 결과: decision `cnss-qca6390-no-driver-delta`, guarded CNSS start-only PASS, QCA6390 driver link absent before/after, WLAN params unchanged, no `wlan*`/wiphy/rfkill, postflight process clean
   - v279 해석: start-only alone does not bind QCA6390 or change WLAN parameter state. 다음은 no-start CNSS/QCA6390 source/sysfs expectation comparison, read-only kernel log extraction, or separately approved QRTR/WLFW readback during start-only이다
   - v280 계획서: `docs/plans/NATIVE_INIT_V280_CNSS_QCA6390_PROBE_EXPECTATION_PLAN_2026-05-19.md`
   - v280 보고서: `docs/reports/NATIVE_INIT_V280_CNSS_QCA6390_PROBE_EXPECTATION_2026-05-19.md`
   - v280 결과: decision `cnss2-driver-dir-missing-qca-unbound`, QCA6390 compatible/modalias visible, QCA6390 driver link absent, `/sys/bus/platform/drivers/cnss2` absent, `/sys/bus/platform/drivers/icnss` present, `CONFIG_CNSS2=n`, no `wlan*`/wiphy
   - v280 해석: CNSS2 source model is not the live kernel binding model. 다음은 live `icnss` driver model/source/sysfs expectation comparison이다
   - v281 계획서: `docs/plans/NATIVE_INIT_V281_ICNSS_PROBE_EXPECTATION_PLAN_2026-05-19.md`
   - v281 보고서: `docs/reports/NATIVE_INIT_V281_ICNSS_PROBE_EXPECTATION_2026-05-19.md`
   - v281 결과: decision `icnss-core-bound-host-driver-waits-fw`, ICNSS core bound, QCA6390 context visible, WLAN module sysfs present, `CONFIG_ICNSS=y`, `CONFIG_ICNSS_QMI=y`, no `wlan*`/wiphy
   - v281 해석: live model은 ICNSS core plus WLAN host-driver registration이며 host-driver probe는 firmware-ready/QMI state를 기다리는 구조다
   - v282 계획서: `docs/plans/NATIVE_INIT_V282_ICNSS_WLFW_READINESS_SURFACE_PLAN_2026-05-19.md`
   - v282 보고서: `docs/reports/NATIVE_INIT_V282_ICNSS_WLFW_READINESS_SURFACE_2026-05-19.md`
   - v282 결과: decision `icnss-readiness-sysfs-candidates-limited`, ICNSS core bound, WLAN module sysfs present, `CONFIG_DEBUG_FS=y`, `CONFIG_ICNSS_DEBUG=n`, `/sys/kernel/debug/icnss` absent, no readiness dmesg, no `wlan*`/wiphy
   - v282 해석: no-start 상태에서 직접 WLFW firmware-ready state file은 보이지 않는다. 다음은 검증된 start-only primitive로 before/during/after readiness delta를 관찰하는 v283이다
   - v283 계획서: `docs/plans/NATIVE_INIT_V283_ICNSS_WLFW_START_DELTA_PLAN_2026-05-19.md`
   - v283 보고서: `docs/reports/NATIVE_INIT_V283_ICNSS_WLFW_START_DELTA_2026-05-19.md`
   - v283 결과: decision `icnss-wlfw-start-no-readiness-delta`, nested runner `start-only-pass`, child pid/pgid `1077/1077`, reaped, postflight clean, dmesg readiness `0 -> 0`, sysfs candidates `13 -> 13`, no `wlan*`/wiphy
   - v283 해석: `cnss-daemon -n -l` start-only는 안전하게 실행/정리되지만 ICNSS/WLFW readiness surface를 바꾸지 않는다. 반복보다는 NCM/tcpctl 또는 broker 기반 concurrent side-channel observer가 다음 후보이다
   - v284 계획서: `docs/plans/NATIVE_INIT_V284_CNSS_CONCURRENT_SIDECHANNEL_PLAN_2026-05-19.md`
   - v284 보고서: `docs/reports/NATIVE_INIT_V284_CNSS_CONCURRENT_SIDECHANNEL_2026-05-19.md`
   - v284 결과: decision `cnss-sidechannel-no-readiness-delta`, serial CNSS start-only `start-only-pass`, NCM/tcpctl 12/12 concurrent samples PASS, no readiness lines, no `wlan*`/wiphy, postflight clean
   - v284 해석: side-channel 구조는 동작한다. 다음은 같은 구조로 ICNSS/QCA6390 sysfs/module/interrupt/dmesg 상태를 더 좁게 샘플링하는 v285가 적절하다
   - v285 계획서: `docs/plans/NATIVE_INIT_V285_ICNSS_QCA6390_DURING_START_PLAN_2026-05-19.md`
   - v285 보고서: `docs/reports/NATIVE_INIT_V285_ICNSS_QCA6390_DURING_START_2026-05-19.md`
   - v285 결과: decision `icnss-qca6390-focused-no-during-delta`, serial CNSS start-only `start-only-pass`, NCM/tcpctl 19 focused samples PASS, focused delta `0`, no `wlan*`/wiphy, postflight clean
   - v285 해석: focused ICNSS/QCA6390 during-start sampling also shows no state delta. 동일 start-only 반복보다는 Android/TWRP/native ICNSS boot timing 비교가 다음 후보이다
   - v286 계획서: `docs/plans/NATIVE_INIT_V286_ICNSS_BOOT_TIMING_COMPARE_PLAN_2026-05-19.md`
   - v286 보고서: `docs/reports/NATIVE_INIT_V286_ICNSS_BOOT_TIMING_COMPARE_2026-05-19.md`
   - v286 결과: decision `icnss-boot-timing-gap-mapped`, first missing native event `android_wifi_action`, Android Wi-Fi service/WLFW/QMI readiness chain visible around `7s..15s`, native boot-window evidence lacks that chain
   - v286 해석: 다음은 blind start-only 반복이 아니라 Android Wi-Fi service-order replay plan이다. QMI payload와 link-up은 계속 blocked
   - v287 계획서: `docs/plans/NATIVE_INIT_V287_WIFI_SERVICE_ORDER_REPLAY_PLAN_2026-05-19.md`
   - v287 보고서: `docs/reports/NATIVE_INIT_V287_WIFI_SERVICE_ORDER_REPLAY_MODEL_2026-05-19.md`
   - v287 결과: decision `wifi-service-order-replay-model-ready`, first missing service boundary `vendor.wifi_hal_ext`, `cnss-daemon`은 bounded start-only candidate로만 유지, Wi-Fi HAL/`cnss_diag`/`wificond`/supplicant/hostapd는 blocked
   - v287 해석: 다음은 HAL/framework boundary inventory이다. binder/hwbinder/hwservicemanager/VINTF/property/socket/SELinux/capability/linker namespace를 확인하기 전 HAL 또는 `wificond` 실행은 금지한다
   - v288 계획서: `docs/plans/NATIVE_INIT_V288_HAL_FRAMEWORK_BOUNDARY_PLAN_2026-05-19.md`
   - v288 보고서: `docs/reports/NATIVE_INIT_V288_HAL_FRAMEWORK_BOUNDARY_2026-05-19.md`
   - v288 결과: decision `hal-framework-boundary-native-blocked`, native `/dev/binder`, `/dev/hwbinder`, `/dev/vndbinder`, service-manager process, property runtime이 blocker로 확인됨
   - v288 해석: binary/VINTF 일부가 보여도 HAL/`wificond` 실행 준비는 아니다. 다음은 Binder/service-manager feasibility inventory가 우선이다
   - v289 계획서: `docs/plans/NATIVE_INIT_V289_BINDER_SERVICE_MANAGER_FEASIBILITY_PLAN_2026-05-19.md`
   - v289 보고서: `docs/reports/NATIVE_INIT_V289_BINDER_SERVICE_MANAGER_FEASIBILITY_2026-05-19.md`
   - v289 결과: decision `binder-kernel-present-devnodes-missing`, `CONFIG_ANDROID_BINDER_IPC=y`, `CONFIG_ANDROID_BINDER_DEVICES=binder,hwbinder,vndbinder`, `/proc/misc` Binder devices present, native Binder `/dev` nodes absent, binderfs absent
   - v289 해석: Binder 커널 지원은 있으나 native init이 Binder devnode를 만들지 않는다. 다음은 service-manager/HAL 실행이 아니라 private Binder devnode feasibility plan이다
   - v290 계획서: `docs/plans/NATIVE_INIT_V290_BINDER_DEVNODE_FEASIBILITY_PLAN_2026-05-19.md`
   - v290 보고서: `docs/reports/NATIVE_INIT_V290_BINDER_DEVNODE_FEASIBILITY_2026-05-19.md`
   - v290 결과: decision `binder-devnode-plan-ready`, Binder devnode 후보 `10:81`, `10:80`, `10:79` 확인, native `/dev` 노드는 계속 absent
   - v290 해석: 다음은 read-only inventory가 아니라 temporary Binder devnode create/cleanup smoke이다. 이는 `mknod`를 수행하는 non-read-only 단계이므로 실행 전 범위가 명확해야 한다
   - v291 계획서: `docs/plans/NATIVE_INIT_V291_BINDER_DEVNODE_SMOKE_PLAN_2026-05-19.md`
   - v291 보고서: `docs/reports/NATIVE_INIT_V291_BINDER_DEVNODE_SMOKE_2026-05-19.md`
   - v291 결과: decision `binder-devnode-create-cleanup-pass`, 세 Binder devnode를 `mknodc`로 생성하고 `stat` 확인 후 `toybox rm -f`로 정리 PASS
   - v291 해석: native `/dev` Binder surface는 임시 복구 가능하다. 다음은 Binder protocol이 아니라 open/close만 검증하는 static helper smoke이다
   - v292 계획서: `docs/plans/NATIVE_INIT_V292_BINDER_OPEN_SMOKE_PLAN_2026-05-19.md`
   - v292 보고서: `docs/reports/NATIVE_INIT_V292_BINDER_OPEN_SMOKE_2026-05-19.md`
   - v292 결과: decision `binder-open-only-smoke-pass`, `toybox dd if=/dev/<binder-node> of=/dev/null bs=1 count=0`로 세 Binder domain open/close PASS, cleanup PASS
   - v292 해석: Binder device open 최저 레벨 blocker는 제거됐다. 다음은 service-manager process/property/SELinux/linker namespace prerequisite model이며, HAL/`wificond` 실행은 아직 금지다
   - v293 계획서: `docs/plans/NATIVE_INIT_V293_SERVICE_MANAGER_PREREQ_PLAN_2026-05-19.md`
   - v293 보고서: `docs/reports/NATIVE_INIT_V293_SERVICE_MANAGER_PREREQ_2026-05-19.md`
   - v293 결과: decision `service-manager-prereq-blockers-mapped`, service-manager process model absent, Android property runtime absent, linker/runtime partial
   - v293 해석: Binder open은 통과했지만 service-manager 실행은 아직 이르다. 다음은 property-runtime feasibility inventory이다
   - v294 계획서: `docs/plans/NATIVE_INIT_V294_PROPERTY_RUNTIME_FEASIBILITY_PLAN_2026-05-19.md`
   - v294 보고서: `docs/reports/NATIVE_INIT_V294_PROPERTY_RUNTIME_FEASIBILITY_2026-05-19.md`
   - v294 결과: decision `property-runtime-inputs-visible-runtime-absent`, mounted property contexts/build props visible, `/dev/socket/property_service`, `/dev/__properties__`, `/dev/socket` absent
   - v294 해석: Android property 입력은 보이지만 runtime은 없다. 다음은 service-manager 실행이 아니라 read-only property snapshot/shim model이다
   - v295 계획서: `docs/plans/NATIVE_INIT_V295_PROPERTY_SNAPSHOT_MODEL_PLAN_2026-05-19.md`
   - v295 보고서: `docs/reports/NATIVE_INIT_V295_PROPERTY_SNAPSHOT_MODEL_2026-05-19.md`
   - v295 결과: decision `property-snapshot-model-ready`, static property `248`개와 property context `1264`라인 파싱, Wi-Fi 관련 property `7`개, selected required baseline `1/4`
   - v295 해석: 정적 property snapshot은 만들 수 있으나 live property runtime은 아니다. 다음은 property shim strategy model이다
   - v296 계획서: `docs/plans/NATIVE_INIT_V296_PROPERTY_SHIM_STRATEGY_PLAN_2026-05-19.md`
   - v296 보고서: `docs/reports/NATIVE_INIT_V296_PROPERTY_SHIM_STRATEGY_2026-05-19.md`
   - v296 결과: decision `property-shim-strategy-capture-needed`, static snapshot에서 `ro.product.name`, `ro.hardware`, `ro.vendor.build.version.sdk` 누락
   - v296 해석: property shim을 합성하기 전에 Android boot 상태의 `getprop`/property baseline capture가 필요하다
   - v297 계획서: `docs/plans/NATIVE_INIT_V297_ANDROID_PROPERTY_CAPTURE_PLAN_2026-05-19.md`
   - v297 보고서: `docs/reports/NATIVE_INIT_V297_ANDROID_PROPERTY_CAPTURE_2026-05-19.md`
   - v297 결과: host capture tool은 준비됐고 현재 native 상태에서는 decision `android-property-capture-waiting-for-android`
   - v297 해석: 다음 live 단계는 명시적으로 Android로 부팅한 뒤 read-only `getprop` baseline을 캡처하는 것이다. 그 전까지 native property runtime 생성과 service-manager 실행은 blocked
   - v298 계획서: `docs/plans/NATIVE_INIT_V298_PROPERTY_BASELINE_COMPARE_PLAN_2026-05-19.md`
   - v298 보고서: `docs/reports/NATIVE_INIT_V298_PROPERTY_BASELINE_COMPARE_2026-05-19.md`
   - v298 결과: decision `property-baseline-compare-waiting-for-android`, v297 Android capture manifest가 아직 없으므로 shim 설계는 blocked
   - v298 해석: 다음은 추가 host-only 모델이 아니라 Android boot 후 v297 capture 실행이다
   - v299 계획서: `docs/plans/NATIVE_INIT_V299_ANDROID_CAPTURE_HANDOFF_PLAN_2026-05-19.md`
   - v299 보고서: `docs/reports/NATIVE_INIT_V299_ANDROID_CAPTURE_HANDOFF_2026-05-19.md`
   - v299 결과: decision `android-capture-handoff-ready-needs-operator`, native rollback image와 Android boot candidate가 확인됐고 native bridge `version/status` PASS
   - v299 해석: Android property capture를 위해 boot partition 전환이 필요하므로 여기서 명시적 operator 승인 경계다. 승인 전 자동 reboot/flash는 하지 않는다
   - v300 계획서: `docs/plans/NATIVE_INIT_V300_ANDROID_CAPTURE_EXECUTOR_PLAN_2026-05-19.md`
   - v300 보고서: `docs/reports/NATIVE_INIT_V300_ANDROID_CAPTURE_EXECUTOR_2026-05-19.md`
   - v300 결과: decision `android-capture-executor-dryrun-ready`, 승인 없는 `run`은 `android-capture-executor-approval-required`로 거부됨
   - v300 해석: live Android handoff 실행기는 준비됐지만 `--allow-android-boot-flash --assume-yes --i-understand-native-rollback` 명시 승인 전까지 실행 금지
   - v301 계획서: `docs/plans/NATIVE_INIT_V301_PROPERTY_SHIM_SEED_PLAN_2026-05-19.md`
   - v301 보고서: `docs/reports/NATIVE_INIT_V301_PROPERTY_SHIM_SEED_2026-05-19.md`
   - v301 결과: decision `property-shim-seed-waiting-for-android`, `seed.json`은 생성됐지만 모든 selected key가 Android capture 부재로 blocked
   - v301 해석: 추가 host-only 모델은 준비됐고, 실제 unblock은 v300 live handoff로 Android capture를 얻는 것이다
   - v302 계획서: `docs/plans/NATIVE_INIT_V302_ANDROID_CAPTURE_APPROVAL_PACKET_PLAN_2026-05-19.md`
   - v302 보고서: `docs/reports/NATIVE_INIT_V302_ANDROID_CAPTURE_APPROVAL_PACKET_2026-05-19.md`
   - v302 결과: decision `android-capture-approval-ready`, v299/v300/current-native evidence를 묶은 final approval packet 생성
   - v302 pre-live audit: v300 executor와 `native_init_flash.py`가 explicit `--adb`/`--serial`을 Android capture 및 native rollback까지 전파하도록 보강했고, target-audit dry-run PASS
   - v302 해석: 이제 남은 것은 host-only 준비가 아니라 operator-approved live command 실행이다
   - v303 계획서: `docs/plans/NATIVE_INIT_V303_ANDROID_CAPTURE_POSTPROCESS_PLAN_2026-05-19.md`
   - v303 보고서: `docs/reports/NATIVE_INIT_V303_ANDROID_CAPTURE_POSTPROCESS_2026-05-19.md`
   - v303 결과: current decision `android-capture-postprocess-waiting-for-live`, synthetic ready path `android-capture-postprocess-seed-ready`
   - v303 해석: live 이후 v300/v297/v298/v301 결과 판독은 자동화됐고, 현재 blocker는 여전히 v300 live handoff 명시 승인이다
   - v304 계획서: `docs/plans/NATIVE_INIT_V304_ANDROID_CAPTURE_LIVE_GUARD_PLAN_2026-05-19.md`
   - v304 보고서: `docs/reports/NATIVE_INIT_V304_ANDROID_CAPTURE_LIVE_GUARD_2026-05-19.md`
   - v304 결과: decision `android-capture-live-guard-go`, v302 approval/v300 target propagation/image hash/native bridge/v303 waiting state PASS
   - v304 해석: host-side readiness is GO; destructive live handoff remains blocked only by explicit operator approval
   - v305 계획서: `docs/plans/NATIVE_INIT_V305_ANDROID_CAPTURE_RESCUE_DOCTOR_PLAN_2026-05-19.md`
   - v305 보고서: `docs/reports/NATIVE_INIT_V305_ANDROID_CAPTURE_RESCUE_DOCTOR_2026-05-19.md`
   - v305 결과: decision `native-ready`, rescue doctor generated live/rollback/capture operator aid commands without executing them
   - v306 계획서: `docs/plans/NATIVE_INIT_V306_ANDROID_CAPTURE_LIVE_RESULT_PLAN_2026-05-19.md`
   - v306 보고서: `docs/reports/NATIVE_INIT_V306_ANDROID_CAPTURE_LIVE_RESULT_2026-05-19.md`
   - v306 결과: approval-gated v300 live handoff PASS, Android property capture PASS, baseline compare READY, Android-backed seed READY, native v261 restored and verified
   - v306 해석: property shim 설계에 필요한 Android-backed required keys가 확보됐다. 다음 후보는 read-only property shim design이며, property runtime mutation/service-manager/HAL/Wi-Fi daemon/scan/connect는 계속 별도 safety gate 전까지 금지다
   - v307 계획서: `docs/plans/NATIVE_INIT_V307_PROPERTY_SHIM_DESIGN_PLAN_2026-05-19.md`
   - v307 보고서: `docs/reports/NATIVE_INIT_V307_PROPERTY_SHIM_DESIGN_2026-05-19.md`
   - v307 결과: decision `property-shim-design-model-ready`, selected next prototype `private-readonly-property-area`
   - v307 해석: 다음은 private namespace 안에서 read-only property area format/proof 모델을 만드는 것이며, global `/dev/__properties__`나 property service socket 생성은 여전히 금지다
   - v308 계획서: `docs/plans/NATIVE_INIT_V308_PRIVATE_PROPERTY_AREA_PROOF_PLAN_2026-05-19.md`
   - v308 보고서: `docs/reports/NATIVE_INIT_V308_PRIVATE_PROPERTY_AREA_PROOF_2026-05-19.md`
   - v308 결과: decision `private-property-area-proof-needs-format-source`
   - v308 해석: Android-backed seed는 read-only 모델 입력으로 유효하지만 property area binary layout과 serialized `property_info` compatibility가 아직 증명되지 않았다. 다음은 runtime node 생성이 아니라 AOSP source 기반 format extractor/proof이다
   - v309 계획서: `docs/plans/NATIVE_INIT_V309_PROPERTY_FORMAT_SOURCE_PROBE_PLAN_2026-05-19.md`
   - v309 보고서: `docs/reports/NATIVE_INIT_V309_PROPERTY_FORMAT_SOURCE_PROBE_2026-05-19.md`
   - v309 결과: decision `property-format-source-map-ready`
   - v309 해석: Android 12 AOSP source에서 property area constants, serialized `property_info` header/version, bionic `ContextsSerialized` read path를 확인했다. 다음은 여전히 host-only인 serializer/parser compatibility proof이며 runtime property file creation은 아직 금지다
   - v310 계획서: `docs/plans/NATIVE_INIT_V310_PROPERTY_SERIALIZER_PROOF_PLAN_2026-05-19.md`
   - v310 보고서: `docs/reports/NATIVE_INIT_V310_PROPERTY_SERIALIZER_PROOF_2026-05-19.md`
   - v310 결과: decision `property-serializer-proof-ready`
   - v310 해석: host-only `property_info`/`prop_area` binary roundtrip은 통과했다. 다만 synthetic context를 사용했으므로 다음은 실제 `property_contexts` 기반 context-aware mapping proof이며, runtime install은 아직 금지다
   - v311 계획서: `docs/plans/NATIVE_INIT_V311_PROPERTY_CONTEXT_MAPPING_PLAN_2026-05-19.md`
   - v311 보고서: `docs/reports/NATIVE_INIT_V311_PROPERTY_CONTEXT_MAPPING_2026-05-19.md`
   - v311 결과: decision `property-context-mapping-ready`
   - v311 해석: selected seed keys가 captured Android `property_contexts`로 실제 context/type에 매핑되고 context-aware `property_info` roundtrip도 통과했다. 다음은 live install이 아니라 private runtime layout package dry-run이다
   - v312 계획서: `docs/plans/NATIVE_INIT_V312_PRIVATE_PROPERTY_LAYOUT_PLAN_2026-05-19.md`
   - v312 보고서: `docs/reports/NATIVE_INIT_V312_PRIVATE_PROPERTY_LAYOUT_2026-05-19.md`
   - v312 결과: decision `private-property-layout-dryrun-ready`
   - v312 해석: private `/dev/__properties__` layout이 host-only로 생성/roundtrip 검증됐다. 다음은 실제 materialization이 아니라 명시적 approval packet 작성이며, live install/bind mount/daemon start는 계속 금지다
   - v313 계획서: `docs/plans/NATIVE_INIT_V313_PRIVATE_PROPERTY_MATERIALIZATION_APPROVAL_PLAN_2026-05-19.md`
   - v313 보고서: `docs/reports/NATIVE_INIT_V313_PRIVATE_PROPERTY_MATERIALIZATION_APPROVAL_2026-05-19.md`
   - v313 결과: decision `private-property-materialization-approval-ready`
   - v313 해석: 다음 v314는 live mutation boundary라서 `approve v314 private property namespace materialization only; no daemon start and no Wi-Fi bring-up` 문구의 명시 승인이 필요하다
   - v314 계획서: `docs/plans/NATIVE_INIT_V314_PRIVATE_PROPERTY_MATERIALIZATION_EXECUTOR_PLAN_2026-05-19.md`
   - v314 보고서: `docs/reports/NATIVE_INIT_V314_PRIVATE_PROPERTY_MATERIALIZATION_EXECUTOR_2026-05-19.md`
   - v314 결과: decisions `private-property-materialization-executor-plan-ready`, `private-property-materialization-executor-approval-required`, `private-property-materialization-executor-live-not-implemented`
   - v314 해석: executor scaffold가 future live sequence와 approval gate를 문서화했지만, v314는 device command/ADB command/generated file install/bind mount를 전혀 수행하지 않는다. 다음은 v315에서 더 작은 live-readonly proof를 둘지, 첫 private namespace materialization 구현으로 갈지 결정해야 한다
   - v315 계획서: `docs/plans/NATIVE_INIT_V315_PRIVATE_PROPERTY_LIVE_PREFLIGHT_PLAN_2026-05-19.md`
   - v315 보고서: `docs/reports/NATIVE_INIT_V315_PRIVATE_PROPERTY_LIVE_PREFLIGHT_2026-05-19.md`
   - v315 결과: decision `private-property-live-preflight-ready`
   - v315 해석: 실제 native v261 기기에서 version/status/selftest/storage/mountsd/logpath read-only preflight가 PASS했다. SD workspace는 rw 상태이고 netservice는 disabled, selftest는 fail=0이다. 다음 v316은 승인된 최소 private namespace copy/materialization proof 후보이며 daemon/Wi-Fi bring-up은 여전히 금지다
   - v316 계획서: `docs/plans/NATIVE_INIT_V316_PRIVATE_PROPERTY_LIVE_APPROVAL_PLAN_2026-05-19.md`
   - v316 보고서: `docs/reports/NATIVE_INIT_V316_PRIVATE_PROPERTY_LIVE_APPROVAL_2026-05-19.md`
   - v316 결과: decision `private-property-live-approval-ready`
   - v316 해석: v317 최소 private namespace proof의 승인 문구를 고정했다. 진행하려면 `approve v317 minimal private property namespace proof only; no daemon start and no Wi-Fi bring-up` 문구의 명시 승인이 필요하다
   - v317 계획서: `docs/plans/NATIVE_INIT_V317_PRIVATE_PROPERTY_NAMESPACE_PROOF_PLAN_2026-05-19.md`
   - v317 보고서: `docs/reports/NATIVE_INIT_V317_PRIVATE_PROPERTY_NAMESPACE_PROOF_2026-05-19.md`
   - v317 결과: decisions `private-property-namespace-proof-plan-ready`, `private-property-namespace-proof-approval-required`, `private-property-namespace-proof-audit-pass`, `private-property-namespace-proof-audit-selftest-pass`
   - v317 해석: runner는 구현됐고 plan/refusal/audit/selftest 검증은 PASS했다. 승인 후에도 범위는 `/mnt/sdext/a90/private-property-v317` private workdir 생성, v312 layout 파일 복사, SHA-256 검증, cleanup으로 제한한다. v316 승인 범위가 daemon start를 금지하므로 NCM/tcpctl 전송은 사용하지 않는다. 현재 전송 추정은 files 5, bytes 524988, chunks 471, estimated device commands 505이다
   - v318 계획서: `docs/plans/NATIVE_INIT_V318_PRIVATE_PROPERTY_TRANSFER_PRIMITIVE_PLAN_2026-05-19.md`
   - v318 보고서: `docs/reports/NATIVE_INIT_V318_PRIVATE_PROPERTY_TRANSFER_PRIMITIVE_2026-05-19.md`
   - v318 결과: decision `private-property-transfer-primitive-preflight-ready`
   - v318 해석: read-only live preflight에서 `toybox sh`가 없다는 사실을 확인했다. 따라서 v317 runner는 shell pipeline/base64 redirection이 아니라 `touch` + native `writefile` ASCII staging + `toybox uudecode -o` + `sha256sum` 방식으로 바뀌어야 한다
   - v319 계획서: `docs/plans/NATIVE_INIT_V319_SERIAL_TRANSFER_APPEND_PLAN_2026-05-19.md`
   - v319 보고서: `docs/reports/NATIVE_INIT_V319_SERIAL_TRANSFER_APPEND_2026-05-19.md`
   - v319 결과: `A90 Linux init 0.9.61 (v319)` 실기 플래시 PASS, scoped `appendfile` 추가, 4096-byte shell/cmdv1x buffer 적용, appendfile transfer smoke PASS
   - v319 해석: V317 runner는 이제 `appendfile` + `toybox uudecode -o` + `sha256sum` 방식으로 private workdir 전송을 수행할 준비가 됐다. live V317 proof는 여전히 exact approval phrase 없이는 실행되지 않는다
   - v320 계획서: `docs/plans/NATIVE_INIT_V320_PRIVATE_PROPERTY_LOOKUP_PROOF_PLAN_2026-05-19.md`
   - v320 보고서: `docs/reports/NATIVE_INIT_V320_PRIVATE_PROPERTY_LOOKUP_PROOF_2026-05-19.md`
   - v320 해석: V317 live PASS 후에만 진행하는 조건부 계획과 fail-closed host runner를 준비했다. 현재 runner는 V317 PASS evidence가 없으면 `private-property-lookup-blocked-v317-missing`으로 거부하며, 목표는 Android-linked read-only property reader를 private namespace 안에서 실행해 v317 private `/dev/__properties__` tree의 값을 읽을 수 있는지 확인하는 것이다. global property runtime, property service socket, daemon start, Wi-Fi bring-up은 계속 금지한다
   - v321 계획서: `docs/plans/NATIVE_INIT_V321_EXECNS_PROPERTY_LOOKUP_HELPER_PLAN_2026-05-19.md`
   - v321 보고서: `docs/reports/NATIVE_INIT_V321_EXECNS_PROPERTY_LOOKUP_HELPER_2026-05-19.md`
   - v321 해석: `a90_android_execns_probe v11`에 `property-lookup`/`system-getprop` helper support를 추가했다. 정적 ARM64 빌드와 marker 검증은 PASS했지만, live 실행은 아직 V317 PASS와 V320 approval gate 전까지 금지다
   - v322 계획서: `docs/plans/NATIVE_INIT_V322_PRIVATE_PROPERTY_LOOKUP_RUNNER_PLAN_2026-05-19.md`
   - v322 보고서: `docs/reports/NATIVE_INIT_V322_PRIVATE_PROPERTY_LOOKUP_RUNNER_2026-05-19.md`
   - v322 해석: V320 runner가 v321 helper command를 생성하고 future live run path를 갖도록 통합됐다. 현재 `plan`/approval-flagged `run` 모두 V317 PASS missing으로 차단되며 device command/mutation은 0이다
   - v323 계획서: `docs/plans/NATIVE_INIT_V323_PRIVATE_PROPERTY_CHAIN_AUDIT_PLAN_2026-05-19.md`
   - v323 보고서: `docs/reports/NATIVE_INIT_V323_PRIVATE_PROPERTY_CHAIN_AUDIT_2026-05-19.md`
   - v323 해석: host-only gate audit 결과 `private-property-chain-blocked-v317-missing`, audit PASS, chain_ready=false다. v312/v315/v316/v317-plan/v317-audit/v319/v321/v322는 PASS이고 남은 live blocker는 v317 PASS evidence뿐이다
   - v324 계획서: `docs/plans/NATIVE_INIT_V324_PRIVATE_PROPERTY_APPROVAL_REFRESH_PLAN_2026-05-19.md`
   - v324 보고서: `docs/reports/NATIVE_INIT_V324_PRIVATE_PROPERTY_APPROVAL_REFRESH_2026-05-19.md`
   - v324 해석: 최신 approval packet을 재생성했다. live_execution_approved=false, transfer estimate는 files 5 / bytes 524988 / chunks 471 / estimated commands 505이며 exact v317 phrase 없이는 실행하지 않는다
   - v325 계획서: `docs/plans/NATIVE_INIT_V325_EXECNS_HELPER_DEPLOY_PREFLIGHT_PLAN_2026-05-19.md`
   - v325 보고서: `docs/reports/NATIVE_INIT_V325_EXECNS_HELPER_DEPLOY_PREFLIGHT_2026-05-19.md`
   - v325 해석: `a90_android_execns_probe v11` fresh artifact를 private evidence에 빌드했고 deploy preflight PASS다. ignored default local helper는 아직 `v10` stale이므로, live deploy 시 v325 evidence artifact 또는 재빌드 산출물을 사용해야 한다
   - v326 계획서: `docs/plans/NATIVE_INIT_V326_PRIVATE_PROPERTY_CHAIN_V325_GATE_PLAN_2026-05-19.md`
   - v326 보고서: `docs/reports/NATIVE_INIT_V326_PRIVATE_PROPERTY_CHAIN_V325_GATE_2026-05-19.md`
   - v326 해석: chain audit에 `v325-fresh-helper-preflight` required gate를 추가했다. 현재 v312/v315/v316/v317-plan/v317-audit/v319/v321/v322/v325는 PASS이고, live blocker는 여전히 v317 PASS evidence missing이다
   - v327 계획서: `docs/plans/NATIVE_INIT_V327_PRIVATE_PROPERTY_APPROVAL_REFRESH_PLAN_2026-05-19.md`
   - v327 보고서: `docs/reports/NATIVE_INIT_V327_PRIVATE_PROPERTY_APPROVAL_REFRESH_2026-05-19.md`
   - v327 해석: approval refresh 기본 chain audit을 v326으로 올렸다. 최신 approval packet도 live_execution_approved=false이며 exact v317 phrase 없이는 실행하지 않는다
   - v328 계획서: `docs/plans/NATIVE_INIT_V328_V317_RUNNER_APPROVAL_REFRESH_GATE_PLAN_2026-05-19.md`
   - v328 보고서: `docs/reports/NATIVE_INIT_V328_V317_RUNNER_APPROVAL_REFRESH_GATE_2026-05-19.md`
   - v328 해석: V317 runner가 v327 approval refresh manifest를 blocker로 요구하도록 조정했다. plan은 PASS, run-without-approval은 approval-required로 fail-closed이며 device command/mutation은 없다
   - v329 계획서: `docs/plans/NATIVE_INIT_V329_WIFI_READINESS_DASHBOARD_PLAN_2026-05-19.md`
   - v329 보고서: `docs/reports/NATIVE_INIT_V329_WIFI_READINESS_DASHBOARD_2026-05-19.md`
   - v329 해석: Wi-Fi readiness dashboard를 host-only로 생성했다. 현재 decision은 `wifi-readiness-dashboard-ready-blocked-by-v317`이며, vendor assets/property layout은 준비됐지만 CNSS start-only 반복은 유효하지 않고 service-manager는 property runtime/process prerequisites로 막혀 있다
   - v330 계획서: `docs/plans/NATIVE_INIT_V330_WIFI_EVIDENCE_FRESHNESS_PLAN_2026-05-19.md`
   - v330 보고서: `docs/reports/NATIVE_INIT_V330_WIFI_EVIDENCE_FRESHNESS_2026-05-19.md`
   - v330 해석: V325-V329 evidence를 current clean git head에서 재생성했는지 audit했다. decision은 `wifi-evidence-freshness-clean`이며 device command/mutation은 없다
   - v331 계획서: `docs/plans/NATIVE_INIT_V331_V317_LIVE_READINESS_PACKET_PLAN_2026-05-19.md`
   - v331 보고서: `docs/reports/NATIVE_INIT_V331_V317_LIVE_READINESS_PACKET_2026-05-19.md`
   - v331 해석: V317 live proof용 operator handoff packet을 host-only로 만들었다. exact approval phrase가 제공되기 전까지 live_execution_approved=false이며 device command/mutation은 없다
   - v332 계획서: `docs/plans/NATIVE_INIT_V332_CURRENT_READONLY_LIVE_PREFLIGHT_PLAN_2026-05-19.md`
   - v332 보고서: `docs/reports/NATIVE_INIT_V332_CURRENT_READONLY_LIVE_PREFLIGHT_2026-05-19.md`
   - v332 해석: 현재 연결된 native device에서 read-only V317 preflight가 PASS했다. native version `A90 Linux init 0.9.61 (v319)`, SD writable, selftest fail=0, netservice disabled, logpath on SD 확인. device mutation은 없다
   - v333 계획서: `docs/plans/NATIVE_INIT_V333_POST_V317_ROUTER_PLAN_2026-05-19.md`
   - v333 보고서: `docs/reports/NATIVE_INIT_V333_POST_V317_ROUTER_2026-05-19.md`
   - v333 해석: V317 결과 라우터를 host-only로 추가했다. 현재 decision은 `post-v317-router-awaiting-v317`이며, V317 PASS 전에는 V320 property lookup을 실행하지 않는다
   - v334 계획서: `docs/plans/NATIVE_INIT_V334_WIFI_EVIDENCE_FRESHNESS_EXPANSION_PLAN_2026-05-19.md`
   - v334 보고서: `docs/reports/NATIVE_INIT_V334_WIFI_EVIDENCE_FRESHNESS_EXPANSION_2026-05-19.md`
   - v334 해석: freshness audit 범위를 V325-V333으로 확장했다. current clean head에서 전체 approval 직전 evidence가 fresh인지 확인한다
   - v335 계획서: `docs/plans/NATIVE_INIT_V335_WIFI_APPROVAL_GATE_REGRESSION_PLAN_2026-05-19.md`
   - v335 보고서: `docs/reports/NATIVE_INIT_V335_WIFI_APPROVAL_GATE_REGRESSION_2026-05-19.md`
   - v335 해석: V317/V320 approval gate regression을 host-only로 추가했다. partial approval과 V320-before-V317은 device command/mutation 없이 거부된다
   - v336 계획서: `docs/plans/NATIVE_INIT_V336_V317_PRELIVE_GATE_AUDIT_PLAN_2026-05-19.md`
   - v336 보고서: `docs/reports/NATIVE_INIT_V336_V317_PRELIVE_GATE_AUDIT_2026-05-19.md`
   - v336 해석: V325-V335 gate evidence를 통합 감사했다. 현재 remaining blocker는 `exact-v317-approval-phrase` 하나이며, V317 live proof 자체는 아직 실행하지 않았다
   - v337 계획서: `docs/plans/NATIVE_INIT_V337_V317_RUNNER_PRELIVE_GATE_PLAN_2026-05-19.md`
   - v337 보고서: `docs/reports/NATIVE_INIT_V337_V317_RUNNER_PRELIVE_GATE_2026-05-19.md`
   - v337 해석: V317 runner가 exact approval만으로 실행되지 않도록 V336 pre-live gate와 clean current HEAD를 추가로 요구하게 했다. dirty-tree exact approval은 device command 없이 blocked 처리된다
   - v338 계획서: `docs/plans/NATIVE_INIT_V338_V317_READINESS_PACKET_V336_AWARE_PLAN_2026-05-19.md`
   - v338 보고서: `docs/reports/NATIVE_INIT_V338_V317_READINESS_PACKET_V336_AWARE_2026-05-19.md`
   - v338 해석: V317 readiness packet이 V336 pre-live gate를 명시적으로 확인하고 generated live command에 `--prelive-gate-manifest`를 포함하도록 갱신했다
   - v339 계획서: `docs/plans/NATIVE_INIT_V339_V317_LIVE_SURFACE_LINTER_PLAN_2026-05-19.md`
   - v339 보고서: `docs/reports/NATIVE_INIT_V339_V317_LIVE_SURFACE_LINTER_2026-05-19.md`
   - v339 해석: V317 runner의 `device_cmd()` 호출 표면을 AST로 검사해 허용된 private-workdir 파일 작업만 남아 있음을 확인했다
   - v340 계획서: `docs/plans/NATIVE_INIT_V340_V317_FINAL_HANDOFF_PACKET_PLAN_2026-05-19.md`
   - v340 보고서: `docs/reports/NATIVE_INIT_V340_V317_FINAL_HANDOFF_PACKET_2026-05-19.md`
   - v340 해석: V331/V336/V339를 단일 operator handoff packet으로 묶었다. 남은 blocker는 `exact-v317-approval-phrase` 하나다
   - v341 계획서: `docs/plans/NATIVE_INIT_V341_HANDOFF_REQUIRES_CURRENT_PRELIVE_PLAN_2026-05-19.md`
   - v341 보고서: `docs/reports/NATIVE_INIT_V341_HANDOFF_REQUIRES_CURRENT_PRELIVE_2026-05-19.md`
   - v341 해석: V340 handoff가 runner와 동일하게 V336 pre-live gate를 current clean HEAD로 요구하도록 수정했다. stale V336은 handoff 단계에서 blocked 된다
   - v342 계획서: `docs/plans/NATIVE_INIT_V342_V317_APPROVED_PREFLIGHT_PLAN_2026-05-19.md`
   - v342 보고서: `docs/reports/NATIVE_INIT_V342_V317_APPROVED_PREFLIGHT_2026-05-19.md`
   - v342 해석: V317 runner에 no-device-command `preflight` 모드를 추가하고 handoff packet에 preflight command와 current-tree-clean check를 추가했다
   - v343 계획서: `docs/plans/NATIVE_INIT_V343_BREAK_V331_V336_CYCLE_PLAN_2026-05-19.md`
   - v343 보고서: `docs/reports/NATIVE_INIT_V343_BREAK_V331_V336_CYCLE_2026-05-19.md`
   - v343 해석: V342 후 발견된 V331/V336/V333 순환 의존성을 끊었다. clean HEAD `da70622`에서 V336/V331/V339/V340과 approved preflight가 PASS했고 남은 blocker는 exact V317 approval phrase 하나다
   - v344 계획서: `docs/plans/NATIVE_INIT_V344_V317_GATE_REFRESH_PLAN_2026-05-19.md`
   - v344 보고서: `docs/reports/NATIVE_INIT_V344_V317_GATE_REFRESH_2026-05-19.md`
   - v344 해석: V317 approval 직전 evidence refresh 순서를 `wifi_v317_gate_refresh.py`로 자동화했다. clean current HEAD에서 optional approved preflight 포함 PASS했고, live proof는 여전히 exact approval phrase 없이는 실행하지 않는다
   - v345 계획서: `docs/plans/NATIVE_INIT_V345_POST_V317_ROUTER_REGRESSION_PLAN_2026-05-19.md`
   - v345 보고서: `docs/reports/NATIVE_INIT_V345_POST_V317_ROUTER_REGRESSION_2026-05-19.md`
   - v345 해석: V317 live proof 이후 V333 router가 PASS/cleanup/failure/manual-review/prereq-blocked 결과를 안전하게 분기하는지 host-only synthetic regression으로 검증했다
   - v346 계획서: `docs/plans/NATIVE_INIT_V346_HANDOFF_PREFLIGHT_OUTDIR_PLAN_2026-05-19.md`
   - v346 보고서: `docs/reports/NATIVE_INIT_V346_HANDOFF_PREFLIGHT_OUTDIR_2026-05-19.md`
   - v346 해석: V340 generated preflight command가 live V317 result path를 오염시키지 않도록 별도 preflight out-dir을 쓰게 수정했고, generated preflight command 자체가 no-device PASS임을 확인했다
   - v347 계획서: `docs/plans/NATIVE_INIT_V347_GATE_REFRESH_GENERATED_PREFLIGHT_PLAN_2026-05-19.md`
   - v347 보고서: `docs/reports/NATIVE_INIT_V347_GATE_REFRESH_GENERATED_PREFLIGHT_2026-05-19.md`
   - v347 해석: `wifi_v317_gate_refresh.py --run-approved-preflight`가 V340 manifest의 generated preflight command까지 직접 실행해 검증하도록 확장했고, clean HEAD에서 direct/generated preflight 모두 PASS했다
   - v348 계획서: `docs/plans/NATIVE_INIT_V348_HANDOFF_COMMAND_CONTRACT_PLAN_2026-05-19.md`
   - v348 보고서: `docs/reports/NATIVE_INIT_V348_HANDOFF_COMMAND_CONTRACT_2026-05-19.md`
   - v348 해석: V340 generated preflight/live/cleanup command의 script/subcommand/out-dir/approval/gate contract를 host-only linter로 검증했다
   - v349 계획서: `docs/plans/NATIVE_INIT_V349_FINAL_READINESS_AGGREGATOR_PLAN_2026-05-19.md`
   - v349 보고서: `docs/reports/NATIVE_INIT_V349_FINAL_READINESS_AGGREGATOR_2026-05-19.md`
   - v349 해석: V344 refresh, V345 router regression, V348 command contract를 하나로 묶는 final readiness aggregator를 추가했고 clean HEAD에서 PASS했다
   - v350 계획서: `docs/plans/NATIVE_INIT_V350_V317_OPERATOR_CHECKLIST_PLAN_2026-05-19.md`
   - v350 보고서: `docs/reports/NATIVE_INIT_V350_V317_OPERATOR_CHECKLIST_2026-05-19.md`
   - v350 해석: V340 live/cleanup command와 V349 final readiness를 사람이 실행하기 쉬운 operator checklist로 결합했고 clean HEAD에서 PASS했다
   - v351 계획서: `docs/plans/NATIVE_INIT_V351_V317_LIVE_EXECUTOR_PLAN_2026-05-19.md`
   - v351 보고서: `docs/reports/NATIVE_INIT_V351_V317_LIVE_EXECUTOR_2026-05-19.md`
   - v351 해석: V350 checklist를 직접 실행하는 fail-closed executor guard를 추가했고 clean HEAD `plan`이 PASS했다. 승인 없는 `run`은 즉시 거부된다
   - v352 계획서: `docs/plans/NATIVE_INIT_V352_V317_LIVE_EXECUTOR_REGRESSION_PLAN_2026-05-19.md`
   - v352 보고서: `docs/reports/NATIVE_INIT_V352_V317_LIVE_EXECUTOR_REGRESSION_2026-05-19.md`
   - v352 해석: V351 executor의 no-approval/partial-approval/plan 경로를 host-only regression으로 고정했고 clean HEAD에서 PASS했다
   - v353 계획서: `docs/plans/NATIVE_INIT_V353_OPERATOR_EXECUTOR_PREFERENCE_PLAN_2026-05-19.md`
   - v353 보고서: `docs/reports/NATIVE_INIT_V353_OPERATOR_EXECUTOR_PREFERENCE_2026-05-19.md`
   - v353 해석: V350 operator checklist의 기본 실행 경로를 raw V340 command가 아니라 V351 executor로 전환했고 clean HEAD에서 V350/V351/V352 PASS했다
   - v354 계획서: `docs/plans/NATIVE_INIT_V354_CLEANUP_APPROVAL_REGRESSION_PLAN_2026-05-19.md`
   - v354 보고서: `docs/reports/NATIVE_INIT_V354_CLEANUP_APPROVAL_REGRESSION_2026-05-19.md`
   - v354 해석: V351 cleanup 경로의 phrase-only/flags-only partial approval 회귀를 추가했고 clean HEAD에서 PASS했다
   - v355 계획서: `docs/plans/NATIVE_INIT_V355_APPROVAL_MATRIX_REGRESSION_PLAN_2026-05-19.md`
   - v355 보고서: `docs/reports/NATIVE_INIT_V355_APPROVAL_MATRIX_REGRESSION_2026-05-19.md`
   - v355 해석: V351 run/cleanup 경로에서 exact phrase가 있어도 mutation 확인 플래그 하나가 빠진 조합을 거부하는 회귀를 추가했고 clean HEAD에서 PASS했다
   - v356 계획서: `docs/plans/NATIVE_INIT_V356_WRONG_PHRASE_REGRESSION_PLAN_2026-05-19.md`
   - v356 보고서: `docs/reports/NATIVE_INIT_V356_WRONG_PHRASE_REGRESSION_2026-05-19.md`
   - v356 해석: mutation flags가 모두 있어도 exact phrase가 아니면 거부하는 회귀를 추가했고 clean HEAD에서 PASS했다
   - v357 계획서: `docs/plans/NATIVE_INIT_V357_PREAPPROVAL_AUDIT_PLAN_2026-05-19.md`
   - v357 보고서: `docs/reports/NATIVE_INIT_V357_PREAPPROVAL_AUDIT_2026-05-19.md`
   - v357 해석: V349/V350/V351-plan/V352-regression을 한 번 더 묶어 clean HEAD/current evidence/no-device-action/exact-approval-only 상태인지 확인하는 host-only pre-approval audit를 추가했고 clean HEAD에서 PASS했다
   - v358 계획서: `docs/plans/NATIVE_INIT_V358_APPROVAL_SUDO_BOUNDARY_PLAN_2026-05-19.md`
   - v358 보고서: `docs/reports/NATIVE_INIT_V358_APPROVAL_SUDO_BOUNDARY_2026-05-19.md`
   - v358 해석: V317 live 전 host-only/no-sudo, host-sudo, exact approval required, separate approval required 명령군을 운영 문서로 고정했고 clean HEAD V357 audit도 계속 PASS했다
   - v359 계획서: `docs/plans/NATIVE_INIT_V359_LIVE_BLOCKER_SNAPSHOT_PLAN_2026-05-19.md`
   - v359 보고서: `docs/reports/NATIVE_INIT_V359_LIVE_BLOCKER_SNAPSHOT_2026-05-19.md`
   - v359 해석: V357/V350을 기반으로 live blocker 상태를 manifest로 남겨 exact approval phrase만 남았는지 재확인했고 clean HEAD에서 PASS했다
   - v317 live 해석: exact approval phrase 수신 후 V351 executor `run --timeout 900`으로 minimal private property namespace proof를 실행했고 `private-property-namespace-proof-pass` / `post-v317-router-v320-ready`를 확인했다
   - v320/v323 해석: V317 PASS 이후 V320 plan은 `private-property-lookup-plan-ready`, V323 chain audit는 `private-property-chain-ready-for-v320-approval`로 전환됐다. 이후 exact V320 approval phrase로 live lookup을 실행했고, stale v10 helper와 unmounted `/mnt/system` 실패를 거쳐 v11 helper serial deploy + `mountsystem ro` 조건에서 `private-property-lookup-getprop-pass`를 확인했다
   - v320 결과: private property namespace 안에서 `/system/bin/getprop`가 allowlisted 4개 property를 v312 expected value와 동일하게 읽었다. 이는 property lookup 조건이 충족됐다는 뜻이며, daemon start/Wi-Fi bring-up 승인은 아직 아니다
   - v360 계획서: `docs/plans/NATIVE_INIT_V360_CNSS_PRESTART_RUNNER_REFRESH_PLAN_2026-05-19.md`
   - v360 보고서: `docs/reports/NATIVE_INIT_V360_CNSS_PRESTART_RUNNER_REFRESH_2026-05-19.md`
   - v360 해석: V320에서 배포된 v11 helper SHA를 CNSS start-only runner 기본값으로 반영했다. no-start `plan`/`preflight`/`dry-run`은 모두 PASS했고 `daemon_start_executed=false`를 유지했다
   - v361 계획서: `docs/plans/NATIVE_INIT_V361_CNSS_START_ONLY_APPROVAL_PACKET_PLAN_2026-05-19.md`
   - v361 보고서: `docs/reports/NATIVE_INIT_V361_CNSS_START_ONLY_APPROVAL_PACKET_2026-05-19.md`
   - v361 해석: v11 helper 기준 approval packet을 재생성했고 `live-approval-packet-ready` PASS, helper no-allow fail-closed PASS, `daemon_start_executed=false`를 확인했다. 생성된 future command는 별도 bounded start-only 승인 전까지 실행하지 않는다
   - v362 계획서: `docs/plans/NATIVE_INIT_V362_CNSS_START_ONLY_LIVE_PLAN_2026-05-20.md`
   - v362 보고서: `docs/reports/NATIVE_INIT_V362_CNSS_START_ONLY_LIVE_2026-05-20.md`
   - v362 해석: 별도 daemon start 요청 후 bounded `cnss-daemon -n -l` start-only live run을 1회 실행했고 `start-only-pass` / `cnss-start-only-evidence-classified` / `cnss-warning-disposition-ready`를 확인했다
   - v362 결과: child observable, timeout 후 SIGTERM/SIGKILL/reap, `postflight_safe=1`, postflight process count/running/zombie `0`, `/proc/net/dev`와 `wifiinv full`에서 `wlan*`/wlan-like interface 없음, `scan_connect_linkup=0`
   - v362 경계: 이 결과는 CNSS daemon start-only 가능성만 의미한다. Wi-Fi scan/connect/link-up/credential/DHCP/routing/supplicant/wificond/hostapd/Wi-Fi HAL은 별도 계획과 승인 전까지 계속 blocked
   - v363 계획서: `docs/plans/NATIVE_INIT_V363_WIFI_BRINGUP_PHASE0_PLAN_2026-05-20.md`
   - v363 보고서: `docs/reports/NATIVE_INIT_V363_WIFI_BRINGUP_PHASE0_2026-05-20.md`
   - v363 해석: Wi-Fi bring-up 방향은 수락됐지만 첫 단계는 no-scan/no-connect baseline gate로 제한했다. live baseline은 `wifi-bringup-phase0-live-baseline-ready` PASS
   - v363 결과: `wlan` module present, ICNSS core bound, QCA6390 node present but driver link absent, no `wlan*`, no Wi-Fi rfkill, no CNSS process leak
   - v363 다음: V364 no-scan/no-connect HAL/service-manager readiness gate. CNSS 단독 반복보다 Android Wi-Fi HAL/service-manager/property/Binder chain을 좁히는 것이 다음 병목이다
   - v364 계획서: `docs/plans/NATIVE_INIT_V364_HAL_SERVICE_READINESS_GATE_PLAN_2026-05-20.md`
   - v364 보고서: `docs/reports/NATIVE_INIT_V364_HAL_SERVICE_READINESS_GATE_2026-05-20.md`
   - v364 해석: V292/V320/V362/V363 선행 증거는 PASS지만 live gate는 `hal-service-readiness-blocked`로 판정됐다. 현재 Binder devnodes, service-manager process, mutable property runtime, linkerconfig visibility가 없다
   - v364 결과: no `wlan*`, no Wi-Fi rfkill, no CNSS process leak은 유지됐다. service binary visibility는 partial이고 Wi-Fi VINTF metadata는 present다
   - v364 다음: V365 bounded Binder/property/linker namespace readiness repair or approval packet. Wi-Fi HAL/service-manager start-only도 아직 별도 계획 전까지 blocked
   - v365 계획서: `docs/plans/NATIVE_INIT_V365_SERVICE_RUNTIME_REPAIR_PACKET_PLAN_2026-05-20.md`
   - v365 보고서: `docs/reports/NATIVE_INIT_V365_SERVICE_RUNTIME_REPAIR_PACKET_2026-05-20.md`
   - v365 해석: V364 blocker를 V366 no-daemon repair smoke packet으로 전환했다. helper, real linkerconfig, private property root, system root, service-manager binaries는 준비됐고 `/dev/block/sda29`는 `/proc/partitions` `259:13` 기반 temporary `mknodb` 후보로 정리됐다
   - v365 결과: `service-runtime-repair-packet-ready`, next approval phrase `approve v366 bounded runtime repair smoke only; no service-manager start and no Wi-Fi bring-up`
   - v365 다음: V366 bounded temporary device-node + private property/linker repair smoke. 아직 service-manager/HAL/scan/connect는 blocked
   - v366 계획서: `docs/plans/NATIVE_INIT_V366_RUNTIME_REPAIR_SMOKE_PLAN_2026-05-20.md`
   - v366 보고서: `docs/reports/NATIVE_INIT_V366_RUNTIME_REPAIR_SMOKE_2026-05-20.md`
   - v366 해석: guarded runtime repair smoke runner를 추가했고 plan/preflight/no-approval refusal 경로를 검증했다. no-approval run은 `runtime-repair-smoke-approval-required`로 PASS했고 mutation step은 실행하지 않았다. 이후 `preexisting-temp-nodes` blocker를 추가해 기존 `/dev` 노드가 있으면 승인 실행도 막도록 보강했다
   - v366 다음: exact phrase `approve v366 bounded runtime repair smoke only; no service-manager start and no Wi-Fi bring-up`가 들어오기 전까지 temporary `/dev` node 생성/property lookup smoke도 보류한다
   - v367 계획서: `docs/plans/NATIVE_INIT_V367_RUNTIME_REPAIR_SMOKE_REGRESSION_PLAN_2026-05-20.md`
   - v367 보고서: `docs/reports/NATIVE_INIT_V367_RUNTIME_REPAIR_SMOKE_REGRESSION_2026-05-20.md`
   - v367 해석: V366 승인 경로에서 preexisting-node blocker가 mutation 전에 평가되도록 순서를 수정했고, host-only synthetic regression으로 no-approval/wrong-phrase/clean-approved/preexisting-approved 케이스를 검증했다
   - v368 계획서: `docs/plans/NATIVE_INIT_V368_RUNTIME_REPAIR_CLEANUP_GATE_PLAN_2026-05-20.md`
   - v368 보고서: `docs/reports/NATIVE_INIT_V368_RUNTIME_REPAIR_CLEANUP_GATE_2026-05-20.md`
   - v368 해석: cleanup도 device mutation이므로 exact phrase + `--apply --assume-yes` 없이는 실행하지 않게 막았다. live cleanup refusal은 `steps=[]`로 PASS했다
   - v369 계획서: `docs/plans/NATIVE_INIT_V369_RUNTIME_REPAIR_APPROVAL_PACKET_PLAN_2026-05-20.md`
   - v369 보고서: `docs/reports/NATIVE_INIT_V369_RUNTIME_REPAIR_APPROVAL_PACKET_2026-05-20.md`
   - v369 해석: V366 live smoke approval packet을 생성했고, preflight/run-refusal/cleanup-refusal/regression과 run/cleanup command contract가 PASS했다. packet 자체는 `live_execution_approved=false`이며 실제 smoke는 아직 실행하지 않았다
   - v370 계획서: `docs/plans/NATIVE_INIT_V370_RUNTIME_REPAIR_RESULT_ROUTER_PLAN_2026-05-20.md`
   - v370 보고서: `docs/reports/NATIVE_INIT_V370_RUNTIME_REPAIR_RESULT_ROUTER_2026-05-20.md`
   - v370 해석: V366 live smoke 결과 router를 추가했고 현재 상태는 `runtime-repair-smoke-router-awaiting-approval`이다. live smoke가 PASS하면 다음은 service-manager start-only approval packet이고, HAL/scan/connect는 여전히 별도 승인 전까지 금지다
   - v371 계획서: `docs/plans/NATIVE_INIT_V371_RUNTIME_REPAIR_SMOKE_LIVE_EXECUTOR_PLAN_2026-05-20.md`
   - v371 보고서: `docs/reports/NATIVE_INIT_V371_RUNTIME_REPAIR_SMOKE_LIVE_EXECUTOR_2026-05-20.md`
   - v371 해석: exact V366 approval phrase 이후 V371 executor로 bounded runtime repair smoke를 실행했고 `runtime-repair-smoke-live-executor-run-pass` / `runtime-repair-smoke-router-service-runtime-next-ready`를 확인했다. temporary `/dev/block/sda29`/binder node 생성, private property lookup, cleanup, postflight cleanliness까지만 수행했고 service-manager/HAL/scan/connect는 실행하지 않았다
   - v371 다음: separate service-manager start-only approval packet 작성. 이 단계도 Wi-Fi HAL start, scan/connect/link-up/credential/DHCP/routing은 제외해야 한다
   - v372 계획서: `docs/plans/NATIVE_INIT_V372_SERVICE_MANAGER_START_ONLY_APPROVAL_PACKET_PLAN_2026-05-20.md`
   - v372 보고서: `docs/reports/NATIVE_INIT_V372_SERVICE_MANAGER_START_ONLY_APPROVAL_PACKET_2026-05-20.md`
   - v372 해석: V371/V366 PASS와 현재 read-only native state를 묶어 `service-manager-start-only-approval-packet-ready`를 확인했다. `servicemanager`/`hwservicemanager` binary visible, service-manager process clean, Wi-Fi link clean, temporary Binder nodes cleaned 상태다
   - v372 다음: V373 fail-closed service-manager start-only smoke runner 구현. required phrase는 `approve v373 service-manager start-only smoke only; no Wi-Fi HAL start and no Wi-Fi bring-up`
   - v373 계획서: `docs/plans/NATIVE_INIT_V373_SERVICE_MANAGER_START_ONLY_SMOKE_PLAN_2026-05-20.md`
   - v373 보고서: `docs/reports/NATIVE_INIT_V373_SERVICE_MANAGER_START_ONLY_SMOKE_2026-05-20.md`
   - v373 해석: service-manager start-only runner scaffold를 추가했고 no-approval run은 `service-manager-start-only-smoke-approval-required` / `steps=0`으로 막혔다. preflight는 read-only로 PASS 조건을 확인했지만 `helper-service-manager-mode` 부재로 mutation 전 blocked 됐다
   - v373 다음: V374에서 `a90_android_execns_probe`에 bounded service-manager start-only mode를 추가하거나 동등한 fail-closed primitive를 설계한다
   - v374 계획서: `docs/plans/NATIVE_INIT_V374_EXECNS_SERVICE_MANAGER_MODE_PLAN_2026-05-20.md`
   - v374 보고서: `docs/reports/NATIVE_INIT_V374_EXECNS_SERVICE_MANAGER_MODE_2026-05-20.md`
   - v374 해석: `a90_android_execns_probe v12` source와 로컬 static ARM64 artifact를 만들었고 `service-manager-start-only`, `--allow-service-manager-start-only`, `system-servicemanager`, `system-hwservicemanager` 문자열을 확인했다. 아직 `/cache/bin` 배포나 daemon start는 하지 않았다
   - v374 다음: V375 helper deploy/preflight packet. v12를 `/cache/bin/a90_android_execns_probe`에 설치/검증하고 V373 preflight를 재실행하되 service-manager live start는 여전히 별도 exact approval 전까지 blocked
   - v375 계획서: `docs/plans/NATIVE_INIT_V375_EXECNS_HELPER_V12_DEPLOY_PREFLIGHT_PLAN_2026-05-20.md`
   - v375 보고서: `docs/reports/NATIVE_INIT_V375_EXECNS_HELPER_V12_DEPLOY_PREFLIGHT_2026-05-20.md`
   - v375 해석: fail-closed helper deploy/preflight runner를 추가했고, NCM host IP 불안정 상황을 serial `appendfile` + `toybox uudecode -o` fallback으로 보강했다. exact phrase 이후 `/cache/bin/a90_android_execns_probe`를 v12로 설치했고 remote SHA/marker/service-manager mode를 확인했다
   - v375 결과: `execns-helper-v12-deploy-pass`, remote SHA `fef21de2897b16e4ead7fe780eff1817675d4ce988e558013ac9a37dc928d918`, V373 post-deploy preflight `service-manager-start-only-smoke-approval-required`, `helper-service-manager-mode` PASS, daemon start/Wi-Fi bring-up 없음
   - v375 다음: 별도 exact phrase `approve v373 service-manager start-only smoke only; no Wi-Fi HAL start and no Wi-Fi bring-up`가 있을 때만 V373 service-manager start-only smoke를 실행한다. Wi-Fi HAL/scan/connect/link-up/credential/DHCP/routing은 계속 blocked

   - v376 계획서: `docs/plans/NATIVE_INIT_V376_SERVICE_MANAGER_START_ONLY_LIVE_RUNNER_PLAN_2026-05-20.md`
   - v376 보고서: `docs/reports/NATIVE_INIT_V376_SERVICE_MANAGER_START_ONLY_LIVE_RUNNER_2026-05-20.md`
   - v376 해석: V375 helper v12 배포 이후 service-manager start-only live runner 실행 본문을 추가했다. plan/preflight/no-approval refusal은 PASS했고, generic approval은 거부된다. live start는 exact phrase `approve v373 service-manager start-only smoke only; no Wi-Fi HAL start and no Wi-Fi bring-up` + `--apply --assume-yes` 없이는 실행하지 않는다
   - v376 결과: exact phrase 이후 approved live run을 실행했고 `service-manager-start-only-live-runtime-gap`이 나왔다. 두 target 모두 `SIGABRT`로 종료했으며 첫 hard blocker는 helper namespace 안의 `/dev/binder` 부재다. postflight는 clean이고 Wi-Fi bring-up은 없음
   - v376 다음: runtime-gap을 분류/수정하기 전 HAL start-only approval packet은 금지한다. Wi-Fi HAL/scan/connect/link-up/credential/DHCP/routing은 계속 blocked

   - v377 계획서: `docs/plans/NATIVE_INIT_V377_SERVICE_MANAGER_RESULT_ROUTER_PLAN_2026-05-20.md`
   - v377 보고서: `docs/reports/NATIVE_INIT_V377_SERVICE_MANAGER_RESULT_ROUTER_2026-05-20.md`
   - v377 해석: V376 result router를 host-only로 추가했다. synthetic regression은 PASS했고 approved V376 evidence route는 `service-manager-start-only-router-runtime-gap`이다. device command/mutation 없이 runtime-gap classification 필요성을 명확히 분류한다
   - v377 다음: V378 runtime-gap classifier/repair planning. 현재 직접 원인은 Binder driver `/dev/binder` open 실패이며, helper private namespace에서 Binder devnode를 안전하게 provisioning하는 방향이 우선이다

   - v378 계획서: `docs/plans/NATIVE_INIT_V378_SERVICE_MANAGER_RUNTIME_GAP_CLASSIFIER_PLAN_2026-05-20.md`
   - v378 보고서: `docs/reports/NATIVE_INIT_V378_SERVICE_MANAGER_RUNTIME_GAP_CLASSIFIER_2026-05-20.md`
   - v378 해석: V376 runtime-gap을 host-only로 분류했고 decision은 `service-manager-runtime-gap-binder-devnode-required`다. current Binder metadata refresh도 `binder-devnode-plan-ready`로, `/dev/binder c 10 81`, `/dev/hwbinder c 10 80`, `/dev/vndbinder c 10 79` 후보가 유지된다
   - v378 다음: V379에서 service-manager start-only helper namespace 안에 private Binder devnode provisioning을 추가한다. binderfs는 별도 mount/ioctl 정책이 필요하므로 우선 static misc devnode 방식이 더 작다
   - live daemon start 범위를 벗어나는 Wi-Fi scan/connect/link-up/credential/DHCP/routing은 별도 계획과 승인 전까지 blocked

   - v379 계획서: `docs/plans/NATIVE_INIT_V379_EXECNS_PRIVATE_BINDER_DEVNODES_PLAN_2026-05-20.md`
   - v379 보고서: `docs/reports/NATIVE_INIT_V379_EXECNS_PRIVATE_BINDER_DEVNODES_2026-05-20.md`
   - v379 해석: `a90_android_execns_probe v13` 로컬 static helper에 service-manager start-only 전용 private `/dev/binder`, `/dev/hwbinder`, `/dev/vndbinder` provisioning을 추가했다. helper child는 Android `system` uid로 drop되므로 private Binder nodes는 `0666`으로 만든다. 아직 `/cache/bin` 배포나 daemon start는 하지 않았다
   - v379 다음: V380에서 v13 helper를 배포/검증하고, 별도 live 승인 범위에서 bounded service-manager start-only를 재실행한다

   - v380 계획서: `docs/plans/NATIVE_INIT_V380_EXECNS_HELPER_V13_DEPLOY_LIVE_PLAN_2026-05-20.md`
   - v380 보고서: `docs/reports/NATIVE_INIT_V380_EXECNS_HELPER_V13_DEPLOY_LIVE_2026-05-20.md`
   - v380 해석: v13 helper를 `/cache/bin/a90_android_execns_probe`에 serial fallback으로 배포했고 remote SHA를 확인했다. 승인된 bounded service-manager start-only에서 `hwservicemanager`는 timeout까지 관찰 후 clean stop 됐고, `servicemanager`는 SIGABRT로 runtime-gap이다. private Binder nodes는 helper namespace 안에 정상 생성됐으므로 Binder blocker는 해소됐다
   - v380 다음: classifier decision은 `service-manager-runtime-gap-property-runtime-required`다. V381에서 private `/dev/__properties__`와 최소 `/data` runtime materialization을 설계한다. Wi-Fi HAL/start/bring-up은 계속 blocked

   - v381 계획서: `docs/plans/NATIVE_INIT_V381_EXECNS_SERVICE_PROPERTY_RUNTIME_PLAN_2026-05-20.md`
   - v381 보고서: `docs/reports/NATIVE_INIT_V381_EXECNS_SERVICE_PROPERTY_RUNTIME_2026-05-20.md`
   - v381 해석: `a90_android_execns_probe v14` 로컬 static helper에서 service-manager start-only mode가 `--property-root`를 받을 수 있게 했다. 기존 V317 private `/dev/__properties__`를 helper temp-root에 read-only bind하고, 다음 live smoke에서 `--data-wifi-mode private-empty`로 최소 `/data` tree를 제공할 수 있다. 아직 `/cache/bin` 배포나 daemon start는 하지 않았다
   - v381 다음: V382에서 v14 helper를 배포하고 private property root + private-empty data mode로 bounded service-manager start-only를 재실행한다

   - v382 계획서: `docs/plans/NATIVE_INIT_V382_EXECNS_HELPER_V14_DEPLOY_LIVE_PLAN_2026-05-20.md`
   - v382 준비 보고서: `docs/reports/NATIVE_INIT_V382_RUNTIME_PROFILE_WRAPPER_2026-05-20.md`
   - v382 라우터 보고서: `docs/reports/NATIVE_INIT_V382_RESULT_ROUTER_2026-05-20.md`
   - v382 final readiness 보고서: `docs/reports/NATIVE_INIT_V382_FINAL_READINESS_2026-05-20.md`
   - v382 deploy/live executor 보고서: `docs/reports/NATIVE_INIT_V382_DEPLOY_LIVE_EXECUTOR_2026-05-20.md`
   - v382 준비: `scripts/revalidation/wifi_execns_helper_v14_deploy_preflight.py`가 V375 deploy mechanics를 재사용하되 helper marker `a90_android_execns_probe v14`, artifact `tmp/wifi/v381-a90_android_execns_probe-v14/a90_android_execns_probe`, sha256 `f8cde6848ad49755b06bfac8136cd81f0b985ca1be13dbf27b369cdb4fe4aea7`, approval phrase `approve v382 deploy execns helper v14 only; no daemon start and no Wi-Fi bring-up`로 고정한다
   - v382 live wrapper: `scripts/revalidation/wifi_service_manager_start_only_v382_live_runner.py`가 기존 V376 runner를 재사용하되 helper sha256 v14, `--property-root /mnt/sdext/a90/private-property-v317/dev/__properties__`, `--data-wifi-mode private-empty`를 기본 profile로 고정한다
   - v382 result router: `scripts/revalidation/wifi_service_manager_start_only_v382_result_router.py`가 V377 router를 재사용하되 권장 live command를 V382 wrapper로 고정한다. no-approval route는 `service-manager-start-only-router-awaiting-approval`로 PASS했고 device command/mutation은 없음
   - v382 final readiness: `scripts/revalidation/wifi_v382_final_readiness.py`가 deploy plan/preflight, live plan/no-approval, router regression/no-approval route를 한 번에 검증한다. clean HEAD run은 `v382-final-readiness-awaiting-deploy-approval` PASS이며, 남은 blocker는 exact deploy/live approval phrases뿐이다
   - v382 로컬 검증: live wrapper plan은 PASS했고, read-only preflight는 property root visible/data profile PASS 후 remote helper가 아직 v13이어서 `helper-v14` blocker로 멈춘다. daemon start와 Wi-Fi bring-up은 없음
   - v382 executor: `scripts/revalidation/wifi_v382_deploy_live_executor.py`가 final readiness → v14 deploy → live preflight → bounded service-manager start-only → result router/classifier 순서를 fail-closed로 묶는다. no-approval deploy/live/full은 모두 `approval-required` PASS, device command/mutation/daemon/Wi-Fi 없음
   - v382 approved 결과 보고서: `docs/reports/NATIVE_INIT_V382_APPROVED_DEPLOY_LIVE_RESULT_2026-05-20.md`
   - v382 결과: exact approval 후 executor `full` PASS. `/cache/bin/a90_android_execns_probe`는 v14 SHA `f8cde6848ad49755b06bfac8136cd81f0b985ca1be13dbf27b369cdb4fe4aea7`로 교체됐고, live는 `service-manager-start-only-live-runtime-gap` / router `service-manager-start-only-router-runtime-gap`이다. `hwservicemanager`는 bounded pass, `servicemanager`는 SIGABRT manual-review. Wi-Fi HAL/scan/connect/link-up/credential/DHCP/routing은 실행 안 됨
   - v383 classifier 보고서: `docs/reports/NATIVE_INIT_V383_SERVICEMANAGER_SIGABRT_CLASSIFIER_2026-05-20.md`
   - v383 결과: `scripts/revalidation/wifi_service_manager_runtime_gap_classifier.py`가 V382 live evidence를 `service-manager-runtime-gap-servicemanager-sigabrt-capture-required`로 분류한다. device command/mutation 없이 regression PASS
   - v384 계획서: `docs/plans/NATIVE_INIT_V384_SERVICEMANAGER_CRASH_CAPTURE_PLAN_2026-05-20.md`
   - v384 구현 보고서: `docs/reports/NATIVE_INIT_V384_SERVICEMANAGER_CRASH_CAPTURE_2026-05-20.md`
   - v384 결과: 로컬 `a90_android_execns_probe v15`가 `service-manager-start-only --capture-mode ptrace-lite`를 지원한다. deploy/live wrapper는 fail-closed이며, v382/v373 승인 문구로는 v384 live/deploy가 실행되지 않는다. 아직 v15 배포와 live crash capture는 미실행
   - v384 executor 보고서: `docs/reports/NATIVE_INIT_V384_DEPLOY_LIVE_EXECUTOR_2026-05-20.md`
   - v384 handoff: `docs/operations/WIFI_V384_PTRACE_LIVE_HANDOFF.md`
   - v384 preflight ready report: `docs/reports/NATIVE_INIT_V384_PREFLIGHT_READY_2026-05-20.md`
   - v384 preapproval audit: `scripts/revalidation/wifi_v384_preapproval_audit.py`, report `docs/reports/NATIVE_INIT_V384_PREAPPROVAL_AUDIT_2026-05-20.md`, clean HEAD decision `v384-preapproval-audit-pass`
   - v384 executor 결과: `scripts/revalidation/wifi_v384_deploy_live_executor.py`가 helper v15 deploy → ptrace-lite live capture → classifier를 fail-closed로 순서화한다. `plan`/no-approval `full` 회귀에서 device command/mutation/daemon/Wi-Fi 모두 false
   - v384 실행 조건: deploy는 exact `approve v384 deploy execns helper v15 only; no daemon start and no Wi-Fi bring-up`, live는 exact `approve v384 service-manager ptrace-lite crash capture only; no Wi-Fi HAL start and no Wi-Fi bring-up` 필요
   - v384 다음: exact v384 deploy 승인으로 v15를 `/cache/bin`에 배포한 뒤, exact v384 ptrace-lite 승인으로 bounded service-manager crash capture를 실행한다. Wi-Fi HAL/start/scan/connect는 계속 blocked

---

## 당장 하지 않을 것

- Android framework 전체 복구
- SELinux/property service 전체 재구현
- 커널 교체
- EFS/modem/keymaster/RPMB 영역 쓰기
- full POSIX shell 구현
- package manager 만들기
- ADB를 최우선 과제로 되돌리기

---

## 완료 기준

단기 완료 기준:

- serial shell이 실패/성공을 신뢰할 수 있게 보고한다.
- 부팅 로그가 `/cache` 또는 `/tmp`에 남는다.
- 화면 HUD가 진행 상태와 에러를 표시한다.
- 버튼만으로 최소 메뉴를 조작할 수 있다.

중기 완료 기준:

- native init 환경이 “부팅되는 실험”이 아니라 “반복 운용 가능한 최소 Linux 콘솔”이 된다.
- 디스플레이, 입력, 센서, 저장소, USB의 안전 사용 범위가 문서화된다.
- 추가 userland 도구나 네트워크를 올릴 기반이 생긴다.

## V109-V116 다음 사이클

- roadmap: `docs/plans/NATIVE_INIT_V109_V116_ROADMAP_2026-05-04.md`
- starting point: `A90 Linux init 0.9.9 (v109)`
- first item: v109 post-v108 structure audit — DONE
- next item: v117 planning
- cycle goal: structure cleanup, extended soak, USB/service/runtime hardening, diagnostics bundle improvement

## V117-V122 다음 사이클

- roadmap: `docs/plans/NATIVE_INIT_V117_V122_ROADMAP_2026-05-05.md`
- starting point: `A90 Linux init 0.9.16 (v116)`
- status: completed through `docs/reports/NATIVE_INIT_V117_V122_COMPLETION_AUDIT_2026-05-05.md`
- current item: post-v122 planning
- planned sequence: v117 roadmap baseline, v118 shell metadata cleanup, v119 menu routing cleanup, v120 command group split, v121 PID1 guard, v122 Wi-Fi inventory refresh
- cycle goal: reduce PID 1 control debt before deciding whether Wi-Fi can move beyond read-only inventory
- guardrails: no risky Wi-Fi bring-up, no partition writes, USB ACM serial remains rescue channel

   - v384 approved live result: `docs/reports/NATIVE_INIT_V384_APPROVED_LIVE_RESULT_2026-05-20.md`
   - v384 approved deploy/live evidence:
     - initial full executor: `tmp/wifi/v384-approved-full-20260520-042720/`
     - compact live rerun: `tmp/wifi/v384-approved-live-compact-20260520-044147/`
   - v384 해석: v15 deploy는 PASS했고 ptrace-lite live는 실제 daemon start-only까지 진입했다. `servicemanager`는 SIGABRT crash context를 확보했고, `hwservicemanager`는 timeout까지 observable 상태였으나 helper 내부 process-group postflight proof가 실패해 `start-only-reboot-required`로 분류됐다. host postflight/selftest는 clean, Wi-Fi bring-up은 없음
   - v384 도구 수정: native shell 30-arg 한계 때문에 service-manager live command에서 `--data-wifi-mode private-empty`만 compact path에서 생략한다. shell wrapper는 `/cache/bin/toybox`에 `sh` applet이 없어 사용하지 않는다
   - v385 다음: `a90_android_execns_probe v16`에서 direct child reap 이후 남은 process group을 final SIGKILL로 정리하고, 잔존 process-group evidence를 캡처한다. Wi-Fi HAL/start/scan/connect는 계속 blocked

   - v385 plan: `docs/plans/NATIVE_INIT_V385_RESIDUAL_PGID_CLEANUP_PLAN_2026-05-20.md`
   - v385 readiness report: `docs/reports/NATIVE_INIT_V385_RESIDUAL_PGID_CLEANUP_2026-05-20.md`
   - v385 구현 상태: `a90_android_execns_probe v16`은 residual process-group scan/final SIGKILL/recheck evidence를 추가한다. 로컬 SHA256은 `4478c73518e950b425af0cf7db28e9570c983f428fbb0d4b5d2ee45573d37cd8`이다
   - v385 검증 상태: static build/py_compile/diff check PASS. no-approval executor는 device mutation/daemon/Wi-Fi 없이 막혔고, preflight는 remote helper가 아직 v15이므로 v16 deploy 필요로 막힌다
   - v385 실행 조건: deploy는 exact `approve v385 deploy execns helper v16 only; no daemon start and no Wi-Fi bring-up`, live는 exact `approve v385 service-manager residual pgid cleanup only; no Wi-Fi HAL start and no Wi-Fi bring-up` 필요

   - v385 approved result report: `docs/reports/NATIVE_INIT_V385_APPROVED_LIVE_RESULT_2026-05-20.md`
   - v385 approved deploy: serial transfer installed helper v16 SHA `4478c73518e950b425af0cf7db28e9570c983f428fbb0d4b5d2ee45573d37cd8`; daemon start/Wi-Fi bring-up 없음
   - v385 approved live: `servicemanager` cleanup proof PASS but runtime gap remains. `hwservicemanager` produced large ptrace exec snapshot and host capture missed `A90P1 END`; bridge capture shows eventual 85s completion, but `service_manager_start.*` summary fields were not captured. Postflight device state is clean
   - v386 다음: compact ptrace capture mode. service-manager live proof must reduce serial output and preserve machine-readable residual cleanup summary before any Wi-Fi HAL/start/scan/connect step

   - v386 plan: `docs/plans/NATIVE_INIT_V386_COMPACT_PTRACE_CAPTURE_PLAN_2026-05-20.md`
   - v386 readiness report: `docs/reports/NATIVE_INIT_V386_COMPACT_PTRACE_CAPTURE_2026-05-20.md`
   - v386 구현 상태: `a90_android_execns_probe v17`은 service-manager `ptrace-lite`에서 raw maps/mountinfo/register dump를 serial stdout으로 뿌리지 않고 compact summary만 보낸다. 로컬 SHA256은 `45c27e28c90a86c75a291edaf16d8233da51358647c1e6d1700f0e4f9cf437c5`이다
   - v386 검증 상태: static build/py_compile/diff check/no-approval executor gate PASS. device deploy/live는 아직 실행하지 않았다
   - v386 실행 조건: deploy는 exact `approve v386 deploy execns helper v17 only; no daemon start and no Wi-Fi bring-up`, live는 exact `approve v386 service-manager compact ptrace capture only; no Wi-Fi HAL start and no Wi-Fi bring-up` 필요

   - v386 approved result report: `docs/reports/NATIVE_INIT_V386_APPROVED_LIVE_RESULT_2026-05-20.md`
   - v386 approved deploy: serial transfer installed helper v17 SHA `45c27e28c90a86c75a291edaf16d8233da51358647c1e6d1700f0e4f9cf437c5`; daemon start/Wi-Fi bring-up 없음
   - v386 approved live: compact ptrace capture fixed the v385 serial output blocker. Both service-manager targets returned `A90P1 END` and machine-readable `service_manager_start.*` fields. `servicemanager` remains `start-only-runtime-gap` with cleanup PASS. `hwservicemanager` is still `start-only-reboot-required` because timeout cleanup treats a ptrace stop as reaped and leaves a temporary zombie until PID1 reaps it
   - v387 다음: ptrace timeout cleanup fix. WIFSTOPPED must not be counted as reaped; cleanup must continue the tracee with termination signal and wait for real WIFEXITED/WIFSIGNALED before claiming postflight safe

   - v387 plan: `docs/plans/NATIVE_INIT_V387_PTRACE_TIMEOUT_CLEANUP_PLAN_2026-05-20.md`
   - v387 readiness report: `docs/reports/NATIVE_INIT_V387_PTRACE_TIMEOUT_CLEANUP_2026-05-20.md`
   - v387 구현 상태: `a90_android_execns_probe v18`은 service-manager `ptrace-lite` timeout cleanup에서 `WIFSTOPPED`를 reap으로 계산하지 않고, TERM/KILL cleanup phase에서 `PTRACE_CONT`로 종료 시그널을 주입한다. 로컬 SHA256은 `1131f0e3dd61bafc5023c25d7fb019303902cdf6cea76dd2e09b44b13a42378e`이다
   - v387 검증 상태: static build/required strings/py_compile/plan-only gates/no-approval executor PASS. read-only device preflight는 remote helper가 아직 v17이므로 expected `helper-v18` blocker로 막혔고 daemon start/Wi-Fi bring-up은 없음
   - v387 실행 조건: deploy는 exact `approve v387 deploy execns helper v18 only; no daemon start and no Wi-Fi bring-up`, live는 exact `approve v387 service-manager ptrace timeout cleanup only; no Wi-Fi HAL start and no Wi-Fi bring-up` 필요

   - v387 approved result report: `docs/reports/NATIVE_INIT_V387_APPROVED_LIVE_RESULT_2026-05-20.md`
   - v387 approved deploy: serial transfer installed helper v18 SHA `1131f0e3dd61bafc5023c25d7fb019303902cdf6cea76dd2e09b44b13a42378e`; daemon start/Wi-Fi bring-up 없음
   - v387 approved live: `hwservicemanager` cleanup blocker is fixed. It now reports `start-only-pass`, `cleanup_stop_continued=1`, `reaped=1`, `residual_cleared=1`, `postflight_safe=1`. `servicemanager` still exits with SIGABRT but crash evidence is captured and cleanup is safe
   - v388 다음: `servicemanager` SIGABRT evidence triage and targeted runtime repair planning. Wi-Fi HAL/start/scan/connect remains blocked until this runtime gap is understood

   - v388 plan: `docs/plans/NATIVE_INIT_V388_SERVICEMANAGER_SIGABRT_TRIAGE_PLAN_2026-05-20.md`
   - v388 report: `docs/reports/NATIVE_INIT_V388_SERVICEMANAGER_SIGABRT_TRIAGE_2026-05-20.md`
   - v388 결과: host-only triage가 V387 `servicemanager` SIGABRT를 분석했고 `servicemanager-sigabrt-triage-needs-enhanced-crash-capture` PASS로 분류했다. `/dev/binder`, property root, SELinux null node는 materialized지만 abort message, register values, stack/abort-message memory가 없어 AOSP fatal site는 아직 미확정이다
   - v389 다음: bounded enhanced crash capture. `NT_PRSTATUS` selected register values, stack/ASCII summary, abort-message memory/string scan을 compact하게 추가한다. Wi-Fi HAL/start/scan/connect remains blocked

   - v389 plan: `docs/plans/NATIVE_INIT_V389_ENHANCED_CRASH_CAPTURE_PLAN_2026-05-20.md`
   - v389 readiness report: `docs/reports/NATIVE_INIT_V389_ENHANCED_CRASH_CAPTURE_2026-05-20.md`
   - v389 구현 상태: `a90_android_execns_probe v19`은 service-manager crash snapshot에서 selected `NT_PRSTATUS` register values(x0-x8/lr/sp/pc/pstate)와 bounded stack/register-pointer ASCII scan을 추가한다. 로컬 SHA256은 `e3da79dec1c7ca58d3208fb0d9a55ce1411fff7159ab613ff9daf6d6befd3e6d`이다
   - v389 검증 상태: static build/required strings/py_compile/plan-only gates/no-approval executor PASS. read-only device preflight는 remote helper가 아직 v18이므로 expected `helper-v19` blocker로 막혔고 daemon start/Wi-Fi bring-up은 없음
   - v389 실행 조건: deploy는 exact `approve v389 deploy execns helper v19 only; no daemon start and no Wi-Fi bring-up`, live는 exact `approve v389 service-manager enhanced crash capture only; no Wi-Fi HAL start and no Wi-Fi bring-up` 필요

   - v389 approved live result: `docs/reports/NATIVE_INIT_V389_APPROVED_LIVE_RESULT_2026-05-20.md`
   - v389 approved deploy: serial transfer installed helper v19 SHA `e3da79dec1c7ca58d3208fb0d9a55ce1411fff7159ab613ff9daf6d6befd3e6d`; daemon start/Wi-Fi bring-up 없음
   - v389 approved live: `hwservicemanager` remains `start-only-pass`; `servicemanager` remains `start-only-runtime-gap` with SIGABRT, but selected register values, stack scan, register-pointer scans, and compact maps metadata are now captured
   - v389 해석: `x8=0xf0`은 AArch64 `rt_tgsigqueueinfo` syscall path로 보이며 PC/LR은 abort delivery 경로에 멈춘 상태다. 현재 capture는 map row/library offset을 보존하지 않아 fatal site symbolization이 아직 불가하다
   - v390 다음: crash map-row/symbolization capture. `pc`/`lr`가 속한 `/proc/<pid>/maps` row와 library-relative offsets를 bounded output으로 추가한다. Wi-Fi HAL/start/scan/connect remains blocked

   - v390 plan: `docs/plans/NATIVE_INIT_V390_CRASH_MAP_CAPTURE_PLAN_2026-05-20.md`
   - v390 readiness report: `docs/reports/NATIVE_INIT_V390_CRASH_MAP_CAPTURE_2026-05-20.md`
   - v390 구현 상태: `a90_android_execns_probe v20`은 crash snapshot에서 PC/LR map row, mapping permissions, file offset, relative offset, path, escaped maps line을 추가한다. 로컬 SHA256은 `44efea328220d37f09d91e4906b7490903d789ef509f0ae2ba74a64049a47171`이다
   - v390 host tool: `scripts/revalidation/wifi_service_manager_crash_symbolize.py`가 V390 live log의 map-row evidence를 파싱하고 matching ELF root가 있을 때 `addr2line` symbolization을 시도한다
   - v390 검증 상태: static build/required strings/py_compile/plan-only gates/no-approval executor PASS. read-only device preflight는 remote helper가 아직 v19이므로 expected `helper-v20` blocker로 막혔고 daemon start/Wi-Fi bring-up은 없음
   - v390 실행 조건: deploy는 exact `approve v390 deploy execns helper v20 only; no daemon start and no Wi-Fi bring-up`, live는 exact `approve v390 service-manager crash map capture only; no Wi-Fi HAL start and no Wi-Fi bring-up` 필요

   - v390 approved live result: `docs/reports/NATIVE_INIT_V390_APPROVED_LIVE_RESULT_2026-05-20.md`
   - v390 approved deploy: serial transfer installed helper v20 SHA `44efea328220d37f09d91e4906b7490903d789ef509f0ae2ba74a64049a47171`; daemon start/Wi-Fi bring-up 없음
   - v390 approved live: `hwservicemanager` remains `start-only-pass`; `servicemanager` remains `start-only-runtime-gap` with SIGABRT, but PC/LR map rows are captured and both point into bionic `libc.so`
   - v390 해석: PC=`libc.so+0x8bebc`, LR=`libc.so+0x8be90`, `x8=0xf0` still indicates abort delivery via `rt_tgsigqueueinfo`. host symbolizer is `maprow-ready` but blocked by missing host-side Android ELF
   - v391 다음: read-only Android `libc.so` ELF pull/mirror and symbolization/disassembly around offsets `0x8be90`/`0x8bebc`. Wi-Fi HAL/start/scan/connect remains blocked

   - v391 plan: `docs/plans/NATIVE_INIT_V391_LIBC_SYMBOLIZATION_PLAN_2026-05-20.md`
   - v391 result: `docs/reports/NATIVE_INIT_V391_LIBC_SYMBOLIZATION_2026-05-20.md`
   - v391 evidence: `tmp/wifi/v391-libc-symbolize-20260520-065233/`
   - v391 결과: read-only `libc.so` pull PASS, ELF SHA `05b46edc9bf95e52c7eaf73ee340d78c52971ca2482cafa3c4d0c510691ba204`, PC/LR both resolve to bionic `abort`
   - v391 해석: captured PC/LR are abort delivery, not original fatal caller. `x8=0xf0`/`svc #0` confirms SIGABRT send path
   - v392 다음: service-manager crash caller-context/backchain capture. x29/frame pointer, stack words, candidate return-address map rows, bounded backchain reconstruction을 추가한다. Wi-Fi HAL/start/scan/connect remains blocked

   - v392 plan: `docs/plans/NATIVE_INIT_V392_BACKCHAIN_CAPTURE_PLAN_2026-05-20.md`
   - v392 readiness report: `docs/reports/NATIVE_INIT_V392_BACKCHAIN_CAPTURE_2026-05-20.md`
   - v392 handoff/analyzer report: `docs/reports/NATIVE_INIT_V392_HANDOFF_AND_FRAMECHAIN_ANALYZER_2026-05-20.md`
   - v392 executor integration report: `docs/reports/NATIVE_INIT_V392_EXECUTOR_FRAMECHAIN_INTEGRATION_2026-05-20.md`
   - v392 live handoff: `docs/operations/WIFI_V392_BACKCHAIN_LIVE_HANDOFF.md`
   - v392 구현 상태: `a90_android_execns_probe v21`은 crash snapshot에서 `x29`/frame pointer와 up to 8 frame-chain 후보를 캡처하고, 각 return address를 `frameN_ra` map row로 기록한다. 로컬 SHA256은 `c6216cc3b579f78bfd668148a24e1948e9e08621ea7d4e21c8b280475cc09ab8`이다
   - v392 분석 도구: `scripts/revalidation/wifi_service_manager_framechain_analyze.py`는 V392 live log의 frame-chain evidence와 `frameN_ra` map rows를 host-only로 파싱하고, matching ELF root가 있을 때 return-address symbolization을 시도한다. `scripts/revalidation/wifi_v392_deploy_live_executor.py`는 approved runtime-gap live 후 이 분석기를 자동 실행한다
   - v392 검증 상태: static build/required strings/py_compile/plan-only gates/no-approval executor PASS. read-only device preflight는 remote helper가 아직 v20이므로 expected `helper-v21` blocker로 막혔고 daemon start/Wi-Fi bring-up은 없음. framechain analyzer negative check는 V390 log에서 expected `service-manager-framechain-needs-v392-live` PASS. executor framechain integration smoke도 V390 runtime-gap evidence 기준 PASS
   - v392 실행 조건: deploy는 exact `approve v392 deploy execns helper v21 only; no daemon start and no Wi-Fi bring-up`, live는 exact `approve v392 service-manager backchain capture only; no Wi-Fi HAL start and no Wi-Fi bring-up` 필요

   - v393 plan: `docs/plans/NATIVE_INIT_V393_FRAMECHAIN_AUTO_ELF_RESOLVER_PLAN_2026-05-20.md`
   - v393 report: `docs/reports/NATIVE_INIT_V393_FRAMECHAIN_AUTO_ELF_RESOLVER_2026-05-20.md`
   - v393 결과: framechain analyzer가 V391 read-only `libc.so` pull과 V221/V227/V222 host-side ELF roots를 자동 재사용한다. synthetic framechain log에서 `/tmp/.../root/apex/com.android.runtime/lib64/bionic/libc.so + 0x8be90`을 `abort`로 symbolization PASS했고 V390 negative regression은 expected `service-manager-framechain-needs-v392-live` PASS
   - v393 해석: 다음 approved V392 live에서 frame return-address가 cached Android ELF에 매핑되면 수동 `--elf-root` 없이 top-level executor route가 symbolized caller inspection으로 이어질 수 있다. Wi-Fi HAL/start/scan/connect remains blocked until V392 exact approval

   - v394 plan: `docs/plans/NATIVE_INIT_V394_POST_V392_ROUTER_PLAN_2026-05-20.md`
   - v394 report: `docs/reports/NATIVE_INIT_V394_POST_V392_ROUTER_2026-05-20.md`
   - v394 결과: `scripts/revalidation/wifi_v392_post_live_router.py`가 V392 executor/framechain manifest를 host-only로 라우팅한다. synthetic regression PASS, current no-approval route는 expected `v392-post-live-router-awaiting-approval` PASS
   - v394 해석: approved V392 live 후 framechain 결과가 symbolized caller, abort-only, missing ELF, missing maprow, clean service-manager 중 어디에 해당하는지 자동 분기한다. Wi-Fi HAL/start/scan/connect remains blocked until V392 evidence says service-manager path is clean enough for a separate HAL start-only approval packet

   - v395 plan: `docs/plans/NATIVE_INIT_V395_CURRENT_READINESS_PACKET_PLAN_2026-05-20.md`
   - v395 report: `docs/reports/NATIVE_INIT_V395_CURRENT_READINESS_PACKET_2026-05-20.md`
   - v395 결과: `scripts/revalidation/wifi_v392_current_readiness_packet.py`가 최신 safe preflight/no-approval/router/read-only health evidence를 묶어 `v392-current-readiness-ready-for-approval` PASS로 판정했다. 디바이스 명령 실행/뮤테이션/daemon/Wi-Fi bring-up은 없음
   - v395 해석: V392 approved executor를 실행할 준비는 됐지만 exact approval phrase 두 개가 없으면 계속 fail-closed 상태다

   - v392 approved backchain result: `docs/reports/NATIVE_INIT_V392_APPROVED_BACKCHAIN_CAPTURE_RESULT_2026-05-20.md`
   - v392 approved 결과: helper v21 deploy PASS, service-manager backchain capture PASS, `hwservicemanager`은 `start-only-pass`, `servicemanager`은 SIGABRT `start-only-runtime-gap`이나 cleanup/postflight safe. framechain은 7 frames를 캡처했고 libc frame `__libc_init`만 symbolization PASS, `servicemanager`/`libbase`/`liblog` frames는 matching ELF artifact가 없어 미해석
   - v396 다음: read-only frame ELF pull/symbolization. `/mnt/system/system/bin/servicemanager`, `/mnt/system/system/lib64/libbase.so`, `/mnt/system/system/lib64/liblog.so`를 host에 안전하게 mirror한 뒤 V392 framechain analyzer를 재실행한다. Wi-Fi HAL/start/scan/connect remains blocked

   - v396 plan: `docs/plans/NATIVE_INIT_V396_FRAME_ELF_SYMBOLIZATION_PLAN_2026-05-20.md`
   - v396 report: `docs/reports/NATIVE_INIT_V396_FRAME_ELF_SYMBOLIZATION_2026-05-20.md`
   - v396 evidence: `tmp/wifi/v396-frame-elf-pull-20260520-073940/`
   - v396 결과: read-only `servicemanager`/`libbase.so`/`liblog.so` pull PASS, framechain rerun `service-manager-framechain-symbolization-pass`, `device_mutations=False`, `daemon_start_executed=False`, `wifi_bringup_executed=False`
   - v396 해석: missing-ELF blocker는 제거됐다. frame0/1은 fatal-log abort path이고 frame2 `servicemanager+0x8294`는 `frameworks/native/cmds/servicemanager/Access.cpp` fatal-log site 근방이다. 주변 문자열상 `selinux_status_open(true)`, `gSehandle`, `getcon` 관련 SELinux runtime/status surface가 가장 강한 후보지만 아직 확정은 아니다
   - v397 다음: private Android namespace에서 `/sys/fs/selinux`, SELinux status/context/service-context 입력, binder devnode와 service-manager fatal 조건을 read-only로 증명한다. Wi-Fi HAL/start/scan/connect remains blocked

   - v397 plan: `docs/plans/NATIVE_INIT_V397_SELINUX_SURFACE_PROOF_PLAN_2026-05-20.md`
   - v397 report: `docs/reports/NATIVE_INIT_V397_SELINUX_SURFACE_PROOF_2026-05-20.md`
   - v397 evidence: `tmp/wifi/v397-selinux-surface-final-20260520-075153/`
   - v397 결과: `service-manager-selinux-status-native-missing` PASS as blocker classification. `/proc/filesystems`에는 `selinuxfs`가 있으나 `/proc/mounts`에는 `/sys/fs/selinux` selinuxfs mount가 없고 `/sys/fs/selinux/status`, `/sys/fs/selinux/enforce`가 absent
   - v397 해석: `servicemanager` crash는 Wi-Fi 자체보다 Android `servicemanager`가 요구하는 SELinux runtime surface 부재 쪽으로 좁혀졌다. mounted Android service context input은 일부 보이지만 native/private runtime status page가 없다
   - v398 다음: minimal SELinux runtime surface plan. 우선 helper v22 private context proof 또는 native selinuxfs mount/bind 설계를 안전하게 분리하고, service-manager clean-start 전까지 Wi-Fi HAL/start/scan/connect remains blocked

   - v398 plan: `docs/plans/NATIVE_INIT_V398_SELINUXFS_MOUNT_APPROVAL_PACKET_PLAN_2026-05-20.md`
   - v398 report: `docs/reports/NATIVE_INIT_V398_SELINUXFS_MOUNT_APPROVAL_PACKET_2026-05-20.md`
   - v398 evidence: `tmp/wifi/v398-selinuxfs-mount-approval-packet-final-20260520-080150/`
   - v398 결과: `selinuxfs-mount-approval-packet-ready` PASS. V399 executor는 exact approval phrase 없이는 run/cleanup 모두 device command 전에 refuse한다. packet은 fresh V397 read-only proof를 포함했고 device mutation/daemon/Wi-Fi bring-up은 없음
   - v398 해석: 다음 live mutation은 명확히 `mount selinuxfs /sys/fs/selinux selinuxfs` 하나로 제한된다. cleanup은 `umount /sys/fs/selinux`로 분리되어 있으며 service-manager와 Wi-Fi는 여전히 범위 밖이다
   - v399 다음: exact-approved SELinuxfs mount smoke. `/sys/fs/selinux/status` 가시성을 증명한 뒤 별도 cycle에서 service-manager start-only packet으로 넘어간다. Wi-Fi HAL/start/scan/connect remains blocked

   - v399 report: `docs/reports/NATIVE_INIT_V399_SELINUXFS_MOUNT_SMOKE_2026-05-20.md`
   - v399 evidence: `tmp/wifi/v399-selinuxfs-mount-live-20260520-080657/`
   - v399 post-proof: `tmp/wifi/v399-post-smoke-proof-20260520-080750/`
   - v399 결과: `selinuxfs-mount-live-executor-run-review`. 승인된 mutation path까지 갔지만 `cmdv1 mount`가 `unknown command: mount`로 거부되어 실제 selinuxfs mount/status page는 생성되지 않았다. post-smoke proof는 여전히 `service-manager-selinux-status-native-missing`
   - v399 해석: 커널 SELinuxfs mount 불가가 아니라 executor command surface 오류다. `cmdv1 run /cache/bin/toybox mount` read-only inventory는 동작하므로 V400은 toybox-backed mount/umount executor로 좁힌다
   - v400 다음: toybox-backed SELinuxfs mount approval packet. Wi-Fi HAL/start/scan/connect remains blocked

   - v400 plan: `docs/plans/NATIVE_INIT_V400_TOYBOX_SELINUXFS_MOUNT_APPROVAL_PACKET_PLAN_2026-05-20.md`
   - v400 report: `docs/reports/NATIVE_INIT_V400_TOYBOX_SELINUXFS_MOUNT_APPROVAL_PACKET_2026-05-20.md`
   - v400 evidence: `tmp/wifi/v400-toybox-selinuxfs-mount-approval-packet-final-20260520-081415/`
   - v401 preapproval syntax evidence: `tmp/wifi/v401-preapproval-toybox-syntax-20260520-082122/`
   - v400 결과: `toybox-selinuxfs-mount-approval-packet-ready` PASS. V401 executor는 exact approval phrase 없이는 run/cleanup 모두 device command 전에 refuse한다. packet은 fresh SELinux proof, read-only toybox mount inventory, executor plan/refusal checks를 포함했고 device mutation/daemon/Wi-Fi bring-up은 없음
   - v401 preapproval syntax 결과: direct `toybox mount --help` and `toybox umount --help` PASS. `toybox --list`는 unsupported지만 V401 command contract에는 필요 없다
   - v400 해석: V399 tooling gap의 수정 경로가 준비됐다. 다음 live mutation은 `run /cache/bin/toybox mount -t selinuxfs selinuxfs /sys/fs/selinux` 하나로 제한된다. cleanup은 `run /cache/bin/toybox umount /sys/fs/selinux`로 분리한다
   - v401 다음: exact-approved toybox-backed SELinuxfs mount smoke. `/sys/fs/selinux/status` 가시성을 증명한 뒤 별도 cycle에서 service-manager start-only packet으로 넘어간다. Wi-Fi HAL/start/scan/connect remains blocked

   - v401 report: `docs/reports/NATIVE_INIT_V401_TOYBOX_SELINUXFS_MOUNT_SMOKE_2026-05-20.md`
   - v401 evidence: `tmp/wifi/v401-toybox-selinuxfs-mount-live-20260520-082325/`
   - v401 post-proof: `tmp/wifi/v401-post-mount-selinux-proof-20260520-082352/`
   - v401 결과: `toybox-selinuxfs-mount-live-executor-run-pass`. `/sys/fs/selinux/status` visible, `/sys/fs/selinux/enforce=0`, `/proc/mounts` includes `selinuxfs /sys/fs/selinux selinuxfs rw,relatime 0 0`
   - v401 post-proof 결과: `service-manager-selinux-surface-native-ready-private-proof-needed`. native SELinux runtime/status surface는 준비됐지만 private service-manager execution namespace에서 status/context/binder/property visibility는 아직 미증명
   - v402 다음: private namespace SELinux surface proof. service-manager start-only는 V402 proof 이후 별도 승인으로 분리한다. Wi-Fi HAL/start/scan/connect remains blocked

   - v402 plan: `docs/plans/NATIVE_INIT_V402_PRIVATE_SELINUX_SURFACE_PROOF_PLAN_2026-05-20.md`
   - v402 packet: `docs/reports/NATIVE_INIT_V402_PRIVATE_SELINUX_SURFACE_PROOF_PACKET_2026-05-20.md`
   - v402 helper artifact: `tmp/wifi/v402-a90_android_execns_probe-v22/a90_android_execns_probe`, SHA `55f83cfa43ebc69ab37b3181262fbdf0e3ed6b5b11f0e41e63d3b56e7ea080e6`
   - v402 결과: helper v22 `private-selinux-proof` mode와 fail-closed deploy/private-proof runners를 준비했다. no-approval run은 mutation/daemon/Wi-Fi 없이 거부되고, read-only private proof preflight는 remote helper가 아직 v22가 아니어서 expected `helper-v22` blocker로 멈춘다
   - v402 실행 조건: deploy는 exact `approve v402 deploy execns helper v22 only; no daemon start and no Wi-Fi bring-up`, private proof는 exact `approve v402 private selinux namespace proof only; no daemon start and no Wi-Fi bring-up` 필요
   - v402 다음: exact-approved helper v22 deploy 후 private SELinux namespace proof. service-manager start-only, Wi-Fi HAL/start/scan/connect는 계속 별도 승인 전까지 blocked

   - v402 live report: `docs/reports/NATIVE_INIT_V402_PRIVATE_SELINUX_SURFACE_PROOF_LIVE_2026-05-20.md`
   - v402 live evidence: deploy `tmp/wifi/v402-execns-helper-v22-deploy-live-20260520-084231/`, proof `tmp/wifi/v402-private-selinux-surface-live-20260520-084832/`, postflight `tmp/wifi/v402-private-proof-postflight-20260520-084853/`
   - v402 live 결과: `execns-helper-v22-deploy-pass` 후 `private-selinux-surface-proof-pass`. private namespace에서 SELinuxfs status/enforce/policy, Binder devnodes, V317 private property tree, service/hwservice context files가 함께 visible하다
   - v402 live 해석: V401 이후 남은 private namespace SELinux surface blocker는 제거됐다. 다음은 V403 bounded service-manager start-only retry approval packet이며, Wi-Fi HAL/start/scan/connect는 계속 blocked

   - v403 plan: `docs/plans/NATIVE_INIT_V403_SERVICE_MANAGER_START_ONLY_RETRY_PLAN_2026-05-20.md`
   - v403 packet: `docs/reports/NATIVE_INIT_V403_SERVICE_MANAGER_START_ONLY_RETRY_APPROVAL_PACKET_2026-05-20.md`
   - v403 evidence: `tmp/wifi/v403-service-manager-start-only-retry-approval-packet-20260520-085357/`
   - v403 결과: `scripts/revalidation/wifi_service_manager_start_only_v403_live_runner.py`와 approval packet을 준비했다. runner plan/preflight/no-approval refusal 모두 PASS했고 packet decision은 `v403-service-manager-start-only-retry-approval-packet-ready`
   - v403 실행 조건: exact `approve v403 service-manager start-only retry only; no Wi-Fi HAL start and no Wi-Fi bring-up` 필요
   - v403 다음: 승인 시 bounded service-manager/hwservicemanager start-only retry를 실행하고 결과를 라우팅한다. Wi-Fi HAL/start/scan/connect는 계속 blocked

   - v403 live report: `docs/reports/NATIVE_INIT_V403_SERVICE_MANAGER_START_ONLY_RETRY_LIVE_2026-05-20.md`
   - v403 live evidence: `tmp/wifi/v403-service-manager-start-only-retry-live-20260520-085702/`, postflight `tmp/wifi/v403-service-manager-start-only-postflight-20260520-085747/`
   - v403 live 결과: `service-manager-start-only-live-pass`. `servicemanager`와 `hwservicemanager` 모두 bounded observation window 동안 살아 있었고, timeout 후 terminate/reap/postflight clean을 증명했다. Wi-Fi bring-up은 없음
   - v403 supplemental HAL gate: old V364 gate refresh는 global/current runtime 기준이라 `current-binder-devnodes`, `current-service-manager-processes`, `current-property-runtime`, `linkerconfig-visibility` blocker로 남는다. 이는 V403 private helper-owned namespace PASS와 충돌하지 않는다
   - v403 다음: V404 private-composite Wi-Fi HAL readiness packet. V403-proven service-manager/hwservicemanager pair를 같은 bounded helper-owned runtime 안에서 유지하는 설계를 먼저 만든 뒤 HAL start-only를 별도 승인으로 분리한다. Wi-Fi scan/connect/link-up/credentials remain blocked

   - v404 plan: `docs/plans/NATIVE_INIT_V404_PRIVATE_COMPOSITE_HAL_READINESS_PLAN_2026-05-20.md`
   - v404 report: `docs/reports/NATIVE_INIT_V404_PRIVATE_COMPOSITE_HAL_READINESS_PACKET_2026-05-20.md`
   - v404 evidence: `tmp/wifi/v404-private-composite-hal-readiness-packet-fixed-20260520-090542/`
   - v404 결과: `v404-private-composite-hal-readiness-packet-ready` PASS. packet은 V402/V403/V210/V216/V287 입력과 현재 read-only native 상태를 묶어 blocker checks PASS로 판정했다. live execution approval, device mutation, daemon start, Wi-Fi bring-up은 모두 false
   - v404 HAL boundary: first candidate는 `vendor.wifi_hal_ext`, sibling fallback은 `vendor.wifi_hal_legacy`. vendor HAL binary/init rc/VINTF 가시성은 현재 global `/mnt/system/vendor` stat가 아니라 V210 vendor-root evidence를 기준으로 판단한다
   - v404 다음: V405 composite helper/runner approval packet. 현재 helper는 한 invocation에 한 target만 start하므로, HAL start-only 전에 `servicemanager` + `hwservicemanager` + 첫 HAL 후보를 같은 helper-owned private namespace에서 bounded supervision하는 실행기를 만들어야 한다. Wi-Fi scan/connect/link-up/credentials/DHCP/routing remain blocked

   - v405 plan: `docs/plans/NATIVE_INIT_V405_COMPOSITE_HAL_APPROVAL_PACKET_PLAN_2026-05-20.md`
   - v405 report: `docs/reports/NATIVE_INIT_V405_COMPOSITE_HAL_APPROVAL_PACKET_2026-05-20.md`
   - v405 evidence: `tmp/wifi/v405-composite-hal-approval-packet-final-20260520-092442/`
   - v405 결과: `v405-composite-hal-approval-packet-ready` PASS. helper v23 local artifact SHA는 `64c80e73d791b82e0b9f60b05db1df1781bf5033b1ffd76e323cf52ce3dbc520`이고, `wifi-hal-composite-start-only`, `vendor-wifi-hal-ext`, `vendor-wifi-hal-legacy`, `--allow-wifi-hal-start-only` guard strings가 확인됐다
   - v405 guard 결과: deploy preflight는 expected `execns-helper-v23-deploy-preflight-ready-needs-deploy`, deploy no-approval은 `execns-helper-v23-deploy-approval-required`, HAL runner no-approval은 `composite-hal-start-only-approval-required`로 모두 fail-closed. device mutation, daemon start, HAL start, Wi-Fi bring-up은 모두 false
   - v405 다음: exact-approved helper v23 deploy only. HAL start-only는 deploy 후 V405 runner preflight PASS를 본 뒤 별도 exact approval로만 진행한다. scan/connect/link-up/credentials/DHCP/routing remain blocked

   - v405 deploy report: `docs/reports/NATIVE_INIT_V405_HELPER_V23_DEPLOY_LIVE_2026-05-20.md`
   - v405 deploy evidence: `tmp/wifi/v405-execns-helper-v23-deploy-live-20260520-092918/`
   - v405 post-deploy checks: helper check `tmp/wifi/v405-execns-helper-v23-deploy-postcheck-20260520-093620/`, composite preflight `tmp/wifi/v405-composite-hal-preflight-post-deploy-20260520-093529/`
   - v405 deploy 결과: exact-approved helper v23 deploy PASS. serial fallback으로 783 chunks / 1,094,836 encoded bytes를 전송했고 remote helper SHA/mode가 v23으로 확인됐다. daemon start, HAL start, Wi-Fi bring-up은 모두 false
   - v405 post-deploy preflight 결과: `composite-hal-start-only-preflight-ready` PASS. 남은 gate는 exact approval phrase뿐이다
   - v405 다음: `approve v405 composite Wi-Fi HAL start-only smoke only; no scan/connect/link-up and no Wi-Fi bring-up` 승인 시 bounded composite HAL start-only smoke만 실행한다. Wi-Fi scan/connect/link-up/credentials/DHCP/routing remain blocked

   - v405 live report: `docs/reports/NATIVE_INIT_V405_COMPOSITE_HAL_START_ONLY_LIVE_2026-05-20.md`
   - v405 live evidence: `tmp/wifi/v405-composite-hal-start-only-live-20260520-094000/`
   - v405 library locate evidence: `tmp/wifi/v405-wifi-hal-lib-locate-20260520-094105/`
   - v405 live 결과: exact-approved composite start-only smoke는 승인 경계 안에서 실행됐고 safety PASS. `servicemanager`, `hwservicemanager`, `vendor.samsung.hardware.wifi@2.0-service`가 같은 helper-owned namespace에서 시작됐지만 Wi-Fi HAL이 `android.hardware.wifi@1.0.so` 미해결로 exit `1` 처리되어 `composite-hal-start-only-runtime-gap`로 분류됐다. scan/connect/link-up 및 Wi-Fi bring-up은 false
   - v405 해석: blocker는 service-manager runtime이 아니라 private APEX materialization이다. 필요한 Wi-Fi HIDL interface libs는 `/mnt/system/system/system_ext/apex/com.android.vndk.v30/lib64/`에 있고, 현재 helper는 `/mnt/system/system/apex` 기반 private farm만 구성한다
   - v406 다음: private `/apex/com.android.vndk.v30`에 `system_ext/apex/com.android.vndk.v30`를 bind/materialize하는 helper/runner를 만들고 linker-list closure를 먼저 증명한다. HAL start-only retry, scan/connect/link-up, credentials, DHCP, routing은 별도 gate로 유지한다

   - v406 plan: `docs/plans/NATIVE_INIT_V406_SYSTEM_EXT_VNDK_APEX_PLAN_2026-05-20.md`
   - v406 report: `docs/reports/NATIVE_INIT_V406_SYSTEM_EXT_VNDK_APEX_PREP_2026-05-20.md`
   - v406 helper artifact: `tmp/wifi/v406-a90_android_execns_probe-v24/a90_android_execns_probe`
   - v406 결과: helper v24가 `v30-to-system-ext-v30` private APEX materialization mode를 추가했고 static ARM64 build PASS, SHA `7ec11d95085f1c3dc370884725b080b44150bf8b0a5f7d897df048188a815063`
   - v406 gate 결과: runner preflight는 `system-ext-vndk-linker-list-preflight-ready-needs-deploy`, deploy preflight는 `execns-helper-v24-deploy-preflight-ready-needs-deploy`, deploy no-approval은 `execns-helper-v24-deploy-approval-required`, runner no-approval은 `system-ext-vndk-linker-list-approval-required`. daemon start, HAL start, Wi-Fi bring-up은 모두 false
   - v406 다음: 먼저 `approve v406 deploy execns helper v24 only; no daemon start and no Wi-Fi bring-up` 승인으로 helper deploy만 진행한다. 그 다음 별도 `approve v406 system_ext VNDK APEX linker-list proof only; no daemon start and no Wi-Fi bring-up` 승인으로 linker-list proof만 진행한다

   - v406 deploy report: `docs/reports/NATIVE_INIT_V406_HELPER_V24_DEPLOY_LIVE_2026-05-20.md`
   - v406 deploy evidence: `tmp/wifi/v406-execns-helper-v24-deploy-live-20260520-095625/`
   - v406 post-deploy checks: helper check `tmp/wifi/v406-execns-helper-v24-deploy-postcheck-20260520-100244/`, runner preflight `tmp/wifi/v406-system-ext-vndk-runner-post-deploy-preflight-20260520-100252/`
   - v406 deploy 결과: exact-approved helper v24 deploy PASS. serial fallback으로 783 chunks / 1,094,836 encoded bytes를 전송했고 remote helper SHA/mode가 v24로 확인됐다. daemon start, HAL start, Wi-Fi bring-up은 모두 false
   - v406 post-deploy preflight 결과: `system-ext-vndk-linker-list-preflight-ready` PASS. 남은 gate는 exact approval phrase뿐이다
   - v406 다음: `approve v406 system_ext VNDK APEX linker-list proof only; no daemon start and no Wi-Fi bring-up` 승인 시 linker-list proof만 실행한다. HAL start-only retry, scan/connect/link-up, credentials, DHCP, routing은 별도 gate로 유지한다

   - v406 linker-list report: `docs/reports/NATIVE_INIT_V406_SYSTEM_EXT_VNDK_LINKER_LIST_LIVE_2026-05-20.md`
   - v406 linker-list evidence: `tmp/wifi/v406-system-ext-vndk-linker-list-live-20260520-100627/`
   - v406 linker-list 결과: exact-approved proof PASS. helper v24 `v30-to-system-ext-v30` mode에서 `/vendor/bin/hw/vendor.samsung.hardware.wifi@2.0-service`가 linker-list child exit `0`, signal `0`, timed_out `0`, missing_libs `[]`로 완료됐다. device mutation, daemon start, HAL start, Wi-Fi bring-up은 모두 false
   - v406 해석: V405의 `android.hardware.wifi@1.0.so` missing blocker는 system_ext VNDK v30 APEX materialization으로 해소됐다
   - v407 다음: bounded composite Wi-Fi HAL start-only retry plan/approval packet을 작성한다. 같은 helper-owned namespace에서 `servicemanager`, `hwservicemanager`, `vendor.wifi_hal_ext`만 시작하고 scan/connect/link-up, credentials, DHCP, routing은 계속 별도 gate로 유지한다

   - v407 plan: `docs/plans/NATIVE_INIT_V407_COMPOSITE_HAL_RETRY_PLAN_2026-05-20.md`
   - v407 report: `docs/reports/NATIVE_INIT_V407_COMPOSITE_HAL_RETRY_APPROVAL_PACKET_2026-05-20.md`
   - v407 runner: `scripts/revalidation/wifi_composite_hal_start_only_v407_runner.py`
   - v407 결과: approval packet PASS. plan은 `v407-composite-hal-start-only-retry-plan-ready`, no-approval은 `v407-composite-hal-start-only-retry-approval-required`, read-only preflight는 `v407-composite-hal-start-only-retry-preflight-ready`
   - v407 guard 결과: V406 linker-list input, helper v24 SHA/mode, system_ext VNDK v30 source, manager binaries, process surface, Wi-Fi link surface가 모두 pass. device mutation, daemon start, HAL start, Wi-Fi bring-up은 모두 false
   - v407 다음: `approve v407 composite Wi-Fi HAL start-only retry only; no scan/connect/link-up and no Wi-Fi bring-up` 승인 시 bounded start-only retry만 실행한다. scan/connect/link-up, credentials, DHCP, routing은 별도 gate로 유지한다

   - v407 live report: `docs/reports/NATIVE_INIT_V407_COMPOSITE_HAL_START_ONLY_RETRY_LIVE_2026-05-20.md`
   - v407 live evidence: `tmp/wifi/v407-composite-hal-start-only-retry-live-20260520-101410/`
   - v407 live 결과: exact-approved bounded composite HAL start-only retry PASS. `servicemanager`, `hwservicemanager`, `vendor.samsung.hardware.wifi@2.0-service`가 모두 observe window 끝까지 observable했고 SIGTERM cleanup/reap/postflight safe로 종료됐다. scan/connect/link-up 및 Wi-Fi bring-up은 false
   - v407 해석: private namespace와 helper v24 `v30-to-system-ext-v30` 조합은 첫 HAL 후보를 bounded start-only로 유지할 수 있다
   - v408 다음: HAL registration/service-surface evidence를 수집하는 plan/approval packet을 작성한다. scan/connect/link-up, credentials, DHCP, routing은 계속 별도 gate로 유지한다

   - v408 plan: `docs/plans/NATIVE_INIT_V408_HAL_REGISTRATION_SURFACE_PLAN_2026-05-20.md`
   - v408 report: `docs/reports/NATIVE_INIT_V408_HAL_REGISTRATION_SURFACE_PACKET_2026-05-20.md`
   - v408 evidence: `tmp/wifi/v408-hal-registration-surface-packet-20260520-102249/`
   - v408 runner: `scripts/revalidation/wifi_hal_registration_surface_v408_packet.py`
   - v408 결과: host-only evidence packet PASS. V407 transcript에서 no-bring-up boundary, composite child start, private Binder/HwBinder/VndBinder devnodes, hwservice context inputs, HAL/hwservicemanager proc/fd/maps captures, Wi-Fi HIDL/HwBinder maps, fatal-runtime-noise absence, clean postflight를 모두 확인했다. V408 자체는 device command, daemon start, HAL start, Wi-Fi bring-up을 실행하지 않았다
   - v408 해석: V407은 실제 Wi-Fi bring-up이 아니라 “HAL service surface까지 살아 있음”을 증명한다. `hwservicemanager`에 실제 service publication/listing이 되었는지는 아직 미검증이다
   - v409 다음: 같은 bounded trio를 live로 띄운 상태에서 `hwservicemanager`/HIDL service-list registration query를 수행하는 gate를 설계한다. scan/connect/link-up, credentials, DHCP, routing은 계속 별도 gate로 유지한다

   - v409 plan: `docs/plans/NATIVE_INIT_V409_HAL_REGISTRATION_QUERY_PLAN_2026-05-20.md`
   - v409 report: `docs/reports/NATIVE_INIT_V409_HAL_REGISTRATION_QUERY_PREP_2026-05-20.md`
   - v409 helper artifact: `tmp/wifi/v409-a90_android_execns_probe-v25/a90_android_execns_probe`
   - v409 deploy wrapper: `scripts/revalidation/wifi_execns_helper_v25_deploy_preflight.py`
   - v409 query runner: `scripts/revalidation/wifi_hal_registration_query_v409_runner.py`
   - v409 결과: helper v25 `wifi-hal-composite-lshal-list` mode와 `--allow-hal-service-query` guard를 구현했고 static ARM64 build PASS, SHA `e90639d55dacc5486c998c4d1470235a6c72e4759cc63ebd1f07cf90c5852b37`. plan/no-approval manifests는 모두 device command와 mutation 없이 fail-closed PASS
   - v409 해석: 실제 `hwservicemanager` publication listing은 `/system/bin/lshal` 또는 별도 HIDL client가 필요하다. V409 runner는 먼저 `/mnt/system/system/bin/lshal` 존재를 read-only preflight로 확인하고, 없으면 V410으로 라우팅한다
   - v409 superseded: V409 approved-plan argcheck가 native argument budget을 맞추기 위해 `--data-wifi-mode private-empty`를 생략해야 했으므로 live deploy 전에 V410으로 대체했다. V409 deploy/query scripts는 이제 `v409-superseded-by-v410`으로 fail-closed된다

   - v409 read-only deploy preflight: `tmp/wifi/v409-helper-v25-deploy-readonly-preflight-20260520-103906/`
   - v409 read-only query preflight: `tmp/wifi/v409-registration-query-readonly-preflight-20260520-103926/`
   - v409 preflight 결과: deploy preflight는 `execns-helper-v25-deploy-preflight-ready-needs-deploy` PASS. query preflight는 `v409-hal-registration-query-blocked`이며 blocker는 `helper-v25`뿐이다. `/mnt/system/system/bin/lshal`, runtime materials, system_ext VNDK v30, service-manager binaries, process surface, Wi-Fi link surface는 모두 pass. device mutation, daemon start, HAL start, Wi-Fi bring-up은 모두 false
   - v409 preflight 해석: `lshal` direct path는 존재하지만 V409 arg-budget contract가 약하므로 exact-approved helper v25 deploy는 더 이상 next step이 아니다. V410 helper v26 + implicit `private-empty` contract가 대체 경로다
   - v409 guardcheck: `tmp/wifi/v409-helper-v25-deploy-guardcheck-preflight-20260520-104455/` PASS. deploy wrapper now records `local-helper-v25-query-guard=pass` and `remote-helper-v25-query-guard=needs-deploy`, proving the local artifact contains the explicit `--allow-hal-service-query` guard before deploy

   - v410 plan: `docs/plans/NATIVE_INIT_V410_ARG_BUDGET_REPAIR_PLAN_2026-05-20.md`
   - v410 report: `docs/reports/NATIVE_INIT_V410_ARG_BUDGET_REPAIR_PREP_2026-05-20.md`
   - v410 helper artifact: `tmp/wifi/v410-a90_android_execns_probe-v26/a90_android_execns_probe`
   - v410 deploy wrapper: `scripts/revalidation/wifi_execns_helper_v26_deploy_preflight.py`
   - v410 query runner: `scripts/revalidation/wifi_hal_registration_query_v410_runner.py`
   - v410 배경: exact-approved v409 query plan에서 command length는 29였지만 `--data-wifi-mode private-empty`가 빠졌다. live query에서 V407과 같은 private `/data/vendor/wifi` boundary를 유지하려면 배포 전 수정이 필요했다
   - v410 결과: helper v26은 `wifi-hal-composite-lshal-list` mode에서 `--data-wifi-mode`가 생략되면 `private-empty`를 기본값으로 설정한다. approved V410 query plan은 command length 29, `--allow-hal-service-query` present, `helper_implicit_data_wifi_mode=private-empty`, device commands false
   - v410 preflight 결과: deploy plan/preflight/no-approval PASS. query read-only preflight는 `lshal-binary` PASS와 `helper-v26` blocker만 확인했다. device mutation, daemon start, HAL start, Wi-Fi bring-up은 모두 false
   - v410 contract linter: `tmp/wifi/v410-arg-budget-linter-privatewrite-20260520-110025/` PASS. helper source default, data-wifi allowlist, runner implicit plan marker, deploy v26 guard, approved command arg budget, query guard, and host-only manifest contract all agree. Evidence output uses 0700 directory and 0600 no-follow/exclusive files
   - v410 deploy/live 결과: helper v26 deploy PASS 후 exact-approved bounded `lshal` registration query를 실행했다. Trio(`servicemanager`, `hwservicemanager`, Wi-Fi HAL)는 observable/clean stop PASS였고 Wi-Fi bring-up은 false였지만 `/system/bin/lshal` 기본 실행은 `lshal-timeout`으로 `v410-hal-registration-query-runtime-gap`을 반환했다
   - v410 해석: 기본 `lshal`은 binderized/passthrough 범위가 넓어 이 gate의 질문보다 과하다. 다음은 V411에서 `lshal list --types=binderized --neat`처럼 hwservicemanager 등록 목록만 좁혀 확인하는 helper/runner를 준비한다

   - v411 plan: `docs/plans/NATIVE_INIT_V411_BINDERIZED_LSHAL_QUERY_PLAN_2026-05-20.md`
   - v411 report: `docs/reports/NATIVE_INIT_V411_BINDERIZED_LSHAL_QUERY_PREP_2026-05-20.md`
   - v411 helper artifact: `tmp/wifi/v411-a90_android_execns_probe-v27/a90_android_execns_probe`
   - v411 deploy wrapper: `scripts/revalidation/wifi_execns_helper_v27_deploy_preflight.py`
   - v411 query runner: `scripts/revalidation/wifi_hal_binderized_registration_query_v411_runner.py`
   - v411 결과: helper v27 `wifi-hal-composite-lshal-binderized-list` mode를 추가했고 query child를 `/system/bin/lshal list --types=binderized --neat`로 좁혔다. Static ARM64 build PASS, SHA `0519b557482f347d47962e9da76ee7afcce270bf12df860d37678e9a26bf2c74`. approved query plan은 command length 29로 유지된다
   - v411 preflight 결과: query read-only preflight는 expected blocker `helper-v27`만 남기고 `lshal-binary`, runtime materials, system_ext VNDK v30, service-manager binaries, process surface, Wi-Fi link surface를 PASS로 확인했다. deploy read-only preflight는 `execns-helper-v27-deploy-preflight-ready-needs-deploy` PASS
   - v411 contract linter: `tmp/wifi/v411-binderized-lshal-linter-20260520-113507/` PASS. helper source, runner, deploy wrapper, approved-plan/noapproval manifests, deploy plan, and read-only preflight all agree on the binderized-only lshal contract. Evidence output uses 0700 directory and 0600 no-follow/exclusive files
   - v411 다음: exact-approved helper v27 deploy only. Required phrase: `approve v411 deploy execns helper v27 only; no daemon start and no Wi-Fi bring-up`

### V428. Explicit lshal Status-Column Probe — RUNTIME-GAP / SAFE CLEANUP

- plan: `docs/plans/NATIVE_INIT_V428_LSHAL_STATUS_COLUMNS_PLAN_2026-05-20.md`
- report: `docs/reports/NATIVE_INIT_V428_LSHAL_STATUS_COLUMNS_2026-05-20.md`
- helper: `a90_android_execns_probe v29`
- helper artifact: `tmp/wifi/v428-a90_android_execns_probe-v29/a90_android_execns_probe`
- helper SHA256: `fcb1a7440995d018a73d52e74fbdd826102cc3fa93ba5f46d50bdca585f2d1bb`
- deploy evidence: `tmp/wifi/v428-helper-v29-deploy-live-20260520-141412/`
- live evidence: `tmp/wifi/v428-lshal-status-query-live-after-selinux-20260520-142354/`
- result:
  - deploy decision `execns-helper-v29-deploy-pass`.
  - live decision `v428-lshal-status-query-runtime-gap`.
  - VINTF-only native rows include `vendor.samsung.hardware.wifi@2.2::ISehWifi/default` as `declared`.
  - VINTF-only native rows do not include Samsung `ISehWifi/default` `@2.0` or `@2.1`.
  - composite status query child timed out: `wifi_hal_service_query.result=service-query-timeout`.
  - composite children were observable and postflight safe.
  - postflight process surface and Wi-Fi link surface were clean.
  - `wifi_bringup_executed=False`.
- interpretation: native private runtime still does not prove live Samsung Wi-Fi hwservice registration. Android boot-complete remains the richer service surface. Next should split the query into cheaper VINTF-only and binderized-only status probes before deciding on Android-managed Wi-Fi runtime control.
- next execution item: V429 minimal lshal status split; no Wi-Fi scan/connect/link-up yet.

### V429. Minimal lshal Status Split — RUNTIME-GAP / SAFE CLEANUP

- plan: `docs/plans/NATIVE_INIT_V429_LSHAL_MINIMAL_SPLIT_PLAN_2026-05-20.md`
- report: `docs/reports/NATIVE_INIT_V429_LSHAL_MINIMAL_SPLIT_2026-05-20.md`
- helper: `a90_android_execns_probe v30`
- helper artifact: `tmp/wifi/v429-a90_android_execns_probe-v30/a90_android_execns_probe`
- helper SHA256: `65b279db9f5a66979140b71688cd3998ddc5832c1ca374e2187db981d5c17757`
- deploy evidence: `tmp/wifi/v429-helper-v30-deploy-live-20260520-143348/`
- live evidence: `tmp/wifi/v429-lshal-minimal-split-live-20260520-144031/`
- result:
  - deploy decision `execns-helper-v30-deploy-pass`.
  - live decision `v429-lshal-minimal-split-runtime-gap`.
  - VINTF-only native rows include `vendor.samsung.hardware.wifi@2.2::ISehWifi/default` as `declared`.
  - VINTF-only native rows do not include Samsung `ISehWifi/default` `@2.0` or `@2.1`.
  - binderized-only status query child timed out: `wifi_hal_service_query.result=service-query-timeout`.
  - query argv was reduced to `/system/bin/lshal list --types=binderized --neat -S`.
  - composite children were observable and postflight safe.
  - postflight process surface and Wi-Fi link surface were clean.
  - `wifi_bringup_executed=False`.
- interpretation: V429 rules out V428's heavy `-p -e -c` and mixed `binderized,vintf` output as the main cause. Native private runtime still cannot return Samsung Wi-Fi binderized registrations. Android boot-complete evidence remains the stronger path.
- next execution item: V430 Android explicit-column mirror. Boot Android to `sys.boot_completed=1`, run read-only minimal `lshal` status commands, restore native v319, then decide Android-managed runtime pivot versus further native reconstruction.

### V430. Android lshal Explicit Mirror Result

- plan: `docs/plans/NATIVE_INIT_V430_ANDROID_LSHAL_EXPLICIT_MIRROR_PLAN_2026-05-20.md`
- report: `docs/reports/NATIVE_INIT_V430_ANDROID_LSHAL_EXPLICIT_MIRROR_2026-05-20.md`
- live evidence: `tmp/wifi/v430-android-lshal-explicit-handoff-live-fix-20260520-145456/`
- result: Android boot-complete handoff and native rollback PASS. Android neat `lshal` shows all three Samsung `ISehWifi/default` target rows, but explicit `lshal -S` exits `rc=136`; Wi-Fi bring-up remains false.
- next: V431 Android Wi-Fi runtime gap map. Collect read-only Android init rc/service/property/socket/devnode/data surfaces and compare them with the native private namespace before deciding Android-managed Wi-Fi control or native repair.

### V431. Android Wi-Fi Runtime Gap Map Result

- plan: `docs/plans/NATIVE_INIT_V431_ANDROID_RUNTIME_GAP_MAP_PLAN_2026-05-20.md`
- report: `docs/reports/NATIVE_INIT_V431_ANDROID_RUNTIME_GAP_MAP_2026-05-20.md`
- live evidence: `tmp/wifi/v431-android-runtime-gap-handoff-live-su-quote-20260520-152315/`
- result: Android boot-complete runtime map PASS. Android has the four target Wi-Fi runtime services running and defined, plus framework services, wifihal/wpa/CNSS sockets, `/dev/wlan`, `wlan0`/`swlan0`/`wifi-aware0`, and `/data/vendor/wifi` layout. Wi-Fi bring-up remains false and native v319 rollback was verified.
- next: V432 Android-managed Wi-Fi control gate plan. Split first control into a narrow enable/status gate with explicit cleanup; keep scan/connect/credentials/routing as later gates.

### V432. Android Wi-Fi Control Gate Result

- plan: `docs/plans/NATIVE_INIT_V432_ANDROID_WIFI_CONTROL_GATE_PLAN_2026-05-20.md`
- report: `docs/reports/NATIVE_INIT_V432_ANDROID_WIFI_CONTROL_GATE_2026-05-20.md`
- live evidence: `tmp/wifi/v432-android-control-gate-handoff-live-classifierfix-20260520-154009/`
- result: Android boot-complete handoff and native rollback PASS. Android Wi-Fi was already enabled and connected from saved framework state by boot-complete, with `wifi_connected=True`, `android_auto_connect_observed=True`, and `wlan0_has_ip=True`. V432 did not issue enable/scan/connect/credential/routing operations and `wifi_bringup_executed=False`.
- next: V433 Android Wi-Fi auto-connect containment/stability gate. Do not proceed to scan/connect or server exposure until routing exposure, stability, cleanup, and intentional-disable behavior are characterized.

### V433. Android Wi-Fi Auto-connect Containment Result

- plan: `docs/plans/NATIVE_INIT_V433_ANDROID_WIFI_AUTOCONNECT_CONTAINMENT_PLAN_2026-05-20.md`
- report: `docs/reports/NATIVE_INIT_V433_ANDROID_WIFI_AUTOCONNECT_CONTAINMENT_2026-05-20.md`
- live evidence: `tmp/wifi/v433-android-autoconnect-containment-handoff-live-redactfix2-20260520-160156/`
- result: Android boot-complete handoff and native rollback PASS. Wi-Fi auto-connect was stable, `wlan0` had IP, default-route/local-route evidence pointed to `wlan0`, Android connectivity was validated, DNS surface was present, and no global listening sockets were observed. V433 did not send external probes or mutate Wi-Fi state; `wifi_bringup_executed=False`.
- next: V434 Android Wi-Fi auto-connect policy gate. Decide whether lab runs should disable/contain Android auto-connect or explicitly accept it for longer exposure-aware stability testing before any server exposure or explicit scan/connect work.

### V434. Android Wi-Fi Auto-connect Policy Result

- plan: `docs/plans/NATIVE_INIT_V434_ANDROID_WIFI_AUTOCONNECT_POLICY_PLAN_2026-05-20.md`
- report: `docs/reports/NATIVE_INIT_V434_ANDROID_WIFI_AUTOCONNECT_POLICY_2026-05-20.md`
- live evidence: `tmp/wifi/v434-android-autoconnect-policy-handoff-live-20260520-161134/`
- result: fresh V433 containment handoff plus host-side policy selection PASS. Policy is `contain-first` because Android Wi-Fi is stable and externally routed through saved auto-connect state. Native rollback restored `A90 Linux init 0.9.61 (v319)`, postflight selftest passed, and redaction scan passed.
- next: V435 bounded Android Wi-Fi auto-connect disable/containment proof. This is the first cleanup/containment gate; it should still forbid scan/connect, credentials, server exposure, and external probes.

### V435. Android Wi-Fi Auto-connect Disable Result

- plan: `docs/plans/NATIVE_INIT_V435_ANDROID_WIFI_AUTOCONNECT_DISABLE_PLAN_2026-05-20.md`
- report: `docs/reports/NATIVE_INIT_V435_ANDROID_WIFI_AUTOCONNECT_DISABLE_2026-05-20.md`
- live evidence: `tmp/wifi/v435-android-wifi-disable-handoff-live-statefix-20260520-163102/`
- result: bounded Android Wi-Fi disable containment PASS. `cmd wifi set-wifi-enabled disabled` executed, final corrected state had Wi-Fi disabled, no `wlan0` IP, no `wlan0` route candidate, no active validated Wi-Fi connectivity, no DNS surface, and no global listener. Native rollback restored `A90 Linux init 0.9.61 (v319)`.
- next: V436 Android Wi-Fi disabled persistence check. Boot Android and verify containment without another disable command before deciding controlled re-enable or native-side Wi-Fi work.

### V436. Android Wi-Fi Disabled Persistence Result

- plan: `docs/plans/NATIVE_INIT_V436_ANDROID_WIFI_DISABLED_PERSISTENCE_PLAN_2026-05-20.md`
- report: `docs/reports/NATIVE_INIT_V436_ANDROID_WIFI_DISABLED_PERSISTENCE_2026-05-20.md`
- live evidence: `tmp/wifi/v436-android-wifi-disabled-persistence-handoff-live-20260520-164037/`
- result: read-only Android disabled persistence PASS. Android boot-complete showed Wi-Fi still disabled, no `wlan0` IP, no `wlan0` route candidate, no active validated Wi-Fi connectivity, no active DNS surface, and no global listener. No additional disable command ran.
- next: V437 controlled Android Wi-Fi branch decision. Decide whether to run a controlled re-enable observation gate or resume native-side Wi-Fi integration while preserving Android disabled containment.

### V437. Wi-Fi Branch Decision Result

- plan: `docs/plans/NATIVE_INIT_V437_WIFI_BRANCH_DECISION_PLAN_2026-05-20.md`
- report: `docs/reports/NATIVE_INIT_V437_WIFI_BRANCH_DECISION_2026-05-20.md`
- host-run evidence: `tmp/wifi/v437-wifi-branch-decision-hostrun-20260520-164708/`
- result: host-side branch decision PASS. Selected `controlled-android-reenable-observation` because V436 proved persistent disabled containment. No device command or mutation ran.
- next: V438 controlled Android Wi-Fi re-enable observation. Permit only bounded `cmd wifi set-wifi-enabled enabled`; still forbid scan/connect, credentials, server exposure, external probes, and routing mutation.

### V438. Android Wi-Fi Re-enable Observation Result

- plan: `docs/plans/NATIVE_INIT_V438_ANDROID_WIFI_REENABLE_OBSERVATION_PLAN_2026-05-20.md`
- report: `docs/reports/NATIVE_INIT_V438_ANDROID_WIFI_REENABLE_OBSERVATION_2026-05-20.md`
- live evidence: `tmp/wifi/v438-android-wifi-reenable-handoff-live-20260520-165358/`
- result: bounded Android Wi-Fi re-enable observation PASS. Android accepted `cmd wifi set-wifi-enabled enabled`; post-enable status reported Wi-Fi enabled, but no active Wi-Fi connection, no `wlan0` IP, no `wlan0` route candidate, no validated Wi-Fi connectivity, no DNS surface, and no global listener were observed. Native rollback restored `A90 Linux init 0.9.61 (v319)`, postflight selftest passed, and redaction scan passed.
- interpretation: V438 is a controlled bring-up observation, not permission for scan/connect, credentials, server exposure, or external traffic. Android framework Wi-Fi is now set enabled and may persist on a future Android boot, even though the current native boot is contained.
- next: V439 post-reenable persistence and containment decision. Either run a longer read-only enabled observation, or disable Wi-Fi again to restore the V436 contained baseline before continuing native/server-side work.

### V439. Android Post-reenable Observation Result

- plan: `docs/plans/NATIVE_INIT_V439_ANDROID_POST_REENABLE_OBSERVATION_PLAN_2026-05-20.md`
- report: `docs/reports/NATIVE_INIT_V439_ANDROID_POST_REENABLE_OBSERVATION_2026-05-20.md`
- live evidence: `tmp/wifi/v439-android-wifi-post-reenable-handoff-live-20260520-170736/`
- result: Android post-reenable observation PASS with exposure observed. V439 did not enable Wi-Fi; it observed the V438-enabled Android state. Android immediately auto-connected and exposed `wlan0` IP, default route, route-get, DNS, and validated Wi-Fi connectivity across seven samples, with no global listener observed. Final cleanup disable passed and removed active IP/route/DNS/connectivity exposure. Native rollback restored `A90 Linux init 0.9.61 (v319)`.
- interpretation: Android-managed Wi-Fi is now proven functional, but it is also proven to create external network exposure via saved auto-connect. Cleanup containment works, so lab-safe work should default to disabled Wi-Fi except during bounded Wi-Fi tests.
- next: V440 Android Wi-Fi control policy after proven auto-connect. Decide contained lab mode versus exposure-aware Android Wi-Fi mode versus explicit scan/connect mode before any server exposure or credential work.

### V440. Android Wi-Fi Control Policy Result

- plan: `docs/plans/NATIVE_INIT_V440_ANDROID_WIFI_CONTROL_POLICY_PLAN_2026-05-20.md`
- report: `docs/reports/NATIVE_INIT_V440_ANDROID_WIFI_CONTROL_POLICY_2026-05-20.md`
- host-run evidence: `tmp/wifi/v440-android-wifi-control-policy-hostrun-20260520-171835/`
- result: host-side policy selector PASS. Selected `contained-lab-default` because V439 proved Android-managed Wi-Fi functionality, immediate external route/DNS/connectivity exposure through saved auto-connect, no global listener, and successful cleanup containment.
- interpretation: default lab state is Wi-Fi disabled unless a bounded Wi-Fi test is active. Android-managed Wi-Fi may be used for explicit exposure-aware test windows, but server exposure and explicit scan/connect remain blocked until policy/credential/target handling is documented.
- next: V441 planning. Choose exposure-aware Wi-Fi stability observation with cleanup, or explicit scan/connect credential and target allowlist design. Serverization remains blocked.

### V441. Android Wi-Fi Exposure-aware Stability Result

- plan: `docs/plans/NATIVE_INIT_V441_ANDROID_WIFI_EXPOSURE_STABILITY_PLAN_2026-05-20.md`
- report: `docs/reports/NATIVE_INIT_V441_ANDROID_WIFI_EXPOSURE_STABILITY_2026-05-20.md`
- live evidence: `tmp/wifi/v441-android-wifi-exposure-stability-live-20260520-172446/`
- result: exposure-aware Android-managed Wi-Fi stability PASS. V441 used V438 to enable Wi-Fi and V439 to observe 11 samples over 300 seconds. All samples stayed connected/exposed with `wlan0` IP, default route, route-get, validated connectivity, and DNS surface; no global listener was observed. Cleanup disable passed and removed active IP/route/DNS/connectivity exposure. Native rollback restored `A90 Linux init 0.9.61 (v319)`.
- interpretation: Android-managed Wi-Fi is functionally stable enough for bounded test windows. The next risk boundary is explicit scan/connect and credential/target handling, not basic connectivity. Server exposure remains blocked.
- next: V442 credential/target allowlist design before explicit scan/connect. Longer stability can be run later, but the immediate design gap is policy-safe credential and target handling.

### V442. Wi-Fi Target Policy Result

- plan: `docs/plans/NATIVE_INIT_V442_WIFI_TARGET_POLICY_PLAN_2026-05-20.md`
- report: `docs/reports/NATIVE_INIT_V442_WIFI_TARGET_POLICY_2026-05-20.md`
- host-run evidence: `tmp/wifi/v442-android-wifi-target-policy-hostrun-20260520-174415/`
- result: host-side target/credential policy gate PASS in template mode. V441 evidence was ready, V442 generated a secret-free target policy template, and the tracked example policy was correctly rejected as not live-ready because it contains a placeholder `ssid_sha256`.
- interpretation: explicit scan/connect is now blocked on an operator-provided private untracked target policy, not on basic Wi-Fi function. Raw SSID/BSSID/password/passphrase/PSK values must not enter tracked files or evidence.
- next: V443 private-policy validation plus explicit scan/connect preflight. Do not issue scan/connect until V442 returns `v442-wifi-target-policy-allowlist-ready` for a private policy.

### V443. Wi-Fi Private Policy Materialize Result

- plan: `docs/plans/NATIVE_INIT_V443_WIFI_PRIVATE_POLICY_MATERIALIZE_PLAN_2026-05-20.md`
- report: `docs/reports/NATIVE_INIT_V443_WIFI_PRIVATE_POLICY_MATERIALIZE_2026-05-20.md`
- evidence:
  - `tmp/wifi/v443-private-policy-materialize-plan-20260520-174833/`
  - `tmp/wifi/v443-private-policy-materialize-env-missing-20260520-174833/`
- result: materializer plan PASS and env-missing negative validation PASS. `A90_WIFI_SSID` and `A90_WIFI_PSK` are not currently present, so V443 refused to create a private policy.
- interpretation: the private policy materializer is ready. The next blocker is local operator env values, which must not be pasted into chat, committed, or written to tracked files.
- next: set `A90_WIFI_SSID` and `A90_WIFI_PSK` locally, rerun V443 to produce `v443-wifi-private-policy-materialized-pass`, then proceed to V444 explicit scan/connect preflight.

### V444. Wi-Fi Explicit Connect Preflight Result

- plan: `docs/plans/NATIVE_INIT_V444_WIFI_EXPLICIT_CONNECT_PREFLIGHT_PLAN_2026-05-20.md`
- report: `docs/reports/NATIVE_INIT_V444_WIFI_EXPLICIT_CONNECT_PREFLIGHT_2026-05-20.md`
- evidence:
  - `tmp/wifi/v444-explicit-connect-preflight-plan-20260520-175411/`
  - `tmp/wifi/v444-explicit-connect-preflight-missing-policy-20260520-175411/`
  - `tmp/wifi/v444-explicit-connect-preflight-synthetic-pass-20260520-175411/`
- result: host-side explicit scan/connect preflight implemented. Missing real private policy is blocked as expected. Synthetic positive path passed and did not leak synthetic SSID/PSK into evidence.
- interpretation: V445 live execution is now technically gated, but real execution remains blocked until V443 materializes a private policy from local env values and V444 returns `v444-wifi-explicit-connect-preflight-ready` for that policy.
- next: provide local private env values, rerun V443 and V444, then run V445 bounded explicit scan/connect. Server exposure remains blocked.

### V445. Wi-Fi Explicit Connect Live Runner Result

- plan: `docs/plans/NATIVE_INIT_V445_WIFI_EXPLICIT_CONNECT_LIVE_PLAN_2026-05-20.md`
- report: `docs/reports/NATIVE_INIT_V445_WIFI_EXPLICIT_CONNECT_LIVE_2026-05-20.md`
- evidence:
  - `tmp/wifi/v445-explicit-connect-live-plan-20260520-180041/`
  - `tmp/wifi/v445-explicit-connect-live-dryrun-20260520-180041/`
  - `tmp/wifi/v445-explicit-connect-live-missing-policy-fixed-20260520-180117/`
- result: V445 bounded explicit scan/connect live runner implemented. Plan/dry-run passed. Missing real policy live attempt was blocked by V444 preflight before Android boot/flash; no device commands, no device mutations, no Wi-Fi bring-up.
- interpretation: the live runner exists and is fail-closed at the correct boundary. Actual V445 live remains blocked until V443 materializes a private policy and V444 returns ready for that policy.
- next: set local private env values, run V443, rerun V444, then run V445 live. Server exposure remains blocked.

### V446. Wi-Fi Private Secret Guard Result

- plan: `docs/plans/NATIVE_INIT_V446_WIFI_PRIVATE_SECRET_GUARD_PLAN_2026-05-20.md`
- report: `docs/reports/NATIVE_INIT_V446_WIFI_PRIVATE_SECRET_GUARD_2026-05-20.md`
- evidence:
  - clean scan `tmp/wifi/v446-wifi-private-secret-guard-postdoc-20260520-181446/`
  - negative probe `tmp/wifi/v446-wifi-private-secret-guard-negative-20260520-181251/`
- result: repository-side private Wi-Fi secret guard PASS. `.gitignore` now blocks local env and private/local Wi-Fi target policy filenames. The scanner passed on current tracked plus untracked repository-visible files, and a synthetic negative probe correctly failed closed with findings before the probe was removed.
- interpretation: V445 live is still blocked by missing real private env/policy, but the local credential flow now has a repo guard before V443/V444/V445.
- next: set local private env values outside chat/tracked files, run V443 materialization, run V444 preflight, then run V445 live. Server exposure remains blocked.

### V447. Wi-Fi Explicit Connect Flow Result

- plan: `docs/plans/NATIVE_INIT_V447_WIFI_EXPLICIT_CONNECT_FLOW_PLAN_2026-05-20.md`
- report: `docs/reports/NATIVE_INIT_V447_WIFI_EXPLICIT_CONNECT_FLOW_2026-05-20.md`
- evidence:
  - plan `tmp/wifi/v447-explicit-connect-flow-plan-final2-20260520-182148/`
  - env-missing `tmp/wifi/v447-explicit-connect-flow-env-missing-final2-20260520-182148/`
  - synthetic preflight `tmp/wifi/v447-explicit-connect-flow-synthetic-final2-20260520-182148/`
- result: one-command gated flow implemented. Current real env state blocks at V443 because `A90_WIFI_SSID` and `A90_WIFI_PSK` are absent. Synthetic host-only flow passed V446, V443, and V444 and stopped before V445 live.
- interpretation: manual sequencing is no longer the blocker. The next blocker is local private Wi-Fi env input, followed by a V447 host preflight and explicit V447/V445 live run.
- next: set private local env values outside chat/tracked files, run V447 host preflight, then rerun V447 with live flags for bounded explicit scan/connect. Server exposure remains blocked.

### V448. Wi-Fi Operator Handoff Packet Result

- plan: `docs/plans/NATIVE_INIT_V448_WIFI_OPERATOR_HANDOFF_PACKET_PLAN_2026-05-20.md`
- report: `docs/reports/NATIVE_INIT_V448_WIFI_OPERATOR_HANDOFF_PACKET_2026-05-20.md`
- evidence:
  - plan `tmp/wifi/v448-operator-handoff-packet-plan-final-20260520-182644/`
  - run `tmp/wifi/v448-operator-handoff-packet-run-final-20260520-182644/`
- result: private handoff packet PASS. V448 ran V446, ran V447 plan, then generated ignored scripts for V447 host preflight and V447 live without storing Wi-Fi values.
- interpretation: the repo-side and operator-sequencing work is ready for the real private Wi-Fi input. V448 itself did not run V443/V444/V445, mutate the device, or bring Wi-Fi up.
- next: run `bash /home/temmie/dev/A90_5G_rooting/tmp/wifi/v448-operator-handoff-packet-run-final-20260520-182644/run-v447-host-preflight.sh`, enter Wi-Fi values locally, then run the generated live script only if preflight returns ready. Server exposure remains blocked.

### V449. Wi-Fi Handoff Result Router Result

- plan: `docs/plans/NATIVE_INIT_V449_WIFI_HANDOFF_RESULT_ROUTER_PLAN_2026-05-20.md`
- report: `docs/reports/NATIVE_INIT_V449_WIFI_HANDOFF_RESULT_ROUTER_2026-05-20.md`
- evidence:
  - plan `tmp/wifi/v449-wifi-handoff-result-router-plan-final-20260520-183130/`
  - run `tmp/wifi/v449-wifi-handoff-result-router-run-final-20260520-183130/`
- result: handoff result router PASS. V449 read current V448/V447/V445 evidence, ignored synthetic/plan/env-missing evidence by default, and classified the state as `v449-wifi-handoff-packet-ready-run-preflight`.
- interpretation: the current safe next action is the generated V448 host preflight script. No private V447 preflight result exists yet.
- next: run the recommended host preflight script, then rerun V449. If private preflight passes, V449 should recommend the generated live script. Server exposure remains blocked.

### V450. Wi-Fi Operator Preflight Readiness Result

- plan: `docs/plans/NATIVE_INIT_V450_WIFI_OPERATOR_PREFLIGHT_READINESS_PLAN_2026-05-20.md`
- report: `docs/reports/NATIVE_INIT_V450_WIFI_OPERATOR_PREFLIGHT_READINESS_2026-05-20.md`
- evidence:
  - plan `tmp/wifi/v450-operator-preflight-readiness-plan-final-20260520-183553/`
  - run `tmp/wifi/v450-operator-preflight-readiness-run-final-20260520-183553/`
- result: operator preflight readiness PASS. V450 confirmed the latest V448 packet is ready, generated scripts are private and structurally valid, V449 routes to host preflight, and no private preflight/live result has superseded the packet yet.
- interpretation: there is no remaining repo-side/env-free blocker before local Wi-Fi input. The next required action is running the generated host preflight script.
- next: run `bash /home/temmie/dev/A90_5G_rooting/tmp/wifi/v448-operator-handoff-packet-run-final-20260520-182644/run-v447-host-preflight.sh`, then rerun V449/V450. Server exposure remains blocked.

### V451. Wi-Fi Operator Script Validation Result

- plan: `docs/plans/NATIVE_INIT_V451_WIFI_OPERATOR_SCRIPT_VALIDATION_PLAN_2026-05-20.md`
- report: `docs/reports/NATIVE_INIT_V451_WIFI_OPERATOR_SCRIPT_VALIDATION_2026-05-20.md`
- evidence:
  - plan `tmp/wifi/v451-operator-script-validation-plan-final-20260520-184016/`
  - run `tmp/wifi/v451-operator-script-validation-run-final-20260520-184016/`
- result: operator script validation PASS. V451 validated generated V448 host preflight/live scripts with `bash -n`, verified host preflight empty-input fail-closed behavior, and verified live cancellation fail-closed behavior.
- interpretation: generated operator scripts now have syntax and fail-closed prompt validation in addition to V450 structural/private-mode validation.
- next: run the generated host preflight script, enter Wi-Fi values locally, then rerun V449/V450. Server exposure remains blocked.

### V452. Wi-Fi Live Cleanup Proof Result

- plan: `docs/plans/NATIVE_INIT_V452_WIFI_LIVE_CLEANUP_PROOF_PLAN_2026-05-20.md`
- report: `docs/reports/NATIVE_INIT_V452_WIFI_LIVE_CLEANUP_PROOF_2026-05-20.md`
- evidence:
  - pre-live run `tmp/wifi/v452-wifi-live-cleanup-proof-run-final-20260520-184611/`
  - synthetic pass `tmp/wifi/v452-wifi-live-cleanup-proof-synth-pass-final-20260520-184611/`
  - synthetic blocked cleanup `tmp/wifi/v452-wifi-live-cleanup-proof-synth-block-final-20260520-184611/`
- result: post-live cleanup proof gate implemented. Current real state is `v452-wifi-live-cleanup-proof-awaiting-live`, which is expected before private host preflight/live. Synthetic pass and blocked-cleanup paths verified that the gate accepts complete cleanup evidence and fails closed on incomplete cleanup.
- interpretation: after eventual V447 live, V452 must pass before Wi-Fi stability or server binding work proceeds.
- next: run the generated host preflight script, enter Wi-Fi values locally, run live if routed, then run V452 on live evidence. Server exposure remains blocked.

### V453. Wi-Fi Operator Post-route Packet Result

- plan: `docs/plans/NATIVE_INIT_V453_WIFI_OPERATOR_POSTROUTE_PACKET_PLAN_2026-05-20.md`
- report: `docs/reports/NATIVE_INIT_V453_WIFI_OPERATOR_POSTROUTE_PACKET_2026-05-20.md`
- evidence:
  - packet `tmp/wifi/v453-operator-postroute-packet-run-final-20260520-185152/`
  - router `tmp/wifi/v449-wifi-handoff-result-router-v453-final-20260520-185152/`
  - readiness `tmp/wifi/v450-operator-preflight-readiness-v453-final-20260520-185152/`
- result: post-route operator packet PASS. V453 generated preflight/live scripts that run V449/V450/V452 automatically after V447 attempts, validated their shell syntax and fail-closed prompt behavior, and updated V449/V450 routing to prefer the latest V448 or V453 packet.
- interpretation: V453 supersedes the older V448 packet for the next operator action. The next command now records routing/proof evidence automatically after execution.
- next: run `bash /home/temmie/dev/A90_5G_rooting/tmp/wifi/v453-operator-postroute-packet-run-final-20260520-185152/run-v453-host-preflight-and-route.sh`, enter Wi-Fi values locally, then follow the routed live command. Server exposure remains blocked.

### V454. Wi-Fi Operator Strict Post-route Packet Result

- plan: `docs/plans/NATIVE_INIT_V454_WIFI_OPERATOR_STRICT_POSTROUTE_PACKET_PLAN_2026-05-20.md`
- report: `docs/reports/NATIVE_INIT_V454_WIFI_OPERATOR_STRICT_POSTROUTE_PACKET_2026-05-20.md`
- evidence:
  - packet `tmp/wifi/v454-operator-strict-postroute-packet-run-20260520-185718/`
  - router `tmp/wifi/v449-wifi-handoff-result-router-v454-20260520-185718/`
  - readiness `tmp/wifi/v450-operator-preflight-readiness-v454-20260520-185718/`
- result: strict post-route operator packet PASS. V454 generated preflight/live scripts that run V449/V450/V452 automatically after V447 attempts and return a post-route failure if V447 succeeds but route/proof evidence generation fails.
- interpretation: V454 supersedes V453 for the next operator action. It is the strongest current handoff packet.
- next: run `bash /home/temmie/dev/A90_5G_rooting/tmp/wifi/v454-operator-strict-postroute-packet-run-20260520-185718/run-v454-host-preflight-strict-route.sh`, enter Wi-Fi values locally, then follow the routed live command. Server exposure remains blocked.

### V455. Wi-Fi Strict Post-route Semantics Result

- plan: `docs/plans/NATIVE_INIT_V455_WIFI_STRICT_POSTROUTE_SEMANTICS_PLAN_2026-05-20.md`
- report: `docs/reports/NATIVE_INIT_V455_WIFI_STRICT_POSTROUTE_SEMANTICS_2026-05-20.md`
- evidence:
  - plan `tmp/wifi/v455-strict-postroute-semantics-plan-20260520-190248/`
  - run `tmp/wifi/v455-strict-postroute-semantics-run-20260520-190248/`
- result: strict post-route semantics PASS. V455 audited the generated V454 scripts for strict markers and proved the return-code matrix: V447 success plus route/proof failure fails the script, while V447 failure preserves the V447 return code.
- interpretation: V454 strict behavior is now proven without executing generated operator scripts or device commands.
- next: run `bash /home/temmie/dev/A90_5G_rooting/tmp/wifi/v454-operator-strict-postroute-packet-run-20260520-185718/run-v454-host-preflight-strict-route.sh`, enter Wi-Fi values locally, then follow the routed live command. Server exposure remains blocked.

### V456. Wi-Fi Operator One-session Packet Result

- plan: `docs/plans/NATIVE_INIT_V456_WIFI_OPERATOR_ONE_SESSION_PACKET_PLAN_2026-05-20.md`
- report: `docs/reports/NATIVE_INIT_V456_WIFI_OPERATOR_ONE_SESSION_PACKET_2026-05-20.md`
- evidence:
  - plan `tmp/wifi/v456-operator-one-session-packet-plan-20260520-191243/`
  - packet `tmp/wifi/v456-operator-one-session-packet-run-20260520-191231/`
  - router `tmp/wifi/v449-wifi-handoff-result-router-v456-20260520-191231/`
  - readiness `tmp/wifi/v450-operator-preflight-readiness-v456-20260520-191231/`
  - secret guard `tmp/wifi/v446-wifi-private-secret-guard-v456-repair2-20260520-191231/`
- result: one-session operator packet PASS. V456 generated one private script that prompts once, runs V447 preflight, routes/proves the result, then optionally runs V447 live after exact `V447-LIVE` confirmation.
- interpretation: V456 supersedes V454 as the next operator action because it preserves strict post-route behavior while removing duplicate Wi-Fi credential prompts.
- next: run `bash /home/temmie/dev/A90_5G_rooting/tmp/wifi/v456-operator-one-session-packet-run-20260520-191231/run-v456-one-session-wifi-flow.sh`, enter Wi-Fi values locally, and type `V447-LIVE` only if preflight passes. Server exposure remains blocked.

### V457. Wi-Fi Operator Session Outcome Result

- plan: `docs/plans/NATIVE_INIT_V457_WIFI_OPERATOR_SESSION_OUTCOME_PLAN_2026-05-20.md`
- report: `docs/reports/NATIVE_INIT_V457_WIFI_OPERATOR_SESSION_OUTCOME_2026-05-20.md`
- evidence:
  - plan `tmp/wifi/v457-wifi-operator-session-outcome-plan-20260520-191957/`
  - run `tmp/wifi/v457-wifi-operator-session-outcome-run-20260520-191957/`
  - secret guard `tmp/wifi/v446-wifi-private-secret-guard-v457-20260520-191957/`
- result: outcome gate PASS. Current state is `v457-wifi-session-awaiting-operator` because V456 is ready and no real V447 preflight/live evidence exists yet.
- interpretation: V457 is the no-secret post-run classifier. After the operator runs V456, V457 summarizes whether the session is blocked, live-pending, cleanup-proof-pending, or ready for bounded stability/server-binding policy.
- next: run the V456 one-session script locally, then run `python3 scripts/revalidation/wifi_operator_session_outcome_v457.py run`. Server exposure remains blocked.

### V458. Wi-Fi Operator Session Bundle Result

- plan: `docs/plans/NATIVE_INIT_V458_WIFI_OPERATOR_SESSION_BUNDLE_PLAN_2026-05-20.md`
- report: `docs/reports/NATIVE_INIT_V458_WIFI_OPERATOR_SESSION_BUNDLE_2026-05-20.md`
- evidence:
  - plan `tmp/wifi/v458-wifi-operator-session-bundle-plan-20260520-192406/`
  - run `tmp/wifi/v458-wifi-operator-session-bundle-run-20260520-192406/`
  - secret guard `tmp/wifi/v446-wifi-private-secret-guard-v458-20260520-192406/`
- result: sanitized session bundle PASS. Current state is `v458-wifi-session-bundle-awaiting-operator` with `leak_findings=0`.
- interpretation: after V456 runs, V457 should classify the result and V458 should package the current evidence as a sanitized index without copying raw captures.
- next: run the V456 one-session script locally, then run V457 and V458. Server exposure remains blocked.

### V459. Wi-Fi NetworkManager Profile Handoff Result

- plan: `docs/plans/NATIVE_INIT_V459_WIFI_NM_PROFILE_HANDOFF_PLAN_2026-05-20.md`
- report: `docs/reports/NATIVE_INIT_V459_WIFI_NM_PROFILE_HANDOFF_2026-05-20.md`
- evidence:
  - packet `tmp/wifi/v459-nm-profile-handoff-packet-run-20260520-193122/`
  - router `tmp/wifi/v449-wifi-handoff-result-router-v459-20260520-193122/`
  - readiness `tmp/wifi/v450-operator-preflight-readiness-v459-20260520-193122/`
  - outcome `tmp/wifi/v457-wifi-operator-session-outcome-v459-20260520-193122/`
  - bundle `tmp/wifi/v458-wifi-operator-session-bundle-v459-20260520-193122/`
  - secret guard `tmp/wifi/v446-wifi-private-secret-guard-v459-final-20260520-193122/`
- result: saved-profile handoff PASS. V459 generated a private script that lists saved NetworkManager Wi-Fi profiles by number and length metadata only, then runs V447 preflight/live with strict route/proof handling.
- interpretation: V459 supersedes V456 as the preferred next local action on this host because two saved Wi-Fi profiles exist and the operator can choose by number without typing SSID/PSK into the terminal.
- next: run `bash /home/temmie/dev/A90_5G_rooting/tmp/wifi/v459-nm-profile-handoff-packet-run-20260520-193122/run-v459-nm-profile-wifi-flow.sh`, select the intended saved profile, and type `V447-LIVE` only if preflight passes. Server exposure remains blocked.

### V460. Wi-Fi Live Retry Pass Result

- plan: `docs/plans/NATIVE_INIT_V460_WIFI_LIVE_RETRY_PASS_PLAN_2026-05-20.md`
- report: `docs/reports/NATIVE_INIT_V460_WIFI_LIVE_RETRY_PASS_2026-05-20.md`
- evidence:
  - live `tmp/wifi/v447-explicit-connect-flow-live-20260520-194306/`
  - cleanup proof `tmp/wifi/v452-wifi-live-cleanup-proof-postlive-20260520-194829/`
  - outcome `tmp/wifi/v457-wifi-operator-session-outcome-postlive2-20260520-194857/`
  - bundle `tmp/wifi/v458-wifi-operator-session-bundle-postlive2-20260520-194857/`
- result: bounded Wi-Fi live PASS. V447 live produced explicit scan/connect evidence, V452 proved cleanup containment and rollback step presence, and native `A90 Linux init 0.9.61 (v319)` was verified after rollback.
- interpretation: Wi-Fi bring-up is proven for a bounded live run. This is not yet a long-running Wi-Fi stability or server exposure approval.
- next: plan bounded Wi-Fi stability and binding policy before any server exposure. Server exposure remains blocked.

### V742. Execns Helper v122 Deploy Result

- plan: `docs/plans/NATIVE_INIT_V742_EXECNS_HELPER_V122_DEPLOY_PLAN_2026-05-24.md`
- report: `docs/reports/NATIVE_INIT_V742_EXECNS_HELPER_V122_DEPLOY_2026-05-24.md`
- evidence: `tmp/wifi/v742-execns-helper-v122-deploy-run-serial1850/`
- result: helper v122 deployed to `/cache/bin/a90_android_execns_probe`; remote SHA `032fe43041b908577bb1a2e4b3ff7a7dfea24958169723907df5d403f811e989` and marker `a90_android_execns_probe v122` verified.
- interpretation: helper v122 deployment is not the active blocker. Serial chunk size `1850` is safe; chunk size `3000` was rejected before writes because it exceeded the safe command-line limit.
- next: run current-boot V741 gated `mdm_helper` proof after SELinuxfs and policy-load prep.

### V743. V741 Current Live Execution Result

- plan: `docs/plans/NATIVE_INIT_V743_V741_CURRENT_LIVE_EXECUTION_PLAN_2026-05-24.md`
- report: `docs/reports/NATIVE_INIT_V743_V741_CURRENT_LIVE_EXECUTION_2026-05-24.md`
- evidence: `tmp/wifi/v743-v741-mdm-helper-gated-live-current/`
- result: V741 gated mode ran safely, `mss` reached `ONLINE`, lower/CNSS children started, but service `74` gate stayed closed and `mdm_helper` was not started. Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping were not executed.
- interpretation: do not force `mdm_helper`; first separate whether the gate miss is helper v122 regression or gated-mode timing/logic.
- next: rerun V735 CNSS-only path with helper v122.

### V744. V122 CNSS-only Comparison Result

- plan: `docs/plans/NATIVE_INIT_V744_V122_CNSS_ONLY_COMPARISON_PLAN_2026-05-24.md`
- report: `docs/reports/NATIVE_INIT_V744_V122_CNSS_ONLY_COMPARISON_2026-05-24.md`
- evidence: `tmp/wifi/v744-v122-cnss-only-comparison-retry/`
- result: helper v122 still reproduces the V735 CNSS-only service publication path: `mss=ONLINE`, QRTR RX/TX, `sysmon-qmi`, and service-notifier `180` appeared; MHI/QCA6390/WLFW/service `69`/BDF/`wlan0` remained absent.
- interpretation: helper v122 itself is not the regression. The active blocker is now the service-publication-to-MHI/WLFW gap, plus a secondary repair candidate in V741 gated `mdm_helper` gate timing.
- next: implement a two-phase same-window proof: first observe CNSS-only service publication, then start `mdm_helper` only after that marker, still below service-manager/HAL/scan/connect.

### V745. Service180-gated MDM Helper Prep Result

- plan: `docs/plans/NATIVE_INIT_V745_SERVICE180_GATED_MDM_HELPER_PLAN_2026-05-24.md`
- prep report: `docs/reports/NATIVE_INIT_V745_SERVICE180_GATED_MDM_HELPER_PREP_2026-05-24.md`
- live report: `docs/reports/NATIVE_INIT_V745_SERVICE180_GATED_MDM_HELPER_LIVE_2026-05-24.md`
- evidence:
  - helper build `tmp/wifi/v745-execns-helper-v123-build/`
  - runner plan `tmp/wifi/v745-mdm-helper-service180-live-plan2/`
  - deploy preflight `tmp/wifi/v745-execns-helper-v123-deploy-preflight-after-hide/`
  - deploy run `tmp/wifi/v745-execns-helper-v123-deploy-run-serial1850/`
  - live run `tmp/wifi/v745-mdm-helper-service180-live-current/`
- result: helper v123 deployed and live-tested. The run reached `mss=ONLINE`, QRTR RX/TX, and `sysmon-qmi`, but service `180` gate stayed closed; `mdm_helper`, service-manager, Wi-Fi HAL, scan/connect, DHCP/routes, credentials, and external ping were not executed.
- interpretation: service `180` is not stable enough as the next live gate. `sysmon-qmi` is the reproducible lower marker in the same window.
- next: implement and deploy helper v124 with sysmon-gated `mdm_helper` start-only.

### V746. Sysmon-gated MDM Helper Prep Result

- plan: `docs/plans/NATIVE_INIT_V746_SYSMON_GATED_MDM_HELPER_PLAN_2026-05-24.md`
- prep report: `docs/reports/NATIVE_INIT_V746_SYSMON_GATED_MDM_HELPER_PREP_2026-05-24.md`
- live report: `docs/reports/NATIVE_INIT_V746_SYSMON_GATED_MDM_HELPER_LIVE_2026-05-24.md`
- evidence:
  - helper build `tmp/wifi/v746-execns-helper-v124-build/`
  - runner plan `tmp/wifi/v746-mdm-helper-sysmon-live-plan-final/`
  - deploy preflight `tmp/wifi/v746-execns-helper-v124-deploy-preflight-final/`
  - deploy run `tmp/wifi/v746-execns-helper-v124-deploy-run-serial1850/`
  - live run `tmp/wifi/v746-mdm-helper-sysmon-live-current/`
- result: helper v124 deployed and live-tested. The `sysmon-qmi` gate opened, `mdm_helper` started and was postflight-safe, but `mdm3` stayed `OFFLINING`; MHI/QCA6390/WLFW/service `69`/BDF/`wlan0` stayed absent. Service-manager, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping were not executed.
- interpretation: `mdm_helper` is not sufficient for the current lower blocker. Native evidence now shows the `a0000000.qcom,cnss-qca6390` platform device exists but has no `driver` link, and `/sys/bus/mhi/devices` is empty.
- next: V747 should be a read-only Android/native QCA6390 driver-binding and MHI power-up comparison. Do not perform generic ICNSS/CNSS bind or unbind.

### V747. QCA6390 Driver-binding Delta Plan

- plan: `docs/plans/NATIVE_INIT_V747_QCA6390_DRIVER_BINDING_DELTA_PLAN_2026-05-24.md`
- report: `docs/reports/NATIVE_INIT_V747_QCA6390_DRIVER_BINDING_DELTA_2026-05-24.md`
- basis evidence:
  - `tmp/wifi/v746-mdm-helper-sysmon-live-current/`
  - `tmp/wifi/v717-provider-first-icnss-edge-long-observe-20260524-103333/`
  - `tmp/wifi/v717-icnss-edge-surface-classifier/`
  - `tmp/wifi/v717-qca-bind-reconciliation/`
- run evidence: `tmp/wifi/v747-qca6390-driver-binding-delta/`
- result: host-only classifier passed with decision `v747-qca-driver-link-gap-not-bind-target`. V746 confirms `mdm_helper` is safe but insufficient; QCA6390 child remains unbound; V716 keeps bind/unbind blocked; Android reference is usable.
- interpretation: the next target is not `mdm_helper` and not QCA6390 `bind`/`unbind`.
- next: V748 classified the remaining candidate matrix and selected a read-only non-bind ICNSS/QCA WLFW trigger capture as the next gate.

### V748. Non-bind ICNSS/QCA Power-up Trigger Classifier

- plan: `docs/plans/NATIVE_INIT_V748_NONBIND_POWERUP_TRIGGER_PLAN_2026-05-24.md`
- report: `docs/reports/NATIVE_INIT_V748_NONBIND_POWERUP_TRIGGER_2026-05-24.md`
- runner: `scripts/revalidation/native_wifi_nonbind_powerup_trigger_v748.py`
- plan evidence: `tmp/wifi/v748-nonbind-powerup-trigger-plan/`
- preflight evidence: `tmp/wifi/v748-nonbind-powerup-trigger-preflight/`
- run evidence: `tmp/wifi/v748-nonbind-powerup-trigger/`
- decision: `v748-icnss-qmi-wlfw-nonbind-trigger-selected`
- result: host-only classifier passed. It rejected QCA6390 `bind`/`unbind`, `mdm_helper` retry, repeated CNSS/HAL start, and `wlan` module load; it marked the private vendor firmware namespace as satisfied.
- interpretation: the remaining pre-connection blocker is below Wi-Fi HAL/connect. The next unit must identify the non-bind ICNSS/CNSS2/QCA path that advances Android from ICNSS parent readiness to WLFW/BDF/`wlan0`.
- next: V749 selected the concrete non-bind control candidate for the next lower-window proof.

### V749. Non-bind Trigger Selector

- plan: `docs/plans/NATIVE_INIT_V749_NONBIND_TRIGGER_SELECTOR_PLAN_2026-05-24.md`
- report: `docs/reports/NATIVE_INIT_V749_NONBIND_TRIGGER_SELECTOR_2026-05-24.md`
- runner: `scripts/revalidation/native_wifi_nonbind_trigger_selector_v749.py`
- plan evidence: `tmp/wifi/v749-nonbind-trigger-selector-plan/`
- preflight evidence: `tmp/wifi/v749-nonbind-trigger-selector-preflight/`
- run evidence: `tmp/wifi/v749-nonbind-trigger-selector/`
- decision: `v749-lower-window-boot-wlan-trigger-selected`
- result: read-only selector passed. Current native exposes `boot_wlan` and `qcwlanstate=OFF`, does not expose `fs_ready`, and still has no `/dev/wlan`, wiphy, or `wlan0`.
- interpretation: standalone `boot_wlan` and standalone `qcwlanstate` are already rejected by V508/V513. The only useful next write is a bounded `boot_wlan` proof inside the lower-ready firmware/modem/companion window.
- next: V750 should implement lower-window `boot_wlan` observe only. Keep service-manager, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, and bind/unbind blocked.

### V750. Lower-window Boot WLAN Proof

- plan: `docs/plans/NATIVE_INIT_V750_LOWER_WINDOW_BOOT_WLAN_PLAN_2026-05-24.md`
- report: `docs/reports/NATIVE_INIT_V750_LOWER_WINDOW_BOOT_WLAN_2026-05-24.md`
- runner: `scripts/revalidation/native_wifi_lower_window_boot_wlan_v750.py`
- evidence:
  - plan `tmp/wifi/v750-lower-window-boot-wlan-plan/`
  - first preflight `tmp/wifi/v750-lower-window-boot-wlan-preflight/`
  - current V401 `tmp/wifi/v750-v401-current-run/`
  - current V490 `tmp/wifi/v750-v490-current-run/`
  - final preflight `tmp/wifi/v750-lower-window-boot-wlan-preflight-retry/`
  - live `tmp/wifi/v750-lower-window-boot-wlan/`
- decision: `v750-lower-window-boot-wlan-control-surface-only`
- result: live proof passed safely. Firmware mounts, `subsys_modem` holder, QRTR RX/TX, `sysmon-qmi`, lower companion contract, `boot_wlan` write, and reboot cleanup all passed. `qcwlanstate` stayed `OFF`; `/dev/wlan`, wiphy, `wlan0`, WLFW/service `69`, and BDF stayed absent.
- interpretation: lower-window `boot_wlan` is not the missing single trigger. The active blocker is now the ICNSS/QCA "modules initialized" path before WLFW/BDF/`wlan0`.
- next: V751 should classify why `icnss: Modules not initialized just return` persists in native. Keep bind/unbind, `driver_override`, module load/unload, service-manager, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping blocked.

### V751. ICNSS Module-init Classifier

- plan: `docs/plans/NATIVE_INIT_V751_ICNSS_MODULE_INIT_CLASSIFIER_PLAN_2026-05-24.md`
- report: `docs/reports/NATIVE_INIT_V751_ICNSS_MODULE_INIT_CLASSIFIER_2026-05-24.md`
- runner: `scripts/revalidation/native_wifi_icnss_module_init_classifier_v751.py`
- evidence:
  - plan `tmp/wifi/v751-icnss-module-init-classifier-plan/`
  - run `tmp/wifi/v751-icnss-module-init-classifier/`
- decision: `v751-boot-wlan-hdd-init-stalls-before-driver-loaded`
- result: read-only classifier passed. V750 `boot_wlan` enters QCACLD/HDD init and creates `qcwlanstate`, but `wlan: driver loaded`, ICNSS-QMI, firmware-ready, wiphy, and `wlan0` never appear. Current native has ICNSS parent bound, but no ICNSS net/ieee80211 child and no MHI devices.
- interpretation: the blocker is inside or before the HDD/PLD/register-driver completion path, not the fixed `boot_wlan` write itself.
- next: V752 should choose between bounded CNSS-daemon plus `boot_wlan` ordering proof and deeper HDD/PLD prerequisite instrumentation. Keep service-manager, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, bind/unbind, `driver_override`, and module load/unload blocked.

### V752. CNSS then Boot WLAN Proof

- plan: `docs/plans/NATIVE_INIT_V752_CNSS_THEN_BOOT_WLAN_PLAN_2026-05-24.md`
- report: `docs/reports/NATIVE_INIT_V752_CNSS_THEN_BOOT_WLAN_2026-05-24.md`
- runner: `scripts/revalidation/native_wifi_cnss_then_boot_wlan_v752.py`
- evidence:
  - plan `tmp/wifi/v752-cnss-then-boot-wlan-plan2/`
  - initial preflight `tmp/wifi/v752-cnss-then-boot-wlan-preflight/`
  - current V401 `tmp/wifi/v752-v401-current-run/`
  - current V490 `tmp/wifi/v752-v490-current-run/`
  - final preflight `tmp/wifi/v752-cnss-then-boot-wlan-preflight-retry/`
  - live `tmp/wifi/v752-cnss-then-boot-wlan/`
- decision: `v752-cnss-then-boot-wlan-hdd-init-still-stalls`
- result: live proof passed safely. Firmware mounts, `subsys_modem` holder, QRTR RX/TX, `sysmon-qmi`, six-child CNSS companion start-only, `boot_wlan` observe, and reboot cleanup all passed. `cnss_diag` and `cnss-daemon` started, but `qcwlanstate` stayed `OFF`; `/dev/wlan`, ICNSS net/ieee80211 child, wiphy, `wlan0`, WLFW/service `69`, BDF, ICNSS-QMI, and firmware-ready stayed absent.
- interpretation: CNSS companion ordering before `boot_wlan` is not sufficient. The blocker remains inside or immediately before HDD/PLD/register-driver completion.
- next: V753 should instrument HDD/PLD prerequisites and the missing driver-loaded / ICNSS-QMI transition. Do not repeat CNSS plus `boot_wlan` ordering blindly; keep service-manager, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, bind/unbind, `driver_override`, and module load/unload blocked.

### V753. HDD/PLD Prerequisite Classifier

- plan: `docs/plans/NATIVE_INIT_V753_HDD_PLD_PREREQ_CLASSIFIER_PLAN_2026-05-24.md`
- report: `docs/reports/NATIVE_INIT_V753_HDD_PLD_PREREQ_CLASSIFIER_2026-05-24.md`
- runner: `scripts/revalidation/native_wifi_hdd_pld_prereq_classifier_v753.py`
- evidence:
  - plan `tmp/wifi/v753-hdd-pld-prereq-classifier-plan/`
  - run `tmp/wifi/v753-hdd-pld-prereq-classifier/`
- decision: `v753-hdd-pld-register-driver-gap-needs-instrumentation`
- result: read-only classifier passed. V752 is valid input, stayed in the safety envelope, and confirmed HDD entry (`boot_wlan=True`, `wlan_loading=1`, `hdd_state_major=1`, `qcwlanstate=30`). No explicit `hdd_init`/PLD/register-driver failure marker appeared, and no driver-loaded/ICNSS-QMI/FW-ready/WLFW/BDF/wiphy/`wlan0` marker appeared. Current native remains healthy and contained with no wiphy/`wlan0`.
- interpretation: current evidence cannot distinguish `pld_init`, `hdd_init`, and `wlan_hdd_register_driver` as the stall point. Another CNSS/`boot_wlan` retry is not useful without new instrumentation.
- next: V754 should add bounded, source-backed HDD/PLD/register-driver observability. If this needs boot image changes, use the standard build/flash/rollback gate; keep service-manager, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping blocked.

### V754. HDD/PLD Traceability Selector

- plan: `docs/plans/NATIVE_INIT_V754_HDD_PLD_TRACEABILITY_SELECTOR_PLAN_2026-05-24.md`
- report: `docs/reports/NATIVE_INIT_V754_HDD_PLD_TRACEABILITY_SELECTOR_2026-05-24.md`
- runner: `scripts/revalidation/native_wifi_hdd_pld_traceability_selector_v754.py`
- evidence:
  - plan `tmp/wifi/v754-hdd-pld-traceability-selector-plan/`
  - run `tmp/wifi/v754-hdd-pld-traceability-selector/`
- decision: `v754-tracefs-mount-gated-observer-needed`
- result: read-only selector passed. tracefs/debugfs filesystem support exists, tracefs/debugfs are not mounted, target symbols are partially visible in `/proc/kallsyms`, and no tracefs mount or ftrace write was executed. `available_filter_functions` is not readable until a mount/filter proof.
- interpretation: ftrace readiness is not proven yet, but a bounded tracefs mount/filter proof is the least invasive next observability gate before any boot image instrumentation or another Wi-Fi trigger.
- next: V755 should mount tracefs with cleanup, read `available_tracers`/`current_tracer`/`available_filter_functions`, verify target filter functions, then stop before `boot_wlan`, service-manager, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.

### V755. Tracefs Mount/Filter Proof

- plan: `docs/plans/NATIVE_INIT_V755_TRACEFS_MOUNT_FILTER_PROOF_PLAN_2026-05-24.md`
- report: `docs/reports/NATIVE_INIT_V755_TRACEFS_MOUNT_FILTER_PROOF_2026-05-24.md`
- runner: `scripts/revalidation/native_wifi_tracefs_mount_filter_proof_v755.py`
- evidence:
  - plan `tmp/wifi/v755-tracefs-mount-filter-proof-plan/`
  - preflight retry `tmp/wifi/v755-tracefs-mount-filter-proof-preflight-retry/`
  - final live `tmp/wifi/v755-tracefs-mount-filter-proof-retry/`
- decision: `v755-tracefs-mounted-no-target-filter-functions`
- result: bounded live proof passed. Tracefs mount returned `0`, controls were readable only for `available_tracers`, `current_tracer`, `tracing_on`, and `trace`; `available_filter_functions`, `set_ftrace_filter`, and `set_graph_function` were not readable. Target filter hits were `0`. Cleanup unmounted tracefs and postflight confirmed `mount_tracefs=no`.
- interpretation: ftrace/function-filter instrumentation is not available for the HDD/PLD target on this kernel state. Do not proceed to ftrace write or boot_wlan trace pairing.
- next: V756 should plan non-ftrace HDD/PLD observability: Android/native dmesg differential expansion, source-backed boot image/kernel-log instrumentation feasibility, or another safe non-ftrace signal path. Keep service-manager, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping blocked.

### V756. Non-ftrace HDD/PLD Observability

- plan: `docs/plans/NATIVE_INIT_V756_NONFTRACE_HDD_PLD_OBSERVABILITY_PLAN_2026-05-24.md`
- report: `docs/reports/NATIVE_INIT_V756_NONFTRACE_HDD_PLD_OBSERVABILITY_2026-05-24.md`
- runner: `scripts/revalidation/native_wifi_nonftrace_hdd_pld_observability_v756.py`
- evidence:
  - plan `tmp/wifi/v756-nonftrace-hdd-pld-observability-plan/`
  - run `tmp/wifi/v756-nonftrace-hdd-pld-observability/`
- decision: `v756-nonftrace-live-observers-exhausted`
- result: read-only classifier passed. Dynamic debug is not compiled in and has no control catalog; kprobes and kprobe events are not configured; printk exists but current dmesg does not expose the missing PLD/HDD/register-driver boundary; target kallsyms remain partially visible; no wiphy or `wlan0` appeared.
- interpretation: live ftrace/dyndbg/kprobe instrumentation is not available on this kernel state. Another `boot_wlan` retry will not add evidence.
- next: V757 should either perform expanded Android/native dmesg differential analysis around the HDD/PLD window or plan a rollback-safe boot-image/kernel-log instrumentation unit. Keep service-manager, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping blocked.

### V757. Android/Native HDD/PLD Differential

- plan: `docs/plans/NATIVE_INIT_V757_ANDROID_NATIVE_HDD_PLD_DIFF_PLAN_2026-05-24.md`
- report: `docs/reports/NATIVE_INIT_V757_ANDROID_NATIVE_HDD_PLD_DIFF_2026-05-24.md`
- runner: `scripts/revalidation/native_wifi_android_native_hdd_pld_diff_v757.py`
- evidence:
  - plan `tmp/wifi/v757-android-native-hdd-pld-diff-plan/`
  - run `tmp/wifi/v757-android-native-hdd-pld-diff/`
- decision: `v757-boot-image-log-instrumentation-selected`
- result: host-only classifier passed. Android success evidence contains QMI/BDF/FW-ready/`wlan0`; native V752 evidence contains HDD entry/qcwlanstate creation with success-marker absence; existing Android dmesg has post-FW HDD markers but no pre-QMI PLD/HDD/register-driver boundary.
- interpretation: existing dmesg proves the gap but cannot locate the internal failing call. Live ftrace/dyndbg/kprobe routes are closed.
- next: V758 should classify rollback-safe kernel/source/boot-image log instrumentation feasibility before any patch. Keep service-manager, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping blocked.

### V758. Kernel Instrumentation Feasibility

- plan: `docs/plans/NATIVE_INIT_V758_KERNEL_INSTRUMENTATION_FEASIBILITY_PLAN_2026-05-24.md`
- report: `docs/reports/NATIVE_INIT_V758_KERNEL_INSTRUMENTATION_FEASIBILITY_2026-05-24.md`
- runner: `scripts/revalidation/native_wifi_kernel_instrumentation_feasibility_v758.py`
- evidence:
  - plan `tmp/wifi/v758-kernel-instrumentation-feasibility-plan/`
  - run `tmp/wifi/v758-kernel-instrumentation-feasibility/`
- decision: `v758-source-acquisition-required-before-kernel-instrumentation`
- result: host-only classifier passed. Boot image tooling and rollback artifacts exist, including current/v319/v261/v48 images, but exact local kernel/QCACLD/CNSS source is absent.
- interpretation: boot-image handoff is feasible after source exists, but patching now would be blind and should remain blocked.
- next: V759 should acquire or stage exact SM-A908N/A908NKSU5EWA3-compatible Samsung kernel source and verify target files before any instrumentation patch. Keep live device, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping blocked.

### V759. Source Acquisition Gate

- plan: `docs/plans/NATIVE_INIT_V759_SOURCE_ACQUISITION_PLAN_2026-05-24.md`
- report: `docs/reports/NATIVE_INIT_V759_SOURCE_ACQUISITION_2026-05-24.md`
- runner: `scripts/revalidation/native_wifi_source_acquisition_v759.py`
- evidence:
  - plan `tmp/wifi/v759-source-acquisition-plan/`
  - run `tmp/wifi/v759-source-acquisition/`
- decision: `v759-official-source-identified-manual-download-gated`
- result: host-only classifier passed. The exact Samsung OSRC package is identified as `SM-A908N_KOR_12_Opensource.zip` for `SM-A908N` / `A908NKSU5EWA3` with source upload id `13272` and announcement attach id `39494`; the source download is hCaptcha/manual-browser gated and the archive is not staged locally.
- interpretation: kernel instrumentation remains blocked until the official source archive is manually downloaded, staged under an ignored path, and verified for target QCACLD/CNSS files.
- next: V760 should verify the staged official archive/source tree and target file availability before any kernel instrumentation patch. Keep live device, boot-image writes, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping blocked.

### V760. Source Staging Verifier

- plan: `docs/plans/NATIVE_INIT_V760_SOURCE_STAGING_PLAN_2026-05-24.md`
- report: `docs/reports/NATIVE_INIT_V760_SOURCE_STAGING_2026-05-24.md`
- runner: `scripts/revalidation/native_wifi_source_staging_v760.py`
- evidence:
  - plan `tmp/wifi/v760-source-staging-plan/`
  - run `tmp/wifi/v760-source-staging/`
- decision: `v760-source-stage-missing`
- result: host-only verifier passed as a classifier. `kernel_build/` is now an explicit ignored staging area with a tracked README/.gitkeep, but the official source archive or extracted source tree is still absent. Target QCACLD/CNSS files are not verified.
- interpretation: the kernel instrumentation path is still blocked by external/manual source staging, not by repo tooling.
- next: manually download `SM-A908N_KOR_12_Opensource.zip`, stage it under `kernel_build/`, rerun V760, and only proceed to V761 kernel log instrumentation planning after target source files are verified. Keep live device, boot-image writes, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping blocked.

### V761. Source Download Handoff

- plan: `docs/plans/NATIVE_INIT_V761_SOURCE_DOWNLOAD_HANDOFF_PLAN_2026-05-24.md`
- report: `docs/reports/NATIVE_INIT_V761_SOURCE_DOWNLOAD_HANDOFF_2026-05-24.md`
- runner: `scripts/revalidation/native_wifi_source_handoff_v761.py`
- evidence:
  - plan `tmp/wifi/v761-source-download-handoff-plan/`
  - run `tmp/wifi/v761-source-download-handoff/`
- decision: `v761-source-download-handoff-ready`
- result: host-only handoff packet passed. It generated private `handoff.md` and `run-v761-source-download-handoff.sh`; the script opens the browser only with `V761_OPEN_BROWSER=1`, copies only an already downloaded official archive into ignored `kernel_build/`, and reruns V760.
- interpretation: the source blocker is reduced to one manual browser download plus rerun; no device or boot-image work is justified until V760 verifies target source files.
- next: execute the generated V761 handoff after downloading the official OSRC package, rerun V760, then proceed to kernel log instrumentation planning only after target files are verified. Keep live device, boot-image writes, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping blocked.

### V762. Source Target Verification

- plan: `docs/plans/NATIVE_INIT_V762_SOURCE_TARGET_VERIFICATION_PLAN_2026-05-24.md`
- report: `docs/reports/NATIVE_INIT_V762_SOURCE_TARGET_VERIFICATION_2026-05-24.md`
- runner: `scripts/revalidation/native_wifi_source_staging_v760.py`
- evidence:
  - run `tmp/wifi/v760-source-staging/`
- decision: `v760-source-targets-verified`
- result: host-only verifier passed after operator staging. `Kernel.tar.gz` inside `kernel_build/SM-A908N_KOR_12_Opensource/` exposes the live ICNSS/QCACLD target groups: `qcacld_hdd_main`, `qcacld_hdd_driver_ops`, `qcacld_pld_snoc`, `icnss_core`, and `icnss_qmi`. V760 was tightened to require those groups and accept Samsung's actual `drivers/net/wireless/qualcomm/wcn39xx/qcacld-3.0` path.
- interpretation: the source acquisition blocker is cleared for planning, and the instrumentation target must be ICNSS/QMI/WLFW service-69 plus PLD-SNOC callbacks rather than CNSS2/MHI. This does not authorize patching, building, flashing, or live Wi-Fi bring-up yet.
- next: V763 should rebase the architecture target to ICNSS/QCACLD before V764 plans minimal kernel log instrumentation. Keep source patching/building, boot-image writes, live device, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping blocked until their own gates.

### V763. ICNSS Architecture Rebase

- plan: `docs/plans/NATIVE_INIT_V763_ICNSS_ARCH_REBASE_PLAN_2026-05-24.md`
- report: `docs/reports/NATIVE_INIT_V763_ICNSS_ARCH_REBASE_2026-05-24.md`
- runner: host/source/evidence review
- evidence:
  - `tmp/wifi/v760-source-staging/`
  - `tmp/wifi/v711-icnss-edge-readonly-live/native/`
  - `tmp/wifi/v744-v122-cnss-only-comparison/native/cnss2-driver-ls-before.txt`
- decision: `v763-icnss-architecture-rebased`
- result: host-only correction passed. SM-A908N live path is ICNSS/QCACLD SNOC, not CNSS2/MHI. Source and evidence identify `drivers/soc/qcom/icnss_qmi.c`, `drivers/soc/qcom/icnss.c`, `pld_snoc.c`, and HDD files as the instrumentation targets.
- interpretation: the root edge to prove is WLFW service `69` -> `wlfw_new_server()` -> `icnss_call_driver_probe()` -> `pld_snoc_probe()` -> HDD startup. Service `180/74` remains side evidence, but V764 was redirected to retry the current service180-gated `mdm_helper` question before source instrumentation.
- next: V764 should classify V745-V749 evidence and rerun a bounded service180-gated `mdm_helper` proof with direct mdm/esoc surface capture. Keep source patching/building, boot-image writes, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping blocked until their own gates.

### V764. Service180-gated MDM Helper Retry

- plan: `docs/plans/NATIVE_INIT_V764_SERVICE180_MDM_HELPER_RETRY_PLAN_2026-05-24.md`
- report: `docs/reports/NATIVE_INIT_V764_SERVICE180_MDM_HELPER_RETRY_2026-05-24.md`
- runner: `scripts/revalidation/native_wifi_mdm_helper_service180_retry_v764.py`
- evidence:
  - V401 prerequisite: `tmp/wifi/v764-v401-toybox-selinuxfs-mount/`
  - live: `tmp/wifi/v764-mdm-helper-service180-retry/`
- decision: `v764-mdm-helper-started-no-lower-progress`
- result: bounded live proof passed. Current service-notifier `180` opened, helper v124 started `mdm_helper`, and cleanup left native healthy. `mss` reached `ONLINE`, but `mdm3` stayed `OFFLINING`; WLFW service `69`, MHI/QCA6390, BDF, and `wlan0` remained absent. No service-manager, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, esoc0 open/hold, subsystem write, bind/unbind, or boot image write was executed.
- access surface: `/sys/bus/esoc/devices/esoc0` and `/sys/class/subsys/subsys_esoc0` are visible with `SDX50M`/`PCIe` metadata, but `/dev/subsys_esoc0` is absent. Global native `/vendor/bin/mdm_helper` is not visible; it only starts inside the private vendor namespace helper path.
- interpretation: this closes the requested mdm_helper retry. `mdm_helper` is safe and startable under service180, but still insufficient as the lower trigger. Unless new evidence changes the service180/esoc model, do not repeat `mdm_helper` as the primary trigger.
- next: reconcile V764 with V749/V750 lower-window `boot_wlan` and the later HDD/PLD stall evidence. If that still cannot locate the gap, return to minimal ICNSS/QCACLD source log instrumentation as a separate V765+ gate.

### V765. ICNSS/QCACLD Log Patch Generator

- plan: `docs/plans/NATIVE_INIT_V765_ICNSS_QCACLD_LOG_PATCH_PLAN_2026-05-24.md`
- report: `docs/reports/NATIVE_INIT_V765_ICNSS_QCACLD_LOG_PATCH_2026-05-24.md`
- runner: `scripts/revalidation/native_wifi_icnss_qcacld_log_patch_v765.py`
- evidence:
  - `tmp/wifi/v765-icnss-qcacld-log-patch/manifest.json`
  - `tmp/wifi/v765-icnss-qcacld-log-patch/a90-v765-icnss-qcacld-log.patch`
- decision: `v765-icnss-qcacld-log-patch-ready`
- result: host-only patch generator passed. It generated a review-only unified diff with 19 `A90V765` log insertions across ICNSS QMI/core, PLD-SNOC, and QCACLD HDD loader/register/startup paths. It did not mutate `kernel_build`, build a kernel, write a boot image, or run any device command.
- interpretation: after V764 closed the `mdm_helper` retry path, the strongest next path is source-backed instrumentation. V765 provides the patch artifact needed to locate the HDD/PLD/register-driver stall, while keeping build/apply/flash as separate gates.
- next: V766 should apply the generated patch to a disposable source build tree and run build/package checks. Keep boot-image writes, live handoff, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping blocked until their own gates.

### V766. ICNSS/QCACLD Patch Apply Build-readiness

- plan: `docs/plans/NATIVE_INIT_V766_ICNSS_QCACLD_PATCH_APPLY_BUILD_PLAN_2026-05-25.md`
- report: `docs/reports/NATIVE_INIT_V766_ICNSS_QCACLD_PATCH_APPLY_BUILD_2026-05-25.md`
- runner: `scripts/revalidation/native_wifi_icnss_qcacld_patch_apply_build_v766.py`
- evidence:
  - `tmp/wifi/v766-icnss-qcacld-patch-apply-build/manifest.json`
  - `tmp/wifi/v766-icnss-qcacld-patch-apply-build/logs/patch-dry-run.txt`
  - `tmp/wifi/v766-icnss-qcacld-patch-apply-build/logs/patch-apply.txt`
  - `tmp/wifi/v766-icnss-qcacld-patch-apply-build/logs/defconfig.txt`
- decision: `v766-patch-applied-defconfig-pass-toolchain-incomplete`
- result: V766 corrected the V765 patch formatting issue, safely extracted the Samsung OSRC source to private evidence, applied the `A90V765` patch cleanly, verified 19 markers, and passed `r3q_kor_single_defconfig`. It did not mutate `kernel_build`, run a full kernel build, write a boot image, or run any device command.
- interpretation: instrumentation is now source-apply-ready and defconfig-ready. The next host blocker is not patch context; it is selecting/staging a compatible Android/Samsung toolchain for a bounded full kernel build/package check.
- next: V767 should select or stage toolchain inputs and run a bounded full kernel build/package readiness gate. Keep boot-image writes, live handoff, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping blocked until their own gates.

### V767. ICNSS/QCACLD Full Build Gate

- plan: `docs/plans/NATIVE_INIT_V767_ICNSS_QCACLD_FULL_BUILD_PLAN_2026-05-25.md`
- report: `docs/reports/NATIVE_INIT_V767_ICNSS_QCACLD_FULL_BUILD_2026-05-25.md`
- runner: `scripts/revalidation/native_wifi_icnss_qcacld_full_build_v767.py`
- evidence:
  - `tmp/wifi/v767-icnss-qcacld-full-build/manifest.json`
  - `tmp/wifi/v767-icnss-qcacld-full-build/logs/kernel-build.txt`
- decision: `v767-instrumented-objects-built-rkp-cfp-python2-blocked`
- result: V767 staged ignored Android/Samsung toolchain inputs, applied disposable host-build repairs, and ran a bounded full kernel build. The build compiled all five ICNSS/QCACLD instrumented target objects with all 19 `A90V765` markers preserved. Final `Image` packaging did not complete because Samsung post-link `scripts/rkp_cfp/instrument.py` is Python2-only and fails under the current host Python path.
- interpretation: the V765 patch is now source-apply, defconfig, and target-object compile proven. This does not explain why WLFW service `69` is absent at runtime; it only proves the planned printk instrumentation can compile up to the relevant object boundary.
- next: split the work into two gates. V768 should classify the mdm_helper/esoc/mdm3 gap without repeating blind Wi-Fi starts. A later packaging gate can decide whether to provide Python2, port/patch `RKP_CFP`, or intentionally bypass that post-link step for a diagnostic boot image. Keep boot-image writes, live handoff, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping blocked until their own gates.

### V768. MDM3/ESOC Gap Classifier

- plan: `docs/plans/NATIVE_INIT_V768_MDM3_ESOC_GAP_CLASSIFIER_PLAN_2026-05-25.md`
- report: `docs/reports/NATIVE_INIT_V768_MDM3_ESOC_GAP_CLASSIFIER_2026-05-25.md`
- runner: `scripts/revalidation/native_wifi_mdm3_esoc_gap_classifier_v768.py`
- evidence:
  - `tmp/wifi/v768-mdm3-esoc-gap-classifier/manifest.json`
  - `tmp/wifi/v768-mdm3-esoc-gap-classifier/summary.md`
- decision: `v768-mdm3-esoc-gap-rerouted-to-instrumentation-packaging`
- result: host-only classifier PASS. V764 already proves service180-gated `mdm_helper` starts with no mdm3/WLFW/BDF/`wlan0` progress. Direct esoc0 open/hold remains unavailable because `/dev/subsys_esoc0` is absent and no safe init-visible contract is proven. Blind lower-window `boot_wlan` retry remains rejected without new observability. V767 proves the ICNSS/QCACLD instrumentation objects compile.
- interpretation: the runtime `mdm_helper`/esoc direct retry branch is not the best next step. The nearest diagnostic path is to get the V767 instrumented kernel through final packaging so the missing HDD/PLD/ICNSS boundary can be observed on-device.
- next: V769 should solve the RKP_CFP/Python2 packaging blocker inside the disposable source tree, or explicitly classify a diagnostic-only RKP_CFP bypass. Keep boot-image handoff, flash, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping blocked until separate gates.

### V769. RKP_CFP Python3 Packaging Gate

- plan: `docs/plans/NATIVE_INIT_V769_RKP_CFP_PYTHON3_PACKAGING_PLAN_2026-05-25.md`
- report: `docs/reports/NATIVE_INIT_V769_RKP_CFP_PYTHON3_PACKAGING_2026-05-25.md`
- runner: `scripts/revalidation/native_wifi_rkp_cfp_packaging_v769.py`
- evidence:
  - `tmp/wifi/v769-rkp-cfp-python3-packaging/manifest.json`
  - `tmp/wifi/v769-rkp-cfp-python3-packaging/logs/kernel-build.txt`
  - `tmp/wifi/v769-rkp-cfp-python3-packaging/logs/rkp-cfp-py-compile.txt`
- decision: `v769-rkp-cfp-python3-repair-image-pass`
- result: bounded host packaging gate PASS. The runner applies idempotent Python3 compatibility repairs for Samsung `scripts/rkp_cfp`, compiles the repaired scripts, and reruns the V767 bounded build path. Final `Image` and `Image-dtb` are present in the disposable source tree; all five ICNSS/QCACLD instrumented objects still exist and preserve all 19 `A90V765` markers.
- safety: no boot image write, partition write, flash, reboot, device command, service-manager/Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, or external ping was executed.
- interpretation: the V767 final-image blocker was host `RKP_CFP` Python compatibility, not the Wi-Fi instrumentation patch. The instrumented kernel is now image-ready for a separate diagnostic boot-image staging gate.
- next: V770 should package/stage a diagnostic boot image from the V769 `Image` and existing boot artifacts without flashing. Live flash/reboot and Wi-Fi observation remain separate explicit gates.

### V770. Instrumented Diagnostic Boot Staging

- plan: `docs/plans/NATIVE_INIT_V770_INSTRUMENTED_DIAGNOSTIC_BOOT_STAGING_PLAN_2026-05-25.md`
- report: `docs/reports/NATIVE_INIT_V770_INSTRUMENTED_DIAGNOSTIC_BOOT_STAGING_2026-05-25.md`
- runner: `scripts/revalidation/native_wifi_diag_boot_staging_v770.py`
- evidence:
  - `tmp/wifi/v770-instrumented-diagnostic-boot-staging/manifest.json`
  - `tmp/wifi/v770-instrumented-diagnostic-boot-staging/boot_linux_v770_icnss_diag.img`
  - `tmp/wifi/v770-instrumented-diagnostic-boot-staging/logs/unpack-staged.txt`
- decision: `v770-instrumented-diagnostic-boot-staged`
- result: local-only staging PASS. The runner repacked V769 `Image-dtb` with the current verified v724 native-init ramdisk/header metadata. The staged image is 4096-byte aligned, mode `0600`, contains the native-init v724 marker and all 19 `A90V765` markers, and unpacks back to a kernel hash matching the V769 `Image-dtb`.
- safety: created a local tmp boot image only. No device command, partition write, flash, reboot, service-manager/Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, or external ping was executed.
- interpretation: the diagnostic boot artifact is ready for an explicitly gated live handoff. This still has not proven runtime Wi-Fi; it only prepares the observable kernel needed to classify the HDD/PLD/ICNSS stall on-device.
- next: V771 should flash the staged diagnostic image under rollback rules, boot native init, verify serial/bridge health, capture dmesg for `A90V765` markers around `boot_wlan`, and roll back if health fails. Wi-Fi scan/connect and credential use remain blocked until `wlan0`/wiphy exists.

### V771. Diagnostic Live Handoff Boot Failure

- report: `docs/reports/NATIVE_INIT_V771_DIAGNOSTIC_LIVE_HANDOFF_BOOT_FAIL_2026-05-25.md`
- recovery_report: `docs/reports/NATIVE_INIT_V771_ROLLBACK_RECOVERY_2026-05-25.md`
- evidence:
  - `tmp/wifi/v771-diagnostic-live-handoff-20260525-013724/native-init-flash.txt`
  - `tmp/wifi/v771-diagnostic-live-handoff-20260525-013724/abort-state.txt`
  - `tmp/wifi/v771-rollback-v724-20260525-014803/native-init-flash-rollback.txt`
  - `tmp/wifi/v771-rollback-v724-20260525-014803/post-rollback-verify.txt`
- decision: `v771-instrumented-kernel-boot-failed-download-mode`
- result: live handoff failed after a successful TWRP flash/readback. The V770 image was pushed to recovery, remote sha256 matched local, `dd` to `/dev/block/by-name/boot` completed, and boot partition prefix sha256 matched. After `twrp reboot`, native init did not verify and the phone enumerated as Samsung Download mode (`04e8:685d`) with no ADB device.
- interpretation: the failure is not an adb push, TWRP transfer, or boot partition write mismatch. The V769/V770 instrumented OSRC kernel image is not currently boot-compatible with the known-good native-init boot image. Do not retry the same V770 image as-is.
- recovery: completed. TWRP flashed `stage3/boot_linux_v724.img`, remote sha256 and boot prefix sha256 matched `4ca72f17aec64153d49def4ad42a49714d27bd833623aa9423220ce2181fc682`, and native verify passed with `version/status rc=0 status=ok`. Post-rollback `bootstatus` reports `BOOT OK shell 4.1s`; `selftest` reports `pass=11 warn=1 fail=0`.
- next: V772 should run a host-only boot incompatibility classifier before any further custom-kernel flash. Wi-Fi scan/connect and credential use remain blocked until `wlan0`/wiphy exists on a healthy native boot.

### V772. Boot Incompatibility Classifier

- plan: `docs/plans/NATIVE_INIT_V772_BOOT_INCOMPAT_CLASSIFIER_PLAN_2026-05-25.md`
- report: `docs/reports/NATIVE_INIT_V772_BOOT_INCOMPAT_CLASSIFIER_2026-05-25.md`
- runner: `scripts/revalidation/native_wifi_boot_incompat_classifier_v772.py`
- evidence:
  - `tmp/wifi/v772-boot-incompat-classifier/manifest.json`
  - `tmp/wifi/v772-boot-incompat-classifier/logs/base-ikconfig.txt`
  - `tmp/wifi/v772-boot-incompat-classifier/logs/diag-ikconfig.txt`
- decision: `v772-boot-fail-likely-missing-appended-dtb`
- result: host-only classifier PASS. The known-good v724 kernel payload has three appended FDT blobs at offsets `48830500`, `49327831`, and `49827440`; the V770 diagnostic payload has zero FDT magic hits. The stock DTB tail is `997113` bytes. Embedded kernel configs match, and the diagnostic payload still contains all 19 `A90V765` markers.
- interpretation: V771 likely failed because V770 packaged a bare OSRC-built/instrumented kernel payload without the appended device DTB tail required by this boot path. The write/readback was valid, but the kernel payload was structurally not boot-compatible. Do not retry V770 as-is.
- next: V773 should be local-only: append the stock v724 DTB tail to the V769 instrumented Image payload, repack, and verify FDT/marker/roundtrip checks before any live flash is considered.

### V773. Stock DTB Tail Repack

- plan: `docs/plans/NATIVE_INIT_V773_STOCK_DTB_TAIL_REPACK_PLAN_2026-05-25.md`
- report: `docs/reports/NATIVE_INIT_V773_STOCK_DTB_TAIL_REPACK_2026-05-25.md`
- runner: `scripts/revalidation/native_wifi_dtb_tail_repack_v773.py`
- evidence:
  - `tmp/wifi/v773-stock-dtb-tail-repack/manifest.json`
  - `tmp/wifi/v773-stock-dtb-tail-repack/instrumented-image-with-stock-dtb-tail.bin`
  - `tmp/wifi/v773-stock-dtb-tail-repack/boot_linux_v773_icnss_diag_stockdtb.img`
- decision: `v773-stock-dtb-tail-diagnostic-boot-staged`
- result: local-only repack PASS. The runner appended the stock v724 DTB tail to the V769 instrumented payload and repacked a private diagnostic boot image. The combined kernel has three FDT blobs at offsets `48830516`, `49327847`, and `49827456`, preserves all 19 `A90V765` markers, and roundtrips through `unpack_bootimg.py`. The staged boot image is 4096-byte aligned, mode `0600`, size `53972992`, sha256 `0fcde6e76fd0de3d2b974aad20dcbbba714e5a81b9fccf5ea2b6a67bdc06f400`.
- safety: no device command, partition write, flash, reboot, service-manager/Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, or external ping was executed.
- interpretation: V773 removes the missing-DTB-tail structural blocker found by V772, but live boot is still unproven. A future live gate must flash only this V773 artifact with rollback ready and immediate health checks.
- next: superseded by V774 live result. Wi-Fi scan/connect and credentials remain blocked until `wlan0`/wiphy exists.

### V774. Stock DTB Tail Live Boot Failure

- report: `docs/reports/NATIVE_INIT_V774_STOCK_DTB_TAIL_LIVE_BOOT_FAIL_2026-05-25.md`
- evidence:
  - `tmp/wifi/v774-stockdtb-live-handoff-20260525-015926/native-init-flash-v773.txt`
  - `tmp/wifi/v774-stockdtb-live-handoff-20260525-015926/abort-state.txt`
  - `tmp/wifi/v774-rollback-v724-20260525-020056/native-init-flash-rollback.txt`
- decision: `v774-stock-dtb-tail-kernel-boot-failed-recovery-mode`
- result: live handoff failed after a successful TWRP flash/readback of the V773 stock-DTB-tail image. The local image sha256 was `0fcde6e76fd0de3d2b974aad20dcbbba714e5a81b9fccf5ea2b6a67bdc06f400`; the remote pushed image matched; `dd` to `/dev/block/by-name/boot` completed; and the boot partition prefix sha256 matched. After `twrp reboot`, native init did not verify. The abort snapshot initially showed no ADB devices, and recovery/TWRP was subsequently available.
- recovery: completed. TWRP flashed `stage3/boot_linux_v724.img`, remote sha256 and boot prefix sha256 matched `4ca72f17aec64153d49def4ad42a49714d27bd833623aa9423220ce2181fc682`, and native verify passed with `version/status rc=0 status=ok`. Current native status reports `BOOT OK shell 4.2s`; `selftest` reports `pass=11 warn=1 fail=0`.
- interpretation: V773 eliminated the missing appended DTB tail as the sole V771 root cause, but the current Samsung OSRC-built instrumented kernel remains live-boot incompatible. V774 differs from V771 because the failure returned to or remained recoverable through TWRP/recovery instead of Download mode, but the same no-retry rule applies to the current custom-kernel artifacts.
- next: superseded by V775. Prefer stock-kernel runtime observability over further custom-kernel flash.

### V775. Boot Incompatibility Postmortem

- plan: `docs/plans/NATIVE_INIT_V775_BOOT_INCOMPAT_POSTMORTEM_PLAN_2026-05-25.md`
- report: `docs/reports/NATIVE_INIT_V775_BOOT_INCOMPAT_POSTMORTEM_2026-05-25.md`
- runner: `scripts/revalidation/native_wifi_boot_incompat_postmortem_v775.py`
- evidence:
  - `tmp/wifi/v775-boot-incompat-postmortem/manifest.json`
  - `tmp/wifi/v775-boot-incompat-postmortem/summary.md`
  - `tmp/wifi/v775-boot-incompat-postmortem/logs/unpack-base-boot.txt`
  - `tmp/wifi/v775-boot-incompat-postmortem/logs/unpack-diag-boot.txt`
- decision: `v775-non-dtb-custom-kernel-incompat-classified`
- result: host-only classifier PASS. The v724 stock and V773 diagnostic boot header args match after normalized unpack, and both kernel payloads contain three appended FDT blobs. The remaining differences are non-DTB: V773 diagnostic kernel size is `49827629` vs stock `49827613`, every appended FDT offset is shifted by `16` bytes, kernel provenance/toolchain strings differ, and coarse RKP/RTIC marker counts differ.
- observability: config surface confirms `CONFIG_KPROBES=n`, `CONFIG_DYNAMIC_DEBUG=n`, `CONFIG_FUNCTION_TRACER=n`, `CONFIG_FTRACE=y`, `CONFIG_TRACEPOINTS=y`, `CONFIG_BPF_SYSCALL=y`, and `CONFIG_BPF_EVENTS=y`.
- interpretation: missing appended DTB tail is no longer the sole cause. The custom OSRC kernel flash route is paused until a separate host-only compatibility gate explains the remaining production/provenance/pre-DTB delta. Repeating V770, V773, or equivalent OSRC-built images is blocked.
- next: superseded by V776. No custom kernel flash.

### V776. Tracepoint Inventory

- plan: `docs/plans/NATIVE_INIT_V776_TRACEPOINT_INVENTORY_PLAN_2026-05-25.md`
- report: `docs/reports/NATIVE_INIT_V776_TRACEPOINT_INVENTORY_2026-05-25.md`
- runner: `scripts/revalidation/native_wifi_tracepoint_inventory_v776.py`
- evidence:
  - `tmp/wifi/v776-tracepoint-inventory/manifest.json`
  - `tmp/wifi/v776-tracepoint-inventory/summary.md`
  - `tmp/wifi/v776-tracepoint-inventory/native/available-events-head.txt`
  - `tmp/wifi/v776-tracepoint-inventory/native/candidate-*.txt`
- decision: `v776-tracepoint-candidates-found`
- result: live stock-v724 bounded tracefs inventory PASS. V776 temporarily mounted tracefs, read event surfaces, and unmounted cleanly. `available_events` is readable with `1250` events. Candidate counts: ICNSS/WLAN/Wi-Fi `1`, QMI/QRTR/service `1`, subsystem/remoteproc `3`, network stack `39`, scheduler/workqueue/IRQ `109`, total `153`.
- focused candidates: `cfg80211:cfg80211_report_wowlan_wakeup`, `dfc:dfc_qmi_tc`, and `msm_pil_event:{pil_event,pil_notif,pil_func}`. Network and scheduler events are broad context rather than primary Wi-Fi bring-up evidence.
- safety: BPF attach, ftrace control writes, Wi-Fi action, scan/connect, credential use, DHCP/routes, external ping, reboot, flash, and partition write were all not executed. Postflight tracefs status confirms no tracefs mount remains.
- interpretation: stock kernel static tracepoints are viable enough for a next observer gate, but not yet enough for BPF attach. V777 should inspect selected tracepoint `format` files and field semantics before any attach proof. Custom OSRC kernel flashing remains paused.
- next: superseded by V777.

### V777. Tracepoint Format Classifier

- plan: `docs/plans/NATIVE_INIT_V777_TRACEPOINT_FORMAT_CLASSIFIER_PLAN_2026-05-25.md`
- report: `docs/reports/NATIVE_INIT_V777_TRACEPOINT_FORMAT_CLASSIFIER_2026-05-25.md`
- runner: `scripts/revalidation/native_wifi_tracepoint_format_classifier_v777.py`
- evidence:
  - `tmp/wifi/v777-tracepoint-format-classifier/manifest.json`
  - `tmp/wifi/v777-tracepoint-format-classifier/summary.md`
  - `tmp/wifi/v777-tracepoint-format-classifier/native/format-*.txt`
- decision: `v777-tracepoint-format-fields-classified`
- result: live stock-v724 bounded format read PASS. All 5 selected tracepoints have readable `format` files and event-specific fields. `msm_pil_event:pil_event` exposes `event_name,fw_name`; `msm_pil_event:pil_notif` exposes `event_name,code,fw_name`; `msm_pil_event:pil_func` exposes `func_name`; `dfc:dfc_qmi_tc` exposes `dev_name,txq,enable`; `cfg80211:cfg80211_report_wowlan_wakeup` exposes wiphy/wakeup fields.
- safety: BPF attach, ftrace control writes, Wi-Fi action, scan/connect, credential use, DHCP/routes, external ping, reboot, flash, and partition write were all not executed. Tracefs was unmounted after the read window.
- interpretation: `msm_pil_event:pil_notif` is the best V778 target because it is modem/PIL-adjacent and exposes event name, code, and firmware name without requiring Wi-Fi HAL or network actions. `cfg80211` is likely post-wiphy and not useful for the current pre-`wlan0` blocker.
- next: superseded by V778. No modem/Wi-Fi trigger, scan/connect, credential use, or custom kernel flash.

### V778. BPF Attach Feasibility

- plan: `docs/plans/NATIVE_INIT_V778_BPF_ATTACH_FEASIBILITY_PLAN_2026-05-25.md`
- report: `docs/reports/NATIVE_INIT_V778_BPF_ATTACH_FEASIBILITY_2026-05-25.md`
- runner: `scripts/revalidation/native_wifi_bpf_attach_feasibility_v778.py`
- evidence:
  - `tmp/wifi/v778-bpf-attach-feasibility/manifest.json`
  - `tmp/wifi/v778-bpf-attach-feasibility/summary.md`
  - `tmp/wifi/v778-bpf-attach-feasibility/native/bpf-loader-surface.txt`
- decision: `v778-custom-bpf-loader-build-needed`
- result: live feasibility classifier PASS. `msm_pil_event:pil_notif` remains the selected target with `event_name,code,fw_name`, but no `bpftool` or `bpftrace` exists on the device. Device sysctls: `perf_event_paranoid=3`, `unprivileged_bpf_disabled=0`. `/sys/kernel/tracing` exists and `/sys/kernel/debug/tracing` is absent.
- host surface: `aarch64-linux-gnu-gcc`, `aarch64-linux-gnu-strip`, and `aarch64-linux-gnu-readelf` are present, and BPF/perf headers are available. Host can build a minimal static aarch64 C helper.
- safety: BPF attach, ftrace control writes, Wi-Fi action, scan/connect, credential use, DHCP/routes, external ping, reboot, flash, and partition write were all not executed.
- interpretation: V778 cannot proceed directly to attach because there is no existing loader. V779 should be build-only: create and statically build a minimal reviewed helper for one target, then audit it before any deploy or attach proof.
- next: superseded by V779.

### V779. BPF Loader Build

- plan: `docs/plans/NATIVE_INIT_V779_BPF_LOADER_BUILD_PLAN_2026-05-25.md`
- report: `docs/reports/NATIVE_INIT_V779_BPF_LOADER_BUILD_2026-05-25.md`
- runner: `scripts/revalidation/native_wifi_bpf_loader_build_v779.py`
- source: `stage3/linux_init/helpers/a90_bpf_trace_probe.c`
- evidence:
  - `tmp/wifi/v779-bpf-loader-build/manifest.json`
  - `tmp/wifi/v779-bpf-loader-build/summary.md`
  - `tmp/wifi/v779-bpf-loader-build/a90_bpf_trace_probe-aarch64-static`
  - `tmp/wifi/v779-bpf-loader-build/logs/readelf-program.txt`
- decision: `v779-bpf-loader-build-pass`
- result: host build-only PASS. The minimal helper compiles with `aarch64-linux-gnu-gcc -static`, strips successfully, has no `INTERP` program header, preserves marker `a90_bpf_trace_probe v779`, and includes explicit `--check-only` and `--allow-attach` gates. Artifact size is `597920` bytes; sha256 is `9d8fdfeaa9281ba814db62ddc588b37959021d68fbd08164ae366dde3f08b1c3`.
- helper contract: default run is check-only and no attach. Attach path is present but gated by `--allow-attach`, targets only `msm_pil_event:pil_notif`, reads the tracepoint id from tracefs, loads a minimal two-instruction tracepoint BPF program, attaches through `perf_event_open`, waits briefly, disables, and closes fds.
- safety: no device command, deploy, BPF attach, ftrace control write, Wi-Fi action, scan/connect, credential use, DHCP/routes, external ping, reboot, flash, or partition write was executed.
- next: V780 should deploy the helper and run only `--check-only` on device, verifying remote hash/version/default no-attach behavior. BPF attach remains blocked until a later separate gate.

### V780. BPF Loader Deploy Check-Only

- plan: `docs/plans/NATIVE_INIT_V780_BPF_LOADER_DEPLOY_CHECKONLY_PLAN_2026-05-25.md`
- report: `docs/reports/NATIVE_INIT_V780_BPF_LOADER_DEPLOY_CHECKONLY_2026-05-25.md`
- runner: `scripts/revalidation/native_wifi_bpf_loader_deploy_checkonly_v780.py`
- evidence:
  - `tmp/wifi/v780-bpf-loader-deploy-checkonly/manifest.json`
  - `tmp/wifi/v780-bpf-loader-deploy-checkonly/summary.md`
  - `tmp/wifi/v780-bpf-loader-deploy-checkonly/native/sha-helper.txt`
  - `tmp/wifi/v780-bpf-loader-deploy-checkonly/native/helper-check-only.txt`
  - `tmp/wifi/v780-bpf-loader-deploy-checkonly/native/helper-default.txt`
- decision: `v780-bpf-loader-deploy-checkonly-pass`
- result: serial deploy to `/cache/bin/a90_bpf_trace_probe` PASS. Remote sha256 matched `9d8fdfeaa9281ba814db62ddc588b37959021d68fbd08164ae366dde3f08b1c3`. `--check-only` and default no-argument modes both printed marker `a90_bpf_trace_probe v779`, `result=check-only`, and `attach_attempted=0`.
- hard gates: no `--allow-attach`, BPF attach, ftrace control write, Wi-Fi action, scan/connect, credential use, DHCP/routes/external ping, reboot/flash/partition write was executed.
- next: V781 may be planned as a separate bounded idle attach/detach proof for `msm_pil_event:pil_notif`.

### V781. BPF Idle Attach Classifier

- plan: `docs/plans/NATIVE_INIT_V781_BPF_IDLE_ATTACH_PLAN_2026-05-25.md`
- report: `docs/reports/NATIVE_INIT_V781_BPF_IDLE_ATTACH_2026-05-25.md`
- runner: `scripts/revalidation/native_wifi_bpf_idle_attach_v781.py`
- evidence:
  - `tmp/wifi/v781-bpf-idle-attach/manifest.json`
  - `tmp/wifi/v781-bpf-idle-attach/summary.md`
  - `tmp/wifi/v781-bpf-idle-attach/native/helper-allow-attach.txt`
  - `tmp/wifi/v781-bpf-idle-attach/native/status-after.txt`
- decision: `v781-bpf-idle-attach-detach-pass`
- result: BPF tracepoint attach/detach PASS on stock v724. Tracepoint `msm_pil_event:pil_notif` id was `595`; helper returned `bpf_prog_fd=3`, `result=attach-detach-pass`, `attach_attempted=1`. Tracefs cleanup passed and status after remained `BOOT OK`.
- hard gates: no modem/WLAN trigger, Wi-Fi HAL/service-manager, scan/connect, credential use, DHCP/routes/external ping, module load/unload, sysfs bind/unbind, reboot/flash/partition write was executed.
- next: V782 can use the BPF observer around one bounded modem/WLAN state transition, still without Wi-Fi scan/connect or external networking.

### V782. BPF Counter Boot WLAN Observer

- plan: `docs/plans/NATIVE_INIT_V782_BPF_COUNTER_BOOT_WLAN_PLAN_2026-05-25.md`
- report: `docs/reports/NATIVE_INIT_V782_BPF_COUNTER_BOOT_WLAN_2026-05-25.md`
- runner: `scripts/revalidation/native_wifi_bpf_counter_boot_wlan_v782.py`
- helper source: `stage3/linux_init/helpers/a90_bpf_trace_counter.c`
- evidence:
  - `tmp/wifi/v782-bpf-counter-boot-wlan/manifest.json`
  - `tmp/wifi/v782-bpf-counter-boot-wlan/summary.md`
  - `tmp/wifi/v782-bpf-counter-boot-wlan/native/bpf-counter-collect.txt`
  - `tmp/wifi/v782-bpf-counter-boot-wlan/native/boot-wlan-observe.txt`
  - `tmp/wifi/v782-bpf-counter-boot-wlan/native/dmesg-delta.txt`
- decision: `v782-bpf-counter-boot-wlan-counted-control-surface-only`
- result: BPF counter captured `event_count=8` on `msm_pil_event:pil_notif` during the lower-window transition. `mss` reached `ONLINE`, QRTR RX/TX and `sysmon-qmi` appeared, and `boot_wlan` executed, but `mdm3` stayed `OFFLINING`; service `69/74/180`, WLFW/BDF, wiphy, and `wlan0` remained absent.
- hard gates: no Wi-Fi HAL/service-manager, scan/connect, credential use, DHCP/routes/external ping, `qcwlanstate ON`, module load/unload, sysfs bind/unbind, `esoc0`, boot image write, or partition write was executed.
- next: V783 should classify Android vs native PIL notification names/codes or related mdm3/WLAN-PD trigger evidence before any further live trigger.

### V783. Android/Native PIL Gap Classifier

- plan: `docs/plans/NATIVE_INIT_V783_ANDROID_NATIVE_PIL_GAP_PLAN_2026-05-25.md`
- report: `docs/reports/NATIVE_INIT_V783_ANDROID_NATIVE_PIL_GAP_2026-05-25.md`
- runner: `scripts/revalidation/native_wifi_android_native_pil_gap_v783.py`
- evidence:
  - `tmp/wifi/v783-android-native-pil-gap/manifest.json`
  - `tmp/wifi/v783-android-native-pil-gap/summary.md`
- decision: `v783-mdm3-wlan-pd-gap-memshare-lead-classified`
- result: host-only PASS. Android reference reaches service-notifier `74/180`, WLAN-PD indication, ICNSS-QMI, BDF, firmware-ready, and `wlan0`; native V782 reaches `mss ONLINE`, QRTR RX/TX, modem `sysmon-qmi`, service-locator, and HDD control-surface creation but lacks service-notifier `74/180` and everything downstream. Native V782 also shows memshare/CMA allocation failures at the sysmon window.
- hard gates: no device command, reboot, boot image or partition write, Wi-Fi HAL/service-manager, scan/connect, credential use, DHCP/routes/external ping, `qcwlanstate ON`, module load/unload, bind/unbind, or `esoc0` access was executed.
- next: V784 should be read-only and target memshare/CMA/reserved-memory plus matching Android/native dmesg recapture before any further live trigger.

### V784. Native Memshare/CMA Surface

- plan: `docs/plans/NATIVE_INIT_V784_MEMSHARE_CMA_SURFACE_PLAN_2026-05-25.md`
- report: `docs/reports/NATIVE_INIT_V784_MEMSHARE_CMA_SURFACE_2026-05-25.md`
- runner: `scripts/revalidation/native_wifi_memshare_cma_surface_v784.py`
- evidence:
  - `tmp/wifi/v784-memshare-cma-surface/manifest.json`
  - `tmp/wifi/v784-memshare-cma-surface/summary.md`
  - `tmp/wifi/v784-memshare-cma-surface/native/memshare-cma-surface.txt`
- decision: `v784-native-memshare-cma-surface-classified`
- result: live read-only PASS on v724. Native exposes memshare sysfs, `client_4`, CMA, and reserved-memory nodes including `linux,cma`, `pil_wlan_fw_region`, and `mhi_region`. V782 failure sizes were confirmed as `100663296` and `33554432` bytes, while current idle `CmaFree` was `243380224` bytes, larger than the V782 request sum.
- hard gates: no boot image or partition write, reboot, mount/unmount, bind/unbind, `driver_override`, module load/unload, `boot_wlan`, `qcwlanstate ON`, service-manager/Wi-Fi HAL, scan/connect, credential use, DHCP/routes, or external ping was executed.
- next: V785 should recapture Android and native dmesg with explicit memshare/CMA filters and map `client_4` / client id `3` registration before any further WLAN trigger.

### V785. Android/Native Memshare Delta

- plan: `docs/plans/NATIVE_INIT_V785_ANDROID_NATIVE_MEMSHARE_DELTA_PLAN_2026-05-25.md`
- report: `docs/reports/NATIVE_INIT_V785_ANDROID_NATIVE_MEMSHARE_DELTA_2026-05-25.md`
- runner: `scripts/revalidation/native_wifi_android_native_memshare_delta_v785.py`
- evidence:
  - `tmp/wifi/v785-android-native-memshare-delta/manifest.json`
  - `tmp/wifi/v785-android-native-memshare-delta/summary.md`
- decision: `v785-memshare-common-nonfatal-sibling-sysmon-gap`
- result: host-only PASS. Android V611 and native V782 both show identical memshare request sizes `100663296` and `33554432`, identical failed sizes, and the same `8192`-page CMA `-12` failure. Android proceeds to sibling sysmon, service-notifier `180/74`, WLAN-PD, ICNSS-QMI, BDF, firmware-ready, and `wlan0`; native first divergence is `sysmon_slpi`, with sibling sysmon absent and `mdm3=OFFLINING`.
- hard gates: no device command, Android handoff, boot image or partition write, reboot, Wi-Fi HAL/service-manager, scan/connect, credential use, DHCP/routes, external ping, `boot_wlan`, `qcwlanstate ON`, module load/unload, bind/unbind, or `esoc0` access was executed.
- next: V786 should target mdm3/esoc0 `ONLINE` and sibling sysmon/service-notifier prerequisites, not another memshare-only or blind `boot_wlan` retry.

### V786. Clean-DSP/v724 Gap Classifier

- plan: `docs/plans/NATIVE_INIT_V786_CLEAN_DSP_V724_GAP_PLAN_2026-05-25.md`
- report: `docs/reports/NATIVE_INIT_V786_CLEAN_DSP_V724_GAP_2026-05-25.md`
- runner: `scripts/revalidation/native_wifi_clean_dsp_v724_gap_v786.py`
- evidence:
  - `tmp/wifi/v786-clean-dsp-v724-gap/manifest.json`
  - `tmp/wifi/v786-clean-dsp-v724-gap/summary.md`
- decision: `v786-v724-clean-dsp-hook-available-but-unarmed`
- result: host-only PASS. Current v724 source and `stage3/boot_linux_v724.img` already contain the V641 firmware-backed sibling SSCTL one-shot hook and markers. V782 did not arm or execute that hook: V641 runtime markers, sibling sysmon, and service-notifier counts are all `0`.
- interpretation: V785's missing sibling-sysmon gap does not require a custom OSRC kernel retry or rebuild yet. It routes to an explicit stock-v724 arm-only clean-DSP proof.
- hard gates: no device command, reboot, boot image or partition write, custom kernel flash, Wi-Fi HAL/service-manager, scan/connect, credential use, DHCP/routes, external ping, `boot_wlan`, `qcwlanstate`, `esoc0`, bind/unbind, or module load/unload was executed.
- next: V787 should arm only `/cache/native-init-sibling-fwssctl-v641` on stock v724, reboot, collect V641 proof/timeline/dmesg/rpmsg evidence, and stop. Do not arm the v724 QRTR flag, CNSS/HAL, scan/connect, or custom-kernel flash in the same gate.

### V787. Clean-DSP Arm-Only Live Proof

- plan: `docs/plans/NATIVE_INIT_V787_CLEAN_DSP_ARM_ONLY_PLAN_2026-05-25.md`
- report: `docs/reports/NATIVE_INIT_V787_CLEAN_DSP_ARM_ONLY_2026-05-25.md`
- runner: `scripts/revalidation/native_wifi_clean_dsp_arm_only_v787.py`
- evidence:
  - `tmp/wifi/v787-clean-dsp-arm-only/manifest.json`
  - `tmp/wifi/v787-clean-dsp-arm-only/summary.md`
  - `tmp/wifi/v787-clean-dsp-arm-only/native/post-timeline.txt`
  - `tmp/wifi/v787-clean-dsp-arm-only/native/post-dmesg-markers.txt`
- decision: `v787-clean-dsp-arm-only-proof-pass`
- result: live stock-v724 PASS. V641 one-shot arm and reboot succeeded; timeline reached `complete failures=0 timeouts=0`; ADSP/CDSP/SLPI each returned `status=0x0` and produced PIL reset/power-clock markers. No `pm_qos`/reference/esoc warning boundary appeared. Firmware mountpoints were unmounted and post-cleanup status stayed healthy.
- interpretation: clean-DSP prerequisite is restored on current v724, but arm-only still does not produce sibling `sysmon-qmi`, service-notifier, WLFW/BDF, or `wlan0`. This matches historical V641 and keeps scan/connect premature.
- hard gates: no boot image or partition write, custom kernel flash, v724 QRTR flag, `boot_wlan`, `qcwlanstate`, CNSS/HAL/service-manager, scan/connect, credential use, DHCP/routes, or external ping was executed.
- next: V788 should be a separate clean-DSP plus lower companion readback gate. It should arm V641, reboot, then run only the lower companion observer/readback; still no HAL, scan/connect, credentials, DHCP/routes, external ping, or custom-kernel flash.

### V788. Clean-DSP Lower Readback

- plan: `docs/plans/NATIVE_INIT_V788_CLEAN_DSP_LOWER_READBACK_PLAN_2026-05-25.md`
- report: `docs/reports/NATIVE_INIT_V788_CLEAN_DSP_LOWER_READBACK_2026-05-25.md`
- runner: `scripts/revalidation/native_wifi_clean_dsp_lower_readback_v788.py`
- evidence:
  - `tmp/wifi/v788-clean-dsp-lower-readback/manifest.json`
  - `tmp/wifi/v788-clean-dsp-lower-readback/summary.md`
  - `tmp/wifi/v788-clean-dsp-lower-readback/native/dmesg-delta.txt`
  - `tmp/wifi/v788-clean-dsp-lower-readback/lower-companion-summary.json`
- decision: `v788-clean-dsp-lower-readback-blocked`
- result: live stock-v724 BLOCKED. Inline clean-DSP proof passed, V401 SELinuxfs mount passed, V490 policy load passed, firmware mounts and `subsys_modem` holder opened, and CNSS-only lower companion observed all six children. `mss` reached `ONLINE`, while `mdm3` stayed `OFFLINING`. QRTR RX/TX, `sysmon-qmi`, and service-notifier markers appeared, but QRTR services `69/74/180`, MHI/QCA6390, WLFW/BDF, wiphy, and `wlan0` remained absent.
- blocker: dmesg delta produced a new `pm_qos_add_request() called for already added request` warning through `msm_asoc_machine_probe` in deferred probe work after ADSP/APR/audio service activity. Historical V733/V735 and V787 had `kernel_warning=0` for this boundary.
- hard gates: no service-manager, Wi-Fi HAL, scan/connect, credential use, DHCP/routes, external ping, boot image or partition write, or custom kernel flash was executed. Cleanup reboot returned to healthy v724.
- next: V789 should be host-only first. Classify whether the V788 warning is caused by clean-DSP plus lower companion composition, CNSS-only addition, service-notifier/audio deferred probe ordering, or current V401/V490 runtime state before any live retry.

### V789. V788 Warning Classifier

- plan: `docs/plans/NATIVE_INIT_V789_V788_WARNING_CLASSIFIER_PLAN_2026-05-25.md`
- report: `docs/reports/NATIVE_INIT_V789_V788_WARNING_CLASSIFIER_2026-05-25.md`
- runner: `scripts/revalidation/native_wifi_v788_warning_classifier_v789.py`
- evidence:
  - `tmp/wifi/v789-v788-warning-classifier/manifest.json`
  - `tmp/wifi/v789-v788-warning-classifier/summary.md`
  - `tmp/wifi/v789-v788-warning-classifier/warning-context.txt`
- decision: `v789-pm-qos-audio-deferred-probe-boundary-classified`
- result: host-only PASS. V788 is the only compared run with the `pm_qos_add_request` warning boundary: V788 `kernel_warning=5`, V733 `0`, V735 `0`, V787 `0`. V788 warning context occurs after service-notifier `180/74`, ADSP/APR audio activity, and duplicate `msm_asoc_machine_probe`; the call trace goes through `msm_asoc_machine_probe` and `deferred_probe_work_func`. WLFW/BDF/wiphy/`wlan0` remain absent.
- hard gates: no device command, reboot, mount/unmount, daemon start, Wi-Fi HAL, scan/connect, credential use, DHCP/routes, external ping, boot image/partition write, or custom kernel flash was executed.
- next: V790 should be narrower than V788: clean-DSP plus current V401/V490 prep plus lower-only companion readback, omitting `cnss_diag` and `cnss-daemon`. If warning-free, CNSS-only can be reintroduced later with a narrower guard; if it warns, classify clean-DSP/lower/audio ordering before repeating CNSS.

### V790. Clean-DSP Lower-Only Warning Isolation

- plan: `docs/plans/NATIVE_INIT_V790_CLEAN_DSP_LOWER_ONLY_PLAN_2026-05-25.md`
- report: `docs/reports/NATIVE_INIT_V790_CLEAN_DSP_LOWER_ONLY_2026-05-25.md`
- runner: `scripts/revalidation/native_wifi_clean_dsp_lower_only_v790.py`
- evidence:
  - `tmp/wifi/v790-clean-dsp-lower-only/manifest.json`
  - `tmp/wifi/v790-clean-dsp-lower-only/summary.md`
  - `tmp/wifi/v790-clean-dsp-lower-only/native/dmesg-delta.txt`
  - `tmp/wifi/v790-clean-dsp-lower-only/lower-only-summary.json`
- decision: `v790-clean-dsp-lower-only-blocked`
- result: live stock-v724 BLOCKED. Inline clean-DSP, V401, V490, firmware mounts, and `subsys_modem` holder passed. Lower-only companion order `qrtr-ns,rmt_storage,tftp_server,pd-mapper` ran with no `cnss_diag` or `cnss-daemon`. `mss` reached `ONLINE`, `mdm3` stayed `OFFLINING`, QRTR RX/TX, `sysmon-qmi`, and service-notifier markers appeared, but MHI/QCA6390/WLFW/BDF/wiphy/`wlan0` stayed absent.
- blocker: the same `pm_qos_add_request() called for already added request` warning recurred through duplicate `msm_asoc_machine_probe` in deferred probe work after service-notifier `180/74` and ADSP/APR audio activity. This proves CNSS-only userspace is not required for the warning.
- hard gates: no `cnss_diag`, `cnss-daemon`, service-manager, Wi-Fi HAL, scan/connect, credential use, DHCP/routes, external ping, boot image or partition write, or custom kernel flash was executed. Cleanup reboot returned to healthy v724.
- next: V791 should be host-only first. Compare V790, V788, V787, and historical V733 to choose whether the next safe live isolation omits V401/V490, omits clean-DSP, or only reads lower service surfaces without spawning lower daemons.

### V840. Provider-first Prearmed Listener

- plan: `docs/plans/NATIVE_INIT_V840_PROVIDER_FIRST_PREARMED_LISTENER_PLAN_2026-05-25.md`
- report: `docs/reports/NATIVE_INIT_V840_PROVIDER_FIRST_PREARMED_LISTENER_2026-05-25.md`
- runner: `scripts/revalidation/native_wifi_provider_first_prearmed_listener_v840.py`
- evidence:
  - `tmp/wifi/v840-provider-first-prearmed-listener-live/manifest.json`
  - `tmp/wifi/v840-provider-first-prearmed-listener-live/summary.md`
  - `tmp/wifi/v840-provider-first-prearmed-listener-live/provider-first-prearmed-summary.json`
- decision: `v840-provider-first-prearmed-no-indication`
- result: live stock-v724 PASS. Helper v130 exposed both provider-first and
  listener-only modes. Clean-DSP, V401, V490, firmware mounts, `subsys_modem`
  holder, V700 provider-first service-manager/PeripheralManager path, and one
  fresh CNSS retry all ran. The listener registered about `1309ms` before
  service `74`, stayed open about `13705ms` after service `74`, and still
  reported WLAN-PD `UNINIT` with no indication.
- hard gates: no Wi-Fi HAL, wificond, supplicant, hostapd, scan/connect,
  credentials, DHCP/routes, external ping, `esoc0`, subsystem state writes,
  `wlan.ko` load/unload, boot image writes, partition writes, or custom kernel
  flash was executed.
- next: V841 should classify the missing lower native WLAN-PD state-up trigger.
  Native has service `74/180`, provider-first service-manager/PeripheralManager,
  and CNSS retry, but still lacks WLAN-PD `UP`, WLFW/BDF, and `wlan0`.

### V843. Current-Window CNSS Stall Classifier

- plan: `docs/plans/NATIVE_INIT_V843_CURRENT_WINDOW_CNSS_STALL_CLASSIFIER_PLAN_2026-05-25.md`
- report: `docs/reports/NATIVE_INIT_V843_CURRENT_WINDOW_CNSS_STALL_CLASSIFIER_2026-05-25.md`
- runner: `scripts/revalidation/native_wifi_current_window_cnss_stall_classifier_v843.py`
- evidence:
  - `tmp/wifi/v843-current-window-cnss-stall-classifier/manifest.json`
  - `tmp/wifi/v843-current-window-cnss-stall-classifier/summary.md`
- decision: `v843-cnss-retry-poll-futex-prewlfw-event-gap`
- result: host-only PASS. V843 parsed the V840 cleanup-time stall snapshot and
  confirmed the retry `cnss-daemon` process is alive in `do_sys_poll` with
  worker threads in `do_sys_poll`/`futex_wait_queue_me`. The CNSS user socket,
  netlink entry, socket fd surface, and vndbinder fd are present, while
  `wlfw_start`, WLAN-PD, BDF, FW-ready, and `wlan0` remain absent.
- hard gates: no device command, daemon start, service-manager, Wi-Fi HAL,
  scan/connect, credential use, DHCP/routes, external ping, boot image or
  partition write, custom kernel flash, `esoc0`, subsystem write, or module
  load/unload was executed.
- next: V844 should classify the missing source-backed ICNSS/WLFW event
  publication prerequisite before any HAL, scan/connect, DHCP/routes,
  credential, external ping, or boot-image work.

### V844. mdm3/ext-sdx50m Boot Interface Classifier

- plan: `docs/plans/NATIVE_INIT_V844_MDM3_EXT_SDX50M_BOOT_INTERFACE_CLASSIFIER_PLAN_2026-05-25.md`
- report: `docs/reports/NATIVE_INIT_V844_MDM3_EXT_SDX50M_BOOT_INTERFACE_CLASSIFIER_2026-05-25.md`
- runner: `scripts/revalidation/native_wifi_mdm3_ext_sdx50m_boot_interface_classifier_v844.py`
- evidence:
  - `tmp/wifi/v844-mdm3-ext-sdx50m-boot-interface-classifier/manifest.json`
  - `tmp/wifi/v844-mdm3-ext-sdx50m-boot-interface-classifier/summary.md`
- decision: `v844-mdm3-ext-sdx50m-boot-interface-selected`
- result: host-only PASS. Samsung OSRC DTS identifies `qcom,mdm3` as
  `qcom,ext-sdx50m` with AP/MDM GPIO handshake, `qcom,ssctl-instance-id=<0x10>`,
  and `qcom,sysmon-id=<0x14>`. ICNSS source shows service-notifier UP is not
  the initial boot trigger and WLFW depends on QRTR service 69 arrival through
  `wlfw_new_server()`. Existing native evidence has `mss=ONLINE`,
  `mdm3=OFFLINING`, SSCTL 43/16 clean-empty, and no WLFW/BDF/FW-ready/`wlan0`.
- hard gates: no device command, QRTR/QMI payload, raw `esoc0` open, GPIO/sysfs
  write, daemon start, service-manager, Wi-Fi HAL, scan/connect, credential
  use, DHCP/routes, external ping, boot image write, partition write, or custom
  kernel flash was executed.
- next: V845 should capture a read-only live mdm3/ext-sdx50m eSoC GPIO/sysfs
  surface snapshot before any raw `esoc0` open, GPIO/sysfs write, HAL/connect,
  or boot-image work.

### V845. mdm3/ext-sdx50m Surface Snapshot

- plan: `docs/plans/NATIVE_INIT_V845_MDM3_EXT_SDX50M_SURFACE_SNAPSHOT_PLAN_2026-05-25.md`
- report: `docs/reports/NATIVE_INIT_V845_MDM3_EXT_SDX50M_SURFACE_SNAPSHOT_2026-05-25.md`
- runner: `scripts/revalidation/native_wifi_mdm3_ext_sdx50m_surface_snapshot_v845.py`
- evidence:
  - `tmp/wifi/v845-mdm3-ext-sdx50m-surface-snapshot/manifest.json`
  - `tmp/wifi/v845-mdm3-ext-sdx50m-surface-snapshot/summary.md`
- decision: `v845-mdm3-ext-sdx50m-surface-captured`
- result: live stock-v724 read-only PASS. Pre/post health stayed `BOOT OK`
  with selftest `fail=0`. mdm3/eSoC sysfs, `subsys_esoc0`, live devicetree
  `qcom,ext-sdx50m`, and AP/MDM GPIO properties are present; `mdm3` is
  `OFFLINING`; raw `/dev/esoc*` and `/dev/subsys*` nodes are absent;
  `/sys/kernel/debug/gpio` is not readable; GPIO 135/142 are not exported.
  Existing readable+writable candidates include `esoc_link`, `esoc_link_info`,
  `esoc_name`, `subsys9/state`, and `subsys0/state`.
- hard gates: no raw `esoc0` open, GPIO/sysfs/debugfs write, subsystem state
  write, bind/unbind, module load/unload, daemon start, service-manager, Wi-Fi
  HAL, scan/connect, credential use, DHCP/routes, external ping, boot image
  write, partition write, or custom kernel flash was executed.
- next: V846 should classify the source-backed mdm3/eSoC state-control contract
  before any bounded write or GPIO action.

### V846. mdm3/eSoC State-Control Contract

- plan: `docs/plans/NATIVE_INIT_V846_MDM3_ESOC_STATE_CONTROL_CONTRACT_PLAN_2026-05-25.md`
- report: `docs/reports/NATIVE_INIT_V846_MDM3_ESOC_STATE_CONTROL_CONTRACT_2026-05-25.md`
- runner: `scripts/revalidation/native_wifi_mdm3_esoc_state_control_contract_v846.py`
- evidence:
  - `tmp/wifi/v846-mdm3-esoc-state-control-contract/manifest.json`
  - `tmp/wifi/v846-mdm3-esoc-state-control-contract/summary.md`
- decision: `v846-mdm3-esoc-char-open-contract-selected`
- result: host-only PASS. OSRC rejects direct subsystem `state` write because
  `state` is `DEVICE_ATTR_RO(state)`. `subsys_device_open()` calls
  `subsystem_get_with_fwname()` and reaches `subsys_start()`, while close calls
  `subsystem_put()` and can reach `subsys_stop()`. V845 provides
  `subsys_esoc0` uevent major `236`, minor `9`, devname `subsys_esoc0`, but no
  `/dev/subsys_esoc0` node. MHI/eSoC hooks are present downstream; raw
  `/dev/esoc*`, opaque `esoc_link` writes, HAL/connect, and MHI `power_up` are
  not selected as the immediate next gate.
- hard gates: no device command, `mknod`, char-device open, sysfs/GPIO write,
  daemon start, service-manager, Wi-Fi HAL, scan/connect, credential use,
  DHCP/routes, external ping, boot image write, partition write, or custom
  kernel flash was executed.
- next: V847 should run one bounded live `subsys_esoc0` char-device
  materialize/open/hold smoke with watchdog, dmesg/state evidence, cleanup
  reboot, and postflight health checks.

### V847. subsys_esoc0 Char-Device Open Smoke

- plan: `docs/plans/NATIVE_INIT_V847_SUBSYS_ESOC0_CHAR_OPEN_SMOKE_PLAN_2026-05-25.md`
- report: `docs/reports/NATIVE_INIT_V847_SUBSYS_ESOC0_CHAR_OPEN_SMOKE_2026-05-25.md`
- runner: `scripts/revalidation/native_wifi_subsys_esoc0_char_open_smoke_v847.py`
- evidence:
  - `tmp/wifi/v847-subsys-esoc0-char-open-smoke/manifest.json`
  - `tmp/wifi/v847-subsys-esoc0-char-open-smoke/summary.md`
  - `tmp/wifi/v847-subsys-esoc0-char-open-smoke/native/dmesg-after-observe.txt`
- decision: `v847-subsys-esoc0-open-blocked-or-pending`
- result: live stock-v724 bounded PASS. V847 created `/dev/subsys_esoc0`
  from V845 uevent major `236`, minor `9`, started one background holder, and
  reboot-cleaned successfully. The open reached kernel dmesg
  `__subsystem_get: esoc0 count:0` and `Changing subsys fw_name to esoc0`, but
  no `holder.opened=1` status appeared within the observation window. mdm3
  remained `OFFLINING`; MHI/PCIe, WLFW/BDF/FW-ready/`wlan0`, warning, panic,
  and fatal markers stayed absent in the focused output.
- hard gates: no raw `/dev/esoc*` open/ioctl, sysfs/GPIO/debugfs write,
  bind/unbind, module load/unload, daemon start, service-manager, Wi-Fi HAL,
  scan/connect, credential use, DHCP/routes, external ping, boot image write,
  partition write, or custom kernel flash was executed.
- next: V848 should classify the `subsys_esoc0` open-block boundary below
  `subsystem_get()` and before MHI/WLFW, using V847 evidence and OSRC source.

### V848. subsys_esoc0 Open-Block Classifier

- plan: `docs/plans/NATIVE_INIT_V848_SUBSYS_ESOC0_OPEN_BLOCK_CLASSIFIER_PLAN_2026-05-25.md`
- report: `docs/reports/NATIVE_INIT_V848_SUBSYS_ESOC0_OPEN_BLOCK_CLASSIFIER_2026-05-25.md`
- runner: `scripts/revalidation/native_wifi_subsys_esoc0_open_block_classifier_v848.py`
- evidence:
  - `tmp/wifi/v848-subsys-esoc0-open-block-classifier/manifest.json`
  - `tmp/wifi/v848-subsys-esoc0-open-block-classifier/summary.md`
- decision: `v848-subsys-esoc0-open-block-boundary-classified`
- result: host-only PASS. V847's holder reached
  `__subsystem_get(esoc0)` and `Changing subsys fw_name to esoc0`, but open
  did not complete, mdm3/subsys9 stayed `OFFLINING`, and MHI/PCIe,
  WLFW/BDF/FW-ready/`wlan0` markers stayed absent. OSRC maps the remaining
  branch to either provider `powerup()` or `wait_for_err_ready()`. Defconfig
  enables ESOC/ESOC_DEV/ESOC_CLIENT/ESOC_MDM_4x/ESOC_MDM_DRV, but the staged
  OSRC tree lacks the eSoC MDM provider source, so source-only attribution is
  insufficient.
- hard gates: no device command, `mknod`, char-device open, raw `/dev/esoc*`
  open/ioctl, sysfs/GPIO/debugfs write, bind/unbind, module load/unload,
  daemon start, service-manager, Wi-Fi HAL, scan/connect, credential use,
  DHCP/routes, external ping, boot image write, partition write, or custom
  kernel flash was executed.
- next: V849 should run one bounded live `subsys_esoc0` char-open wait-state
  sampler with holder process tree, `/proc/<pid>/wchan`, `/proc/<pid>/stack`
  if readable, `/proc/<pid>/status`, `/proc/<pid>/syscall`, read-only
  `/sys/module` eSoC/module surface, mdm3 state, focused dmesg, node removal,
  cleanup reboot, and postflight health checks.

### V849. subsys_esoc0 Wait-State Sampler

- plan: `docs/plans/NATIVE_INIT_V849_SUBSYS_ESOC0_WAIT_STATE_SAMPLER_PLAN_2026-05-25.md`
- report: `docs/reports/NATIVE_INIT_V849_SUBSYS_ESOC0_WAIT_STATE_SAMPLER_2026-05-25.md`
- runner: `scripts/revalidation/native_wifi_subsys_esoc0_wait_state_sampler_v849.py`
- evidence:
  - `tmp/wifi/v849-subsys-esoc0-wait-state-sampler/manifest.json`
  - `tmp/wifi/v849-subsys-esoc0-wait-state-sampler/summary.md`
  - `tmp/wifi/v849-subsys-esoc0-wait-state-sampler/native/sample-after-start.txt`
- decision: `v849-subsys-esoc0-block-provider-powerup-or-opaque`
- result: live stock-v724 bounded PASS. V849 created `/dev/subsys_esoc0`,
  started one holder, captured in-window `/proc` wait-state evidence, removed
  the node, and reboot-cleaned successfully. The holder did not complete open;
  its `wchan` was `mdm_subsys_powerup`, task state was `D (disk sleep)`, and
  stack showed `mdm_subsys_powerup -> __subsystem_get -> subsys_device_open`.
  `wait_for_err_ready`, MHI/WLFW/BDF/FW-ready/`wlan0` progress stayed absent,
  and mdm3/subsys9 remained `OFFLINING`.
- hard gates: no raw `/dev/esoc*` open/ioctl, GPIO/sysfs/debugfs write,
  bind/unbind, module load/unload, daemon start, service-manager, Wi-Fi HAL,
  scan/connect, credential use, DHCP/routes, external ping, boot image write,
  partition write, or custom kernel flash was executed.
- next: V850 should classify the proprietary ext-mdm provider surface around
  `mdm_subsys_powerup` using V849 evidence, current read-only sysfs/module
  surfaces, available symbols, and Android reference behavior before any GPIO,
  raw eSoC ioctl, MHI write, HAL/connect, DHCP/routes, external ping, or
  boot-image work.

### V850. ext-mdm Powerup Surface Classifier

- plan: `docs/plans/NATIVE_INIT_V850_EXT_MDM_POWERUP_SURFACE_CLASSIFIER_PLAN_2026-05-25.md`
- report: `docs/reports/NATIVE_INIT_V850_EXT_MDM_POWERUP_SURFACE_CLASSIFIER_2026-05-25.md`
- runner: `scripts/revalidation/native_wifi_ext_mdm_powerup_surface_classifier_v850.py`
- evidence:
  - `tmp/wifi/v850-ext-mdm-powerup-surface-classifier/manifest.json`
  - `tmp/wifi/v850-ext-mdm-powerup-surface-classifier/summary.md`
- decision: `v850-ext-mdm-powerup-surface-selected`
- result: host-only PASS. V850 correlates V849's `mdm_subsys_powerup`
  D-state stack with Android V591 mdm3/WLAN-PD positive reference and the
  Samsung DTS `qcom,ext-sdx50m` GPIO/IRQ contract. The blocker is provider
  `powerup()` level, not `wait_for_err_ready`, MHI, HAL, or credentials.
  Defconfig enables ESOC MDM support, but the staged OSRC tree lacks the
  provider source. V849 dmesg also preserves `MDM_PMIC_PWR_STATUS` and
  `AP2MDM_ERRFATAL2` provider hints.
- hard gates: no device command, node creation, char open, raw `/dev/esoc*`
  open/ioctl, GPIO/sysfs/debugfs write, bind/unbind, module load/unload,
  daemon start, service-manager, Wi-Fi HAL, scan/connect, credential use,
  DHCP/routes, external ping, boot image write, partition write, or custom
  kernel flash was executed.
- next: V851 should run a live read-only ext-mdm provider surface snapshot:
  filtered `/proc/kallsyms`, `/proc/interrupts`, platform driver/sysfs/of_node
  power state, eSoC sysfs, msm_subsys state, readable GPIO/debug/pinctrl if
  available, and focused dmesg. No raw eSoC open, GPIO/sysfs write, MHI write,
  HAL/connect, DHCP/routes, external ping, or boot-image work.

### V851. ext-mdm Provider Surface Snapshot

- plan: `docs/plans/NATIVE_INIT_V851_EXT_MDM_PROVIDER_SURFACE_SNAPSHOT_PLAN_2026-05-25.md`
- report: `docs/reports/NATIVE_INIT_V851_EXT_MDM_PROVIDER_SURFACE_SNAPSHOT_2026-05-25.md`
- runner: `scripts/revalidation/native_wifi_ext_mdm_provider_surface_snapshot_v851.py`
- overview:
  - `docs/overview/MDM3_ESOC_SDX50M_BRINGUP_RESEARCH_2026-05-25.md`
- evidence:
  - `tmp/wifi/v851-ext-mdm-provider-surface-snapshot/manifest.json`
  - `tmp/wifi/v851-ext-mdm-provider-surface-snapshot/summary.md`
- decision: `v851-ext-mdm-provider-surface-limited`
- result: live stock-v724 read-only PASS. Pre/post health stayed `BOOT OK`
  with selftest `fail=0`. mdm3 remains `OFFLINING`. Idle `/proc/kallsyms`
  exposes `__subsystem_get`, `subsys_device_open`,
  `mhi_arch_esoc_ops_power_on`, and `mhi_pci_probe`, but does not expose
  `mdm_subsys_powerup`; V849 stack evidence remains the authoritative proof for
  that blocked symbol. mdm3/eSoC/sysfs and live devicetree AP2MDM/MDM2AP status
  properties are present, but GPIO debug is unreadable, pinctrl debug is not
  present/readable, raw `/dev/esoc*` remains absent, and MHI/WLFW/BDF/`wlan0`
  progress is still absent.
- hard gates: no raw `/dev/esoc*` or `/dev/subsys*` open/ioctl,
  GPIO/sysfs/debugfs write, GPIO export, subsystem state write, bind/unbind,
  driver override, module load/unload, daemon start, service-manager, Wi-Fi
  HAL, scan/connect, credential use, DHCP/routes, external ping, boot image
  write, partition write, or custom kernel flash was executed.
- next: V852 should capture the same ext-mdm provider surface from Android as
  a matched positive-control snapshot. Compare mdm3 state, AP2MDM/MDM2AP IRQ
  counts, PMIC/pinctrl visibility, GPIO/debug exposure, and MHI/WLFW/BDF/`wlan0`
  deltas before any GPIO/eSoC write or upper Wi-Fi action.

### V852. Android ext-mdm Provider Surface Handoff

- plan: `docs/plans/NATIVE_INIT_V852_ANDROID_EXT_MDM_PROVIDER_SURFACE_HANDOFF_PLAN_2026-05-25.md`
- report: `docs/reports/NATIVE_INIT_V852_ANDROID_EXT_MDM_PROVIDER_SURFACE_HANDOFF_2026-05-25.md`
- handoff runner: `scripts/revalidation/android_ext_mdm_provider_surface_handoff_v852.py`
- Android collector:
  `scripts/revalidation/native_wifi_android_ext_mdm_provider_surface_sample_v852.py`
- evidence:
  - `tmp/wifi/v852-android-ext-mdm-provider-surface-handoff/manifest.json`
  - `tmp/wifi/v852-android-ext-mdm-provider-surface-handoff/summary.md`
  - `tmp/wifi/v852-android-ext-mdm-provider-surface-handoff/v852-android-ext-mdm-provider-surface-run/manifest.json`
  - `tmp/wifi/v852-android-ext-mdm-provider-surface-handoff/v852-android-ext-mdm-provider-surface-run/summary.md`
- decision: `v852-android-mdm3-online-provider-surface-captured`
- result: bounded Android handoff PASS with native v724 rollback verified.
  Android positive-control captured mdm3 `ONLINE`, mss `ONLINE`, readable
  GPIO/pinctrl debug, real `/dev/esoc-0` and `/dev/subsys_esoc0` nodes, MHI
  IRQs, WLAN-PD indication, BDF downloads for `regdb.bin`/`bdwlan.bin`, and
  `wlan0` dmesg markers. Native V851 still has mdm3 `OFFLINING`, no raw eSoC
  node, no debug GPIO/pinctrl visibility, and no MHI/WLFW/BDF/`wlan0`.
- hard gates: Android collector did not enable Wi-Fi, scan/connect, use
  credentials, run DHCP, change routes, ping externally, write provider
  sysfs/debugfs, export/write GPIOs, load/unload modules, or start services
  directly. Handoff temporarily wrote boot only to enter Android and restored
  native v724.
- next: V853 should classify the Android actor/device-node path for mdm3/eSoC:
  process FDs for `/dev/esoc-0` and `/dev/subsys_esoc0`, SELinux domains,
  ueventd/init rules, and service ordering. Do this before any native raw eSoC
  ioctl, GPIO write, subsystem write, HAL start, scan/connect, DHCP/routes,
  external ping, or boot-image change.

### V853. Android eSoC Actor Handoff

- plan: `docs/plans/NATIVE_INIT_V853_ANDROID_ESOC_ACTOR_HANDOFF_PLAN_2026-05-25.md`
- report: `docs/reports/NATIVE_INIT_V853_ANDROID_ESOC_ACTOR_HANDOFF_2026-05-25.md`
- handoff runner: `scripts/revalidation/android_esoc_actor_handoff_v853.py`
- Android collector:
  `scripts/revalidation/native_wifi_android_esoc_actor_sample_v853.py`
- evidence:
  - `tmp/wifi/v853-android-esoc-actor-handoff/manifest.json`
  - `tmp/wifi/v853-android-esoc-actor-handoff/summary.md`
  - `tmp/wifi/v853-android-esoc-actor-handoff/v853-android-esoc-actor-run/manifest.json`
  - `tmp/wifi/v853-android-esoc-actor-handoff/v853-android-esoc-actor-run/summary.md`
- decision: `v853-android-esoc-actor-surface-captured`
- result: bounded Android handoff PASS with native v724 rollback verified.
  Android actor sampling captured real `/dev/esoc-0`, `/dev/subsys_esoc0`,
  `/dev/subsys_modem`, and `/dev/wlan` nodes. `/dev/esoc-0` is held by
  `mdm_helper` and child `ks` in `u:r:vendor_mdm_helper:s0`; `/dev/subsys_esoc0`
  and `/dev/subsys_modem` are held by `pm-service` in `u:r:vendor_per_mgr:s0`.
  ueventd rules set `/dev/esoc-0` to `0660 root:radio` and `/dev/subsys_*` to
  `0640 system:system`; SELinux labels are `vendor_esoc_device` and
  `vendor_ssr_device`.
- hard gates: Android collector did not directly open/ioctl eSoC/subsys nodes,
  enable Wi-Fi, scan/connect, use credentials, run DHCP, change routes, ping
  externally, write provider sysfs/debugfs, export/write GPIOs, load/unload
  modules, or start services directly. Handoff temporarily wrote boot only to
  enter Android and restored native v724.
- next: V854 should host-only classify the smallest safe native equivalent of
  the Android actor contract: device-node/ueventd parity, `pm-service`
  PeripheralManager start-only, `mdm_helper` `/dev/esoc-0` contract, or init
  ordering replay. Do this before any native raw eSoC ioctl, GPIO/sysfs write,
  subsystem state write, HAL start, scan/connect, DHCP/routes, external ping,
  or boot-image change.

### V854. eSoC Actor Parity Classifier

- plan: `docs/plans/NATIVE_INIT_V854_ESOC_ACTOR_PARITY_CLASSIFIER_PLAN_2026-05-25.md`
- report: `docs/reports/NATIVE_INIT_V854_ESOC_ACTOR_PARITY_CLASSIFIER_2026-05-25.md`
- runner: `scripts/revalidation/native_wifi_esoc_actor_parity_classifier_v854.py`
- evidence:
  - `tmp/wifi/v854-esoc-actor-parity-classifier/manifest.json`
  - `tmp/wifi/v854-esoc-actor-parity-classifier/summary.md`
- decision: `v854-esoc-actor-parity-selects-node-contract-preflight`
- result: host-only PASS. V854 reconciled V853 Android actor evidence with V849
  `mdm_subsys_powerup` block, V840 provider-first no-indication, and V764
  `mdm_helper` no-progress results. It rejects blind repeats of manual
  `/dev/subsys_esoc0` open, `mdm_helper` alone, and provider-first
  PeripheralManager without node parity. It keeps GPIO/sysfs/debugfs writes and
  raw eSoC ioctl forbidden for now.
- hard gates: no bridge, ADB, QRTR socket, device command, node creation/open,
  service start, GPIO/sysfs/debugfs write, subsystem state write, module
  load/unload, boot/partition write, Wi-Fi HAL, scan/connect, credential use,
  DHCP/routes, or external ping was executed.
- next: V855 should implement native Android eSoC/subsys node parity preflight:
  compute and optionally materialize `/dev/esoc-0`, `/dev/subsys_esoc0`, and
  `/dev/subsys_modem` with Android-equivalent major/minor/mode/owner, verify
  vendor path prerequisites, clean up, and verify native health. Do not
  open/ioctl nodes or start `pm-service`, `mdm_helper`, `ks`, Wi-Fi HAL,
  scan/connect, DHCP/routes, external ping, GPIO/sysfs/debugfs writes,
  subsystem state writes, module load/unload, or boot-image changes.

### V855. eSoC Node Parity Preflight

- plan: `docs/plans/NATIVE_INIT_V855_ESOC_NODE_PARITY_PREFLIGHT_PLAN_2026-05-25.md`
- report: `docs/reports/NATIVE_INIT_V855_ESOC_NODE_PARITY_PREFLIGHT_2026-05-25.md`
- runner: `scripts/revalidation/native_wifi_esoc_node_parity_preflight_v855.py`
- evidence:
  - `tmp/wifi/v855-esoc-node-parity-preflight/manifest.json`
  - `tmp/wifi/v855-esoc-node-parity-preflight/summary.md`
- decision: `v855-esoc-node-parity-clean`
- result: bounded native live PASS. V855 confirmed native exposes `subsys`
  major `236`, `esoc` major `484`, `subsys_esoc0` dev `236:9`,
  `subsys_modem` dev `236:0`, and eSoC metadata `mdm-4x` / `qcom,ext-sdx50m`
  / `PCIe` / `SDX50M`. It materialized `/dev/esoc-0`, `/dev/subsys_esoc0`,
  and `/dev/subsys_modem` with Android-equivalent mode/owner/major/minor,
  confirmed `holder_found=0`, removed all created nodes, and postflight stayed
  `BOOT OK` with selftest `fail=0`.
- hard gates: no eSoC/subsys node open/ioctl, actor service start, `pm-service`,
  `mdm_helper`, `ks`, CNSS retry, Wi-Fi HAL, scan/connect, credential use,
  DHCP/routes, external ping, GPIO/sysfs/debugfs write, subsystem state write,
  module load/unload, boot image write, or partition write was executed.
- next: V856 should run `pm-service` start-only with Android node parity
  present. It should capture whether `pm-service` holds `/dev/subsys_esoc0` and
  `/dev/subsys_modem`, then terminate/cleanup and verify native health. Do not
  start `mdm_helper`, `ks`, Wi-Fi HAL, scan/connect, DHCP/routes, external
  ping, raw eSoC ioctl, GPIO/sysfs/debugfs writes, subsystem state writes,
  module load/unload, or boot-image changes.

### V856. pm-service Node Parity Start-Only

- plan: `docs/plans/NATIVE_INIT_V856_PM_SERVICE_NODE_PARITY_START_ONLY_PLAN_2026-05-25.md`
- report: `docs/reports/NATIVE_INIT_V856_PM_SERVICE_NODE_PARITY_START_ONLY_2026-05-25.md`
- runner: `scripts/revalidation/native_wifi_pm_service_node_parity_start_only_v856.py`
- deploy wrapper: `scripts/revalidation/wifi_execns_helper_v131_deploy_preflight.py`
- helper: `a90_android_execns_probe v131`
- evidence:
  - `tmp/wifi/v856-pm-service-node-parity-start-only-r5/manifest.json`
  - `tmp/wifi/v856-pm-service-node-parity-start-only-r5/summary.md`
- decision: `v856-pm-service-observable-without-subsys-hold`
- result: bounded native live PASS. V856 prepared `mountsystem ro`, V401
  SELinuxfs, helper v131, service-manager trio, private property root, and
  V855-equivalent node parity. It started only `pm-service`/`pm-proxy`, captured
  both actors, and cleaned up created nodes with postflight `BOOT OK` and
  selftest `fail=0`.
- finding: native `pm-service` did not prove fd holds on `/dev/subsys_esoc0` or
  `/dev/subsys_modem`, unlike Android V853. The clearest runtime delta is the
  property shim: `vendor.peripheral.SDX50M.state=OFFLINE` and
  `vendor.peripheral.modem.state=OFFLINE` were accepted, while
  `vendor.peripheral.shutdown_critical_list` updates for `SDX50M ` and
  `SDX50M modem ` were denied.
- hard gates: no `mdm_helper`, `ks`, CNSS retry, Wi-Fi HAL, scan/connect,
  credential use, DHCP/routes, external ping, raw eSoC ioctl,
  GPIO/sysfs/debugfs write, subsystem state write, module load/unload,
  boot-image write, or Android partition write was executed.
- next: V857 should replay only the narrow PeripheralManager property contract,
  permitting exactly the observed `vendor.peripheral.shutdown_critical_list`
  values under the same no-`mdm_helper`/no-Wi-Fi guardrails. If subsystem fd
  holds appear, then V858 can plan `mdm_helper`/`ks` contract replay; otherwise
  continue classifying missing init property/context/service inputs.

### V857. pm-service Property Contract Start-Only

- plan: `docs/plans/NATIVE_INIT_V857_PM_SERVICE_PROPERTY_CONTRACT_PLAN_2026-05-25.md`
- report: `docs/reports/NATIVE_INIT_V857_PM_SERVICE_PROPERTY_CONTRACT_2026-05-25.md`
- runner: `scripts/revalidation/native_wifi_pm_service_property_contract_start_only_v857.py`
- deploy wrapper: `scripts/revalidation/wifi_execns_helper_v132_deploy_preflight.py`
- helper: `a90_android_execns_probe v132`
- evidence:
  - `tmp/wifi/v857-pm-service-property-contract-start-only/manifest.json`
  - `tmp/wifi/v857-pm-service-property-contract-start-only/summary.md`
- decision: `v857-pm-property-contract-no-subsys-hold`
- result: bounded native live PASS. V857 replayed the two observed
  `vendor.peripheral.shutdown_critical_list` values and both property requests
  returned success. The run still avoided `mdm_helper`, `ks`, CNSS retry, Wi-Fi
  HAL, scan/connect, credential use, DHCP/routes, external ping, raw eSoC
  ioctl, GPIO/sysfs/debugfs write, subsystem state write, module load/unload,
  boot-image write, and Android partition write.
- finding: allowing the shutdown-critical-list contract did not make native
  `pm-service` hold `/dev/subsys_esoc0` or `/dev/subsys_modem`. Newly exposed
  stderr gaps are service-specific property context/read keys:
  `debug.ld.app.pm-service`, `arm64.memtag.process.pm-service`,
  `persist.log.tag.PerMgrSrv`, `log.tag.PerMgrSrv`, and corresponding
  `pm-proxy` keys.
- next: V858 should classify Android/native property-info context deltas for
  those `pm-service`/`pm-proxy` lookup keys, then prove the smallest safe
  property input overlay. Do not escalate to `mdm_helper`/`ks` until
  PeripheralManager either holds the subsystem nodes or the remaining
  property/context gap is closed and shown irrelevant.

### V858. pm-service Property Context Delta

- plan: `docs/plans/NATIVE_INIT_V858_PM_SERVICE_PROPERTY_CONTEXT_DELTA_PLAN_2026-05-25.md`
- report: `docs/reports/NATIVE_INIT_V858_PM_SERVICE_PROPERTY_CONTEXT_DELTA_2026-05-25.md`
- classifier: `scripts/revalidation/native_property_runtime_pm_service_v858.py`
- deployer: `scripts/revalidation/native_property_runtime_incremental_v858.py`
- evidence:
  - `tmp/wifi/v858-pm-service-private-property-runtime/manifest.json`
  - `tmp/wifi/v858-pm-service-property-incremental-live/manifest.json`
- decision: `v858-pm-service-property-incremental-deploy-pass`
- result: V858 mapped all eight V857 `pm-service`/`pm-proxy` residual property
  keys to Android property contexts, generated a private property layout with
  zero roundtrip failures, then deployed selected files into the private V535
  property root with device-side hash verification.
- hard gates: no daemon start, no `mdm_helper`/`ks`, no Wi-Fi HAL,
  scan/connect, credentials, DHCP/routes, external ping, global property root
  replacement, raw eSoC ioctl, GPIO/sysfs/debugfs/subsystem write,
  module load/unload, boot image write, or partition write.
- next: V859 should rerun only the bounded `pm-service`/`pm-proxy` start-only
  path against the updated private root, without helper redeploy.

### V859. pm-service Property Delta Replay

- plan: `docs/plans/NATIVE_INIT_V859_PM_SERVICE_PROPERTY_DELTA_REPLAY_PLAN_2026-05-25.md`
- report: `docs/reports/NATIVE_INIT_V859_PM_SERVICE_PROPERTY_DELTA_REPLAY_2026-05-25.md`
- runner: `scripts/revalidation/native_wifi_pm_service_property_delta_replay_v859.py`
- evidence:
  - `tmp/wifi/v859-pm-service-property-delta-replay-r2/manifest.json`
  - `tmp/wifi/v859-pm-service-property-delta-replay-r2/summary.md`
- decision: `v859-v858-target-denials-removed-new-property-gap`
- result: bounded native live PASS. V859 reused helper v132 without redeploy,
  materialized and cleaned up Android-equivalent eSoC/subsys nodes, and proved
  `v858_target_remaining=[]`. The previous `pm-service`/`pm-proxy` denial set
  is gone, but `pm-service` still does not hold `/dev/subsys_esoc0` or
  `/dev/subsys_modem`.
- new blocker: property denials moved to `vndservicemanager`, `ServiceManager`,
  and `PerMgrLib` keys. This indicates the next useful step is another private
  property superset delta, not `mdm_helper`/`ks` replay yet.
- hard gates: no helper deployment, no `mdm_helper`/`ks`, no Wi-Fi HAL,
  scan/connect, credentials, DHCP/routes, external ping, raw eSoC ioctl,
  GPIO/sysfs/debugfs/subsystem write, module load/unload, boot image write, or
  partition write.
- next: V860 should extend the private property layout for the new
  `vndservicemanager`/`ServiceManager`/`PerMgrLib` keys and rerun the same
  bounded replay before any actor escalation.

### V860. pm-service Property Superset Delta

- plan: `docs/plans/NATIVE_INIT_V860_PM_SERVICE_PROPERTY_SUPERSET_PLAN_2026-05-25.md`
- report: `docs/reports/NATIVE_INIT_V860_PM_SERVICE_PROPERTY_SUPERSET_2026-05-25.md`
- classifier: `scripts/revalidation/native_property_runtime_pm_service_v860.py`
- deployer: `scripts/revalidation/native_property_runtime_incremental_v860.py`
- runner: `scripts/revalidation/native_wifi_pm_service_property_superset_replay_v860.py`
- evidence:
  - `tmp/wifi/v860-pm-service-property-superset-runtime/manifest.json`
  - `tmp/wifi/v860-pm-service-property-superset-incremental-live/manifest.json`
  - `tmp/wifi/v860-pm-service-property-superset-replay-live/manifest.json`
- decision: `v860-property-clean-no-subsys-hold`
- result: bounded native live PASS. V860 generated a single private property
  superset from V858, V859, and V677 evidence, deployed selected files into the
  versioned private V535 property root, and reran the same `pm-service`/
  `pm-proxy` start-only path. Property denials dropped to zero
  (`total=0`, `unique=0`, `v860_target_remaining=[]`), but `pm-service` still
  did not hold `/dev/subsys_esoc0` or `/dev/subsys_modem`.
- hard gates: no helper deployment, no `mdm_helper`/`ks`, no Wi-Fi HAL,
  scan/connect, credentials, DHCP/routes, external ping, raw eSoC ioctl,
  GPIO/sysfs/debugfs/subsystem write, module load/unload, boot image write, or
  partition write.
- next: V861 should classify the post-property-clean `pm-service` lifetime and
  provider-input gap. Focus on child exit status, stdout/stderr, provider
  registration, and fd timing versus Android V853 before actor escalation.

### V861. pm-service Domain Parity

- plan: `docs/plans/NATIVE_INIT_V861_PM_SERVICE_DOMAIN_PARITY_PLAN_2026-05-25.md`
- report: `docs/reports/NATIVE_INIT_V861_PM_SERVICE_DOMAIN_PARITY_2026-05-25.md`
- helper source: `stage3/linux_init/helpers/a90_android_execns_probe.c`
- deploy wrapper: `scripts/revalidation/wifi_execns_helper_v133_deploy_preflight.py`
- runner: `scripts/revalidation/native_wifi_pm_service_domain_parity_v861.py`
- evidence:
  - `tmp/wifi/v861-pm-service-domain-parity-plan-r2/manifest.json`
  - `tmp/wifi/v861-pm-service-domain-parity-live-r2/manifest.json`
- decision: `v861-exec-target-accepted-current-kernel-no-subsys-hold`
- result: bounded native live PASS. Helper v133 mapped `/vendor/bin/pm-service`
  and `/vendor/bin/pm-proxy` to `u:r:vendor_per_mgr:s0`; the exec target was
  accepted and property denials stayed zero. Runtime `attr/current` still read
  `kernel`, `pm-service` exited `0`, `pm-proxy` exited `1`, and no subsystem fd
  hold appeared.
- hard gates: no `mdm_helper`/`ks`, no Wi-Fi HAL, scan/connect, credentials,
  DHCP/routes, external ping, raw eSoC ioctl, GPIO/sysfs/debugfs/subsystem
  write, module load/unload, boot image write, or partition write.
- next: V862 should classify Android init service contract differences for
  `vendor.per_mgr`, `vendor.per_proxy`, and `vendor.per_proxy_helper` before
  actor escalation.

### V862. Android Init Service Contract Classifier

- plan: `docs/plans/NATIVE_INIT_V862_ANDROID_INIT_SERVICE_CONTRACT_PLAN_2026-05-25.md`
- report: `docs/reports/NATIVE_INIT_V862_ANDROID_INIT_SERVICE_CONTRACT_2026-05-25.md`
- classifier: `scripts/revalidation/native_wifi_android_init_service_contract_v862.py`
- evidence:
  - `tmp/wifi/v862-android-init-service-contract/manifest.json`
- decision: `v862-init-contract-classified-pm-proxy-helper-content-needed`
- result: host-only PASS. V862 parsed the V210 vendor init capture, V210
  inventory, V853 Android actor dmesg, V861 native replay, and helper source.
  Android `vendor.per_mgr` is `/vendor/bin/pm-service` with `class core`,
  `user system`, `group system`, and `ioprio rt 4`; `vendor.per_proxy` is
  `/vendor/bin/pm-proxy`, disabled, and started by
  `init.svc.vendor.per_mgr=running`. V210 lists `pm_proxy_helper.rc`, and V853
  proves Android starts `vendor.per_proxy_helper`, but that rc content was not
  captured. V861 still leaves runtime `attr/current=kernel` and no subsystem fd
  hold.
- hard gates: no device contact, no daemon start, no `mdm_helper`/`ks`, no
  Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, raw eSoC
  ioctl, GPIO/sysfs/debugfs/subsystem write, module load/unload, boot image
  write, or partition write.
- next: V863 should capture `/vendor/etc/init/pm_proxy_helper.rc` read-only and
  classify `vendor.per_proxy_helper` before modelling or starting it.

### V863. pm_proxy_helper.rc Read-only Capture

- plan: `docs/plans/NATIVE_INIT_V863_PM_PROXY_HELPER_RC_CAPTURE_PLAN_2026-05-25.md`
- report: `docs/reports/NATIVE_INIT_V863_PM_PROXY_HELPER_RC_CAPTURE_2026-05-25.md`
- runner: `scripts/revalidation/native_wifi_pm_proxy_helper_rc_capture_v863.py`
- evidence:
  - `tmp/wifi/v863-pm-proxy-helper-rc-plan/manifest.json`
  - `tmp/wifi/v863-pm-proxy-helper-rc-live/manifest.json`
- decision: `v863-pm-proxy-helper-contract-captured`
- result: bounded read-only live PASS. V863 dynamically read current
  `/sys/class/block/sda29/dev` as `259:13`, created only a temporary block node
  under `/tmp/a90-v863-*`, mounted it ext4 `ro,noload`, captured
  `/vendor/etc/init/pm_proxy_helper.rc`, then unmounted and removed the
  temporary path. Captured service:
  `vendor.per_proxy_helper /vendor/bin/pm_proxy_helper`, `class core`,
  `user system`, `group system`, `disabled`, `oneshot`, started by
  `on post-fs-data`. Cleanup and post-run selftest passed.
- hard gates: no daemon start, no `mdm_helper`/`ks`, no Wi-Fi HAL,
  scan/connect, credentials, DHCP/routes, external ping, raw eSoC ioctl,
  GPIO/sysfs/debugfs/subsystem write, module load/unload, boot image write, or
  partition write.
- next: V864 should classify helper support for the complete PeripheralManager
  init contract before starting anything new: `vendor.per_proxy_helper`
  post-fs-data oneshot, `vendor.per_mgr` `ioprio rt 4`, `vendor.per_proxy`
  property lifecycle, and V861's runtime `kernel` domain gap.

### V864-V869. PeripheralManager Init Contract Path

- basis:
  `docs/overview/MDM3_ESOC_SDX50M_BRINGUP_RESEARCH_2026-05-25.md`
  section 18.
- external references checked:
  - Android init service/property-trigger semantics:
    `https://android.googlesource.com/platform/system/core/+/refs/heads/android10-dev/init/README.md`
  - Qualcomm/Pixel `per_mgr`/`per_proxy` init pattern:
    `https://android.googlesource.com/device/google/redbull/+/2cd0dab5d232bbf2bf5af38cb2e92111e882af43/init.hardware.rc`
  - Linux `ioprio_set(2)` behavior and permissions:
    `https://man7.org/linux/man-pages/man2/ioprio_set.2.html`
- decision: V864 is the immediate next cycle. It is host-only and must not
  start any service.
- V864 target: compare current helper source against V861/V862/V863 evidence
  and produce a fail-closed implementation checklist for the full
  PeripheralManager init contract.
- V865 target: implement helper support for `pm_proxy_helper`, `ioprio rt 4`,
  `init.svc.vendor.per_mgr=running` proxy lifecycle, shutdown stop, child
  fd/domain capture, and mode guardrails. Build only.
- V866 target: deploy new helper only after static validation and checksum
  proof. No daemon start.
- V867 target: bounded live start-only of `pm_proxy_helper` oneshot plus
  init-equivalent `per_mgr`/`per_proxy` lifecycle under Android node parity.
  Capture fd holds, runtime `attr/current`, ioprio result, dmesg, and cleanup.
- V868 target: classify V867 result. If no subsystem fd hold appears, separate
  SELinux transition gap from missing PeripheralManager input. If fd hold or
  `mdm3` movement appears, classify the next safe gate.
- V869 target: only if V867/V868 prove PeripheralManager parity, consider a
  PM-gated `mdm_helper`/`ks` start-only proof.
- hard gates for V864-V868: no `mdm_helper`, no `ks`, no Wi-Fi HAL,
  scan/connect, credentials, DHCP/routes, external ping, raw eSoC ioctl,
  GPIO/sysfs/debugfs/subsystem write, module load/unload, boot image write, or
  partition write.

### V864. PeripheralManager Helper-support Classifier

- plan: `docs/plans/NATIVE_INIT_V864_PM_INIT_CONTRACT_SUPPORT_PLAN_2026-05-25.md`
- report: `docs/reports/NATIVE_INIT_V864_PM_INIT_CONTRACT_SUPPORT_2026-05-25.md`
- classifier: `scripts/revalidation/native_wifi_pm_init_contract_support_v864.py`
- evidence:
  - `tmp/wifi/v864-pm-init-contract-support-plan/manifest.json`
  - `tmp/wifi/v864-pm-init-contract-support/manifest.json`
- decision: `v864-init-contract-wrapper-needed`
- result: host-only PASS. V864 proved the V861/V862/V863 prerequisite evidence
  is present and then classified the current helper source. Runtime
  attr/current and fd capture primitives already exist, but the helper does not
  yet model `pm_proxy_helper`, `per_proxy_helper` SELinux mapping,
  `vendor.per_mgr` `ioprio rt 4`, `init.svc.vendor.per_mgr=running`
  property-start lifecycle, or shutdown-stop semantics for `vendor.per_proxy`.
- hard gates: no device contact, helper deploy, daemon start, `mdm_helper`,
  `ks`, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, raw
  eSoC ioctl, GPIO/sysfs/debugfs/subsystem write, module load/unload, boot
  image write, or partition write.
- next: V865 should implement source/build-only helper support for the missing
  PeripheralManager init-contract model. V866 deploy and V867 live start-only
  remain blocked until V865 static validation passes.

### V865. PeripheralManager Init Contract Helper Build

- plan: `docs/plans/NATIVE_INIT_V865_PM_INIT_CONTRACT_HELPER_PLAN_2026-05-25.md`
- report: `docs/reports/NATIVE_INIT_V865_PM_INIT_CONTRACT_HELPER_BUILD_2026-05-25.md`
- helper source: `stage3/linux_init/helpers/a90_android_execns_probe.c`
- evidence:
  - `tmp/wifi/v865-execns-helper-v134-build/a90_android_execns_probe`
  - `tmp/wifi/v865-post-build-v864-classifier/manifest.json`
- result: source/build-only PASS. Helper `v134` adds
  `wifi-companion-peripheral-manager-init-contract-start-only`, a distinct
  `/vendor/bin/pm_proxy_helper` child, `u:r:per_proxy_helper:s0` target mapping,
  `per_mgr` `SYS_ioprio_set` realtime priority `4` instrumentation,
  `init.svc.vendor.per_mgr=running` proxy lifecycle markers, and bounded
  shutdown-stop markers for `vendor.per_proxy`.
- classifier: post-build V864 classifier shows all source support markers
  present. Remaining gaps are runtime evidence only: V861 still had
  `attr/current=kernel` and no `/dev/subsys_esoc0` or `/dev/subsys_modem` fd
  hold.
- hard gates: no helper deploy, no actor start, no `mdm_helper`, no `ks`, no
  Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, raw eSoC
  ioctl, GPIO/sysfs/debugfs/subsystem write, module load/unload, boot image
  write, or partition write.
- next: V866 should deploy helper `v134` only with checksum/version proof and
  no actor start. V867 should then run the first bounded
  `pm_proxy_helper`/`per_mgr`/`per_proxy` init-contract start-only proof.

### V866. Helper v134 Deploy-only Proof

- plan: `docs/plans/NATIVE_INIT_V866_HELPER_V134_DEPLOY_PLAN_2026-05-25.md`
- report: `docs/reports/NATIVE_INIT_V866_HELPER_V134_DEPLOY_2026-05-25.md`
- deploy wrapper: `scripts/revalidation/wifi_execns_helper_v134_deploy_preflight.py`
- evidence:
  - `tmp/wifi/v866-execns-helper-v134-plan/manifest.json`
  - `tmp/wifi/v866-execns-helper-v134-preflight/manifest.json`
  - `tmp/wifi/v866-execns-helper-v134-deploy-r3/manifest.json`
  - `tmp/wifi/v866-post-health/`
- decision: `execns-helper-v134-deploy-pass`
- result: deploy-only PASS. Helper `v134` was installed to
  `/cache/bin/a90_android_execns_probe` by serial appendfile/uudecode using a
  safe 1850-byte chunk size. Remote sha is
  `92792fb954de42825d328c047498c5291be803185d9897d22dd734fd9bd77582`, usage
  shows `a90_android_execns_probe v134`, and the new
  `wifi-companion-peripheral-manager-init-contract-start-only` mode is present.
  Post-deploy selftest is `pass=11 warn=1 fail=0`, gated actor process count is
  `0`, and Wi-Fi link count is `0`.
- hard gates: no actor start, no `mdm_helper`, no `ks`, no Wi-Fi HAL,
  scan/connect, credentials, DHCP/routes, external ping, raw eSoC ioctl,
  GPIO/sysfs/debugfs/subsystem write, module load/unload, boot image write, or
  partition write.
- next: V867 should run the bounded PM init-contract start-only proof with only
  `pm_proxy_helper`, `per_mgr`, and `per_proxy` under Android node parity.

### V867. PeripheralManager Init-contract Start-only Proof

- plan: `docs/plans/NATIVE_INIT_V867_PM_INIT_CONTRACT_START_ONLY_PLAN_2026-05-25.md`
- report: `docs/reports/NATIVE_INIT_V867_PM_INIT_CONTRACT_START_ONLY_2026-05-25.md`
- runner: `scripts/revalidation/native_wifi_pm_init_contract_start_only_v867.py`
- evidence:
  - `tmp/wifi/v867-pm-init-contract-plan/manifest.json`
  - `tmp/wifi/v867-pm-init-contract-live-r3/manifest.json`
  - `tmp/wifi/v867-reboot-cleanup/`
- decision: `v867-residual-actor-cleanup-required`
- result: bounded live proof found a blocker. Helper `v134` PM init-contract
  markers executed: `pm_proxy_helper` child, `per_mgr` `ioprio rt 4`,
  `init.svc.vendor.per_mgr=running`, property-gated `per_proxy`, and
  shutdown-stop markers. Runtime domains still stayed `kernel`, `per_mgr` did
  not hold `/dev/subsys_esoc0` or `/dev/subsys_modem`, and `pm_proxy_helper`
  remained `Ds` after the helper cleanup window. Native reboot restored v724,
  selftest `pass=11 warn=1 fail=0`, and actor process count `0`.
- hard gates held: no `mdm_helper`, no `ks`, no CNSS, no Wi-Fi HAL,
  scan/connect, credentials, DHCP/routes, external ping, raw eSoC ioctl,
  GPIO/sysfs/debugfs/subsystem state write, module load/unload, boot image
  write, or partition write.
- next: V868 should classify `pm_proxy_helper` blocking behavior and SELinux
  transition semantics host-only/read-only before any more live actor start.

### V868. PM/eSoC Contract Classifier

- plan: `docs/plans/NATIVE_INIT_V868_PM_ESOC_CONTRACT_CLASSIFIER_PLAN_2026-05-25.md`
- report: `docs/reports/NATIVE_INIT_V868_PM_ESOC_CONTRACT_CLASSIFIER_2026-05-25.md`
- runner: `scripts/revalidation/native_wifi_pm_esoc_contract_classifier_v868.py`
- evidence:
  - `tmp/wifi/v868-pm-esoc-contract-classifier/manifest.json`
  - `tmp/wifi/v868-pm-esoc-contract-classifier/summary.md`
- decision: `v868-esoc-req-eng-precondition-selected`
- result: host-only PASS. V868 tied the V867 `pm_proxy_helper` D-state to the
  local A90 Samsung OSRC eSoC contract: `ESOC_REG_REQ_ENG=7`,
  `ESOC_REG_CMD_ENG=8`, `ESOC_CMD_EXE=1`, and `ESOC_PWR_ON=1`. It also
  confirmed the Samsung `subsystem_restart.c` `pm_proxy_helper` exception.
- interpretation: `pm_proxy_helper` alone should not be retried. Android likely
  brings up the `/dev/esoc-0` CMD/REQ engine side first, then allows
  `pm_proxy_helper` to hold `/dev/subsys_esoc0`; V867 did only the hold side
  and reproduced the D-state class.
- hard gates held: no device contact, daemon start, `mdm_helper`, `ks`,
  Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, raw live
  eSoC ioctl, GPIO/sysfs/debugfs/subsystem state write, module load/unload,
  boot image write, or partition write.
- next: V869 should be source/build-only helper design for an A90 eSoC control
  preflight. Live `ESOC_PWR_ON`, `mdm_helper`, `ks`, PM actor starts, CNSS,
  HAL, scan/connect, credentials, DHCP/routes, and external ping remain blocked
  until separate gates.

### V869. eSoC Control Preflight Helper Build

- plan: `docs/plans/NATIVE_INIT_V869_ESOC_CONTROL_PREFLIGHT_HELPER_PLAN_2026-05-25.md`
- report: `docs/reports/NATIVE_INIT_V869_ESOC_CONTROL_PREFLIGHT_HELPER_BUILD_2026-05-25.md`
- helper source: `stage3/linux_init/helpers/a90_android_execns_probe.c`
- evidence:
  - `tmp/wifi/v869-execns-helper-v135-build/a90_android_execns_probe`
- result: source/build-only PASS. Helper `v135` adds
  `wifi-companion-esoc-control-preflight`, local A90 eSoC UAPI markers,
  `--allow-esoc-control-preflight`, and fail-closed markers proving no
  `mdm_helper`, `ks`, Wi-Fi HAL, scan/connect, credentials, DHCP/routes,
  external ping, `REG_REQ_ENG`, `REG_CMD_ENG`, `CMD_EXE`, `WAIT_FOR_REQ`,
  `NOTIFY`, or `PWR_ON` is attempted by default.
- build: static ARM64 artifact created with sha256
  `ad1bbbf295be61ef612406091ccd469c4ef45ab44c0f753c4de034e487ddaad1` and no
  dynamic section.
- hard gates held: no helper deploy, device contact, live eSoC ioctl,
  `mdm_helper`, `ks`, `pm_proxy_helper`, CNSS, Wi-Fi HAL, scan/connect,
  credentials, DHCP/routes, external ping, module load/unload, boot image
  write, or partition write.
- next: V870 should deploy helper `v135` only with checksum/version/mode proof
  and post-deploy health. Live eSoC control preflight remains a separate later
  gate.

### V870. Helper v135 Deploy-only Proof

- plan: `docs/plans/NATIVE_INIT_V870_HELPER_V135_DEPLOY_PLAN_2026-05-25.md`
- report: `docs/reports/NATIVE_INIT_V870_HELPER_V135_DEPLOY_2026-05-25.md`
- deploy wrapper: `scripts/revalidation/wifi_execns_helper_v135_deploy_preflight.py`
- evidence:
  - `tmp/wifi/v870-execns-helper-v135-plan/manifest.json`
  - `tmp/wifi/v870-execns-helper-v135-preflight/manifest.json`
  - `tmp/wifi/v870-execns-helper-v135-deploy/manifest.json`
  - `tmp/wifi/v870-post-health/manifest.json`
- decision: `execns-helper-v135-deploy-pass`
- result: deploy-only PASS. Helper `v135` was installed to
  `/cache/bin/a90_android_execns_probe` by serial appendfile/uudecode using
  1850-byte chunks. Remote sha is
  `ad1bbbf295be61ef612406091ccd469c4ef45ab44c0f753c4de034e487ddaad1`; usage
  shows `a90_android_execns_probe v135` and
  `wifi-companion-esoc-control-preflight`.
- post health: selftest `pass=11 warn=1 fail=0`, exact actor process hits `0`,
  and Wi-Fi link hits `0`.
- hard gates held: no actor start, no `mdm_helper`, no `ks`,
  no `pm_proxy_helper`, no CNSS, no service-manager trio, no Wi-Fi HAL,
  no scan/connect, credentials, DHCP/routes, external ping, live eSoC control
  preflight, mutating eSoC ioctl, module load/unload, boot image write,
  partition write, or firmware mutation.
- next: V871 should run a bounded live eSoC control preflight with helper
  `v135`, limited to node visibility and read-only eSoC status ioctls. Mutating
  eSoC state-machine steps remain blocked.


### V872. eSoC Preflight Helper v136 Build

- plan: `docs/plans/NATIVE_INIT_V872_ESOC_PREFLIGHT_HELPER_V136_PLAN_2026-05-25.md`
- report: `docs/reports/NATIVE_INIT_V872_ESOC_PREFLIGHT_HELPER_V136_BUILD_2026-05-25.md`
- helper source: `stage3/linux_init/helpers/a90_android_execns_probe.c`
- evidence:
  - `tmp/wifi/v872-execns-helper-v136-build/a90_android_execns_probe`
- result: source/build-only PASS. Helper `v136` splits eSoC control preflight
  from service-manager/SELinuxfs runtime classification while preserving private
  `/dev/esoc-0`, `/dev/subsys_esoc0`, and `/dev/subsys_modem` materialization.
- build: sha256
  `76dce733b8444073fc615a44df240aa7f8256dfb7f6c123c3f5e388907356980`, static
  ARM64, no dynamic section.
- hard gates held: no deploy, no live eSoC ioctl, no actor start, no Wi-Fi
  bring-up.
- next: V873 helper `v136` deploy-only proof.

### V873. Helper v136 Deploy-only Proof

- plan: `docs/plans/NATIVE_INIT_V873_HELPER_V136_DEPLOY_PLAN_2026-05-25.md`
- report: `docs/reports/NATIVE_INIT_V873_HELPER_V136_DEPLOY_2026-05-25.md`
- deploy wrapper: `scripts/revalidation/wifi_execns_helper_v136_deploy_preflight.py`
- evidence:
  - `tmp/wifi/v873-execns-helper-v136-plan/manifest.json`
  - `tmp/wifi/v873-execns-helper-v136-preflight/manifest.json`
  - `tmp/wifi/v873-execns-helper-v136-deploy/manifest.json`
- decision: `execns-helper-v136-deploy-pass`
- result: deploy-only PASS. Helper `v136` was installed by serial
  appendfile/uudecode using 1850-byte chunks.
- hard gates held: no actor start, no Wi-Fi bring-up, no live eSoC ioctl.
- next: V874 bounded read-only eSoC control preflight.

### V874. eSoC Control Read-only Preflight

- plan: `docs/plans/NATIVE_INIT_V874_ESOC_CONTROL_PREFLIGHT_PLAN_2026-05-25.md`
- report: `docs/reports/NATIVE_INIT_V874_ESOC_CONTROL_PREFLIGHT_2026-05-25.md`
- live runner: `scripts/revalidation/native_wifi_esoc_control_preflight_v874.py`
- evidence:
  - `tmp/wifi/v874-esoc-control-preflight-plan/manifest.json`
  - `tmp/wifi/v874-esoc-control-preflight-live/manifest.json`
- decision: `v874-esoc-readonly-ioctl-probe-pass`
- result: `/dev/esoc-0` open succeeded and read-only ioctl probe completed.
  `GET_STATUS` and `GET_ERR_FATAL` returned rc `0`; `GET_LINK_ID` returned
  errno `22`, which is recorded as diagnostic data rather than a gate failure.
- hard gates held: no `REG_REQ_ENG`, `REG_CMD_ENG`, `CMD_EXE`, `WAIT_FOR_REQ`,
  `NOTIFY`, `PWR_ON`, actor start, Wi-Fi HAL, scan/connect, DHCP/routes,
  credentials, or external ping.
- next: V875 host-only eSoC state-machine precondition classifier for future
  CMD/REQ registration.


### V875. eSoC State-machine Precondition Classifier

- plan: `docs/plans/NATIVE_INIT_V875_ESOC_STATE_MACHINE_PRECONDITION_PLAN_2026-05-25.md`
- report: `docs/reports/NATIVE_INIT_V875_ESOC_STATE_MACHINE_PRECONDITION_2026-05-25.md`
- classifier: `scripts/revalidation/native_wifi_esoc_state_machine_precondition_classifier_v875.py`
- evidence:
  - `tmp/wifi/v875-esoc-state-machine-precondition-classifier/manifest.json`
- decision: `v875-esoc-state-machine-precondition-pass`
- result: host-only PASS. The next implementation step is helper `v137`
  source/build-only support for CMD/REQ registration. V875 did not contact the
  device and did not execute any eSoC ioctl.
- hard gates held: no `REG_CMD_ENG`, `REG_REQ_ENG`, `CMD_EXE`, `PWR_ON`,
  `WAIT_FOR_REQ`, `NOTIFY`, `/dev/subsys_esoc0` open, actor start, Wi-Fi HAL,
  scan/connect, DHCP/routes, credentials, or external ping.
- next: V876 helper `v137` source/build-only CMD/REQ registration support.


### V876. eSoC Engine Register Helper v137 Build

- plan: `docs/plans/NATIVE_INIT_V876_ESOC_ENGINE_REGISTER_HELPER_PLAN_2026-05-25.md`
- report: `docs/reports/NATIVE_INIT_V876_ESOC_ENGINE_REGISTER_HELPER_BUILD_2026-05-25.md`
- helper source: `stage3/linux_init/helpers/a90_android_execns_probe.c`
- evidence:
  - `tmp/wifi/v876-execns-helper-v137-build/a90_android_execns_probe`
- result: source/build-only PASS. Helper `v137` adds
  `wifi-companion-esoc-engine-register-preflight` and
  `--allow-esoc-engine-register-preflight`.
- build: sha256
  `e47eb52b0b2b2fb601fdbc4ecebdf72e2fda9519eac37e776d62c11d2d469aa3`, static
  ARM64, no dynamic section.
- hard gates held: no deploy, no live eSoC ioctl, no `CMD_EXE`, `PWR_ON`,
  `WAIT_FOR_REQ`, `NOTIFY`, `/dev/subsys_esoc0` open, actor start, Wi-Fi HAL,
  scan/connect, DHCP/routes, credentials, or external ping.
- next: V877 helper `v137` deploy-only checksum/version/mode proof.

### V877. Helper v137 Deploy-only Proof

- plan: `docs/plans/NATIVE_INIT_V877_HELPER_V137_DEPLOY_PLAN_2026-05-25.md`
- report: `docs/reports/NATIVE_INIT_V877_HELPER_V137_DEPLOY_2026-05-25.md`
- deploy wrapper: `scripts/revalidation/wifi_execns_helper_v137_deploy_preflight.py`
- evidence:
  - `tmp/wifi/v877-execns-helper-v137-plan/manifest.json`
  - `tmp/wifi/v877-execns-helper-v137-preflight/manifest.json`
  - `tmp/wifi/v877-execns-helper-v137-deploy-preflight/manifest.json`
- decision: `execns-helper-v137-deploy-pass`
- result: deploy-only PASS. Helper `v137` was installed by serial
  appendfile/uudecode using 1850-byte chunks. Remote sha, helper marker,
  eSoC engine registration mode token, selftest fail0, actor-clean, and
  Wi-Fi-link-clean all passed.
- hard gates held: no live eSoC ioctl, no `/dev/subsys_esoc0` open, no actor
  start, no Wi-Fi HAL, scan/connect, DHCP/routes, credentials, or external ping.
- next: V878 bounded live `REG_CMD_ENG`/`REG_REQ_ENG` registration preflight.

### V878. eSoC Engine Register Preflight

- plan: `docs/plans/NATIVE_INIT_V878_ESOC_ENGINE_REGISTER_PREFLIGHT_PLAN_2026-05-25.md`
- report: `docs/reports/NATIVE_INIT_V878_ESOC_ENGINE_REGISTER_PREFLIGHT_2026-05-25.md`
- live runner: `scripts/revalidation/native_wifi_esoc_engine_register_preflight_v878.py`
- evidence:
  - `tmp/wifi/v878-esoc-engine-register-preflight-plan/manifest.json`
  - `tmp/wifi/v878-esoc-engine-register-preflight-missing-flags/manifest.json`
  - `tmp/wifi/v878-esoc-engine-register-preflight-live/manifest.json`
- decision: `v878-esoc-engine-register-ioctl-review`
- result: bounded live review. `REG_REQ_ENG` returned rc `0`; `REG_CMD_ENG`
  returned errno `16` (`EBUSY`). Helper fds were closed, created nodes were
  cleaned up, postflight selftest stayed fail0, and actor/Wi-Fi surfaces stayed
  clean.
- hard gates held: no `CMD_EXE`, `PWR_ON`, `WAIT_FOR_REQ`, `NOTIFY`,
  `/dev/subsys_esoc0` open, actor start, Wi-Fi HAL, scan/connect, DHCP/routes,
  credentials, or external ping.
- next: V879 host-only classifier for CMD engine ownership, eSoC client hooks,
  and the next safe subsystem-powerup guardrails.

### V879. CMD Engine Ownership Classifier

- plan: `docs/plans/NATIVE_INIT_V879_CMD_ENGINE_OWNERSHIP_CLASSIFIER_PLAN_2026-05-26.md`
- report: `docs/reports/NATIVE_INIT_V879_CMD_ENGINE_OWNERSHIP_CLASSIFIER_2026-05-26.md`
- classifier: `scripts/revalidation/native_wifi_esoc_cmd_engine_classifier_v879.py`
- evidence:
  - `tmp/wifi/v879-cmd-engine-ownership-classifier/manifest.json`
- decision: `v879-cmd-engine-ebusy-classified`
- result: host-only PASS. Direct userspace `CMD_EXE` remains blocked because
  `REG_CMD_ENG` returned `EBUSY`. `REG_REQ_ENG` rc0 makes a REQ-registered
  subsystem-open helper mode the next source/build-only candidate.
- hard gates held: no device contact, no helper deploy, no eSoC ioctl, no
  subsystem open, no actor start, no Wi-Fi HAL, scan/connect, DHCP/routes,
  credentials, or external ping.
- next: V880 helper `v138` source/build-only stale-open-errno repair plus
  fail-closed REQ-registered subsystem-hold preflight support.

### V880. REQ-registered Subsystem Hold Helper v138 Build

- plan: `docs/plans/NATIVE_INIT_V880_REQ_REGISTERED_SUBSYS_HOLD_HELPER_PLAN_2026-05-26.md`
- report: `docs/reports/NATIVE_INIT_V880_REQ_REGISTERED_SUBSYS_HOLD_HELPER_BUILD_2026-05-26.md`
- helper source: `stage3/linux_init/helpers/a90_android_execns_probe.c`
- evidence:
  - `tmp/wifi/v880-execns-helper-v138-build/manifest.json`
  - `tmp/wifi/v880-execns-helper-v138-build/a90_android_execns_probe`
- decision: `v880-helper-v138-build-pass`
- result: source/build-only PASS. Helper `v138` repairs stale successful-open
  errno reporting and adds fail-closed
  `wifi-companion-esoc-req-registered-subsys-hold-preflight` support.
- build: sha256
  `2ac8c6730768f86a221722a6ff259e3a4617134221498bd1956a63980a22a9b5`, static
  ARM64, no dynamic section.
- hard gates held: no device contact, no helper deploy, no live eSoC ioctl, no
  `/dev/subsys_esoc0` open, no actor start, no Wi-Fi HAL, scan/connect,
  DHCP/routes, credentials, or external ping.
- next: V881 helper `v138` deploy-only checksum/version/mode proof.

### V881. Helper v138 Deploy-only Proof

- plan: `docs/plans/NATIVE_INIT_V881_HELPER_V138_DEPLOY_PLAN_2026-05-26.md`
- report: `docs/reports/NATIVE_INIT_V881_HELPER_V138_DEPLOY_2026-05-26.md`
- deploy wrapper: `scripts/revalidation/wifi_execns_helper_v138_deploy_preflight.py`
- evidence:
  - `tmp/wifi/v881-execns-helper-v138-plan/manifest.json`
  - `tmp/wifi/v881-execns-helper-v138-preflight/manifest.json`
  - `tmp/wifi/v881-execns-helper-v138-deploy-preflight/manifest.json`
- decision: `execns-helper-v138-deploy-pass`
- result: deploy-only PASS. Helper `v138` was installed by serial
  appendfile/uudecode using 1850-byte chunks. Remote sha, helper marker, eSoC
  REQ-registered subsystem-hold mode token, selftest fail0, actor-clean, and
  Wi-Fi-link-clean all passed.
- route correction: follow-up source analysis says initial powerup only needs
  `REG_REQ_ENG`; `REG_CMD_ENG` ownership is not required for the kernel's
  internal power-on path, and SDX50M may not emit `ESOC_REQ_IMG`.
- hard gates held: no live eSoC ioctl, no `/dev/subsys_esoc0` open, no actor
  start, no Wi-Fi HAL, scan/connect, DHCP/routes, credentials, or external ping.
- next: V882 helper `v139` source/build-only passive `ESOC_WAIT_FOR_REQ`
  observer support before any live subsystem-hold window.

### V882. Passive WAIT_FOR_REQ Observer Helper v139 Build

- plan: `docs/plans/NATIVE_INIT_V882_PASSIVE_WAIT_FOR_REQ_HELPER_PLAN_2026-05-26.md`
- report: `docs/reports/NATIVE_INIT_V882_PASSIVE_WAIT_FOR_REQ_HELPER_BUILD_2026-05-26.md`
- helper source: `stage3/linux_init/helpers/a90_android_execns_probe.c`
- evidence:
  - `tmp/wifi/v882-execns-helper-v139-build/manifest.json`
  - `tmp/wifi/v882-execns-helper-v139-build/a90_android_execns_probe`
- decision: `v882-helper-v139-build-pass`
- result: source/build-only PASS. Helper `v139` adds passive
  `ESOC_WAIT_FOR_REQ` observer markers to the REQ-registered subsystem-hold
  preflight mode.
- build: sha256
  `077ced65ae5b0b546ecdf3b1bb0c808d3ec34bfa2462516e6ceba170b18f23c5`, static
  ARM64, no dynamic section.
- hard gates held: no device contact, no helper deploy, no live eSoC ioctl, no
  `/dev/subsys_esoc0` open, no `ESOC_NOTIFY`, no actor start, no Wi-Fi HAL,
  scan/connect, DHCP/routes, credentials, or external ping.
- next: V883 helper `v139` deploy-only checksum/version/mode proof.

### V883. Helper v139 Deploy-only Proof

- plan: `docs/plans/NATIVE_INIT_V883_HELPER_V139_DEPLOY_PLAN_2026-05-26.md`
- report: `docs/reports/NATIVE_INIT_V883_HELPER_V139_DEPLOY_2026-05-26.md`
- deploy wrapper: `scripts/revalidation/wifi_execns_helper_v139_deploy_preflight.py`
- evidence:
  - `tmp/wifi/v883-execns-helper-v139-plan/manifest.json`
  - `tmp/wifi/v883-execns-helper-v139-preflight/manifest.json`
  - `tmp/wifi/v883-execns-helper-v139-deploy-preflight/manifest.json`
  - `tmp/wifi/v883-execns-helper-v139-postdeploy/manifest.json`
- decision: `execns-helper-v139-deploy-pass`
- result: deploy-only PASS. Helper `v139` was installed by serial
  appendfile/uudecode using 1850-byte chunks. Remote sha, helper marker, eSoC
  REQ-registered subsystem-hold mode token, selftest fail0, actor-clean, and
  Wi-Fi-link-clean all passed.
- hard gates held: no live eSoC ioctl, no `/dev/subsys_esoc0` open, no actor
  start, no Wi-Fi HAL, scan/connect, DHCP/routes, credentials, or external ping.
- next: V884 bounded live REQ-registered subsystem-hold observer preflight.
  The next gate should rely on `REG_REQ_ENG`, record passive
  `ESOC_WAIT_FOR_REQ`, and treat absent `ESOC_REQ_IMG` as diagnostic data.

### V884. REQ-registered Subsystem-hold Observer

- plan: `docs/plans/NATIVE_INIT_V884_REQ_REGISTERED_SUBSYS_HOLD_OBSERVER_PLAN_2026-05-26.md`
- report: `docs/reports/NATIVE_INIT_V884_REQ_REGISTERED_SUBSYS_HOLD_OBSERVER_2026-05-26.md`
- live runner: `scripts/revalidation/native_wifi_esoc_req_registered_subsys_hold_v884.py`
- evidence:
  - `tmp/wifi/v884-esoc-req-registered-subsys-hold-plan/manifest.json`
  - `tmp/wifi/v884-esoc-req-registered-subsys-hold-live/manifest.json`
  - `tmp/wifi/v884-esoc-req-registered-subsys-hold-reboot-cleanup/`
- decision: `v884-reboot-required`
- result: bounded live evidence PASS, cleanup required. `REG_REQ_ENG` returned
  rc `0`. Passive `ESOC_WAIT_FOR_REQ` returned rc `4`, errno `0`, value `1`,
  which local OSRC maps to copied `sizeof(u32)` plus `ESOC_REQ_IMG`.
  `/dev/subsys_esoc0` open did not return and required recovery reboot.
- cleanup: reboot returned to native `v724`; post-reboot `BOOT OK` and
  selftest `fail=0` were confirmed.
- hard gates held: no `REG_CMD_ENG`, no direct userspace `CMD_EXE`, no
  explicit userspace `PWR_ON`, no `ESOC_NOTIFY`, no actor start, no Wi-Fi HAL,
  scan/connect, DHCP/routes, credentials, or external ping.
- next: V885 host-only Android `mdm_helper` image-request response classifier.
  Do not retry `/dev/subsys_esoc0` live until the `ESOC_REQ_IMG` response
  contract is known.

### V885. ESOC_REQ_IMG Response Contract Classifier

- plan: `docs/plans/NATIVE_INIT_V885_ESOC_REQ_IMG_RESPONSE_CLASSIFIER_PLAN_2026-05-26.md`
- report: `docs/reports/NATIVE_INIT_V885_ESOC_REQ_IMG_RESPONSE_CLASSIFIER_2026-05-26.md`
- classifier: `scripts/revalidation/native_wifi_esoc_req_img_response_classifier_v885.py`
- evidence:
  - `tmp/wifi/v885-esoc-req-img-response-classifier/manifest.json`
  - `tmp/wifi/v885-esoc-req-img-response-classifier/summary.md`
- decision: `v885-esoc-req-img-response-contract-classified`
- result: host-only PASS. V884 `ESOC_WAIT_FOR_REQ rc=4 errno=0 value=1` maps
  to copied `sizeof(u32)` plus `ESOC_REQ_IMG`, not an ioctl failure. Local OSRC
  exposes `ESOC_IMG_XFER_DONE` and `ESOC_BOOT_DONE` response hooks.
- hard gates held: no device contact, no live eSoC ioctl, no
  `/dev/subsys_esoc0` open, no `ESOC_NOTIFY`, no actor start, no Wi-Fi HAL,
  scan/connect, DHCP/routes, credentials, or external ping.
- next: V886 helper `v140` source/build-only semantic repair plus guarded
  response-mode scaffold. Live `ESOC_NOTIFY` remains blocked until a separate
  deploy/live response gate.

### V886. ESOC_REQ_IMG Response Helper v140 Build

- plan: `docs/plans/NATIVE_INIT_V886_ESOC_REQ_IMG_RESPONSE_HELPER_PLAN_2026-05-26.md`
- report: `docs/reports/NATIVE_INIT_V886_ESOC_REQ_IMG_RESPONSE_HELPER_BUILD_2026-05-26.md`
- helper source: `stage3/linux_init/helpers/a90_android_execns_probe.c`
- evidence:
  - `tmp/wifi/v886-execns-helper-v140-build/manifest.json`
  - `tmp/wifi/v886-execns-helper-v140-build/build.log`
  - `tmp/wifi/v886-execns-helper-v140-build/a90_android_execns_probe`
- decision: `v886-helper-v140-build-pass`
- result: source/build-only PASS. Helper `v140` repairs passive
  `ESOC_WAIT_FOR_REQ` semantics so copied `sizeof(u32)` byte counts are
  `request-observed`, labels value `1` as `ESOC_REQ_IMG`, and adds fail-closed
  response scaffold markers for `ESOC_IMG_XFER_DONE`/`ESOC_BOOT_DONE`.
- build: sha256
  `894fdd753cb6567b2abbb3c94f332ce63cf959b7d1708768cf3bcdc10b2b53e0`, static
  ARM64, no dynamic section.
- hard gates held: no helper deploy, no device contact, no live eSoC ioctl, no
  `/dev/subsys_esoc0` open, no `ESOC_NOTIFY`, no actor start, no Wi-Fi HAL,
  scan/connect, DHCP/routes, credentials, or external ping.
- next: V887 helper `v140` deploy-only checksum/version/mode proof. Live
  response remains blocked until a separate bounded response gate.

### V887. Helper v140 Deploy-only Proof

- plan: `docs/plans/NATIVE_INIT_V887_HELPER_V140_DEPLOY_PLAN_2026-05-26.md`
- report: `docs/reports/NATIVE_INIT_V887_HELPER_V140_DEPLOY_2026-05-26.md`
- deploy wrapper: `scripts/revalidation/wifi_execns_helper_v140_deploy_preflight.py`
- evidence:
  - `tmp/wifi/v887-execns-helper-v140-plan/manifest.json`
  - `tmp/wifi/v887-execns-helper-v140-preflight/manifest.json`
  - `tmp/wifi/v887-execns-helper-v140-deploy-preflight/manifest.json`
  - `tmp/wifi/v887-execns-helper-v140-deploy-preflight-retry1850/manifest.json`
- decision: `execns-helper-v140-deploy-pass`
- result: deploy-only PASS. First serial chunk `3000` failed line-safety before
  writes (`chunks_written=0`); retry with chunk `1850` installed helper `v140`
  and verified remote sha/mode marker.
- hard gates held: no live eSoC ioctl, no `/dev/subsys_esoc0` open, no
  `ESOC_NOTIFY`, no actor start, no service-manager, no Wi-Fi HAL,
  scan/connect, DHCP/routes, credentials, or external ping.
- next: V888 host-only response-gate classifier. Live response remains blocked
  until it decides the exact bounded `ESOC_NOTIFY` sequence and cleanup rules.

### V888. eSoC Response Gate Classifier

- plan: `docs/plans/NATIVE_INIT_V888_ESOC_RESPONSE_GATE_CLASSIFIER_PLAN_2026-05-26.md`
- report: `docs/reports/NATIVE_INIT_V888_ESOC_RESPONSE_GATE_CLASSIFIER_2026-05-26.md`
- classifier: `scripts/revalidation/native_wifi_esoc_response_gate_classifier_v888.py`
- evidence:
  - `tmp/wifi/v888-esoc-response-gate-classifier/manifest.json`
  - `tmp/wifi/v888-esoc-response-gate-classifier/summary.md`
- decision: `v888-esoc-response-gate-classified`
- result: host-only PASS. The next response sequence is
  `ESOC_IMG_XFER_DONE` first, then `ESOC_GET_STATUS`/readiness polling, then
  conditional `ESOC_BOOT_DONE` only if readiness is proven.
- hard gates held: no device contact, no live eSoC ioctl, no
  `/dev/subsys_esoc0` open, no `ESOC_NOTIFY`, no actor start, no
  service-manager, no Wi-Fi HAL, scan/connect, DHCP/routes, credentials, or
  external ping.
- next: V889 helper `v141` source/build-only conditional response mode. Live
  response remains blocked until a separate bounded proof.

### V889. eSoC Conditional Response Helper v141 Build

- plan: `docs/plans/NATIVE_INIT_V889_ESOC_CONDITIONAL_RESPONSE_HELPER_PLAN_2026-05-26.md`
- report: `docs/reports/NATIVE_INIT_V889_ESOC_CONDITIONAL_RESPONSE_HELPER_BUILD_2026-05-26.md`
- helper source: `stage3/linux_init/helpers/a90_android_execns_probe.c`
- evidence:
  - `tmp/wifi/v889-execns-helper-v141-build/manifest.json`
  - `tmp/wifi/v889-execns-helper-v141-build/build.log`
  - `tmp/wifi/v889-execns-helper-v141-build/a90_android_execns_probe`
- decision: `v889-helper-v141-build-pass`
- result: source/build-only PASS. Helper `v141` adds fail-closed conditional
  response mode and allow flag. It prepares `ESOC_IMG_XFER_DONE` first,
  `ESOC_GET_STATUS` polling, and status-gated `ESOC_BOOT_DONE`.
- build: sha256
  `e6909cbfee79a4a1f55a3f039cdc29dca57f31e00c19d63a1a452d633c060f21`, static
  ARM64, no dynamic section.
- hard gates held: no helper deploy, no device contact, no live eSoC ioctl, no
  `/dev/subsys_esoc0` open, no `ESOC_NOTIFY`, no actor start, no
  service-manager, no Wi-Fi HAL, scan/connect, DHCP/routes, credentials, or
  external ping.
- next: V890 helper `v141` deploy-only checksum/version/mode proof.

### V890. Helper v141 Deploy-only Proof

- plan: `docs/plans/NATIVE_INIT_V890_HELPER_V141_DEPLOY_PLAN_2026-05-26.md`
- report: `docs/reports/NATIVE_INIT_V890_HELPER_V141_DEPLOY_2026-05-26.md`
- deploy wrapper: `scripts/revalidation/wifi_execns_helper_v141_deploy_preflight.py`
- evidence:
  - `tmp/wifi/v890-execns-helper-v141-plan/manifest.json`
  - `tmp/wifi/v890-execns-helper-v141-preflight/manifest.json`
  - `tmp/wifi/v890-execns-helper-v141-deploy-preflight/manifest.json`
- decision: `execns-helper-v141-deploy-pass`
- result: deploy-only PASS. Helper `v141` was installed by serial transfer and
  remote sha/mode marker matched.
- hard gates held: no live eSoC ioctl, no `/dev/subsys_esoc0` open, no
  `ESOC_NOTIFY`, no actor start, no service-manager, no Wi-Fi HAL,
  scan/connect, DHCP/routes, credentials, or external ping.
- next: V891 bounded conditional response proof using helper `v141`.

### V891. eSoC Conditional Response Proof

- plan: `docs/plans/NATIVE_INIT_V891_ESOC_CONDITIONAL_RESPONSE_PROOF_PLAN_2026-05-26.md`
- report: `docs/reports/NATIVE_INIT_V891_ESOC_CONDITIONAL_RESPONSE_PROOF_2026-05-26.md`
- runner: `scripts/revalidation/native_wifi_esoc_conditional_response_v891.py`
- evidence:
  - `tmp/wifi/v891-esoc-conditional-response-plan/manifest.json`
  - `tmp/wifi/v891-esoc-conditional-response-live/manifest.json`
  - `tmp/wifi/v891-esoc-conditional-response-live-v142/manifest.json`
- decision: `v891-img-xfer-done-sent-status-not-ready-reboot-cleaned`
- result: bounded live proof PASS after V892 helper repair. `ESOC_REQ_IMG`
  was observed, `ESOC_IMG_XFER_DONE` was sent with rc `0`, and
  `ESOC_GET_STATUS` stayed value `0` for 87 polls. `ESOC_BOOT_DONE` was not
  attempted.
- cleanup: helper child remained unkillable, recovery reboot executed, and
  post-reboot `bootstatus` plus `selftest fail=0` passed.
- hard gates held: no `REG_CMD_ENG`, direct userspace `CMD_EXE`, explicit
  userspace `PWR_ON`, blind `ESOC_BOOT_DONE`, actor start, service-manager,
  Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, module
  load/unload, boot image write, partition write, firmware mutation, or Wi-Fi
  link-up.
- next: V893 post-image-done readiness classifier.

### V892. Helper v142 Allowlist Repair and Deploy

- plan: `docs/plans/NATIVE_INIT_V892_HELPER_V142_ALLOWLIST_DEPLOY_PLAN_2026-05-26.md`
- report: `docs/reports/NATIVE_INIT_V892_HELPER_V142_ALLOWLIST_DEPLOY_2026-05-26.md`
- deploy wrapper: `scripts/revalidation/wifi_execns_helper_v142_deploy_preflight.py`
- evidence:
  - `tmp/wifi/v892-execns-helper-v142-build/manifest.json`
  - `tmp/wifi/v892-execns-helper-v142-plan/manifest.json`
  - `tmp/wifi/v892-execns-helper-v142-preflight/manifest.json`
  - `tmp/wifi/v892-execns-helper-v142-deploy-preflight/manifest.json`
- decision: `execns-helper-v142-deploy-pass`
- result: helper `v142` adds conditional response mode to the global v235
  allowlist and deploys cleanly.
- hard gates held: deploy-only helper replacement; no live eSoC ioctl,
  subsystem open, actor start, service-manager, Wi-Fi HAL, scan/connect,
  credentials, DHCP/routes, external ping, reboot, or Wi-Fi bring-up.

### V893. Post Image-done Readiness Classifier

- plan: `docs/plans/NATIVE_INIT_V893_ESOC_POST_IMG_XFER_CLASSIFIER_PLAN_2026-05-26.md`
- report: `docs/reports/NATIVE_INIT_V893_ESOC_POST_IMG_XFER_CLASSIFIER_2026-05-26.md`
- classifier: `scripts/revalidation/native_wifi_esoc_post_img_xfer_classifier_v893.py`
- evidence:
  - `tmp/wifi/v893-esoc-post-img-xfer-classifier/manifest.json`
- decision: `v893-post-img-xfer-status-line-classified`
- result: host-only PASS. V891 showed `ESOC_IMG_XFER_DONE` sent and
  `ESOC_GET_STATUS` value `0`; source shows `IMG_XFER_DONE` only schedules
  MDM2AP status checking. Readiness still depends on the MDM2AP status/ready
  transition.
- hard gates held: no device command, no live eSoC ioctl, no subsystem open,
  no `ESOC_NOTIFY`, no actor start, no Wi-Fi HAL, no scan/connect, no
  credentials, no DHCP/routes, and no external ping.
- next: V894 bounded MDM2AP status/ready observer planning.

### V894. MDM2AP Ready Surface Classifier

- plan: `docs/plans/NATIVE_INIT_V894_MDM2AP_READY_SURFACE_PLAN_2026-05-26.md`
- report: `docs/reports/NATIVE_INIT_V894_MDM2AP_READY_SURFACE_2026-05-26.md`
- classifier: `scripts/revalidation/native_wifi_mdm2ap_ready_surface_v894.py`
- evidence:
  - `tmp/wifi/v894-mdm2ap-ready-surface/manifest.json`
- decision: `v894-mdm2ap-ready-surface-classified`
- result: read-only PASS. DTS maps MDM2AP status to GPIO `142`, and current
  native `/proc/interrupts` exposes `msmgpio-dc 142 Edge mdm status`.
- source reconciliation: `mdm_subsys_powerup()` waits on `REG_REQ_ENG`, then
  the kernel executes `ESOC_PWR_ON`; `REG_CMD_ENG` is not needed for this
  initial path. V891 already observed `ESOC_REQ_IMG`, so the next gate should
  stay focused on the MDM2AP status transition rather than adding a generic
  command engine or blind request loop.
- hard gates held: no device mutation, no live eSoC ioctl, no subsystem open,
  no `ESOC_NOTIFY`, no GPIO export/write, no debugfs/sysfs write, no actor
  start, no Wi-Fi HAL, no scan/connect, no credentials, no DHCP/routes, and no
  external ping.
- next: V895 bounded `mdm status` IRQ snapshot proof around the existing
  guarded `IMG_XFER_DONE` flow.

### V895. MDM2AP IRQ Snapshot Proof

- plan: `docs/plans/NATIVE_INIT_V895_MDM2AP_IRQ_SNAPSHOT_PROOF_PLAN_2026-05-26.md`
- report: `docs/reports/NATIVE_INIT_V895_MDM2AP_IRQ_SNAPSHOT_PROOF_2026-05-26.md`
- helper source: `stage3/linux_init/helpers/a90_android_execns_probe.c`
- deploy wrapper: `scripts/revalidation/wifi_execns_helper_v143_deploy_preflight.py`
- live runner: `scripts/revalidation/native_wifi_mdm2ap_irq_snapshot_v895.py`
- evidence:
  - `tmp/wifi/v895-execns-helper-v143-build/manifest.json`
  - `tmp/wifi/v895-execns-helper-v143-deploy-safe/manifest.json`
  - `tmp/wifi/v895-mdm2ap-irq-snapshot-live/manifest.json`
- decision: `v895-mdm-status-irq-not-fired-reboot-cleaned`
- result: bounded live PASS. Helper `v143` was built/deployed, `ESOC_REQ_IMG`
  was observed, `ESOC_IMG_XFER_DONE` was sent, `ESOC_GET_STATUS` stayed `0`
  for 86 polls, and `ESOC_BOOT_DONE` was not sent.
- IRQ result: GPIO `142` `mdm status` snapshots parsed in 89 phases; count
  stayed `0` before image-done, after image-done, and throughout the polling
  window.
- cleanup: helper child was not proven stopped, recovery reboot executed, and
  post-reboot plus manual `bootstatus`/`selftest` rechecks showed fail=0.
- hard gates held: no `REG_CMD_ENG`, direct userspace `CMD_EXE`, explicit
  userspace `PWR_ON`, blind `ESOC_BOOT_DONE`, actor start, Wi-Fi HAL,
  scan/connect, credentials, DHCP/routes, external ping, module load/unload,
  boot image write, partition write, firmware mutation, GPIO/sysfs/debugfs
  write, or Wi-Fi link-up.
- next: V896 host-only Android `mdm_helper` / image-transfer contract
  classifier before any new live mutating eSoC state-machine attempt.

### V896. Android mdm_helper Image Contract Classifier

- plan: `docs/plans/NATIVE_INIT_V896_ANDROID_MDM_HELPER_IMAGE_CONTRACT_PLAN_2026-05-26.md`
- report: `docs/reports/NATIVE_INIT_V896_ANDROID_MDM_HELPER_IMAGE_CONTRACT_2026-05-26.md`
- classifier:
  `scripts/revalidation/native_wifi_android_mdm_helper_image_contract_v896.py`
- evidence:
  - `tmp/wifi/v896-android-mdm-helper-image-contract/manifest.json`
  - `tmp/wifi/v896-android-mdm-helper-image-contract/summary.md`
- decision: `v896-android-mdm-helper-image-contract-classified`
- result: host-only PASS. Existing Android V852/V853 evidence is sufficient:
  Android reaches `mdm3=ONLINE`, WLFW/BDF/`wlan0`, and GPIO 142 IRQ count `1`
  while `mdm_helper` plus `ks` hold `/dev/esoc-0`; `ks` uses the MHI pipe
  `/dev/mhi_0305_01.01.00_pipe_10`, and `pm-service` holds
  `/dev/subsys_esoc0` plus `/dev/subsys_modem`.
- contrast: V895 native sent `ESOC_IMG_XFER_DONE`, kept `GET_STATUS=0`,
  withheld `BOOT_DONE`, and saw GPIO 142 IRQ delta `0`.
- interpretation: the missing piece is Android's `mdm_helper`/`ks` MHI
  image/link contract before image-done, not a blind retry.
- hard gates held: no Android boot, ADB command, Magisk module, device contact,
  live eSoC ioctl, subsystem open, actor start, daemon start, Wi-Fi HAL,
  scan/connect, credentials, DHCP/routes, external ping, GPIO/sysfs/debugfs
  write, boot image write, or Wi-Fi bring-up.
- next: V897 host-only native `mdm_helper`/`ks` contract design and preflight
  classifier before any live actor start.

### V897. Native mdm_helper/ks Contract Design Classifier

- plan: `docs/plans/NATIVE_INIT_V897_MDM_HELPER_KS_CONTRACT_DESIGN_PLAN_2026-05-26.md`
- report: `docs/reports/NATIVE_INIT_V897_MDM_HELPER_KS_CONTRACT_DESIGN_2026-05-26.md`
- classifier:
  `scripts/revalidation/native_wifi_mdm_helper_ks_contract_design_v897.py`
- evidence:
  - `tmp/wifi/v897-mdm-helper-ks-contract-design/manifest.json`
  - `tmp/wifi/v897-mdm-helper-ks-contract-design/summary.md`
- decision: `v897-mdm-helper-ks-contract-build-needed`
- result: host-only PASS. V896/V895/V764/V855/V867 evidence shows the current
  helper has only old service-gated `mdm_helper` modes and lacks the Android
  pre-subsys `mdm_helper`/`ks` image/link contract.
- required delta: add a distinct helper mode that materializes eSoC/subsys
  nodes, starts `/vendor/bin/mdm_helper` before `/dev/subsys_esoc0` open, lets
  `mdm_helper` own `/dev/esoc-0` request handling, observes `ks` and
  `/dev/mhi_0305_01.01.00_pipe_10`, and keeps `BOOT_DONE`/HAL/scan/connect
  blocked unless readiness is proven.
- hard gates held: no device contact, Android boot, ADB command, Magisk module,
  live eSoC ioctl, subsystem open, actor start, `mdm_helper` start, `ks` start,
  daemon start, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external
  ping, GPIO/sysfs/debugfs write, boot image write, partition write, firmware
  mutation, module load/unload, or Wi-Fi link-up.
- next: V898 source/build-only helper support for a fail-closed
  `mdm_helper`/`ks` image-contract mode. Deploy and live proof remain separate
  cycles.

### V898. mdm_helper/ks Contract Helper v144 Build

- plan: `docs/plans/NATIVE_INIT_V898_MDM_HELPER_KS_CONTRACT_HELPER_PLAN_2026-05-26.md`
- report: `docs/reports/NATIVE_INIT_V898_MDM_HELPER_KS_CONTRACT_HELPER_BUILD_2026-05-26.md`
- helper source: `stage3/linux_init/helpers/a90_android_execns_probe.c`
- evidence:
  - `tmp/wifi/v898-mdm-helper-ks-contract-helper-build/manifest.json`
  - `tmp/wifi/v898-mdm-helper-ks-contract-helper-build/summary.md`
  - `tmp/wifi/v898-v897-contract-presence-validate/manifest.json`
- decision: `v898-helper-v144-build-pass`
- result: source/build-only PASS. Helper marker is now
  `a90_android_execns_probe v144`, and the artifact advertises
  `wifi-companion-mdm-helper-ks-image-contract-preflight` plus
  `--allow-mdm-helper-ks-contract-preflight`.
- contract added: materialize eSoC/subsys nodes, start
  `/vendor/bin/mdm_helper` before `/dev/subsys_esoc0` open, do not
  `REG_REQ_ENG`/`ESOC_NOTIFY`/`BOOT_DONE` from the controller, observe
  `/vendor/bin/ks` and `/dev/mhi_0305_01.01.00_pipe_10`, and classify unsafe
  cleanup as reboot-required.
- build: static AArch64 ELF, no dynamic section, sha256
  `c7b02320f143f57a837b5f1cf8af17258307439be3b8969dc33000735116ce4e`.
- hard gates held: no deploy, no new live device action, no live eSoC ioctl,
  no `/dev/subsys_esoc0` open, no `mdm_helper`/`ks` start, no live notify or
  `BOOT_DONE`, no service-manager, CNSS daemon, Wi-Fi HAL, scan/connect,
  credentials, DHCP/routes, external ping, boot image write, partition write,
  firmware mutation, GPIO/sysfs/debugfs write, module load/unload, reboot, or
  Wi-Fi link-up.
- next: V899 deploy-only helper `v144` checksum/version/mode parity. First
  live contract execution remains a separate bounded cycle.

### V899. Helper v144 Deploy-only Parity

- plan: `docs/plans/NATIVE_INIT_V899_HELPER_V144_DEPLOY_PLAN_2026-05-26.md`
- report: `docs/reports/NATIVE_INIT_V899_HELPER_V144_DEPLOY_2026-05-26.md`
- deploy wrapper: `scripts/revalidation/wifi_execns_helper_v144_deploy_preflight.py`
- evidence:
  - `tmp/wifi/v899-execns-helper-v144-deploy-preflight/manifest.json`
  - `tmp/wifi/v899-execns-helper-v144-postdeploy-preflight/manifest.json`
- decision: `execns-helper-v144-deploy-pass`
- result: deploy-only PASS. Helper `v144` is installed at
  `/cache/bin/a90_android_execns_probe`; postdeploy preflight shows remote sha
  and mode marker match.
- transfer: serial appendfile/uudecode, `788` chunks, `1456699` encoded bytes,
  max cmdv1 line `3890` under safe limit `3968`.
- remote sha256:
  `c7b02320f143f57a837b5f1cf8af17258307439be3b8969dc33000735116ce4e`.
- health: post-deploy `selftest fail=0`, service-manager process surface clean,
  Wi-Fi link surface clean, and manual `bootstatus` OK.
- hard gates held: no live eSoC ioctl, no `/dev/subsys_esoc0` open, no
  `REG_REQ_ENG`, `ESOC_NOTIFY`, `BOOT_DONE`, `mdm_helper` start, `ks` start,
  service-manager, CNSS daemon, Wi-Fi HAL, scan/connect, credentials,
  DHCP/routes, external ping, boot image write, partition write, firmware
  mutation, GPIO/sysfs/debugfs write, module load/unload, reboot, or Wi-Fi
  link-up.
- next: V900 bounded live `mdm_helper`/`ks` contract proof. Wi-Fi HAL,
  scan/connect, credentials, DHCP/routes, and external ping remain blocked.

### V900. mdm_helper/ks Contract Live Proof

- plan: `docs/plans/NATIVE_INIT_V900_MDM_HELPER_KS_CONTRACT_LIVE_PLAN_2026-05-26.md`
- report: `docs/reports/NATIVE_INIT_V900_MDM_HELPER_KS_CONTRACT_LIVE_2026-05-26.md`
- runner: `scripts/revalidation/native_wifi_mdm_helper_ks_contract_live_v900.py`
- evidence:
  - `tmp/wifi/v900-mdm-helper-ks-contract-live/manifest.json`
- decision: `v900-reboot-required-cleaned`
- result: repaired helper `v145` starts `/vendor/bin/mdm_helper`, then attempts
  `/dev/subsys_esoc0` only after `mdm_helper_observable=1`. The trigger blocks,
  no `ks`/MHI/GPIO142/`mdm3=ONLINE`/WLFW/BDF/`wlan0` progress appears, and
  cleanup reboot restores native health.
- next: V902 blocker capture before any repeat of the same subsystem-open path.

### V902. mdm_helper/ks Blocker Capture

- plan: `docs/plans/NATIVE_INIT_V902_MDM_HELPER_KS_BLOCKER_CAPTURE_PLAN_2026-05-26.md`
- report: `docs/reports/NATIVE_INIT_V902_MDM_HELPER_KS_BLOCKER_CAPTURE_2026-05-26.md`
- runner: `scripts/revalidation/native_wifi_mdm_helper_ks_blocker_capture_v902.py`
- evidence:
  - `tmp/wifi/v902-mdm-helper-ks-blocker-capture-live/manifest.json`
- decision: `v902-reboot-required-cleaned`
- result: helper `v146` captures blocked trigger evidence:
  `wchan=mdm_subsys_powerup`, D-state, stack
  `mdm_subsys_powerup -> __subsystem_get -> subsys_device_open -> ... ->
  SyS_openat`. Native `mdm_helper` itself did not hold `/dev/esoc-0`.
- next: V903 `mdm_helper`-only deep capture with no `/dev/subsys_esoc0` open.

### V903. mdm_helper-only Deep Capture

- plan: `docs/plans/NATIVE_INIT_V903_MDM_HELPER_ONLY_DEEP_CAPTURE_PLAN_2026-05-26.md`
- report: `docs/reports/NATIVE_INIT_V903_MDM_HELPER_ONLY_DEEP_CAPTURE_2026-05-26.md`
- deploy wrapper:
  `scripts/revalidation/wifi_execns_helper_v147_deploy_preflight.py`
- runner:
  `scripts/revalidation/native_wifi_mdm_helper_only_deep_capture_v903.py`
- evidence:
  - `tmp/wifi/v903-execns-helper-v147-build/a90_android_execns_probe`
  - `tmp/wifi/v903-execns-helper-v147-deploy-preflight/manifest.json`
  - `tmp/wifi/v903-mdm-helper-only-deep-capture-live/manifest.json`
- decision: `v903-mdm-helper-no-esoc-fd`
- result: helper `v147` starts `/vendor/bin/mdm_helper` only. It is observable,
  but holds no `/dev/esoc-0`, `/dev/subsys_esoc0`, or MHI pipe fd, spawns no
  `/vendor/bin/ks`, and postflight is clean without reboot.
- next: V904 Android/native `mdm_helper` runtime-input parity classifier before
  any new subsystem-open retry.

### V904. mdm_helper Runtime Input Parity

- plan: `docs/plans/NATIVE_INIT_V904_MDM_HELPER_RUNTIME_INPUT_PARITY_PLAN_2026-05-26.md`
- report: `docs/reports/NATIVE_INIT_V904_MDM_HELPER_RUNTIME_INPUT_PARITY_2026-05-26.md`
- classifier:
  `scripts/revalidation/native_wifi_mdm_helper_runtime_input_parity_v904.py`
- evidence:
  - `tmp/wifi/v904-mdm-helper-runtime-input-parity/manifest.json`
  - `tmp/wifi/v904-mdm-helper-runtime-input-parity/summary.md`
- decision: `v904-mdm-helper-runtime-input-parity-classified`
- result: host-only PASS. Android `mdm_helper` is init-managed as
  `u:r:vendor_mdm_helper:s0`, after `vendor.per_mgr=running`, with
  `pm-service` holding subsystem nodes and `mdm_helper`/`ks` reaching
  `/dev/esoc-0`/MHI. Native V903 starts `mdm_helper` directly in `kernel`
  context and never reaches the eSoC/MHI path.
- next: V905 fail-closed runtime-input repair design; do not retry
  `/dev/subsys_esoc0` before modelling missing init/SELinux/per_mgr/property
  context.

### V1046. Android /vendor/etc/init/ RC Capture

- report: `docs/reports/NATIVE_INIT_V1046_ANDROID_VENDOR_INIT_RC_CAPTURE_2026-05-26.md`
- script: `scripts/revalidation/android_vendor_init_rc_handoff_v1046.py`
- evidence: `tmp/wifi/v1046-android-vendor-init-rc-handoff/manifest.json`
- decision: `v1046-android-vendor-init-rc-partial`
- result: Android boot RC capture PASS. All PM/eSoC actor definitions are in
  `/vendor/etc/init/hw/init.target.rc`; `pm_proxy_helper.rc` is a separate file.
  `vendor.mdm_helper` is disabled; starts only via `vendor.mdm_launcher` →
  `init.mdm.sh` → `ro.baseband=mdm` check. `ks` has no RC entry, spawned
  directly by `mdm_helper`. Native rollback to v724 verified.
- next: V1047 source/build-only — add subsys_modem holder before pm_proxy_helper.

### V1047. PM Full Contract with Modem Holder — Source/Build-Only

- report: `docs/reports/NATIVE_INIT_V1047_PM_FULL_CONTRACT_WITH_MODEM_HOLDER_SOURCE_BUILD_2026-05-26.md`
- helper: `stage3/linux_init/helpers/a90_android_execns_probe.c` (v177 → v178)
- decision: `v1047-pm-full-contract-with-modem-holder-source-build-pass`
- result: source/build PASS. New order value
  `after-mdm-helper-esoc-fd-with-pm-full-contract-with-modem-holder` and allow
  flag `--allow-pm-full-contract-with-modem-holder` added. Helper forks a modem
  pre-holder child that opens `/dev/subsys_modem` (PIL boot) before
  `pm_proxy_helper`, mirroring Android's pm-service → pm_proxy_helper ordering.
  Binary: sha256 `7df75c618f58d599ece1a6017f66040aff57badb8955a70e07de2a77a3561c75`,
  size 1336728, static aarch64, no dynamic section.
- next: V1048 deploy-only preflight, then V1049 bounded live gate.

### V1176. PM State-3 Dependency Classifier

- report: `docs/reports/NATIVE_INIT_V1176_PM_STATE3_DEPENDENCY_CLASSIFIER_2026-05-27.md`
- classifier: `scripts/revalidation/native_wifi_pm_state3_dependency_classifier_v1176.py`
- evidence: `tmp/wifi/v1176-pm-state3-dependency-classifier/manifest.json`
- decision: `v1176-dependency-flag-state-order-gap-classified`
- result: host-only PASS. V1175 confirmed state-2 opens `/dev/subsys_modem` (not
  esoc0) because `dependency_flag=0`. Disassembly confirms: zero dependency flag
  at `[x20,#320]` skips dependency branch; state-3 falls through to return
  (no-op); state-0 path contains a dependency flag setter and state-1 transition.
  State-0 arrives ~15.99s after state-2.
- next: V1177 live trace of PM dependency flag setter path.

### V1177. PM Dependency Flag Live

- report: `docs/reports/NATIVE_INIT_V1177_PM_DEPENDENCY_FLAG_LIVE_2026-05-27.md`
- classifier: `scripts/revalidation/native_wifi_pm_dependency_flag_live_v1177.py`
- evidence: `tmp/wifi/v1177-pm-dependency-flag-live-after-v490/manifest.json`
- decision: `v1177-dependency-flag-not-armed`
- result: live PASS. Native state order `[2, 3, 0, 1]`. State-2 sees
  `dependency_flag=0` → skips esoc0 → opens `/dev/subsys_modem`. State-3 is a
  no-op. State-0 arrives at t=1009.93s (gap=15.99s from state-2 at t=993.94s);
  state-0 dep at `peripheral+0x40` is already `state=1` → flag-set path never
  reached. Two distinct dependency objects: state-2 dep at `peripheral-0x180`,
  state-0 dep at `peripheral+0x40`.
- next: V1178 PM dependency init/order parity classifier.

### V1178. PM Dependency Init Classifier

- report: `docs/reports/NATIVE_INIT_V1178_PM_DEPENDENCY_INIT_CLASSIFIER_2026-05-28.md`
- classifier: `scripts/revalidation/native_wifi_pm_dependency_init_classifier_v1178.py`
- evidence: `tmp/wifi/v1178-pm-dependency-init-classifier/manifest.json`
- decision: `v1178-pm-dep-init-order-gap-classified`
- result: host-only PASS. Root cause: native starts `per_proxy` late (after
  `mdm_helper` acquires `/dev/esoc-0`), by which time per_proxy_helper's PM
  state machine has already completed and the dep at `peripheral+0x40` is
  `state=1`. Android starts `per_proxy` within ~2.16s of `per_proxy_helper`
  (8.824s − 6.666s), so when the parent peripheral's `state-0` arrives the dep
  is still `state<1` and the flag-set path runs. The fix: start `per_proxy`
  before per_proxy_helper's state machine completes, independently of the
  `mdm_helper` esoc-0 gate.
- next: V1179 — arm uprobes before per_proxy_helper/per_proxy/pm-service startup
  to catch the dep transition from state=0 to state=1 and prove that early
  per_proxy start keeps the dep in state=0 when parent state-0 is processed.
  Keep Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, boot
  image write, partition write, and flash blocked.

### V1179. PM Dep Early Per-Proxy Observer

- script: `scripts/revalidation/native_wifi_pm_dep_early_per_proxy_observer_v1179.py`
- result: live PASS (two attempts). `EARLY_PER_PROXY_PPH_DELTA_MS=2159ms` (attempt 1)
  and `800ms` (attempt 2) both reach `decision: v1179-per-mgr-probe-wait-delays-per-proxy-too-late`.
  Root cause: helper per_mgr post-start probe wait is 1000ms; even with target_delta=800ms,
  `already_elapsed=1` because probe_wait(1000ms) > target_delta(800ms), pushing actual
  per_proxy start to pph+1244ms — 244ms after per_mgr has already exited.
  Per_mgr exits cleanly (exit_code=0) within ~600-800ms because pm-service times out with
  no initial clients (pm_proxy_helper vndbinder fd count=0). State machine never fires:
  `state_set_event_count=0`, `pm_proxy_helper_vndbinder_count=0`.
- next: V1180 — helper v219 with per_mgr probe_wait=0ms and per_proxy pph_delta ~300ms.
  Per_mgr starts at pph+177ms; per_proxy at pph+300ms should connect while pm-service
  is still alive (before ~500-800ms init timeout). Modem pm-proxy at pph+1254ms then
  drives dep state=1 after per_proxy is already connected.
  Keep Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, boot image
  write, partition write, and flash blocked.

### V1199. ESOC IMG_XFER_DONE + MHI Observe (Option B)

- script: `scripts/revalidation/native_wifi_esoc_img_xfer_mhi_observe_v1199.py`
- helper: `stage3/linux_init/helpers/a90_android_execns_probe.c` (v238)
- decision: `v1199-mhi-not-appeared-after-img-xfer-done`
- result: live PASS. ESOC_IMG_XFER_DONE sent; MHI devices did not appear.
  SDX50M requires actual firmware bytes via ks/MHI pipe, not just IMG_XFER_DONE signal.
- next: V1200 Option A — mdm_helper SELinux context repair.

### V1200/V1201. PM Observer: mdm_helper SELinux Context Repair

- script: `scripts/revalidation/native_wifi_pm_mdm_helper_selinux_context_v1200.py`
- helper: `stage3/linux_init/helpers/a90_android_execns_probe.c` (v239→v241)
- decision: `v1200-mdm-helper-has-esoc0-fd-no-mhi`
- result: live PASS. mdm_helper runs as `u:r:vendor_mdm_helper:s0`, holds
  `/dev/esoc-0` (chroot path confirmed), receives ESOC_REQ_IMG at t=0, then
  enters 10s SyS_nanosleep retry loop. ks_count=0, mhi_dev_count=0 throughout 100s.
  v241 fixed fd filter (chroot path artifact) and added ks_count scan.
- next: V1202 — root cause: PCIe link training failure.

### V1202. mdm_helper Binary Strings + PCIe/MHI Idle Surface Classifier

- script: `scripts/revalidation/native_wifi_mdm_helper_binary_pcie_surface_v1202.py`
- deploy: `scripts/revalidation/wifi_execns_helper_v242_deploy_preflight_v1202.py`
- helper: `stage3/linux_init/helpers/a90_android_execns_probe.c` (v242)
  SHA256: `affc335d580bbb016c651b19d44998ec755e9471fd2fff1ae7784c63861fe3fc`
- decision: expected `v1202-pcie-link-training-blocker-classified`
- v242 new status fields: `pcie_link_state`, `pci_dev_count`, `mhi_bus_count`
- next: V1203 live gate with PCIe monitoring.

### V1203. PM Observer: PCIe LTSSM + MHI Bus Count Monitoring

- script: `scripts/revalidation/native_wifi_pm_mdm_pcie_observe_v1203.py`
- helper: `a90_android_execns_probe v242`
  SHA256: `affc335d580bbb016c651b19d44998ec755e9471fd2fff1ae7784c63861fe3fc`
- decision: `v1203-pcie-link-training-failed`
- result: live PASS. pcie_link_state=absent, pci_dev_count=0, mhi_bus_count=0
  throughout 10 status entries (0–90s). mdm_helper holds esoc-0 as
  `u:r:vendor_mdm_helper:s0`, GPIO 142 stays 0, mdm3 stays OFFLINING.
  PCIe link training failure definitively confirmed: after sdx50m_toggle_soft_reset,
  /sys/devices/platform/soc/1c08000.qcom,pcie/current_link_state stays absent,
  no MDM endpoint on PCIe bus, no MHI bus devices, no ks spawn.
  selftest pass=11 fail=0 after cleanup reboot.
- root cause: PCIe PERST# / power not managed by PM framework when trigger
  child opens subsys_esoc0 directly (bypassing pm-service state machine).
- next: V1204 — PM dependency_flag=1 fix: per_proxy timing so pm-service
  opens subsys_esoc0 via proper PCIe-resourced path (state-2 with dep flag=1).
  Keep Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping blocked.

### V1204. PM Dep per_proxy Late Start (pph+20s)

- script: `scripts/revalidation/native_wifi_pm_dep_per_proxy_late_start_v1204.py`
- helper: `a90_android_execns_probe v242`
- decision: `v1203-pcie-link-training-failed` (false vndservice-gate check; actual data present)
- result: live PASS (evidence captured). per_proxy started at pph+20000ms (after state-0 at
  pph+15.99s per V1177). pm-service STILL opened subsys_modem (not esoc0). PCIe still absent
  (pci_dev_count=0, mhi_bus_count=0, pcie_link_state=absent). Dep state tracefs events NOT
  captured (state-0 dep path may not have run or trace buffer overflow). selftest pass=11 fail=0.
- root cause: dep_flag per_proxy timing approach is INEFFECTIVE — pm-service opens modem
  regardless of when per_proxy starts. dep_flag mechanism either doesn't apply to native
  pm-service, or a different client is needed to trigger esoc0 open.
- new hypothesis: In Android V853, pm-service holds BOTH /dev/subsys_esoc0 AND
  /dev/subsys_modem. The esoc0 open may be triggered by a SECOND PM client (cnss-daemon?
  or other) registering for the MDM3/eSoC peripheral, not by the dep_flag state-2 path.
- next: V1205 host-only — identify what PM client triggers pm-service to open subsys_esoc0
  in Android V853 evidence. Focus on pm_client_connect call pattern for MDM3/eSoC
  peripheral vs modem peripheral. Check if cnss-daemon or mdm_helper makes this call.

## V1221 Private CNSS Daemon SDX50M Live Gate (2026-05-31)

- helper: `a90_android_execns_probe v253`
- helper deploy: `tmp/wifi/v1221-execns-helper-v253-deploy/manifest.json`
- artifact deploy: `tmp/wifi/v1221-cnss-daemon-sdx50m-artifact-deploy/manifest.json`
- live evidence: `tmp/wifi/v1221-private-cnss-daemon-sdx50m-live/manifest.json`
- report: `docs/reports/NATIVE_INIT_V1221_PRIVATE_CNSS_DAEMON_SDX50M_LIVE_2026-05-31.md`
- result: `v1221-sdx50m-per-mgr-esoc0`, pass `true`.
- finding: private `/cache/bin/cnss-daemon.sdx50m` bind-mounted over `/vendor/bin/cnss-daemon` in the helper namespace (`bind_rc=0`), CNSS registered both `modem` and `SDX50M`, and dmesg showed `pm-service` reaching `__subsystem_get(): esoc0 count:0` plus `Changing subsys fw_name to esoc0`.
- current blocker: eSoC subsystem power-up starts but does not complete; `mdm3` remains `OFFLINING`, WLFW service 69/BDF/FW-ready/`wlan0` are still absent.
- safety: no Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, boot image write, or vendor partition write. `cnss-daemon` start was intentional for this gate.
- next: V1222 should focus on the post-`subsys_esoc0` power-up boundary: MDM down/crash markers, `mdm3` transitions, WLFW service 69, BDF, and `wlan0`. Keep Wi-Fi HAL and connect/ping gates blocked until lower readiness is proven.

## V1222 Post-eSoC Power Boundary Live Gate (2026-05-31)

- runner: `scripts/revalidation/native_wifi_post_esoc_power_boundary_v1222.py`
- evidence: `tmp/wifi/v1222-post-esoc-power-boundary-live/manifest.json`
- report: `docs/reports/NATIVE_INIT_V1222_POST_ESOC_POWER_BOUNDARY_2026-05-31.md`
- result: `v1222-esoc-powerup-crash-before-wlfw`, pass `true`.
- finding: V1221's private CNSS `SDX50M` path still reaches `/dev/subsys_esoc0`; V1222 held the observer open for 46 post-hold samples and confirmed `pm-service` stays in `mdm_subsys_powerup`, `mdm3` remains `OFFLINING`, modem-down/crash marker count rises to `4`, and WLFW/BDF/`wlan0` markers remain `0`.
- current blocker: the lower SDX50M power-up/firmware/MHI handoff fails before WLFW publication. CNSS selection and PM eSoC routing are no longer the primary blocker.
- safety: no Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, boot image write, or vendor partition write. `cnss-daemon` start was intentional for this gate.
- next: V1223 should classify why Android's post-`subsys_esoc0` path reaches `mdm_helper` `/dev/esoc-0`, `ks`, MHI pipe, WLFW/BDF/`wlan0`, while native V1222 crashes/stalls before WLFW. Keep Wi-Fi HAL and connect/ping gates blocked until lower readiness is proven.

## V1223 SDX50M Crash Source Classifier (2026-05-31)

- runner: `scripts/revalidation/native_wifi_sdx50m_crash_source_classifier_v1223.py`
- evidence: `tmp/wifi/v1223-sdx50m-crash-source-classifier/manifest.json`
- report: `docs/reports/NATIVE_INIT_V1223_SDX50M_CRASH_SOURCE_CLASSIFIER_2026-05-31.md`
- result: `v1223-sdx50m-crash-source-contract-gap-classified`, pass `true`.
- finding: V1222 already repairs the CNSS/PM selection branch enough to reach `/dev/subsys_esoc0`; the post-open failure is a lower SDX50M image-link/lifetime gap. Android success requires init-managed `vendor_mdm_helper` owning `/dev/esoc-0`, `ks` reaching `/dev/mhi_0305_01.01.00_pipe_10`, and `pm-service` owning subsystem nodes. Direct native `mdm_helper` evidence lacked `/dev/esoc-0`, `ks`, and MHI pipe surface.
- safety: host-only classifier; no device contact, live daemon start, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, boot image write, or partition write.
- next: V1224 should run a bounded live parity gate that proves `mdm_helper` owns `/dev/esoc-0` and `ks`/MHI appears before or while `pm-service` opens `/dev/subsys_esoc0`. Keep Wi-Fi HAL and connect/ping gates blocked until WLFW/BDF/`wlan0` readiness is proven.

## V1224 mdm_helper / ks / MHI Parity Live Gate (2026-05-31)

- runner: `scripts/revalidation/native_wifi_mdm_helper_ks_mhi_parity_live_v1224.py`
- evidence: `tmp/wifi/v1224-mdm-helper-ks-mhi-parity-live/manifest.json`
- report: `docs/reports/NATIVE_INIT_V1224_MDM_HELPER_KS_MHI_PARITY_LIVE_2026-05-31.md`
- result: `v1224-mdm-helper-esoc-present-ks-mhi-absent-crash`, pass `true`.
- finding: the native path now proves `mdm_helper` owns `/dev/esoc-0` and `pm-service` attempts `/dev/subsys_esoc0`, but `ks` and `/dev/mhi_0305_01.01.00_pipe_10` never appear before modem-down/crash markers. `mdm3` remains `OFFLINING`, WLFW/BDF/`wlan0` markers remain `0`.
- postflight: selftest `pass=11 warn=1 fail=0`, netservice stopped, and no PM/CNSS/`mdm_helper`/`ks` actors remained in `ps`.
- safety: no Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, boot image write, flash, or partition write.
- next: V1225 should classify why native `mdm_helper` remains before Android's `ks`/MHI image-transfer path. Focus on `mdm_helper` eSoC ioctl/wchan, MHI device creation, and Android timing around `ESOC_WAIT_FOR_REQ`, PCIe/MHI readiness, and `ks` spawn.

## V1225 mdm_helper WAIT_FOR_REQ Gap Classifier (2026-05-31)

- runner: `scripts/revalidation/native_wifi_mdm_helper_wait_req_gap_classifier_v1225.py`
- evidence: `tmp/wifi/v1225-mdm-helper-wait-req-gap-classifier/manifest.json`
- report: `docs/reports/NATIVE_INIT_V1225_MDM_HELPER_WAIT_REQ_GAP_CLASSIFIER_2026-05-31.md`
- result: `v1225-mdm-helper-post-wait-sleep-gap-classified`, pass `true`.
- finding: V1224 did not merely lack `mdm_helper` visibility; lower trace shows `mdm_helper` threads in `SyS_nanosleep`, with `/dev/esoc-0` held but no `ks`, MHI pipe, WLFW/BDF/FW-ready, or `wlan0`. V911/V1144 keep `ESOC_WAIT_FOR_REQ` as the earlier request-engine boundary, so the current gap is the post-wait sleep/no-MHI branch.
- safety: host-only classifier; no device command, live eSoC ioctl, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, boot image write, flash, or partition write.
- next: V1226 should add a bounded lower-trace v2 live gate in the V1224 PM/CNSS path: trace `mdm_helper` syscall/returns from process start, capture the `ESOC_WAIT_FOR_REQ` result and subsequent open/exec/ioctl errors, and poll `/dev/mhi_0305_01.01.00_pipe_10`, `/sys/bus/mhi/devices`, PCIe link state, and `/vendor/bin/ks` before/after `pm-service` opens `/dev/subsys_esoc0`.

## V1226 mdm_helper Lower Trace v2 Live Gate (2026-05-31)

- runner: `scripts/revalidation/native_wifi_mdm_helper_lower_trace_v2_live_v1226.py`
- evidence: `tmp/wifi/v1226-mdm-helper-lower-trace-v2-live/manifest.json`
- report: `docs/reports/NATIVE_INIT_V1226_MDM_HELPER_LOWER_TRACE_V2_LIVE_2026-05-31.md`
- result: `v1226-ptrace-lite-perturbed-mdm-helper-window`, pass `true`.
- finding: forcing the existing broad `ptrace-lite` capture onto the V1224
  PM/CNSS path changes the observed path before the target lower boundary.
  `mdm_helper` starts but is not observable in the post-PM window,
  `pm-service` never attempts `/dev/subsys_esoc0`, `per_mgr` syscall tracing
  reaches the stop limit, and no `mdm_helper` syscall or `ESOC_WAIT_FOR_REQ`
  records are captured.
- interpretation: V1226 is a valid instrumentation-blocker classification, not
  lower-Wi-Fi progress. V1224 remains the better behavioral baseline.
- safety: no Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping,
  boot image write, flash, or partition write. Postflight selftest remained
  fail0 and netservice was stopped.
- next: V1227 should implement focused `mdm_helper`-only tracing or compact
  helper-side eSoC event markers for `/dev/esoc-0` and `ESOC_WAIT_FOR_REQ`,
  without tracing earlier PM actors or perturbing the V1224 path.

## V1227 mdm_helper Focused Trace Live Gate (2026-05-31)

- helper: `a90_android_execns_probe v254`
- helper source: `stage3/linux_init/helpers/a90_android_execns_probe.c`
- deploy wrapper: `scripts/revalidation/wifi_execns_helper_v254_deploy_preflight_v1227.py`
- live runner: `scripts/revalidation/native_wifi_mdm_helper_focused_trace_live_v1227.py`
- report: `docs/reports/NATIVE_INIT_V1227_MDM_HELPER_FOCUSED_TRACE_LIVE_2026-05-31.md`
- result: `v1227-focused-ptrace-stops-mdm-helper-before-esoc`, pass `true`.
- finding: v254 adds `--pm-observer-mdm-helper-only-syscall-trace`, and V1227
  proves this disables earlier `per_mgr` syscall tracing while tracing
  `mdm_helper`. However, pre-gate ptrace still stops `mdm_helper` before
  `/dev/esoc-0` opens. The observer sees `ptrace_stop`, `fd_esoc0_count=0`, no
  selected syscall records, no `ESOC_WAIT_FOR_REQ`, no `ks`/MHI, and no
  WLFW/`wlan0`.
- interpretation: broad tracing was narrowed successfully, but pre-gate ptrace
  itself is incompatible with the existing `/dev/esoc-0` readiness gate.
- safety: no Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping,
  boot image write, flash, or partition write. Postflight selftest remained
  fail0 and netservice was stopped.
- next: V1228 should avoid pre-gate ptrace. Use delayed attach after
  `/dev/esoc-0` appears, or compact non-ptrace helper-side event capture around
  `mdm_helper` eSoC request/response state.

## V1228 mdm_helper Early Compact Trace Live Gate (2026-05-31)

- helper: `a90_android_execns_probe v255`
- helper source: `stage3/linux_init/helpers/a90_android_execns_probe.c`
- deploy wrapper: `scripts/revalidation/wifi_execns_helper_v255_deploy_preflight_v1228.py`
- live runner: `scripts/revalidation/native_wifi_mdm_helper_early_compact_trace_live_v1228.py`
- evidence: `tmp/wifi/v1228-mdm-helper-early-compact-trace-live/manifest.json`
- report: `docs/reports/NATIVE_INIT_V1228_MDM_HELPER_EARLY_COMPACT_TRACE_LIVE_2026-05-31.md`
- result: `v1228-early-wait-for-req-observed-no-ks-mhi`, pass `true`.
- finding: v255 avoids pre-gate ptrace and samples the existing V1224 path via
  read-only `/proc` inspection. The early compact trace proves `mdm_helper`
  owns `/dev/esoc-0` and is blocked in `ioctl(ESOC_WAIT_FOR_REQ)` with
  `wchan=esoc_dev_ioctl`; `pm-service` still attempts `/dev/subsys_esoc0`, but
  `ks`, `/dev/mhi_0305_01.01.00_pipe_10`, WLFW/BDF/FW-ready, and `wlan0` remain
  absent before modem-down/crash markers.
- interpretation: the active blocker is now the ESOC request/image-link handoff
  after `ESOC_WAIT_FOR_REQ`, not `mdm_helper` launch, `/dev/esoc-0` ownership,
  or ptrace observability.
- safety: no Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping,
  boot image write, flash, or partition write. Postflight selftest remained
  fail0 and netservice was stopped.
- next: V1229 should classify the `ESOC_WAIT_FOR_REQ` request/result contract
  and why native does not transition into Android's `ks`/MHI transfer path.

## V1229 ESOC WAIT_FOR_REQ / ks-MHI Contract Classifier (2026-05-31)

- runner: `scripts/revalidation/native_wifi_esoc_wait_req_ks_mhi_contract_v1229.py`
- evidence: `tmp/wifi/v1229-esoc-wait-req-ks-mhi-contract/manifest.json`
- report: `docs/reports/NATIVE_INIT_V1229_ESOC_WAIT_REQ_KS_MHI_CONTRACT_2026-05-31.md`
- result: `v1229-esoc-wait-req-ks-mhi-contract-classified`, pass `true`.
- finding: V1228 proves the natural native path reaches `mdm_helper` blocked
  in `ESOC_WAIT_FOR_REQ` while `pm-service` attempts `/dev/subsys_esoc0`;
  V891/V1199 prove bare `ESOC_REQ_IMG` plus `ESOC_IMG_XFER_DONE` does not create
  MHI readiness; V896 proves Android readiness includes the `mdm_helper` /
  `ks` / `/dev/mhi_0305_01.01.00_pipe_10` image-link contract.
- interpretation: the active blocker is the request/image-link handoff around
  `ks`/MHI, not eSoC request existence, bare notify response, service-manager
  expansion, or Wi-Fi HAL.
- safety: host-only classifier; no device command, live eSoC ioctl/notify,
  actor start, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping,
  boot image write, flash, or partition write.
- next: V1230 should add source/build-only support for a bounded `mdm_helper`
  request-return / `ks` observer that preserves the V1228 non-ptrace path and
  samples `/vendor/bin/ks` plus `/dev/mhi_0305_01.01.00_pipe_10` before any
  `ESOC_NOTIFY`, `ESOC_BOOT_DONE`, or Wi-Fi HAL expansion.

## V1323 Provider Wait-cause Classifier (2026-05-31)

- runner: `scripts/revalidation/native_wifi_provider_wait_cause_classifier_v1323.py`
- evidence: `tmp/wifi/v1323-provider-wait-cause-classifier/manifest.json`
- report: `docs/reports/NATIVE_INIT_V1323_PROVIDER_WAIT_CAUSE_CLASSIFIER_2026-05-31.md`
- result: `v1323-provider-wait-cause-is-proprietary-powerup-response`, pass `true`.
- finding: public Samsung OSRC `subsystem_restart.c` places the board provider
  `powerup()` before `wait_for_err_ready()`, and the staged OSRC tree does not
  contain the proprietary `mdm_subsys_powerup` body. V849/V918/V963 place the
  live native block inside that proprietary ext-mdm path with stacks including
  `sdx50m_toggle_soft_reset`, `mdm4x_do_first_power_on`, `mdm_cmd_exe`, and
  `mdm_subsys_powerup`.
- interpretation: the blocker is not public `wait_for_err_ready()` and not the
  earlier image-link/PM actor delivery gate. It is the proprietary provider
  response path after SDX50M soft-reset/AP2MDM activity and before GPIO142,
  PCIe RC1/MHI, WLFW/BDF, or `wlan0` response. Android-positive evidence proves
  those downstream responses are possible under Android.
- safety: host-only classifier; no device command, PM actor start, `mdm_helper`
  start, tracefs write, live eSoC ioctl/notify, PMIC write, GPIO line request,
  direct GDSC/eSoC write, Wi-Fi HAL start, scan/connect, credentials,
  DHCP/routes, external ping, flash, boot image write, or partition write.
- next: V1324 should classify Android-vs-native provider response deltas around
  GPIO142, errfatal, soft-reset, and PCIe timing from host/source evidence
  first. Only after that should a bounded read-only or reboot-bounded live
  sampler be designed.

## V1324 Provider Response Delta Classifier Plan (2026-05-31)

- plan: `docs/plans/NATIVE_INIT_V1324_PROVIDER_RESPONSE_DELTA_PLAN_2026-05-31.md`
- type: host/source-only classifier plan
- status: plan ready; implementation not yet run
- objective: compare Android-positive and native-negative evidence inside the
  V1323 proprietary ext-mdm provider response window, specifically after
  GPIO1270/GPIO135/AP2MDM activity and before GPIO142/MDM2AP, PCIe RC1, MHI/ks,
  WLFW/BDF, and `wlan0` response.
- required inputs: V1323, V1318, V1319, V1239, V1240, V1291, V852, V896, and the
  staged MDM3/eSoC research/source files.
- expected output: `scripts/revalidation/native_wifi_provider_response_delta_classifier_v1324.py`,
  `tmp/wifi/v1324-provider-response-delta-classifier/manifest.json`, and
  `docs/reports/NATIVE_INIT_V1324_PROVIDER_RESPONSE_DELTA_CLASSIFIER_2026-05-31.md`.
- safety: no device command, helper deploy, PM actor start, `mdm_helper`,
  tracefs write, eSoC ioctl/notify/BOOT_DONE, PMIC/GPIO/GDSC write, Wi-Fi HAL,
  scan/connect, credentials, DHCP/routes, external ping, flash, boot image write,
  or partition write.

## V1324 Provider Response Delta Classifier (2026-05-31)

- runner: `scripts/revalidation/native_wifi_provider_response_delta_classifier_v1324.py`
- evidence: `tmp/wifi/v1324-provider-response-delta-classifier/manifest.json`
- report: `docs/reports/NATIVE_INIT_V1324_PROVIDER_RESPONSE_DELTA_CLASSIFIER_2026-05-31.md`
- result: `v1324-delta-is-post-ap2mdm-mdm2ap-response-gap`, pass `true`.
- finding: existing evidence proves native reaches AP-side provider activity:
  GPIO1270 PMIC soft-reset lines, GPIO135/AP2MDM high, and GPIO141
  AP2MDM_ERRFATAL-side activity. Native still has GPIO142/MDM2AP IRQ `0`, MDM
  errfatal IRQ `0`, PCI/MHI/MHI pipe absent, WLFW/BDF absent, and `wlan0`
  absent. Android-positive V852/V896/V1239 evidence has GPIO142 IRQ, PCIe
  RC1/L0, MHI/ks, WLFW/BDF, and `wlan0`.
- interpretation: the remaining delta is a post-AP2MDM MDM2AP/PCIe response
  gap, not public `wait_for_err_ready()`, not image-link delivery, and not static
  GPIO135/GPIO142 shape.
- safety: host/source-only classifier; no device command, helper deploy, PM actor
  start, `mdm_helper`, tracefs write, live eSoC ioctl/notify, PMIC/GPIO/GDSC
  write, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping,
  flash, boot image write, or partition write.
- next: V1325 should design a small bounded read-only or reboot-bounded observer
  for GPIO142/MDM errfatal/PCIe timing, or choose Android read-only timing
  recapture if exact Android phase ordering is still required.

## V1325 GPIO142 / Errfatal / PCIe Timing Observer Plan (2026-05-31)

- plan: `docs/plans/NATIVE_INIT_V1325_GPIO142_ERRFATAL_PCIE_TIMING_OBSERVER_PLAN_2026-05-31.md`
- type: source/build design plan
- status: plan ready; implementation not yet run
- finding: V1324 closed the host/source classification as a post-AP2MDM
  MDM2AP/PCIe response gap. Existing helper v275 lower-sequence summary is close
  but does not provide compact MDM errfatal IRQ delta and first-transition timing
  fields.
- next implementation: V1326 should add helper `v276` mode
  `--pm-observer-late-per-proxy-mdm2ap-errfatal-pcie-timing-sampler` with compact
  `mdm2ap_timing.*` output fields for GPIO142 IRQ delta, MDM errfatal IRQ delta,
  PCIe RC1 transition, MHI bus/pipe, `ks`, WLFW, `wlan0`, and safety zeros.
- safety: V1325 is documentation-only; no device command, helper deploy, PM actor
  start, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping,
  PMIC/GPIO/GDSC/eSoC write, flash, boot image write, or partition write.

## V1326 MDM2AP Timing Sampler Support (2026-05-31)

- runner: `scripts/revalidation/native_wifi_mdm2ap_timing_sampler_support_v1326.py`
- evidence: `tmp/wifi/v1326-mdm2ap-timing-sampler-support/manifest.json`
- report: `docs/reports/NATIVE_INIT_V1326_MDM2AP_TIMING_SAMPLER_SUPPORT_2026-05-31.md`
- helper: `stage3/linux_init/helpers/a90_android_execns_probe_v276`
- result: `v1326-mdm2ap-timing-sampler-build-pass`, pass `true`.
- finding: helper `a90_android_execns_probe v276` adds opt-in flag
  `--pm-observer-late-per-proxy-mdm2ap-errfatal-pcie-timing-sampler`.
  The new mode emits compact aggregate `mdm2ap_timing.*` fields for GPIO142 IRQ
  delta, MDM errfatal IRQ delta, PCIe RC1 transition, MHI bus/pipe, `ks`, WLFW
  kmsg count, `wlan0`, and safety zeros.
- build: static aarch64 helper sha256
  `dad57e135d3b4f0db2f1f95ee04022a3f5610fdbd0ecc6b69c243883689ca66f`;
  `readelf` confirms no interpreter and no dynamic section.
- safety: source/build-only; no device command, helper deploy, PM actor start,
  Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping,
  PMIC/GPIO/GDSC/eSoC write, flash, boot image write, or partition write.
- next: V1327 should deploy helper `v276` only, then V1328 should run the
  bounded `mdm2ap_timing` sampler live.

## V1327 Execns Helper v276 Deploy (2026-05-31)

- runner: `scripts/revalidation/wifi_execns_helper_v276_deploy_preflight_v1327.py`
- evidence: `tmp/wifi/v1327-execns-helper-v276-deploy/manifest.json`
- report: `docs/reports/NATIVE_INIT_V1327_EXECNS_HELPER_V276_DEPLOY_2026-05-31.md`
- result: `execns-helper-v276-deploy-pass`, pass `true`.
- finding: helper `a90_android_execns_probe v276` is deployed to
  `/cache/bin/a90_android_execns_probe`. Manual post-deploy verification
  confirmed remote SHA256
  `dad57e135d3b4f0db2f1f95ee04022a3f5610fdbd0ecc6b69c243883689ca66f`, the
  helper marker, and the new
  `--pm-observer-late-per-proxy-mdm2ap-errfatal-pcie-timing-sampler` flag.
- transfer: NCM was inactive, so deploy used serial fallback.
- safety: deploy-only; no daemon start, service-manager start, Wi-Fi HAL,
  scan/connect, credentials, DHCP/routes, external ping, PMIC/GPIO/GDSC/eSoC
  write, flash, boot image write, or partition write.
- next: V1328 should run the bounded no-write `mdm2ap_timing` live sampler.

## V1328 MDM2AP Timing Sampler Live (2026-05-31)

- runner: `scripts/revalidation/native_wifi_mdm2ap_timing_sampler_live_v1328.py`
- evidence: `tmp/wifi/v1328-mdm2ap-timing-sampler-live/manifest.json`
- report: `docs/reports/NATIVE_INIT_V1328_MDM2AP_TIMING_SAMPLER_LIVE_2026-05-31.md`
- result: `v1328-mdm2ap-timing-full-window-no-transition`, pass `true`.
- finding: full `120 x 50ms` timing window saw `pm-service` enter
  `mdm_subsys_powerup` (`timing_pm_service_powerup_seen=true`,
  max powerup thread count `1`) but still recorded GPIO142 IRQ delta `0`, MDM
  errfatal IRQ delta `0`, no PCIe RC1 transition, PCI/MHI max `0`, no MHI pipe,
  `ks` max `0`, WLFW kmsg max `0`, and `wlan0=false`.
- safety: all `mdm2ap_timing.safety_*` fields were zero. No Wi-Fi HAL,
  scan/connect, credentials, DHCP/routes, external ping, PMIC/GPIO/GDSC/eSoC
  write, flash, boot image write, or partition write. Cleanup reboot was
  requested because a PM process was not proven stopped; post-run selftest
  remained `pass=11 warn=1 fail=0`.
- next: V1329 should classify the Android-only SDX50M response prerequisite
  before any PMIC/GPIO/eSoC mutation.

## V1329 Android-only SDX50M Prerequisite Classifier (2026-05-31)

- runner: `scripts/revalidation/native_wifi_android_only_sdx50m_prereq_classifier_v1329.py`
- evidence: `tmp/wifi/v1329-android-only-sdx50m-prereq-classifier/manifest.json`
- report: `docs/reports/NATIVE_INIT_V1329_ANDROID_ONLY_SDX50M_PREREQ_CLASSIFIER_2026-05-31.md`
- result: `v1329-android-prereq-is-earlier-sdx50m-response-sequence`, pass `true`.
- finding: V1328 proves native reaches `mdm_subsys_powerup` with a complete
  no-transition timing window. Android-positive V852/V896/V1239 evidence has
  GPIO142 IRQ, PCIe RC1/L0, `ks` on the MHI pipe, WLFW/BDF, and `wlan0`; the
  existing Android evidence places PCIe L0 before the captured `pm-service`
  eSoC timestamp.
- interpretation: the next blocker is not a longer native wait and not Wi-Fi
  HAL/scan/connect. It is an Android-only earlier SDX50M response prerequisite
  or timing relation that native has not reproduced.
- safety: host-only classifier. No device command, helper deploy, actor start,
  tracefs write, live eSoC ioctl/notify, PMIC write, GPIO request, GDSC/eSoC
  write, Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external
  ping, flash, boot image write, or partition write occurred.
- next: V1330 should design a focused Android read-only timing recapture around
  earliest `per_mgr`/`per_proxy`, `mdm_helper`, GPIO142, PCIe RC1, and `ks`/MHI
  on one monotonic timeline before any native PMIC/GPIO/eSoC mutation.

## V1330 Android Timing Recapture Plan (2026-05-31)

- report: `docs/reports/NATIVE_INIT_V1330_ANDROID_TIMING_RECAPTURE_PLAN_2026-05-31.md`
- result: `v1330-focused-android-readonly-timing-recapture-plan-ready`, pass `true`.
- objective: implement V1331 as an Android read-only collector/handoff that
  places first `__subsystem_get(esoc0)`, GPIO142, PCIe RC1/L0, MHI, `ks`,
  WLFW/BDF, and `wlan0` on one coherent timeline.
- key correction: do not compare post-boot fd snapshot timing against kernel
  dmesg timestamps as if they are the same source. Use dmesg monotonic
  timestamps for kernel events, and keep `ro.boottime.*` init service times
  separately labelled unless the runner verifies clock-source comparability.
- reuse: extend the V622 Android handoff/collector pattern, but replace its
  marker set with the V1330 SDX50M/eSoC/PCIe/MHI marker contract.
- safety: collector read-only. Android boot handoff is allowed only in an
  explicit rollback wrapper. No Wi-Fi HAL start, scan/connect, credential use,
  DHCP/routes, external ping, PMIC/GPIO/GDSC/eSoC write, blind eSoC notify,
  flash outside the handoff/rollback wrapper, boot image write outside approved
  rollback, or partition write.
- next: V1331 should implement the collector/handoff and run only after the
  script exposes plan/preflight gates with the V1330 guardrails.

## V1331 Android SDX50M Timing Handoff (2026-05-31)

- runner: `scripts/revalidation/android_sdx50m_timing_handoff_v1331.py`
- collector: `scripts/revalidation/native_wifi_android_sdx50m_timing_recapture_v1331.py`
- evidence: `tmp/wifi/v1331-android-sdx50m-timing-handoff/manifest.json`
- report: `docs/reports/NATIVE_INIT_V1331_ANDROID_SDX50M_TIMING_HANDOFF_2026-05-31.md`
- result: `v1331-android-wlfw-before-subsys-esoc0`, pass `true`.
- finding: Android-positive recapture captured `wlfw_start=8.396410s`,
  `__subsystem_get(esoc0)=8.449943s`, `BDF=9.513055s`, and
  `wlan0=14.772258s`. PCIe RC1/L0 and MHI pipe dmesg markers were not present
  in this run, so the runner did not claim PCIe-vs-eSoC ordering.
- rollback: restored `stage3/boot_linux_v724.img`; post-run native version was
  `A90 Linux init 0.9.68 (v724)` and selftest remained
  `pass=11 warn=1 fail=0`.
- safety: no Wi-Fi HAL start, scan/connect, credential use, DHCP/routes,
  external ping, native PMIC/GPIO/GDSC/eSoC write, direct eSoC ioctl/notify,
  blind `BOOT_DONE`, or partition write outside the bounded Android
  handoff/rollback path.
- next: V1332 should host-only classify whether native is missing an earlier
  Android `cnss-daemon` WLFW request/provider state before `pm-service` enters
  `mdm_subsys_powerup`.

## V1332 WLFW-before-eSoC Classifier (2026-05-31)

- runner: `scripts/revalidation/native_wifi_wlfw_before_esoc_classifier_v1332.py`
- evidence: `tmp/wifi/v1332-wlfw-before-esoc-classifier/manifest.json`
- report: `docs/reports/NATIVE_INIT_V1332_WLFW_BEFORE_ESOC_CLASSIFIER_2026-05-31.md`
- result: `v1332-native-missing-early-wlfw-provider-state`, pass `true`.
- finding: Android V1331 recorded `wlfw_start=8.396410s` before captured
  `__subsystem_get(esoc0)=8.449943s`, then BDF at `9.513055s` and `wlan0` at
  `14.772258s`. Native V1328 starts `cnss_daemon` before `mdm_helper`/late
  `per_proxy` and reaches `mdm_subsys_powerup`, but records no WLFW/BDF/MHI/ks
  or `wlan0`.
- interpretation: the next useful native gate is not a longer wait after
  `mdm_subsys_powerup`. It should prove whether native `cnss-daemon` can reach
  the same early WLFW userspace state that Android reaches before the captured
  eSoC trigger.
- safety: host-only classifier. No device command, helper deploy, actor start,
  tracefs write, live eSoC ioctl/notify, PMIC/GPIO write, Wi-Fi HAL start,
  scan/connect, credential use, DHCP/routes, external ping, flash, boot image
  write, or partition write occurred.
- next: V1333 should run a bounded native early-CNSS WLFW parity observer before
  `per_proxy`/eSoC trigger, capturing `cnss-daemon` stdout/stderr, properties,
  fds, and kmsg WLFW markers without Wi-Fi HAL/scan/connect.

## OUT-OF-BAND HOST ANALYSIS — 2026-06-01 (eSoC track pivot; not a vNNN cycle)

- result: host-only kernel/DTS static analysis. Full writeup
  `docs/reports/ESOC_PROVIDER_STATIC_ANALYSIS_2026-06-01.md`.
- finding: ext-sdx50m eSoC provider is BUILT-IN and is only a GPIO/ioctl
  handshake (mdm_subsys_powerup -> mdm4x_do_first_power_on ->
  sdx50m_toggle_soft_reset). It does NOT power PCIe/MHI and has NO regulator.
  Clean kallsyms decode: 131833 syms, pcie=109, esoc=20, mhi=0, sdx=0; provider
  funcs are static (printk/__func__ strings present in image). The
  ESOC_REG_REQ_ENG/WAIT_FOR_REQ/NOTIFY ioctls == esoc_dev_ioctl.
- DTS: mdm3=qcom,ext-sdx50m; ap2mdm-status=TLMM135, mdm2ap-status=TLMM142,
  ap2mdm-soft-reset/PON=PM8150L GPIO9 (no regulator-supply); mhi_0 esoc-0=<&mdm3>
  on pcie1 (qcom,pcie@1c08000) -> SDX50M is a PCIe endpoint on RC pcie1.
- verdict: FINITE / multi-subsystem (not infinite). Provider already runs on
  native (D-state, GPIO135 + PM8150L GPIO9 toggled) but MDM2AP/GPIO142 never
  asserts -> modem not powering on. SDX50M is a PCIe EP needing pcie1 RC
  refclk/PERST; V1306 shows pcie1 GDSC 0mV.
- PIVOT: pause upper eSoC-ioctl / ESOC_REQ_IMG / ks / MHI / CNSS-WLFW track
  (V1337-V1352) — downstream of MDM2AP. next read-only: (1) classify pcie1 RC
  power (GDSC/clocks/PERST/refclk; native enable vs V1306 0mV); (2) verify
  PM8150L GPIO9 PON sequence/timing parity vs provider reset-time-ms. Then a
  bounded reboot-safe RC power experiment. No PMIC/GPIO/GDSC writes, no Wi-Fi
  HAL/scan/connect/DHCP/routes/external ping until read-only work justifies a
  specific bounded action.

### Post-V1352 routing correction

- V1351/V1352 evidence is retained, but it is no longer the best next branch:
  `cnss-daemon` reaches `cld80211` and stops before `wlfw_start`, while the
  lower SDX50M still never asserts MDM2AP/GPIO142. Per the 2026-06-01 host
  analysis, that makes the CNSS-WLFW branch downstream evidence, not the next
  active blocker.
- Do not spend the next cycle on PM register/connect return tracing, CNSS-WLFW
  retry, `ESOC_REQ_IMG`, `ESOC_NOTIFY`, `BOOT_DONE`, `ks`, or MHI pipe
  expansion unless a read-only pcie1/PON classifier first proves MDM2AP can
  plausibly advance.
- Current active blocker statement:
  `mdm_subsys_powerup -> mdm4x_do_first_power_on -> sdx50m_toggle_soft_reset`
  is already reached on native; AP2MDM/TLMM135 and PM8150L GPIO9 are observed
  moving in prior evidence; MDM2AP/TLMM142 remains low; pcie1 RC power was
  previously observed at 0mV. Therefore the next unknown is whether the RC-side
  PCIe prerequisites or PON timing/parity are missing at the moment SDX50M is
  asked to boot.

### Next read-only cycle candidates

1. **V1353 pcie1 RC static contract classifier (host-only).**
   - Inputs: `sm8150-pcie.dtsi`, `sm8150-mhi.dtsi`, `sm8150-sdx50m.dtsi`,
     r3q overlay, V1306 GDSC evidence, and the host analysis report.
   - Output: pcie1 (`qcom,pcie@1c08000`) contract table for GDSC, GCC clocks,
     PERST/reset GPIO, refclk, wake GPIO, power-domains, pinctrl, and any
     runtime sysfs/debugfs paths expected to exist in native.
   - No device command, no live probing, no writes.
   - Status: PASS. See
     `docs/reports/NATIVE_INIT_V1353_PCIE1_RC_STATIC_CONTRACT_CLASSIFIER_2026-06-01.md`.
     Decision: `v1353-pcie1-rc-static-contract-ready`. V1354 can now use the
     generated read-only surface contract.
2. **V1354 pcie1 RC live read-only power observer.**
   - Run only after V1353 defines the expected surfaces.
   - Observe pcie1 GDSC/regulator/debugfs clock summaries, link state,
     runtime PM state, PERST/refclk-visible pinctrl/debugfs lines, PCI/MHI bus
     entries, and dmesg pcie1 markers before/during a bounded existing
     current-route power-up window.
   - Must not write sysfs/debugfs, request GPIO lines, trigger pcie enumerate,
     change GDSC/regulator state, call eSoC notify/BOOT_DONE, start Wi-Fi HAL,
     scan/connect, use credentials, DHCP/routes, external ping, flash, boot
     image write, or partition write.
   - Support status: PASS (source/build-only). Helper `a90_android_execns_probe
     v281` now emits read-only pcie1 RC fields for `pcie_1_gdsc`,
     pcie1/refgen/pipe clocks, and GPIO102/PERST, GPIO103/CLKREQ,
     GPIO104/WAKE in the existing MDM2AP timing summary. Parser/report support
     and deploy wrapper are staged. See
     `docs/reports/NATIVE_INIT_V1354_PCIE1_RC_POWER_OBSERVER_SUPPORT_2026-06-01.md`.
   - Remaining V1354 live gate: deploy helper v281 and run the bounded
     read-only current-route timing sampler. Decision target is whether pcie1
     RC GDSC/refclk/PERST/CLKREQ/WAKE ever transitions while provider/PON
     runs and MDM2AP remains low.
   - Live status: PASS. Helper v281 was deployed by serial fallback and V1354
     live returned `v1354-current-route-pcie1-rc-stayed-off`. Evidence:
     `docs/reports/NATIVE_INIT_V1354_EXECNS_HELPER_V281_DEPLOY_2026-06-01.md`
     and
     `docs/reports/NATIVE_INIT_V1354_PCIE1_RC_POWER_OBSERVER_LIVE_2026-06-01.md`.
     The current route reached `mdm_subsys_powerup`, but `pcie_1_gdsc` stayed
     `0mV`, pcie1 clkref/pipe lines stayed disabled, GPIO102/PERST stayed low,
     and no GPIO142/PCI/MHI/WLFW/wlan0 transition appeared.
3. **V1355 PM8150L GPIO9 PON parity classifier.**
   - Compare provider `sdx50m_toggle_soft_reset` / `mdm4x_do_first_power_on`
     strings/DTS timing (`reset-time-ms`) with native read-only evidence for
     PM8150L GPIO9/PON level and transition timing.
   - If live is needed, it must be a read-only sampler of pinctrl/debugfs/gpio
     text plus timestamped dmesg, not a GPIO request or PMIC write.
   - Status: PASS. See
     `docs/reports/NATIVE_INIT_V1355_PMIC_GPIO9_PON_PARITY_CLASSIFIER_2026-06-01.md`.
     Decision: `v1355-pon-parity-closed-pcie1-rc-next`. PM8150L GPIO9/PON maps
     to the expected ext-sdx50m soft-reset line, V1276 proves native and
     Android steady-state polarity both `out/high`, and V1318 captured the
     native provider's GPIO1270 low/high pulse before GPIO135/AP2MDM. Public
     DTS/OSRC does not expose the proprietary `reset-time-ms`, but PON parity is
     closed enough to reject blind PMIC GPIO9 write/hold as the next step.
4. **V1356 pcie1 RC bounded enable design (host-only first).**
   - Design, but do not yet execute, a reboot-safe pcie1 RC enable experiment
     using the V1353 static contract and V1354 live proof that `pcie_1_gdsc`,
     pcie1 clkref/pipe, GPIO102/PERST, PCI, and MHI remain off in native.
   - Required design gates: exact kernel/userland control surface, preflight
     readback, timeout, cleanup/reboot behavior, negative safety exclusions, and
     stop conditions if GDSC/refclk/PERST does not become healthy.
   - Keep Wi-Fi HAL, scan/connect, credential use, DHCP/routes, external ping,
     eSoC notify/`BOOT_DONE`, flash, boot image write, and partition write out
     of the first pcie1 RC experiment.
   - Status: PASS. See
     `docs/reports/NATIVE_INIT_V1356_PCIE1_RC_ENABLE_DESIGN_2026-06-01.md`.
     Decision: `v1356-pcie1-rc-enable-design-ready-readonly-surface-next`.
     V1356 identifies `msm_pcie_enumerate(1)` as the correct kernel semantic
     operation, but no safe userspace entry is proven yet. `cnss/dev_boot
     enumerate` is a possible surface only if V1357 proves it exists and maps
     to pcie1 rather than generic RC0; platform driver bind/probe and broad
     PCI rescan remain too broad for the first mutation.
5. **V1357 pcie1 RC control-surface verifier (live read-only).**
   - Collect only read-only evidence for `/sys/devices/platform/soc/*1c08000*`,
     `/sys/bus/platform/devices/*1c08000*`, platform driver symlinks,
     `/sys/kernel/debug/cnss/dev_boot` usage text if present, live devicetree
     `qcom,wlan-rc-num` / `qcom,pcie-parent` mappings, pcie1 GDSC/refclk/pipe
     clocks, GPIO102/PERST, GPIO103/CLKREQ, GPIO104/WAKE, `/proc/interrupts`,
     and focused pcie1/LTSSM/MHI dmesg.
   - Do not write sysfs/debugfs, do not bind/unbind platform drivers, do not
     write `cnss/dev_boot`, do not rescan PCI, and do not touch PMIC/GPIO/GDSC
     control. The output should decide whether a later V1358-style bounded
     `enumerate` experiment is valid or whether no safe live surface exists.
   - Status: PASS. See
     `docs/reports/NATIVE_INIT_V1357_PCIE1_RC_CONTROL_SURFACE_VERIFIER_LIVE_2026-06-01.md`.
     Decision: `v1357-pcie1-platform-surface-only`. Live native exposes
     pcie1 as `/sys/bus/platform/drivers/pci-msm/1c08000.qcom,pcie`; the
     driver is bound and runtime power reports `unsupported`/`auto`. However
     debugfs is not mounted, `/sys/kernel/debug/cnss/dev_boot` is absent in
     that state, no PCI/MHI devices exist, and live DT only shows generic
     `qcom,wlan-rc-num` value `0` for the inactive cnss2 node plus a separate
     `qcom,pcie-parent` phandle. V1357 does not prove any RC1-safe userspace
     enumerate surface.
6. **V1358 temporary-debugfs pcie1 RC control-surface verifier.**
   - Use the existing V1255-style temporary debugfs mount/cleanup pattern, but
     only to read `/sys/kernel/debug/cnss/dev_boot`, cnss debug files,
     regulator/clock/gpio summaries, and pcie1/PERST/CLKREQ/WAKE state. This
     is still not an RC enable experiment.
   - Required cleanup: if V1358 mounts debugfs, unmount it before exit and
     verify `/proc/mounts` returns to the pre-run state. Keep `cnss/dev_boot`
     write, platform bind/unbind, PCI rescan, PMIC/GPIO/GDSC write, eSoC
     notify/`BOOT_DONE`, Wi-Fi HAL, scan/connect, DHCP/routes, external ping,
     flash, boot image write, and partition write excluded.
   - Status: PASS. See
     `docs/reports/NATIVE_INIT_V1358_PCIE1_RC_DEBUGFS_SURFACE_VERIFIER_LIVE_2026-06-01.md`.
     Decision: `v1358-icnss-debugfs-only-no-cnss-dev-boot`. V1358 mounted
     debugfs temporarily, verified cleanup (`mounted_before=false`,
     `mounted_during=true`, `mounted_after=false`), and found `icnss/stats`
     but no `cnss` directory and no `cnss/dev_boot`. ICNSS state is
     `0x80(SSR REGISTERED)` with `SERVER_ARRIVE=0`, `FW_READY=0`, and
     `REGISTER_DRIVER=0`; pcie1 GDSC/clock/GPIO surfaces are visible but
     PCI/MHI devices remain absent. Therefore `cnss/dev_boot enumerate` is not
     available on this live kernel.
7. **V1359 ICNSS/pci-msm userspace entry classifier (host-only first).**
   - Reclassify the remaining safe entry options after V1358: the active
     debugfs surface is ICNSS `stats` only, while pcie1 is a bound `pci-msm`
     platform device. Determine whether any read/write sysfs/debugfs surface
     can invoke `msm_pcie_enumerate(1)` narrowly, or whether a custom kernel
     module/source patch is the only remaining direct path.
   - Do not attempt platform bind/unbind, PCI rescan, direct MMIO, PMIC/GPIO/
     GDSC writes, eSoC notify/`BOOT_DONE`, or Wi-Fi HAL/scan/connect in V1359.
   - Status: PASS. See
     `docs/reports/NATIVE_INIT_V1359_ICNSS_PCI_ENTRY_CLASSIFIER_2026-06-01.md`.
     Decision: `v1359-no-safe-userspace-msm-pcie-enumerate-entry`. ICNSS
     source exposes debugfs `stats` only, has zero `dev_boot`/`boot_wlan`
     mentions, and has no `msm_pcie_enumerate`, `qcom,wlan-rc-num`, or
     `qcom,pcie-parent` driven path. CNSS2 `dev_boot` exists only on the wrong
     branch (`qcom,cnss-qca6390` with `qcom,wlan-rc-num=<0>`), while the
     live pcie1 platform node is only the already-bound `pci-msm` device.
8. **V1360 MHI platform surface verifier (live read-only).**
   - Collect read-only live surfaces for `mhi_dev@1c0b000`, `mhi_0/qcom,mhi@0`,
     `/sys/bus/platform/devices/*mhi*`, `/sys/bus/platform/drivers/*mhi*`,
     `/sys/bus/mhi/devices`, `/dev/mhi*`, MHI debugfs directories, and
     pcie1/MHI dmesg markers. The goal is to determine whether an MHI platform
     driver is present, bound, unbound, or absent before even considering any
     `pci-msm` bind/rescan mutation.
   - Keep the same exclusions: no platform bind/unbind, no PCI rescan, no
     debugfs/sysfs writes, no PMIC/GPIO/GDSC write, no eSoC notify/`BOOT_DONE`,
     no Wi-Fi HAL/scan/connect/DHCP/routes/external ping.
   - Result:
     `docs/reports/NATIVE_INIT_V1360_MHI_PLATFORM_SURFACE_VERIFIER_LIVE_2026-06-01.md`.
     Decision: `v1360-mhi-surface-present-no-live-device`. Live DT exposes
     MHI topology including `1c0b000` and `esoc-0`, the MHI bus and drivers
     exist, and the pcie1 platform node remains bound to `pci-msm`, but there
     are no MHI bus devices, `/dev/mhi*` nodes, or PCIe link-up markers.

9. **V1361 MHI ownership/downstream classifier (host-only).**
   - Use V1360 evidence plus OSRC sources to classify whether the observed MHI
     surfaces can initiate SDX50M/pcie1 enumeration or are downstream consumers
     that require a PCI/MHI device first.
   - Required answer: whether any observed MHI bus driver, platform device, or
     debugfs surface is a narrower safe entry than `pci-msm` bind/rescan. If
     bind files only belong to MHI client drivers with no device instances, they
     are not a valid next mutation.
   - Keep this host-only: no live command, platform bind/unbind, PCI rescan,
     PMIC/GPIO/GDSC write, eSoC notify/`BOOT_DONE`, Wi-Fi HAL/scan/connect,
     DHCP/routes, or external ping.
   - Result:
     `docs/reports/NATIVE_INIT_V1361_MHI_SURFACE_OWNERSHIP_CLASSIFIER_2026-06-01.md`.
     Decision: `v1361-mhi-surfaces-downstream-no-safe-mutation`. The live MHI
     bus drivers are client drivers and require existing `mhi_device`
     instances; the MHI controller is created from an existing `pci_dev`.
     Therefore MHI bind/debugfs surfaces are downstream of pcie1 enumeration and
     are not a narrower safe mutation.

10. **V1362 pci-msm/pcie1 mutation risk classifier (host-only).**
    - With ICNSS `dev_boot` and MHI client surfaces closed, classify the
      remaining already-bound `pci-msm` platform surface and generic PCI rescan
      paths before any live mutation.
    - Required output: risk table for platform unbind/bind, driver reprobe,
      `drivers_probe`, and global PCI rescan; identify whether any option can
      be made RC1-specific, bounded, observable, and rollback-safe. If not,
      choose a kernel-side shim/design route instead of a blind mutation.
    - Keep this host-only: no live command, no platform bind/unbind, no PCI
      rescan, no PMIC/GPIO/GDSC write, no eSoC notify/`BOOT_DONE`, no Wi-Fi
      HAL/scan/connect/DHCP/routes/external ping.
    - Result:
      `docs/reports/NATIVE_INIT_V1362_PCI_MSM_MUTATION_RISK_CLASSIFIER_2026-06-01.md`.
      Decision: `v1362-no-safe-userspace-pci-msm-mutation`. Platform
      unbind/bind is only partially RC1-scoped and enters proprietary
      `pci-msm` remove/probe without timeout/rollback proof; `drivers_probe`
      and global PCI rescan are not RC1-specific. No live userspace mutation is
      selected.

11. **V1363 pci-msm debugfs surface verifier (live read-only).**
    - V1362 initially pointed at a kernel-side shim, but V1360 evidence showed
      `/sys/kernel/debug/pci-msm`. Before any shim work, classify that existing
      userspace surface read-only.
    - Collect only directory/file names and small read outputs from
      `/sys/kernel/debug/pci-msm`, with temporary debugfs mount/cleanup if
      needed. No debugfs writes.
    - Result:
      `docs/reports/NATIVE_INIT_V1363_PCI_MSM_DEBUGFS_SURFACE_VERIFIER_LIVE_2026-06-01.md`.
      Decision: `v1363-pci-msm-debugfs-rc-control-candidate`. The live kernel
      exposes `case` and `rc_sel`; read-only `case` lists option `11:
      ENUMERATE`, `26: OUTPUT PERST AND WAKE GPIO STATUS`, and PERST assert/
      deassert options. This is now the shortest candidate, but still requires
      a host-only contract before any write.

12. **V1364 pci-msm debugfs RC1 contract classifier (host-only).**
    - Use V1363 live evidence plus kallsyms/source evidence to prove what
      `rc_sel` and `case=11` do, whether `rc_sel=1` maps to pcie1, and whether
      the write sequence can be bounded and observed without touching PMIC/GPIO
      directly.
    - Required answer: exact write contract candidate, if any, for a later live
      test. At minimum classify `rc_sel`, `case`, `boot_option`, and whether
      `case=11` calls `msm_pcie_enumerate(selected_rc)`.
    - Keep this host-only: no debugfs/sysfs writes, no PCI rescan, no platform
      bind/unbind, no PMIC/GPIO/GDSC write, no eSoC notify/`BOOT_DONE`, no
      Wi-Fi HAL/scan/connect/DHCP/routes/external ping.
    - Result:
      `docs/reports/NATIVE_INIT_V1364_PCI_MSM_DEBUGFS_CONTRACT_CLASSIFIER_2026-06-01.md`.
      Decision: `v1364-pci-msm-debugfs-contract-candidate-not-approved`.
      `rc_sel=<RC>` plus `case=<testcase>` is the likely contract. `case=11`
      is `ENUMERATE`, but enumerate is not approved yet because proprietary
      call-path proof is incomplete. `case=26` is status-only `OUTPUT PERST AND
      WAKE GPIO STATUS`, making it the first bounded live write candidate.

13. **V1365 pci-msm debugfs status-only proof (bounded live).**
    - Candidate writes only:
      `echo 1 > /sys/kernel/debug/pci-msm/rc_sel`, then
      `echo 26 > /sys/kernel/debug/pci-msm/case`.
    - Scope: prove `rc_sel=1` selects a valid RC and `case=26` emits pcie1
      PERST/WAKE status without changing link state. Collect before/after
      pcie1 GDSC/refclk/PERST/LTSSM/PCI/MHI/GPIO142 and dmesg. Cleanup by
      restoring debugfs mount state; reboot only if health changes.
    - Hard stop: no `case=11`, no PERST assert/deassert cases, no boot option
      write, no MMIO write cases, no platform bind/unbind, no PCI rescan, no
      PMIC/GPIO/GDSC direct write, no eSoC notify/`BOOT_DONE`, no Wi-Fi HAL,
      scan/connect/DHCP/routes/external ping.
    - Result:
      `docs/reports/NATIVE_INIT_V1365_PCI_MSM_STATUS_CASE_LIVE_2026-06-01.md`.
      Decision: `v1365-case26-transport-reset-reboot-risk`. The debugfs
      surface was mounted and read successfully, but `rc_sel=1` followed by
      `case=26` caused cmdv1 transport loss before settle/after-captures could
      complete. A later manual health check showed the device recovered
      normally, but the write cannot be treated as a harmless status-only
      operation. Therefore `case=11` enumerate is blocked, and further
      pci-msm `case` writes require source/disassembly proof or a new
      reboot-safe design.

14. **V1366 pci-msm debugfs case-path classifier (host-only).**
    - Inputs: V1363 `pci-msm/case` listing, V1364 contract classifier, V1365
      transport-loss evidence, stock kernel strings/kallsyms, available OSRC
      pcie sources, and any local Samsung source drop.
    - Required output: prove whether `case=26` really is status-only, whether
      `case` writes synchronously call into RC reset/enumeration paths, and
      whether `rc_sel=1` is sufficient to scope side effects to pcie1/RC1.
      If source cannot prove this, mark pci-msm debugfs case writes unsafe and
      return to a kernel-side shim or Android-reference capture path.
    - Keep host-only: no debugfs/sysfs writes, no `case=11`, no PERST
      assert/deassert, no PCI rescan, no platform bind/unbind, no PMIC/GPIO/
      GDSC write, no eSoC notify/`BOOT_DONE`, no Wi-Fi HAL, scan/connect,
      DHCP/routes, external ping, flash, boot image write, or partition write.
    - Result:
      `docs/reports/NATIVE_INIT_V1366_PCI_MSM_CASE_PATH_CLASSIFIER_2026-06-01.md`.
      Decision: `v1366-pci-msm-case-path-corrected-rc-selector-no-live-write`.
      Reference pci-msm source proves `rc_sel` is a bitmask, not an ordinal RC
      index. V1365 wrote `rc_sel=1`, selecting `BIT(0)`/RC0; pcie1/RC1 has
      `cell-index=<1>` and would require `rc_sel=2`. Source also shows
      `case=26` is intended as PERST/WAKE `gpio_get_value` readout, while
      `case=11` calls `msm_pcie_enumerate(dev->rc_idx)`. Because V1365 still
      caused transport loss, corrected `rc_sel=2` live retry is not approved
      until a new reboot-safe design exists.

15. **V1367 corrected-RC1 action design (host-only).**
    - Inputs: V1366 corrected selector model, V1365 transport-loss evidence,
      pci-msm source, pcie1 static contract, and native recovery constraints.
    - Required output: choose one next action path:
      (A) a reboot-safe `rc_sel=2` + `case=26` status read with explicit
      pre/post health, expected output, transport-loss handling, and no
      enumerate; (B) a kernel-side `msm_pcie_enumerate(1)` shim/patch design
      that avoids broad debugfs `case` semantics; or (C) stop pci-msm live
      writes and gather Android reference RC1 debugfs output first.
    - Keep host-only until the chosen design has exact commands, timeout,
      cleanup/reboot behavior, stop conditions, and secret-safe evidence paths.
      No debugfs/sysfs writes, no `case=11`, no PERST assert/deassert, no PCI
      rescan, no platform bind/unbind, no PMIC/GPIO/GDSC write, no eSoC
      notify/`BOOT_DONE`, no Wi-Fi HAL, scan/connect, DHCP/routes, external
      ping, flash, boot image write, or partition write.
    - Result:
      `docs/reports/NATIVE_INIT_V1367_PCI_MSM_CORRECTED_RC1_DESIGN_2026-06-01.md`.
      Decision: `v1367-corrected-rc1-status-read-design-ready`. The selected
      next path is one corrected RC1 status-read proof, `rc_sel=2` then
      `case=26`, treated as reboot-risky and bounded. `case=11` enumerate,
      PERST assert/deassert, MMIO write, boot option write, platform
      bind/unbind, PCI rescan, PMIC/GPIO/GDSC direct write, eSoC notify/
      `BOOT_DONE`, Wi-Fi HAL, scan/connect, DHCP/routes, external ping, flash,
      boot image write, and partition write remain excluded.

16. **V1368 corrected-RC1 status-read proof (bounded live).**
    - Candidate writes only:
      `printf '2\n' > /sys/kernel/debug/pci-msm/rc_sel`, then
      `printf '26\n' > /sys/kernel/debug/pci-msm/case`.
    - Preflight: native version/status/selftest `fail=0`, debugfs mount state
      captured, `pci-msm/case` listing matches V1363/V1366, PCI/MHI devices
      absent before proof, and focused pcie1 regulator/clock/gpio/dmesg
      snapshots captured.
    - Success: write returns without transport loss, after-captures complete,
      no PCI/MHI/link-up transition, debugfs mount state restored, and
      post-selftest `fail=0`.
    - Failure: cmdv1 transport loss/reboot, PCI/MHI/link transition, cleanup
      failure, or post-selftest failure. Transport loss is classified as
      reboot-risk failure; wait for recovery and record separate out-of-window
      status/selftest only.
    - Hard stop: no `case=11`, no PERST assert/deassert cases, no MMIO write
      cases, no boot option write, no platform bind/unbind, no PCI rescan, no
      PMIC/GPIO/GDSC direct write, no eSoC notify/`BOOT_DONE`, no Wi-Fi HAL,
      scan/connect/DHCP/routes/external ping, flash, boot image write, or
      partition write.
    - Result:
      `docs/reports/NATIVE_INIT_V1368_PCI_MSM_CORRECTED_RC1_STATUS_LIVE_2026-06-01.md`.
      Decision: `v1368-corrected-rc1-status-proof-clean`. `rc_sel=2` followed
      by `case=26` emitted RC1 PERST/WAKE status without transport loss, PCI/
      MHI/link transition, or health regression. Debugfs mount state was
      restored and post-selftest stayed `fail=0`. Observed RC1 values:
      PERST gpio102=`0`, WAKE gpio104=`0`.

17. **V1369 pcie1 enumerate-vs-shim decision (host-only).**
    - Inputs: V1368 clean corrected-RC1 status proof, pci-msm source showing
      `case=11` calls `msm_pcie_enumerate(dev->rc_idx)`, V1354 proof that
      pcie1 stays off in the current route, and V1362 rejection of broad
      bind/rescan paths.
    - Required output: choose whether the next mutation should be a bounded
      debugfs `rc_sel=2` + `case=11` enumerate attempt, or a kernel-side
      `msm_pcie_enumerate(1)` shim/patch. The decision must include exact
      preflight, timeout, dmesg/PCI/MHI/GPIO142 success criteria, cleanup/
      recovery behavior, and stop conditions.
    - Keep host-only until the design is explicit. No live `case=11`, no PERST
      assert/deassert, no MMIO write cases, no boot option write, no platform
      bind/unbind, no generic PCI rescan, no PMIC/GPIO/GDSC direct write, no
      eSoC notify/`BOOT_DONE`, no Wi-Fi HAL, scan/connect, DHCP/routes,
      external ping, flash, boot image write, or partition write.
    - Result:
      `docs/reports/NATIVE_INIT_V1369_PCIE1_ENUMERATE_DECISION_2026-06-01.md`.
      Decision: `v1369-select-corrected-debugfs-rc1-enumerate-design`. The
      corrected debugfs path is narrower than a new kernel shim for the next
      proof: V1368 proved `rc_sel=2` reaches RC1 cleanly, and pci-msm source
      shows `case=11` calls `msm_pcie_enumerate(dev->rc_idx)`, which performs
      `msm_pcie_enable(PM_ALL)` followed by PCI root-bus scan/add.

18. **V1370 corrected-RC1 enumerate proof (bounded live).**
    - Candidate writes only:
      `printf '2\n' > /sys/kernel/debug/pci-msm/rc_sel`, then
      `printf '11\n' > /sys/kernel/debug/pci-msm/case`.
    - Preflight: native version/status/selftest `fail=0`, V1368 status path
      already clean, debugfs mount state captured, PCI/MHI devices absent
      before enumerate, and pcie1 regulator/clock/gpio/dmesg snapshots
      captured.
    - Success signals: command returns without transport loss, dmesg includes
      RC1 enumerate attempt, pcie1 GDSC/clock/PERST/link or PCI/MHI state
      changes are captured, debugfs cleanup completes, and post-selftest
      remains `fail=0`.
    - Failure signals: transport loss/reboot, post-selftest failure,
      unexpected non-RC1 PCI changes, or debugfs cleanup failure. Failure is
      still evidence; do not retry blindly.
    - Hard stop: no Wi-Fi HAL, scan/connect/credentials, DHCP/routes/external
      ping, PERST assert/deassert cases, MMIO write cases, boot option write,
      platform bind/unbind, generic PCI rescan, PMIC/GPIO/GDSC direct write,
      eSoC notify/`BOOT_DONE`, flash, boot image write, or partition write.
    - Result:
      `docs/reports/NATIVE_INIT_V1370_PCI_MSM_CORRECTED_RC1_ENUMERATE_LIVE_2026-06-01.md`.
      Decision: `v1370-corrected-rc1-link-training-no-l0-clean`. Corrected
      `rc_sel=2` + `case=11` reached RC1 enumerate and transient pcie1
      enable/link training: endpoint reset asserted/released, RC1 PHY ready,
      LTSSM poll active/compliance observed, then RC1 link initialization
      failed before L0. No PCI/MHI device appeared, steady regulator/clock
      snapshots returned unchanged, debugfs cleanup restored the original mount
      state, and post-selftest remained `fail=0`.

19. **V1371 RC1 LTSSM failure classifier (host-only).**
    - Inputs: V1370 native dmesg showing RC1 PHY ready but no L0, Android V852
      RC1 sequence that reaches L0, pci-msm source around `msm_pcie_enable()`,
      and DTS for pcie1/esoc0/reset/refclk wiring.
    - Goal: decide whether the remaining gap is endpoint-side SDX50M power/PON
      readiness, PERST/refclk timing, RC1 clock/GDSC ownership, or a required
      Android-only precondition before pcie1 enumeration.
    - Required output: timestamp/order comparison of Android versus native RC1
      LTSSM states, source-level map of `msm_pcie_enable(PM_ALL)` reset/refclk
      handling, and a narrowed next live candidate or an explicit no-mutation
      stop.
    - Hard stop: host-only. No new debugfs `case` write, no PERST
      assert/deassert, no PMIC/GPIO/GDSC direct write, no eSoC notify/`BOOT_DONE`,
      no Wi-Fi HAL, scan/connect/credentials, DHCP/routes, external ping, flash,
      boot image write, or partition write.
    - Result:
      `docs/reports/NATIVE_INIT_V1371_RC1_LTSSM_FAILURE_CLASSIFIER_2026-06-01.md`.
      Decision: `v1371-endpoint-readiness-gap-after-rc1-power-proven`. V1370
      proves the AP-side pcie1 RC path can run corrected enumerate, enable
      power/clocks/PERST, reach PHY-ready, release endpoint reset, and enter
      LTSSM. Native stops in poll active/compliance before L0; Android reaches
      L0 only after esoc0/provider startup. Therefore the next blocker is
      endpoint/SDX50M readiness at PERST release, not a missing `pci-msm`
      enumerate entry or upper Wi-Fi HAL path.

20. **V1372 provider-held delayed corrected-RC1 enumerate proof (bounded live design).**
    - Goal: match Android ordering without starting Wi-Fi HAL/network bring-up:
      hold the SDX50M provider/eSoC path first, wait near the Android
      esoc0-to-RC1 interval, then run only corrected `rc_sel=2` + `case=11`.
    - Candidate order: preflight native selftest `fail=0`; capture debugfs
      mount state; start the existing lower/provider path that holds
      `/dev/subsys_esoc0` and toggles AP2MDM/PON; wait roughly the Android
      `esoc0` to RC1 interval or poll readable AP2MDM/PON state; write only
      `rc_sel=2` then `case=11`; capture GPIO142, pcie1 LTSSM/L0, PCI/MHI,
      dmesg, cleanup, and post-selftest.
    - Success signals: RC1 reaches L0 or PCI/MHI appears while post-selftest
      remains `fail=0`; or, if still no L0, evidence cleanly proves the
      provider-held endpoint state did not change the LTSSM failure class.
    - Failure signals: transport loss/reboot, cleanup failure, post-selftest
      failure, non-RC1 PCI side effects, or any unexpected Wi-Fi/network
      activity.
    - Hard stop: no Wi-Fi HAL, scan/connect/credentials, DHCP/routes, external
      ping, PERST assert/deassert debug cases, PMIC/GPIO/GDSC direct writes,
      eSoC notify/`BOOT_DONE` spoof, flash, boot image write, or partition
      write.
    - Result:
      `docs/reports/NATIVE_INIT_V1372_PROVIDER_HELD_PCIE1_ENUMERATE_LIVE_2026-06-01.md`.
      Decision: `v1372-provider-held-still-no-l0-clean`. The ext-sdx50m
      provider path was opened via `/dev/subsys_esoc0` and the holder was
      observed in `mdm_subsys_powerup` before corrected `rc_sel=2` + `case=11`.
      RC1 reached PHY-ready and LTSSM poll active/compliance, then failed before
      L0 again. No GPIO142/MDM2AP, PCI, MHI, WLFW, or `wlan0` appeared, and
      reboot cleanup restored native health with selftest `fail=0`.

21. **V1373 provider-path parity classifier (host-only).**
    - Inputs: V1372 native provider-held evidence, V1370 native corrected
      enumerate evidence, Android V852 RC1-L0 timeline, V1157/V1158
      `mdm_helper` strace evidence, V1228 compact trace, and the ext-sdx50m/
      pci-msm source/DTS analysis.
    - Goal: decide why Android reaches endpoint readiness while raw native
      provider-hold plus corrected RC1 enumerate does not. The classifier must
      separate timing-only hypotheses from missing Android-only participants
      such as `mdm_helper` command-engine registration, `pm-service`/peripheral
      manager ordering, PM QoS/client votes, or other provider-adjacent
      prerequisites.
    - Required output: ordered Android-vs-native table for `mdm_helper`,
      `pm-service`/`__subsystem_get(esoc0)`, AP2MDM/PON, GPIO142/MDM2AP, RC1
      PERST release, LTSSM states, PCI/MHI creation, and a single next live
      candidate or an explicit no-mutation stop.
    - Hard stop: host-only. No new device command, debugfs case write, PERST
      assert/deassert, PMIC/GPIO/GDSC direct write, eSoC notify/`BOOT_DONE`,
      Wi-Fi HAL, scan/connect/credentials, DHCP/routes, external ping, flash,
      boot image write, or partition write.
    - Result:
      `docs/reports/NATIVE_INIT_V1373_PROVIDER_PATH_PARITY_CLASSIFIER_2026-06-01.md`.
      Decision: `v1373-gap-is-android-participant-plus-rc1-combination`.
      Existing evidence has tested PM actors without corrected RC1 enumerate,
      corrected RC1 enumerate without PM actors, and raw provider-hold plus
      corrected RC1 enumerate without Android `mdm_helper`/`pm-service`
      context. All native variants stop below RC1 L0/MDM2AP/WLFW/`wlan0`; the
      Android reference reaches all of them. The remaining narrow untested
      combination is Android participant parity plus corrected RC1 enumerate.

22. **V1374 Android participant parity + corrected RC1 enumerate design (source/build-only first).**
    - Goal: turn V1373 into a bounded live runner design that starts only the
      lower Android participant parity needed for `mdm_helper` CMD_ENG /
      WAIT_FOR_REQ and `pm-service` `/dev/subsys_esoc0`, then writes corrected
      `rc_sel=2` + `case=11` after that provider window is confirmed.
    - Required preflight: native selftest `fail=0`, debugfs mount state,
      `/dev/esoc-0` fd or equivalent `mdm_helper` evidence, `pm-service`
      `/dev/subsys_esoc0` `wchan=mdm_subsys_powerup`, no existing PCI/MHI/WLFW
      link, and explicit reboot cleanup path.
    - Success signals: RC1 reaches L0, GPIO142/MDM2AP asserts, PCI/MHI appears,
      WLFW/BDF markers appear, or a strictly stronger lower-boundary failure is
      captured while post-selftest returns `fail=0`.
    - Failure signals: transport loss without cleanup, post-selftest failure,
      accidental HAL/scan/connect/network activity, or non-RC1/global PCI side
      effects.
    - Hard stop: source/build-only first. No live execution until the runner
      preflight is implemented. No Wi-Fi HAL, scan/connect/credentials,
      DHCP/routes, external ping, direct PMIC/GPIO/GDSC writes, eSoC notify/
      `BOOT_DONE` spoof, flash, boot image write, or partition write.
    - Result:
      `docs/reports/NATIVE_INIT_V1374_ANDROID_PARTICIPANT_RC1_SUPPORT_2026-06-01.md`.
      Decision: `v1374-helper-v282-support-ready`. Helper
      `a90_android_execns_probe v282` adds
      `--pm-observer-late-per-proxy-corrected-rc1-enumerate`; it is only valid
      with the late-`per_proxy` response sampler and MDM2AP timing sampler,
      waits until `pm-service` is observed with `/dev/subsys_esoc0`, then writes
      corrected `rc_sel=2` + `case=11` from inside the same helper process.
      Source/build checks passed with static aarch64 helper SHA256
      `c1f4670536c37b068dd2f8ac807c0eb5416eb3f248857791002156c1f0195418`.

23. **V1375 helper v282 deploy preflight (deploy-only).**
    - Goal: deploy helper v282 and prove the device-side helper marker, SHA256,
      mode parsing, and selftest are clean before any live RC1 enumerate action.
    - Required checks: native version/status/selftest `fail=0`, helper SHA256
      equals `c1f4670536c37b068dd2f8ac807c0eb5416eb3f248857791002156c1f0195418`,
      `strings`/version output contains `a90_android_execns_probe v282`, new
      flag appears in usage, debugfs mount state is observed, and no live
      `case=11` write is executed.
    - Hard stop: deploy/preflight only. No Wi-Fi HAL, scan/connect/credentials,
      DHCP/routes, external ping, PMIC/GPIO/GDSC writes, eSoC notify/
      `BOOT_DONE`, flash, boot image write, or partition write.
    - Result:
      `docs/reports/NATIVE_INIT_V1375_EXECNS_HELPER_V282_DEPLOY_2026-06-01.md`.
      Decision: `execns-helper-v282-deploy-pass`. Helper v282 was installed to
      `/cache/bin/a90_android_execns_probe`; post-deploy SHA matched
      `c1f4670536c37b068dd2f8ac807c0eb5416eb3f248857791002156c1f0195418`,
      helper usage exposed `a90_android_execns_probe v282` and
      `--pm-observer-late-per-proxy-corrected-rc1-enumerate`, and post selftest
      stayed clean. NCM was inactive, so `auto` transfer used serial fallback;
      the safe successful chunk size was `1800`.

24. **V1376 bounded Android participant + corrected RC1 enumerate live gate.**
    - Goal: start the lower Android participant parity path
      (`mdm_helper` CMD_ENG/WAIT_FOR_REQ plus late `per_proxy`/`pm-service`
      `/dev/subsys_esoc0`) and trigger corrected RC1 enumerate only after that
      gate is observed in the same helper process.
    - Required flags: `--allow-post-pm-mdm-helper-esoc-observer`,
      `--allow-post-pm-mdm-helper-lower-trace`,
      `--pm-observer-start-mdm-helper-after-cnss`,
      `--pm-observer-start-cnss-after-provider`,
      `--pm-observer-start-cnss-before-per-proxy`,
      `--pm-observer-start-per-proxy-after-mdm-helper-esoc-fd`,
      `--pm-observer-late-per-proxy-response-sampler`,
      `--pm-observer-late-per-proxy-mdm2ap-errfatal-pcie-timing-sampler`, and
      `--pm-observer-late-per-proxy-corrected-rc1-enumerate`.
    - Success signals: `corrected_rc1_enumerate.triggered=1`, `rc_sel_rc=0`,
      `case_rc=0`, and then either RC1 reaches L0/GPIO142/PCI/MHI/WLFW/`wlan0`
      or a stricter lower-boundary failure is captured with postflight
      selftest `fail=0`.
    - Failure signals: `per_mgr_subsys_esoc0_count` never becomes positive,
      `rc_sel`/`case` write failure, transport loss without recovery evidence,
      postflight selftest failure, or any unintended HAL/network activity.
    - Hard stop: still below Wi-Fi bring-up. No Wi-Fi HAL, scan/connect/
      credentials, DHCP/routes, external ping, direct PMIC/GPIO/GDSC writes,
      eSoC notify/`BOOT_DONE`, flash, boot image write, or partition write.
    - Result:
      `docs/reports/NATIVE_INIT_V1376_ANDROID_PARTICIPANT_CORRECTED_RC1_LIVE_2026-06-01.md`.
      Decision: `v1376-corrected-rc1-not-triggered`. The run was safe and
      informative but did not execute `rc_sel=2`/`case=11`: helper v282 gated on
      `per_mgr_subsys_esoc0_count > 0`, while the actual desired lower state is
      `pm-service` blocked inside `open("/dev/subsys_esoc0")` /
      `mdm_subsys_powerup`, before an fd is created. Timing did prove
      `timing_pm_service_powerup_seen=True` over 120 samples, with no GPIO142,
      PCI, MHI, WLFW, or `wlan0` transition. V1377 must patch the helper gate to
      trigger on powerup-thread/wchan observation.

25. **V1377 corrected RC1 powerup-thread gate support (source/build-only).**
    - Goal: bump helper to v283 and change the corrected RC1 enumerate gate from
      fd ownership to `mdm_subsys_powerup`/powerup-thread observation, while
      preserving the existing late-`per_proxy` and MDM2AP timing sampler
      requirements.
    - Success criteria: source/build checks prove helper v283 reports both
      `gate_per_mgr_subsys_esoc0_count` and
      `gate_pm_service_powerup_thread_count`, triggers when the powerup thread
      count is positive, and still skips without either lower gate.
    - Hard stop: source/build-only. No device command, Wi-Fi HAL, scan/connect,
      DHCP/routes, external ping, PMIC/GPIO/GDSC direct write, eSoC notify/
      `BOOT_DONE`, flash, boot image write, or partition write.
    - Result:
      `docs/reports/NATIVE_INIT_V1377_CORRECTED_RC1_POWERUP_GATE_SUPPORT_2026-06-01.md`.
      Decision: `v1377-helper-v283-powerup-gate-ready`. Helper
      `a90_android_execns_probe v283` (SHA256
      `985eba4834b3b0324d886df39cecff9811ae183ea800119fdaea2d6ef8431a18`)
      preserves the fd gate but also accepts a positive
      `pm_service_powerup_thread_count`, emits
      `gate_pm_service_powerup_thread_count`, and updates the non-trigger
      skip reason to `pm_service_powerup_not_observed`. Source/build checks
      passed without device commands. V1378 must deploy/preflight v283 before
      the live rerun.
26. **V1378 helper v283 deploy preflight (deploy-only).**
    - Goal: deploy helper v283 to `/cache/bin/a90_android_execns_probe` and
      prove marker/SHA/usage/selftest before any corrected RC1 live retry.
    - Required checks: native version/status/selftest `fail=0`, helper SHA256
      equals
      `985eba4834b3b0324d886df39cecff9811ae183ea800119fdaea2d6ef8431a18`,
      helper usage exposes `a90_android_execns_probe v283`, the corrected RC1
      flag is present, and evidence confirms the new
      `gate_pm_service_powerup_thread_count` marker.
    - Transfer note: NCM may be inactive; if serial fallback is used, keep the
      safe chunk size from V1375 (`1800`) unless a current preflight proves a
      larger line size is safe.
    - Hard stop: deploy/preflight only. No daemon start, Wi-Fi HAL,
      scan/connect, credentials, DHCP/routes, external ping, PMIC/GPIO/GDSC
      writes, eSoC notify/`BOOT_DONE`, flash, boot image write, or partition
      write.
    - Result:
      `docs/reports/NATIVE_INIT_V1378_EXECNS_HELPER_V283_DEPLOY_2026-06-01.md`.
      Decision: `execns-helper-v283-deploy-pass`. Helper v283 was installed to
      `/cache/bin/a90_android_execns_probe`; post-deploy SHA matched
      `985eba4834b3b0324d886df39cecff9811ae183ea800119fdaea2d6ef8431a18`,
      helper usage exposed `a90_android_execns_probe v283` and
      `gate_pm_service_powerup_thread_count`, and post selftest stayed clean.
      NCM was inactive, so `auto` transfer used serial fallback with safe
      chunk size `1800`, `1061` chunks, and max cmdv1 line bytes `3786`.
27. **V1379 bounded Android participant + corrected RC1 live rerun.**
    - Goal: rerun the V1376 lower Android participant parity path with helper
      v283 so corrected RC1 enumerate triggers when `pm-service` is observed
      blocked in `mdm_subsys_powerup`, even before a `/dev/subsys_esoc0` fd is
      visible.
    - Required preflight: V1378 helper v283 deploy PASS, native selftest
      `fail=0`, debugfs mount state captured, PCI/MHI/WLFW/`wlan0` absent
      before the run, and the same late-`per_proxy`/MDM2AP timing sampler
      flags used by V1376.
    - Success signals: `corrected_rc1_enumerate.triggered=1`,
      `gate_pm_service_powerup_thread_count > 0`, `rc_sel_rc=0`, `case_rc=0`,
      and then either RC1 reaches L0/GPIO142/PCI/MHI/WLFW/`wlan0`, or a
      strictly stronger lower-boundary failure is captured with postflight
      selftest `fail=0`.
    - Failure signals: no powerup-thread gate, `rc_sel`/`case` write failure,
      transport loss without recovery evidence, debugfs cleanup failure,
      postflight selftest failure, non-RC1 PCI side effects, or any unintended
      HAL/network activity.
    - Hard stop: still below Wi-Fi bring-up. No Wi-Fi HAL, scan/connect,
      credentials, DHCP/routes, external ping, direct PMIC/GPIO/GDSC writes,
      eSoC notify/`BOOT_DONE`, flash, boot image write, or partition write.
    - Result:
      `docs/reports/NATIVE_INIT_V1379_ANDROID_PARTICIPANT_CORRECTED_RC1_LIVE_2026-06-01.md`.
      Decision: `v1379-corrected-rc1-ltssm-no-downstream-clean`. Helper v283
      triggered corrected RC1 enumerate inside the Android participant window:
      `gate_pm_service_powerup_thread_count=1`, `rc_sel_rc=0`, and
      `case_rc=0`. The timing sampler saw RC1 transition
      (`timing_pcie_rc1_transition_seen=True`) but no GPIO142/MDM2AP, PCI/MHI,
      MHI pipe, `ks`, WLFW, or `wlan0`. Safety markers stayed clear, debugfs
      cleanup completed, and post selftest stayed clean.
28. **V1380 RC1 LTSSM/participant gap classifier (host-only).**
    - Goal: classify V1379 against Android-positive RC1 L0 evidence and prior
      V1370/V1372/V1373 results to decide what Android participant or endpoint
      prerequisite is still missing after the v283 powerup-thread gate.
    - Inputs: V1379 manifest/report, focused V1379 dmesg/pcie kmsg evidence,
      Android V852 RC1 L0 timing, V1370 isolated corrected-RC1 enumerate,
      V1372 raw provider-held enumerate, and V1373 parity classifier.
    - Required output: source/evidence-backed answer for whether the remaining
      gap is only timing, missing participant/service, endpoint reset/refclk
      readiness, or a lower SDX50M response condition. It must select exactly
      one next candidate or explicitly stop live mutation.
    - Hard stop: host-only. No device command, debugfs/sysfs write,
      `rc_sel`/`case` write, PMIC/GPIO/GDSC write, eSoC notify/`BOOT_DONE`,
      Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, flash,
      boot image write, or partition write.
    - Result:
      `docs/reports/NATIVE_INIT_V1380_RC1_LTSSM_PARTICIPANT_GAP_CLASSIFIER_2026-06-01.md`.
      Decision: `v1380-v1379-rc1-action-too-late-for-android-window`. V1379
      fixed the v283 gate and executed `rc_sel=2`/`case=11`, but the action
      occurred about `4.123s` after `__subsystem_get(esoc0)`. Android's
      reference path asserts RC1 about `0.255s` after `esoc0` and reaches L0
      about `0.017s` after reset release. V1379 still failed before L0 with no
      GPIO142, PCI/MHI, WLFW, or `wlan0`, so the next implementation should
      move the corrected RC1 write earlier, before expensive snapshots/samplers.
29. **V1381 immediate corrected RC1 gate support (source/build-only).**
    - Goal: bump helper to v284 and add a mode/flag path that writes corrected
      `rc_sel=2` + `case=11` immediately when
      `pm_service_powerup_thread_count > 0`, then samples the post-enumerate
      MDM2AP/PCI/MHI/WLFW/`wlan0` window.
    - Rationale: V1380 shows V1379's current helper ordering runs the RC1
      action far outside the Android esoc0-to-RC1 timing window. V1381 must
      change ordering only; no live execution yet.
    - Success criteria: source/build checks prove helper v284 exposes the new
      immediate flag/marker, performs the corrected RC1 write before the
      post-enumerate sampler, reports the gate time and write time, preserves
      existing v283 behavior for old flags, and remains static aarch64.
    - Hard stop: source/build-only. No device command, debugfs/sysfs write,
      `rc_sel`/`case` live write, PMIC/GPIO/GDSC write, eSoC notify/`BOOT_DONE`,
      Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, flash,
      boot image write, or partition write.
    - Result:
      `docs/reports/NATIVE_INIT_V1381_IMMEDIATE_CORRECTED_RC1_SUPPORT_2026-06-01.md`.
      Decision: `v1381-helper-v284-immediate-corrected-rc1-ready`. Helper
      `a90_android_execns_probe v284` (SHA256
      `da1f8b65cbc3872f7ec31a368bd382720a399d3a785e50ae383c800632047b9f`)
      exposes the new immediate flag, validates required samplers, writes
      corrected RC1 before the sampler branch, emits a monotonic write timestamp,
      and preserves the legacy delayed path for old flags. No device command was
      run.
30. **V1382 execns helper v284 deploy/preflight.**
    - Goal: deploy `a90_android_execns_probe v284` to `/cache/bin/` and prove
      on-device SHA/version/usage markers before any immediate-RC1 live run.
    - Required checks: local SHA matches V1381, deployed SHA matches, helper
      usage exposes `a90_android_execns_probe v284` and the immediate corrected
      RC1 flag; V1381 source/build evidence covers internal output markers such
      as `response_sampler.immediate_corrected_rc1_enumerate_enabled` and
      `gate_pm_service_powerup_thread_count`; post selftest remains `fail=0`.
    - Hard stop: deploy/preflight only. No daemon start, no `rc_sel`/`case`
      write, no PMIC/GPIO/GDSC direct write, no eSoC notify/`BOOT_DONE`, no
      Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, flash,
      boot image write, or partition write.
    - Result:
      `docs/reports/NATIVE_INIT_V1382_EXECNS_HELPER_V284_DEPLOY_2026-06-01.md`.
      Decision: `execns-helper-v284-deploy-pass`. Helper v284 was installed to
      `/cache/bin/a90_android_execns_probe`; NCM was not reachable so `auto`
      selected serial fallback (`1061` chunks, chunk size `1800`, max cmdv1
      line `3788` under safe limit `3968`). Post-deploy SHA matched, usage
      printed the v284 marker and immediate flag, V373 preflight remained
      approval-required, and post selftest stayed clean. No daemon start or
      Wi-Fi bring-up occurred.
31. **V1383 bounded immediate corrected RC1 live gate.**
    - Goal: rerun the Android participant path with helper v284 and
      `--pm-observer-late-per-proxy-immediate-corrected-rc1-enumerate`, so
      corrected RC1 enumerate fires in the first poll where the powerup-thread
      gate is positive, before expensive response/timing sampling.
    - Success criteria: capture `__subsystem_get(esoc0)` to corrected-RC1
      action delta, compare it against the Android reference (`~0.255s`), and
      record GPIO142, PCI, MHI, MHI pipe/`ks`, WLFW, and `wlan0` transitions. A
      clean failure before L0 is still useful if timing is now near Android and
      cleanup/selftest remain clean.
    - Hard stop: bounded live only below Wi-Fi bring-up. No Wi-Fi HAL,
      scan/connect, credentials, DHCP/routes, external ping, PMIC/GPIO/GDSC
      direct write, eSoC notify/`BOOT_DONE`, flash, boot image write, or
      partition write.
    - Result:
      `docs/reports/NATIVE_INIT_V1383_ANDROID_PARTICIPANT_IMMEDIATE_CORRECTED_RC1_LIVE_2026-06-01.md`.
      Decision: `v1383-corrected-rc1-ltssm-no-downstream-clean`. The immediate
      flag fired at `late_per_proxy_poll_00` with
      `gate_pm_service_powerup_thread_count=1`, `rc_sel_rc=0`, and `case_rc=0`.
      Dmesg shows RC1 LTSSM activity and link failure before L0, but
      `__subsystem_get(esoc0)` to RC1 assert was still about `3.666s` versus
      Android's about `0.255s`; GPIO142, PCI/MHI, MHI pipe/`ks`, WLFW, and
      `wlan0` stayed absent. Safety markers remained clear and no Wi-Fi
      bring-up/network action occurred.
32. **V1384 V1383 timing/gap classifier (host-only).**
    - Goal: classify why V1383 still asserts RC1 about `3.666s` after
      `__subsystem_get(esoc0)` despite the immediate flag, and compare LTSSM
      phase/timing against V1379 and Android V852/V1371.
    - Required output: determine whether the remaining gap is helper polling
      latency, delayed `per_proxy`/Binder participant startup, debugfs write
      latency, endpoint non-readiness despite earlier write, or an Android-only
      participant that must occur before RC1 enumerate.
    - Hard stop: host-only. No device command, debugfs/sysfs write,
      `rc_sel`/`case` write, PMIC/GPIO/GDSC direct write, eSoC notify/`BOOT_DONE`,
      Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, flash,
      boot image write, or partition write.
    - Result:
      `docs/reports/NATIVE_INIT_V1384_V1383_TIMING_GAP_CLASSIFIER_2026-06-01.md`.
      Decision: `v1384-immediate-flag-still-too-late-poll-entry-gap`. V1383
      improved `esoc0`-to-RC1 assert by only about `0.456s` versus V1379 and
      remains about `14.38x` slower than Android. Debugfs write latency is not
      primary (`TEST 11` to assert about `20us`); the remaining gap is before
      the write, in late_per_proxy poll entry or per_proxy/Binder/powerup-thread
      ordering.
33. **V1385 earlier RC1 trigger/instrumentation support (source/build-only).**
    - Goal: update the helper so the next live gate can either trigger corrected
      RC1 earlier than the late_per_proxy poll loop or record tighter monotonic
      timestamps around `per_proxy` start, pm-service powerup-thread first
      observation, and debugfs write start/return.
    - Required output: source/build-only helper bump, exact new markers, static
      aarch64 artifact, and fail-closed validation that no live action runs in
      V1385.
    - Hard stop: source/build-only. No device command, debugfs/sysfs write,
      `rc_sel`/`case` live write, PMIC/GPIO/GDSC direct write, eSoC
      notify/`BOOT_DONE`, Wi-Fi HAL, scan/connect, credentials, DHCP/routes,
      external ping, flash, boot image write, or partition write.
    - Result:
      `docs/reports/NATIVE_INIT_V1385_PREPOLL_CORRECTED_RC1_SUPPORT_2026-06-01.md`.
      Decision: `v1385-helper-v285-prepoll-corrected-rc1-ready`. Helper v285
      exposes the pre-poll corrected RC1 flag, validates required samplers,
      reports pre-poll mode markers, and adds a 1ms gate loop immediately after
      late `per_proxy` spawn and before the main sampler loop. No device command
      was run.
34. **V1386 execns helper v285 deploy/preflight.**
    - Goal: deploy `a90_android_execns_probe v285` to `/cache/bin/` and prove
      SHA/version/usage markers before any pre-poll RC1 live run.
    - Hard stop: deploy/preflight only. No daemon start, no `rc_sel`/`case`
      write, no PMIC/GPIO/GDSC direct write, no eSoC notify/`BOOT_DONE`, no
      Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, flash,
      boot image write, or partition write.
    - Result:
      `docs/reports/NATIVE_INIT_V1386_EXECNS_HELPER_V285_DEPLOY_2026-06-01.md`.
      Decision: `execns-helper-v285-deploy-pass`. Helper v285 was installed to
      `/cache/bin/a90_android_execns_probe`; NCM was not reachable so `auto`
      selected serial fallback (`1061` chunks, chunk size `1800`, max cmdv1
      line `3788` under safe limit `3968`). Post-deploy SHA matched, usage
      printed the v285 marker and pre-poll flag, V373 preflight remained
      approval-required, and post selftest stayed clean. No daemon start or
      Wi-Fi bring-up occurred.
35. **V1387 bounded pre-poll corrected RC1 live gate.**
    - Goal: rerun the Android participant path with helper v285 and
      `--pm-observer-late-per-proxy-prepoll-corrected-rc1-enumerate`, then
      compare `__subsystem_get(esoc0)` to RC1 assert timing against Android.
    - Hard stop: bounded live only below Wi-Fi bring-up. No Wi-Fi HAL,
      scan/connect, credentials, DHCP/routes, external ping, PMIC/GPIO/GDSC
      direct write, eSoC notify/`BOOT_DONE`, flash, boot image write, or
      partition write.
    - Result:
      `docs/reports/NATIVE_INIT_V1387_ANDROID_PARTICIPANT_PREPOLL_CORRECTED_RC1_LIVE_2026-06-01.md`.
      Decision: `v1387-corrected-rc1-ltssm-no-downstream-clean`. The helper v285
      pre-poll block triggered immediately at `late_per_proxy_prepoll_000`
      (`prepoll_triggered=true`, `poll_count=0`, `elapsed_ms=119`) and wrote
      corrected RC1 debugfs controls successfully (`rc_sel_rc=0`, `case_rc=0`).
      Dmesg saw RC1 TEST 11, reset assert/release, PHY ready, poll-compliance,
      and link failure before L0. However `__subsystem_get(esoc0)` to RC1 assert
      remained about `3.561s` versus Android's about `0.255s`; GPIO142, PCI/MHI,
      MHI pipe/`ks`, WLFW, and `wlan0` stayed absent. Safety markers remained
      clear.
36. **V1388 V1387 timing/participant classifier (host-only).**
    - Goal: classify why even the V1387 pre-poll gate still reaches RC1 too
      late. Compare V1387, V1383, V1379, Android V852/V1371 timing, and the
      helper ordering around late `per_proxy`, Binder `pm-service`, and
      `mdm_subsys_powerup`.
    - Required output: decide whether the next design must start Android
      participants earlier, split `per_proxy` startup from corrected RC1 action,
      instrument first Binder request timing more tightly, or stop live mutation
      and return to Android reference capture.
    - Hard stop: host-only. No device command, debugfs/sysfs write,
      `rc_sel`/`case` write, PMIC/GPIO/GDSC direct write, eSoC notify/
      `BOOT_DONE`, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external
      ping, flash, boot image write, or partition write.
    - Result:
      `docs/reports/NATIVE_INIT_V1388_V1387_TIMING_PARTICIPANT_CLASSIFIER_2026-06-01.md`.
      Decision: `v1388-prepoll-gate-works-but-helper-enters-it-too-late`.
      V1387 proves the v285 pre-poll code path works, but it starts about
      `3.556s` after `__subsystem_get(esoc0)` and only improves V1383 by
      `0.106s`. The observer already saw a `pm-service`
      `mdm_subsys_powerup` thread at `thread_sample index=1` before
      `late_per_proxy.begin`, so the next correction must move the RC1 write
      into that earlier observer phase.
37. **V1389 early-observer corrected RC1 trigger support (source/build-only).**
    - Goal: bump helper to v286 and add an opt-in early-observer corrected RC1
      trigger that fires on the first `pm_service_powerup_thread` observation
      before response-sampler/proc-map/CNSS snapshots and before the late
      `per_proxy` response-sampler block.
    - Required output: new fail-closed flag/markers, static aarch64 helper,
      source checks proving old v285 paths remain unchanged unless the new flag
      is set, and marker fields for early gate time, phase, `rc_sel_rc`,
      `case_rc`, and whether debugfs control writes executed.
    - Hard stop: source/build-only. No device command, helper deploy,
      debugfs/sysfs live write, `rc_sel`/`case` live write,
      PMIC/GPIO/GDSC direct write, eSoC notify/`BOOT_DONE`, Wi-Fi HAL,
      scan/connect, credentials, DHCP/routes, external ping, flash, boot image
      write, or partition write.
    - Result:
      `docs/reports/NATIVE_INIT_V1389_EARLY_POWERUP_CORRECTED_RC1_SUPPORT_2026-06-01.md`.
      Decision: `v1389-helper-v286-early-powerup-corrected-rc1-ready`.
      Helper v286 built as static aarch64 with sha256
      `e5fc81a5becb2c6e6efd2ca026800560ed9e0e72a692f0fbb07861cf26d5380f`.
      The new `--pm-observer-early-powerup-corrected-rc1-enumerate` path is
      opt-in, requires the existing response/timing samplers, rejects ambiguous
      combinations with late/immediate/pre-poll RC1 modes, reports early
      phase/timing/write-state markers, and fail-closes without falling back to
      later RC1 writes when the early powerup gate is absent. No device command,
      helper deploy, live write, Wi-Fi bring-up/network action, flash, boot
      image write, or partition write occurred.
38. **V1390 deploy helper v286 (deploy/preflight-only).**
    - Goal: put the exact V1389 helper v286 on-device and verify marker,
      sha256, usage, and selftest before any live RC1 action.
    - Required output: deployed helper reports `a90_android_execns_probe v286`,
      sha256 matches
      `e5fc81a5becb2c6e6efd2ca026800560ed9e0e72a692f0fbb07861cf26d5380f`,
      new early-observer flag appears in usage, and post-deploy selftest has no
      new failures.
    - Hard stop: deploy/preflight only. No daemon start, no debugfs/sysfs live
      write, no `rc_sel`/`case` write, no PCI rescan, no PMIC/GPIO/GDSC direct
      write, no eSoC notify/`BOOT_DONE`, no Wi-Fi HAL, no scan/connect, no
      credentials, no DHCP/routes, no external ping, no flash, no boot image
      write, and no partition write.
    - Result:
      `docs/reports/NATIVE_INIT_V1390_EXECNS_HELPER_V286_DEPLOY_2026-06-01.md`.
      Decision: `execns-helper-v286-deploy-pass`. Remote helper
      `/cache/bin/a90_android_execns_probe` now matches v286 sha256
      `e5fc81a5becb2c6e6efd2ca026800560ed9e0e72a692f0fbb07861cf26d5380f`,
      and usage prints both `a90_android_execns_probe v286` and
      `--pm-observer-early-powerup-corrected-rc1-enumerate`. NCM was not
      reachable, so `auto` used serial appendfile + uudecode fallback
      (`1061` chunks, max cmdv1 line `3788` bytes below safe limit `3968`).
      Post-deploy selftest stayed `pass=11 warn=1 fail=0`. No daemon start,
      Wi-Fi bring-up/network action, flash, boot image write, or partition
      write occurred.
39. **V1391 early-observer corrected RC1 live gate (bounded live).**
    - Goal: run the Android-participant parity window with helper v286 and fire
      corrected RC1 from the early observer phase where `pm-service`
      `mdm_subsys_powerup` is first visible, not from the later response
      sampler.
    - Required output: confirm
      `pm_service_trigger_observer.early_powerup_corrected_rc1.triggered=1`,
      phase `early_powerup_observer`, `rc_sel_rc=0`, `case_rc=0`, and
      `response_sampler.debugfs_control_write_executed=1` or an explicit
      fail-closed skip reason. Compare `__subsystem_get(esoc0)` to RC1 assert
      timing against Android, and capture GPIO142, PCI/MHI, MHI pipe/`ks`,
      WLFW, and `wlan0` counts.
    - Hard stop: bounded corrected RC1 live gate only. No PMIC/GPIO/GDSC direct
      write, no blind eSoC notify/`BOOT_DONE` spoof, no Wi-Fi HAL, no
      scan/connect, no credentials, no DHCP/routes, no external ping, no flash,
      no boot image write, and no partition write.
    - Result:
      `docs/reports/NATIVE_INIT_V1391_ANDROID_PARTICIPANT_EARLY_POWERUP_CORRECTED_RC1_LIVE_2026-06-01.md`.
      Decision: `v1391-corrected-rc1-ltssm-no-downstream-clean`. The helper
      v286 early gate fired (`corrected_phase=early_powerup_observer`,
      `early_triggered=True`, `gate_pm_service_powerup_thread_count=1`,
      `rc_sel_rc=0`, `case_rc=0`), but RC1 assert still followed
      `__subsystem_get(esoc0)` by about `3.605s`. Dmesg saw RC1 TEST 11,
      reset assert/release, PHY ready, poll-compliance, and link failure before
      L0; GPIO142 IRQ delta, PCI/MHI counts, MHI pipe/`ks`, WLFW, and `wlan0`
      remained absent. Safety markers stayed clear and no Wi-Fi HAL,
      scan/connect, credentials, DHCP/routes, external ping, flash, boot image
      write, or partition write occurred.
40. **V1392 Wi-Fi test boot design (host/source plan).**
    - Goal: stop spending cycles on same-shape external helper timing retries
      and define a separate rollbackable native-init Wi-Fi test boot image that
      moves the timing-critical observer/trigger sequence into PID1/boot flow.
    - Required output: document the selected architecture, artifact boundaries,
      safety scope, rollback rules, and the V1393/V1394/V1395 gate sequence.
    - Hard stop: planning/source-audit only. No generated test image flash, no
      boot partition write, no partition write, no Wi-Fi HAL, no scan/connect,
      no credentials, no DHCP/routes, no external ping, no PMIC/GPIO/GDSC
      direct write, and no blind eSoC notify/`BOOT_DONE` spoof.
    - Result:
      `docs/plans/NATIVE_INIT_V1392_WIFI_TEST_BOOT_PLAN_2026-06-01.md`.
      Decision: `v1392-plan-wifi-test-boot-pid1-timing-path`. V1392 selects a
      dedicated test boot image, keeps `stage3/boot_linux_v724.img` as the
      rollback target, and chooses a ramdisk-bundled
      `/bin/a90_android_execns_probe` helper invoked from PID1/boot flow as the
      V1393 source/build-only path. The first test-boot objective is
      MDM2AP/GPIO142, RC1 L0, MHI, WLFW service `69`, or `wlan0` evidence only;
      credentialed scan/connect and external ping stay deferred until `wlan0`
      is stable.
41. **V1393 Wi-Fi test boot source/build (local-only).**
    - Goal: implement the V1392 selected path without flashing by adding a
      compile-time PID1 test hook, bundling the verified helper into the ramdisk,
      and staging a separate boot artifact under `tmp`.
    - Required output: static aarch64 PID1/helper builds, ramdisk entries,
      marker checks, private staged artifact mode, no-secret artifact check, and
      a manifest with SHA256 values.
    - Hard stop: source/build-only. No device command, no flash, no reboot, no
      boot partition write, no partition write, no Wi-Fi HAL, no scan/connect,
      no credentials, no DHCP/routes, no external ping, no PMIC/GPIO/GDSC
      direct write, and no blind eSoC notify/`BOOT_DONE` spoof.
    - Result:
      `docs/reports/NATIVE_INIT_V1393_WIFI_TEST_BOOT_SOURCE_BUILD_2026-06-01.md`.
      Decision: `v1393-wifi-test-boot-source-build-pass`. The staged artifact is
      `tmp/wifi/v1393-wifi-test-boot/boot_linux_v1393_wifi_test.img`
      (`sha256=ebb4097db71dee77cdf7a26b671a1535a8e0afe1e53b4a23400af518d4d63048`),
      built as `A90 Linux init 0.9.69 (v1393-wifitest)` from v724
      header/kernel metadata. The ramdisk includes
      `/bin/a90_android_execns_probe` with helper marker
      `a90_android_execns_probe v286`. The build verified static binaries,
      required ramdisk entries, expected boot markers, private artifact modes,
      and forbidden credential-like byte patterns.
42. **V1394 Wi-Fi test boot artifact sanity (local-only).**
    - Goal: independently verify the exact V1393 staged boot artifact before
      any live flash/handoff.
    - Required output: manifest decision/SHA checks, base boot availability,
      static PID1/helper verification, ramdisk helper inclusion, expected boot
      markers, v724 header/kernel parity, private modes, and forbidden
      credential-like byte absence.
    - Hard stop: local-only artifact verifier. No device command, no flash, no
      reboot, no boot partition write, no partition write, no Wi-Fi HAL, no
      scan/connect, no credentials, no DHCP/routes, no external ping, no
      PMIC/GPIO/GDSC direct write, and no blind eSoC notify/`BOOT_DONE` spoof.
    - Result:
      `docs/reports/NATIVE_INIT_V1394_WIFI_TEST_BOOT_ARTIFACT_SANITY_2026-06-01.md`.
      Decision: `v1394-wifi-test-boot-artifact-sanity-pass`. The exact V1393
      staged artifact passed local sanity checks. The boot image remains
      `tmp/wifi/v1393-wifi-test-boot/boot_linux_v1393_wifi_test.img`
      (`sha256=ebb4097db71dee77cdf7a26b671a1535a8e0afe1e53b4a23400af518d4d63048`).
43. **V1395 Wi-Fi test boot live handoff (bounded live with rollback).**
    - Goal: flash the V1393 test boot image, collect below-connect boot
      evidence, and roll back to v724.
    - Required output: test image flash/readback/verify evidence, V1393 version
      and boot status, V1393 boot log, dmesg grep for provider/RC1/MHI/WLFW
      markers, `wlan0` presence check, and rollback verification.
    - Hard stop: test boot flash plus rollback only. No Wi-Fi HAL, no
      scan/connect, no credentials, no DHCP/routes, no external ping, no
      PMIC/GPIO/GDSC direct write, and no blind eSoC notify/`BOOT_DONE` spoof.
    - Result:
      `docs/reports/NATIVE_INIT_V1395_WIFI_TEST_BOOT_HANDOFF_2026-06-01.md`.
      Decision: `v1395-test-boot-provider-trigger-no-downstream-rollback-pass`.
      The test boot verified `A90 Linux init 0.9.69 (v1393-wifitest)`, spawned
      the ramdisk helper, reached `subsys_modem` and `__subsystem_get: esoc0`,
      and rolled back to healthy `A90 Linux init 0.9.68 (v724)`. No RC1 L0,
      MHI, WLFW/BDF, or `wlan0` appeared; `wlan0` stayed absent. V1395 collected
      immediately after bridge verification, so the helper's `30s` window was
      likely cut short by rollback.
44. **V1396 Wi-Fi test boot hold handoff (bounded live with rollback).**
    - Goal: rerun the same V1393 test boot with an explicit post-boot hold
      before collecting evidence and rolling back, closing the V1395
      short-window ambiguity.
    - Required output: test image flash/readback/verify evidence, V1393 version
      and boot status, post-boot hold evidence, V1393 boot log, dmesg grep for
      provider/RC1/MHI/WLFW markers, `wlan0` presence check, and rollback
      verification.
    - Hard stop: test boot flash plus rollback only. No Wi-Fi HAL, no
      scan/connect, no credentials, no DHCP/routes, no external ping, no
      PMIC/GPIO/GDSC direct write, and no blind eSoC notify/`BOOT_DONE` spoof.
    - Result:
      `docs/reports/NATIVE_INIT_V1396_WIFI_TEST_BOOT_HOLD_HANDOFF_2026-06-01.md`.
      Decision: `v1396-test-boot-provider-trigger-no-downstream-rollback-pass`.
      The test boot verified `A90 Linux init 0.9.69 (v1393-wifitest)`, held for
      `40s`, reached the PID1-launched helper path, `subsys_modem`, and
      `__subsystem_get: esoc0`, then rolled back to healthy
      `A90 Linux init 0.9.68 (v724)`. No `PCIe RC1`, `LTSSM`, MHI, WLFW/BDF, or
      `wlan0` marker appeared after the hold; `wlan0` stayed absent. V1396
      closes the immediate-rollback explanation and moves the next useful work
      to test-boot logging/observability cleanup.
45. **V1397 Wi-Fi test boot logging source/build (local-only).**
    - Goal: improve the separate Wi-Fi test boot's per-boot observability before
      another live handoff, so the PID1-launched helper produces a clean log and
      summary instead of appending across old boots.
    - Required output: source/build-only hook changes, V1397 boot artifact,
      manifest SHA256 values, fresh log/summary paths, handoff runner parameter
      support, and no-secret artifact checks.
    - Hard stop: source/build/local artifact only. No device command, no flash,
      no reboot, no boot partition write, no partition write, no Wi-Fi HAL, no
      scan/connect, no credentials, no DHCP/routes, no external ping, no
      PMIC/GPIO/GDSC direct write, and no blind eSoC notify/`BOOT_DONE` spoof.
    - Result:
      `docs/reports/NATIVE_INIT_V1397_WIFI_TEST_BOOT_LOGGING_SOURCE_BUILD_2026-06-01.md`.
      Decision: `v1397-wifi-test-boot-logging-source-build-pass`. The PID1 hook
      now truncates the per-boot log, initializes a summary file, and spawns a
      non-blocking `35s` watcher that samples helper liveness, helper `wchan`,
      helper `/proc` status, `wlan0` presence, and log size. The V1397 artifact
      is `tmp/wifi/v1397-wifi-test-boot/boot_linux_v1397_wifi_test.img`
      (`sha256=8bb427c1567b1e4d466b17d5db72db3184132e7087ba0c6d2e5682f00ddeb376`),
      built as `A90 Linux init 0.9.70 (v1397-wifitest)`. The handoff runner now
      accepts configurable expected-version/log/summary/dmesg parameters for a
      later V1397 live gate.
46. **V1398 Wi-Fi test boot artifact sanity (local-only).**
    - Goal: independently verify the exact V1397 staged artifact before any
      live flash/handoff.
    - Required output: manifest decision/SHA checks, base boot availability,
      static PID1/helper verification, ramdisk helper inclusion, expected boot
      markers, Wi-Fi test logging contract, v724 header/kernel parity, private
      modes, and forbidden credential-like byte absence.
    - Hard stop: local-only artifact verifier. No device command, no flash, no
      reboot, no boot partition write, no partition write, no Wi-Fi HAL, no
      scan/connect, no credentials, no DHCP/routes, no external ping, no
      PMIC/GPIO/GDSC direct write, and no blind eSoC notify/`BOOT_DONE` spoof.
    - Result:
      `docs/reports/NATIVE_INIT_V1398_WIFI_TEST_BOOT_ARTIFACT_SANITY_2026-06-01.md`.
      Decision: `v1398-wifi-test-boot-artifact-sanity-pass`. The exact V1397
      artifact passed local sanity checks for manifest decision, SHA values,
      static PID1/helper, ramdisk entries, boot markers, Wi-Fi test logging
      contract, v724 header/kernel parity, private modes, and forbidden
      credential-like byte absence.
47. **V1399 Wi-Fi test boot logging handoff (bounded live with rollback).**
    - Goal: flash the V1397 logging test boot, hold long enough for the `35s`
      summary watcher, collect fresh log/summary/dmesg/`wlan0` evidence, and
      roll back to v724.
    - Required output: V1397 flash/readback/verify evidence, V1397 version and
      boot status, post-boot hold evidence, V1397 fresh log, V1397 summary,
      dmesg grep for provider/RC1/MHI/WLFW markers, `wlan0` presence check, and
      rollback verification.
    - Hard stop: test boot flash plus rollback only. No Wi-Fi HAL, no
      scan/connect, no credentials, no DHCP/routes, no external ping, no
      PMIC/GPIO/GDSC direct write, and no blind eSoC notify/`BOOT_DONE` spoof.
    - Result:
      `docs/reports/NATIVE_INIT_V1399_WIFI_TEST_BOOT_LOGGING_HANDOFF_2026-06-01.md`.
      Decision: `v1399-test-boot-provider-trigger-no-downstream-rollback-pass`.
      The V1397 test boot verified `A90 Linux init 0.9.70 (v1397-wifitest)`,
      wrote a fresh V1397 log/summary, reached `subsys_modem` and
      `__subsystem_get: esoc0`, and rolled back to healthy
      `A90 Linux init 0.9.68 (v724)`. The summary watcher sampled after
      `35001ms` and found the helper process in `State: Z (zombie)`. No `PCIe
      RC1`, `LTSSM`, MHI, WLFW/BDF, or `wlan0` marker appeared; `wlan0` stayed
      absent.
48. **V1400 Wi-Fi test boot supervisor source/build (local-only).**
    - Goal: convert the test boot from direct PID1 helper spawn to a
      non-blocking supervisor child so helper exit status and timeout can be
      observed without blocking PID1.
    - Required output: source/build-only hook changes, V1400 boot artifact,
      manifest SHA256 values, supervised-helper contract fields, and no-secret
      artifact checks.
    - Hard stop: source/build/local artifact only. No device command, no flash,
      no reboot, no boot partition write, no partition write, no Wi-Fi HAL, no
      scan/connect, no credentials, no DHCP/routes, no external ping, no
      PMIC/GPIO/GDSC direct write, and no blind eSoC notify/`BOOT_DONE` spoof.
    - Result:
      `docs/reports/NATIVE_INIT_V1400_WIFI_TEST_BOOT_SUPERVISOR_SOURCE_BUILD_2026-06-01.md`.
      Decision: `v1400-wifi-test-boot-supervisor-source-build-pass`. PID1 now
      forks a non-blocking supervisor child in supervised builds; the supervisor
      spawns the helper, waits with a bounded `40s` timeout, and writes helper
      wait result, timeout state, raw wait status, exit code or signal, log
      size, and `wlan0` presence into the summary. The V1400 artifact is
      `tmp/wifi/v1400-wifi-test-boot/boot_linux_v1400_wifi_test.img`
      (`sha256=461d69cdf9d0680421dea9f77b3f444f028bb4c188a964bd6d7fd98142cdd27c`),
      built as `A90 Linux init 0.9.71 (v1400-wifitest)`.
49. **V1401 Wi-Fi test boot artifact sanity (local-only).**
    - Goal: independently verify the exact V1400 supervised test boot artifact
      before any live flash/handoff.
    - Required output: manifest decision/SHA checks, base boot availability,
      static PID1/helper verification, ramdisk helper inclusion, expected boot
      markers, supervised-helper contract, v724 header/kernel parity, private
      modes, and forbidden credential-like byte absence.
    - Hard stop: local-only artifact verifier. No device command, no flash, no
      reboot, no boot partition write, no partition write, no Wi-Fi HAL, no
      scan/connect, no credentials, no DHCP/routes, no external ping, no
      PMIC/GPIO/GDSC direct write, and no blind eSoC notify/`BOOT_DONE` spoof.
    - Result:
      `docs/reports/NATIVE_INIT_V1401_WIFI_TEST_BOOT_ARTIFACT_SANITY_2026-06-01.md`.
      Decision: `v1401-wifi-test-boot-artifact-sanity-pass`. The exact V1400
      artifact passed local sanity checks for manifest decision, SHA values,
      static PID1/helper, ramdisk entries, boot markers, supervised-helper
      contract, v724 header/kernel parity, private modes, and forbidden
      credential-like byte absence.
50. **V1402 Wi-Fi test boot supervisor handoff (bounded live with rollback).**
    - Goal: flash the V1400 supervised test boot, hold long enough for the
      `40s` supervisor timeout, collect helper exit-status summary plus
      dmesg/`wlan0` evidence, and roll back to v724.
    - Required output: V1400 flash/readback/verify evidence, V1400 version and
      boot status, post-boot hold evidence, V1400 fresh log, V1400 supervised
      summary, dmesg grep for provider/RC1/MHI/WLFW markers, `wlan0` presence
      check, and rollback verification.
    - Hard stop: test boot flash plus rollback only. No Wi-Fi HAL, no
      scan/connect, no credentials, no DHCP/routes, no external ping, no
      PMIC/GPIO/GDSC direct write, and no blind eSoC notify/`BOOT_DONE` spoof.
    - Result:
      `docs/reports/NATIVE_INIT_V1402_WIFI_TEST_BOOT_SUPERVISOR_HANDOFF_2026-06-01.md`.
      Decision: `v1402-test-boot-provider-trigger-no-downstream-rollback-pass`.
      The V1400 test boot verified `A90 Linux init 0.9.71 (v1400-wifitest)`,
      reached `subsys_modem` and `__subsystem_get: esoc0`, recorded
      `helper_wait_rc=0`, `helper_timed_out=0`, `helper_status_raw=0`, and
      `helper_exit_code=0`, then rolled back to healthy
      `A90 Linux init 0.9.68 (v724)`. No `PCIe RC1`, `LTSSM`, MHI, WLFW/BDF, or
      `wlan0` marker appeared; `wlan0` stayed absent.

### Required decision before any new mutation

- V1354 proved pcie1 RC never powers/refclks while the lower provider route is
  reached, and V1355 closed PON parity as the shortest blocker. Therefore the
  next step is not a mutation yet; V1357 live read-only control-surface
  verification found only the bound `pci-msm` platform surface.
- Because debugfs was not mounted in V1357, V1358 may perform a temporary
  debugfs mount/cleanup read-only verifier before declaring `cnss/dev_boot`
  unavailable.
- V1358 proved `cnss/dev_boot` unavailable even with debugfs mounted; the
  remaining path is an ICNSS/pci-msm userspace entry analysis, not CNSS2
  `dev_boot` usage.
- V1359 found no safe userspace `msm_pcie_enumerate(1)` entry in ICNSS/pci-msm
  surfaces. Before any broad `pci-msm` bind/rescan idea, V1360 must inspect
  MHI platform live surfaces read-only.
- V1360 found MHI topology and MHI bus/client-driver surfaces, but no live MHI
  devices or `/dev/mhi*` nodes. V1361 must classify whether these are only
  downstream of PCIe enumeration before any mutation is selected.
- V1361 proved the observed MHI bind/debugfs surfaces are downstream consumers:
  `mhi_pci_probe()` requires an existing `pci_dev`, and MHI client driver bind
  files require existing `mhi_device` instances. The next decision is V1362
  host-only risk classification of the remaining `pci-msm`/PCI rescan options.
- V1362 rejected the remaining userspace mutations: pcie1-specific platform
  unbind/bind is still a proprietary `pci-msm` lifecycle without rollback
  proof, and `drivers_probe`/global PCI rescan are not RC1-specific. Next is
  V1363 host-only feasibility for a kernel-side `msm_pcie_enumerate(1)` shim.
- V1363 supersedes that next step: live read-only debugfs verification found
  `/sys/kernel/debug/pci-msm/case` and `/sys/kernel/debug/pci-msm/rc_sel`, with
  `case` listing `11: ENUMERATE`. Before any write, V1364 must prove the exact
  RC1 contract and observation/cleanup model.
- V1364 proves a likely pci-msm debugfs contract but does not approve
  enumerate. The next live gate is status-only: `rc_sel=1` then `case=26`
  (`OUTPUT PERST AND WAKE GPIO STATUS`) to validate selection/observability
  before considering any enumerate.
- V1365 invalidates the assumption that `case=26` is a safe live stepping
  stone: the write caused command transport loss and prevented after-captures.
  Treat the whole pci-msm `case` debugfs path as unsafe until the proprietary
  call path is proven. Do not attempt `case=11` enumerate from V1365 evidence.
- V1366 corrects the selector model: V1365 targeted RC0, not pcie1. The correct
  pcie1 bitmask would be `rc_sel=2`, but the prior transport loss still blocks
  blind retry. V1367 must be a host-only design choice between corrected RC1
  status-read, kernel-side shim, or Android reference capture.
- V1367 selects the corrected RC1 status-read as the next bounded live gate,
  not enumerate. V1368 may only write `rc_sel=2` and `case=26`, with
  reboot-risk handling and no Wi-Fi bring-up side effects.
- V1368 proves corrected RC1 status-read is clean: `rc_sel=2` + `case=26`
  returns RC1 PERST/WAKE status with no PCI/MHI/link transition. The next
  decision is not Wi-Fi bring-up yet; V1369 must choose an enumerate strategy
  versus kernel shim with explicit rollback/recovery criteria.
- V1369 selects corrected debugfs RC1 enumerate as the next live proof because
  it is the existing source-proven caller of `msm_pcie_enumerate(RC1)` and is
  narrower than a new shim. V1370 still excludes Wi-Fi HAL/network bring-up.
- V1370 proves the corrected enumerate path can reach RC1 PHY/LTSSM training
  without transport loss, but RC1 does not reach L0 and creates no PCI/MHI
  device. The next step is V1371 host-only Android-vs-native LTSSM/source
  classification, not Wi-Fi HAL or another blind live mutation.
- V1371 proves the remaining pcie1 gap is endpoint readiness at PERST release:
  the RC side is no longer missing an enumerate entry. V1372 should combine the
  already-known provider/eSoC hold path with the corrected RC1 enumerate timing;
  it must not start Wi-Fi HAL/network bring-up.
- V1372 proves raw provider-hold plus corrected RC1 enumerate is still not
  enough: the holder reaches `mdm_subsys_powerup`, but RC1 remains below L0 and
  GPIO142/MDM2AP never asserts. V1373 must compare Android's full
  `mdm_helper`/`pm-service` provider path against this raw-holder path before
  any new live mutation.
- V1373 proves the next live design must not retry raw provider-hold or isolated
  RC1 enumerate. The untested narrow path is Android participant parity plus
  corrected RC1 enumerate; V1374 should design that runner first, still below
  Wi-Fi HAL/scan/connect/network.
- V1374 implements the source/build-only support for that path in helper v282.
  V1375 must deploy/preflight the helper before V1376 live. Do not run V1376
  until v282 marker/SHA/usage/selftest are proven on-device.
- V1375 proves helper v282 is on-device and healthy. V1376 may now run the
  bounded Android participant parity + corrected RC1 enumerate gate, still
  below Wi-Fi HAL/scan/connect/network and with reboot cleanup/recovery
  evidence required.
- V1376 proves the corrected RC1 trigger gate must use the observed
  `mdm_subsys_powerup` thread, not `/dev/subsys_esoc0` fd ownership. V1377
  should patch helper v283 before any V1378 retry.
- V1377 implements that helper-side fix in v283 and keeps it source/build-only.
  V1378 is deploy/preflight only; V1379 is the first allowed live rerun of the
  Android participant + corrected RC1 gate, and it must remain below Wi-Fi HAL,
  scan/connect, credentials, DHCP/routes, external ping, PMIC/GPIO/GDSC writes,
  and eSoC notify/`BOOT_DONE` spoofing.
- V1378 proves helper v283 is on-device and healthy. V1379 may now run the
  bounded Android participant parity + corrected RC1 live rerun. It must
  classify transport loss as recovery evidence, not success.
- V1379 proves the fixed gate works and RC1 can transition in the Android
  participant window, but it still does not reach MDM2AP/GPIO142, PCI/MHI,
  WLFW, or `wlan0`. V1380 must be host-only classification; do not run another
  live mutation until that classifier chooses a narrower next action.
- V1386 proves helper v285 is deployed and healthy. V1387 is the first
  bounded live gate allowed to exercise the pre-poll path.
- V1387 proves the pre-poll code path works, but it only moves the corrected
  RC1 write slightly earlier (`3.561s` after `__subsystem_get(esoc0)`, still far
  from Android's about `0.255s`). Do not run another RC1 live mutation until
  V1388 host-only classification explains the late participant/Binder ordering
  and selects a narrower next design.
- V1388 selects the narrower next design: helper v286 should fire corrected RC1
  from the early observer phase where `mdm_subsys_powerup` is already visible,
  before the response sampler and expensive snapshots. V1389 is source/build
  only; V1390 deploy and V1391 live are separate gates.
- V1389 implements that helper v286 support source/build-only and keeps all
  live actions blocked. V1390 may only deploy/preflight the exact v286 helper;
  V1391 is the first bounded live gate that may exercise the early-observer
  corrected RC1 trigger.
- V1390 proves the exact v286 helper is deployed and healthy on-device. V1391
  is now the next gate and may exercise only the bounded early-observer
  corrected RC1 trigger; it must remain below Wi-Fi HAL, scan/connect,
  credentials, DHCP/routes, external ping, PMIC/GPIO/GDSC direct writes, blind
  eSoC notify/`BOOT_DONE`, flash, boot image write, and partition write.
- V1391 proves the early-observer helper gate itself works but still reaches
  RC1 too late (`~3.605s` after `__subsystem_get(esoc0)`) and creates no
  downstream MDM2AP/PCI/MHI/WLFW/`wlan0` progress. Do not spend the next cycle
  on another same-shape external helper retry. V1392 should design a separate,
  rollbackable Wi-Fi test boot image that moves the timing-critical observer/
  trigger sequence into PID1/boot flow, initially stopping at MDM2AP/WLFW/`wlan0`
  evidence before any credentialed scan/connect or external ping.
- V1392 completes that design and selects the ramdisk-bundled helper test-boot
  path. V1393 may be source/build-only: add the separate test boot source and
  builder path, stage a local artifact, verify markers/static helper/no-secret
  output, and do not flash. V1394 should be local artifact sanity verification;
  V1395 is the first possible flash/handoff gate and must name rollback to
  `stage3/boot_linux_v724.img`.
- V1393 completes source/build-only and stages the test boot artifact. V1394
  should be a local-only artifact sanity verifier over the exact staged manifest
  and boot image. It must re-check marker identity, ramdisk helper inclusion,
  rollback image availability, private modes, boot header parity, and no-secret
  output before V1395 is allowed to flash.
- V1394 passes local artifact sanity. V1395 is the first possible bounded live
  handoff: flash only
  `tmp/wifi/v1393-wifi-test-boot/boot_linux_v1393_wifi_test.img`, capture the
  V1393 boot evidence, and rollback to `stage3/boot_linux_v724.img` unless a
  later explicit decision keeps the test boot. V1395 still must not perform
  Wi-Fi scan/connect, credential handling, DHCP/routes, or external ping.
- V1395 proves the test boot can boot and roll back safely, and it reaches the
  eSoC provider trigger, but it does not yet prove the 30s helper window. V1396
  should rerun the same test boot with an explicit post-boot hold before
  collecting dmesg/helper output and rolling back. V1396 still must not perform
  Wi-Fi scan/connect, credential handling, DHCP/routes, or external ping.
- V1396 proves the same test boot still reaches the eSoC provider trigger after
  an explicit `40s` post-boot hold and rolls back safely, but it still produces
  no RC1/MHI/WLFW/`wlan0` downstream marker. The next cycle should not be
  another blind live handoff or a scan/connect gate; V1397 should be
  source/build-only logging cleanup for the Wi-Fi test boot so the
  PID1-launched helper writes a fresh per-boot transcript/summary before any
  V1398/V1399 rebuild/live retry.
- V1397 completes that source/build logging cleanup and stages a new test boot
  artifact. V1398 should be local artifact sanity over the exact V1397 manifest
  and boot image before any live flash. The first later live gate must flash
  only `tmp/wifi/v1397-wifi-test-boot/boot_linux_v1397_wifi_test.img`, expect
  `A90 Linux init 0.9.70 (v1397-wifitest)`, collect the V1397 log and summary,
  then roll back to `stage3/boot_linux_v724.img`.
- V1398 passes local artifact sanity. The next live gate may flash only
  `tmp/wifi/v1397-wifi-test-boot/boot_linux_v1397_wifi_test.img`, expect
  `A90 Linux init 0.9.70 (v1397-wifitest)`, hold long enough for the `35s`
  summary watcher, collect `/cache/native-init-wifi-test-boot-v1397.log` and
  `/cache/native-init-wifi-test-boot-v1397.summary`, then roll back to
  `stage3/boot_linux_v724.img`. It still must not perform Wi-Fi scan/connect,
  credential handling, DHCP/routes, or external ping.
- V1399 proves the V1397 logging handoff works and rollback is safe, but also
  proves the helper has already exited into zombie state by the `35s` summary
  sample. The next cycle should not be another same-shape live handoff. V1400
  should be source/build-only: add a non-blocking supervisor child that spawns
  the helper, waits with a bounded timeout, records exit status/duration/log
  size/`wlan0` state, and leaves PID1 responsive.
- V1400 completes the supervised source/build path and stages a new test boot
  artifact. V1401 should be local artifact sanity over the exact V1400 manifest
  and boot image before any live flash. A later live gate may flash only
  `tmp/wifi/v1400-wifi-test-boot/boot_linux_v1400_wifi_test.img`, expect
  `A90 Linux init 0.9.71 (v1400-wifitest)`, collect the V1400 log and summary,
  then roll back to `stage3/boot_linux_v724.img`.
- V1401 passes local artifact sanity. The next live gate may flash only
  `tmp/wifi/v1400-wifi-test-boot/boot_linux_v1400_wifi_test.img`, expect
  `A90 Linux init 0.9.71 (v1400-wifitest)`, hold long enough for the `40s`
  supervisor timeout, collect `/cache/native-init-wifi-test-boot-v1400.log` and
  `/cache/native-init-wifi-test-boot-v1400.summary`, then roll back to
  `stage3/boot_linux_v724.img`. It still must not perform Wi-Fi scan/connect,
  credential handling, DHCP/routes, or external ping.
- V1402 proves the supervisor path works and the helper exits cleanly with code
  `0`, but still without RC1/MHI/WLFW/`wlan0` progress. The next cycle should
  not be another same-shape live handoff. V1403 should be source/build-only:
  make the helper/test-boot summary emit explicit `provider_trigger`,
  `rc1_progress`, `wlfw_progress`, `wlan0_present`, and `final_decision` keys,
  and classify provider-trigger/no-downstream as non-progress for the Wi-Fi
  objective.
- V1403 completes the strict host-only reclassification layer. Existing V1402
  evidence now produces `handoff_pass=true` but `wifi_progress_pass=false` and
  `final_decision=provider-trigger-no-downstream`. The runner exposes explicit
  `provider_trigger`, `rc1_progress`, `mhi_progress`, `wlfw_progress`,
  `bdf_progress`, `fw_ready_progress`, `wlan0_present`, and `connect_ready`
  fields. The next cycle should target the first missing downstream transition
  after `__subsystem_get: esoc0`; do not advance to scan/connect, credentials,
  DHCP/routes, or external ping until at least RC1/MHI/WLFW/`wlan0` progress is
  proven.
- V1404 stages a narrower test-boot artifact for that missing downstream
  transition: PID1 mounts debugfs before the supervised helper so the existing
  corrected RC1 enumerate path can reach `/sys/kernel/debug/pci-msm/rc_sel` and
  `case` during boot. Local sanity passed for the source/build artifact, but no
  device command or flash occurred. V1405 should independently verify the exact
  V1404 manifest/image before any V1406 rollbackable handoff. V1406, if allowed,
  should collect V1404 log/summary/dmesg and classify whether `TEST: 11`,
  RC1/LTSSM, MHI/WLFW, or `wlan0` appears; it must still stop before
  scan/connect, credentials, DHCP/routes, or external ping.
- V1405 independently verifies the exact V1404 artifact and passes. The next
  action may be V1406 rollbackable live handoff: flash only
  `tmp/wifi/v1404-wifi-test-boot-debugfs/boot_linux_v1404_wifi_test.img`, expect
  `A90 Linux init 0.9.72 (v1404-wifitest)`, collect the V1404 log, summary,
  dmesg, and `wlan0` state, then roll back to `stage3/boot_linux_v724.img`.
  V1406 should classify `debugfs_pci_msm_case_present`, corrected RC1 write
  execution, `TEST: 11`, RC1/LTSSM, MHI/WLFW/BDF, and `wlan0`. No scan/connect,
  credentials, DHCP/routes, or external ping until `wlan0` progress is proven.
- V1406 proves the debugfs-prepared test boot successfully reaches the corrected
  RC1 enumerate path from boot (`TEST: 11`) and produces RC1 PHY/LTSSM activity,
  but still fails before L0 with `LTSSM_STATE:0x3` and no MHI/WLFW/BDF/`wlan0`.
  Rollback to v724 and selftest fail=0 were verified. V1407 should be host-only:
  compare V1406 with Android and V1370/V1371/V1372/V1391 to classify the
  endpoint-readiness delta at PERST/LTSSM, then select the narrowest next
  below-connect action. Keep scan/connect, credentials, DHCP/routes, and
  external ping blocked.
- V1407 host-only comparison passes and classifies V1406 as
  `v1407-test-boot-rc1-trigger-still-late-no-l0`: test-boot debugfs availability
  is fixed, but the corrected RC1 trigger still fires about `3.598s` after
  `esoc0`, matching V1391's late class and far slower than Android's `0.255s`
  reference. V1408 should be source/build-only: split corrected RC1 into a tiny
  PID1-started parallel watcher that performs no service snapshots and writes
  debugfs immediately after the first `esoc0`/powerup condition. Verify that
  artifact locally before any rollbackable live handoff. Keep scan/connect,
  credentials, DHCP/routes, and external ping blocked.
- V1408 source/build passes and stages
  `tmp/wifi/v1408-wifi-test-boot-pid1-rc1-watcher/boot_linux_v1408_wifi_test.img`.
  The test boot has `A90 Linux init 0.9.73 (v1408-wifitest)` and enables a
  PID1-started parallel RC1 watcher. The watcher reads future `/dev/kmsg`
  records, triggers corrected RC1 on the first `esoc0`/powerup marker, records
  `pid1_rc1_watcher_result`, and disables the helper's duplicate
  corrected-RC1 flag. V1409 should independently sanity-check the exact V1408
  manifest/image before any live flash. Keep scan/connect, credentials,
  DHCP/routes, and external ping blocked.
- V1409 local artifact sanity passes for the exact V1408 manifest/image:
  static/header/kernel/ramdisk/marker/forbidden-byte/private-mode checks all
  pass. A V1410 rollbackable live handoff may flash only the V1408 test image,
  expect `A90 Linux init 0.9.73 (v1408-wifitest)`, collect V1408 log, summary,
  RC1 watcher result, dmesg, and `wlan0` state, then roll back to
  `stage3/boot_linux_v724.img`. Keep scan/connect, credentials, DHCP/routes,
  and external ping blocked.
- V1410 rollbackable live handoff booted the V1408 test image and rollback was
  healthy, but strict Wi-Fi progress remained blocked:
  `v1410-test-boot-provider-trigger-no-downstream-wifi-progress-blocked`.
  The PID1 RC1 watcher failed before watching because `/dev/kmsg` is absent
  (`state=open-kmsg-failed rc=-2 errno=2`), while a read-only follow-up confirms
  `/proc/kmsg` is present. V1411 should be source/build-only: add `/proc/kmsg`
  fallback with an initial drain-to-current step before watching future
  `esoc0`/powerup markers. Keep scan/connect, credentials, DHCP/routes, and
  external ping blocked.
- V1411 source/build passes and stages
  `tmp/wifi/v1411-wifi-test-boot-kmsg-fallback/boot_linux_v1411_wifi_test.img`.
  The PID1 RC1 watcher now falls back from absent `/dev/kmsg` to `/proc/kmsg`,
  drains existing records, then watches future `esoc0`/powerup markers. V1412
  should independently sanity-check the exact V1411 manifest/image before any
  live flash. Keep scan/connect, credentials, DHCP/routes, and external ping
  blocked.
- V1412 local artifact sanity passes for the exact V1411 manifest/image:
  static/header/kernel/ramdisk/marker/forbidden-byte/private-mode checks all
  pass. A V1413 rollbackable live handoff may flash only the V1411 test image,
  expect `A90 Linux init 0.9.74 (v1411-wifitest)`, collect V1411 log, summary,
  RC1 watcher result, dmesg, and `wlan0` state, then roll back to
  `stage3/boot_linux_v724.img`. Keep scan/connect, credentials, DHCP/routes,
  and external ping blocked.
- V1413 rollbackable live handoff passes for procedure and downstream RC1
  progress. The `/proc/kmsg` fallback watcher triggered corrected RC1
  successfully (`write_rc=0`), but still failed before L0 with no
  MHI/WLFW/BDF/`wlan0`. Timing is now too early: `esoc0_to_test11` is about
  `0.032s`, while Android reference `esoc0_to_assert` is about `0.255s`.
  V1414 should be source/build-only: add a configurable PID1 RC1 watcher delay
  after the first `esoc0`/powerup marker, initially `250ms`, then rebuild and
  sanity-check before any live handoff. Keep scan/connect, credentials,
  DHCP/routes, and external ping blocked.
- V1414 source/build-only passes and stages
  `tmp/wifi/v1414-wifi-test-boot-delayed-rc1/boot_linux_v1414_wifi_test.img`.
  The V1414 artifact is `A90 Linux init 0.9.75 (v1414-wifitest)` and keeps the
  `/proc/kmsg` PID1 RC1 watcher, but now waits `250ms` after detecting the
  first `esoc0`/powerup marker before issuing corrected RC1 enumerate. The
  watcher result records `detect_elapsed_ms`, `write_elapsed_ms`, and
  `delay_ms`. V1415 should independently sanity-check the exact V1414
  manifest/image before any rollbackable live handoff. Keep scan/connect,
  credentials, DHCP/routes, and external ping blocked.
- V1415 local-only artifact sanity passes for the exact V1414 manifest/image:
  manifest decision, static PID1/helper, ramdisk entries, boot markers,
  delayed-RC1 contract (`rc1_watcher_delay_ms=250`), v724 header/kernel parity,
  forbidden credential-like byte absence, and private modes all pass. A V1416
  rollbackable live handoff may flash only
  `tmp/wifi/v1414-wifi-test-boot-delayed-rc1/boot_linux_v1414_wifi_test.img`,
  expect `A90 Linux init 0.9.75 (v1414-wifitest)`, collect the V1414 log,
  summary, RC1 watcher result, dmesg, and `wlan0` state, then roll back to
  `stage3/boot_linux_v724.img`. Keep scan/connect, credentials, DHCP/routes,
  and external ping blocked.
- V1416 rollbackable live handoff passes for procedure and downstream RC1
  evidence. The V1414 test boot triggered corrected RC1 with the `250ms` delay:
  `esoc0_to_test11` is about `0.275s`, close to Android's about `0.255s`
  reference, but RC1 still fails in `LTSSM_POLL_COMPLIANCE` before L0 with no
  MHI/WLFW/BDF/`wlan0`. Rollback to v724 and selftest fail=0 were verified.
  V1417 should be host-only: compare V1416, V1413, and Android traces to
  classify whether the remaining gap is delay tuning, debugfs `TEST: 11`
  trigger semantics, or endpoint reset/refclk/PERST readiness. Keep
  scan/connect, credentials, DHCP/routes, and external ping blocked.
- V1417 host-only classifier passes with
  `v1417-delayed-rc1-timing-aligned-filtered-dmesg-recapture-needed`. V1416 now
  aligns with Android timing within about `20ms`, so the large early/late timing
  error is no longer the leading explanation. It still fails in
  `LTSSM_POLL_COMPLIANCE` before L0, but the V1416 dmesg grep pattern omitted
  endpoint reset/release strings, so reset/release marker absence is not proven.
  V1418 should rerun the same V1414 test image with an expanded dmesg pattern
  including endpoint reset/release and `PCIE20_PARF_INT` markers before changing
  timing or trigger design. Keep scan/connect, credentials, DHCP/routes, and
  external ping blocked.
- V1418 rollbackable live handoff passes for procedure and downstream RC1
  evidence with expanded dmesg capture. The V1414 test boot now proves the
  corrected RC1 path executes assert reset, `PCIE20_PARF_INT_ALL_MASK`, PHY
  ready, release reset, and LTSSM. Timing is still close to Android:
  `esoc0_to_assert` about `0.277s` vs Android about `0.255s`. RC1 still fails
  in `LTSSM_POLL_COMPLIANCE` before L0, with no MHI/WLFW/BDF/`wlan0`. Rollback
  to v724 and selftest fail=0 were verified. V1419 should be host/source-only:
  design a below-connect endpoint-readiness probe after PERST release, likely a
  read-only GPIO142/interrupt sampler around the RC1 window plus Android V852
  timing comparison. Keep scan/connect, credentials, DHCP/routes, and external
  ping blocked.
- V1419 host/source-only design passes with
  `v1419-endpoint-readiness-sampler-design-ready`. V1420 should build a new
  rollbackable test boot that preserves the V1414 `250ms` delayed-RC1 path but
  adds a read-only PID1 RC1-window sampler. Required snapshots:
  pre-delay, pre-RC1, +50ms, +150ms, and +500ms after RC1 write. Required
  read-only sources: `/proc/interrupts` for GPIO142/`mdm status`/PCIe/MHI,
  debugfs/pinctrl excerpts for GPIO 102/104/135/142 when readable, and ordinary
  read-only PCIe status if available. Do not write pci-msm `case=26` or any
  other `case` in this sampler. Keep scan/connect, credentials, DHCP/routes,
  external ping, PMIC/GPIO/GDSC direct write, eSoC notify/`BOOT_DONE`, global
  PCI rescan, and platform bind/unbind blocked.
- V1420 source/build-only passes with
  `v1420-wifi-test-boot-rc1-window-sampler-source-build-pass`. The generated
  artifact is
  `tmp/wifi/v1420-wifi-test-boot-rc1-window-sampler/boot_linux_v1420_wifi_test.img`
  and carries native init `0.9.76 (v1420-wifitest)`. The artifact preserves the
  V1414 `250ms` delayed corrected-RC1 path and adds a read-only PID1
  RC1-window sampler with private output at
  `/cache/native-init-wifi-test-boot-v1420-rc1-window.result`. V1421 should
  perform host-only artifact sanity against this exact manifest and marker
  contract. V1422 may run a rollbackable live handoff only after V1421 passes.
- V1421 local-only artifact sanity passes with
  `v1421-wifi-test-boot-rc1-window-sampler-artifact-sanity-pass`. The exact
  V1420 artifact passed manifest decision, SHA, static binary, ramdisk entry,
  boot marker, header/kernel parity, forbidden credential-like byte, private
  mode, and RC1-window contract checks. V1422 may now be a rollbackable live
  handoff for this exact image, with mandatory collection of the V1420 log,
  summary, RC1 watcher result, RC1-window result, expanded dmesg markers, and
  `wlan0` state, followed by rollback to v724 and selftest verification.
- V1422 rollbackable live handoff passes with
  `v1422-test-boot-downstream-progress-rollback-pass`, then rolls back to v724
  with selftest fail=0. The test boot collects all five RC1-window samples and
  classifies the current blocker as `rc1-ltssm-link-failed-no-l0`: GPIO135
  remains `out 0`, GPIO142 remains `in 0`, `mdm status` IRQ count remains `0`,
  RC1 reaches PHY/LTSSM but fails before L0, and MHI/WLFW/BDF/FW-ready/`wlan0`
  remain absent. V1423 should be host-only/read-only: compare this V1422 window
  against Android positive evidence to determine whether GPIO135/AP2MDM is
  active-low, pulsed too briefly, or not asserted in native at the comparable
  point. Keep scan/connect, credentials, DHCP/routes, and external ping blocked.
- V1423 host-only/read-only classifier passes with
  `v1423-gpio135-low-is-not-actionable-by-itself`. Android-positive steady-state
  captures also show GPIO135/AP2MDM low, so V1422's GPIO135 low is not enough to
  justify a direct GPIO/PMIC mutation. The actionable delta remains missing
  GPIO142/MDM2AP IRQ, PCIe L0, MHI, WLFW/BDF/FW-ready, and `wlan0`. V1424
  should either perform host-only Android-vs-V1422 timing classification or
  build a higher-frequency read-only RC1/interrupt sampler. Keep connect-side
  work blocked until at least L0/MHI/WLFW/`wlan0` progress appears.
- V1424 host-only/read-only classifier passes with
  `v1424-rc1-timing-precondition-parity-but-endpoint-no-l0`. Android V852
  reaches RC1 assert `254.929ms` after `esoc0`; native V1422 reaches corrected
  RC1 assert `287.384ms` after `esoc0`, a `32.455ms` gap. Reset/release and RC1
  INT mask parity are present. Native diverges after PERST release: Android
  reaches L0 in `16.666ms`, while native fails before L0 after `109.086ms`, with
  no MHI/WLFW/BDF/FW-ready/`wlan0`. V1425 should focus on post-release endpoint
  response, not credential/scan/connect work: either build a higher-resolution
  read-only sampler or design a narrowly justified rollbackable RC1 retry/timing
  experiment.
- V1425 source/build-only passes with
  `v1425-wifi-test-boot-rc1-retry-source-build-pass`. The generated artifact is
  `tmp/wifi/v1425-wifi-test-boot-rc1-retry/boot_linux_v1425_wifi_test.img` with
  native init `0.9.77 (v1425-wifitest)`. It preserves the 250ms delayed
  corrected-RC1 path and adds two bounded corrected-RC1 retries spaced by
  `500ms` after the first write. V1426 should perform local artifact sanity over
  this exact manifest and marker contract. V1427 may live-test only after V1426
  passes, and must roll back to v724/selftest afterward.
- V1426 local-only artifact sanity passes with
  `v1426-wifi-test-boot-rc1-retry-artifact-sanity-pass`. The exact V1425 image
  passed manifest, SHA, static binary, ramdisk, boot marker, header/kernel
  parity, forbidden credential-like byte, private mode, and retry contract
  checks. V1427 may now be a rollbackable live handoff for this image, with
  mandatory evidence collection and rollback to v724/selftest.
- V1427 rollbackable live handoff passes with
  `v1427-test-boot-downstream-progress-rollback-pass`, then rolls back to v724
  with selftest fail=0. The V1425 image executed three corrected-RC1 attempts
  total: initial plus two `500ms` retries. All three reached the same
  reset/release/LTSSM path and failed before L0: `TEST: 11` count `3`, link
  failure count `3`, L0 count `0`, no MHI/WLFW/BDF/FW-ready/`wlan0`. V1428
  should stop widening retry count and return to lower endpoint prerequisites:
  RC1 power/refclk/PERST/PMIC state or a narrowly justified pre-RC1 prerequisite
  test. Keep connect-side work blocked until at least L0/MHI/WLFW/`wlan0`
  appears.
- V1428 host-only classifier passes with
  `v1428-rc1-retry-closed-pre-rc1-endpoint-prereq-next`. It closes retry
  widening, GPIO135, PON, provider-held ordering, corrected-RC1 entry, and
  timing as shortest next branches. The next useful gate is V1429 source/build
  only: a read-only Wi-Fi test-boot endpoint-prerequisite sampler around PERST
  release for GPIO102/PERST, GPIO103/CLKREQ, GPIO104/WAKE, `pcie_1_gdsc`,
  refclk/pipe clocks, GPIO142/MDM2AP IRQ, and LTSSM terminal state. Keep it
  below Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping,
  PMIC/GPIO/GDSC direct writes, eSoC notify/`BOOT_DONE`, global PCI rescan,
  platform bind/unbind, flash, boot image write, and partition write.
- V1429 source/build-only passes with
  `v1429-wifi-test-boot-endpoint-prereq-source-build-pass`. It generated
  `tmp/wifi/v1429-wifi-test-boot-endpoint-prereq-sampler/boot_linux_v1429_wifi_test.img`
  with native init `0.9.78 (v1429-wifitest)`. The test boot keeps the 250ms
  corrected-RC1 watcher, removes retry widening (`rc1_retry_count=0`), and adds
  read-only endpoint-prerequisite sampling for GPIO102/PERST, GPIO103/CLKREQ,
  GPIO104/WAKE, `pcie_1_gdsc`, pcie1 refclk/pipe clocks, GPIO142/MDM2AP IRQ,
  pcie1 link state files, and LTSSM terminal state. V1430 should perform
  local-only artifact sanity over this exact manifest and marker contract before
  any live handoff. Keep connect-side work blocked until at least
  L0/MHI/WLFW/`wlan0` progress appears.
- V1430 local-only artifact sanity passes with
  `v1430-wifi-test-boot-endpoint-prereq-artifact-sanity-pass`. It verifies the
  V1429 manifest decision, static init/helper binaries, ramdisk entries, boot
  markers, absence of retry-loop markers, header/kernel parity, forbidden
  credential-like byte absence, private modes, and endpoint sampler contract.
  V1431 may be a rollbackable live handoff for only the V1429 image, expecting
  `A90 Linux init 0.9.78 (v1429-wifitest)`, collecting the V1429 log, summary,
  RC1 watcher result, endpoint window result, expanded dmesg markers, and
  `wlan0` state, then rolling back to `stage3/boot_linux_v724.img` and verifying
  selftest fail=0.
- V1431 rollbackable live handoff passes with
  `v1431-test-boot-downstream-progress-rollback-pass`; rollback returned to
  v724 and selftest fail=0. The test boot still ends at
  `rc1-ltssm-link-failed-no-l0`: RC1/LTSSM progresses, L0 remains false, and
  MHI/WLFW/BDF/FW-ready/`wlan0` remain absent. The new endpoint sampler did
  collect five samples with `read-only-v1429-endpoint-prereq`: GPIO103/CLKREQ
  stayed high/pull-up, `pcie_1_gdsc` and pcie1 clocks briefly enabled around
  `pre_rc1`, then returned off after link failure. V1432 should classify this
  endpoint evidence before any new live mutation; likely next branches are a
  focused sampler refinement or Android-side pcie1 clock/GDSC/CLKREQ parity
  capture.
- V1432 host-only classifier passes with
  `v1432-ap-rc1-prereqs-toggle-but-endpoint-no-l0`. It narrows the blocker:
  the corrected-RC1 path briefly enables AP-side pcie1 GDSC/clocks in the test
  window (`pcie_1_gdsc` enable 0 -> 1 -> 0, pcie1 clocks enabled at `pre_rc1`,
  GPIO103/CLKREQ high/pull-up), but the endpoint still never reaches L0 and
  MHI/WLFW/BDF/FW-ready/`wlan0` remain absent. V1433 should remain host/source
  only first: either refine native sampler output to avoid clock-summary
  truncation and emit exact pcie1 clock/GDSC/PERST/CLKREQ fields, or capture an
  Android-side pcie1 clock/GDSC/CLKREQ reference for the known-good L0 path.
- V1433 source/build-only passes with
  `v1433-wifi-test-boot-focused-endpoint-source-build-pass`. It generated
  `tmp/wifi/v1433-wifi-test-boot-focused-endpoint-sampler/boot_linux_v1433_wifi_test.img`
  with native init `0.9.79 (v1433-wifitest)`. The new focused endpoint sampler
  preserves the V1429 broad sampler and adds exact one-line `focused_*` records
  for pcie1 regulators, clocks, GPIO102/PERST, GPIO103/CLKREQ, GPIO104/WAKE,
  GPIO142/MDM2AP, pinmux, and pinconf. V1434 should perform local-only artifact
  sanity over this exact focused marker contract before any live handoff.
- V1434 local-only artifact sanity passes with
  `v1434-wifi-test-boot-focused-endpoint-artifact-sanity-pass`. It verifies the
  V1433 manifest decision, static init/helper binaries, ramdisk entries, boot
  markers, absence of retry-loop markers, header/kernel parity, forbidden
  credential-like byte absence, private modes, and focused endpoint sampler
  contract. V1435 may be a rollbackable live handoff for only the V1433 image,
  expecting `A90 Linux init 0.9.79 (v1433-wifitest)`, collecting the V1433 log,
  summary, RC1 watcher result, focused endpoint window result, expanded dmesg
  markers, and `wlan0` state, then rolling back to `stage3/boot_linux_v724.img`
  and verifying selftest fail=0.
- V1435 rollbackable live handoff passes with
  `v1435-test-boot-downstream-progress-rollback-pass`, then rolls back to v724
  with selftest fail=0. The V1433 focused test boot still ends at
  `rc1-ltssm-link-failed-no-l0`: RC1/LTSSM progresses, L0 remains false, and
  MHI/WLFW/BDF/FW-ready/`wlan0` remain absent. The focused endpoint sampler
  removed broad summary truncation and recorded exact pcie1 regulator/clock/
  GPIO/pinmux/pinconf lines, but it also shows same-window timing sensitivity:
  broad `pre_rc1` saw `pcie_1_gdsc` and pcie1 clocks enabled, while later
  focused exact `pre_rc1` reads had them already off. V1436 should be
  host-only/read-only classification of this V1435 evidence before any new live
  mutation, with the likely next branch being a tighter in-PID1 immediate
  around-write sampler or Android reference capture. Keep connect-side work
  blocked until at least L0/MHI/WLFW/`wlan0` progress appears.
- V1436 host-only classifier passes with
  `v1436-focused-window-race-endpoint-no-l0`. It validates the V1435 evidence
  without issuing device commands: focused sampler output is present for all
  five samples, GPIO103/CLKREQ remains high, GPIO142/MDM2AP remains low,
  GPIO102/PERST is owned by RC1, and dmesg still shows link failure without
  L0/MHI/WLFW/BDF/FW-ready/`wlan0`. It also explains the apparent V1435
  `pre_rc1` contradiction as sampling-window timing sensitivity, not a stable
  pcie1 GDSC/clock state: broad reads saw enable activity, later focused exact
  reads in the same logical sample saw them off. V1437 should be source/build
  only and tighten the test-boot instrumentation so exact pcie1 GDSC/clocks,
  PERST/CLKREQ/WAKE/MDM2AP, and LTSSM are sampled immediately around the
  `case=11` write inside PID1, or else capture an Android positive reference
  for the same exact fields before any new live mutation.
- V1437 source/build-only passes with
  `v1437-wifi-test-boot-immediate-endpoint-source-build-pass`. It generated
  `tmp/wifi/v1437-wifi-test-boot-immediate-endpoint-sampler/boot_linux_v1437_wifi_test.img`
  with native init `0.9.80 (v1437-wifitest)`, keeps the V1433 focused endpoint
  sampler, and adds `read-only-v1437-immediate-endpoint`. The new immediate
  sampler runs inside the PID1 watcher after the corrected RC1 `case=11` write
  and records exact pcie1 regulator/clock/GPIO/pinmux/pinconf/link-state fields
  at `after_case_0ms`, `after_case_1ms`, `after_case_5ms`, and
  `after_case_20ms`. V1438 should be local-only artifact sanity over this exact
  manifest, marker contract, v724 header/kernel parity, private modes, and
  forbidden credential-like byte absence before any live handoff.
- V1438 local-only artifact sanity passes with
  `v1438-wifi-test-boot-immediate-endpoint-artifact-sanity-pass`. It verifies
  the exact V1437 image, static init/helper binaries, ramdisk entries, immediate
  endpoint sampler markers, retry-marker absence, v724 header/kernel parity,
  forbidden credential-like byte absence, private modes, and the V1437 contract
  (`rc1_immediate_endpoint_sampler=true`, `250ms` watcher delay, retry count
  `0`). V1439 may be a rollbackable live handoff for only the V1437 image,
  expecting `A90 Linux init 0.9.80 (v1437-wifitest)`, collecting the V1437 log,
  summary, RC1 watcher result, immediate endpoint window result, expanded dmesg
  markers, and `wlan0` state, then rolling back to `stage3/boot_linux_v724.img`
  and verifying selftest fail=0.
- V1439 rollbackable live handoff passes with
  `v1439-test-boot-downstream-progress-rollback-pass`, then rolls back to v724
  with selftest fail=0. The V1437 image still reaches corrected RC1/LTSSM but
  fails before L0, and MHI/WLFW/BDF/FW-ready/`wlan0` remain absent. The
  immediate sampler emitted all requested labels, but all immediate pcie1
  GDSC/clock reads were already off and GPIO142 stayed low.
- V1440 host-only classifier passes with
  `v1440-immediate-sampler-too-slow-no-l0`. It explains the V1439 immediate
  evidence: exact debugfs regulator/clock scans are too slow to resolve the
  active RC1 window (`after_case_1ms` landed at `2402ms`, `after_case_20ms` at
  `8634ms`). V1441 should be source/build-only and replace active-window full
  debugfs summary scans with a micro-sampler: a concurrent case writer plus a
  minimal fast reader for the narrowest fields that can be sampled within the
  sub-100ms RC1 window. Keep connect-side work blocked until at least
  L0/MHI/WLFW/`wlan0` progress appears.
- V1441 source/build-only passes with
  `v1441-wifi-test-boot-micro-endpoint-source-build-pass`. It generated
  `tmp/wifi/v1441-wifi-test-boot-micro-endpoint-sampler/boot_linux_v1441_wifi_test.img`
  with native init `0.9.81 (v1441-wifitest)` and adds
  `read-only-v1441-micro-endpoint`. The new sampler forks a concurrent writer
  for corrected `rc_sel=2` and `case=11`, while the parent samples only narrow
  active-window fields: selected interrupts, exact endpoint GPIOs
  (GPIO102/GPIO103/GPIO104/GPIO135/GPIO142), and pcie1 link-state files at
  `0ms`, `1ms`, `2ms`, `5ms`, `10ms`, `20ms`, `50ms`, `100ms`, and `150ms`.
  It deliberately avoids regulator and clock summary scans during the active
  window and keeps one slower `post_micro_200ms` context sample. V1442 should
  be local-only artifact sanity over this exact manifest, marker contract,
  v724 header/kernel parity, private modes, and forbidden credential-like byte
  absence before any live handoff.
- V1442 local-only artifact sanity passes with
  `v1442-wifi-test-boot-micro-endpoint-artifact-sanity-pass`. It verifies the
  exact V1441 manifest, boot image, static init/helper binaries, ramdisk
  entries, micro endpoint marker contract, retry/immediate marker absence,
  v724 header/kernel parity, forbidden credential-like byte absence, private
  modes, and the V1441 contract (`rc1_micro_endpoint_sampler=true`,
  `rc1_endpoint_sampler=true`, `rc1_immediate_endpoint_sampler=false`,
  `rc1_focused_endpoint_sampler=false`, `250ms` watcher delay, retry count
  `0`). V1443 may be a rollbackable live handoff for only the V1441 image,
  expecting `A90 Linux init 0.9.81 (v1441-wifitest)`, collecting the V1441 log,
  summary, RC1 watcher result, micro endpoint window result, dmesg markers, and
  `wlan0` state, then rolling back to `stage3/boot_linux_v724.img` and
  verifying selftest fail=0.
- V1443 rollbackable live handoff passes with
  `v1443-test-boot-downstream-progress-rollback-pass`, then rolls back to v724
  with selftest fail=0. The V1441 image still reaches corrected RC1/LTSSM but
  fails before L0; MHI/WLFW/BDF/FW-ready/`wlan0` remain absent. The micro
  sampler emitted nine `rc1_micro_sample` entries and a successful bounded
  writer summary, but the writer's actual `case=11` completion occurred after
  most parent samples.
- V1444 host-only classifier passes with
  `v1444-micro-sampler-case-write-late-no-l0`. It proves the V1441 micro
  reader started before the actual corrected RC1 `case=11` write returned:
  writer case elapsed `7790ms`, micro start elapsed `7675ms`, case-after-micro
  offset `115ms`, and only `micro_after_case_150ms` landed after the real case
  write. GPIO135 remained `out 0` and GPIO142 remained `in 0` across micro
  samples, while RC1 still failed in LTSSM before L0. V1445 should be
  source/build-only and realign the parent sampling origin to the writer's
  post-`case=11` completion signal before any further live handoff.
- V1445 source/build-only passes with
  `v1445-wifi-test-boot-case-aligned-micro-endpoint-source-build-pass`. It
  generated
  `tmp/wifi/v1445-wifi-test-boot-case-aligned-micro-endpoint-sampler/boot_linux_v1445_wifi_test.img`
  with native init `0.9.82 (v1445-wifitest)` and adds
  `read-only-v1445-case-aligned-micro-endpoint`. The writer still performs
  corrected `rc_sel=2` and `case=11`, but the parent now waits for the writer
  to return, records `rc1_micro_writer_summary`, then starts micro samples at
  `0ms`, `1ms`, `2ms`, `5ms`, `10ms`, `20ms`, `50ms`, `100ms`, and `150ms`
  after confirmed case completion. V1446 should be local-only artifact sanity
  over this exact manifest, marker contract, v724 header/kernel parity, private
  modes, and forbidden credential-like byte absence before any live handoff.
- V1446 local-only artifact sanity passes with
  `v1446-wifi-test-boot-case-aligned-micro-endpoint-artifact-sanity-pass`. It
  verifies the exact V1445 manifest, boot image, static init/helper binaries,
  ramdisk entries, case-aligned micro endpoint marker contract,
  retry/immediate/V1441 marker absence, v724 header/kernel parity, forbidden
  credential-like byte absence, private modes, and the V1445 contract
  (`rc1_case_aligned_micro_endpoint_sampler=true`,
  `rc1_micro_endpoint_sampler=true`, `rc1_endpoint_sampler=true`,
  `rc1_immediate_endpoint_sampler=false`, `rc1_focused_endpoint_sampler=false`,
  `250ms` watcher delay, retry count `0`). V1447 may be a rollbackable live
  handoff for only the V1445 image, expecting
  `A90 Linux init 0.9.82 (v1445-wifitest)`, collecting the V1445 log, summary,
  RC1 watcher result, case-aligned micro endpoint window result, dmesg markers,
  and `wlan0` state, then rolling back to `stage3/boot_linux_v724.img` and
  verifying selftest fail=0.
- V1447 rollbackable live handoff passes with
  `v1447-test-boot-downstream-progress-rollback-pass`, then rolls back to v724
  with selftest fail=0. The V1445 image still reaches corrected RC1/LTSSM but
  fails before L0; MHI/WLFW/BDF/FW-ready/`wlan0` remain absent. The writer
  completed `rc_sel=2` and `case=11` successfully, and all nine case-aligned
  micro samples were collected after confirmed case completion.
- V1448 host-only classifier passes with
  `v1448-case-aligned-micro-all-low-no-l0`. It closes the sampler-alignment
  issue: writer case elapsed was `7793ms`, the first case-aligned parent sample
  landed at `7794ms`, all nine samples were after case completion, GPIO135
  stayed `out 0`, GPIO142 stayed `in 0`, and RC1 still failed in LTSSM before
  L0 with no MHI/WLFW/BDF/FW-ready/`wlan0`. V1449 should be host-only and
  compare provider-trigger timing against RC1 debugfs case timing before any
  further live mutation; do not repeat RC1 case sampling until the
  provider-level AP2MDM/MDM2AP timing question is sharper.
- V1449 host-only timing classifier passes with
  `v1449-provider-precedes-rc1-case-no-l0`. It shows the provider-level
  `__subsystem_get: esoc0` transition occurred at `9.243453s`, while explicit
  RC1 debugfs `TEST: 11` occurred later at `9.520422s`, and RC1 link failed at
  `9.635246s`. The gap between esoc0 and the RC1 case was about `276.969ms`.
  Therefore V1447 proves post-RC1-case GPIO135/GPIO142 stayed low, but it does
  not yet sample the provider transition itself. V1450 should be
  source/build-only and add a provider-trigger micro sampler that watches
  PID1 kmsg for `__subsystem_get: esoc0`/`mdm_subsys_powerup`, then samples
  GPIO135/GPIO142/RC1 status immediately around that provider event without
  Wi-Fi scan/connect or credential handling.
- V1450 source/build-only passes with
  `v1450-wifi-test-boot-provider-trigger-micro-endpoint-source-build-pass`. It
  generated
  `tmp/wifi/v1450-wifi-test-boot-provider-trigger-micro-endpoint-sampler/boot_linux_v1450_wifi_test.img`
  with native init `0.9.83 (v1450-wifitest)` and adds
  `read-only-v1450-provider-trigger-micro-endpoint`. The PID1 watcher keeps the
  provider-level kmsg trigger, sets delay to `0ms`, does not write RC1 debugfs
  `rc_sel`/`case`, and samples selected interrupts, exact endpoint GPIOs, and
  pcie1 link state at `0ms`, `1ms`, `2ms`, `5ms`, `10ms`, `20ms`, `50ms`,
  `100ms`, and `150ms` after provider-trigger detection. V1451 should be
  local-only artifact sanity over this exact manifest, marker contract, v724
  header/kernel parity, private modes, and forbidden credential-like byte
  absence before any live handoff.
- V1451 local-only artifact sanity passes with
  `v1451-wifi-test-boot-provider-trigger-micro-endpoint-artifact-sanity-pass`.
  It verifies the exact V1450 manifest, boot image, static init/helper
  binaries, ramdisk entries, provider-trigger micro endpoint marker contract,
  retry/immediate/case-writer marker absence, v724 header/kernel parity,
  forbidden credential-like byte absence, private modes, and the V1450 contract
  (`provider_trigger_micro_endpoint_sampler=true`,
  `rc1_micro_endpoint_sampler=true`, `rc1_endpoint_sampler=true`,
  `rc1_case_aligned_micro_endpoint_sampler=false`,
  `rc1_immediate_endpoint_sampler=false`, `rc1_focused_endpoint_sampler=false`,
  `0ms` watcher delay, retry count `0`). V1452 may be a rollbackable live
  handoff for only the V1450 image, expecting
  `A90 Linux init 0.9.83 (v1450-wifitest)`, collecting the V1450 log, summary,
  RC1 watcher result, provider-trigger micro endpoint window result, dmesg
  markers, and `wlan0` state, then rolling back to
  `stage3/boot_linux_v724.img` and verifying selftest fail=0.
- V1452 rollbackable live handoff passes with
  `v1452-test-boot-provider-trigger-no-downstream-rollback-pass`. The V1450
  test image booted as `A90 Linux init 0.9.83 (v1450-wifitest)`, collected the
  provider-trigger micro endpoint evidence, then rolled back to
  `A90 Linux init 0.9.68 (v724)` with selftest fail=0. The live result is
  diagnostic, not Wi-Fi bring-up progress: `wlan0=absent`, no RC1/MHI/WLFW/BDF
  or FW-ready marker appeared, GPIO135 stayed `out 0`, GPIO142 stayed `in 0`
  from the provider-trigger `0ms` through `150ms` samples, and pcie1 link-state
  nodes remained unreadable. V1453 should be host-only evidence classification
  over the V1452 files before another test boot is built. Keep all hard
  exclusions: no Wi-Fi HAL, scan/connect, credential handling, DHCP/routes,
  external ping, PMIC/GPIO/GDSC direct write, blind eSoC notify/`BOOT_DONE`
  spoof, global PCI rescan, or platform bind/unbind.
- V1453 host-only classifier passes with
  `v1453-provider-window-low-no-downstream`. It confirms V1452 did not issue an
  explicit RC1 debugfs test, did collect nine provider-window micro samples,
  kept GPIO135 `out 0` and GPIO142 `in 0`, kept MDM status and PCIe wake IRQ
  counts at zero, saw pcie1 GDSC at `0mV` with pcie1 clocks zero-enabled in the
  context sample, and saw no RC1/MHI/WLFW/BDF/FW-ready/`wlan0` progress. The
  remaining measurement weakness is chunk-level `/proc/kmsg` recording: the
  stored line prefix can show an earlier cnss-daemon netlink message even when
  the chunk matched the provider trigger. V1454 should be source/build-only and
  create an exact-line provider-trigger test boot: split kmsg chunks into
  individual lines, trigger only on `__subsystem_get: esoc0` or
  `mdm_subsys_powerup`, keep the run read-only, and extend endpoint samples to
  at least `250ms`, `300ms`, `500ms`, and `1000ms` after the exact provider
  trigger.
- V1454 source/build-only passes with
  `v1454-wifi-test-boot-exact-provider-long-endpoint-source-build-pass`. It
  generated
  `tmp/wifi/v1454-wifi-test-boot-exact-provider-long-endpoint-sampler/boot_linux_v1454_wifi_test.img`
  with native init `0.9.84 (v1454-wifitest)`. The test boot keeps the
  rollbackable V1450 strategy but fixes the measurement weakness: PID1 now
  splits kmsg chunks into individual lines before matching, triggers only on
  the exact `__subsystem_get: esoc0` or `mdm_subsys_powerup` provider line,
  performs no explicit RC1 debugfs `rc_sel`/`case` write, samples endpoint
  state at `0ms`, `1ms`, `2ms`, `5ms`, `10ms`, `20ms`, `50ms`, `100ms`,
  `150ms`, `250ms`, `300ms`, `500ms`, and `1000ms`, then adds a `1200ms`
  context sample. V1455 should be local-only artifact sanity over the exact
  V1454 manifest, static binaries, marker contract, v724 header/kernel parity,
  private modes, and forbidden credential-like byte absence before any live
  flash/handoff.
- V1455 local-only artifact sanity passes with
  `v1455-wifi-test-boot-exact-provider-long-endpoint-artifact-sanity-pass`. It
  verifies the exact V1454 manifest, boot image, static init/helper binaries,
  ramdisk entries, exact-provider long-window marker contract, absent
  retry/legacy/case-writer markers, v724 header/kernel parity, forbidden
  credential-like byte absence, private modes, and the V1454 contract
  (`provider_trigger_micro_endpoint_sampler=true`,
  `provider_trigger_exact_line=true`, `provider_trigger_long_window=true`,
  `rc1_micro_endpoint_sampler=true`, `rc1_endpoint_sampler=true`,
  `rc1_case_aligned_micro_endpoint_sampler=false`,
  `rc1_immediate_endpoint_sampler=false`, `rc1_focused_endpoint_sampler=false`,
  `0ms` watcher delay, retry count `0`). V1456 may be a rollbackable live
  handoff for only the V1454 image, expecting
  `A90 Linux init 0.9.84 (v1454-wifitest)`, collecting V1454 log, summary,
  watcher result, exact-line provider long-window result, expanded dmesg
  markers, and `wlan0` state, then rolling back to
  `stage3/boot_linux_v724.img` and verifying selftest fail=0.
- V1456 rollbackable live handoff passes with
  `v1456-test-boot-provider-trigger-no-downstream-rollback-pass`. The V1454
  test image booted as `A90 Linux init 0.9.84 (v1454-wifitest)`, collected the
  exact-line provider long-window evidence, then rolled back to
  `A90 Linux init 0.9.68 (v724)` with selftest fail=0. No Wi-Fi bring-up
  progress occurred: `wlan0=absent`, no RC1/MHI/WLFW/BDF/FW-ready marker
  appeared, and the runner stayed below scan/connect, credentials, DHCP/routes,
  external ping, PMIC/GPIO/GDSC writes, eSoC notify/`BOOT_DONE`, global PCI
  rescan, and platform bind/unbind.
- V1457 host-only classifier passes with
  `v1457-exact-provider-long-window-low-no-downstream`. It closes the prior
  kmsg chunk ambiguity: the watcher line is the exact
  `__subsystem_get: esoc0` provider line, `exact_provider_line=1`, and
  `long_provider_window=1`. Thirteen micro samples cover `0ms`, `1ms`, `2ms`,
  `5ms`, `10ms`, `20ms`, `50ms`, `100ms`, `150ms`, `250ms`, `300ms`,
  `500ms`, and `1000ms`, followed by a `1200ms` context sample. GPIO135 stayed
  `out 0`, GPIO142 stayed `in 0`, MDM status and PCIe wake IRQs stayed zero,
  pcie1 GDSC stayed `0mV`, pcie1 clocks stayed zero-enabled, and no
  RC1/MHI/WLFW/BDF/FW-ready/`wlan0` progress appeared. The next useful
  question is no longer trigger timing; V1458 should be source/build-only and
  add a provider-trigger thread-state sampler that captures the triggering
  Binder PID/TID, `/proc/<pid>/task/*/wchan`, state, and compact process
  metadata around exact provider trigger time.
- V1458 source/build-only passes with
  `v1458-wifi-test-boot-exact-provider-thread-state-source-build-pass`. It
  generated
  `tmp/wifi/v1458-wifi-test-boot-exact-provider-thread-state-sampler/boot_linux_v1458_wifi_test.img`
  with native init `0.9.85 (v1458-wifitest)`. The test boot keeps the exact
  provider trigger, no explicit RC1 debugfs `rc_sel`/`case` write, and the
  long endpoint window through `1000ms` plus `1200ms` context. It additionally
  parses the triggering provider thread PID from the exact kmsg line and
  samples `/proc/<pid>/comm`, `/proc/<pid>/wchan`, `/proc/<pid>/stat`, and
  selected `/proc/<pid>/status` fields at each micro sample. V1459 should be
  local-only artifact sanity over the exact V1458 manifest, static binaries,
  marker contract, v724 header/kernel parity, private modes, and forbidden
  credential-like byte absence before any live flash/handoff.
- V1459 local-only artifact sanity passes with
  `v1459-wifi-test-boot-exact-provider-thread-state-artifact-sanity-pass`. It
  verifies the exact V1458 manifest, boot image, static init/helper binaries,
  ramdisk entries, exact-provider thread-state marker contract, absent
  retry/legacy/case-writer markers, v724 header/kernel parity, forbidden
  credential-like byte absence, private modes, and the V1458 contract
  (`provider_trigger_micro_endpoint_sampler=true`,
  `provider_trigger_exact_line=true`, `provider_trigger_long_window=true`,
  `provider_trigger_thread_state=true`, `rc1_micro_endpoint_sampler=true`,
  `rc1_endpoint_sampler=true`, `rc1_case_aligned_micro_endpoint_sampler=false`,
  `rc1_immediate_endpoint_sampler=false`, `rc1_focused_endpoint_sampler=false`,
  `0ms` watcher delay, retry count `0`). V1460 may be a rollbackable live
  handoff for only the V1458 image, expecting
  `A90 Linux init 0.9.85 (v1458-wifitest)`, collecting V1458 log, summary,
  watcher result, exact-line provider thread-state result, expanded dmesg
  markers, and `wlan0` state, then rolling back to
  `stage3/boot_linux_v724.img` and verifying selftest fail=0.
- V1460 rollbackable live handoff passes with
  `v1460-test-boot-provider-trigger-no-downstream-rollback-pass`. The V1458
  test image booted as `A90 Linux init 0.9.85 (v1458-wifitest)`, collected the
  exact provider thread-state window, and rolled back to
  `A90 Linux init 0.9.68 (v724)`. This is diagnostic evidence, not Wi-Fi
  bring-up progress: `wlan0=absent`, and no RC1/MHI/WLFW/BDF/FW-ready marker
  appeared.
- V1461 host-only classifier passes with
  `v1461-provider-thread-state-powerup-block-no-downstream`. It confirms the
  exact provider Binder thread is sampled in D-state through all 13 provider
  micro samples: `sdx50m_toggle_soft_reset` from `0ms` through `100ms`,
  `msleep` at `150ms` and `250ms`, then `mdm_subsys_powerup` at `300ms`,
  `500ms`, and `1000ms`. GPIO135 stayed `out 0`, GPIO142 stayed `in 0`, MDM
  status and PCIe wake IRQs stayed zero, pcie1 GDSC stayed `0mV`, pcie1 clocks
  stayed zero-enabled, and no RC1/MHI/WLFW/BDF/FW-ready/`wlan0` progress
  appeared. V1462 should be source/build-only and add an exact-provider
  tracepoint test boot for GPIO1270/GPIO135/GPIO142 plus pcie1 clock/GDSC
  timing around these provider thread phases. Keep it below Wi-Fi HAL,
  scan/connect, credential handling, DHCP/routes, external ping,
  PMIC/GPIO/GDSC direct writes, blind eSoC notify/`BOOT_DONE`, global PCI
  rescan, and platform bind/unbind.
- V1462 source/build-only passes with
  `v1462-wifi-test-boot-exact-provider-tracepoint-source-build-pass`. It
  generated
  `tmp/wifi/v1462-wifi-test-boot-exact-provider-tracepoint-sampler/boot_linux_v1462_wifi_test.img`
  with native init `0.9.86 (v1462-wifitest)`. The test boot keeps the exact
  provider trigger, V1458 thread-state sampler, no explicit RC1 debugfs
  `rc_sel`/`case` write, and the long endpoint window through `1000ms` plus
  `1200ms` context. It additionally arms `gpio_value` and `gpio_direction`
  tracepoints before helper start, then samples trace output for GPIO1270,
  GPIO135, GPIO142, and GPIO141 at each provider micro sample. V1463 should be
  local-only artifact sanity over the exact V1462 manifest, static binaries,
  marker contract, v724 header/kernel parity, private modes, and forbidden
  credential-like byte absence before any live flash/handoff.
- V1463 local-only artifact sanity passes with
  `v1463-wifi-test-boot-exact-provider-tracepoint-artifact-sanity-pass`. It
  verifies the exact V1462 manifest, boot image, static init/helper binaries,
  ramdisk entries, exact-provider tracepoint marker contract, absent
  retry/legacy/case-writer markers, v724 header/kernel parity, forbidden
  credential-like byte absence, private modes, and the V1462 contract
  (`provider_trigger_micro_endpoint_sampler=true`,
  `provider_trigger_exact_line=true`, `provider_trigger_long_window=true`,
  `provider_trigger_thread_state=true`,
  `provider_trigger_tracepoint_sampler=true`,
  `rc1_micro_endpoint_sampler=true`, `rc1_endpoint_sampler=true`,
  `rc1_case_aligned_micro_endpoint_sampler=false`,
  `rc1_immediate_endpoint_sampler=false`, `rc1_focused_endpoint_sampler=false`,
  `0ms` watcher delay, retry count `0`). V1464 may be a rollbackable live
  handoff for only the V1462 image, expecting
  `A90 Linux init 0.9.86 (v1462-wifitest)`, collecting V1462 log, summary,
  watcher result, exact-provider tracepoint window result, expanded dmesg
  markers, and `wlan0` state, then rolling back to
  `stage3/boot_linux_v724.img` and verifying selftest fail=0.
- V1464 rollbackable live handoff passes with
  `v1464-test-boot-provider-trigger-no-downstream-rollback-pass`. It flashed
  only the V1462 exact-provider tracepoint test image, verified the test boot,
  collected the V1462 log/summary, exact-provider tracepoint window, dmesg
  markers, and `wlan0` state, then rolled back to healthy v724 with selftest
  fail=0. The handoff reached the exact `__subsystem_get: esoc0` provider
  trigger, but no RC1/MHI/WLFW/BDF/FW-ready/`wlan0` progress appeared.
- V1465 host-only classifier passes with
  `v1465-pon-toggles-ap2mdm-absent-no-downstream`. It classifies V1464's
  exact-provider GPIO tracepoint evidence: GPIO1270/PON toggles low-high and
  GPIO141 goes low, but GPIO135/AP2MDM and GPIO142/MDM2AP have no tracepoint
  events. Endpoint state keeps GPIO135 `out 0`, GPIO142 `in 0`, MDM status IRQ
  and PCIe wake IRQ counts at zero, pcie1 GDSC at `0mV`, and pcie1 clocks
  zero-enabled. No RC1/MHI/WLFW/BDF/FW-ready/`wlan0` progress appears. V1466
  should be host-only provider AP2MDM branch/source classification before any
  new live mutation.
- V1466 host-only classifier passes with
  `v1466-ap2mdm-branch-divergence-needs-pil-parity-test-boot`. It reconciles
  V1464/V1465 with V1318 and source/static provider evidence. V1464 proves the
  test boot reaches the PON side (`GPIO1270` low-high, about `180.115ms`) but
  records zero GPIO135/AP2MDM and zero GPIO142/MDM2AP events. V1318 proves an
  earlier native PM path captured `fw=esoc0` PIL notifications, PON trace, and
  GPIO135/AP2MDM high while still missing GPIO142. The current PID1 sampler
  lacks `msm_pil_event:pil_notif` parity, so V1467 should be source/build-only
  and add PIL notification tracepoint sampling to the exact-provider GPIO
  tracepoint test boot before any new live mutation.
- V1467 source/build-only passes with
  `v1467-wifi-test-boot-exact-provider-pil-gpio-tracepoint-source-build-pass`.
  It adds `A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_PIL_TRACEPOINT_SAMPLER` to the
  rollbackable PID1 test-boot path. The artifact keeps the exact provider
  trigger, thread-state sampler, long endpoint window, and GPIO tracepoints,
  then additionally arms `msm_pil_event:pil_notif` and samples `fw=esoc0`
  trace lines under sampler marker
  `read-only-v1467-exact-provider-pil-gpio-tracepoint`. Built boot image:
  `tmp/wifi/v1467-wifi-test-boot-exact-provider-pil-gpio-tracepoint-sampler/boot_linux_v1467_wifi_test.img`
  (`sha256=e9fd747a483f9d5d22126ddda0f99c0a4b5b4b5343f20094d1d5d8cf3adb359e`),
  native init `0.9.87 (v1467-wifitest)`. Static init/helper verification,
  ramdisk entry verification, boot marker verification, and forbidden
  credential-like byte scan passed. V1468 should be local-only artifact sanity
  over the exact V1467 manifest before any rollbackable live handoff.
- V1468 local-only artifact sanity passes with
  `v1468-wifi-test-boot-exact-provider-pil-gpio-tracepoint-artifact-sanity-pass`.
  It verifies the exact V1467 manifest, boot image, static PID1/helper
  binaries, ramdisk entries, exact-provider PIL+GPIO tracepoint marker
  contract, absent retry/legacy/case-writer markers, v724 header/kernel parity,
  forbidden credential-like byte absence, private modes, and the V1467 contract
  (`provider_trigger_tracepoint_sampler=true`,
  `provider_trigger_pil_tracepoint_sampler=true`,
  `provider_trigger_thread_state=true`, `provider_trigger_exact_line=true`,
  `provider_trigger_long_window=true`, `rc1_watcher_delay_ms=0`,
  `rc1_retry_count=0`). V1469 may be a rollbackable live handoff for only the
  V1467 image, expecting `A90 Linux init 0.9.87 (v1467-wifitest)`, collecting
  the V1467 log, summary, RC1 watcher result, exact-provider PIL+GPIO
  tracepoint window result, expanded dmesg markers, and `wlan0` state, then
  rolling back to `stage3/boot_linux_v724.img` and verifying selftest fail=0.
- V1469 rollbackable live handoff passes with
  `v1469-test-boot-provider-trigger-no-downstream-rollback-pass`. It flashed
  only the V1467 exact-provider PIL+GPIO tracepoint test image, verified the
  test boot, collected the V1467 log/summary, RC1 watcher/window results, dmesg
  markers, and `wlan0` state, then rolled back to healthy v724 with selftest
  fail=0. The handoff reached the modem and esoc0 provider triggers, but no
  RC1/MHI/WLFW/BDF/FW-ready/`wlan0` progress appeared.
- V1470 host-only classifier passes with
  `v1470-ap2mdm-set-called-but-not-effective-no-mdm2ap-no-rc1`. It classifies
  V1469's exact-provider PIL+GPIO tracepoint evidence: `fw=esoc0` PIL parity is
  present, GPIO1270/PON toggles low-high, and GPIO135/AP2MDM set-high is called
  about `306.356ms` after esoc0 PIL start. However, live readback still shows
  zero GPIO135 high samples, zero GPIO142 high samples, zero MDM status IRQ
  increments, zero PCIe wake IRQ increments, and no RC1/MHI/WLFW/BDF/FW-ready
  /`wlan0` progress. V1471 should be host-only AP2MDM effective-level and
  pinctrl ownership classification before any write-based workaround or upper
  Wi-Fi work.
- V1471 host-only classifier passes with
  `v1471-ap2mdm-active-pinctrl-present-effective-output-low`. It verifies the
  GPIO tracepoint semantics (`gpio_direction ... out (0)` is error code 0, not
  output-low), confirms `gpio_value: 135 set 1` is a real AP2MDM set-high call,
  and reconciles source ownership: SDX5XM DTS maps GPIO135 to AP2MDM, uses
  `ap2mdm_active`, and SM8150 pinctrl config sets GPIO function, 16mA drive,
  and bias disabled. V1469's live readback shows that active pinctrl config, so
  simple missing ownership/pinctrl is closed. The open gap is effective level:
  GPIO135 still samples low, GPIO142/MDM2AP and PCIe wake IRQs stay zero, and
  no RC1/MHI/WLFW/BDF/FW-ready/`wlan0` progress appears. V1472 should be
  source/build-only and extend the test boot sampler around the AP2MDM set-high
  point with more effective-level/pinctrl/debugfs readback, still with no
  writes or upper Wi-Fi actions.
- V1472 source/build-only passes with
  `v1472-wifi-test-boot-effective-level-source-build-pass`. It adds
  `A90_WIFI_TEST_BOOT_PROVIDER_TRIGGER_EFFECTIVE_LEVEL_SAMPLER` to the
  rollbackable PID1 test-boot path, preserves the exact provider trigger,
  thread-state, GPIO tracepoint, and PIL tracepoint contract, extends samples
  through `3000ms`, and adds full read-only endpoint/pinctrl/regulator/clock
  snapshots at provider samples from `250ms` onward. Built boot image:
  `tmp/wifi/v1472-wifi-test-boot-exact-provider-effective-level-sampler/boot_linux_v1472_wifi_test.img`
  (`sha256=2835568c31f9a9a25dac6e7830cdb51d666bdd050bf16646fa1518b8d7ed1e02`),
  native init `0.9.88 (v1472-wifitest)`. V1473 should be local-only artifact
  sanity over the exact V1472 manifest before any rollbackable live handoff.
- V1473 local-only artifact sanity passes with
  `v1473-wifi-test-boot-effective-level-artifact-sanity-pass`. It verifies the
  exact V1472 manifest, base boot, static init/helper binaries, ramdisk entries,
  boot markers, retry/legacy/case-writer marker absence, header/kernel parity,
  forbidden credential-like byte absence, private modes, and the effective-level
  sampler contract. V1474 may be a rollbackable live handoff for only the V1472
  image, expecting `A90 Linux init 0.9.88 (v1472-wifitest)`, collecting V1472
  log/summary, RC1 watcher result, effective-level window result, expanded
  dmesg markers, and `wlan0` state, then rolling back to
  `stage3/boot_linux_v724.img` and verifying selftest fail=0.
- V1474 rollbackable live handoff passes with
  `v1474-test-boot-provider-trigger-no-downstream-rollback-pass`. It flashed
  only the V1472 effective-level test image, verified the test boot, collected
  the V1472 log/summary, effective-level window, dmesg markers, and `wlan0`
  state, then rolled back to healthy v724 with selftest fail=0. The handoff
  reached the modem and esoc0 provider triggers, but no RC1/MHI/WLFW/BDF
  /FW-ready/`wlan0` progress appeared.
- V1475 host-only classifier passes with
  `v1475-effective-level-low-pcie1-off-through-extended-window`. V1474's
  extended full snapshots cover the provider trigger through a long effective
  wall-clock window caused by slow read-only debugfs snapshots; the last full
  sample reports `56754ms` child elapsed. GPIO135 remains low despite the
  AP2MDM set-high trace and mdm3 pinmux ownership, GPIO142 remains low, pcie1
  GDSC remains `0mV`, pcie1 pipe clock remains zero-enabled, and downstream
  RC1/MHI/WLFW/BDF/FW-ready/`wlan0` markers remain absent. V1476 should be a
  host-only lower-intervention design review before any write-based experiment.
  Keep Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, direct
  PMIC/GPIO/GDSC writes, blind eSoC notify/`BOOT_DONE`, global PCI rescan, and
  platform bind/unbind prohibited from this state.
- V1476 host-only design gate passes with
  `v1476-select-ap2mdm-bounded-hold-test-boot-design`. It rejects upper Wi-Fi
  work because `wlan0` is absent, rejects repeating only corrected RC1
  `rc_sel=2` + `case=11` because prior gates already reached LTSSM without L0,
  rejects direct PON and unspecific pcie1 GDSC/clock writes, and selects the
  narrowest next test-boot direction: source/build-only AP2MDM bounded-hold
  support. V1477 should add a compile-time-gated wifitest mode that waits for
  the provider/AP2MDM set-high trace, verifies GPIO135 still reads low, then
  attempts a bounded GPIO135 hold only if the userspace GPIO interface permits
  it, samples GPIO135/GPIO142/pcie1/LTSSM/MHI/WLFW/`wlan0`, releases the line,
  and records cleanup. V1478 should be local artifact sanity; V1479 may be a
  rollbackable live handoff only after those pass. Plan:
  `docs/plans/NATIVE_INIT_V1476_LOWER_INTERVENTION_DESIGN_2026-06-01.md`.
- V1477 source/build-only passes with
  `v1477-wifi-test-boot-ap2mdm-hold-source-build-pass`. It adds the
  compile-time marker `bounded-v1477-ap2mdm-hold-test` and builds
  `tmp/wifi/v1477-wifi-test-boot-ap2mdm-hold/boot_linux_v1477_wifi_test.img`
  with native init `0.9.89 (v1477-wifitest)`. The test boot waits for the
  provider/AP2MDM set-high trace, confirms GPIO135 still reads low, attempts a
  bounded GPIO135 hold only through `/sys/class/gpio` if export/direction is
  permitted, samples GPIO135/GPIO142/pcie1/LTSSM/MHI/WLFW/`wlan0`, releases the
  line, and records cleanup. V1477 is source/build-only; no device command,
  flash, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, or
  partition write occurred. V1478 should be local-only artifact sanity over the
  exact V1477 manifest before any rollbackable live handoff.
- V1478 local-only artifact sanity passes with
  `v1478-wifi-test-boot-ap2mdm-hold-artifact-sanity-pass`. It verifies the
  exact V1477 manifest, base boot, static init/helper binaries, ramdisk entries,
  AP2MDM hold boot markers, legacy marker absence, header/kernel parity,
  forbidden credential-like byte absence, private modes, and the AP2MDM hold
  contract. V1479 may be a rollbackable live handoff for only the V1477 image,
  expecting `A90 Linux init 0.9.89 (v1477-wifitest)`, collecting V1477 log,
  summary, RC1 watcher result, AP2MDM hold window result, dmesg markers, and
  `wlan0` state, then rolling back to `stage3/boot_linux_v724.img` and
  verifying selftest fail=0.
- V1479 rollbackable live handoff passes with
  `v1479-test-boot-provider-trigger-no-downstream-rollback-pass`. It flashed
  only the V1477 AP2MDM hold test image, collected the V1477 evidence, and
  rolled back to healthy v724. The handoff reached the provider trigger and
  AP2MDM hold gate, but no RC1/MHI/WLFW/BDF/FW-ready/`wlan0` progress appeared.
- V1480 host-only classifier passes with
  `v1480-ap2mdm-userspace-hold-refused-busy-no-downstream`. The AP2MDM hold
  gate saw the provider set-high trace and confirmed GPIO135 low, but
  `/sys/class/gpio` export for GPIO135 returned `-16` (`EBUSY`), so the line
  was not exported and no userspace hold was applied. GPIO135/GPIO142 stayed
  low, pcie1 stayed off, and downstream Wi-Fi markers remained absent. Do not
  retry this exact userspace hold. V1481 should be host-only kernel-provider
  feasibility review or another lower-prerequisite hypothesis that does not
  fight the kernel-owned GPIO line.
- V1481 host-only classifier passes with
  `v1481-userspace-hold-closed-kernel-provider-not-live-feasible`. Samsung OSRC
  GPIO source explains V1480's `/sys/class/gpio/export` `-16` result:
  `export_store()` first calls `gpiod_request(desc, "sysfs")`, and
  `__gpiod_request()` returns `-EBUSY` when `FLAG_REQUESTED` is already set.
  The DTS maps GPIO135 directly to `qcom,ap2mdm-status-gpio` for `mdm3`, so
  AP2MDM is kernel/eSoC-provider-owned and cannot be held from userspace sysfs.
  Kernel-provider patching is the direct layer but is not currently selected
  for live work because the Samsung OSRC custom-kernel boot path remains
  incompatible from V771/V774/V775. Direct MMIO/pinctrl/GPIO writes and blind
  RC1 retries remain rejected. V1482 should be a host-only Android AP2MDM
  effective-level reference classifier before building another Wi-Fi auto-start
  test boot: determine whether Android-positive evidence ever shows GPIO135
  high, or whether GPIO135 readback can be low even when SDX50M/Wi-Fi succeeds.
  Report:
  `docs/reports/NATIVE_INIT_V1481_AP2MDM_PROVIDER_FEASIBILITY_2026-06-01.md`.
- V1482 host-only classifier passes with
  `v1482-android-gpio135-low-not-primary-gate-next-auto-boot-supervisor`.
  Existing Android-positive evidence already answers the V1481 question:
  V914 shows Android reaches service-notifier, WLFW, WLAN-PD, BDF, and `wlan0`
  while post-boot lower diagnostics can still show `subsys9=OFFLINING`, GPIO142
  IRQ total `0`, no current `ks`, and no current MHI pipe. V1291 shows static
  GPIO parity: Android and native both have GPIO135 `out 0 16mA no pull` and
  GPIO142 `in 0 8mA no pull`. Therefore GPIO135/GPIO142 low readback is not
  enough to drive another GPIO-hold cycle. The next test image direction is
  valid, but it should be a credential-free automatic Wi-Fi readiness boot:
  primary checkpoints are WLFW, ICNSS/QMI or WLFW service progress, BDF,
  FW-ready, and `wlan0`; GPIO135/GPIO142/pcie1/MHI stay secondary diagnostics.
  V1483 should be source/build-only design for that rollbackable test boot.
  Report:
  `docs/reports/NATIVE_INIT_V1482_ANDROID_AP2MDM_REFERENCE_CLASSIFIER_2026-06-01.md`.
- V1483 plan is ready with
  `v1483-plan-auto-readiness-test-boot-before-credentials`. It converts the
  user's test-boot direction into a concrete gated sequence: first add a compact
  helper readiness summary (`auto_readiness.*`) for WLFW, ICNSS/QMI or WLFW
  service progress, BDF, FW-ready, `wlan0`, and lower diagnostics; then build a
  rollbackable credential-free PID1 Wi-Fi readiness test image that runs one
  Android-order provider/CNSS route automatically at boot. V1483 keeps
  scan/connect, credential materialization, DHCP/routes, external ping, direct
  PMIC/GPIO/GDSC writes, raw MMIO/pinctrl writes, blind eSoC notify/`BOOT_DONE`,
  global PCI rescan, platform bind/unbind, and custom OSRC kernel flash
  blocked. V1484 should be source/build-only helper support for the compact
  readiness summary. Plan:
  `docs/plans/NATIVE_INIT_V1483_WIFI_AUTO_READINESS_TEST_BOOT_PLAN_2026-06-01.md`.
- V1484 source/build-only passes with
  `v1484-auto-readiness-helper-build-pass`. Helper
  `a90_android_execns_probe v287` adds `--pm-observer-auto-readiness-summary`,
  requiring the existing bounded
  `--pm-observer-late-per-proxy-mdm2ap-errfatal-pcie-timing-sampler` window.
  It emits `auto_readiness.*` keys for CNSS daemon/diag start, WLFW start or
  request, ICNSS/QMI, BDF, FW-ready, `wlan0`, GPIO142 IRQ delta, pcie1 state,
  MHI/pipe/`ks`, and safety zeros. Built static aarch64 helper:
  `stage3/linux_init/helpers/a90_android_execns_probe_v287`, sha256
  `660d88fc9e0ebdf6c95e495d9dd659c09321feb407fe6a7f77213f3b5c2bb411`.
  V1484 performed no device command or live action. V1485 should be
  source/build-only and add the rollbackable PID1 test-boot wrapper that bundles
  helper v287 and passes the new readiness summary flag. Report:
  `docs/reports/NATIVE_INIT_V1484_AUTO_READINESS_HELPER_SOURCE_BUILD_2026-06-01.md`.
- V1485 source/build-only passes with
  `v1485-wifi-auto-readiness-test-boot-source-build-pass`. It extends the v1393
  rollbackable test-boot builder for helper v287 and adds the compile-time
  `A90_WIFI_TEST_BOOT_AUTO_READINESS_SUPERVISOR` path. Built image:
  `tmp/wifi/v1485-wifi-auto-readiness-test-boot/boot_linux_v1485_wifi_test.img`
  (`sha256=7d3a59fe5fe4cd683bd830491c5ccf7e5b3aea1271558b320f6fe7e76ad1ac23`),
  native init `0.9.90 (v1485-wifitest)`, init sha256
  `9eb11472596e316f4c993428b32cde263aa6a7baa29fdabff0f56c261efbee54`, helper
  sha256 `660d88fc9e0ebdf6c95e495d9dd659c09321feb407fe6a7f77213f3b5c2bb411`.
  The test boot bundles `/bin/a90_android_execns_probe`, passes
  `--pm-observer-auto-readiness-summary`, emits marker
  `auto-v1485-wifi-readiness-test`, and keeps Wi-Fi HAL, scan/connect,
  credentials, DHCP/routes, external ping, direct PMIC/GPIO/GDSC writes, blind
  eSoC notify/`BOOT_DONE`, and device flashing blocked. V1486 should be
  local-only artifact sanity over the exact V1485 manifest before any
  rollbackable live handoff. Report:
  `docs/reports/NATIVE_INIT_V1485_WIFI_AUTO_READINESS_TEST_BOOT_SOURCE_BUILD_2026-06-01.md`.
- V1486 local-only artifact sanity passes with
  `v1486-wifi-auto-readiness-artifact-sanity-pass`. It verifies the exact V1485
  manifest, v724 base boot presence, static init/helper binaries, ramdisk
  entries, boot markers, AP2MDM hold marker absence, auto-readiness contract,
  v724 header/kernel parity, forbidden credential-like byte absence, and private
  artifact modes. Verified boot image remains
  `tmp/wifi/v1485-wifi-auto-readiness-test-boot/boot_linux_v1485_wifi_test.img`
  with sha256 `7d3a59fe5fe4cd683bd830491c5ccf7e5b3aea1271558b320f6fe7e76ad1ac23`.
  V1487 may perform a rollbackable live handoff for only the V1485 image,
  expecting `A90 Linux init 0.9.90 (v1485-wifitest)`, collecting the V1485 log,
  summary, focused dmesg, and `wlan0` state, then rolling back to
  `stage3/boot_linux_v724.img` and verifying selftest `fail=0`. Report:
  `docs/reports/NATIVE_INIT_V1486_WIFI_AUTO_READINESS_ARTIFACT_SANITY_2026-06-01.md`.
- V1487 rollbackable live handoff completed with
  `v1487-test-boot-provider-trigger-no-downstream-wifi-progress-blocked`.
  Handoff and rollback passed: V1485 test boot verified, evidence was collected,
  then v724 rollback verified. The test boot reached the established provider
  path (`__subsystem_get: modem` then `__subsystem_get: esoc0`) but produced no
  PCIe RC1/LTSSM, MHI, WLFW, BDF, FW-ready, or `wlan0` marker; `wlan0=absent`.
  PID1 summary confirmed `auto_readiness_supervisor_requested=1`, but the helper
  timed out (`helper_wait_rc=-110`, `helper_timed_out=1`) before its buffered
  `auto_readiness.*` stdout summary was emitted. V1488 should make
  auto-readiness timeout-safe: either persist a sidecar result before helper
  cleanup can block, or have PID1 synthesize readiness from focused dmesg and
  `wlan0` after the bounded helper timeout. Do not proceed to scan/connect,
  credentials, DHCP/routes, or external ping until RC1/MHI/WLFW/`wlan0`
  progress is proven. Report:
  `docs/reports/NATIVE_INIT_V1487_WIFI_AUTO_READINESS_HANDOFF_2026-06-01.md`.
- V1488 source/build-only passes with
  `v1488-wifi-auto-readiness-timeout-safe-test-boot-source-build-pass`. It adds
  PID1-synthesized `auto_readiness_pid1.*` summary keys so readiness evidence is
  still emitted after a bounded helper timeout. The summary uses
  `SYSLOG_ACTION_READ_ALL` plus `wlan0` sysfs state to classify modem/provider
  trigger, PCIe RC1/LTSSM, MHI, WLFW, ICNSS/QMI, BDF, FW-ready, and `wlan0`.
  Built image:
  `tmp/wifi/v1488-wifi-auto-readiness-timeout-safe-test-boot/boot_linux_v1488_wifi_test.img`
  (`sha256=3d18c340e69f5f448be27fca370479e06b19bccb3a903a797ca3f5b0181eac32`),
  native init `0.9.91 (v1488-wifitest)`, init sha256
  `290b59d23fd29ca862a716992f34e3c753fdceb36fa69781531178003dc209ce`, helper
  sha256 `660d88fc9e0ebdf6c95e495d9dd659c09321feb407fe6a7f77213f3b5c2bb411`.
  V1488 ran no device command or live action. V1489 should run local artifact
  sanity over the exact V1488 manifest before any rollbackable live handoff.
  Report:
  `docs/reports/NATIVE_INIT_V1488_WIFI_AUTO_READINESS_TIMEOUT_SAFE_SOURCE_BUILD_2026-06-01.md`.
- V1489 local-only artifact sanity passes with
  `v1489-wifi-auto-readiness-timeout-safe-artifact-sanity-pass`. It verifies the
  exact V1488 manifest, v724 base boot presence, static init/helper binaries,
  ramdisk entries, boot markers including `auto_readiness_pid1.*`, AP2MDM hold
  marker absence, timeout-safe auto-readiness contract, v724 header/kernel
  parity, forbidden credential-like byte absence, and private artifact modes.
  Verified boot image remains
  `tmp/wifi/v1488-wifi-auto-readiness-timeout-safe-test-boot/boot_linux_v1488_wifi_test.img`
  with sha256 `3d18c340e69f5f448be27fca370479e06b19bccb3a903a797ca3f5b0181eac32`.
  V1490 may perform a rollbackable live handoff for only the V1488 image,
  expecting `A90 Linux init 0.9.91 (v1488-wifitest)`, collecting the V1488 log,
  summary, focused dmesg, and `wlan0` state, then rolling back to
  `stage3/boot_linux_v724.img` and verifying selftest `fail=0`. Report:
  `docs/reports/NATIVE_INIT_V1489_WIFI_AUTO_READINESS_TIMEOUT_SAFE_ARTIFACT_SANITY_2026-06-01.md`.
- V1490 rollbackable live handoff reached
  `v1490-timeout-safe-provider-trigger-no-downstream-manual-rollback-pass`.
  The V1488 test boot produced the intended timeout-safe PID1 summary:
  `auto_readiness_pid1.syslog_ok=1`, modem/provider trigger seen, primary
  checkpoint `provider-trigger`, and no PCIe RC1, MHI, WLFW, ICNSS/QMI, BDF,
  FW-ready, or `wlan0`. The generic TWRP rollback path failed because recovery
  ADB never appeared, so rollback was corrected manually from native init:
  NCM HTTP downloaded `stage3/boot_linux_v724.img` to
  `/cache/boot_linux_v724.img`, sha256 matched
  `ae01fa106391756dae12fc9a6c9f57d4111b2180c82cdcfe3691ee31f7542adc`, sysfs
  identified `boot` as `sda24` (`259:8`), `/dev/block/sda24` was written and
  read back with the same sha256 prefix, then reboot verified
  `A90 Linux init 0.9.68 (v724)` and selftest `fail=0`. Before another live
  handoff, V1491 should add an explicit native direct rollback fallback using a
  pre-staged `/cache/boot_linux_v724.img` when recovery ADB is unavailable.
  Report:
  `docs/reports/NATIVE_INIT_V1490_WIFI_AUTO_READINESS_TIMEOUT_SAFE_HANDOFF_2026-06-01.md`.
- V1491 source-only safety update passes with
  `v1491-native-direct-rollback-fallback-source-pass`. The shared handoff
  runner now supports `--native-direct-rollback-fallback`, which verifies a
  pre-staged `/cache/boot_linux_v724.img`, creates `/dev/block/sda24` if
  missing (`259:8`), writes the image with `dd ... conv=fsync && sync`, checks
  the boot prefix sha256, reboots, and verifies the expected rollback version.
  V1491 performed no live mutation. V1492 may use this fallback in a bounded
  live handoff, but only after the rollback image is pre-staged on-device with
  the expected v724 sha256. Report:
  `docs/reports/NATIVE_INIT_V1491_NATIVE_DIRECT_ROLLBACK_FALLBACK_SOURCE_2026-06-01.md`.
- V1492 rollbackable live handoff completed with
  `v1492-test-boot-provider-trigger-no-downstream-wifi-progress-blocked`.
  Added `scripts/revalidation/native_wifi_test_boot_handoff_v1492.py` so the
  V1488 timeout-safe Wi-Fi test boot can be rerun with
  `--native-direct-rollback-fallback` enabled. The `/cache/boot_linux_v724.img`
  rollback image was present with the expected sha256 before live execution.
  Handoff and rollback passed through the generic from-native route; post-run
  validation confirmed v724 and selftest `fail=0`. The test boot still stopped
  at `provider-trigger-no-downstream`: no PCIe RC1/LTSSM, MHI, WLFW,
  ICNSS/QMI, BDF, FW-ready, or `wlan0` marker appeared. Next gate: keep
  credentials, scan/connect, DHCP/routes, and external ping blocked; build a
  narrower rollbackable test boot that preserves the auto path but adds focused
  RC1/MHI prerequisite capture around the boot-time provider trigger. Report:
  `docs/reports/NATIVE_INIT_V1492_WIFI_AUTO_READINESS_NATIVE_ROLLBACK_HANDOFF_2026-06-01.md`.
- V1493 source/build-only passes with
  `v1493-wifi-auto-readiness-rc1-window-test-boot-source-build-pass`. It adds
  `scripts/revalidation/build_native_init_wifi_test_boot_v1493.py` and builds a
  rollbackable credential-free test boot that keeps the V1488 timeout-safe
  `auto_readiness_pid1.*` summary while enabling a PID1 RC1 watcher and RC1
  window sampler. The watcher is not observation-only: after the provider
  trigger it performs bounded pci-msm debugfs corrected RC1 enumerate writes
  (`rc_sel=2` + `case=11`) while the sampler records the window. Built image:
  `tmp/wifi/v1493-wifi-auto-readiness-rc1-window-test-boot/boot_linux_v1493_wifi_test.img`
  (`sha256=bc1a6484eb8786323b2a534b099839db32ad627d7688395265c63b647ed56c8e`),
  native init `0.9.92 (v1493-wifitest)`, init sha256
  `8dce5a6515fa427bb3bd2b89bceda518c989c9978b3bd42049e2ba9eb96d3347`, helper
  sha256 `660d88fc9e0ebdf6c95e495d9dd659c09321feb407fe6a7f77213f3b5c2bb411`.
  V1493 performed no device command or live action. V1494 should run local
  artifact sanity over the exact V1493 manifest before any rollbackable live
  handoff. Report:
  `docs/reports/NATIVE_INIT_V1493_WIFI_AUTO_READINESS_RC1_WINDOW_SOURCE_BUILD_2026-06-01.md`.
- V1494 local-only artifact sanity passes with
  `v1494-wifi-auto-readiness-rc1-window-artifact-sanity-pass`. It verifies the
  exact V1493 manifest and image, including static init/helper binaries,
  ramdisk entries, RC1 watcher/window boot markers, absence of AP2MDM-hold
  markers, v724 header/kernel parity, private artifact modes, forbidden
  credential-like byte absence, and RC1 auto-readiness contract including the
  bounded `rc_sel=2` + `case=11` watcher writes. V1494 performed no device
  command or live action. V1495 may perform a rollbackable
  live handoff for only the V1493 image, expecting
  `A90 Linux init 0.9.92 (v1493-wifitest)`, collecting V1493 log/summary, RC1
  watcher/window results, focused dmesg, and `wlan0` state, then rolling back
  to `stage3/boot_linux_v724.img` and verifying selftest `fail=0`. Report:
  `docs/reports/NATIVE_INIT_V1494_WIFI_AUTO_READINESS_RC1_WINDOW_ARTIFACT_SANITY_2026-06-01.md`.
- V1495 rollbackable live handoff reached `v1495-test-boot-version-missing`.
  The exact V1493 RC1-window test image was flashed and the generic
  from-native rollback restored v724 successfully; post-run validation showed
  selftest `fail=0`. The V1493 image may issue bounded pci-msm debugfs
  corrected RC1 enumerate writes (`rc_sel=2` + `case=11`) after the provider
  trigger, but V1495 did not collect the post-trigger sidecars, so the in-boot
  watcher result is unproven for this run. The flash verifier saw the V1493 version marker
  immediately after reboot, but after the 100s hold all post-hold `cmdv1`
  evidence reads failed with missing END marker or bridge connection reset.
  Therefore V1495 proves rollback safety for this image but not RC1/MHI
  progress. Treat it as a communication-loss blocker. V1496 should isolate the
  RC1 watcher/window side effect with shorter/earlier collection or a
  PID1-persisted sidecar; keep credentials, scan/connect, DHCP/routes, and
  external ping blocked until `wlan0` exists. Report:
  `docs/reports/NATIVE_INIT_V1495_WIFI_AUTO_READINESS_RC1_WINDOW_HANDOFF_2026-06-01.md`.
- V1496 rollbackable live handoff passes with
  `v1496-test-boot-downstream-progress-rollback-pass`. It reused the V1493
  RC1-window test image but shortened the hold to 10s, proving the V1495
  post-hold failure was a long-window communication-loss issue rather than an
  immediate RC1-window wedge. Evidence collection succeeded and rollback
  verified v724/selftest `fail=0`. This run also executed the test image's
  bounded pci-msm debugfs corrected RC1 enumerate (`rc_sel=2` + `case=11`) after
  the provider trigger. The critical new blocker is no longer
  provider-only: RC1 PHY became ready and LTSSM entered polling, but link
  training stopped at `LTSSM_POLL_COMPLIANCE` with
  `PCIe RC1 link initialization failed (LTSSM_STATE:0x3)`. No L0, MHI, WLFW,
  BDF, FW-ready, or `wlan0` appeared; GPIO142/MDM status stayed low/IRQ count
  `0`. Focused samples show GPIO102 low, GPIO103 high/unclaimed `pci_e1`,
  GPIO104 low, GPIO135 low, and GPIO142 low through post-500ms. V1497 should
  classify this RC1 link failure host-only against Android-good RC1 timing and
  DTS pin/power contracts before any bounded write experiment. Report:
  `docs/reports/NATIVE_INIT_V1496_WIFI_RC1_WINDOW_SHORT_HOLD_HANDOFF_2026-06-01.md`.
- V1497 host-only classifier passes with
  `v1497-auto-readiness-rc1-fail-reconciled-existing-endpoint-gap`. It adds
  `scripts/revalidation/native_wifi_auto_readiness_rc1_failure_classifier_v1497.py`
  and reconciles V1496 against V1371/V1379/V1432/V1448/V1461/V1475 plus the
  V1476 lower-intervention design gate and the V1481/V1482 AP2MDM closure.
  V1496 proved the rollbackable test boot can execute bounded corrected RC1
  enumerate (`rc_sel=2` + `case=11`) and collect evidence, but this still
  matches the established endpoint-readiness gap: LTSSM fails before L0 and no
  MHI/WLFW/BDF/FW-ready/`wlan0` appears. Repeating GPIO135 sysfs hold or
  corrected RC1-only experiments is rejected. Next work should continue from the
  V1482/V1496 endpoint-readiness branch and start with a source/build-only
  pre-L0 endpoint parity observer; keep Wi-Fi HAL, credentials, scan/connect,
  DHCP/routes, and external ping blocked until `wlan0` exists.
  Report:
  `docs/reports/NATIVE_INIT_V1497_AUTO_READINESS_RC1_FAILURE_CLASSIFIER_2026-06-01.md`.
- V1498 host-only `msm_pcie` TEST:11 static analysis passes with
  `v1498-msm-pcie-test11-enumerate-path-confirmed-endpoint-response-gap`. It
  adds
  `scripts/revalidation/native_wifi_msm_pcie_test11_static_analysis_v1498.py`
  and parses V1496 evidence, local DTS, and public `pci-msm.c` reference source.
  TEST:11 maps to `MSM_PCIE_ENUMERATION`, the case calls
  `msm_pcie_enumerate()`, and enumeration calls `msm_pcie_enable(dev, PM_ALL)`.
  Local DTS confirms the RC1/SDX50M contract: PERST GPIO102, WAKE GPIO104,
  `pcie_1` clock/reset names, RC bridge `17cb:0108`, MHI IDs
  `17cb:0305`..`17cb:0308`, and SDX50M link-info `0305_01.01.00`. Therefore
  V1496 exercised the intended RC1 enumerate/link-training path; the remaining
  gap is pre-L0 endpoint response / PERST-refclk-power-sequence parity. V1499
  should be source/build-only and add a pre-L0 endpoint parity observer for
  PERST/refclk/clock/GDSC/GPIO102/GPIO103/GPIO104/GPIO135/GPIO142 plus LTSSM
  timing around provider-trigger and corrected RC1 enumerate. Keep Wi-Fi HAL,
  credentials, scan/connect, DHCP/routes, external ping, PMIC/GPIO/GDSC direct
  writes, global PCI rescan, and platform bind/unbind blocked. Report:
  `docs/reports/NATIVE_INIT_V1498_MSM_PCIE_TEST11_STATIC_ANALYSIS_2026-06-01.md`.
- V1499 source/build-only pre-L0 endpoint parity test boot passes with
  `v1499-wifi-auto-readiness-pre-l0-parity-test-boot-source-build-pass`. It
  adds `scripts/revalidation/build_native_init_wifi_test_boot_v1499.py` and
  builds a rollbackable credential-free image:
  `tmp/wifi/v1499-wifi-auto-readiness-pre-l0-parity-test-boot/boot_linux_v1499_wifi_test.img`
  (`sha256=cd974b855816c3debc9a9505b4d96dee44ba86b48665e35c2ca3376822fa43d8`),
  native init `0.9.93 (v1499-wifitest)`, init sha256
  `2bbca1bf624dae729b244a553921af306f595fb0ba74660a6581f5405295dbe0`, helper
  sha256 `660d88fc9e0ebdf6c95e495d9dd659c09321feb407fe6a7f77213f3b5c2bb411`.
  It keeps the V1493/V1496 PID1 provider-triggered corrected RC1 enumerate
  (`rc_sel=2` + `case=11`) and adds micro + case-aligned micro samples at
  0/1/2/5/10/20/50/100/150ms after the case write, with focused endpoint
  sampling for `pcie_1_gdsc`, PCIe1 clocks/refclk, GPIO102/PERST,
  GPIO103/CLKREQ, GPIO104/WAKE, GPIO135/AP2MDM, GPIO142/MDM2AP, pinmux/pinconf,
  interrupts, and RC1 link-state files. The shared marker verifier now accepts
  auto-readiness + case-aligned micro sampler combinations without requiring
  the older read-only sampler-name string. V1499 performed no device command or
  live action. V1500 should run local artifact sanity over the exact V1499
  manifest before any rollbackable live handoff. Report:
  `docs/reports/NATIVE_INIT_V1499_WIFI_AUTO_READINESS_PRE_L0_PARITY_SOURCE_BUILD_2026-06-01.md`.
- V1500 local-only artifact sanity passes with
  `v1500-wifi-auto-readiness-pre-l0-parity-artifact-sanity-pass`. It adds
  `scripts/revalidation/native_wifi_test_boot_artifact_sanity_v1500.py` and
  verifies the exact V1499 artifact. Checks passed for manifest decision, base
  boot existence, init/helper sha and static linkage, ramdisk entries, boot
  markers, AP2MDM-hold marker absence, pre-L0 parity contract, v724
  header/kernel parity, forbidden credential-like byte absence, and private
  output modes. V1500 performed no device command or live action. V1501 may
  perform a rollbackable live handoff for only the V1499 image, expecting
  `A90 Linux init 0.9.93 (v1499-wifitest)`, collecting the V1499 log, summary,
  RC1 watcher result, pre-L0 parity result, focused dmesg, and `wlan0` state,
  then rolling back to `stage3/boot_linux_v724.img` and verifying selftest
  `fail=0`. Report:
  `docs/reports/NATIVE_INIT_V1500_WIFI_AUTO_READINESS_PRE_L0_PARITY_ARTIFACT_SANITY_2026-06-01.md`.
- V1501 rollbackable live handoff passes with
  `v1501-test-boot-downstream-progress-rollback-pass`. It adds
  `scripts/revalidation/native_wifi_test_boot_handoff_v1501.py`, boots only the
  V1499 pre-L0 parity test image, collects log/summary/RC1 watcher/pre-L0 parity
  result/focused dmesg/`wlan0`, and rolls back to v724 from native. The collected
  progress decision remains `rc1-ltssm-link-failed-no-l0`: corrected RC1
  enumerate succeeds, PHY/LTSSM progresses, L0 stays absent, and no
  MHI/WLFW/BDF/FW-ready/`wlan0` appears. Report:
  `docs/reports/NATIVE_INIT_V1501_WIFI_PRE_L0_PARITY_HANDOFF_2026-06-01.md`.
- V1502 host-only V1501 evidence classifier passes with
  `v1502-pre-l0-parity-confirms-rc1-link-fail-with-endpoint-lines-low`. It adds
  `scripts/revalidation/native_wifi_pre_l0_parity_classifier_v1502.py` and fixes
  the evidence interpretation gap left by the generic V1501 report: all nine
  case-aligned micro samples are present at 0/1/2/5/10/20/50/100/150ms after
  `case=11`, GPIO102/PERST remains `out 0`, GPIO103/CLKREQ remains `in 1`,
  GPIO104/WAKE remains `in 0`, GPIO135/AP2MDM remains `out 0`, GPIO142/MDM2AP
  remains `in 0`, and GPIO104/GPIO142 IRQ counts stay zero. The 200ms post
  sample shows `pcie_1_gdsc` and PCIe1 focused clocks off with refgen available,
  but that 200ms sample may be after link-failure cleanup. Next work should
  either add focused regulator/clock/GDSC reads to each micro sample or capture
  an Android-good RC1 parity reference before returning to firmware/MHI/WLFW
  work. Report:
  `docs/reports/NATIVE_INIT_V1502_WIFI_PRE_L0_PARITY_CLASSIFIER_2026-06-01.md`.
- V1503 source/build-only dense pre-L0 parity test boot passes with
  `v1503-wifi-dense-pre-l0-parity-test-boot-source-build-pass`. It adds
  `scripts/revalidation/build_native_init_wifi_test_boot_v1503.py` and builds
  `A90 Linux init 0.9.94 (v1503-wifitest)` at
  `tmp/wifi/v1503-wifi-dense-pre-l0-parity-test-boot/boot_linux_v1503_wifi_test.img`
  (`sha256=dbb0ee6feb6fa2640797d6bd9b1901b4e7c20af8cea1e0af4c7eaee8bc68d522`).
  The image keeps the corrected RC1 enumerate path and adds
  `micro_focused_*` regulator/clock/GDSC/GPIO/pinmux/pinconf reads to every
  0/1/2/5/10/20/50/100/150ms case-aligned micro sample after `case=11`.
  Report:
  `docs/reports/NATIVE_INIT_V1503_WIFI_DENSE_PRE_L0_PARITY_SOURCE_BUILD_2026-06-01.md`.
- V1504 local-only artifact sanity passes with
  `v1504-wifi-dense-pre-l0-parity-artifact-sanity-pass`. It adds
  `scripts/revalidation/native_wifi_test_boot_artifact_sanity_v1504.py` and
  verifies the exact V1503 artifact: manifest decision, static init/helper,
  ramdisk entries, boot markers, dense pre-L0 parity contract, v724
  header/kernel parity, forbidden credential-like byte absence, private modes,
  and AP2MDM-hold marker absence. V1505 may perform a rollbackable live handoff
  for only the V1503 image, collect dense pre-L0 parity result and focused
  dmesg, then roll back to v724 and verify selftest `fail=0`. Report:
  `docs/reports/NATIVE_INIT_V1504_WIFI_DENSE_PRE_L0_PARITY_ARTIFACT_SANITY_2026-06-01.md`.
- V1505 rollbackable live handoff passes with
  `v1505-test-boot-downstream-progress-rollback-pass`. It adds
  `scripts/revalidation/native_wifi_test_boot_handoff_v1505.py`, boots only the
  V1503 dense image, collects V1503 log/summary/RC1 watcher/dense pre-L0 parity
  result/focused dmesg/`wlan0`, then rolls back to v724 from native. Rollback
  succeeds and v724 selftest stays `fail=0`; the progress decision remains
  `rc1-ltssm-link-failed-no-l0`. Report:
  `docs/reports/NATIVE_INIT_V1505_WIFI_DENSE_PRE_L0_PARITY_HANDOFF_2026-06-01.md`.
- V1506 host-only V1505 evidence classifier passes with
  `v1506-dense-pre-l0-captures-off-state-but-overruns-micro-window`. It adds
  `scripts/revalidation/native_wifi_dense_pre_l0_parity_classifier_v1506.py`.
  Dense focused reads confirm `pcie_1_gdsc` and PCIe1 clocks are off, refgen is
  available, GPIO102/103/104/135/142 are in expected states, GPIO142 IRQ stays
  zero, and no L0/MHI/WLFW/BDF/FW-ready/`wlan0` appears. But the exact-match
  dense sampler overruns the micro schedule: nominal `1ms` starts near
  `1007ms`, and max sample elapsed reaches about `12564ms`. V1507 should be
  source/build-only and replace per-needle exact-match scanning with a batched
  per-file sampler that reads each debugfs file at most once per sample. Report:
  `docs/reports/NATIVE_INIT_V1506_WIFI_DENSE_PRE_L0_PARITY_CLASSIFIER_2026-06-01.md`.
- V1507 source/build-only batched pre-L0 parity test boot passes with
  `v1507-wifi-batched-pre-l0-parity-test-boot-source-build-pass`. It extends
  the shared V1393 builder/C hook with
  `A90_WIFI_TEST_BOOT_RC1_MICRO_BATCHED_FOCUSED_ENDPOINT_SAMPLER` and adds
  `scripts/revalidation/build_native_init_wifi_test_boot_v1507.py`. The
  generated image is
  `tmp/wifi/v1507-wifi-batched-pre-l0-parity-test-boot/boot_linux_v1507_wifi_test.img`
  (`sha256=d3e92460ff1d68a80a99c8b7dbb5b0997ea88c53e120b8e507671e16d5bee8b4`),
  native init `0.9.95 (v1507-wifitest)`. The batched sampler emits
  `micro_batched_regulator`, `micro_batched_clk`, `micro_batched_debug_gpio`,
  `micro_batched_pinmux`, and `micro_batched_pinconf`, scanning each debugfs
  file at most once per micro sample. V1508 should run local artifact sanity
  over this exact manifest before any rollbackable live handoff. Report:
  `docs/reports/NATIVE_INIT_V1507_WIFI_BATCHED_PRE_L0_PARITY_SOURCE_BUILD_2026-06-01.md`.
- V1508 local-only artifact sanity passes with
  `v1508-wifi-batched-pre-l0-parity-artifact-sanity-pass`. It adds
  `scripts/revalidation/native_wifi_test_boot_artifact_sanity_v1508.py` and
  verifies the exact V1507 image, manifest decision, static init/helper,
  ramdisk entries, batched pre-L0 contract, v724 header/kernel parity,
  private modes, and forbidden credential-like byte absence. Report:
  `docs/reports/NATIVE_INIT_V1508_WIFI_BATCHED_PRE_L0_PARITY_ARTIFACT_SANITY_2026-06-01.md`.
- V1509 rollbackable live handoff passes with
  `v1509-test-boot-downstream-progress-rollback-pass`. It adds
  `scripts/revalidation/native_wifi_test_boot_handoff_v1509.py`, boots only the
  V1507 batched pre-L0 image, collects V1507 log/summary/RC1 watcher/batched
  result/focused dmesg/`wlan0`, rolls back to v724 from native, and verifies
  selftest `fail=0`. Progress remains `rc1-ltssm-link-failed-no-l0`: RC1
  reaches PHY/LTSSM and link failure, but no L0/MHI/WLFW/BDF/FW-ready/`wlan0`
  appears. Report:
  `docs/reports/NATIVE_INIT_V1509_WIFI_BATCHED_PRE_L0_PARITY_HANDOFF_2026-06-01.md`.
- V1510 host-only V1509 evidence classifier passes with
  `v1510-batched-pre-l0-improves-sampling-but-source-timestamps-needed`. It
  adds `scripts/revalidation/native_wifi_batched_pre_l0_parity_classifier_v1510.py`.
  Batched reads confirm `pcie_1_gdsc` and PCIe1 clocks are off, refgen is
  available, GPIO102/103/104/135/142 are in expected states, GPIO142 IRQ stays
  zero, and no L0/MHI/WLFW/BDF/FW-ready/`wlan0` appears. The sampler improves
  over V1505, but still lacks per-source begin/end timing; first sample starts
  at case+0ms and the second starts around `148ms`, after the ~`114.8ms`
  link-fail marker. V1511 should be source/build-only and add source
  begin/end timestamps to the batched sampler or narrow capture to critical
  files only. Report:
  `docs/reports/NATIVE_INIT_V1510_WIFI_BATCHED_PRE_L0_PARITY_CLASSIFIER_2026-06-01.md`.
- V1511 source/build-only source-timestamped pre-L0 test boot passes with
  `v1511-wifi-source-timestamped-pre-l0-test-boot-source-build-pass`. It
  extends the shared V1393 builder/C hook with
  `A90_WIFI_TEST_BOOT_RC1_MICRO_SOURCE_TIMESTAMPED_SAMPLER` and adds
  `scripts/revalidation/build_native_init_wifi_test_boot_v1511.py`. The image
  is
  `tmp/wifi/v1511-wifi-source-timestamped-pre-l0-test-boot/boot_linux_v1511_wifi_test.img`
  (`sha256=9a3ff92c488f41f77ce4fdb1fee403229ea12e408fb5b86773c945623d074e57`),
  native init `0.9.96 (v1511-wifitest)`. It keeps V1507 batched reads and adds
  `source_timing=begin/end` plus `source_duration_ms` around each micro source
  read. Report:
  `docs/reports/NATIVE_INIT_V1511_WIFI_SOURCE_TIMESTAMPED_PRE_L0_SOURCE_BUILD_2026-06-01.md`.
- V1512 local-only artifact sanity passes with
  `v1512-wifi-source-timestamped-pre-l0-artifact-sanity-pass`. It adds
  `scripts/revalidation/native_wifi_test_boot_artifact_sanity_v1512.py` and
  verifies the exact V1511 image, manifest decision, static init/helper,
  ramdisk entries, source-timestamped pre-L0 contract, v724 header/kernel
  parity, private modes, and forbidden credential-like byte absence. Report:
  `docs/reports/NATIVE_INIT_V1512_WIFI_SOURCE_TIMESTAMPED_PRE_L0_ARTIFACT_SANITY_2026-06-01.md`.
- V1513 rollbackable live handoff passes with
  `v1513-test-boot-downstream-progress-rollback-pass`. It adds
  `scripts/revalidation/native_wifi_test_boot_handoff_v1513.py`, boots only the
  V1511 source-timestamped image, collects V1511 log/summary/RC1 watcher/source
  timing result/focused dmesg/`wlan0`, rolls back to v724 from native, and
  verifies selftest `fail=0`. Progress remains `rc1-ltssm-link-failed-no-l0`.
  Report:
  `docs/reports/NATIVE_INIT_V1513_WIFI_SOURCE_TIMESTAMPED_PRE_L0_HANDOFF_2026-06-01.md`.
- V1514 host-only V1513 evidence classifier passes with
  `v1514-source-timing-identifies-clk-summary-overrun`. It adds
  `scripts/revalidation/native_wifi_source_timing_classifier_v1514.py`. The
  first sample begins at case+0ms and fast sources finish before link failure,
  but full `clk_summary` spans about `35ms` to `149ms`, crossing the
  ~`114.9ms` RC1 link-fail marker. V1515 should be source/build-only and add a
  critical-source pre-L0 sampler that avoids full `clk_summary` during the
  first link-fail window. Report:
  `docs/reports/NATIVE_INIT_V1514_WIFI_SOURCE_TIMING_CLASSIFIER_2026-06-01.md`.
- V1515 source/build-only critical-source pre-L0 test boot passes with
  `v1515-wifi-critical-source-pre-l0-test-boot-source-build-pass`. It extends
  the shared V1393 builder/C hook with
  `A90_WIFI_TEST_BOOT_RC1_MICRO_CRITICAL_FAST_ENDPOINT_SAMPLER` and adds
  `scripts/revalidation/build_native_init_wifi_test_boot_v1515.py`. The image
  is
  `tmp/wifi/v1515-wifi-critical-source-pre-l0-test-boot/boot_linux_v1515_wifi_test.img`
  (`sha256=b2578c7bec6565ae051d7101e8e6074890f8151b99767ed4ac27f2aa69df9b78`),
  native init `0.9.97 (v1515-wifitest)`. It keeps source timing but skips full
  `clk_summary` during the first link-fail window, emitting fast
  `micro_critical_regulator` and `micro_critical_pinmux` instead. Report:
  `docs/reports/NATIVE_INIT_V1515_WIFI_CRITICAL_SOURCE_PRE_L0_SOURCE_BUILD_2026-06-01.md`.
- V1516 local-only artifact sanity passes with
  `v1516-wifi-critical-source-pre-l0-artifact-sanity-pass`. It adds
  `scripts/revalidation/native_wifi_test_boot_artifact_sanity_v1516.py` and
  verifies the exact V1515 image, manifest decision, static init/helper,
  ramdisk entries, critical-source contract, v724 header/kernel parity,
  private modes, and forbidden credential-like byte absence. Report:
  `docs/reports/NATIVE_INIT_V1516_WIFI_CRITICAL_SOURCE_PRE_L0_ARTIFACT_SANITY_2026-06-01.md`.
- V1517 rollbackable live handoff passes with
  `v1517-test-boot-downstream-progress-rollback-pass`. It adds
  `scripts/revalidation/native_wifi_test_boot_handoff_v1517.py`, boots only the
  V1515 critical-source image, collects V1515 log/summary/RC1 watcher/critical
  timing result/focused dmesg/`wlan0`, rolls back to v724 from native, and
  verifies selftest `fail=0`. Progress remains `rc1-ltssm-link-failed-no-l0`.
  Report:
  `docs/reports/NATIVE_INIT_V1517_WIFI_CRITICAL_SOURCE_PRE_L0_HANDOFF_2026-06-01.md`.
- V1518 host-only V1517 evidence classifier passes with
  `v1518-critical-source-first-window-pre-fail-confirmed`. It adds
  `scripts/revalidation/native_wifi_critical_source_timing_classifier_v1518.py`.
  Selected first-window sources finish by about `30ms` after `case=11`, before
  the ~`114.9ms` RC1 link-fail marker. In that source-exact pre-fail window,
  GPIO135/GPIO142 remain low, `pcie_1_gdsc` remains `0mV`, pinmux ownership is
  visible, and no L0/MHI/WLFW/BDF/FW-ready/`wlan0` appears. V1519 should
  compare Android-good and native-fail critical source timing/order before any
  new live mutation. Report:
  `docs/reports/NATIVE_INIT_V1518_WIFI_CRITICAL_SOURCE_TIMING_CLASSIFIER_2026-06-01.md`.
- V1519 host-only Android-good/native-fail comparator passes with
  `v1519-android-good-native-fail-compared-matched-rc1-source-capture-needed`.
  It adds
  `scripts/revalidation/native_wifi_android_good_native_fail_critical_comparison_v1519.py`
  and compares V1518/V1517 native source-exact failure evidence against V852,
  V896, V1239, and V1331 Android-good references. The result keeps the blocker
  at `rc1-ltssm-link-failed-no-l0`, but corrects the GPIO interpretation:
  GPIO135/GPIO142 low readback is not independently discriminating because
  Android-good static snapshots also show low readback while Android reaches
  GPIO142 IRQ, PCIe L0, WLFW/BDF, and `wlan0`. V1520 should capture or classify
  a matched Android-good critical-source RC1 timeline for pcie1 GDSC/clock,
  refclk, PERST/reset, and the exact normal RC1 path before another native
  mutation. Report:
  `docs/reports/NATIVE_INIT_V1519_ANDROID_GOOD_NATIVE_FAIL_CRITICAL_SOURCE_COMPARISON_2026-06-01.md`.
- V1520 rollbackable Android handoff passes with
  `v1520-handoff-adb-sampler-missed-pre-l0-rollback-pass`. It adds
  `scripts/revalidation/native_wifi_android_rc1_early_critical_source_sample_v1520.py`
  and `scripts/revalidation/android_rc1_early_critical_source_handoff_v1520.py`.
  The plain early-ADB sampler does not start early enough for the RC1 pre-L0
  source window: the first sample is at uptime `13.85s`, after Android WLFW
  `8.433089s` and BDF `9.561577s`; Android reaches `wlan0` at `15.214683s`.
  This closes the plain-ADB capture path and makes V1521 an earlier Android
  boot-hook problem, not another native RC1 mutation. The preferred next gate is
  a temporary Magisk `post-fs-data` read-only sampler or equivalent earlier
  Android boot hook that starts before WLFW/BDF, captures the same
  GPIO/interrupt/pinctrl/pcie1 regulator/clock/refclk/PERST sources, writes
  only to `/data/local/tmp` or a bounded evidence path, and is removed before
  rollback. Report:
  `docs/reports/NATIVE_INIT_V1520_ANDROID_RC1_EARLY_CRITICAL_SOURCE_HANDOFF_2026-06-01.md`.
- V1521 rollbackable Android Magisk post-fs-data handoff passes with
  `v1521-magisk-postfs-pre-lower-window-rollback-pass`. It adds
  `scripts/revalidation/android_rc1_magisk_postfs_sampler_handoff_v1521.py`,
  installs a temporary read-only Magisk module from Android `su`, collects early
  Android-good post-fs-data samples, captures host dmesg before cleanup, removes
  the module/evidence, reboots recovery, and restores `stage3/boot_linux_v724.img`.
  The sampler starts at uptime `5.72s`, brackets the first lower Wi-Fi marker
  with samples before/after WLFW `8.585121s`, and records BDF at `9.673077s` and
  `wlan0` at `14.843021s`; rollback verifies native v724 and selftest remains
  `fail=0`. The important interpretation is negative: Android-good pre/post
  lower samples still report GPIO135/GPIO142 low, GPIO142 IRQ count `0`, and
  `pcie_1_gdsc` `0mV`, so those debugfs/interrupt/regulator snapshots alone are
  not discriminating. V1522 should compare V1521 Android-good samples directly
  against V1518/V1517 native pre-fail samples, then move to `msm_pcie` TEST:11
  vs normal-path static/callgraph analysis if the source comparison does not
  explain why native TEST:11 reaches `POLL_COMPLIANCE` but no L0. Report:
  `docs/reports/NATIVE_INIT_V1521_ANDROID_RC1_MAGISK_POSTFS_HANDOFF_2026-06-01.md`.
- V1522 host-only Android/native RC1 source parity classifier passes with
  `v1522-sampled-sources-nondiscriminating-msm-pcie-static-needed`. It adds
  `scripts/revalidation/native_wifi_android_native_rc1_source_parity_classifier_v1522.py`
  and compares V1521 Android-good pre/post lower samples against V1518/V1517
  native pre-fail samples. V1521 proves Android-good WLFW/BDF/`wlan0`, while
  V1518/V1517 prove native `rc1-ltssm-link-failed-no-l0`; nevertheless the
  sampled GPIO/debugfs/interrupt/regulator fields overlap: GPIO135/GPIO142 low,
  GPIO142 IRQ count `0`, and `pcie_1_gdsc` `0mV` are visible in Android-good and
  native-fail windows. This closes those sampled sources as root-cause evidence.
  V1523 should classify `msm_pcie` corrected TEST:11 vs Android normal-path
  static/callgraph semantics and list operations TEST:11 lacks before any new
  native mutation. Report:
  `docs/reports/NATIVE_INIT_V1522_ANDROID_NATIVE_RC1_SOURCE_PARITY_CLASSIFIER_2026-06-01.md`.
- V1523 host-only `msm_pcie` TEST:11 vs normal-path static/callgraph classifier
  passes with `v1523-test11-shares-enable-normal-trigger-readiness-gap`. It
  adds
  `scripts/revalidation/native_wifi_msm_pcie_test11_vs_normal_path_classifier_v1523.py`
  and compares corrected TEST:11 with the public `pci-msm.c` normal entry
  points plus local SM8150 PCIe DTS. TEST:11 is not missing the common AP-side
  enable sequence: debugfs TEST:11, sysfs/client enumeration, endpoint-wake
  work, and non-deferred probe all converge on
  `msm_pcie_enumerate() -> msm_pcie_enable(PM_ALL)`. Local pcie1 has
  `qcom,boot-option=<0x1>`, so probe-time enumeration is intentionally skipped.
  The blocker therefore moves to pre-enumerate endpoint readiness/trigger
  semantics that Android satisfies and native TEST:11 does not. V1524 should
  classify Android-good and native-fail evidence for endpoint wake IRQ/GPIO104,
  sysfs/client caller, or vendor client request before another native mutation.
  Report:
  `docs/reports/NATIVE_INIT_V1523_MSM_PCIE_TEST11_VS_NORMAL_PATH_CLASSIFIER_2026-06-02.md`.
- V1524 host-only endpoint-trigger attribution classifier passes with
  `v1524-trigger-attribution-pivots-to-esoc-mhi-pm-resume`. It adds
  `scripts/revalidation/native_wifi_endpoint_trigger_attribution_classifier_v1524.py`
  and compares V852 Android-good RC1 evidence, V1521 Android-good sampled
  IRQ/dmesg evidence, V1517 native TEST:11 failure evidence, local
  `mhi_arch_qcom.c`, and public `pci-msm.c`. Android-good initial RC1 is not
  observed as debugfs TEST:11, while native V1517 is explicitly TEST:11 and
  fails before L0. Existing Android-good GPIO104 wake IRQ evidence is
  contradictory enough that endpoint wake cannot be treated as the proven
  initial trigger. The new source-supported candidate is eSoC/MHI PM-resume:
  `mhi_arch_esoc_ops_power_on()` calls
  `msm_pcie_pm_control(MSM_PCIE_RESUME, ...)`, which dispatches to
  `msm_pcie_pm_resume()` and reaches `msm_pcie_enable(PM_PIPE_CLK | PM_CLK |
  PM_VREG)` before `mhi_pci_probe()`. V1525 should compare the MHI/eSoC
  PM-resume path against TEST:11 `PM_ALL` semantics before any new live
  mutation. Report:
  `docs/reports/NATIVE_INIT_V1524_ENDPOINT_TRIGGER_ATTRIBUTION_CLASSIFIER_2026-06-02.md`.
- V1525 host-only MHI PM-resume position classifier passes with
  `v1525-mhi-pm-resume-is-post-enumeration-not-first-l0-trigger`. It adds
  `scripts/revalidation/native_wifi_mhi_pm_resume_position_classifier_v1525.py`
  and validates the V1524 eSoC/MHI PM-resume candidate against local
  `mhi_arch_qcom.c`, local `mhi_qcom.c`, public `pci-msm.c`, V852 Android-good
  dmesg, and V1517 native TEST:11 failure evidence. The MHI/eSoC
  `MSM_PCIE_RESUME` path is real, but it requires an existing `pci_dev`:
  `mhi_arch_esoc_ops_power_on()` reads `mhi_dev->pci_dev`, pci-msm casts the
  caller to `struct pci_dev`, and pci-msm validates it against `pcidev_table`.
  The eSoC hook is registered from MHI PCI init/probe, so it cannot be the
  operation that creates the first PCI device or first L0. It explains later
  Android RC1 resume cycles, not the missing native first-L0 transition. V1526
  should capture or classify the Android-only first-L0 trigger below Wi-Fi
  connect: endpoint wake IRQ timing, pci-msm sysfs/client enumerate, or another
  kernel caller. Report:
  `docs/reports/NATIVE_INIT_V1525_MHI_PM_RESUME_POSITION_CLASSIFIER_2026-06-02.md`.
- V1526 host-only Android initial RC1 trigger capture design passes with
  `v1526-android-initial-rc1-trigger-capture-design-ready`. It adds
  `scripts/revalidation/android_initial_rc1_trigger_capture_design_v1526.py`
  and defines the V1527 capture contract. Fixed points: Android V852 has
  `esoc0` at `8.541440s`, first RC1 assert at `8.796369s`, and first L0 at
  `8.820231s` without a debugfs TEST marker; native V1517 uses explicit
  TEST:11 and fails before L0; V1525 closes MHI PM-resume as first-L0 trigger.
  V1521's temporary Magisk post-fs-data handoff starts early enough
  (`5.72s`) but its IRQ snapshots stayed zero, so V1527 should extend that
  rollbackable Android-good handoff with raw `/dev/kmsg` or `dmesg -w` capture
  plus high-cadence GPIO104/GPIO142 `/proc/interrupts` and debug GPIO samples.
  Success labels: raw kmsg caller found, endpoint wake before L0, mdm status
  before/during L0, or opaque kernel caller requiring tracefs. Report:
  `docs/reports/NATIVE_INIT_V1526_ANDROID_INITIAL_RC1_TRIGGER_CAPTURE_DESIGN_2026-06-02.md`.
- V1527 rollbackable Android initial RC1 trigger handoff source/plan passes with
  `v1527-handoff-plan-ready`. It adds
  `scripts/revalidation/android_initial_rc1_trigger_handoff_v1527.py` and
  generates
  `docs/reports/NATIVE_INIT_V1527_ANDROID_INITIAL_RC1_TRIGGER_HANDOFF_2026-06-02.md`.
  The runner reuses the proven V1521 Magisk/rollback handoff engine, but
  installs a V1527 temporary post-fs-data sampler that captures raw
  `/dev/kmsg` or `dmesg -w` plus high-cadence GPIO104/GPIO142 interrupt,
  debug GPIO, and pcie1 state samples. Plan mode verified the full
  Android-boot handoff/rollback step list without mutating the device. Live
  execution remains a separate explicit gate and must keep the hard exclusions:
  no Wi-Fi HAL start, scan/connect, credentials, DHCP/routes, external ping,
  PMIC/GPIO/GDSC writes, blind eSoC notify, PCI rescan, or platform bind/unbind.
- V1528 host-only V1527 evidence escalation classifier passes with
  `v1528-route-to-android-tracefs-event-capture`. V1527 live evidence proves
  Android-good WLFW/BDF/`wlan0` and native rollback, but raw kmsg contains zero
  RC1/LTSSM lines, GPIO104/GPIO142 IRQ totals remain zero, and GPIO135/GPIO142
  debugfs levels remain low during the successful lower Wi-Fi window. Treat
  those sources as nondiscriminating for this blocker. Next gate: V1529 should
  reuse the rollbackable Android handoff and capture bounded tracefs events
  around the `pm-service`/`subsys_esoc0` window. Report:
  `docs/reports/NATIVE_INIT_V1528_V1527_EVIDENCE_TRACEFS_ESCALATION_2026-06-02.md`.
- V1529 rollbackable Android tracefs RC1 event handoff passes with partial
  evidence and native rollback: `v1529-tracefs-event-partial-rollback-pass`.
  It adds `scripts/revalidation/android_tracefs_rc1_event_handoff_v1529.py`
  and captures bounded tracefs events under the V1521/V1527 Android
  boot/Magisk/native-rollback harness. Android-good lower markers recur:
  `wlfw_start=43.208627s`, `subsys_esoc0=43.367958s`, BDF at `44.452551s`,
  FW-ready at `49.369675s`, and `wlan0=49.864980s`. Tracefs adds modem PIL
  notifications at `40.820s..41.328s`, `icnss_driver_event_work=40.836714s`,
  and `pm-service` exec at `41.922287s`; no eSoC/SDX50M PIL notification
  appears. IRQ trace events were removed from the final runner after the first
  broad run proved too noisy. The run remains partial because the module `done`
  marker was not observed before pull, but rollback passed and the evidence is
  usable. Next gate: V1530 should classify this trace against native no-L0 and
  design a narrower targeted observer rather than rerunning broad workqueue
  capture.
  Report:
  `docs/reports/NATIVE_INIT_V1529_ANDROID_TRACEFS_RC1_EVENT_HANDOFF_2026-06-02.md`.
- V1530 host-only Android tracefs vs native no-L0 classifier passes with
  `v1530-android-tracefs-confirms-opaque-initial-rc1-trigger`. It adds
  `scripts/revalidation/native_wifi_android_tracefs_native_no_l0_classifier_v1530.py`
  and reconciles V1529 Android tracefs evidence against V1496/V1517 native
  no-L0 references plus V1523/V1525 source classifiers. V1529 proves
  Android-good lower progress and captures modem PIL notifications,
  `icnss_driver_event_work`, `pm-service` exec, WLFW/BDF/FW-ready, and `wlan0`,
  while still exposing no eSoC/SDX50M `pil_notif` and no RC1/LTSSM text. Native
  V1496/V1517 stay fixed at `rc1-ltssm-link-failed-no-l0`, and V1523/V1525
  already rule out missing TEST:11 AP-side enable semantics and MHI PM-resume
  as first-L0 triggers. Next gate: V1531 should be a targeted Android/source
  classifier for `icnss_driver_event_work`, `pm-service` Binder
  `subsystem_get`, and pci-msm initial enumerate callsites before any new
  native mutation.
  Report:
  `docs/reports/NATIVE_INIT_V1530_ANDROID_TRACEFS_NATIVE_NO_L0_CLASSIFIER_2026-06-02.md`.
- V1531 host-only targeted trace/source classifier passes with
  `v1531-targeted-trace-source-classifies-visible-signals-not-trigger`. It adds
  `scripts/revalidation/native_wifi_targeted_trace_source_classifier_v1531.py`
  and maps V1529/V1530 evidence against local ICNSS source, pm-service binary
  strings, and local `pci-msm.c`. Source confirms `icnss_driver_event_work` is
  only a shared dispatcher for SERVER_ARRIVE, FW_READY, REGISTER_DRIVER, and
  other ICNSS events, so V1529's `workqueue_execute_start` line cannot identify
  the event type by itself. pm-service is the proprietary
  `vendor.qcom.PeripheralManager` Binder/QMI voter actor and V1529 sees the
  Android sequence `pm-service exec -> Binder subsystem_get(modem) -> WLFW
  start -> Binder subsystem_get(esoc0) -> QMI server -> BDF -> FW-ready ->
  wlan0`. pci-msm TEST:11, wake IRQ work, sysfs enumerate, and probe paths all
  converge on `msm_pcie_enumerate`, while native still reaches enable/LTSSM and
  fails before L0. Next gate: V1532 should design or run a targeted Android
  tracefs capture with `workqueue_queue_work` plus execute pairing and
  pm-service Binder subsystem timing, still avoiding broad IRQ tracing and all
  Wi-Fi connect/credential/network paths.
  Report:
  `docs/reports/NATIVE_INIT_V1531_TARGETED_TRACE_SOURCE_CLASSIFIER_2026-06-02.md`.
- V1532 rollbackable Android targeted tracefs queue-pair handoff passes with
  `v1532-targeted-tracefs-partial-rollback-pass`. It adds
  `scripts/revalidation/android_targeted_tracefs_queue_pair_handoff_v1532.py`
  and executes the bounded Android/Magisk/native-rollback handoff with sched
  exec, workqueue queue/activate/execute, PIL, and printk console tracefs
  events. The run captures Android-good lower Wi-Fi progress and one paired
  `icnss_driver_event_work` queue/execute item, then restores native v724 with
  `selftest` verification. `native_init_flash.py` now supports
  `--verify-protocol selftest`, and the V1532 handoff replaces native
  `version`/`status` precheck with `selftest` to avoid sensitive status text in
  new evidence. Report:
  `docs/reports/NATIVE_INIT_V1532_ANDROID_TARGETED_TRACEFS_QUEUE_PAIR_HANDOFF_2026-06-02.md`.
- V1533 host-only queue-pair classifier passes with
  `v1533-icnss-queue-pair-is-hdd-register-path-not-first-l0-trigger`. It adds
  `scripts/revalidation/native_wifi_v1532_queue_pair_classifier_v1533.py` and
  classifies the V1532 pair: `/vendor/bin/hw/macloader` queues
  `icnss_driver_event_work` during WLAN driver load at ~40.882s, it executes
  about 0.012 ms later, and it precedes pm-service `subsys_esoc0` by ~2.78s
  and QMI server connect by ~3.54s. Therefore the visible ICNSS workqueue event
  is HDD/register-driver path evidence, not Android's first-L0 trigger. Next
  gate: V1534 should target pm-service Binder/QMI voter behavior around
  `subsys_esoc0` and the immediate pci-msm first-L0 path; do not return to
  firmware/MHI/WLFW until native L0 and PCI enumeration exist. Report:
  `docs/reports/NATIVE_INIT_V1533_V1532_QUEUE_PAIR_CLASSIFIER_2026-06-02.md`.
- V1534 host-only PM route first-L0 focus classifier passes with
  `v1534-current-pm-route-supersedes-old-gap-first-l0-focus`. It adds
  `scripts/revalidation/native_wifi_pm_route_first_l0_focus_classifier_v1534.py`
  and reclassifies the PM-service branch against the current route. The older
  V1178 late-`per_proxy` dependency gap is preserved as historical context, but
  V1343 proves current SDX50M registration plus `per_mgr_esoc0`, V1345 proves
  current-route `mdm_subsys_powerup` with no lower response, V1496/V1517 prove
  RC1 LTSSM progress with no L0, V1523 proves TEST:11 shares the core pci-msm
  enumerate/enable path with normal callers, and V1525/V1533 close MHI
  PM-resume plus ICNSS workqueue as first-L0 leads. The active blocker is now
  PCIe RC1 endpoint readiness/link training, not PM registration or
  firmware/MHI. Next gate: V1535 should design or run a bounded first-L0
  trigger/readiness observer focused on endpoint wake GPIO104, sysfs/client
  enumerate, or vendor request semantics around `msm_pcie_enumerate`, with
  rollback and no scan/connect path. Report:
  `docs/reports/NATIVE_INIT_V1534_PM_ROUTE_FIRST_L0_FOCUS_CLASSIFIER_2026-06-02.md`.
- V1535 host-only first-L0 trigger candidate classifier passes with
  `v1535-first-l0-candidates-narrowed-to-client-enumerate-or-endpoint-readiness`.
  It adds
  `scripts/revalidation/native_wifi_first_l0_trigger_candidate_classifier_v1535.py`
  and fixes the next action around the current lowest blocker. V1496/V1517
  prove native RC1/LTSSM progress with no L0, V1523 proves TEST:11 and normal
  callers converge on `msm_pcie_enumerate`, V1525 closes MHI PM-resume, V1533
  closes visible ICNSS workqueue, and Android V852/V1527/V1529/V1532 do not
  prove endpoint wake GPIO104 or trace-visible RC1 as the initial caller. The
  only AP-side trigger still worth an empirical close-out is targeted
  sysfs/client enumerate; if that path also reaches LTSSM but no L0, move focus
  to endpoint electrical/readiness around PERST/refclk/reset/SDX50M response.
  Next gate: V1536 source/build-only rollbackable test-boot variant that uses
  targeted pci-msm sysfs/client enumerate instead of debugfs TEST:11. Keep no
  global PCI rescan, no platform bind/unbind, no PMIC/GPIO/GDSC writes, no
  eSoC notify/BOOT_DONE spoof, and no Wi-Fi HAL/scan/connect/credentials/DHCP/
  routes/external ping. Report:
  `docs/reports/NATIVE_INIT_V1535_FIRST_L0_TRIGGER_CANDIDATE_CLASSIFIER_2026-06-02.md`.
- V1536/V1537 sysfs/client enumerate test-boot preparation passes. V1536 adds
  `scripts/revalidation/build_native_init_wifi_test_boot_v1536.py`, extends
  the V1393 build base with `--wifi-test-rc1-sysfs-client-enumerate`, and adds
  a PID1 writer mode that targets
  `/sys/devices/platform/soc/1c08000.qcom,pcie/debug/enumerate` instead of
  debugfs `rc_sel=2` + `case=11`. It preserves the V1515 critical-source,
  source-timestamped, case-aligned micro sampling contract and builds
  `tmp/wifi/v1536-wifi-sysfs-client-enumerate-test-boot/boot_linux_v1536_wifi_test.img`
  with SHA256
  `9a8f10f9ae3cf6247faa49e78baa2fa9de5ce2539380893c8b7a777923b4e527`.
  V1537 adds
  `scripts/revalidation/native_wifi_test_boot_artifact_sanity_v1537.py` and
  passes local artifact sanity with
  `v1537-wifi-sysfs-client-enumerate-artifact-sanity-pass`. The shared
  rollbackable handoff base now requests `--verify-protocol selftest` from
  `native_init_flash.py` so new flash verifier logs do not need rollback
  version/status output. Next gate: V1538 live handoff for only the V1536 image,
  collect sysfs-client enumerate evidence, roll back to v724, and verify native
  selftest `fail=0`. Reports:
  `docs/reports/NATIVE_INIT_V1536_WIFI_SYSFS_CLIENT_ENUMERATE_SOURCE_BUILD_2026-06-02.md`,
  `docs/reports/NATIVE_INIT_V1537_WIFI_SYSFS_CLIENT_ENUMERATE_ARTIFACT_SANITY_2026-06-02.md`.
- V1538 rollbackable sysfs/client enumerate test-boot handoff passes with
  `v1538-test-boot-downstream-progress-rollback-pass`. The test image wrote
  `/sys/devices/platform/soc/1c08000.qcom,pcie/debug/enumerate` through the
  PID1 `sysfs_client_enumerate` writer, recorded `write_rc=0` / `sysfs_rc=0`,
  collected RC1 watcher/window/dmesg evidence, and rolled back to native v724
  with selftest verification. The result remains `rc1-ltssm-link-failed-no-l0`:
  RC1 assert/release, PHY ready, and LTSSM poll active/compliance are present,
  followed by `PCIe RC1 link initialization failed (LTSSM_STATE:0x3)`. There is
  no L0, MHI, WLFW, BDF, FW-ready, `wlan0`, scan/connect, DHCP/routes, or
  external ping. Report:
  `docs/reports/NATIVE_INIT_V1538_WIFI_SYSFS_CLIENT_ENUMERATE_HANDOFF_2026-06-02.md`.
- V1539 host-only sysfs enumerate result classifier passes with
  `v1539-sysfs-client-enumerate-closes-ap-side-trigger-no-l0`. It adds
  `scripts/revalidation/native_wifi_sysfs_enumerate_result_classifier_v1539.py`
  and classifies V1538 against V1535/V1523. The targeted sysfs/client enumerate
  path is now empirically closed as the remaining AP-side caller question: it
  succeeds as a writer and reaches the same no-L0 RC1 link failure. The active
  blocker moves fully to endpoint readiness/electrical/reset/refclk/PERST
  response around SDX50M and RC1. Next gate: V1540 host-only endpoint-readiness
  classifier; do not repeat enumerate retries or move to firmware/MHI/WLFW/
  Wi-Fi HAL/scan/connect/credentials/DHCP/routes/external ping until native
  RC1 L0 and PCI enumeration exist. Report:
  `docs/reports/NATIVE_INIT_V1539_SYSFS_ENUMERATE_RESULT_CLASSIFIER_2026-06-02.md`.
- V1540 host-only endpoint-readiness classifier passes with
  `v1540-endpoint-readiness-gap-after-sysfs-enumerate`. It adds
  `scripts/revalidation/native_wifi_endpoint_readiness_classifier_v1540.py` and
  reconciles V1538/V1539 against local DTS plus `pci-msm.c`. The RC1 contract
  is now explicit: GPIO102 PERST, GPIO104 WAKE, `pcie_1_gdsc`, `pm8150l_l3`,
  `pm8150_l5`, clkref/refgen/pipe clocks, SDX50M/MHI endpoint `17cb:0305`, and
  eSoC AP2MDM GPIO135 / MDM2AP GPIO142 / PM8150L GPIO9 PON. Source order in
  `msm_pcie_enable()` is PERST assert, vregs/clocks/PHY/pipe, PHY ready, PERST
  release, LTSSM enable, and link polling. Native V1538 reaches this sequence
  but fails at `POLL_COMPLIANCE`/no L0 with GPIO142 IRQ `0` and no
  MHI/WLFW/BDF/FW-ready/`wlan0`; Android V852 reaches L0/current GEN/WLFW/BDF/
  `wlan0`. Next gate: V1541 source/build-only endpoint electrical observer
  design for PERST/refclk/GDSC/CLKREQ/WAKE/AP2MDM/MDM2AP in the exact RC1
  link-training window. Do not repeat enumerate retries or move to
  firmware/MHI/WLFW/Wi-Fi HAL/scan/connect/credentials/DHCP/routes/external
  ping until native RC1 L0 and PCI enumeration exist. Report:
  `docs/reports/NATIVE_INIT_V1540_ENDPOINT_READINESS_CLASSIFIER_2026-06-02.md`.
- V1541/V1542 endpoint-electrical observer test-boot preparation passes.
  V1541 adds `scripts/revalidation/build_native_init_wifi_test_boot_v1541.py`
  and builds the rollbackable test image
  `tmp/wifi/v1541-endpoint-electrical-observer-test-boot/boot_linux_v1541_wifi_test.img`
  with init `A90 Linux init 0.9.99 (v1541-wifitest)` and helper marker
  `a90_android_execns_probe v287`. The image keeps the targeted
  sysfs/client enumerate writer and adds the focused endpoint-state sampler.
  V1542 adds
  `scripts/revalidation/native_wifi_endpoint_electrical_artifact_sanity_v1542.py`
  and passes artifact sanity before any live handoff. Reports:
  `docs/reports/NATIVE_INIT_V1541_ENDPOINT_ELECTRICAL_OBSERVER_SOURCE_BUILD_2026-06-02.md`,
  `docs/reports/NATIVE_INIT_V1542_ENDPOINT_ELECTRICAL_ARTIFACT_SANITY_2026-06-02.md`.
- V1543 rollbackable endpoint-electrical observer handoff passes with
  `v1543-test-boot-downstream-progress-rollback-pass`. The test image writes
  `/sys/devices/platform/soc/1c08000.qcom,pcie/debug/enumerate`, reaches RC1
  assert, PHY-ready, PERST release, LTSSM poll active/compliance, and then
  fails with `PCIe RC1 link initialization failed (LTSSM_STATE:0x3)`. Rollback
  to v724 passes selftest verification. The fixed progress decision remains
  `rc1-ltssm-link-failed-no-l0`, with no L0, MHI, WLFW, BDF, FW-ready,
  `wlan0`, scan/connect, DHCP/routes, or external ping. Report:
  `docs/reports/NATIVE_INIT_V1543_ENDPOINT_ELECTRICAL_HANDOFF_2026-06-02.md`.
- V1544 host-only endpoint-electrical result classifier passes with
  `v1544-endpoint-electrical-confirms-no-l0-gpio-gdsc-zero-clk-postfail`. It
  adds
  `scripts/revalidation/native_wifi_endpoint_electrical_result_classifier_v1544.py`
  and fixes the current blocker: the AP-side writer reaches RC1/LTSSM, but
  SDX50M does not enter L0. GPIO104/WAKE and GPIO142/MDM2AP stay low with zero
  IRQ count, GPIO135 remains low in captured debug GPIO samples, `pcie_1_gdsc`
  is observed at 0mV, and no downstream Wi-Fi marker appears. Focused
  `clk_summary` lines are disabled but too slow for a definitive sub-120ms
  pre-fail clock proof. Next gate: V1545 should design a lower-overhead
  pre-fail endpoint-state observer that does not read full `clk_summary` in
  the critical RC1 window. Do not repeat enumerate-only experiments or move to
  firmware/MHI/WLFW/connect-side work until native RC1 L0 and PCI enumeration
  exist. Report:
  `docs/reports/NATIVE_INIT_V1544_ENDPOINT_ELECTRICAL_RESULT_CLASSIFIER_2026-06-02.md`.
- V1545 host-only low-overhead observer design classifier passes with
  `v1545-low-overhead-observer-design-ready`. It adds
  `scripts/revalidation/native_wifi_low_overhead_observer_design_v1545.py` and
  fixes the next observer contract: keep sysfs/client enumerate and
  case-aligned micro sampling, but remove `micro_focused_endpoint_sampler` from
  the critical loop because full `clk_summary` is too slow for the sub-120ms
  no-L0 window. The existing critical-fast sampler records interrupts, debug
  GPIO, link-state files, regulator summary, and pinmux while emitting
  `micro_critical_clk_summary_skipped=1`. Report:
  `docs/reports/NATIVE_INIT_V1545_LOW_OVERHEAD_ENDPOINT_OBSERVER_DESIGN_2026-06-02.md`.
- V1546/V1547 low-overhead endpoint observer preparation passes. V1546 adds
  `scripts/revalidation/build_native_init_wifi_test_boot_v1546.py` and builds
  `tmp/wifi/v1546-low-overhead-endpoint-observer-test-boot/boot_linux_v1546_wifi_test.img`
  with init `A90 Linux init 0.9.100 (v1546-wifitest)` and the targeted
  sysfs/client enumerate writer. V1547 adds
  `scripts/revalidation/native_wifi_low_overhead_artifact_sanity_v1547.py` and
  passes with `v1547-low-overhead-artifact-sanity-pass`, verifying that
  `micro_focused_clk` and batched clock markers are absent from the boot image
  while `micro_critical_clk_summary_skipped=1` is present. Next gate: V1548
  rollbackable live handoff for only the V1546 image, then classify whether
  fast source reads finish before link failure and whether GPIO/GDSC/link-state
  observations differ from V1543. Reports:
  `docs/reports/NATIVE_INIT_V1546_LOW_OVERHEAD_ENDPOINT_OBSERVER_SOURCE_BUILD_2026-06-02.md`,
  `docs/reports/NATIVE_INIT_V1547_LOW_OVERHEAD_ARTIFACT_SANITY_2026-06-02.md`.
- V1548 rollbackable low-overhead handoff passes with
  `v1548-test-boot-downstream-progress-rollback-pass`. It adds
  `scripts/revalidation/native_wifi_low_overhead_handoff_v1548.py`, flashes
  only the V1546 image, collects the low-overhead endpoint window, and rolls
  back to v724 with selftest verification. The outcome remains fixed at
  `rc1-ltssm-link-failed-no-l0`: sysfs/client enumerate succeeds, RC1 reaches
  PHY-ready and LTSSM poll active/compliance, then fails before L0 with no
  MHI/WLFW/BDF/FW-ready/`wlan0`. Report:
  `docs/reports/NATIVE_INIT_V1548_LOW_OVERHEAD_HANDOFF_2026-06-02.md`.
- V1549 host-only low-overhead result classifier passes with
  `v1549-low-overhead-confirms-pre-fail-gpio-gdsc-no-l0`. It adds
  `scripts/revalidation/native_wifi_low_overhead_result_classifier_v1549.py`
  and closes the V1543 slow-clock ambiguity. The critical micro loop contains
  `micro_critical_clk_summary_skipped=1`, no `micro_focused_clk`, and captures
  pre-fail interrupt/GPIO/link-state/regulator/pinmux sources. Before the
  link-fail marker, GPIO104/WAKE and GPIO142/MDM2AP remain low with zero IRQ,
  GPIO135/AP2MDM remains low in debug GPIO, and `pcie_1_gdsc` remains reported
  as 0mV. Next gate: V1550 host/source classifier for pcie1 power-domain and
  debugfs regulator semantics; no more enumerate retries and no firmware/MHI/
  WLFW/connect work until that gap is classified. Report:
  `docs/reports/NATIVE_INIT_V1549_LOW_OVERHEAD_RESULT_CLASSIFIER_2026-06-02.md`.
- V1550 host-only pcie1 power-domain semantics classifier passes with
  `v1550-pcie1-gdsc-summary-is-not-power-proof-tracefs-needed`. It adds
  `scripts/revalidation/native_wifi_pcie1_power_domain_semantics_classifier_v1550.py`
  and reconciles V1549 with `pci-msm.c`, `regulator/core.c`,
  `gdsc-regulator.c`, and SM8150 DTS. Source confirms the normal
  sysfs-client enumerate route calls `msm_pcie_enable(PM_ALL)` and requests
  `regulator_enable(dev->gdsc)` for `gdsc-vdd = <&pcie_1_gdsc>` before
  PHY/LTSSM. The `regulator_summary` `0mV` field is not physical-voltage proof:
  the GDSC regulator has enable/disable/is_enabled ops but no voltage getter or
  list operation, while the debugfs table still prints
  `_regulator_get_voltage()/1000`. The remaining question is event timing for
  GDSC use-count and cleanup. Next gate: V1551 bounded targeted tracefs
  regulator/clk/gpio observer around the existing sysfs-client-enumerate
  window, using V1315-proven events, with no direct PMIC/GPIO/GDSC writes,
  global PCI rescan, platform bind/unbind, Wi-Fi HAL, scan/connect,
  credentials, DHCP/routes, or external ping. Report:
  `docs/reports/NATIVE_INIT_V1550_PCIE1_POWER_DOMAIN_SEMANTICS_CLASSIFIER_2026-06-02.md`.
- V1551 bounded live pcie1 tracefs enumerate observer passes with
  `v1551-pcie1-gdsc-enable-captured-no-l0`. It adds
  `scripts/revalidation/native_wifi_pcie1_tracefs_enumerate_live_v1551.py`,
  enables only selected regulator/clk/gpio static tracefs events, writes once
  to the already-proven pcie1 sysfs-client enumerate endpoint, disables the
  events, captures filtered trace lines and dmesg, and verifies post selftest.
  It captures `pcie_1_gdsc` enable/enable-complete and disable/disable-complete
  events, pcie1 clock/refgen/pipe clock activity, and GPIO102 toggles. The
  result still has no RC1 L0, MHI, WLFW/BDF/FW-ready, or `wlan0`, and the
  target trace window does not show GPIO104/WAKE, GPIO135/AP2MDM, or
  GPIO142/MDM2AP activity. Next gate: classify PERST/refclk/endpoint response
  after confirmed RC1 power-domain enable; keep firmware/MHI/WLFW/connect work
  parked until native RC1 L0 and PCI enumeration exist. Report:
  `docs/reports/NATIVE_INIT_V1551_PCIE1_TRACEFS_ENUMERATE_LIVE_2026-06-02.md`.
- V1552 bounded live RC1 endpoint-response tracefs observer passes with
  `v1552-ap-side-power-refclk-perst-confirmed-endpoint-silent-no-l0`. It adds
  `scripts/revalidation/native_wifi_rc1_endpoint_response_tracefs_v1552.py`
  and extends V1551 with `irq_handler_entry/exit` tracefs events plus
  before/after interrupt snapshots for `msm_pcie_wake`, `mdm status`, and
  `mdm errfatal`. The same bounded sysfs-client enumerate window now proves
  AP-side RC1 prerequisites are active: `pcie_1_gdsc` enable/disable,
  PM8150L voltage requests, pcie1 refclk/pipe-clock enable/disable, and
  GPIO102/PERST assert-release-assert timing. The endpoint remains silent:
  GPIO104/WAKE, GPIO142/MDM2AP, and MDM errfatal trace/delta all stay zero,
  and RC1 still fails before L0 with no MHI/WLFW/BDF/FW-ready/`wlan0`. Next
  gate: classify why SDX50M does not respond after PERST release despite
  confirmed AP-side power/refclk/PERST; keep firmware/MHI/WLFW/connect work
  parked until native RC1 L0 and PCI enumeration exist. Report:
  `docs/reports/NATIVE_INIT_V1552_RC1_ENDPOINT_RESPONSE_TRACEFS_LIVE_2026-06-02.md`.
- V1553 host-only endpoint-silence next-gate classifier passes with
  `v1553-next-gate-android-good-power-trace-reference`. It adds
  `scripts/revalidation/native_wifi_endpoint_silence_next_gate_v1553.py` and
  reconciles V1552 against the prior PM/eSoC, sysfs-enumerate, Android-good,
  and MHI-position classifiers without running any device command. The fixed
  point is: native AP-side RC1 power/refclk/PERST is proven, endpoint IRQs
  stay silent, V1496 already showed provider+RC1 still no L0, and MHI
  PM-resume remains downstream of first PCI enumeration. Another blind native
  enumerate retry is not next. Next gate: V1554 Android-good bounded tracefs
  reference for regulator/clk/gpio/irq events around the successful first-L0
  lower-Wi-Fi window, then compare against V1552 before any new native
  mutation. Report:
  `docs/reports/NATIVE_INIT_V1553_ENDPOINT_SILENCE_NEXT_GATE_CLASSIFIER_2026-06-02.md`.
- V1554 rollbackable Android-good tracefs reference attempt completes native
  rollback and preserves v724 selftest, but it is classified as
  `v1554-target-trace-captured-lower-missing-review` rather than a successful
  Android-good reference. It adds
  `scripts/revalidation/android_good_power_trace_reference_handoff_v1554.py`.
  The persisted run captures target tracefs evidence, including
  AP2MDM/GPIO135 set-high and repeated `refgen` regulator activity, but Android
  does not reach BDF, FW-ready, or `wlan0` before rollback. Next gate: V1555
  should lower observer impact to console/dmesg plus minimal GPIO/IRQ trace and
  a longer hold; only after Android reaches BDF/FW-ready/`wlan0` under that
  observer should regulator/clk tracefs be reintroduced or compared against
  V1552. Report:
  `docs/reports/NATIVE_INIT_V1554_ANDROID_GOOD_POWER_TRACE_REFERENCE_2026-06-02.md`.
- V1555 rollbackable Android-good minimal trace reference passes with
  `v1555-android-good-minimal-trace-reference-pass`. It adds
  `scripts/revalidation/android_good_minimal_trace_reference_handoff_v1555.py`
  and updates the shared V1521 handoff engine so transient `adb shell` closure
  during Android boot-complete wait is retried instead of aborting before
  module installation. The successful run uses only GPIO/IRQ tracefs plus
  filtered dmesg, preserves Android lower Wi-Fi progress, and rolls back to
  native v724 with selftest passing. It captures WLFW start, BDF downloads,
  FW-ready, and `wlan0`, plus endpoint-response signals absent in V1552:
  GPIO135/AP2MDM set-high, GPIO102/PERST activity, IRQ252 `msm_pcie_wake`,
  IRQ290 `mdm status`, and GPIO142 high after mdm status. Timing caveat:
  retained RC1 L0/MHI excerpts are late relative to first lower-Wi-Fi markers,
  so the next gate is V1556 host-only stable-signal comparator against V1552,
  not a direct first-L0 timestamp claim. Report:
  `docs/reports/NATIVE_INIT_V1555_ANDROID_GOOD_MINIMAL_TRACE_REFERENCE_2026-06-02.md`.
- V1556 host-only endpoint signal comparator passes with
  `v1556-stable-gap-android-endpoint-signals-native-zero`. It adds
  `scripts/revalidation/native_wifi_v1555_vs_v1552_endpoint_signal_comparator_v1556.py`
  and compares V1552 native endpoint-silent evidence with the V1555
  Android-good minimal trace reference. The fixed delta: native V1552 has
  AP-side pcie1 power/refclk/pipe-clock/PERST activity but zero endpoint
  response (`GPIO104/pcie wake`, `GPIO142/MDM2AP`, IRQ252, IRQ290 all absent);
  Android-good V1555 has the missing positive endpoint signals and reaches
  BDF/FW-ready/`wlan0`. Timing caveat remains because retained V1555 RC1 L0/MHI
  excerpts are late relative to first lower-Wi-Fi markers. Next gate: V1557
  should either run a native provider+minimal endpoint hold aligned to V1555's
  positive signals, or first capture a dmesg-only Android timing clarifier if
  first-L0 ordering is required. Report:
  `docs/reports/NATIVE_INIT_V1556_V1555_VS_V1552_ENDPOINT_SIGNAL_COMPARATOR_2026-06-02.md`.
- V1557 rollbackable native endpoint long-hold handoff passes with
  `v1557-native-long-hold-endpoint-still-silent-no-l0-rollback-pass`. It adds
  `scripts/revalidation/native_wifi_endpoint_long_hold_handoff_v1557.py`,
  reuses the V1493 Wi-Fi test boot image, holds the native provider/RC1 path
  for 280 seconds, collects below-connect evidence, and rolls back to native
  v724 with selftest healthy. The delayed-endpoint-response hypothesis is now
  rejected for this route: provider/modem triggers are present and RC1 progress
  reaches link-failed/no-L0, but MHI/WLFW/BDF/FW-ready/`wlan0` remain absent,
  IRQ252/IRQ290/errfatal totals stay zero, and GPIO104/GPIO142/GPIO135 never
  show high. Next gate: stop same-path long-hold retries and compare the
  Android-good pre-endpoint/pre-IRQ sequence against the native
  provider-driven path to explain why Android produces wake/status endpoint
  signals while native remains endpoint-silent. Report:
  `docs/reports/NATIVE_INIT_V1557_NATIVE_ENDPOINT_LONG_HOLD_HANDOFF_2026-06-02.md`.
- V1558 host-only post-V1557 next-gate classifier passes with
  `v1558-next-gate-android-pre-endpoint-sequence-classifier`. It adds
  `scripts/revalidation/native_wifi_post_v1557_next_gate_classifier_v1558.py`
  and combines V1523, V1552, V1555, V1556, and V1557 evidence. This fixes the
  next branch: do not repeat same-path V1493/V1496 long-hold or blind pci-msm
  TEST:11 timing retries, and keep firmware/MHI/WLFW downstream until RC1 L0
  or PCI enumeration exists. Next gate: V1559 should compare Android-good
  pre-endpoint/pre-IRQ ordering against native provider-driven endpoint silence,
  specifically provider/esoc0 timing, GPIO135/AP2MDM, GPIO102/PERST, pcie1
  refclk/pipe/GDSC, GPIO104/WAKE + IRQ252, GPIO142/MDM2AP + IRQ290, and only
  then first L0/PCI/MHI ordering if the evidence can prove it. Report:
  `docs/reports/NATIVE_INIT_V1558_POST_V1557_NEXT_GATE_CLASSIFIER_2026-06-02.md`.
- V1559 host-only Android pre-endpoint order classifier passes with
  `v1559-ap2mdm-before-bdf-gap-endpoint-order-caveat`. It adds
  `scripts/revalidation/native_wifi_android_pre_endpoint_order_classifier_v1559.py`
  and parses existing V1552, V1555, and V1557 evidence. The earliest currently
  ordered Android-good discriminator is GPIO135/AP2MDM: it appears after
  `esoc0` get and before BDF download. Native still has AP-side pcie1
  GDSC/refclk/pipe/PERST activity but no GPIO135/AP2MDM, GPIO104/WAKE,
  GPIO142/MDM2AP, IRQ252, IRQ290, L0, MHI, WLFW, BDF, FW-ready, or `wlan0`.
  V1559 also fixes the ordering caveat: retained V1555 IRQ252/IRQ290/L0
  excerpts are late relative to first retained `wlan0`, so they are positive
  endpoint proof but not first-L0 ordering proof. Next gate: V1560 should focus
  on the AP2MDM assertion/effective-level gap before BDF and explain why native
  provider/RC1 does not assert GPIO135/AP2MDM despite AP-side pcie1 readiness.
  Report:
  `docs/reports/NATIVE_INIT_V1559_ANDROID_PRE_ENDPOINT_ORDER_CLASSIFIER_2026-06-02.md`.
- V1560 host-only Android-order vs native-route classifier passes with
  `v1560-android-wlfw-before-ap2mdm-native-route-lacks-wlfw`. It adds
  `scripts/revalidation/native_wifi_android_order_vs_native_route_classifier_v1560.py`
  and compares Android-good lower ordering against native V1496/V1557. This
  refines the V1559 AP2MDM finding: Android first reaches
  `cnss-daemon wlfw_start` and `wlfw_service_request`, then `esoc0`, BDF,
  FW-ready, and `wlan0`. Native sees `cnss-daemon` generic netlink and reaches
  `esoc0`, then forced RC1 enumerate fails before L0, but native never emits
  `wlfw_start`, BDF, FW-ready, or `wlan0`. Next gate: V1561 should compare the
  Android vs native `cnss-daemon` WLFW start/request contract (invocation,
  properties, sockets, service-manager context) before any live connect-side
  action. Keep forced RC1 enumerate diagnostic-only until native reproduces the
  WLFW start/request contract. Report:
  `docs/reports/NATIVE_INIT_V1560_ANDROID_ORDER_VS_NATIVE_ROUTE_CLASSIFIER_2026-06-02.md`.
- V1561 host-only WLFW contract rebase classifier passes with
  `v1561-current-wlfw-contract-rebases-v966-service-window-next`. It adds
  `scripts/revalidation/native_wifi_wlfw_contract_rebase_classifier_v1561.py`
  and reconciles V966 with current V1560/V1496/V1557 evidence. Android-good
  reaches `cnss-daemon wlfw_start`/`wlfw_service_request` before
  `/dev/subsys_esoc0`, BDF, FW-ready, and `wlan0`; current native v1393 test
  boot is still hardwired to `wifi-companion-post-pm-mdm-helper-esoc-observer`
  and never emits `wlfw_start`. The helper already has bounded
  `wifi-companion-android-wifi-service-window-start-only` and
  `wifi-companion-android-wifi-service-window-subsys-trigger-capture` modes.
  Next gate: V1562 should be source/build-only route selection to use that
  service-window mode with `--allow-android-wifi-service-window` and without
  scan/connect, credentials, DHCP/routes, external ping, PMIC/GPIO/GDSC writes,
  blind eSoC notify, global PCI rescan, or platform bind/unbind. Report:
  `docs/reports/NATIVE_INIT_V1561_WLFW_CONTRACT_REBASE_CLASSIFIER_2026-06-02.md`.
- V1562 source/build-only route selector passes with
  `v1562-android-wifi-service-window-test-boot-source-build-pass`. It updates
  `stage3/linux_init/v724/90_main.inc.c` and
  `scripts/revalidation/build_native_init_wifi_test_boot_v1393.py` so the v1393
  Wi-Fi test boot can select `android-service-window-start-only` at build time.
  The generated artifact launches
  `wifi-companion-android-wifi-service-window-start-only` with
  `--allow-android-wifi-service-window` and excludes the post-PM observer route
  flags from the PID1 argv. Artifact:
  `tmp/wifi/v1562-android-wifi-service-window-test-boot/boot_linux_v1393_wifi_test.img`,
  boot sha256
  `3b927f60b81caaf60f01ea5fcf23cccc56d68cbc58edaf5db6e7993f5cad262d`.
  Backcompat source-build smoke for the default post-PM observer branch also
  passes. Next gate: V1563 rollbackable live handoff should only check for
  `cnss-daemon wlfw_start`/`wlfw_service_request` under service-window mode; no
  credentials, scan/connect, DHCP/routes, external ping, PMIC/GPIO/GDSC writes,
  blind eSoC notify, global PCI rescan, or platform bind/unbind. Report:
  `docs/reports/NATIVE_INIT_V1562_ANDROID_WIFI_SERVICE_WINDOW_TEST_BOOT_SOURCE_BUILD_2026-06-02.md`.
- V1563 local-only artifact sanity passes with
  `v1563-android-wifi-service-window-artifact-sanity-pass`. It adds
  `scripts/revalidation/native_wifi_test_boot_artifact_sanity_v1563.py` and
  verifies the V1562 service-window artifact, header/kernel parity, static ELF
  properties, ramdisk entries, private output modes, credential-byte absence,
  service-window boot markers, and PID1 route contract. Sanity manifest:
  `tmp/wifi/v1563-android-wifi-service-window-artifact-sanity/manifest.json`;
  verified boot sha256
  `3b927f60b81caaf60f01ea5fcf23cccc56d68cbc58edaf5db6e7993f5cad262d`.
  Next gate: V1564 rollbackable live handoff for only the V1562 artifact,
  expecting `A90 Linux init 0.9.69 (v1562-service-window)`, collecting
  service-window log/summary/dmesg/`wlan0` state, rolling back to v724, and
  classifying only `wlfw_start`/`wlfw_service_request` progress. No credentials,
  scan/connect, DHCP/routes, or external ping. Report:
  `docs/reports/NATIVE_INIT_V1563_ANDROID_WIFI_SERVICE_WINDOW_ARTIFACT_SANITY_2026-06-02.md`.
- V1564 rollbackable live handoff completes and rolls back cleanly, but strict
  Wi-Fi progress is blocked with
  `v1564-test-boot-no-downstream-wifi-progress-blocked`. It adds
  `scripts/revalidation/native_wifi_test_boot_handoff_v1564.py` and runs only
  the V1562 Android Wi-Fi service-window test boot artifact. The device enters
  `A90 Linux init 0.9.69 (v1562-service-window)`, the PID1 supervisor launches
  `wifi-companion-android-wifi-service-window-start-only`, the helper exits
  normally, and rollback to v724 selftest passes. Focused dmesg shows
  `cnss_diag`, `cnss-daemon`, and `wificond` netlink/binder activity, but no
  `wlfw_start`, `wlfw_service_request`, ICNSS-QMI, BDF/regdb, FW-ready, MHI,
  RC1, or `wlan0` marker appears; explicit `wlan0` check reports absent. This
  removes the "service-window route alone is enough" candidate. Next gate:
  classify why the service-window helper exits cleanly without the Android-good
  WLFW request contract by comparing helper output, service-manager context,
  properties, sockets, and environment against Android-good evidence. Do not
  move to credentials, scan/connect, DHCP/routes, external ping, PMIC/GPIO/GDSC
  writes, blind eSoC notify, global PCI rescan, or platform bind/unbind.
  Report:
  `docs/reports/NATIVE_INIT_V1564_ANDROID_WIFI_SERVICE_WINDOW_HANDOFF_2026-06-02.md`.
- V1565 host-only service-window gap classifier passes with
  `v1565-select-service-window-subsys-trigger-capture-build`. It adds
  `scripts/revalidation/native_wifi_service_window_gap_classifier_v1565.py` and
  reconciles V1564 with V998/V1001. V1564 proves the start-only service-window
  test boot and rollback path but no WLFW/downstream progress; V998 proves the
  repaired full actor window still had no WLFW when `/dev/subsys_esoc0` was not
  attempted; V1001 already selected a scoped service-window subsystem trigger
  as the next useful route. Current sources support
  `android-service-window-subsys-trigger-capture` at build time with
  `--allow-android-wifi-service-window-subsys-trigger-capture` and explicit
  connect/credential/DHCP/external-ping guardrails. Next gate: V1566 should be
  source/build-only, generating and sanity-checking a Wi-Fi test boot artifact
  using `android-service-window-subsys-trigger-capture`, not another start-only
  retry and not a credentialed connect attempt. Report:
  `docs/reports/NATIVE_INIT_V1565_SERVICE_WINDOW_GAP_CLASSIFIER_2026-06-02.md`.
- V1566 source/build plus local artifact sanity passes with
  `v1566-service-window-subsys-trigger-artifact-sanity-pass`. It adds
  `scripts/revalidation/native_wifi_test_boot_artifact_sanity_v1566.py` and
  builds
  `tmp/wifi/v1566-android-wifi-service-window-subsys-trigger-test-boot/boot_linux_v1393_wifi_test.img`
  using `android-service-window-subsys-trigger-capture`. The artifact reports
  boot sha256
  `4b2cd6b0fe07c5826c0c3865b5fd60fff37a3d3a9437f5998312b7103cc11a65`,
  helper runtime mode
  `wifi-companion-android-wifi-service-window-subsys-trigger-capture`, both
  Android service-window allow flags, supervised helper timeout `75s`, header
  and kernel parity with v724, static init/helper binaries, private output
  modes, and no credential/scan/connect/DHCP/route/external-ping action in the
  build manifest. Next gate: V1567 rollbackable live handoff of only this
  V1566 image, expecting
  `A90 Linux init 0.9.69 (v1566-service-window-subsys-trigger)`, collecting
  helper log/summary, focused dmesg, trigger-window fields, and `wlan0` state,
  then rolling back to v724. Still no credentials, scan/connect, DHCP/routes,
  external ping, blind eSoC notify/`BOOT_DONE`, global PCI rescan, or platform
  bind/unbind. Report:
  `docs/reports/NATIVE_INIT_V1566_SERVICE_WINDOW_SUBSYS_TRIGGER_ARTIFACT_SANITY_2026-06-02.md`.
- V1567 rollbackable live handoff of the V1566 service-window subsystem-trigger
  artifact completes and rolls back cleanly. The test boot reaches
  `A90 Linux init 0.9.69 (v1566-service-window-subsys-trigger)`, launches
  `wifi-companion-android-wifi-service-window-subsys-trigger-capture`, and the
  helper exits normally with `helper_exit_code=0` and `helper_timed_out=0`.
  Strict Wi-Fi progress still blocks with final decision
  `no-provider-no-downstream`: no RC1/MHI/WLFW/BDF/FW-ready/`wlan0` marker is
  captured. Focused dmesg shows generic `cnss_diag`, `cnss-daemon`, and
  `wificond` activity only. The new blocker is evidence quality: the persisted
  PID1 log contains supervisor lifecycle lines but not the helper's detailed
  `android_wifi_service_window.*`, `cnss_before_esoc.*`, or `subsys_trigger.*`
  contract fields, so the run cannot classify whether `/dev/subsys_esoc0` was
  attempted or predicate-skipped. Next gate: V1568 source/build-only should
  repair helper contract output persistence in a private result artifact or
  equivalent PID1-captured stdout/stderr log, then sanity-check before any live
  rerun. Still no credentials, scan/connect, DHCP/routes, external ping, blind
  eSoC notify/`BOOT_DONE`, global PCI rescan, or platform bind/unbind. Report:
  `docs/reports/NATIVE_INIT_V1567_SERVICE_WINDOW_SUBSYS_TRIGGER_HANDOFF_2026-06-02.md`.
- V1568 source/build repairs the service-window evidence path and passes local
  artifact sanity with
  `v1568-service-window-subsys-trigger-result-artifact-sanity-pass`. The helper
  is bumped to `a90_android_execns_probe v288` and adds
  `--result-output-path`, writing final helper `STDOUT`/`STDERR` buffers to a
  private result file. The V1393 PID1 test-boot path passes
  `/cache/native-init-wifi-test-boot-v1393-helper.result` and records its path
  and size in the summary. The generated artifact is
  `tmp/wifi/v1568-service-window-subsys-trigger-result-test-boot/boot_linux_v1393_wifi_test.img`
  with boot sha256
  `0bf402cf31ce53e4e6a8d365d4b105cb31ec8e58b484c9a681872c62c87279a4`.
  Next gate: V1569 rollbackable live handoff of only this V1568 image, collect
  normal log, summary, focused dmesg, `wlan0`, and the new helper result file,
  then roll back to v724. The live target is classifying whether
  `/dev/subsys_esoc0` was attempted, predicate-skipped, or attempted without
  RC1/MHI/WLFW/`wlan0` progress. Still no credentials, scan/connect,
  DHCP/routes, external ping, blind eSoC notify/`BOOT_DONE`, global PCI rescan,
  or platform bind/unbind. Report:
  `docs/reports/NATIVE_INIT_V1568_SERVICE_WINDOW_SUBSYS_TRIGGER_RESULT_ARTIFACT_SANITY_2026-06-02.md`.
- V1569 rollbackable live handoff of the V1568 result-output image completes
  and rolls back cleanly to v724. The helper result artifact is successfully
  preserved and collected from
  `/cache/native-init-wifi-test-boot-v1393-helper.result` (`563961` bytes),
  closing the V1567 evidence gap. The classified result is
  `subsys-trigger-not-attempted-no-mdm-helper-esoc-fd`: the helper enters
  `guarded-subsys-trigger-capture` and starts all 14 service-window actors, but
  `mdm_helper_esoc0_fd_count=0`, `subsys_trigger_gate_open=0`,
  `subsys_trigger_start_attempted=0`, `subsys_trigger_started=0`, and
  `subsys_esoc0_open_attempted=0`. Focused dmesg still shows only generic
  `cnss_diag`, `cnss-daemon`, and `wificond` activity, with no provider/RC1/
  MHI/WLFW/BDF/FW-ready/`wlan0` marker. Current blocker for this route is before
  RC1/LTSSM: native service-window userspace starts `mdm_helper`, but
  `mdm_helper` never acquires `/dev/esoc-0`, so the scoped `/dev/subsys_esoc0`
  trigger is correctly not attempted. Next gate: V1570 host-only or
  source/build-only should compare Android-good `mdm_helper` launch contract
  against native service-window launch and add a bounded mdm-helper fd
  acquisition classifier if needed. Do not move to credentials/connect,
  DHCP/routes, external ping, firmware/MHI deep dive, or RC1 retry until the
  mdm-helper `/dev/esoc-0` fd predicate is satisfied or deliberately replaced by
  a reviewed gate. Report:
  `docs/reports/NATIVE_INIT_V1569_SERVICE_WINDOW_RESULT_HANDOFF_2026-06-02.md`.
- V1570 host-only mdm-helper fd-gate classifier passes with
  `v1570-select-mdm-helper-launch-contract-delta`. It consumes V1569 plus
  Android V1158, reduced-native V1228, and the prior service-window negative
  V1008/V1009 references. The result confirms the active route is not currently
  an RC1/LTSSM failure: V1569 starts `mdm_helper` but never observes
  `/dev/esoc-0`, while Android and reduced native references prove the fd
  predicate is achievable. Next gate: V1571 source/build-only should add a
  service-window `mdm_helper` launch-contract comparator for argv/env/
  properties/dev-node/context against known positive mdm-helper modes. Do not
  retry RC1, firmware/MHI, credentials/connect, DHCP/routes, or external ping
  until the mdm-helper `/dev/esoc-0` fd predicate is satisfied or a new reviewed
  bounded gate replaces that predicate. Report:
  `docs/reports/NATIVE_INIT_V1570_MDM_HELPER_FD_GATE_CLASSIFIER_2026-06-02.md`.
- V1571 source/build-only service-window `mdm_helper` launch-contract
  comparator passes with
  `v1571-mdm-helper-launch-contract-artifact-sanity-pass`. The helper is bumped
  to `a90_android_execns_probe v289` and the V1393 test boot artifact is rebuilt
  as
  `tmp/wifi/v1571-mdm-helper-launch-contract-test-boot/boot_linux_v1393_wifi_test.img`
  with boot sha256
  `d5fc21430720868d3836f6bb6b7b811348cfadb3596bdc3274a7aef84f0b6392`. The new
  `android_wifi_service_window.mdm_helper_launch_contract` diagnostics record
  planned and post-spawn target/argv/env/identity/SELinux/dev-node/fd state and
  the known `pm_proxy`/`pm_proxy_helper` absence delta without changing actor
  order or performing any lower eSoC/PCIe action. Next gate: V1572 rollbackable
  live handoff of only this V1571 image, collect the helper result file, compare
  launch-contract output against V1158/V1228 positives, and roll back to v724.
  Still no credentials/connect, DHCP/routes, external ping, firmware/MHI deep
  dive, or RC1 retry until the mdm-helper `/dev/esoc-0` fd predicate is
  satisfied or deliberately replaced by a reviewed bounded gate. Report:
  `docs/reports/NATIVE_INIT_V1571_MDM_HELPER_LAUNCH_CONTRACT_ARTIFACT_SANITY_2026-06-02.md`.
- V1572 rollbackable live handoff of the V1571 image rolled back cleanly, but
  the result is a test-artifact defect: the helper exited by signal 11 and the
  collected helper result was stale (`result_file_version=a90_android_execns_probe v288`).
  Treat V1572 as crash/stale-result evidence, not a service-window conclusion.
  Report:
  `docs/reports/NATIVE_INIT_V1572_MDM_HELPER_LAUNCH_CONTRACT_HANDOFF_2026-06-02.md`.
- V1573 source/build-only crashfix unlinks the stale helper result file at test
  boot start, bumps the helper to `a90_android_execns_probe v290`, and splits
  the launch-contract formatter into bounded append calls. Artifact sanity
  passes with
  `v1573-mdm-helper-launch-contract-crashfix-artifact-sanity-pass`; test image:
  `tmp/wifi/v1573-mdm-helper-launch-contract-crashfix-test-boot/boot_linux_v1393_wifi_test.img`
  with boot sha256
  `ea028a2c0c96241a9e1a558cfa39af631924ee428672004f410218b8e15c893a`.
  Report:
  `docs/reports/NATIVE_INIT_V1573_MDM_HELPER_LAUNCH_CONTRACT_CRASHFIX_ARTIFACT_SANITY_2026-06-02.md`.
- V1574 rollbackable live handoff of the V1573 image rolls back to v724
  successfully and collects a fresh v290 result. The helper no longer crashes:
  `helper_status_raw=0`, `helper_exited=1`, `helper_exit_code=0`,
  `helper_signaled=0`. The active service-window delta is confirmed:
  `planned.compare.pm_proxy_absent_delta=1`,
  `after_mdm_helper_spawn.compare.pm_proxy_absent_delta=1`,
  `after_mdm_helper_spawn.fd.esoc0=0`,
  `after_mdm_helper_spawn.fd.subsys_esoc0=0`,
  `after_mdm_helper_spawn.fd.subsys_modem=0`,
  `mdm_helper_esoc0_fd_count=0`, `subsys_trigger_gate_open=0`,
  `subsys_trigger.started=0`, final result
  `subsys-trigger-not-attempted-no-mdm-helper-esoc-fd`. This blocks before the
  RC1/LTSSM track: service-window `mdm_helper` is launched without the
  Android-good `pm_proxy`/`pm_proxy_helper` contract and never obtains
  `/dev/esoc-0`. Next gate: source/build-only addition of the missing
  `pm_proxy`/`pm_proxy_helper` launch contract, or host-only proof of the exact
  `pm-service` Binder request needed to make `mdm_helper` hold `/dev/esoc-0`.
  Still no credentials/connect, DHCP/routes, external ping, firmware/MHI deep
  dive, or RC1 retry until this fd predicate is satisfied or replaced by a
  reviewed bounded gate. Report:
  `docs/reports/NATIVE_INIT_V1574_MDM_HELPER_LAUNCH_CONTRACT_CRASHFIX_HANDOFF_2026-06-02.md`.
- If V1359 only finds platform bind/probe or global PCI rescan, stop for a new
  design instead of binding or rescanning blindly.
- If both pcie1 RC and PON parity are read-only-proven healthy yet MDM2AP still
  never asserts, then re-open the lower eSoC/MHI/ks branch with the new
  evidence. Until then, keep V1337-V1352 upper tracks parked.

- V1575-V1586 service-window PM proxy contract and firmware overlay loop is now
  closed.  V1576 selected the PM proxy contract route but still lacked private
  `/dev/esoc-0`/`/dev/subsys_*` nodes.  V1578 fixed service-window private
  devnode materialization: `mdm_helper_esoc0_fd_count=1`,
  `subsys_trigger_gate_open=1`, and `subsys_trigger_started=1`, moving the
  active blocker to modem firmware visibility.  V1580/V1582 then proved the
  first firmware mount attempt was structurally wrong because `/vendor` resolves
  into read-only `/mnt/system/vendor`.  V1585 changes PID1's firmware path prep
  to use a firmware-only global `/vendor` overlay while leaving vendor daemon
  execution to the helper private `sda29` vendor namespace.  V1586 rollbackable
  live handoff passes with
  `v1586-test-boot-downstream-progress-rollback-pass`: firmware mounts prepare
  with `rc=0`, the helper result is fresh (`758102` bytes), modem PIL is
  brought out of reset, `subsys_esoc0` is attempted, and `icnss_qmi` evidence is
  present.  `wlan0`, BDF/regdb, FW-ready, MHI, and RC1/L0 markers are still
  absent; final progress decision is `firmware-progress-no-wlan0`.  Next gate:
  keep V1586 firmware mount parity and add focused RC1/MHI/WLFW request/state
  markers.  Do not proceed to credentials, scan/connect, DHCP/routes, external
  ping, blind eSoC notify/`BOOT_DONE`, PMIC/GPIO/GDSC direct writes, global PCI
  rescan, or platform bind/unbind.  Reports:
  `docs/reports/NATIVE_INIT_V1578_SERVICE_WINDOW_PM_PROXY_CONTRACT_DEVNODE_HANDOFF_2026-06-02.md`,
  `docs/reports/NATIVE_INIT_V1580_SERVICE_WINDOW_PM_PROXY_CONTRACT_DEVNODE_FW_HANDOFF_2026-06-02.md`,
  `docs/reports/NATIVE_INIT_V1584_SERVICE_WINDOW_PM_PROXY_CONTRACT_DEVNODE_FWOVERLAY_HANDOFF_2026-06-02.md`,
  and
  `docs/reports/NATIVE_INIT_V1586_SERVICE_WINDOW_PM_PROXY_CONTRACT_DEVNODE_FWOVERLAY_HANDOFF_2026-06-02.md`.

- V1587 host-only lower-marker next-gate classifier passes with
  `v1587-v1586-current-lower-marker-gate-required`.  This reconciles the older
  V1496 RC1 framing with the current V1586 route.  V1496 remains a valid
  forced-RC1 `no L0` result, but V1535 already completed the `msm_pcie`
  static/first-L0 candidate classification and V1560 already showed that
  Android-good reaches `cnss-daemon wlfw_start` while the native forced-RC1
  route does not.  Therefore the next useful unit is not another V1496 dossier
  and not credentialed scan/connect.  Next gate: V1588 source/build-only
  focused lower-marker sampler preserving V1586 firmware mount parity and the
  helper private vendor namespace, then compactly sampling process lifetimes,
  fd counts, subsystem states, RC1/LTSSM, runtime MHI bus/pipe, QRTR/WLFW,
  BDF, FW-ready, and `wlan0` in one bounded window.  Keep credentials,
  scan/connect, DHCP/routes, external ping, blind eSoC notify/`BOOT_DONE`,
  PMIC/GPIO/GDSC direct writes, global PCI rescan, and platform bind/unbind
  blocked.  Report:
  `docs/reports/NATIVE_INIT_V1587_LOWER_MARKER_NEXT_GATE_CLASSIFIER_2026-06-02.md`.

- V1588-V1589 lower-marker loop is complete.  V1588 updates
  `a90_android_execns_probe` to v293 and builds a V1586-parity service-window
  test boot with compact `android_wifi_service_window.lower_marker` sampling.
  Source build passes with
  `v1588-service-window-lower-marker-test-boot-source-build-pass`; artifact
  sanity passes with `v1588-service-window-lower-marker-artifact-sanity-pass`.
  V1589 rollbackable live handoff flashes only the V1588 image, collects
  lower-marker evidence, and rolls back from native to v724; post-rollback
  `version` is `0.9.68 (v724)` and `selftest fail=0`.  V1589 passes as
  `v1589-test-boot-downstream-progress-rollback-pass`, but final progress is
  still `firmware-progress-no-wlan0`.

  V1589 lower-marker outcome: `pm_proxy_helper` is alive and holds
  `/dev/subsys_modem`, `pm_proxy` is alive, `mdm_helper` is alive and holds
  `/dev/esoc-0`, CNSS actors are alive, and the scoped trigger child reaches
  `mdm_subsys_powerup`.  However `pm-service` is not alive
  (`per_mgr_alive_seen=0`), no process obtains a returned `/dev/subsys_esoc0`
  fd (`global_subsys_esoc0_fd_max=0`), and RC1/LTSSM, runtime MHI, `ks`,
  `wlfw_start`, BDF, FW-ready, and `wlan0` all remain absent.  Next gate:
  classify `pm-service` exit/lifetime and the missing Android-good
  PM-service-owned powerup contract.  Do not proceed to credentials,
  scan/connect, DHCP/routes, external ping, PMIC/GPIO/GDSC direct writes, blind
  eSoC notify/`BOOT_DONE`, global PCI rescan, or platform bind/unbind. Reports:
  `docs/reports/NATIVE_INIT_V1588_SERVICE_WINDOW_LOWER_MARKER_SOURCE_BUILD_2026-06-02.md`,
  `docs/reports/NATIVE_INIT_V1588_SERVICE_WINDOW_LOWER_MARKER_ARTIFACT_SANITY_2026-06-02.md`,
  and
  `docs/reports/NATIVE_INIT_V1589_SERVICE_WINDOW_LOWER_MARKER_HANDOFF_2026-06-02.md`.

- V1590 host-only PM-service lifetime route classifier is complete.  It passes
  as `v1590-route-current-service-window-loses-pm-service-owned-powerup` and
  compares current V1589 lower-marker evidence with older positive route
  references V1238/V1303.  The current V1589 service-window route starts the
  scoped `/dev/subsys_esoc0` trigger, but loses the Android-good PM-service
  owned path: `per_mgr` exits `0`, `pm_proxy` exits `1`,
  `global_subsys_esoc0_fd_max=0`, `pm_service_powerup_seen=0`, and no dmesg
  `pm-service` `__subsystem_get: esoc0` marker exists.  The process captured in
  `mdm_subsys_powerup` is the scoped helper trigger child, not PM-service.

  V1238/V1303 remain the positive PM-service route references:
  late `pm-proxy` made PM-service reach `/dev/subsys_esoc0`,
  `mdm_subsys_powerup`, and a powerup marker.  Next gate: V1591
  source/build-only should derive a firmware-mount-preserving
  late-`per_proxy`-only service-window test boot with lower-marker sampling, no
  direct scoped trigger, and explicit PM-service lifetime/exit markers.  Keep
  credentials, scan/connect, DHCP/routes, external ping, PMIC/GPIO/GDSC direct
  writes, blind eSoC notify/`BOOT_DONE`, global PCI rescan, and platform
  bind/unbind blocked.  Report:
  `docs/reports/NATIVE_INIT_V1590_PM_SERVICE_LIFETIME_ROUTE_CLASSIFIER_2026-06-02.md`.

- V1591 source/build and artifact sanity are complete.  Helper
  `a90_android_execns_probe` is bumped to v294 and adds
  `--allow-android-wifi-service-window-late-per-proxy-only`.  The new route
  preserves firmware mount parity, private devnodes, and lower-marker sampling,
  but starts `pm-proxy` after the mdm_helper/CNSS window and disables the direct
  scoped helper `/dev/subsys_esoc0` trigger child.  This targets the V1590
  finding that the current route lost PM-service-owned powerup while V1238/V1303
  proved late `pm-proxy` can make PM-service reach `/dev/subsys_esoc0`.

  V1591 build passes with
  `v1591-late-per-proxy-lower-marker-test-boot-source-build-pass`; boot image:
  `tmp/wifi/v1591-late-per-proxy-lower-marker-test-boot/boot_linux_v1591_wifi_test.img`,
  sha256
  `ef917e0f6dc65530b93ecd808598098c8b8cf94897cc5b518eca026829823466`.
  Artifact sanity passes as
  `v1591-late-per-proxy-lower-marker-artifact-sanity-pass`.  Next gate: V1592
  rollbackable live handoff of only this V1591 image, collect helper
  lower-marker result/dmesg/`wlan0`, then roll back to v724 and verify selftest
  `fail=0`.  Still no credentials, scan/connect, DHCP/routes, external ping,
  PMIC/GPIO/GDSC direct writes, blind eSoC notify/`BOOT_DONE`, global PCI
  rescan, or platform bind/unbind.  Reports:
  `docs/reports/NATIVE_INIT_V1591_LATE_PER_PROXY_LOWER_MARKER_SOURCE_BUILD_2026-06-02.md`
  and
  `docs/reports/NATIVE_INIT_V1591_LATE_PER_PROXY_LOWER_MARKER_ARTIFACT_SANITY_2026-06-02.md`.

- V1592 rollbackable live handoff and strict reclassification are complete.
  The V1591 image booted, evidence was collected, rollback from native restored
  v724, and post-rollback selftest remained `fail=0`.  The initial live
  handoff classified as downstream progress because the old classifier treated
  any `icnss_qmi` line as WLFW progress.  V1592 hardens that classifier:
  `icnss_qmi: Fail to send Shutdown req` is now shutdown/error evidence, while
  only `icnss_qmi: QMI Server Connected` counts as ICNSS QMI progress.

  With strict reclassification, V1592 is blocked as
  `v1592-test-boot-no-downstream-wifi-progress-blocked`.  Evidence shows
  `modem_trigger=True` but `provider_trigger=False`, no RC1/LTSSM, MHI, WLFW,
  BDF, FW-ready, or `wlan0`; helper mode is
  `guarded-pm-proxy-contract-late-per-proxy-lower-marker`; direct
  `/dev/subsys_esoc0` triggering is disabled; `mdm_helper` holds `/dev/esoc-0`;
  `pm_proxy` exits `1`; `per_mgr` exits `0`; and `pm_full_contract_seen=0`.
  Next gate: host-only/source-only classification of the `pm_proxy` exit path
  and `per_mgr` lifetime against V1238/V1303 positive late-`per_proxy`
  evidence before any new lower-layer live mutation.  Still no credentials,
  scan/connect, DHCP/routes, external ping, PMIC/GPIO/GDSC direct writes, blind
  eSoC notify/`BOOT_DONE`, global PCI rescan, platform bind/unbind, or
  unbounded boot-image/partition writes.  Report:
  `docs/reports/NATIVE_INIT_V1592_LATE_PER_PROXY_LOWER_MARKER_HANDOFF_2026-06-02.md`.

- V1593 PM proxy / `per_mgr` lifetime classifier is complete.  It passes as
  `v1593-late-per-proxy-regressed-before-pm-service-owned-powerup` and fixes
  the next blocker selection after V1592.  V1592 is not a lower
  SDX50M/eSoC/RC1 failure: it never reaches that boundary.  `pm-proxy` is
  spawned with successful preexec/SELinux setup and then exits `1`;
  `pm-service` (`per_mgr`) starts but is already gone when fd matching tries to
  inspect `/dev/subsys_modem`, exits `0`, and `pm_full_contract_seen=0`.

  The regression is route/order related.  V1592 uses the full service-window
  order with Wi-Fi HAL/wificond before the late actor:
  `... wifi_hal_legacy,wifi_hal_ext,per_mgr,cnss_diag,wificond,mdm_helper,cnss_daemon,pm_proxy_late ...`.
  V1238/V1303 remain the positive route references: stripped PM-first order
  with `pm_proxy_helper,per_mgr,vndservice_query,per_proxy_deferred,
  cnss_daemon,mdm_helper,late_per_proxy` reaches PM-service-owned
  `/dev/subsys_esoc0` and `mdm_subsys_powerup`.

  Next gate: V1594 source/build-only should preserve V1591 firmware mount
  parity but switch the test-boot route to the V1238/V1303 PM-first boundary:
  no Wi-Fi HAL/wificond before PM-service-owned powerup observation, direct
  scoped `/dev/subsys_esoc0` trigger still disabled, and explicit
  `pm-proxy`/`per_mgr` stderr/exit/lifetime diagnostics added.  Still no
  credentials, scan/connect, DHCP/routes, external ping, PMIC/GPIO/GDSC direct
  writes, blind eSoC notify/`BOOT_DONE`, global PCI rescan, platform
  bind/unbind, or unbounded boot-image/partition writes.  Report:
  `docs/reports/NATIVE_INIT_V1593_PM_PROXY_PER_MGR_LIFETIME_CLASSIFIER_2026-06-02.md`.

- V1594/V1595 PM-first lower-marker source/build loop is complete.  Helper
  `a90_android_execns_probe` is bumped to v295 and adds
  `--allow-android-wifi-service-window-pm-first-route`.  V1594 keeps V1591
  firmware mount parity but switches the test-boot service-window to the
  V1238/V1303-inspired PM-first route:
  `servicemanager,hwservicemanager,vndservicemanager,pm_proxy_helper,per_mgr,
  pm_proxy,mdm_helper,cnss_daemon,pm-first-lower-marker-no-direct-trigger-no-wifi-hal`.
  Wi-Fi HAL and `wificond` are not started before PM-service-owned
  `/dev/subsys_esoc0` observation.  The direct scoped `/dev/subsys_esoc0`
  trigger remains disabled.  The helper now classifies the PM boundary as
  `pm-service-owned-powerup-observed` or `pm-service-owned-powerup-missing`.

  V1594 source build passes as
  `v1594-pm-first-lower-marker-test-boot-source-build-pass`; boot image:
  `tmp/wifi/v1594-pm-first-lower-marker-test-boot/boot_linux_v1594_wifi_test.img`,
  sha256 `86ec9d6fbce5ac56e70815cac7aa1dc1a45aee1d5dd8a0fb53f81dc7c4d44417`.
  V1595 artifact sanity passes as
  `v1595-pm-first-lower-marker-artifact-sanity-pass`; it verifies static
  binaries, boot/header/kernel parity, ramdisk entries, PM-first route strings,
  firmware mounts, helper v295, private modes, and forbidden credential-like
  byte absence.  Next gate: V1596 rollbackable live handoff of only the V1594
  image, collect helper result/lower markers/dmesg/`wlan0`, then roll back to
  v724 and verify selftest `fail=0`.  Still no credentials, scan/connect,
  DHCP/routes, external ping, PMIC/GPIO/GDSC direct writes, blind eSoC
  notify/`BOOT_DONE`, global PCI rescan, platform bind/unbind, or unbounded
  boot-image/partition writes.  Reports:
  `docs/reports/NATIVE_INIT_V1594_PM_FIRST_LOWER_MARKER_SOURCE_BUILD_2026-06-02.md`
  and
  `docs/reports/NATIVE_INIT_V1595_PM_FIRST_LOWER_MARKER_ARTIFACT_SANITY_2026-06-02.md`.

- V1596 rollbackable live handoff is complete.  The V1594 PM-first
  lower-marker image booted, evidence was collected, rollback from native
  restored v724, and post-rollback selftest remained `fail=0`.  The handoff
  itself is safe/clean, but strict Wi-Fi progress is blocked as
  `v1596-test-boot-no-downstream-wifi-progress-blocked`.

  V1596 proves the stripped PM-first route still does not reach the
  Android-good PM-service-owned `/dev/subsys_esoc0` boundary.  Evidence shows
  `modem_trigger=True`, `provider_trigger=False`, no RC1/LTSSM, MHI, WLFW,
  BDF, FW-ready, or `wlan0`; helper mode
  `guarded-pm-proxy-contract-pm-first-lower-marker`; `pm_first_route=1`;
  direct scoped `/dev/subsys_esoc0` triggering disabled; `pm_proxy_helper`
  alive with `/dev/subsys_modem`; `mdm_helper` alive with `/dev/esoc-0`;
  `per_mgr` exits `0` before lower-marker observation; `pm_proxy` exits `1`;
  and `pm_full_contract_seen=0`.  Helper result:
  `pm-service-owned-powerup-missing`, reason
  `pm-first-route-did-not-reach-dev-subsys-esoc0-mdm-subsys-powerup`.

  Current blocker remains above SDX50M/eSoC/RC1 hardware.  V1596 did not reach
  provider powerup, so RC1/PERST/refclk, MHI, WLFW, BDF, and `wlan0` remain
  downstream and should not be expanded yet.  Next gate: V1597
  source/build-only should reproduce the V1238/V1303 positive route more
  exactly: stripped no-HAL/no-wificond service window, `pm_proxy_helper` and
  `per_mgr` preserved, CNSS/`mdm_helper` setup before a late/deferred
  `pm-proxy`, direct helper `/dev/subsys_esoc0` trigger still disabled, and
  focused `pm-proxy`/`pm-service` exit/lifetime diagnostics.  Still no
  credentials, scan/connect, DHCP/routes, external ping, PMIC/GPIO/GDSC direct
  writes, blind eSoC notify/`BOOT_DONE`, global PCI rescan, platform
  bind/unbind, or unbounded boot-image/partition writes.  Report:
  `docs/reports/NATIVE_INIT_V1596_PM_FIRST_LOWER_MARKER_HANDOFF_2026-06-02.md`.

- V1597/V1598 PM-first late-per-proxy lower-marker source/build loop is
  complete.  Helper `a90_android_execns_probe` is bumped to v296 and adds
  `--allow-android-wifi-service-window-pm-first-late-per-proxy-route`.  V1597
  keeps V1591 firmware mount parity, private devnodes, and the helper private
  vendor namespace, but changes the stripped route to match the V1238/V1303
  positive boundary more closely:
  `servicemanager,hwservicemanager,vndservicemanager,pm_proxy_helper,per_mgr,
  cnss_daemon,mdm_helper,pm_proxy_late,pm-first-late-per-proxy-lower-marker-no-direct-trigger-no-wifi-hal`.
  Wi-Fi HAL and `wificond` are not started.  The direct scoped
  `/dev/subsys_esoc0` trigger remains disabled.  The helper classifies the PM
  boundary as `pm-service-owned-powerup-observed` or
  `pm-service-owned-powerup-missing`.

  V1597 source build passes as
  `v1597-pm-first-late-per-proxy-lower-marker-test-boot-source-build-pass`;
  boot image:
  `tmp/wifi/v1597-pm-first-late-per-proxy-lower-marker-test-boot/boot_linux_v1597_wifi_test.img`,
  sha256 `68f25e21cb09a7420a9e7876b05e1455d25eaeec3d6ac8c37a3d7e649cf425f3`.
  V1598 artifact sanity passes as
  `v1598-pm-first-late-per-proxy-lower-marker-artifact-sanity-pass`; it
  verifies static binaries, boot/header/kernel parity, ramdisk entries,
  PM-first late-per-proxy route strings, firmware mounts, helper v296, private
  modes, and forbidden credential-like byte absence.  Next gate: V1599
  rollbackable live handoff of only the V1597 image, collect helper
  result/lower markers/dmesg/`wlan0`, then roll back to v724 and verify
  selftest `fail=0`.  Still no credentials, scan/connect, DHCP/routes,
  external ping, PMIC/GPIO/GDSC direct writes, blind eSoC notify/`BOOT_DONE`,
  global PCI rescan, platform bind/unbind, or unbounded boot-image/partition
  writes.  Reports:
  `docs/reports/NATIVE_INIT_V1597_PM_FIRST_LATE_PER_PROXY_LOWER_MARKER_SOURCE_BUILD_2026-06-02.md`
  and
  `docs/reports/NATIVE_INIT_V1598_PM_FIRST_LATE_PER_PROXY_LOWER_MARKER_ARTIFACT_SANITY_2026-06-02.md`.

- V1599 rollbackable live handoff is complete.  The V1597 image booted,
  evidence was collected, rollback from native restored v724, and post-rollback
  selftest remained `fail=0`.  Strict Wi-Fi progress is blocked as
  `v1599-test-boot-no-downstream-wifi-progress-blocked`: `modem_trigger=True`,
  `provider_trigger=False`, and no RC1/LTSSM, MHI, WLFW, BDF, FW-ready, or
  `wlan0` marker appears.  The stripped late route also fails to reach
  PM-service-owned `/dev/subsys_esoc0`; `per_mgr` exits `0`, `pm-proxy` exits
  `1`, `pm_full_contract_seen=0`, and helper result is
  `pm-service-owned-powerup-missing` with reason
  `pm-first-late-per-proxy-route-did-not-reach-dev-subsys-esoc0-mdm-subsys-powerup`.

  New blocker selection: `pm_proxy_helper_subsys_modem_initial_count=0` at the
  fixed post-PPH settle point, but lower-marker sampling later sees
  `pm_proxy_helper_subsys_modem_fd_max=1`.  That means `per_mgr` is likely being
  spawned before `pm_proxy_helper` actually holds `/dev/subsys_modem`.  Next
  gate: V1600 source/build-only should add a bounded PPH fd gate before
  spawning `per_mgr`, recording first-seen timing and classifying timeout as
  `pm-proxy-helper-modem-fd-missing`.  Still no credentials, scan/connect,
  DHCP/routes, external ping, PMIC/GPIO/GDSC direct writes, blind eSoC
  notify/`BOOT_DONE`, global PCI rescan, platform bind/unbind, or unbounded
  boot-image/partition writes.  Report:
  `docs/reports/NATIVE_INIT_V1599_PM_FIRST_LATE_PER_PROXY_LOWER_MARKER_HANDOFF_2026-06-02.md`.

- V1600/V1601 PPH modem-fd gate source/build loop is complete.  Helper
  `a90_android_execns_probe` is bumped to v297 and adds
  `--allow-android-wifi-service-window-pph-modem-fd-gate`.  V1600 keeps V1591
  firmware mount parity and the stripped late `pm-proxy` route, but inserts a
  bounded gate after `pm_proxy_helper`: poll until `pm_proxy_helper` holds
  `/dev/subsys_modem`, then start `per_mgr`; if the fd never appears, classify
  as `pm-proxy-helper-modem-fd-missing` before starting `per_mgr`.

  V1600 source build passes as
  `v1600-pm-first-late-per-proxy-pph-gate-lower-marker-test-boot-source-build-pass`;
  boot image:
  `tmp/wifi/v1600-pm-first-late-per-proxy-pph-gate-lower-marker-test-boot/boot_linux_v1600_wifi_test.img`,
  sha256 `be60778022ce772194ad156eeecf4c3cffe81c4e25514559a4c3d2fb6a627504`.
  V1601 artifact sanity passes as
  `v1601-pm-first-late-per-proxy-pph-gate-lower-marker-artifact-sanity-pass`;
  it verifies static binaries, boot/header/kernel parity, ramdisk entries,
  PPH-gated route strings, firmware mounts, helper v297, private modes, and
  forbidden credential-like byte absence.  Next gate: V1602 rollbackable live
  handoff of only the V1600 image, collect helper result/lower markers/dmesg/
  `wlan0`, then roll back to v724 and verify selftest `fail=0`.  Still no
  credentials, scan/connect, DHCP/routes, external ping, PMIC/GPIO/GDSC direct
  writes, blind eSoC notify/`BOOT_DONE`, global PCI rescan, platform
  bind/unbind, or unbounded boot-image/partition writes.  Reports:
  `docs/reports/NATIVE_INIT_V1600_PM_FIRST_LATE_PER_PROXY_PPH_GATE_LOWER_MARKER_SOURCE_BUILD_2026-06-02.md`
  and
  `docs/reports/NATIVE_INIT_V1601_PM_FIRST_LATE_PER_PROXY_PPH_GATE_LOWER_MARKER_ARTIFACT_SANITY_2026-06-02.md`.

- V1602 rollbackable live handoff is complete.  The V1600 image booted,
  evidence was collected, rollback from native restored v724, and post-rollback
  selftest remained `fail=0`.  Strict Wi-Fi progress is blocked as
  `v1602-test-boot-no-downstream-wifi-progress-blocked`, but the new PPH fd gate
  passes: `pph_modem_fd_gate_seen=1`, `pph_modem_fd_gate_first_seen_ms=301`,
  `pph_modem_fd_gate_samples=7`, and final count `1`.

  This closes the PPH race hypothesis.  After a proven PPH `/dev/subsys_modem`
  fd, `per_mgr` still exits `0` before observation, `per_mgr_subsys_modem_*=-1`,
  `pm-proxy` exits `1`, `pm_full_contract_seen=0`, and PM-service-owned
  `/dev/subsys_esoc0` never appears.  Current blocker is now `per_mgr`/
  `pm-service` startup itself, above SDX50M/eSoC/RC1.  Next gate: V1603 should
  be host/source-only first and classify why `/vendor/bin/pm-service` exits
  cleanly in the native service-window: focused startup diagnostics for
  argv/env, cwd, sockets/properties/service-manager dependencies, stdout/stderr,
  exit timing, and early fd/open attempts.  Still no credentials, scan/connect,
  DHCP/routes, external ping, PMIC/GPIO/GDSC direct writes, blind eSoC
  notify/`BOOT_DONE`, global PCI rescan, platform bind/unbind, or unbounded
  boot-image/partition writes.  Report:
  `docs/reports/NATIVE_INIT_V1602_PM_FIRST_LATE_PER_PROXY_PPH_GATE_LOWER_MARKER_HANDOFF_2026-06-02.md`.

- V1603 host-only PM-service exit classifier is complete and passes as
  `v1603-pph-gate-passed-per-mgr-exit-before-contract`.  It reads the V1602
  handoff manifest, summary, helper result, dmesg, and helper source without
  contacting the device.

  Final boundary: PPH modem-fd gate is proven (`pph_modem_fd_gate_seen=1`,
  first seen at `301ms`, final count `1`, and
  `pm_proxy_helper_subsys_modem_fd_count=1`), but `/vendor/bin/pm-service`
  exits `0` before observation and before holding `/dev/subsys_modem`.
  `pm-proxy` exits `1`, `pm_full_contract_seen=0`,
  `subsys_esoc0_open_attempted=0`, and no PM-service-owned
  `mdm_subsys_powerup`, RC1, MHI, WLFW, BDF, FW-ready, or `wlan0` marker is
  present.

  This keeps RC1/PERST/refclk and firmware/MHI/WLFW work parked for the current
  branch.  Next gate: V1604 source/build-only focused `per_mgr` startup
  diagnostic in `a90_android_execns_probe`: after the proven PPH fd gate,
  sample `per_mgr` at 10-20ms cadence from spawn until exit or one second;
  record first observable time, exit timing, exit code/signal, cwd, cmdline,
  wchan, fd links, `/dev/subsys_modem`, `/dev/vndbinder`, `/dev/hwbinder`,
  binder/socket surface, and stdout/stderr byte counts/diagnostic tails.  Still
  no credentials, scan/connect, DHCP/routes, external ping, PMIC/GPIO/GDSC
  direct writes, blind eSoC notify/`BOOT_DONE`, global PCI rescan, platform
  bind/unbind, or unbounded boot-image/partition writes.  Report:
  `docs/reports/NATIVE_INIT_V1603_PM_SERVICE_EXIT_CLASSIFIER_2026-06-02.md`.

- V1604/V1605 source/build and local sanity loop is complete.  V1604 bumps
  `a90_android_execns_probe` to v298 and builds a rollbackable test boot that
  preserves the V1600 PM-first late-per-proxy PPH-gated lower-marker route, but
  adds `--allow-android-wifi-service-window-per-mgr-startup-trace`.

  The new bounded diagnostic samples `per_mgr` every `20ms` for `1s` after
  spawn, immediately after the proven PPH `/dev/subsys_modem` fd gate.  It
  records liveness, state, cmdline, cwd, wchan, exit timing, and fd counts for
  `/dev/subsys_modem`, `/dev/subsys_esoc0`, binder nodes, sockets, and
  `/dev/socket`.  This is intended to catch the clean early `pm-service` exit
  boundary that V1602/V1603 identified.

  V1604 source build passes as
  `v1604-per-mgr-startup-trace-test-boot-source-build-pass`; boot image:
  `tmp/wifi/v1604-per-mgr-startup-trace-test-boot/boot_linux_v1604_wifi_test.img`,
  sha256 `eb8d1dc11656a8380180b96239d9fe9c8ba160f55f1ca3ff34a8552a6438cca8`.
  Helper marker is `a90_android_execns_probe v298`, sha256
  `6a56b15650fe5c7785a878e7f86ade8e9c323e33cfb8c049952388022592d898`.

  V1605 artifact sanity passes as
  `v1605-per-mgr-startup-trace-artifact-sanity-pass`; it verifies static
  binaries, ramdisk entries, boot/header/kernel parity, V1604 route markers,
  helper markers, init route, route contract, forbidden credential-like byte
  absence, and private modes.

  Next gate: V1606 rollbackable live handoff of only the V1604 image.  Collect
  helper result/startup trace/lower markers/dmesg/`wlan0`, roll back to
  `stage3/boot_linux_v724.img`, and verify native selftest `fail=0`.  Still no
  credentials, scan/connect, DHCP/routes, external ping, PMIC/GPIO/GDSC direct
  writes, blind eSoC notify/`BOOT_DONE`, global PCI rescan, platform
  bind/unbind, or unbounded boot-image/partition writes.  Reports:
  `docs/reports/NATIVE_INIT_V1604_PER_MGR_STARTUP_TRACE_SOURCE_BUILD_2026-06-02.md`
  and
  `docs/reports/NATIVE_INIT_V1605_PER_MGR_STARTUP_TRACE_ARTIFACT_SANITY_2026-06-02.md`.

- V1606/V1607 live handoff and host classifier loop is complete.  V1606 flashes
  only the V1604 image, collects helper result/startup trace/lower
  markers/dmesg/`wlan0`, rolls back from native to v724, and verifies selftest
  `fail=0`.  Strict Wi-Fi progress is blocked as
  `v1606-test-boot-no-downstream-wifi-progress-blocked`; there is still no
  provider trigger, RC1, MHI, WLFW, BDF, FW-ready, or `wlan0` marker.

  V1607 passes as `v1607-per-mgr-exits-before-any-contract-fd`.  The PPH modem
  fd gate remains proven (`pm_proxy_helper_subsys_modem_fd_count=1`), but
  `/vendor/bin/pm-service` exits cleanly before any PM contract fd appears:
  sample count `51`, alive at `0ms`, last alive at `20ms`, child-done at `21ms`,
  gone by `41ms`, `exit_code=0`, `signal=0`, and max fd counts are `0` for
  `/dev/subsys_modem`, `/dev/subsys_esoc0`, `/dev/vndbinder`, `/dev/hwbinder`,
  `/dev/binder`, sockets, and `/dev/socket`.

  Current blocker: a pre-contract startup/branch exit inside
  `/vendor/bin/pm-service`.  Lower SDX50M/eSoC/RC1, firmware/MHI/WLFW, and
  Wi-Fi HAL work remain downstream until `pm-service` stays alive long enough to
  open or register the expected PM surfaces.

  Next gate: V1608 source/build-only focused pm-service early-exit cause tracer.
  Prefer bounded ptrace/exit or uprobe/openat/exit tracing around only
  `/vendor/bin/pm-service`, enough to capture the syscall/library branch that
  leads to `exit(0)` and whether properties, service state, vndservicemanager,
  binder nodes, or peripheral state are checked before exit.  Do not ptrace
  `mdm_helper` or any long-running eSoC path.  Still no credentials,
  scan/connect, DHCP/routes, external ping, PMIC/GPIO/GDSC direct writes, blind
  eSoC notify/`BOOT_DONE`, global PCI rescan, platform bind/unbind, or unbounded
  boot-image/partition writes.  Reports:
  `docs/reports/NATIVE_INIT_V1606_PER_MGR_STARTUP_TRACE_HANDOFF_2026-06-02.md`
  and
  `docs/reports/NATIVE_INIT_V1607_PER_MGR_STARTUP_TRACE_CLASSIFIER_2026-06-02.md`.

- V1608/V1609 source/build and local sanity loop is complete.  V1608 bumps
  `a90_android_execns_probe` to v299 and preserves the V1604 PM-first
  late-per-proxy PPH-gated lower-marker route, but adds a bounded
  `per_mgr`-only early-exit tracer:
  `--capture-mode ptrace-lite` plus
  `--allow-android-wifi-service-window-per-mgr-early-exit-trace`.

  The new tracer is scoped to `/vendor/bin/pm-service`; it does not ptrace
  `mdm_helper`, directly open scoped `/dev/subsys_esoc0`, broaden the lower
  eSoC/RC1 path, or start Wi-Fi HAL/scan/connect work.  It records selected
  `openat`, stat/access/readlink, socket/bind/connect, ioctl, read/write,
  futex, wait, and exit syscalls under
  `pm_service_trigger_observer.syscall.per_mgr.*`, plus child trace summaries
  under `android_wifi_service_window.child.per_mgr.*`.

  V1608 source build passes as
  `v1608-per-mgr-early-exit-trace-test-boot-source-build-pass`; boot image:
  `tmp/wifi/v1608-per-mgr-early-exit-trace-test-boot/boot_linux_v1608_wifi_test.img`,
  sha256 `6eb8f218b2bc7a7cfdd7c2f27cba290643149e0de4631de89574c9ac255cf076`.
  Init is `A90 Linux init 0.9.107 (v1608-per-mgr-early-exit-trace)`.
  Helper marker is `a90_android_execns_probe v299`, sha256
  `c5ecbd41c06943f88c88f32fbdacdcd28d5d46c62fbcceb159de4f269619389b`.

  V1609 artifact sanity passes as
  `v1609-per-mgr-early-exit-trace-artifact-sanity-pass`; it verifies static
  binaries, ramdisk entries, V1608 route and ptrace-lite markers, helper/init
  route contract, boot/header/kernel parity, forbidden credential-like byte
  absence, and private modes.

  Next gate: V1610 rollbackable live handoff of only the V1608 image.  Collect
  helper result, `pm_service_trigger_observer.syscall.per_mgr.*`,
  `android_wifi_service_window.child.per_mgr.*`, lower markers, dmesg, and
  `wlan0`; roll back to `stage3/boot_linux_v724.img`; verify native selftest
  `fail=0`.  The target is to classify the V1607 blocker: a clean
  pre-contract `/vendor/bin/pm-service` exit before any PM fd, binder, socket,
  or eSoC trigger surface appears.  Still no `mdm_helper` ptrace,
  credentials, scan/connect, DHCP/routes, external ping, PMIC/GPIO/GDSC direct
  writes, blind eSoC notify/`BOOT_DONE`, global PCI rescan, platform
  bind/unbind, or unbounded boot-image/partition writes.  Reports:
  `docs/reports/NATIVE_INIT_V1608_PER_MGR_EARLY_EXIT_TRACE_SOURCE_BUILD_2026-06-02.md`
  and
  `docs/reports/NATIVE_INIT_V1609_PER_MGR_EARLY_EXIT_TRACE_ARTIFACT_SANITY_2026-06-02.md`.

- V1610/V1611 live handoff and host classifier loop is complete.  V1610 flashes
  only the V1608 image, collects helper result/syscall trace/lower
  markers/dmesg/`wlan0`, rolls back from native to v724, and verifies selftest
  `fail=0`.  Strict Wi-Fi progress remains blocked as
  `v1610-test-boot-no-downstream-wifi-progress-blocked`; progress decision is
  `modem-trigger-no-downstream`.

  The important result is not lower Wi-Fi progress.  V1611 passes as
  `v1611-ptrace-lite-intrusive-stop-limit-no-exit-cause`: ptrace-lite changed
  `/vendor/bin/pm-service` behavior.  The target stayed in `ptrace_stop` for
  the full 1s startup sampler (`last_alive_ms=1000`, `first_gone_ms=-1`,
  `first_child_done_ms=-1`), the tracer captured only
  `faccessat('/dev/urandom')`, and then hit the syscall stop limit
  (`syscall_stop_count=128`, `trace_disable_reason=stop-limit`).  No
  `/dev/subsys_modem`, `/dev/subsys_esoc0`, PM full contract, RC1, MHI, WLFW,
  BDF, FW-ready, or `wlan0` marker appeared.

  Current branch correction: retire syscall ptrace for `pm-service`.  V1607's
  natural early exit is still the relevant blocker, but V1608/V1610 cannot
  explain it because the observer perturbs the process.  Do not use this run to
  select a lower SDX50M/eSoC/RC1 retry.

  Next gate: V1612 source/build-only non-stopping `pm-service` startup
  classifier.  Replace ptrace-lite with stdout/stderr tails, bounded service-
  manager/property/socket namespace snapshots, vendor init/env comparison, and
  host-only dependency/string analysis.  Still no `pm-service` syscall ptrace,
  `mdm_helper` ptrace, direct scoped `/dev/subsys_esoc0`, credentials,
  scan/connect, DHCP/routes, external ping, PMIC/GPIO/GDSC direct writes,
  blind eSoC notify/`BOOT_DONE`, global PCI rescan, platform bind/unbind, or
  unbounded boot-image/partition writes.  Reports:
  `docs/reports/NATIVE_INIT_V1610_PER_MGR_EARLY_EXIT_TRACE_HANDOFF_2026-06-02.md`
  and
  `docs/reports/NATIVE_INIT_V1611_PER_MGR_EARLY_EXIT_TRACE_CLASSIFIER_2026-06-02.md`.

- V1612-V1615 non-stopping `pm-service` loop is complete.  V1612 bumps
  `a90_android_execns_probe` to v300, preserves the PM-first late-per-proxy
  PPH-gated lower-marker route, removes ptrace-lite from the `pm-service`
  branch, and adds
  `--allow-android-wifi-service-window-per-mgr-nonstop-context-trace`.
  V1613 artifact sanity passes, and V1614 rollbackable live handoff boots the
  V1612 image, collects evidence, rolls back from native to v724, and verifies
  selftest `fail=0`.

  V1615 passes as
  `v1615-natural-pm-service-exit-after-offline-property-writes`.  This fixes
  the current blocker more precisely: without ptrace perturbation,
  `/vendor/bin/pm-service` naturally exits cleanly before any PM contract fd.
  The startup trace sees state `D` at `0ms`, state `Z` at `20ms`,
  `first_child_done_ms=21`, `first_gone_ms=41`, and `exit_code=0`.  It never
  opens `/dev/subsys_modem`, `/dev/subsys_esoc0`, binder nodes, sockets, or a
  PM full contract.

  The property shim records exactly three requests in that window:
  `hwservicemanager.ready=true`, `vendor.peripheral.SDX50M.state=OFFLINE`, and
  `vendor.peripheral.modem.state=OFFLINE`.  Lower Wi-Fi remains absent: no
  provider trigger, RC1, MHI, WLFW, BDF, FW-ready, or `wlan0`.

  Current branch correction: do not retry lower SDX50M/eSoC/RC1 from this
  state, and do not reintroduce `pm-service` syscall ptrace.  The active
  blocker is the peripheral-manager launch/property contract that makes
  `pm-service` publish SDX50M/modem OFFLINE and exit before opening binder or
  `/dev/subsys_modem`.

  Next gate: V1616 host-only plus source/build-only `pm-service`
  dependency/launch-contract classifier.  Check `/vendor/bin/pm-service`
  strings/readelf/needed-libs, Android vendor init service stanza, user/group,
  seclabel, capabilities, environment, and Android-good property values
  consumed by peripheral manager.  If justified, build a bounded
  property-contract variant that exposes initial peripheral properties without
  ptrace.  Still no `pm-service` syscall ptrace, `mdm_helper` ptrace, direct
  scoped `/dev/subsys_esoc0`, credentials, scan/connect, DHCP/routes, external
  ping, PMIC/GPIO/GDSC direct writes, blind eSoC notify/`BOOT_DONE`, global PCI
  rescan, platform bind/unbind, or unbounded boot-image/partition writes.
  Reports:
  `docs/reports/NATIVE_INIT_V1612_PER_MGR_NONSTOP_CONTEXT_SOURCE_BUILD_2026-06-02.md`,
  `docs/reports/NATIVE_INIT_V1613_PER_MGR_NONSTOP_CONTEXT_ARTIFACT_SANITY_2026-06-02.md`,
  `docs/reports/NATIVE_INIT_V1614_PER_MGR_NONSTOP_CONTEXT_HANDOFF_2026-06-02.md`,
  and
  `docs/reports/NATIVE_INIT_V1615_PER_MGR_NONSTOP_CONTEXT_CLASSIFIER_2026-06-02.md`.

- V1616 host-only `pm-service` launch/dependency contract classifier is
  complete and passes as
  `v1616-pm-service-clean-exit-is-offline-system-info-contract-gap`.
  It uses V1614/V1615 runtime evidence, V862 Android init contract data, V1073
  extracted `pm-service` binary metadata, V1081 early-path analysis, and
  Android-good property evidence.

  The important branch correction is that older init-contract gaps are already
  modelled in current source: `ioprio rt 4`, `per_proxy_helper`,
  `init.svc.vendor.per_mgr=running`, shutdown-critical property allowlist, and
  OFFLINE property allowlist.  Yet native `pm-service` still exits naturally
  with code `0`, signal `0`, no `/dev/vndbinder`, socket, `/dev/subsys_modem`,
  `/dev/subsys_esoc0`, or PM full-contract fd, after publishing only
  `hwservicemanager.ready=true`,
  `vendor.peripheral.SDX50M.state=OFFLINE`, and
  `vendor.peripheral.modem.state=OFFLINE`.

  Android-good evidence contrasts this with `vendor.per_mgr=running`,
  `vendor.per_proxy=running`, `vendor.peripheral.SDX50M.state=ONLINE`,
  `vendor.peripheral.modem.state=ONLINE`, and
  `vendor.peripheral.shutdown_critical_list=SDX50M modem `.  Static binary
  evidence proves `pm-service` still has the Binder/QMI persistent server path
  available (`libbinder`, QMI CSI/CCI, `libmdmdetect`,
  `libperipheral_client`, `get_system_info`, `property_set`,
  `qmi_csi_register`, `vendor.qcom.PeripheralManager`).

  Current blocker: `pm-service` is making an OFFLINE-only
  `libmdmdetect`/`get_system_info` decision before Binder/QMI setup.  Do not
  retry lower RC1/MHI/WLFW from this route until the system-info input surface
  is classified.

  Next gate: V1617 source/build-only non-ptrace `pm-service` system-info
  surface capture.  Add bounded helper output around `pm-service` startup for
  `/sys/bus/msm_subsys/devices`, `/sys/bus/esoc/devices`,
  `/sys/class/esoc-dev`, `/dev/subsys_*`, `/dev/esoc-*`, `/dev/vndbinder`,
  private property root, and service-manager sockets.  Still no `pm-service`
  syscall ptrace, `mdm_helper` ptrace, direct scoped `/dev/subsys_esoc0`,
  Wi-Fi HAL start, credentials, scan/connect, DHCP/routes, external ping,
  PMIC/GPIO/GDSC writes, blind eSoC notify/`BOOT_DONE`, global PCI rescan, or
  platform bind/unbind.  Report:
  `docs/reports/NATIVE_INIT_V1616_PM_SERVICE_LAUNCH_CONTRACT_CLASSIFIER_2026-06-02.md`.

- V1617 source/build-only `pm-service` system-info surface test boot is
  complete and passes as
  `v1617-pm-service-system-info-surface-test-boot-source-build-pass`.

  It bumps `a90_android_execns_probe` to v301 and builds
  `A90 Linux init 0.9.109 (v1617-pm-service-system-info-surface)`.
  The boot image is
  `tmp/wifi/v1617-pm-service-system-info-surface-test-boot/boot_linux_v1617_wifi_test.img`
  with SHA256
  `7d9b60862a8eab04e0a0fe35b929ace255f0de669412a0cbe6262f6f0495419d`;
  helper SHA256 is
  `1b870e4244ba2794ee30bc113d6aa421f66dfea55a9c116139978b1b4b9e787e`.

  The helper adds
  `--allow-android-wifi-service-window-per-mgr-system-info-surface` and captures
  read-only `pm_service_system_info_surface.*` snapshots around `per_mgr`
  startup.  The intended classification target is exactly what
  `libmdmdetect`/`get_system_info` can see in the private namespace:
  `/sys/bus/msm_subsys/devices`, `/sys/bus/esoc/devices`,
  `/sys/class/esoc-dev`, `/dev/subsys_*`, `/dev/esoc-*`, binder nodes, private
  property root, and service-manager sockets.

  This cycle performed no live execution, flash, reboot, Wi-Fi HAL start,
  scan/connect, credentials, DHCP/routes, external ping, PMIC/GPIO/GDSC write,
  blind eSoC notify/`BOOT_DONE`, global PCI rescan, platform bind/unbind, or
  partition write.  It also does not reintroduce `pm-service` syscall ptrace,
  `mdm_helper` ptrace, or direct scoped `/dev/subsys_esoc0` actor opens.

  Next gate: V1618 local artifact sanity over
  `tmp/wifi/v1617-pm-service-system-info-surface-test-boot/manifest.json`.
  If V1618 passes, V1619 can be a rollbackable live handoff to collect the
  `pm_service_system_info_surface.*` evidence and roll back to
  `stage3/boot_linux_v724.img`.  Report:
  `docs/reports/NATIVE_INIT_V1617_PM_SERVICE_SYSTEM_INFO_SURFACE_SOURCE_BUILD_2026-06-02.md`.

- V1618 local-only artifact sanity is complete and passes as
  `v1618-pm-service-system-info-surface-artifact-sanity-pass`.

  It verifies the V1617 boot artifact at
  `tmp/wifi/v1617-pm-service-system-info-surface-test-boot/boot_linux_v1617_wifi_test.img`
  with SHA256
  `7d9b60862a8eab04e0a0fe35b929ace255f0de669412a0cbe6262f6f0495419d`.
  The verifier confirms manifest decision, base boot existence, static
  init/helper binaries, ramdisk entries, boot/helper/init route markers, route
  contract, boot header/kernel parity, forbidden credential-like byte absence,
  and private modes.

  No live command, flash, reboot, boot partition write, partition write,
  scan/connect, credential handling, DHCP/routes, external ping,
  PMIC/GPIO/GDSC direct write, blind eSoC notify/`BOOT_DONE` spoof, global PCI
  rescan, or platform bind/unbind was performed.

  Next gate: V1619 rollbackable live handoff.  Flash only the V1617 image,
  collect `pm_service_system_info_surface.*` evidence, roll back to
  `stage3/boot_linux_v724.img`, and verify selftest `fail=0`.  Report:
  `docs/reports/NATIVE_INIT_V1618_PM_SERVICE_SYSTEM_INFO_SURFACE_ARTIFACT_SANITY_2026-06-02.md`.

- V1619 rollbackable live handoff is complete.  It flashed the V1617 image,
  collected `pm_service_system_info_surface.*` evidence, rolled back from
  native, and verified v724/selftest after rollback.  Handoff/rollback pass is
  `True`, but strict Wi-Fi progress remains `False`; the result is
  `v1619-test-boot-no-downstream-wifi-progress-blocked`.

  V1620 host-only classifier passes as
  `v1620-pm-service-offline-decision-despite-visible-esoc-surface`.
  The private namespace exposes the expected core surface:
  `/dev/subsys_modem`, `/dev/subsys_esoc0`, `/dev/esoc-0`, binder nodes,
  `/dev/socket/property_service`, `/sys/bus/msm_subsys`, `/sys/bus/esoc`, and
  `/sys/class/esoc-dev`.  The read-only system-info snapshot sees
  `subsys0=modem ONLINE`, `subsys9=esoc0 OFFLINING`, and
  `esoc0=SDX50M PCIe 0305_01.01.00`.

  Despite that visible surface, `/vendor/bin/pm-service` still exits naturally
  with code `0`, signal `0`, before opening binder, sockets,
  `/dev/subsys_modem`, or `/dev/subsys_esoc0`.  It publishes only
  `hwservicemanager.ready=true`,
  `vendor.peripheral.SDX50M.state=OFFLINE`, and
  `vendor.peripheral.modem.state=OFFLINE`.  `/dev/__properties__` is absent in
  the private namespace, while the configured property root
  `/mnt/sdext/a90/private-property-v317/v535/dev/__properties__` exists on the
  device.

  Branch correction: do not treat this as missing core dev/sysfs nodes.  The
  next direct gate is to repair private property-root materialization for
  `wifi-companion-android-wifi-service-window-*` modes and retest whether
  `libmdmdetect`/`get_system_info` still chooses the OFFLINE-only path.

  Next gate: V1621 source/build-only property-root materialization repair.
  Keep blocked: Wi-Fi HAL start, scan/connect, credentials, DHCP/routes,
  external ping, PMIC/GPIO/GDSC writes, blind eSoC notify/`BOOT_DONE`, global
  PCI rescan, platform bind/unbind, and direct scoped `/dev/subsys_esoc0`
  actor opens.  Reports:
  `docs/reports/NATIVE_INIT_V1619_PM_SERVICE_SYSTEM_INFO_SURFACE_HANDOFF_2026-06-02.md`
  and
  `docs/reports/NATIVE_INIT_V1620_PM_SERVICE_SYSTEM_INFO_SURFACE_CLASSIFIER_2026-06-02.md`.

- V1621 source/build-only property-root materialization repair is complete and
  passes as `v1621-pm-service-property-root-test-boot-source-build-pass`.

  The helper change is deliberately small: `a90_android_execns_probe` v302 now
  treats `wifi-companion-android-wifi-service-window-*` plus
  `--allow-android-wifi-service-window` plus `--property-root` as a valid
  private property materialization path.  This should bind the existing remote
  property root
  `/mnt/sdext/a90/private-property-v317/v535/dev/__properties__` as
  `/dev/__properties__` inside the helper private namespace.

  V1622 local artifact sanity passes as
  `v1622-pm-service-property-root-artifact-sanity-pass`.  It verifies
  `tmp/wifi/v1621-pm-service-property-root-test-boot/boot_linux_v1621_wifi_test.img`
  with SHA256
  `52a56bc02787f2f72c44fad60aae6d8e4ca619135393798425e9d802f7d1c635`,
  `A90 Linux init 0.9.110 (v1621-pm-service-property-root)`, and
  `a90_android_execns_probe v302` SHA256
  `09732d4469d963e3c14ecb50f6f01341e92adfd3370c614d2ce779a71510230c`.

  V1622 remains local-only: no live command, flash, reboot, boot partition
  write, partition write, scan/connect, credential handling, DHCP/routes,
  external ping, PMIC/GPIO/GDSC direct write, blind eSoC notify/`BOOT_DONE`,
  global PCI rescan, or platform bind/unbind.

  Next gate: V1623 rollbackable live handoff.  Flash only the V1621 image,
  confirm `/dev/__properties__` appears in `pm_service_system_info_surface.*`,
  reclassify whether `pm-service` still exits through the OFFLINE-only path,
  roll back to `stage3/boot_linux_v724.img`, and verify selftest `fail=0`.
  Reports:
  `docs/reports/NATIVE_INIT_V1621_PM_SERVICE_PROPERTY_ROOT_SOURCE_BUILD_2026-06-02.md`
  and
  `docs/reports/NATIVE_INIT_V1622_PM_SERVICE_PROPERTY_ROOT_ARTIFACT_SANITY_2026-06-02.md`.

- V1623 rollbackable live handoff is complete.  It flashes the V1621
  property-root test image, collects service-window evidence, rolls back from
  native, and verifies v724 selftest after rollback.  Handoff/rollback passes,
  but strict Wi-Fi progress remains absent; the decision is
  `v1623-test-boot-no-downstream-wifi-progress-blocked`.

  V1624 host-only classifier passes as
  `v1624-property-root-materialized-shutdown-critical-list-blocked`.

  Important boundary movement:

  - `/dev/__properties__` is now visible and captured inside the private
    namespace, so V1621 repaired the property-root materialization gap.
  - `pm-service` still exits naturally with code `0`, signal `0`, before
    binder/socket/subsystem fd ownership.
  - the newly visible property path exposes a narrower blocker:
    `vendor.peripheral.shutdown_critical_list` writes for `SDX50M ` and
    `SDX50M modem ` are denied by the shim.
  - no RC1, MHI, WLFW, BDF, FW-ready, or `wlan0` progress appears.

  Next gate: V1625 source/build-only property-shim allowlist repair.  Enable
  the already-supported shutdown-critical-list values only for
  `wifi-companion-android-wifi-service-window-*` modes with
  `--allow-android-wifi-service-window`, then rebuild and locally sanity-check
  the test boot artifact before any new rollbackable live handoff.  Reports:
  `docs/reports/NATIVE_INIT_V1623_PM_SERVICE_PROPERTY_ROOT_HANDOFF_2026-06-02.md`
  and
  `docs/reports/NATIVE_INIT_V1624_PM_SERVICE_PROPERTY_ROOT_CLASSIFIER_2026-06-02.md`.

- V1625 source/build-only shutdown-critical-list repair is complete and passes
  as `v1625-pm-service-shutdown-list-test-boot-source-build-pass`.

  The helper change is deliberately narrow: `a90_android_execns_probe` v303
  enables the existing `vendor.peripheral.shutdown_critical_list` allowlist for
  android service-window modes with `--allow-android-wifi-service-window`.
  Accepted values remain only `SDX50M ` and `SDX50M modem `.

  V1626 local artifact sanity passes as
  `v1626-pm-service-shutdown-list-artifact-sanity-pass`.  It verifies
  `tmp/wifi/v1625-pm-service-shutdown-list-test-boot/boot_linux_v1625_wifi_test.img`
  with SHA256
  `8a9370fe4ed60f30eed044bd7b6d79d428106033856934b7d27c9e102939757b`,
  `A90 Linux init 0.9.111 (v1625-pm-service-shutdown-list)`, and
  `a90_android_execns_probe v303` SHA256
  `d58f637ce53b12f16f7143b388b20007553fe8d47bd6ed06379bde96a69c8798`.

  V1626 remains local-only: no live command, flash, reboot, boot partition
  write, partition write, scan/connect, credential handling, DHCP/routes,
  external ping, PMIC/GPIO/GDSC direct write, blind eSoC notify/`BOOT_DONE`,
  global PCI rescan, or platform bind/unbind.

  Next gate: V1627 rollbackable live handoff.  Flash only the V1625 image,
  verify shutdown-critical-list property requests are accepted, reclassify
  whether `pm-service` advances to IPC or PM fd ownership, roll back to
  `stage3/boot_linux_v724.img`, and verify selftest `fail=0`.  Reports:
  `docs/reports/NATIVE_INIT_V1625_PM_SERVICE_SHUTDOWN_LIST_SOURCE_BUILD_2026-06-02.md`
  and
  `docs/reports/NATIVE_INIT_V1626_PM_SERVICE_SHUTDOWN_LIST_ARTIFACT_SANITY_2026-06-02.md`.

- V1627 rollbackable live handoff is complete.  It flashes the V1625
  shutdown-list test image, collects service-window evidence, rolls back from
  native, and verifies v724 selftest after rollback.  Handoff/rollback passes,
  but strict Wi-Fi progress remains absent; the decision is
  `v1627-test-boot-no-downstream-wifi-progress-blocked`.

  V1628 host-only classifier passes as
  `v1628-shutdown-list-accepted-pm-service-still-exits-before-ipc`.

  Important boundary movement:

  - `allow_peripheral_shutdown_list=1` is proven in the property shim.
  - `vendor.peripheral.shutdown_critical_list` writes for `SDX50M ` and
    `SDX50M modem ` now return success.
  - `/dev/__properties__` remains materialized.
  - `pm-service` still exits naturally before binder/socket/subsystem fd
    ownership.
  - no RC1, MHI, WLFW, BDF, FW-ready, or `wlan0` progress appears.

  Branch correction: the immediate blockers are no longer property-root
  materialization or shutdown-critical-list allowlisting.  The next work should
  be host-only and should classify the remaining `pm-service` early-exit
  dependency against Android-good lifecycle evidence and prior V857-V860
  property-contract results.

  Next gate: V1629 host-only `pm-service` early-exit dependency classifier.
  Decide whether the next minimal experiment should be private read-only
  system-info parity modelling, init-property lifecycle modelling, or another
  missing IPC/service-manager surface.  Do not add any new live lower-layer
  retry until that dependency is narrowed.  Reports:
  `docs/reports/NATIVE_INIT_V1627_PM_SERVICE_SHUTDOWN_LIST_HANDOFF_2026-06-02.md`
  and
  `docs/reports/NATIVE_INIT_V1628_PM_SERVICE_SHUTDOWN_LIST_CLASSIFIER_2026-06-02.md`.

## OUT-OF-BAND CAUSALITY HANDOFF — 2026-06-02 (pm-service track redirect; not a vNNN cycle)

- full writeup: docs/reports/ESOC_PMSERVICE_CAUSALITY_HANDOFF_2026-06-02.md
- flag: V1616-V1630 pm-service "OFFLINE-exit / system-info" track has inverted
  causality. subsys9=esoc0=OFFLINING is a TRUE fact (modem not powered), not a
  pm-service bug. pm-service publishing OFFLINE then exiting is CORRECT. V1616
  itself states Android keeps per_mgr/per_proxy alive BECAUSE SDX50M/modem are
  ONLINE (ONLINE is cause, pm-service-alive is effect).
- do NOT proceed with V1630 fake-ONLINE system-info bind: even if pm-service is
  tricked forward, the real modem is dead, so the next step
  (/dev/subsys_esoc0 -> mdm_subsys_powerup -> wait MDM2AP) blocks as V849/V1238/
  V1552 already proved. It is also state-spoofing vs fact-based observation.
- already-closed: V857/V860 closed "property cleanup alone does not make
  pm-service hold subsystem nodes." V1621-V1628 re-derived the same result; 6
  live boots (V1606/1610/1614/1619/1623/1627) all returned the identical
  no-downstream BLOCKED.
- real blocker (cross-confirmed by the loop's own V1552/V1556/V1559 + host static
  analysis 2026-06-01): native AP-side pcie1 power/refclk/PERST all proven, but
  the SDX50M endpoint is electrically silent -- GPIO104/WAKE=0, GPIO142/MDM2AP=0,
  IRQ252/IRQ290=0, no L0. Android asserts GPIO135/AP2MDM after esoc0 and before
  BDF; native never gets the GPIO142/MDM2AP answer. The modem never boots.
- keep (genuine): V1586 firmware/PIL progress via the software route;
  V1615/V1616 pm-service clean-exit mechanism; mdm_helper holds /dev/esoc-0.
- redirect (read-only first, no fake-ONLINE): classify what asserts
  GPIO142/MDM2AP -- i.e. what actually powers/boots SDX50M -- and why native's
  AP2MDM(GPIO135)/PM8150L-GPIO9 PON assertion gets no answer (level/timing/
  reset-time-ms parity vs Android). Revisit upper PM/WLFW only after that; V1586
  shows it follows once the modem is up. No PMIC/GPIO/GDSC write, no notify/
  BOOT_DONE spoof, no HAL/scan/connect.

- V1629 host-only causality reconciliation is complete and passes as
  `v1629-pm-service-causality-reconciled-lower-sdx50m-gate`.

  V1629 accepts the handoff correction and closes the pm-service property /
  system-info track for now:

  - V1496/V1497 fixed the low-level failure as
    `rc1-ltssm-link-failed-no-l0`.
  - V1498/V1523 prove TEST:11 reaches the common RC1 enumerate/enable path, so
    the core AP-side PCIe enable operation is not missing from that route.
  - V1552 proves AP-side pcie1 GDSC/refclk/pipe/PERST activity can occur while
    the endpoint remains electrically silent: no GPIO104/WAKE, no
    GPIO142/MDM2AP, no MDM status IRQ, and no L0.
  - V1621-V1628 repaired property-root and shutdown-critical-list behavior, but
    `pm-service` still exits because `subsys9=esoc0=OFFLINING` is true.
  - fake ONLINE system-info is rejected as state spoofing; it would only push an
    upper layer into the already-proven `/dev/subsys_esoc0` /
    `mdm_subsys_powerup` / MDM2AP block.

  Next gate: V1630 host-only lower-layer classifier/design.  Compare
  Android-good and native-fail evidence for AP2MDM, PM8150L GPIO9/PON,
  MDM2AP/GPIO142 IRQ, RC1 PHY/LTSSM/L0, MHI, WLFW/BDF/FW-ready, and `wlan0`.
  Reject fake ONLINE system-info, pm-service property chasing, blind TEST:11
  retry, PMIC/GPIO/GDSC direct writes, eSoC notify/`BOOT_DONE` spoof, Wi-Fi HAL
  start, scan/connect, credentials, DHCP/routes, and external ping.  Report:
  `docs/reports/NATIVE_INIT_V1629_PM_SERVICE_CAUSALITY_RECONCILIATION_2026-06-02.md`.

---

## OUT-OF-BAND HOST CLOSURE + LIVE CONTRACT (2026-06-02) — READ THIS, it sets the next live gate

A host-only deep-dive (no device writes) closed the entire static/config layer as
the Android-vs-native differentiator. All three are at parity:
- bootloader: non-differential (only boot partition is flashed).
- eSoC provider source (`docs/reports/ESOC_PON_SOURCE_ANALYSIS_2026-06-02.md`):
  full esoc-mdm C source found on disk (V766 tree). PON polarity CORRECT on native
  (`soft_reset_inverted=0`, assert LOW 120ms → de-assert HIGH; matches V1276 idle +
  V1318 pulse). Provider has ZERO regulator code — it cannot power the modem rail.
- DTB (`docs/reports/ESOC_DTB_PARITY_2026-06-02.md`): non-differential — appended
  SoC dtb matches source; mdm3/esoc board layer from shared dtb/dtbo partitions,
  live-proven correct on native (GPIO135/142/9 claim + polarity).

⇒ AP/software side is correct. The only remaining unknown is HARDWARE: does the
SDX50M power up and answer MDM2AP/GPIO142 when native's correct PON lands.

**Next live gate is fixed by the contract**:
`docs/reports/ESOC_NATURAL_PATH_MDM2AP_OBSERVATION_CONTRACT_2026-06-02.md`.
- Trigger: NATURAL `__subsystem_get(esoc0)` → `mdm_subsys_powerup` ONLY
  (PM-first / mdm_helper route, V1238/V1303/V1586). NO forced RC1 / case writes,
  NO fake-ONLINE.
- Observe (one long read-only window): esoc0 PIL, GPIO9 PON pulse, GPIO135 assert,
  **GPIO142/MDM2AP IRQ delta** + **errfatal IRQ delta** (discriminator). Reuse
  V1467 exact-provider PIL+GPIO tracepoint (rc1 writer OFF) + V1326 mdm2ap_timing
  sampler.
- Labels: `mdm2ap-responds` (new progress) / `mdm2ap-silent-natural-path` (PASS as
  classification — clean-path confirmation, removes V1552 forced-RC1 caveat) /
  `provider-did-not-trigger` (route regression).
- ONE run sets the label. Do NOT spin timing/window variants (that is the
  V1370–V1559 failure mode). After `mdm2ap-silent-natural-path`, STOP and hand
  back — the next move is a SEPARATELY user-authorized bounded modem-rail/PMIC
  experiment (V1250–V1255 direction), NOT autonomous.

This supersedes the V1630 "fake ONLINE / pm-service property chasing" direction
above (rejected as inverted causality).

## V1630-V1632 Natural-path MDM2AP Observation Gate (2026-06-02)

- V1630 source/build-only natural-path test boot is complete and passes as
  `v1630-natural-path-mdm2ap-observation-source-build-pass`.

  The artifact builds `A90 Linux init 0.9.112 (v1630-natural-mdm2ap)` with
  `a90_android_execns_probe v303` and targets the fixed 2026-06-02 contract:
  observe the natural `__subsystem_get(esoc0)` -> `mdm_subsys_powerup` route
  with V1467-style exact provider PIL/GPIO tracing and no forced RC1 case write,
  fake ONLINE, PMIC/GPIO/GDSC direct write, eSoC notify/`BOOT_DONE`, Wi-Fi HAL,
  scan/connect, credentials, DHCP/routes, or external ping.

- V1631 local artifact sanity passes as
  `v1631-natural-path-mdm2ap-observation-artifact-sanity-pass`.

  It verifies the V1630 boot image, helper/static linkage, ramdisk markers,
  private modes, forbidden credential-like bytes, and absence of forced writer /
  AP2MDM-hold markers in the test image artifact.

- V1632 executed the one rollbackable natural-path live handoff and rolled back
  successfully to `stage3/boot_linux_v724.img`; post-rollback device verification
  showed `A90 Linux init 0.9.68 (v724)` and selftest `fail=0`.

  Reclassification result: `v1632-natural-path-observation-incomplete`.

  Evidence captured:

  - natural provider trigger observed: `__subsystem_get(esoc0)` / provider thread
    in `sdx50m_toggle_soft_reset`.
  - esoc0 PIL notification observed: `fw=esoc0`.
  - PM8150L GPIO9/PON pulse observed: GPIO1270 LOW then HIGH.
  - AP2MDM observed: GPIO135 set high.
  - short-window GPIO142/MDM2AP samples stayed low: mdm status IRQ count lines
    stayed zero and debug GPIO reported `gpio142 : in 0`.
  - errfatal sample stayed zero in the captured post-provider window.
  - no forced RC1 `TEST: 11`, no LTSSM/RC1, no MHI, no WLFW, no BDF, no FW-ready,
    and no `wlan0` marker appeared.

  Important correction: the first V1632 wrapper version over-classified generic
  `GPIO142` / `mdm status` text as `mdm2ap-responds`.  The classifier was fixed
  host-only to require a real GPIO142 high sample or positive IRQ delta.  The
  evidence does **not** prove `mdm2ap-responds`.

  The run also failed to collect the required V1326-style `mdm2ap_timing.*`
  IRQ-delta result because the helper result file was absent and the supervisor
  timed out.  Therefore this is not the contract label
  `mdm2ap-silent-natural-path`, even though the short-window evidence suggests
  the endpoint remained silent.

  Do not run another timing/window variant automatically.  The contract's
  one-run rule was honored, the device is rolled back, and this should be handed
  back for direction.  A future live gate, if approved separately, should first
  repair evidence capture so the natural-path helper writes bounded
  `mdm2ap_timing.gpio142_irq_delta` and `mdm2ap_timing.errfatal_irq_delta`
  before any modem-rail/PMIC experiment.

  Reports:
  `docs/reports/NATIVE_INIT_V1630_NATURAL_PATH_MDM2AP_OBSERVATION_SOURCE_BUILD_2026-06-02.md`,
  `docs/reports/NATIVE_INIT_V1631_NATURAL_PATH_MDM2AP_OBSERVATION_ARTIFACT_SANITY_2026-06-02.md`,
  and
  `docs/reports/NATIVE_INIT_V1632_NATURAL_PATH_MDM2AP_OBSERVATION_HANDOFF_2026-06-02.md`.

## V1633 Natural-path MDM2AP IRQ Summary Repair (2026-06-02)

- V1633 source/build-only evidence-capture repair is complete and passes as
  `v1633-natural-path-mdm2ap-irq-summary-source-build-pass`.

  The V1632 live run proved the natural provider/PON/AP2MDM route can be
  observed, but did not collect the required `mdm2ap_timing.*` IRQ-delta helper
  output because the helper result file was absent and the supervised helper
  timed out.  V1633 fixes that capture dependency without running a new live
  gate: PID1 now writes the IRQ-delta summary directly into the provider window
  result file.

  V1633 artifact:

  - init: `A90 Linux init 0.9.113 (v1633-natural-mdm2ap-irq-summary)`.
  - boot image:
    `tmp/wifi/v1633-natural-path-mdm2ap-irq-summary-test-boot/boot_linux_v1633_natural_mdm2ap_irq_summary.img`.
  - boot SHA256:
    `cec663be484b15245200e2409cdd863f7976b204e064613295546b8a9a316691`.
  - helper remains `a90_android_execns_probe v303` with SHA256
    `d58f637ce53b12f16f7143b388b20007553fe8d47bd6ed06379bde96a69c8798`.
  - window result path:
    `/cache/native-init-wifi-test-boot-v1633-natural-window.result`.

  New capture behavior:

  - initial GPIO142/MDM2AP and mdm errfatal IRQ counts are collected immediately
    after natural provider detection.
  - after the provider micro-window, PID1 samples `/proc/interrupts` read-only
    for 120 samples at 50 ms and appends `mdm2ap_timing.gpio142_irq_delta`,
    `mdm2ap_timing.errfatal_irq_delta`, first-delta sample indexes, and safety
    zero markers into the window result.
  - this removes the previous dependency on helper normal exit for the specific
    MDM2AP discriminator required by the 2026-06-02 contract.

  Static validation completed: `py_compile`, source/build, boot marker checks,
  dangerous init argv marker absence, forbidden credential-like byte scan, and
  `git diff --check` passed.  No device command, flash, reboot, partition write,
  Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping,
  PMIC/GPIO/GDSC write, eSoC notify/`BOOT_DONE`, PCI rescan, or platform
  bind/unbind was performed for V1633.

  Next gate: V1634 local artifact sanity for V1633.  After that, if a live gate
  is selected, flash only the V1633 image, collect the V1633 window result, roll
  back to `stage3/boot_linux_v724.img`, verify selftest `fail=0`, and classify
  with the stricter V1632 logic that accepts `mdm2ap-responds` only on GPIO142
  high or positive IRQ delta.  Do not start modem-rail/PMIC writes from V1633
  automatically.

  Report:
  `docs/reports/NATIVE_INIT_V1633_NATURAL_PATH_MDM2AP_IRQ_SUMMARY_SOURCE_BUILD_2026-06-02.md`.

## V1634-V1638 Natural-path MDM2AP IRQ Summary Handoff (2026-06-02)

- V1634 local artifact sanity for V1633 passed, but V1635 live reclassification
  was corrected to `v1635-natural-path-observation-incomplete`: rollback was
  successful, natural provider/PON/AP2MDM evidence was present, and the short
  window stayed silent, but the PID1 IRQ parser had not collected the required
  parsed IRQ-delta contract fields.

- V1636 repaired the PID1 IRQ parser by streaming `/proc/interrupts` line-by-line
  instead of depending on one bounded read buffer.  V1637 local artifact sanity
  passed for the V1636 image:
  `tmp/wifi/v1636-natural-path-mdm2ap-irq-summary-test-boot/boot_linux_v1636_natural_mdm2ap_irq_summary.img`.

- V1638 executed one rollbackable natural-path live handoff with the V1636 image
  and rolled back successfully to `stage3/boot_linux_v724.img`; post-rollback
  verification showed the v724 baseline and selftest `fail=0`.

  Reclassification result: `v1638-natural-path-observation-incomplete`.

  Evidence captured:

  - natural provider trigger observed: `__subsystem_get(esoc0)` / esoc0 PIL.
  - GPIO1270/PON low/assert observed.
  - GPIO135/AP2MDM asserted.
  - GPIO142/MDM2AP IRQ initial parsed and delta collected: delta `0`.
  - mdm errfatal IRQ initial parsed and delta collected: delta `0`.
  - sample count `120`; safety markers all zero.
  - no RC1 transition, MHI, WLFW, BDF, FW-ready, or `wlan0`.

  Strict label remains incomplete because the window did not capture an explicit
  GPIO1270/PON high/de-assert trace marker.  The evidence strongly suggests
  MDM2AP stayed silent on the clean natural path, but the report deliberately
  does not promote this to `mdm2ap-silent-natural-path` without the full PON
  low->high trace required by the 2026-06-02 contract.

  Stop here for handoff.  Do not spin timing/window variants or enter bounded
  modem-rail/PMIC write gates from V1638 without a separate decision.

  Reports:
  `docs/reports/NATIVE_INIT_V1635_NATURAL_PATH_MDM2AP_IRQ_SUMMARY_HANDOFF_2026-06-02.md`,
  `docs/reports/NATIVE_INIT_V1636_NATURAL_PATH_MDM2AP_IRQ_SUMMARY_SOURCE_BUILD_2026-06-02.md`,
  `docs/reports/NATIVE_INIT_V1637_NATURAL_PATH_MDM2AP_IRQ_SUMMARY_ARTIFACT_SANITY_2026-06-02.md`,
  and
  `docs/reports/NATIVE_INIT_V1638_NATURAL_PATH_MDM2AP_IRQ_SUMMARY_HANDOFF_2026-06-02.md`.

## V1639-V1640 PON-high Reconciliation and Modem-rail Gate Plan (2026-06-02)

- V1639 host-only reconciliation passed as
  `v1639-pon-high-inferred-not-promoted`.

  It confirms the V1638 strict label remains `natural-path-observation-incomplete`
  because GPIO1270/PON high was not explicitly traced.  However, source order in
  `mdm4x_do_first_power_on()` makes GPIO135/AP2MDM high downstream of the PON
  de-assert path; V1638 observed PON low at `9.142510`, AP2MDM high at `9.480079`,
  and zero GPIO142/errfatal IRQ deltas over 120 samples.  This is useful evidence
  but intentionally not promoted to `mdm2ap-silent-natural-path`.

- V1640 host-only plan passed as
  `v1640-modem-rail-pmic-gate-plan-ready`.

  The next Wi-Fi-relevant blocker is below the natural eSoC provider path, but
  the next step is not a live write.  V1641 should first inventory plausible
  SDX50M power prerequisites and classify each as closed, observe-only,
  candidate, or rejected.  PM8150L GPIO9/PON and GPIO135/AP2MDM remain rejected
  as direct userspace write targets because they are kernel-owned and already
  parity-correct.  Forced RC1 enumerate, fake ONLINE, eSoC notify/`BOOT_DONE`,
  Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, and blind
  PMIC/GPIO/GDSC writes remain blocked.

  Reports:
  `docs/reports/NATIVE_INIT_V1639_PON_HIGH_EVIDENCE_RECONCILIATION_2026-06-02.md`
  and
  `docs/reports/NATIVE_INIT_V1640_MODEM_RAIL_PMIC_GATE_PLAN_2026-06-02.md`.

## V1641 Rail / Control Inventory (2026-06-02)

- V1641 host-only inventory passed as
  `v1641-no-safe-live-write-target-host-inventory-pass`.

  Candidate classification:

  - PM8150L GPIO9/PON: closed; reject direct userspace request/hold.
  - GPIO135/AP2MDM: closed as eSoC-provider output; reject direct write.
  - GPIO142/MDM2AP and GPIO141/errfatal: observe-only response inputs.
  - pcie1 GDSC/clocks/refclk/PERST: diagnostic/AP-side prerequisite; reject
    blind enable or pci-msm case write from this state.
  - unknown SDX50M main rail / bootloader PMIC default: only remaining candidate,
    but unowned and not writeable yet.

  Bounded artifact scan found no binary-like bootloader/PMIC artifacts in the
  limited `stage3` / `tmp/wifi` scope outside source/ramdisk subtrees.  Therefore
  no safe live PMIC/GPIO/GDSC write target is currently justified.  V1642 should
  stay host-only and classify bootloader/PMIC-owner artifacts and source
  references for the unknown SDX50M main-rail prerequisite before any live write
  preflight is designed.

  Report:
  `docs/reports/NATIVE_INIT_V1641_RAIL_CONTROL_INVENTORY_2026-06-02.md`.

## V1642 SDX50M Power Owner Classifier (2026-06-02)

- V1642 host-only classifier passed as
  `v1642-sdx-main-rail-owner-outside-ap-source-pass`.

  Findings:

  - AP `qcom,mdm3` / `qcom,ext-sdx50m` node exposes GPIO handshake only; no
    regulator/supply property appears in the mdm3 block.
  - AP `sm8150-sdxprairie.dtsi` links `mhi_0` to `mdm3` and deletes the AP-side
    `vdd_mss-supply`, so it does not expose a named AP main-rail control.
  - AP `pcie1` supplies (`pcie_1_gdsc`, `pm8150l_l3`, `pm8150_l5`, `VDD_CX_LEVEL`)
    are RC-side prerequisites and remain diagnostic, not a justified SDX main
    rail write target.
  - SDX-side source names `VDD_MODEM_LEVEL`, PMXPRAIRIE rails, and WLAN supplies,
    but those belong to the SDX/PMXPRAIRIE domain and are not currently reachable
    as a narrow AP-native write surface.
  - Bounded search found no binary-like bootloader/PMIC artifacts in the current
    repo scope.

  Decision: no live PMIC/GPIO/GDSC write gate is justified.  V1643 should remain
  non-mutating and either prepare a read-only partition/artifact acquisition plan
  for bootloader/PMIC ownership evidence, or hand off this external artifact gap
  explicitly.  Do not start Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or
  external ping until lower readiness progresses beyond MDM2AP/RC1/MHI/WLFW.

  Report:
  `docs/reports/NATIVE_INIT_V1642_SDX_POWER_OWNER_CLASSIFIER_2026-06-02.md`.

## V1643 Bootloader / PMIC Artifact Acquisition Plan (2026-06-02)

- V1643 host-only planning passed as
  `v1643-read-only-bootloader-pmic-artifact-plan-ready`.

  The natural-path MDM2AP observation has already been run once and V1642 found
  no AP-native safe write target for the suspected SDX50M main-rail owner.
  Therefore V1643 deliberately stays non-mutating: the next defensible step is
  read-only bootloader / PMIC ownership evidence, not a PMIC/GPIO/GDSC live
  write.

  Acquisition policy:

  - primary candidates: `xbl`, `xblbak`, `abl`, `ablbak`, `aop`, `aopbak`,
    `devcfg`, `devcfgbak`, `tz`, `tzbak`, `hyp`, `hypbak`, `keymaster`,
    `keymasterbak`, `cmnlib`, `cmnlibbak`, `cmnlib64`, `cmnlib64bak`,
    `qupfw`, `qupfwbak`;
  - context-only firmware candidates: `modem`, `NON-HLOS`, `bluetooth`, `dsp`;
  - sensitive / identity-bearing exclusions: `userdata`, `metadata`, `persist`,
    `efs`, `modemst1`, `modemst2`, `fsg`, `fsc`, `keystore`, `sec_efs`;
  - do not commit raw proprietary bootloader, firmware, partition dumps, `.img`,
    `.bin`, `.mbn`, `.elf`, `.tar`, `.lz4`, or `.md5` artifacts.

  V1644, if selected, should be read-only live partition metadata/hash capture
  only: partition map, resolved block paths, byte sizes, SHA256, and optionally
  bounded token-filtered strings.  Any later full dump must be an explicit
  separate private-evidence gate under ignored `tmp/` storage with `umask 077`;
  it must not enter git.

  Hard stops remain unchanged: no forced RC1 enumerate, pci-msm case write, fake
  ONLINE/system-info spoof, PMIC/GPIO/GDSC/regulator write, eSoC
  notify/`BOOT_DONE`, PCI rescan, platform bind/unbind, Wi-Fi HAL start,
  scan/connect, credentials, DHCP/routes, external ping, boot image write, or
  partition write.

  Report:
  `docs/reports/NATIVE_INIT_V1643_BOOTLOADER_PMIC_ARTIFACT_ACQUISITION_PLAN_2026-06-02.md`.

## V1644 Read-only Partition Metadata Capture (2026-06-02)

- V1644 live read-only metadata capture passed as
  `v1644-read-only-partition-metadata-captured`.

  The device remained on the v724 baseline and both pre/post selftest checks
  reported `fail=0`.  No boot image write, partition write, Wi-Fi HAL,
  scan/connect, credentials, DHCP/routes, external ping, PMIC/GPIO/GDSC write,
  eSoC notify/`BOOT_DONE`, PCI rescan, or platform bind/unbind was performed.

  Important runtime finding:

  - `/dev/block/by-name` is absent in native v724.
  - Candidate partition labels are still available through sysfs GPT metadata.
  - Candidate `/dev/block/<devname>` nodes are not exposed for the captured
    bootloader / firmware candidates, so V1644 records metadata but not raw
    partition SHA256 values.

  Candidate partition metadata captured:

  - `modem`: `sda21`, size `204472320`.
  - `dsp`: `sda22`, size `67108864`.
  - `xbl`: `sdb1`, size `4194304`.
  - `xbl`: `sdc1`, size `4194304`.
  - `tz`: `sdd5`, size `4194304`.
  - `aop`: `sdd7`, size `524288`.
  - `abl`: `sdd8`, size `4194304`.
  - `bluetooth`: `sdd10`, size `1048576`.
  - `keymaster`: `sdd12`, size `524288`.
  - `cmnlib`: `sdd13`, size `524288`.
  - `cmnlib64`: `sdd14`, size `524288`.
  - `devcfg`: `sdd22`, size `131072`.
  - `qupfw`: `sdd25`, size `81920`.
  - `hyp`: `sdd33`, size `1048576`.

  V1645 should stay host-only first: interpret which of these candidate
  partitions can plausibly contain SDX50M / PMIC / PON ownership evidence, then
  define a separate private read-only artifact extraction gate if raw content is
  actually required.  Any such extraction must keep proprietary binaries under
  ignored private evidence storage and out of git.

  Report:
  `docs/reports/NATIVE_INIT_V1644_PARTITION_METADATA_CAPTURE_2026-06-02.md`.

## V1645 Partition Owner Interpretation (2026-06-02)

- V1645 host-only interpretation passed as
  `v1645-partition-owner-priority-classified`.

  Priority classification:

  - high: `xbl` (`sdb1`, `sdc1`) as earliest bootloader / PMIC policy candidate.
  - high: `aop` (`sdd7`) as always-on power / RPMh-side firmware candidate.
  - medium-high: `devcfg` (`sdd22`) as board hardware configuration candidate.
  - medium: `abl` (`sdd8`) as late bootloader handoff context.
  - medium/context: `tz`, `hyp`, `qupfw`, `cmnlib`, `cmnlib64`, `keymaster`.
  - context-only: `modem`, `dsp`, `bluetooth`; do not pull the loop back into
    MHI/WLFW or firmware-transfer analysis before MDM2AP responds.

  Interpretation: the next evidence target is not a PMIC/GPIO/GDSC write and not
  Wi-Fi HAL.  It is a private read-only artifact access preflight for the small
  high-priority candidates (`xbl`, `aop`, `devcfg`, `abl`) because V1644 exposed
  sysfs GPT metadata but no candidate `/dev/block/<devname>` nodes.

  V1646 should choose one safe extraction path before touching raw content:

  - temporary private devnodes derived from sysfs major/minor with cleanup; or
  - TWRP/Android read-only pull.

  Either path must keep proprietary binaries under ignored private evidence
  storage and out of git.  It must not write partitions, force PMIC/GPIO/GDSC
  state, issue eSoC notify/`BOOT_DONE`, rescan PCI, start Wi-Fi HAL, scan/connect,
  use credentials, run DHCP/routes, or external ping.

  Report:
  `docs/reports/NATIVE_INIT_V1645_PARTITION_OWNER_INTERPRETATION_2026-06-02.md`.

## V1646 Private Devnode Preflight (2026-06-02)

- V1646 read-only preflight passed as
  `v1646-private-devnode-preflight-ready`.

  This gate did not create devnodes and did not read partition contents.  It only
  confirmed selected high-priority candidates expose sysfs major/minor metadata
  and that toybox has the helpers required for a later private SHA256-only gate
  (`mknod`, `mkdir`, `rm`, `sha256sum`, `ls`, `cat`).

  Selected candidates:

  - `xbl_a`: `sdb1`, major:minor `8:17`, size `4194304`, `ro=1`.
  - `xbl_b`: `sdc1`, major:minor `8:33`, size `4194304`, `ro=1`.
  - `aop`: `sdd7`, major:minor `8:55`, size `524288`, `ro=1`.
  - `devcfg`: `sdd22`, major:minor `259:9`, size `131072`, `ro=1`.
  - `abl`: `sdd8`, major:minor `8:56`, size `4194304`, `ro=1`.

  V1647 may create temporary private devnodes under ignored evidence storage,
  compute SHA256 for these selected small candidates, remove the devnodes, and
  document only hashes/metadata.  Raw proprietary binaries must remain out of
  git.  V1647 must still avoid partition writes, PMIC/GPIO/GDSC writes, eSoC
  notify/`BOOT_DONE`, PCI rescan, Wi-Fi HAL, scan/connect, credentials,
  DHCP/routes, and external ping.

  Report:
  `docs/reports/NATIVE_INIT_V1646_PRIVATE_DEVNODE_PREFLIGHT_2026-06-02.md`.

## V1647 Private Devnode SHA256 Gate (2026-06-02)

- V1647 temporary-devnode SHA256 gate passed as
  `v1647-private-devnode-sha256-captured`.

  This gate created temporary filesystem-only devnodes under `/dev`, computed
  SHA256 for the selected small candidates, removed each node, then removed the
  temporary directory.  Final cleanup was verified by `ls -ld
  /dev/a90_v1647_devnodes` returning `No such file or directory`.

  Hashes:

  - `xbl_a` (`sdb1`, `8:17`, size `4194304`):
    `e73a07a0b5e3eb9e8db9199eda125ee29b218765f050f85dd934a556549ebe37`.
  - `xbl_b` (`sdc1`, `8:33`, size `4194304`):
    `ae1191b5d70e6de9fd67c6d629bc93aa567296605d30b5c9196ff58fcc26cb50`.
  - `aop` (`sdd7`, `8:55`, size `524288`):
    `eadd6c78daca52221e1e3419f34a53eac7c1e2c2bb46c9b663325df1998b9c7c`.
  - `devcfg` (`sdd22`, `259:9`, size `131072`):
    `0399578253dd293dfc961c6a1077f660834df3ae5e1d65555f4225e327a03d14`.
  - `abl` (`sdd8`, `8:56`, size `4194304`):
    `1db19d11a5ce6865e3fbcabadfbdaa9045e75f144b8bc8593a58338c20a3120c`.

  Duplicate groups: none.  The two `xbl` slots differ, so any future offline
  analysis must treat them as distinct copies or versions rather than assuming a
  mirrored pair.

  V1647 did not dump raw partition bytes, commit proprietary binaries, write
  partitions, write PMIC/GPIO/GDSC state, issue eSoC notify/`BOOT_DONE`, rescan
  PCI, start Wi-Fi HAL, scan/connect, use credentials, run DHCP/routes, or
  external ping.

  V1648 should stay host-only first: interpret the hashes and decide whether a
  bounded strings-only or external offline analysis gate is justified.  Do not
  proceed to modem-rail writes or Wi-Fi HAL until an actual SDX50M power-owner
  hypothesis is supported.

  Report:
  `docs/reports/NATIVE_INIT_V1647_PRIVATE_DEVNODE_HASH_GATE_2026-06-02.md`.

## V1648 Hash Interpretation / Token Scan Plan (2026-06-02)

- V1648 host-only interpretation passed as
  `v1648-bounded-token-scan-plan-ready`.

  Hash interpretation:

  - all five selected candidates have stable SHA256 evidence from V1647.
  - duplicate hash groups: none.
  - the two `xbl` slots differ, so they must be treated as separate copies or
    versions until external comparison proves which slot is active.

  V1649 should avoid raw `strings` dumps.  The next allowed content-read shape is
  token-only bounded grep through temporary private devnodes:

  ```sh
  toybox grep -a -i -b -o -m 200 -E 'sdx|sdx50|sdxprairie|pmic|pm8150|pm8150l|pmxprairie|pon|ps_hold|mdm|mdm2ap|ap2mdm|vdd|rpmh|aop|gpio|pcie|mhi' <temporary-node>
  ```

  This emits only `offset:matched-token`, not full strings or raw binary lines.
  Use it only to classify which artifact contains SDX/PMIC/PON vocabulary before
  deciding whether private offline string extraction is justified.

  Hard stops remain: no raw partition dump, no full `strings` output, no
  proprietary binary commit, no partition write, no PMIC/GPIO/GDSC write, no
  eSoC notify/`BOOT_DONE`, no PCI rescan, no Wi-Fi HAL, no scan/connect, no
  credentials, no DHCP/routes, and no external ping.

  Report:
  `docs/reports/NATIVE_INIT_V1648_HASH_INTERPRETATION_TOKEN_SCAN_PLAN_2026-06-02.md`.

## V1649 Bounded Token Scan Gate (2026-06-02)

- V1649 temporary-devnode token-only scan passed as
  `v1649-bounded-token-scan-captured`.

  This gate used the V1647-selected candidates and emitted only
  `offset:matched-token` pairs via bounded `grep -a -i -b -o -m`; it did not run
  full `strings`, dump raw partition bytes, commit proprietary binaries, write
  partitions, write PMIC/GPIO/GDSC state, issue eSoC notify/`BOOT_DONE`, rescan
  PCI, start Wi-Fi HAL, scan/connect, use credentials, run DHCP/routes, or
  external ping.  Final cleanup verified `/dev/a90_v1649_devnodes` absent.

  Token summary:

  - `xbl_a`: 413 token hits; includes `pmic`, `vdd`, `aop`, `pon`, `ps_hold`,
    `sdx`, `rpmh`, `gpio`, `pcie`, `mdm`.
  - `xbl_b`: 333 token hits; includes the same relevant vocabulary family.
  - `aop`: 13 token hits; mostly `aop`, plus `gpio` and `pmic`.
  - `devcfg`: 3 token hits; `gpio` and `pmic`.
  - `abl`: 2 token hits; `aop` and `mdm`.

  Interpretation: `xbl_a` / `xbl_b` now have the strongest evidence as the
  next artifact-analysis targets for SDX50M / PMIC / PON ownership.  `aop` and
  `devcfg` remain secondary.  `abl` is low-yield for this specific blocker.

  Note: `grep -m` limits matching lines; with binary-like input and `-o`, total
  token counts can exceed the line limit while still remaining token-only output.

  V1650 should stay host-only first: interpret token distribution and decide
  whether a narrower private offline analysis target is justified.  Do not
  proceed to modem-rail writes or Wi-Fi HAL until an actual SDX50M power-owner
  hypothesis is supported.

  Report:
  `docs/reports/NATIVE_INIT_V1649_BOUNDED_TOKEN_SCAN_GATE_2026-06-02.md`.

## V1650 Token Owner Hypothesis (2026-06-02)

- V1650 host-only interpretation passed as
  `v1650-xbl-first-private-analysis-hypothesis`.

  Ranked artifact scores:

  - `xbl_a`: matches `413`, power score `328`, SDX score `85`, specific score
    `554`.
  - `xbl_b`: matches `333`, power score `247`, SDX score `86`, specific score
    `452`.
  - `aop`: matches `13`, power score `13`, SDX score `0`, specific score `2`.
  - `devcfg`: matches `3`, power score `3`, SDX score `0`, specific score `2`.
  - `abl`: matches `2`, power score `1`, SDX score `1`, specific score `2`.

  Hypothesis: the next private offline analysis target should be `xbl_a` /
  `xbl_b`.  They contain dense PMIC/VDD/PON/PS_HOLD/RPMh/SDX/PCIe vocabulary.
  `aop` and `devcfg` remain secondary context; `abl` is low-yield for this
  blocker.

  This does not prove a concrete PMIC write target.  It only narrows the next
  analysis target to XBL.  PMIC/GPIO/GDSC mutation remains unjustified.

  V1651 should be a host-only/private-evidence plan for bounded XBL
  string-context extraction around offsets already observed in V1649.  Raw
  proprietary content must remain under ignored private storage; tracked output
  should summarize only non-sensitive token contexts and hypotheses.  No Wi-Fi
  HAL, scan/connect, credentials, DHCP/routes, external ping, partition write,
  PMIC/GPIO/GDSC write, eSoC notify/`BOOT_DONE`, or PCI rescan.

  Report:
  `docs/reports/NATIVE_INIT_V1650_TOKEN_OWNER_HYPOTHESIS_2026-06-02.md`.

## V1651 XBL Token Cluster Context (2026-06-02)

- V1651 host-only XBL token clustering passed as
  `v1651-xbl-cluster-context-ready`.

  Method: group V1649 `offset:matched-token` evidence into XBL regions with an
  `8192` byte gap.  No device command, live write, raw strings dump, binary dump,
  or proprietary artifact commit was performed.

  Top clusters:

  - `xbl_a` region `3340797..3377867`: `rpmh-aop-pmic-context`, score `504`,
    tokens `aop=54`, `rpmh=83`, `pmic=12`, `pon=5`, `vdd=4`, `pcie=1`.
  - `xbl_b` region `3355345..3400091`: `rpmh-aop-pmic-context`, score `376`,
    tokens `aop=53`, `rpmh=49`, `pmic=8`, `pon=7`, `vdd=1`, `pcie=1`,
    `gpio=6`.
  - both XBL copies also have early `pon-pshold-pmic-context` clusters around
    offset `~20000..30662` containing `pmic`, `pon`, `ps_hold`, `sdx`, and `vdd`.
  - both XBL copies have dense `pcie-context` clusters around `~3666k..3682k`.

  Interpretation: XBL is no longer merely a high-level candidate.  The
  token-only evidence identifies compact XBL regions combining RPMh/AOP/PMIC/PCIe
  and PON/PS_HOLD/SDX vocabulary.  This is the strongest current artifact-level
  path for explaining the native-vs-Android SDX50M power-state difference.

  This still does not identify a concrete PMIC/GPIO/GDSC write target.  V1652
  should plan a bounded private string-context extraction only around these top
  XBL clusters.  Raw strings and proprietary binary content must remain under
  ignored private evidence; tracked output should contain only redacted context
  classes, token neighborhoods, hashes, and hypotheses.  No PMIC/GPIO/GDSC
  write, partition write, eSoC notify/`BOOT_DONE`, PCI rescan, Wi-Fi HAL,
  scan/connect, credentials, DHCP/routes, or external ping.

  Report:
  `docs/reports/NATIVE_INIT_V1651_XBL_TOKEN_CLUSTER_CONTEXT_2026-06-02.md`.

## V1652 XBL Private Context Contract (2026-06-02)

- V1652 host-only extraction contract passed as
  `v1652-xbl-private-context-contract-ready`.

  Target clusters:

  - `xbl_a` range `3340797..3377867`: `rpmh-aop-pmic-context`.
  - `xbl_b` range `3355345..3400091`: `rpmh-aop-pmic-context`.
  - `xbl_a` range `20034..29600`: `pon-pshold-pmic-context`.
  - `xbl_b` range `20027..30662`: `pon-pshold-pmic-context`.

  Tracked output allowlist for any later context extraction:

  - artifact label, range start/end, string offset, string length;
  - SHA256 of the private string;
  - matched token list;
  - redacted token-neighborhood class.

  Tracked output and git must not include raw string text, raw binary bytes, full
  `strings` output, partition dumps, SSID/passphrase values, PMIC/GPIO/GDSC
  writes, eSoC notify/`BOOT_DONE`, PCI rescan, Wi-Fi HAL, or scan/connect
  material.

  V1653 should be source/build-only for a static helper named
  `a90_xbl_context_probe`.  The helper contract: input a temporary private block
  devnode path, artifact label, bounded ranges, and token regex; read only those
  ranges; identify printable strings intersecting the ranges; emit tracked-safe
  records only.  Raw string text may exist only in ignored private evidence if a
  later gate explicitly needs it.

  Report:
  `docs/reports/NATIVE_INIT_V1652_XBL_PRIVATE_CONTEXT_CONTRACT_2026-06-02.md`.

## V1653 XBL Context Probe Build (2026-06-02)

- V1653 source/build-only helper gate passed as
  `v1653-xbl-context-probe-build-pass`.

  Built helper:

  - source: `stage3/linux_init/helpers/a90_xbl_context_probe.c`;
  - artifact: `tmp/wifi/v1653-xbl-context-probe-build/a90_xbl_context_probe_v1653`;
  - SHA256:
    `e7a143550d99e89aa5dfd3f25daa5c05118e4530cdafe4d1f615cc98daf32f53`;
  - size: `663456`;
  - static checks: no `INTERP`, no dynamic section, statically linked.

  Helper contract:

  - input: `--path PATH --artifact LABEL --range START:END`;
  - reads only bounded ranges;
  - emits tracked-safe `record` lines with artifact/range/offset/length/
    truncated/`string_sha256`/tokens/class;
  - emits no raw string text in tracked output;
  - binary artifact remains under ignored private `tmp/` evidence and is not
    committed.

  V1654 may deploy/run this helper against temporary XBL devnodes and only the
  V1652 ranges.  Tracked reports must include only redacted records.  No
  partition write, PMIC/GPIO/GDSC write, eSoC notify/`BOOT_DONE`, PCI rescan,
  Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.

  Report:
  `docs/reports/NATIVE_INIT_V1653_XBL_CONTEXT_PROBE_BUILD_2026-06-02.md`.

## V1654 XBL Context Probe Live Gate (2026-06-02)

- V1654 private live XBL redacted-context probe passed as
  `v1654-xbl-context-probe-live-pass`.

  Execution summary:

  - helper: `/cache/bin/a90_xbl_context_probe_v1653`;
  - helper SHA256:
    `e7a143550d99e89aa5dfd3f25daa5c05118e4530cdafe4d1f615cc98daf32f53`;
  - transfer: serial `appendfile` + `uudecode`, chunk size `1800`, chunks `508`;
  - temporary devnodes: `/dev/a90_v1654_devnodes/xbl_a` and `xbl_b`;
  - approved ranges only:
    - `xbl_a`: `3340797:3377867`, `20034:29600`;
    - `xbl_b`: `3355345:3400091`, `20027:30662`;
  - redacted records: `326` total (`xbl_a=175`, `xbl_b=151`);
  - cleanup: temporary devnode directory absent after the run;
  - native health: pre/post `selftest fail=0`.

  The tracked report includes only artifact/range/offset/length/truncation,
  string SHA256, matched tokens, and redacted context class.  No raw strings,
  raw partition bytes, proprietary binary dumps, partition writes,
  PMIC/GPIO/GDSC writes, eSoC notify/`BOOT_DONE`, PCI rescan, Wi-Fi HAL,
  scan/connect, credentials, DHCP/routes, or external ping were performed.

  The context records strengthen XBL as the highest-value bootloader-side
  artifact for PMIC/RPMh/AOP/PON/SDX vocabulary, but they still do not justify
  any direct power-rail or GPIO write.  V1655 should remain host-only: reduce
  the redacted context records into duplicate/hash groupings, class clusters,
  and a concrete hypothesis list.  Bounded rail or PMIC mutation remains a
  separate explicit gate.

  Report:
  `docs/reports/NATIVE_INIT_V1654_XBL_CONTEXT_PROBE_LIVE_2026-06-02.md`.

## V1655 XBL Context Interpretation (2026-06-02)

- V1655 host-only interpretation passed as
  `v1655-xbl-context-interpretation-pass`.

  Input:

  - `tmp/wifi/v1654-xbl-context-probe-live/manifest.json`;
  - source decision: `v1654-xbl-context-probe-live-pass`;
  - total redacted records: `326`;
  - cross-slot duplicate digest groups: `96`.

  Interpretation:

  - XBL remains the highest-yield bootloader-side artifact for SDX50M power
    context.  Both slots contain PMIC/PON/SDX/RPMh/AOP/PCIe-class records in
    the V1652-approved windows.
  - The early PON windows remain relevant because the redacted record set
    includes SDX, PON, PS_HOLD, PMIC, and VDD token classes.
  - Dense RPMh/AOP/PMIC/PCIe clusters are likely boot-resource vocabulary or
    nearby boot code/data context, but V1655 still does not identify a concrete
    register, GPIO, GDSC, rail, or PMIC write target.
  - Slot-local deltas remain potentially useful, especially because xbl_b adds
    GPIO-token records, but they are not causal without Android-good vs
    native-fail linkage.

  Decision: V1655 does not authorize direct PMIC/GPIO/GDSC/PCI/eSoC or upper
  Wi-Fi actions.  V1656 should remain host-only and map the redacted hashes and
  context classes against Android-good boot references or public OSRC-adjacent
  metadata where possible.  Any bounded rail or PMIC mutation remains a separate
  explicit gate with a concrete target and rollback contract.

  Report:
  `docs/reports/NATIVE_INIT_V1655_XBL_CONTEXT_INTERPRETATION_2026-06-02.md`.

## V1656 XBL Reference Reconciliation (2026-06-02)

- V1656 host-only reconciliation passed as
  `v1656-xbl-reference-reconciliation-pass`.

  Input:

  - `tmp/wifi/v1655-xbl-context-interpretation/manifest.json`;
  - source decision: `v1655-xbl-context-interpretation-pass`;
  - redacted XBL records: `326`;
  - cross-slot duplicate groups: `96`.

  Reconciliation:

  - XBL is supported as an information source: it contains SDX/PON/PMIC/RPMh/AOP/
    PCIe context and helps identify ownership/context around the SDX50M power
    path.
  - XBL is not currently a native-vs-Android differential or mutation target.
    Existing reference reports keep bootloader/DTB/config parity closed; only the
    boot partition changes between native and Android rollback flows.
  - Provider/PON remains host-side closed: source and evidence show the natural
    provider path reaches the correct PON/GPIO135 sequence, but host evidence
    cannot prove whether the SDX50M main rail electrically responds.
  - Connect-side Wi-Fi remains downstream. Native still lacks MDM2AP/GPIO142
    response, RC1 L0, MHI, WLFW, BDF, FW-ready, and `wlan0`.

  Decision: stop expanding XBL unless a concrete differential appears. The next
  aligned live gate is V1657: one bounded natural-path MDM2AP observation run
  using the existing contract, with GPIO142 IRQ delta and errfatal IRQ delta as
  discriminators. No forced RC1 enumerate, fake-ONLINE/system-info spoof,
  PMIC/GPIO/GDSC writes, eSoC notify/`BOOT_DONE`, Wi-Fi HAL, scan/connect,
  credentials, DHCP/routes, or external ping.

  Report:
  `docs/reports/NATIVE_INIT_V1656_XBL_REFERENCE_RECONCILIATION_2026-06-02.md`.

## V1657 Natural-path MDM2AP Observation Handoff (2026-06-02)

- V1657 one-run rollbackable natural-path live observation passed as
  `v1657-mdm2ap-silent-natural-path`.

  Execution:

  - test image:
    `tmp/wifi/v1636-natural-path-mdm2ap-irq-summary-test-boot/boot_linux_v1636_natural_mdm2ap_irq_summary.img`;
  - rollback image: `stage3/boot_linux_v724.img`;
  - rollback result: `ok=True`;
  - post-rollback baseline: `A90 Linux init 0.9.68 (v724)`, selftest `fail=0`.

  Contract evidence:

  - `provider_trigger_seen=True`;
  - `pil_esoc_seen=True`;
  - `pon_low_seen=True` and `pon_high_seen=True`;
  - `ap2mdm_seen=True`;
  - `gpio142_irq_initial_parsed=True` and `errfatal_irq_initial_parsed=True`;
  - `gpio142_irq_delta=0`;
  - `errfatal_irq_delta=0`;
  - `timing_complete=True`, `sample_count=120`, `safety_zero=True`;
  - downstream remains absent: `pcie_rc1_transition_seen=0`, `mhi_bus_max=0`,
    `wlfw_kmsg_max=0`, `wlan0_seen=0`.

  Interpretation: the clean natural provider/PON/AP2MDM path ran and the modem
  stayed silent on MDM2AP/GPIO142 with complete IRQ-delta evidence.  This removes
  the forced-RC1 contamination caveat and fixes the current lower blocker at
  `mdm2ap-silent-natural-path`.

  Stop condition: do not run more timing/window variants and do not autonomously
  enter modem-rail/PMIC write gates.  The next step toward Wi-Fi bring-up is a
  separate explicit bounded rail/PMIC hypothesis gate with concrete target,
  rollback contract, and no Wi-Fi HAL/scan/connect/credentials/DHCP/routes/
  external ping until lower readiness progresses.

  Report:
  `docs/reports/NATIVE_INIT_V1657_NATURAL_PATH_MDM2AP_OBSERVATION_HANDOFF_2026-06-02.md`.

## V1658 Post-MDM2AP Silence Next-Gate Selector (2026-06-02)

- V1658 host-only next-gate selector passed as
  `v1658-select-android-good-rail-reference-next`.

  Inputs:

  - V1657 clean natural-path label: `v1657-mdm2ap-silent-natural-path`;
  - V1641 rail/control inventory: no safe live write target;
  - V1642 SDX50M power owner classifier: suspected main-rail owner is outside
    AP-native eSoC/provider source;
  - V1656 XBL reconciliation: XBL is useful owner/context evidence but not a
    direct native-vs-Android differential or write target;
  - V1555 Android-good minimal trace reference: Android can reach BDF,
    FW-ready, and `wlan0` under a lower-impact observer.

  Gate decision:

  - reject repeated natural-path timing/window variants;
  - reject forced RC1 enumerate / pci-msm case writes;
  - reject fake ONLINE / system-info spoof;
  - reject direct PMIC/GPIO/GDSC writes for now because no named owner,
    voltage/sequence constraint, or rollbackable AP-native write surface exists;
  - select Android-good rail/reference capture as the next non-mutating gate.

  V1659 should be source/build-only first: design a minimal Android-good
  rollbackable reference handoff that preserves the good lower Wi-Fi path while
  capturing read-only regulator/PMIC/GPIO/IRQ summaries around esoc0/provider
  trigger and `wlan0` creation.  It must still avoid PMIC/GPIO/GDSC writes, PCI
  rescan, platform bind/unbind, eSoC notify/`BOOT_DONE`, native Wi-Fi HAL,
  scan/connect, credentials, DHCP/routes, and external ping.  Rollback must
  restore `stage3/boot_linux_v724.img` and verify native selftest `fail=0`.

  Report:
  `docs/reports/NATIVE_INIT_V1658_POST_MDM2AP_SILENCE_NEXT_GATE_2026-06-02.md`.

## V1659 Android-good vs Native Power Diff Plan (2026-06-02)

- V1659 source/build-only plan passed as
  `v1659-android-native-power-diff-plan-ready`.

  Rationale:

  - V1657 fixed the native lower blocker at clean natural-path
    `mdm2ap-silent-natural-path`;
  - the fixed contract now requires the same observables on both sides:
    Android-good and native natural path;
  - V1555 proves Android can reach BDF, FW-ready, and `wlan0` under a
    lower-impact GPIO/IRQ observer;
  - V1514 proves broad `clk_summary` reads can overrun critical timing, so the
    diff must use full `regulator_summary` snapshots plus targeted named clocks
    only.

  Execution split:

  - V1660: Android-good source/build-only then rollbackable handoff using the
    V1521/V1555 Magisk post-fs-data engine, with full regulator snapshots and
    targeted clock reads;
  - V1661: native source/build-only then rollbackable natural-path handoff using
    the V1657 PM-first route with the same observables;
  - V1662: host-only diff classifier that emits exactly one fixed label:
    `power-vote-gap`, `sequence-gap`, or `full-power-parity-hardware-wall`.

  Hard stops remain unchanged: no PMIC/GPIO/GDSC writes, forced RC1/case write,
  fake ONLINE/system-info spoof, eSoC notify/`BOOT_DONE`, PCI rescan, platform
  bind/unbind, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external
  ping.  No autonomous write gate follows any label.

  Report:
  `docs/reports/NATIVE_INIT_V1659_ANDROID_NATIVE_POWER_DIFF_PLAN_2026-06-02.md`.

---

## NEXT GATE after V1657 (2026-06-02) — Android vs native POWER/SEQUENCE diff (read-only)

V1657 confirmed `mdm2ap-silent-natural-path` (PON low→high fired, GPIO135 assert,
GPIO142/errfatal IRQ = 0 on the clean natural path). XBL track (V1643–V1656) was
read-only and hit the forecast dead-end: SDX/PON/PMIC context tokens but NO
concrete rail/register owner (V1655). Rail inventory (V1641): SDX50M main rail
"not identified on disk." ⇒ a write gate has no target yet.

**Next gate is fixed by contract**:
`docs/reports/ESOC_ANDROID_NATIVE_POWER_DIFF_CONTRACT_2026-06-02.md`.
- Last AP-side read-only check before any write is justified.
- Capture SAME observables on Android-good (V1521/V1555 Magisk post-fs-data
  handoff) AND native (V1657 natural PM-first route), SAME powerup window
  (esoc0 get → past mdm_subsys_powerup), then host-only diff.
- Observables: regulator_summary full + targeted named clocks (NOT full
  clk_summary — V1514 overrun) + subsys0/subsys9 bring-up sequence + GPIO/IRQ.
- Labels: `power-vote-gap` (found a rail/clock Android has, native lacks → STOP,
  hand back for separately-authorized targeted write) / `sequence-gap` (route fix)
  / `full-power-parity-hardware-wall` (terminal PASS — AP-side fully at parity,
  cause is modem-side PMIC below AP control; STOP, no write, Wi-Fi via Android
  only).
- Honest limit: SDX50M's own modem-side rail is NOT in the AP regulator tree, so
  if that's the blocker this diff reads `full-power-parity`. Both outcomes are
  decision-useful.
- ONE Android + ONE native + ONE diff sets the label. NO timing/window variants.
  NO autonomous write gate from any label.

## V1660 Android-good Power Diff Reference (2026-06-02)

- V1660 rollbackable Android-good handoff passed as
  `v1660-android-good-power-diff-reference-trace-opaque-pass`.

  Result:

  - Android lower path reached BDF, FW-ready, and `wlan0`;
  - native rollback restored `stage3/boot_linux_v724.img`;
  - native `selftest` returned `fail=0`;
  - captured 39 full `regulator_summary` snapshots;
  - captured 39 targeted named-clock snapshots without reading full
    `clk_summary`;
  - captured 39 subsystem sequence snapshots;
  - pre/post `esoc0` and pre/post `wlan0` power windows are present for
    regulator, clock, and subsystem snapshots.

  GPIO/IRQ tracefs targets were opaque in this Android-good run, but the lower
  Android success path and read-only power/clock/subsystem snapshots were
  captured.  Do not rerun timing/window variants.  The next required unit is
  the matching V1661 native natural-path capture with the same observables,
  then V1662 host-only diff.

  Report:
  `docs/reports/NATIVE_INIT_V1660_ANDROID_GOOD_POWER_DIFF_REFERENCE_2026-06-02.md`.
