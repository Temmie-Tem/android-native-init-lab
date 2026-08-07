# A90 5G Native Linux Init 실험 기록 (2026-04-23)

## 개요

이 문서는 `SM-A908N (A908NKSU5EWA3)` 장치에서 Android kernel 위에
native Linux init을 pid 1로 실행하는 데 성공한 과정을 기록한다.
모든 결정에는 관찰값과 근거를 병기하며, 실패와 수정 과정도 생략 없이 남긴다.

---

## 기준점 A (실험 출발점)

| 항목 | 값 |
|---|---|
| 디바이스 | SM-A908N, DEVICE-A90-01 |
| 빌드 | A908NKSU5EWA3 / Android 12 |
| AP | Magisk 30.7 패치 boot.img |
| Recovery | stock (이후 TWRP로 교체) |
| ADB | 정상 |
| root | `su -c id` → `uid=0 context=u:r:magisk:s0` |
| `ro.boot.verifiedbootstate` | `orange` |
| `ro.boot.flash.locked` | `0` |
| `ro.boot.warranty_bit` | `1` (Knox tripped) |

---

## Stage 0: 기준점 캡처

### 목적

모든 실험 전 boot / recovery / vbmeta 이미지를 로컬에 저장한다.
실험이 잘못됐을 때 `dd`로 즉시 복구할 수 있어야 한다.

### 실행

```bash
./scripts/revalidation/verify_device_state.sh
./scripts/revalidation/capture_baseline.sh --label baseline_a
```

### 발견된 문제

`capture_baseline.sh`가 `by-name partition directory` 탐색에서 실패했다.

**원인 분석**: 스크립트 내부 명령이
```bash
adb shell su -c "for path in ...; do ...; done"
```
형태였는데, `adb shell`이 명령줄을 디바이스 shell로 전달할 때 공백 분리가 일어나
Magisk `su -c`가 `for` 뒤를 독립 토큰으로 받아서 `syntax error: unexpected 'do'`가 발생했다.

**근거**: 수동으로 `adb shell "su -c 'for ... do ... done'"` 형태로 단일 따옴표로
묶으면 정상 동작하는 것을 확인. Magisk su -c는 단일 토큰 인자만 처리한다.

**수정**: `sq_escape()` 헬퍼를 `capture_baseline.sh`에 추가.
```bash
sq_escape() {
    local s="${1//\'/\'\\\'\'}"
    printf "'%s'" "$s"
}
# 사용 예
adb shell "su -c $(sq_escape "$cmd")"
```

`exec-out su -c "dd if=..."` 형태의 dd 풀 명령에도 동일하게 적용했다.

### 결과

```
backups/baseline_a_20260423_030309/
  boot.img      64MB  sha256: c15ce425...
  recovery.img  82MB  sha256: 8f91ce25...
  vbmeta.img    64KB  sha256: f051caab...
  device_getprop.txt
  by_name_listing.txt
  SHA256SUMS
```

### 다운로드 모드 캡처

`adb reboot download`으로 다운로드 모드 진입 후 화면 사진으로 기록했다.

| 항목 | 값 |
|---|---|
| RPMB | Fuse Set, PROVISIONED |
| CURRENT BINARY | Custom (0x303) |
| OEM LOCK | OFF (U) |
| FRP LOCK | OFF |
| WARRANTY VOID | 0x1 (0xE03) |
| QUALCOMM SECUREBOOT | ENABLE |
| SECURE DOWNLOAD | ENABLE |
| RP SWREV | B5(1,1,1,5,1,1) K5 S5 |
| KG | 사진 크롭 상단 부 미확인 |

**KG 미표시 해석**: Samsung Knox 공식 문서는 다운로드 모드에 KG STATE 줄이
항상 표시된다고 명시하지 않는다. Knox Guard는 cloud-managed state이며
Completed/삭제 후에는 client가 비활성화된다. 따라서 KG 줄 미표시는
`KG = not enrolled` 또는 `KG = completed` 중 하나일 가능성이 있으나,
공식 문서만으로 단정할 수 없으므로 `not shown in Download Mode`로 기록했다.

---

## Stage 1: 기본 4조합 재검증

### 목적

boot / recovery 커스텀 바이너리를 어떤 경계에서 차단하는지 관찰하기 위해
4개 조합을 체계적으로 테스트한다.

### row 2 (patched AP + stock recovery)

**근거**: 현재 기준점 A가 이미 이 조합이므로 플래시 없이 기록할 수 있다.

**관찰값**:
- flash: 이미 완료 상태
- `verifiedbootstate=orange`, `flash.locked=0`
- 첫 부팅: PASS
- recovery fallback: 없음
- ADB / su: 정상

### row 4 (patched AP + TWRP)

**근거**: 현재 기준점에서 recovery 파티션만 교체하면 되므로
`한 번에 한 변수` 원칙에 따라 이 조합을 먼저 시도했다.

**Magisk가 recovery를 건드리지 않는다는 확인**:
patched AP tar(`magisk_patched-30700_I3l18.tar`)와 stock tar를 직접 비교했다.

| 파일 | stock | patched | 변화 |
|---|---|---|---|
| `boot.img.lz4` | 24MB 압축 | `boot.img` 64MB 비압축 | **수정됨** |
| `vbmeta.img.lz4` | 3.4KB 압축 | `vbmeta.img` 8.3KB 비압축 | **수정됨** |
| `recovery.img.lz4` | 38,760,803 bytes | 38,760,803 bytes | **동일** |

Magisk는 boot + vbmeta만 수정한다. recovery는 stock 그대로다.
따라서 TWRP를 recovery에 플래시해도 Magisk root는 유지된다.

**플래시 방법**: Odin 없이 ADB dd로 직접 기록.
```bash
adb push firmware/twrp/recovery.img /data/local/tmp/twrp_recovery.img
adb shell "su -c 'dd if=/data/local/tmp/twrp_recovery.img of=/dev/block/by-name/recovery bs=4M && sync'"
# sha256 검증
adb shell "su -c 'dd if=/dev/block/by-name/recovery bs=4M status=none | sha256sum'"
```

sha256 일치 확인 후 재부팅.

**관찰값**:
- 재부팅 후 정상 시스템 부팅 (recovery fallback 없음)
- "SECURE CHECK FAIL" 문구 없음
- `verifiedbootstate=orange` 유지 (vbmeta Magisk 패치가 TWRP 서명 불일치 흡수)
- ADB / su / Wi-Fi 전부 유지

### row 1, 3 (stock AP 포함)

stock AP 플래시 시 Magisk 소멸 → 이후 롤백 시점에 자연 관찰 예정으로 deferred.

---

## Stage 2: 보안 경계 분해

### 목적

Stage 1 결과를 바탕으로 어느 경계에서 차단이 발생하는지 결론을 강제한다.

### 결론

| 질문 | 관찰 | 결론 |
|---|---|---|
| boot image 수용 여부 | patched AP 정상 부팅 | **허용** |
| recovery 교체 허용 여부 | TWRP 플래시 후 정상 부팅, SECURE CHECK FAIL 없음 | **허용** |
| `official binaries only` 발생 조건 | 미발생 | OEM LOCK OFF(U) + flash.locked=0 + Magisk vbmeta에서 발생 안 함 |
| KG 표기 변화 | 없음 | KG가 차단 요인으로 작용한 증거 없음 |
| factory reset 영향 | 미측정 | stock AP 롤백 시 관찰 예정 |

**최종 결론**: `OEM LOCK OFF(U) + flash.locked=0 + Magisk vbmeta 패치` 조합에서
boot/recovery 커스텀 바이너리 전면 허용. 현 상태에서 보안 차단 경계 없음.

이 결론이 Stage 3 진입의 근거가 됐다.

---

## Stage 3: native Linux init 진입

### 사전 분석: boot.img 구조

```bash
python3 mkbootimg/unpack_bootimg.py \
  --boot_img backups/baseline_a_20260423_030309/boot.img \
  --out /tmp/boot_unpacked
```

출력:
```
boot magic: ANDROID!
kernel_size: 49827613
ramdisk size: 427324
boot image header version: 1
product name: SRPSE29A005
command line args: console=null androidboot.hardware=qcom ...
```

ramdisk 내용 확인:
```
cpio -t < /tmp/boot_unpacked/ramdisk
  .backup/.magisk
  init               ← Magisk init 바이너리
  overlay.d/sbin/init-ld.xz
  overlay.d/sbin/magisk.xz
  overlay.d/sbin/stub.xz
```

**의미**: Magisk는 ramdisk의 `init` 바이너리만 교체한 구조다.
우리가 이 `init` 자리에 Linux init을 넣으면 kernel이 Android 대신 우리 코드를 실행한다.

**Stock firmware 확인**: stock tar에 `init_boot.img`와 `vendor_boot.img` 없음.
GKI(Generic Kernel Image) 기반이 아니라 boot.img header v1 전통 구조.
Magisk가 boot.img 하나만 패치하면 되는 가장 단순한 레이아웃이다.

### 도구 확보

host가 x86_64이므로 ARM64 cross-compiler가 필요했다.

```bash
sudo apt install gcc-aarch64-linux-gnu
```

busybox-static:arm64는 apt에서 찾을 수 없었고 (`dpkg --add-architecture arm64`가
패키지 목록에 없음), cross-compiler로 최소 C init을 직접 빌드하는 방향을 선택했다.
이 방법이 더 가볍고 (수십 KB vs 수 MB) 동작을 완전히 제어할 수 있다.

---

## Stage 3 시도 1: by-name 경로 사용 (실패)

### 코드

```c
mount("/dev/block/by-name/cache", "/cache", "ext4", 0, "");
wf("/cache/linux_init_ran", "ok\n");
sleep(10);
wf("/proc/sysrq-trigger", "b");  // 재부팅
```

### 빌드 및 플래시

```bash
aarch64-linux-gnu-gcc -static -Os -o init init.c
aarch64-linux-gnu-strip init
# ramdisk 조립
cp init stage3/ramdisk_new/init
find stage3/ramdisk_new | cpio -o -H newc > stage3/ramdisk_new.cpio
# 재패킹 (원본 kernel/cmdline/헤더 그대로)
python3 mkbootimg/mkbootimg.py --kernel /tmp/boot_unpacked/kernel \
  --ramdisk stage3/ramdisk_new.cpio [원본 헤더 인자들] \
  -o stage3/boot_linux_init.img
# 플래시
adb shell "su -c 'dd if=/data/local/tmp/boot_linux_init.img of=/dev/block/by-name/boot bs=4M && sync'"
```

### 결과

`/cache/linux_init_ran` 없음. Samsung 부트루프 보호가 작동해 boot 파티션을
다른 이미지로 자동 교체했다.

### 원인 분석

`/dev/block/by-name/cache` 심링크는 Android의 `ueventd`가 udev 규칙을 처리해
생성한다. ueventd는 Android init의 일부이므로, 우리 init이 Android init을 대체한
상태에서는 by-name 아래가 비어 있다.

**확인 방법**: `adb shell 'su -c "ls /dev/block/by-name/cache"'` → 존재함 (Android 기동 후).
TWRP에서 `ls /dev/block/by-name/cache` → 존재함 (TWRP의 자체 ueventd).
초기 부팅 ramdisk 단계 → ueventd 없으므로 by-name 비어 있음.

---

## Stage 3 시도 2: sda31 직접 경로 + 무한 대기 (실패)

### 수정

`/dev/block/by-name/cache` → `/dev/block/sda31` 직접 경로.
sysrq 재부팅 제거 후 무한 대기.

### 결과

또 실패. `/cache/linux_init_ran` 여전히 없음.

### 원인 분석이 필요한 상황

init이 실행되는지 자체가 불확실해졌다. `/proc/last_kmsg`를 확인했으나
Samsung XBL 부트로더 로그만 나왔고 (Linux kernel ring buffer가 아님),
pstore `console-ramoops-0`는 현재 Android 부팅 로그로 이미 덮어씌워져 있었다.

---

## Stage 3 진단: 타이밍 테스트 (결정적 증거)

### 근거

init 실행 여부 자체를 확인하려면 side effect만 있는 최소 바이너리가 필요했다.
`sleep(30)` 후 `reboot(RB_AUTOBOOT)`를 실행하면:
- init이 실행됐다면 → 검은 화면(또는 Samsung 경고 화면) 정확히 30초
- init이 실행 안 됐다면 → 즉각 TWRP/Android 부팅

### 코드

```c
int main(void) {
    sleep(30);
    reboot(RB_AUTOBOOT);
    while (1) {}
}
```

### 결과

**Samsung 경고 화면이 정확히 30초 지속된 후 자동 재부팅.**

**해석**:
- Samsung 경고 화면(비공식 소프트웨어 문구)은 ABL(Android Boot Loader)이
  kernel/init에 제어를 넘기기 전에 표시한다.
- 경고 화면이 30초 지속됐다는 것은 우리 init이 실행되고 sleep 중이었다는 뜻이다.
- `reboot(RB_AUTOBOOT)`가 30초 후 정확히 작동해 재부팅이 일어났다.

**결론: init은 실행되고 있었다.** 문제는 `/dev/block/sda31` 노드가
devtmpfs 마운트 직후 아직 존재하지 않아 mount가 실패하는 것이었다.

---

## Stage 3 원인: devtmpfs async 초기화

### 분석

UFS(Universal Flash Storage) 드라이버는 비동기로 초기화된다.
Android init은 ueventd를 통해 udev 이벤트를 처리하며 block 디바이스 노드가
준비될 때까지 대기하는 내부 로직이 있다.

우리 init은 `mount("devtmpfs", ...)` 직후 바로 `/dev/block/sda31`에 접근하므로
UFS 드라이버가 아직 block 디바이스를 등록하지 않은 시점일 수 있다.

**devtmpfs 내 block 디바이스 타이밍 확인**:
pstore에서 `sda31`이 처음 나타나는 시점:
```
[    0.845085] sda: sda1 sda2 ... sda31 sda32 sda33
```
커널 시작 후 0.845초에 UFS가 초기화된다. 그러나 devtmpfs의 async 특성상
노드 생성이 실제 마운트 시도보다 늦을 수 있다.

### 해결책: mknod으로 직접 생성

TWRP에서 sda31의 major:minor를 확인했다.
```
brw------- 1 root root 259, 15 /dev/block/sda31
Device type: 103,f  (= hex 0x103=259, 0xf=15)
```

init에서 devtmpfs 마운트 후 직접 mknod:
```c
mkdir("/dev/block", 0755);
mknod("/dev/block/sda31", S_IFBLK | 0600, makedev(259, 15));
```

이렇게 하면 UFS async 초기화 타이밍에 완전히 독립적이다.
major:minor는 하드웨어와 파티션 번호로 결정되므로 리부팅 간 변하지 않는다.

---

## Stage 3 시도 3: mknod 직접 생성 (성공)

### 최종 init.c

```c
#include <fcntl.h>
#include <sys/mount.h>
#include <sys/stat.h>
#include <sys/sysmacros.h>
#include <unistd.h>
#include <string.h>

static void wf(const char *path, const char *s) {
    int fd = open(path, O_WRONLY | O_CREAT | O_TRUNC, 0644);
    if (fd < 0) return;
    write(fd, s, strlen(s));
    close(fd);
}

int main(void) {
    mkdir("/proc",  0755);
    mkdir("/sys",   0755);
    mkdir("/dev",   0755);
    mkdir("/cache", 0755);

    mount("proc",     "/proc", "proc",    0, NULL);
    mount("sysfs",    "/sys",  "sysfs",   0, NULL);
    mount("devtmpfs", "/dev",  "devtmpfs",0, "mode=0755");

    wf("/dev/kmsg", "<6>A90_LINUX_INIT: step1 mounts done\n");

    mkdir("/dev/block", 0755);
    mknod("/dev/block/sda31", S_IFBLK | 0600, makedev(259, 15));

    wf("/dev/kmsg", "<6>A90_LINUX_INIT: step2 mknod done\n");

    if (mount("/dev/block/sda31", "/cache", "ext4", 0, "") == 0) {
        wf("/dev/kmsg",             "<6>A90_LINUX_INIT: step3 cache mounted OK\n");
        wf("/cache/linux_init_ran", "ok\n");
        sync();
        wf("/dev/kmsg",             "<6>A90_LINUX_INIT: step4 marker written\n");
    } else {
        wf("/dev/kmsg", "<6>A90_LINUX_INIT: step3 cache mount FAILED\n");
    }

    while (1) { sleep(60); }
}
```

### 빌드

```bash
aarch64-linux-gnu-gcc -static -Os -o init init.c
aarch64-linux-gnu-strip init
# → 663KB stripped static ELF, ARM aarch64
```

### 결과

TWRP에서 확인:
```bash
adb shell "cat /cache/linux_init_ran"
# → ok
adb shell "ls -la /cache/linux_init_ran"
# → -rw-r--r-- 1 root root 3 2018-01-03 04:54 /cache/linux_init_ran
```

**성공**.

---

## 종합 관찰값

| 항목 | 결과 |
|---|---|
| init 실행 (pid 1) | ✓ confirmed (30초 타이밍 테스트) |
| proc 마운트 | ✓ |
| sysfs 마운트 | ✓ |
| devtmpfs 마운트 | ✓ |
| ext4 파티션 마운트 (sda31 = /cache) | ✓ mknod(259:15)으로 우회 |
| 파일 쓰기 | ✓ `/cache/linux_init_ran = "ok"` |
| Android 프로세스 없음 | ✓ (zygote, system_server 등 미실행) |
| Samsung 부트루프 보호 | 관찰됨 — sysrq 재부팅 반복 시 boot 파티션 자동 교체 |

---

## 핵심 발견 사항

1. **Samsung 부트루프 보호**: 부팅 후 Android init이 정상 완료되지 않으면
   Samsung 부트로더가 boot 파티션을 자동으로 다른 이미지로 교체한다.
   이를 피하려면 init에서 재부팅하지 말고 무한 대기해야 한다.

2. **devtmpfs async 초기화**: `mount("devtmpfs", ...)` 직후 `/dev/block/by-name/`
   심링크와 `/dev/block/sdaXX` 노드가 즉시 존재하지 않는다.
   해결책: `mknod(makedev(major, minor))`으로 직접 생성.

3. **by-name 심링크는 ueventd 의존**: `/dev/block/by-name/` 아래는 Android의
   ueventd가 udev 이벤트를 처리해 채운다. Android init을 대체한 환경에서는
   이 심링크들이 존재하지 않는다.

4. **OEM LOCK OFF(U) + flash.locked=0 + Magisk vbmeta 패치 = 차단 없음**:
   Stage 1/2에서 확인한 대로 이 조합에서는 boot/recovery 커스텀 바이너리를
   부트로더가 차단하지 않는다.

---

## 다음 목표

**Linux init에서 ADB 연결 유지 → 인터랙티브 셸**

현재 init은 파일시스템 동작을 확인했지만 외부 관찰 채널이 없다.
다음 단계로 USB ADB 연결을 유지하는 방법을 확보해야 한다.

접근 후보:
1. `/sys/class/android_usb` 또는 configfs로 USB gadget ADB 모드 활성화 후
   Android의 `/system/bin/adbd` 실행 (system 파티션 마운트 필요)
2. static으로 빌드한 dropbear (SSH) 또는 telnetd 탑재
3. TWRP ADB 채널 활용 (recovery 파티션을 관찰 창으로 사용)

**복구 기준점**: `backups/baseline_a_20260423_030309/boot.img` (sha256: `c15ce425...`)를
TWRP에서 `dd`로 복구하면 Magisk root가 즉시 복원된다.
