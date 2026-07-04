# WSTA134 D-public HUD Split Prepared Rootfs Pass

Date: 2026-07-05 08:00 KST

## Verdict

WSTA134 built a real private D-public rootfs/tarball using the WSTA133 split HUD
wiring, then inspected the prepared rootfs and tarball to prove the split HUD
producer/presenter files and markers landed in the artifact that a later D4/live
gate would consume.

This is a host-only private artifact unit.  It did not perform device action,
boot flash, native reboot, Wi-Fi association, DHCP, public tunnel, public smoke,
packet-filter mutation, userdata mutation, DRM open, KMS `SETCRTC`, or
switch-root.

## Build Command

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/server-distro/prepare_wsta3_sta_rootfs.py \
  --run-id wsta134-dpublic-hud-split-prepared-rootfs-20260705T0800KST \
  --run-dir workspace/private/runs/server-distro/wsta134-dpublic-hud-split-prepared-rootfs-20260705T0800KST \
  --immediate-snapshot-only \
  --stage-dpublic-binaries \
  --stage-api-probe-tools \
  --stage-syscall-trace-tools
```

Result:

- decision: `wsta3-private-rootfs-prepared`
- ok: true
- device action: `none`
- no flash: true
- no Wi-Fi association: true
- no DHCP: true
- no public tunnel: true
- secret values logged: `0`

Private artifacts:

- rootfs:
  `workspace/private/runs/server-distro/wsta134-dpublic-hud-split-prepared-rootfs-20260705T0800KST/rootfs`
- tarball:
  `workspace/private/runs/server-distro/wsta134-dpublic-hud-split-prepared-rootfs-20260705T0800KST/a90-wsta3-userdata-rootfs.tar`
- tarball size: `340019200` bytes
- tarball mode: `0600`
- tarball SHA256: redacted by policy

## WSTA134 Proof

Private proof JSON:

`workspace/private/runs/server-distro/wsta134-dpublic-hud-split-prepared-rootfs-20260705T0800KST/wsta134_dpublic_hud_split_prepared_rootfs_proof.json`

Result:

- decision: `wsta134-dpublic-hud-split-prepared-rootfs-pass`
- summary pass: true
- tarball exists: true
- tarball mode `0600`: true
- no device action: true
- no Wi-Fi/public path: true
- quick tunnel disabled: true
- secret values logged zero: true

Split HUD rootfs checks:

- `usr/local/bin/a90-dpublic-hud-intent` exists, mode `0755`
- `usr/local/bin/a90-dpublic-hud-presenter` exists, mode `0755`
- intent producer SHA256:
  `f09d1eb6b57de50ed14fdf17d4d77751fc86ff41782ab51c90bb40ea070334f3`
- presenter SHA256:
  `055588a9c9ce61afa47ed532b2a7f62dbbef2a319d0b07fda1cd9b8d0fa2a76d`
- `etc/a90-dpublic/service-hardening.json` sets `dpublic-hud` to
  `no-network-intent-producer-only`
- `etc/a90-dpublic/service-hardening.json` keeps `default_public_off=true`
- `etc/a90-server-distro-stage` includes
  `hud-split-boundary=/run/a90-dpublic/hud-intent.json`
- `etc/a90-server-distro-stage` includes
  `hud-split-direct-kms-for-a90hud=disabled`
- `etc/a90-server-distro-stage` includes
  `hud-split-presenter-owner=native-init`
- `etc/a90-d3-firstboot` invokes
  `a90-service-launch dpublic-hud ... a90-dpublic-hud-intent`
- `etc/a90-d3-firstboot` records `hud_presenter_started=0`
- `etc/a90-d3-firstboot` keeps the legacy direct HUD as fallback only

Tarball entry check:

```text
./etc/a90-d3-firstboot
./etc/a90-dpublic/service-hardening.json
./etc/a90-server-distro-stage
./usr/local/bin/a90-dpublic-hud-intent
./usr/local/bin/a90-dpublic-hud-presenter
```

Direct rootfs file check:

```text
644 1466 .../rootfs/etc/a90-dpublic/service-hardening.json
644 1570 .../rootfs/etc/a90-server-distro-stage
755 11733 .../rootfs/etc/a90-d3-firstboot
755 71480 .../rootfs/usr/local/bin/a90-dpublic-hud-intent
755 71504 .../rootfs/usr/local/bin/a90-dpublic-hud-presenter
```

## Validation

The preparer internally verified the tarball and reported
`required_entry_count=6`.

Additional host-only verification:

```sh
tar -tf workspace/private/runs/server-distro/wsta134-dpublic-hud-split-prepared-rootfs-20260705T0800KST/a90-wsta3-userdata-rootfs.tar |
  rg '(^|/)(a90-dpublic-hud-intent|a90-dpublic-hud-presenter|a90-d3-firstboot|a90-server-distro-stage|service-hardening\.json)$'
```

Pass.

```sh
find workspace/private/runs/server-distro/wsta134-dpublic-hud-split-prepared-rootfs-20260705T0800KST/rootfs \
  -maxdepth 4 \
  \( -path '*/usr/local/bin/a90-dpublic-hud-intent' \
     -o -path '*/usr/local/bin/a90-dpublic-hud-presenter' \
     -o -path '*/etc/a90-server-distro-stage' \
     -o -path '*/etc/a90-d3-firstboot' \
     -o -path '*/etc/a90-dpublic/service-hardening.json' \) \
  -printf '%m %s %p\n'
```

Pass.

## Next

WSTA135 should be the live-capable D4/preflight gate for this prepared artifact:
stage the WSTA134 tarball through the guarded userdata/rootfs path, boot it, and
verify firstboot writes only the bounded HUD intent while native/root owns the
display presenter.  Keep D-public exposure default-off unless a separate
operator gate explicitly enables it.
