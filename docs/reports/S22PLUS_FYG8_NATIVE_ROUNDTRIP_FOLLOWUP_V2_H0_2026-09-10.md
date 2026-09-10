# S22+ P384 native roundtrip followup V2 qualification

Status: **first approved invocation ABORTED before Download or transfer;
reviewed host correction and prepared-4 reopen complete; new approval pending.**
Target: **SM-S906N / g0q / S906NKSS7FYG8**.
Candidate: **P384 / v0.2.0-rc.2**. This follows the completed ordinary
[local-display adoption](S22PLUS_FYG8_LOCAL_DISPLAY_ADOPTION_H0_2026-09-10.md).
No F1 grant or candidate/restoration/rollback effect is created by this report.

## Scope and resulting behavior

The operator requested the next step toward native-to-native qualification.
P384's prior ordinary H0 graph allowed one N and one Android A; consuming it
there first would not authorize its reuse for a roundtrip. The separately
reviewed [V2 common exception](../operations/S22PLUS_NATIVE_ROUNDTRIP_FOLLOWUP_V2.md)
therefore selects one new qualification by both the exact P384 run identity and
`s22plus-fyg8-p384-native-roundtrip-v2-ready-1` manifest ID. The ordinary P384
manifest remains ordinary. No core manifest schema or registry algorithm changes.

V2 permits one N installation, one same-N restoration after proved first native
health and timely exact Download, and one exact A cleanup/fallback. Its global
V2 claim is separate and immutable. Each role and each arrival's CONTROL remains
one-shot. The original research window is 1,800 seconds from that claim, with
60 seconds per native observer and unchanged 30-second CONTROL windows.
No stage, exception, changed boot or recovery resumes a research budget.

The existing owner selects explicit policy/schema/claim/budget data. V1's policy
bytes, digest, claim name/format and old P383 plan/retained projection remain
unchanged. No old claim is removed or reused. The ordinary physical-target plus
AP/member consumed key is unchanged and remains permanently consumed after N
installation. V2's plan additionally enforces its exact public target, fixed N
AP/member and fixed Android A, even if a supplied profile and manifest agree
with one another on different values.

P384 health is rederived through its existing complete authenticated observer
replay: fixed health EXEC3/STATUS4, optional HUD5, and actual CONTROL5/6. Legacy
P383 replay remains strictly EXEC3/STATUS4/CONTROL5. Before second CONTROL both
kernel boot identity and nonce must differ. HUD failure/omission does not supply
or invalidate native health; health, authentication or wire failure stops
research. Recovery cannot restore N or replay an uncertain/completed A.

## Candidate and source evidence

All **108 byte-affecting candidate inputs are unchanged**, `CHANGED_KEYS=[]`.
Candidate declaration, generator, C/templates, builder, compiler flags and AP
are reused. Fresh static/execution/approval records bind the host/policy change;
the earlier ordinary H0 bundle and all P383 consumed records are not repinned.

- N AP: 31,150,121 bytes, SHA-256
  `4845ee93971bafcd73042128eeeae676715de9ede4a306d15a21e9db7c5a7d5c`.
- N `boot.img.lz4`: 31,141,009 bytes, SHA-256
  `9ba1097d6a1b6d0f3ab774737909c426d7630c87d0e76bb00f82f737979dc802`.
- A AP: 23,367,721 bytes, SHA-256
  `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`.

The fresh private bundle is
`workspace/private/outputs/s22plus-fyg8-v0.2.0-rc.2/h0-roundtrip-v2-review-1/`.
The actual common bundle reader, V2 role planner and execution-closure reader
pass. The role plan records the three ordered one-shot roles, 60/1,800-second
limits, immutable N/A identity and no claim release.

| Private record | Bytes | SHA-256 |
| --- | ---: | --- |
| `review-manifest.json` | 7,091 | `4c01e502db949937567570dd63cb11bdd1d72f534a3f6ee7d483fc1f822987df` |
| `execution-closure.json` | 44,927 | `7fe32aa52552ccff6966fb24df7ccc729de0f74022c57a56309f565491cd6042` |
| `result.json` | 31,003 | `df8990980c778ecf5c6d767f8028a1e6236c6333bcf8fbd4310e80da012311e4` |

The root's current reviewed bytes are retained privately as `reviewed-AGENTS.md`.
Its pre-existing S20+ table/recovery-note edits are outside this unit's staging;
the V2 details-pin hunk is the only root change in this qualification.

## Validation

**101 parent tests passed:** six V2 tests, 13 legacy-health/P383/ordinary-P384
compatibility tests, and 82 binding/observer/common-live regressions.
Seven touched Python files pass `py_compile`. No native byte input changed, so
the validated matching ARM64 A/B builds are reused.

The V2 tests execute real generated P384 C and renderer, authentication, raw
reopen, CONTROL/role writers, measured USB departure and terminal consumers.
Root/mount/UUID, hardware, USB/Odin/ADB and small test archives are explicit H0
fixtures. Actual fixed P384 N/A are separately validated by the real bundle.
Cases include normal, failed and omitted HUD, first/second health/wire failure,
same boot, same nonce, fixed-target/A/N/budget mismatch, selector crossover,
V1/V2 claim isolation, restoration intent/delivery/result cuts, proof cut,
A intent/result cuts, and failed/uncertain restoration and A without replay.

Initial new-test failures were fixture integration issues: a stale RNG-hook
anchor, the generic test's deterministic rollback receipt versus the actual
ordinary A reader, and its assertion rejecting intentionally failed health.
Only those fixture joins were corrected; production safety checks were retained.
Independent review found the missing V2-specific fixed A/target comparison;
the plan now rejects both, with focused negative coverage. FIRST is unchanged.

The reviewer independently passed five legacy health tests, selector checks,
old/current P383 plan/claim/projection comparison, and twelve V2 failure/
freshness/publication-cut scenarios. It checked the 108 unchanged inputs,
V1 policy digest, incorporation pins and scoped diff, then returned **PASS_GO**.

## Initial independent source binding

Production Python paths are under `workspace/public/src/scripts/revalidation/`
except candidate static under `workspace/public/src/scripts/analysis/`.

| Reviewed input | SHA-256 |
| --- | --- |
| `s22plus_native_roundtrip_owner_v1.py` | `2c09735d7bdc9c905c3c9dfb4eb92343804c0a7863a94e74c09a0b9c92c20260` |
| `s22plus_native_baseline_health_v1.py` | `3f87da168643d5b62f9f9c35278981c20a531bf88d00b510d56b85c26ac4fb09` |
| `device_action_f1_live_v2.py` | `25a46c4dbc8730c3f8a463b32e1c501f8b661940a03d5efbf8b81328fdcdc144` |
| `s22plus_fyg8_p384_process_v2_candidate_static.py` | `9ce77b5bcd4f587eaa4b64797bf7c71674238696f8477e4026027b2b75f54b55` |
| `S22PLUS_NATIVE_ROUNDTRIP_FOLLOWUP_V2.md` | `6f62dbe4d53be7839e9a5f06dfcb922bc1af39545f30734d499dfe73caccff4e` |
| `DEVICE_ACTION_CONTRACT_DETAILS.md` | `e79d39a44bce9f861f939de32051d25b2d6b1a4a34e2c976776669bab50d5fac` |
| `S22PLUS_FYG8_TARGET_CONTRACT.md` | `4e3113eab170f3e9fb0871f525a473fe99db1ec475fe1df8c1b73fb540ab2d6c` |
| `AGENTS.md` current working bytes | `c960b6814a52f832e6c9c62cfaf181f8d5d33dca9505273a83b47287279b303f` |

## Authority and limits

V2 is a separate closed common-boundary exception, not a semantics-only
refactor or a renewal of P383. Its reviewed capability requires exact fresh
preparation and a separately returned finite attended approval before effects.
Physical Download recovery must remain usable. Neither H0/PASS_GO nor a READY
manifest establishes attendance or that grant.

No live P384 native boot, roundtrip, pixel output, final health, automatic
recovery, standing native baseline or persistent storage is proved here.
P383 remains consumed NO_PROOF with its completed Android recovery. A90/S20+
device commands and unrelated repository changes are outside this unit.

## First connected preparation: retained baseline negative

One Process-v2 `--prepare` ran at
`workspace/private/runs/device-action-f1-live-v2/p384-native-roundtrip-v2-prepared-20260910-1/`.
Its initial exact S22+ identity, rooted FYG8, original boot/supporting hashes,
completed Android boot and Download absence passed. The fixed `/proc/last_kmsg`
capture completed to EOF: 2,097,136 bytes, empty stderr, SHA-256
`df8b01202f55b03f797621b4a364a59d4772951ff8a9b4ad5fafc1efc8bb868e`.

The clean-baseline reader rejected a current, legacy or partial evidence family.
Offline replay of those retained bytes through the actual decoder reproduces
that rejection. This establishes no new candidate or native boot fact and does
not identify a particular prior run without additional evidence.
The baseline rule is retained; no record is removed, relabelled or treated as
clean. That stopped invocation was not resumed; the later ordinary reboot and
fresh D0 below have separate records.

The durable `preflight/result.json` is
`STOP_DEVICE_ACTION_D0_V2_BASELINE_REJECTED`: 3,287 bytes, SHA-256
`4c9d53eec7438fd10bc25eff3e60ab877ded5e67be72a220cd6f8ccf14513243`.
It is nonreusable and explicitly records final target continuity/final health
as unobserved. Device writes, reboot, Download transition, Odin, partition
transfer, F1 and live authorization are all false. No prepared approval token,
transaction or V2 claim was created. Initial health is not a final-health claim.

The selected next action was one ordinary Android reboot through the existing
foreground-goal capability, followed by its fresh full target/health return
and a new Process-v2 D0. The old-boot raw evidence was retained before this
separate action. A baseline negative does not authorize automatic repeated
reboots or a relaxed decoder.

An independent scoped review qualified the foreground-goal metadata refresh:
only `f1_owner`, `common` and `target` source hashes changed. The six other
source roles, eight actions, F1 owner publication/retirement, pending-reboot
interlocks and attendance requirements are unchanged. The parent passed 22
existing capability tests, and the reviewer passed seven focused uncertainty/
interlock tests. The prior review is retained privately; old goals are not
repinned. The refresh itself opens no grant or F1 authority. A new H0 readiness
goal selects only `normal-reboot`, limited by its stated objective to one action
after attendance is established. Its exact private target matches both the
prior D0 binding and this invocation's initial target identity.

## One attended ordinary reboot and later health

The operator confirmed physical attendance. The one-action readiness goal
issued exactly one ordinary Android reboot, whose bounded raw command result
returned zero. Its return observer encountered an empty `boot_completed` field
when ADB first appeared and raised `D0Error`. The existing runner wrote STOP,
closed the goal and retained the pending-reboot record. There was no reboot
replay or second D1 goal.

The existing read-only reconciliation then verified the same exact S22+, a new
kernel boot, rooted FYG8, original boot/supporting hashes, completed Android
health and Download absence. It returned **LATE_HEALTH_OBSERVED_GOAL_CLOSED**,
with `action_proof=NOT_UPGRADED` and no reboot replay; the pending record was
cleared and the goal remained closed. Its private `result.json` is 1,275 bytes,
SHA-256 `fc1f5dd405387e8612abfd9fbd086b4d335514d0a3581e6459b31552f15d778a`.
This establishes later health, not bounded D1 success. The D1 parser was not
changed in this unit. The F1 final-health loop already handles this D0 parser
exception within its existing deadline, so the separate early-return parser
repair is not a prerequisite for this F1 graph.

## Second D0 and preparation publication repair

A separate read-only preparation in
`p384-native-roundtrip-v2-prepared-20260910-2` passed the complete D0 check.
Its exact target/final health passed and the full 2,097,136-byte `last_kmsg`
capture reached EOF with zero stderr and a clean baseline. Raw SHA-256 is
`fc46c59ee021fd918f4410f57dbc7d7a36b89b18b9e9fde76dd0b2a193d50260`.
The PASS D0 `result.json` is 3,296 bytes, SHA-256
`cff9939a67495df6cc208b71daf8123ceeb22a5f09b5c0460e7cfa00746576c0`.

The following host publication failed before opening `prepared.json`: the
complete preparation serialized to 67,403 bytes with indentation, exceeding
its existing 65,536-byte bound. The same parsed record is 56,489 bytes in compact
JSON. This was a host publication defect after a valid D0, not a new baseline
rejection or a device transfer failure. No prepared token or F1 effect resulted.

The durable writer now has an opt-in compact format; only preparation records
already selected for the existing 64-KiB limit use it. Every field, byte limit,
exclusive/no-follow open, short-write rejection and fsync is retained. Default
writers and 32-KiB preparations retain their previous bytes. The full reader
still reopens D0/private target and rederives source closure and approval binding.

The second D0 and its old bundle remain immutable. Both changed writer sources
are execution inputs, so a fresh source-qualified bundle and fresh read-only
D0 are required by the existing bundle-hash check. No old D0 hash is rewritten
or combined with the new source binding. This correction entails no additional
ordinary reboot.

The final repair passed `py_compile` and **107 core/live regression tests**,
including full preparation/reopen with a closure whose pretty form exceeds
64 KiB, exact-limit and one-byte-over records, nonfinite JSON, exclusive create,
short-write failure, unchanged legacy bytes and the original target/source
tamper checks. Independent review passed three focused tests and returned
**PASS_GO** for the repair and a one-role foreground-review refresh. Only
`f1_owner` changed in that capability's nine-role identity; its eight actions
and other eight sources are unchanged. Both earlier review records are retained,
and the consumed one-reboot goal stays closed.

Final changed execution-source hashes:

| Source | SHA-256 |
| --- | --- |
| `device_action_f1_v2.py` | `b40c51abea67df97eddb4b7e1ae761548c051bdac8480168e0fff72668b60abd` |
| `device_action_f1_live_v2.py` | `19a865b70fecf12a25657ae87494fad246d89761086f4426f917f94bf1205727` |

All other initially reviewed execution/policy inputs above remain unchanged.
The actual 108 candidate source inputs still have `CHANGED_KEYS=[]`; no build
or AP replacement was needed. The repository boundary check passes.
The fresh actual bundle reader and all current execution-source receipt checks
pass in `h0-roundtrip-v2-review-2/`:

| Private record | Bytes | SHA-256 |
| --- | ---: | --- |
| `review-manifest.json` | 7,091 | `9f67ad4e198988db84339859c7bd2aa7ac3913a50dd4458c08cad84fe2928965` |
| `execution-closure.json` | 44,927 | `6cf959b7c72eb5d8cde5558ce5290b95c51058ba49a73b9614214f6645ab8a8b` |
| `result.json` | 31,003 | `378438a2ee4c6538b5775a73425b6946e7db41a8cddcad1abfea47778086282b` |

## Prepared-3 readiness before the first approved invocation

The fresh read-only preparation in
`workspace/private/runs/device-action-f1-live-v2/p384-native-roundtrip-v2-prepared-20260910-3/`
completed. Its D0 result is **PASS_DEVICE_ACTION_D0_V2_CONNECTED_READ_ONLY**:
exact same-target rooted FYG8, original boot/supporting hashes, complete Android
health, Download absence and a clean fully captured baseline all pass.
`preflight/result.json` is 3,295 bytes, SHA-256
`be3f06fb2563456f6cdcf636a0b3a245af9b81c22b23ff900224d84669e84426`.

The complete `prepared.json` was durably published in **56,489 bytes**, SHA-256
`ce42c9a11dc70199d5c86c63af3402381064db0c3c6dd011e6e553cdb1ad684f`.
The actual `load_prepared` consumer reverified the current exact bundle,
179 execution-source receipts, D0/private-target identities, current Type-C
lane, credential identity and complete approval binding. The V2 role planner
reopened its exact N/A and three one-shot roles with the original 60/1,800-second
limits. N has no active consumed claim; the V2 claim, F1 transaction and pending
D1 record are absent. The read-only reopening result is retained privately as
`h0-roundtrip-v2-review-2/prepared-reopen.json`.

Physical attendance has been confirmed for the current foreground task. The
fresh approval token is private and has not yet been returned by the operator.
No P384 installation, native restoration, A transfer or native qualification
has occurred. Prepared `f1_authorized` and `live_authorized` remain false.
The closed ordinary-reboot goal is unchanged. A90 and S20+ were untouched.

## Past-failure checklist reconciliation

The operator asked whether every item had been checked. The initial readiness
report did not contain the ID-to-evidence mapping required by the
[checklist](../operations/S22PLUS_FYG8_PAST_FAILURE_CHECKLIST.md). More materially,
the full actual prepared-record serialization had not been exercised before
connected preparation; its size failure was discovered after D0 #2. Initial
H0 PASS therefore did not establish that every applicable checklist item had
already passed. The publication repair and final actual prepare/reopen above
close that specific gap; this accounting preserves when it was discovered.

The following records the reconciliation before the first approved startup;
the later ROUTE/HOST factory gap and correction are documented below. Reused
component results apply only to unchanged inputs. The comparison found
finds all 108 candidate inputs unchanged and all 179 prepared execution-source
receipts current. In particular, the measured USB core/identity, local observer,
shared wire and direct-source generator match their cited reviewed hashes.

| ID | Status at initial reconciliation | Evidence and remaining limit |
| --- | --- | --- |
| ABI | No new ABI change; prior H0 reused | No C, numeric flag, layout, ioctl or kernel API changed in V2. The identical AP and static ARM64 A/B package checks are retained. These are not new on-device ABI execution proof. |
| IO | Confirmed in H0; unchanged producer reused | The [local observer tests](S22PLUS_FYG8_LOCAL_DISPLAY_OBSERVER_1C_H0_2026-09-10.md#validation) exercise production subprocess/output paths, HUD stall/read failure/output loss and budget skip. V2 tests re-exercise the production C/raw path with optional HUD success/failure/skip. No pipe or queue implementation changed. |
| SEMANTIC | Confirmed in H0 and applicable D0 | Fixed root/PID1-parentage/mount/idle health, first/second boot and nonce freshness, and optional HUD separation are tested. CONTROL ACK remains acceptance only. Actual D0 verifies Android identity/health; late D1 health does not upgrade the stopped return. Native P384 health still requires execution. |
| WIRE | Confirmed in H0 | Actual generated C, authenticated live collection, retained RX/TX and the production replay/result consumers are joined. Failed health and corrupt first/second wire stop further research and preserve raw evidence. |
| PERSIST | Initial gap; now confirmed for preparation and H0 lifecycle | The real preparation initially exceeded the bound; compact serialization now passes full actual prepare/reopen at 56,489 bytes. The 107 core/live tests cover limit/exclusive/short-write/reader failures. V2 success and late failure/cut cases use actual journal/role/result writers and recovery consumers, with fixture hardware/transport. This does not predict every future live byte stream. |
| ROUTE | Confirmed in H0 and actual preparation | Exact V2 selector, wrong/crossed selector rejection, ordinary P384 and legacy P383 compatibility pass. Real `prepare_connected`/`load_prepared` and the sealed role plan pass; fixture N/restore/A backend records reach PASS/NO_PROOF/CLOSED and retained recovery readers. |
| ARTIFACT | Confirmed with retained actual packages | [P384 adoption](S22PLUS_FYG8_LOCAL_DISPLAY_ADOPTION_H0_2026-09-10.md#source-and-package-binding) decoded both complete actual APs, all ramdisk entries and declared Image changes. Current bundle verification rechecks exact N/A, member identities and unchanged candidate inputs. Consumed V1 pins remain intact. |
| AUDIT | Confirmed for the invoked operations | Offline diagnostics preserve old D0 bytes and bundle identities. `load_prepared` validates retained data and reads the current lane; no journal repair was invoked in the final preparation check. The earlier D1 reconciliation is explicitly a state-changing host finalizer: it clears pending state after verified health while keeping the goal closed. No repeat device effect occurred. |
| HOST | H0/current D0 confirmed; live guard startup unconfirmed | The [measured first-child inventory repair](S22PLUS_FYG8_RESTORATION_ARRIVAL_H0_2026-09-10.md#validation-and-review) and actual V2 fixture path pass. Current D0/ADB and host publication pass. This prepared run has not started its real privileged observer guard, so current polkit/guard readiness is not claimed. The existing execution path arms the guard before Download request/candidate transfer and aborts on failure. |
| DISPLAY | Unchanged component H0 reused; physical display unconfirmed | The local lifecycle/observer tests cover before-auth lifetime, failed/omitted HUD and diagnostic-frame rejection; V2 uses the same candidate/display bytes. Reported flips, native health and physical pixels remain separate. P384 physical pixels and second-boot display have not been observed. |
| RETURN | Confirmed in H0 and later Android health; native roundtrip unconfirmed | V2 tests cover restoration/A uncertainty, no replay and retained recovery. The one ordinary reboot STOP and later exact healthy reconciliation remain separate. F1's existing final-health loop handles transient D0 parse errors; the ordinary D1 early-return parser remains unfixed. Actual two-native-arrival/timely-Download/A-cleanup success is still the proposed qualification. |

This reconciliation adds no gate or authority and does not repeat device
commands. The two edited documentation files are not prepared execution inputs;
the prepared source binding remained current. The approval request was still
unanswered at that point. Any future execution performs its existing fresh target,
artifact, ownership and guard checks before effects; this table does not replace
those checks or claim their future outcome.

## First approved invocation: host startup abort before effects

The operator returned the exact prepared-3 approval. One original `--execute`
ran from source commit `426b124262`; that invocation was not repeated. Its
fresh execute D0 verified exact rooted FYG8, original boot/supporting hashes,
completed Android health, clean baseline and Download absence. The process
had UID/EUID 1000, `NoNewPrivs=0` and `Seccomp=0` before invocation.

The journal advanced to APPROVED, then **ABORTED/4** at
`2026-09-10T09:58:12.788900Z`. Its recorded error type is `AttributeError`, outcome
`candidate_observer_arm_failed_before_candidate`, verdict
**FAIL_F1_V2_PRE_CANDIDATE_DOWNLOAD**, and `recovery_required=false`.
N installation, same-N restoration and A cleanup each have null intent/result;
Download request, guard arm, candidate claim and V2 claim are absent. Counts are
**0 N installation / 0 N restoration / 0 A**. No native or USB boot result exists.
The execute preflight is the latest observed health; the result's
`final_verified=false` is retained rather than presented as post-experiment
health proof. No recovery transfer is needed for this pre-effect abort.

The actual unchanged-source terminal validator passed before the repair.
The canonical public timeline contains only
`live_session_start — 2026-09-10T09:58:12.735740Z`; no later transition is invented.
All private records remain under `p384-native-roundtrip-v2-prepared-20260910-3/`.

| Retained record | Bytes | SHA-256 |
| --- | ---: | --- |
| `execute-preflight-01/result.json` | 3,318 | `7a2ed3cdc7ffb35a0c0207722ef28b027abcca3767801b134a072b206042f103` |
| `live-result.json` | 1,959 | `e671928bf0824234a0daaadecca610fa911760566d558ac10102d8ce3bb931ec` |
| `live-state.json` | 711 | `fa0113a98b1047851b731d308ba00c6690d382661dc5f66bb56d2f0e10735e5d` |

### Reproduced cause and scoped correction

Off-device replay of the actual `_p345_candidate_observer_session` entry with
the retained prepared input reproduced `AttributeError: 'Artifacts' object
has no attribute 'DEFAULT_AUTH_KEY_PATH'`. A guard-call sentinel was never
reached. The original journal preserves only the exception type; the exact
message/traceback is separately retained as H0 reproduction, not relabelled as
an original live trace, in `h0-roundtrip-v2-review-2/startup-h0-reproduction.log`.
The stopped result/claim absence and unchanged-source validation are recorded
in that bundle's `startup-incident-validation.json`.

P384's direct artifact object supplies package and key identity, while the
shared session-entry consumer expects the legacy credential-reader interface.
Earlier lifecycle tests substituted `_p328_read_auth_key` and constructed the
observer fixture directly. That hid this production factory connection. The
ROUTE/HOST checklist coverage therefore had a second concrete gap beyond the
already corrected PERSIST size issue; neither a prepared reopen nor a fixture
session proved the actual startup factory.

The host-only correction explicitly selects the existing strict P328 reader
for the exact P384 shell. That is the same fixed private key used by the retained
build; its current 32-byte digest was verified equal to the prepared P384
identity without publishing key bytes. Existing direct-path, single-link,
0400-mode, stable-inode and exact-length checks remain, followed by the P384
prepared digest comparison. There is no caller-supplied key path or permissive
reader fallback. Other candidates retain their prior path. The candidate
declaration, artifact helper, 108 build inputs and AP are unchanged.

The old approval/run stays ABORTED and cannot execute again. Its absent N/V2
claims do not make that approval reusable. A later attempt requires a fresh
source-qualified bundle, fresh D0 and separately returned approval under the
existing Process-v2 pre-candidate-failure rule. No ordinary reboot or new
partition effect follows from this H0 correction.

### Startup repair qualification and fresh preparation

Three focused startup tests now pass through the real
`SamsungOdinBackend.candidate_observer_session` dispatch, registered factory,
empty-plan seal, strict credential reader and `_P375ObserverSession`
construction. The lane and lower hardware guard are explicit fixtures. Ordinary
and V2 construction pass; missing, wrong-mode, symlink, hardlink, short and
wrong-digest keys all fail before guard entry. The execution-level wrong-key
and guard-start failures terminate ABORTED with no Download request, N/V2 claim
or transfer, and a second execute of the stopped fixture is refused.

The 88 existing P328 credential/artifact and common-live regressions also pass.
Initial new-test failures were a 33-byte fixture corrected to 32 bytes and an
object-identity comparison against a separate import instead of the registered
variant. Only those fixture issues were corrected; the final three entry tests
pass. Independent review repeated all three and returned **PASS_GO** against
live-source SHA-256
`fedf5e5afca59865a9144f3da8ece644033402ca9a456929df0e47fc7725bf2e`.
Touched Python compilation, diff/link and repository boundary checks pass.

The separately reviewed foreground capability metadata changes only `f1_owner`;
its other eight source roles and all eight actions remain unchanged. The prior
review and new receipt are retained under `h0-roundtrip-v2-review-3/`. This
refresh opens no grant and leaves the earlier ordinary-reboot goal closed.

The new private `h0-roundtrip-v2-review-3/` bundle passes its actual reader and
current source checks. All 108 candidate byte inputs still match the retained
build. No AP, key or candidate-identity replacement occurred.

| Fresh bundle record | Bytes | SHA-256 |
| --- | ---: | --- |
| `review-manifest.json` | 7,091 | `4737fb2febc9ea75edc64ef6f26d908337306ed24f2be6c248af2864c0598e38` |
| `execution-closure.json` | 44,927 | `bd2303851a5f7257bc4adda7627914ea47dc7b2dda0c8ae26b7f1513f9ca1df1` |
| `result.json` | 31,003 | `308c6b898145e1eb6dbc55256ada432c300919838756e2094d18a1cfd0fa739e` |

New connected preparation in
`p384-native-roundtrip-v2-prepared-20260910-4` passes exact current rooted FYG8,
original boot/supporting hashes, Android health, Download absence and clean
baseline. Its D0 result is 3,296 bytes, SHA-256
`b945b2f4258f99768f01561356b1a569b146df60ffc5fea8f4991b2801f53cd1`.
The new prepared record is 56,489 bytes, SHA-256
`cb3b40adca2122ecf810466cbf8ea0ac9560a34d088838e2163444edb364ae7c`.
Full `load_prepared`, V2 plan/claim-absence and candidate registry checks pass.
The actual fixed private key reader matches this prepared identity; the real
session factory also constructs successfully with that actual input and a
fixture guard in a disposable private directory. No key bytes are published.
`prepared-reopen.json` records
**PASS_P384_V2_FRESH_PREPARATION_AND_KEY_ENTRY**. The actual privileged guard
has not started and no new F1 approval has been returned. Old prepared-3 remains
ABORTED; prepared-4 has no transaction, and N/V2 claims remain absent.

The ledger has one new zero-transfer F1-stop row, which contributes no candidate
attempt. Existing ledger bytes are unchanged. The full historical taxonomy
audit fails identically on HEAD and the edited ledger at the pre-existing P353
`PROVED_DISPATCH_VISUAL_CORRUPTION` outcome. The new row passes the actual parser
with the retained valid historical prefix and is classified
`PRESESSION_OR_ZERO_TRANSFER_F1_STOP`; no unrelated historical correction or
validator change was made. Both audit results are retained privately.
