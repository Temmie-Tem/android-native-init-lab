# S22+ uniLoader-to-FYG8 Android control: H0 qualification

The operator selected one physical control after ML002: retained ABL through
uniLoader into the exact original-A FYG8 kernel and Android. This distinguishes
the common loader path from the mainline kernel/DTB/runtime path. The final
product remains mainline Linux and resident Debian. This report records H0
qualification and preparation; it does not claim physical loader execution.
The subsequently completed physical control is recorded separately in the
[LA001 run report](S22PLUS_LOADER_ANDROID_LA001_RUN_2026-10-29.md).

## Candidate and proof

The new loader preserves the current ABL FDT argument before relocation. A
stackless guard checks the complete tree, inherited initrd, reserved ranges,
RAM banks and source/destination geometry before stores. The inherited initrd
is untouched. The full tree is cloned with one fresh candidate-bound marker;
the byte-identical original-A vendor kernel is copied and entered. The boot-v4
package preserves the original outer ramdisk and other retained payloads and
has only `boot.img.lz4` in its AP. Retained signature bytes do not authenticate
the modified image.

Candidate proof requires one same-boot raw Android bracket: numeric root,
target properties, exact candidate boot/supporting partition digests, exact
kernel release and the marker digest. Before normal Download return, a fresh
complete bracket must retain that boot identity and marker; USB generation is
checked before and after it and again at dispatch. Observation uses the original
N-launch deadline, not a renewed window.

The [policy](../operations/S22PLUS_LOADER_ANDROID_V1.md) selects the existing V3
owner, lease, consumption registry and boot-only transport. One attended task
has 1800 BOOTTIME seconds, one N and one original A. Normal success returns to A
inside that owner. Failure retains the stopped owner for physical Download and
original-A recovery; candidate/control actions never replay. Raw-proved A needs
only health continuation. Neither normal return nor this control proves recovery
from an unresponsive experimental component.

## Validation and corrected findings

Private evidence is retained under
`workspace/private/outputs/s22plus-loader-android-h0-20261029-1/`.

- `build-5`, `qualification-5`: 109 actual ARM64 loader cases and 1,051 copy
  cases pass. Representative complete copies/jumps retain incoming tree
  semantics and initrd bytes. The compiled guard has no stack access, stores
  or calls before admission. Read alignment is checked throughout the guard
  and runtime, including rejected input cases.
- `entry-vm-4`: actual EL1 and EL2 entry pass and EL3 rejects. Entry registers
  come from fixture instructions. These tests do not establish physical cache
  coherence or hardware boot.
- `package-3`: two identical boot-v4/AP outputs, one boot member each, joined
  to the actual qualified loader and exact original A.
- 152 focused host tests pass. They exercise raw producer failures, wrong marker/kernel/root/partition,
  changed boot, USB reattachment, original observation/return deadlines, owner
  interruption, expiry, uncertain A and health-only continuation. Closure tests
  interrupt after each durable H0 output; retries preserve existing bytes and
  journals and perform no device action.
- The selected observer/Android reader pass the existing raw-first source
  audit; injected legacy subprocess acquisition is rejected. This is a scoped
  audit, not a claim that unrelated historical observers were requalified.

Independent review found a mismatch between exact FDT node-name recognition
and libfdt's unit-address alias lookup. The prior build is retained as NO_GO.
The current guard rejects root aliases of chosen/reserved-memory/memory, and
the qualifier reproduces both actual libfdt lookup and rejection before stores.
Review also found a partial H0 closure-publication retry defect. Closure now
rederives existing artifacts with a stable durable end time instead of trying
to create them again or changing their contents.

The operator also requested a Claude review. Its supplied-source verdict was
conditional advisory PASS, with practical gaps; that was not a review of the
subsequent fixes or execution authority. The independent repository reviewer
checked the resulting deltas and actual artifacts. The changes are:

- A settled original launcher may have its missing stop truthfully reconciled
  under the lease before stopped-owner recovery. Missing settlement, uncertain
  A and a changed host boot still reject; no worker-policy exception is added.
- After any original-A intent, stop guidance forbids entering Download or
  transferring A again and distinguishes raw completion from remaining health.
- Candidate readiness waits for both boot completion and stopped animation,
  within the original window, before starting one complete health bracket.
- Historical H0 proof/readiness validation joins the original grant epoch.
  Fresh readiness, live observation/control and recovery retain current-host
  checks. A host reboot cannot renew device authority.
- The actual guard/read/copy corpus now checks read alignment and both memory
  node rejection branches. Initrd overlap with the loader source is also
  rejected before stores. An independent counterexample established why this
  matters; the selected 969-instruction guard retains the original no-stack,
  no-store, no-call checks. A compiler-spilling intermediate build was rejected.

The current `unchanged()` implementation caches verified identity against
device/inode/mode/link count/size/mtime/ctime. It does not rehash every unchanged
large artifact on every guard. Real task validation took 0.097 seconds cold
and 0.0054–0.0060 seconds in three warm checks on this host. This measures the
actual source/artifact/recovery validator, not all of `Session.check` or ADB
latency. Physical uncached loader copy time remains unmeasured.

## Past-failure checklist applicability

The [current checklist](../operations/S22PLUS_FYG8_PAST_FAILURE_CHECKLIST.md)
is applied to the reachable control path:

| Item | Evidence and limit |
| --- | --- |
| ABI | Actual ARM64 guard/copy/jump and exception-level fixtures; source alignment and FDT pointer preservation. Physical handoff remains unproved. |
| SEMANTIC | Exact kernel and loader marker join; same-boot health, numeric root, producer status/stderr, freshness and USB-generation rejection. A screen or boot digest alone is insufficient. |
| IO / WIRE | Bounded raw captures are sealed before parsing; failed producer output survives. Fixed marker command extends the existing reader without arbitrary shell input. |
| PERSIST / AUDIT | Immutable task source snapshot; raw index and canonical timeline; publication interruption and historical rederivation without device I/O or rewriting old journal records. The separate stop reconciliation is an explicitly cited append. |
| ROUTE | Exact loader schema/operation dispatch, connector preparation/readiness/start, stopped-owner recovery and health-only paths; wrong profile and normal continuation reject. Settled interruption gets one truthful stop, never fabricated completion. |
| ARTIFACT | Two reproducible boot-only packages, actual unpacked loader/kernel/ramdisk joins and retained build versus current checker provenance. |
| HOST | Existing reviewed ordinary-terminal worker and measured transport reused. Fresh named preapproval D0 must establish actual original-A health before grant. |
| RETURN | Candidate normal Download binds fresh proof; stopped original owner retains one A; uncertain transfer never retries; Android health does not settle native_data consistency. |
| DISPLAY / storage | No new display or native_data operation. Logo, absence of USB and Android health do not establish unobserved execution or filesystem state. |

The final source-bound independent review is PASS_GO. It binds the loader
capability and backend v11; the persistent worker and its invariant policy
remain byte-identical. The private review receipt and 54-file source snapshot
preserve backend/entry provenance as well as the task's capability snapshot.
The external advisory was resolved through the changes above. The independent PASS qualifies the capability only;
the exact task still requires its finite returned approval and attendance.
No A90 or S20+ action is included.
