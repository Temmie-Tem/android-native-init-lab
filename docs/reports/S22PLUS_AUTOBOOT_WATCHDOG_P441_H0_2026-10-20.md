# S22+ P441 watchdog/idle automatic-boot qualification

Status: **PASS_GO; FRESH_FIXED_D0_AND_TASK_REOPEN_PASS**.
Only fixed read-only Android preparation has run. No P441 grant, transfer,
mode change or native_data write has occurred.
The [committed design](S22PLUS_AUTOBOOT_WATCHDOG_P441_DESIGN_2026-10-20.md)
defines the physical functional aim and comparison limits.

## Selected capability

The new `post-autoboot-p440-v1` selection adds only the two complete P437 files
authenticated by the closed P440 reader to the three retained historical rows.
The resulting immutable table contains 8,974 entries. The original clean
superblock/checker/markers/full-tree checks remain mandatory in both same-boot
admissions. Neither P439's incomplete full-root result nor P440's historical
retrieval substitutes for current admission.

The selected P441 build enables the previously reviewed bounded watchdog
observer in the existing rcS/runlevel parents. It retains the FYG8 diagnostic
kernel, 82 module rows, Debian startup, two filesystem lifetimes, absolute
300000 ms device deadline, 360-second host window, fixed services, NCM/SSH and
physical original-A return. No new C runtime code, process, pet/control write,
persistent file or automatic-recovery claim is introduced.

The physical selection is exactly `cpuidle.off=1`. An H0 comparison archive
uses the retained empty boot command line with the same run, key, initramfs and
executables. Its whole boot image is byte-identical outside the command-line
field. The comparison archive is not a separately VM-qualified physical
candidate, and neither archive is a replay of consumed P437.

The fixed vendor-boot command line, all four selected DTB `bootargs`, and
compiled kernel command line contain no conflicting idle option. The retained
kernel extends rather than forces its compiled command line. The package and
actual-AP consumer positively derive the allowed header; they preserve every
other header byte except the existing ramdisk size field, plus exact kernel
and signature bytes. Existing trailer and ramdisk checks remain.

## H0 findings and checks

The first packaging attempt was correctly rejected because magiskboot removed
the leading space from an empty-base command line. The selector now emits the
canonical argument without that space. The first VM attempt placed the option
after the retained `--`, where it became an extra init argument. Actual parent
measurement rejected it before filesystem work. The VM harness now places the
kernel option before the separator, preserving the initial userspace arguments.
Both failed attempts and their source bytes remain private evidence; neither
is qualification or a device incident.

The corrected physical build has identical A/B static ARM64 entry, hook,
witness and initramfs, with a 147-file runtime source closure. The matched
archives differ only in the selected command-line bytes.

All 85 focused autoboot tests and 12 repository-boundary tests pass, as do
compilation of the 11 changed Python files and the repository boundary check.
The new ten header/history tests cover conflicting boot/vendor options,
hidden command-line padding, overflow, legacy-selection isolation, unchanged
VM init arguments, exact historical metadata, partial capture, cross-boot
join, incomplete records, unhealthy closure and changed bytes. The prior
watchdog producer tests exercise actual C reads and authenticated output on
host and ARM64; their source remains unchanged.

Eight coherently repinned actual-AP mutations are rejected: missing/zero/extra
idle options, hidden command-line padding, reserved header bytes, OS version,
kernel bytes and signature bytes. The original actual AP passes the same
consumer. The final 49-case ARM64 corpus passes the current strict
`vm_results` consumer. Its actual 1,250,851-byte aggregate is published and
reopened; final image/qualification and actual-archive binding pass. The final
AP and boot hashes equal the previously checked idle-disabled paired archive.

Corrected normal-VM records authenticate all eight actors, rcS/runlevel
completion and 120-second local services. Separate pinned SSH health, fixed
shutdown, clean ext4 and durable boot count pass. Its rcS entry occurs after
the observer's 12.5-second
window, so no watchdog samples are produced in that run. This validates the
expired-window integration only; it does not demonstrate Samsung watchdog,
idle behavior or an active early proc sample.

The network-absent VM's forced-stop home view contains an authenticated
19-record runtime prefix, ending at service sample seven. The ordinary local
proof consumer rejects that incomplete view. The existing H0 copy-only
journal-readback procedure recovers 25 records/3,456 bytes and complete local
service proof from a separate regular-file copy. Original disk, extracted
filesystem and raw prefix remain unchanged; device/inode, mode, size and
mtime/ctime are checked, while atime is not asserted. The current strict
copy-readback consumer accepts the provenance. This proves neither live SSH
nor clean shutdown and grants no physical journal replay. The original failed
corpus result stays preserved. Only uncompleted cases continued under the same
frozen build and source closure; the 15 completed cases were reused.

The pending-child fault's parallel VM attempt is also preserved as rejected:
the fork record completes at 15.908 seconds, but the fixed 25-second external
VM stop precedes its earliest first heartbeat at about 25.908 seconds.
Authenticated first wait/sleep returns exist; a heartbeat, exec or reap does
not. After the other cases settled, one isolated H0 attempt with the same
helper, source, predicate and 25-second limit passes: fork-record return is
14.378 seconds and heartbeat return is 24.409 seconds. The required real
heartbeat remains mandatory. Contention is a hypothesis; this covers the
isolated case only, without erasing the earlier miss or proving parallel
timing margin. The aggregate selects 15 original completed cases, 27 resumed
cases, five remaining history cases, this isolated case and the separately
recovered network case, with exclusive completed provenance for every case.

## 과거 실패 체크리스트 적용성

기존 [11개 항목](../operations/S22PLUS_FYG8_PAST_FAILURE_CHECKLIST.md)을 현재
생산자·소비자와 대조했다. 아래의 H0 확인은 실기 성공이나 실행 권한이 아니다.
완료되지 않은 준비·종료 산출물은 확인으로 표시하지 않는다.

| ID | 현재 판정 | 이번 경로의 근거와 남은 범위 |
| --- | --- | --- |
| ABI | H0 확인 / 실기 미확인 | 보존된 커널의 `cpuidle.off` 처리와 WFI 분기는 stock-first 감사 근거를 재사용한다. 실제 boot v4 바이트와 ARM64 C 생산자를 검사했다. 새 숫자 syscall 플래그나 레이아웃은 추가하지 않았으며 Samsung idle/watchdog 동작은 아직 실기 미확인이다. |
| IO | H0 확인 / 병렬 시간 여유 미확인 | 동일 C 관측기의 host/ARM64 시험이 짧은 읽기·EINTR/EIO·close 실패·예산 초과·기록 유실·fd 정리를 검사한다. pending-child의 25초 병렬 시험은 거부 상태로 보존했다. 같은 한도의 단독 시험은 실제 heartbeat 24.409초로 통과했다. 커널 syscall 중단·자동 복구나 병렬 시간 여유는 주장하지 않는다. |
| SEMANTIC | H0 확인 / 실기 미확인 | 초기/설치 PID1, rcS, 서비스, SSH health, 종료 후 파일시스템을 구분했다. 네트워크 부재의 불완전한 원본 기록은 실패로 보존했고 복제본의 서비스 증거를 live SSH/clean shutdown으로 승격하지 않았다. P437 기록과 새 부팅도 구분한다. |
| WIRE | H0 확인 / 실기 미확인 | 실제 C의 인증 프레임과 호스트 decoder 시험, VM의 8개 actor join, 보존된 원시 로그 재해석을 확인했다. 현재 VM에는 이른 watchdog 표본이 없고 새 실기 보존 가능성은 미확인이다. |
| PERSIST | H0·준비 확인 / 실기 종료 미확인 | P440의 두 완전한 파일을 정확한 metadata/hash로 봉인했다. 실제 빌드·개별 VM·AP 음성·복제본 readback·49개 VM 집계·최종 qualification과 현재 prepare/task/proposal을 저장하고 다시 읽었다. 호스트 139개·런타임 147개 소스와 capability를 보존했다. 미래 실기 journal/terminal은 아직 완료 전이다. |
| ROUTE | H0·준비 확인 / 실기 연결 미확인 | 새 선택을 두 admission, 실제 패키징/소비자, 8-actor decoder와 기존 post-closure D0에 연결했다. 첫 VM의 `--` 뒤 인자는 실제 parent 검사에서 거부돼 수정했다. 최종 image qualification과 prepare/reopen이 통과했으며 새 실기 closure 연결은 아직 완료 전이다. |
| ARTIFACT | H0 확인 | 실제 A/B ELF/initramfs/AP 및 동일 payload 비교 이미지의 명령행 외 전체 바이트 일치를 확인했다. 공백 정규화 결함을 실제 packager에서 잡았고 외부 pin까지 맞춘 AP 변조 8개를 거부했다. 전체 49개 VM 결과와 묶인 최종 image/실제 AP 검증도 통과했다. |
| AUDIT | H0 확인 | 실패 원본과 소스 snapshot을 유지한다. 복제본의 journal replay는 쓰기임을 명시하고 원본 내용·신원·mtime/ctime 보존을 대조했다. 기록이 없는 내부 watchdog 단계나 원인은 UNKNOWN으로 남긴다. |
| HOST | 현재 준비 확인 / 실행 시 재검증 필요 | 최종 독립 PASS_GO 후 기존 고정 D0 준비의 17개 capture로 Android health·정확한 GPT·Android32 용량과 같은 부팅의 전후 건강을 확인했다. 현재 호스트 도구·lane·복구 artifact·owner 부재 및 실제 task/proposal 재개방도 통과했다. 실행 시 fresh binding은 여전히 필요하다. |
| DISPLAY | 해당 없음 | 이번 후보는 headless Debian 경로이며 display/HUD를 추가하지 않는다. 화면 부재를 커널/PID1 미도달 근거로 쓰지 않는다. |
| RETURN | H0 확인 / 새 실기 미확인 | 기존 owner 시험의 불확실 전송 no-replay, 한 번의 A와 A 이후 health-only 이어가기를 재사용한다. P440의 건강한 종료는 별도 사실이다. P441은 아직 미실행이며 현장 Download/original-A 복구와 최종 건강이 필요하다. |

## Authority and remaining work

Common details, root revision/digest, the selected target and automatic-boot
policy adopt only this precise variant. The independent final review returns
`PASS_GO / V3_REACHABLE_CAPABILITY` with no findings, binding 139 host and 147
runtime files, the actual package and all 49 VM cases. The public P441 review
binding passes the current capability consumer. Frozen host/runtime copies,
the review and the original failed attempts remain private evidence.

The current fixed foreground D0 preparation passes 17 captures: Android health
before/after on the same boot, exact proposed GPT and Android32 capacity.
Existing host-holder/lane checks and hash-bound original-A/recovery evidence
pass. The actual ready/task/proposal reopen under the qualified capability,
with one `debian-autoboot` operation, 3600 seconds and attended recovery.
There is no grant file or F1 owner. This does not inspect/admit current
native_data or demonstrate a new physical recovery.

The next effect requires the lane's exact returned attended
one-operation/3600-second grant and fresh execution-time machine checks.
Physical Download/original-A recovery remains necessary. No consumed approval
is renewed, no uncertain effect replays, and A does not undo native_data writes.
A90 and S20+ remain outside the work.

Private build, failed-attempt evidence, source snapshots, VM corpus and
comparison artifacts are under
`workspace/private/outputs/s22plus-autoboot-watchdog-p441-h0-20261020-1/`.
