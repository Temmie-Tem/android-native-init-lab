# S22+ FYG8 P3.26 bidirectional USB and BusyBox F1 pass

Date: 2026-09-02 KST

Target: `SM-S906N` / `g0q` / `S906NKSS7FYG8`

Status: `PASS_F1_V2_P326_NATIVE_PID1_BIDIRECTIONAL_USB_BUSYBOX_SHELL_AND_ROLLED_BACK`

## Result

P3.26 is the first S22+ run to prove the declared bidirectional native-PID1
USB exchange and execution of static BusyBox `ash`. The candidate observer
sent exactly 77 bytes in two fixed writes, received exactly 145 bytes with
SHA-256
`8e5136ac8d61b322595d2795ab946022ba2818f0100214a1e47358b88f3c6279`,
and retained zero trailing bytes. It accepted the run-bound PID1 `PONG` and
BusyBox `SHELL-OK` replies with `pid1_bidirectional_proof=true` and
`busybox_shell_roundtrip_proof=true`.

This proves host-to-device and device-to-host traffic through the fixed ACM
channel, a PID1 response, and the fixed BusyBox `ash -c` child execution. The
child exits after its fixed reply. P3.26 therefore does not prove a general
interactive shell, arbitrary command execution, or a persistent management
service.

The separately retained supplemental Carrier remains
`NO_PROOF_OBSERVER`. No Max77705 scientific or causal claim is promoted from
this result.

## Execution and recovery

Candidate AP 28,631,081 bytes/SHA-256
`954b560309e5c7a1f99484dbe00efc08743cc97bc228bad5c7f8924e8c7c2712`
transferred exactly once. The candidate observation closed successfully in
22.51 seconds. A subsequent measured rollback-endpoint inventory stopped the
first process after that durable observation; recovery resumed only the
journal and never resent the candidate.

Exact Magisk rollback AP 23,367,721 bytes/SHA-256
`d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`
then transferred exactly once. Final rooted FYG8 health passed, the Download
endpoint was absent, and the supporting partition identities matched. The
journal is `CLOSED` with 19 records, candidate/rollback attempts are 1/1, no
attempt 2 exists, and `recovery_required=false`.

## Host result publication

The already-valid live state is 30,189 bytes/SHA-256
`565e16113ab58d7d2859bd9af01ac83397f2675a3390f7d3314b8b1e0679e028`.
The ordinary publisher then stopped after device closure because the complete
canonical result is 33,879 bytes, 1,111 bytes above the shared 32 KiB record
bound. This was a host reporting failure, not an experiment or rollback
failure.

Exact-run finalizer commit `3675699a1b` accepts only the frozen P3.26 sources,
prepared binding, 19-record CLOSED journal, one candidate result, one rollback
result, retained observation, and final health. It has no device backend and
uses a local 64 KiB bound solely for atomic no-clobber publication. Its six
focused tests and noncreating audit passed, and independent read-only review
returned `PASS_GO_P326_CLOSED_FINALIZER`.

The published mode-`0400`, single-link `live-result.json` is 33,879 bytes with
SHA-256
`a78a9c50c8242506e6f531cc3d48f5fcadbe19410b1da8a7fc5215847aef91b5`.
Post-publication audit rederived the same bytes and formal outcome
`p326_native_pid1_bidirectional_usb_busybox_shell_rollback_verified` with zero
device, ADB, USB, Odin, candidate, or rollback actions.

P3.26 is closed, consumed, and never replayable. A broader interactive control
channel must be a fresh successor with a new run identity and artifact; it may
reuse this proved fixed transport result as evidence, never this candidate or
approval.
