# S22+ FYG8 P3.01-R1 Expected-Final Correction

Date: 2026-08-05 KST
Target: Samsung Galaxy S22+ FYG8 (`SM-S906N` / `g0q` / `S906NKSS7FYG8`)
Tier: H0 only
Verdict: `PASS_P301_R1_EXPECTED_FINAL_CORRECTION_HOST_ONLY`

## Outcome

P3.01-R1 corrects the userspace subtype-selection precondition from the wrong
`0xE06` attached/UNKNOWN tuple to the exact P3.00 baseline `0xE02`, which is
UDC not-attached, speed UNKNOWN, `COREIDLE=1`, and `SUSPHY=0`.

The value is no longer copied as a second literal. The telemetry specification
derives it with the inherited canonical final-state encoder, and both generated
runtime C and the executable C closure consume that specification value.
Known, unknown, mixed, and four count-bucket subtype paths execute at `0xE02`.
The next valid final-state index and ingress-class mismatch still execute the
drift branches at `0x5004` and `0x5003` respectively.

## Identity and artifacts

The complete nine-key P3.01 payload identity was printed and hashed before the
new intent. Exactly three keys changed: telemetry specification, telemetry
transform, and the overlay contract's new immutable output location. The
generated-C closure and focused test changed outside payload identity. After
intent derivation all nine payload keys remained unchanged.

- overlay semantic intent SHA-256: `996f08859e6a2049754f470755ec448d0c5efdf8c8a506665eb3a0270d2cebdc`
- `/init`: 66,384 bytes, SHA-256 `17eae28ae1e8fa0abcd47b05c3b57cfa5c54124db0192137b208a3f85978ee35`
- fixed P3.00 Image: 41,490,944 bytes, SHA-256 `01457240881b432f725b0f2d795813c38ef7cca4365633f9b0fc7c3a62744a3f`
- A/B boot image: 100,663,296 bytes, SHA-256 `bd1f044e92dfb73bcc92cfd69be4d30b442af1585e8b34aa39e55adab02effa5`
- A/B Odin AP: 27,105,321 bytes, SHA-256 `d281bef819ef2986b19eb826391a66f26401f16d6c54f13f1163d8183df9abfd`
- ready manifest: 2,797 bytes, SHA-256 `dcb9a96ff247836203d42afb8273208aa75dfbd697ceadc34995b0fc4179c4ea`

Both APs are byte-identical and contain exactly one regular
`boot.img.lz4`. The fixed kernel Image, probe descriptor, module plan,
rollback artifact, and transfer machinery did not change.

## Validation

- focused telemetry and overlay build tests passed;
- generated C executed the corrected subtype and preserved drift branches;
- combined P3.01/P3.00/sidecar regression passed 33/33;
- independent userspace links and candidate A/B packages were byte-identical;
- static artifact closure passed;
- Process-v2 offline promotion passed;
- a non-writing ready-manifest rehearsal reproduced the exact manifest hash;
- a narrow independent check of the changed selection closure and package
  binding returned `PASS_GO` with no finding.

No device command, reboot, payload, transfer, F1 arm, or A90 action occurred.
The next action is fresh S22+ D0 preparation; a retained-baseline stop, if
present, is handled separately and does not authorize replay of P3.01.
