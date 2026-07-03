# Server-Distro D3A Sysvinit Usrmerge Rebuild - Host

- Date: `2026-07-03`
- Unit: `D3A host-only sysvinit rootfs/image repair`
- Decision: `server-distro-d3a-sysvinit-usrmerge-rebuild-host-pass`
- Device action: none
- Flash: none
- Userdata: untouched

## Artifact

- Rootfs: `workspace/private/builds/server-distro/d3-sysvinit-usrmerge-20260703T101657Z-rootfs`
- Image: `workspace/private/builds/server-distro/d3-sysvinit-usrmerge-20260703T101657Z.img`
- Image size: `2147483648`
- Image SHA256: `6f1960eb4332e1a22d5da1c98e990352c58d80157fbe6286b53ec9fe8ebe59f7`
- Summary: `workspace/private/builds/server-distro/d3-sysvinit-usrmerge-20260703T101657Z-summary.json`

## Fix

The previous D3A image broke Debian usrmerge top-level links while extracting sysv packages:

- `/bin` became a real directory instead of `bin -> usr/bin`.
- `/sbin` became a real directory instead of `sbin -> usr/sbin`.
- `/lib` became a real directory instead of `lib -> usr/lib`.

That made `/sbin/init` visible but non-executable after `switch_root`, because its requested interpreter
`/lib/ld-linux-aarch64.so.1` no longer resolved to the loader under `/usr/lib`.

`prepare_d3_sysvinit_rootfs.py` now merges extracted top-level `/bin`, `/sbin`, and `/lib` contents into
their `/usr/*` targets after `dpkg-deb -x`, then recreates the usrmerge symlinks.

## Verification

- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile workspace/public/src/scripts/server-distro/prepare_d3_sysvinit_rootfs.py tests/test_server_distro_d3_sysvinit_rootfs.py`
- `PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest tests.test_server_distro_d3_sysvinit_rootfs`
- Host build completed with `decision=server-distro-d3a-sysvinit-rootfs-host-pass`.
- Summary reports `usrmerge_links.bin -> usr/bin`, `usrmerge_links.sbin -> usr/sbin`, and `usrmerge_links.lib -> usr/lib`.
- `debugfs` verified image `/lib` is a symlink to `usr/lib`.
- `debugfs` verified image `/lib/ld-linux-aarch64.so.1` resolves to the loader symlink.
- `debugfs` verified image `/sbin/init` exists and is mode `0755`.

## Next

The D3B runner now pins this usrmerge-fixed D3 source image while keeping the V3372 native-init candidate.
