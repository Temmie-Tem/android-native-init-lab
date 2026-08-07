# Bootchain Revalidation Matrix (2026-04-23)

이 문서는 `native Linux rechallenge`의 실제 작업 시트입니다.
자동 수집 가능한 값은 스크립트로 저장하고,
다운로드 모드 화면 값과 플래시 후 관찰값은 여기 수동으로 채웁니다.

## 기준점 A 스냅샷

현재 알려진 기준점:

- 디바이스: `SM-A908N`
- 빌드: `A908NKSU5EWA3`
- Android 12 stock 기반
- patched AP 부팅 성공
- `Magisk 30.7`
- ADB 가능
- `su` 가능
- Wi-Fi 가능
- `user 0` 패키지 수: `92`

다음 항목은 다음 실험 전 캡처 필요:

| Item | Value | Status |
| --- | --- | --- |
| capture label | `baseline_a_20260423_030309` | captured |
| capture serial | `DEVICE-A90-01` | captured |
| by-name path | `/dev/block/by-name` | captured |
| boot backup path | `backups/baseline_a_20260423_030309/boot.img` (sha256 `c15ce425…3057b`) | captured |
| recovery backup path | `backups/baseline_a_20260423_030309/recovery.img` (sha256 `8f91ce25…2bb68`) | captured |
| vbmeta backup path | `backups/baseline_a_20260423_030309/vbmeta.img` (sha256 `f051caab…919f6`) | captured |
| `ro.product.model` | `SM-A908N` | captured |
| `ro.build.fingerprint` | `samsung/r3qks/r3q:12/SP1A.210812.016/A908NKSU5EWA3:user/release-keys` | captured |
| `ro.boot.verifiedbootstate` | `orange` | captured |
| `ro.boot.flash.locked` | `0` | captured |
| `ro.boot.warranty_bit` | `1` (Knox tripped) | captured |
| `ro.boot.vbmeta.device_state` | empty string | captured |
| `sys.boot_completed` | `1` | captured |
| `su -c id` | `uid=0(root) … context=u:r:magisk:s0` | captured |
| Wi-Fi status | connected to `Whaletale 5G`, RSSI -49 | captured |
| `RPMB` | `Fuse Set`, `PROVISIONED` | captured from photo |
| `CURRENT BINARY` | `Custom (0x303)` | captured from photo |
| `FRP LOCK` | `OFF` | captured from photo |
| `OEM LOCK` | `OFF (U)` | captured from photo |
| `WARRANTY VOID` | `0x1 (0xE03)` | captured from photo |
| `QUALCOMM SECUREBOOT` | `ENABLE` | captured from photo |
| `RP SWREV` | `B5(1,1,1,5,1,1) K5 S5` | captured from photo |
| `SECURE DOWNLOAD` | `ENABLE` | captured from photo |
| `DID` | `2030A54C447F3A11` | captured from photo |
| KG | not visible in supplied photo crop | still needed |
| custom binary message | no extra warning text visible in supplied photo crop | partial |

권장 캡처 명령:

```bash
./scripts/revalidation/verify_device_state.sh
./scripts/revalidation/capture_baseline.sh --label baseline_a
```

다운로드 모드 사진 메모:

- 이번 사진은 상단 일부만 포함하고 있어 `KG STATE` 줄은 확인되지 않음
- 대신 `CURRENT BINARY`, `OEM LOCK`, `FRP LOCK`, `WARRANTY VOID`,
  `QUALCOMM SECUREBOOT`, `SECURE DOWNLOAD`는 판독 가능

## Web Recheck: KG line absent

`2026-04-23`에 Samsung Knox 공식 문서만 기준으로 다시 확인한 결과:

- Knox Guard는 Samsung의 cloud-managed device state이며, 장치는 콘솔에 추가되고
  부팅 후 네트워크에 연결되어 실제로 enroll 되어야 `Active` 상태가 됩니다.
- 관리가 끝나 `Completed`가 되거나 삭제되면, Knox Guard client는
  비활성화되거나 영구 제거되고 더 이상 추적되지 않습니다.
- Samsung 공식 문서에서는 `Download Mode` 화면에 `KG STATE` 줄이
  항상 표시된다고 명시하지 않습니다.

현재 작업 가설:

- `KG` 줄이 다운로드 모드에 아예 안 보이는 경우는 공식 문서와 모순되지 않습니다.
- 다만 Samsung 공식 문서는 다운로드 모드 UI 표시 규칙 자체를 설명하지 않으므로,
  `왜` 안 보이는지까지는 공식 문서만으로 단정할 수 없습니다.
- 따라서 이번 기준점에서는 `KG = not shown in Download Mode`를
  하나의 관찰값으로 기록하고, 이를 `Prenormal/Normal/Locked` 중 특정 값으로
  자동 환산하지 않습니다.

공식 근거:

- Samsung Knox Guard overview:
  https://docs.samsungknox.com/admin/knox-guard/
- Samsung Knox Guard status / lifecycle:
  https://docs.samsungknox.com/dev/knox-guard/how-knox-guard-works/
- Samsung Knox Guard completed state:
  https://docs.samsungknox.com/admin/knox-guard/kbas/what-happens-to-device-once-it-is-fully-paid/
- Samsung Knox Guard hardened security notes:
  https://docs.samsungknox.com/admin/knox-guard/how-to-guides/manage-devices/view-device-details/

## Stage 1: 기본 4조합 결과표

| ID | AP | Recovery | Factory reset | Flash result | Download mode / KG note | First boot | Recovery fallback | ADB | `su` | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | stock | stock | | deferred — stock AP 롤백 시 자연 관찰 예정 | | | | | | |
| 2 | patched | stock | no | PASS (current baseline A) | CURRENT BINARY: Custom (0x303), OEM LOCK: OFF (U), KG: not shown | PASS | no | PASS | PASS | `verifiedbootstate=orange`, `flash.locked=0`, `warranty_bit=1`, Magisk 30.7 su context |
| 3 | stock | TWRP | | deferred — stock AP 롤백 시 자연 관찰 예정 | | | | | | |
| 4 | patched | TWRP | no | PASS (dd + sha256 verified) | CURRENT BINARY: Custom (0x303), OEM LOCK: OFF (U), KG: not shown (same as row 2) | PASS | no | PASS | PASS | `verifiedbootstate=orange` 유지, Magisk 30.7 root 유지, Wi-Fi 유지 |

## Stage 2: 보안 경계 분해

| Question | Observation | Conclusion |
| --- | --- | --- |
| boot image 수용 여부 | patched AP(Magisk) 정상 부팅, `verifiedbootstate=orange` | **허용** — OEM LOCK OFF(U) + flash.locked=0 + vbmeta AVB 비활성 조합에서 custom boot 전면 수용 |
| recovery 교체 허용 여부 | TWRP dd 플래시 후 정상 시스템 부팅, recovery fallback 없음, "SECURE CHECK FAIL" 없음 | **허용** — 동일 조건에서 custom recovery도 전면 수용 |
| `official binaries only` 발생 조건 | row 2/4 모두 미발생 | OEM LOCK OFF(U) + flash.locked=0 + Magisk vbmeta 패치 상태에서는 발생 조건 충족 안 됨 |
| KG 표기 변화와 결과 상관관계 | 다운로드 모드에서 KG 줄 미표시 (baseline, row 2/4 동일) | KG가 부트체인 차단 요인으로 작용한 증거 없음 |
| factory reset 영향 | row 2/4 모두 factory reset 없이 진행 | 미측정 — stock AP 롤백 시 관찰 예정 |

강제 결론 후보:

- ~~`AP 변경은 허용, recovery 변경은 차단`~~ → 불일치 (recovery도 허용됨)
- ~~`custom binary는 일부 경로에서만 허용`~~ → 불일치 (AP/recovery 모두 허용)
- ~~`KG/서명/복구 경계가 실제 차단 지점`~~ → 미발생

**현재 선택 결론**: `OEM LOCK OFF(U) + flash.locked=0 + Magisk vbmeta 패치 = boot/recovery 커스텀 바이너리 전면 허용. 현 상태에서 보안 차단 경계는 확인되지 않음.`

## Stage 3: native Linux 진입 후보

| Priority | Candidate path | Why it stays in scope | Result |
| --- | --- | --- | --- |
| 1 | `patched AP 유지 + Linux ramdisk/init 경로` | boot/recovery 모두 허용 확인 → ramdisk init 교체가 가장 직접적인 경로 | **성공 (2026-04-23)** |
| 2 | `recovery 경로 활용 (TWRP → Linux)` | TWRP 이미 설치됨 | 불필요 (1번 성공) |
| 3 | `vbmeta/부트 이미지 조합 변형` | AVB 이미 비활성 상태 | 불필요 |
| 4 | `TWRP` 기반 보조 경로 | TWRP 설치 완료 | 준비됨 |

### Stage 3 Priority 1 결과 (2026-04-23)

**성공** — Android kernel이 우리 static ARM64 init을 pid 1로 실행함.

실험 구성:
- ramdisk: 비압축 CPIO, `init` 바이너리만 포함 (663KB stripped)
- compiler: `aarch64-linux-gnu-gcc -static -Os`
- sda31 mknod: devtmpfs async 초기화 우회 위해 `makedev(259, 15)` 직접 사용
- 재부팅 없이 무한 대기 → TWRP 강제 진입으로 결과 확인

관찰값:
- Samsung 경고 화면 30초 이상 지속 → init sleep 실행 확인
- TWRP에서 `/cache/linux_init_ran = "ok"` 확인
- proc / sys / devtmpfs / ext4(sda31) 마운트 모두 성공
- Android 프로세스(zygote, system_server 등) 없음 — 완전 대체됨

다음 목표: **ADB 연결 유지** → 진짜 Linux 셸 진입

## 종료 기준 추적

| Stage | Exit condition | Current state |
| --- | --- | --- |
| 1 | 4개 기본 조합 결과표 완성 | row 2/4 완료. row 1/3은 stock AP 롤백 시 자연 기록 예정 |
| 2 | 실제 차단 경계 결론 1개 이상 확보 | 완료 — boot/recovery 모두 허용, 현 상태에서 차단 경계 없음 확인 |
| 3 | Linux 진입 실증 또는 불가능 경계 재정의 | **완료** — pid 1 진입 및 파일시스템 동작 실증. 다음: ADB 유지 |
