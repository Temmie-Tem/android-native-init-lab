# S22+ P376 minimal boot HUD and root console

Target: SM-S906N/g0q/S906NKSS7FYG8. P376 adds a separate text HUD child to the
consumed P375 root-console capability. This report records H0 qualification;
it grants no device effect or standing console. The next attended run requires
its own exact prepared binding and approval.

## Result and limits

The generated HUD shows NATIVE INIT, a PID1 state snapshot, monotonic uptime and
console READY/BUSY/BLOCKED in large white bitmap text on black. It starts after
authenticated native console preparation, not as an unauthenticated standalone
boot UI. The actual packaged AArch64 renderer's H0 paint entry produced both
complete frames (20,367,360 bytes); the preview was inspected. This is host
rendering evidence, not a physical panel observation.

PID1 remains the sole console owner. One separate HUD child receives fixed
nonblocking state snapshots over a run-bound SOCK_SEQPACKET channel. Command
cancellation uses its own process group. HUD exit, park or diagnostic flood does
not block repeated commands, STATUS, CANCEL or CONTROL. CONTROL stops HUD updates
immediately, signals it at most once and does not wait for renderer/DRM cleanup.
The ten-minute console budget and ordinary exact rollback remain unchanged.

The fixed qualification has six commands: P375's five root-console checks plus
a bounded RAM-log read requiring at least three increasing matched HUD frames,
at least two seconds of update span, and a BUSY console snapshot. A separate
sealed plan may contain at most 64 commands (70 total); P375 remains 5/69.
Raw receipt replay rederives the HUD claim and rejects altered HUD or plan data.
A matched flip event still does not prove physical pixels. Supplemental stock
proof, Download arrival, rollback and final health remain separate evidence.

## New rendering hazard and implementation

The source-bound target commit-wait path can swallow a timeout before returning
from a synchronous atomic ioctl. P373's prepainted buffers therefore did not
qualify repainting old buffers. Cached GEM CPU_PREP/FINI also do not establish
repeated CPU-write cache visibility in this driver.

P376 paints each fresh, non-imported GEM once before its first scanout mapping.
The initial mapping reaches `dma_map_sg_attrs` with zero attributes. One atomic
commit is in flight at a time. Successful ioctl return and an exact
FLIP_COMPLETE type/length/CRTC/user_data event on the still-open DRM descriptor
are required before retiring the previous buffer. RMFB, munmap and GEM_CLOSE
must finish before the next allocation; at most two frame buffers are held.
Any commit/event/retirement uncertainty parks with remaining resources and no
new allocation, retry, repaint or cleanup sequence.

The event argument requires fresh successful DRM module insertion, sole HUD DRM
ownership, no virtual/clone output, and rejection of other active encoders.
The encoder query alone is insufficient to exclude internal CWB-disabling state.
Preclose-generated events are never treated as completion. The eight inspected
driver-source hashes are retained in the private H0 evidence. This is a
source-derived design constraint, not proof of kernel-stall recovery.

See the [capability contract](../operations/S22PLUS_FYG8_BOOT_HUD_V1.md) for the
complete scope and [target clause](../operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md)
for authority and isolation.

## Validation

- Final capability/regression suite: 30 tests passed. It includes actual generated
  PID1 and renderer joined by real IPC with DRM fixtures; HUD exit/stall/flood;
  cancellation and CONTROL ownership; immutable buffer ordering; malformed,
  stale, partial and missing completion events; retirement faults; long uptime
  and clipped text; HUD evidence negatives; and P376/P375 raw receipt replay.
- Common execution suite: 30 tests passed, including the normal full rollback
  timeline and prepare/execute/recovery separation.
- Twenty touched Python files passed py_compile. Target C compiled as static
  AArch64, and `file` confirmed the architecture. Real AArch64 IPC tests cover
  full/broken channels, MSG_NOSIGNAL, fork/dup/exec, close_range, separate process
  groups and exact ARM64 log-create/no-follow flags.
- A/B candidate bytes match. The actual AP audit permits only `boot.img.lz4`.
  The common promotion rehearsal passed with no device contact/publication.

Two host-only drafts failed before qualification: missing freestanding C
constants and an extra literal run-ID occurrence in `/init`. The final source
uses verified target UAPI constants and the existing run-ID storage. Failed
outputs remain private; neither draft received connected preparation or a
candidate effect. No consumed source, approval or journal was changed.

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| Candidate AP (A/B identical) | 31,006,761 | `6ad835596f3409957f065cc685b8ef5a5f19696cb71a510c0fef844c65df6ff0` |
| Sole `boot.img.lz4` | 30,999,929 | `9f726003691d1152b70a48b6fe4593aa1d049a4e08d269cecf26a8b1173fa1b8` |
| Native `/init` | 149,344 | `442fd5095357f16f0128e261c68593d47268adc5792f56f6f0420fbf1ff0d6c4` |
| HUD renderer | 710,664 | `f72448a2cc399ca0184ae3bc16cb0c19480ea4d78286c2ff5fab01f885d09f42` |
| Candidate static | 35,992 | `f86e53115e9e8d802691c0436cf4aee29a7b648f0f379b69192cfc20d97cb995` |

The static closure binds 36 direct source records; the A/B build records 224
source inputs. Independent review returned `PASS_GO` after 28 independently
executed tests, current source rehashing, exact static regeneration and the
common rehearsal. Its private receipt is 53,022 bytes, SHA-256
`0ef43541943d48e137e76009930d595b83234541d7193ddc7ddf7a161bb38852`.

The [READY manifest](../../workspace/public/src/device-action/manifests/s22plus_fyg8_p376_process_v2_ready_1.json)
is published and verified at its actual final path: 8,664 bytes, SHA-256
`354082d49a6bcbb528be3fa9851a15b85cce092fa541a78bd84310844cfe4cb7`.
The actual common bundle SHA-256 is
`6b8e2ce54a46bed546a2b1bd999382ae383cdad2a90b2379ab3d1bd2b4e5adc2`.
No F1 ledger row exists before a candidate effect. No live grant exists.
A90 and S20+ received no commands from this task.


## Connected read-only preparation

Run `p376-ready1-prepared-20260909-1` passed
`PASS_DEVICE_ACTION_D0_V2_CONNECTED_READ_ONLY` against the exact target.
The prepared record is 35,474 bytes, SHA-256
`427cb3ae9453e1440bc87f1515c16041d2b0a82c76c09485721d883a1c7e29c8`.
Device contact was limited to the fixed reads: device_writes, reboot_requested,
odin_invoked, partition_transfer, f1_authorized and live_authorized are false.
No execution transaction or candidate consumption exists. The actual prepared
consumer reopened the exact bundle, and the plan was sealed in that run.

The three-command RAM-only plan is 837 bytes, SHA-256
`4ef55d429360185bef47e71563ec69eeabed360e23573f5fd7c8fccc41de0e35`.
It reports root identity and waits five seconds, writes/reads a RAM file, then
checks that HUD frames continued across a further ten seconds and retains the
last four diagnostic lines. This supplies approximately fifteen seconds of
additional viewing time. Individual plan outcomes remain separate from the six
fixed qualifications; a terminal command is not automatically a successful one.

The run still requires the operator's current physical attendance and its fresh
exact Process-v2 approval before the first write-capable transition. It cannot
reuse the consumed P375 approval or P372-P374 session grant. No screen-visible,
live HUD or rollback claim is made for this unexecuted candidate.
