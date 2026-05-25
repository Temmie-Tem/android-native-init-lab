# mdm3 / ext-sdx50m / esoc bring-up research

Date: 2026-05-25
Context: V849 wchan confirmed `mdm_subsys_powerup` D-state block; this document records
all supporting research conducted on the same date.

---

## 1. 배경

SM-A908N (r3q, SM8250) 기기에서 QCA6390 Wi-Fi를 native Linux init에서 bring-up하려면
SDX50M 내장 모뎀(mdm3, `qcom,ext-sdx50m`)이 ONLINE 상태에 도달해야 한다.
WLFW service 69는 SDX50M 위에서 동작하며, ICNSS는 service 69가 QRTR에 나타날 때
`wlfw_new_server()`를 통해 초기화된다.

현재 블로커: `subsys_esoc0` char-device open 시 holder process가
`mdm_subsys_powerup`에서 D-state(uninterruptible sleep)로 블록됨.

---

## 2. esoc/ext-sdx50m 드라이버 소스 소재

### 2-1. Samsung OSRC에 없는 파일

Samsung SM-A908N OSRC (`SM-A908N_KOR_12_Opensource.zip`)에는 esoc **헤더만** 포함된다.

| 파일 | OSRC 포함 여부 |
|---|---|
| `include/linux/esoc_client.h` | ✓ 포함 |
| `include/uapi/linux/esoc_ctrl.h` | ✓ 포함 |
| `drivers/esoc/esoc-mdm-4x.c` | ✗ 없음 (proprietary) |
| `drivers/esoc/esoc-mdm-pon.c` | ✗ 없음 (proprietary) |
| `drivers/esoc/esoc-mdm-drv.c` | ✗ 없음 (proprietary) |

이 드라이버들은 Qualcomm proprietary closed-source 모듈로 기기 binary에 포함된다.

### 2-2. 공개 소스 위치

동일 구현이 아래 공개 커널 트리에 존재한다.

| 트리 | 경로 | 비고 |
|---|---|---|
| kimocoder/kernel_sm8150 (msm-4.14.190) | `drivers/esoc/esoc-mdm-4x.c` | SM8150 기반, SDX50M 동일 |
| kimocoder/kernel_sm8150 (msm-4.14.190) | `drivers/esoc/esoc-mdm-pon.c` | powerup 시퀀스 |
| CodeLinaro msm-4.14 | `drivers/esoc/` | upstream Qualcomm |
| LineageOS android_kernel_samsung_sm8250 | `drivers/esoc/` | Samsung 패치 포함 |

**출처:**
- https://github.com/kimocoder/kernel_sm8150/blob/msm-4.14.190/drivers/esoc/esoc-mdm-4x.c
- https://github.com/kimocoder/kernel_sm8150/blob/msm-4.14.190/drivers/esoc/esoc-mdm-pon.c
- https://git.codelinaro.org/clo/la/kernel/msm-4.14/-/tree/a8cd8852ce618dfe03fc0e082677e06100d6f182/drivers/esoc
- https://github.com/LineageOS/android_kernel_samsung_sm8250

---

## 3. r3q (SM-A908N) DTS GPIO 할당 확정

OSRC 내 `sm8150-sec-r3q-kor-overlay-r00.dts` (line 3813–3844) 기준.

| DTS property | 값 | 실제 GPIO |
|---|---|---|
| `qcom,ap2mdm-status-gpio` | `<&tlmm 0x87>` | **GPIO 135** — AP → MDM alive signal |
| `qcom,mdm2ap-status-gpio` | `<&tlmm 0x8e>` | **GPIO 142** — MDM → AP ready signal |
| `qcom,ap2mdm-errfatal-gpio` | `<&tlmm 0x8d>` | GPIO 141 — AP → MDM error fatal |
| `qcom,mdm2ap-errfatal-gpio` | `<&tlmm 0x35>` | GPIO 53 — MDM → AP error fatal |
| `qcom,ap2mdm-soft-reset-gpio` | `<&pm8150l_gpios 0x9>` | **PMIC pm8150l GPIO 9** — soft reset / PON |

**출처:** 로컬 OSRC
`kernel_build/SM-A908N_KOR_12_Opensource/Kernel/arch/arm64/boot/dts/samsung/renovation/sm8150-sec-r3q-kor-overlay-r00.dts`

---

## 4. ext-sdx50m powerup 시퀀스 분석

### 4-1. `mdm4x_do_first_power_on()` (esoc-mdm-pon.c)

```c
static int mdm4x_do_first_power_on(struct mdm_ctrl *mdm)
{
    mdm_toggle_soft_reset(mdm, false);   // PMIC pm8150l GPIO 9 → LOW (de-assert)
    msleep(150);
    gpio_direction_output(MDM_GPIO(mdm, AP2MDM_STATUS), 1);  // GPIO 135 → HIGH
    msleep(200);
    return 0;
    // GPIO 142 응답을 여기서 대기하지 않음 — IRQ로 비동기 처리
}
```

총 소요 시간: ~350ms. `GPIO 142 (MDM2AP_STATUS)` 응답은 함수 내부에서 직접 대기하지
않고, IRQ 핸들러(`mdm_status_change()`)로 비동기 처리한다.

### 4-2. `sdx50m_toggle_soft_reset()` (esoc-mdm-pon.c)

```c
static void sdx50m_toggle_soft_reset(struct mdm_ctrl *mdm, bool reset)
{
    if (reset) {
        gpio_direction_output(MDM_GPIO(mdm, AP2MDM_SOFT_RESET), 1);
        usleep_range(80000, 180000);  // 80~180ms
    } else {
        gpio_direction_output(MDM_GPIO(mdm, AP2MDM_SOFT_RESET), 0);
    }
}
```

`do_first_power_on`은 `reset=false`로 호출 — de-assert(0)만 한다.
**PMIC pm8150l GPIO 9에 대한 SPMI 트랜잭션이 필요하다.**

### 4-3. `wait_for_err_ready()` (subsystem_restart.c)

```c
static int wait_for_err_ready(struct subsys_device *subsys)
{
    if ((subsys->desc->generic_irq <= 0 && !subsys->desc->err_ready_irq) ||
            enable_debug == 1 || is_timeout_disabled())
        return 0;  // err_ready_irq 없으면 즉시 리턴

    ret = wait_for_completion_timeout(&subsys->err_ready,
                                      msecs_to_jiffies(10000));  // 10초 타임아웃
    ...
}
```

r3q DTS의 mdm3 노드에는 `err-ready-gpio` 속성이 없다.
→ `wait_for_err_ready()`는 **즉시 0을 리턴**한다.
→ V849 블록 위치는 `wait_for_err_ready()`가 아닌 `powerup()` 내부다.

**출처:**
- https://github.com/ianmacd/winnerx/blob/master/drivers/soc/qcom/subsystem_restart.c
- https://github.com/ianmacd/winnerx/blob/master/arch/arm64/boot/dts/qcom/sm8150-sdx50m.dtsi

---

## 5. esoc ops 구조

```c
// esoc-mdm-4x.c
static struct esoc_clink_ops mdm_cops = {
    .cmd_exe    = mdm_cmd_exe,
    .get_status = mdm_get_status,
    .get_err_fatal = mdm_get_err_fatal,
    .notify     = mdm_notify,
};

static struct mdm_ops sdx50m_ops = {
    .clink_ops  = &mdm_cops,
    .config_hw  = sdx50m_setup_hw,
    .pon_ops    = &sdx50m_pon_ops,
};

// esoc-mdm-pon.c
struct mdm_pon_ops sdx50m_pon_ops = {
    .pon         = mdm4x_do_first_power_on,
    .soft_reset  = sdx50m_toggle_soft_reset,
    .poff_force  = sdx50m_power_down,
    .cold_reset  = sdx50m_cold_reset,
    .dt_init     = mdm4x_pon_dt_init,
    .setup       = mdm4x_pon_setup,
};
```

`sdx50m_setup_hw`는 `auto-boot` 속성이 없으면 setup 시 GPIO 135를 HIGH로 올리지 않는다.
r3q mdm3 노드에 `auto-boot`가 없으므로 powerup은 명시적 `ESOC_PWR_ON` 커맨드로만 트리거된다.

---

## 6. Samsung r3q 전용 패치

공개 LineageOS sm8250 트리 기준, Samsung이 upstream esoc-mdm-4x.c에 추가한 내용:

| 패치 | 내용 | powerup 영향 |
|---|---|---|
| `CONFIG_SEC_DEBUG` 블록 | `sec_debug_level`이 낮으면 `esoc_ramdump_disable=true` | **없음** — 크래시 복구 경로만 |
| `CONFIG_DEV_RIL_BRIDGE` 블록 | RIL bridge notifier로 ramdump 동작 런타임 제어 | **없음** — 크래시 복구 경로만 |
| `qcom,esoc-skip-restart-for-mdm-crash` | `ESOC_EXE_DEBUG` 크래시 핸들러에서 soft-reset/ramdump skip | **없음** — 초기 powerup 무관 |

**결론: Samsung 전용 패치는 초기 powerup 시퀀스에 영향을 주지 않는다.**

---

## 7. MHI esoc 클라이언트 훅 (mhi_arch_qcom.c)

esoc가 power-on 이벤트를 발생시키면 MHI 클라이언트가 받는 콜백:

```c
static int mhi_arch_esoc_ops_power_on(void *priv, unsigned int flags)
{
    // PCIe RPM resume
    ret = msm_pcie_pm_control(MSM_PCIE_RESUME, pci_dev->bus->number, ...);
    // MHI 프로브
    ret = mhi_pci_probe(pci_dev, NULL);
    return ret;
}
```

이 함수는 esoc powerup **이후에** 실행된다. 현재는 esoc powerup 자체가 블록되므로
이 단계에 도달하지 않는다.

**출처:** 로컬 OSRC
`kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/bus/mhi/controllers/mhi_arch_qcom.c`

---

## 8. V849 wchan 확정 결과

```
holder wchan  : mdm_subsys_powerup
holder state  : D (disk sleep / uninterruptible)
holder stack  : mdm_subsys_powerup → __subsystem_get → subsys_device_open
```

`mdm_subsys_powerup`은 OSRC에 없는 proprietary 심볼이다.
D-state는 단순 `msleep()`이 아닌 커널 자원 대기(completion, mutex, IRQ 등)를 의미한다.

**블록 후보 (우선순위 순):**
1. **PMIC pm8150l GPIO 9 SPMI 트랜잭션** — native init에서 pm8150l이 완전히 초기화되지 않았을 가능성
2. **GPIO 142 (MDM2AP_STATUS) IRQ 대기** — SDX50M이 부팅하지 않아 GPIO 142가 HIGH가 되지 않음
3. **SUBSYS_BEFORE_POWERUP notifier 체인** — powerup() 진입 전 다른 서브시스템 notifier 블록

---

## 9. ath11k vs QCACLD — 아키텍처 비교

| 항목 | ath11k (mainline) | QCACLD/ICNSS (SM-A908N) |
|---|---|---|
| QCA6390 연결 방식 | PCIe-attached | **SNOC-attached** (`18800000.qcom,icnss`) |
| SDX50M/esoc 의존성 | **없음** — PCIe MHI 직접 FW 로드 | **필수** — service 69 QRTR 의존 |
| SM8250 기기 동작 사례 | OnePlus 8, Xiaomi Pad 5 Pro 등 | SM-A908N 전용 경로 |
| SM-A908N 적용 가능성 | **불가** — PCIe 열거 없음 | 현재 연구 경로 |

SM8250 mainline(sm8250-mainline GitLab)에서 QCA6390 ath11k Wi-Fi가 동작하지만,
SM-A908N은 SNOC-attached라 해당 경로가 존재하지 않는다.

**출처:**
- https://wireless.docs.kernel.org/en/latest/en/users/drivers/ath11k.html
- https://gitlab.com/sm8250-mainline/linux/-/merge_requests/8
- http://lists.infradead.org/pipermail/ath11k/2020-August/000112.html

---

## 10. 비Android ext-sdx50m bring-up 공개 사례

**없음.** 검색 범위: OpenWRT, postmarketOS, Yocto, mainline Linux 커뮤니티.

`subsys_esoc0` / esoc 서브시스템을 통한 SDX50M bring-up은 Android HLOS 커널 코드에만
문서화되어 있으며, 비Android 환경에서 시도하거나 성공한 공개 사례가 존재하지 않는다.

**이 프로젝트는 해당 경로의 최초 공개 연구 사례로 기록된다.**

---

## 11. 다음 단계 (V850+)

| 우선순위 | 작업 | 목적 |
|---|---|---|
| 1 | `/proc/kallsyms`에서 `mdm_subsys_powerup`, `ap2mdm`, `mdm2ap` 심볼 확인 | 바이너리 구조 추정 |
| 2 | Android 부팅 중 GPIO 142 HIGH 여부 확인 | SDX50M 실제 부팅 여부 |
| 3 | `esoc-mdm-4x.c` 공개 소스 + kallsyms cross-reference | Samsung delta 추정 |
| 4 | PMIC pm8150l GPIO 9 초기화 상태 확인 | 블록 후보 1번 검증 |
| 5 | GPIO 135 userspace 직접 조작 가능성 검토 | esoc 드라이버 우회 경로 |

GPIO 135를 userspace에서 직접 HIGH로 올리면 SDX50M이 반응할 가능성이 있다.
단, GPIO export 및 명시적 승인 필요.

---

## 12. V853 Android actor evidence

V853 Android handoff에서 실제 Android userspace actor가 확인됐다.

| Node | Android holder |
|---|---|
| `/dev/esoc-0` | `mdm_helper`, child `ks` (`u:r:vendor_mdm_helper:s0`) |
| `/dev/subsys_esoc0` | `pm-service` (`u:r:vendor_per_mgr:s0`) |
| `/dev/subsys_modem` | `pm-service` (`u:r:vendor_per_mgr:s0`) |

ueventd/SELinux 계약:

| Surface | Android rule/context |
|---|---|
| `/dev/esoc-0` | `0660 root:radio`, `vendor_esoc_device` |
| `/dev/subsys_*` | `0640 system:system`, `vendor_ssr_device` |
| `/vendor/bin/mdm_helper`, `/vendor/bin/ks` | `vendor_mdm_helper_exec` |
| `/vendor/bin/pm-service` | `vendor_per_mgr_exec` |

이 결과는 native의 단일 `/dev/subsys_esoc0` 수동 open 재시도가 충분하지 않다는
점을 보여준다. 다음 단계는 GPIO 직접 조작이 아니라 Android actor 계약의 최소
native equivalent를 host-only로 분류하는 것이다.

V854 host-only 분류 결과, 다음 live gate는 actor replay가 아니라
Android node/ueventd parity preflight로 고정됐다. 즉 `/dev/esoc-0`,
`/dev/subsys_esoc0`, `/dev/subsys_modem`의 major/minor/mode/owner를 먼저
native에서 안전하게 맞추고 cleanup 가능한지 검증한 뒤에야 `pm-service` 또는
`mdm_helper` start-only를 검토한다.

V855 live 결과 이 node parity는 통과했다. native에서 `esoc` major `484`,
`subsys` major `236`, `subsys_esoc0=236:9`, `subsys_modem=236:0`, eSoC
`mdm-4x/qcom,ext-sdx50m/PCIe/SDX50M` 표면이 확인됐고, 세 node를 Android
metadata에 맞춰 생성한 뒤 holder 없이 cleanup 가능했다. 따라서 다음 gate는
`pm-service` start-only이며, 아직 `mdm_helper`/`ks`, raw eSoC ioctl, GPIO
write, HAL/connect는 이르다.

V856 live 결과 `pm-service`/`pm-proxy` start-only는 안전하게 관찰됐다.
native는 `mountsystem ro`, V401 `selinuxfs`, service-manager 3종,
private property root, private node parity를 갖춘 상태에서
`pm-service`와 `pm-proxy`를 실행할 수 있었다. 그러나 Android V853과 달리
`pm-service`가 `/dev/subsys_esoc0` 또는 `/dev/subsys_modem` fd를 보유한
증거는 나오지 않았다. 대신 property shim evidence에서
`vendor.peripheral.SDX50M.state=OFFLINE` 및
`vendor.peripheral.modem.state=OFFLINE`은 허용됐지만
`vendor.peripheral.shutdown_critical_list` 값(`SDX50M `, `SDX50M modem `)은
차단됐다. 따라서 다음 gate는 `mdm_helper`/`ks`가 아니라
PeripheralManager property contract를 좁게 재현하는 V857이다.

V857 live 결과 shutdown-critical-list property contract는 닫혔다.
`vendor.peripheral.shutdown_critical_list=SDX50M ` 및
`vendor.peripheral.shutdown_critical_list=SDX50M modem ` 요청이 모두
성공했지만, `pm-service`는 여전히 `/dev/subsys_esoc0` 또는
`/dev/subsys_modem` fd hold를 증명하지 못했다. 새로 남은 갭은
`debug.ld.app.pm-service`, `arm64.memtag.process.pm-service`,
`persist.log.tag.PerMgrSrv`, `log.tag.PerMgrSrv` 및 `pm-proxy` 대응 키의
property context/read 입력이다. 따라서 V858은 `mdm_helper`가 아니라
Android/native property-info context delta classifier가 되어야 한다.

---

## 참고 문헌

| 출처 | 내용 |
|---|---|
| https://github.com/kimocoder/kernel_sm8150/blob/msm-4.14.190/drivers/esoc/esoc-mdm-4x.c | esoc-mdm-4x.c 전체 소스 |
| https://github.com/kimocoder/kernel_sm8150/blob/msm-4.14.190/drivers/esoc/esoc-mdm-pon.c | powerup 시퀀스 |
| https://github.com/ianmacd/winnerx/blob/master/drivers/soc/qcom/subsystem_restart.c | subsys_start / wait_for_err_ready |
| https://github.com/ianmacd/winnerx/blob/master/arch/arm64/boot/dts/qcom/sm8150-sdx50m.dtsi | SM8150 sdx50m DTS 참조 |
| https://git.codelinaro.org/clo/la/kernel/msm-4.14/-/tree/a8cd8852ce618dfe03fc0e082677e06100d6f182/drivers/esoc | CodeLinaro upstream esoc |
| https://github.com/LineageOS/android_kernel_samsung_sm8250 | Samsung SM8250 LineageOS 트리 |
| https://wireless.docs.kernel.org/en/latest/en/users/drivers/ath11k.html | ath11k 공식 문서 |
| https://gitlab.com/sm8250-mainline/linux/-/merge_requests/8 | SM8250 mainline QCA6390 ath11k MR |
| http://lists.infradead.org/pipermail/ath11k/2020-August/000112.html | ath11k QCA6390 MHI 등록 패치 |
| 로컬 OSRC `sm8150-sec-r3q-kor-overlay-r00.dts` | r3q GPIO 할당 확정 |
| 로컬 OSRC `mhi_arch_qcom.c` | MHI esoc 클라이언트 훅 |
| V849 evidence `tmp/wifi/v849-subsys-esoc0-wait-state-sampler/` | wchan D-state 확정 |

## 13. V858/V859 property delta outcome

V858 closed the immediate V857 property-context gap. The following eight
`pm-service`/`pm-proxy` keys were added to the private property layout and
deployed into the versioned private root:

- `debug.ld.app.pm-service`
- `arm64.memtag.process.pm-service`
- `persist.log.tag.PerMgrSrv`
- `log.tag.PerMgrSrv`
- `debug.ld.app.pm-proxy`
- `arm64.memtag.process.pm-proxy`
- `persist.log.tag.PerMgrProxy`
- `log.tag.PerMgrProxy`

V859 then reran the bounded `pm-service`/`pm-proxy` start-only gate without
helper redeploy. Result: `v858_target_remaining=[]`, so the target V857 denials
were removed. However `pm-service` still did not hold `/dev/subsys_esoc0` or
`/dev/subsys_modem`.

The next exposed gap is a broader service-manager/log property set:

| Key | Count |
|---|---:|
| `persist.log.tag.vndservicemanager` | 104 |
| `log.tag.vndservicemanager` | 104 |
| `persist.log.tag.ServiceManager` | 102 |
| `log.tag.ServiceManager` | 102 |
| `debug.ld.app.vndservicemanager` | 20 |
| `persist.log.tag.PerMgrLib` | 4 |
| `log.tag.PerMgrLib` | 4 |
| `arm64.memtag.process.vndservicemanager` | 2 |

Interpretation: the current path is still property-runtime completeness below
PeripheralManager lifetime, not `mdm_helper`/`ks` or GPIO/eSoC writes. V860
should produce a superset property delta that preserves the V858 keys and adds
these newly exposed keys, then rerun the same bounded replay.

## 14. V860 property superset outcome

V860 produced and deployed that superset. The host layout combined:

- the 8 V858 `pm-service`/`pm-proxy` keys,
- the 8 V859 newly exposed `vndservicemanager`/`ServiceManager`/`PerMgrLib`
  keys,
- the 20 V677 residual keys as a regression guard.

The resulting private property model has `131` properties and `21` contexts.
The incremental deploy updated only the existing versioned private V535
property root and verified device-side hashes for all selected files.

Bounded replay result: `v860-property-clean-no-subsys-hold`.

| Check | Result |
|---|---|
| property denial total | `0` |
| V860 target remaining | `[]` |
| new after V860 | `[]` |
| `pm-service` holds `/dev/subsys_esoc0` | `false` |
| `pm-service` holds `/dev/subsys_modem` | `false` |

Interpretation: the active blocker moved past private property coverage. The
next gate is V861 lifetime/provider-input classification for `pm-service` and
`pm-proxy`: capture exit status, stdout/stderr, provider registration, and fd
timing under the same node parity before considering `mdm_helper`/`ks`.

## 15. V861 domain parity outcome

V861 added helper-side Android default exec-context mappings for
`/vendor/bin/pm-service` and `/vendor/bin/pm-proxy`:

| Target | Requested context |
|---|---|
| `/vendor/bin/pm-service` | `u:r:vendor_per_mgr:s0` |
| `/vendor/bin/pm-proxy` | `u:r:vendor_per_mgr:s0` |

Bounded replay result: `v861-exec-target-accepted-current-kernel-no-subsys-hold`.

| Check | Result |
|---|---|
| property denial total | `0` |
| `pm-service` exec target accepted | `true` |
| `pm-proxy` exec target accepted | `true` |
| `pm-service` runtime `attr/current` | `kernel` |
| `pm-proxy` runtime `attr/current` | `kernel` |
| `pm-service` exit code | `0` |
| `pm-proxy` exit code | `1` |
| `pm-service` holds `/dev/subsys_esoc0` | `false` |
| `pm-service` holds `/dev/subsys_modem` | `false` |

Interpretation: V861 fixed the helper-side missing target mapping, but direct
exec still does not behave like Android init-managed `vendor.per_mgr`. The next
gate should classify the Android init service contract for `vendor.per_mgr`,
`vendor.per_proxy`, and `vendor.per_proxy_helper` before `mdm_helper`/`ks`.

## 16. V862 Android init service-contract outcome

V862 classified the Android init contract that V861 direct exec still lacks.

Host-only result: `v862-init-contract-classified-pm-proxy-helper-content-needed`.

| Item | Android contract / evidence |
|---|---|
| `vendor.per_mgr` | `/vendor/bin/pm-service`, `class core`, `user system`, `group system`, `ioprio rt 4` |
| `vendor.per_proxy` | `/vendor/bin/pm-proxy`, `class core`, `user system`, `group system`, `disabled` |
| per-proxy lifecycle | `on property:init.svc.vendor.per_mgr=running` starts `vendor.per_proxy` |
| shutdown lifecycle | `on property:sys.shutdown.requested=*` stops `vendor.per_proxy` |
| `vendor.per_proxy_helper` | V210 lists `pm_proxy_helper.rc`; V853 dmesg shows Android starts `vendor.per_proxy_helper` |

Open native gaps:

- helper has no `ioprio rt 4` model for `vendor.per_mgr`;
- helper starts `per_proxy` directly instead of through the Android
  `init.svc.vendor.per_mgr=running` lifecycle;
- helper does not model shutdown stop semantics;
- `pm_proxy_helper.rc` content is not captured yet;
- V861 runtime domains still stayed `kernel` and no subsystem fd hold appeared.

Next gate: V863 should capture `/vendor/etc/init/pm_proxy_helper.rc` read-only
and classify `vendor.per_proxy_helper` before any `mdm_helper`/`ks`, eSoC ioctl,
GPIO/sysfs write, Wi-Fi HAL, scan/connect, DHCP, or external ping.

## 17. V863 pm_proxy_helper.rc capture outcome

V863 captured `/vendor/etc/init/pm_proxy_helper.rc` from the live vendor
partition using a temporary ext4 `ro,noload` mount.

Result: `v863-pm-proxy-helper-contract-captured`.

Important runtime correction: current `sda29` major/minor is `259:13`; older
`259:22` evidence is stale and must not be hardcoded.

Captured contract:

```text
service vendor.per_proxy_helper /vendor/bin/pm_proxy_helper
    class core
    user system
    group system
    disabled
    oneshot

on post-fs-data
    start vendor.per_proxy_helper
```

Cleanup passed and post-run selftest passed. No daemon start, `mdm_helper`,
`ks`, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, raw eSoC
ioctl, GPIO/sysfs/debugfs/subsystem write, module load, boot image write, or
partition write occurred.

Next gate: V864 should classify helper support for the complete
PeripheralManager init contract before starting any new actor:

- `vendor.per_proxy_helper` post-fs-data oneshot;
- `vendor.per_mgr` `ioprio rt 4`;
- `vendor.per_proxy` property-start and shutdown-stop lifecycle;
- V861 runtime domain still reading `kernel`.

## 18. V864+ next candidate selection

V863 changes the immediate path. The next useful work is no longer another
`mdm_helper` replay or direct eSoC/sysfs attempt. The evidence chain now points
at Android init contract parity for the Qualcomm PeripheralManager stack:

- V849 proved raw `/dev/subsys_esoc0` open blocks inside proprietary
  `mdm_subsys_powerup`.
- V853 proved Android has distinct actors for `/dev/subsys_esoc0`,
  `/dev/subsys_modem`, and `/dev/esoc-0`.
- V856-V861 proved direct `pm-service`/`pm-proxy` execution is safe but still
  not Android-equivalent and does not hold subsystem fds.
- V862/V863 proved Android starts a third actor,
  `vendor.per_proxy_helper /vendor/bin/pm_proxy_helper`, as a disabled oneshot
  from `post-fs-data`.

External reference checks support this direction:

- Android init defines service identity, class, disabled/oneshot semantics,
  shutdown behavior, and property triggers; therefore modelling
  `init.svc.vendor.per_mgr=running` is not optional if the goal is Android init
  parity.
- AOSP/Pixel Qualcomm device init files use the same pattern:
  `vendor.per_mgr /vendor/bin/pm-service` with `user system`, `group system`,
  `ioprio rt 4`, a disabled `/vendor/bin/pm-proxy`, and a property trigger
  that starts the proxy when `vendor.per_mgr` becomes running.
- Linux `ioprio_set(2)` requires explicit syscall handling and may fail with
  privilege errors for realtime I/O priority; a live runner must record the
  exact result instead of assuming `ioprio rt 4` was applied.

Selected next candidates:

| Version | Candidate | Type | Purpose | Hard gates |
|---|---|---|---|---|
| V864 | PeripheralManager helper-support classifier | host-only | Compare V861/V862/V863 evidence against current helper source and decide the exact implementation gap. | no device contact |
| V865 | Init-contract wrapper implementation | source/build only | Add model support for `pm_proxy_helper`, `ioprio rt 4`, `init.svc.vendor.per_mgr=running`, proxy start/stop lifecycle, child fd/domain capture, and fail-closed guards. | no helper deploy, no daemon start |
| V866 | Helper v134 deploy preflight/live deploy | deploy only | Verify the new helper binary, checksum, mode list, and device deployment without starting actors. | no daemon start |
| V867 | PeripheralManager contract start-only proof | bounded live | Start only `pm_proxy_helper` oneshot plus init-equivalent `per_mgr`/`per_proxy` lifecycle under node parity and capture fd holds, runtime domain, ioprio result, dmesg, and cleanup. | no `mdm_helper`, no `ks`, no HAL, no Wi-Fi bring-up |
| V868 | Post-contract blocker classifier | host-only/live read-only if needed | If V867 still has no subsystem fd hold, separate SELinux transition gap from missing PeripheralManager inputs; if fds appear, classify `mdm3`/WLFW movement. | no new actor escalation |
| V869 | PM-gated `mdm_helper` candidate | gated live only if V867/V868 pass | Start `mdm_helper`/`ks` only after PM stack parity proves stable and useful. | no Wi-Fi HAL, no scan/connect, no DHCP/routes, no external ping |

Primary decision: **V864 is the immediate next cycle.** It should not start
anything. It should produce a concrete implementation checklist for V865 and
block V867 until helper support is explicitly proven.
