# A90 retained-work cleanup cmdv1x frame incident

Date: 2026-08-04 KST
Target: Samsung Galaxy A90 5G only
Classification: `HOST_OBSERVER_FAILURE`, device remained `BASELINE_HEALTHY`

## Outcome

The attended retained-work cleanup transaction
`a90-v3406-work-cleanup-20260804-02` consumed one approval and recorded one
dispatch. The effect command did not reach `/bin/busybox run`: native-init
decoded only one truncated `cmdv1x` argument and returned `rc=-22` before the
requested `run` command existed. Read-only reconciliation then proved the work
copy still present, the distinct protected source exact, the run stage absent,
and exact V2321 health. The unlink was not retransmitted and will never be
replayed from this journal.

The private durable evidence is bound by these SHA256 values:

- manifest: `d0715a296154f9e8f34cbb929468dd8d8530b788704889b4239cd2ec5734ef0e`
- intent: `e42ea5623530561560d946740341f16c5ea56f7b8bf2c98c7577ff56d3d45bfd`
- dispatch: `8587e1da46900246a257f6d113b0b8a443f61976a9e09512c7de55ba9b4de7b3`
- dispatch error: `b81839aad6f4bbeb145acb549f115cf04cc1eaa922b28a5c158949729cf1a10f`
- result: `ea1d69a899d7c9c0c62c31a66dc17198c71b889968bb6f4d036fc6fd93563ca8`

No partition payload, reboot, rootfs transfer, or command to S22+ occurred.

## Cause

The cleanup shell was 1,663 bytes. After `cmdv1x` length-prefix and hexadecimal
encoding, the complete control line was 4,128 bytes, exceeding the resident
console's 4,096-byte line/decode envelope. The raw private bridge capture shows
the resulting decoder-only terminal (`cmd=cmdv1x argc=1`, `rc=-22`) and no
`cmd=run` begin record for the cleanup effect.

The cleanup capability had exact one-shot and no-retransmit semantics, but it
did not statically bound its encoded control frame even though the repository's
newer SD GC capability already used a 3,800-byte bound. This was an execution
machinery defect, not a target-health failure and not authority for a retry.

## Corrective action and retirement evidence

The cleanup effect script was compacted without widening its path or operation
allowlist. The encoded worst-case frame is now 3,083 bytes and every cleanup
control command is rejected host-side above 3,800 bytes before durable intent
or dispatch. Focused cleanup tests cover the encoded bound and pre-dispatch
oversize rejection.

The old cleanup transaction remains terminal. The frame defect is retired for
future campaigns only after a fresh independent capability review binds the
changed cleanup helper and target contract. The current resident-install
campaign instead uses a separate reviewed no-stage lane that preserves both
exact files and marks the resulting resident `handoff_eligible=false`.
