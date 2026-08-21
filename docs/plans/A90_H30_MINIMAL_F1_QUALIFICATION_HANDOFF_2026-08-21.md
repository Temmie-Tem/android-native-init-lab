# A90 H30 minimal F1 qualification handoff — H0

Target: operator-owned Samsung Galaxy A90 5G only
Authority: none; no D0, approval, ordinal, F1, transfer, reboot or live effect

## Review subject

Review the public input
`docs/reports/A90_H30_MINIMAL_F1_QUALIFICATION_INPUT_2026-08-21.json`
against owner closure
`e0a1fa5d05ce15322b7e2966901b443917e54836fd1d04f5550fc9f05467c5ed`.
The reusable candidate-return capability is independently `PASS_GO` at current
closure `a396a7440ba936e90dbf8956c1c2404cc0dc1271fda1b304192b35f13eb28d6c`;
its stable review lease is 547 bytes at SHA-256
`d1537f029a922b5e6fdcbe3c27e97a3b6f94d240d4e53e0fd87cdc9fb0b8910b`.

H30 is version `0.11.197`, build
`phase3-minimal-h30-stock-rebuild-1007-cfp`, size 58,372,096, SHA-256
`d28bd41434d252619dd95ecb352f55140d93889fd599784c0a7dbf491959c5fe`.
It is identity-only relative to H29 and carries the same exact kernel. H29 is a
consumed, unproved historical run and cannot be replayed or used as evidence
that H30 boots.

Rollback remains exact V2321 `0.9.285 / v2321-usb-clean-identity-rodata`,
size 60,882,944, SHA-256
`ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`.
H30 state paths are `/cache/a90-auto-handoff-phase3-minimal-h30.enable` and
`.done`.

## Required checks

1. Recompute the owner closure and current continuation review lease.
2. Bind candidate, rollback, build report, flat/effective manifests, fresh
   state and exact new-build-certificate hazard without reading private bytes.
3. Confirm the hazard limits the unit to one attended boot-only Native health
   experiment and leaves external modules, stock equivalence, reproducibility
   and boot acceptance unproved.
4. Confirm H29 replay, H29 evidence substitution, candidate replay, extra
   Samsung/ADB endpoints, unconfirmed System return, nonquiescent helper,
   unstable boot ID, unhealthy selftest/pstore and stale review all fail closed.
5. Confirm the public recovery identity remains deliberately unbound: the
   eventual private manifest alone supplies the exact recovery serial digest.

On PASS, publish only canonical
`docs/reports/A90_BOOT_ONLY_F1_MINIMAL_H30_INDEPENDENT_REVIEW_2026-08-21.json`
with the existing minimal-review schema and zero findings/contacts. A PASS
qualifies the candidate/owner pairing but grants no private manifest, D0,
approval, F1 or live authority.
