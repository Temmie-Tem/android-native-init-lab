# esoc / PeripheralManager / mdm3 bring-up 메커니즘 연구

Date: 2026-05-25
Context: V866 helper v134 배포 완료, V867 PeripheralManager live 시도 준비 중.
이 문서는 V867+ 방향 결정을 위해 수행한 3개 병렬 웹서치의 결과를 기록한다.

---

## 1. 배경 및 목적

V849에서 `/dev/subsys_esoc0` open이 `mdm_subsys_powerup` D-state에서 블록됨이 확인됐다.
V850–V866은 PeripheralManager (`vendor.per_mgr`) 경로를 통해 mdm3를 bring-up하는 방법을
분류했다. 이 문서는 그 과정에서 확인된 세 가지 핵심 질문에 대한 연구 결과를 기록한다:

1. `pm_proxy_helper`가 실제로 무엇을 하는가
2. `vendor.per_mgr` / `vendor.per_proxy` 서비스 계약은 무엇인가
3. `ESOC_PWR_ON` ioctl 경로와 `mdm-helper`의 역할은 무엇인가

---

## 2. pm_proxy_helper 실체

### 2-1. pm_proxy_helper = mdm_helper (다른 이름으로 실행)

`pm_proxy_helper`는 독립적인 바이너리가 아니다. `/vendor/bin/pm_proxy_helper`는
`/vendor/bin/mdm_helper`의 심볼릭 링크 또는 동일 바이너리이며, `argv[0]`의 basename을
검사해 다른 코드 경로를 실행한다:

```c
// mdm_helper.c (David112x/android_vendor_qcom_proprietary)
if (!strcmp(basename(argv[0]), "mdm_helper_proxy"))
    mdm_routine = &modem_proxy_routine;
else
    mdm_routine = &modem_state_machine;
```

`modem_proxy_routine`이 실행하는 것:

```c
static void* modem_proxy_routine(void *arg) {
    snprintf(powerup_node, sizeof(powerup_node),
             "/dev/subsys_%s", dev->esoc_node);  // "/dev/subsys_esoc0"
    fd = open(powerup_node, O_RDONLY);            // 이 open()이 mdm3 bring-up을 트리거
    do { sleep(50000); } while(1);               // fd 보유 → subsystem refcount 유지
}
```

**pm_proxy_helper가 하는 일의 전부**: `/dev/subsys_esoc0`를 열고 영원히 들고 있는 것.

### 2-2. open()이 bring-up을 트리거하는 이유

`/dev/subsys_esoc0` open() → 커널 `subsys_device_open()` → `subsystem_get_with_fwname("esoc0")` → `subsys_start(esoc0)` → `mdm_subsys_powerup()` 호출.

fd를 열어두는 것이 subsystem refcount를 증가시켜 mdm3가 ONLINE 상태를 유지하게 한다.
fd를 닫으면 refcount가 0으로 떨어져 mdm3가 다시 OFFLINING으로 돌아간다.

### 2-3. 커널의 pm_proxy_helper 특별 처리

Samsung `subsystem_restart.c`에 pm_proxy_helper를 위한 특별 예외 코드가 있다:

```c
// subsystem_restart.c (ianmacd/winnerx)
subsys_d = find_subsys_device(subsys->desc->poff_depends_on);
if (subsys_d && strncmp("pm_proxy_helper", current->comm,
                         strlen("pm_proxy_helper")))
    subsystem_put(subsys_d);
```

의미: modem(mss) 서브시스템이 종료될 때 커널은 보통 `poff_depends_on = "esoc0"` 체인으로
esoc0도 연쇄 종료한다. 그러나 **종료 프로세스가 `pm_proxy_helper`인 경우 이 체인 종료를
건너뛴다**. 이는 RIL이 재투표하기 전에 esoc0가 종료되는 race condition을 방지하기 위한
Samsung 패치다.

**출처:**
- https://github.com/David112x/android_vendor_qcom_proprietary/tree/master/mdm-helper
- https://github.com/ianmacd/winnerx/blob/master/drivers/soc/qcom/subsystem_restart.c

---

## 3. V849 D-state 블록의 정확한 원인

### 3-1. req_eng_wait completion

`mdm_subsys_powerup()` 내부 (`esoc-mdm-drv.c`):

```c
static int mdm_subsys_powerup(const struct subsys_desc *desc)
{
    ...
    if (!esoc_req_eng_enabled(esoc_clink)) {
        dev_dbg(..., "Wait for req eng registration\n");
        wait_for_completion(&mdm_drv->req_eng_wait);  // ← V849 D-state 원인
    }
    ...
    // REQ_ENG 등록 후에야 GPIO powerup 진행
}
```

**REQ_ENG가 등록되지 않으면 영원히 대기한다.** V847, V849 모두 REQ_ENG 없이
`/dev/subsys_esoc0`를 열었으므로 동일하게 블록됐다.

### 3-2. REQ_ENG 등록 방법

`/dev/esoc-0` (하이픈, underscore 아님) char device에서 ioctl로 등록:

```c
// esoc_ctrl.h (uapi header)
#define ESOC_REG_REQ_ENG  _IO(ESOC_CODE, 7)  // REQ_ENG 등록
#define ESOC_REG_CMD_ENG  _IO(ESOC_CODE, 8)  // CMD_ENG 등록
```

A90 로컬 Samsung OSRC 기준 값이다. 일부 공개 mdm-helper 예제의 ioctl 번호와
다를 수 있으므로, native helper 구현은 반드시
`kernel_build/SM-A908N_KOR_12_Opensource/Kernel/include/uapi/linux/esoc_ctrl.h`
의 `ESOC_CODE`, `ESOC_REG_REQ_ENG`, `ESOC_REG_CMD_ENG` 값을 기준으로 한다.

REQ_ENG 등록 시 `mdm_drv->req_eng_wait` completion이 시그널되고,
`mdm_subsys_powerup`의 D-state 블록이 해제된다.

**출처:**
- https://git.codelinaro.org/clo/la/kernel/msm-4.4/-/blob/LA.UM.6.1.1.c25-03600-sdm660.0/drivers/esoc/esoc-mdm-drv.c
- 로컬 OSRC: `kernel_build/.../include/uapi/linux/esoc_ctrl.h`

---

## 4. esoc ioctl 인터페이스 전체

`/dev/esoc_ctrl.h` (로컬 OSRC 확인):

| ioctl | 방향 | 목적 |
|---|---|---|
| `ESOC_CMD_EXE` | write (u32) | `enum esoc_cmd` 커맨드 실행 |
| `ESOC_WAIT_FOR_REQ` | read (u32) | 커널 요청 대기 (블로킹) |
| `ESOC_NOTIFY` | write (u32) | `enum esoc_notify` 전송 |
| `ESOC_GET_STATUS` | read | clink 상태 읽기 |
| `ESOC_GET_ERR_FATAL` | read | error-fatal 플래그 읽기 |
| `ESOC_WAIT_FOR_CRASH` | read | crash/reset 이벤트 대기 |
| `ESOC_REG_REQ_ENG` | none | REQ_ENG로 등록 |
| `ESOC_REG_CMD_ENG` | none | CMD_ENG로 등록 |
| `ESOC_SET_BOOT_FAIL_ACT` | write | 부트 실패 액션 설정 |
| `ESOC_SET_N_PON_TRIES` | write | 전원 켜기 재시도 횟수 |

`ESOC_PWR_ON`은 독립 ioctl이 아니라 `enum esoc_cmd`의 값 1이며,
`ESOC_CMD_EXE`의 인자로 전달한다.

### 4-1. ESOC_CMD_EXE(ESOC_PWR_ON) 처리

```c
// esoc-mdm-4x.c
case ESOC_PWR_ON:
    gpio_set_value(MDM_GPIO(mdm, AP2MDM_ERRFATAL), 0);
    mdm_enable_irqs(mdm);
    mdm->init = 1;
    mdm_do_first_power_on(mdm);  // GPIO 135 → HIGH 등 powerup 시퀀스
    break;
```

CMD_ENG 등록 후 `ESOC_CMD_EXE(ESOC_PWR_ON)` 호출 → `mdm_cmd_exe()` → `mdm_do_first_power_on()`.

**출처:**
- https://github.com/commaai/android_kernel_comma_msm8996/blob/master/drivers/esoc/esoc-mdm-4x.c
- https://android.googlesource.com/kernel/msm/+/android-7.1.0_r0.2/drivers/esoc/esoc-mdm-4x.c

---

## 5. mdm-helper (state machine 모드) 역할

Android에서 `mdm-helper` (state machine 모드, `pm_proxy_helper`와 다름)가 하는 일:

1. `/dev/esoc-0` fd1 열기 → `ESOC_REG_CMD_ENG` 등록
2. `/dev/esoc-0` fd2 열기 → `ESOC_REG_REQ_ENG` 등록 → **req_eng_wait 해제**
3. `ESOC_CMD_EXE(ESOC_PWR_ON)` → GPIO 135 HIGH → SDX50M 부팅 시작
4. REQ_ENG 루프:
   ```
   ESOC_WAIT_FOR_REQ → ESOC_REQ_IMG 수신
   → tftp_server로 wlanmdsp.mbn 전송 (sda29)
   → ESOC_NOTIFY(ESOC_IMG_XFER_DONE / ESOC_BOOT_DONE)
   ```
5. MDM2AP_STATUS GPIO 142 HIGH → mdm3 ONLINE

`ks` (kick-start)는 ext-sdx50m에 사용되지 않는다. ks는 레거시 MDM9x25/MDM9x35
USB-attached 모뎀 전용 도구다.

**출처:**
- https://github.com/David112x/android_vendor_qcom_proprietary/tree/master/mdm-helper
- https://github.com/Bigcountry907/HTC_a13_vzw_Kernel/tree/master/vendor/qcom/proprietary/mdm-helper/esoc/mdm9k

---

## 6. /dev/esoc-0 vs /dev/subsys_esoc0 차이

| 장치 | 생성자 | 목적 | open() 동작 |
|---|---|---|---|
| `/dev/esoc-0` (하이픈) | `esoc_dev.c` (`"esoc-%d"` 포맷) | ESOC ioctl 제어 | 즉시 리턴, `esoc_uhandle` 할당 |
| `/dev/subsys_esoc0` | SSR framework | 서브시스템 restart 제어 | `subsystem_get()` 호출 → mdm3 bring-up 트리거 |

`/dev/esoc-0` 경로는 SSR 프레임워크를 우회하여 `mdm_cmd_exe`를 직접 호출한다.
`/dev/subsys_esoc0` 경로는 SSR 프레임워크를 통해 `mdm_subsys_powerup`을 호출한다
(REQ_ENG 등록 필요).

---

## 7. PeripheralManager 서비스 계약

### 7-1. init.rc 정의 (SM8250/MSM8998 공통)

```rc
service vendor.per_mgr /vendor/bin/pm-service
    class core
    user system
    group system
    ioprio rt 4

on property:init.svc.vendor.per_mgr=running
    start vendor.per_proxy

on property:sys.shutdown.requested=*
    stop vendor.per_proxy

service vendor.per_proxy /vendor/bin/pm-proxy
    class core
    user system
    group system
    disabled
```

`ioprio rt 4` = realtime IO class, priority 4. `SYS_ioprio_set`으로 설정.

**출처:**
- https://github.com/AOSPA/android_device_qcom_msm8996/blob/pie/init.target.rc
- https://github.com/moto-common/android_device_motorola_common/blob/13/rootdir/vendor/etc/init/hw/init.target.rc
- https://github.com/David112x/android-device-qti-sdm660_32/blob/master/init.target.rc

### 7-2. SELinux domain

- 도메인: `u:r:vendor_per_mgr:s0` (Android 10+) 또는 `u:r:per_mgr:s0`
- 필요 capability: `net_raw`, `net_bind_service` (CAP_SYS_ADMIN 불필요)
- 접근 장치: `ssr_device`, `sysfs_esoc`, `sysfs_ssr`, `firmware_file`
- vndbinder: `per_mgr_service` 등록

**출처:**
- https://github.com/sonyxperiadev/device-qcom-sepolicy/blob/master/common/peripheral_manager.te
- https://android.googlesource.com/device/google/marlin/+/nougat-mr1-dev/sepolicy/per_mgr.te
- https://github.com/IzumiReina/Sepolicy_vendor-mido/blob/Master/vendor_per_mgr.te

### 7-3. PeripheralManager 내부 동작 (PeripheralManagerServer.cpp)

pm-service의 내부 동작:

1. `libmdmdetect::get_system_info()`로 ESOC 버스 스캔 → `MDM_TYPE_EXTERNAL` 감지
2. `powerup_node = "/dev/subsys_<esoc_name>"` 설정
3. 클라이언트가 `requestPeripheralAccess()` 호출 → voter로 등록
4. 첫 voter → `increaseVoters()` → `open(powerup_node)` → mdm3 bring-up
5. voter 0 → `decreaseVoters()` → mdm3 power-down

**voter가 없으면 pm-service는 MDM을 OFFLINE 상태로 두고 즉시 종료한다.**

**출처:**
- https://github.com/bcyj/android_tools_leeco_msm8996/blob/master/peripheral-manager/pm-server/PeripheralManagerServer.cpp
- https://github.com/bcyj/android_tools_leeco_msm8996/blob/master/peripheral-manager/pm-server/Peripheral.cpp
- https://github.com/David112x/android_vendor_qcom_proprietary/tree/master/mdm-helper/libmdmdetect

### 7-4. 첫 번째 voter = cnss-daemon

Android에서 **`cnss-daemon`이 `requestPeripheralAccess()`를 호출하는 첫 번째 voter다.**
cnss-daemon 없이 per_mgr만 실행하면 voter 부재로 pm-service가 즉시 종료된다.

### 7-5. vendor.per_proxy 역할

pm-proxy는 MDM bring-up 자체를 담당하지 않는다.
**SSR(SubSystem Restart) 요청 QMI를 pm-service → 커널 ssreq 인터페이스로 포워딩하는
Binder RPC 헬퍼**다. 재시작 관리 전용.

---

## 8. 완전한 Android mdm3 bring-up 체인

```
[Android 부팅 시 mdm3 ONLINE 도달 과정]

mdm-helper (state machine 모드)
  ├─ open(/dev/esoc-0) → ESOC_REG_CMD_ENG
  ├─ open(/dev/esoc-0) → ESOC_REG_REQ_ENG  ← req_eng_wait 해제
  └─ ESOC_CMD_EXE(ESOC_PWR_ON) → mdm_do_first_power_on()
       ├─ PMIC pm8150l GPIO 9 soft-reset de-assert
       ├─ GPIO 135 (AP2MDM_STATUS) → HIGH
       └─ REQ_ENG 루프 대기 중...

pm_proxy_helper (mdm_helper_proxy 모드)
  └─ open(/dev/subsys_esoc0, O_RDONLY)
       └─ subsystem_get("esoc0")
            └─ mdm_subsys_powerup()
                 ├─ req_eng_wait 이미 해제됨 (mdm-helper가 먼저 등록)
                 └─ GPIO powerup 진행

SDX50M 부팅 → ESOC_REQ_IMG 발생
  └─ mdm-helper REQ_ENG 루프
       ├─ ESOC_WAIT_FOR_REQ → ESOC_REQ_IMG 수신
       ├─ tftp_server로 wlanmdsp.mbn 전송 (sda29 마운트)
       └─ ESOC_NOTIFY(ESOC_BOOT_DONE)

MDM2AP_STATUS GPIO 142 → HIGH
  └─ mdm3 ONLINE
       └─ WLFW service 69 (QRTR) → ICNSS wlfw_new_server()
            └─ BDF 다운로드 → FW_READY → wlan0
```

---

## 9. V867 예측 및 V868 방향

### 9-1. V867 예측

V867은 `per_mgr + per_proxy + pm_proxy_helper`만 허용, `mdm-helper` 차단.

예상 결과:
- per_mgr: voter(cnss-daemon) 없어 즉시 exit(0)
- pm_proxy_helper: REQ_ENG 미등록 → `mdm_subsys_powerup` D-state 블록 (V849와 동일)
- mdm3: OFFLINING 유지

### 9-2. V868 필요 조건

| 조건 | 방법 |
|---|---|
| `/dev/esoc-0` materialization | mknod (major/minor는 V851 evidence 확인) |
| `/dev/subsys_esoc0` materialization | mknod major 236 minor 9 (V846 확인) |
| REQ_ENG 등록 | `mdm-helper` (state machine 모드) 시작 |
| voter 제공 | `cnss-daemon` 시작 후 `requestPeripheralAccess()` |
| firmware download | `tftp_server` + sda29 read-only 마운트 |
| pm_proxy_helper | subsys_esoc0 fd 보유 |

### 9-3. 대안 경로 (PeripheralManager 우회)

helper 내부에서 직접 구현 가능한 최소 경로:

```
1. /dev/esoc-0 mknod
2. fd1 = open("/dev/esoc-0") → ESOC_REG_CMD_ENG
3. fd2 = open("/dev/esoc-0") → ESOC_REG_REQ_ENG  ← 블록 해제
4. thread A: ESOC_CMD_EXE(ESOC_PWR_ON)
5. thread B: loop ESOC_WAIT_FOR_REQ → firmware download → ESOC_NOTIFY(ESOC_BOOT_DONE)
6. sda29 마운트 (wlanmdsp.mbn 접근)
```

이 경로는 PeripheralManager/per_mgr 없이 mdm3를 직접 bring-up한다.
단, `mdm-helper` 및 관련 gate 승인 필요.

---

## 10. property 계약 (live 기기 증거, V857–V861)

pm-service가 시작 시 설정하는 property:

| Property | 값 | 시점 |
|---|---|---|
| `vendor.peripheral.SDX50M.state` | `OFFLINE` | 초기화 시 |
| `vendor.peripheral.modem.state` | `OFFLINE` | 초기화 시 |
| `vendor.peripheral.shutdown_critical_list` | `SDX50M`, `SDX50M modem` | 초기화 시 누적 |

pm-service가 읽는 property (denied without proper namespace):
`log.tag.PerMgrLib`, `log.tag.PerMgrSrv`, `log.tag.PerMgrProxy`

---

## 11. 참고 문헌

| 출처 | 내용 |
|---|---|
| https://github.com/David112x/android_vendor_qcom_proprietary/tree/master/mdm-helper | mdm_helper.c — pm_proxy_helper=mdm_helper_proxy 확인 |
| https://github.com/ianmacd/winnerx/blob/master/drivers/soc/qcom/subsystem_restart.c | pm_proxy_helper 커널 예외 처리 |
| https://git.codelinaro.org/clo/la/kernel/msm-4.4/-/blob/LA.UM.6.1.1.c25-03600-sdm660.0/drivers/esoc/esoc-mdm-drv.c | req_eng_wait D-state 원인 |
| https://github.com/commaai/android_kernel_comma_msm8996/blob/master/drivers/esoc/esoc-mdm-4x.c | ESOC_CMD_EXE(ESOC_PWR_ON) 처리 |
| https://android.googlesource.com/kernel/msm/+/android-7.1.0_r0.2/drivers/esoc/esoc-mdm-4x.c | esoc-mdm-4x.c GoogleSource 참조 |
| https://github.com/bcyj/android_tools_leeco_msm8996/blob/master/peripheral-manager/pm-server/PeripheralManagerServer.cpp | PeripheralManager voter 메커니즘 |
| https://github.com/bcyj/android_tools_leeco_msm8996/blob/master/peripheral-manager/pm-server/Peripheral.cpp | Peripheral class powerup_node 처리 |
| https://github.com/AOSPA/android_device_qcom_msm8996/blob/pie/init.target.rc | per_mgr/per_proxy init.rc 정의 |
| https://github.com/sonyxperiadev/device-qcom-sepolicy/blob/master/common/peripheral_manager.te | per_mgr SELinux policy |
| https://github.com/sonyxperiadev/device-qcom-sepolicy/blob/master/common/mdm_helper.te | mdm_helper SELinux policy |
| https://github.com/Bigcountry907/HTC_a13_vzw_Kernel/tree/master/vendor/qcom/proprietary/mdm-helper/esoc/mdm9k | mdm-helper REQ_ENG 루프 참조 |
| 로컬 OSRC: `include/uapi/linux/esoc_ctrl.h` | esoc ioctl 전체 목록 확인 |
| V849 evidence: `tmp/wifi/v849-subsys-esoc0-wait-state-sampler/` | wchan D-state 확정 |
| V856–V861 evidence | per_mgr property/fd live 증거 |

---

## 12. V868 classifier 결과

V868 host-only classifier:
`scripts/revalidation/native_wifi_pm_esoc_contract_classifier_v868.py`

Evidence:

- `tmp/wifi/v868-pm-esoc-contract-classifier/manifest.json`
- `tmp/wifi/v868-pm-esoc-contract-classifier/summary.md`

Decision:

- `v868-esoc-req-eng-precondition-selected`

해석:

- V867의 `pm_proxy_helper` D-state는 `pm_proxy_helper` 자체 결함보다
  `/dev/esoc-0` CMD/REQ engine 등록 없이 `/dev/subsys_esoc0` hold를 먼저
  시도한 순서 문제로 보는 것이 현재 증거에 가장 잘 맞는다.
- `pm_proxy_helper` 단독 재시도는 닫는다.
- 다음 구현 대상은 Wi-Fi HAL, scan/connect, credential 사용이 아니라
  A90 로컬 `esoc_ctrl.h` 값에 기반한 eSoC control preflight helper다.
- live `ESOC_PWR_ON`은 별도 gate 전까지 차단한다.

---

## 13. V869 helper 결과

V869 source/build-only:
`stage3/linux_init/helpers/a90_android_execns_probe.c`

Evidence:

- `tmp/wifi/v869-execns-helper-v135-build/a90_android_execns_probe`
- `docs/reports/NATIVE_INIT_V869_ESOC_CONTROL_PREFLIGHT_HELPER_BUILD_2026-05-25.md`

결과:

- helper marker: `a90_android_execns_probe v135`
- new mode: `wifi-companion-esoc-control-preflight`
- allow flag: `--allow-esoc-control-preflight`
- static ARM64 build PASS

이 mode는 다음 live gate를 위한 기반만 제공한다. 기본 상태에서는
`REG_REQ_ENG`, `REG_CMD_ENG`, `CMD_EXE`, `WAIT_FOR_REQ`, `NOTIFY`, `PWR_ON`,
`mdm_helper`, `ks`, Wi-Fi HAL, scan/connect, DHCP/routes, external ping을 모두
시도하지 않는다.

다음 후보:

- V870 helper `v135` deploy-only checksum/version/mode proof
- V871 bounded live eSoC control preflight는 V870 이후 별도 gate

---

## 14. V870 deploy 결과

V870 deploy-only evidence:

- `tmp/wifi/v870-execns-helper-v135-deploy/manifest.json`
- `tmp/wifi/v870-post-health/manifest.json`

Decision:

- `execns-helper-v135-deploy-pass`

결과:

- `/cache/bin/a90_android_execns_probe` remote sha:
  `ad1bbbf295be61ef612406091ccd469c4ef45ab44c0f753c4de034e487ddaad1`
- remote marker: `a90_android_execns_probe v135`
- mode token: `wifi-companion-esoc-control-preflight`
- selftest: `pass=11 warn=1 fail=0`
- actor hits: `0`
- Wi-Fi link hits: `0`

다음 후보:

- V871 bounded live eSoC control preflight
- 범위는 `/dev/esoc-0` visibility와 read-only status ioctl로 제한한다.
- `REG_REQ_ENG`, `REG_CMD_ENG`, `CMD_EXE`, `WAIT_FOR_REQ`, `NOTIFY`,
  `PWR_ON`, `mdm_helper`, `ks`, `pm_proxy_helper`, CNSS, HAL, scan/connect는
  계속 별도 gate 전까지 차단한다.

---

## 15. V872 helper v136 classification repair

V871 live evidence showed that helper `v135` reached argument parsing but did
not reach the eSoC preflight body. The mode was still grouped with
PeripheralManager/service-manager node-materialization modes, so setup tried to
materialize SELinuxfs/service-manager runtime surfaces before the read-only
`/dev/esoc-0` probe.

V872 repaired this by splitting the helper classification:

- PeripheralManager service-node materialization remains separate.
- `wifi-companion-esoc-control-preflight` still creates the private eSoC nodes:
  `/dev/esoc-0`, `/dev/subsys_esoc0`, and `/dev/subsys_modem`.
- The eSoC preflight no longer inherits service-manager or SELinuxfs runtime
  requirements.

Evidence:

- `tmp/wifi/v872-execns-helper-v136-build/a90_android_execns_probe`
- `docs/reports/NATIVE_INIT_V872_ESOC_PREFLIGHT_HELPER_V136_BUILD_2026-05-25.md`

## 16. V873 helper v136 deploy result

V873 deployed helper `v136` to `/cache/bin/a90_android_execns_probe` with serial
appendfile/uudecode only.

Evidence:

- `tmp/wifi/v873-execns-helper-v136-deploy/manifest.json`
- remote sha256:
  `76dce733b8444073fc615a44df240aa7f8256dfb7f6c123c3f5e388907356980`

Guardrails held: no actor start, no Wi-Fi bring-up, and no live eSoC ioctl in
V873.

## 17. V874 read-only eSoC control preflight result

V874 ran the bounded live read-only eSoC control preflight with helper `v136`.

Decision:

- `v874-esoc-readonly-ioctl-probe-pass`

Observed read-only ioctl results:

| ioctl | request | rc | errno | value |
| --- | --- | --- | --- | --- |
| `GET_STATUS` | `0x8004cc04` | `0` | `0` | `0` |
| `GET_ERR_FATAL` | `0x8004cc05` | `0` | `0` | `0` |
| `GET_LINK_ID` | `0xc008cc09` | `-1` | `22` | `0` |

Important guardrails:

- `REG_REQ_ENG`, `REG_CMD_ENG`, `CMD_EXE`, `WAIT_FOR_REQ`, `NOTIFY`, and
  `PWR_ON` were not attempted.
- `mdm_helper`, `ks`, `pm_proxy_helper`, CNSS, service-manager trio, Wi-Fi HAL,
  scan/connect, credentials, DHCP/routes, and external ping were not executed.
- Created device nodes were cleaned up and postflight selftest stayed
  `pass=11 warn=1 fail=0`.

Current interpretation:

- `/dev/esoc-0` is reachable for read-only control ioctls.
- The immediate blocker is now safe design of a future mutating CMD/REQ engine
  registration gate.
- `PWR_ON` remains blocked until a later explicit gate.

Next candidate:

- V875 host-only eSoC state-machine precondition classifier for
  `REG_CMD_ENG`/`REG_REQ_ENG`, fd ownership, timeout, cleanup, and rollback.

---

## 18. V875 state-machine precondition classifier

V875 classified the next eSoC gate host-only. It used local A90 OSRC plus V849
and V874 evidence, and did not contact the device.

Evidence:

- `tmp/wifi/v875-esoc-state-machine-precondition-classifier/manifest.json`
- `docs/reports/NATIVE_INIT_V875_ESOC_STATE_MACHINE_PRECONDITION_2026-05-25.md`

Decision:

- `v875-esoc-state-machine-precondition-pass`

Important classifications:

| Operation | Result |
| --- | --- |
| `ESOC_REG_CMD_ENG` | next source/build helper support only |
| `ESOC_REG_REQ_ENG` | next source/build helper support only |
| `ESOC_CMD_EXE(ESOC_PWR_ON)` | blocked |
| `ESOC_WAIT_FOR_REQ` | blocked |
| `ESOC_NOTIFY` | blocked |
| `/dev/subsys_esoc0` open | blocked until CMD/REQ/PWR_ON sequencing is defined |

Recommended sequence:

1. V876 source/build helper `v137` with fail-closed CMD/REQ registration mode.
2. V877 deploy-only helper `v137` checksum/version/mode proof.
3. V878 bounded live CMD/REQ registration preflight, still no
   `CMD_EXE`/`PWR_ON`/`WAIT_FOR_REQ`/`NOTIFY`/`/dev/subsys_esoc0` open.
4. Later gate: firmware request loop and only then explicit `PWR_ON`
   consideration.

---

## 19. V876 helper v137 CMD/REQ registration support

V876 implemented source/build-only helper support for the next eSoC gate.

Evidence:

- `tmp/wifi/v876-execns-helper-v137-build/a90_android_execns_probe`
- `docs/reports/NATIVE_INIT_V876_ESOC_ENGINE_REGISTER_HELPER_BUILD_2026-05-25.md`

Result:

- helper marker: `a90_android_execns_probe v137`
- mode: `wifi-companion-esoc-engine-register-preflight`
- allow flag: `--allow-esoc-engine-register-preflight`
- sha256: `e47eb52b0b2b2fb601fdbc4ecebdf72e2fda9519eac37e776d62c11d2d469aa3`

V876 did not deploy the helper and did not execute live eSoC ioctls. The helper
now has the source path needed for a later bounded CMD/REQ registration live
gate while explicitly keeping `CMD_EXE`, `PWR_ON`, `WAIT_FOR_REQ`, `NOTIFY`,
`/dev/subsys_esoc0` open, actor start, Wi-Fi HAL, scan/connect, credentials,
DHCP/routes, and external ping blocked.

Next candidate:

- V877 helper `v137` deploy-only checksum/version/mode proof.

---

## 20. V877 helper v137 deploy result

V877 deployed helper `v137` to `/cache/bin/a90_android_execns_probe`.

Evidence:

- `tmp/wifi/v877-execns-helper-v137-plan/manifest.json`
- `tmp/wifi/v877-execns-helper-v137-preflight/manifest.json`
- `tmp/wifi/v877-execns-helper-v137-deploy-preflight/manifest.json`
- `docs/reports/NATIVE_INIT_V877_HELPER_V137_DEPLOY_2026-05-25.md`

Decision:

- `execns-helper-v137-deploy-pass`

Result:

- remote sha256:
  `e47eb52b0b2b2fb601fdbc4ecebdf72e2fda9519eac37e776d62c11d2d469aa3`
- remote marker: `a90_android_execns_probe v137`
- mode token: `wifi-companion-esoc-engine-register-preflight`
- selftest stayed `fail=0`
- service-manager process hits: `0`
- Wi-Fi netdev hits: `0`

Guardrails held: V877 did not execute live eSoC ioctls, did not open
`/dev/subsys_esoc0`, did not start Android actors, and did not bring up Wi-Fi.

Next candidate:

- V878 bounded live `REG_CMD_ENG`/`REG_REQ_ENG` registration preflight.
- Still block `CMD_EXE`, `PWR_ON`, `WAIT_FOR_REQ`, `NOTIFY`,
  `/dev/subsys_esoc0` open, actors, Wi-Fi HAL, scan/connect, credentials,
  DHCP/routes, and external ping.

---

## 21. V878 CMD/REQ engine registration preflight result

V878 ran the first bounded mutating eSoC preflight with helper `v137`.

Evidence:

- `tmp/wifi/v878-esoc-engine-register-preflight-plan/manifest.json`
- `tmp/wifi/v878-esoc-engine-register-preflight-missing-flags/manifest.json`
- `tmp/wifi/v878-esoc-engine-register-preflight-live/manifest.json`
- `docs/reports/NATIVE_INIT_V878_ESOC_ENGINE_REGISTER_PREFLIGHT_2026-05-25.md`

Decision:

- `v878-esoc-engine-register-ioctl-review`

Result:

| Operation | rc | errno | Interpretation |
| --- | --- | --- | --- |
| `REG_CMD_ENG` | `-1` | `16` | command engine busy/unavailable; direct userspace `CMD_EXE` remains blocked |
| `REG_REQ_ENG` | `0` | `0` | request engine registration path works |

Additional findings:

- helper result: `engine-register-preflight-complete`
- fds were closed after a 6s hold
- created private nodes were removed
- selftest stayed `fail=0`
- actor hits: `0`
- Wi-Fi netdev hits: `0`
- dmesg filter: `mdm-4x esoc0: Client hooks not registered for the device`

Guardrails held: no `CMD_EXE`, no `PWR_ON`, no `WAIT_FOR_REQ`, no `NOTIFY`, no
`/dev/subsys_esoc0` open, no actor start, no Wi-Fi HAL, and no Wi-Fi bring-up.

Next candidate:

- V879 host-only classifier for `REG_CMD_ENG` `EBUSY`, eSoC client-hook state,
  and whether the next live gate should use a REQ-registered subsystem powerup
  path rather than direct userspace `CMD_EXE`.

---

## 22. V879 CMD engine ownership classifier result

V879 classified V878 host-only.

Evidence:

- `tmp/wifi/v879-cmd-engine-ownership-classifier/manifest.json`
- `docs/reports/NATIVE_INIT_V879_CMD_ENGINE_OWNERSHIP_CLASSIFIER_2026-05-26.md`

Decision:

- `v879-cmd-engine-ebusy-classified`

Classification:

- Direct userspace `CMD_EXE` remains blocked because V878 did not acquire
  command-engine ownership (`REG_CMD_ENG` returned `EBUSY`).
- `REG_REQ_ENG` returned rc `0`, so the earlier V849 `req_eng_wait` blocker now
  has a narrower next candidate.
- The next path should be kernel subsystem powerup with a REQ fd held, not a
  helper-owned direct `ESOC_CMD_EXE`.
- V878 dmesg still reported `Client hooks not registered for the device`, so
  any future live subsystem-open proof must capture MHI/CNSS eSoC hook state
  around the window.

Next candidate:

- V880 helper `v138` source/build-only:
  1. repair stale successful-open errno reporting,
  2. add fail-closed REQ-registered subsystem-hold preflight support,
  3. keep direct userspace `CMD_EXE`, explicit userspace `PWR_ON`,
     `WAIT_FOR_REQ`, `NOTIFY`, actors, Wi-Fi HAL, scan/connect, credentials,
     DHCP/routes, and external ping blocked.

---

## 23. V880 REQ-registered subsystem-hold helper build result

V880 implemented the V879-selected helper support as a source/build-only step.

Evidence:

- `tmp/wifi/v880-execns-helper-v138-build/manifest.json`
- `docs/plans/NATIVE_INIT_V880_REQ_REGISTERED_SUBSYS_HOLD_HELPER_PLAN_2026-05-26.md`
- `docs/reports/NATIVE_INIT_V880_REQ_REGISTERED_SUBSYS_HOLD_HELPER_BUILD_2026-05-26.md`

Decision:

- `v880-helper-v138-build-pass`

Result:

- helper marker: `a90_android_execns_probe v138`
- artifact sha256:
  `2ac8c6730768f86a221722a6ff259e3a4617134221498bd1956a63980a22a9b5`
- new mode token:
  `wifi-companion-esoc-req-registered-subsys-hold-preflight`
- new allow flag:
  `--allow-esoc-req-registered-subsys-hold-preflight`
- stale successful-open errno reporting repaired for existing eSoC open paths
- new mode remains fail-closed by default and records reboot-required evidence
  if a future bounded child cannot be proven stopped

Guardrails held: V880 did not deploy the helper, did not contact the device,
did not execute live eSoC ioctls, did not open `/dev/subsys_esoc0`, did not
start Android actors, and did not bring up Wi-Fi.

Next candidate:

- V881 helper `v138` deploy-only checksum/version/mode proof.
- Still block live eSoC ioctls, `/dev/subsys_esoc0` open, actors, Wi-Fi HAL,
  scan/connect, credentials, DHCP/routes, and external ping.

---

## 24. V881 helper v138 deploy result and route correction

V881 deployed helper `v138` to `/cache/bin/a90_android_execns_probe`.

Evidence:

- `tmp/wifi/v881-execns-helper-v138-plan/manifest.json`
- `tmp/wifi/v881-execns-helper-v138-preflight/manifest.json`
- `tmp/wifi/v881-execns-helper-v138-deploy-preflight/manifest.json`
- `docs/plans/NATIVE_INIT_V881_HELPER_V138_DEPLOY_PLAN_2026-05-26.md`
- `docs/reports/NATIVE_INIT_V881_HELPER_V138_DEPLOY_2026-05-26.md`

Decision:

- `execns-helper-v138-deploy-pass`

Result:

- remote sha256:
  `2ac8c6730768f86a221722a6ff259e3a4617134221498bd1956a63980a22a9b5`
- remote marker: `a90_android_execns_probe v138`
- mode token:
  `wifi-companion-esoc-req-registered-subsys-hold-preflight`
- serial chunks written: `788`
- post-deploy selftest stayed `fail=0`
- service-manager process hits: `0`
- Wi-Fi netdev hits: `0`

Guardrails held: V881 did not execute live eSoC ioctls, did not open
`/dev/subsys_esoc0`, did not start Android actors, and did not bring up Wi-Fi.

Route correction from follow-up source analysis:

- `REG_CMD_ENG` ownership is not required for initial subsystem powerup; the
  kernel eSoC path can issue the initial power-on command internally after
  `REG_REQ_ENG` releases `req_eng_wait`.
- SDX50M may not emit `ESOC_REQ_IMG`; that request loop is more likely an
  older USB/HSIC modem image-transfer pattern.
- The next useful helper gap is passive `ESOC_WAIT_FOR_REQ` observation during
  a future REQ-registered subsystem-hold window, not direct userspace
  `CMD_EXE`.

Next candidate:

- V882 helper `v139` source/build-only passive `ESOC_WAIT_FOR_REQ` observer
  support.
- Still block helper deploy, live eSoC ioctl, `/dev/subsys_esoc0` open,
  `ESOC_NOTIFY`, actors, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and
  external ping in V882.

---

## 25. V882 passive WAIT_FOR_REQ observer helper build result

V882 added passive request observation support as a source/build-only step.

Evidence:

- `tmp/wifi/v882-execns-helper-v139-build/manifest.json`
- `docs/plans/NATIVE_INIT_V882_PASSIVE_WAIT_FOR_REQ_HELPER_PLAN_2026-05-26.md`
- `docs/reports/NATIVE_INIT_V882_PASSIVE_WAIT_FOR_REQ_HELPER_BUILD_2026-05-26.md`

Decision:

- `v882-helper-v139-build-pass`

Result:

- helper marker: `a90_android_execns_probe v139`
- artifact sha256:
  `077ced65ae5b0b546ecdf3b1bb0c808d3ec34bfa2462516e6ceba170b18f23c5`
- mode token remains:
  `wifi-companion-esoc-req-registered-subsys-hold-preflight`
- passive observer markers added under:
  `esoc_req_registered_subsys_hold_preflight.wait_for_req_observer.*`
- `ESOC_NOTIFY`, explicit userspace `PWR_ON`, direct userspace `CMD_EXE`,
  actors, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping
  remain blocked.
- Timeout cleanup now treats surviving observer process/pipe state as
  reboot-required evidence instead of an unbounded host wait.

Guardrails held: V882 did not deploy the helper, did not contact the device,
did not execute live eSoC ioctls, did not open `/dev/subsys_esoc0`, did not
start Android actors, and did not bring up Wi-Fi.

Next candidate:

- V883 helper `v139` deploy-only checksum/version/mode proof.
- Still block live eSoC ioctls, `/dev/subsys_esoc0` open, `ESOC_NOTIFY`,
  actors, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping.

---

## 26. V883 helper v139 deploy result

V883 deployed helper `v139` to `/cache/bin/a90_android_execns_probe`.

Evidence:

- `tmp/wifi/v883-execns-helper-v139-plan/manifest.json`
- `tmp/wifi/v883-execns-helper-v139-preflight/manifest.json`
- `tmp/wifi/v883-execns-helper-v139-deploy-preflight/manifest.json`
- `tmp/wifi/v883-execns-helper-v139-postdeploy/manifest.json`
- `docs/plans/NATIVE_INIT_V883_HELPER_V139_DEPLOY_PLAN_2026-05-26.md`
- `docs/reports/NATIVE_INIT_V883_HELPER_V139_DEPLOY_2026-05-26.md`

Decision:

- `execns-helper-v139-deploy-pass`

Result:

- remote sha256:
  `077ced65ae5b0b546ecdf3b1bb0c808d3ec34bfa2462516e6ceba170b18f23c5`
- remote marker: `a90_android_execns_probe v139`
- mode token:
  `wifi-companion-esoc-req-registered-subsys-hold-preflight`
- serial chunks written: `788`
- post-deploy selftest stayed `fail=0`
- service-manager process hits: `0`
- Wi-Fi netdev hits: `0`

Guardrails held: V883 did not execute live eSoC ioctls, did not open
`/dev/subsys_esoc0`, did not start Android actors, and did not bring up Wi-Fi.

Next candidate:

- V884 bounded live REQ-registered subsystem-hold observer preflight using
  deployed helper `v139`.
- The next gate should rely on `REG_REQ_ENG` as the powerup precondition,
  record passive `ESOC_WAIT_FOR_REQ` output, and treat absent `ESOC_REQ_IMG`
  as diagnostic data rather than a failure.
- Still block `REG_CMD_ENG` dependency, direct userspace `CMD_EXE`, explicit
  userspace `PWR_ON`, `ESOC_NOTIFY`, actors, Wi-Fi HAL, scan/connect,
  credentials, DHCP/routes, and external ping.

---

## 27. V884 REQ-registered subsystem-hold observer result

V884 ran the first REQ-registered `/dev/subsys_esoc0` hold window with helper
`v139`.

Evidence:

- `tmp/wifi/v884-esoc-req-registered-subsys-hold-plan/manifest.json`
- `tmp/wifi/v884-esoc-req-registered-subsys-hold-live/manifest.json`
- `tmp/wifi/v884-esoc-req-registered-subsys-hold-reboot-cleanup/`
- `docs/plans/NATIVE_INIT_V884_REQ_REGISTERED_SUBSYS_HOLD_OBSERVER_PLAN_2026-05-26.md`
- `docs/reports/NATIVE_INIT_V884_REQ_REGISTERED_SUBSYS_HOLD_OBSERVER_2026-05-26.md`

Decision:

- live runner: `v884-reboot-required`
- recovery: post-reboot native version returned and selftest stayed `fail=0`

Result:

- `REG_REQ_ENG` returned rc `0`, errno `0`.
- Passive `ESOC_WAIT_FOR_REQ` returned rc `4`, errno `0`, value `1`.
- Local OSRC interprets this as request observed: rc `4` is the copied
  `sizeof(u32)` byte count and value `1` is `ESOC_REQ_IMG`.
- `/dev/subsys_esoc0` open did not return, was not reaped after TERM/KILL, and
  required reboot cleanup.
- `mss`, `mdm3`, and `rpmsg` stayed `OFFLINING`/empty across before, hold, and
  after snapshots.

Guardrails held: V884 did not execute `REG_CMD_ENG`, direct userspace
`CMD_EXE`, explicit userspace `PWR_ON`, `ESOC_NOTIFY`, Android actors, Wi-Fi
HAL, scan/connect, credentials, DHCP/routes, or external ping.

Route correction:

- The earlier assumption that SDX50M may not emit `ESOC_REQ_IMG` is wrong for
  this live path.
- The next blocker is the missing Android-equivalent response to
  `ESOC_REQ_IMG`, not another `/dev/subsys_esoc0` open retry.

Next candidate:

- V885 host-only Android `mdm_helper` image-request response classifier.
- Determine which image transfer path and `ESOC_NOTIFY` value Android uses
  before any new live eSoC ioctl or subsystem open attempt.

---

## 28. V885 ESOC_REQ_IMG response classifier result

V885 classified the V884 request evidence host-only.

Evidence:

- `tmp/wifi/v885-esoc-req-img-response-classifier/manifest.json`
- `tmp/wifi/v885-esoc-req-img-response-classifier/summary.md`
- `docs/plans/NATIVE_INIT_V885_ESOC_REQ_IMG_RESPONSE_CLASSIFIER_PLAN_2026-05-26.md`
- `docs/reports/NATIVE_INIT_V885_ESOC_REQ_IMG_RESPONSE_CLASSIFIER_2026-05-26.md`

Decision:

- `v885-esoc-req-img-response-contract-classified`

Result:

- V884 `ESOC_WAIT_FOR_REQ rc=4 errno=0 value=1` is request evidence, not an
  ioctl failure.
- Local OSRC `esoc_dev.c` returns the copied `u32` byte count after reading the
  request FIFO and writing the request value to userspace.
- Local `esoc_ctrl.h` maps value `1` to `ESOC_REQ_IMG`.
- Local `esoc-mdm-pon.c` shows the SDX50M path can queue `ESOC_REQ_IMG`.
- Local `esoc-mdm-4x.c` exposes the response hooks for `ESOC_IMG_XFER_DONE` and
  `ESOC_BOOT_DONE`.

Guardrails held: V885 did not contact the device, did not execute live eSoC
ioctls, did not open `/dev/subsys_esoc0`, did not issue `ESOC_NOTIFY`, did not
start Android actors, and did not bring up Wi-Fi.

Next candidate:

- V886 helper `v140` source/build-only semantic repair plus guarded response
  scaffold.
- Fix helper output so nonnegative `WAIT_FOR_REQ` byte-count returns are
  classified as request observations.
- Keep live `ESOC_NOTIFY`, subsystem open retries, actors, Wi-Fi HAL,
  scan/connect, credentials, DHCP/routes, and external ping blocked until a
  separate deploy/live response gate exists.

---

## 29. V886 helper v140 ESOC_REQ_IMG response scaffold result

V886 updated the helper source and built helper `v140`.

Evidence:

- `tmp/wifi/v886-execns-helper-v140-build/manifest.json`
- `tmp/wifi/v886-execns-helper-v140-build/build.log`
- `tmp/wifi/v886-execns-helper-v140-build/a90_android_execns_probe`
- `docs/plans/NATIVE_INIT_V886_ESOC_REQ_IMG_RESPONSE_HELPER_PLAN_2026-05-26.md`
- `docs/reports/NATIVE_INIT_V886_ESOC_REQ_IMG_RESPONSE_HELPER_BUILD_2026-05-26.md`

Decision:

- `v886-helper-v140-build-pass`

Result:

- helper marker is now `a90_android_execns_probe v140`.
- Passive `ESOC_WAIT_FOR_REQ` observer now treats rc equal to copied
  `sizeof(u32)` as `request-observed`.
- Observer output now includes byte count, expected byte count, request name,
  request-observed, and `ESOC_REQ_IMG` classification markers.
- Response scaffold markers expose `ESOC_REQ_IMG`, `ESOC_IMG_XFER_DONE`, and
  `ESOC_BOOT_DONE` values while keeping live notify execution blocked.
- Static ARM64 build passed with no dynamic section.

Guardrails held: V886 did not deploy the helper, did not contact the device,
did not execute live eSoC ioctls, did not open `/dev/subsys_esoc0`, did not
issue `ESOC_NOTIFY`, did not start Android actors, and did not bring up Wi-Fi.

Next candidate:

- V887 helper `v140` deploy-only checksum/version/mode proof.
- Live `ESOC_NOTIFY`, subsystem-open retry, actors, Wi-Fi HAL, scan/connect,
  credentials, DHCP/routes, and external ping remain blocked until a separate
  bounded response gate.

---

## 30. V887 helper v140 deploy result

V887 deployed helper `v140` to `/cache/bin/a90_android_execns_probe`.

Evidence:

- `tmp/wifi/v887-execns-helper-v140-plan/manifest.json`
- `tmp/wifi/v887-execns-helper-v140-preflight/manifest.json`
- `tmp/wifi/v887-execns-helper-v140-deploy-preflight/manifest.json`
- `tmp/wifi/v887-execns-helper-v140-deploy-preflight-retry1850/manifest.json`
- `docs/plans/NATIVE_INIT_V887_HELPER_V140_DEPLOY_PLAN_2026-05-26.md`
- `docs/reports/NATIVE_INIT_V887_HELPER_V140_DEPLOY_2026-05-26.md`

Decision:

- final retry: `execns-helper-v140-deploy-pass`

Result:

- Initial `--serial-chunk-size 3000` attempt failed before device writes:
  `chunks_written=0`, `max_cmdv1_line_bytes=6190`, safe limit `3968`.
- Retry with `--serial-chunk-size 1850` passed:
  `chunks=788`, `max_cmdv1_line_bytes=3890`, safe limit `3968`.
- Remote helper sha256 matches V886:
  `894fdd753cb6567b2abbb3c94f332ce63cf959b7d1708768cf3bcdc10b2b53e0`.
- Remote helper usage output includes `a90_android_execns_probe v140`.
- Post-deploy read-only health checks passed; no Wi-Fi bring-up occurred.

Guardrails held: V887 did not execute live eSoC ioctls, did not open
`/dev/subsys_esoc0`, did not issue `ESOC_NOTIFY`, did not start Android actors,
and did not bring up Wi-Fi.

Next candidate:

- V888 host-only response-gate plan/classifier before any live `ESOC_NOTIFY`.
- Decide whether the next live response proof should send `ESOC_IMG_XFER_DONE`,
  `ESOC_BOOT_DONE`, or a bounded two-step sequence.

---

## 31. V888 eSoC response gate classifier result

V888 classified the next response gate host-only.

Evidence:

- `tmp/wifi/v888-esoc-response-gate-classifier/manifest.json`
- `tmp/wifi/v888-esoc-response-gate-classifier/summary.md`
- `docs/plans/NATIVE_INIT_V888_ESOC_RESPONSE_GATE_CLASSIFIER_PLAN_2026-05-26.md`
- `docs/reports/NATIVE_INIT_V888_ESOC_RESPONSE_GATE_CLASSIFIER_2026-05-26.md`

Decision:

- `v888-esoc-response-gate-classified`

Result:

- First response after `ESOC_REQ_IMG` should be `ESOC_IMG_XFER_DONE`.
- `ESOC_BOOT_DONE` is not safe as a blind first response because it emits
  `ESOC_RUN_STATE`, and `ESOC_RUN_STATE` completes the subsystem powerup wait.
- The next live response proof must poll `ESOC_GET_STATUS` or equivalent
  mdm2ap readiness evidence before `ESOC_BOOT_DONE`.

Guardrails held: V888 did not contact the device, did not execute live eSoC
ioctls, did not open `/dev/subsys_esoc0`, did not issue `ESOC_NOTIFY`, did not
start Android actors, and did not bring up Wi-Fi.

Next candidate:

- V889 helper `v141` source/build-only conditional response mode.
- Live response remains blocked until a separate bounded proof exists.

---

## 32. V889 helper v141 conditional response build result

V889 updated and built helper `v141`.

Evidence:

- `tmp/wifi/v889-execns-helper-v141-build/manifest.json`
- `tmp/wifi/v889-execns-helper-v141-build/build.log`
- `tmp/wifi/v889-execns-helper-v141-build/a90_android_execns_probe`
- `docs/plans/NATIVE_INIT_V889_ESOC_CONDITIONAL_RESPONSE_HELPER_PLAN_2026-05-26.md`
- `docs/reports/NATIVE_INIT_V889_ESOC_CONDITIONAL_RESPONSE_HELPER_BUILD_2026-05-26.md`

Decision:

- `v889-helper-v141-build-pass`

Result:

- helper marker is now `a90_android_execns_probe v141`.
- Added mode `wifi-companion-esoc-conditional-response-preflight`.
- Added allow flag `--allow-esoc-conditional-response-preflight`.
- Conditional response logic is present but not executed in V889:
  `ESOC_REQ_IMG` -> `ESOC_IMG_XFER_DONE` -> `ESOC_GET_STATUS` polling ->
  conditional `ESOC_BOOT_DONE`.
- Static ARM64 build passed with no dynamic section.

Guardrails held: V889 did not deploy the helper, did not contact the device,
did not execute live eSoC ioctls, did not open `/dev/subsys_esoc0`, did not
issue `ESOC_NOTIFY`, did not start Android actors, and did not bring up Wi-Fi.

Next candidate:

- V890 helper `v141` deploy-only checksum/version/mode proof.
- Live conditional response remains blocked until a separate bounded proof.
