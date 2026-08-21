# A90 H32 minimal F1 qualification handoff — H0

Target: operator-owned Samsung Galaxy A90 5G only
Authority: none; no D0, approval, F1, transfer, reboot, or live effect

Review `docs/reports/A90_H32_MINIMAL_F1_QUALIFICATION_INPUT_2026-08-22.json`
against current owner closure `0a6122d2902d9f72b8e4d1e1f9d23cbcc3767d48be50a01e052ba81a1c41745e`
and continuation closure `585869c5c4eb843b165afea4ba1e5d10f228cda84dd1b924936e0ea0c369921f`.
The stable continuation review is 547 bytes at SHA-256
`7688558ec7a0b592053e04408d4a3863ae8a8ecc389c542d17ca906137c5d606`.

H32 is `0.11.199 / phase3-minimal-h32-stock-rebuild-1007-cfp`, size
58,372,096, SHA-256 `e56cb1201d63e26f275de10d6a4eb6a1686f6021b6613aa4dde1374930dd299d`.
A/B are byte-identical and its kernel blob equals H31 at `59f79b8f…`.
Only version/build and fresh H32 enable/latch identities differ. H29, H30, and
H31 are consumed and cannot be replayed or used as H32 boot evidence.

Confirm candidate, rollback, report, flat/effective manifests, fresh state,
current continuation lease, and accepted new-build-certificate hazard
`cd8d868ac3b7fd5f5a934955a50ff2f32c228ab8b2e52e061d9f0ad90d73ca69`.
The claim is only one attended boot-only Native-health experiment with exact
V2321 rollback. External modules, stock equivalence, full reproducibility, and
H32 boot acceptance remain unproved. Public recovery identity stays unbound
until the private manifest is prepared.

On PASS publish only
`docs/reports/A90_BOOT_ONLY_F1_MINIMAL_H32_INDEPENDENT_REVIEW_2026-08-22.json`
with the existing minimal-review schema, zero findings/contacts, and
`liveAuthority=false`. PASS qualifies the candidate/owner pairing but grants no
private manifest, D0, approval, F1, or live authority.
