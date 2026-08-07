# Native Init USB Gadget Map (2026-04-25)

이 문서는 `A90 Linux init v47` 기준 USB gadget 구성을 정리한다.
목표는 현재 안정적인 ACM serial 제어 채널을 기준점으로 고정하고,
ADB와 USB networking 후보를 어디서부터 봐야 하는지 분리하는 것이다.

## 결론

- 현재 기준 제어 채널은 USB CDC ACM serial이다.
- device-side 구성은 configfs gadget `g1` + function `acm.usb0` + UDC `a600000.dwc3`이다.
- host-side 노출은 `/dev/ttyACM0`, driver는 `cdc_acm`이다.
- host descriptor 기준 현재 활성 USB interface는 CDC ACM control/data 2개뿐이다.
- ADB는 현재 기본 경로가 아니다. `startadbd`는 `ffs.adb`를 추가 시도하지만, 과거 실측 기준 `adbd` zombie와 FunctionFS `ep0 only` 상태가 핵심 blocker다.
- USB networking은 다음 확장 후보지만, ACM rescue channel을 유지한 상태에서 두 번째 function으로 추가해야 한다.

## 현재 구성 코드

`stage3/linux_init/init_v47.c`의 `setup_acm_gadget()`가 만드는 구조:

```text
/config
└── usb_gadget
    └── g1
        ├── idVendor                  0x04e8
        ├── idProduct                 0x6861
        ├── bcdUSB                    0x0200
        ├── bcdDevice                 0x0100
        ├── strings/0x409
        │   ├── serialnumber          DEVICE-A90-01
        │   ├── manufacturer          samsung
        │   └── product               SM8150-ACM
        ├── configs/b.1
        │   ├── strings/0x409/configuration  serial
        │   ├── MaxPower              900
        │   └── f1 -> functions/acm.usb0
        ├── functions/acm.usb0
        └── UDC                       a600000.dwc3
```

부팅 흐름:

1. `mount("configfs", "/config", "configfs", ...)`
2. `g1` gadget tree 생성
3. `functions/acm.usb0` 생성
4. `configs/b.1/f1 -> functions/acm.usb0` symlink 생성
5. `UDC = a600000.dwc3` bind
6. `/sys/class/tty/ttyGS0/dev` 기준 `/dev/ttyGS0` 생성
7. `/dev/ttyGS0`를 native init shell stdin/stdout/stderr로 attach

## Host 관찰값

현재 host에서 보이는 장치:

```text
Bus 002 Device 020: ID 04e8:6861 Samsung Electronics Co., Ltd SAMSUNG_Android
```

USB tree:

```text
Port 003: Dev 020, If 0, Class=Communications, Driver=cdc_acm, 5000M
Port 003: Dev 020, If 1, Class=CDC Data, Driver=cdc_acm, 5000M
```

host sysfs:

```text
/dev/ttyACM0 -> .../2-1.3:1.0/tty/ttyACM0
MAJOR=166
MINOR=0
DEVNAME=ttyACM0
```

device descriptor:

| Field | Value |
|---|---|
| VID:PID | `04e8:6861` |
| Manufacturer | `SAMSUNG` |
| Product | `SAMSUNG_Android` |
| Serial | `DEVICE-A90-01` |
| Speed | `5000` |
| bDeviceClass | `00` |
| bDeviceSubClass | `00` |
| bDeviceProtocol | `00` |
| bNumConfigurations | `1` |

host `lsusb -v`는 negotiated speed를 SuperSpeed 5Gbps로 표시했다.
`init_v47`은 `bcdUSB=0x0200`, `bcdDevice=0x0100`을 쓰지만 host descriptor에서는
`bcdUSB 3.20`, `bcdDevice 4.00`으로 보인다. 이 값은 DWC3/composite gadget 쪽에서
실제 speed/capability에 맞춰 보정되어 노출되는 것으로 판단한다.

## 활성 Interface

### Interface 0

| Field | Value |
|---|---|
| bInterfaceNumber | `00` |
| bInterfaceClass | `02` |
| bInterfaceSubClass | `02` |
| bInterfaceProtocol | `01` |
| bNumEndpoints | `01` |
| Interface | `CDC Abstract Control Model (ACM)` |
| Driver | `cdc_acm` |

Endpoint:

| Endpoint | Type | Direction | Interval | Max packet |
|---|---|---|---:|---:|
| `ep_82` | Interrupt | IN | 32ms | `0x000a` |

### Interface 1

| Field | Value |
|---|---|
| bInterfaceNumber | `01` |
| bInterfaceClass | `0a` |
| bInterfaceSubClass | `00` |
| bInterfaceProtocol | `00` |
| bNumEndpoints | `02` |
| Interface | `CDC ACM Data` |
| Driver | `cdc_acm` |

Endpoints:

| Endpoint | Type | Direction | Interval | Max packet |
|---|---|---|---:|---:|
| `ep_81` | Bulk | IN | 0ms | `0x0400` |
| `ep_01` | Bulk | OUT | 0ms | `0x0400` |

의미:

- host에서 ADB, RNDIS, NCM, MTP interface는 보이지 않는다.
- 현재 안정성이 높은 이유는 function이 ACM 하나뿐이고, Android property/service 없이 kernel composite gadget만으로 동작하기 때문이다.

## ADB 상태

현재 `startadbd` 경로:

1. Android layout 준비
2. `/config/usb_gadget/g1/functions/ffs.adb` 생성
3. `/dev/usb-ffs/adb`에 FunctionFS mount
4. `configs/b.1/f2 -> functions/ffs.adb` symlink 생성
5. 필요 시 UDC rebind
6. `/apex/com.android.adbd/bin/adbd` exec

과거 native shell 실측:

```text
/dev/usb-ffs/adb/ep0 exists
ep1/ep2 missing
adbd zombie
```

해석:

- FunctionFS mount 자체는 된다.
- `ep1`/`ep2`는 userspace driver가 `ep0`에 descriptors/strings를 쓴 뒤 생성된다.
- 현재 `adbd`는 Android property service, SELinux context, bionic/apex/runtime 환경 없이 단독으로 안정 실행되지 않는다.
- 따라서 ADB는 `serial -> USB networking -> SSH/custom TCP shell`보다 우선순위가 낮다.

## USB Networking 후보

가능한 방향:

- `rndis.usb0`
- `ncm.usb0`
- `ecm.usb0`

현재 판단:

- host Linux 관점에서는 NCM/ECM이 깔끔하지만, Windows 호환성까지 보면 RNDIS도 후보가 된다.
- 기존 kernel config 관찰에서 RNDIS configfs 지원은 있었지만, native init v47의 active gadget에는 network function이 없다.
- 다음 실험은 ACM을 유지한 채 network function을 추가하는 방식이어야 한다.

권장 순서:

1. 현재 ACM-only boot image를 known-good rescue path로 유지
2. `functions/rndis.usb0` 또는 `functions/ncm.usb0` 생성 가능 여부를 재부팅으로 원복 가능한 probe로 확인
3. 새 config `configs/c.1` 또는 기존 `configs/b.1/f2`에 network function 추가
4. UDC rebind 후 host `ip link`에 `usb0`/`enx...` 류 interface 생성 확인
5. device-side IP 설정용 최소 명령 또는 static helper 검토
6. 그 다음에야 dropbear/custom TCP shell 검토

## 안전 규칙

- ACM serial은 항상 rescue/control channel로 유지한다.
- network/ADB 실험은 새 boot image 버전에서만 수행한다.
- UDC rebind는 host serial disconnect를 일으킬 수 있으므로 log와 recovery path가 준비된 상태에서만 실행한다.
- ADB를 다시 시도하더라도 `startadbd`가 zombie가 되면 즉시 serial 기준으로 복귀한다.
- report 작성 시점의 current shell bridge는 열려 있지 않았고 현재 계정은 `dialout` 그룹이 아니어서, device-side live configfs dump는 다음 bridge 세션에서 보강한다.

## 다음 작업

- native init shell에 `usbinfo`/`gadgetinfo` 명령 추가 검토
- network function 생성 가능성 probe용 `usbnetprobe` 명령 또는 별도 v49 image 준비
- host/device 양쪽 IP 설정 전략 정리
- SSH/dropbear 이전에 custom TCP shell 또는 static busybox `nc` 가능성 검토
