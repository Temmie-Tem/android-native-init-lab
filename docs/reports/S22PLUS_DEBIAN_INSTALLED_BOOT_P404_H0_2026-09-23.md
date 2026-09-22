# S22+ P404 installed Debian PID 1 preparation — H0, 2026-09-23

## Result and boundary

One fresh `v0.4.0-rc.4` boot-only P404 candidate was built from the completed
P401 root identity. This preparation performed **zero device actions**. The
[installed-boot definition](../operations/S22PLUS_DEBIAN_INSTALLED_BOOT_V1.md)
remains `DRAFT_H0`; the new owner has no live `PASS_GO` review receipt, target
adoption, finite attended grant or live authority. Samsung Debian PID 1, NCM,
SSH, shutdown, P399 native return and physical recovery remain unproved.

The private retained outputs are under
`workspace/private/outputs/s22plus-debian-installed-h0-20260923-1/`:

| Selected input | SHA-256 | Meaning |
| --- | --- | --- |
| `build-5/artifact.json` | `99de9421701ee202769645ab5bdb3273fc7319f36cfe7fe064fbcaca4d67cf7b` | Identical A/B AP, retained FYG8 kernel, archive-free installed-only bootstrap. |
| `vm-6/result.json` | `c7cf93950c55b0e782ec4b30049841a74027f854da5eb92954e6143a69513598` | Real ARM64 virtual installed-root PID 1/SSH, orderly shutdown and empty-root rejection. |
| `qualified-1/qualification.json` | `d0af6c1072b4cbc0acc3733ee0b00a95417b766d15d20d3724f3b6a4ae7fb513` | Independent artifact-byte readback joining the physical package, fixed RAM command and VM result; H0 only. |

The [independent H0 review receipt](../../workspace/public/src/device-action/bindings/s22plus_debian_installed_boot_h0_review.json)
binds 59 exact source receipts to private request SHA-256
`d0ba9b5aff9961dfdf146cb35ebe24797663cfaff3457b7319a31bccbfe30b25`.
The reviewer rechecked the final bytes and closed the identified source,
recovery, result-validation and lease findings with `PASS_H0_REVIEW_READY`.
This receipt has no `PASS_GO` or device authority.

P401's physical installation claim and candidate remain consumed. P403 proved
the retained root's fixed userspace child and its Android close; neither result
is relabelled as PID 1 handoff. The selected P399 native `v0.3.1-rc.1` AP and
old V3 admission are rederived as the proposed normal return image. Its old
grant and installation claim are not reused. The unchanged original A is the
separate attended fallback.

## Implementation and checks

The installed-only compile path requires completed markers and full root
metadata/content verification before a writable mount, then omits the archive,
extractor and installation marker paths. Without that compile selection, the
P401 init compiles byte-identically to its retained binary. The new ramdisk
binds a hash-checked restricted shutdown command from tmpfs, read-only, over
the existing Debian command file; it does not alter the ext4 file. This permits
one shutdown request at a positive boot count while keeping the prior command
vocabulary. The virtual installed root had reached count 3 and completed
shutdown. A cloned virtual disk with only the earlier virtual shutdown receipt
removed was used for that exercise; no physical root byte was changed.

The candidate A/B packages matched. The selected bootstrap is a static ARM64
ELF. The VM authenticated initial PID 1 and root, rejected another installation,
and powered off through the fixed command. The empty-root case stopped before
handoff, without changing the backing disk. Focused tests cover the new
journal's ordered effects, physical return statement, no-replay recovery,
interrupted A-result completion, corrupted-result rejection, recovery import
isolation, native-close lease serialization and raw health projection (9 tests);
the existing P401 owner suite still passes
(24 tests). Touched Python compiled, and the diff passed whitespace checks.

The host owner is a new P404 one-shot proposal. It durably separates Android
Download, P404 transfer, Debian health, Debian shutdown, P399 normal return,
native health and original-A recovery. It rejects repeated transfer intents
and an A recovery without physical attendance. After an uncertain intended
effect it preserves the global F1 owner until a proved native or original-A
terminal. Candidate-only source drift and grant expiry do not reopen the
research path and do not erase the retained A recovery owner.

## Remaining review before a live proposal

Adopt the exception in the common and exact target contracts, then independently
review those higher-precedence changes with the reachable owner, transfer,
observation and recovery closure for a live `PASS_GO` receipt. Fresh
current-state/grant checks would then be required for a finite attended run.
The H0 receipt and earlier consent are not substitutes for those steps.
