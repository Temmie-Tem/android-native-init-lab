# P419 RAM-only USB trial: no early endpoint, original Android healthy

Date: 2026-10-12 KST. Target: S22+ `SM-S906N/g0q/S906NKSS7FYG8` only.
Final state: **ANDROID_CLOSED_HEALTHY**, `recovered=true`.
Scientific result: **USB/PID1 NO_PROOF**. A90 and S20+ were untouched.

## Actual operation and result

The operator returned the exact 1800-second, one-operation attended approval
for task `466075ccf001ae92a51a6c33fc37b281c796e53f1e88e5b7693e7baf56fa3563`,
in response to the current-attendance/physical-Download condition. The
[qualified P419 preparation](S22PLUS_DEBIAN_USB_RAM_P419_H0_2026-10-12.md)
and [USB-first contract](../operations/S22PLUS_DEBIAN_USB_FIRST_V1.md) were
unchanged. Fresh machine binding and full original Android health passed.
One Android-to-Download control and one candidate N transfer completed.

The exact early USB endpoint was not detected within 90 seconds. Observation
stopped before the early-evidence directory, tty acquisition or challenge.
There is no authenticated P419 PID1, module-completion or USB result. The
operator reported the boot screen remained unchanged with no observed bootloop;
this is a separate visual observation, not an internal-stage or PID1 proof.

P419 removed the `sec_log_buf`/printk/readback prerequisites and retained the
73-module USB path plus mandatory RAM evidence. That change alone did not
produce an observable authenticated USB channel in this trial. It does not
identify where execution stopped, establish non-execution, or settle the cause
of P418's missing USB. The prior P418 partial retained records remain historical.

This candidate deliberately selected RAM evidence retrievable through USB only.
No post-return retention reader was selected or invoked, and internal RAM
records were not recovered. No UFS/GPT/native_data preparation, root mount,
filesystem write or installed Debian execution was selected by this candidate.
P415 remains the last authenticated native_data observation.

## Original-A recovery and final health

After the observation stop, the operator entered physical Download. The
machine observer matched the exact endpoint and one original-A transfer
completed. No candidate or Android transfer was repeated.

The first post-A health bracket lost ADB during its root-health command and
returned device-not-found. Its failed raw capture is preserved. Continuation
rederived the already completed A transfer and performed only health reads.
Full rooted original boot/supporting hashes, a changed Android boot, exact
Android32 GPT, native-partition presence and 34,357,624,832-byte userdata
capacity passed. Final transfer counts are **N=1, A=1**.

## Canonical timeline

Times are host BOOTTIME seconds after grant opening, not device runtime.

| Event | Seconds |
| --- | ---: |
| Fresh preflight complete | 2.984 |
| Android Download intent / complete | 3.399 / 7.081 |
| Candidate transfer intent / complete | 17.922 / 19.588 |
| Early endpoint observation start / stop | 19.701 / 109.902 |
| Original-A recovery start | 203.368 |
| Original-A transfer intent / complete | 210.535 / 211.964 |
| First post-A health start | 211.979 |
| Health-only continuation start / complete | 311.849 / 316.763 |
| H0 finite-grant closure | 402.141 |

## Durable closure

Private evidence root:
`workspace/private/outputs/s22plus-debian-usb-ram-p419-h0-20261012-1/`.
`connected-2/task/operation-0001` owns the unchanged 15-row journal and terminal.
H0 closure blocked command acquisition, rederived initial health, Download,
candidate and original-A transfers and final health, verified all 560 raw
captures including the classified failed health read, and joined 227 unique
frozen host/runtime source paths. The permanent consumed claim remains, no
F1 owner remains, and the finite grant is closed.

| Record | SHA-256 |
| --- | --- |
| Task close | `32e4f510020989afb239a50836f1734dc1bd1f1d69d75253bbd8ba9dc4043e91` |
| Operation terminal | `48b74d31e32743d484a94f95f1ced5e19e8a520ff5f235e45576ba1308117a4f` |
| Closure audit | `d58ef33915db2564b90ed342324a035e64e79a2d7413a275c521fa182ed13327` |

Execution used the frozen complete working-tree closure recorded by the
preparation over commit `91a060b119`. No execution-critical source, consumed
record, raw evidence or historical review was modified to obtain closure.
The candidate and grant remain consumed; no follow-up candidate is selected.
Healthy Android return and absent USB/PID1 proof retain separate meanings.
