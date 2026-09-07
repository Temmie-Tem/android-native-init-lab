# P360: one cached two-frame transition

The operator authorized H0 preparation and D0/D1 in the current foreground task.
P359 is consumed and closed healthy; no prior candidate or observation is
replayed. At preparation completion P360 F1 required a separately returned fresh prepared
approval. That approval was subsequently returned; the consumed result is below.

## Capability and evidence limits

Two distinct CACHED ABGR8888 buffers retain 1080x2340 geometry, pitch4352 and
30HS timing. Both are allocated and painted before the unchanged first blocking
ALLOW_MODESET request. First pixels match P359 RGB/grid/white border. Five seconds
after that request succeeds, a blocking atomic with flags zero changes only the
selected primary FB_ID. The second frame has green/red/blue regions and a large
white 2 with black backing. No repaint, reuse, cleanup, fallback or retry occurs.
First allocation/commit or sleep failure prevents the second request; second
request failure terminates without retry. Both buffers and mode blob remain
retained until the existing parent deadline or physical Download.

Vendor source review supports the FB-only source-address update path. The
second DMA mapping may occur during second commit. Existing mapping-failure
limitations remain. Host dispatch and ioctl return cannot prove visible output.
Success requires operator-observed first-to-second transition with intact
regions, numeral, grid and border. Every outcome requires attended physical
Download, exact Magisk rollback and final rooted FYG8 health. No standing runtime,
automatic recovery, session-stop exception or permanent boundary is added.

## H0 validation

Nine fresh namespace/renderer scripts reuse sealed P353 machinery and the sealed
P359 renderer. All 78 construction sources were listed and frozen before build.
The new identity-only Image is
`41490944B/466408ac7ac0615203160e3606fad56be9570f3a67b27aedbff92061ec260f2b`.
A/B userspace, renderer, boot and AP agree. Candidate AP:
`30965801B/466a631d23ff23aef8a130971b3b8ef22f2190742d49e75a19456c06484399f7`.
Actual static qualification passed. Kernel/module executable code is unchanged.

The actual static AArch64 renderer was inspected with file. A byte-identical
executable under QEMU emitted two complete frames; all 20,367,360 bytes match an
independent oracle, SHA-256
`825efa32402df0307d922e4423a8ba2a9fff5c12154d3828685467145b055f28`.
This mode reuses one buffer and does not qualify live two-buffer resource use.
Generated fake-DRM tests exercise both allocations and complete paints before
first commit, exact first and second requests, retained lifetime, inherited
plane replacement, interrupted delay and failures on second GEM creation,
mapping or framebuffer registration. All such allocation failures cause zero
atomic calls; first/second commit errors do not retry. The host live-path fixture
runs under 64MiB address-space and 15 CPU-second limits. This is host behavioral
qualification, not a guarantee of vendor memory use or device timing.
All 23 focused tests, 21 P359 regression tests and compilation of 14 Python
files passed; boundary check is clean.
Private evidence is under `workspace/private/outputs/s22plus_fyg8_p360/`.

## Status at preparation completion

Offline promotion passed with common_offline_verified=true. Independent final
review passed PASS_GO with no findings; receipt SHA-256
`5a33e2d2815b7b0ddc9d36b8c5f38b469c63c6e9c82974f3755bad998cc76cee`.
All 108 reviewed execution-critical inputs and six artifact identities reverify.
No P360 candidate transfer or F1 effect has occurred. Unrelated S20+ changes
and the pre-existing P345 manifest remain outside this work.


## Connected baseline preparation

First D0 verified exact initial health and preserved the expected baseline
rejection in `p360-ready1-prepared-20260907-1`. The actual bundle and strict
stop validator passed; result
`3252B/00ae8a834310a6a93a6df5678a5ce8df9e64ea42aa1d00381d54c9bd88132d80`.
This non-reusable result grants no transfer or control action.

Current D0/D1 preapproval was bound through fresh private metadata to the
unchanged reviewed P341/P320/P296 one-normal-reboot primitive, the closed P359
result and exact stop receipt. Self-test passed before the sole execution.
The D1 result is `PASS_P360_D1_EXACT_NORMAL_REBOOT_RETURN_HEALTH`,
`2963B/77652cd7fcb48f35f6a0202c1bc4523ae5868b71b6ced3f9d16c81331b9786e1`.
Changed boot ID, exact rooted FYG8, original boot/supporting hashes and Android
health passed. Linked invocation/primitive receipts reverify. No retry or manual
recovery occurred; A90/S20+ received no command from this task.
Fresh D0 preparation in `p360-ready1-prepared-20260907-2` passed
`PASS_DEVICE_ACTION_D0_V2_CONNECTED_READ_ONLY`, result
`3261B/ebe327c2143ead9cd3bfb84435c300b3d9b25917e10ee68fa07daed236ada407`.
Prepared record:
`30321B/7a1b469af9f87ca6d7bdabb6e30ace81b8ae8337d94cfef5ca81edd4d75d0dca`.
The fresh token is supplied directly to the operator and excluded from tracked
documents. Candidate transfer, Download transition and F1 authorization remain
absent. Actual load_prepared reopening passed and all reviewed identities remained
unchanged. H0 was committed as `6d5a1b76e6`. At preparation completion the remaining attended F1 required
the fresh token returned separately and physical Download availability under
the P360 target clause.


## Consumed F1: two clean frames and one observed transition

The operator returned the exact prepared approval. One candidate and one exact
Magisk rollback transferred; the original execute completed without a recover
invocation. The operator reported: both frames normal and transition to numeral
2 observed. The original statement is retained privately in a separate immutable
operator-visual-witness.json. This qualifies the bounded operator-observed
first-to-second transition without reported corruption. It does not prove
pixel-exact readback, exact five-second panel timing, repeated flips or a general
display runtime, and does not isolate cache coherency from mmap/DMA-map timing.

Machine verdict is
`PASS_F1_V2_P360_STATIC_DISPLAY_DISPATCH_AND_ROLLED_BACK`; it remains dispatch
and rollback evidence, separate from the visual witness. Live result:
`22805B/7bd7c40c3009bdbbede2c517a15e2aaecfe549b17374744c5b125615f99f371b`.
Final rooted FYG8, original boot/supporting hashes, Android health and absent
Download passed. Journal CLOSED/19, recovery_required=false, no active lease.
Candidate and observation are consumed and never replayable. A90/S20+ received
no command from this task. No successor F1 or standing native runtime is granted.

Canonical timeline, UTC:

| Event | Timestamp |
| --- | --- |
| live_session_start | 2026-09-07T12:40:21.548915Z |
| candidate_flash_start | 2026-09-07T12:40:38.979909Z |
| candidate_flash_done | 2026-09-07T12:40:40.670450Z |
| candidate_boot_ready | 2026-09-07T12:41:05.125856Z |
| rollback_flash_start | 2026-09-07T12:42:43.545775Z |
| rollback_flash_done | 2026-09-07T12:42:45.070193Z |
| rollback_boot_ready | 2026-09-07T12:43:30.882205Z |
| live_session_end | 2026-09-07T12:43:30.903085Z |
