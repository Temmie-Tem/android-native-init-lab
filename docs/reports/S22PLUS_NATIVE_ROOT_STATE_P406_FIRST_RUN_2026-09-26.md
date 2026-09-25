# S22+ P406 protected root inspection and Android return

## Result

P406 `v0.4.0-rc.6` completed one attended protected inspection of the retained
native_data root. Its result is **PASS_INSPECTION_COMPLETED** with
**COMPLETE_RECORD_BOOT_INPUTS_MATCH**. At observation, ext4 was clean:
state 1, RECOVER 0, orphan head 0. Installation start/completion records and
the original witness were present. All 8,969 expected archive entries matched,
including all 8,175 boot-input entries, with no missing, metadata or content
discrepancies. The helper hashed 199,362,324 known file bytes.

Native partition-only block RO, protected mount, ordinary unmount/cleanup and
unchanged complete superblock/GPT readback were proved. No filesystem data
write, repair, installed-code execution or PID 1 handoff occurred. This narrows
the investigation: a currently dirty or mismatched retained root was not
observed. It does not locate P404/P405's earlier stop or prove Debian init,
USB networking or SSH.

Original Android A returned after the native controller's normal Download
transition and one A transfer. The first final-health attempt stopped when a
boot-readiness read returned `error: closed` with exit 1 and empty stdout.
The existing runner rederived
the completed A transfer, then performed only the permitted health reads.
The next full bracket passed: distinct rooted Android boot, exact original
partition hashes, complete GPT and 34,357,624,832-byte Android32 capacity.

The unchanged terminal is **ANDROID_CLOSED_HEALTHY**, `recovered=true`;
the inspection PASS is retained. The recovery flag records the final-health
continuation, not another image transfer. P406, its one-operation budget and
grant are consumed and closed. There is no F1 owner, effect replay or physical
button intervention. A90 and S20+ were untouched.

## Binding and canonical timeline

Execution used preparation commit `be4079ae0d`, the current independent
`PASS_GO` and the [qualified actual P406 package](S22PLUS_NATIVE_ROOT_STATE_P406_H0_2026-09-26.md).
The operator returned the concrete attended one-operation start. Task SHA-256:
`1f9be032628c9d8d72279eeb9e5db4c5c81bfa1c6b3267e3e651b7f71554aa04`.
Grant SHA-256:
`67f1b905fc200be93f661b94a27c0284f5bec419a0f49ad52e17f991c3e0343b`.

Times below are seconds from opening the original 1,800-second BOOTTIME grant.

| Elapsed | Retained event |
| ---: | --- |
| 5.225 | Fresh exact original-A preflight completed. |
| 5.335–7.119 | One Android Download request and measured departure. |
| 17.956–19.448 | One P406 boot-only transfer intent and completion. |
| 38.427–41.248 | One authenticated inspection intent, complete raw proof and DETACH. |
| 42.772–43.380 | Same-native-boot CONTROL and measured Download departure. |
| 49.492–51.031 | One original-A boot-only transfer intent and completion. |
| 77.719 | Initial final-health readiness read stopped with `RawCaptureError`. |
| 77.768–85.167 | Health-only continuation and complete Android32 final proof. |
| 164.016 | Raw audit completed and the grant closed. |

The five effect intents are exactly Android Download, P406 transfer, fixed
inspection, native Download and original-A transfer. There is one consumed
operation. No second inspector execution or recovery transfer was introduced.

## Retained evidence

Private evidence is under
`workspace/private/outputs/s22plus-debian-root-state-p406-h0-20260926-1/`.
The close audit rederived the five completed normal steps and the final
health-only continuation from their original captures. All 618 raw capture
receipts and stream identities were checked, along with the 217 source files
saved before effects. The 20 append-only journal rows remained unchanged.

| Record | SHA-256 |
| --- | --- |
| Inspection stdout, 705 bytes | `6e1a299d4b11a97c3d891ec32092af198f5a53858a27324e7071755cdcc3f35a` |
| Terminal | `071cbf0570a450952678a660da75838e4f4e1936c7a49ef762000d6a2a76ad85` |
| Closure audit | `24d06ea7663c4da9e9a5dc0b7fae697bfac93c8fffffdc969cfd3c9573517187` |
| Closed grant | `ed6f5e6f865694b323cd356f980c2f4b7cd9928461633455a86cf0c9aaadca32` |
| Source snapshot | `9d3cafc939d475f844bec32b17456312429b1a332e1d8b8fc7891c918714319f` |

The next bounded question is the installed-boot bootstrap path before Debian
init: module/UFS readiness, its own root checks and the handoff boundary. Its
observation design must return evidence without depending on Debian NCM/SSH.
P406 supplies current root evidence; it grants no further experimental effect.
