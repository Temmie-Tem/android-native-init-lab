# WSTA132 D-public HUD Split Prototype Source Pass

Date: 2026-07-05 07:50 KST

## Verdict

WSTA132 starts the implementation ladder for the WSTA130/WSTA131 split HUD
architecture.  It adds a minimal Debian-side intent producer and a root/native
presenter parser prototype, then proves the host and arm64 binaries can be built
and staged into a private rootfs-like tree.

This is still a host-only source/prototype unit.  It did not perform device
action, boot flash, native reboot, Wi-Fi association, DHCP, public tunnel,
public smoke, packet-filter mutation, userdata mutation, DRM open, KMS
`SETCRTC`, or switch-root.

## Added

- `workspace/public/src/scripts/server-distro/a90_dpublic_hud_intent.c`
  - writes `/run/a90-dpublic/hud-intent.json` by `write` + `fsync` + `rename`;
  - keeps the intent bounded to `4096` bytes;
  - creates the parent runtime directory and writes mode `0640`;
  - defaults public state to `PUBLIC_OFF`;
  - does not reference `/dev/dri`, KMS ioctls, or network APIs.

- `workspace/public/src/scripts/server-distro/a90_dpublic_hud_presenter.c`
  - validates the WSTA130 intent schema;
  - rejects over-size intents, missing required fields, forbidden fields, and
    unknown top-level keys;
  - records the root/native presenter as the KMS owner;
  - keeps live DRM/KMS presentation out of scope for this unit.

- `workspace/public/src/scripts/server-distro/run_wsta132_dpublic_hud_split_prototype.py`
  - inert by default and requires `--emit-split-prototype`;
  - fail-closes outside `workspace/private`;
  - compiles host and arm64 variants;
  - runs a host producer/presenter selftest;
  - stages arm64 binaries under `rootfs-stage/usr/local/bin/`.

- `tests/test_server_distro_wsta132_dpublic_hud_split_prototype.py`
  - covers default inert behavior, source contract, private build/stage proof,
    non-private fail-closed behavior, and redaction/source-scope checks.

- `tests/test_dpublic_smoke_helpers.py`
  - adds static checks for the split intent producer and presenter sources.

## Source Proof

Command:

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/server-distro/run_wsta132_dpublic_hud_split_prototype.py \
  --run-id wsta132-dpublic-hud-split-prototype-20260705T0750KST \
  --run-dir workspace/private/runs/server-distro/wsta132-dpublic-hud-split-prototype-20260705T0750KST \
  --emit-split-prototype
```

Private output:

`workspace/private/runs/server-distro/wsta132-dpublic-hud-split-prototype-20260705T0750KST/wsta132_dpublic_hud_split_prototype.json`

Result:

- decision: `wsta132-dpublic-hud-split-prototype-source-pass`
- gate decision: `ok`
- source contract: true
- host build: true
- arm64 build: true
- host selftest: true
- rootfs stage: true
- default public state: `PUBLIC_OFF`
- public URL value logged: false
- secret values logged: `0`

Host build outputs:

- intent producer SHA256:
  `e75a0d81ea008c907803ca7ab965d791fae8a07802fcf63a05f3e1d87fa24923`
- presenter SHA256:
  `d5e157eb5228a01c7a0212db4aebb808795077a58cb17154c7913193101efcdb`

Arm64 build outputs staged privately:

- `usr/local/bin/a90-dpublic-hud-intent`
  - SHA256:
    `f09d1eb6b57de50ed14fdf17d4d77751fc86ff41782ab51c90bb40ea070334f3`
  - mode: `0755`
- `usr/local/bin/a90-dpublic-hud-presenter`
  - SHA256:
    `055588a9c9ce61afa47ed532b2a7f62dbbef2a319d0b07fda1cd9b8d0fa2a76d`
  - mode: `0755`

Host selftest intent:

- size: `292` bytes
- SHA256: `7895d01d92ae4e760f4c9fca5e572bb7ba413fe978bbdc2fdeb2352736a0d4f3`
- schema: `a90-dpublic-hud-intent-v1`
- public state: `PUBLIC_OFF`

## Validation

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/server-distro/run_wsta132_dpublic_hud_split_prototype.py \
  tests/test_server_distro_wsta132_dpublic_hud_split_prototype.py \
  tests/test_dpublic_smoke_helpers.py
```

Pass.

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest discover \
  -s tests -p 'test_server_distro_wsta132_dpublic_hud_split_prototype.py'
```

`5 tests OK`.

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest discover \
  -s tests -p 'test_dpublic_smoke_helpers.py'
```

`15 tests OK`.

```sh
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest discover \
  -s tests -p 'test_server_distro_wsta*.py'
```

`447 tests OK`.

The WSTA94 runner-error JSON printed during the full run is the expected
exception-path fixture from that unit test; unittest completed OK.

## Next

WSTA133 should integrate the staged split HUD binaries into the D-public rootfs
preparation path and firstboot/profile wiring, still default-off and no-public.
The live proof should come after that integration: Debian writes only the
bounded intent file, while native/root owns DRM master and presentation.
