# A90 H15 UFS `dev_t` Cross-Boot Drift Incident

Date: 2026-08-10

## Result

H15 run01 is refuted and consumed. The exact A90 returned healthy after the
separately reviewed one-shot armed-state recovery, with H15 installed and
`binding=1 enable=0 latch=0`. No candidate, arm, reboot, handoff, or recovery
action from that ordinal may be replayed.

The visible automatic-handoff `E1` was a pre-latch `-EPERM` caused by treating
Linux block `dev_t` as a cross-boot identity. Arm-time qualification observed
the unique userdata partition as `sda33` `259:17`. After the one authorized
reboot, the same stable partition was `sda33` `259:36`. H15 rejected that new
numeric tuple before runtime userdata resolution, latch creation, UFS mount,
or `switch_root`.

## Evidence and impact

- The arm-time path passed the full read-only UFS qualification at `259:17`.
- Same-boot post-incident D0 found one `PARTNAME=userdata` at `sda33`, sector
  count `231577432`, writable-capable block state, unmounted, with runtime
  `dev_t` `259:36`.
- No `A90D4` stop marker followed because H15 returned from the compiled-value
  validator before entering the runtime resolver.
- The H15 enable marker remained at `1,0`; exact recovery removed only that
  marker once, synced the parent, and proved H15 health at `0,0`.
- Userdata write, format, repair, filesystem replay, payload transfer, boot
  flash, and S22+ command counts for the incident and diagnosis are all zero.

The device safety result is unambiguous: stable UFS identity and content did
not drift, but the ephemeral kernel numeric assignment did. The incident adds
the `UFS_DEVT_CROSS_BOOT_DRIFT` hazard class and invalidates the V1 fixed-`dev_t`
capability for successor boots.

## H16 correction boundary

H16 is a fresh version/build and marker namespace. Its V2 capability:

1. resolves the sole `PARTNAME=userdata` sysfs entry in each native session;
2. requires exact `sda33`, sector count, size range, `ro=0`, and unmounted state;
3. requires any existing by-name or private node to match the freshly resolved
   `dev_t`;
4. uses that numeric tuple only to create and validate a private block node in
   the same session;
5. re-resolves after display-owner cleanup and requires the numeric tuple and
   stable identity to remain unchanged before a read-only `noload` mount; and
6. retains exact UUID, label, appliance marker, content-manifest, read-only
   mount, no-replay, boot-only rollback, and final-health requirements.

Any duplicate userdata `PARTNAME`, stable identity drift, same-session numeric
drift, mounted target, node mismatch, content mismatch, or recovery ambiguity
fails closed. H16 requires a fresh independent capability review and fresh
F1/D1 bindings; this incident report grants no live authority.

Validation: same-boot exact A90 D0 isolated the `259:17` to `259:36` drift;
38 H16 focused tests and 103 related auto-handoff, benchmark, and recovery
tests passed; Python compilation and `git diff --check` passed; deterministic
A/B builds were byte-identical at boot SHA256
`d545082ed6fd5dcab6c050f1f6b0b6ffa8c7cdb8783a1cb262eec428e1451b88`.
S22+ was not contacted.
