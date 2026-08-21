# A90 exact-toolchain H29 identity-only materialization — H0

Date: 2026-08-21
Target: Samsung Galaxy A90 5G only
Tier: H0 host-only build/materialization
Device contact: none
Authority: no D0, D1, F1, token, approval, or live authority

## Result

H29 was materialized from the already-staged exact-toolchain H28 functional
configuration. This unit changes identity only:

- version: `0.11.196`;
- build: `phase3-minimal-h29-stock-rebuild-1007-cfp`;
- cycle: `H0-PHASE3H29`;
- fresh enable/latch paths:
  `/cache/a90-auto-handoff-phase3-minimal-h29.enable` and
  `/cache/a90-auto-handoff-phase3-minimal-h29.done`.

The H28 base boot, init closure, cflags, kernel, and ramdisk functional content
were preserved. `candidate_authority = false` remains explicit. The manifest
derives the same H16 base lineage because the flat-builder's maximum manifest
inheritance depth is two; all H28 functional leaves are copied and compared in
the focused H29 test.

Whether this kernel boots A90 is unproved. This report does not qualify H29,
create an F1 manifest, issue a token, or authorize any device effect.

## Exact bindings

| Item | Size | SHA-256 |
|---|---:|---|
| H29 manifest | — | `faab594e46ca9cfaaa477b70ef55f4674b8aab9e95847a1db8e1871a62c6988a` |
| H29 effective manifest | — | `ecefcf16abcd603c69c16900cc21f2c7f422ad3beda5c032c7bcea5245d77347` |
| H29 A/boot.img | 58,372,096 | `c3d1b84eab65f387ce807cf9c355dc04dcc966cef15bf64e4fda901242907324` |
| H29 B/boot.img | 58,372,096 | `c3d1b84eab65f387ce807cf9c355dc04dcc966cef15bf64e4fda901242907324` |
| A/B receipt | 5,426 | `8749cc6577089fc93166ffa17d1eeb491ce040b3871e1b16c1a9732fe5e5c4dc` |
| exact H29 kernel blob | 49,827,613 | `59f79b8f0e8f8f3551d04488ec32073faa8ef9ba7439bd65e95d0585ab82ccac` |
| kernel Image | 48,830,480 | `6b9468eaa5c67dee0f8df8aa2492e33e0a2181049e5e87547d2241c7f3fc8557` |
| H29 init | 1,723,376 | `5cb2eff26fcc20a8e750d9fbc722a0f1c256c7bb8c0a62f303df039fbe9b3db9` |
| H29 helper | 1,649,904 | `fcb005b0454aceb08aa6f8f81d83aa303e37199a56e018eb2501e4225f08e00e` |
| H29 ramdisk | 8,537,600 | `92270a9efd493bc4eff741810944e3b1ff127fa379461cdf9e4f1daafd90f111` |

H28's candidate SHA was
`aea34a96464affd2f7e6c30d237e2175940eef511e69c1452c9deab4833a521b`; H27's
candidate SHA was
`fa7ab8af8cec027c433653da92eb6cb4ca6f3a02d7624a4f292f61906e8ce500`. H29 is
distinct from both and was built in the fresh private namespace:

`workspace/private/outputs/a90-h29-stock-rebuild-1007-cfp-ab-20260821-01/`

The private base input remains the exact H28 base:

`workspace/private/inputs/boot_images/boot_a90_base_stock_rebuild_1007_20260821.img`

size `66,379,776`, SHA-256
`5cf27a56b7887b3f766af3caa7c1441cac51d153faf4f64a771902ad7f0118f6`.

## Validation

The flat-builder audit and A/B build both passed with the staged observer key,
the exact 10.0.7-era toolchain, and unchanged accepted-base input. The packed
boot contains the exact expected kernel blob and H29 banner; the H28 banner is
absent. The receipt contains only `boot`, `init`, `helper`, and `ramdisk`
artifacts; no recovery, vendor_boot, DTBO, vbmeta, super, userdata, persist,
modem, bootloader, or other partition payload is selected.

Focused H29 tests pass `6/6` with private checks active (no skips on this host).
The H28/H29 materialization tests pass `12/12`. The broader legacy
`test_a90_flat_builder` suite remains non-green on the current tree (`33/40`):
five cases report the existing native-init closure hash mismatch and two assert
older error text/depth behavior. That is recorded as a repository-wide
validation blocker, not promoted to an H29 artifact failure; the H29-specific
audit and build completed successfully. Python compilation and
`git diff --check` also pass. No qualification review,
F1 manifest, D0, attended approval, or device contact was created by this
unit.
