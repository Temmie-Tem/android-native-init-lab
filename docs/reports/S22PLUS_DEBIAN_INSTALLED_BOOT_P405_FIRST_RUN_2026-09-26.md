# S22+ P405 installed Debian first run — 2026-09-26

## Result

P405 `v0.4.0-rc.5` transferred once to the exact operator-owned S22+ FYG8
after current rooted Android32 health and the operator's concrete attended
3600-second grant. The fixed 180-second NCM window ended without an endpoint.
Research stopped without SSH, Debian health, shutdown or a P399 transfer.
The operator physically entered Download; the exact original Android A
transferred once and its first final-health bracket passed.

The terminal is **NO_PROOF_ANDROID_CLOSED_HEALTHY**. Original boot/supporting
partition hashes, full GPT and 34,357,624,832-byte Android32 capacity match,
and the final rooted Android boot ID differs from the initial one. The F1
owner is absent, the finite grant is closed and P405's candidate claim remains
consumed. No transfer or control was replayed. A90 and S20+ were untouched.

## What the new observation establishes

All 98 bounded USB samples rederive from their original raw captures. Both
declared USB paths were absent at every sampled observation: 196
`ABSENT_USB` path results, spanning grant offsets 61.701–240.059 seconds.
There was no matching endpoint record and no NetworkManager connection setup.
Thus this P405 run did not merely reject a present interface by its MAC or
descriptor: the two permitted USB device paths themselves were not observed.

This is sampled, fixed-path host evidence. It does not establish continuous
USB absence between samples, inspect other physical paths, or identify the
bootstrap's last executed stage. Root validation, writable mount, SysVinit,
UDC/role setup and the RAM candidate marker remain unproved on Samsung. The
RAM log was not available through SSH. This result also does not retroactively
establish why P404 lacked an endpoint.

## Canonical timeline

Elapsed time uses the original finite grant's BOOTTIME clock. The final row
is a separate H0 close receipt after the live journal terminal.

| Elapsed (s) | Durable event | Meaning |
| ---: | --- | --- |
| 38.281 | owner-opened | Fresh exact rooted Android/storage health passed. |
| 40.721–43.404 | android-download intent/result | Original Android entered Download once. |
| 59.358–60.841 | candidate-boot intent/result | One P405 boot-only transfer; candidate claim consumed. |
| 241.075 | research-stopped | No NCM endpoint within the fixed observation window. |
| 274.650 | physical A statement | Operator confirmed Download entry. |
| 276.857–278.229 | android-restore intent/result | One exact original-A boot-only transfer. |
| 316.717 | terminal | Rooted Android32 health proved; F1 owner retired. |
| 363.026 | H0 close record | Source, transfer, health and all USB raw evidence rederived. |

Before the finite grant, the first preparation inventory was rejected for
ADB server-startup stderr despite producer exit zero. Its raw record remains
under `pregrant-android`; a separate allowed read-only preparation bracket
passed. This was not a device transition or a candidate attempt. Execution's
fresh-start bracket and the single final-health bracket both passed. The
[preparation report](S22PLUS_DEBIAN_INSTALLED_BOOT_P405_H0_2026-09-26.md)
records actual package/VM qualification and the independent source review.

## Preserved evidence and next scope

Private task:
`workspace/private/outputs/s22plus-debian-installed-h0-20260926-1/live-task-1`.
All 63 actual reviewed execution sources were saved before effects. The H0
closure rechecks their hashes, original Odin prelaunch intents/invocations and
raw completion, complete before/after Android health, the permanent consumed
claim, all diagnostic captures and the absence of an F1 owner.

| Receipt | SHA-256 |
| --- | --- |
| `plan.json` | `d7242e0d10ec6f8a6c6f90b315f55e833ea35dd96825649c1d1d4c78fc06370c` |
| `terminal.json` | `2927b13d68f69c75912f4d2c79ec33bdef2aeec45121fac481cc192f0207dfa4` |
| `closed.json` | `c2e7c977c1baab2510076c5fe042cc5969acde08776d9abab417cfc42808f7cb` |
| `source-snapshot.json` | `c23a5c3849bba70d5280050907d21e95547a3b9bba80e3d896c41b477edef49e` |
| `usb-diagnostic-audit.json` | `36d5a9e71a1ae2fe4de5c902949ae1328627fd620173d819240c41b890ed241f` |

The next bounded work is H0 design for evidence before USB availability,
including the retained root's state and the boundary between bootstrap root
validation and initial PID 1 handoff. Android recovery does not prove the
post-attempt native_data filesystem clean or unchanged. A future protected read
or new candidate needs its applicable current scope; no repair, reinstall,
P405 replay or extra live experiment is implied by this close.
