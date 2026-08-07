# ADB from Linux Init 실험 기록 (2026-04-23)

이 문서는 Stage 3(native Linux pid 1 진입 성공) 이후,
**Linux init에서 ADB 연결 유지 → 인터랙티브 셸** 확보를 목표로 한
실험 과정을 상세 기록한다.

---

## 출발점 요약

| 항목 | 상태 |
|---|---|
| Stage 3 결과 | 성공 — Android kernel이 static ARM64 init을 pid 1로 실행 |
| 확인 방법 | TWRP에서 `/cache/linux_init_ran = "ok"` 확인 |
| 현재 recovery | TWRP |
| 복구 수단 | `backups/baseline_a_20260423_030309/boot.img` dd 복구 |
| 폰 상태 | TWRP에서 작업 중 |

---

## 목표

`adb devices` 정상 → `adb shell` → 인터랙티브 Linux 셸

---

## 사전 조사

### adbd 위치 및 의존성 (Android 실행 중 조사)

- adbd 바이너리: `/apex/com.android.adbd/bin/adbd` (APEX 모듈)
  - `/system/bin/adbd` 없음
  - APEX init.rc: `service adbd /apex/com.android.adbd/bin/adbd --root_seclabel=u:r:su:s0`
- ELF INTERP (동적 링커): `/system/bin/linker64`
  - 실체: `/system/bin/linker64` → symlink → `/apex/com.android.runtime/bin/linker64`
- adbd 직접 의존 라이브러리 (readelf -d):
  - APEX adbd lib64: `libbase`, `libadb_protos`, `libcrypto`, `libc++`, `libcutils`,
    `libprotobuf-cpp-lite`, `libcrypto_utils`, `libadb_pairing_*`, `libadbconnection_client`
  - system lib64: `libadbd_fs`, `libadbd_auth`, `liblog`, `libselinux`
  - bionic (com.android.runtime): `libc`, `libm`, `libdl`
- `libselinux` 추가 의존: `libpcre2`, `libpackagelistparser`

### USB gadget 조사 (Android 실행 중)

- configfs 위치: `/config` (Android mount: `none /config configfs`)
- 현재 gadget: `g1`
  - VID: `0x04e8`, PID: `0x6860`, UDC: `a600000.dwc3`
  - `g1/configs/b.1/f4` → `ffs.adb`
- functionfs: `adb /dev/usb-ffs/adb functionfs`
- ADB 활성화 순서 (init.qcom.usb.rc 기준):
  1. `start adbd` (adbd가 `/dev/usb-ffs/adb/ep0`에 descriptor 기록)
  2. `sys.usb.ffs.ready=1` 감지 후
  3. `ffs.adb → configs/b.1/f1` 심링크
  4. `UDC = a600000.dwc3` 기록

### sda28 구조 조사 (system-as-root)

TWRP에서 sda28을 `/mnt/sc`에 직접 마운트하여 확인:

| 경로 | 내용 |
|---|---|
| `sda28:/` | system-as-root 루트 (전체 Android 루트) |
| `sda28:/bin` | symlink → `/system/bin` (**절대 경로 심링크**) |
| `sda28:/lib64` | symlink → `/system/lib64` (절대 경로 심링크) |
| `sda28:/apex/` | 빈 디렉토리 (apexd가 런타임에 채움) |
| `sda28:/system/` | 실제 Android system 디렉토리 |
| `sda28:/system/bin/linker64` | symlink → `/apex/com.android.runtime/bin/linker64` |
| `sda28:/system/lib64/` | libadbd_fs, libadbd_auth, liblog, libselinux 등 |
| `sda28:/system/apex/com.android.adbd/` | APEX 디렉토리 (flattened, bin/adbd 포함) |
| `sda28:/system/apex/com.android.runtime/` | APEX 디렉토리 (linker64, bionic 포함) |

### 초기 부팅 시 block device minor 번호

sdd LUN이 등록되기 전(초기 부팅 시점)의 blkext(259) 할당:

| 파티션 | 런타임 minor | 초기 부팅 minor | 근거 |
|---|---|---|---|
| sda31 (cache) | 259:34 | **259:15** | Stage 3 실증 (mknod→mount→파일 TWRP 확인) |
| sda28 (system) | 259:31 | **259:12** | sda16=259:0 기준 역산 |

원리: 런타임에는 sdd16-sdd34(19개)가 259:0~18을 선점하여 sda16+가 259:19 이후로 밀림.
초기 부팅 시점에는 sdd 미등록 상태이므로 sda16=259:0부터 시작.

---

## 시도 목록

### 시도 1 — sda28을 /system에 마운트 후 adbd exec

**코드 (`init_v2.c` v1)**:
```
mknod sda28 → makedev(259, 12)
mount sda28 → /system
symlink /system/apex/com.android.adbd → /apex/com.android.adbd
exec /apex/com.android.adbd/bin/adbd
```

**결과**: `adbd_exec_failed = 040` → **errno 40 = ELOOP**

**원인 분석**:  
sda28 루트의 `/bin`이 `→ /system/bin` (절대 경로 심링크).  
sda28을 `/system`에 마운트하면:
- `/system/bin` = sda28의 `/bin` = symlink `→ /system/bin`
- 커널이 `/system/bin` 해석 시 sda28의 `/bin`을 따라가면
  다시 `/system/bin` 절대 경로로 → 무한 루프 → ELOOP

adbd ELF INTERP = `/system/bin/linker64`이므로 커널이 이 경로 해석 중 ELOOP 발생.

---

### 시도 2 — sda28을 /rootfs에 마운트 + /rootfs/system → /system bind mount

**코드 (`init_v2.c` v2)**:
```
mount sda28 → /rootfs
mount --bind /rootfs/system → /system    (MS_BIND)
symlink /system/apex/com.android.adbd → /apex/com.android.adbd
exec /apex/com.android.adbd/bin/adbd
LD_LIBRARY_PATH=/apex/com.android.adbd/lib64:/system/system/lib64:/system/lib64
```

**결과**: `adbd_exec_failed = 002` → **errno 2 = ENOENT**

**원인 분석**:  
bind mount 결과를 cache에 기록하는 코드가 cache mount 전에 실행됨 →  
bind mount 성공/실패 여부 확인 불가.  
ENOENT = `/apex/com.android.adbd/bin/adbd` 없음  
→ `/system/apex/com.android.adbd/` 비어 있음  
→ bind mount가 실제로 실패했거나, 심링크 경로가 틀림.

심링크를 `/system/apex/com.android.adbd` (sda28 루트의 /apex/ = 빈 디렉토리)로 설정한 것이 오류.  
sda28을 /system에 마운트했을 때 실제 adbd 경로는 `/system/system/apex/com.android.adbd/bin/adbd`.

---

### 시도 3 — 모든 파일을 ramdisk에 번들링

**코드 (`init_v2.c` v2b)**:

ramdisk에 직접 포함:
- `/apex/com.android.adbd/bin/adbd`
- `/apex/com.android.adbd/lib64/*.so` (11개)
- `/apex/com.android.runtime/bin/linker64` (실제 바이너리)
- `/apex/com.android.runtime/lib64/bionic/*.so` (libc, libm, libdl, libdl_android)
- `/system/bin/linker64` → symlink → `/apex/com.android.runtime/bin/linker64`
- `/system/lib64/*.so` (libadbd_fs, libadbd_auth, liblog, libselinux, libpcre2, libpackagelistparser)

**결과 1차**: `adbd_exec_failed = 013` → **errno 13 = EACCES**

추가 조사:
- CPIO 내 adbd 권한: `-rw-r--r--` (**exec bit 없음** — `adb pull`이 제거)
- linker64 실제 바이너리 없음 (`ln -sf`로 심링크 교체 후 원본 사라짐)

수정 후 2차 빌드:
- `chmod 755` for adbd, linker64, 모든 .so
- linker64 실제 바이너리를 `/apex/com.android.runtime/bin/linker64`에 배치

**결과 2차**: 동일 — `adbd_exec_failed = 013` (EACCES)

**원인 분석**:  
파일 권한이 정상(rwxr-xr-x)임에도 EACCES 지속.  
**가설: initramfs(tmpfs)가 noexec로 마운트됨.**

근거:
- 커널이 pid 1을 시작할 때는 `kernel_execve()`를 사용 → noexec 체크 없음
- 하지만 pid 1이 `fork() + execve()`를 호출하면 userspace syscall로 noexec 체크 적용
- Android kernel (SM8150)에서 initramfs tmpfs에 noexec 패치가 있을 가능성
- init 자체는 정상 실행되지만 init이 fork 후 자식에서 exec하는 파일이 EACCES

---

### 시도 4 (현재 진행 중) — /cache (ext4)에서 exec

**설계 원리**:
- ext4 파티션은 기본적으로 noexec 아님
- 실행 파일을 /cache에 배치하면 init의 fork+execve가 noexec를 우회
- ELF INTERP `/system/bin/linker64`는 ramdisk의 심링크로 만들어 `/cache/adb/linker64`를 가리키게 함
  - 심링크 자체는 noexec와 무관 (파일이 아님)
  - 커널이 심링크 따라가서 `/cache/adb/linker64` (ext4)를 로드 → exec 가능

**TWRP에서 배치 (사전 준비)**:
```
/cache/adb/adbd              (chmod 755)
/cache/adb/linker64          (chmod 755)
/cache/adb/lib/              (21개 .so, chmod 755)
```

**코드 (`init_v2.c` v2c)**:
```
mount sda31 → /cache (ext4)
symlink /cache/adb/linker64 → /system/bin/linker64 (ramdisk에 심링크)
configfs + USB gadget + functionfs 설정
exec /cache/adb/adbd
LD_LIBRARY_PATH=/cache/adb/lib
```

**현재 상태**: 플래시 완료, 결과 대기 중

---

## 핵심 발견 사항 (이번 세션)

| 발견 | 내용 |
|---|---|
| sda28 구조 | system-as-root. /bin, /lib64는 /system/bin, /system/lib64로의 절대 심링크 |
| /apex/ | sda28 루트의 /apex/는 빈 디렉토리 — apexd가 런타임에 채움 |
| adbd 실제 위치 | sda28:/system/apex/com.android.adbd/bin/adbd |
| linker64 실제 위치 | sda28:/system/apex/com.android.runtime/bin/linker64 |
| bionic 위치 | sda28:/system/apex/com.android.runtime/lib64/bionic/ |
| ELOOP 원인 | sda28을 /system에 마운트 시 /bin→/system/bin 절대심링크 루프 |
| ENOENT 원인 | /apex/는 빈 디렉토리. 실제 adbd는 /system/apex/에 있음 |
| EACCES 원인 (가설) | initramfs(tmpfs) noexec + adb pull exec bit 제거 |
| adb pull 주의사항 | **exec bit 보존 안 됨** → 반드시 수동 chmod 755 필요 |
| init-time minor | sda28=259:12, sda31=259:15 (sdd 미등록 시점 기준) |
| USB gadget | configfs g1, ffs.adb function, UDC=a600000.dwc3 |
| USB gadget 순서 | adbd 먼저 실행 → ep0 descriptor 기록 후 UDC 활성화 (3초 간격) |

---

## 파일 경로 요약

```
stage3/linux_init/init_v2.c          v2c init 소스 (adbd + functionfs)
stage3/ramdisk_v2c.cpio              v2c ramdisk
stage3/boot_linux_v2c.img            v2c boot 이미지
stage3/linux_init/init_v3.c          v3 init 소스 (USB ACM mini-shell)
stage3/ramdisk_v3.cpio               v3 ramdisk
stage3/boot_linux_v3.img             v3 boot 이미지
backups/baseline_a_20260423_030309/  복구용 기준점 백업
```

복구 명령:
```bash
adb shell "dd if=/data/local/tmp/boot.img of=/dev/block/by-name/boot bs=4096 && sync"
# 또는 TWRP에서:
# dd if=/cache/boot_backup.img of=/dev/block/by-name/boot
```

---

## 다음 단계 후보

### 사후 확인 (TWRP recovery에서 2026-04-23 재점검)

- `adb devices -l` 기준 장치는 현재 `recovery`(`product:twrp_r3q`)로 연결됨
- `/cache/v2c_step = 9_udc_set` 확인
  - 즉, `v2c`는 최소한 configfs/functionfs 설정과 UDC 활성화까지 도달
- `/cache/adbd_exec_failed = 013` 파일은 남아 있으나,
  `v2c_step`보다 이른 타임스탬프라 **이전 시도의 잔존물일 가능성**이 큼
- TWRP 셸에서 `LD_LIBRARY_PATH=/cache/adb/lib /cache/adb/adbd --help` 실행 시
  `Permission denied`가 아니라 **Segmentation fault (rc=139)** 발생
  - 따라서 `v2c`의 핵심 실패점은 `EACCES`보다 `adbd` 자체 초기화/런타임 크래시일 가능성이 더 높음
- 커널 설정 확인:
  - `CONFIG_USB_CONFIGFS_ACM=y`
  - `CONFIG_USB_F_ACM=y`
  - `CONFIG_USB_CONFIGFS_RNDIS=y`
  - 즉, `ADB/functionfs`를 버리고 **USB ACM serial** 또는 **RNDIS**로 우회 가능

### 다음 단계

- `v3` (`init_v3.c`)로 부팅:
  - configfs `acm.usb0` gadget 생성
  - `/dev/ttyGS0` 대기
  - USB ACM serial 위에서 built-in mini-shell 제공
- 현재 실측 결과:
  - `twrp reboot system` 후 host `lsusb`에 `04e8:6861` (`SAMSUNG_Android`)로 재열거
  - `adb devices -l`는 빈 목록
  - host에 `/dev/ttyACM0` 및 `/dev/serial/by-id/usb-SAMSUNG_SAMSUNG_Android_DEVICE-A90-01-if00` 생성
  - 즉, **ADB-less native init → USB ACM gadget 활성화** 까지는 성공
- 호스트 측 접속 예상:
  - `screen /dev/ttyACM0 115200`
  - 또는 `socat -,rawer,echo=0 /dev/ttyACM0,rawer,echo=0`
- 현재 Codex 세션은 host `dialout` 그룹 권한이 없어 `/dev/ttyACM0`를 열지 못함
  - `Permission denied`
  - 따라서 mini-shell 배너/명령 응답 최종 검증은 사용자 측 serial open 1회가 필요
- `v3`가 뜨면 우선 확인:
  - `/cache/v3_step`
  - shell prompt 출력 여부
  - `uname`, `mounts`, `ls /dev`, `cat /proc/partitions`
- `v3`가 실패하면 다음 분기:
  - `v3_step` 단계값으로 gadget/tty 생성 실패 구간 식별
  - 필요 시 `RNDIS + 정적 도구` 경로로 전환

---

## 현재 폰 상태

- boot: 직전 실험은 `boot_linux_v2c.img`, 다음 후보는 `boot_linux_v3.img`
- recovery: TWRP
- /cache: `/cache/adb/` 에 adbd + libs 배치됨
- /cache 마커:
  - `v2c_step = 9_udc_set`
  - `adbd_exec_failed = 013` (해석 보류)
- 기준점 복구: `backups/baseline_a_20260423_030309/boot.img` dd 가능
