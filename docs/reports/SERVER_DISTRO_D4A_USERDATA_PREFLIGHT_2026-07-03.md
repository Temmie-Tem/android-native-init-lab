# Server-Distro D4A Userdata Preflight

- Date: `2026-07-03`
- Unit: `D4A read-only userdata appliance preflight`
- Decision: `server-distro-d4a-userdata-preflight-pass`
- Private run: `workspace/private/runs/server-distro/d4a-userdata-preflight-r4-20260703T112158Z/`
- Device action: read-only observation only
- Final device state: `v2321-usb-clean-identity-rodata`, `selftest fail=0`

## Result

D4A passed. The runner performed no format, no mount, no flash, and no reboot:

```text
NO FORMAT PERFORMED
NO MOUNT PERFORMED
NO FLASH PERFORMED
```

The authoritative target was re-derived from sysfs `PARTNAME=userdata`:

```text
target.source=partname-scan
target.block=sda33
target.realpath=/dev/block/sda33
target.dev=259:27
target.partname=userdata
target.devname=sda33
target.size=118567645184 bytes
target.gib=110.42
target.ro=0
```

Only one `PARTNAME=userdata` block was found (`sda33`). The target is not mounted, and the preflight
found no collision with the forbidden partition names. SD remains mounted read-write at `/mnt/sdext`
with about `48687256` KiB available.

## Recovery and Source Checks

Rollback images were present:

- v2321 SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- v2237 SHA256: `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`
- v48: present, SHA256 `1c87fa59712395027c5c2e489b15c4f6ddefabc3c50f78d3c235c4508a63e042`

The clean D3 sysvinit source image is present and SHA-pinned:

```text
workspace/private/builds/server-distro/d3-sysvinit-usrmerge-20260703T101657Z.img
6f1960eb4332e1a22d5da1c98e990352c58d80157fbe6286b53ec9fe8ebe59f7
```

The extracted rootfs source exists, including `/sbin/init` and the D3 firstboot marker. The D3B live pass
report is present and contains the TWRP v2321 recovery evidence used as the D4A recovery-envelope check.

## D4B Requirements Found

The current v2321 resident is sufficient for D4A observation, but D4B must add the missing destructive
operation support in a fail-closed candidate:

- `mkfs.ext4` is not present in the current busybox applet list, so D4B must stage or bundle a known
  formatter before D4C.
- `/dev/block/sda33` is not materialized in the current native-init `/dev`, even though sysfs proves
  `PARTNAME=userdata`. D4B must materialize the userdata block node from the verified `dev=259:27`
  identity immediately before format, then re-run the same identity checks.

## Verification

- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile workspace/public/src/scripts/server-distro/run_d4a_userdata_preflight.py tests/test_server_distro_d4a_userdata_preflight.py`
- `PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest tests.test_server_distro_d4a_userdata_preflight`
- Live D4A run: `server-distro-d4a-userdata-preflight-pass`
- Final live health: `v2321-usb-clean-identity-rodata`, `selftest fail=0`

## Next

D4A unblocks D4B. D4C is still not allowed: `d4c_allowed_now=false` until D4B provides the fail-closed
native-init surface, userdata node materialization, and `mkfs.ext4` support.
