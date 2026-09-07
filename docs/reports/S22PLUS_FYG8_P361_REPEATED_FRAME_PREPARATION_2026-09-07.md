# P361: ten swaps of a retained frame pair

The operator authorized this successor preparation and D0/D1 in the foreground
task. P360 is consumed and closed healthy, with both clean frames and one
transition reported by the operator. No prior candidate or observation is
replayed. P361 F1 requires separately returned fresh prepared approval.

## Capability

P361 retains the exact P360 two prepainted CACHED ABGR8888 buffers, first blocking
ALLOW_MODESET request, 1080x2340 geometry, pitch4352, 30HS mode, modules,
noise/fill zero, privilege drop, one-way dispatch and 60-second parent bound.
After first submission succeeds, ten iterations each require a successful
one-second nanosleep and one flags-zero blocking atomic changing only the
selected primary FB_ID. The selected frames alternate second/first, ending on
the first. This is eleven total atomic requests on the successful path.
Buffers, FB IDs and mode blob remain held; pixels are never changed or reused
for new content. Any sleep or commit failure ends the child without further
requests, fallback or retry. Physical Download and exact rollback remain the
mandatory return path. Ten one-second waits do not guarantee an exact 1Hz rate
or ten-second completion because blocking commit durations are additional.

Independent source review supports retained-FB reselection: the vendor normal
cleanup calls msm_gem_put_iova, which is a no-op in this tree, and existing VMA
lookup can reuse the IOVA. This does not guarantee mapping survival across
unrelated domain teardown. Existing vendor mapping/error limitations remain;
no recovery rule, selector or permanent boundary is changed.

Success requires operator-observed repeated alternation without corruption,
freeze or unexpected order, then final first-frame hold. Host dispatch remains
separate from visual evidence. The pattern is not PID1 health or a heartbeat.
A PID1 state/heartbeat HUD is a subsequent bounded step, after this display path.

## H0 preparation

Nine fresh namespace/renderer scripts reuse sealed P353 machinery and sealed
P360 renderer bytes. All 79 construction sources were listed and frozen before
build. The identity-only Image is
`41490944B/fd7c92f95ba00650378721df651d1dea7e289a9c3a46748c6704d97f8d5d6881`.
The new run ID is `c361f1e0a90b5e6d7c8a9b0c1d2e3f0b`.

The generated fake-DRM fixture exercises exactly eleven commits, alternating FBs,
one-second waits and final first FB. Both complete paints are checked before
first commit, and immutable contents are checked at every subsequent commit and
final hold. Second allocation/GEM/mmap/FB failures cause zero commits. First,
second, middle and last commit failures, and initial/middle sleep failures,
stop without later requests or cleanup. The host fixture is bounded by
64MiB address space and 15 CPU seconds; this is not a vendor memory/timing proof.

A/B userspace, renderer, boot and AP agree. Candidate AP:
`30965801B/c9a53a82af2336b2035e7fd5e13d38514b834df1eb989b1ac5ca8049e5a656ef`.
The static AArch64 executable was inspected with file. Its QEMU paint output
matches the P360 frame pair already verified against an independent complete
pixel oracle: 20,367,360 bytes, SHA-256
`825efa32402df0307d922e4423a8ba2a9fff5c12154d3828685467145b055f28`.
The paint-only mode reuses one buffer and does not prove live two-buffer use.
Actual static qualification passed, along with all 24 P361 tests, 23 P360
regression tests, Python compilation of 14 files and the repository boundary
check. Offline promotion passed with common_offline_verified=true. Final independent
review passed PASS_GO with no findings, receipt SHA-256
`3db3ad458fae94c884612d50bed66eb424ddd56a7ac03a1a026b5f12ff56c2d3`.
Reviewed execution-critical and artifact identities reverify. No P361 connected preparation or F1 effect has occurred.
Private evidence: `workspace/private/outputs/s22plus_fyg8_p361/`.
Unrelated S20+ edits and the pre-existing P345 manifest remain outside this work.
