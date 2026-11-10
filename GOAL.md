# Goal: S22+ mainline Linux and resident Debian home server

On **2026-10-27**, the operator selected **mainline Linux as the final kernel
direction** for the operator-owned Samsung Galaxy S22+
SM-S906N / g0q / S906NKSS7FYG8. The final product boots directly into a
persistent Debian arm64 home server, with Debian init as **host PID 1 in the
initial PID namespace**, ordinary package-managed services and authenticated
headless access. A resident native supervisor or isolated Debian child is not
the selected product architecture.

**Android is to be retired from the final operating system.** Its present role
is a verified experimental return and management environment. Keep that route
during early mainline qualification, then replace its role with an independently
usable Linux rescue path and demonstrated Download recovery. Returning to
Android after each experiment is not a requirement of final resident operation.
Android retirement does not imply removing the bootloader, hypervisor,
TrustZone, calibration, device-identity or required firmware partitions.

The FYG8 vendor-kernel route remains a retained recovery/comparison resource;
it is no longer the final kernel architecture or the primary development track.
Do not update Samsung firmware, including the proposed One UI 8 / Android 16
route. Firmware stays FYG8 while the Linux kernel and device tree are developed
separately under the applicable target contract.

This goal records product direction and state, **never device authority**.
[AGENTS.md](AGENTS.md) and the [S22+ binding target contract](docs/operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md)
continue to govern actual effects. This selection changes no active lane,
permanent boundary, source review, grant or recovery owner. A90 and S20+
identities, goals, artifacts and authority remain separate.

## Current state and evidence

- **ML050 completed automatic original-A return and closed healthy.** The
  host saw no USB endpoint in 73 samples during the initial 120 seconds.
  New-generation Download appeared at N+590.227 seconds and the owner
  dispatched original A once at N+591.636. A health-only continuation
  passed all seven final Android reads. The same-boot post-closure reader
  recovered 2,097,136 bytes with zero ML050 records or candidate identifier
  occurrences. Physical bind and UDC state remain unproved. ML050 is
  consumed and the owner is released.
  [Physical result and retained-log audit](docs/reports/S22PLUS_MAINLINE_ML050_UDC_AUTO_RETURN_RUN_2026-11-11.md)

- **ML049 was prepared and remained unexecuted when ML050 was selected.** A new
  Debian RAM-only boot image records configfs bind outcomes and timed device
  states in the small Samsung retained-log window. In the actual-kernel ARM64
  fixtures the returned records distinguished EBUSY/controller absent,
  successful bind/not attached, and successful bind/configured. The
  independent review passed for the exact package, reader and terminal
  backend. This ordinary RAM owner requires attended physical Download for
  original-A return and healthy closure before the fixed log read. Physical
  UDC state and retention are unproved.
  [Candidate and evidence](docs/reports/S22PLUS_MAINLINE_ML049_UDC_OBSERVATION_H0_2026-11-11.md)

- **ML048 reached the original 120-second USB deadline with the cable and
  buttons untouched, as confirmed by the operator after the window.** All 88
  host samples reported the selected USB path absent with zero related
  children. No endpoint, first request, authenticated response or UFS permit
  followed. The fresh candidate reused ML047's exact V12 capability. The
  original owner observed new-generation Download at N+588.979 seconds,
  transferred original A once and closed `ANDROID_CLOSED_HEALTHY` after
  seven successful final health reads through its health-only continuation.
  One failed ADB read is preserved. The audit verified 7,005 raw captures
  across 28 pages and owner release. ML048 is consumed with UFS `NO_PROOF`.
  [No-replug experiment and raw audit](docs/reports/S22PLUS_MAINLINE_ML048_NO_REPLUG_RUN_2026-11-11.md)

- **ML047 captured UIC_ERROR and is consumed with `NO_PROOF` and
  `ANDROID_CLOSED_HEALTHY`.** Six local UniPro commands succeeded and
  one DME_LINK_STARTUP was issued with pre-command HCS `0x8`. The first
  rejected IRQ_STATUS word was `0x00000004`, solely UIC_ERROR. V12 retained
  that exact sample before returning EIO. The originating protocol layer
  remains unknown. Authenticated result-bound Download and one original-A
  transfer restored Android. The same owner retained one failed initial ADB
  read and passed all seven final health reads. The offline audit verified
  531 task captures over three pages and both cue receipts. The owned profile
  is absent and the F1 owner is closed. A host audio-wait timeout is recorded
  separately from the operator's completed reconnection.
  [Physical result and raw audit](docs/reports/S22PLUS_MAINLINE_ML047_RUN_2026-11-11.md)
  · [V12 implementation and independent review](docs/reports/S22PLUS_MAINLINE_ML047_LINK_IRQ_H0_2026-11-11.md)

- **ML046 is consumed with `NO_PROOF` and `ANDROID_CLOSED_HEALTHY`.** V11
  again sampled CFG1 pre/post `0x1c00052c`, with bit 0 clear, but passed the
  original budget and progressed through all six local UniPro commands and
  the one permitted link-start command. The result was EIO. Source inference
  narrows it to unexpected IRQ_STATUS bits during link polling; the actual
  failing word was not recorded, and the terminal zero fields are unfilled,
  not observed successful values. The 300-second same-boot witness and all
  initial guards passed. Automatic result-bound Download, one original A and
  the same owner's health-only continuation completed all seven final reads,
  retaining the initial ADB failure. All 497 task captures/two pages and both
  cue captures were audited; the owned profile is absent and no F1 owner
  remains. Local-command/link-attempt progress is proved; link success,
  bit-clear cause and hang recovery remain unproved. No further device action
  is opened.
  [Physical result and raw audit](docs/reports/S22PLUS_MAINLINE_ML046_RUN_2026-11-11.md)
  · [Argon analysis, bounded correction and validation](docs/reports/S22PLUS_MAINLINE_ML046_CFG1_SELECTION_H0_2026-11-11.md)

- **ML045 is consumed with `NO_PROOF` and `ANDROID_CLOSED_HEALTHY`.** The
  V10 diagnostic identified the first CFG1 bit-readback branch: both existing
  reads were `0x1c00052c`, bit 0 was clear, and the budget check was not
  evaluated. All eleven initial guards and the timely initial IS-zero
  acknowledgement passed; stage six had PCS ready and settled eleven power
  records, but zero local UIC/link commands. The immediate-readback cause and
  ML044's unrecorded branch remain unproved. The repaired capture CLI issued
  the cue at N+33.689 seconds; actual completion was recorded at N+64.138.
  Authentication completed at N+57.847 seconds and the five-minute witness
  passed. Automatic result-bound Download and one original A completed; the
  same owner's health-only continuation retained one failed ADB read then
  passed all seven final reads. All 532 task captures/three pages plus both
  cue captures were audited, the owned profile is absent and no F1 owner
  remains. No further device action is opened.
  [Physical result and raw audit](docs/reports/S22PLUS_MAINLINE_ML045_RUN_2026-11-11.md)
  · [Argon analysis, H0 validation and independent review](docs/reports/S22PLUS_MAINLINE_ML045_CFG1_DIAGNOSTICS_H0_2026-11-11.md)

- **ML044 is consumed with `NO_PROOF` and `ANDROID_CLOSED_HEALTHY`.** V9
  completed one exact initial `0x400` acknowledgement and observed timely full
  IS zero after all eleven guards. One HCE stop completed in one poll (reported
  2 microseconds), HCS masked sample remained `0x8`, and eleven fixed power
  records settled. The reset/PHY/lane path reached stage six, then EIO occurred
  with zero local UIC commands and no link command. Source inference narrows
  this to the first HCI_CFG1 bit-0 readback-or-budget branch before the HCE-one
  write; the raw value and which alternative failed remain unobserved. A host
  cue-wrapper argument error followed by a correctly refused late caller was
  preserved. The operator later recalled probably reconnecting after watching
  the screen and progress. The action time is unknown. Authentication completed
  at N+116.258 seconds and the same-boot witness passed. Automatic result-bound
  Download and one original A completed; one failed ADB health read was kept
  and the same owner passed all seven final reads through health-only recovery.
  All 586 captures/three pages and the separate cue refusal were audited, the
  owned profile is absent and no F1 owner remains. Initial acknowledgement and
  later preparation progressed; completion-event origin, final EIO cause, UFS
  link and hang recovery remain unproved. No further device action is opened.
  [Physical run, incident and raw audit](docs/reports/S22PLUS_MAINLINE_ML044_RUN_2026-11-11.md)
  · [Mythos analysis, implementation and independent review](docs/reports/S22PLUS_MAINLINE_ML044_UIC_COMPLETION_H0_2026-11-11.md).

- **ML043 is consumed with `NO_PROOF` and `ANDROID_CLOSED_HEALTHY`.** After
  its exact attended grant, V8 passed authenticated USB, child liveness and the
  five-minute same-boot witness. One HCE stop observed zero in one poll within
  the original bounds (reported interval 4 microseconds). The same-read HCS
  sample masked by `0x39` was `0x8`, and the new predicate passed. Both
  doorbells, both RUN registers and IE then passed; the next IRQ_STATUS read
  refused raw `0x400` (UIC_COMMAND_COMPL). Later post-stop predicates remain
  unobserved. No status clear, fixed RPMh request, reset pulse, local UniPro or
  link command followed. Result-bound automatic Download and one original A
  completed; one failed ADB health read was preserved and the same executor's
  health-only path passed all seven reads. No physical Download was requested,
  the owned profile is absent and no F1 owner remains. All 542 raw captures
  and the three-page closure were rederived offline. The new HCS predicate
  made physical progress; the bit's internal cause, later initialization and
  link/hang recovery remain unproved. The next bounded H0 question is the
  post-stop completion-status predicate, without clearing it or replaying ML043.
  [Physical run and raw audit](docs/reports/S22PLUS_MAINLINE_ML043_RUN_2026-11-11.md)
  · [Mythos discussion, implementation and review](docs/reports/S22PLUS_MAINLINE_ML043_DISABLED_HCS_H0_2026-11-11.md).

- **ML042 is consumed with `NO_PROOF` and `ANDROID_CLOSED_HEALTHY`.** The
  reviewed V7 candidate passed authenticated USB, child liveness and the
  five-minute same-boot witness. Its pre-stop exact CTL `0xb` and IO bit-0
  high-latch predicates passed; one HCE-zero write then observed full zero
  in one poll within the original limits (reported interval 2 microseconds).
  The next HCS check refused raw `0x8`, the UIC_COMMAND_READY bit; later
  post-stop predicates remain unobserved. No fixed RPMh request, device-reset
  pulse, local UniPro or link command followed. The authenticated negative
  result selected automatic Download and one original-A transfer. One failed
  ADB health read was preserved; the same executor's existing health-only
  recovery passed all seven reads. No physical Download was requested or
  reported; the owned profile is absent and no F1 owner remains. The 537 raw
  captures and three-page closure were rederived offline.
  HCE stop is now physically observed; UFS link, timer/hang recovery and
  electrical reset state remain unproved. The next bounded H0 question is the
  post-stop HCS readiness predicate, without changing it or replaying ML042.
  [Physical run and raw audit](docs/reports/S22PLUS_MAINLINE_ML042_RUN_2026-11-11.md)
  · [Mythos analysis, implementation and independent review](docs/reports/S22PLUS_MAINLINE_ML042_RESET_CONFIG_H0_2026-11-10.md).

- **ML041 is consumed with `NO_PROOF` and `ANDROID_CLOSED_HEALTHY`.** The
  second requested physical experiment reused the unchanged V6 capability and
  its unused qualified peer, with a fresh exact attended grant. Its predeclared
  no-cue branch produced 88 absent first-window censuses and no protocol request,
  child-arm receipt, witness or module permit. Exact new-generation Download
  arrived automatically at N+587.921 seconds inside the original 660-second cap;
  one original-A transfer and all seven first-bracket health reads completed.
  No physical fallback was requested or reported, no profile was created and no
  F1 owner remains. Arrival and healthy recovery are proved; the guest trigger,
  PID1/UFS progress and kernel-stall recovery remain unproved. Conditional
  unattended F1 stays inactive. A post-terminal 2 MiB raw-index overflow is
  handled by a separate reviewed H0 paged finalizer, preserving original raw
  evidence, execution sources and consumed state without replay.
  [Run, proof limits and reporting repair](docs/reports/S22PLUS_MAINLINE_ML041_RUN_2026-11-10.md).

- **ML040 is consumed with `NO_PROOF` and `ANDROID_CLOSED_HEALTHY`.** Its
  reviewed V6 candidate passed USB, child-arm/liveness and the five-minute
  same-boot witness. HCE handoff stopped before its write at RESET_OUTPUT,
  raw control word `0xb`; HCE/HCS/IS remained observed as `1`/`0x10f`/`0x400`.
  No HCE stop, fixed RPMh or local/link command followed. The complete negative
  result triggered automatic Download and one original-A return; all seven
  final-health reads passed on the first bracket. No physical Download or
  recovery/health continuation was needed, the owned profile is absent and no
  F1 owner remains. This proves the new completed-refusal return path, not the
  timer or kernel/probe-stall recovery. Conditional unattended F1 stays inactive.
  One cue-wrapper output-directory failure occurred before caller spawn and
  was repaired without replay; the actual cue and completion were timely.
  Pin-direction semantics and no-response automatic recovery are the next
  bounded questions. [Run and raw audit](docs/reports/S22PLUS_MAINLINE_ML040_RUN_2026-11-10.md)
  · [Implementation and review](docs/reports/S22PLUS_MAINLINE_ML040_HCE_AUTORECOVERY_H0_2026-11-10.md).

- **ML039 is consumed with `NO_PROOF` and `ANDROID_CLOSED_HEALTHY`, with a
  complete physical HCE snapshot.** A fresh key-only candidate reused the
  unchanged v5 capability/review and v41 owner. The host popup/beep accompanied
  the one attach cue; authenticated base arrived at N+63.839s and the operator's
  completion reply at N+73.953s. The same-boot witness passed with 300.336s
  host and 300.423s guest advance. One module permit returned stage 2 / HCI
  QUIESCENT / HCE FAIL, with raw HCE `0x1`, HCS `0x10f`, both doorbells zero,
  interrupt enable zero and interrupt status `0x400`. All six snapshot fields
  were captured; later guard predicates remain unevaluated. No fixed RPMh
  request, local UniPro or link command followed. Physical Download and one
  original-A transfer restored Android; after one failed ADB health read,
  the existing health-only continuation passed all seven fresh reads. The
  owned profile is absent and no F1 owner remains. HCE's full value is now
  observed, while its origin and any safe initialization change remain separate
  H0 questions. No guard, deadline or hardware scope changed and this run cannot
  replay. [Physical snapshot and raw audit](docs/reports/S22PLUS_MAINLINE_ML039_RUN_2026-11-10.md).

- **ML038 is consumed with `NO_PROOF` and `ANDROID_CLOSED_HEALTHY`.** It
  reused the already qualified unused peer and unchanged v5 capability/review,
  with a fresh exact attended task. N transferred once; all 88 selected USB
  censuses were absent through 120 seconds. A timely cue was issued at N+26.527s;
  its completion reply arrived after expiry and actual physical timing remains
  unmeasured. No base request, witness or module permit was sent. After cue
  resolution and physical Download, original A transferred once. One closed-
  channel ADB health read was preserved; a health-only continuation passed all
  seven fresh reads. No profile or F1 owner remains. A host popup/beep test
  requested by the operator was noticed successfully; it is an attention signal,
  not device authority or proof of the USB failure cause. Its first-response
  failure cause remains unproved. This run did not exercise HCE diagnostics
  and cannot replay.
  [Physical run, reuse and raw audit](docs/reports/S22PLUS_MAINLINE_ML038_RUN_2026-11-10.md).

- **ML037 is consumed with `NO_PROOF` and `ANDROID_CLOSED_HEALTHY`.** Its
  HCE-state diagnostic capability passed 54 focused checks, independent
  PASS_GO, fresh complete artifact qualification and v41 preparation. The
  exact attended operation transferred N once but all 88 selected USB censuses
  were absent through the original first-response window. One timely cue was
  issued; the actual completion reply arrived after expiry, with physical
  reconnection time unmeasured. No base request, five-minute witness or module
  permit was issued, so the new diagnostic has no physical result. The cue was
  resolved before separate physical Download; original A transferred once and
  the first seven-read health bracket passed. No profile was created and no F1
  owner remains. The H0 implementation and one attended experiment are complete;
  this run left the HCE-state question unproved. A future fresh candidate may reuse
  the unchanged reviewed capability but needs its own current attended
  admission. No guard or deadline was relaxed and ML037 cannot replay.
  [Physical run and raw audit](docs/reports/S22PLUS_MAINLINE_ML037_RUN_2026-11-10.md)
  · [Implementation and qualification](docs/reports/S22PLUS_MAINLINE_ML037_HCE_SNAPSHOT_H0_2026-11-10.md).

- **ML036 is consumed with `NO_PROOF` and `ANDROID_CLOSED_HEALTHY`.** The first
  shared-V2 physical run passed USB admission and the five-minute same-boot
  witness. Its new diagnostic identifies stage 2 / HCI QUIESCENT / HCE FAIL:
  the original controller-enable predicate observed a nonzero value, while
  all later guard predicates remain unobserved. No fixed RPMh request, local
  UniPro or link command followed. Its origin and ML035's historical predicate
  remain unproved. Physical Download, one original A and a fresh seven-read
  health-only continuation closed the run after one failed ADB health read.
  N/A each transferred once; the owned network profile is absent and no F1
  owner remains. The grant/candidate cannot replay. Further work starts with
  H0 study of the HCE handoff/initialization condition, without relaxing the
  guard. [Physical run and raw audit](docs/reports/S22PLUS_MAINLINE_ML036_RUN_2026-11-10.md)
  · [V2 adoption and preparation](docs/reports/S22PLUS_MAINLINE_UFS_V2_ADOPTION_H0_2026-11-10.md)

- **ML035 is consumed with `NO_PROOF` and `ANDROID_CLOSED_HEALTHY`.**
  The corrected BCM producer passed the unchanged USB/PM/ICC/SH1/CN0 admission
  on the first attempt, with its USB reference released. Authenticated base
  arrived at N+90.749s; the same-boot witness proved a 300.405s host interval
  and 300.525s guest uptime advance. The one module permit returned `EBUSY(16)`
  at stage 2, with no fixed RPMh request or local UniPro/link command. Earlier
  PM/clock preparation occurred; the precise stage-two rejecting predicate is
  unobserved. Physical Download and one original A restored Android. After an
  ADB disappearance in the first health bracket, health-only continuation
  completed seven fresh reads. N/A each transferred once, the network profile
  is absent and no F1 owner remains. It is a preceding physical closure and
  cannot replay. [Physical run and raw audit](docs/reports/S22PLUS_MAINLINE_ML035_RUN_2026-11-10.md)
  · [H0 correction and preparation](docs/reports/S22PLUS_MAINLINE_ML035_BCM_ALIAS_H0_2026-11-10.md).

- **ML034 is consumed with `NO_PROOF` and `ANDROID_CLOSED_HEALTHY`.** Its
  authenticated base arrived at N+67.704s; the same-socket witness proved a
  300.355s host gap and 300.495s guest uptime advance. One coverage attempt
  reported `BCM_VALUES`, with no trylock failure: SH1's confirmation cache had
  Y values 0/0/0 instead of the required 1/1/1. No overlay/UFS probe, local
  UniPro or link command followed. This identifies ML034's rejecting branch,
  not the cause of the zero cache values or ML033's historical branch.
  Physical Download and one original A restored Android. After a closed-channel
  readiness-read failure, health-only continuation passed seven fresh reads.
  N/A each transferred once, the owned network profile is absent and no F1
  owner remains. It is a preceding physical closure and cannot replay.
  [Physical run and raw audit](docs/reports/S22PLUS_MAINLINE_ML034_RUN_2026-11-10.md)
  · [Correction and H0 evidence](docs/reports/S22PLUS_MAINLINE_ML034_USB_ADMISSION_H0_2026-11-10.md)
  · [Exact prospective scope](docs/operations/S22PLUS_MAINLINE_UFS_LINK_USB_ADMISSION_V1.md).

- **ML033 is consumed with `NO_PROOF` and `ANDROID_CLOSED_HEALTHY`.** Its
  authenticated first response arrived at N+74.463 seconds, within the original
  120-second window. A fresh same-socket witness proved a 300.422-second host
  interval and 300.564-second guest uptime advance on the same boot. The one
  module permit returned operation `EBUSY(16)` at stage 0 with no USB coverage,
  fixed RPMh request or UniPro/link command. Retained source locates this at
  initial USB-coverage admission; the exact rejecting condition is unobserved.
  Physical Download and one original A restored Android; after one failed ADB
  health read, the permitted health-only continuation passed seven fresh reads.
  N/A each transferred once, the owned network profile is absent, and no F1
  owner remains. First-response and five-minute proof are retained independently
  from the unproved UFS link. It is a preceding physical closure and cannot replay.
  [Physical run and raw audit](docs/reports/S22PLUS_MAINLINE_ML033_RUN_2026-11-10.md)
  · [Comparison, evidence and preparation](docs/reports/S22PLUS_MAINLINE_ML033_USB_COMPARISON_H0_2026-11-10.md)
  · [Adopted scope](docs/operations/S22PLUS_MAINLINE_UFS_LINK_TIMED_ATTACH_V1.md).

- **ML032 is consumed with `NO_PROOF` and `ANDROID_CLOSED_HEALTHY`.**
  The corrected caller issued one cue with 101.163 seconds remaining, but all
  86 sealed USB censuses reported the selected path absent. No base request,
  five-minute witness or UFS permit was issued. The reconnect completion
  response arrived after observation expired; the actual physical action time
  is unmeasured. Its cue was resolved before separate physical Download.
  Original A transferred once, then the permitted health-only continuation
  completed all seven reads after an ADB disappearance in the first bracket.
  N/A each transferred once, no F1 owner remains, and ML032 cannot be replayed.
  It is the preceding physical closure. This proves cue publication during live
  polling, not mainline boot, timely physical replug or a UFS failure cause.
  Later retained host-journal analysis found its exact USB identity/NCM at
  N+180.621/+180.685 seconds, outside the original first-response window.
  That passive enumeration does not upgrade authenticated proof or establish
  the physical reconnect time; the terminal result remains unchanged.
  [Physical run](docs/reports/S22PLUS_MAINLINE_ML032_RUN_2026-11-09.md)
  · [H0/adoption evidence](docs/reports/S22PLUS_MAINLINE_ML032_CUE_REFRESH_H0_2026-11-09.md).

- **ML031 is consumed with `NO_PROOF` and `ANDROID_CLOSED_HEALTHY`.**
  Its N transfer completed, but all 86 sealed USB censuses reported the
  selected path absent. Two prepared cue calls failed the latest-census
  stability check; a third failed the remaining-time check. No cue, base
  request or UFS permit was issued. A deterministic H0 fixture reproduces the
  refusal when another identical absence census appears between checks;
  the exact live comparison ordinals were not recorded. Physical Download,
  one original-A recovery and seven final health reads completed. ML031 is
  a preceding healthy closure and cannot be replayed.
  [Physical run](docs/reports/S22PLUS_MAINLINE_ML031_RUN_2026-11-09.md)
  · [H0/adoption evidence](docs/reports/S22PLUS_MAINLINE_ML031_ATTACH_DWELL_H0_2026-11-07.md).

- **ML030 is consumed with `NO_PROOF` and `ANDROID_CLOSED_HEALTHY`.**
  Its one attended N transfer completed, but all 87 sealed USB censuses found
  the selected path absent through the original 120-second window. No base
  request, five-minute witness or UFS permit was sent. Assistant-side cue
  preparation missed the permitted replug-issuance window; no cue was issued.
  This does not establish a boot or UFS failure cause. Physical Download and
  one original-A recovery completed with seven successful final health reads.
  Its candidate cannot be replayed.
  [Physical run](docs/reports/S22PLUS_MAINLINE_ML030_RUN_2026-11-07.md)
  · [H0 evidence](docs/reports/S22PLUS_MAINLINE_ML030_DWELL_LINK_H0_2026-11-05.md)
  · [adopted policy](docs/operations/S22PLUS_MAINLINE_UFS_LINK_V1.md).

- **ML029 completed a host-only UFS wiring and probe study.** A private copy
  of the disabled ML028 DT gained two known g0q connections (reset GPIO 210
  and PHY analog L5) and a correction to the host reference-clock rate
  table. Reversing those three changes reproduced ML028's canonical DT.
  This study left the PM8350 L6/L9 supply and pre-scan command limits for
  ML030. The study itself performed no device action.
  [Study, sources and next decision](docs/reports/S22PLUS_MAINLINE_ML029_UFS_H0_2026-11-05.md).

- **ML028 is consumed with `PASS_DEBIAN_RC_SSH_CYCLE_RAM` and `ANDROID_CLOSED_HEALTHY`.**
  On the S22+, packaged rc2 started SSH, one fixed UID/GID 1000 command
  succeeded with zero effective capabilities, and rc6 stopped the same master.
  An exact normal Download ticket admitted original A. N and A each transferred
  once. After an ADB health read failed, the existing owner completed a fresh
  seven-read bracket and removed its network profile. The one-service RAM
  result is complete. [Physical run](docs/reports/S22PLUS_MAINLINE_ML028_RUN_2026-11-05.md) · [H0 qualification](docs/reports/S22PLUS_MAINLINE_ML028_RC_SSH_CYCLE_H0_2026-11-05.md).

- **ML027 is consumed: PASS_MAINLINE_DOWNLOAD_RAM / ANDROID_CLOSED_HEALTHY.**
  Authenticated packaged Debian RAM PID1/USB and one same-connection fixed
  control led to machine-proved normal Download and original-A return.
  N/A each transferred once. One failed final-health properties read was
  preserved; a health-only continuation completed all seven health reads
  without another transfer. The owned profile was removed and no owner remains.
  No physical Download was requested. Automatic failure recovery, full SysV
  shutdown and persistence remain unproved; its grant is consumed.
  [Run and limits](docs/reports/S22PLUS_MAINLINE_ML027_RUN_2026-11-05.md) · [H0 qualification](docs/reports/S22PLUS_MAINLINE_ML027_DOWNLOAD_RETURN_H0_2026-11-05.md).

- **ML026 is consumed: PASS_DEBIAN_SSH_RAM / ANDROID_CLOSED_HEALTHY.**
  Authenticated packaged Debian PID1/USB and one same-boot fixed SSH command
  proved UID/GID 1000 and zero effective capabilities. N/A each transferred
  once; normal final health passed and the owned profile was removed. A tool
  acknowledgment timed out, but the original continuation completed without
  replay. Anchor/final names matched, so correction causality is not isolated.
  Persistence/general shell/automatic recovery remain unproved; no new owner/grant.
  [Run and limits](docs/reports/S22PLUS_MAINLINE_ML026_RUN_2026-11-05.md) · [H0 correction](docs/reports/S22PLUS_MAINLINE_ML026_INTERFACE_BINDING_H0_2026-11-05.md).

- The mainline baseline has proved RAM PID1/USB, packaged Debian SysVinit as
  initial PID1, the ML026 fixed unprivileged same-boot SSH command and ML027's
  fixed normal Download return. ML028 joined packaged rc2 startup, nonroot SSH,
  rc6 stop and normal Download in one RAM boot. It
  has not proved installed Debian on mainline, Linux UFS, full SysV shutdown,
  a general shell, automatic failure recovery, residency or endurance.
- ML025 and ML024 are closed NO_PROOF with original-A/final health complete.
  ML024's late replug report remains separate from its actual unknown timing;
  ML025's interface-name stop remains separate from rename/replug causality.
  Their grants, candidate effects and raw failures remain consumed.

## Selected architecture and reuse

The initial preferred mainline boot route is:

    retained Samsung ABL -> reviewed uniLoader boot payload
                        -> mainline Linux + g0q DTB + minimal initramfs
                        -> admitted Debian root -> exec Debian host PID 1

uniLoader has delivered the FYG8 Android control, ML003's early mainline entry
and ML021's authenticated RAM PID1/USB boot. Installed Debian on mainline is
still unproved. The initial carrier
should retain stock vendor_boot/DTBO and avoid changing the bootloader or
recovery partition. Pin the complete loader/kernel/patch/config/DTB/initramfs
set. Do not copy the sister port's Android-removal or flashing workflow.

Reuse Debian userspace, authenticated access design, package/data expectations,
host tooling and raw-first evidence/recovery practices where compatible.
Vendor modules, platform preparation, USB ownership, watchdog controls,
kernel health predicates and prior artifact reviews do not automatically
transfer to mainline. Required firmware remains privately retained and bound.

The bootstrap owns only temporary preparation and root admission. Debian owns
services, process reaping, device events, networking, logging, filesystem
policy and shutdown after exec. Target-specific long-lived helpers must be
ordinary Debian-managed services with explicit lifecycle and logs. Normal
resident boot must not require an interactive native shell or a development
host permission exchange.

Retain the current Debian init/root where compatible for initial integration.
Evaluate systemd, containers and other ordinary Linux facilities against the
new kernel's actual configuration and runtime; do not require a simultaneous
userspace migration merely to prove the new boot path. Display, desktop,
camera, telephony, sensors and system suspend are optional later work.

## Completed bounded unit: ML027 normal Download from RAM

The selected unit uses the same four-package Debian RAM SysVinit closure and
adds one distinct authenticated Download control, mutually exclusive with the
SSH variant. The same TCP connection first supplies full sealed base evidence;
only its validated current boot/artifact can receive one fixed control. The
existing mainline NVMEM reboot-mode driver gains only the exact DT Download
value, and the existing SCM NODUMP/PSCI normal reboot chain remains explicit.
There is no Linux storage or new vendor-module/reset framework.

H0 qualification, complete producer reproduction, independent review and exact
boot-only preparation were followed by one approved attended physical run.
The issued replug cue was resolved before normal control. The original
host/device windows, fixed intent-time return deadline, exact Download ticket,
single original-A transfer and final health all joined their retained evidence.
The first failed health bracket remains separate from the successful complete
health-only continuation; consumed controls and transfers never replayed.

The selected completion criterion, `PASS_MAINLINE_DOWNLOAD_RAM`, is achieved.
ACK/EOF alone were not accepted as Download arrival. This normal return proves
neither automatic stall recovery nor persistent/resident Debian. The broader
watchdog interface and Linux storage work remain separate possible subsequent
units. ML027's grant is consumed.

## Completed bounded unit: ML028 Debian rc-managed SSH cycle in RAM

The physical run met the selected service criterion. Packaged rc2 and rc6
ran their fixed SSH scripts under Debian PID 1. The stop receipt joined the
startup PID and start ticks to both successful exits, the disappearance of
the old master and pidfile, and a final count of zero matching packaged SSH
processes. The original owner proved normal Download and returned original A.
The ML028 grant is consumed.

## Completed bounded unit: ML029 mainline UFS host study

The FYG8 board overlay and captured FDT agree on six regulator votes.
Mainline's clock names expose an inherited 75–300 MHz range on `ref_clk`;
the study DT restores the shipped zero limits without changing USB's L5
constraints. The normal UFS probe performs reset, link startup and device
initialization before asynchronous SCSI discovery. The next design needs
g0q-specific evidence for the L6/L9 upstream supply, vendor auxiliary votes
and a defined limit on controller/device effects. ML029 used only retained
data and has no physical grant.

## Closed bounded experiment: ML034 USB admission

The approved experiment and original-A healthy closure are complete. The
five-minute witness and exact rejection branch are proved; the selected UFS
link criterion remains `NO_PROOF`. Its known-zero SH1 confirmation is a
software command observation; the historical producing object/order and
electrical state remain unobserved. It cannot replay.

## Completed bounded unit: ML035 ordinary BCM producer correction

Argon and Opus discussion plus full-table H0 execution identified a reachable
duplicate-producer defect: unused display BCM objects can submit zero votes
after normal USB/DDR votes on the same apps voter. The prospective kernel
removes six unused display BCM registrations and their orphan definitions,
preserving all nodes, binding indices, normal BCMs and observer predicates.
The exact reduced DT has no active DISP consumer or normal-to-DISP path.
Host and ARM64 cases reproduce the old failure and qualify the correction;
they do not establish ML034's historical physical cause.

The selected correction and next attended experiment are complete. USB admission
passed on the corrected candidate; the five-minute witness and healthy original-A
return are proved. UFS link completion remains `NO_PROOF` after the stage-two
stop. Its exact HCI/reset/rate/supply rejection is not identified by this run.
No guard was relaxed and no consumed action may replay. Further work starts
with H0 examination of that later boundary; this goal grants no successor
device effect. [H0 evidence and progress](docs/reports/S22PLUS_MAINLINE_ML035_BCM_ALIAS_H0_2026-11-10.md)
· [Exact prospective scope](docs/operations/S22PLUS_MAINLINE_UFS_LINK_BCM_ALIAS_V1.md).

## Completed host-only unit: stage-two diagnostics

The host-only unit adds stage-two diagnostic reporting after ML035.
It preserves the existing guards, short-circuit MMIO reads, five-minute witness
and success-only return conditions. The implementation and validation are
isolated on `codex/s22-stage2-diagnostics-h0`; no successor candidate or live
admission is created. The ARM64 module build, 28 focused tests, 210 comparative
trace cases and retained v1/v2 decoding passed; independent review returned
PASS_GO for this H0 change only. [H0 report](docs/reports/S22PLUS_MAINLINE_STAGE2_DIAGNOSTICS_H0_2026-11-10.md)
records the result and isolated commit scope. Normal-return expansion and capability identity separation
are implemented by the separate H0 unit below, without live adoption.


## Completed host-only unit: candidate reuse and pre-effect return

The H0 work from `codex/s22-mainline-efficiency-h0` was fast-forwarded into
main on 2026-11-10 through `5feed3658a`, including the preceding `30d74d0ac7`
diagnostic commit. It implements report-v4 normal Download after a proved,
settled pre-overlay coverage refusal, and a key-only V2 capability/candidate
split through the existing image/task paths. Existing boot-journal work is
preserved; code integration does not activate the shared policy.
Existing guards, same-boot 300-second witness, deadlines, original-A owner and
no-replay semantics remain mandatory; stage-two failures remain excluded from
the return extension. The UFS result after refusal stays `NO_PROOF`.

Two fresh H0 candidates have actual ARM64 observer/archive/loader/AP artifacts,
loader and exception-level qualification, with unchanged kernel/module and
shared capability inputs. Both passed complete producer reproduction and
fresh qualification with the same independent capability `PASS_GO`. The
102-case focused suite and final 16-case V2 check passed; this bounded H0 unit
is closed. At that H0 completion the shared policy remained `H0_NOT_ADOPTED`,
with no connected read, grant, activation, transfer or physical result.
The subsequent reviewed adoption and first candidate preparation are recorded
in the current-state section above; the H0 evidence itself stays unchanged.
[Implementation and validation](docs/reports/S22PLUS_MAINLINE_EFFICIENCY_H0_2026-11-10.md)


## Milestones toward the final server

1. **Mainline boot and access:** close the RAM-only canary with separate boot,
   USB and recovery claims.
2. **Power and recoverability:** qualify the actual Gunyah/watchdog interface,
   bounded timeout reset and defined failure coverage; conservative thermal
   and frequency control; battery/input-current/charge limits and policy-failure
   behavior. Demonstrate safe idle and sustained combined load. A normal reboot
   does not prove stall recovery, and charge-current control is not an SOC cap
   or battery bypass.
3. **Protected Debian integration:** qualify read-only UFS first, then the
   existing root's current journal and exact package/data state. Permit writes
   only under the selected native_data scope. Require full current-root
   admission before installed execution. NFS root is an optional intermediate
   way to test userspace without local filesystem writes.
4. **Useful persistent runtime:** prove host PID1, one userspace owner,
   authenticated SSH/networking, ordinary package installation/configuration,
   service lifecycle and the selected container workload. Show synchronized
   data/configuration retention across clean reboot in the same integrated
   system. Do not combine unrelated historical runs into a mainline PASS.
5. **Resident recovery and updates:** boot without the development host;
   qualify network reconnection, clean/crash shutdown behavior, startup after
   power loss/low battery, and a rescue route independent of the writable root.
   Version the kernel/DTB/initramfs/modules together and qualify failed-update
   recovery and reboot-loop containment. Preserve exact host recovery artifacts.
6. **Android retirement:** once the new recovery role is demonstrated, perform
   a separately scoped migration to Linux-only operation and any needed storage
   reallocation. Retain required firmware/identity/calibration and usable
   Download recovery. Final normal operation stays in Debian.

Maintain a supported kernel and a reviewable local patch set; a frozen port
release is not a security-maintenance plan. Firmware remaining on FYG8 retains
its own security limitations. Keep important data backed up away from the phone.

## Retained history and continuing boundaries

The previous 798-line goal through ML026 is preserved byte-for-byte in
[the mainline RAM snapshot](docs/archive/roadmaps/GOAL_THROUGH_ML026_MAINLINE_RAM_2026-11-05.md).
It retains the completed ML001–ML026 research/diagnostic history, exact report
links, proof limits and the earlier vendor-route snapshots. Archival changes
neither retained evidence nor current authority. Historical next-step text is
superseded by the current selected bounded unit; consumed grants remain consumed.

This product change does not relax partition/evidence boundaries, activate a
mainline lane, grant unattended operation or authorize Android deletion now.
Each future effect still needs the applicable exact target, current health,
artifact/source, scope and recovery binding. Required operational policy
changes are separately reviewed rather than inferred from this goal.
Uncertain writes, transfers and controls never replay. Preserve private raw
evidence and distinguish functionality, filesystem consistency, recovery and
terminal health in every result.
