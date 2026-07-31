# A90 Resident Boot Promotion v1 H0 Policy — 2026-08-01

## Result

`A90_RESIDENT_BOOT_PROMOTION_V1_H0_POLICY_PASS`

The A90-only F1-RP policy is adopted. It permits one previously exercised
candidate to become the resident experimental baseline only after exact health
passes on its first boot and on one separate reboot with a distinct USB
generation. Ordinary F1 and every S22+ run retain mandatory rollback.

This unit is H0 only. It created no runner, manifest, approval, candidate
packet, or device authority. Exact V2321 therefore remains resident.

## Bounded contract

- Fresh preflight binds one A90, exact candidate, exact V2321 rollback, and
  final rootfs disposition `absent` or `exact`.
- `absent` permits at most one absent-only staging write; `exact` uses a
  read-only verified-existing path with zero writes. The work path is absent in
  either case, and delete-and-restage repair is forbidden.
- One candidate attempt and one resident reboot must produce two exact health
  closures on distinct USB generations before `PROMOTED_CLOSED`.
- Every failure or ambiguity after candidate attempt starts takes the exact
  rollback-only branch. Candidate and rollback replay remain forbidden.
- A closed or blocked outcome cannot reuse its approval. `RECOVERY_REQUIRED`
  retains only the exact rollback recovery authority.

The binding policy is
`docs/operations/A90_RESIDENT_BOOT_PROMOTION_V1.md`. Its pure H0 state model is
`workspace/public/src/scripts/server-distro/a90_resident_promotion_v1_model.py`.

## Verification

- Focused local regression: `148/148 PASS` (`13 + 4 + 11 + 9 + 6 + 105`).
- Modified Python: `py_compile PASS`.
- Independent safety review: `PASS`, no remaining High, Medium, or Low finding;
  reviewer-selected checks `28/28 PASS`.
- `git diff --check`: PASS.
- Policy SHA256:
  `082a45e7b04e0762faeca4b4e9ca41666610faaf48cc66c820dfeb16d652d412`.
- State-model SHA256:
  `d8daaa459a36be6bd5a23e10653c1e85c06b46b7d6b04e493da8b4266a65ee89`.
- Private host receipt SHA256:
  `110b7b7251d8fee387fc73d4d7b9e6cd1c222ce8f40d67dfb6649be25b129959`.

No A90, S22+, USB, network, flash, or other device action occurred.

## Next boundary

If continued, the next unit is only the small A90 F1-RP runner and immutable
manifest validator. It remains H0 until independently reviewed and followed by
a fresh, exact live approval. The ordinary resident D1 runner stays inactive
until promotion itself closes successfully.
