# S22+ P424: authenticated PRE retained; full calibration incomplete

Status: **PARTIAL_NATIVE_LOG_RETENTION; ANDROID_CLOSED_HEALTHY**.

P424 consumed its exact returned attended 1800-second/one-operation grant on
2026-10-13 KST. Only `SM-S906N/g0q/S906NKSS7FYG8` was selected. The fixed native
helper completed and its authenticated PRE marker survived physical original-A
return. The full two-marker calibration remains unproved. One N and one A
transfer completed; the candidate/grant are consumed/closed and no F1 owner
remains. A90 and S20+ were untouched.

## Scientific result and limits

The [qualified P424 helper](S22PLUS_NATIVE_LOG_CALIBRATION_P424_H0_2026-10-13.md)
ran once through the retained native carrier's authenticated command channel.
The [reviewed profile](../operations/S22PLUS_NATIVE_LOG_CALIBRATION_V1.md)
selected no storage command, mount, filesystem writer or installed Debian.

| Observation | Physical evidence |
| --- | --- |
| Native authentication, helper entry and settlement | Proved |
| PRE write and exact current-kernel-ring readback | Proved |
| Stock module syscall | One attempt, returned success (`module_errno=0`) |
| Fixed module/platform/proc binding conjunction | Unproved; stage 4, `ENODEV` |
| POST write / ring readback | Not reached |
| Current `/proc/ap_klog` snapshot | Not selected after binding failure |
| Cleanup | Completed with zero cleanup error |
| Complete live retained pair | Unproved |
| Exact PRE after physical original-A return | One authenticated match |

The complete live command result is **PASS_LOG_CALIBRATION_OBSERVED** with
scientific status **CALIBRATION_NEGATIVE**. This means the bounded observation
completed; it does not promote the failed binding check to success.

After healthy closure, the fixed D0 collector read **2097136 bytes** of
`last_kmsg`, bracketed by rooted health on the same returned Android boot.
The production decoder found one PRE at byte offset **1643997**, with zero
damaged candidates or foreign frames. Its run, original native boot, helper
identity and exact frame bytes match the live authenticated result. The verdict
is **PARTIAL_NATIVE_LOG_RETENTION**, with `live_pair_proved=false` and
`post_return_retention_proved=false` for the required complete pair.

This establishes retention of that one native-origin marker across the tested
physical return. It does not establish live current-backend membership, POST,
earliest Debian PID1, historical P421/P423 execution, installed Debian, SSH,
normal-reboot retention or automatic recovery. Missing POST is explained by
the recorded control flow, which stopped before generating it; it is not a
post-return retention failure. No bytes were reconstructed and no replay is
authorized.

## H0 finding: fixed binding name differs from observed probe name

The actual helper checks the exact symlink
`/sys/bus/platform/drivers/samsung,kernel_log_buf/soc:samsung,kernel_log_buf`.
The returned kernel log reports that driver probing device
`8.samsung,kernel_log_buf`. Thus the fixed observer's expected device name
differs from the observed probe name. Together with successful module return
and retained PRE, this is a concrete reason to examine the binding predicate
before concluding that the logger failed.

The stage-4 result aggregates module-directory, driver-link and proc-file
checks; it does not identify the failing predicate. The returned probe line
alone is not a live sysfs snapshot or proof of the complete binding conjunction.
The current backend was never opened by the helper, so its absence is not
proved. `p424-diagnosis-h0-1.json` pins the actual consumer, retained raw data,
live result and unchanged stock logger sources. This diagnosis changes no
execution code, reviewed capability, old result or consumed journal.

The smallest useful successor is an H0 correction/qualification of the exact
binding observation using this evidence. A later physical calibration needs
its own fresh qualified candidate and finite authority; P424 cannot repeat.

## Physical return and health-only continuation

Fresh original-A health and all bound source/artifact/recovery checks passed
before execution. The native observation settled and detached cleanly, after
which the owner requested physical Download. The normal A branch stopped
before dispatch when USB enumeration membership changed. Its preserved Odin
diagnostic names `inventory-membership-changed` at
`enumeration-evidence-before-snapshot`, with no persisted snapshot. That branch
has no A effect intent, launch record or Odin transfer capture.

After the operator reported Download entry, the existing attended recovery
owner verified the endpoint and transferred original A once. The first health
read then returned exit 1 with `error: closed`, without timeout, overflow or
producer failure. Its bounded raw evidence is preserved. Existing recovery
rederived the completed transfer and continued health only; it dispatched no
second A and no new native command or control.

Final root, original boot/supporting digests, changed Android boot, exact GPT
and **34357624832-byte** Android userdata capacity passed, with the native
partition present. Terminal: **ANDROID_CLOSED_HEALTHY**, `recovered=true`,
`research_closed=true`. Android health is separate from the scientific result
and does not constitute a native_data filesystem inspection.

## Canonical timeline

Seconds are host BOOTTIME elapsed from the original grant opening.

| Event | Seconds |
| --- | ---: |
| Live session start | 0.000 |
| Fresh Android preflight complete | 4.743 |
| Candidate flash start | 19.661 |
| Candidate flash done | 21.305 |
| Authenticated native readiness | Proved before fixed-command intent at 47.881 |
| Complete calibration observation | 51.651 |
| Normal A branch stops before dispatch | 100.899 |
| Original-A recovery flash start | 155.961 |
| Original-A recovery flash done | 157.320 |
| Health-only continuation complete | 280.377 |
| H0 audit and grant closure | 315.828 |

## Evidence preservation and closure

Process/device acquisition was blocked during H0 closure. It rederived both
transfers, the settled live command, initial/final health and terminal; checked
**676 raw captures**, the one classified ADB health failure, the separate
pre-dispatch enumeration diagnostic and **264 frozen source paths**; and
preserved the **18-row journal** and terminal byte-for-byte. The 16 post-closure
D0 captures succeeded. Pure H0 retention rederivation matched the stored
result, with the consumed journal, terminal and closed-task bytes unchanged.

Private evidence root:
`workspace/private/outputs/s22plus-native-log-calibration-p424-h0-20261013-1/`.
`offline-2/task/` holds the original preparation and consumed operation.
`source-snapshot-1/`, physical/return/recovery driver outputs,
`retention-p424-1/` and the closure/retention/diagnosis audits preserve provenance.
Execution base: `bf4c31b40b91b686a7c65ac4697ed94be643516a`, with the frozen
working-tree closure described in the H0 qualification report.

| Receipt | SHA-256 |
| --- | --- |
| Operation terminal | `602aa7b58e48b1356b4985af769e64ac18848972d9f7a0370c9c6739fa8e87e5` |
| Closure audit | `c365482a7be8f00828d0621fb57de033bae274863f9d096aa180c580b4b5aacd` |
| Closed task | `c91a37d3c63b010c64a8544cbcbb177e1c778e615012fd66aeee969c33fbf3b0` |
| Retained-log acquisition receipt | `fe79c02ed6a5ad1c58edcba1e6b75f71f7203203b31a8bee23fc8ba83bfaea4d` |
| Retention result | `83b34071f7a99652968c6dc30dba087125a1eb593bc7bb8f5e677795679f8dc3` |
| H0 retention audit | `c8f1db39657188792fcf9d69e82aeb673ceb87ffa5d358f88a4cdd9a216866f7` |
| H0 binding-name diagnosis | `44a35d1127d527afdb930ae5a0cf560c6e4786d3219fe9e11ad51e4d3bc14136` |

The bounded calibration, original-A recovery, retained-log collection and
reporting are complete. Full Debian/SSH ownership remains unachieved.
