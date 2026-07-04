# WSTA133 D-public HUD Split Rootfs Wiring Source Pass

Date: 2026-07-05 07:57 KST

## Verdict

WSTA133 integrates the WSTA132 split HUD producer/presenter into the D-public
rootfs preparation and firstboot profile wiring.  New rootfs builds can now
stage both split HUD binaries, mark the native-presenter boundary, and run the
Debian `a90hud` side only as a bounded intent producer.

This is a host-only source/wiring unit.  It did not perform device action, boot
flash, native reboot, Wi-Fi association, DHCP, public tunnel, public smoke,
packet-filter mutation, userdata mutation, DRM open, KMS `SETCRTC`, or
switch-root.

## Changed

- `workspace/public/src/scripts/server-distro/prepare_wsta3_sta_rootfs.py`
  - adds default private WSTA132 arm64 paths for:
    - `usr/local/bin/a90-dpublic-hud-intent`;
    - `usr/local/bin/a90-dpublic-hud-presenter`;
  - stages both split binaries when `--stage-dpublic-binaries` is used;
  - changes `dpublic-hud` service hardening intent from direct DRM output to
    `no-network-intent-producer-only`;
  - adds `hud-split-*` stage markers, including the intent file boundary,
    native-init presenter owner, and disabled direct KMS for `a90hud`;
  - records firstboot split-HUD checks in the preparation summary.

- `workspace/public/src/scripts/server-distro/a90_dpublic_firstboot.sh`
  - prefers `/usr/local/bin/a90-dpublic-hud-intent` when present;
  - runs it through `a90-service-launch dpublic-hud` so the Debian side remains
    `a90hud`;
  - writes `/run/a90-dpublic/hud-intent.json`;
  - does not start the native/root presenter from Debian firstboot;
  - keeps the old direct HUD path only as a fallback when the split producer is
    absent.

- Tests now cover split binary staging, split stage markers, firstboot intent
  producer wiring, presenter-not-started-by-Debian markers, and the updated
  service hardening network intent.

## Source Proof

Private run directory:

`workspace/private/runs/server-distro/wsta133-dpublic-hud-split-rootfs-wiring-20260705T0805KST`

Private output:

`workspace/private/runs/server-distro/wsta133-dpublic-hud-split-rootfs-wiring-20260705T0805KST/wsta133_dpublic_hud_split_rootfs_wiring.json`

Result:

- decision: `wsta133-dpublic-hud-split-rootfs-wiring-source-pass`
- intent staged: true
- presenter staged: true
- intent mode `0755`: true
- presenter mode `0755`: true
- `dpublic-hud` network intent split: true
- launcher maps `dpublic-hud` to `a90hud`: true
- firstboot invokes intent producer: true
- firstboot does not start presenter: true
- firstboot keeps legacy direct HUD as fallback only: true
- stage marker disables direct KMS for `a90hud`: true
- stage marker records presenter owner as native-init: true
- public default off: true
- secret values logged zero: true

Staged binary keys:

- `cloudflared`
- `http_get`
- `hud`
- `hud_intent`
- `hud_presenter`
- `smoke_httpd`

## Validation

```sh
sh -n workspace/public/src/scripts/server-distro/a90_dpublic_firstboot.sh
```

Pass.

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/server-distro/prepare_wsta3_sta_rootfs.py \
  tests/test_prepare_wsta3_sta_rootfs.py \
  tests/test_dpublic_smoke_helpers.py \
  tests/test_server_distro_wsta110_service_launcher_chroot_proof.py
```

Pass.

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest discover \
  -s tests -p 'test_prepare_wsta3_sta_rootfs.py'
```

`32 tests OK`.

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest discover \
  -s tests -p 'test_dpublic_smoke_helpers.py'
```

`15 tests OK`.

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest discover \
  -s tests -p 'test_server_distro_wsta110_service_launcher_chroot_proof.py'
```

`10 tests OK`.

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest discover \
  -s tests -p 'test_server_distro_wsta*.py'
```

`447 tests OK`.

The WSTA94 runner-error JSON printed during the full run is the expected
exception-path fixture from that unit test; unittest completed OK.

## Next

WSTA134 should build a private D-public rootfs/tarball with the WSTA133 split HUD
wiring enabled and prove the staged files/markers in that real prepared rootfs.
After that, the live gate can verify that Debian writes only the bounded intent
while native/root owns display presentation.
