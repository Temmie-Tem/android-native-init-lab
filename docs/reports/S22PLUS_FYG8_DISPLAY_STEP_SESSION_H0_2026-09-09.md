# S22+ fixed display-step session H0 qualification

Target: SM-S906N/g0q/S906NKSS7FYG8. This report records host qualification;
no new live observation, session grant or device effect is implied.

## Bounded behavior

P372 requests one fixed pattern. P373 requests two fixed patterns in order.
P374 exits the sole display child with status 7 after receiving its fixed request
and emitting the start marker, before that request completes. The shared code
keeps one outstanding eventfd request, exact run/ordinal/pattern markers and two
signed STATUS samples. Queue acceptance is not completion. The initial display
setup is separate from requested submissions; visible pixels remain unproved.

PID1 never waits for renderer completion inside the control parser. Child startup
failure yields a negative ACK; pending or failed first work prevents STEP2 while
STATUS and CONTROL remain available. Authentication/framing/USB failures keep
the existing no-retry stop behavior. Original sixty-second supervision and exact
Download/boot-only rollback/final health remain. Kernel/PID1 stalls still require
attended physical recovery; successful software return does not prove that case.

## Session authority and recovery

One explicit attended grant freezes an ordered reviewed READY catalog, at most
three reservations and two hours. Fresh target/boot/artifact/health bindings are
still checked per run. A pre-effect ABORT may use another reservation with a fresh
prepared run of the same untransferred candidate. Only PASS advances the catalog.
An unexplained device interruption closes research authority before recovery;
later healthy PASS cannot reopen it. Already-CLOSED publication repair is distinct
and performs no new device effect. Expiry/withdrawal never cancel authorized
journal-bound rollback. No exact-token approval is manufactured for the session.

Independent review found and resolved two concrete authority gaps: legacy execute
now consults the authoritative reservation even if per-run sidecar publication
was cut, and nonterminal recovery closes the grant even after a hard process cut
bypassed exception cleanup. No new general shell, daemon, target or partition
capability was added. The three/time limits and ordered PASS dependency describe
this batch, not a new permanent rule for all research.

## Host verification

The changed-path suite passed 142 tests, with two additional activation-gate
cases passing separately; 53 changed/new Python files compiled. Tests include
actual generated supervisor and renderer with real eventfd/fork/dup/exec,
fixture DRM and PTY transport; one/two-step completion, declared child exit,
stalled/startup-failed child, IPC error/short write, partial ACK, duplicate step,
CONTROL before/during work, and common raw/result/rollback reopening. P373's
skipped STEP2 negative receipt is rederived from retained raw bytes and rejects
completion-field tampering. These are H0 results, not real USB/DRM recovery proof.

Exact FYG8 target UAPI confirms eventfd2 syscall 19 and inherited ARM64
NONBLOCK/CLOEXEC values. A static AArch64 probe executed through qemu verifies
fork/dup/exec flags, empty-read EAGAIN, ordinals 1/2, child exit, coalescing and
backpressure. Child code never clears the shared nonblocking flag. Strict actual
ARM64 builds removed unreachable predecessor wait helpers without weakening
compiler warnings. Distinct Image hashes were derived through the unchanged
identity-only transform and complete Image validation; the old expected hash
correctly rejected the initial H0 preparation. No consumed source was altered.

All three builds have identical A/B outputs and contain only boot.img.lz4 in the
AP archive. Each candidate static check passed with 267 closure entries; each
build binds 209 source inputs. A shared private freeze preserves 260 unique
execution-source files. Raw build/test/review evidence stays private under
workspace/private/outputs/s22plus_attended_f1_session_v1/ and each candidate folder.

| Candidate | AP bytes | AP SHA-256 |
| --- | ---: | --- |
| P372 | 31,006,761 | `825736e27bf29d4175f77ee380e22dd6cc0a2e0f952c75679407066adf0dec4d` |
| P373 | 31,006,761 | `2039593cda5d3496f9ce0885baa1cdffdaf2f3208ad7de573a61cc100d3f22a0` |
| P374 | 31,006,761 | `358649eb5eda982c1085cfb3e74592efdb315818f22bd280ac8496d4f58d4bd9` |

One shared independent artifact/source review returned PASS_GO for all three
candidates and the session capability. The activation receipt is published at
[the capability binding](../../workspace/public/src/device-action/bindings/s22plus_attended_f1_session_v1_review.json),
SHA-256 `f49182773aea2dbbc91f3ebc37b8ee6f3cc1e40d6ed1015e6d87d5b05d6b20a6`.
The actual source-gate and all three catalog admissions passed. READY manifests
for P372, P373 and P374 are published; this is capability readiness, not a grant.
The unchanged foreground D0/D1 capability review was refreshed under the same
reviewed delta and its historical receipt preserved privately.

Fresh P372 connected preparation completed in
`p372-ready1-prepared-20260909-1` with exact rooted FYG8, original boot/supporting
hashes, completed Android/stopped boot animation and Download absence. The
actual prepared-record consumer reopened it. This fixed D0 read requested no
reboot or partition transfer. No session grant or F1 candidate has started;
current physical attendance is the remaining operator condition. P373/P374
will receive fresh connected preparation only after the preceding experiment
closes healthy, so a normal changed boot identity is rebound mechanically.

S22+ P371 remains consumed/CLOSED with its historical proof limits. A90 and S20+
received no commands and their unrelated changes are excluded.
