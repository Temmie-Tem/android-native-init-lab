# Server-Distro D3B Switchroot Attempt 5 - Loop Major Parser Stop

- Date: `2026-07-03`
- Unit: `D3B live checked switch_root handoff`
- Candidate: `A90 Linux init 0.11.130 (v3369-server-distro-switchroot)`
- Candidate image: `workspace/private/inputs/boot_images/boot_linux_v3369_server_distro_switchroot.img`
- Candidate SHA256: `13fa09320a42d98af7cc2712347dba0c35283af0085b7f87c12f81691f737505`
- D3 keyed image: staged on SD before candidate flash
- Final device state: rolled back to `v2321-usb-clean-identity-rodata`, `selftest fail=0`

## Result

The runner reached the gated PID1 handoff command after the pre-staged SD image SHA check passed.
The command verified the image SHA, but stopped before `switch_root` while creating `/dev/loop0`:

```text
A90D3B sha=... expected_sha_match=1
A90D3B loop_node=fail rc=-2
```

No Debian handoff was attempted, no SSH marker was expected, and `userdata` was not touched.
The runner rollback-flashed v2321 through `native_init_flash.py`; post-rollback health check reported
the rollback version and `selftest fail=0`.

## Root Cause

The V3369 native parser for `/proc/devices` used a loop shaped as:

```c
while (fscanf(fp, " %u %63s", &major_num, name) == 2) {
    ...
}
```

That stops on section header lines such as `Character devices:` before it reaches the later
`Block devices:` entry for `loop`, so `d3_read_loop_major()` returned `-ENOENT`.

## Follow-up

V3370 fixes the native parser to read `/proc/devices` line-by-line with `fgets()`, skip non-matching
headers, and continue scanning until it finds the `loop` block-device entry. The D3B runner default
candidate is moved to the V3370 loopfix image before the next live attempt.
