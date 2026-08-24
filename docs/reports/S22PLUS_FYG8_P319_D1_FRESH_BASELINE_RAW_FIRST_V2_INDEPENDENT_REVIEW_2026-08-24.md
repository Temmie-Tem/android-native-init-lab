# S22+ FYG8 P3.19 D1 fresh-baseline raw-first V2 independent review

Date: 2026-08-24 KST

Verdict: `PASS_GO_P319_D1_FRESH_BASELINE_RAW_FIRST_V2_H0_CAPABILITY_V1`

## Reviewed closure

Independent Luna review covered implementation commit `694ad3ad53` and the
exact 66,357-byte V2 source at SHA-256
`9443c81cd51e23a24f48a0f43573e1449cfa188b3cd1c69e6f6f11644d15d478`.
The review included its fixed ordinal and namespace, exact target and source
bindings, inherited P2.96/P3.18 one-reboot state machine, immutable raw-handle
inventory, typed stop receipts, consumed V1 evidence and hostile tests.

Two main-review blockers were closed before that commit. First, a pre-existing
or concurrently won arm is not owned by the new invocation and cannot append a
stop or change an already consumed/successful namespace; only a partial arm
created by the current invocation may publish the consumed typed stop. Second,
an early post-reboot properties `D0Error` or `OSError` retains its immutable raw
handle and remains connected-but-not-ready inside the bounded P2.96 return
poll; persistent failure terminates once as `RETURN_HEALTH` without replaying
the reboot. The bounded CLI host-input exception path also returns fail-closed
without a traceback or private path.

The review-pending canonical binding committed with the implementation is
preserved as the 5,300-byte SHA-256
`917daa0257fda4b6bd784bf303ef9226b744ba0ce458e1bbfc4b7a48721cef8f`
predecessor. Mechanical promotion changes only its `independent_review` tuple.
The final canonical binding is 5,351 bytes at SHA-256
`65e2953ecdcb55a0b5b21614e181c7ed8fe4daafaadda5e7319ae142ad9fbae9`
and records the exact verdict above.

The corresponding authority *format* is
`DEVICE-ACTION-D1-P319-FRESH-BASELINE-V2-APPROVE:` followed by that complete
binding digest. It is capability data only: no current operator approval has
been supplied and no arm, run, raw namespace or ADB snapshot exists.

## Unchanged evidence

The V2 source did not change during promotion. Therefore the permanent
raw-first auditor and prerequisite evidence remain byte-identical:

- raw auditor: 66,941 bytes, SHA-256 `86a0fc328538c5a39470dca2272957a4ac7453a48a7f629feebfb7edbddfd3d2`,
  normalized self-hash `139838505b937c8634c21db652d1d50adaf45bfaf65d2b8359743f2aaedcbe28`;
- raw receipt `raw-first-observer-audit-20260824-05-p319-d1-v2-no-replay.json`:
  12,394 bytes, SHA-256 `2d5fc0428f6683ce9a7ac056c6da6b92c4decad45b7fd7430febf2edbd1325e9`,
  mode `0400`, link count one;
- prerequisite auditor: 45,262 bytes, SHA-256
  `08654b354da110c21fb0ec4e672505e3f57db253b74c0e9da4535d9109633481`;
- prerequisite receipt `process-v2-prerequisite-audit-20260824-05.json`:
  12,532 bytes, SHA-256 `5ea7fd30aabc99041ce64e1b1e9c50f6cea181dc7f73d251d5cbdc396624fb4a`,
  mode `0400`, link count one.

The reviewed validation record is V2 hostile tests `28/28`, combined
V1/V2/reducer/integration `81/81`, permanent raw-first `24/24`, raw docs
`19/19`, prerequisite `9/9`, integration docs `8/8`, taxonomy `39/39`,
consumed-stop evidence `4/4`, and common Process-v2 `142/142`. The broad P3.19
record remains 688 total: 687 passed, zero failed, and one known unavailable
`/mnt/android-lab-logical/vendor_dlkm/lib/modules/spu_verify.ko` input error.

## Boundary

This `PASS_GO` qualifies only the exact H0 capability. The D0 consumer remains
pinned to V1, the consumed V1 action remains non-replayable, and machine
integration remains blocked on `FRESH_BASELINE_MISSING`. No approval, arm,
run, D1 result, D0 baseline, ready/run/public candidate manifest, D0, D1, F1,
recovery, replay, causal-result, candidate-success, device, ADB, USB, Odin or
live authority is created.
