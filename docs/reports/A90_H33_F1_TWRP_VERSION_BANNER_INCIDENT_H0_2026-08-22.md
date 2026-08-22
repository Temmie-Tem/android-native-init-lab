# A90 H33 F1 TWRP version-banner incident — H0

Date: 2026-08-22
Target: Samsung Galaxy A90 5G only
Device contact by this repair: none
Authority: no D0, approval, F1, replay, or live authority

## Incident

The attended H33 F1 attempt stopped before both image writes. The candidate
and rollback branches each ended in `PRE_WRITE_FAILURE`; candidate and rollback
boot-write counts are zero. The fixed native-init helper compared
`$(twrp --version)` with the bare string `3.7.0_12-0`.

The exact bound recovery output is the full canonical banner
`TWRP openrecoveryscript command line tool, TWRP version 3.7.0_12-0` followed
by its terminal newline. The bare comparison therefore rejected the exact
TWRP identity before the push/write boundary. This is a host helper defect,
not evidence that the candidate kernel booted or failed.

The candidate-neutral postrollback finalizer later observed exact healthy
V2321, closed the H33 recovery branch, and released only the active guard. The
H33 candidate guard remains consumed. No candidate/rollback write, reboot,
recovery transition, image, partition, or replay effect is authorized by this
record.

## Narrow repair

`native_init_flash.py` now binds the complete literal TWRP banner for
`3.7.0_12-0` in the existing first identity check. It does not use a
substring, regex, prefix, suffix, or alternate version. The existing
`rebootsystem.sh` symlink/type/mode/owner/size/link-count/hash checks and
command ordering are unchanged. Host tests cover the exact full banner and
reject bare, wrong-version, prefixed, suffixed, and multiline outputs.

The owner execution closure changed from the H33 review's
`48cb09e35b25f02e15fde091c93f2755b366fcb561210df49ffbafea3d333854` to
`1c31fb97e8f181e63bd71949b020f647aa8dab45c63d13bd089f6be2659da8a8`.
The continuation closure bound by the frozen H33 input was
`a62318c74c334509560f7c84fead011eb0a0c7fa6d8a80a45b4d72539a97a4df`; the
current continuation is `d053e137ca6d984709e53a1200d1e980f6d766ab4dd30cbb012cef2ddd3ee9e1`.
Therefore the H33 `PASS_GO` review
`251235439de66b408397768201016c390bbf4d3d94bd73877117501b21294f77` remains
historical evidence bound to the old closure and is not current authority.
A fresh independent review is required before any future F1 use. No H34
candidate is built or allocated here.
