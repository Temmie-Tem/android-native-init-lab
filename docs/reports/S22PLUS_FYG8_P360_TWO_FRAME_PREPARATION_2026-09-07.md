# P360: one cached two-frame transition

The operator authorized H0 preparation and D0/D1 in the current foreground task.
P359 is consumed and closed healthy; no prior candidate or observation is
replayed. P360 F1 requires a separately returned fresh prepared approval.

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

## Preparation status

Offline promotion passed with common_offline_verified=true. Independent final
review passed PASS_GO with no findings; receipt SHA-256
`5a33e2d2815b7b0ddc9d36b8c5f38b469c63c6e9c82974f3755bad998cc76cee`.
All reviewed execution-critical and artifact identities reverify. No P360 connected
preparation, candidate transfer or F1 effect has occurred. Unrelated S20+ changes
and the pre-existing P345 manifest remain outside this work.
