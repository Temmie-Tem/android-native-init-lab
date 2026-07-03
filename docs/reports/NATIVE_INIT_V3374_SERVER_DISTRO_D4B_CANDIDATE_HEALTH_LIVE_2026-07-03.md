# Native Init V3374 Server-Distro D4B Candidate Health Live

- Cycle: `V3374`
- Decision: `v3374-server-distro-d4b-candidate-health-live`
- Candidate under test: `A90 Linux init 0.11.134 (v3373-server-distro-userdata-appliance)`
- Candidate boot image: `workspace/private/inputs/boot_images/boot_linux_v3373_server_distro_userdata_appliance.img`
- Candidate boot SHA256: `78e3297063b1957626075bc8c22223ef7a195d0de684fdbd7f51deb824a49f6d`
- Final device state: rolled back to `v2321-usb-clean-identity-rodata`, `selftest fail=0`

## Result

D4B candidate-health passed. The V3373 D4-capable candidate was flashed through the checked
`native_init_flash.py` helper, booted cleanly, exposed the read-only D4B userdata preflight command, and
was then rolled back to v2321 through the same checked helper.

No D4C action was performed:

```text
NO FORMAT
NO POPULATE
NO SWITCH_ROOT_TO_USERDATA
NO USERDATA NODE MATERIALIZATION
```

## Preconditions

Before the candidate flash:

- resident device was `A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)`;
- resident `status` reported `selftest pass=11 warn=1 fail=0`;
- standalone resident `selftest` reported `pass=11 warn=1 fail=0`;
- rollback and candidate boot image SHA-256 values matched the pinned values:
  - v3373: `78e3297063b1957626075bc8c22223ef7a195d0de684fdbd7f51deb824a49f6d`
  - v2321: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
  - v2237: `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`
  - v48: `1c87fa59712395027c5c2e489b15c4f6ddefabc3c50f78d3c235c4508a63e042`

## Candidate Flash

The checked helper validated the local V3373 image marker and SHA, requested recovery from native init,
observed recovery ADB, pushed the sealed boot image copy, verified the remote SHA, wrote only the boot
partition, read back the boot prefix SHA, and rebooted to the candidate:

```text
local image sha256: 78e3297063b1957626075bc8c22223ef7a195d0de684fdbd7f51deb824a49f6d
ADB ready: recovery
remote image sha256: 78e3297063b1957626075bc8c22223ef7a195d0de684fdbd7f51deb824a49f6d
boot block prefix sha256: 78e3297063b1957626075bc8c22223ef7a195d0de684fdbd7f51deb824a49f6d
cmdv1 verify passed: version/status rc=0 status=ok
phase.native_init_flash.total.elapsed_sec=63.591 ok=1
```

Candidate identity and health:

```text
A90 Linux init 0.11.134 (v3373-server-distro-userdata-appliance)
selftest: pass=12 warn=1 fail=0
```

One repeated `status` command printed the status body and `[done]` marker but missed the protocol
`A90P1 END` marker, so it was not used as primary evidence. The helper-verified candidate status and a
separate standalone `selftest` both passed.

## Device-Side D4B Preflight

The first preflight attempt was refused with `status=busy` because the auto menu was active. The same
read-only command was retried with `--hide-on-busy` and passed:

```text
A90D4 preflight target.source=partname-scan target.devname=sda33 target.sysname=sda33 target.dev=259:17 target.sectors=231577432 target.size_bytes=118567645184 target.ro=0 target.mounted=0 target.node=/dev/block/a90-userdata target.node_exists=0 target.byname_exists=0 target.byname_matches=0
A90D4 preflight=ok format_allowed=0 node_materialized=0
A90P1 END seq=8 cmd=userdata-appliance-preflight rc=0 errno=0 duration_ms=10 flags=0x0 status=ok
```

This proves:

- the candidate resolves exactly one `PARTNAME=userdata` target;
- the target is still `sda33`;
- sector count and byte size match D4A;
- the target is read-write capable and not mounted;
- `/dev/block/a90-userdata` was not materialized by preflight;
- no format/populate/handoff operation ran in this gate.

## rdev Drift Note

D4A observed the same `sda33` userdata target as `dev=259:27`. This V3373 candidate boot observed it as
`dev=259:17`. The stable cross-boot identity is therefore `PARTNAME=userdata` plus `devname=sda33`,
sector count, byte size, `ro=0`, and mounted state. The numeric `target.dev` major:minor remains useful
only as a same-session guard.

Consequence for D4C: do not pass the D4A `259:27` literal to `userdata-appliance-format`. The D4C
runner must parse the live `userdata-appliance-preflight` output in the same candidate session and pass
that exact same-session `target.dev` value into the mutating command.

## Rollback

The v2321 rollback used the checked helper from the V3373 candidate:

```text
local image sha256: ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb
remote image sha256: ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb
boot block prefix sha256: ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb
cmdv1 verify passed: version/status rc=0 status=ok
phase.native_init_flash.total.elapsed_sec=64.356 ok=1
```

Final standalone checks:

```text
selftest: pass=11 warn=1 fail=0
A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)
```

One immediate chained post-rollback `version` command hit serial input noise and missed its protocol END
marker. A slow-input retry succeeded and is the final version evidence above.

## Next

D4B candidate-health is complete. D4C is now blocked only by its remaining entry gates:

- prove the selected formatter path on device, or add a non-destructive formatter probe command before
  the destructive run;
- prepare and SD-stage a SHA-pinned rootfs tarball derived from the clean D3 rootfs source;
- re-confirm rollback/TWRP and run a fresh same-session `userdata-appliance-preflight` immediately
  before formatting.
