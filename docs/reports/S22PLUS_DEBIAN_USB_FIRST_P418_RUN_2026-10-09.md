# P418 first physical run: partial retained records, USB unproved

Date: 2026-10-09 KST. Target: S22+ `SM-S906N/g0q/S906NKSS7FYG8` only.
Final state: **ANDROID_CLOSED_HEALTHY**, `recovered=true`.
Scientific result: **USB/PID1 protocol NO_PROOF; two authenticated stage records
retained across physical original-A return**. A90 and S20+ were untouched.

## Actual operation

The operator returned the exact prepared 1800-second, one-operation attended
grant for task `28edefbce472c08fa18441ca730af6c131267c733b321e1c589ed19fce938499`.
The [qualified P418 preparation](S22PLUS_DEBIAN_USB_FIRST_P418_H0_2026-10-08.md)
and [USB-first scope](../operations/S22PLUS_DEBIAN_USB_FIRST_V1.md) remained
unchanged. Current source/artifact/host binding and fresh original Android
health passed before control. One Android-to-Download control and one candidate
N transfer completed.

The exact early USB endpoint was not detected within 90 seconds. The stop
occurred before the early-observation directory, tty acquisition or challenge
transmission. No authenticated PID1 measurement or USB snapshot was obtained.
This does not establish continuous physical USB absence, non-execution, a
reboot/panic, or an internal failure stage. N was not repeated.

The first recovery attempt waited for physical Download and ended with a
pre-dispatch Odin-enumeration input error. Its raw captures and exception are
preserved; it produced no A-transfer intent. After the operator confirmed
physical Download, a fresh fixed observation under the same recovery owner
identified the exact endpoint and completed one original-A transfer.

The first post-A root-health read returned ADB device-not-found. Continuation
rederived the completed A transfer and performed health only. Full rooted
original boot/supporting hashes, changed Android boot, exact Android32 GPT,
native-partition presence and 34,357,624,832-byte userdata capacity passed.
Final transfer counts are **N=1, A=1**, with no additional recovery transfer.

## Retained evidence after closure

After the finite operation closed, the fixed D0 reader captured
`/proc/last_kmsg`: 2,097,136 bytes, SHA-256
`f859e585570763ef6d2611ef4356dd3cae245cb6d49c723edf9de484cd3b3d79`.
Before/after rooted health and shell-v2 checks bind the exact target and the
same Android boot as the completed original-A return. No further reboot,
transfer, mount, clear or device write was issued.

The original strict decoder stopped with `retained marker authentication
failed`. Its stop is retained and is not relabelled as a complete reader PASS.
The sequence-1 physical line contains a damaged marker body interleaved with
old Android QSEECOM text and the beginning of sequence 2. That captured
sequence-1 body does not authenticate.

H0 analysis located all marker headers, then authenticated each exact contiguous
captured body through its LF using the original candidate key/run and domain.
It reconstructed no message, shortened no body to force a match, changed no raw
byte and weakened no authentication check. Independent evidence review confirmed:

| Sequence | Exact authenticated event | Meaning |
| --- | --- | --- |
| 2 | `FYG8_H0 seq=2 TARGET_GUARD_OK` | The fixed preparation child's target guard completed. |
| 3 | `FYG8_H0 seq=3 MODULE_BEGIN ordinal=1 name=sec_log_buf` | The first module's BEGIN record was emitted. |

Both intact records bind one candidate kernel boot. Sequence 2 is embedded in
the damaged sequence-1 physical line, which explains why a line-first parser
did not reach it. These records prove partial device-local retention through
the tested physical return. They do not supply the missing challenge-bound
PID1/USB measurements.

`MODULE_BEGIN` precedes the per-insertion presence check and `finit_module`.
It proves neither invocation nor completion of that syscall, and does not prove
a stall. Missing `MODULE_DONE` or later records cannot distinguish stopped
execution from lost/overwritten evidence. The corruption's cause is unproved;
damaged/interleaved retained framing is a concrete concern for the next logging
qualification, not a reason to repeat this consumed candidate.

## Canonical timeline

Times are host BOOTTIME seconds from grant opening, not device execution time.

| Event | Seconds |
| --- | ---: |
| Fresh preflight complete | 2.460 |
| Android Download intent / complete | 2.643 / 6.443 |
| Candidate transfer intent / complete | 16.064 / 17.589 |
| Early endpoint observation start / stop | 17.644 / 107.812 |
| First recovery observation start; no A dispatch | 251.323 |
| Second recovery observation start | 444.853 |
| Original-A transfer intent / complete | 446.350 / 447.719 |
| First post-A health start | 447.731 |
| Health-only continuation start / complete | 567.212 / 571.215 |
| H0 finite-grant closure | 637.177 |

## Durable closure and limits

Private evidence root:
`workspace/private/outputs/s22plus-debian-usb-first-p418-h0-20261008-1/`.
`connected-1/task/operation-0001` owns the unchanged 16-row journal and terminal.
H0 closure blocked command acquisition, rederived the initial/candidate/recovery
proofs, verified 2,263 raw captures and 227 unique frozen source paths, and
confirmed the permanent consumed claim and absent F1 owner.

The task close SHA-256 is
`710b378d0712cbbaf48000ec79a576d72a090c8e0a14594a0cc2b95b3ac63308`;
terminal SHA-256 is
`aecfb1e5bad940a47e09956043ca05fd39eaa658a7a80656070db78b25b6a393`.
The separate `retention-1/h0-partial-analysis.json` has SHA-256
`d6409081a40bbc454cbb7bbeed55f05c558819ec68b027d74347d948c233fdf5`.
Its H0 audit revalidated all 16 D0 captures, both health brackets, exact intact
record spans and the unchanged strict-decoder rejection, without device calls.

Execution used the frozen complete working-tree closure over committed base
`73490f4c74033c844e9313bad97c6d3987b24c67`; the H0 report records the retained
source/artifact bindings. No critical source, consumed journal, raw evidence or
historical review was modified to obtain the partial interpretation.

The candidate and grant are consumed and closed. No UFS/GPT/native_data
observation, repair, writable-root handoff or installed Debian execution was
selected by P418. P415 remains the last authenticated native_data observation.
Original Android health, partial retained-stage evidence and the absent USB/
PID1 proof remain separate outcomes. No further candidate is selected here.
