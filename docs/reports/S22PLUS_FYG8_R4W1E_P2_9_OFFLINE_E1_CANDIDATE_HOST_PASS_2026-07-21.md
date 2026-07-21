# S22+ FYG8 R4W1-E P2.9 offline E1 candidate host pass

Date: 2026-07-21 KST
Target: `SM-S906N/g0q/S906NKSS7FYG8`
Tier: H0 only

## Verdict

`PASS_R4W1E_E1_OFFLINE_CANDIDATE_STATIC_CONTRACT`

P2.9 produced one clean Full-LTO R4W1-E kernel build and one independently
checked offline E1 boot-only candidate. No device was contacted, Odin was not
invoked, no partition was written, and this result grants no D0, D1, F1, or
live authority.

## Kernel build

The source-matched FYG8 tree was built remotely with the reviewed R4W1-E
adapter. The successful build took 36 minutes 9.82 seconds and reached
24,243,668 KiB maximum resident memory without swap activity. Source patching,
the six controlled source links, the pinned clang runtime override, build-time
link mutation, and source restoration all passed their post-build checks.

- build schema: `s22plus_fyg8_r4w1e_build_v1`
- result: `rc=0`, `r4w1e_build_pass=true`, Full LTO
- `Image` size: `41490944`
- `Image` SHA256:
  `b45b87beab49b65a8212468178ff440004a20e76ff2e5564a271f47ff6dd80c8`
- build-result size: `703813`
- build-result SHA256:
  `0ac93b9adb9e7b02c04f5f7c2109bcfb8b7088b7ed6b98baf81e8e5fd2f4eee3`

These two identities are pinned by
`s22plus_fyg8_r4w1e_build_artifact_contract_v1`. Candidate construction and
checking reject structurally valid but differently identified build outputs.

## Offline candidate

The builder generated one fresh manifest-bound run ID and replaced only the
kernel interval in the independently reconstructed carrier. The ramdisk and
boot header were preserved, LZ4 round-trip verification passed, and the AP has
exactly one regular member named `boot.img.lz4`.

- run ID: `395f27c3ac34ebe61395d7efd5a058e8`
- carrier boot SHA256:
  `665f7513075b2e7a07af3230898da37b72bfe9b85074cc25d6a59b19aeaf30e0`
- candidate boot SHA256:
  `6f6ae486950226f5bdc297c65c5e48fd11e3ea95bac8bfe6990495799334995c`
- `boot.img.lz4` SHA256:
  `ba95458f834bb589382f386351d96b212cd62cbe4ed8bb20e3b547806e3ccfbb`
- boot-only AP SHA256:
  `ff4e1766b82306005bfa3cbb6280347ad6133bb60801c9d6236d7eaf044bd421`
- E1 `/init` SHA256:
  `105062e2de8f6ef1b3fd705238743691dd1993c6bb78e452c35da0fc7e3101d1`
- E1 child SHA256:
  `9a57b30aa3fb08ee0aab4d045d2805dd36875bb80bcba7b0b6606f619df71639`

The independent static checker verified the fixed kernel interval, carrier
reconstruction, preserved ramdisk, 474-entry rootfs, five-module closure,
runtime contract, run binding, and boot-only AP contract with zero blockers.

## Fail-closed repair

The first real independent check rejected the AP because the checker compared
the parsed member metadata object directly with the member-name string. The
candidate itself was not regenerated. The checker was repaired to validate the
metadata type, exact member name, and exact parsed frame bytes. A focused real
AP test now accepts the exact member and rejects a frame mutation.

Independent review returned `BUILD-GO` for the build adapter and
`FINAL-CANDIDATE-GO` after the checker repair. The final integrated relevant
suite passes 143 tests.

After the build, one machine-specific recorded clang-link prefix was removed
from tracked source. The guard still requires an absolute path with the exact
toolchain suffix, uses the runtime-observed original target for exact
restoration, and overrides it with the separately pinned build toolchain. The
fixed Image, build-result, and candidate bytes were not regenerated. The
changed closure passed its override-to-restore test and an additional
independent `FINAL-CANDIDATE-GO` review.

## Limits

- One clean Full-LTO build is not two-build kernel reproducibility.
- Offline qualification does not prove candidate boot, userspace execution,
  retained publication, rollback, or final device health.
- Any future connected qualification or F1 attempt remains a separate Process
  v2 action with a new D0 preparation and fresh exact approval.
