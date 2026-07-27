# S22+ FYG8 P2.80 candidate closure and live-ready H0

Date: 2026-07-28 KST

Scope: H0 host-only. No connected D0, approval, transaction, Download request,
Odin session, transfer, reboot, device contact, or device write occurred.

## Verdict

`READY_HOST_VALIDATED; CONNECTED_D0_NOT_YET_RUN`

The exact P2.80 v5 candidate is deterministically packaged, independently
closed, promoted into Process v2 evidence, and bound by one immutable ready
manifest:

`workspace/public/src/device-action/manifests/s22plus_fyg8_p280_process_v2_ready_1.json`

F1 is not authorized. The next bounded action is connected read-only D0.

## Exact candidate

- source contract:
  `s22plus-fyg8-p280-parent-pullup-discriminator-v1`
- candidate run ID: `568abdddae4a0320e14c95aad8bf1e9c`
- kernel Image SHA256:
  `36054cdf754b52a3c158f57969fbf2c6742b58188628e42aa738272c45a237b5`
- boot image SHA256:
  `9867c5fcd17ea4111911f64d410dc623808689da1834fd0c550710c41e92a3a5`
- `boot.img.lz4` SHA256:
  `4ba43000b05d0f32c961da0d7168f0fcf7e1191f871ef38b0b90b895a8ab370a`
- boot-only AP SHA256:
  `6713cfef1ad2abe5d2b144f695c1e0cbc71ea0dbf6c78212565b19cb8beb3486`
- exact rollback AP SHA256:
  `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`

Candidate A and B match for `artifact-result.json`, `boot.img`,
`boot.img.lz4`, and `odin4/AP.tar.md5`. Each AP contains exactly one regular
member named `boot.img.lz4`; no manifest or device authority is embedded in
the package result.

## Static and promotion closure

The independent static checker returned:

`PASS_P234_INDEPENDENT_ARTIFACT_CLOSURE_HOST_ONLY`

Its result is 46,881 bytes with SHA256:

`0debfbddc7378b4ddb8b460264bda8f08e8217644358c1a5e75f889869f66f61`

It freshly reopens the exact intent and patch, reruns the P2.80 linked adapter,
checks the two Full-LTO bundles and package pair, reconstructs the candidate,
extracts the exact init and child, and validates the 60-module effective
stock-rootfs composition.

Offline promotion returned:

`PASS_P234_PROCESS_V2_OFFLINE_EVIDENCE_PROMOTION`

The promoted artifacts are:

| Artifact | Size | SHA256 |
|---|---:|---|
| `candidate-static.json` | 46,881 | `0debfbddc7378b4ddb8b460264bda8f08e8217644358c1a5e75f889869f66f61` |
| `run-manifest.json` | 782 | `fd967f0c0d01f60fa4c65782437f15ebccbd2065614b2e6831a8882de257fcbe` |
| `static-check-result.json` | 1,692 | `81f8d75d27d2e241d17de6e5f61d55c656c701ff9da7c575a5d30de8966a2e54` |

Promotion independently decodes the AP member and replays the exact generic
rootfs semantics before emitting these files.

## Fail-closed verifier findings

Three downstream verifier defects were found after the immutable package pair
already existed. None changed the kernel, userspace, initramfs, boot image, AP,
intent, patch, qualification, or candidate run ID.

### Linked adapter dispatch

The candidate checker called the common repro checker directly. That path knew
the adapter name but did not execute the P2.80 wrapper that accounts for the
six-byte target ABI storage. The checker now selects `check()` through the
source-contract adapter registry, verifies the adapter contract ID, and still
requires the fresh result to equal the frozen result exactly.

### Entrypoint context lifetime

The versioned P2.80 closure derived the exact current init entrypoint
`0x403b20`, but restored that context before a nested validator compared it
with the inherited `0x401a9c` value. The final static checker keeps the
exact-userspace entrypoint context over the complete nested audit and restores
all historical state afterward. The qualification-bound closure file remains
unchanged.

### Generic module view

Process v2 promotion validated the full 60-module closure, then passed that
full shape to an isolated P2.42 generic-rootfs audit. The established effective
rootfs path instead performs:

`P2.57 full 60 -> P2.53 legacy 59 -> P2.42 legacy 59`

The typed evidence verifier now uses that exact two-step view only for generic
rootfs replay. The original 60-module closure remains separately validated and
unchanged.

These are verifier call-boundary defects, not candidate defects. Rebuilding
would have reproduced the same failures and was therefore rejected.

## Ready manifest

The ready manifest is 2,648 bytes with SHA256:

`0db87652a9e9eef6452193c9f81d8cbf0d3ab67a5a26051f994b0a73fad0a449`

It binds:

- exact candidate and rollback AP identities;
- terminal stage `0x90`;
- P2.80 decoder and policy IDs;
- exact 49-byte synthetic run-bound ACM banner;
- a 240-second observation window;
- the three promoted evidence files; and
- Process v2 runner version `device-action-f1-v2-host-core-3`.

Offline live validation returned:

`PASS_DEVICE_ACTION_F1_LIVE_V2_HOST_READY`

The validated bundle SHA256 is
`8f81f6a75b43e643b66408ca4ab4e4a79a97742f1b3c38884f61437d59e4e37b`.
The execution-closure SHA256 is
`4a56e84d699fbb1f880748dbc50a2eaaac289bd3cd287a2857fa814b763a2bc2`.
It explicitly reports `prepare_is_d0_only=true`,
`execute_requires_fresh_exact_approval=true`, and `f1_authorized=false`.

## Validation

- execution-critical and historical regression tests: 202 passed;
- exact ready-manifest bundle test: 1 passed separately;
- Python compilation: passed;
- Ruff `0.6.9` fatal-error set `E9,F63,F7,F82`: passed;
- full Ruff additionally reports one unchanged pre-existing `F841` from
  2026-07-23 outside this diff;
- whitespace validation: passed;
- exact package A/B equality: passed;
- independent static closure: passed;
- offline Process v2 promotion: passed; and
- offline live manifest validation: passed.

One independent read-only adversarial review found no acceptance weakening,
candidate/rollback identity confusion, historical-contract regression, context
leak, or D0 authority violation and returned `GO`.

## Next

Run connected D0 with the exact ready1 manifest. If D0 passes, stop at the
fresh approval token. Do not invoke F1 `--execute` without the operator's new
exact approval.
