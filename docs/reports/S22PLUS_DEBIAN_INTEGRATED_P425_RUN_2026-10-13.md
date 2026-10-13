# S22+ P425: retained preparation progress, USB unproved, Android healthy

Status: **CONSUMED_NO_PROOF_ANDROID_CLOSED_HEALTHY**

P425 `v0.6.0-rc.1` ran once on the exact operator-owned
`SM-S906N/g0q/S906NKSS7FYG8` under the returned attended
3600-second/one-operation grant. The boot-only candidate and original Android A
each transferred once. The expected native USB endpoint did not arrive within
90 seconds, so no integrated start request or continuation was sent.
Installed Debian PID1, services, SSH and clean Debian shutdown remain unproved.

Physical original-A recovery and final health completed:
**ANDROID_CLOSED_HEALTHY**, `recovered=true`, `research_closed=true`.
The grant and candidate are consumed/closed, and no F1 owner remains.
A separate same-returned-Android-boot read preserved 146 authenticated early
preparation records, proving the corrected logger binding and provider barrier
passed on this physical boot. This is partial preparation evidence.

## Exact scope and starting state

The [H0 qualification](S22PLUS_DEBIAN_INTEGRATED_P425_H0_2026-10-13.md)
retains independent PASS_GO, exact A/B artifacts, nine integrated ARM64 VM
cases and four current revision-4 failure cases. Its source and image bindings
were unchanged for this trial. The [integrated policy](../operations/S22PLUS_DEBIAN_INTEGRATED_V1.md)
owned the whole operation; no old grant or candidate was reused.

Fresh fixed preparation and execution preflight proved the original Android
boot/supporting digests, root, exact target and full GPT/Android32 capacity.
Those reads did not inspect or admit native_data. The operator returned the
exact prepared approval and confirmed physical attendance and manual recovery.
The selected scope permitted protected native_data admission and a bounded
Debian writable lifetime, but neither is proved to have occurred.

## Physical sequence

Times are host BOOTTIME seconds from the original grant opening. They are
host event times, not inferred device execution timestamps.

| Event | Elapsed seconds | Result |
| --- | ---: | --- |
| Fresh execution preflight | 18.539 | PASS |
| Android Download request / arrival | 19.328 / 23.220 | Proved |
| P425 N transfer intent / completion | 32.337 / 33.958 | One successful transfer |
| Expected native endpoint wait | 34.188–124.397 | Timeout; no start transmission |
| First physical recovery wait | From 189.518 | No A dispatch |
| Original A transfer intent / completion | 399.668 / 401.035 | One successful transfer |
| Final Android health completion | 604.639 | PASS |

The first physical Download wait ended before any A launch or transfer intent.
Its preserved traceback reports rejection of a raw enumeration invocation.
H0 source inspection identifies the existing deadline-tail mismatch: the
endpoint loop can pass a positive remaining timeout below 0.1 seconds, while
the raw producer requires at least 0.1 seconds. The frozen implementation was
not changed during the run. After the operator indicated readiness to enter
Download, the same original recovery acquired the exact endpoint and sent A
once; the first read-only wait was not a transfer attempt.

The first post-A health read returned `error: closed` with no stdout. Its raw
failure remains preserved. Health-only continuation then proved the original
boot/root, changed Android boot ID and complete Android32/GPT state. It did not
send A again. The returned capacity remains 34,357,624,832 bytes, with the native
partition present; this does not prove native_data filesystem consistency.

## Retained physical evidence

After healthy closure, the existing fixed D0 collector read exactly 2,097,136
bytes from `last_kmsg`, between same-returned-boot original-A health brackets.
The command completed without truncation or producer error. Whole-capture
interpretation stopped on a current-run marker authentication failure. The raw
capture, parser stop and original closed records are unchanged.

Pure H0 analysis then verified the original contiguous raw prefix with the
existing strict decoder and separately rederived every authenticated record.
The prefix contains sequences 1–146 in order and one authenticated kernel boot.
No bytes were repaired or synthesized; each record retains its source offset,
length and SHA-256. Later malformed/interleaved material is excluded from these
claims, and the whole-capture parser remains failed.

| Authenticated record | Physical fact supported |
| --- | --- |
| 2: `TARGET_GUARD_OK` | Fixed helper target guard completed |
| 4: `LOGGER_BIND phase=0 error=0` | Corrected stock logger predicate completed successfully |
| 5: module 1 DONE | Stock logger module and required binding checks completed |
| 139: module 68 DONE | `qcom_spmi_pmic` module stage completed |
| 141: `PROVIDERS_READY mask=7` | Exact SPMI controller, PM8350c and GPIO provider barrier completed |
| 145: module 70 DONE | `gpi` module stage completed |
| 146: module 71 BEGIN | `i2c_msm_geni` insertion stage was entered |

The logger binding correction therefore has physical positive evidence.
The module-71 BEGIN record does not prove that insertion failed or that the
device stopped there. Later records are damaged or absent, and neither a full
platform-ready result nor the separate initial-parent measurement was retained.
The exact subsequent stopping point remains unknown. No USB receipt, installed
PID1, root admission, service, SSH, durable Debian record or shutdown proof is
inferred from this prefix or from successful Android recovery.

## Closure and provenance

The private output root is
`workspace/private/outputs/s22plus-debian-integrated-p425-h0-20261013-1/`.
`connected-1/task/closure-audit.json` rederives the initial/final health,
both transfers, consumed claim and terminal with process/device acquisition
blocked. It verifies 2,260 live raw captures and 329 frozen source files while
preserving the original 16-row journal and terminal bytes.

`connected-1/task/closed.json` closes the exact grant and original recovery.
The separate `retention-1/` keeps the 16 D0 command captures and strict parser
stop. `retention-prefix-audit.json` binds all 146 unchanged authenticated spans,
same-returned-boot health and the retained full-parser failure. Its SHA-256 is
`0ea8de6c357632fe2dd6b8ad792bc27578dcbd5734ca06c58c68318c8b932689`.

No candidate, compound request, shutdown or transfer is replayed. A90 and S20+
receive no commands or edits from this unit. Any successor begins from the
closed result and fresh qualification; the current candidate remains consumed.
