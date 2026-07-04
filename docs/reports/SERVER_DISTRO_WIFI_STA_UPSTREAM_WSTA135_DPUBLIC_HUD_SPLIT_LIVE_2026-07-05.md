# WSTA135 D-public HUD Split Live Pass

Date: 2026-07-05 08:19 KST

## Verdict

WSTA135 ran the guarded D4 userdata path live for the split HUD appliance:
preflight, journaled ext4 format, tarball populate, switch-root to Debian PID1,
and SSH proof from inside the userdata-backed Debian appliance.

The first live attempt with the WSTA134 artifact found a real boundary bug:
`a90-service-launch dpublic-hud` correctly dropped to `a90hud`, but
`/run/a90-dpublic` was `root:root 0755`, so the intent producer could not create
its atomic tmp file and returned `write intent: Permission denied`.

WSTA135 fixes that contract in `a90_dpublic_firstboot.sh`: before launching the
intent producer, firstboot prepares `/run/a90-dpublic` as `root:a90hud` mode
`1770`.  This keeps the same intent path while giving `a90hud` bounded write
access and preserving sticky-directory protection for root-owned runtime files.

## Scope And Safety

- Boot flash: none.
- Native reboot: one reboot from Debian back to the existing V3397 native image.
- Userdata: explicitly formatted through the existing guarded D4
  `userdata-appliance-*` commands only.
- Formatter: SHA-pinned e2fsprogs `mke2fs`/`dumpe2fs`/`tune2fs`.
- Public tunnel: not started.
- Public URL: not observed or logged.
- Secrets: no secret values logged.
- Final live state: Debian userdata appliance left running on
  `192.168.7.2:2222` for operator inspection.

## Evidence

Private run directory:

`workspace/private/runs/server-distro/wsta135-dpublic-hud-split-live-20260705T0810KST/`

Corrected private rootfs/tarball directory:

`workspace/private/runs/server-distro/wsta135-hud-intent-boundary-prepared-rootfs-20260705T0825KST/`

Key live markers:

- Native return after the first Debian attempt: V3397, `selftest fail=0`.
- D4 preflight: `target.devname=sda33`, `target.dev=259:17`,
  `target.sectors=231577432`, `preflight=ok`.
- D4 format: `formatter=e2fsprogs-mkfs.ext4`, `has_journal=1`,
  `format=done`.
- D4 populate: corrected tarball SHA matched expected, `populate=done`.
- Switch-root retry reached `exec_switch_root_now`.
- SSH proof:
  - `pid1_comm=init`
  - `proc1_exe=/usr/sbin/init`
  - `/` mounted from `/dev/block/a90-userdata` as ext4
  - `hud_intent_run_dir_group=a90hud`
  - `hud_intent_run_dir_mode=1770`
  - `hud_intent_rc=0`
  - `hud_intent_written=1`
  - intent JSON schema `a90-dpublic-hud-intent-v1`
  - intent public state `PUBLIC_OFF`
  - `/run/a90-dpublic` stat: `root a90hud 1770`
  - `/run/a90-dpublic/hud-intent.json` stat: `a90hud a90hud 640`
  - `hud_presenter_staged=1`
  - `hud_presenter_owner=native-init`
  - `hud_presenter_started=0`
  - `hud_legacy_direct_kms_started=0`
  - `tunnel_started=manual`
  - `tunnel_process_alive=0`
  - `tunnel_url_observed=0`

## Important Boundary

This is a Debian-side split-HUD live pass, not a native presenter visual pass.
The live proof shows that Debian writes only the bounded JSON intent as
`a90hud`, does not start the presenter, and does not run the legacy direct-KMS
HUD.  The native/root-owned presenter consuming that intent and presenting it on
KMS remains the next integration unit.

## Validation

Host/static:

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/server-distro/prepare_wsta3_sta_rootfs.py
```

Live:

- `preflight-corrected-before-format.txt`
- `format-corrected.txt`
- `populate-corrected.txt`
- `switch-root-to-userdata-corrected-retry.txt`
- `ssh-proof-corrected.txt`
- `wsta135_corrected_live_summary.json`

All are private run artifacts under the WSTA135 run directory.

## Next

WSTA136 should implement the native/root-owned presenter consumption path:
read `/run/a90-dpublic/hud-intent.json`, reject stale or forbidden fields, and
present a minimal native KMS HUD without giving Debian direct DRM/KMS ownership.
