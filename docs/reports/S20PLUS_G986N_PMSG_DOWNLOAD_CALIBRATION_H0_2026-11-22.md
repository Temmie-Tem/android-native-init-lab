# S20+ PMSG retention calibration through physical Download

Target `SM-G986N / y2q / y2qksx / G986NKSS8IYC2`. Status **H0 qualified,
connected preparation held**.

## Question and control

The closed stage run recovered healthy original Magisk Android. Its
same-boot pstore command returned successfully and found neither fixed
record. This left generation, preservation, and publication of the
candidate marker unresolved. The active metadata-only D0 now confirms
ramoops, the mounted pstore filesystem and the PMSG node on the rooted
resident device. Its fixed old PMSG and console record paths are
`unavailable`, and the 2,097,136-byte `/proc/last_kmsg` file was
metadata-checked without a body read. D0 receipt SHA-256 is
`393ff08fc06a2e16a2040bbdaf804254768c0c8194d2d9195ca1eaa0f3553af1`.
[Prior stage result](S20PLUS_G986N_UNILOADER_STAGE_H0_2026-11-22.md#attended-stage-result)

The proposed control starts on the proved resident boot. Before approval
it would pin the exact current boot and test a zero-byte open of the PMSG
character write path. After approval it sends a single fresh 144-byte
marker through the verified character descriptor and checks the exact
write receipt. The stock PMSG API routes accepted writes to the same
ramoops PMSG zone used by the stage candidate. The receipt proves API
acceptance and does not directly measure the contents immediately before
the physical transition.

Only accepted bytes arm the physical handoff. The operator returns the
bound confirmation, waits for the durable Download intent and uses the
same physical button route and USB port. The owner observes the exact
endpoint and uses the previously proved caged Odin transport for one
resident Magisk `boot.img.lz4` AP. After that it pins the first
changed boot ID observed on the exact target before Android completes,
joins full Magisk health to it and scans the fixed pstore PMSG record once.
Raw record bytes stay on the device. Recovery or collection cuts retain
the original intents, and an unobserved arrival gap bars a retention
claim. [Proposed target scope](../operations/targets/S20PLUS_G986N_TARGET_CONTRACT.md#s20-pmsg-physical-download-retention-calibration-f1)

An exact returned match establishes that a stock-kernel-produced PMSG
marker survived this physical Download, AP transfer and Android return
combination. It cannot retrospectively establish that UniLoader had
written its marker. An accepted write followed by an empty or unavailable
record rules out failure to dispatch the control marker. It leaves live
ring overwrite, physical reset, Download, original AP return and Android
record publication as possible loss points.

## S22+ precedents

- **Mainline ML005** had no qualified USB/PID1 observation, yet the returned
  original Android `/proc/last_kmsg` contained five `post-fdt` and five
  `post-paging` records following physical Download and original-A. They
  establish arrival at those recording points. The S20+ experiment applies
  the same independent returned-boot evidence and health bracket to PMSG.
  [ML005 outcome](S22PLUS_MAINLINE_ML005_RUN_2026-10-30.md)
- **Native P424** obtained exact current kernel ring readback before recovery
  and one authenticated PRE match afterward. The POST write was never
  reached. This is the precedent for recording producer acceptance before
  the handoff and treating partial or absent records as distinct outcomes.
  S20+ PMSG uses API acceptance in place of current kernel-ring readback.
  [P424 outcome](S22PLUS_NATIVE_LOG_CALIBRATION_P424_RUN_2026-10-13.md)
- **UniLoader LOGM on November 22** verified write readback and a matching
  `last_kmsg` record while candidate Android was running. That record
  supplies candidate-boot visibility evidence for its logger. ML005
  supplies the physical-return retention precedent. The S20+ images use
  ramoops PMSG for their loader-stage comparison, with Samsung sec_log
  as a separate channel. The S20+ `last_kmsg` D0 definition is dormant
  and supplies no matching-content acquisition for this run.
  [LOGM outcome](S22PLUS_UNILOADER_LOGM_RUN_2026-11-22.md)

## Qualification and authority

Host validation rederived the previous exact physical Download and
resident Magisk AP proof, audited the AP and checked the process cage.
The stock IYC2 mksh and Toybox fixtures covered the complete PMSG probe,
write and reader scripts. They reject wrong boot and failed producers,
including a failed writer sink and a reader that produces matching
bytes before failing. The connected zero-byte character probe remains
part of future preparation. The fixture runs prove shell behavior and
record interpretation. Physical persistence is outside H0.
[Dormant calibration owner](../../workspace/public/src/scripts/revalidation/s20plus_g986n_pmsg_download_calibration_f1.py)

The focused aggregate passed 48 tests, including eight calibration cases.
Independent review returned `PASS_GO` for dormant H0 and held live
activation. The reproduced host closure SHA-256 is
`38c1bc837f1a01a7d82cf697446e5fd4593e9ea5db86ee1904958be2ea0a87ef`.

The pinned common PMSG delegation admits one ordinary reboot and its
exact marker write and comparison. Its clause excludes Download, AP
transfer and physical return. This proposed one-original-AP calibration
also differs from ordinary candidate-plus-rollback F1. An explicit
common delegation for this exact attended composition is therefore
required. The proposed scope is one fixed character marker, one physical
entry, one exact original Magisk AP and one bounded first-return read,
all under a returned finite approval, unchanged partition limits and
no replay. An amendment must account for existing reviewed owners that
bind the common document bytes. Both S20+ UniLoader F1
activations still validate with the existing common bytes.
[Common contract](../operations/DEVICE_ACTION_CONTRACT_DETAILS.md)
[S22+ source binding](../../workspace/public/src/scripts/revalidation/s22plus_native_research_scope_v1.py)

No calibration activation, trial or approval token exists. The connected
entrypoint is closed before USB exposure. The only connected work was the
fixed S20+ metadata D0. New marker writes, mode transitions, transfers,
and S22+/A90 commands were zero.
